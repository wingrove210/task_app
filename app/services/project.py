from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.enums import ProjectRole
from app.models.membership import Membership
from app.models.project import Project
from app.models.user import User, UserRole
from app.schemas.project import ProjectCreate, ProjectUpdate


def create_project(db: Session, current_user: User, data: ProjectCreate):
    project = Project(**data.model_dump())
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


def get_projects(db: Session, current_user: User):
    if current_user.role == UserRole.admin:
        return db.query(Project).all()

    return (
        db.query(Project)
        .join(Project.memberships)
        .filter(Membership.user_id == current_user.id)
        .all()
    )


def get_project(db: Session, project_id: int, current_user: User):
    project = db.get(Project, project_id)
    if not project:
        return None

    if current_user.role == UserRole.admin:
        return project

    membership = (
        db.query(Membership)
        .filter(Membership.project_id == project.id, Membership.user_id == current_user.id)
        .first()
    )
    if membership:
        return project

    return None


def can_manage_project(db: Session, project: Project, current_user: User) -> bool:
    if current_user.role == UserRole.admin:
        return True

    membership = (
        db.query(Membership)
        .filter(Membership.project_id == project.id, Membership.user_id == current_user.id)
        .first()
    )
    return bool(membership and membership.role == ProjectRole.OWNER)


def update_project(db: Session, current_user: User, project: Project, data: ProjectUpdate):
    if not can_manage_project(db, project, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(project, key, value)

    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, current_user: User, project: Project):
    if not can_manage_project(db, project, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    db.delete(project)
    db.commit()