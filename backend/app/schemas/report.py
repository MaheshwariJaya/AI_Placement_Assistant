"""Pydantic schemas for TASK 07: Automated Placement Report Generator."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.models.report import ReportFormat, ReportStatus, ReportType


class ReportFilterParams(BaseModel):
    """Optional multi-dimensional filters for placement report generation."""
    academic_year: Optional[str] = Field(None, description="e.g. '2025-2026'")
    graduation_batch: Optional[int] = Field(None, description="e.g. 2026")
    graduation_year: Optional[int] = Field(None, description="Alias for graduation_batch")
    department_id: Optional[int] = Field(None, description="Department ID")
    department: Optional[str] = Field(None, description="Department code/name")
    company_id: Optional[int] = Field(None, description="Company ID")
    drive_id: Optional[int] = Field(None, description="Placement Drive ID")
    application_status: Optional[str] = Field(None, description="e.g. 'offer_accepted', 'offered'")
    start_date: Optional[datetime] = Field(None, description="Filter records from date")
    end_date: Optional[datetime] = Field(None, description="Filter records up to date")
    min_package_lpa: Optional[float] = Field(None, ge=0.0)
    max_package_lpa: Optional[float] = Field(None, ge=0.0)


class ReportGenerateRequest(BaseModel):
    """Payload to trigger report generation and persistence."""
    report_type: ReportType = Field(..., description="One of 10 supported institutional report types")
    file_format: ReportFormat = Field(default=ReportFormat.PDF, description="Target document format")
    title: Optional[str] = Field(None, max_length=255, description="Custom title override")
    description: Optional[str] = Field(None, max_length=1000, description="Optional notes or description")
    filters: ReportFilterParams = Field(default_factory=ReportFilterParams)
    async_generate: bool = Field(default=False, description="Whether to enqueue generation in background")


class ReportSummaryKPIs(BaseModel):
    """Core placement KPIs computed with strict database validation."""
    total_registered_students: int = 0
    total_eligible_students: int = 0
    total_placed_students: int = 0
    placement_rate_pct: float = 0.0
    students_in_pipeline: int = 0
    students_not_yet_placed: int = 0
    total_companies: int = 0
    total_active_drives: int = 0
    total_published_jobs: int = 0
    total_offers_released: int = 0
    total_accepted_offers: int = 0
    total_declined_offers: int = 0
    pending_offers: int = 0
    offer_acceptance_rate_pct: float = 0.0
    average_package_lpa: Optional[float] = None
    median_package_lpa: Optional[float] = None
    highest_package_lpa: Optional[float] = None

    @computed_field
    @property
    def active_in_pipeline_students(self) -> int:
        return self.students_in_pipeline

    @computed_field
    @property
    def total_unplaced_students(self) -> int:
        return self.students_not_yet_placed

    @computed_field
    @property
    def total_offers_accepted(self) -> int:
        return self.total_accepted_offers

    @computed_field
    @property
    def total_participating_companies(self) -> int:
        return self.total_companies

    @computed_field
    @property
    def total_placement_drives(self) -> int:
        return self.total_active_drives


class ReportDepartmentStat(BaseModel):
    """Department-wise placement statistics breakdown."""
    department_id: int
    department_code: str
    department_name: str
    eligible_students: int
    placed_students: int
    placement_rate_pct: float
    offers_accepted: int
    average_package_lpa: Optional[float] = None
    highest_package_lpa: Optional[float] = None
    top_recruiting_companies: List[str] = Field(default_factory=list)

    @computed_field
    @property
    def department(self) -> str:
        return self.department_code or self.department_name


class ReportFunnelStage(BaseModel):
    """Hiring funnel stage breakdown."""
    stage: str
    label: str
    count: int
    percentage: float

    @computed_field
    @property
    def display_name(self) -> str:
        return self.label

    @computed_field
    @property
    def conversion_from_applied_pct(self) -> float:
        return self.percentage


class ReportDataPayload(BaseModel):
    """Comprehensive analytical payload representing the computed report."""
    report_type: ReportType
    report_type_label: str
    title: str
    generated_at: datetime
    generated_by_name: str
    generated_by_role: str
    institution_id: int
    institution_name: str
    institution_code: str
    institution_city: str
    institution_logo_url: Optional[str] = None
    policy_summary: str
    filters_applied: ReportFilterParams
    summary_kpis: ReportSummaryKPIs
    department_stats: List[ReportDepartmentStat] = Field(default_factory=list)
    recruitment_funnel: List[ReportFunnelStage] = Field(default_factory=list)
    table_headers: List[str] = Field(default_factory=list)
    table_rows: List[Dict[str, Any]] = Field(default_factory=list)
    notes_and_disclaimers: List[str] = Field(default_factory=list)


class PlacementReportResponse(BaseModel):
    """Metadata representation of an archived placement report."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    institution_id: int
    generated_by_user_id: Optional[int] = None
    generated_by_name: Optional[str] = None
    report_type: ReportType
    report_type_label: str
    title: str
    description: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    file_format: ReportFormat
    file_name: str
    file_size_bytes: Optional[int] = None
    status: ReportStatus
    error_message: Optional[str] = None
    summary_snapshot: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    download_url: Optional[str] = None


class ReportOptionItem(BaseModel):
    id: Any
    label: str
    description: Optional[str] = None


class ReportFormOptionsResponse(BaseModel):
    """Filter dropdown options and metadata for the reports workspace."""
    institution_id: int
    institution_name: str
    academic_years: List[str] = Field(default_factory=list)
    graduation_batches: List[int] = Field(default_factory=list)
    departments: List[ReportOptionItem] = Field(default_factory=list)
    companies: List[ReportOptionItem] = Field(default_factory=list)
    drives: List[ReportOptionItem] = Field(default_factory=list)
    application_statuses: List[ReportOptionItem] = Field(default_factory=list)
    report_types: List[ReportOptionItem] = Field(default_factory=list)
    file_formats: List[ReportOptionItem] = Field(default_factory=list)

