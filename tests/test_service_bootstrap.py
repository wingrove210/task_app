from sqlalchemy import Column, Integer, text
from sqlalchemy.orm import DeclarativeBase

from services.common.database import create_sqlalchemy_engine, initialize_database


class BaseModel(DeclarativeBase):
    pass


class Sample(BaseModel):
    __tablename__ = "samples"

    id = Column(Integer, primary_key=True)


def test_initialize_database_creates_tables(tmp_path):
    database_path = tmp_path / "bootstrap-test.db"
    engine = create_sqlalchemy_engine(f"sqlite:///{database_path}")

    initialize_database(engine, BaseModel, retries=3, delay_seconds=0)

    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='samples'")
        ).fetchall()

    assert rows == [("samples",)]
