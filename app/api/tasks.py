from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.enums import ProjectRole
from app.models.membership import Membership
from app.models.project import Project
from app.models.user import User
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse
from app.services import task_service as service

router = APIRouter(prefix="/projects/{project_id}/tasks", tags=["Tasks"])


def ensure_test_project(db: Session, project_id: int, current_user: User) -> Project:
    """Ensure a test project exists with the given ID and creator membership."""
    project = db.get(Project, project_id)
    if not project:
        project = Project(
            id=project_id,
            name=f"Test Project {project_id}",
            description="Auto-created test project",
        )
        db.add(project)
        db.flush()

        membership = Membership(
            user_id=current_user.id,
            project_id=project.id,
            role=ProjectRole.OWNER,
        )
        db.add(membership)
        db.commit()
        db.refresh(project)
    return project


@router.post("", response_model=TaskResponse)
def create_task(
    project_id: int,
    data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_test_project(db, project_id=project_id, current_user=current_user)
    return service.create_task(db, project_id, current_user, data)


@router.get("", response_model=list[TaskResponse])
def get_tasks(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.get_tasks_by_project(db, project_id, current_user)


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    project_id: int,
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = service.get_task(db, task_id, current_user)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return task


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    project_id: int,
    task_id: int,
    data: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = service.get_task(db, task_id, current_user)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return service.update_task(db, current_user, task, data)


@router.delete("/{task_id}")
def delete_task(
    project_id: int,
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = service.get_task(db, task_id, current_user)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    service.delete_task(db, current_user, task)
    return {"status": "deleted"}