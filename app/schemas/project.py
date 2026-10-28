from pydantic import BaseModel, Field
from datetime import datetime

class ProjectCreate(BaseModel):
    name: str = Field(min_length=3, max_length=100)
    description: str = Field(default="", max_length=1000)


class ProjectUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=3,
        max_length=100
    )
    description: str | None = Field(
        default=None,
        max_length=1000
    )

class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str | None=None
    tenant_id: str
    created_by: str
    created_at: datetime | None=None

class ProjectListResponse(BaseModel):
    page: int
    page_size: int
    total: int
    projects: list[ProjectResponse]