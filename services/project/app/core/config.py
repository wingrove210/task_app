import os


class Settings:
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@db:5432/task_manager_project",
    )
    IDENTITY_SERVICE_URL = os.getenv("IDENTITY_SERVICE_URL", "http://identity:8000")
    REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
    RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
