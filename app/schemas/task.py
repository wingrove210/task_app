from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.tag import TagResponse


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    assignee_id: Optional[int] = None

    @field_validator("assignee_id", mode="before")
    @classmethod
    def convert_zero_to_none(cls, v):
        return None if v == 0 else v


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assignee_id: Optional[int] = None

    @field_validator("assignee_id", mode="before")
    @classmethod
    def convert_zero_to_none(cls, v):
        return None if v == 0 else v


class TaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    status: str
    priority: str
    project_id: int
    creator_id: int
    assignee_id: Optional[int]
    tags: list[TagResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)