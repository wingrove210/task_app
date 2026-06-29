import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.membership import Membership
from app.models.project import Project
from app.models.tag import Tag
from app.models.task import Task
from app.models.user import User, UserRole
from app.schemas.project import ProjectResponse
from app.schemas.task import TaskResponse
from app.services import project as project_service
from app.schemas.project import ProjectCreate


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_create_project_links_owner_membership(db_session):
    user = User(
        email="owner@example.com",
        full_name="Owner",
        hashed_password="secret",
        role=UserRole.member,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    project = project_service.create_project(
        db_session,
        user,
        ProjectCreate(name="My Project", description="Demo"),
    )

    memberships = (
        db_session.query(Membership)
        .filter(Membership.project_id == project.id)
        .all()
    )

    assert len(memberships) == 1
    assert memberships[0].user_id == user.id
    assert memberships[0].role.value == "owner"


def test_project_and_task_responses_include_nested_tasks_and_tags(db_session):
    user = User(
        email="member@example.com",
        full_name="Member",
        hashed_password="secret",
        role=UserRole.member,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    project = project_service.create_project(
        db_session,
        user,
        ProjectCreate(name="Project", description="With tasks"),
    )

    tag = Tag(name="urgent")
    task = Task(
        title="Write docs",
        description="Document API",
        project_id=project.id,
        creator_id=user.id,
        assignee_id=user.id,
    )
    task.tags.append(tag)
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    project_payload = ProjectResponse.model_validate(project)
    task_payload = TaskResponse.model_validate(task)

    assert project_payload.tasks[0].title == "Write docs"
    assert task_payload.tags[0].name == "urgent"
