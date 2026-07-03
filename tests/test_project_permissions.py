from pathlib import Path
import sys
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "project"))

import project.app.main as project_main
from project.app.core import database as project_db
from project.app.core.database import Project, ProjectMember


def make_client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    project_db.Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    project_main.SessionLocal = SessionLocal
    project_main.initialize = lambda: None
    project_main.redis_client = SimpleNamespace(
        get=lambda *args, **kwargs: None,
        set=lambda *args, **kwargs: None,
        delete=lambda *args, **kwargs: None,
    )

    client = TestClient(project_main.app)
    return client, SessionLocal


def test_list_projects_includes_collaborator_projects():
    client, SessionLocal = make_client()

    with SessionLocal() as db:
        project = Project(name="Shared", description="Shared description", owner_id=99)
        db.add(project)
        db.commit()
        db.refresh(project)
        db.add(
            ProjectMember(
                project_id=project.id,
                user_id=7,
                email="collaborator@example.com",
                role="editor",
            )
        )
        db.commit()

    project_main.app.dependency_overrides[project_main.get_current_user_dep] = lambda: {
        "user_id": 7,
        "email": "collaborator@example.com",
        "role": "member",
    }
    try:
        response = client.get("/projects")
    finally:
        project_main.app.dependency_overrides.pop(project_main.get_current_user_dep, None)

    assert response.status_code == 200
    payload = response.json()
    assert any(item["id"] == 1 for item in payload)


def test_viewer_cannot_edit_project():
    client, SessionLocal = make_client()

    with SessionLocal() as db:
        project = Project(name="Protected", description="Discussion", owner_id=99)
        db.add(project)
        db.commit()
        db.refresh(project)
        db.add(
            ProjectMember(
                project_id=project.id,
                user_id=7,
                email="viewer@example.com",
                role="viewer",
            )
        )
        db.commit()

    project_main.app.dependency_overrides[project_main.get_current_user_dep] = lambda: {
        "user_id": 7,
        "email": "viewer@example.com",
        "role": "member",
    }
    try:
        response = client.put(
            f"/projects/{project.id}",
            json={"name": "Updated", "description": "New description"},
        )
    finally:
        project_main.app.dependency_overrides.pop(project_main.get_current_user_dep, None)

    assert response.status_code == 403
    assert "cannot edit" in response.json()["detail"].lower()
