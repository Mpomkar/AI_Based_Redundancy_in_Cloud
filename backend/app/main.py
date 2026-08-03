from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, engine, get_db
from app.models import StoredFileRecord, UploadEvent
from app.schemas import DashboardStats, FileListItem, UploadResult
from app.services.process_upload import process_upload
from app.services.trainer import ensure_model


def create_app() -> FastAPI:
    ensure_model(settings.ml_model_path)
    Base.metadata.create_all(bind=engine)

    app = FastAPI(title=settings.project_name, version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    upload_root = settings.storage_dir / settings.uploads_subdir
    upload_root.mkdir(parents=True, exist_ok=True)
    app.mount(
        "/static/uploads",
        StaticFiles(directory=str(upload_root)),
        name="uploads",
    )

    @app.get("/api/health")
    def health():
        return {"status": "ok", "service": settings.project_name}

    @app.post("/api/upload", response_model=UploadResult)
    async def upload_file(
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
    ):
        raw = await file.read()
        if not raw:
            raise HTTPException(status_code=400, detail="Empty file.")
        mime = file.content_type or "application/octet-stream"
        try:
            result = process_upload(db, file.filename or "unnamed", mime, raw)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        return UploadResult(**result)

    @app.get("/api/stats", response_model=DashboardStats)
    def stats(db: Session = Depends(get_db)):
        events = db.query(UploadEvent).all()
        stored = db.query(StoredFileRecord).filter(StoredFileRecord.decision == "stored").all()
        by_decision: dict[str, int] = {}
        saved = 0
        rejected_dup = 0
        rejected_red = 0
        for e in events:
            by_decision[e.decision] = by_decision.get(e.decision, 0) + 1
            if e.decision == "rejected_duplicate":
                rejected_dup += 1
                saved += e.size_bytes
            elif e.decision == "rejected_redundant":
                rejected_red += 1
                saved += e.size_bytes
        risks = [float(s.risk_score) for s in stored]
        avg_risk = sum(risks) / len(risks) if risks else 0.0
        return DashboardStats(
            total_upload_attempts=len(events),
            total_stored_files=len(stored),
            rejected_duplicates=rejected_dup,
            rejected_redundant=rejected_red,
            storage_saved_bytes=saved,
            avg_risk_stored=round(avg_risk, 2),
            by_decision=by_decision,
        )

    @app.get("/api/files", response_model=list[FileListItem])
    def list_files(db: Session = Depends(get_db), limit: int = 50):
        rows = (
            db.query(StoredFileRecord)
            .order_by(StoredFileRecord.created_at.desc())
            .limit(limit)
            .all()
        )
        return [FileListItem.model_validate(r) for r in rows]

    @app.get("/api/events", response_model=list[dict])
    def list_events(db: Session = Depends(get_db), limit: int = 80):
        rows = (
            db.query(UploadEvent)
            .order_by(UploadEvent.created_at.desc())
            .limit(limit)
            .all()
        )
        out = []
        for r in rows:
            out.append(
                {
                    "id": r.id,
                    "original_name": r.original_name,
                    "decision": r.decision,
                    "size_bytes": r.size_bytes,
                    "max_similarity": r.max_similarity,
                    "risk_score": r.risk_score,
                    "reason": r.reason,
                    "created_at": r.created_at.isoformat(),
                    "kind": r.kind,
                }
            )
        return out

    return app


app = create_app()
