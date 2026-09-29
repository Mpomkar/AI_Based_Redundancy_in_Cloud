from __future__ import annotations

import re
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import StoredFileRecord, UploadEvent, User
from app.services.docx_text import extract_docx_text
from app.services.features import build_features
from app.services.hasher import sha256_bytes
from app.services.image_sim import phash_hex, phash_similarity
from app.services.pdf_text import extract_pdf_text, jaccard_word_similarity
from app.services.predictor import redundant_probability, risk_score
from app.services.text_guidance import build_content_guidance, build_image_guidance
from app.services.upload_validation import reject_if_blocked, validate_file_content


def _kind_from_mime(mime: str) -> str | None:
    m = (mime or "").lower().split(";")[0].strip()
    if m == "application/pdf":
        return "pdf"
    if m == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return "docx"
    if m in ("image/jpeg", "image/png", "image/webp", "image/gif"):
        return "image"
    return None


def _kind_from_filename(filename: str) -> str | None:
    ext = Path(filename or "").suffix.lower()
    if ext == ".pdf":
        return "pdf"
    if ext == ".docx":
        return "docx"
    if ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        return "image"
    return None


def _detect_kind(mime: str, filename: str) -> str | None:
    """Prefer MIME, fall back to extension (browsers often send octet-stream)."""
    return _kind_from_mime(mime) or _kind_from_filename(filename)


def _ensure_dirs(user_id: int) -> Path:
    base = settings.storage_dir / settings.uploads_subdir / str(user_id)
    base.mkdir(parents=True, exist_ok=True)
    return base


def _truncate(s: str, n: int = 256) -> str:
    return s if len(s) <= n else s[: n - 3] + "..."


def _should_reject_redundant(ml_p: float, sim: float) -> bool:
    if sim >= 0.96:
        return True
    if ml_p >= 0.88 and sim >= 0.4:
        return True
    if ml_p >= settings.redundant_threshold and sim >= 0.5:
        return True
    return False


