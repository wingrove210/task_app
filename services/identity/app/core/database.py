from sqlalchemy import Column, Integer, String, text
from sqlalchemy.engine import Engine
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import DeclarativeBase

from common.database import build_session_factory, create_sqlalchemy_engine, initialize_database
from .config import Settings


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="member", nullable=False)


engine = create_sqlalchemy_engine(Settings.DATABASE_URL)
SessionLocal = build_session_factory(engine)


def initialize() -> None:
    initialize_database(engine, Base)
    ensure_username_column(engine)


def ensure_username_column(engine: Engine) -> None:
    try:
        inspector = inspect(engine)
        columns = {column["name"] for column in inspector.get_columns("users")}
        if "username" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE users ADD COLUMN username VARCHAR(255)"))
                connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username)"))
    except Exception as exc:  # pragma: no cover - defensive for existing databases
        print(f"Unable to ensure username column exists: {exc}")
