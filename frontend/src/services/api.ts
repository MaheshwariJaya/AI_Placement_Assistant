import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import {
  AuthResponse,
  Department,
  HealthLiveResponse,
  HealthReadyResponse,
  Institution,
  RegisterPayload,
  StudentAcademicContext,
  StudentProfile,
  User,
  Resume,
  ResumeStructuredData,
  ResumeSyncRequest,
  ResumeSyncResponse,
  Company,
  CompanyCreate,
  CompanyUpdate,
  RecruiterProfile,
  Job,
  JobCreate,
  JobUpdate,
  JobEligibilityResult,
  JobMatchEvaluationResponse,
  JobRecommendationCard,
  JobRecommendationListResponse,
  CandidateIntelligenceResponse,
  ChatMessage,
  CareerAssistantResponse,
  CareerContextSummary,
  CareerPromptSuggestion,
  ResumeFeedbackRequest,
  ResumeFeedbackResponse,
  FeedbackTargetJob,
  TpoOverviewResponse,
  TpoStudentRosterResponse,
  EligibilitySimulationRequest,
  EligibilitySimulationResponse,
  AdminOverviewResponse,
  RecruiterOverviewResponse,
  RecruiterOverviewApplication,
  MockInterviewTargetJob,
  MockInterviewAnalyticsResponse,
  MockInterviewSessionSummary,
  MockInterviewSessionDetail,
  MockInterviewCreatePayload,
  SubmitMockAnswerResponse,
  MockInterviewCategory,
  MockInterviewStatus,
  ReadinessSnapshot,
  ReadinessHistoryResponse,
  ReadinessIndicatorWeights,
  JobReadinessCheckResponse,
  TpoReadinessAnalyticsResponse,
  ReadinessCategory,
  ApplicationTrackerResponse,
  ApplicationStageStatus,
  TrackerApplicationItem,
  TrackerCalendarResponse,
  StudentInterviewListResponse,
  PlacementNotification,
  NotificationPreference,
  NotificationPreferenceUpdate,
  ArenaCategory,
  ArenaDifficulty,
  ArenaQuestionType,
  ArenaAssessmentMode,
  ArenaCodeLanguage,
  ArenaCategorySummary,
  ArenaQuestionView,
  ArenaAssessmentSummary,
  ArenaAttemptSummary,
  ArenaAttemptDetail,
  SandboxRunResponse,
  ArenaSubmitAnswerResponse,
  ArenaPerformanceAnalytics,
  ArenaPersonalizedPracticeResponse,
  ArenaUserPreference,
  ArenaLeaderboardResponse,
  ArenaTpoAnalyticsResponse,
  ArenaTpoStudentRosterResponse,
  ArenaOptionItem,
  TpoPlacementIntelligenceResponse,
  DriveLifecyclePhase,
  DriveActivityStatus,
  DriveAttendanceStatus,
  DriveAnnouncementAudience,
  PlacementDrive,
  PlacementDriveDetail,
  PlacementDriveCreatePayload,
  PlacementDriveUpdatePayload,
  DriveFormOptionsResponse,
  DriveDashboardResponse,
  DriveRegistrationItem,
  DriveCandidatesResponse,
  DriveApplicationItem,
  DriveActivityItem,
  DriveActivityCreatePayload,
  DriveAttendanceRecord,
  DriveAttendanceAuditItem,
  DriveAnnouncementItem,
  DriveReportResponse,
  ReportType,
  ReportFormat,
  ReportStatus,
  ReportFilterParams,
  ReportGenerateRequest,
  ReportSummaryKPIs,
  ReportDepartmentStat,
  ReportFunnelStage,
  ReportDataPayload,
  PlacementReportResponse,
  ReportOptionItem,
  ReportFormOptionsResponse,
  CandidateFilterParams,
  CandidateListResponse,
  CandidateWorkspaceDetailResponse,
  CandidateEvaluationCreate,
  CandidateEvaluationResponse,
  CandidateNoteCreate,
  CandidateNoteResponse,
  CandidateStatusTransitionRequest,
  CandidateAISummary,
  InterviewPortalItem,
  InterviewListPortalResponse,
  InterviewCalendarResponse,
  InterviewRoundTemplate,
  InterviewWorkspaceDetailResponse,
  InterviewSchedulePayload,
  InterviewReschedulePayload,
  InterviewCancelPayload,
  InterviewOutcomePayload,
  InterviewPortalFilterParams,
  CandidateComparisonItem,
  SkillMatrixRow,
  CandidateComparisonAISummary,
  CandidateComparisonResponse,
  CandidateComparisonRequest,
  ComparisonSessionCreateRequest,
  ComparisonSessionUpdateRequest,
  ComparisonSessionResponse,
  ComparisonSessionListResponse,
  AuditLogItem,
  AuditLogListResponse,
  AuditSummaryStats,
  AuditIntegrityVerificationResponse,
  AuditCategoriesResponse,
  AuditFilterParams,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request Interceptor: Attach JWT Bearer Token if present in localStorage
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('access_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error: AxiosError) => Promise.reject(error)
);

// Response Interceptor: Handle 401 Unauthorized / Token Expiration
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Clear expired credentials and notify
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user');
    }
    return Promise.reject(error);
  }
);

// Health API
export const healthApi = {
  getLive: async (): Promise<HealthLiveResponse> => {
    const response = await apiClient.get<HealthLiveResponse>('/health/live');
    return response.data;
  },

  getReady: async (): Promise<HealthReadyResponse> => {
    try {
      const response = await apiClient.get<HealthReadyResponse>('/health/ready');
      return response.data;
    } catch (error: any) {
      if (error.response && error.response.data) {
        return error.response.data as HealthReadyResponse;
      }
      return {
        success: false,
        status: 'degraded',
        timestamp: new Date().toISOString(),
        database: {
          status: 'disconnected',
          error: error.message || 'Network connection failed to backend.',
          remedy: 'Ensure FastAPI backend is running on 127.0.0.1:8000.',
        },
      };
    }
  },
};

