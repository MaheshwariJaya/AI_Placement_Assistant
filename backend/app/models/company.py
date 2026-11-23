from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, IntegerIdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.organization import Institution
    from app.models.user import User
    from app.models.job import Job


class Company(Base, IntegerIdMixin, TimestampMixin):
    """Represents a corporate hiring organization."""
    __tablename__ = "companies"

    institution_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("institutions.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
        doc="Optional institutional affiliation: when set, this partner is associated with a specific institution",
    )
    name: Mapped[str] = mapped_column(
        String(200),
        unique=True,
        nullable=False,
    )
    industry: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    website: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    location: Mapped[Optional[str]] = mapped_column(
        String(150),
        nullable=True,
        doc="Corporate headquarters or primary operational office",
    )
    company_size: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="e.g. 1-50, 51-200, 201-1000, 1000+ employees",
    )
    contact_email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    contact_phone: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    # Relationships - Restricted cascading to protect recruitment history and associations
    institution: Mapped[Optional["Institution"]] = relationship(
        "Institution",
    )
    recruiters: Mapped[List["RecruiterProfile"]] = relationship(
        "RecruiterProfile",
        back_populates="company",
    )
    jobs: Mapped[List["Job"]] = relationship(
        "Job",
        back_populates="company",
    )


class RecruiterProfile(Base, IntegerIdMixin, TimestampMixin):
    """Associates an authenticated recruiter user to their corporate company."""
    __tablename__ = "recruiter_profiles"

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    company_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("companies.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    designation: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="e.g. Technical Talent Acquisition Specialist, HR Manager",
    )
    corporate_phone: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="recruiter_profile",
    )
    company: Mapped["Company"] = relationship(
        "Company",
        back_populates="recruiters",
    )

