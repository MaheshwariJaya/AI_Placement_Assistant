"""ORM models for Placement Preparation Arena (questions, assessments, attempts, submissions, and privacy prefs)."""
import enum
from datetime import datetime
from typing import Any, Optional, TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SQLAlchemyEnum,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import get_settings
from app.core.base import Base, IntegerIdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.organization import Department, Institution
    from app.models.student import StudentProfile
    from app.models.user import User

settings = get_settings()


class ArenaCategory(str, enum.Enum):
    DSA = "dsa"
    PROGRAMMING_FUNDAMENTALS = "programming_fundamentals"
    DBMS = "dbms"
    OPERATING_SYSTEMS = "operating_systems"
    COMPUTER_NETWORKS = "computer_networks"
    OOP = "oop"
    APTITUDE_LOGICAL = "aptitude_logical"
    QUANTITATIVE = "quantitative"
    VERBAL = "verbal"
    TECHNICAL_MCQS = "technical_mcqs"
    HR_BEHAVIORAL = "hr_behavioral"

    # --- Civil Engineering Core Placement Categories ---
    CIVIL_STRUCTURES = "civil_structures"
    CIVIL_CONCRETE = "civil_concrete"
    CIVIL_GEOTECH = "civil_geotech"
    CIVIL_SURVEYING = "civil_surveying"
    CIVIL_TRANSPORTATION = "civil_transportation"
    CIVIL_HYDRAULICS = "civil_hydraulics"
    CIVIL_ENVIRONMENTAL = "civil_environmental"
    CIVIL_CONSTRUCTION = "civil_construction"

    # --- Mechanical Engineering Core Placement Categories ---
    MECH_THERMAL = "mech_thermal"
    MECH_FLUID = "mech_fluid"
    MECH_SOM = "mech_som"
    MECH_DESIGN = "mech_design"
    MECH_MANUFACTURING = "mech_manufacturing"
    MECH_INDUSTRIAL = "mech_industrial"
    MECH_AUTOMOBILE = "mech_automobile"
    MECH_HEAT_TRANSFER = "mech_heat_transfer"

    # --- Electrical Engineering Core Placement Categories ---
    EEE_MACHINES = "eee_machines"
    EEE_POWER_SYSTEMS = "eee_power_systems"
    EEE_CONTROL_SYSTEMS = "eee_control_systems"
    EEE_POWER_ELECTRONICS = "eee_power_electronics"
    EEE_CIRCUITS = "eee_circuits"
    EEE_MEASUREMENTS = "eee_measurements"

    # --- Electronics & Communication Engineering Core Placement Categories ---
    ECE_DIGITAL = "ece_digital"
    ECE_ANALOG = "ece_analog"
    ECE_COMMUNICATION = "ece_communication"
    ECE_SIGNALS = "ece_signals"
    ECE_VLSI = "ece_vlsi"
    ECE_EM_ANTENNAS = "ece_em_antennas"

    # --- Chemical Engineering Core Placement Categories ---
    CHEM_REACTION = "chem_reaction"
    CHEM_MASS_TRANSFER = "chem_mass_transfer"
    CHEM_HEAT_TRANSFER = "chem_heat_transfer"
    CHEM_THERMODYNAMICS = "chem_thermodynamics"
    CHEM_PROCESS_CONTROL = "chem_process_control"
    CHEM_FLUID_OPERATIONS = "chem_fluid_operations"

    # --- Mining Engineering Core Placement Categories ---
    MINE_METHODS = "mine_methods"
    MINE_ROCK_MECHANICS = "mine_rock_mechanics"
    MINE_VENTILATION = "mine_ventilation"
    MINE_DRILLING_BLASTING = "mine_drilling_blasting"
    MINE_SURVEYING = "mine_surveying"
    MINE_MACHINERY = "mine_machinery"

    # --- Petroleum Engineering Core Placement Categories ---
    PETRO_RESERVOIR = "petro_reservoir"
    PETRO_DRILLING = "petro_drilling"
    PETRO_PRODUCTION = "petro_production"
    PETRO_WELL_LOGGING = "petro_well_logging"
    PETRO_NATURAL_GAS = "petro_natural_gas"
    PETRO_OFFSHORE = "petro_offshore"

    # --- Production & Industrial Engineering Core Placement Categories ---
    PIE_MANUFACTURING = "pie_manufacturing"
    PIE_OPERATIONS_RESEARCH = "pie_operations_research"
    PIE_QUALITY = "pie_quality"
    PIE_WORK_STUDY = "pie_work_study"
    PIE_PPC = "pie_ppc"
    PIE_METROLOGY = "pie_metrology"

    # --- Structural Engineering Core Placement Categories ---
    STRUCT_ADVANCED_ANALYSIS = "struct_advanced_analysis"
    STRUCT_CONCRETE_DESIGN = "struct_concrete_design"
    STRUCT_STEEL_DESIGN = "struct_steel_design"
    STRUCT_EARTHQUAKE = "struct_earthquake"
    STRUCT_FOUNDATIONS = "struct_foundations"
    STRUCT_DYNAMICS = "struct_dynamics"

    # --- Architecture & Planning Core Placement Categories ---
    ARCH_DESIGN = "arch_design"
    ARCH_CONSTRUCTION = "arch_construction"
    ARCH_URBAN_PLANNING = "arch_urban_planning"
    ARCH_SUSTAINABILITY = "arch_sustainability"
    ARCH_SERVICES = "arch_services"
    ARCH_LANDSCAPE = "arch_landscape"

    # --- Computer Science & Engineering 40 Curricular Subjects ---
    CS_MATHS_FOR_COMPUTING = "cs_maths_for_computing"
    CS_POPL = "cs_popl"
    CS_LOGIC_DESIGN = "cs_logic_design"
    CS_CYBER_LAW_ETHICS = "cs_cyber_law_ethics"
    CS_DAA = "cs_daa"
    CS_WEB_TECHNOLOGIES = "cs_web_technologies"
    CS_COA = "cs_coa"
    CS_SOFTWARE_ENGINEERING = "cs_software_engineering"
    CS_THEORY_OF_COMPUTATION = "cs_theory_of_computation"
    CS_AIML = "cs_aiml"
    CS_MICROPROCESSORS = "cs_microprocessors"
    CS_COMPUTER_GRAPHICS = "cs_computer_graphics"
    CS_JAVA_PROGRAMMING = "cs_java_programming"
    CS_ROBOTICS_EMBEDDED = "cs_robotics_embedded"
    CS_COMPILER_DESIGN = "cs_compiler_design"
    CS_IMAGE_PROCESSING = "cs_image_processing"
    CS_SYSTEM_PROGRAMMING = "cs_system_programming"
    CS_ADVANCED_ML = "cs_advanced_ml"
    CS_GRAPHS_NETWORKS = "cs_graphs_networks"
    CS_NLP = "cs_nlp"
    CS_ECOMMERCE_BI = "cs_ecommerce_bi"
    CS_WIRELESS_MOBILE = "cs_wireless_mobile"
    CS_MODERN_WEB_DEV = "cs_modern_web_dev"
    CS_DISTRIBUTED_COMPUTING = "cs_distributed_computing"
    CS_DATA_SCIENCE_ANALYTICS = "cs_data_science_analytics"
    CS_CRYPTOGRAPHY_SECURITY = "cs_cryptography_security"
    CS_BLOCKCHAIN = "cs_blockchain"
    CS_BIOMETRICS_BIOSIGNAL = "cs_biometrics_biosignal"
    CS_PARALLEL_GPU = "cs_parallel_gpu"
    CS_DEEP_LEARNING = "cs_deep_learning"
    CS_COMPUTER_VISION = "cs_computer_vision"
    CS_IOT = "cs_iot"
    CS_BIG_DATA_IR = "cs_big_data_ir"
    CS_CYBER_SECURITY = "cs_cyber_security"


