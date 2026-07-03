from pydantic import BaseModel

class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    assignee_id: int | None = None

class TaskOut(BaseModel):
    id: int
    title: str
    description: str | None = None
    project_id: int
    creator_id: int
    assignee_id: int | None = None
    status: str
