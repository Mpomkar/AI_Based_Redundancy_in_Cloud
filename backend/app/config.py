from pathlib import Path
import os
import sys

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_ROOT = Path(__file__).resolve().parent.parent


def _default_sqlite_url() -> str:
    return f"sqlite:///{(_BACKEND_ROOT / 'app.db').as_posix()}"


def _resolve_desktop() -> Path | None:
    """Best-effort user Desktop (handles Windows OneDrive Desktop redirection)."""
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
            # CSIDL_DESKTOPDIRECTORY = 0x10
            if ctypes.windll.shell32.SHGetFolderPathW(None, 0x10, None, 0, buf) == 0:
                p = Path(buf.value)
                if p.is_dir():
                    return p
        except Exception:
            pass
        for key in ("USERPROFILE", "HOME"):
            base = os.environ.get(key)
            if not base:
                continue
            for rel in ("Desktop", "OneDrive\\Desktop"):
                p = Path(base) / rel
                if p.is_dir():
                    return p
    for candidate in (Path.home() / "Desktop", Path.home() / "OneDrive" / "Desktop"):
        if candidate.is_dir():
            return candidate
    return None


def _default_storage_dir() -> Path:
    """
    Store accepted uploads on the Desktop in 'Uploaded Files'.
    Multi-PC: this path is on the machine running the backend — other PCs
    access the same files via that shared API (do not run a second backend).
    Override with STORAGE_DIR in backend/.env if needed.
    """
    desktop = _resolve_desktop()
    if desktop is not None:
        return desktop / "Uploaded Files"
    return _BACKEND_ROOT / "storage"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_BACKEND_ROOT / ".env"),
        extra="ignore",
        protected_namespaces=("settings_",),
    )

    project_name: str = "Cloud Redundancy AI"
    api_prefix: str = "/api"
    storage_dir: Path = Field(default_factory=_default_storage_dir)
    uploads_subdir: str = "uploads"
    database_url: str = Field(default_factory=_default_sqlite_url)
    ml_model_path: Path = _BACKEND_ROOT / "models" / "redundancy_model.joblib"
    redundant_threshold: float = 0.62
    # Policy: reject when best similarity (0–100) is >= this (documents: word Jaccard; images: pHash score × 100).
    content_match_reject_threshold_percent: float = 92.0
    max_pdf_text_chars: int = 120_000
    image_hash_size: int = 8
    jwt_secret_key: str = "change-me-in-production-cloud-redundancy-ai"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480


settings = Settings()
# Ensure the Desktop upload folder exists as soon as settings load
settings.storage_dir.mkdir(parents=True, exist_ok=True)
(settings.storage_dir / settings.uploads_subdir).mkdir(parents=True, exist_ok=True)
