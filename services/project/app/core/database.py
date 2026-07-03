from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase

from services.common.database import build_session_factory, create_sqlalchemy_engine, initialize_database

from .config import Settings


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, nullable=False)


engine = create_sqlalchemy_engine(Settings.DATABASE_URL)
SessionLocal = build_session_factory(engine)


def initialize() -> None:
    initialize_database(engine, Base)