def _default_ext(kind: str, filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext:
        return ext
    if kind == "pdf":
        return ".pdf"
    if kind == "docx":
        return ".docx"
    return ".bin"


def _safe_stored_name(filename: str, kind: str) -> str:
    """Keep original name recognizable on disk; UUID suffix avoids collisions."""
    ext = _default_ext(kind, filename)
    stem = Path(filename or "file").stem
    stem = re.sub(r"[^\w.\-]+", "_", stem, flags=re.UNICODE).strip("._") or "file"
    stem = stem[:80]
    return f"{stem}_{uuid.uuid4().hex[:10]}{ext}"


def process_upload(
    db: Session,
    filename: str,
    mime: str,
    data: bytes,
    user_id: int,
) -> dict:
    reject_if_blocked(filename, mime)
    kind = _detect_kind(mime, filename)
    if not kind:
        raise ValueError(
            "Unsupported file type. Upload PDF, Word (.docx), or image (JPEG, PNG, WebP, GIF)."
        )
    validate_file_content(kind, data)

    threshold = settings.content_match_reject_threshold_percent
    h = sha256_bytes(data)
    size = len(data)

    policy_meta = {"policy_threshold_percent": threshold}

    # 1) Same user already has this exact file → reject (no second copy for them)
    existing = db.execute(
        select(StoredFileRecord).where(
            StoredFileRecord.sha256 == h,
            StoredFileRecord.user_id == user_id,
        )
    ).scalar_one_or_none()
    if existing:
        ev = UploadEvent(
            user_id=user_id,
            original_name=filename,
            sha256=h,
            size_bytes=size,
            mime=mime,
            kind=kind,
            max_similarity=1.0,
            risk_score=100.0,
            decision="rejected_duplicate",
            reason=_truncate("Exact duplicate (SHA-256 match)."),
        )
        db.add(ev)
        db.commit()
        return {
            "filename": filename,
            "decision": "rejected_duplicate",
            "reason": "Exact duplicate — you already uploaded this file (same content).",
            "sha256": h,
            "size_bytes": size,
            "original_size_bytes": size,
            "max_similarity": 1.0,
            "risk_score": 100.0,
            "ml_redundant_probability": 1.0,
            "content_match_percent": 100.0,
            "compared_to_filename": existing.original_name,
            "compared_to_user": None,
            "content_guidance": "Byte-identical to a file already in your library (same SHA-256).",
            "toast_message": (
                f'Duplicate blocked: "{filename}" matches your existing file '
                f'"{existing.original_name}". Not stored again.'
            ),
            **policy_meta,
        }

    # 2) Another user already has the same content → store for this user as 0 KB shared ref
    global_match = db.execute(
        select(StoredFileRecord)
        .where(
            StoredFileRecord.sha256 == h,
            StoredFileRecord.user_id != user_id,
            StoredFileRecord.decision.in_(("stored", "stored_shared")),
        )
        .order_by(StoredFileRecord.size_bytes.desc())
    ).scalars().first()
    if global_match:
        owner = db.get(User, global_match.user_id) if global_match.user_id else None
        owner_name = owner.username if owner else "another user"
        shared_path = global_match.relative_path or ""
        toast = (
            f'Same content already exists (uploaded by {owner_name} as '
            f'"{global_match.original_name}"). Your file "{filename}" was stored '
            f"as a 0 KB shared reference - no extra storage used."
        )
        reason = (
            f"Stored as 0 KB shared copy: identical content already in the system "
            f'(user "{owner_name}", file "{global_match.original_name}").'
        )
        rec = StoredFileRecord(
            user_id=user_id,
            original_name=filename,
            sha256=h,
            mime=mime,
            size_bytes=0,  # 0 KB for this user — physical bytes reused
            relative_path=shared_path,
            kind=kind,
            pdf_text_excerpt=global_match.pdf_text_excerpt,
            image_phash=global_match.image_phash,
            max_similarity=1.0,
            risk_score=100.0,
            ml_redundant_proba=1.0,
            decision="stored_shared",
        )
        db.add(rec)
        ev = UploadEvent(
            user_id=user_id,
            original_name=filename,
            sha256=h,
            size_bytes=size,  # original size counted as storage saved
            mime=mime,
            kind=kind,
            max_similarity=1.0,
            risk_score=100.0,
            decision="stored_shared",
            reason=_truncate(reason),
        )
        db.add(ev)
        db.commit()
        return {
            "filename": filename,
            "decision": "stored_shared",
            "reason": reason,
            "sha256": h,
            "size_bytes": 0,
            "original_size_bytes": size,
            "max_similarity": 1.0,
            "risk_score": 100.0,
            "ml_redundant_probability": 1.0,
            "content_match_percent": 100.0,
            "compared_to_filename": global_match.original_name,
            "compared_to_user": owner_name,
            "content_guidance": (
                "Exact match with another user's file. Your account keeps a listing "
                "with 0 KB stored; the original bytes are shared on the server."
            ),
            "toast_message": toast,
            **policy_meta,
        }

    max_sim = 0.0
    best_match_size: int | None = None
    similar_count = 0
    doc_text: str | None = None
    img_phash: str | None = None
    best_match_row: StoredFileRecord | None = None

    if kind in ("pdf", "docx"):
        try:
            if kind == "pdf":
                doc_text = extract_pdf_text(data)
            else:
                doc_text = extract_docx_text(data, max_chars=settings.max_pdf_text_chars)
        except Exception:
            doc_text = ""
        rows = db.execute(
            select(StoredFileRecord).where(
                StoredFileRecord.user_id == user_id,
                StoredFileRecord.kind.in_(("pdf", "docx")),
                StoredFileRecord.decision.in_(("stored", "stored_shared")),
            )
        ).scalars().all()
        for row in rows:
            if not row.pdf_text_excerpt:
                continue
            sim = jaccard_word_similarity(doc_text or "", row.pdf_text_excerpt)
            if sim > max_sim:
                max_sim = sim
                best_match_size = row.size_bytes
                best_match_row = row
            if sim >= 0.55:
                similar_count += 1
    else:
        try:
            img_phash = phash_hex(data)
        except Exception as e:
            raise ValueError(
                "Corrupted or unreadable image. The file could not be opened and was not accepted."
            ) from e
        rows = db.execute(
            select(StoredFileRecord).where(
                StoredFileRecord.user_id == user_id,
                StoredFileRecord.kind == "image",
                StoredFileRecord.decision.in_(("stored", "stored_shared")),
                StoredFileRecord.image_phash.isnot(None),
            )
        ).scalars().all()
        for row in rows:
            if not row.image_phash:
                continue
            sim = phash_similarity(img_phash, row.image_phash)
            if sim > max_sim:
                max_sim = sim
                best_match_size = row.size_bytes
                best_match_row = row
            if sim >= 0.55:
                similar_count += 1

    sim_percent = max_sim * 100.0
    reject_policy = max_sim > 0 and sim_percent >= threshold

    content_guidance: str | None = None
    compared_to: str | None = None
    if kind in ("pdf", "docx") and best_match_row and best_match_row.pdf_text_excerpt:
        compared_to = best_match_row.original_name
        content_guidance = build_content_guidance(
            doc_text or "",
            best_match_row.pdf_text_excerpt,
            best_match_row.original_name,
            max_sim,
        )
    elif kind == "image" and best_match_row:
        compared_to = best_match_row.original_name
        content_guidance = build_image_guidance(max_sim, best_match_row.original_name)

    feats = build_features(max_sim, size, best_match_size, similar_count)
    ml_p = redundant_probability(feats)
    risk = risk_score(ml_p, max_sim)

    reject_ml = (max_sim >= 0.12) and _should_reject_redundant(ml_p, max_sim)
    reject = reject_policy or reject_ml

    if reject_policy:
        reason = (
            f"Rejected: content match {sim_percent:.1f}% meets or exceeds policy threshold ({threshold}% — near-duplicate)."
        )
    elif reject:
        reason = "Rejected: high redundancy risk (similarity + ML score)."
    else:
        reason = "Stored: below policy threshold and acceptable similarity."

    decision = "rejected_redundant" if reject else "stored"

    rel_path = ""
    if not reject:
        upload_dir = _ensure_dirs(user_id)
        safe_name = _safe_stored_name(filename, kind)
        full = upload_dir / safe_name
        full.write_bytes(data)
        rel_path = f"{settings.uploads_subdir}/{user_id}/{safe_name}"

        excerpt = (doc_text[:80_000] if doc_text else None)
        rec = StoredFileRecord(
            user_id=user_id,
            original_name=filename,
            sha256=h,
            mime=mime,
            size_bytes=size,
            relative_path=rel_path,
            kind=kind,
            pdf_text_excerpt=excerpt,
            image_phash=img_phash,
            max_similarity=max_sim,
            risk_score=risk,
            ml_redundant_proba=ml_p,
            decision="stored",
        )
        db.add(rec)

    ev = UploadEvent(
        user_id=user_id,
        original_name=filename,
        sha256=h,
        size_bytes=size,
        mime=mime,
        kind=kind,
        max_similarity=max_sim,
        risk_score=risk,
        decision=decision,
        reason=_truncate(reason),
    )
    db.add(ev)
    db.commit()

    toast: str | None = None
    if reject:
        # reason already starts with "Rejected:"
        toast = reason
    else:
        toast = f'Stored successfully: "{filename}" ({size} bytes).'

    return {
        "filename": filename,
        "decision": decision,
        "reason": reason,
        "sha256": h,
        "size_bytes": size if not reject else size,
        "original_size_bytes": size,
        "max_similarity": round(max_sim, 4),
        "risk_score": risk,
        "ml_redundant_probability": round(ml_p, 4),
        "content_match_percent": round(sim_percent, 2),
        "compared_to_filename": compared_to,
        "compared_to_user": None,
        "content_guidance": content_guidance,
        "toast_message": toast,
        **policy_meta,
    }