// Auth API
export const authApi = {
  login: async (email: string, password: string): Promise<AuthResponse> => {
    const response = await apiClient.post<AuthResponse>('/api/v1/auth/login', {
      email,
      password,
    });
    return response.data;
  },

  register: async (payload: RegisterPayload): Promise<AuthResponse> => {
    const response = await apiClient.post<AuthResponse>('/api/v1/auth/register', payload);
    return response.data;
  },

  getMe: async (): Promise<User> => {
    const response = await apiClient.get<any>('/api/v1/auth/me');
    return response.data?.user || response.data;
  },

  refreshToken: async (refreshToken: string): Promise<AuthResponse> => {
    const response = await apiClient.post<AuthResponse>('/api/v1/auth/refresh', {
      refresh_token: refreshToken,
    });
    return response.data;
  },

  logout: async (): Promise<void> => {
    try {
      const refreshToken = localStorage.getItem('refresh_token');
      await apiClient.post('/api/v1/auth/logout', {
        refresh_token: refreshToken || undefined,
      });
    } finally {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user');
    }
  },

  logoutAll: async (): Promise<void> => {
    try {
      await apiClient.post('/api/v1/auth/logout', {});
    } finally {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user');
    }
  },

  changePassword: async (currentPassword: string, newPassword: string): Promise<{ success: boolean; message: string }> => {
    const response = await apiClient.post<{ success: boolean; message: string }>('/api/v1/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
    return response.data;
  },
};

// Organizations API
export const orgApi = {
  getInstitutions: async (): Promise<Institution[]> => {
    const response = await apiClient.get<Institution[]>('/api/v1/institutions');
    return response.data;
  },

  getDepartments: async (institutionId: number): Promise<Department[]> => {
    const response = await apiClient.get<Department[]>(`/api/v1/institutions/${institutionId}/departments`);
    return response.data;
  },
};

export const organizationApi = orgApi;

// User & Profile API
export const userApi = {
  getMe: async (): Promise<User> => {
    const response = await apiClient.get<User>('/api/v1/users/me');
    return response.data;
  },

  updateMe: async (data: { full_name?: string; phone?: string }): Promise<User> => {
    const response = await apiClient.put<User>('/api/v1/users/me', data);
    return response.data;
  },

  getStudentProfile: async (): Promise<StudentProfile> => {
    const response = await apiClient.get<StudentProfile>('/api/v1/students/profile');
    return response.data;
  },

  getAcademicContext: async (studentId?: number): Promise<StudentAcademicContext> => {
    const params = studentId ? { student_id: studentId } : {};
    const response = await apiClient.get<StudentAcademicContext>('/api/v1/students/academic-context', { params });
    return response.data;
  },

  updateCareerInterests: async (interests: string[]): Promise<StudentAcademicContext> => {
    const response = await apiClient.put<StudentAcademicContext>('/api/v1/students/career-interests', {
      career_interests: interests,
    });
    return response.data;
  },

  tpoUpdateStudentBranch: async (
    studentProfileId: number,
    departmentId: number,
    reason: string,
    academicOverrides?: {
      cgpa?: number;
      active_backlogs?: number;
      total_backlogs?: number;
    }
  ): Promise<StudentAcademicContext> => {
    const response = await apiClient.put<StudentAcademicContext>(
      `/api/v1/tpo/students/${studentProfileId}/official-branch`,
      { department_id: departmentId, reason, ...academicOverrides }
    );
    return response.data;
  },

  updatePortfolio: async (data: {
    linkedin_url?: string;
    github_url?: string;
    portfolio_url?: string;
  }): Promise<StudentProfile> => {
    const response = await apiClient.put<StudentProfile>('/api/v1/students/profile/portfolio', data);
    return response.data;
  },
};

export const studentApi = userApi;

// Resume Intelligence API
export const resumeApi = {
  uploadResume: async (file: File, autoExtract: boolean = true): Promise<Resume> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post<Resume>(
      `/api/v1/resumes/upload?auto_extract=${autoExtract}`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 90000,
      }
    );
    return response.data;
  },

  getResumes: async (studentId?: number): Promise<Resume[]> => {
    const params = studentId ? { student_id: studentId } : {};
    const response = await apiClient.get<Resume[]>('/api/v1/resumes', { params });
    return response.data;
  },

  getResumeDetails: async (resumeId: number): Promise<Resume> => {
    const response = await apiClient.get<Resume>(`/api/v1/resumes/${resumeId}`);
    return response.data;
  },

  downloadResume: async (resumeId: number, fileName: string): Promise<void> => {
    const response = await apiClient.get(`/api/v1/resumes/${resumeId}/download`, {
      responseType: 'blob',
    });
    const blob = new Blob([response.data]);
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },

  deleteResume: async (resumeId: number): Promise<{ message: string }> => {
    const response = await apiClient.delete<{ message: string }>(`/api/v1/resumes/${resumeId}`);
    return response.data;
  },

  triggerExtraction: async (resumeId: number): Promise<Resume> => {
    const response = await apiClient.post<Resume>(`/api/v1/resumes/${resumeId}/extract`, null, {
      timeout: 90000,
    });
    return response.data;
  },

  reviewResume: async (resumeId: number, structuredData: ResumeStructuredData): Promise<Resume> => {
    const response = await apiClient.put<Resume>(`/api/v1/resumes/${resumeId}/review`, {
      structured_data: structuredData,
    });
    return response.data;
  },

  approveResume: async (resumeId: number, req: ResumeSyncRequest = {}): Promise<ResumeSyncResponse> => {
    const response = await apiClient.post<ResumeSyncResponse>(`/api/v1/resumes/${resumeId}/approve`, req);
    return response.data;
  },

  rejectResume: async (resumeId: number): Promise<{ message: string }> => {
    const response = await apiClient.post<{ message: string }>(`/api/v1/resumes/${resumeId}/reject`);
    return response.data;
  },

  getFeedback: async (resumeId: number, jobId?: number): Promise<ResumeFeedbackResponse> => {
    const params = jobId ? { job_id: jobId } : {};
    const response = await apiClient.get<ResumeFeedbackResponse>(`/api/v1/resumes/${resumeId}/feedback`, {
      params,
      timeout: 30000,
    });
    return response.data;
  },

  requestFeedback: async (resumeId: number, req: ResumeFeedbackRequest = {}): Promise<ResumeFeedbackResponse> => {
    const response = await apiClient.post<ResumeFeedbackResponse>(`/api/v1/resumes/${resumeId}/feedback`, req, {
      timeout: 90000,
    });
    return response.data;
  },

  getFeedbackJobs: async (resumeId: number): Promise<FeedbackTargetJob[]> => {
    const response = await apiClient.get<FeedbackTargetJob[]>(`/api/v1/resumes/${resumeId}/feedback/jobs`);
    return response.data;
  },
};

