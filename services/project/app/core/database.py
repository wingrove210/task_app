from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, relationship, selectinload

from common.database import build_session_factory, create_sqlalchemy_engine, initialize_database
from .config import Settings


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, nullable=False, index=True)

    members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    invitations = relationship("ProjectInvitation", back_populates="project", cascade="all, delete-orphan")


class ProjectMember(Base):
    __tablename__ = "project_members"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    role = Column(String(50), nullable=False, default="editor")

    project = relationship("Project", back_populates="members")

    __table_args__ = (
        Index("ix_project_members_project_user", "project_id", "user_id"),
        Index("ix_project_members_project_email", "project_id", "email"),
    )


class ProjectInvitation(Base):
    __tablename__ = "project_invitations"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    role = Column(String(50), nullable=False, default="editor")
    token = Column(String(255), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    accepted = Column(Integer, nullable=False, default=0)

    project = relationship("Project", back_populates="invitations")

    __table_args__ = (
        Index("ix_project_invitations_project_email", "project_id", "email"),
    )


engine = create_sqlalchemy_engine(Settings.DATABASE_URL)
SessionLocal = build_session_factory(engine)


def initialize() -> None:
    initialize_database(engine, Base)


def get_project_with_members(session, project_id: int) -> Optional[Project]:
    return (
        session.query(Project)
        .options(selectinload(Project.members))
        .filter(Project.id == project_id)
        .first()
    )
