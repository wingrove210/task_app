from sqlalchemy.orm import Session

from app.models.tag import Tag
from app.models.task import Task


def create_tag(db: Session, name: str):
    tag = Tag(name=name)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


def get_tags(db: Session):
    return db.query(Tag).all()


def delete_tag(db: Session, tag: Tag):
    db.delete(tag)
    db.commit()


def get_tag(db: Session, tag_id: int):
    return db.get(Tag, tag_id)


# --- связь Task <-> Tag ---

def add_tag_to_task(db: Session, task: Task, tag: Tag):
    task.tags.append(tag)
    db.commit()
    return task


def remove_tag_from_task(db: Session, task: Task, tag: Tag):
    task.tags.remove(tag)
    db.commit()
    return task