export const companyApi = {
  list: async (params?: { search?: string; industry?: string; verified_only?: boolean }): Promise<Company[]> => {
    const response = await apiClient.get<Company[]>('/api/v1/companies', { params });
    return response.data;
  },
  getById: async (id: number): Promise<Company> => {
    const response = await apiClient.get<Company>(`/api/v1/companies/${id}`);
    return response.data;
  },
  getMyProfile: async (): Promise<RecruiterProfile> => {
    const response = await apiClient.get<RecruiterProfile>('/api/v1/companies/me');
    return response.data;
  },
  create: async (data: CompanyCreate): Promise<Company> => {
    const response = await apiClient.post<Company>('/api/v1/companies', data);
    return response.data;
  },
  update: async (id: number, data: CompanyUpdate): Promise<Company> => {
    const response = await apiClient.put<Company>(`/api/v1/companies/${id}`, data);
    return response.data;
  },
  verify: async (id: number, is_verified: boolean): Promise<Company> => {
    const response = await apiClient.patch<Company>(`/api/v1/companies/${id}/verify`, { is_verified });
    return response.data;
  },
};

export const jobApi = {
  list: async (params?: {
    status?: string;
    search?: string;
    employment_type?: string;
    work_mode?: string;
    department_id?: number;
    my_company_only?: boolean;
  }): Promise<Job[]> => {
    const response = await apiClient.get<Job[]>('/api/v1/jobs', { params });
    return response.data;
  },
  getById: async (id: number): Promise<Job> => {
    const response = await apiClient.get<Job>(`/api/v1/jobs/${id}`);
    return response.data;
  },
  create: async (data: JobCreate): Promise<Job> => {
    const response = await apiClient.post<Job>('/api/v1/jobs', data);
    return response.data;
  },
  update: async (id: number, data: JobUpdate): Promise<Job> => {
    const response = await apiClient.put<Job>(`/api/v1/jobs/${id}`, data);
    return response.data;
  },
  updateStatus: async (id: number, status: string): Promise<Job> => {
    const response = await apiClient.patch<Job>(`/api/v1/jobs/${id}/status`, { status });
    return response.data;
  },
  checkEligibility: async (id: number, studentId?: number): Promise<JobEligibilityResult> => {
    const params = studentId ? { student_id: studentId } : {};
    const response = await apiClient.get<JobEligibilityResult>(`/api/v1/jobs/${id}/check-eligibility`, { params });
    return response.data;
  },
};

export const intelligenceApi = {
  evaluateJob: async (jobId: number, studentId?: number): Promise<JobMatchEvaluationResponse> => {
    const params = studentId ? { student_id: studentId } : {};
    const response = await apiClient.get<JobMatchEvaluationResponse>(`/api/v1/intelligence/jobs/${jobId}/evaluate`, { params });
    return response.data;
  },
  getRecommendations: async (): Promise<JobRecommendationListResponse> => {
    const response = await apiClient.get<JobRecommendationListResponse>('/api/v1/intelligence/jobs/recommended');
    return response.data;
  },
  getCandidateIntelligence: async (jobId: number): Promise<CandidateIntelligenceResponse> => {
    const response = await apiClient.get<CandidateIntelligenceResponse>(`/api/v1/intelligence/jobs/${jobId}/candidates`);
    return response.data;
  },
};

export const careerAssistantApi = {
  chat: async (
    message: string,
    jobId?: number,
    conversationHistory?: ChatMessage[]
  ): Promise<CareerAssistantResponse> => {
    const response = await apiClient.post<CareerAssistantResponse>('/api/v1/career-assistant/chat', {
      message,
      job_id: jobId,
      conversation_history: conversationHistory || [],
    });
    return response.data;
  },
  getPrompts: async (jobId?: number): Promise<CareerPromptSuggestion[]> => {
    const params = jobId ? { job_id: jobId } : {};
    const response = await apiClient.get<CareerPromptSuggestion[]>('/api/v1/career-assistant/prompts', { params });
    return response.data;
  },
  getContext: async (jobId?: number): Promise<CareerContextSummary> => {
    const params = jobId ? { job_id: jobId } : {};
    const response = await apiClient.get<CareerContextSummary>('/api/v1/career-assistant/context', { params });
    return response.data;
  },
};

export const placementApi = {
  getTpoOverview: async (): Promise<TpoOverviewResponse> => {
    const response = await apiClient.get<TpoOverviewResponse>('/api/v1/placement/tpo/overview');
    return response.data;
  },
  getTpoStudents: async (): Promise<TpoStudentRosterResponse> => {
    const response = await apiClient.get<TpoStudentRosterResponse>('/api/v1/placement/tpo/students');
    return response.data;
  },
  simulateEligibility: async (
    criteria: EligibilitySimulationRequest
  ): Promise<EligibilitySimulationResponse> => {
    const response = await apiClient.post<EligibilitySimulationResponse>(
      '/api/v1/placement/tpo/simulate-eligibility',
      criteria
    );
    return response.data;
  },
  getAdminOverview: async (): Promise<AdminOverviewResponse> => {
    const response = await apiClient.get<AdminOverviewResponse>('/api/v1/placement/admin/overview');
    return response.data;
  },
  getRecruiterOverview: async (): Promise<RecruiterOverviewResponse> => {
    const response = await apiClient.get<RecruiterOverviewResponse>('/api/v1/recruiter/overview');
    return response.data;
  },
};

export const applicationApi = {
  submitApplication: async (data: {
    job_id: number;
    resume_id: number;
    drive_id?: number;
    cover_letter?: string;
  }): Promise<RecruiterOverviewApplication> => {
    const response = await apiClient.post<RecruiterOverviewApplication>('/api/v1/applications', data);
    return response.data;
  },
  getMyApplications: async (): Promise<{ items: RecruiterOverviewApplication[]; total: number }> => {
    const response = await apiClient.get<{ items: RecruiterOverviewApplication[]; total: number }>(
      '/api/v1/applications/my',
      { params: { limit: 100 } }
    );
    return response.data;
  },
  respondToOffer: async (
    applicationId: number,
    accept: boolean,
    notes?: string
  ): Promise<RecruiterOverviewApplication> => {
    const response = await apiClient.post<RecruiterOverviewApplication>(
      `/api/v1/applications/${applicationId}/offer-response`,
      { accept, notes }
    );
    return response.data;
  },
  withdrawApplication: async (
    applicationId: number,
    reason: string
  ): Promise<RecruiterOverviewApplication> => {
    const response = await apiClient.post<RecruiterOverviewApplication>(
      `/api/v1/applications/${applicationId}/withdraw`,
      { reason }
    );
    return response.data;
  },
  getTracker: async (params?: {
    status?: ApplicationStageStatus;
    company?: string;
    role?: string;
    search?: string;
    date_from?: string;
    date_to?: string;
    interview_status?: string;
    skip?: number;
    limit?: number;
    sync_notifications?: boolean;
  }): Promise<ApplicationTrackerResponse> => {
    const response = await apiClient.get<ApplicationTrackerResponse>('/api/v1/applications/tracker', {
      params,
    });
    return response.data;
  },
  getApplicationDetail: async (applicationId: number): Promise<TrackerApplicationItem> => {
    const response = await apiClient.get<TrackerApplicationItem>(`/api/v1/applications/${applicationId}`);
    return response.data;
  },
  getCalendarEvents: async (params?: {
    start_date?: string;
    end_date?: string;
    status?: ApplicationStageStatus;
    company?: string;
    role?: string;
    interview_status?: string;
  }): Promise<TrackerCalendarResponse> => {
    const response = await apiClient.get<TrackerCalendarResponse>('/api/v1/applications/tracker/calendar', {
      params,
    });
    return response.data;
  },
  screenApplication: async (
    applicationId: number,
    status: 'shortlisted' | 'rejected',
    feedback?: string
  ): Promise<DriveApplicationItem> => {
    const response = await apiClient.post<DriveApplicationItem>(
      `/api/v1/applications/${applicationId}/screen`,
      { status, feedback }
    );
    return response.data;
  },
};

