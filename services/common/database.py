import time
from typing import Type

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


def create_sqlalchemy_engine(database_url: str) -> Engine:
    return create_engine(database_url, pool_pre_ping=True)


def initialize_database(engine: Engine, base_model: Type[DeclarativeBase], retries: int = 30, delay_seconds: int = 2) -> None:
    for attempt in range(retries):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            base_model.metadata.create_all(bind=engine)
            return
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(delay_seconds)


def build_session_factory(engine: Engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)
