from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.tag import TagCreate, TagResponse
from app.services import tag_service as service
from app.services.task_service import get_task

router = APIRouter(prefix="/tags", tags=["Tags"])

@router.post("", response_model=TagResponse)
def create_tag(data: TagCreate, db: Session = Depends(get_db)):
    return service.create_tag(db, data.name)

@router.get("", response_model=list[TagResponse])
def list_tags(db: Session = Depends(get_db)):
    return service.get_tags(db)

@router.delete("/{tag_id}")
def delete_tag(tag_id: int, db: Session = Depends(get_db)):
    tag = service.get_tag(db, tag_id)

    if not tag:
        raise HTTPException(404, "Tag not found")

    service.delete_tag(db, tag)
    return {"status": "deleted"}

@router.post("/tasks/{task_id}/tags/{tag_id}")
def add_tag(task_id: int, tag_id: int, db: Session = Depends(get_db)):
    task = get_task(db, task_id)
    tag = service.get_tag(db, tag_id)

    if not task or not tag:
        raise HTTPException(404, "Task or Tag not found")

    return service.add_tag_to_task(db, task, tag)

@router.delete("/tasks/{task_id}/tags/{tag_id}")
def remove_tag(task_id: int, tag_id: int, db: Session = Depends(get_db)):
    task = get_task(db, task_id)
    tag = service.get_tag(db, tag_id)

    if not task or not tag:
        raise HTTPException(404, "Task or Tag not found")

    return service.remove_tag_from_task(db, task, tag)