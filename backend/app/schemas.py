from datetime import datetime

from pydantic import BaseModel, Field


class UploadResult(BaseModel):
    filename: str
    decision: str = Field(
        description="stored | stored_shared | rejected_duplicate | rejected_redundant"
    )
    reason: str
    sha256: str
    size_bytes: int = Field(description="Bytes stored for this user (0 when shared/deduped).")
    original_size_bytes: int | None = Field(
        default=None, description="Original upload size before cross-user dedup."
    )
    max_similarity: float = Field(ge=0, le=1)
    risk_score: float = Field(ge=0, le=100)
    ml_redundant_probability: float = Field(ge=0, le=1)
    content_match_percent: float = Field(
        default=0, ge=0, le=100, description="Best similarity as percent (word Jaccard or image pHash)."
    )
    compared_to_filename: str | None = None
    compared_to_user: str | None = None
    content_guidance: str | None = None
    toast_message: str | None = Field(
        default=None, description="User-facing toast for UI (e.g. cross-user dedup)."
    )
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


class LoginRequest(BaseModel):
    username: str
    password: str


class UserPublic(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = "user"


class UpdateUserRequest(BaseModel):
    is_active: bool | None = None
    password: str | None = None
