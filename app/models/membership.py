from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ProjectRole
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.user import User


class Membership(Base, TimestampMixin):
    __tablename__ = "memberships"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE")
    )

    role: Mapped[ProjectRole] = mapped_column(
        Enum(ProjectRole),
        default=ProjectRole.MEMBER,
    )

    user: Mapped["User"] = relationship(
        back_populates="memberships"
    )

    project: Mapped["Project"] = relationship(
        back_populates="memberships"
    )