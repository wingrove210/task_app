from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
)

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import TaskPriority, TaskStatus
from app.models.mixins import TimestampMixin
from app.models.task_tag import task_tags

if TYPE_CHECKING:
    from app.models.comment import Comment
    from app.models.project import Project
    from app.models.tag import Tag
    from app.models.user import User


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"

    __table_args__ = (
        Index("ix_tasks_project_status", "project_id", "status"),
        Index("ix_tasks_assignee_id", "assignee_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    title: Mapped[str] = mapped_column(String(255))

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus),
        default=TaskStatus.TODO,
    )

    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority),
        default=TaskPriority.MEDIUM,
    )

    due_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE")
    )

    creator_id: Mapped[int] = mapped_column(
        ForeignKey("users.id")
    )

    assignee_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )

    project: Mapped["Project"] = relationship(
        back_populates="tasks"
    )

    creator: Mapped["User"] = relationship(
        foreign_keys=[creator_id],
        back_populates="created_tasks",
    )

    assignee: Mapped["User"] = relationship(
        foreign_keys=[assignee_id],
        back_populates="assigned_tasks",
    )

    comments: Mapped[list["Comment"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
    )

    tags: Mapped[list["Tag"]] = relationship(
        secondary=task_tags,
        back_populates="tasks",
    )