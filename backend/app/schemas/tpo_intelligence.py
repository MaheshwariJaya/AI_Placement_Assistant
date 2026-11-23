"""Pydantic schemas for TASK 05: TPO Placement Intelligence, Skill Demand & Forecasting."""
from datetime import datetime
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class IntelligenceFilterOptions(BaseModel):
    academic_years: List[str] = Field(default_factory=list)
    graduation_batches: List[int] = Field(default_factory=list)
    departments: List[Dict[str, object]] = Field(default_factory=list)
    companies: List[Dict[str, object]] = Field(default_factory=list)
    job_categories: List[str] = Field(default_factory=list)
    employment_types: List[str] = Field(default_factory=list)


class AppliedIntelligenceFilters(BaseModel):
    institution_id: int
    academic_year: Optional[str] = None
    graduation_year: Optional[int] = None
    department_id: Optional[int] = None
    company_id: Optional[int] = None
    job_category: Optional[str] = None
    employment_type: Optional[str] = None


class PlacementOverviewStats(BaseModel):
    total_registered_students: int = 0
    total_eligible_students: int = 0
    total_placed_students: int = 0
    students_in_pipeline: int = 0
    students_not_yet_placed: int = 0
    total_active_drives: int = 0
    total_participating_companies: int = 0
    total_published_jobs: int = 0
    total_offers_released: int = 0
    total_accepted_offers: int = 0
    total_declined_offers: int = 0
    pending_offers: int = 0
    placement_rate_pct: float = 0.0
    offer_acceptance_rate_pct: float = 0.0
    average_package_lpa: Optional[float] = None
    median_package_lpa: Optional[float] = None
    highest_package_lpa: Optional[float] = None
    offers_missing_package_count: int = 0


class DepartmentAnalyticsItem(BaseModel):
    department_id: int
    department_code: str
    department_name: str
    eligible_students: int
    placed_students: int
    in_pipeline_students: int
    unplaced_students: int
    placement_rate_pct: float
    offers_accepted: int
    average_package_lpa: Optional[float] = None
    highest_package_lpa: Optional[float] = None
    top_demanded_skills: List[str] = Field(default_factory=list)
    skill_gaps: List[str] = Field(default_factory=list)


class YearDepartmentComparisonItem(BaseModel):
    academic_year: str
    graduation_year: int
    department_code: str
    department_name: str
    eligible_students: int
    placed_students: int
    placement_rate_pct: float
    average_package_lpa: Optional[float] = None


class HistoricalTrendPoint(BaseModel):
    academic_year: str
    graduation_year: int
    eligible_students: int
    placed_students: int
    placement_rate_pct: float
    yoy_placement_growth_pct_pts: Optional[float] = None
    participating_companies: int
    offers_released: int
    offers_accepted: int
    offers_declined: int
    offer_conversion_rate_pct: float
    average_package_lpa: Optional[float] = None
    median_package_lpa: Optional[float] = None
    highest_package_lpa: Optional[float] = None


class SalaryDistributionBucket(BaseModel):
    bucket_label: str
    min_lpa: float
    max_lpa: Optional[float] = None
    accepted_offer_count: int
    percentage: float


class RecruitmentFunnelStage(BaseModel):
    stage_key: str
    stage_label: str
    application_count: int
    conversion_from_applied_pct: float


class ForecastMetricEstimate(BaseModel):
    metric_key: str
    metric_label: str
    unit: str
    target_period: str
    projected_value: float
    ci_lower_95: float
    ci_upper_95: float
    sample_size: int
    r_squared: Optional[float] = None
    methodology: str
    confidence_level: Literal["high", "moderate", "low", "exploratory"]
    limitations: List[str] = Field(default_factory=list)


class DepartmentForecastItem(BaseModel):
    department_code: str
    department_name: str
    latest_placement_rate_pct: float
    projected_placement_rate_pct: float
    ci_lower_95: float
    ci_upper_95: float
    projected_placed_students: int
    sample_size: int
    trend_direction: Literal["upward", "stable", "downward", "insufficient_history"]
    confidence_level: Literal["high", "moderate", "low", "exploratory"]


class ForecastingSection(BaseModel):
    target_academic_year: str
    target_graduation_year: int
    overall_sample_years: int
    placement_forecast: ForecastMetricEstimate
    company_participation_forecast: ForecastMetricEstimate
    offer_volume_forecast: ForecastMetricEstimate
    department_forecasts: List[DepartmentForecastItem] = Field(default_factory=list)
    disclaimer: str


class SkillDemandStat(BaseModel):
    skill_name: str
    job_postings_count: int
    mandatory_count: int
    accepted_offer_count: int
    outcome_success_rate_pct: float
    growth_delta_pct: Optional[float] = None


class DepartmentSkillGapItem(BaseModel):
    department_code: str
    department_name: str
    demanded_skills: List[str] = Field(default_factory=list)
    verified_coverage_pct: float
    missing_or_low_supply_skills: List[str] = Field(default_factory=list)


class SkillDemandIntelligence(BaseModel):
    most_requested_skills: List[SkillDemandStat] = Field(default_factory=list)
    emerging_skills: List[SkillDemandStat] = Field(default_factory=list)
    winning_outcome_skills: List[SkillDemandStat] = Field(default_factory=list)
    department_skill_gaps: List[DepartmentSkillGapItem] = Field(default_factory=list)


class DataCompletenessSummary(BaseModel):
    students_missing_department: int = 0
    offers_missing_package: int = 0
    jobs_missing_ctc: int = 0
    applications_without_drive: int = 0
    historical_years_available: int = 0
    warnings: List[str] = Field(default_factory=list)


class TpoPlacementIntelligenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    generated_at: datetime
    cache_hit: bool = False
    filters_applied: AppliedIntelligenceFilters
    filter_options: IntelligenceFilterOptions
    policy_summary: str
    overview: PlacementOverviewStats
    department_analytics: List[DepartmentAnalyticsItem] = Field(default_factory=list)
    year_department_comparisons: List[YearDepartmentComparisonItem] = Field(default_factory=list)
    historical_trends: List[HistoricalTrendPoint] = Field(default_factory=list)
    salary_distribution: List[SalaryDistributionBucket] = Field(default_factory=list)
    recruitment_funnel: List[RecruitmentFunnelStage] = Field(default_factory=list)
    forecasting: ForecastingSection
    skill_intelligence: SkillDemandIntelligence
    data_completeness: DataCompletenessSummary

