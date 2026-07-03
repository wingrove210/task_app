from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services"))

from project.app.core.database import Base, Project, ProjectInvitation, ProjectMember


def test_project_invitation_and_member_persist():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    with SessionLocal() as session:
        project = Project(name="Demo", description="Test", owner_id=1)
        session.add(project)
        session.commit()
        session.refresh(project)

        invitation = ProjectInvitation(
            project_id=project.id,
            email="member@example.com",
            role="editor",
            token="token-123",
            created_at=project.id and __import__("datetime").datetime.utcnow(),
            expires_at=__import__("datetime").datetime.utcnow(),
            accepted=0,
        )
        session.add(invitation)

        member = ProjectMember(
            project_id=project.id,
            user_id=42,
            email="member@example.com",
            role="editor",
        )
        session.add(member)
        session.commit()

        saved_invitation = session.query(ProjectInvitation).filter_by(token="token-123").one()
        saved_member = session.query(ProjectMember).filter_by(project_id=project.id).one()

        assert saved_invitation.email == "member@example.com"
        assert saved_member.role == "editor"
