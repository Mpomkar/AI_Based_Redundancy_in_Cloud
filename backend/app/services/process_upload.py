from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import StoredFileRecord, UploadEvent
from app.services.docx_text import extract_docx_text
from app.services.features import build_features
from app.services.hasher import sha256_bytes
from app.services.image_sim import phash_hex, phash_similarity
from app.services.pdf_text import extract_pdf_text, jaccard_word_similarity
from app.services.predictor import redundant_probability, risk_score
from app.services.text_guidance import build_content_guidance, build_image_guidance


def _kind_from_mime(mime: str) -> str | None:
    m = (mime or "").lower().split(";")[0].strip()
    if m == "application/pdf":
        return "pdf"
    if m == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return "docx"
    if m in ("image/jpeg", "image/png", "image/webp", "image/gif"):
        return "image"
    return None


def _ensure_dirs() -> Path:
    base = settings.storage_dir / settings.uploads_subdir
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


def process_upload(
    db: Session,
    filename: str,
    mime: str,
    data: bytes,
) -> dict:
    kind = _kind_from_mime(mime)
    if not kind:
        raise ValueError(
            "Unsupported file type. Upload PDF, Word (.docx), or image (JPEG, PNG, WebP, GIF)."
        )

    threshold = settings.content_match_reject_threshold_percent
    h = sha256_bytes(data)
    size = len(data)

    policy_meta = {"policy_threshold_percent": threshold}

    existing = db.execute(select(StoredFileRecord).where(StoredFileRecord.sha256 == h)).scalar_one_or_none()
    if existing:
        ev = UploadEvent(
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
            "reason": "Exact duplicate (SHA-256 match).",
            "sha256": h,
            "size_bytes": size,
            "max_similarity": 1.0,
            "risk_score": 100.0,
            "ml_redundant_probability": 1.0,
            "content_match_percent": 100.0,
            "compared_to_filename": None,
            "content_guidance": "Byte-identical to an already stored file (same SHA-256).",
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
                StoredFileRecord.kind.in_(("pdf", "docx")),
                StoredFileRecord.decision == "stored",
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
            raise ValueError(f"Could not read image: {e}") from e
        rows = db.execute(
            select(StoredFileRecord).where(
                StoredFileRecord.kind == "image",
                StoredFileRecord.decision == "stored",
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
        upload_dir = _ensure_dirs()
        ext = _default_ext(kind, filename)
        safe_name = f"{uuid.uuid4().hex}{ext}"
        full = upload_dir / safe_name
        full.write_bytes(data)
        rel_path = f"{settings.uploads_subdir}/{safe_name}"

        excerpt = (doc_text[:80_000] if doc_text else None)
        rec = StoredFileRecord(
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

    return {
        "filename": filename,
        "decision": decision,
        "reason": reason,
        "sha256": h,
        "size_bytes": size,
        "max_similarity": round(max_sim, 4),
        "risk_score": risk,
        "ml_redundant_probability": round(ml_p, 4),
        "content_match_percent": round(sim_percent, 2),
        "compared_to_filename": compared_to,
        "content_guidance": content_guidance,
        **policy_meta,
    }
