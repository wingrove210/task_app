from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Enum
import enum
from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.comment import Comment
    from app.models.membership import Membership
    from app.models.task import Task
    
class UserRole(str, enum.Enum):

    admin = "admin"

    member = "member"

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
    )

    full_name: Mapped[str] = mapped_column(String(255))

    hashed_password: Mapped[str] = mapped_column(String)

    is_active: Mapped[bool] = mapped_column(default=True)

    memberships: Mapped[list["Membership"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    created_tasks: Mapped[list["Task"]] = relationship(
        foreign_keys="Task.creator_id",
        back_populates="creator",
    )

    assigned_tasks: Mapped[list["Task"]] = relationship(
        foreign_keys="Task.assignee_id",
        back_populates="assignee",
    )

    comments: Mapped[list["Comment"]] = relationship(
        back_populates="author",
    )
    role: Mapped[UserRole] = mapped_column(

    Enum(UserRole, native_enum=False),

    default=UserRole.member,

    nullable=False,

    index=True,

)