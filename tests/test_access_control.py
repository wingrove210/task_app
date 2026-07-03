import os

from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_identity.db")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("IDENTITY_SERVICE_URL", "http://identity")
os.environ.setdefault("PROJECT_SERVICE_URL", "http://project")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("RABBITMQ_HOST", "localhost")

from services.identity.app.main import app as identity_app
from services.project.app.main import app as project_app
from services.task.app.main import app as task_app


def test_identity_service_health():
    with TestClient(identity_app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["service"] == "identity"


def test_project_service_health():
    with TestClient(project_app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["service"] == "project"


def test_task_service_health():
    with TestClient(task_app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["service"] == "task"
