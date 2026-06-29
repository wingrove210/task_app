from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from app.services import project as service

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("", response_model=ProjectResponse)
def create(
    data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.create_project(db, current_user, data)


@router.get("", response_model=list[ProjectResponse])
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.get_projects(db, current_user)


@router.get("/{project_id}", response_model=ProjectResponse)
def get(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = service.get_project(db, project_id, current_user)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
def update(
    project_id: int,
    data: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = service.get_project(db, project_id, current_user)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return service.update_project(db, current_user, project, data)


@router.delete("/{project_id}")
def delete(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = service.get_project(db, project_id, current_user)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    service.delete_project(db, current_user, project)
    return {"status": "deleted"}