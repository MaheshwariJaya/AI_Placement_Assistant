import enum
from typing import Optional, TYPE_CHECKING
from sqlalchemy import Boolean, Enum as SQLAlchemyEnum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import get_settings
from app.core.base import Base, IntegerIdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.organization import Institution, Department
    from app.models.student import StudentProfile
    from app.models.company import RecruiterProfile
    from app.models.placement import Notification

settings = get_settings()


class UserRole(str, enum.Enum):
    """Four distinct system roles as defined in SRS."""
    STUDENT = "student"
    TPO = "tpo"
    RECRUITER = "recruiter"
    ADMIN = "admin"


class User(Base, IntegerIdMixin, TimestampMixin):
    """Central user identity table supporting all 4 roles."""
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )
    role: Mapped[UserRole] = mapped_column(
        SQLAlchemyEnum(
            UserRole,
            name="user_role_enum",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
            schema=settings.DB_SCHEMA,
        ),
        nullable=False,
        index=True,
    )
    institution_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("institutions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Scopes Students and TPOs to their collegiate institution. NULL for Recruiters and Admins.",
    )
    department_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Explicitly nullable. Mandatory for Students only. NULL for TPOs, Recruiters, and Admins.",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Relationships
    institution: Mapped[Optional["Institution"]] = relationship(
        "Institution",
        back_populates="users",
    )
    department: Mapped[Optional["Department"]] = relationship(
        "Department",
        back_populates="users",
    )
    student_profile: Mapped[Optional["StudentProfile"]] = relationship(
        "StudentProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    recruiter_profile: Mapped[Optional["RecruiterProfile"]] = relationship(
        "RecruiterProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification",
        back_populates="recipient",
        foreign_keys="[Notification.recipient_user_id]",
        cascade="all, delete-orphan",
    )

    @property
    def department_name(self) -> Optional[str]:
        return self.department.name if self.department else None

    @property
    def institution_name(self) -> Optional[str]:
        return self.institution.name if self.institution else None

