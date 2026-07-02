from dataclasses import asdict, dataclass
from typing import Any


class DomainEvent:
    event_name: str = ""

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProjectCreatedEvent(DomainEvent):
    event_name: str = "project.created"
    project_id: int = 0
    owner_id: int = 0
    name: str = ""


@dataclass
class TaskCreatedEvent(DomainEvent):
    event_name: str = "task.created"
    task_id: int = 0
    project_id: int = 0
    creator_id: int = 0
    title: str = ""


@dataclass
class TaskAssignedEvent(DomainEvent):
    event_name: str = "task.assigned"
    task_id: int = 0
    assignee_id: int = 0
    project_id: int = 0
