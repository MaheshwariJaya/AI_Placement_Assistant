import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { DashboardLayout } from '../../components/layout/DashboardLayout';
import { Card, CardHeader } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { useAuth } from '../../context/AuthContext';
import { companyApi, placementApi } from '../../services/api';
import { RecruiterOverviewResponse, RecruiterProfile } from '../../types';
import {
  Briefcase,
  Users,
  CheckCircle,
  Clock,
  Plus,
  Building,
  RefreshCw,
} from 'lucide-react';

const STATUS_BADGE_VARIANT: Record<string, 'success' | 'warning' | 'danger' | 'brand' | 'neutral'> = {
  offer_accepted: 'success',
  offered: 'success',
  shortlisted: 'brand',
  interview_scheduled: 'warning',
  applied: 'neutral',
  rejected: 'danger',
  offer_declined: 'danger',
  withdrawn: 'neutral',
};

export const RecruiterDashboard: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const recruiterName = user?.full_name || 'Recruiter';
  const [profile, setProfile] = useState<RecruiterProfile | null>(null);
  const [overview, setOverview] = useState<RecruiterOverviewResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    try {
      const [profRes, overRes] = await Promise.allSettled([
        companyApi.getMyProfile(),
        placementApi.getRecruiterOverview(),
      ]);
      setProfile(profRes.status === 'fulfilled' ? profRes.value : null);
      setOverview(overRes.status === 'fulfilled' ? overRes.value : null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  const activeJobsCount = overview?.active_jobs_count ?? 0;
  const totalApplicants = overview?.total_applicants ?? 0;
  const shortlistedCount = overview?.shortlisted_count ?? 0;
  const offersReleased = overview?.offers_released ?? 0;
  const recentApps = overview?.recent_applications ?? [];

  return (
    <DashboardLayout
      role="recruiter"
      title="Recruiter Hiring Command Center"
      subtitle="Corporate Scope: Manage campus recruitment drives, review scored applicants, and advance hiring pipelines."
    >
      {/* Corporate Summary Card */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-xl p-5 mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-sm">
        <div className="flex items-center gap-3.5">
          <div className="w-12 h-12 rounded-xl bg-sky-50 dark:bg-sky-950/60 text-sky-600 dark:text-sky-400 flex items-center justify-center font-bold text-lg border border-sky-100 dark:border-sky-900">
            <Building className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
                {profile?.company?.name || overview?.company_name || 'Campus Hiring Portal'}
              </h2>
              <Badge variant={profile?.company ? 'success' : 'warning'}>
                {profile?.company ? 'Verified Corporate Partner' : 'Company Setup Pending'}
              </Badge>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Authorized Recruiter: {recruiterName} {profile?.designation ? `(${profile.designation})` : ''}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={loadDashboard}
            disabled={loading}
            icon={<RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />}
          >
            Refresh
          </Button>
          <Button
            size="sm"
            onClick={() => navigate('/recruiter/jobs')}
            icon={<Plus className="w-3.5 h-3.5" />}
          >
            Manage Job Postings
          </Button>
        </div>
      </div>

      {/* KPI Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Card>
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Active Job Openings</span>
            <span className="w-8 h-8 rounded-lg bg-sky-50 dark:bg-sky-950/60 text-sky-600 dark:text-sky-400 flex items-center justify-center">
              <Briefcase className="w-4 h-4" />
            </span>
          </div>
          <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-2">{loading ? '...' : activeJobsCount}</div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
            {activeJobsCount === 0 ? 'No published job postings yet' : `${activeJobsCount} published to students`}
          </p>
        </Card>

        <Card>
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Total Applicants</span>
            <span className="w-8 h-8 rounded-lg bg-brand-50 dark:bg-brand-950/60 text-brand-600 dark:text-brand-400 flex items-center justify-center">
              <Users className="w-4 h-4" />
            </span>
          </div>
          <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-2">{loading ? '...' : totalApplicants}</div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
            {totalApplicants === 0 ? 'Awaiting student applications' : 'Live active applications'}
          </p>
        </Card>

        <Card>
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Shortlisted Candidates</span>
            <span className="w-8 h-8 rounded-lg bg-amber-50 dark:bg-amber-950/60 text-amber-600 dark:text-amber-400 flex items-center justify-center">
              <Clock className="w-4 h-4" />
            </span>
          </div>
          <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-2">{loading ? '...' : shortlistedCount}</div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
            {shortlistedCount === 0 ? 'No shortlisted candidates yet' : 'In screening or interviews'}
          </p>
        </Card>

        <Card>
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Final Offers Released</span>
            <span className="w-8 h-8 rounded-lg bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 flex items-center justify-center">
              <CheckCircle className="w-4 h-4" />
            </span>
          </div>
          <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-2">{loading ? '...' : offersReleased}</div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
            {offersReleased === 0
              ? 'No offers released yet'
              : `${overview?.offers_accepted ?? 0} accepted by candidates`}
          </p>
        </Card>
      </div>

      {/* Applicant Review Pipeline */}
      <Card>
        <CardHeader
          title="Candidate Evaluation Pipeline"
          subtitle="Live applicant pipeline ranked from submitted applications and deterministic screening"
          action={
            <Button
              size="sm"
              variant="outline"
              onClick={() => navigate('/recruiter/candidates')}
            >
              Open Candidate Pipeline
            </Button>
          }
        />
        <div className="overflow-x-auto mt-4">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400 font-semibold uppercase tracking-wider bg-slate-50/75 dark:bg-slate-800/70">
                <th className="py-2.5 px-3">Candidate</th>
                <th className="py-2.5 px-3">Role Applied</th>
                <th className="py-2.5 px-3">Department</th>
                <th className="py-2.5 px-3">TPO Screening</th>
                <th className="py-2.5 px-3">Compatibility Score</th>
                <th className="py-2.5 px-3">Pipeline Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {recentApps.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-10 text-center text-slate-500 dark:text-slate-400 text-xs">
                    No candidate applications received yet. Applicants will appear here once candidates apply to your published job postings.
                  </td>
                </tr>
              ) : (
                recentApps.map((app) => (
                  <tr
                    key={app.id}
                    className="hover:bg-slate-50/80 dark:hover:bg-slate-800/50 transition-colors cursor-pointer"
                    onClick={() => navigate(`/recruiter/candidates/${app.id}`)}
                  >
                    <td className="py-2.5 px-3">
                      <div className="font-semibold text-slate-900 dark:text-slate-100">{app.student_name || 'Student Candidate'}</div>
                      <div className="text-[11px] text-slate-500 dark:text-slate-400 font-mono">
                        {app.student_roll_number || app.student_email || `ID #${app.student_id}`}
                      </div>
                    </td>
                    <td className="py-2.5 px-3 text-slate-800 dark:text-slate-200 font-medium">{app.job_title || `Job #${app.job_id}`}</td>
                    <td className="py-2.5 px-3 text-slate-600 dark:text-slate-400">{app.student_department || '—'}</td>
                    <td className="py-2.5 px-3">
                      <Badge
                        variant={
                          app.tpo_screening_status === 'shortlisted'
                            ? 'success'
                            : app.tpo_screening_status === 'rejected'
                            ? 'danger'
                            : app.tpo_screening_status === 'pending'
                            ? 'warning'
                            : 'neutral'
                        }
                      >
                        {app.tpo_screening_status === 'bypassed'
                          ? 'DIRECT'
                          : app.tpo_screening_status.replace(/_/g, ' ').toUpperCase()}
                      </Badge>
                    </td>
                    <td className="py-2.5 px-3 font-semibold text-slate-900 dark:text-slate-100">
                      {app.compatibility_score_at_application.toFixed(1)}%
                    </td>
                    <td className="py-2.5 px-3">
                      <Badge variant={STATUS_BADGE_VARIANT[app.current_status] || 'neutral'}>
                        {app.current_status.replace(/_/g, ' ').toUpperCase()}
                      </Badge>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </DashboardLayout>
  );
};