export const interviewApi = {
  getMyInterviews: async (params?: {
    status?: string;
    company?: string;
    date_from?: string;
    date_to?: string;
  }): Promise<StudentInterviewListResponse> => {
    const response = await apiClient.get<StudentInterviewListResponse>('/api/v1/interviews/me', {
      params,
    });
    return response.data;
  },

  listCompanyInterviews: async (params?: InterviewPortalFilterParams): Promise<InterviewListPortalResponse> => {
    const response = await apiClient.get<InterviewListPortalResponse>('/api/v1/interviews', {
      params,
    });
    return response.data;
  },

  getCalendar: async (params?: {
    start_date?: string;
    end_date?: string;
    status?: string;
    job_id?: number;
  }): Promise<InterviewCalendarResponse> => {
    const response = await apiClient.get<InterviewCalendarResponse>('/api/v1/interviews/calendar', {
      params,
    });
    return response.data;
  },

  getRoundTemplates: async (): Promise<InterviewRoundTemplate[]> => {
    const response = await apiClient.get<InterviewRoundTemplate[]>('/api/v1/interviews/rounds/templates');
    return response.data;
  },

  getInterviewWorkspace: async (interviewId: number): Promise<InterviewWorkspaceDetailResponse> => {
    const response = await apiClient.get<InterviewWorkspaceDetailResponse>(`/api/v1/interviews/${interviewId}`);
    return response.data;
  },

  scheduleInterview: async (
    applicationId: number,
    payload: InterviewSchedulePayload
  ): Promise<InterviewPortalItem> => {
    const response = await apiClient.post<InterviewPortalItem>(
      `/api/v1/applications/${applicationId}/interviews`,
      payload
    );
    return response.data;
  },

  rescheduleInterview: async (
    interviewId: number,
    payload: InterviewReschedulePayload
  ): Promise<InterviewPortalItem> => {
    const response = await apiClient.post<InterviewPortalItem>(
      `/api/v1/interviews/${interviewId}/reschedule`,
      payload
    );
    return response.data;
  },

  cancelInterview: async (
    interviewId: number,
    payload: InterviewCancelPayload
  ): Promise<InterviewPortalItem> => {
    const response = await apiClient.post<InterviewPortalItem>(
      `/api/v1/interviews/${interviewId}/cancel`,
      payload
    );
    return response.data;
  },

  recordOutcome: async (
    interviewId: number,
    payload: InterviewOutcomePayload
  ): Promise<InterviewPortalItem> => {
    const response = await apiClient.post<InterviewPortalItem>(
      `/api/v1/interviews/${interviewId}/outcome`,
      payload
    );
    return response.data;
  },

  listTpoMonitoring: async (params?: InterviewPortalFilterParams): Promise<InterviewListPortalResponse> => {
    const response = await apiClient.get<InterviewListPortalResponse>('/api/v1/interviews/tpo/monitoring', {
      params,
    });
    return response.data;
  },
};

export const notificationApi = {
  listNotifications: async (params?: {
    unread_only?: boolean;
    skip?: number;
    limit?: number;
  }): Promise<PlacementNotification[]> => {
    const response = await apiClient.get<PlacementNotification[]>('/api/v1/notifications', {
      params,
    });
    return response.data;
  },
  getUnreadCount: async (): Promise<{ unread_count: number }> => {
    const response = await apiClient.get<{ unread_count: number }>('/api/v1/notifications/unread-count');
    return response.data;
  },
  markAsRead: async (notificationId: number): Promise<PlacementNotification> => {
    const response = await apiClient.patch<PlacementNotification>(`/api/v1/notifications/${notificationId}/read`);
    return response.data;
  },
  markAllAsRead: async (): Promise<{ marked_read_count: number }> => {
    const response = await apiClient.post<{ marked_read_count: number }>('/api/v1/notifications/mark-all-read');
    return response.data;
  },
  getPreferences: async (): Promise<NotificationPreference> => {
    const response = await apiClient.get<NotificationPreference>('/api/v1/notifications/preferences');
    return response.data;
  },
  updatePreferences: async (payload: NotificationPreferenceUpdate): Promise<NotificationPreference> => {
    const response = await apiClient.put<NotificationPreference>('/api/v1/notifications/preferences', payload);
    return response.data;
  },
  syncSmartNotifications: async (): Promise<{ generated_count: number; notifications: PlacementNotification[] }> => {
    const response = await apiClient.post<{ generated_count: number; notifications: PlacementNotification[] }>(
      '/api/v1/notifications/sync'
    );
    return response.data;
  },
};

