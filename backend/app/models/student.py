from typing import Optional, TYPE_CHECKING
from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, IntegerIdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.resume import Resume
    from app.models.placement import JobApplication
    from app.models.mock_interview import MockInterviewSession
    from app.models.readiness import ReadinessSnapshot


class StudentProfile(Base, IntegerIdMixin, TimestampMixin):
    """Normalized student academic details and placement readiness profile."""
    __tablename__ = "student_profiles"
    __table_args__ = (
        CheckConstraint("cgpa >= 0.0 AND cgpa <= 10.0", name="chk_student_cgpa_range"),
        CheckConstraint("active_backlogs >= 0", name="chk_student_active_backlogs_non_negative"),
        CheckConstraint("total_backlogs >= 0", name="chk_student_total_backlogs_non_negative"),
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    roll_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )
    graduation_year: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )
    cgpa: Mapped[float] = mapped_column(
        Numeric(4, 2),
        nullable=False,
    )
    active_backlogs: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    total_backlogs: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    linkedin_url: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    github_url: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    portfolio_url: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    is_placement_ready: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="student_profile",
    )
    resumes: Mapped[list["Resume"]] = relationship(
        "Resume",
        back_populates="student_profile",
        cascade="all, delete-orphan",
    )
    education_history: Mapped[list["StudentEducation"]] = relationship(
        "StudentEducation",
        back_populates="student_profile",
        cascade="all, delete-orphan",
    )
    skills: Mapped[list["StudentSkill"]] = relationship(
        "StudentSkill",
        back_populates="student_profile",
        cascade="all, delete-orphan",
    )
    projects: Mapped[list["StudentProject"]] = relationship(
        "StudentProject",
        back_populates="student_profile",
        cascade="all, delete-orphan",
    )
    experiences: Mapped[list["StudentExperience"]] = relationship(
        "StudentExperience",
        back_populates="student_profile",
        cascade="all, delete-orphan",
    )
    certifications: Mapped[list["StudentCertification"]] = relationship(
        "StudentCertification",
        back_populates="student_profile",
        cascade="all, delete-orphan",
    )
    applications: Mapped[list["JobApplication"]] = relationship(
        "JobApplication",
        back_populates="student_profile",
    )
    mock_interview_sessions: Mapped[list["MockInterviewSession"]] = relationship(
        "MockInterviewSession",
        back_populates="student_profile",
        cascade="all, delete-orphan",
    )
    readiness_snapshots: Mapped[list["ReadinessSnapshot"]] = relationship(
        "ReadinessSnapshot",
        back_populates="student_profile",
        cascade="all, delete-orphan",
    )

    @property
    def department_name(self) -> Optional[str]:
        return self.user.department.name if (self.user and self.user.department) else None

    @property
    def institution_name(self) -> Optional[str]:
        return self.user.institution.name if (self.user and self.user.institution) else None


class StudentEducation(Base, IntegerIdMixin, TimestampMixin):
    """Normalized educational background history (Degree, 12th, 10th, etc.)."""
    __tablename__ = "student_education"

    student_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("student_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    institution_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        doc="Name of school, college, or university.",
    )
    degree: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        doc="Degree, diploma, or standard (e.g. B.Tech, Class XII, Class X).",
    )
    field_of_study: Mapped[Optional[str]] = mapped_column(
        String(150),
        nullable=True,
        doc="Major, department, or specialization (e.g. Computer Science).",
    )
    start_year: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    end_year: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Completion or graduation year.",
    )
    cgpa_or_percentage: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Self-reported academic score from resume.",
    )

    # Relationships
    student_profile: Mapped["StudentProfile"] = relationship(
        "StudentProfile",
        back_populates="education_history",
    )


class StudentSkill(Base, IntegerIdMixin, TimestampMixin):
    """Normalized technical, soft, or tool skill associated with a student."""
    __tablename__ = "student_skills"
    __table_args__ = (
        UniqueConstraint("student_id", "skill_name", name="uq_student_skills_student_skill"),
    )

    student_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("student_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(
        String(50),
        default="technical",
        nullable=False,
        doc="Category: technical, soft, tool, framework, language.",
    )
    proficiency_level: Mapped[str] = mapped_column(
        String(20),
        default="intermediate",
        nullable=False,
        doc="Proficiency: beginner, intermediate, advanced, expert.",
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Relationships
    student_profile: Mapped["StudentProfile"] = relationship(
        "StudentProfile",
        back_populates="skills",
    )


class StudentProject(Base, IntegerIdMixin, TimestampMixin):
    """Academic, capstone, or personal technical project."""
    __tablename__ = "student_projects"

    student_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("student_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    technologies: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Comma-separated or formatted string of tools/languages.",
    )
    project_url: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    start_date: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
    )
    end_date: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
    )

    # Relationships
    student_profile: Mapped["StudentProfile"] = relationship(
        "StudentProfile",
        back_populates="projects",
    )


class StudentExperience(Base, IntegerIdMixin, TimestampMixin):
    """Internship or work experience."""
    __tablename__ = "student_experiences"

    student_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("student_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    role_title: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    start_date: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
    )
    end_date: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
    )
    is_current: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Relationships
    student_profile: Mapped["StudentProfile"] = relationship(
        "StudentProfile",
        back_populates="experiences",
    )


class StudentCertification(Base, IntegerIdMixin, TimestampMixin):
    """Industry or professional certification."""
    __tablename__ = "student_certifications"

    student_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("student_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    certificate_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    issuing_organization: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    issue_date: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
    )
    credential_url: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    # Relationships
    student_profile: Mapped["StudentProfile"] = relationship(
        "StudentProfile",
        back_populates="certifications",
    )
