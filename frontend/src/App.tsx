import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { AcademicProvider } from './context/AcademicContext';
import { ThemeProvider } from './context/ThemeContext';
import { ProtectedRoute } from './components/ProtectedRoute';

// Public Pages
import { LandingPage } from './pages/LandingPage';
import { LoginPage } from './pages/auth/LoginPage';
import { RegisterPage } from './pages/auth/RegisterPage';

// Dashboards
import { StudentDashboard } from './pages/dashboards/StudentDashboard';
import { AcademicProfilePage } from './pages/profile/AcademicProfilePage';
import { ResumeIntelligencePage } from './pages/resumes/ResumeIntelligencePage';
import { ExploreJobsPage } from './pages/jobs/ExploreJobsPage';
import { ApplicationTrackerPage } from './pages/applications/ApplicationTrackerPage';
import { CareerAssistantPage } from './pages/career/CareerAssistantPage';
import { InterviewStudioPage } from './pages/interview/InterviewStudioPage';
import { ReadinessAnalyticsPage } from './pages/readiness/ReadinessAnalyticsPage';
import { PreparationArenaPage } from './pages/arena/PreparationArenaPage';
import { TpoDashboard } from './pages/dashboards/TpoDashboard';
import { TpoJobsPage } from './pages/tpo/TpoJobsPage';
import { TpoDrivesPage } from './pages/tpo/TpoDrivesPage';
import { TpoReadinessPage } from './pages/tpo/TpoReadinessPage';
import { TpoArenaPage } from './pages/tpo/TpoArenaPage';
import { TpoIntelligencePage } from './pages/tpo/TpoIntelligencePage';
import { TpoReportsPage } from './pages/tpo/TpoReportsPage';
import { RecruiterDashboard } from './pages/dashboards/RecruiterDashboard';
import { RecruiterJobsPage } from './pages/recruiter/RecruiterJobsPage';
import { CandidatePipelinePage } from './pages/recruiter/CandidatePipelinePage';
import { CandidateWorkspacePage } from './pages/recruiter/CandidateWorkspacePage';
import { CandidateComparisonPage } from './pages/recruiter/CandidateComparisonPage';
import { RecruiterInterviewsPage } from './pages/recruiter/RecruiterInterviewsPage';
import { TpoInterviewsPage } from './pages/tpo/TpoInterviewsPage';
import { AdminDashboard } from './pages/dashboards/AdminDashboard';
import { AdminAuditDashboardPage } from './pages/admin/AdminAuditDashboardPage';
import { TpoActivityLogPage } from './pages/tpo/TpoActivityLogPage';
import { SettingsPage } from './pages/settings/SettingsPage';

