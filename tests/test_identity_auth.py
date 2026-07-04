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


class DummyRedis:
    def __init__(self):
        self._store = {}
        self._expirations = {}

    def incr(self, key):
        self._store[key] = self._store.get(key, 0) + 1
        return self._store[key]

    def expire(self, key, seconds):
        self._expirations[key] = seconds
        return True

    def ttl(self, key):
        return self._expirations.get(key, -1)


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
    identity_main.redis_client = DummyRedis()

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
    assert "refresh_token" in payload

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
    assert "refresh_token" in payload


def test_refresh_token_returns_new_access_token():
    client, SessionLocal = make_client()

    with SessionLocal() as db:
        user = User(
            email="carol@example.com",
            username="carol",
            full_name="Carol Smith",
            hashed_password=identity_main.pwd_context.hash("secret123"),
            role="member",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    login_response = client.post(
        "/auth/login",
        data={"username": "carol", "password": "secret123"},
    )
    refresh_token = login_response.json()["refresh_token"]

    refresh_response = client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert refresh_response.status_code == 200
    payload = refresh_response.json()
    assert "access_token" in payload
    assert "refresh_token" in payload


def test_login_is_rate_limited_after_five_requests():
    client, _ = make_client()

    for _ in range(5):
        response = client.post(
            "/auth/login",
            data={"username": "missing", "password": "secret123"},
        )
        assert response.status_code == 404

    response = client.post(
        "/auth/login",
        data={"username": "missing", "password": "secret123"},
    )

    assert response.status_code == 429
    assert "too many requests" in response.json()["detail"].lower()


def test_register_is_rate_limited_after_five_requests():
    client, _ = make_client()

    for index in range(5):
        response = client.post(
            "/auth/register",
            data={
                "email": f"user{index}@example.com",
                "username": f"user{index}",
                "password": "secret123",
            },
        )
        assert response.status_code == 200

    response = client.post(
        "/auth/register",
        data={
            "email": "user5@example.com",
            "username": "user5",
            "password": "secret123",
        },
    )

    assert response.status_code == 429
    assert "too many requests" in response.json()["detail"].lower()


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
