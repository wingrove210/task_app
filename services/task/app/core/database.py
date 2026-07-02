from sqlalchemy import Column, Integer, String, Text
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
    project_id = Column(Integer, nullable=False)
    creator_id = Column(Integer, nullable=False)
    assignee_id = Column(Integer, nullable=True)
    status = Column(String(50), default="todo")


engine = create_sqlalchemy_engine(Settings.DATABASE_URL)
SessionLocal = build_session_factory(engine)


def initialize() -> None:
    initialize_database(engine, Base)
