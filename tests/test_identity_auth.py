from pathlib import Path
import sys

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services"))

import identity.app.main as identity_main
from identity.app.core import database as identity_db
from identity.app.core.database import User


def make_client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    identity_db.Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    identity_main.SessionLocal = SessionLocal
    identity_main.initialize = lambda: None

    client = TestClient(identity_main.app)
    return client, SessionLocal


def test_register_accepts_email_and_username():
    client, SessionLocal = make_client()

    response = client.post(
        "/auth/register",
        data={
            "email": "Alice@Example.com",
            "username": "Alice",
            "password": "secret123",
            "full_name": "Alice Smith",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert "access_token" in payload

    with SessionLocal() as db:
        saved = db.query(User).filter(User.email == "alice@example.com").one()
        assert saved.username == "alice"
        assert saved.full_name == "Alice Smith"


def test_login_returns_clear_message_if_user_not_found():
    client, _ = make_client()

    response = client.post(
        "/auth/login",
        data={"username": "missing", "password": "secret123"},
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_login_returns_username_in_payload():
    client, SessionLocal = make_client()

    with SessionLocal() as db:
        user = User(
            email="bob@example.com",
            username="bob",
            full_name="Bob Smith",
            hashed_password=identity_main.pwd_context.hash("secret123"),
            role="member",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    response = client.post(
        "/auth/login",
        data={"username": "bob", "password": "secret123"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["username"] == "bob"


def test_admin_can_delete_user():
    client, SessionLocal = make_client()

    with SessionLocal() as db:
        admin = User(
            email="admin@example.com",
            username="admin",
            full_name="Admin",
            hashed_password="unused",
            role="admin",
        )
        user = User(
            email="target@example.com",
            username="target",
            full_name="Target",
            hashed_password="unused",
            role="member",
        )
        db.add_all([admin, user])
        db.commit()
        db.refresh(admin)
        db.refresh(user)

    token = identity_main.create_access_token(admin)
    response = client.delete(
        f"/admin/users/{user.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    with SessionLocal() as db:
        assert db.query(User).filter(User.id == user.id).first() is None
