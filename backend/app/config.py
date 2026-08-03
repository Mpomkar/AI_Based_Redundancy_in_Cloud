from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_ROOT = Path(__file__).resolve().parent.parent


def _default_sqlite_url() -> str:
    return f"sqlite:///{(_BACKEND_ROOT / 'app.db').as_posix()}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        protected_namespaces=("settings_",),
    )

    project_name: str = "Cloud Redundancy AI"
    api_prefix: str = "/api"
    storage_dir: Path = _BACKEND_ROOT / "storage"
    uploads_subdir: str = "uploads"
    database_url: str = Field(default_factory=_default_sqlite_url)
    ml_model_path: Path = _BACKEND_ROOT / "models" / "redundancy_model.joblib"
    redundant_threshold: float = 0.62
    # Policy: reject when best similarity (0–100) is >= this (documents: word Jaccard; images: pHash score × 100).
    content_match_reject_threshold_percent: float = 92.0
    max_pdf_text_chars: int = 120_000
    image_hash_size: int = 8


settings = Settings()
