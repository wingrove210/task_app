from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.events.domain_events import TaskAssignedEvent, TaskCreatedEvent
from app.events.event_bus import get_event_bus
from app.integrations.redis_client import RedisClient
from app.models.membership import Membership
from app.models.project import Project
from app.models.tag import Tag
from app.models.task import Task
from app.models.user import User, UserRole
from app.schemas.task import TaskCreate, TaskUpdate

redis_client = RedisClient()


def _can_access_project(db: Session, project_id: int, current_user: User) -> bool:
    if current_user.role == UserRole.admin:
        return True

    membership = (
        db.query(Membership)
        .filter(Membership.project_id == project_id, Membership.user_id == current_user.id)
        .first()
    )
    return bool(membership)


def create_task(db: Session, project_id: int, current_user: User, data: TaskCreate):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=400, detail=f"Project with id {project_id} not found")

    if not _can_access_project(db, project_id, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    creator = db.get(User, current_user.id)
    if not creator:
        raise HTTPException(status_code=400, detail=f"User with id {current_user.id} not found")

    if data.assignee_id:
        assignee = db.get(User, data.assignee_id)
        if not assignee:
            raise HTTPException(status_code=400, detail=f"User with id {data.assignee_id} not found")

    task = Task(
        **data.model_dump(),
        project_id=project_id,
        creator_id=current_user.id,
    )

    db.add(task)
    db.commit()
    db.refresh(task)
    get_event_bus().publish(TaskCreatedEvent(task_id=task.id, project_id=task.project_id, creator_id=task.creator_id, title=task.title))
    if task.assignee_id:
        get_event_bus().publish(TaskAssignedEvent(task_id=task.id, assignee_id=task.assignee_id, project_id=task.project_id))
    redis_client.delete(f"tasks:project:{project_id}")
    return task


def get_task(db: Session, task_id: int, current_user: User):
    task = db.get(Task, task_id)
    if not task:
        return None

    if not _can_access_project(db, task.project_id, current_user):
        return None

    return task


def get_tasks_by_project(db: Session, project_id: int, current_user: User):
    if not _can_access_project(db, project_id, current_user):
        return []

    cached = redis_client.get_json(f"tasks:project:{project_id}")
    if cached is not None:
        return [db.get(Task, task_id) for task_id in cached if db.get(Task, task_id)]

    stmt = select(Task).where(Task.project_id == project_id)
    tasks = db.scalars(stmt).all()
    redis_client.set_json(f"tasks:project:{project_id}", [task.id for task in tasks], ttl_seconds=60)
    return tasks


def update_task(db: Session, current_user: User, task: Task, data: TaskUpdate):
    if not _can_access_project(db, task.project_id, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(task, key, value)

    db.commit()
    db.refresh(task)
    redis_client.delete(f"tasks:project:{task.project_id}")
    return task


def delete_task(db: Session, current_user: User, task: Task):
    if not _can_access_project(db, task.project_id, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    db.delete(task)
    db.commit()
    redis_client.delete(f"tasks:project:{task.project_id}")


def filter_tasks_by_tag(db, project_id: int, tag_name: str):
    return (
        db.query(Task)
        .join(Task.tags)
        .filter(Task.project_id == project_id)
        .filter(Tag.name == tag_name)
        .all()
    )