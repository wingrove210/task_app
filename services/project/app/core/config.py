import os


class Settings:
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@db:5432/task_manager_project",
    )
    IDENTITY_SERVICE_URL = os.getenv("IDENTITY_SERVICE_URL", "http://identity:8000")
    REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
    RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
    SMTP_HOST = os.getenv("SMTP_HOST", "localhost")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "25"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "false").lower() == "true"
    SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "no-reply@taskmanager.local")
    PROJECT_INVITE_BASE_URL = os.getenv("PROJECT_INVITE_BASE_URL", "http://localhost:8002/projects/invitations/accept")
