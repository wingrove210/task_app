import json
from typing import Optional

import httpx
from fastapi import Depends, FastAPI, Form, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis import Redis
from sqlalchemy.orm import Session

from common.auth import get_current_user
from common.events import publish_event
from common.exceptions import NotFoundError, ValidationError
from common.models import TaskPriority, TaskResponse, TaskStatus
from app.core.config import Settings
from app.core.database import SessionLocal, Task, initialize
from common.observability import setup_observability

redis_client = Redis.from_url(Settings.REDIS_URL, decode_responses=True)

app = FastAPI(
    title="Task Service",
    docs_url="/tasks/docs",
    redoc_url=None,
    openapi_url="/tasks/openapi.json",
)
setup_observability(app, "task")


def get_db():
    """Database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


security_scheme = HTTPBearer()


def get_current_user_dep(
    credentials: HTTPAuthorizationCredentials = Security(security_scheme),
):
    """Get current user from token."""
    return get_current_user(
        Settings.IDENTITY_SERVICE_URL,
        f"Bearer {credentials.credentials}",
    )


def ensure_project_exists(project_id: int) -> dict:
    """
    Verify project exists with project service.
    
    Args:
        project_id: Project ID to validate
        
    Returns:
        Project data
        
    Raises:
        NotFoundError: If project doesn't exist
    """
    try:
        response = httpx.get(
            f"{Settings.PROJECT_SERVICE_URL}/internal/projects/{project_id}",
            timeout=3.0,
        )
        
        if response.status_code != 200:
            raise NotFoundError("Project")
        
        return response.json()
    except httpx.RequestError as exc:
        raise NotFoundError("Project") from exc


@app.on_event("startup")
def startup_event() -> None:
    """Initialize database on startup."""
    initialize()


@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "task"}


@app.post("/projects/{project_id}/tasks", response_model=TaskResponse, status_code=201)
def create_task(
    project_id: int,
    title: str = Form(...),
    description: Optional[str] = Form(None),
    status: TaskStatus = Form(TaskStatus.TODO),
    priority: TaskPriority = Form(TaskPriority.MEDIUM),
    assignee_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_dep),
) -> dict:
    """
    Create a new task in a project.
    
    Args:
        project_id: Project ID
        title: Task title from form input
        description: Optional task description from form input
        status: Task status from form input
        priority: Task priority from form input
        assignee_id: Optional assignee ID from form input
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Created task data
    """
    # Verify project exists
    ensure_project_exists(project_id)

    if not title or not title.strip():
        raise ValidationError("Task title cannot be empty")

    task = Task(
        title=title.strip(),
        description=description.strip() if description else None,
        status=status.value if status else "todo",
        priority=priority.value if priority else "medium",
        project_id=project_id,
        creator_id=current_user["user_id"],
        assignee_id=assignee_id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # Invalidate cache
    redis_client.delete(f"tasks:project:{project_id}")

    # Publish domain event
    publish_event(
        Settings.RABBITMQ_HOST,
        "task.created",
        {
            "task_id": task.id,
            "project_id": project_id,
            "creator_id": task.creator_id,
            "title": task.title,
            "priority": task.priority,
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
        "priority": task.priority,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
    }


@app.get("/projects/{project_id}/tasks", response_model=list[TaskResponse])
def list_tasks(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_dep),
) -> list[dict]:
    """
    Get all tasks in a project.
    
    Args:
        project_id: Project ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        List of tasks
    """
    # Verify project exists
    ensure_project_exists(project_id)

    # Try to get from cache
    cached = redis_client.get(f"tasks:project:{project_id}")
    if cached:
        return json.loads(cached)

    # Query from database
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
            "priority": task.priority,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
        }
        for task in tasks
    ]

    # Cache results
    redis_client.set(f"tasks:project:{project_id}", json.dumps(payload), ex=60)
    return payload
