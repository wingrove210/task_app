from datetime import datetime
from typing import Optional

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


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"

    __table_args__ = (
        Index("ix_tasks_project_status", "project_id", "status"),
        Index("ix_tasks_assignee_id", "assignee_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)

    description: Mapped[Optional[str]] = mapped_column(Text)

    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, native_enum=False, name="task_status"),
        default=TaskStatus.TODO,
        nullable=False,
    )

    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority, native_enum=False, name="task_priority"),
        default=TaskPriority.MEDIUM,
        nullable=False,
    )

    due_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    creator_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )

    assignee_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )

    project = relationship("Project", back_populates="tasks")

    creator = relationship("User", foreign_keys=[creator_id])

    assignee = relationship("User", foreign_keys=[assignee_id])

    comments = relationship(
        "Comment",
        back_populates="task",
        cascade="all, delete-orphan",
    )

    tags = relationship(
        "Tag",
        secondary=task_tags,
        back_populates="tasks",
    )