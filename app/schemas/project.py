from typing import Optional

from pydantic import AliasChoices, BaseModel, Field


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

    class Config:
        from_attributes = True