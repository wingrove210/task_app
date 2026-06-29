from typing import Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from app.schemas.task import TaskResponse


class ProjectBase(BaseModel):
    name: str = Field(validation_alias=AliasChoices("name", "title"))
    description: Optional[str] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, validation_alias=AliasChoices("name", "title"))
    description: Optional[str] = None


class ProjectResponse(ProjectBase):
    id: int
    tasks: list[TaskResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)