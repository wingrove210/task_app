import os


class Settings:
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@db:5432/task_manager_identity",
    )
    JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