export const App: React.FC = () => {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <AuthProvider>
          <AcademicProvider>
            <Routes>
          {/* Public Views */}
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          {/* Student Dashboard Routes (Protected) */}
          <Route
            path="/dashboard/student"
            element={
              <ProtectedRoute allowedRoles={['student']}>
                <StudentDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/student"
            element={
              <ProtectedRoute allowedRoles={['student']}>
                <StudentDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/student/profile"
            element={
              <ProtectedRoute allowedRoles={['student']}>
                <AcademicProfilePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/student/profile"
            element={
              <ProtectedRoute allowedRoles={['student']}>
                <AcademicProfilePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/student/resumes"
            element={
              <ProtectedRoute allowedRoles={['student']}>
                <ResumeIntelligencePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/student/resumes"
            element={
              <ProtectedRoute allowedRoles={['student']}>
                <ResumeIntelligencePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/student/jobs"
            element={
              <ProtectedRoute allowedRoles={['student']}>
                <ExploreJobsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/student/jobs"
            element={
              <ProtectedRoute allowedRoles={['student']}>
                <ExploreJobsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/student/career-assistant"
            element={
              <ProtectedRoute allowedRoles={['student']}>
                <CareerAssistantPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/student/career-assistant"
            element={
              <ProtectedRoute allowedRoles={['student']}>
                <CareerAssistantPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/student/interview-studio"
            element={
              <ProtectedRoute allowedRoles={['student']}>
                <InterviewStudioPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/student/interview-studio"
            element={
              <ProtectedRoute allowedRoles={['student']}>
                <InterviewStudioPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/student/readiness"
            element={
              <ProtectedRoute allowedRoles={['student']}>
                <ReadinessAnalyticsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/student/readiness"
            element={
              <ProtectedRoute allowedRoles={['student']}>
                <ReadinessAnalyticsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/student/applications"
            element={
              <ProtectedRoute allowedRoles={['student']}>
                <ApplicationTrackerPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/student/applications"
            element={
              <ProtectedRoute allowedRoles={['student']}>
                <ApplicationTrackerPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/student/arena"
            element={
              <ProtectedRoute allowedRoles={['student']}>
                <PreparationArenaPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/student/arena"
            element={
              <ProtectedRoute allowedRoles={['student']}>
                <PreparationArenaPage />
              </ProtectedRoute>
            }
          />

          {/* TPO Dashboard Routes (Protected: TPO and Admin) */}
          <Route
            path="/dashboard/tpo"
            element={
              <ProtectedRoute allowedRoles={['tpo', 'admin']}>
                <TpoDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/tpo"
            element={
              <ProtectedRoute allowedRoles={['tpo', 'admin']}>
                <TpoDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/tpo/jobs"
            element={
              <ProtectedRoute allowedRoles={['tpo', 'admin']}>
                <TpoJobsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/tpo/drives"
            element={
              <ProtectedRoute allowedRoles={['tpo', 'admin']}>
                <TpoDrivesPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/tpo/drives"
            element={
              <ProtectedRoute allowedRoles={['tpo', 'admin']}>
                <TpoDrivesPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/tpo/readiness"
            element={
              <ProtectedRoute allowedRoles={['tpo', 'admin']}>
                <TpoReadinessPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/tpo/readiness"
            element={
              <ProtectedRoute allowedRoles={['tpo', 'admin']}>
                <TpoReadinessPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/tpo/arena"
            element={
              <ProtectedRoute allowedRoles={['tpo', 'admin']}>
                <TpoArenaPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/tpo/arena"
            element={
              <ProtectedRoute allowedRoles={['tpo', 'admin']}>
                <TpoArenaPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/tpo/intelligence"
            element={
              <ProtectedRoute allowedRoles={['tpo', 'admin']}>
                <TpoIntelligencePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/tpo/intelligence"
            element={
              <ProtectedRoute allowedRoles={['tpo', 'admin']}>
                <TpoIntelligencePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/tpo/jobs"
            element={
              <ProtectedRoute allowedRoles={['tpo', 'admin']}>
                <TpoJobsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/tpo/companies"
            element={
              <ProtectedRoute allowedRoles={['tpo', 'admin']}>
                <TpoJobsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/tpo/reports"
            element={
              <ProtectedRoute allowedRoles={['tpo', 'admin']}>
                <TpoReportsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/tpo/reports"
            element={
              <ProtectedRoute allowedRoles={['tpo', 'admin']}>
                <TpoReportsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/tpo/interviews"
            element={
              <ProtectedRoute allowedRoles={['tpo', 'admin']}>
                <TpoInterviewsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/tpo/interviews"
            element={
              <ProtectedRoute allowedRoles={['tpo', 'admin']}>
                <TpoInterviewsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/tpo/activity-logs"
            element={
              <ProtectedRoute allowedRoles={['tpo', 'admin']}>
                <TpoActivityLogPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/tpo/activity-logs"
            element={
              <ProtectedRoute allowedRoles={['tpo', 'admin']}>
                <TpoActivityLogPage />
              </ProtectedRoute>
            }
          />

          {/* Recruiter Hub Routes (Protected: Recruiter) */}
          <Route
            path="/dashboard/recruiter"
            element={
              <ProtectedRoute allowedRoles={['recruiter']}>
                <RecruiterDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/recruiter"
            element={
              <ProtectedRoute allowedRoles={['recruiter']}>
                <RecruiterDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/recruiter/jobs"
            element={
              <ProtectedRoute allowedRoles={['recruiter']}>
                <RecruiterJobsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/recruiter/jobs"
            element={
              <ProtectedRoute allowedRoles={['recruiter']}>
                <RecruiterJobsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/recruiter/candidates"
            element={
              <ProtectedRoute allowedRoles={['recruiter', 'admin']}>
                <CandidatePipelinePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/recruiter/candidates"
            element={
              <ProtectedRoute allowedRoles={['recruiter', 'admin']}>
                <CandidatePipelinePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/recruiter/candidates/:applicationId"
            element={
              <ProtectedRoute allowedRoles={['recruiter', 'admin']}>
                <CandidateWorkspacePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/recruiter/candidates/:applicationId"
            element={
              <ProtectedRoute allowedRoles={['recruiter', 'admin']}>
                <CandidateWorkspacePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/recruiter/candidate-comparisons"
            element={
              <ProtectedRoute allowedRoles={['recruiter', 'admin']}>
                <CandidateComparisonPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/recruiter/candidate-comparisons"
            element={
              <ProtectedRoute allowedRoles={['recruiter', 'admin']}>
                <CandidateComparisonPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/recruiter/candidates/compare"
            element={
              <ProtectedRoute allowedRoles={['recruiter', 'admin']}>
                <CandidateComparisonPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/recruiter/interviews"
            element={
              <ProtectedRoute allowedRoles={['recruiter', 'admin']}>
                <RecruiterInterviewsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/recruiter/interviews"
            element={
              <ProtectedRoute allowedRoles={['recruiter', 'admin']}>
                <RecruiterInterviewsPage />
              </ProtectedRoute>
            }
          />

          {/* Admin Dashboard Routes (Protected: Admin) */}
          <Route
            path="/dashboard/admin"
            element={
              <ProtectedRoute allowedRoles={['admin']}>
                <AdminDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin"
            element={
              <ProtectedRoute allowedRoles={['admin']}>
                <AdminDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/audit-logs"
            element={
              <ProtectedRoute allowedRoles={['admin']}>
                <AdminAuditDashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/admin/audit-logs"
            element={
              <ProtectedRoute allowedRoles={['admin']}>
                <AdminAuditDashboardPage />
              </ProtectedRoute>
            }
          />

          {/* Account & App Settings (Protected: All Authenticated Roles) */}
          <Route
            path="/settings"
            element={
              <ProtectedRoute allowedRoles={['student', 'tpo', 'recruiter', 'admin']}>
                <SettingsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/student/settings"
            element={
              <ProtectedRoute allowedRoles={['student']}>
                <SettingsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/tpo/settings"
            element={
              <ProtectedRoute allowedRoles={['tpo', 'admin']}>
                <SettingsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/recruiter/settings"
            element={
              <ProtectedRoute allowedRoles={['recruiter']}>
                <SettingsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/settings"
            element={
              <ProtectedRoute allowedRoles={['admin']}>
                <SettingsPage />
              </ProtectedRoute>
            }
          />

            {/* Fallback Catch-all */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
          </AcademicProvider>
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  );
};

export default App;