export const mockInterviewApi = {
  getTargetJobs: async (): Promise<MockInterviewTargetJob[]> => {
    const response = await apiClient.get<MockInterviewTargetJob[]>('/api/v1/mock-interviews/target-jobs');
    return response.data;
  },
  getAnalytics: async (): Promise<MockInterviewAnalyticsResponse> => {
    const response = await apiClient.get<MockInterviewAnalyticsResponse>('/api/v1/mock-interviews/analytics');
    return response.data;
  },
  listSessions: async (params?: {
    category?: MockInterviewCategory;
    status?: MockInterviewStatus;
  }): Promise<MockInterviewSessionSummary[]> => {
    const response = await apiClient.get<MockInterviewSessionSummary[]>('/api/v1/mock-interviews', { params });
    return response.data;
  },
  createSession: async (payload: MockInterviewCreatePayload): Promise<MockInterviewSessionDetail> => {
    const response = await apiClient.post<MockInterviewSessionDetail>('/api/v1/mock-interviews', payload);
    return response.data;
  },
  getSession: async (sessionId: number): Promise<MockInterviewSessionDetail> => {
    const response = await apiClient.get<MockInterviewSessionDetail>(`/api/v1/mock-interviews/${sessionId}`);
    return response.data;
  },
  submitAnswer: async (
    sessionId: number,
    payload: {
      question_id: number;
      answer_text?: string;
      selected_option_key?: string | null;
      input_mode?: 'text' | 'voice';
      response_time_seconds?: number;
      elapsed_seconds?: number;
    }
  ): Promise<SubmitMockAnswerResponse> => {
    const response = await apiClient.post<SubmitMockAnswerResponse>(
      `/api/v1/mock-interviews/${sessionId}/answers`,
      payload
    );
    return response.data;
  },
  pauseSession: async (sessionId: number, elapsedSeconds: number): Promise<MockInterviewSessionDetail> => {
    const response = await apiClient.post<MockInterviewSessionDetail>(
      `/api/v1/mock-interviews/${sessionId}/pause`,
      { elapsed_seconds: elapsedSeconds }
    );
    return response.data;
  },
  resumeSession: async (sessionId: number): Promise<MockInterviewSessionDetail> => {
    const response = await apiClient.post<MockInterviewSessionDetail>(
      `/api/v1/mock-interviews/${sessionId}/resume`
    );
    return response.data;
  },
  completeSession: async (sessionId: number, elapsedSeconds?: number): Promise<MockInterviewSessionDetail> => {
    const response = await apiClient.post<MockInterviewSessionDetail>(
      `/api/v1/mock-interviews/${sessionId}/complete`,
      elapsedSeconds !== undefined ? { elapsed_seconds: elapsedSeconds } : {}
    );
    return response.data;
  },
};

export const readinessApi = {
  getOverview: async (): Promise<ReadinessSnapshot> => {
    const response = await apiClient.get<ReadinessSnapshot>('/api/v1/readiness/me');
    return response.data;
  },
  calculateSnapshot: async (payload: {
    job_id?: number | null;
    target_role?: string | null;
    custom_weights?: ReadinessIndicatorWeights | null;
    include_ai_recommendations?: boolean;
  }): Promise<ReadinessSnapshot> => {
    const response = await apiClient.post<ReadinessSnapshot>('/api/v1/readiness/calculate', payload);
    return response.data;
  },
  getHistory: async (): Promise<ReadinessHistoryResponse> => {
    const response = await apiClient.get<ReadinessHistoryResponse>('/api/v1/readiness/history');
    return response.data;
  },
  checkJobReadiness: async (payload: {
    job_id?: number | null;
    target_role?: string | null;
    custom_weights?: ReadinessIndicatorWeights | null;
  }): Promise<JobReadinessCheckResponse> => {
    const response = await apiClient.post<JobReadinessCheckResponse>('/api/v1/readiness/job-check', payload);
    return response.data;
  },
  toggleRecommendation: async (
    snapshotId: number,
    recommendationId: string,
    completed: boolean
  ): Promise<ReadinessSnapshot> => {
    const response = await apiClient.patch<ReadinessSnapshot>(
      `/api/v1/readiness/snapshots/${snapshotId}/recommendations/${recommendationId}`,
      { completed }
    );
    return response.data;
  },
  getTpoAnalytics: async (params?: {
    department_id?: number;
    graduation_year?: number;
    category?: ReadinessCategory;
    skill_category?: string;
  }): Promise<TpoReadinessAnalyticsResponse> => {
    const response = await apiClient.get<TpoReadinessAnalyticsResponse>('/api/v1/readiness/tpo/analytics', {
      params,
    });
    return response.data;
  },
};

