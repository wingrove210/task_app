import json
import smtplib
import uuid
from datetime import datetime, timedelta
from email.message import EmailMessage
from typing import Optional

from fastapi import Depends, FastAPI, Form, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis import Redis
from sqlalchemy import or_
from sqlalchemy.orm import Session

from common.auth import get_current_user
from common.events import publish_event
from common.exceptions import AuthorizationError, ConflictError, NotFoundError, ValidationError
from common.models import (
    ProjectCollaboratorResponse,
    ProjectCollaboratorRole,
    ProjectCollaboratorUpdateRequest,
    ProjectCreateRequest,
    ProjectInviteRequest,
    ProjectResponse,
    ProjectUpdateRequest,
)
from app.core.config import Settings
from app.core.database import Project, ProjectInvitation, ProjectMember, SessionLocal, initialize

redis_client = Redis.from_url(Settings.REDIS_URL, decode_responses=True)

app = FastAPI(title="Project Service")


def get_db():
    """Database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


security_scheme = HTTPBearer()


def get_current_user_dep(
    credentials: HTTPAuthorizationCredentials = Security(security_scheme),
):
    """Get current user from token."""
    return get_current_user(
        Settings.IDENTITY_SERVICE_URL,
        f"Bearer {credentials.credentials}",
    )


def get_project_or_404(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise NotFoundError("Project")
    return project


def ensure_project_access(db: Session, project: Project, current_user_id: int) -> str:
    if project.owner_id == current_user_id:
        return "owner"

    membership = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project.id, ProjectMember.user_id == current_user_id)
        .first()
    )
    if not membership:
        raise AuthorizationError("You do not have access to this project")

    return membership.role


def ensure_project_edit_access(db: Session, project: Project, current_user_id: int) -> str:
    role = ensure_project_access(db, project, current_user_id)
    if role in {"owner", "editor", "admin"}:
        return role

    raise AuthorizationError("You cannot edit this project")


def send_invite_email(to_email: str, project_name: str, invite_token: str, role: str) -> None:
    accept_url = f"{Settings.PROJECT_INVITE_BASE_URL}?token={invite_token}"
    message = EmailMessage()
    message["Subject"] = f"Invitation to collaborate on {project_name}"
    message["From"] = Settings.SMTP_FROM_EMAIL
    message["To"] = to_email
    message.set_content(
        "Hello!\n\n"
        f"You were invited to collaborate on project '{project_name}' with role '{role}'.\n"
        f"Open this link to accept the invitation: {accept_url}\n\n"
        "Regards,\nTask Manager"
    )

    try:
        with smtplib.SMTP(Settings.SMTP_HOST, Settings.SMTP_PORT, timeout=5) as server:
            if Settings.SMTP_USE_TLS:
                server.starttls()
            if Settings.SMTP_USERNAME:
                server.login(Settings.SMTP_USERNAME, Settings.SMTP_PASSWORD)
            server.send_message(message)
    except Exception as exc:  # pragma: no cover - best effort delivery
        print(f"Failed to send invitation email to {to_email}: {exc}")


def send_project_update_email(db: Session, project: Project, actor: dict, changes: list[str]) -> None:
    if actor.get("user_id") == project.owner_id:
        return

    recipients: list[str] = []
    members = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project.id)
        .all()
    )
    for member in members:
        if member.email and member.email != (actor.get("email") or "").strip().lower():
            recipients.append(member.email)

    actor_email = (actor.get("email") or "").strip().lower()
    if actor_email:
        recipients.append(actor_email)

    if not recipients:
        return

    unique_recipients = list(dict.fromkeys(recipients))
    change_summary = "; ".join(changes)
    message = EmailMessage()
    message["Subject"] = f"Project updated: {project.name}"
    message["From"] = Settings.SMTP_FROM_EMAIL
    message["To"] = ", ".join(unique_recipients)
    message.set_content(
        f"Hello!\n\n"
        f"A collaborator updated project '{project.name}'.\n"
        f"Changes: {change_summary}\n\n"
        "Regards,\nTask Manager"
    )

    try:
        with smtplib.SMTP(Settings.SMTP_HOST, Settings.SMTP_PORT, timeout=5) as server:
            if Settings.SMTP_USE_TLS:
                server.starttls()
            if Settings.SMTP_USERNAME:
                server.login(Settings.SMTP_USERNAME, Settings.SMTP_PASSWORD)
            server.send_message(message)
    except Exception as exc:  # pragma: no cover - best effort delivery
        print(f"Failed to send project update email for project {project.id}: {exc}")


@app.on_event("startup")
def startup_event() -> None:
    """Initialize database on startup."""
    initialize()


@app.post("/projects/{project_id}/collaborators", status_code=201)
def invite_collaborator(
    project_id: int,
    email: str = Form(...),
    role: ProjectCollaboratorRole = Form(ProjectCollaboratorRole.EDITOR),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_dep),
) -> dict:
    project = get_project_or_404(db, project_id)
    if project.owner_id != current_user["user_id"]:
        raise AuthorizationError("Only the project owner can invite collaborators")

    email_address = email.strip().lower()
    if not email_address or "@" not in email_address:
        raise ValidationError("A valid email address is required")

    existing_member = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project_id, ProjectMember.email == email_address)
        .first()
    )
    if existing_member:
        raise ConflictError("This user is already a collaborator")

    now = datetime.utcnow()
    invitation = (
        db.query(ProjectInvitation)
        .filter(
            ProjectInvitation.project_id == project_id,
            ProjectInvitation.email == email_address,
            ProjectInvitation.accepted == 0,
            ProjectInvitation.expires_at > now,
        )
        .first()
    )

    if invitation:
        invitation.role = role.value
        invitation.expires_at = now + timedelta(days=7)
        invitation.token = uuid.uuid4().hex
    else:
        invitation = ProjectInvitation(
            project_id=project_id,
            email=email_address,
            role=role.value,
            token=uuid.uuid4().hex,
            created_at=now,
            expires_at=now + timedelta(days=7),
            accepted=0,
        )
        db.add(invitation)

    db.commit()
    db.refresh(invitation)
    send_invite_email(email_address, project.name, invitation.token, invitation.role)

    return {
        "message": "Invitation sent",
        "email": email_address,
        "role": invitation.role,
        "invite_link": f"{Settings.PROJECT_INVITE_BASE_URL}?token={invitation.token}",
    }


@app.get("/projects/{project_id}/collaborators", response_model=list[ProjectCollaboratorResponse])
def list_collaborators(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_dep),
) -> list[dict]:
    project = get_project_or_404(db, project_id)
    ensure_project_access(db, project, current_user["user_id"])

    members = db.query(ProjectMember).filter(ProjectMember.project_id == project_id).all()
    return [
        {
            "id": member.id,
            "project_id": member.project_id,
            "user_id": member.user_id,
            "email": member.email,
            "role": member.role,
        }
        for member in members
    ]


@app.put("/projects/{project_id}/collaborators/{member_id}", response_model=ProjectCollaboratorResponse)
def update_collaborator_role(
    project_id: int,
    member_id: int,
    role: ProjectCollaboratorRole = Form(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_dep),
) -> dict:
    project = get_project_or_404(db, project_id)
    if project.owner_id != current_user["user_id"]:
        raise AuthorizationError("Only the project owner can change collaborator roles")

    member = db.query(ProjectMember).filter(ProjectMember.id == member_id, ProjectMember.project_id == project_id).first()
    if not member:
        raise NotFoundError("Collaborator")

    member.role = role.value
    db.commit()
    db.refresh(member)

    return {
        "id": member.id,
        "project_id": member.project_id,
        "user_id": member.user_id,
        "email": member.email,
        "role": member.role,
    }


@app.delete("/projects/{project_id}/collaborators/{member_id}", status_code=204)
def remove_collaborator(
    project_id: int,
    member_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_dep),
) -> None:
    project = get_project_or_404(db, project_id)
    if project.owner_id != current_user["user_id"]:
        raise AuthorizationError("Only the project owner can remove collaborators")

    member = db.query(ProjectMember).filter(ProjectMember.id == member_id, ProjectMember.project_id == project_id).first()
    if not member:
        raise NotFoundError("Collaborator")

    db.delete(member)
    db.commit()


@app.get("/projects/invitations/accept")
def accept_invitation(
    token: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_dep),
) -> dict:
    invitation = db.query(ProjectInvitation).filter(ProjectInvitation.token == token).first()
    if not invitation:
        raise NotFoundError("Invitation")

    if invitation.accepted == 1:
        return {"message": "Invitation was already accepted"}

    if invitation.expires_at < datetime.utcnow():
        raise ValidationError("Invitation expired")

    user_email = (current_user.get("email") or "").strip().lower()
    if user_email != invitation.email.lower():
        raise AuthorizationError("This invitation belongs to another account")

    project = get_project_or_404(db, invitation.project_id)
    existing_member = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project.id, ProjectMember.user_id == current_user["user_id"])
        .first()
    )
    if existing_member:
        existing_member.email = user_email
        existing_member.role = invitation.role
    else:
        db.add(
            ProjectMember(
                project_id=project.id,
                user_id=current_user["user_id"],
                email=user_email,
                role=invitation.role,
            )
        )

    invitation.accepted = 1
    db.commit()

    return {
        "message": "You are now a collaborator",
        "project_id": project.id,
        "project_name": project.name,
        "role": invitation.role,
    }


@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "project"}


@app.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_dep),
) -> dict:
    project = get_project_or_404(db, project_id)
    ensure_project_access(db, project, current_user["user_id"])
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "owner_id": project.owner_id,
    }


@app.put("/projects/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    payload: ProjectUpdateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_dep),
) -> dict:
    project = get_project_or_404(db, project_id)
    ensure_project_edit_access(db, project, current_user["user_id"])

    changes: list[str] = []
    if payload.name is not None and payload.name.strip() != project.name:
        changes.append(f"name: {project.name} -> {payload.name.strip()}")
        project.name = payload.name.strip()

    if payload.description is not None and payload.description != project.description:
        old_description = project.description or ""
        new_description = payload.description.strip() if payload.description else None
        changes.append(f"description: {old_description} -> {new_description or ''}")
        project.description = new_description

    if not changes:
        return {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "owner_id": project.owner_id,
        }

    db.commit()
    db.refresh(project)

    send_project_update_email(db, project, current_user, changes)

    redis_client.delete(f"projects:user:{current_user['user_id']}")
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "owner_id": project.owner_id,
    }


@app.post("/projects", response_model=ProjectResponse, status_code=201)
def create_project(
    payload: ProjectCreateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_dep),
) -> dict:
    """
    Create a new project.
    """
    if not payload.name or not payload.name.strip():
        raise ValidationError("Project name cannot be empty")

    project = Project(
        name=payload.name.strip(),
        description=payload.description.strip() if payload.description else None,
        owner_id=current_user["user_id"],
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    redis_client.delete(f"projects:user:{current_user['user_id']}")

    publish_event(
        Settings.RABBITMQ_HOST,
        "project.created",
        {
            "project_id": project.id,
            "owner_id": project.owner_id,
            "name": project.name,
        },
    )

    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "owner_id": project.owner_id,
    }


@app.get("/projects", response_model=list[ProjectResponse])
def list_projects(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_dep),
) -> list[dict]:
    """
    List all projects for the current user, including collaborator projects.
    """
    cache_key = f"projects:user:{current_user['user_id']}"
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    memberships = (
        db.query(ProjectMember)
        .filter(ProjectMember.user_id == current_user["user_id"])
        .all()
    )
    member_project_ids = [member.project_id for member in memberships]

    if member_project_ids:
        projects = (
            db.query(Project)
            .filter(or_(Project.owner_id == current_user["user_id"], Project.id.in_(member_project_ids)))
            .all()
        )
    else:
        projects = db.query(Project).filter(Project.owner_id == current_user["user_id"]).all()

    payload = [
        {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "owner_id": project.owner_id,
        }
        for project in projects
    ]

    redis_client.set(cache_key, json.dumps(payload), ex=60)
    return payload


@app.get("/internal/projects/{project_id}", response_model=ProjectResponse)
def internal_get_project(project_id: int, db: Session = Depends(get_db)) -> dict:
    """
    Internal endpoint to validate project exists (for other services).
    
    Args:
        project_id: Project ID
        db: Database session
        
    Returns:
        Project data
        
    Raises:
        NotFoundError: If project doesn't exist
    """
    project = db.get(Project, project_id)
    if not project:
        raise NotFoundError("Project")
    
    return {
        "id": project.id,
        "owner_id": project.owner_id,
        "name": project.name,
        "description": project.description,
    }
