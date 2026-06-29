from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.models.task import Task
from app.schemas.comment import CommentCreate, CommentResponse
from app.services import comment_service as service

router = APIRouter(
    prefix="/tasks/{task_id}/comments",
    tags=["Comments"]
)


def ensure_test_user(db: Session, user_id: int = 1) -> User:
    """Ensure a test user exists with the given ID."""
    user = db.get(User, user_id)
    if not user:
        user = User(
            id=user_id,
            email=f"user{user_id}@test.local",
            full_name=f"Test User {user_id}",
            hashed_password="test",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


@router.post("", response_model=CommentResponse)
def create_comment(
    task_id: int,
    data: CommentCreate,
    db: Session = Depends(get_db),
):
    # Ensure test user exists
    ensure_test_user(db, user_id=1)
    # временно author_id = 1 (потом заменим на JWT user)
    return service.create_comment(db, task_id, author_id=1, data=data)

@router.get("", response_model=list[CommentResponse])
def get_comments(task_id: int, db: Session = Depends(get_db)):
    return service.get_comments_by_task(db, task_id)

@router.delete("/{comment_id}")
def delete_comment(comment_id: int, db: Session = Depends(get_db)):
    comment = service.get_comment(db, comment_id)

    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    service.delete_comment(db, comment)
    return {"status": "deleted"}