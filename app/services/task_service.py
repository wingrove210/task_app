from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi import HTTPException
from app.models.tag import Tag
from app.models.task import Task
from app.models.user import User
from app.models.project import Project
from app.schemas.task import TaskCreate, TaskUpdate


def create_task(db: Session, project_id: int, creator_id: int, data: TaskCreate):
    # Validate project exists
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=400, detail=f"Project with id {project_id} not found")
    
    # Validate creator exists
    creator = db.get(User, creator_id)
    if not creator:
        raise HTTPException(status_code=400, detail=f"User with id {creator_id} not found")
    
    # Validate assignee exists if provided
    if data.assignee_id:
        assignee = db.get(User, data.assignee_id)
        if not assignee:
            raise HTTPException(status_code=400, detail=f"User with id {data.assignee_id} not found")
    
    task = Task(
        **data.model_dump(),
        project_id=project_id,
        creator_id=creator_id,
    )

    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_task(db: Session, task_id: int):
    return db.get(Task, task_id)


def get_tasks_by_project(db: Session, project_id: int):
    stmt = select(Task).where(Task.project_id == project_id)
    return db.scalars(stmt).all()


def update_task(db: Session, task: Task, data: TaskUpdate):
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(task, key, value)

    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, task: Task):
    db.delete(task)
    db.commit()
    
def filter_tasks_by_tag(db, project_id: int, tag_name: str):

    return (

        db.query(Task)

        .join(Task.tags)

        .filter(Task.project_id == project_id)

        .filter(Tag.name == tag_name)

        .all()

    )