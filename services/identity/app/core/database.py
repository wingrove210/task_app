from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import DeclarativeBase

from services.common.database import build_session_factory, create_sqlalchemy_engine, initialize_database

from .config import Settings


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="member", nullable=False)


engine = create_sqlalchemy_engine(Settings.DATABASE_URL)
SessionLocal = build_session_factory(engine)


def initialize() -> None:
    initialize_database(engine, Base)
