from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, SessionLocal, engine, get_db
from app.deps import get_current_user, require_admin
from app.models import StoredFileRecord, UploadEvent, User
from app.schemas import (
    CreateUserRequest,
    DashboardStats,
    FileListItem,
    LoginRequest,
    LoginResponse,
    UpdateUserRequest,
    UploadResult,
    UserPublic,
)
from app.services.auth import create_access_token, hash_password, verify_password
from app.services.process_upload import process_upload
from app.services.seed import migrate_schema, seed_default_users
from app.services.trainer import ensure_model


def _compute_stats(events: list[UploadEvent], stored: list[StoredFileRecord]) -> DashboardStats:
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
        elif e.decision == "stored_shared":
            # Cross-user dedup: file listed for user but 0 KB written; size_bytes = original size saved
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


def _event_dict(r: UploadEvent, username: str | None = None) -> dict:
    return {
        "id": r.id,
        "original_name": r.original_name,
        "decision": r.decision,
        "size_bytes": r.size_bytes,
        "max_similarity": r.max_similarity,
        "risk_score": r.risk_score,
        "reason": r.reason,
        "created_at": r.created_at.isoformat(),
        "kind": r.kind,
        "user_id": r.user_id,
        "username": username,
    }


def _username_map(db: Session) -> dict[int, str]:
    return {u.id: u.username for u in db.query(User).all()}


