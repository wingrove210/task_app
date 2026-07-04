from datetime import datetime

from sqlalchemy import Column, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase

from common.database import build_session_factory, create_sqlalchemy_engine, initialize_database
from .config import Settings


class Base(DeclarativeBase):
    pass


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="todo", nullable=False)
    priority = Column(String(50), default="medium", nullable=False)
    project_id = Column(Integer, nullable=False, index=True)
    creator_id = Column(Integer, nullable=False, index=True)
    assignee_id = Column(Integer, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_tasks_project_status_created_at", "project_id", "status", "created_at"),
        Index("ix_tasks_project_assignee", "project_id", "assignee_id"),
    )


engine = create_sqlalchemy_engine(Settings.DATABASE_URL)
SessionLocal = build_session_factory(engine)


def initialize() -> None:
    initialize_database(engine, Base)
