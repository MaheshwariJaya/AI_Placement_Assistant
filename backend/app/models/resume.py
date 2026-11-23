from typing import Optional, Any, TYPE_CHECKING
from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, IntegerIdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.student import StudentProfile
    from app.models.placement import JobApplication


class Resume(Base, IntegerIdMixin, TimestampMixin):
    """Stores physical file references and AI-extracted metadata for uploaded student CVs."""
    __tablename__ = "resumes"
    __table_args__ = (
        CheckConstraint("file_size_bytes <= 5242880", name="chk_resume_file_size_limit"),
        CheckConstraint("file_type IN ('pdf', 'docx')", name="chk_resume_file_type"),
    )

    student_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("student_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Private to StudentProfile. Enforces tenant boundary.",
    )
    file_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Original sanitized filename presented by student.",
    )
    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        doc="Private server storage path outside static public web directory.",
    )
    file_type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        doc="Document extension / type: 'pdf' or 'docx'.",
    )
    file_size_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="File size in bytes (hard max 5MB).",
    )
    file_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        doc="SHA-256 hash of file content for integrity and deduplication.",
    )
    raw_extracted_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Raw text extracted locally via PyMuPDF or python-docx.",
    )
    parsed_entities_json: Mapped[Optional[Any]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        nullable=True,
        doc="Semi-structured entity JSON extracted via AI.",
    )
    parsing_status: Mapped[str] = mapped_column(
        String(50),
        default="uploaded",
        nullable=False,
        index=True,
        doc="Status: uploaded, processing, extracted, review_required, approved, rejected, failed.",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Flag indicating if this is the active/primary resume for applications.",
    )

    # Relationships
    student_profile: Mapped["StudentProfile"] = relationship(
        "StudentProfile",
        back_populates="resumes",
    )
    applications: Mapped[list["JobApplication"]] = relationship(
        "JobApplication",
        back_populates="resume",
    )

