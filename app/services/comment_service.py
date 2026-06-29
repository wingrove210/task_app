from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.comment import Comment
from app.models.task import Task
from app.models.user import User
from app.schemas.comment import CommentCreate


def create_comment(db: Session, task_id: int, author_id: int, data: CommentCreate):
    # Validate task exists
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=400, detail=f"Task with id {task_id} not found")
    
    # Validate author exists
    author = db.get(User, author_id)
    if not author:
        raise HTTPException(status_code=400, detail=f"User with id {author_id} not found")
    
    comment = Comment(
        content=data.content,
        task_id=task_id,
        author_id=author_id,
    )

    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


def get_comments_by_task(db: Session, task_id: int):
    return (
        db.query(Comment)
        .filter(Comment.task_id == task_id)
        .order_by(Comment.created_at.asc())
        .all()
    )


def delete_comment(db: Session, comment: Comment):
    db.delete(comment)
    db.commit()


def get_comment(db: Session, comment_id: int):
    return db.get(Comment, comment_id)