import json
from typing import Optional

from fastapi import Depends, FastAPI, Form, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis import Redis
from sqlalchemy.orm import Session

from common.auth import get_current_user
from common.events import publish_event
from common.exceptions import NotFoundError, ValidationError
from common.models import ProjectCreateRequest, ProjectResponse, ProjectUpdateRequest
from app.core.config import Settings
from app.core.database import Project, SessionLocal, initialize

redis_client = Redis.from_url(Settings.REDIS_URL, decode_responses=True)

app = FastAPI(title="Project Service")


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


@app.on_event("startup")
def startup_event() -> None:
    """Initialize database on startup."""
    initialize()


@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "project"}


@app.post("/projects", response_model=ProjectResponse, status_code=201)
def create_project(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_dep),
) -> dict:
    """
    Create a new project.
    
    Args:
        name: Project name from form input
        description: Optional project description from form input
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Created project data
    """
    if not name or not name.strip():
        raise ValidationError("Project name cannot be empty")

    project = Project(
        name=name.strip(),
        description=description.strip() if description else None,
        owner_id=current_user["user_id"],
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    # Invalidate cache
    redis_client.delete("projects:all")

    # Publish domain event
    publish_event(
        Settings.RABBITMQ_HOST,
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


@app.get("/projects", response_model=list[ProjectResponse])
def list_projects(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_dep),
) -> list[dict]:
    """
    List all projects for current user.
    
    Args:
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        List of projects
    """
    # Try to get from cache
    cached = redis_client.get("projects:all")
    if cached:
        return json.loads(cached)

    # Query from database
    projects = db.query(Project).filter(Project.owner_id == current_user["user_id"]).all()
    payload = [
        {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "owner_id": project.owner_id,
        }
        for project in projects
    ]

    # Cache results
    redis_client.set("projects:all", json.dumps(payload), ex=60)
    return payload


@app.get("/internal/projects/{project_id}", response_model=ProjectResponse)
def internal_get_project(project_id: int, db: Session = Depends(get_db)) -> dict:
    """
    Internal endpoint to validate project exists (for other services).
    
    Args:
        project_id: Project ID
        db: Database session
        
    Returns:
        Project data
        
    Raises:
        NotFoundError: If project doesn't exist
    """
    project = db.get(Project, project_id)
    if not project:
        raise NotFoundError("Project")
    
    return {
        "id": project.id,
        "owner_id": project.owner_id,
        "name": project.name,
        "description": project.description,
    }
