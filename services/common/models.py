"""
Common Pydantic models for request/response validation.
"""
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Task status enumeration."""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class TaskPriority(str, Enum):
    """Task priority enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class ProjectCreateRequest(BaseModel):
    """Request model for creating a project."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Project name",
    )
    description: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Project description",
    )

    class Config:
        examples = [
            {
                "name": "Mobile App",
                "description": "Development of mobile application",
            }
        ]


class ProjectUpdateRequest(BaseModel):
    """Request model for updating a project."""

    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Updated project name",
    )
    description: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Updated project description",
    )

    class Config:
        examples = [
            {
                "name": "Updated Project Name",
                "description": "Updated description",
            }
        ]


class ProjectResponse(BaseModel):
    """Response model for project."""

    id: int
    name: str
    description: Optional[str]
    owner_id: int

    class Config:
        from_attributes = True


class ProjectCollaboratorRole(str, Enum):
    """Possible collaborator roles within a project."""

    VIEWER = "viewer"
    EDITOR = "editor"
    ADMIN = "admin"


class ProjectCollaboratorResponse(BaseModel):
    """Response model for a project collaborator."""

    id: int
    project_id: int
    user_id: int
    email: str
    role: str

    class Config:
        from_attributes = True


class TaskResponse(BaseModel):
    """Response model for task."""

    id: int
    title: str
    description: Optional[str]
    status: str
    priority: str
    project_id: int
    creator_id: int
    assignee_id: Optional[int]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True
