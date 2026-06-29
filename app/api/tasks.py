from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.models.project import Project
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse
from app.services import task_service as service

router = APIRouter(prefix="/projects/{project_id}/tasks", tags=["Tasks"])


def ensure_test_user(db: Session, user_id: int = 1) -> User:
    """Ensure a test user exists with the given ID."""
    user = db.get(User, user_id)
    if not user:
        user = User(
            id=user_id,
            email=f"user{user_id}@test.local",
            full_name=f"Test User {user_id}",
            hashed_password="test",  # In production, use proper hashing
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def ensure_test_project(db: Session, project_id: int) -> Project:
    """Ensure a test project exists with the given ID."""
    project = db.get(Project, project_id)
    if not project:
        project = Project(
            id=project_id,
            name=f"Test Project {project_id}",
            description="Auto-created test project",
        )
        db.add(project)
        db.commit()
        db.refresh(project)
    return project


@router.post("", response_model=TaskResponse)
def create_task(
    project_id: int,
    data: TaskCreate,
    db: Session = Depends(get_db),
):
    # Ensure test user and project exist
    ensure_test_user(db, user_id=1)
    ensure_test_project(db, project_id=project_id)
    # временно creator_id = 1 (потом заменим на JWT user)
    return service.create_task(db, project_id, creator_id=1, data=data)

@router.get("", response_model=list[TaskResponse])
def get_tasks(
    project_id: int,
    db: Session = Depends(get_db),
):
    return service.get_tasks_by_project(db, project_id)

@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = service.get_task(db, task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return task

@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    data: TaskUpdate,
    db: Session = Depends(get_db),
):
    task = service.get_task(db, task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return service.update_task(db, task, data)

@router.delete("/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = service.get_task(db, task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    service.delete_task(db, task)
    return {"status": "deleted"}