def create_app() -> FastAPI:
    ensure_model(settings.ml_model_path)
    Base.metadata.create_all(bind=engine)
    migrate_schema(engine)
    with SessionLocal() as db:
        seed_default_users(db)

    app = FastAPI(title=settings.project_name, version="1.1.0")

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

    @app.get("/")
    def root():
        return {
            "service": settings.project_name,
            "message": "API is running. Open the frontend at http://localhost:5173",
            "health": "/api/health",
            "docs": "/docs",
        }

    @app.get("/api/health")
    def health():
        return {"status": "ok", "service": settings.project_name}

    @app.post("/api/auth/login", response_model=LoginResponse)
    def login(body: LoginRequest, db: Session = Depends(get_db)):
        username = body.username.strip()
        if not username:
            raise HTTPException(status_code=401, detail="Invalid username or password.")
        user = (
            db.query(User)
            .filter(func.lower(User.username) == username.lower())
            .first()
        )
        if not user or not user.is_active or not verify_password(body.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid username or password.")
        token = create_access_token(user.id, user.username, user.role)
        return LoginResponse(access_token=token, user=UserPublic.model_validate(user))

    @app.get("/api/auth/me", response_model=UserPublic)
    def me(user: User = Depends(get_current_user)):
        return UserPublic.model_validate(user)

    @app.post("/api/upload", response_model=UploadResult)
    async def upload_file(
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user),
    ):
        raw = await file.read()
        if not raw:
            raise HTTPException(status_code=400, detail="Empty file.")
        mime = file.content_type or "application/octet-stream"
        try:
            result = process_upload(db, file.filename or "unnamed", mime, raw, user.id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        return UploadResult(**result)

    @app.get("/api/me/stats", response_model=DashboardStats)
    def my_stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
        events = db.query(UploadEvent).filter(UploadEvent.user_id == user.id).all()
        stored = (
            db.query(StoredFileRecord)
            .filter(
                StoredFileRecord.user_id == user.id,
                StoredFileRecord.decision.in_(("stored", "stored_shared")),
            )
            .all()
        )
        return _compute_stats(events, stored)

    @app.get("/api/me/events", response_model=list[dict])
    def my_events(
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user),
        limit: int = 100,
    ):
        rows = (
            db.query(UploadEvent)
            .filter(UploadEvent.user_id == user.id)
            .order_by(UploadEvent.created_at.desc())
            .limit(limit)
            .all()
        )
        return [_event_dict(r, user.username) for r in rows]

    @app.get("/api/me/duplicates", response_model=list[dict])
    def my_duplicates(
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user),
        limit: int = 100,
    ):
        rows = (
            db.query(UploadEvent)
            .filter(
                UploadEvent.user_id == user.id,
                UploadEvent.decision.in_(("rejected_duplicate", "rejected_redundant")),
            )
            .order_by(UploadEvent.created_at.desc())
            .limit(limit)
            .all()
        )
        return [_event_dict(r, user.username) for r in rows]

    @app.get("/api/stats", response_model=DashboardStats)
    def stats(db: Session = Depends(get_db), _: User = Depends(require_admin)):
        events = db.query(UploadEvent).all()
        stored = (
            db.query(StoredFileRecord)
            .filter(StoredFileRecord.decision.in_(("stored", "stored_shared")))
            .all()
        )
        return _compute_stats(events, stored)

    @app.get("/api/files", response_model=list[FileListItem])
    def list_files(
        db: Session = Depends(get_db),
        _: User = Depends(require_admin),
        limit: int = 50,
    ):
        rows = (
            db.query(StoredFileRecord)
            .order_by(StoredFileRecord.created_at.desc())
            .limit(limit)
            .all()
        )
        return [FileListItem.model_validate(r) for r in rows]

    @app.get("/api/events", response_model=list[dict])
    def list_events(
        db: Session = Depends(get_db),
        _: User = Depends(require_admin),
        limit: int = 80,
        user_id: int | None = None,
    ):
        q = db.query(UploadEvent)
        if user_id is not None:
            q = q.filter(UploadEvent.user_id == user_id)
        rows = q.order_by(UploadEvent.created_at.desc()).limit(limit).all()
        names = _username_map(db)
        return [_event_dict(r, names.get(r.user_id) if r.user_id else None) for r in rows]

    @app.get("/api/admin/users/{user_id}/events", response_model=list[dict])
    def admin_user_events(
        user_id: int,
        db: Session = Depends(get_db),
        _: User = Depends(require_admin),
        limit: int = 100,
    ):
        target = db.get(User, user_id)
        if not target:
            raise HTTPException(status_code=404, detail="User not found.")
        rows = (
            db.query(UploadEvent)
            .filter(UploadEvent.user_id == user_id)
            .order_by(UploadEvent.created_at.desc())
            .limit(limit)
            .all()
        )
        return [_event_dict(r, target.username) for r in rows]

    @app.get("/api/admin/users", response_model=list[UserPublic])
    def list_users(db: Session = Depends(get_db), _: User = Depends(require_admin)):
        rows = db.query(User).order_by(User.created_at.desc()).all()
        return [UserPublic.model_validate(r) for r in rows]

    @app.post("/api/admin/users", response_model=UserPublic, status_code=201)
    def create_user(
        body: CreateUserRequest,
        db: Session = Depends(get_db),
        _: User = Depends(require_admin),
    ):
        username = body.username.strip().lower()
        if not username:
            raise HTTPException(status_code=400, detail="Username is required.")
        if len(body.password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")
        role = body.role.strip().lower()
        if role not in ("admin", "user"):
            raise HTTPException(status_code=400, detail="Role must be 'admin' or 'user'.")
        if db.query(User).filter(func.lower(User.username) == username).first():
            raise HTTPException(status_code=409, detail="Username already exists.")
        user = User(
            username=username,
            password_hash=hash_password(body.password),
            role=role,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return UserPublic.model_validate(user)

    @app.patch("/api/admin/users/{user_id}", response_model=UserPublic)
    def update_user(
        user_id: int,
        body: UpdateUserRequest,
        db: Session = Depends(get_db),
        admin: User = Depends(require_admin),
    ):
        user = db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")
        if user.id == admin.id and body.is_active is False:
            raise HTTPException(status_code=400, detail="You cannot deactivate your own account.")
        if body.is_active is not None:
            user.is_active = body.is_active
        if body.password:
            if len(body.password) < 6:
                raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")
            user.password_hash = hash_password(body.password)
        db.commit()
        db.refresh(user)
        return UserPublic.model_validate(user)

    @app.delete("/api/admin/users/{user_id}", status_code=204)
    def delete_user(
        user_id: int,
        db: Session = Depends(get_db),
        admin: User = Depends(require_admin),
    ):
        user = db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")
        if user.id == admin.id:
            raise HTTPException(status_code=400, detail="You cannot delete your own account.")
        if user.role == "admin":
            raise HTTPException(status_code=400, detail="Cannot delete an admin account.")
        # Clear ownership so FK rows do not block delete (keep history under admin)
        admin_id = admin.id
        db.query(StoredFileRecord).filter(StoredFileRecord.user_id == user.id).update(
            {StoredFileRecord.user_id: admin_id}
        )
        db.query(UploadEvent).filter(UploadEvent.user_id == user.id).update(
            {UploadEvent.user_id: admin_id}
        )
        db.delete(user)
        db.commit()
        return None

    return app


app = create_app()