class ArenaDifficulty(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class ArenaQuestionType(str, enum.Enum):
    MCQ = "mcq"
    CODING = "coding"
    BEHAVIORAL = "behavioral"


class ArenaAssessmentMode(str, enum.Enum):
    TOPIC_PRACTICE = "topic_practice"
    TIMED_TEST = "timed_test"
    COMPANY_PREP = "company_prep"
    INSTITUTIONAL_TEST = "institutional_test"


class ArenaAttemptStatus(str, enum.Enum):
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    EXPIRED = "expired"


class ArenaContentSource(str, enum.Enum):
    CURATED_ORIGINAL = "curated_original"
    INSTITUTIONAL_STAFF = "institutional_staff"
    AI_GENERATED_PRACTICE = "ai_generated_practice"


def _enum_col(enum_cls: type[enum.Enum], pg_name: str):
    return SQLAlchemyEnum(
        enum_cls,
        name=pg_name,
        native_enum=True,
        values_callable=lambda obj: [e.value for e in obj],
        schema=settings.DB_SCHEMA,
    )


class ArenaQuestion(Base, IntegerIdMixin, TimestampMixin):
    """Reusable placement preparation question supporting MCQ, coding, and HR/behavioral prompts."""

    __tablename__ = "arena_questions"
    __table_args__ = (
        CheckConstraint("expected_time_seconds >= 10 AND expected_time_seconds <= 7200", name="chk_arena_q_time_bounds"),
        CheckConstraint("max_marks >= 1 AND max_marks <= 100", name="chk_arena_q_marks_bounds"),
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[ArenaCategory] = mapped_column(
        _enum_col(ArenaCategory, "arena_category_enum"),
        nullable=False,
        index=True,
    )
    difficulty: Mapped[ArenaDifficulty] = mapped_column(
        _enum_col(ArenaDifficulty, "arena_difficulty_enum"),
        nullable=False,
        index=True,
    )
    question_type: Mapped[ArenaQuestionType] = mapped_column(
        _enum_col(ArenaQuestionType, "arena_question_type_enum"),
        nullable=False,
        index=True,
    )
    content_source: Mapped[ArenaContentSource] = mapped_column(
        _enum_col(ArenaContentSource, "arena_content_source_enum"),
        default=ArenaContentSource.CURATED_ORIGINAL,
        nullable=False,
        index=True,
    )
    company_tag: Mapped[Optional[str]] = mapped_column(
        String(120),
        nullable=True,
        index=True,
        doc="Company-style preparation label; always original/curated pattern and never confidential real exam leaks.",
    )
    role_tags_json: Mapped[Any] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    options_json: Mapped[Optional[Any]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        nullable=True,
    )
    correct_option_key: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    starter_code_json: Mapped[Optional[Any]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        nullable=True,
    )
    test_cases_json: Mapped[Optional[Any]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        nullable=True,
        doc="List of {'stdin': str, 'expected_stdout': str, 'is_sample': bool} for coding problems.",
    )
    explanation_text: Mapped[str] = mapped_column(Text, nullable=False)
    sample_solution_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expected_time_seconds: Mapped[int] = mapped_column(Integer, default=90, nullable=False)
    max_marks: Mapped[int] = mapped_column(Integer, default=10, nullable=False)

    institution_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    created_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    institution: Mapped[Optional["Institution"]] = relationship("Institution")
    created_by_user: Mapped[Optional["User"]] = relationship("User")


class ArenaAssessment(Base, IntegerIdMixin, TimestampMixin):
    """Curated timed test, company-style track, or TPO/Admin published institutional test."""

    __tablename__ = "arena_assessments"
    __table_args__ = (
        CheckConstraint("duration_minutes >= 1 AND duration_minutes <= 180", name="chk_arena_assess_duration"),
        CheckConstraint("passing_percentage >= 0 AND passing_percentage <= 100", name="chk_arena_assess_passing_pct"),
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[ArenaAssessmentMode] = mapped_column(
        _enum_col(ArenaAssessmentMode, "arena_assessment_mode_enum"),
        nullable=False,
        index=True,
    )
    category: Mapped[Optional[ArenaCategory]] = mapped_column(
        _enum_col(ArenaCategory, "arena_category_enum"),
        nullable=True,
        index=True,
    )
    difficulty: Mapped[ArenaDifficulty] = mapped_column(
        _enum_col(ArenaDifficulty, "arena_difficulty_enum"),
        default=ArenaDifficulty.MEDIUM,
        nullable=False,
        index=True,
    )
    company_name_style: Mapped[Optional[str]] = mapped_column(String(120), nullable=True, index=True)
    provenance_notice: Mapped[str] = mapped_column(
        String(500),
        default=(
            "Original & curated placement preparation content modeled on industry patterns. "
            "Not confidential or leaked company test material."
        ),
        nullable=False,
    )
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    question_ids_json: Mapped[Any] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    passing_percentage: Mapped[float] = mapped_column(Numeric(5, 2), default=60.0, nullable=False)

    institution_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    department_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    target_graduation_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    created_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    starts_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    institution: Mapped[Optional["Institution"]] = relationship("Institution")
    department: Mapped[Optional["Department"]] = relationship("Department")
    created_by_user: Mapped[Optional["User"]] = relationship("User")


class ArenaAttempt(Base, IntegerIdMixin, TimestampMixin):
    """Student attempt for topic practice, timed test, company-style track, or institutional test."""

    __tablename__ = "arena_attempts"
    __table_args__ = (
        CheckConstraint("elapsed_seconds >= 0", name="chk_arena_attempt_elapsed"),
        CheckConstraint("accuracy_pct >= 0 AND accuracy_pct <= 100", name="chk_arena_attempt_accuracy"),
        CheckConstraint("score_pct >= 0 AND score_pct <= 100", name="chk_arena_attempt_score"),
    )

    student_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("student_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assessment_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("arena_assessments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    mode: Mapped[ArenaAssessmentMode] = mapped_column(
        _enum_col(ArenaAssessmentMode, "arena_assessment_mode_enum"),
        nullable=False,
        index=True,
    )
    category: Mapped[Optional[ArenaCategory]] = mapped_column(
        _enum_col(ArenaCategory, "arena_category_enum"),
        nullable=True,
        index=True,
    )
    difficulty: Mapped[Optional[ArenaDifficulty]] = mapped_column(
        _enum_col(ArenaDifficulty, "arena_difficulty_enum"),
        nullable=True,
    )
    company_name_style: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    status: Mapped[ArenaAttemptStatus] = mapped_column(
        _enum_col(ArenaAttemptStatus, "arena_attempt_status_enum"),
        default=ArenaAttemptStatus.IN_PROGRESS,
        nullable=False,
        index=True,
    )
    question_ids_json: Mapped[Any] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    time_limit_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    elapsed_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    total_questions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    attempted_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    correct_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    accuracy_pct: Mapped[float] = mapped_column(Numeric(5, 2), default=0.0, nullable=False)
    score_pct: Mapped[float] = mapped_column(Numeric(5, 2), default=0.0, nullable=False)

    student_profile: Mapped["StudentProfile"] = relationship("StudentProfile")
    assessment: Mapped[Optional["ArenaAssessment"]] = relationship("ArenaAssessment")
    answers: Mapped[list["ArenaAttemptAnswer"]] = relationship(
        "ArenaAttemptAnswer",
        back_populates="attempt",
        cascade="all, delete-orphan",
        order_by="ArenaAttemptAnswer.question_order",
    )


class ArenaAttemptAnswer(Base, IntegerIdMixin, TimestampMixin):
    """Per-question response, coding execution result, solving time, and explanation review state."""

    __tablename__ = "arena_attempt_answers"
    __table_args__ = (
        UniqueConstraint("attempt_id", "question_id", name="uq_arena_attempt_question"),
        CheckConstraint("time_spent_seconds >= 0", name="chk_arena_ans_time_non_negative"),
    )

    attempt_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("arena_attempts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("arena_questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("student_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_order: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    selected_option_key: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    submitted_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    code_language: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    behavioral_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    is_correct: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    score_awarded: Mapped[float] = mapped_column(Numeric(5, 2), default=0.0, nullable=False)
    time_spent_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    execution_result_json: Mapped[Optional[Any]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        nullable=True,
    )
    ai_feedback_json: Mapped[Optional[Any]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        nullable=True,
    )
    answered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    attempt: Mapped["ArenaAttempt"] = relationship("ArenaAttempt", back_populates="answers")
    question: Mapped["ArenaQuestion"] = relationship("ArenaQuestion")
    student_profile: Mapped["StudentProfile"] = relationship("StudentProfile")


class ArenaUserPreference(Base, IntegerIdMixin, TimestampMixin):
    """Privacy controls and coding preferences for Placement Preparation Arena."""

    __tablename__ = "arena_user_preferences"

    student_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("student_profiles.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    leaderboard_opt_in: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Explicit opt-in for department and batch leaderboards (privacy-preserving by default).",
    )
    anonymize_name: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="When opted into leaderboards, mask full name behind anonymous scholar alias if True.",
    )
    preferred_language: Mapped[str] = mapped_column(String(32), default="python", nullable=False)

    student_profile: Mapped["StudentProfile"] = relationship("StudentProfile")

