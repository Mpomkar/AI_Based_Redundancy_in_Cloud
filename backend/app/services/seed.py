from __future__ import annotations

from sqlalchemy import func, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models import UploadEvent, StoredFileRecord, User
from app.services.auth import hash_password


def _column_exists(engine: Engine, table: str, column: str) -> bool:
    insp = inspect(engine)
    if table not in insp.get_table_names():
        return False
    return column in {c["name"] for c in insp.get_columns(table)}


def migrate_schema(engine: Engine) -> None:
    """Add user_id columns to legacy tables when upgrading an existing DB."""
    with engine.begin() as conn:
        if not _column_exists(engine, "stored_files", "user_id"):
            conn.execute(text("ALTER TABLE stored_files ADD COLUMN user_id INTEGER"))
        if not _column_exists(engine, "upload_events", "user_id"):
            conn.execute(text("ALTER TABLE upload_events ADD COLUMN user_id INTEGER"))


def _ensure_user(db: Session, username: str, password: str, role: str) -> User:
    user = (
        db.query(User)
        .filter(func.lower(User.username) == username.lower())
        .first()
    )
    if not user:
        user = User(
            username=username.lower(),
            password_hash=hash_password(password),
            role=role,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def seed_default_users(db: Session) -> User:
    admin = _ensure_user(db, "admin", "ADMIN123", "admin")
    # Demo account for presentations (user portal)
    _ensure_user(db, "user", "USER123", "user")

    # Assign legacy rows without owner to admin.
    db.query(StoredFileRecord).filter(StoredFileRecord.user_id.is_(None)).update(
        {StoredFileRecord.user_id: admin.id}
    )
    db.query(UploadEvent).filter(UploadEvent.user_id.is_(None)).update(
        {UploadEvent.user_id: admin.id}
    )
    db.commit()
    return admin
