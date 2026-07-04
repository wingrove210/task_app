import os


class Settings:
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@db:5432/task_manager_identity",
    )
    JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    SMTP_HOST = os.getenv("SMTP_HOST", "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "0") or 0)
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "false").lower() == "true"
    SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "no-reply@taskmanager.local")
    SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "Task Manager")
    APP_NAME = os.getenv("APP_NAME", "Task Manager")
    REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
