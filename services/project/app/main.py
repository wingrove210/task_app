import json
from typing import Optional

import httpx
import pika
from fastapi import Depends, FastAPI, Header, HTTPException
from redis import Redis
from sqlalchemy.orm import Session

from .core.config import Settings
from .core.database import Project, SessionLocal, initialize

redis_client = Redis.from_url(Settings.REDIS_URL, decode_responses=True)

app = FastAPI(title="Project Service")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(authorization: Optional[str] = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="token required")

    token = authorization.split(" ", 1)[1]
    response = httpx.post(
        f"{Settings.IDENTITY_SERVICE_URL}/internal/validate",
        json={"token": token},
        timeout=3.0,
    )
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="invalid token")

    return response.json()


def publish_event(routing_key: str, payload: dict):
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=Settings.RABBITMQ_HOST, heartbeat=30)
        )
        channel = connection.channel()
        channel.exchange_declare(exchange="domain-events", exchange_type="topic", durable=True)
        channel.basic_publish(
            exchange="domain-events",
            routing_key=routing_key,
            body=json.dumps(payload).encode("utf-8"),
            properties=pika.BasicProperties(delivery_mode=2),
        )
        connection.close()
    except Exception:
        return False
    return True


@app.on_event("startup")
def startup_event() -> None:
    initialize()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "project"}


@app.post("/projects", response_model=dict)
def create_project(payload: dict, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    name = payload.get("name")
    description = payload.get("description")
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    project = Project(name=name, description=description, owner_id=current_user["user_id"])
    db.add(project)
    db.commit()
    db.refresh(project)

    redis_client.delete("projects:all")
    publish_event(
        "project.created",
        {
            "project_id": project.id,
            "owner_id": project.owner_id,
            "name": project.name,
        },
    )

    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "owner_id": project.owner_id,
    }


@app.get("/projects", response_model=list[dict])
def list_projects(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    cached = redis_client.get("projects:all")
    if cached:
        return json.loads(cached)

    projects = db.query(Project).filter(Project.owner_id == current_user["user_id"]).all()
    payload = [
        {"id": project.id, "name": project.name, "description": project.description, "owner_id": project.owner_id}
        for project in projects
    ]
    redis_client.set("projects:all", json.dumps(payload), ex=60)
    return payload


@app.get("/internal/projects/{project_id}", response_model=dict)
def internal_project(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    return {"id": project.id, "owner_id": project.owner_id, "name": project.name}
