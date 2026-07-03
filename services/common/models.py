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


class TaskCreateRequest(BaseModel):
    """Request model for creating a task."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Task title",
    )
    description: Optional[str] = Field(
        default=None,
        max_length=5000,
        description="Task description or details",
    )
    status: Optional[TaskStatus] = Field(
        default=TaskStatus.TODO,
        description="Task status",
    )
    priority: Optional[TaskPriority] = Field(
        default=TaskPriority.MEDIUM,
        description="Task priority level",
    )
    assignee_id: Optional[int] = Field(
        default=None,
        gt=0,
        description="ID of assigned user (optional)",
    )

    class Config:
        examples = [
            {
                "title": "Implement authentication",
                "description": "Add JWT-based authentication to the API",
                "status": "in_progress",
                "priority": "high",
                "assignee_id": 1,
            }
        ]


class TaskUpdateRequest(BaseModel):
    """Request model for updating a task."""

    title: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=500,
        description="Updated task title",
    )
    description: Optional[str] = Field(
        default=None,
        max_length=5000,
        description="Updated task description",
    )
    status: Optional[TaskStatus] = Field(
        default=None,
        description="Updated task status",
    )
    priority: Optional[TaskPriority] = Field(
        default=None,
        description="Updated task priority",
    )
    assignee_id: Optional[int] = Field(
        default=None,
        gt=0,
        description="Updated assignee ID (optional)",
    )

    class Config:
        examples = [
            {
                "title": "Updated task title",
                "status": "done",
                "priority": "medium",
            }
        ]


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