export const arenaApi = {
  getCategories: async (): Promise<ArenaCategorySummary[]> => {
    const response = await apiClient.get<ArenaCategorySummary[]>('/api/v1/arena/categories');
    return response.data;
  },
  listQuestions: async (params?: {
    category?: ArenaCategory;
    difficulty?: ArenaDifficulty;
    question_type?: ArenaQuestionType;
    company_tag?: string;
    search?: string;
  }): Promise<ArenaQuestionView[]> => {
    const response = await apiClient.get<ArenaQuestionView[]>('/api/v1/arena/questions', { params });
    return response.data;
  },
  listAssessments: async (params?: {
    mode?: ArenaAssessmentMode;
    category?: ArenaCategory;
  }): Promise<ArenaAssessmentSummary[]> => {
    const response = await apiClient.get<ArenaAssessmentSummary[]>('/api/v1/arena/assessments', { params });
    return response.data;
  },
  startAttempt: async (payload: {
    assessment_id?: number;
    mode?: ArenaAssessmentMode;
    category?: ArenaCategory;
    difficulty?: ArenaDifficulty;
    company_name_style?: string;
    question_count?: number;
    time_limit_minutes?: number;
    title?: string;
  }): Promise<ArenaAttemptDetail> => {
    const response = await apiClient.post<ArenaAttemptDetail>('/api/v1/arena/attempts', payload);
    return response.data;
  },
  listAttempts: async (): Promise<ArenaAttemptSummary[]> => {
    const response = await apiClient.get<ArenaAttemptSummary[]>('/api/v1/arena/attempts');
    return response.data;
  },
  getAttemptDetail: async (attemptId: number): Promise<ArenaAttemptDetail> => {
    const response = await apiClient.get<ArenaAttemptDetail>(`/api/v1/arena/attempts/${attemptId}`);
    return response.data;
  },
  runCode: async (
    attemptId: number,
    payload: { question_id: number; language: ArenaCodeLanguage; source_code: string; custom_stdin?: string }
  ): Promise<SandboxRunResponse> => {
    const response = await apiClient.post<SandboxRunResponse>(`/api/v1/arena/attempts/${attemptId}/run-code`, payload);
    return response.data;
  },
  submitAnswer: async (
    attemptId: number,
    payload: {
      question_id: number;
      selected_option_key?: string;
      submitted_code?: string;
      code_language?: ArenaCodeLanguage;
      behavioral_response?: string;
      time_spent_seconds?: number;
    }
  ): Promise<ArenaSubmitAnswerResponse> => {
    const response = await apiClient.post<ArenaSubmitAnswerResponse>(
      `/api/v1/arena/attempts/${attemptId}/answer`,
      payload
    );
    return response.data;
  },
  submitAttempt: async (attemptId: number, elapsedSeconds?: number): Promise<ArenaAttemptDetail> => {
    const response = await apiClient.post<ArenaAttemptDetail>(`/api/v1/arena/attempts/${attemptId}/submit`, {
      elapsed_seconds: elapsedSeconds,
    });
    return response.data;
  },
  getAnalytics: async (): Promise<ArenaPerformanceAnalytics> => {
    const response = await apiClient.get<ArenaPerformanceAnalytics>('/api/v1/arena/analytics');
    return response.data;
  },
  getRecommendations: async (jobId?: number): Promise<ArenaPersonalizedPracticeResponse> => {
    const response = await apiClient.get<ArenaPersonalizedPracticeResponse>('/api/v1/arena/recommendations', {
      params: jobId ? { job_id: jobId } : undefined,
    });
    return response.data;
  },
  getPreferences: async (): Promise<ArenaUserPreference> => {
    const response = await apiClient.get<ArenaUserPreference>('/api/v1/arena/preferences');
    return response.data;
  },
  updatePreferences: async (payload: {
    leaderboard_opt_in?: boolean;
    anonymize_name?: boolean;
    preferred_language?: ArenaCodeLanguage;
  }): Promise<ArenaUserPreference> => {
    const response = await apiClient.put<ArenaUserPreference>('/api/v1/arena/preferences', payload);
    return response.data;
  },
  getLeaderboard: async (scope: 'department' | 'batch' | 'institution'): Promise<ArenaLeaderboardResponse> => {
    const response = await apiClient.get<ArenaLeaderboardResponse>('/api/v1/arena/leaderboard', { params: { scope } });
    return response.data;
  },
  createTpoQuestion: async (payload: {
    title: string;
    prompt_text: string;
    category: ArenaCategory;
    difficulty: ArenaDifficulty;
    question_type: ArenaQuestionType;
    options: ArenaOptionItem[];
    correct_option_key?: string;
    explanation_text: string;
    expected_time_seconds?: number;
    max_marks?: number;
  }): Promise<ArenaQuestionView> => {
    const response = await apiClient.post<ArenaQuestionView>('/api/v1/arena/tpo/questions', payload);
    return response.data;
  },
  listTpoQuestions: async (): Promise<ArenaQuestionView[]> => {
    const response = await apiClient.get<ArenaQuestionView[]>('/api/v1/arena/tpo/questions');
    return response.data;
  },
  createTpoAssessment: async (payload: {
    title: string;
    description: string;
    category?: ArenaCategory;
    difficulty: ArenaDifficulty;
    duration_minutes: number;
    question_ids: number[];
    passing_percentage?: number;
    department_id?: number;
    target_graduation_year?: number;
    is_published?: boolean;
  }): Promise<ArenaAssessmentSummary> => {
    const response = await apiClient.post<ArenaAssessmentSummary>('/api/v1/arena/tpo/assessments', payload);
    return response.data;
  },
  listTpoAssessments: async (): Promise<ArenaAssessmentSummary[]> => {
    const response = await apiClient.get<ArenaAssessmentSummary[]>('/api/v1/arena/tpo/assessments');
    return response.data;
  },
  getTpoAnalytics: async (): Promise<ArenaTpoAnalyticsResponse> => {
    const response = await apiClient.get<ArenaTpoAnalyticsResponse>('/api/v1/arena/tpo/analytics');
    return response.data;
  },
  getTpoStudentRoster: async (params?: {
    department_id?: number;
    graduation_year?: number;
    search?: string;
    institution_id?: number;
  }): Promise<ArenaTpoStudentRosterResponse> => {
    const response = await apiClient.get<ArenaTpoStudentRosterResponse>('/api/v1/arena/tpo/students', {
      params,
    });
    return response.data;
  },
  getTpoStudentDetail: async (
    studentId: number,
    institutionId?: number
  ): Promise<ArenaPerformanceAnalytics> => {
    const params = institutionId ? { institution_id: institutionId } : {};
    const response = await apiClient.get<ArenaPerformanceAnalytics>(`/api/v1/arena/tpo/students/${studentId}`, {
      params,
    });
    return response.data;
  },
};

export interface TpoIntelligenceQueryParams {
  academic_year?: string;
  graduation_year?: number;
  department_id?: number;
  company_id?: number;
  job_category?: string;
  employment_type?: string;
  institution_id?: number;
  refresh?: boolean;
}

export const tpoIntelligenceApi = {
  getDashboard: async (
    params?: TpoIntelligenceQueryParams
  ): Promise<TpoPlacementIntelligenceResponse> => {
    const response = await apiClient.get<TpoPlacementIntelligenceResponse>(
      '/api/v1/tpo/intelligence/dashboard',
      { params }
    );
    return response.data;
  },
  exportPdf: async (params?: TpoIntelligenceQueryParams): Promise<Blob> => {
    const response = await apiClient.get('/api/v1/tpo/intelligence/export/pdf', {
      params,
      responseType: 'blob',
    });
    return response.data;
  },
  exportExcel: async (params?: TpoIntelligenceQueryParams): Promise<Blob> => {
    const response = await apiClient.get('/api/v1/tpo/intelligence/export/excel', {
      params,
      responseType: 'blob',
    });
    return response.data;
  },
};

