from datetime import datetime

from pydantic import BaseModel, Field


class UploadResult(BaseModel):
    filename: str
    decision: str = Field(
        description="stored | rejected_duplicate | rejected_redundant"
    )
    reason: str
    sha256: str
    size_bytes: int
    max_similarity: float = Field(ge=0, le=1)
    risk_score: float = Field(ge=0, le=100)
    ml_redundant_probability: float = Field(ge=0, le=1)
    content_match_percent: float = Field(
        default=0, ge=0, le=100, description="Best similarity as percent (word Jaccard or image pHash)."
    )
    compared_to_filename: str | None = None
    content_guidance: str | None = None
    policy_threshold_percent: float = Field(
        default=92.0, description="Configured policy: reject at or above this match %."
    )


class FileListItem(BaseModel):
    id: int
    original_name: str
    decision: str
    size_bytes: int
    max_similarity: float
    risk_score: float
    created_at: datetime
    kind: str

    model_config = {"from_attributes": True}


class DashboardStats(BaseModel):
    total_upload_attempts: int
    total_stored_files: int
    rejected_duplicates: int
    rejected_redundant: int
    storage_saved_bytes: int
    avg_risk_stored: float
    by_decision: dict[str, int]
