export type UserRole = 'student' | 'tpo' | 'recruiter' | 'admin';

export interface User {
  id: number;
  email: string;
  full_name: string;
  phone?: string;
  role: UserRole;
  institution_id?: number;
  department_id?: number;
  department_name?: string;
  institution_name?: string;
  student_profile_id?: number;
  roll_number?: string;
  student_profile?: StudentProfile;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

export interface StudentProfile {
  id: number;
  user_id: number;
  roll_number: string;
  graduation_year: number;
  cgpa: number;
  active_backlogs: number;
  total_backlogs: number;
  linkedin_url?: string;
  github_url?: string;
  portfolio_url?: string;
  is_placement_ready: boolean;
  created_at: string;
  updated_at: string;
  department_name?: string;
  institution_name?: string;
  user?: Partial<User>;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in_hours: number;
  user: User;
}

export interface StudentRegistrationData {
  roll_number: string;
  graduation_year: number;
  cgpa: number;
  active_backlogs?: number;
  total_backlogs?: number;
}

export interface RegisterPayload {
  email: string;
  password: string;
  full_name: string;
  phone?: string;
  role: UserRole;
  institution_id?: number;
  department_id?: number;
  student_data?: StudentRegistrationData;
}

export interface Institution {
  id: number;
  name: string;
  code: string;
  city: string;
  is_active: boolean;
}

export interface Department {
  id: number;
  institution_id: number;
  name: string;
  code: string;
  is_active: boolean;
}

export interface HealthLiveResponse {
  success: boolean;
  status: string;
  timestamp: string;
  app: string;
  environment: string;
}

export interface HealthReadyResponse {
  success: boolean;
  status: 'ready' | 'degraded';
  timestamp: string;
  database: {
    status: 'connected' | 'disconnected';
    host?: string;
    database_name?: string;
    schema?: string;
    latency_ms?: number;
    error?: string;
    remedy?: string;
  };
  ai_engine?: {
    active_provider: string;
    gemini_model?: string;
    openai_model?: string;
  };
}

export interface NavItem {
  label: string;
  path: string;
  icon?: string;
  badge?: string;
}

export interface DashboardStat {
  title: string;
  value: string | number;
  change?: string;
  isPositive?: boolean;
  description: string;
}

// ==========================================
// Phase 3: Resume Intelligence Types
// ==========================================

export interface PersonalInfo {
  full_name?: string;
  email?: string;
  phone?: string;
  location?: string;
  linkedin_url?: string;
  github_url?: string;
  portfolio_url?: string;
  evidence?: string;
  confidence?: 'high' | 'medium' | 'low';
}

export interface EducationItem {
  institution: string;
  degree: string;
  field_of_study?: string;
  start_year?: number;
  end_year?: number;
  cgpa_or_percentage?: string;
  evidence?: string;
  confidence?: 'high' | 'medium' | 'low';
}

export interface SkillItem {
  skill_name: string;
  category: string;
  proficiency_level: string;
  evidence?: string;
  confidence?: 'high' | 'medium' | 'low';
}

export interface ProjectItem {
  title: string;
  description?: string;
  technologies?: string;
  project_url?: string;
  start_date?: string;
  end_date?: string;
  evidence?: string;
  confidence?: 'high' | 'medium' | 'low';
}

export interface ExperienceItem {
  company_name: string;
  role_title: string;
  description?: string;
  start_date?: string;
  end_date?: string;
  is_current?: boolean;
  evidence?: string;
  confidence?: 'high' | 'medium' | 'low';
}

export interface CertificationItem {
  certificate_name: string;
  issuing_organization: string;
  issue_date?: string;
  credential_url?: string;
  evidence?: string;
  confidence?: 'high' | 'medium' | 'low';
}

export interface ResumeStructuredData {
  personal_info?: PersonalInfo;
  education?: EducationItem[];
  skills?: SkillItem[];
  projects?: ProjectItem[];
  experiences?: ExperienceItem[];
  certifications?: CertificationItem[];
  extraction_method?: string;
  overall_confidence?: 'high' | 'medium' | 'low';
  hallucinations_purged?: number;
}

export type ParsingStatus =
  | 'uploaded'
  | 'processing'
  | 'extracted'
  | 'review_required'
  | 'approved'
  | 'rejected'
  | 'failed';

export interface Resume {
  id: number;
  student_id: number;
  file_name: string;
  file_type: 'pdf' | 'docx';
  file_size_bytes: number;
  file_hash: string;
  parsing_status: ParsingStatus;
  is_active: boolean;
  parsed_entities?: ResumeStructuredData;
  raw_text_preview?: string;
  created_at: string;
  updated_at: string;
}

export interface ResumeSyncRequest {
  verified_data?: ResumeStructuredData;
  sync_education?: boolean;
  sync_skills?: boolean;
  sync_projects?: boolean;
  sync_experiences?: boolean;
  sync_certifications?: boolean;
  sync_links?: boolean;
  update_existing_links?: boolean;
  update_phone?: boolean;
}

export interface ResumeSyncResponse {
  message: string;
  synced_counts: {
    education?: number;
    skills: number;
    projects: number;
    experiences: number;
    certifications: number;
    profile_links_updated: number;
    phone_updated?: number;
  };
  verified_metrics_protected: boolean;
  protected_academic_fields?: string[];
}

// ==========================================
// Phase 4: Company and Job Management Types
// ==========================================

export interface Company {
  id: number;
  name: string;
  industry: string;
  description?: string;
  website?: string;
  location?: string;
  company_size?: string;
  contact_email?: string;
  contact_phone?: string;
  is_verified: boolean;
  is_active?: boolean;
  created_at: string;
  updated_at: string;
  active_jobs_count?: number;
}

export interface CompanyCreate {
  name: string;
  industry: string;
  description?: string;
  website?: string;
  location?: string;
  company_size?: string;
  contact_email?: string;
  contact_phone?: string;
}

export interface CompanyUpdate {
  name?: string;
  industry?: string;
  description?: string;
  website?: string;
  location?: string;
  company_size?: string;
  contact_email?: string;
  contact_phone?: string;
}

export interface RecruiterProfile {
  id: number;
  user_id: number;
  company_id: number;
  designation?: string;
  corporate_phone?: string;
  company?: Company;
  created_at: string;
  updated_at: string;
}

export type EmploymentType = 'full_time' | 'internship' | 'intern_to_full_time';
export type WorkMode = 'on_site' | 'hybrid' | 'remote';
export type JobStatus = 'draft' | 'published' | 'closed' | 'cancelled';

export interface JobSkill {
  id: number;
  job_id: number;
  skill_name: string;
  is_mandatory: boolean;
  weight_factor: number;
}

export interface JobDepartment {
  id: number;
  department_id: number;
  department_name?: string;
  department_code?: string;
}

export interface Job {
  id: number;
  company_id: number;
  company_name: string;
  company_industry?: string;
  created_by_user_id: number;
  institution_id?: number;
  institution_name?: string;
  is_active?: boolean;
  title: string;
  description?: string;
  employment_type: EmploymentType;
  work_mode: WorkMode;
  location: string;
  salary_range?: string;
  ctc_lpa?: number;
  base_salary_lpa?: number;
  stipend_monthly?: number;
  min_cgpa: number;
  target_graduation_year?: number;
  max_active_backlogs: number;
  max_total_backlogs: number;
  application_deadline: string;
  status: JobStatus;
  created_at: string;
  updated_at: string;
  skills: string[];
  eligible_department_names: string[];
  all_skills?: JobSkill[];
  eligible_departments?: JobDepartment[];
  company?: Company;
}

export interface JobCreate {
  title: string;
  description: string;
  employment_type: EmploymentType;
  work_mode: WorkMode;
  location: string;
  salary_range?: string;
  ctc_lpa?: number;
  base_salary_lpa?: number;
  stipend_monthly?: number;
  min_cgpa: number;
  target_graduation_year?: number;
  max_active_backlogs: number;
  max_total_backlogs: number;
  application_deadline: string;
  status?: JobStatus;
  institution_id?: number;
  required_skills?: string[];
  preferred_skills?: string[];
  eligible_department_ids?: number[];
}

export interface JobUpdate {
  title?: string;
  description?: string;
  employment_type?: EmploymentType;
  work_mode?: WorkMode;
  location?: string;
  salary_range?: string;
  ctc_lpa?: number;
  base_salary_lpa?: number;
  stipend_monthly?: number;
  min_cgpa?: number;
  target_graduation_year?: number;
  max_active_backlogs?: number;
  max_total_backlogs?: number;
  application_deadline?: string;
  status?: JobStatus;
  institution_id?: number;
  required_skills?: string[];
  preferred_skills?: string[];
  eligible_department_ids?: number[];
}

export interface CriterionEvaluation {
  criterion: string;
  required: any;
  student_value: any;
  passed: boolean;
  message: string;
}

export interface JobEligibilityResult {
  job_id: number;
  job_title: string;
  student_id: number;
  student_name: string;
  is_eligible: boolean;
  reasons: string[];
  passed_criteria?: string[];
  failed_criteria?: string[];
  criteria: Record<string, CriterionEvaluation>;
}

// ==========================================
// Phase 5: Placement Intelligence Types
// ==========================================

export interface ScoreBreakdown {
  skills: number;
  academics: number;
  projects: number;
  experience: number;
  certifications: number;
}

export interface JobMatchEvaluationResponse {
  job_id: number;
  job_title: string;
  company_name: string;
  student_id: number;
  student_name: string;
  is_eligible: boolean;
  reasons: string[];
  passed_criteria: string[];
  failed_criteria: string[];
  criteria: Record<string, CriterionEvaluation>;
  compatibility_score: number;
  score_breakdown: ScoreBreakdown;
  matched_skills: string[];
  missing_mandatory_skills: string[];
  recommended_skills: string[];
  no_skill_requirements: boolean;
  match_rationale: string;
}

export interface JobRecommendationCard {
  job_id: number;
  title: string;
  company_name: string;
  company_industry?: string | null;
  location: string;
  employment_type: EmploymentType;
  work_mode: WorkMode;
  salary_range?: string | null;
  ctc_lpa?: number | null;
  application_deadline: string;
  is_eligible: boolean;
  compatibility_score: number;
  score_breakdown: ScoreBreakdown;
  matched_skills: string[];
  missing_mandatory_skills: string[];
  recommended_skills: string[];
  reasons: string[];
  relevance_tier?: 'directly_relevant' | 'interdisciplinary' | 'open_to_all' | 'not_relevant';
  relevance_reason?: string | null;
  branch_match_status?: 'matched' | 'interdisciplinary' | 'open_to_all' | 'branch_mismatch';
  institution_id?: number | null;
  institution_name?: string | null;
}

export interface JobRecommendationListResponse {
  total_eligible: number;
  total_ineligible: number;
  eligible_jobs: JobRecommendationCard[];
  ineligible_jobs: JobRecommendationCard[];
}

export interface CandidateRankedCard {
  rank: number;
  student_id: number;
  user_id: number;
  student_name: string;
  roll_number: string;
  department_name?: string | null;
  cgpa: number;
  graduation_year: number;
  compatibility_score: number;
  score_breakdown: ScoreBreakdown;
  matched_skills: string[];
  match_rationale: string;
}

export interface CandidateIneligibleCard {
  student_id: number;
  user_id: number;
  student_name: string;
  roll_number: string;
  department_name?: string | null;
  cgpa?: number | null;
  graduation_year?: number | null;
  compatibility_score: number;
  failed_criteria: string[];
  reasons: string[];
}

export interface CandidateIntelligenceResponse {
  job_id: number;
  job_title: string;
  company_name: string;
  total_candidates: number;
  eligible_count: number;
  ineligible_count: number;
  ranked_eligible_candidates: CandidateRankedCard[];
  ineligible_candidates: CandidateIneligibleCard[];
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface CareerAdviceStructuredOutput {
  advice_type: string;
  answer: string;
  key_points: string[];
  suggested_next_actions: string[];
  relevant_skills_to_acquire: string[];
  limitations_or_missing_context?: string | null;
  disclaimer: string;
}

export interface CareerContextSummary {
  student_id: number;
  department_name?: string | null;
  graduation_year?: number | null;
  cgpa?: number | null;
  active_backlogs?: number | null;
  skills_count: number;
  projects_count: number;
  experiences_count: number;
  certifications_count: number;
  is_profile_complete: boolean;
  missing_sections: string[];
  job_id?: number | null;
  job_title?: string | null;
  company_name?: string | null;
  is_eligible?: boolean | null;
  compatibility_score?: number | null;
  matched_skills: string[];
  missing_mandatory_skills: string[];
}

export interface CareerAssistantResponse {
  success: boolean;
  data: CareerAdviceStructuredOutput;
  context_summary: CareerContextSummary;
  usage?: {
    provider: string;
    model: string;
    prompt_tokens?: number | null;
    completion_tokens?: number | null;
    total_tokens?: number | null;
    latency_ms: number;
  } | null;
}

export interface CareerPromptSuggestion {
  id: string;
  category: string;
  title: string;
  prompt: string;
  requires_job_context: boolean;
}

export interface StudentAcademicContext {
  student_id: number;
  user_id: number;
  full_name: string;
  email: string;
  roll_number?: string | null;
  institution_id: number;
  institution_name: string;
  official_department_id?: number | null;
  official_department_name?: string | null;
  official_department_code?: string | null;
  is_branch_verified: boolean;
  branch_verification_message?: string | null;
  graduation_year?: number | null;
  current_semester?: number | null;
  verified_cgpa: number;
  active_backlogs: number;
  total_backlogs: number;
  academic_status: string;
  career_interests: string[];
  approved_skills: string[];
  approved_projects: string[];
}

// =============================================================================
// AI Resume Feedback & Quality Scoring Types (Phase 7 Stage 5)
// =============================================================================

export type FeedbackSectionType =
  | 'structure'
  | 'ats_readability'
  | 'action_impact'
  | 'skills_organization'
  | 'project_depth'
  | 'job_alignment';

export type SectionStatus =
  | 'excellent'
  | 'good'
  | 'needs_work'
  | 'critical_gap'
  | 'not_assessed';

export type RewriteCategory =
  | 'verb_strengthening'
  | 'quantification_prompt'
  | 'conciseness'
  | 'ats_keyword_alignment'
  | 'grammar_and_tone'
  | 'structural_formatting';

export interface ResumeRewrittenSnippet {
  id: string;
  section: FeedbackSectionType;
  original_text: string;
  suggested_rewrite: string;
  rationale: string;
  evidence_reference: string;
  category: RewriteCategory;
  requires_student_metric: boolean;
}

export interface ResumeSectionEvaluation {
  section: FeedbackSectionType;
  score_awarded: number;
  max_score: number;
  status: SectionStatus;
  evidence_found: string[];
  deduction_reasons: string[];
  suggestions: string[];
  limitations_or_unavailable?: string | null;
}

export interface JobAlignmentFeedback {
  job_id: number;
  job_title: string;
  company_name: string;
  deterministic_compatibility_score?: number | null;
  matching_skills_in_resume: string[];
  skills_not_evidenced_mandatory: string[];
  skills_not_evidenced_preferred: string[];
  tailoring_advice: string[];
}

export interface ResumeFeedbackReport {
  overall_presentation_score: number;
  executive_summary: string;
  section_evaluations: ResumeSectionEvaluation[];
  rewritten_snippets: ResumeRewrittenSnippet[];
  priority_action_items: string[];
  job_alignment?: JobAlignmentFeedback | null;
  advisory_disclaimer: string;
}

export interface ResumeFeedbackRequest {
  job_id?: number | null;
  force_refresh?: boolean;
}

export interface ResumeFeedbackResponse {
  resume_id: number;
  file_name: string;
  file_hash: string;
  job_id?: number | null;
  job_title?: string | null;
  evaluated_at: string;
  is_cached: boolean;
  feedback: ResumeFeedbackReport;
  usage: {
    provider: string;
    model: string;
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
    latency_ms: number;
  };
}

export interface FeedbackTargetJob {
  id: number;
  title: string;
  company_name: string;
  employment_type: string;
  work_mode: string;
  location?: string | null;
  is_campus_exclusive: boolean;
}

// =============================================================================
// TPO Command Center & Admin Analytics Types
// =============================================================================

export interface DepartmentPlacementStat {
  name: string;
  dept_name: string;
  total: number;
  placed: number;
  placed_count: number;
}

export interface TpoOverviewResponse {
  total_cohort: number;
  target_batch: string;
  available_batches?: number[];
  placed_students: number;
  placement_rate: number;
  active_drives: number;
  published_jobs?: number;
  visiting_this_week: number;
  average_package_lpa: number;
  highest_package_lpa: number;
  top_open_ctc_lpa?: number;
  department_stats: DepartmentPlacementStat[];
}

export interface RecruiterOverviewApplication {
  id: number;
  job_id: number;
  student_id: number;
  resume_id: number;
  drive_id?: number | null;
  tpo_screening_status: string;
  current_status: string;
  compatibility_score_at_application: number;
  created_at: string;
  updated_at: string;
  job_title?: string | null;
  company_name?: string | null;
  drive_name?: string | null;
  student_name?: string | null;
  student_email?: string | null;
  student_roll_number?: string | null;
  student_department?: string | null;
}

export interface RecruiterOverviewResponse {
  company_id?: number | null;
  company_name?: string | null;
  active_jobs_count: number;
  total_applicants: number;
  shortlisted_count: number;
  offers_released: number;
  offers_accepted: number;
  recent_applications: RecruiterOverviewApplication[];
}

export interface SimulatedStudentSummary {
  student_id: number;
  name: string;
  email: string;
  roll_number: string;
  department: string;
  graduation_year: number;
  cgpa: number;
  active_backlogs: number;
  skills: string[];
}

export interface EligibilitySimulationRequest {
  target_batch?: number | null;
  min_cgpa: number;
  max_active_backlogs: number;
  max_total_backlogs?: number | null;
  department_codes?: string[] | null;
}

export interface EligibilitySimulationResponse {
  eligible_count: number;
  total_cohort_count: number;
  eligible_percentage: number;
  criteria_summary: {
    target_batch?: string | number;
    min_cgpa: number;
    max_active_backlogs: number;
    max_total_backlogs?: number | null;
    departments: string[];
  };
  matching_students: SimulatedStudentSummary[];
}

export interface UserRoleCount {
  role: string;
  count: number;
  percentage: number;
}

export interface AdminOverviewResponse {
  total_users: number;
  role_distribution: UserRoleCount[];
  students_count: number;
  recruiters_count: number;
  tpos_count: number;
  admins_count: number;
  institutions_count: number;
  departments_count: number;
  companies_count: number;
  jobs_count: number;
  drives_count: number;
  applications_count: number;
}

export interface TpoStudentRosterItem {
  student_id: number;
  user_id: number;
  full_name: string;
  email: string;
  roll_number: string;
  department_id?: number | null;
  department_code: string;
  department_name: string;
  is_branch_verified?: boolean;
  graduation_year: number;
  cgpa: number;
  active_backlogs: number;
  total_backlogs: number;
  is_placement_ready: boolean;
  skills: string[];
  approved_resumes_count: number;
  applications_count: number;
  placement_status: 'hired' | 'in_pipeline' | 'not_hired' | string;
  offer_state: string;
  hired_company?: string | null;
  hired_role?: string | null;
  hired_ctc_lpa?: number | null;
  active_pipeline_roles: string[];
}

export interface TpoStudentRosterResponse {
  total_students: number;
  hired_count: number;
  offer_accepted_count: number;
  offer_pending_count: number;
  in_pipeline_count: number;
  not_hired_count: number;
  unverified_count?: number;
  students: TpoStudentRosterItem[];
}

// =============================================================================
// AI Mock Interview & Assessment Studio Types
// =============================================================================

export type MockInterviewCategory =
  | 'technical'
  | 'hr'
  | 'behavioral'
  | 'aptitude'
  | 'project_based';

export type MockInterviewDifficulty = 'beginner' | 'intermediate' | 'advanced';

export type MockInterviewStatus = 'in_progress' | 'paused' | 'completed' | 'abandoned';

export interface MockInterviewTargetJob {
  id: number;
  title: string;
  company_name: string;
  employment_type: string;
  work_mode: string;
  location: string;
  compatibility_score?: number | null;
  is_eligible?: boolean | null;
}

export interface CriteriaBreakdownScores {
  technical_correctness: number;
  conceptual_understanding: number;
  problem_solving_approach: number;
  communication_clarity: number;
  answer_structure: number;
  relevance: number;
  project_knowledge?: number | null;
}

export interface MockInterviewAnswer {
  id: number;
  question_id: number;
  answer_text: string;
  selected_option_key?: string | null;
  input_mode: 'text' | 'voice' | string;
  response_time_seconds: number;
  submitted_at: string;
}

export interface MockInterviewQuestion {
  id: number;
  question_order: number;
  is_followup: boolean;
  parent_question_id?: number | null;
  category: MockInterviewCategory;
  topic: string;
  question_text: string;
  difficulty_hint: string;
  question_type?: 'open_ended' | 'mcq';
  options?: { key: string; text: string }[] | null;
  selected_option_key?: string | null;
  correct_option_key?: string | null;
  expected_key_points?: string[] | null;
  model_answer?: string | null;
  answer?: MockInterviewAnswer | null;
}

export interface MockInterviewQuestionEvaluationDetail {
  question_id?: number | null;
  question_order: number;
  question_text?: string | null;
  topic?: string | null;
  is_followup: boolean;
  student_answer?: string | null;
  selected_option_key?: string | null;
  correct_option_key?: string | null;
  is_correct?: boolean | null;
  score: number;
  criteria_scores: CriteriaBreakdownScores;
  feedback: string;
  strengths: string[];
  weaknesses: string[];
  improvement_tip: string;
  model_answer: string;
}

export interface MockInterviewEvaluation {
  id: number;
  session_id: number;
  overall_score: number;
  criteria_scores: CriteriaBreakdownScores;
  question_evaluations: MockInterviewQuestionEvaluationDetail[];
  strengths: string[];
  weaknesses: string[];
  suggested_improvements: string[];
  recommended_topics: string[];
  executive_summary: string;
  advisory_disclaimer: string;
  evaluated_at: string;
}

export interface MockInterviewSessionSummary {
  id: number;
  student_id: number;
  job_id?: number | null;
  job_title?: string | null;
  company_name?: string | null;
  target_role?: string | null;
  category: MockInterviewCategory;
  difficulty: MockInterviewDifficulty;
  question_format?: 'conversational' | 'mcq';
  status: MockInterviewStatus;
  question_count: number;
  total_questions_generated: number;
  answered_count: number;
  include_followups: boolean;
  time_limit_minutes?: number | null;
  elapsed_seconds: number;
  current_question_order: number;
  overall_score?: number | null;
  score_delta_from_previous?: number | null;
  ai_provider?: string | null;
  ai_model?: string | null;
  started_at: string;
  paused_at?: string | null;
  completed_at?: string | null;
}

export interface MockInterviewSessionDetail extends MockInterviewSessionSummary {
  context_snapshot?: Record<string, any> | null;
  questions: MockInterviewQuestion[];
  current_question?: MockInterviewQuestion | null;
  evaluation?: MockInterviewEvaluation | null;
  usage?: {
    provider: string;
    model: string;
    prompt_tokens?: number | null;
    completion_tokens?: number | null;
    total_tokens?: number | null;
    latency_ms: number;
  } | null;
}

export interface MockInterviewCreatePayload {
  category: MockInterviewCategory;
  difficulty: MockInterviewDifficulty;
  question_format?: 'conversational' | 'mcq';
  question_count: number;
  job_id?: number | null;
  target_role?: string | null;
  subject_focus?: string | null;
  time_limit_minutes?: number | null;
  include_followups: boolean;
}

export interface SubmitMockAnswerResponse {
  session: MockInterviewSessionDetail;
  submitted_answer: MockInterviewAnswer;
  followup_generated: boolean;
  followup_rationale?: string | null;
  next_question?: MockInterviewQuestion | null;
  ready_to_complete: boolean;
}

export interface MockInterviewTrendPoint {
  session_id: number;
  attempt_number: number;
  category: MockInterviewCategory;
  difficulty: MockInterviewDifficulty;
  overall_score: number;
  completed_at: string;
  target_label: string;
}

export interface MockInterviewCategoryStat {
  category: MockInterviewCategory;
  attempts: number;
  average_score: number;
  best_score: number;
  latest_score: number;
}

export interface MockInterviewAnalyticsResponse {
  total_sessions: number;
  completed_sessions: number;
  in_progress_or_paused_sessions: number;
  average_score?: number | null;
  best_score?: number | null;
  latest_score?: number | null;
  improvement_delta?: number | null;
  average_criteria?: CriteriaBreakdownScores | null;
  category_breakdown: MockInterviewCategoryStat[];
  score_trend: MockInterviewTrendPoint[];
  areas_requiring_improvement: string[];
  top_recommended_topics: string[];
  advisory_disclaimer: string;
}

// =============================================================================
// TASK 02: Placement Readiness Prediction & Historical Analytics Types
// =============================================================================

export type ReadinessCategory =
  | 'excellent_preparation'
  | 'placement_ready'
  | 'needs_improvement'
  | 'requires_significant_preparation';

export interface ReadinessCategoryDefinition {
  category: ReadinessCategory;
  label: string;
  min_score: number;
  max_score: number;
  summary: string;
  criteria_notes: string;
}

export interface ReadinessIndicatorWeights {
  verified_skills: number;
  project_portfolio: number;
  internship_experience: number;
  certifications: number;
  resume_quality: number;
  mock_interview_performance: number;
  aptitude_technical_assessment: number;
  profile_completeness: number;
}

export interface ReadinessIndicatorScore {
  key: string;
  label: string;
  weight: number;
  raw_score_pct: number;
  weighted_points: number;
  status: 'strong' | 'moderate' | 'developing' | 'missing_data';
  data_present: boolean;
  evidence_summary: string;
  limitation_note?: string | null;
}

export interface ReadOnlyAcademicSummary {
  cgpa?: number | null;
  active_backlogs: number;
  total_backlogs: number;
  graduation_year?: number | null;
  department_name?: string | null;
  is_placement_ready_flag: boolean;
  read_only_notice: string;
}

export interface ReadinessRecommendationItem {
  id: string;
  title: string;
  description: string;
  category: 'skills' | 'projects' | 'resume' | 'interview' | 'aptitude' | 'profile' | 'certifications';
  priority: 'high' | 'medium' | 'low';
  estimated_impact: string;
  completed: boolean;
  completed_at?: string | null;
}

export interface ReadinessSnapshot {
  id: number;
  student_id: number;
  job_id?: number | null;
  job_title?: string | null;
  target_role?: string | null;
  formula_version: string;
  overall_score: number;
  category: ReadinessCategory;
  category_label: string;
  score_delta_from_previous?: number | null;
  weights: Record<string, number>;
  indicators: ReadinessIndicatorScore[];
  academic_summary: ReadOnlyAcademicSummary;
  missing_data_fields: string[];
  limitations: string[];
  remaining_skill_gaps: string[];
  recommendations: ReadinessRecommendationItem[];
  completed_recommendations_count: number;
  total_recommendations_count: number;
  ai_provider?: string | null;
  ai_model?: string | null;
  transparency_notice: string;
  category_definitions: ReadinessCategoryDefinition[];
  calculated_at: string;
}

export interface ReadinessHistoryPoint {
  snapshot_id: number;
  formula_version: string;
  overall_score: number;
  category: ReadinessCategory;
  category_label: string;
  score_delta?: number | null;
  completed_recommendations_count: number;
  total_recommendations_count: number;
  remaining_skill_gaps_count: number;
  target_label: string;
  calculated_at: string;
}

export interface ReadinessHistoryResponse {
  total_snapshots: number;
  latest_score?: number | null;
  best_score?: number | null;
  net_change?: number | null;
  total_completed_recommendations: number;
  remaining_skill_gaps: string[];
  snapshots: ReadinessSnapshot[];
  trend: ReadinessHistoryPoint[];
  transparency_notice: string;
}

export interface JobReadinessCheckResponse {
  job_id?: number | null;
  target_label: string;
  company_name?: string | null;
  academic_eligibility_checked: boolean;
  is_academically_eligible?: boolean | null;
  eligibility_reasons: string[];
  eligibility_passed_criteria: string[];
  eligibility_failed_criteria: string[];
  skill_alignment_pct: number;
  deterministic_compatibility_score?: number | null;
  matched_skills: string[];
  missing_mandatory_skills: string[];
  missing_preferred_skills: string[];
  portfolio_gaps: string[];
  interview_preparation_gaps: string[];
  readiness_score: number;
  readiness_category: ReadinessCategory;
  readiness_category_label: string;
  recommendations: ReadinessRecommendationItem[];
  missing_data_fields: string[];
  limitations: string[];
  transparency_notice: string;
}

export interface TpoCategoryDistributionItem {
  category: ReadinessCategory;
  label: string;
  student_count: number;
  percentage: number;
}

export interface TpoDepartmentReadinessStat {
  department_id?: number | null;
  department_code: string;
  department_name: string;
  student_count: number;
  average_readiness_score: number;
  placement_ready_count: number;
  needs_attention_count: number;
}

export interface TpoBatchReadinessStat {
  graduation_year: number;
  student_count: number;
  average_readiness_score: number;
  excellent_or_ready_pct: number;
}

export interface TpoSkillCategoryStat {
  skill_category: string;
  students_with_skill_count: number;
  verified_skills_count: number;
  cohort_coverage_pct: number;
}

export interface TpoStudentReadinessRow {
  student_id: number;
  full_name: string;
  roll_number: string;
  department_code: string;
  department_name: string;
  graduation_year: number;
  cgpa?: number | null;
  active_backlogs: number;
  readiness_score: number;
  category: ReadinessCategory;
  category_label: string;
  verified_skills_count: number;
  projects_count: number;
  completed_mock_interviews: number;
  has_approved_resume: boolean;
  missing_data_count: number;
  data_completeness_note: string;
}

export interface TpoReadinessAnalyticsResponse {
  institution_id: number;
  formula_version: string;
  total_students_evaluated: number;
  cohort_average_readiness: number;
  placement_ready_or_above_count: number;
  placement_ready_or_above_pct: number;
  profiles_with_missing_data_count: number;
  category_distribution: TpoCategoryDistributionItem[];
  department_stats: TpoDepartmentReadinessStat[];
  batch_stats: TpoBatchReadinessStat[];
  skill_category_stats: TpoSkillCategoryStat[];
  available_departments: Array<{ id: string; label: string }>;
  available_batches: number[];
  available_skill_categories: string[];
  students: TpoStudentReadinessRow[];
  transparency_notice: string;
  category_definitions: ReadinessCategoryDefinition[];
}

// =============================================================================
// Smart Application & Recruitment Tracker Types (TASK 03)
// =============================================================================

export type ApplicationStageStatus =
  | 'applied'
  | 'under_review'
  | 'shortlisted'
  | 'interview_scheduled'
  | 'interviewed'
  | 'offered'
  | 'offer_accepted'
  | 'offer_declined'
  | 'rejected'
  | 'withdrawn';

export type TpoScreeningStageStatus = 'pending' | 'shortlisted' | 'rejected' | 'bypassed';

export type TrackerDecisionDomain = 'tpo_screening' | 'recruitment_lifecycle';

export type TrackerInterviewMode = 'virtual' | 'in_person';

export type TrackerInterviewStatus = 'scheduled' | 'completed' | 'cancelled' | 'no_show';

export type TrackerInterviewOutcome = 'pending' | 'passed' | 'failed' | 'on_hold';

export type PlacementNotificationCategory =
  | 'application_update'
  | 'interview_scheduled'
  | 'interview_update'
  | 'drive_announcement'
  | 'offer_extended'
  | 'action_required';

export interface ApplicationStatusHistoryItem {
  id: number;
  application_id: number;
  changed_by_user_id: number;
  created_at: string;
  decision_domain: TrackerDecisionDomain;
  from_status?: string | null;
  to_status: string;
  notes?: string | null;
}

export interface StudentInterviewRound {
  id: number;
  application_id: number;
  round_number: number;
  round_title: string;
  interview_mode: TrackerInterviewMode;
  meeting_link?: string | null;
  location?: string | null;
  scheduled_start_time: string;
  duration_minutes: number;
  interviewer_names?: string | null;
  instructions?: string | null;
  status: TrackerInterviewStatus;
  outcome: TrackerInterviewOutcome;
  cancellation_reason?: string | null;
  is_rescheduled: boolean;
  created_at: string;
  updated_at: string;
}

export interface StudentInterviewTrackingItem extends StudentInterviewRound {
  company_name?: string | null;
  job_title?: string | null;
  drive_name?: string | null;
  application_status: ApplicationStageStatus;
  is_upcoming: boolean;
  reschedule_note?: string | null;
}

export interface StudentInterviewListResponse {
  upcoming: StudentInterviewTrackingItem[];
  completed: StudentInterviewTrackingItem[];
  cancelled_or_other: StudentInterviewTrackingItem[];
  total: number;
}

export interface TrackerLatestUpdate {
  title: string;
  description?: string | null;
  timestamp: string;
  domain?: TrackerDecisionDomain | null;
  from_status?: string | null;
  to_status?: string | null;
}

export interface TrackerNextActivity {
  activity_type: 'interview' | 'offer_deadline' | 'application_review' | 'tpo_screening' | 'completed';
  title: string;
  scheduled_at?: string | null;
  description?: string | null;
  interview_id?: number | null;
  meeting_link?: string | null;
  location?: string | null;
}

export interface TrackerOfferDetail {
  company_name: string;
  role_title: string;
  package_lpa?: number | null;
  salary_range?: string | null;
  response_deadline?: string | null;
  status: ApplicationStageStatus;
  offer_notes?: string | null;
  can_respond: boolean;
}

export interface TrackerApplicationItem {
  id: number;
  job_id: number;
  student_id: number;
  resume_id: number;
  drive_id?: number | null;
  tpo_screening_status: TpoScreeningStageStatus;
  tpo_screened_by_user_id?: number | null;
  tpo_screened_at?: string | null;
  tpo_feedback?: string | null;
  current_status: ApplicationStageStatus;
  recruiter_decision_at?: string | null;
  compatibility_score_at_application: number;
  cover_letter?: string | null;
  withdrawn_at?: string | null;
  withdrawal_reason?: string | null;
  offer_deadline_at?: string | null;
  offer_package_lpa?: number | null;
  offer_notes?: string | null;
  created_at: string;
  updated_at: string;
  job_title?: string | null;
  company_name?: string | null;
  drive_name?: string | null;
  application_deadline?: string | null;
  job_location?: string | null;
  work_mode?: string | null;
  employment_type?: string | null;
  salary_range?: string | null;
  status_history: ApplicationStatusHistoryItem[];
  interviews: StudentInterviewRound[];
  latest_update: TrackerLatestUpdate;
  next_scheduled_activity: TrackerNextActivity;
  offer_details?: TrackerOfferDetail | null;
  upcoming_interviews_count: number;
  completed_interviews_count: number;
}

export interface TrackerSummaryStats {
  total_applications: number;
  active_count: number;
  upcoming_interviews_count: number;
  completed_interviews_count: number;
  pending_offers_count: number;
  accepted_offers_count: number;
  rejected_or_withdrawn_count: number;
}

export interface ApplicationTrackerResponse {
  items: TrackerApplicationItem[];
  total: number;
  skip: number;
  limit: number;
  summary: TrackerSummaryStats;
  unread_notifications_count: number;
}

export interface TrackerCalendarEvent {
  event_id: string;
  event_type: 'interview' | 'application_deadline' | 'offer_deadline' | 'drive_registration';
  title: string;
  subtitle?: string | null;
  company_name?: string | null;
  job_title?: string | null;
  application_id?: number | null;
  interview_id?: number | null;
  drive_id?: number | null;
  start_at: string;
  end_at?: string | null;
  status: string;
  meeting_link?: string | null;
  location?: string | null;
  instructions?: string | null;
  is_rescheduled: boolean;
}

export interface TrackerCalendarResponse {
  events: TrackerCalendarEvent[];
  total: number;
}

export interface PlacementNotification {
  id: number;
  recipient_user_id: number;
  sender_user_id?: number | null;
  category: PlacementNotificationCategory;
  title: string;
  message: string;
  related_application_id?: number | null;
  related_drive_id?: number | null;
  related_interview_id?: number | null;
  is_read: boolean;
  read_at?: string | null;
  idempotency_key?: string | null;
  created_at: string;
}

export interface NotificationPreference {
  user_id: number;
  interview_schedules: boolean;
  upcoming_interview_reminders: boolean;
  status_changes: boolean;
  offer_alerts: boolean;
  offer_deadline_reminders: boolean;
  placement_announcements: boolean;
  reminder_hours_before: number;
  updated_at?: string | null;
}

export interface NotificationPreferenceUpdate {
  interview_schedules?: boolean;
  upcoming_interview_reminders?: boolean;
  status_changes?: boolean;
  offer_alerts?: boolean;
  offer_deadline_reminders?: boolean;
  placement_announcements?: boolean;
  reminder_hours_before?: number;
}

// =============================================================================
// TASK 04: PLACEMENT PREPARATION ARENA TYPES
// =============================================================================

export type ArenaCategory =
  | 'dsa'
  | 'programming_fundamentals'
  | 'dbms'
  | 'operating_systems'
  | 'computer_networks'
  | 'oop'
  | 'aptitude_logical'
  | 'quantitative'
  | 'verbal'
  | 'technical_mcqs'
  | 'hr_behavioral'
  // Civil Engineering
  | 'civil_structures'
  | 'civil_concrete'
  | 'civil_geotech'
  | 'civil_surveying'
  | 'civil_transportation'
  | 'civil_hydraulics'
  | 'civil_environmental'
  | 'civil_construction'
  // Mechanical Engineering
  | 'mech_thermal'
  | 'mech_fluid'
  | 'mech_som'
  | 'mech_design'
  | 'mech_manufacturing'
  | 'mech_industrial'
  | 'mech_automobile'
  | 'mech_heat_transfer'
  // Electrical Engineering
  | 'eee_machines'
  | 'eee_power_systems'
  | 'eee_control_systems'
  | 'eee_power_electronics'
  | 'eee_circuits'
  | 'eee_measurements'
  // ECE
  | 'ece_digital'
  | 'ece_analog'
  | 'ece_communication'
  | 'ece_signals'
  | 'ece_vlsi'
  | 'ece_em_antennas'
  // Chemical Engineering
  | 'chem_reaction'
  | 'chem_mass_transfer'
  | 'chem_heat_transfer'
  | 'chem_thermodynamics'
  | 'chem_process_control'
  | 'chem_fluid_operations'
  // Mining Engineering
  | 'mine_methods'
  | 'mine_rock_mechanics'
  | 'mine_ventilation'
  | 'mine_drilling_blasting'
  | 'mine_surveying'
  | 'mine_machinery'
  // Petroleum Engineering
  | 'petro_reservoir'
  | 'petro_drilling'
  | 'petro_production'
  | 'petro_well_logging'
  | 'petro_natural_gas'
  | 'petro_offshore'
  // PIE
  | 'pie_manufacturing'
  | 'pie_operations_research'
  | 'pie_quality'
  | 'pie_work_study'
  | 'pie_ppc'
  | 'pie_metrology'
  // Structural Engineering
  | 'struct_advanced_analysis'
  | 'struct_concrete_design'
  | 'struct_steel_design'
  | 'struct_earthquake'
  | 'struct_foundations'
  | 'struct_dynamics'
  // Architecture & Planning
  | 'arch_design'
  | 'arch_construction'
  | 'arch_urban_planning'
  | 'arch_sustainability'
  | 'arch_services'
  | 'arch_landscape';

export type ArenaDifficulty = 'easy' | 'medium' | 'hard';
export type ArenaQuestionType = 'mcq' | 'coding' | 'behavioral';
export type ArenaAssessmentMode =
  | 'topic_practice'
  | 'timed_test'
  | 'company_prep'
  | 'institutional_test';
export type ArenaAttemptStatus = 'in_progress' | 'submitted' | 'expired';
export type ArenaCodeLanguage = 'python' | 'javascript' | 'java';

export interface ArenaCategorySummary {
  category: ArenaCategory;
  label: string;
  description: string;
  total_questions: number;
  mcq_count: number;
  coding_count: number;
  behavioral_count: number;
  easy_count: number;
  medium_count: number;
  hard_count: number;
  attempted_questions: number;
  accuracy_pct: number;
  avg_solving_seconds: number;
  proficiency_label: string;
  track_type?: 'common' | 'branch_core' | 'career_elective';
  branch_name?: string | null;
  is_recommended_for_student?: boolean;
}

export interface ArenaOptionItem {
  key: string;
  text: string;
}

export interface ArenaSampleTestCase {
  stdin: string;
  expected_stdout: string;
}

export interface ArenaQuestionView {
  id: number;
  title: string;
  prompt_text: string;
  category: ArenaCategory;
  difficulty: ArenaDifficulty;
  question_type: ArenaQuestionType;
  content_source: 'curated_original' | 'institutional_staff' | 'ai_generated_practice';
  company_tag?: string | null;
  provenance_notice: string;
  role_tags: string[];
  options: ArenaOptionItem[];
  starter_code: Record<string, string>;
  sample_test_cases: ArenaSampleTestCase[];
  expected_time_seconds: number;
  max_marks: number;
  institution_id?: number | null;
  correct_option_key?: string | null;
  explanation_text?: string | null;
  sample_solution_text?: string | null;
}

export interface ArenaAssessmentSummary {
  id: number;
  title: string;
  description: string;
  mode: ArenaAssessmentMode;
  category?: ArenaCategory | null;
  difficulty: ArenaDifficulty;
  company_name_style?: string | null;
  provenance_notice: string;
  duration_minutes: number;
  question_count: number;
  passing_percentage: number;
  institution_id?: number | null;
  department_id?: number | null;
  department_name?: string | null;
  target_graduation_year?: number | null;
  is_published: boolean;
  starts_at?: string | null;
  ends_at?: string | null;
}

export interface SandboxTestCaseResult {
  test_index: number;
  is_sample: boolean;
  passed: boolean;
  stdin?: string | null;
  expected_stdout?: string | null;
  actual_stdout: string;
  stderr: string;
  runtime_ms: number;
  status: string;
}

export interface SandboxRunResponse {
  language: string;
  sandbox_provider: string;
  isolated_execution: boolean;
  all_passed: boolean;
  passed_count: number;
  total_count: number;
  compile_error?: string | null;
  security_violation?: string | null;
  custom_stdout?: string | null;
  custom_stderr?: string | null;
  runtime_ms: number;
  test_results: SandboxTestCaseResult[];
}

export interface ArenaAttemptAnswerView {
  id: number;
  question_id: number;
  question_order: number;
  selected_option_key?: string | null;
  submitted_code?: string | null;
  code_language?: string | null;
  behavioral_response?: string | null;
  is_correct: boolean;
  score_awarded: number;
  time_spent_seconds: number;
  execution_result?: SandboxRunResponse | null;
  ai_feedback?: Record<string, any> | null;
  answered_at: string;
}

export interface ArenaQuestionSlot {
  question_order: number;
  answered: boolean;
  question: ArenaQuestionView;
  answer?: ArenaAttemptAnswerView | null;
}

export interface ArenaAttemptSummary {
  id: number;
  assessment_id?: number | null;
  title: string;
  mode: ArenaAssessmentMode;
  category?: ArenaCategory | null;
  difficulty?: ArenaDifficulty | null;
  company_name_style?: string | null;
  status: ArenaAttemptStatus;
  time_limit_seconds?: number | null;
  started_at: string;
  expires_at?: string | null;
  submitted_at?: string | null;
  elapsed_seconds: number;
  total_questions: number;
  attempted_count: number;
  correct_count: number;
  accuracy_pct: number;
  score_pct: number;
}

export interface ArenaAttemptDetail extends ArenaAttemptSummary {
  provenance_notice: string;
  questions: ArenaQuestionSlot[];
}

export interface ArenaSubmitAnswerResponse {
  attempt: ArenaAttemptSummary;
  answer: ArenaAttemptAnswerView;
  immediate_review_unlocked: boolean;
  correct_option_key?: string | null;
  explanation_text?: string | null;
  sample_solution_text?: string | null;
}

export interface ArenaTopicProficiencyItem {
  category: ArenaCategory;
  label: string;
  questions_attempted: number;
  correct_count: number;
  incorrect_count: number;
  accuracy_pct: number;
  avg_solving_seconds: number;
  proficiency_band: string;
}

export interface ArenaTrendPoint {
  attempt_id: number;
  title: string;
  mode: ArenaAssessmentMode;
  submitted_at: string;
  score_pct: number;
  accuracy_pct: number;
  questions_attempted: number;
}

export interface ArenaPerformanceAnalytics {
  total_attempts: number;
  completed_attempts: number;
  total_questions_attempted: number;
  total_correct: number;
  total_incorrect: number;
  overall_accuracy_pct: number;
  avg_solving_time_seconds: number;
  coding_problems_solved: number;
  topic_proficiency: ArenaTopicProficiencyItem[];
  recent_attempts: ArenaAttemptSummary[];
  improvement_trend: ArenaTrendPoint[];
  advisory_note: string;
}

export interface ArenaRecommendedExercise {
  recommendation_id: string;
  title: string;
  reason: string;
  source_signal: 'skill_gap' | 'weak_category' | 'target_job' | 'career_roadmap';
  category: ArenaCategory;
  category_label: string;
  difficulty: ArenaDifficulty;
  suggested_question_ids: number[];
  target_role?: string | null;
}

export interface ArenaPersonalizedPracticeResponse {
  target_roles_considered: string[];
  missing_skills_detected: string[];
  weak_categories: ArenaCategory[];
  recommendations: ArenaRecommendedExercise[];
  ai_study_tip?: string | null;
  advisory_notice: string;
}

export interface ArenaUserPreference {
  leaderboard_opt_in: boolean;
  anonymize_name: boolean;
  preferred_language: ArenaCodeLanguage;
  privacy_notice: string;
}

export interface ArenaLeaderboardEntry {
  rank: number;
  display_name: string;
  is_current_user: boolean;
  is_anonymized: boolean;
  department_name?: string | null;
  graduation_year?: number | null;
  questions_attempted: number;
  accuracy_pct: number;
  avg_score_pct: number;
  completed_attempts: number;
}

export interface ArenaLeaderboardResponse {
  scope: 'department' | 'batch' | 'institution';
  department_name?: string | null;
  graduation_year?: number | null;
  viewer_opted_in: boolean;
  total_opted_in_participants: number;
  privacy_guarantee: string;
  entries: ArenaLeaderboardEntry[];
}

export interface ArenaTpoAssessmentAnalyticsItem {
  assessment_id: number;
  title: string;
  category?: ArenaCategory | null;
  difficulty: ArenaDifficulty;
  is_published: boolean;
  department_name?: string | null;
  target_graduation_year?: number | null;
  total_attempts: number;
  submitted_attempts: number;
  avg_score_pct: number;
  avg_accuracy_pct: number;
  pass_rate_pct: number;
}

export interface ArenaTpoAnalyticsResponse {
  institution_id: number;
  total_published_assessments: number;
  total_institutional_questions: number;
  participating_students: number;
  total_submitted_attempts: number;
  institution_avg_score_pct: number;
  institution_avg_accuracy_pct: number;
  category_performance: ArenaTopicProficiencyItem[];
  assessment_breakdown: ArenaTpoAssessmentAnalyticsItem[];
}

export interface ArenaStudentPerformanceItem {
  student_id: number;
  user_id: number;
  full_name: string;
  roll_number: string;
  department_id?: number | null;
  department_name?: string | null;
  graduation_year?: number | null;
  cgpa?: number | null;
  total_attempts: number;
  completed_attempts: number;
  questions_attempted: number;
  questions_correct: number;
  overall_accuracy_pct: number;
  avg_score_pct: number;
  top_category?: string | null;
  weakest_category?: string | null;
  last_active_at?: string | null;
  latest_attempt_title?: string | null;
}

export interface ArenaTpoStudentRosterResponse {
  institution_id: number;
  total_students: number;
  participating_students: number;
  average_accuracy_pct: number;
  students: ArenaStudentPerformanceItem[];
}

export interface IntelligenceFilterOptionNamed {
  id: number;
  name: string;
  code?: string;
}

export interface IntelligenceFilterOptions {
  academic_years: string[];
  graduation_batches: number[];
  departments: IntelligenceFilterOptionNamed[];
  companies: IntelligenceFilterOptionNamed[];
  job_categories: string[];
  employment_types: string[];
}

export interface AppliedIntelligenceFilters {
  institution_id: number;
  academic_year?: string | null;
  graduation_year?: number | null;
  department_id?: number | null;
  company_id?: number | null;
  job_category?: string | null;
  employment_type?: string | null;
}

export interface PlacementOverviewStats {
  total_registered_students: number;
  total_eligible_students: number;
  total_placed_students: number;
  students_in_pipeline: number;
  students_not_yet_placed: number;
  total_active_drives: number;
  total_participating_companies: number;
  total_published_jobs: number;
  total_offers_released: number;
  total_accepted_offers: number;
  total_declined_offers: number;
  pending_offers: number;
  placement_rate_pct: number;
  offer_acceptance_rate_pct: number;
  average_package_lpa?: number | null;
  median_package_lpa?: number | null;
  highest_package_lpa?: number | null;
  offers_missing_package_count: number;
}

export interface DepartmentAnalyticsItem {
  department_id: number;
  department_code: string;
  department_name: string;
  eligible_students: number;
  placed_students: number;
  in_pipeline_students: number;
  unplaced_students: number;
  placement_rate_pct: number;
  offers_accepted: number;
  average_package_lpa?: number | null;
  highest_package_lpa?: number | null;
  top_demanded_skills: string[];
  skill_gaps: string[];
}

export interface YearDepartmentComparisonItem {
  academic_year: string;
  graduation_year: number;
  department_code: string;
  department_name: string;
  eligible_students: number;
  placed_students: number;
  placement_rate_pct: number;
  average_package_lpa?: number | null;
}

export interface HistoricalTrendPoint {
  academic_year: string;
  graduation_year: number;
  eligible_students: number;
  placed_students: number;
  placement_rate_pct: number;
  yoy_placement_growth_pct_pts?: number | null;
  participating_companies: number;
  offers_released: number;
  offers_accepted: number;
  offers_declined: number;
  offer_conversion_rate_pct: number;
  average_package_lpa?: number | null;
  median_package_lpa?: number | null;
  highest_package_lpa?: number | null;
}

export interface SalaryDistributionBucket {
  bucket_label: string;
  min_lpa: number;
  max_lpa?: number | null;
  accepted_offer_count: number;
  percentage: number;
}

export interface RecruitmentFunnelStage {
  stage_key: string;
  stage_label: string;
  application_count: number;
  conversion_from_applied_pct: number;
}

export interface ForecastMetricEstimate {
  metric_key: string;
  metric_label: string;
  unit: string;
  target_period: string;
  projected_value: number;
  ci_lower_95: number;
  ci_upper_95: number;
  sample_size: number;
  r_squared?: number | null;
  methodology: string;
  confidence_level: 'high' | 'moderate' | 'low' | 'exploratory';
  limitations: string[];
}

export interface DepartmentForecastItem {
  department_code: string;
  department_name: string;
  latest_placement_rate_pct: number;
  projected_placement_rate_pct: number;
  ci_lower_95: number;
  ci_upper_95: number;
  projected_placed_students: number;
  sample_size: number;
  trend_direction: 'upward' | 'stable' | 'downward' | 'insufficient_history';
  confidence_level: 'high' | 'moderate' | 'low' | 'exploratory';
}

export interface ForecastingSection {
  target_academic_year: string;
  target_graduation_year: number;
  overall_sample_years: number;
  placement_forecast: ForecastMetricEstimate;
  company_participation_forecast: ForecastMetricEstimate;
  offer_volume_forecast: ForecastMetricEstimate;
  department_forecasts: DepartmentForecastItem[];
  disclaimer: string;
}

export interface SkillDemandStat {
  skill_name: string;
  job_postings_count: number;
  mandatory_count: number;
  accepted_offer_count: number;
  outcome_success_rate_pct: number;
  growth_delta_pct?: number | null;
}

export interface DepartmentSkillGapItem {
  department_code: string;
  department_name: string;
  demanded_skills: string[];
  verified_coverage_pct: number;
  missing_or_low_supply_skills: string[];
}

export interface SkillDemandIntelligence {
  most_requested_skills: SkillDemandStat[];
  emerging_skills: SkillDemandStat[];
  winning_outcome_skills: SkillDemandStat[];
  department_skill_gaps: DepartmentSkillGapItem[];
}

export interface DataCompletenessSummary {
  students_missing_department: number;
  offers_missing_package: number;
  jobs_missing_ctc: number;
  applications_without_drive: number;
  historical_years_available: number;
  warnings: string[];
}

export interface TpoPlacementIntelligenceResponse {
  generated_at: string;
  cache_hit: boolean;
  filters_applied: AppliedIntelligenceFilters;
  filter_options: IntelligenceFilterOptions;
  policy_summary: string;
  overview: PlacementOverviewStats;
  department_analytics: DepartmentAnalyticsItem[];
  year_department_comparisons: YearDepartmentComparisonItem[];
  historical_trends: HistoricalTrendPoint[];
  salary_distribution: SalaryDistributionBucket[];
  recruitment_funnel: RecruitmentFunnelStage[];
  forecasting: ForecastingSection;
  skill_intelligence: SkillDemandIntelligence;
  data_completeness: DataCompletenessSummary;
}

// =============================================================================
// TASK 06: Complete Placement Drive Management Types
// =============================================================================

export type DriveLifecyclePhase =
  | 'draft'
  | 'scheduled'
  | 'registration_open'
  | 'registration_closed'
  | 'ongoing'
  | 'completed'
  | 'cancelled';

export type DriveMode = 'on_campus' | 'virtual' | 'hybrid';

export type DriveActivityType =
  | 'pre_placement_talk'
  | 'company_presentation'
  | 'online_assessment'
  | 'offline_assessment'
  | 'interview_round'
  | 'other';

export type DriveActivityStatus = 'scheduled' | 'in_progress' | 'completed' | 'cancelled';

export type DriveAttendanceStatus = 'present' | 'absent' | 'late' | 'excused';

export type DriveAnnouncementAudience =
  | 'all_registered'
  | 'eligible_students'
  | 'shortlisted_candidates'
  | 'specific_job_applicants';

export interface PlacementDriveJobSummary {
  id: number;
  drive_id: number;
  job_id: number;
  is_active: boolean;
  removed_at?: string | null;
  created_at: string;
  job_title?: string | null;
  company_name?: string | null;
  employment_type?: string | null;
  location?: string | null;
}

export interface PlacementDrive {
  id: number;
  institution_id: number;
  created_by_user_id: number;
  name: string;
  academic_year: string;
  target_graduation_year: number;
  registration_start_date: string;
  registration_end_date: string;
  drive_mode: DriveMode;
  status: 'draft' | 'upcoming' | 'ongoing' | 'completed' | 'cancelled';
  description?: string | null;
  guidelines?: string | null;
  lifecycle_phase?: DriveLifecyclePhase | null;
  drive_start_date?: string | null;
  drive_end_date?: string | null;
  venue_location?: string | null;
  instructions?: string | null;
  required_documents: string[];
  target_graduation_batches: number[];
  participating_company_ids: number[];
  eligible_department_ids: number[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
  total_jobs: number;
  total_applications: number;
}

export interface PlacementDriveDetail extends PlacementDrive {
  jobs: PlacementDriveJobSummary[];
}

export interface PlacementDriveCreatePayload {
  name: string;
  academic_year: string;
  target_graduation_year: number;
  registration_start_date: string;
  registration_end_date: string;
  drive_mode: DriveMode;
  description?: string | null;
  guidelines?: string | null;
  lifecycle_phase?: DriveLifecyclePhase;
  drive_start_date?: string | null;
  drive_end_date?: string | null;
  venue_location?: string | null;
  instructions?: string | null;
  required_documents?: string[];
  target_graduation_batches?: number[];
  participating_company_ids?: number[];
  eligible_department_ids?: number[];
  job_ids?: number[];
}

export interface PlacementDriveUpdatePayload {
  name?: string;
  academic_year?: string;
  target_graduation_year?: number;
  registration_start_date?: string;
  registration_end_date?: string;
  drive_mode?: DriveMode;
  status?: 'draft' | 'upcoming' | 'ongoing' | 'completed' | 'cancelled';
  lifecycle_phase?: DriveLifecyclePhase;
  description?: string | null;
  guidelines?: string | null;
  drive_start_date?: string | null;
  drive_end_date?: string | null;
  venue_location?: string | null;
  instructions?: string | null;
  required_documents?: string[];
  target_graduation_batches?: number[];
  participating_company_ids?: number[];
  eligible_department_ids?: number[];
  is_active?: boolean;
}

export interface DriveFormCompanyOption {
  id: number;
  name: string;
  industry: string;
  is_verified: boolean;
  institution_id?: number | null;
}

export interface DriveFormJobOption {
  id: number;
  company_id: number;
  company_name: string;
  title: string;
  employment_type: string;
  status: string;
  location: string;
  min_cgpa: number;
  target_graduation_year?: number | null;
  application_deadline: string;
  eligible_department_ids: number[];
}

export interface DriveFormDepartmentOption {
  id: number;
  code: string;
  name: string;
}

export interface DriveFormCoordinatorOption {
  id: number;
  full_name: string;
  email: string;
  role: string;
}

export interface DriveFormOptionsResponse {
  institution_id: number;
  companies: DriveFormCompanyOption[];
  jobs: DriveFormJobOption[];
  departments: DriveFormDepartmentOption[];
  coordinators: DriveFormCoordinatorOption[];
  graduation_batches: number[];
}

export interface DriveDashboardJobBreakdown {
  job_id: number;
  title: string;
  company_name: string;
  applications_count: number;
  shortlisted_count: number;
  interview_count: number;
  offered_count: number;
  accepted_count: number;
}

export interface DriveDashboardResponse {
  drive_id: number;
  drive_name: string;
  institution_id: number;
  academic_year: string;
  lifecycle_phase: DriveLifecyclePhase;
  allowed_next_phases: DriveLifecyclePhase[];
  total_registered_students: number;
  eligible_students: number;
  ineligible_students: number;
  applications_received: number;
  shortlisted_candidates: number;
  interview_scheduled_count: number;
  interview_completed_count: number;
  offers_released: number;
  final_placements: number;
  activities_total: number;
  activities_completed: number;
  announcements_count: number;
  job_breakdown: DriveDashboardJobBreakdown[];
}

export interface DriveRegistrationItem {
  id: number;
  drive_id: number;
  student_id: number;
  user_id?: number | null;
  student_name: string;
  roll_number: string;
  department_code?: string | null;
  department_name?: string | null;
  graduation_year: number;
  cgpa: number;
  active_backlogs: number;
  registered_by_user_id: number;
  registration_source: string;
  status: 'registered' | 'withdrawn' | 'cancelled';
  eligibility_passed: boolean;
  eligibility_snapshot: Record<string, unknown>;
  notes?: string | null;
  registered_at: string;
}

export interface DriveCandidateItem {
  student_id: number;
  user_id: number;
  full_name: string;
  email: string;
  roll_number: string;
  department_code?: string | null;
  department_name?: string | null;
  graduation_year: number;
  cgpa: number;
  active_backlogs: number;
  is_eligible: boolean;
  ineligible_reasons: string[];
  eligible_job_ids: number[];
  eligible_job_titles: string[];
  is_registered: boolean;
  registration_status?: 'registered' | 'withdrawn' | 'cancelled' | null;
  application_count: number;
  tpo_screening_statuses: string[];
  latest_application_status?: string | null;
  final_outcome?: string | null;
}

export interface DriveCandidatesResponse {
  drive_id: number;
  eligible_candidates: DriveCandidateItem[];
  ineligible_audit_records: DriveCandidateItem[];
}

export interface DriveApplicationItem {
  id: number;
  job_id: number;
  student_id: number;
  resume_id: number;
  drive_id?: number | null;
  tpo_screening_status: 'pending' | 'shortlisted' | 'rejected' | 'bypassed';
  tpo_screened_by_user_id?: number | null;
  tpo_screened_at?: string | null;
  tpo_feedback?: string | null;
  current_status: string;
  compatibility_score_at_application?: number | null;
  offer_package_lpa?: number | null;
  offer_deadline_at?: string | null;
  created_at: string;
  updated_at: string;
  job_title?: string | null;
  company_name?: string | null;
  drive_name?: string | null;
  student_name?: string | null;
  student_email?: string | null;
  student_roll_number?: string | null;
  student_department?: string | null;
}

export interface DriveActivityItem {
  id: number;
  drive_id: number;
  job_id?: number | null;
  job_title?: string | null;
  company_id?: number | null;
  company_name?: string | null;
  coordinator_user_id?: number | null;
  coordinator_name: string;
  coordinator_contact?: string | null;
  title: string;
  activity_type: DriveActivityType;
  mode: DriveMode;
  venue?: string | null;
  meeting_link?: string | null;
  scheduled_start: string;
  scheduled_end: string;
  description?: string | null;
  status: DriveActivityStatus;
  present_count: number;
  absent_count: number;
  late_count: number;
  excused_count: number;
  created_at: string;
}

export interface DriveActivityCreatePayload {
  title: string;
  activity_type: DriveActivityType;
  mode: DriveMode;
  scheduled_start: string;
  scheduled_end: string;
  venue?: string | null;
  meeting_link?: string | null;
  description?: string | null;
  job_id?: number | null;
  company_id?: number | null;
  coordinator_user_id?: number | null;
  coordinator_name: string;
  coordinator_contact?: string | null;
}

export interface DriveAttendanceRecord {
  id: number;
  activity_id: number;
  drive_id: number;
  student_id: number;
  student_name: string;
  roll_number: string;
  department_code?: string | null;
  attendance_status: DriveAttendanceStatus;
  marked_by_user_id: number;
  marked_by_name: string;
  marked_at: string;
  remarks?: string | null;
}

export interface DriveAttendanceAuditItem {
  id: number;
  attendance_id: number;
  activity_id: number;
  student_id: number;
  student_name: string;
  roll_number: string;
  changed_by_user_id: number;
  changed_by_name: string;
  previous_status?: string | null;
  new_status: string;
  remarks?: string | null;
  changed_at: string;
}

export interface DriveAnnouncementItem {
  id: number;
  drive_id: number;
  sender_user_id: number;
  sender_name: string;
  job_id?: number | null;
  title: string;
  message: string;
  target_audience: DriveAnnouncementAudience;
  recipients_count: number;
  created_at: string;
}

export interface DriveActivityAttendanceSummary {
  activity_id: number;
  title: string;
  activity_type: string;
  scheduled_start: string;
  status: string;
  coordinator_name: string;
  total_marked: number;
  present_count: number;
  absent_count: number;
  late_count: number;
  excused_count: number;
  attendance_rate_pct: number;
}

export interface DriveReportResponse {
  generated_at: string;
  drive: Record<string, unknown>;
  dashboard: DriveDashboardResponse;
  attendance_summary: DriveActivityAttendanceSummary[];
  registrations_sample_count: number;
  eligible_sample_count: number;
  ineligible_sample_count: number;
  placed_outcomes: Array<{
    application_id: number;
    student_id: number;
    student_name: string;
    roll_number: string;
    department?: string | null;
    job_title?: string | null;
    company_name?: string | null;
    package_lpa?: number | null;
    status: string;
  }>;
}

// =============================================================================
// Automated Placement Report Generator Types (TASK 07)
// =============================================================================

export type ReportType =
  | 'overall_institutional'
  | 'academic_year_wise'
  | 'department_wise'
  | 'graduation_batch'
  | 'company_wise'
  | 'placement_drive'
  | 'student_placement_status'
  | 'salary_package_analysis'
  | 'unplaced_students'
  | 'offer_acceptance';

export type ReportFormat = 'pdf' | 'xlsx' | 'csv' | 'json';

export type ReportStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface ReportFilterParams {
  academic_year?: string;
  graduation_batch?: number;
  graduation_year?: number;
  department_id?: number;
  department?: string;
  company_id?: number;
  drive_id?: number;
  application_status?: string;
  start_date?: string;
  end_date?: string;
  min_package_lpa?: number;
  max_package_lpa?: number;
}

export interface ReportGenerateRequest {
  report_type: ReportType;
  file_format?: ReportFormat;
  title?: string;
  description?: string;
  filters?: ReportFilterParams;
  notes?: string;
}

export interface ReportSummaryKPIs {
  total_registered_students?: number;
  total_eligible_students: number;
  total_placed_students: number;
  total_unplaced_students?: number;
  students_not_yet_placed?: number;
  placement_rate_pct: number;
  active_in_pipeline_students?: number;
  students_in_pipeline?: number;
  total_companies?: number;
  total_participating_companies?: number;
  total_active_drives?: number;
  total_placement_drives?: number;
  total_published_jobs?: number;
  total_offers_released: number;
  total_accepted_offers?: number;
  total_offers_accepted?: number;
  total_declined_offers?: number;
  pending_offers?: number;
  offer_acceptance_rate_pct: number;
  multiple_offers_count?: number;
  highest_package_lpa?: number | null;
  average_package_lpa?: number | null;
  median_package_lpa?: number | null;
  total_applications?: number;
}

export interface ReportDepartmentStat {
  department_id?: number;
  department_code?: string;
  department_name?: string;
  department?: string;
  total_students?: number;
  eligible_students: number;
  placed_students: number;
  placement_rate_pct: number;
  highest_package_lpa?: number | null;
  average_package_lpa?: number | null;
  offers_accepted?: number;
  total_offers?: number;
  top_recruiting_companies?: string[];
}

export interface ReportFunnelStage {
  stage: string;
  label?: string;
  display_name?: string;
  count: number;
  percentage?: number;
  conversion_from_applied_pct?: number;
}

export interface ReportDataPayload {
  institution_id: number;
  institution_name: string;
  report_type: ReportType;
  title: string;
  generated_at: string;
  generated_by_user_id?: number;
  generated_by_name?: string;
  filters_applied: Record<string, unknown>;
  summary_kpis: ReportSummaryKPIs;
  department_stats: ReportDepartmentStat[];
  recruitment_funnel: ReportFunnelStage[];
  table_headers?: string[];
  table_rows?: Array<Record<string, unknown>>;
  rows?: Array<Record<string, unknown>>;
  row_count?: number;
  metadata?: Record<string, unknown>;
}

export interface PlacementReportResponse {
  id: number;
  institution_id: number;
  generated_by_user_id?: number | null;
  generated_by_name?: string | null;
  created_by_user_id?: number | null;
  creator_name?: string | null;
  report_type: ReportType;
  report_type_label?: string | null;
  file_format: ReportFormat;
  status: ReportStatus;
  title: string;
  description?: string | null;
  parameters?: Record<string, unknown>;
  filters?: Record<string, unknown>;
  file_size_bytes?: number | null;
  download_url?: string | null;
  error_message?: string | null;
  created_at: string;
  completed_at?: string | null;
  summary_snapshot?: Record<string, unknown> | null;
}

export interface ReportOptionItem {
  id: number | string;
  label: string;
  description?: string | null;
  secondary?: string;
}

export interface ReportFormOptionsResponse {
  academic_years: string[];
  graduation_batches: number[];
  departments: ReportOptionItem[];
  companies: ReportOptionItem[];
  drives: ReportOptionItem[];
  application_statuses: ReportOptionItem[];
  report_types?: ReportOptionItem[];
  file_formats?: ReportOptionItem[];
  institution_id?: number;
  institution_name?: string;
}

// ==========================================
// TASK 08: CANDIDATE EVALUATION WORKSPACE TYPES
// ==========================================

export type EvaluationStage =
  | 'technical'
  | 'hr'
  | 'communication'
  | 'problem_solving'
  | 'project_discussion'
  | 'overall';

export type EvaluationRecommendation =
  | 'strong_hire'
  | 'hire'
  | 'hold'
  | 'no_hire'
  | 'strong_no_hire';

export type CandidateNoteCategory =
  | 'general'
  | 'interview'
  | 'compensation'
  | 'decision'
  | 'reference';

export interface CandidateEvaluationFormCriteria {
  technical_proficiency?: number | null;
  problem_solving?: number | null;
  communication?: number | null;
  project_depth?: number | null;
  cultural_fit?: number | null;
}

export interface CandidateEvaluationCreate {
  interview_id?: number | null;
  stage: EvaluationStage;
  technical_proficiency?: number | null;
  problem_solving?: number | null;
  communication?: number | null;
  project_depth?: number | null;
  cultural_fit?: number | null;
  overall_rating: number; // 1.0 to 5.0
  recommendation: EvaluationRecommendation;
  written_feedback: string;
  strengths?: string[];
  weaknesses?: string[];
}

export interface CandidateEvaluationResponse {
  id: number;
  application_id: number;
  interview_id?: number | null;
  interviewer_user_id: number;
  interviewer_name: string;
  stage: EvaluationStage;
  technical_proficiency?: number | null;
  problem_solving?: number | null;
  communication?: number | null;
  project_depth?: number | null;
  cultural_fit?: number | null;
  overall_rating: number;
  recommendation: EvaluationRecommendation;
  written_feedback: string;
  strengths: string[];
  weaknesses: string[];
  created_at: string;
  updated_at: string;
}

export interface CandidateNoteCreate {
  category?: CandidateNoteCategory;
  content: string;
  is_pinned?: boolean;
}

export interface CandidateNoteResponse {
  id: number;
  application_id: number;
  author_user_id: number;
  author_name: string;
  category: CandidateNoteCategory;
  content: string;
  is_pinned: boolean;
  created_at: string;
  updated_at: string;
}

export interface EligibilityCheckCriterion {
  criterion: string;
  status: 'passed' | 'failed' | 'not_applicable';
  candidate_value: string;
  required_value: string;
  details?: string | null;
}

export interface CandidateEligibilityChecklist {
  is_eligible: boolean;
  criteria: EligibilityCheckCriterion[];
  reasons: string[];
}

export interface CandidateAcademicInfo {
  cgpa: number;
  tenth_percentage?: number | null;
  twelfth_percentage?: number | null;
  active_backlogs: number;
  total_backlogs: number;
  is_placement_ready: boolean;
}

export interface CandidateSkillItem {
  skill_name: string;
  category: string;
  proficiency_level: string;
  is_verified: boolean;
}

export interface CandidateProjectItem {
  title: string;
  description?: string | null;
  technologies: string[];
  repo_url?: string | null;
  demo_url?: string | null;
}

export interface CandidateExperienceItem {
  job_title: string;
  company_name: string;
  start_date?: string | null;
  end_date?: string | null;
  is_current: boolean;
  description?: string | null;
}

export interface CandidateCertificationItem {
  name: string;
  issuing_organization: string;
  issue_date?: string | null;
  credential_url?: string | null;
}

export interface CandidateResumeSummary {
  resume_id: number;
  file_name: string;
  file_size_bytes?: number | null;
  file_type?: string | null;
  parsing_status?: string | null;
  resume_score?: number | null;
  download_url?: string | null;
}

export interface CandidateActivityTimelineItem {
  event_type: string;
  timestamp: string;
  actor_name: string;
  title: string;
  details?: string | null;
  metadata?: Record<string, unknown> | null;
}

export interface CandidateAISummary {
  candidate_name: string;
  verified_facts: Record<string, unknown>;
  calculated_metrics: Record<string, unknown>;
  ai_observations: {
    readiness_headline: string;
    synthesized_strengths: string[];
    suggested_interview_probes: string[];
    areas_for_development: string[];
    overall_synthesis: string;
  };
  safety_disclaimer: string;
  generated_at: string;
}

export interface CandidateWorkspaceDetailResponse {
  application_id: number;
  job_id: number;
  job_title: string;
  company_name: string;
  is_campus_drive_application: boolean;
  drive_id?: number | null;
  drive_name?: string | null;
  current_status: string;
  tpo_screening_status: string;
  applied_at: string;
  compatibility_score: number;
  score_breakdown: Record<string, unknown>;
  eligibility_checklist: CandidateEligibilityChecklist;
  profile: Record<string, unknown>;
  academics: CandidateAcademicInfo;
  skills: CandidateSkillItem[];
  projects: CandidateProjectItem[];
  experiences: CandidateExperienceItem[];
  certifications: CandidateCertificationItem[];
  resume?: CandidateResumeSummary | null;
  interviews: Array<Record<string, unknown>>;
  evaluations: CandidateEvaluationResponse[];
  notes: CandidateNoteResponse[];
  activity_timeline: CandidateActivityTimelineItem[];
}

export interface CandidateListItem {
  application_id: number;
  job_id: number;
  job_title: string;
  company_name: string;
  student_id: number;
  student_name: string;
  email: string;
  roll_number: string;
  department: string;
  graduation_year: number;
  cgpa: number;
  is_eligible: boolean;
  compatibility_score: number;
  current_status: string;
  tpo_screening_status: string;
  applied_at: string;
  interviews_count: number;
  evaluations_count: number;
  average_rating?: number | null;
  latest_recommendation?: EvaluationRecommendation | null;
}

export interface CandidateListResponse {
  items: CandidateListItem[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

export interface CandidateFilterParams {
  job_id?: number;
  department?: string;
  graduation_year?: number;
  eligibility?: 'all' | 'eligible_only' | 'ineligible_only';
  status?: string;
  min_compatibility_score?: number;
  skill?: string;
  min_experience_months?: number;
  search?: string;
  page?: number;
  limit?: number;
}

export interface CandidateStatusTransitionRequest {
  to_status: string;
  decision_notes?: string;
  offer_package_lpa?: number;
  offer_deadline_at?: string;
  offer_notes?: string;
}

// =============================================================================
// TASK 09: Complete Interview Management Portal Types
// =============================================================================

export interface InterviewPortalItem {
  id: number;
  application_id: number;
  round_number: number;
  round_title: string;
  interview_mode: 'virtual' | 'in_person';
  meeting_link?: string | null;
  location?: string | null;
  scheduled_start_time: string;
  duration_minutes: number;
  interviewer_names?: string | null;
  instructions?: string | null;
  status: 'scheduled' | 'completed' | 'cancelled' | 'no_show';
  outcome: 'pending' | 'passed' | 'failed' | 'on_hold';
  feedback_notes?: string | null;
  cancellation_reason?: string | null;
  is_rescheduled: boolean;
  created_at: string;
  updated_at: string;

  // Candidate details
  student_id: number;
  student_name: string;
  student_email: string;
  roll_number: string;
  department: string;
  graduation_year: number;
  cgpa: number;

  // Job & Company details
  job_id: number;
  job_title: string;
  company_id: number;
  company_name: string;

  // Placement Drive details
  drive_id?: number | null;
  drive_name?: string | null;

  // Evaluations summary
  evaluations_count: number;
  average_rating?: number | null;
}

export interface InterviewListPortalResponse {
  items: InterviewPortalItem[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

export interface CalendarEventItem {
  id: number;
  application_id: number;
  round_title: string;
  round_number: number;
  scheduled_start_time: string;
  duration_minutes: number;
  status: 'scheduled' | 'completed' | 'cancelled' | 'no_show';
  outcome: 'pending' | 'passed' | 'failed' | 'on_hold';
  interview_mode: 'virtual' | 'in_person';
  meeting_link?: string | null;
  location?: string | null;
  student_name: string;
  roll_number: string;
  job_title: string;
  company_name: string;
  is_rescheduled: boolean;
}

export interface InterviewCalendarDay {
  date: string; // YYYY-MM-DD
  events: CalendarEventItem[];
}

export interface InterviewCalendarResponse {
  days: InterviewCalendarDay[];
  total_events: number;
  scheduled_count: number;
  completed_count: number;
  cancelled_count: number;
  rescheduled_count: number;
}

export interface InterviewRoundTemplate {
  round_number: number;
  round_title: string;
  stage: string;
  default_duration_minutes: number;
  description: string;
}

export interface InterviewWorkspaceDetailResponse {
  interview: InterviewPortalItem;
  candidate_profile: {
    id: number;
    full_name: string;
    email: string;
    roll_number: string;
    department: string;
    graduation_year: number;
    cgpa: number;
    skills: string[];
    phone?: string | null;
    resume_url?: string | null;
    compatibility_score?: number | null;
  };
  job: {
    id: number;
    title: string;
    ctc_lpa?: number | null;
    work_mode: string;
    company_name: string;
    required_skills?: string[];
  };
  past_rounds: InterviewPortalItem[];
  evaluations: Array<{
    id: number;
    interviewer_name: string;
    stage: string;
    technical_rating?: number | null;
    problem_solving_rating?: number | null;
    communication_rating?: number | null;
    project_depth_rating?: number | null;
    cultural_fit_rating?: number | null;
    overall_rating: number;
    recommendation: string;
    written_feedback?: string | null;
    created_at: string;
  }>;
  allowed_next_actions: string[];
}

export interface InterviewSchedulePayload {
  round_number: number;
  round_title: string;
  interview_mode: 'virtual' | 'in_person';
  meeting_link?: string;
  location?: string;
  scheduled_start_time: string;
  duration_minutes: number;
  interviewer_names?: string;
  instructions?: string;
}

export interface InterviewReschedulePayload {
  scheduled_start_time: string;
  duration_minutes?: number;
  meeting_link?: string;
  location?: string;
  instructions?: string;
  reason: string;
}

export interface InterviewCancelPayload {
  reason: string;
}

export interface InterviewOutcomePayload {
  outcome: 'passed' | 'failed' | 'on_hold';
  feedback_notes?: string;
  cancellation_reason?: string;
}

export interface InterviewPortalFilterParams {
  job_id?: number;
  drive_id?: number;
  status?: string;
  outcome?: string;
  search?: string;
  date_from?: string;
  date_to?: string;
  page?: number;
  limit?: number;
}

// =============================================================================
// TASK 10: Candidate Comparison & Hiring Insights Types
// =============================================================================

export interface CandidateComparisonItem {
  application_id: number;
  student_id: number;
  user_id: number;
  candidate_name: string;
  roll_number: string;
  email: string;
  department: string;
  graduation_year: number;
  current_status: string;
  applied_at: string;

  // Academic & Eligibility
  is_eligible: boolean;
  eligibility_reasons: string[];
  academics: CandidateAcademicInfo;

  // Compatibility Scores
  compatibility_score_at_application: number;
  current_compatibility_score: number;
  score_breakdown: ScoreBreakdown;

  // Skill Coverage
  mandatory_skills_coverage: {
    required: string[];
    matched: string[];
    missing: string[];
    coverage_percentage: number;
  };
  preferred_skills_coverage: {
    required: string[];
    matched: string[];
    missing: string[];
    coverage_percentage: number;
  };
  skills: CandidateSkillItem[];

  // Practical Depth & Portfolio
  projects: CandidateProjectItem[];
  total_projects_count: number;
  experiences: CandidateExperienceItem[];
  total_experience_months: number;
  certifications: CandidateCertificationItem[];

  // Resume & Evaluations
  resume?: CandidateResumeSummary | null;
  interviews_count: number;
  evaluations_count: number;
  average_rating?: number | null;
  latest_recommendation?: string | null;
  notes_count: number;
}

export interface SkillMatrixRow {
  skill_name: string;
  is_mandatory: boolean;
  candidate_coverage: Record<string, boolean>;
}

export interface CandidateComparisonAISummary {
  shared_strengths: string[];
  candidate_strengths: Record<string, string[]>;
  missing_requirements: Record<string, string[]>;
  project_differences: string[];
  recommended_interview_focus: Record<string, string[]>;
  evidence_grounding_notes: string;
}

export interface CandidateComparisonResponse {
  job_id: number;
  job_title: string;
  company_id: number;
  company_name: string;
  required_mandatory_skills: string[];
  required_preferred_skills: string[];
  candidates: CandidateComparisonItem[];
  skill_matrix: SkillMatrixRow[];
  rankings: {
    by_compatibility?: number[];
    by_cgpa?: number[];
    by_experience?: number[];
    by_rating?: number[];
  };
  highlights: {
    highest_compatibility?: { application_id: number; candidate_name: string; score: number };
    highest_cgpa?: { application_id: number; candidate_name: string; cgpa: number };
    most_experience?: { application_id: number; candidate_name: string; months: number };
    highest_rating?: { application_id: number; candidate_name: string; rating: number };
  };
  ai_insights?: CandidateComparisonAISummary | null;
  comparison_timestamp: string;
}

export interface CandidateComparisonRequest {
  job_id: number;
  application_ids: number[];
  generate_ai_insights?: boolean;
}

export interface ComparisonSessionCreateRequest {
  job_id: number;
  title: string;
  application_ids: number[];
  notes?: string;
  include_ai_insights?: boolean;
}

export interface ComparisonSessionUpdateRequest {
  title?: string;
  notes?: string;
}

export interface ComparisonSessionResponse {
  id: number;
  company_id: number;
  job_id: number;
  job_title: string;
  title: string;
  application_ids: number[];
  notes?: string | null;
  ai_summary?: CandidateComparisonAISummary | null;
  created_by_user_id: number;
  created_by_name: string;
  created_at: string;
  updated_at: string;
}

export interface ComparisonSessionListResponse {
  items: ComparisonSessionResponse[];
  total: number;
}

// =============================================================================
// TASK 11: Centralized Audit Logging & Activity Monitoring Types
// =============================================================================

export type AuditCategoryType =
  | 'AUTHENTICATION'
  | 'ACADEMIC'
  | 'RECRUITMENT'
  | 'RESUME'
  | 'ADMINISTRATION';

export type AuditStatusType = 'SUCCESS' | 'FAILURE' | 'WARNING';

export interface AuditLogItem {
  id: number;
  event_id: string;
  user_id?: number | null;
  user_role?: string | null;
  user_email?: string | null;
  user_name?: string | null;
  institution_id?: number | null;
  category: AuditCategoryType | string;
  action: string;
  entity_type: string;
  entity_id?: string | null;
  status: AuditStatusType | string;
  correlation_id?: string | null;
  ip_address?: string | null;
  user_agent?: string | null;
  previous_values?: Record<string, any> | null;
  updated_values?: Record<string, any> | null;
  metadata?: Record<string, any> | null;
  prev_hash?: string | null;
  record_hash: string;
  timestamp: string;
}

export interface AuditLogListResponse {
  items: AuditLogItem[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}

export interface AuditSummaryStats {
  total_events: number;
  security_events: number;
  critical_changes: number;
  failed_operations: number;
  integrity_status: 'VERIFIED' | 'COMPROMISED' | string;
}

export interface AuditIntegrityVerificationResponse {
  is_valid: boolean;
  total_checked: number;
  broken_links_count: number;
  invalid_records: number[];
  details: string;
}

export interface AuditCategoriesResponse {
  categories: string[];
  actions: string[];
  entity_types: string[];
}

export interface AuditFilterParams {
  category?: string;
  action?: string;
  entity_type?: string;
  entity_id?: string;
  status?: string;
  user_id?: number;
  institution_id?: number;
  date_from?: string;
  date_to?: string;
  search?: string;
  page?: number;
  limit?: number;
}