export const driveApi = {
  getFormOptions: async (): Promise<DriveFormOptionsResponse> => {
    const response = await apiClient.get<DriveFormOptionsResponse>('/api/v1/drives/form-options');
    return response.data;
  },
  listDrives: async (params?: {
    academic_year?: string;
    target_graduation_year?: number;
    drive_mode?: string;
    status?: string;
    limit?: number;
  }): Promise<PlacementDrive[]> => {
    const response = await apiClient.get<PlacementDrive[]>('/api/v1/drives', { params });
    return response.data;
  },
  getDrive: async (driveId: number): Promise<PlacementDriveDetail> => {
    const response = await apiClient.get<PlacementDriveDetail>(`/api/v1/drives/${driveId}`);
    return response.data;
  },
  createDrive: async (payload: PlacementDriveCreatePayload): Promise<PlacementDrive> => {
    const response = await apiClient.post<PlacementDrive>('/api/v1/drives', payload);
    return response.data;
  },
  updateDrive: async (driveId: number, payload: PlacementDriveUpdatePayload): Promise<PlacementDrive> => {
    const response = await apiClient.patch<PlacementDrive>(`/api/v1/drives/${driveId}`, payload);
    return response.data;
  },
  transitionLifecycle: async (
    driveId: number,
    target_phase: DriveLifecyclePhase,
    reason?: string
  ): Promise<PlacementDrive> => {
    const response = await apiClient.post<PlacementDrive>(`/api/v1/drives/${driveId}/transition`, {
      target_phase,
      reason,
    });
    return response.data;
  },
  addJobToDrive: async (driveId: number, jobId: number): Promise<unknown> => {
    const response = await apiClient.post(`/api/v1/drives/${driveId}/jobs`, { job_id: jobId });
    return response.data;
  },
  removeJobFromDrive: async (driveId: number, jobId: number): Promise<unknown> => {
    const response = await apiClient.delete(`/api/v1/drives/${driveId}/jobs/${jobId}`);
    return response.data;
  },
  getDashboard: async (driveId: number): Promise<DriveDashboardResponse> => {
    const response = await apiClient.get<DriveDashboardResponse>(`/api/v1/drives/${driveId}/dashboard`);
    return response.data;
  },
  studentRegister: async (driveId: number, notes?: string): Promise<DriveRegistrationItem> => {
    const response = await apiClient.post<DriveRegistrationItem>(`/api/v1/drives/${driveId}/register`, {
      notes,
    });
    return response.data;
  },
  tpoRegisterStudents: async (
    driveId: number,
    studentIds: number[],
    notes?: string
  ): Promise<DriveRegistrationItem[]> => {
    const response = await apiClient.post<DriveRegistrationItem[]>(
      `/api/v1/drives/${driveId}/registrations`,
      { student_ids: studentIds, notes }
    );
    return response.data;
  },
  getRegistrations: async (driveId: number): Promise<DriveRegistrationItem[]> => {
    const response = await apiClient.get<DriveRegistrationItem[]>(`/api/v1/drives/${driveId}/registrations`);
    return response.data;
  },
  getCandidates: async (driveId: number): Promise<DriveCandidatesResponse> => {
    const response = await apiClient.get<DriveCandidatesResponse>(`/api/v1/drives/${driveId}/candidates`);
    return response.data;
  },
  getDriveApplications: async (
    driveId: number
  ): Promise<{ items: DriveApplicationItem[]; total: number }> => {
    const response = await apiClient.get<{ items: DriveApplicationItem[]; total: number }>(
      `/api/v1/drives/${driveId}/applications`,
      { params: { limit: 100 } }
    );
    return response.data;
  },
  listActivities: async (driveId: number): Promise<DriveActivityItem[]> => {
    const response = await apiClient.get<DriveActivityItem[]>(`/api/v1/drives/${driveId}/activities`);
    return response.data;
  },
  createActivity: async (
    driveId: number,
    payload: DriveActivityCreatePayload
  ): Promise<DriveActivityItem> => {
    const response = await apiClient.post<DriveActivityItem>(
      `/api/v1/drives/${driveId}/activities`,
      payload
    );
    return response.data;
  },
  updateActivityStatus: async (
    driveId: number,
    activityId: number,
    status: DriveActivityStatus
  ): Promise<DriveActivityItem> => {
    const response = await apiClient.patch<DriveActivityItem>(
      `/api/v1/drives/${driveId}/activities/${activityId}`,
      { status }
    );
    return response.data;
  },
  getActivityAttendance: async (
    driveId: number,
    activityId: number
  ): Promise<DriveAttendanceRecord[]> => {
    const response = await apiClient.get<DriveAttendanceRecord[]>(
      `/api/v1/drives/${driveId}/activities/${activityId}/attendance`
    );
    return response.data;
  },
  markActivityAttendance: async (
    driveId: number,
    activityId: number,
    records: Array<{ student_id: number; attendance_status: DriveAttendanceStatus; remarks?: string }>
  ): Promise<DriveAttendanceRecord[]> => {
    const response = await apiClient.post<DriveAttendanceRecord[]>(
      `/api/v1/drives/${driveId}/activities/${activityId}/attendance`,
      { records }
    );
    return response.data;
  },
  getAttendanceAudit: async (
    driveId: number,
    activityId: number
  ): Promise<DriveAttendanceAuditItem[]> => {
    const response = await apiClient.get<DriveAttendanceAuditItem[]>(
      `/api/v1/drives/${driveId}/activities/${activityId}/attendance/audit`
    );
    return response.data;
  },
  listAnnouncements: async (driveId: number): Promise<DriveAnnouncementItem[]> => {
    const response = await apiClient.get<DriveAnnouncementItem[]>(`/api/v1/drives/${driveId}/announcements`);
    return response.data;
  },
  createAnnouncement: async (
    driveId: number,
    payload: {
      title: string;
      message: string;
      target_audience: DriveAnnouncementAudience;
      job_id?: number | null;
    }
  ): Promise<DriveAnnouncementItem> => {
    const response = await apiClient.post<DriveAnnouncementItem>(
      `/api/v1/drives/${driveId}/announcements`,
      payload
    );
    return response.data;
  },
  getReport: async (driveId: number): Promise<DriveReportResponse> => {
    const response = await apiClient.get<DriveReportResponse>(`/api/v1/drives/${driveId}/report`);
    return response.data;
  },
  exportReportPdf: async (driveId: number): Promise<Blob> => {
    const response = await apiClient.get(`/api/v1/drives/${driveId}/report/export/pdf`, {
      responseType: 'blob',
    });
    return response.data;
  },
  exportReportExcel: async (driveId: number): Promise<Blob> => {
    const response = await apiClient.get(`/api/v1/drives/${driveId}/report/export/excel`, {
      responseType: 'blob',
    });
    return response.data;
  },
};

export const reportApi = {
  getFormOptions: async (institutionId?: number): Promise<ReportFormOptionsResponse> => {
    const params = institutionId ? { institution_id: institutionId } : {};
    const response = await apiClient.get<ReportFormOptionsResponse>('/api/v1/reports/form-options', { params });
    return response.data;
  },
  previewReport: async (
    payload: ReportGenerateRequest,
    institutionId?: number
  ): Promise<ReportDataPayload> => {
    const params = institutionId ? { institution_id: institutionId } : {};
    const response = await apiClient.post<ReportDataPayload>('/api/v1/reports/preview', payload, { params });
    return response.data;
  },
  generateReport: async (
    payload: ReportGenerateRequest,
    download = false,
    institutionId?: number
  ): Promise<PlacementReportResponse | Blob> => {
    const params: Record<string, unknown> = { download };
    if (institutionId) params.institution_id = institutionId;
    if (download) {
      const response = await apiClient.post('/api/v1/reports/generate', payload, {
        params,
        responseType: 'blob',
      });
      return response.data as Blob;
    }
    const response = await apiClient.post<PlacementReportResponse>('/api/v1/reports/generate', payload, { params });
    return response.data;
  },
  generateAsyncReport: async (
    payload: ReportGenerateRequest,
    institutionId?: number
  ): Promise<PlacementReportResponse> => {
    const params = institutionId ? { institution_id: institutionId } : {};
    const response = await apiClient.post<PlacementReportResponse>('/api/v1/reports/generate-async', payload, { params });
    return response.data;
  },
  listReports: async (params?: {
    report_type?: string;
    file_format?: string;
    status?: string;
    skip?: number;
    limit?: number;
    institution_id?: number;
  }): Promise<PlacementReportResponse[]> => {
    const response = await apiClient.get<PlacementReportResponse[]>('/api/v1/reports', { params });
    return response.data;
  },
  getReport: async (reportId: number): Promise<PlacementReportResponse> => {
    const response = await apiClient.get<PlacementReportResponse>(`/api/v1/reports/${reportId}`);
    return response.data;
  },
  downloadReportFile: async (reportId: number): Promise<Blob> => {
    const response = await apiClient.get(`/api/v1/reports/${reportId}/download`, {
      responseType: 'blob',
    });
    return response.data;
  },
  deleteReport: async (reportId: number): Promise<{ message: string; id: number }> => {
    const response = await apiClient.delete<{ message: string; id: number }>(`/api/v1/reports/${reportId}`);
    return response.data;
  },
};

