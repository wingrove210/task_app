import json
from typing import Optional

import httpx
import pika
from fastapi import Depends, FastAPI, Header, HTTPException
from redis import Redis
from sqlalchemy.orm import Session

from .core.config import Settings
from .core.database import SessionLocal, Task, initialize

redis_client = Redis.from_url(Settings.REDIS_URL, decode_responses=True)

app = FastAPI(title="Task Service")


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


def ensure_project_exists(project_id: int):
    response = httpx.get(f"{Settings.PROJECT_SERVICE_URL}/internal/projects/{project_id}", timeout=3.0)
    if response.status_code != 200:
        raise HTTPException(status_code=404, detail="project not found")
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
    return {"status": "ok", "service": "task"}


@app.post("/projects/{project_id}/tasks", response_model=dict)
def create_task(project_id: int, payload: dict, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    ensure_project_exists(project_id)
    title = payload.get("title")
    if not title:
        raise HTTPException(status_code=400, detail="title is required")

    task = Task(
        title=title,
        description=payload.get("description"),
        project_id=project_id,
        creator_id=current_user["user_id"],
        assignee_id=payload.get("assignee_id"),
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    redis_client.delete(f"tasks:project:{project_id}")
    publish_event(
        "task.created",
        {
            "task_id": task.id,
            "project_id": project_id,
            "creator_id": task.creator_id,
            "title": task.title,
        },
    )
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "project_id": task.project_id,
        "creator_id": task.creator_id,
        "assignee_id": task.assignee_id,
        "status": task.status,
    }


@app.get("/projects/{project_id}/tasks", response_model=list[dict])
def list_tasks(project_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    ensure_project_exists(project_id)
    cached = redis_client.get(f"tasks:project:{project_id}")
    if cached:
        return json.loads(cached)

    tasks = db.query(Task).filter(Task.project_id == project_id).all()
    payload = [
        {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "project_id": task.project_id,
            "creator_id": task.creator_id,
            "assignee_id": task.assignee_id,
            "status": task.status,
        }
        for task in tasks
    ]
    redis_client.set(f"tasks:project:{project_id}", json.dumps(payload), ex=60)
    return payload