export const recruiterCandidateApi = {
  listCandidates: async (params?: CandidateFilterParams): Promise<CandidateListResponse> => {
    const response = await apiClient.get<CandidateListResponse>('/api/v1/recruiter/candidates', { params });
    return response.data;
  },
  getCandidateWorkspace: async (applicationId: number): Promise<CandidateWorkspaceDetailResponse> => {
    const response = await apiClient.get<CandidateWorkspaceDetailResponse>(`/api/v1/recruiter/candidates/${applicationId}`);
    return response.data;
  },
  submitEvaluation: async (
    applicationId: number,
    payload: CandidateEvaluationCreate
  ): Promise<CandidateEvaluationResponse> => {
    const response = await apiClient.post<CandidateEvaluationResponse>(
      `/api/v1/recruiter/candidates/${applicationId}/evaluations`,
      payload
    );
    return response.data;
  },
  listEvaluations: async (applicationId: number): Promise<CandidateEvaluationResponse[]> => {
    const response = await apiClient.get<CandidateEvaluationResponse[]>(
      `/api/v1/recruiter/candidates/${applicationId}/evaluations`
    );
    return response.data;
  },
  createNote: async (applicationId: number, payload: CandidateNoteCreate): Promise<CandidateNoteResponse> => {
    const response = await apiClient.post<CandidateNoteResponse>(
      `/api/v1/recruiter/candidates/${applicationId}/notes`,
      payload
    );
    return response.data;
  },
  listNotes: async (applicationId: number): Promise<CandidateNoteResponse[]> => {
    const response = await apiClient.get<CandidateNoteResponse[]>(
      `/api/v1/recruiter/candidates/${applicationId}/notes`
    );
    return response.data;
  },
  deleteNote: async (applicationId: number, noteId: number): Promise<{ message: string; id: number }> => {
    const response = await apiClient.delete<{ message: string; id: number }>(
      `/api/v1/recruiter/candidates/${applicationId}/notes/${noteId}`
    );
    return response.data;
  },
  transitionStatus: async (
    applicationId: number,
    payload: CandidateStatusTransitionRequest
  ): Promise<Record<string, unknown>> => {
    const response = await apiClient.post<Record<string, unknown>>(
      `/api/v1/recruiter/candidates/${applicationId}/status`,
      payload
    );
    return response.data;
  },
  generateAISummary: async (applicationId: number): Promise<CandidateAISummary> => {
    const response = await apiClient.post<CandidateAISummary>(
      `/api/v1/recruiter/candidates/${applicationId}/ai-summary`
    );
    return response.data;
  },
};

export const candidateComparisonApi = {
  compareCandidates: async (payload: CandidateComparisonRequest): Promise<CandidateComparisonResponse> => {
    const response = await apiClient.post<CandidateComparisonResponse>(
      '/api/v1/recruiter/candidate-comparisons/compare',
      payload
    );
    return response.data;
  },

  createSession: async (payload: ComparisonSessionCreateRequest): Promise<ComparisonSessionResponse> => {
    const response = await apiClient.post<ComparisonSessionResponse>(
      '/api/v1/recruiter/candidate-comparisons/sessions',
      payload
    );
    return response.data;
  },

  listSessions: async (jobId?: number): Promise<ComparisonSessionListResponse> => {
    const response = await apiClient.get<ComparisonSessionListResponse>(
      '/api/v1/recruiter/candidate-comparisons/sessions',
      {
        params: jobId ? { job_id: jobId } : undefined,
      }
    );
    return response.data;
  },

  getSession: async (
    sessionId: number
  ): Promise<{ session: ComparisonSessionResponse; comparison: CandidateComparisonResponse }> => {
    const response = await apiClient.get<{ session: ComparisonSessionResponse; comparison: CandidateComparisonResponse }>(
      `/api/v1/recruiter/candidate-comparisons/sessions/${sessionId}`
    );
    return response.data;
  },

  updateSession: async (
    sessionId: number,
    payload: ComparisonSessionUpdateRequest
  ): Promise<ComparisonSessionResponse> => {
    const response = await apiClient.patch<ComparisonSessionResponse>(
      `/api/v1/recruiter/candidate-comparisons/sessions/${sessionId}`,
      payload
    );
    return response.data;
  },

  deleteSession: async (sessionId: number): Promise<{ message: string; deleted_id: number }> => {
    const response = await apiClient.delete<{ message: string; deleted_id: number }>(
      `/api/v1/recruiter/candidate-comparisons/sessions/${sessionId}`
    );
    return response.data;
  },
};

export const auditApi = {
  getLogs: async (params?: AuditFilterParams): Promise<AuditLogListResponse> => {
    const response = await apiClient.get<AuditLogListResponse>('/api/v1/audit/logs', { params });
    return response.data;
  },

  getLogDetail: async (logId: number): Promise<AuditLogItem> => {
    const response = await apiClient.get<AuditLogItem>(`/api/v1/audit/logs/${logId}`);
    return response.data;
  },

  getStats: async (): Promise<AuditSummaryStats> => {
    const response = await apiClient.get<AuditSummaryStats>('/api/v1/audit/stats');
    return response.data;
  },

  getCategories: async (): Promise<AuditCategoriesResponse> => {
    const response = await apiClient.get<AuditCategoriesResponse>('/api/v1/audit/categories');
    return response.data;
  },

  verifyIntegrity: async (limit = 1000): Promise<AuditIntegrityVerificationResponse> => {
    const response = await apiClient.get<AuditIntegrityVerificationResponse>('/api/v1/audit/verify-integrity', {
      params: { limit },
    });
    return response.data;
  },
};

export default apiClient;
