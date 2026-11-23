import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { DashboardLayout } from '../../components/layout/DashboardLayout';
import { Card } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { intelligenceApi, resumeApi, applicationApi, driveApi } from '../../services/api';
import {
  JobRecommendationCard,
  JobRecommendationListResponse,
  JobMatchEvaluationResponse,
  Resume,
  RecruiterOverviewApplication,
  PlacementDrive,
  DriveRegistrationItem,
  DriveActivityItem,
  DriveAnnouncementItem,
} from '../../types';
import {
  Briefcase,
  Building,
  Search,
  MapPin,
  Calendar,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Clock,
  Sparkles,
  ChevronRight,
  X,
  Award,
  BookOpen,
  Code2,
  RefreshCw,
  Layers,
  ArrowUpRight,
} from 'lucide-react';

export const ExploreJobsPage: React.FC = () => {
  const [recommendations, setRecommendations] = useState<JobRecommendationListResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Tab & Filter States
  const [activeTab, setActiveTab] = useState<'eligible' | 'ineligible' | 'all' | 'applications' | 'drives'>('eligible');
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [modeFilter, setModeFilter] = useState<string>('all');

  // Campus Drives Registration & Schedule State
  const [campusDrives, setCampusDrives] = useState<PlacementDrive[]>([]);
  const [driveRegistrations, setDriveRegistrations] = useState<Record<number, DriveRegistrationItem>>({});
  const [driveExtras, setDriveExtras] = useState<
    Record<number, { activities: DriveActivityItem[]; announcements: DriveAnnouncementItem[] }>
  >({});
  const [registeringDriveId, setRegisteringDriveId] = useState<number | null>(null);
  const [driveFeedback, setDriveFeedback] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Detail Modal & Comprehensive Match Evaluation State
  const [selectedCard, setSelectedCard] = useState<JobRecommendationCard | null>(null);
  const [evaluation, setEvaluation] = useState<JobMatchEvaluationResponse | null>(null);
  const [isEvaluating, setIsEvaluating] = useState<boolean>(false);
  const [evalError, setEvalError] = useState<string | null>(null);

  // Student Application State
  const [approvedResumes, setApprovedResumes] = useState<Resume[]>([]);
  const [selectedResumeId, setSelectedResumeId] = useState<number | null>(null);
  const [myApplications, setMyApplications] = useState<RecruiterOverviewApplication[]>([]);
  const [appliedMap, setAppliedMap] = useState<Record<number, RecruiterOverviewApplication>>({});
  const [isApplying, setIsApplying] = useState<boolean>(false);
  const [respondingAppId, setRespondingAppId] = useState<number | null>(null);
  const [applyFeedback, setApplyFeedback] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const fetchRecommendations = async () => {
    setIsLoading(true);
    setFetchError(null);
    try {
      const [recRes, resumesRes, appsRes, drivesRes] = await Promise.allSettled([
        intelligenceApi.getRecommendations(),
        resumeApi.getResumes(),
        applicationApi.getMyApplications(),
        driveApi.listDrives({ limit: 50 }),
      ]);

      if (recRes.status === 'fulfilled') {
        setRecommendations(recRes.value);
      } else {
        throw recRes.reason;
      }

      if (resumesRes.status === 'fulfilled') {
        const approved = resumesRes.value.filter(
          (r) => r.parsing_status === 'approved' && r.is_active
        );
        setApprovedResumes(approved);
        if (approved.length > 0) {
          setSelectedResumeId((prev) => prev ?? approved[0].id);
        }
      }

      if (appsRes.status === 'fulfilled') {
        setMyApplications(appsRes.value.items);
        const map: Record<number, RecruiterOverviewApplication> = {};
        for (const app of appsRes.value.items) {
          map[app.job_id] = app;
        }
        setAppliedMap(map);
      }

      if (drivesRes.status === 'fulfilled') {
        setCampusDrives(drivesRes.value);
        const regEntries = await Promise.allSettled(
          drivesRes.value.map(async (d) => ({
            driveId: d.id,
            regs: await driveApi.getRegistrations(d.id),
          }))
        );
        const regMap: Record<number, DriveRegistrationItem> = {};
        regEntries.forEach((r) => {
          if (r.status === 'fulfilled' && r.value.regs.length > 0) {
            regMap[r.value.driveId] = r.value.regs[0];
          }
        });
        setDriveRegistrations(regMap);
      }
    } catch (err: any) {
      console.error('Failed to load placement recommendations:', err);
      const detailMsg =
        err.response?.data?.detail?.message ||
        (typeof err.response?.data?.detail === 'string' ? err.response?.data?.detail : null) ||
        'Unable to load job recommendations. Please ensure your student profile is up to date.';
      setFetchError(detailMsg);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchRecommendations();
  }, []);

  const handleOpenJobModal = async (jobCard: JobRecommendationCard) => {
    setSelectedCard(jobCard);
    setEvaluation(null);
    setEvalError(null);
    setApplyFeedback(null);
    setIsEvaluating(true);

    try {
      const evalData = await intelligenceApi.evaluateJob(jobCard.job_id);
      setEvaluation(evalData);
    } catch (err: any) {
      console.error('Failed to evaluate candidate job match:', err);
      const msg =
        err.response?.data?.detail?.message ||
        'Could not evaluate complete criteria for this opportunity.';
      setEvalError(msg);
    } finally {
      setIsEvaluating(false);
    }
  };

  const handleApplyToJob = async () => {
    if (!selectedCard || !selectedResumeId) return;
    setIsApplying(true);
    setApplyFeedback(null);
    try {
      const created = await applicationApi.submitApplication({
        job_id: selectedCard.job_id,
        resume_id: selectedResumeId,
      });
      setAppliedMap((prev) => ({ ...prev, [selectedCard.job_id]: created }));
      setMyApplications((prev) => [created, ...prev.filter((a) => a.job_id !== created.job_id)]);
      setApplyFeedback({
        type: 'success',
        text: `Application submitted for ${selectedCard.title} at ${selectedCard.company_name}.`,
      });
    } catch (err: any) {
      const msg =
        err.response?.data?.error?.message ||
        err.response?.data?.detail?.message ||
        (typeof err.response?.data?.detail === 'string' ? err.response?.data?.detail : null) ||
        'Failed to submit application.';
      setApplyFeedback({ type: 'error', text: msg });
    } finally {
      setIsApplying(false);
    }
  };

  const handleRegisterForDrive = async (drive: PlacementDrive) => {
    setRegisteringDriveId(drive.id);
    setDriveFeedback(null);
    try {
      const reg = await driveApi.studentRegister(drive.id);
      setDriveRegistrations((prev) => ({ ...prev, [drive.id]: reg }));
      setDriveFeedback({
        type: 'success',
        text: `Successfully registered for "${drive.name}".`,
      });
    } catch (err: any) {
      const msg =
        err.response?.data?.message ||
        err.response?.data?.detail?.message ||
        (typeof err.response?.data?.detail === 'string' ? err.response?.data?.detail : null) ||
        'Registration could not be completed.';
      setDriveFeedback({ type: 'error', text: msg });
    } finally {
      setRegisteringDriveId(null);
    }
  };

  const handleToggleDriveDetails = async (driveId: number) => {
    if (driveExtras[driveId]) {
      setDriveExtras((prev) => {
        const next = { ...prev };
        delete next[driveId];
        return next;
      });
      return;
    }
    try {
      const [activities, announcements] = await Promise.all([
        driveApi.listActivities(driveId),
        driveApi.listAnnouncements(driveId),
      ]);
      setDriveExtras((prev) => ({ ...prev, [driveId]: { activities, announcements } }));
    } catch (err) {
      console.error('Failed to load drive schedule/announcements', err);
    }
  };

  const handleOfferResponse = async (applicationId: number, accept: boolean) => {
    setRespondingAppId(applicationId);
    setApplyFeedback(null);
    try {
      const updated = await applicationApi.respondToOffer(applicationId, accept);
      setMyApplications((prev) => prev.map((a) => (a.id === updated.id ? updated : a)));
      setAppliedMap((prev) => ({ ...prev, [updated.job_id]: updated }));
      setApplyFeedback({
        type: 'success',
        text: accept
          ? `Congratulations! You accepted the offer for ${updated.job_title || 'this role'} at ${updated.company_name || 'the company'}.`
          : `You declined the offer for ${updated.job_title || 'this role'}.`,
      });
    } catch (err: any) {
      const msg =
        err.response?.data?.error?.message ||
        err.response?.data?.detail?.message ||
        (typeof err.response?.data?.detail === 'string' ? err.response?.data?.detail : null) ||
        'Failed to submit offer response.';
      setApplyFeedback({ type: 'error', text: msg });
    } finally {
      setRespondingAppId(null);
    }
  };

  // Determine active list based on selected tab
  const getActiveJobsList = (): JobRecommendationCard[] => {
    if (!recommendations) return [];
    if (activeTab === 'eligible') {
      return recommendations.eligible_jobs;
    }
    if (activeTab === 'ineligible') {
      return recommendations.ineligible_jobs;
    }
    // 'all' tab: eligible first, then ineligible
    return [...recommendations.eligible_jobs, ...recommendations.ineligible_jobs];
  };

  // Filter jobs by search and dropdowns
  const activeJobs = getActiveJobsList();
  const filteredJobs = activeJobs.filter((j) => {
    const matchesSearch =
      !searchQuery ||
      j.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      j.company_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      j.location.toLowerCase().includes(searchQuery.toLowerCase()) ||
      j.matched_skills.some((s) => s.toLowerCase().includes(searchQuery.toLowerCase())) ||
      j.missing_mandatory_skills.some((s) => s.toLowerCase().includes(searchQuery.toLowerCase()));

    const matchesType = typeFilter === 'all' || j.employment_type === typeFilter;
    const matchesMode = modeFilter === 'all' || j.work_mode === modeFilter;

    return matchesSearch && matchesType && matchesMode;
  });

  const getScoreBadgeColor = (score: number) => {
    if (score >= 75) return 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800/60';
    if (score >= 50) return 'bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 border-blue-200 dark:border-blue-800/60';
    if (score >= 30) return 'bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-800/60';
    return 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700';
  };

  return (
    <DashboardLayout
      role="student"
      title="Explore Campus Placement Drives"
      subtitle="Placement Intelligence: Explore personalized opportunities ranked by continuous compatibility, inspect academic cutoffs, and audit criteria."
    >
      {/* Search & Filter Bar */}
      <Card className="mb-6">
        <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3">
          {/* Tab Selection */}
          <div className="flex items-center space-x-1.5 p-1 bg-slate-100/80 dark:bg-slate-800/80 rounded-xl overflow-x-auto">
            <button
              onClick={() => setActiveTab('eligible')}
              className={`px-3.5 py-2 text-xs font-semibold rounded-lg transition-all flex items-center gap-1.5 whitespace-nowrap ${activeTab === 'eligible'
                  ? 'bg-white dark:bg-slate-900 text-brand-700 dark:text-brand-300 shadow-xs'
                  : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100'
                }`}
            >
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
              <span>Eligible For You</span>
              {recommendations && (
                <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] bg-emerald-100 dark:bg-emerald-900/50 text-emerald-800 dark:text-emerald-300 font-bold">
                  {recommendations.total_eligible}
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab('ineligible')}
              className={`px-3.5 py-2 text-xs font-semibold rounded-lg transition-all flex items-center gap-1.5 whitespace-nowrap ${activeTab === 'ineligible'
                  ? 'bg-white dark:bg-slate-900 text-rose-700 dark:text-rose-300 shadow-xs'
                  : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100'
                }`}
            >
              <XCircle className="w-3.5 h-3.5 text-rose-500 dark:text-rose-400" />
              <span>Ineligible (Cutoffs Not Met)</span>
              {recommendations && (
                <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] bg-rose-100 dark:bg-rose-900/50 text-rose-800 dark:text-rose-300 font-bold">
                  {recommendations.total_ineligible}
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab('all')}
              className={`px-3.5 py-2 text-xs font-semibold rounded-lg transition-all flex items-center gap-1.5 whitespace-nowrap ${activeTab === 'all'
                  ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 shadow-xs'
                  : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100'
                }`}
            >
              <Layers className="w-3.5 h-3.5 text-slate-500 dark:text-slate-400" />
              <span>All Opportunities</span>
              {recommendations && (
                <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] bg-slate-200 dark:bg-slate-700 text-slate-800 dark:text-slate-200 font-bold">
                  {recommendations.total_eligible + recommendations.total_ineligible}
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab('applications')}
              className={`px-3.5 py-2 text-xs font-semibold rounded-lg transition-all flex items-center gap-1.5 whitespace-nowrap ${activeTab === 'applications'
                  ? 'bg-white dark:bg-slate-900 text-brand-700 dark:text-brand-300 shadow-xs'
                  : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100'
                }`}
            >
              <Award className="w-3.5 h-3.5 text-brand-600 dark:text-brand-400" />
              <span>My Applications</span>
              <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] bg-brand-100 dark:bg-brand-900/50 text-brand-800 dark:text-brand-300 font-bold">
                {myApplications.length}
              </span>
            </button>

            <button
              onClick={() => setActiveTab('drives')}
              className={`px-3.5 py-2 text-xs font-semibold rounded-lg transition-all flex items-center gap-1.5 whitespace-nowrap ${activeTab === 'drives'
                  ? 'bg-white dark:bg-slate-900 text-brand-700 dark:text-brand-300 shadow-xs'
                  : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100'
                }`}
            >
              <Calendar className="w-3.5 h-3.5 text-brand-600 dark:text-brand-400" />
              <span>Campus Drives</span>
              <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] bg-brand-100 dark:bg-brand-900/50 text-brand-800 dark:text-brand-300 font-bold">
                {campusDrives.length}
              </span>
            </button>
          </div>

          {/* Search Input & Select Dropdowns */}
          <div className="flex flex-col sm:flex-row items-center gap-2 flex-1 max-w-xl">
            <div className="relative flex-1 w-full">
              <Search className="w-4 h-4 text-slate-400 dark:text-slate-500 absolute left-3.5 top-3" />
              <input
                type="text"
                placeholder="Search by role, company, skills, or city..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full text-xs pl-10 pr-4 py-2.5 rounded-lg border border-slate-200 dark:border-slate-700 focus:outline-none focus:ring-1 focus:ring-brand-500 bg-slate-50/50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 dark:placeholder:text-slate-500"
              />
            </div>

            <div className="flex items-center gap-2 w-full sm:w-auto">
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="text-xs px-3 py-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 focus:outline-none flex-1 sm:flex-initial"
              >
                <option value="all">All Contracts</option>
                <option value="full_time">Full-Time</option>
                <option value="internship">Internship</option>
                <option value="intern_to_full_time">Intern to Full-Time</option>
              </select>

              <select
                value={modeFilter}
                onChange={(e) => setModeFilter(e.target.value)}
                className="text-xs px-3 py-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 focus:outline-none flex-1 sm:flex-initial"
              >
                <option value="all">All Modes</option>
                <option value="on_site">On-Site</option>
                <option value="hybrid">Hybrid</option>
                <option value="remote">Remote</option>
              </select>
            </div>
          </div>
        </div>
      </Card>

      {/* Error State Banner */}
      {fetchError && (
        <Card className="mb-6 border-amber-200 dark:border-amber-800/60 bg-amber-50 dark:bg-amber-950/30">
          <div className="flex items-start gap-3 p-2">
            <AlertCircle className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1 text-xs">
              <h4 className="font-bold text-amber-900 dark:text-amber-200">Placement Intelligence Notice</h4>
              <p className="text-amber-800 dark:text-amber-300/90 mt-0.5">{fetchError}</p>
              <div className="mt-3 flex items-center gap-2">
                <Button size="sm" variant="outline" onClick={fetchRecommendations}>
                  <RefreshCw className="w-3.5 h-3.5 mr-1" /> Retry
                </Button>
                <Link to="/student/resumes">
                  <Button size="sm" variant="primary">
                    Update Resume & Profile
                  </Button>
                </Link>
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Loading Skeleton */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Card key={i} className="animate-pulse space-y-4">
              <div className="flex justify-between items-start">
                <div className="space-y-2 w-3/4">
                  <div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-1/2"></div>
                  <div className="h-5 bg-slate-200 dark:bg-slate-800 rounded w-5/6"></div>
                </div>
                <div className="h-7 w-16 bg-slate-200 dark:bg-slate-800 rounded-full"></div>
              </div>
              <div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-1/3"></div>
              <div className="h-10 bg-slate-100 dark:bg-slate-800/70 rounded"></div>
              <div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-full"></div>
            </Card>
          ))}
        </div>
      ) : activeTab === 'applications' ? (
        (() => {
          const q = searchQuery.trim().toLowerCase();
          const filteredApps = myApplications.filter(
            (a) =>
              !q ||
              (a.job_title || '').toLowerCase().includes(q) ||
              (a.company_name || '').toLowerCase().includes(q) ||
              a.current_status.toLowerCase().includes(q)
          );
          if (filteredApps.length === 0) {
            return (
              <Card>
                <div className="text-center py-16 text-slate-400">
                  <Briefcase className="w-12 h-12 mx-auto mb-3 opacity-30 text-slate-500" />
                  <h3 className="text-sm font-bold text-slate-700">No Applications Found</h3>
                  <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
                    Explore eligible opportunities and click Apply Now inside a job card to track your hiring status and offers here.
                  </p>
                </div>
              </Card>
            );
          }

          return (
            <div className="space-y-4">
              {applyFeedback && (
                <div
                  className={`p-3 rounded-xl border text-xs flex items-center gap-2 ${
                    applyFeedback.type === 'success'
                      ? 'bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-800/60 text-emerald-800 dark:text-emerald-300'
                      : 'bg-rose-50 dark:bg-rose-950/40 border-rose-200 dark:border-rose-800/60 text-rose-800 dark:text-rose-300'
                  }`}
                >
                  {applyFeedback.type === 'success' ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
                  ) : (
                    <AlertCircle className="w-4 h-4 text-rose-600 dark:text-rose-400 shrink-0" />
                  )}
                  <span>{applyFeedback.text}</span>
                </div>
              )}

              <div className="flex flex-wrap items-center justify-between gap-2 bg-brand-50/70 dark:bg-brand-950/30 border border-brand-200 dark:border-brand-800/70 rounded-xl px-4 py-2.5 text-xs">
                <span className="text-slate-700 dark:text-slate-200">
                  Track full chronological history, interview schedules, calendar deadlines, and smart alerts in the centralized tracker.
                </span>
                <Link
                  to="/student/applications"
                  className="font-semibold text-brand-700 dark:text-brand-300 hover:underline whitespace-nowrap"
                >
                  Open Smart Application Tracker →
                </Link>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {filteredApps.map((app) => {
                  const statusTone =
                    app.current_status === 'offer_accepted' || app.current_status === 'offered'
                      ? 'success'
                      : app.current_status === 'rejected' || app.current_status === 'offer_declined'
                      ? 'danger'
                      : app.current_status === 'shortlisted' || app.current_status === 'interview_scheduled' || app.current_status === 'interviewed'
                      ? 'warning'
                      : 'neutral';

                  return (
                    <Card key={app.id} className="space-y-3">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 flex items-center gap-1">
                            <Building className="w-3.5 h-3.5 text-slate-400 dark:text-slate-500" />
                            <span>{app.company_name || 'Hiring Partner'}</span>
                          </div>
                          <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 mt-0.5">
                            {app.job_title || `Job #${app.job_id}`}
                          </h3>
                          {app.drive_name && (
                            <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">{app.drive_name}</p>
                          )}
                        </div>
                        <Badge variant={statusTone}>
                          {app.current_status.replace(/_/g, ' ').toUpperCase()}
                        </Badge>
                      </div>

                      <div className="flex flex-wrap items-center justify-between gap-2 text-xs bg-slate-50 dark:bg-slate-800/60 p-2.5 rounded-lg border border-slate-100 dark:border-slate-700/80">
                        <span className="text-slate-600 dark:text-slate-300">
                          Match at Application:{' '}
                          <strong className="text-slate-900 dark:text-slate-100">
                            {app.compatibility_score_at_application.toFixed(1)}%
                          </strong>
                        </span>
                        <span className="text-[11px] text-slate-500 dark:text-slate-400">
                          TPO Screening:{' '}
                          <strong className="uppercase">{app.tpo_screening_status}</strong>
                        </span>
                      </div>

                      <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-100 dark:border-slate-800 text-[11px]">
                        <span className="text-slate-400 dark:text-slate-500">
                          Applied {new Date(app.created_at).toLocaleDateString()}
                        </span>

                        {app.current_status === 'offered' && (
                          <div className="flex items-center gap-2">
                            <Button
                              size="sm"
                              variant="primary"
                              disabled={respondingAppId === app.id}
                              onClick={() => handleOfferResponse(app.id, true)}
                            >
                              {respondingAppId === app.id ? 'Updating...' : 'Accept Offer'}
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              disabled={respondingAppId === app.id}
                              onClick={() => handleOfferResponse(app.id, false)}
                            >
                              Decline Offer
                            </Button>
                          </div>
                        )}
                      </div>
                    </Card>
                  );
                })}
              </div>
            </div>
          );
        })()
      ) : activeTab === 'drives' ? (
        <div className="space-y-4">
          {driveFeedback && (
            <div
              className={`p-3 rounded-xl border text-xs flex items-center gap-2 ${
                driveFeedback.type === 'success'
                  ? 'bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-800/60 text-emerald-800 dark:text-emerald-300'
                  : 'bg-rose-50 dark:bg-rose-950/40 border-rose-200 dark:border-rose-800/60 text-rose-800 dark:text-rose-300'
              }`}
            >
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{driveFeedback.text}</span>
            </div>
          )}

          {campusDrives.length === 0 ? (
            <Card>
              <div className="text-center py-14 text-slate-400">
                <Calendar className="w-10 h-10 mx-auto mb-3 opacity-30" />
                <h3 className="text-sm font-bold text-slate-700 dark:text-slate-200">
                  No Active Campus Drives Right Now
                </h3>
                <p className="text-xs text-slate-500 mt-1">
                  When your Training & Placement Office publishes a drive, you can register and track its schedule here.
                </p>
              </div>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {campusDrives
                .filter((d) => {
                  const q = searchQuery.trim().toLowerCase();
                  return (
                    !q ||
                    d.name.toLowerCase().includes(q) ||
                    (d.venue_location || '').toLowerCase().includes(q)
                  );
                })
                .map((drive) => {
                  const reg = driveRegistrations[drive.id];
                  const extras = driveExtras[drive.id];
                  const phase = (drive.lifecycle_phase || drive.status).replace(/_/g, ' ');
                  return (
                    <Card key={drive.id} className="space-y-3">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                            {drive.name}
                          </h3>
                          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                            {drive.academic_year} · Batch {drive.target_graduation_year} ·{' '}
                            {drive.drive_mode.replace(/_/g, ' ')}
                          </p>
                        </div>
                        <Badge variant={reg ? 'success' : 'brand'} size="sm">
                          {reg ? 'Registered' : phase}
                        </Badge>
                      </div>

                      <div className="text-xs text-slate-600 dark:text-slate-300 space-y-1">
                        <div className="flex items-center gap-1.5">
                          <Clock className="w-3.5 h-3.5 text-slate-400" />
                          <span>
                            Registration: {new Date(drive.registration_start_date).toLocaleDateString()} –{' '}
                            {new Date(drive.registration_end_date).toLocaleDateString()}
                          </span>
                        </div>
                        {drive.venue_location && (
                          <div className="flex items-center gap-1.5">
                            <MapPin className="w-3.5 h-3.5 text-slate-400" />
                            <span>{drive.venue_location}</span>
                          </div>
                        )}
                        {drive.required_documents?.length > 0 && (
                          <div className="text-[11px] text-slate-500">
                            Required docs: {drive.required_documents.join(', ')}
                          </div>
                        )}
                      </div>

                      {drive.instructions && (
                        <p className="text-xs text-slate-600 dark:text-slate-400 bg-slate-50 dark:bg-slate-800/60 p-2.5 rounded-lg">
                          {drive.instructions}
                        </p>
                      )}

                      <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-100 dark:border-slate-800">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleToggleDriveDetails(drive.id)}
                        >
                          {extras ? 'Hide Schedule & Updates' : 'View Schedule & Updates'}
                        </Button>

                        {reg ? (
                          <span className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-600 dark:text-emerald-400">
                            <CheckCircle2 className="w-4 h-4" /> Registered ({new Date(reg.registered_at).toLocaleDateString()})
                          </span>
                        ) : (
                          <Button
                            size="sm"
                            variant="primary"
                            disabled={registeringDriveId === drive.id}
                            onClick={() => handleRegisterForDrive(drive)}
                          >
                            {registeringDriveId === drive.id ? 'Validating...' : 'Register for Drive'}
                          </Button>
                        )}
                      </div>

                      {extras && (
                        <div className="pt-3 border-t border-slate-100 dark:border-slate-800 space-y-3 text-xs">
                          <div>
                            <div className="font-semibold text-slate-700 dark:text-slate-200 mb-1">
                              Scheduled Activities ({extras.activities.length})
                            </div>
                            {extras.activities.length === 0 ? (
                              <div className="text-slate-400">No sessions scheduled yet.</div>
                            ) : (
                              <ul className="space-y-1">
                                {extras.activities.map((a) => (
                                  <li key={a.id} className="text-slate-600 dark:text-slate-300">
                                    • <strong>{a.title}</strong> ({new Date(a.scheduled_start).toLocaleString()})
                                    {a.venue ? ` · ${a.venue}` : ''}
                                  </li>
                                ))}
                              </ul>
                            )}
                          </div>

                          <div>
                            <div className="font-semibold text-slate-700 dark:text-slate-200 mb-1">
                              Drive Announcements ({extras.announcements.length})
                            </div>
                            {extras.announcements.length === 0 ? (
                              <div className="text-slate-400">No announcements yet.</div>
                            ) : (
                              <ul className="space-y-1.5">
                                {extras.announcements.map((ann) => (
                                  <li
                                    key={ann.id}
                                    className="p-2 rounded bg-slate-50 dark:bg-slate-800/70"
                                  >
                                    <div className="font-medium text-slate-800 dark:text-slate-100">
                                      {ann.title}
                                    </div>
                                    <div className="text-slate-600 dark:text-slate-300">{ann.message}</div>
                                  </li>
                                ))}
                              </ul>
                            )}
                          </div>
                        </div>
                      )}
                    </Card>
                  );
                })}
            </div>
          )}
        </div>
      ) : filteredJobs.length === 0 ? (
        /* Empty State */
        <Card>
          <div className="text-center py-16 text-slate-400 dark:text-slate-500">
            <Briefcase className="w-12 h-12 mx-auto mb-3 opacity-30 text-slate-500 dark:text-slate-400" />
            <h3 className="text-sm font-bold text-slate-700 dark:text-slate-200">
              {activeTab === 'eligible'
                ? 'No eligible placement opportunities found'
                : activeTab === 'ineligible'
                  ? 'No ineligible opportunities found'
                  : 'No published opportunities match your filters'}
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-md mx-auto leading-relaxed">
              {activeTab === 'eligible'
                ? 'You do not satisfy cutoffs for any currently published drive, or no jobs have been published for your department yet. Inspect the "Ineligible" tab to see cutoff gaps.'
                : 'Try adjusting your search query, contract type, or work mode filters.'}
            </p>
            {activeTab === 'eligible' && recommendations && recommendations.total_ineligible > 0 && (
              <div className="mt-4">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setActiveTab('ineligible')}
                  icon={<XCircle className="w-3.5 h-3.5 text-rose-500" />}
                >
                  View Ineligible Opportunities ({recommendations.total_ineligible})
                </Button>
              </div>
            )}
          </div>
        </Card>
      ) : (
        /* Jobs Grid */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredJobs.map((job) => {
            const scoreColor = getScoreBadgeColor(job.compatibility_score);
            return (
              <div
                key={job.job_id}
                onClick={() => handleOpenJobModal(job)}
                className={`bg-white dark:bg-slate-900 rounded-xl border p-5 transition-all cursor-pointer flex flex-col justify-between group hover:shadow-md ${job.is_eligible
                    ? 'border-slate-200/90 dark:border-slate-800 hover:border-brand-300 dark:hover:border-brand-600'
                    : 'border-rose-200/80 dark:border-rose-800/60 bg-rose-50/20 dark:bg-rose-950/20 hover:border-rose-300 dark:hover:border-rose-700'
                  }`}
              >
                <div className="space-y-3">
                  {/* Card Header: Company, Location & Badges */}
                  <div>
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0 flex-1">
                        <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 flex items-center gap-1 truncate">
                          <Building className="w-3.5 h-3.5 text-slate-400 dark:text-slate-500 flex-shrink-0" />
                          <span className="truncate">{job.company_name}</span>
                        </span>
                        <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 group-hover:text-brand-600 dark:group-hover:text-brand-400 transition-colors line-clamp-1 mt-0.5">
                          {job.title}
                        </h3>
                      </div>

                      {/* Compatibility Score Pill */}
                      <div
                        className={`flex flex-col items-end px-2.5 py-1 rounded-lg border text-right ${scoreColor}`}
                      >
                        <span className="text-[10px] font-semibold uppercase tracking-wider">
                          Match
                        </span>
                        <span className="text-sm font-black leading-tight">
                          {job.compatibility_score.toFixed(1)}%
                        </span>
                      </div>
                    </div>

                    {/* Eligibility Status Pill (Separate from Compatibility) */}
                    <div className="mt-2 flex items-center justify-between gap-2">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        {job.is_eligible ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 dark:bg-emerald-950/50 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/60">
                            <CheckCircle2 className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
                            Eligible to Apply
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-100 dark:bg-rose-950/50 text-rose-800 dark:text-rose-300 border border-rose-200 dark:border-rose-800/60">
                            <XCircle className="w-3 h-3 text-rose-600 dark:text-rose-400" />
                            Cutoff Not Satisfied
                          </span>
                        )}
                        {job.relevance_tier === 'directly_relevant' && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                            Branch Match
                          </span>
                        )}
                        {job.relevance_tier === 'interdisciplinary' && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-purple-50 dark:bg-purple-950/50 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800">
                            Interdisciplinary
                          </span>
                        )}
                        {job.relevance_tier === 'open_to_all' && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-50 dark:bg-blue-950/50 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
                            Open to All
                          </span>
                        )}
                        {appliedMap[job.job_id] && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-brand-100 dark:bg-brand-950/50 text-brand-800 dark:text-brand-300 border border-brand-200 dark:border-brand-800/60">
                            Applied
                          </span>
                        )}
                      </div>

                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 capitalize">
                        {job.work_mode.replace(/_/g, ' ')}
                      </span>
                    </div>
                  </div>

                  {/* Compensation & Location */}
                  <div className="flex items-center justify-between text-xs pt-1 border-t border-slate-100 dark:border-slate-800">
                    <div className="font-bold text-slate-800 dark:text-slate-200">
                      {job.salary_range
                        ? `₹ ${job.salary_range}`
                        : job.ctc_lpa
                          ? `₹ ${job.ctc_lpa} LPA`
                          : 'Commensurate'}
                    </div>
                    <div className="flex items-center gap-1 text-slate-500 dark:text-slate-400 text-[11px] truncate max-w-[140px]">
                      <MapPin className="w-3 h-3 text-slate-400 dark:text-slate-500 flex-shrink-0" />
                      <span className="truncate">{job.location}</span>
                    </div>
                  </div>

                  {/* Skills Alignment Preview */}
                  <div className="space-y-1.5 pt-1 text-[11px]">
                    {job.matched_skills && job.matched_skills.length > 0 && (
                      <div className="flex flex-wrap items-center gap-1">
                        <span className="text-[10px] text-emerald-700 dark:text-emerald-400 font-semibold">Matched:</span>
                        {job.matched_skills.slice(0, 3).map((s, idx) => (
                          <span
                            key={idx}
                            className="px-1.5 py-0.2 rounded bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 font-medium text-[10px] border border-emerald-200 dark:border-emerald-800/60"
                          >
                            ✓ {s}
                          </span>
                        ))}
                        {job.matched_skills.length > 3 && (
                          <span className="text-[10px] text-slate-400 dark:text-slate-500">
                            +{job.matched_skills.length - 3}
                          </span>
                        )}
                      </div>
                    )}

                    {job.missing_mandatory_skills && job.missing_mandatory_skills.length > 0 && (
                      <div className="flex flex-wrap items-center gap-1">
                        <span className="text-[10px] text-rose-700 dark:text-rose-400 font-semibold">Missing:</span>
                        {job.missing_mandatory_skills.slice(0, 2).map((s, idx) => (
                          <span
                            key={idx}
                            className="px-1.5 py-0.2 rounded bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-300 font-medium text-[10px] border border-rose-200 dark:border-rose-800/60"
                          >
                            ✕ {s}
                          </span>
                        ))}
                        {job.missing_mandatory_skills.length > 2 && (
                          <span className="text-[10px] text-rose-500 dark:text-rose-400">
                            +{job.missing_mandatory_skills.length - 2}
                          </span>
                        )}
                      </div>
                    )}

                    {/* If ineligible, show primary rejection reason preview */}
                    {!job.is_eligible && job.reasons && job.reasons.length > 0 && (
                      <div className="p-1.5 rounded bg-rose-100/70 dark:bg-rose-950/40 text-[10px] text-rose-900 dark:text-rose-300 border border-rose-200 dark:border-rose-800/60 line-clamp-1">
                        <strong>Reason:</strong> {job.reasons[0]}
                      </div>
                    )}
                  </div>
                </div>

                {/* Card Footer */}
                <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-[11px] text-slate-400 dark:text-slate-500">
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    Due {new Date(job.application_deadline).toLocaleDateString()}
                  </span>
                  <span className="text-brand-600 dark:text-brand-400 font-semibold group-hover:translate-x-0.5 transition-transform flex items-center">
                    Match Analysis <ChevronRight className="w-3.5 h-3.5 ml-0.5" />
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Comprehensive Match Analysis & Eligibility Modal */}
      {selectedCard && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 dark:bg-slate-950/70 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-2xl max-w-3xl w-full p-6 space-y-5 my-8 max-h-[92vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="flex items-start justify-between border-b border-slate-200 dark:border-slate-800 pb-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider flex items-center gap-1">
                    <Building className="w-3.5 h-3.5 text-slate-400 dark:text-slate-500" />
                    {selectedCard.company_name}
                  </span>
                  {selectedCard.institution_name ? (
                    <Badge variant="brand">Campus Exclusive: {selectedCard.institution_name}</Badge>
                  ) : (
                    <Badge variant="neutral">Open Campus Drive</Badge>
                  )}
                </div>
                <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">{selectedCard.title}</h2>
                <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500 dark:text-slate-400">
                  <span className="flex items-center gap-1">
                    <MapPin className="w-3.5 h-3.5 text-slate-400 dark:text-slate-500" />
                    {selectedCard.location}
                  </span>
                  <span>• {selectedCard.work_mode.replace(/_/g, ' ')}</span>
                  <span>• {selectedCard.employment_type.replace(/_/g, ' ')}</span>
                  {selectedCard.salary_range && (
                    <span className="font-bold text-slate-800 dark:text-slate-200">• ₹ {selectedCard.salary_range}</span>
                  )}
                  {selectedCard.ctc_lpa && (
                    <span className="font-bold text-slate-800 dark:text-slate-200">• ₹ {selectedCard.ctc_lpa} LPA</span>
                  )}
                </div>
              </div>

              <button
                onClick={() => {
                  setSelectedCard(null);
                  setEvaluation(null);
                }}
                className="text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-300 p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Placement Intelligence Score & Eligibility Banner */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
              {/* Compatibility Score */}
              <div className="flex flex-col items-center justify-center p-3 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-center">
                <span className="text-[10px] font-bold uppercase text-slate-500 dark:text-slate-400 tracking-wider">
                  Overall Compatibility
                </span>
                <span className="text-3xl font-black text-brand-700 dark:text-brand-400 mt-1">
                  {selectedCard.compatibility_score.toFixed(1)}%
                </span>
                <span className="text-[10px] text-slate-400 dark:text-slate-500 mt-0.5">
                  Continuous 5-Factor Weighted Score
                </span>
              </div>

              {/* Eligibility Status */}
              <div className="sm:col-span-2 flex flex-col justify-center p-3 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[10px] font-bold uppercase text-slate-500 dark:text-slate-400 tracking-wider">
                    Academic Eligibility
                  </span>
                  {selectedCard.is_eligible ? (
                    <Badge variant="success">Eligible to Apply</Badge>
                  ) : (
                    <Badge variant="danger">Cutoffs Not Satisfied</Badge>
                  )}
                </div>
                <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
                  {selectedCard.is_eligible
                    ? 'Your academic credentials, department affiliation, backlog count, and graduation year satisfy all mandatory institutional recruitment criteria.'
                    : 'Campus placement policy restricts application because your profile does not satisfy one or more mandatory eligibility requirements.'}
                </p>
                {selectedCard.reasons && selectedCard.reasons.length > 0 && (
                  <ul className="list-disc list-inside mt-1.5 text-[11px] text-rose-700 dark:text-rose-300 font-medium">
                    {selectedCard.reasons.map((r, i) => (
                      <li key={i}>{r}</li>
                    ))}
                  </ul>
                )}
              </div>
            </div>

            {/* Score Breakdown (5 Continuous Dimensions) */}
            <div className="space-y-3">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                <Sparkles className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                Continuous 5-Dimension Score Breakdown
              </h4>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                {/* 1. Skills */}
                <div className="p-3 rounded-xl bg-slate-50/70 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
                  <div className="flex justify-between font-semibold mb-1">
                    <span className="flex items-center gap-1.5 text-slate-700 dark:text-slate-200">
                      <Code2 className="w-3.5 h-3.5 text-brand-600 dark:text-brand-400" /> Skill Compatibility
                    </span>
                    <span className="text-slate-900 dark:text-slate-100 font-bold">
                      {selectedCard.score_breakdown.skills.toFixed(1)} / 50 pts
                    </span>
                  </div>
                  <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2 overflow-hidden">
                    <div
                      className="bg-brand-600 h-2 rounded-full transition-all"
                      style={{
                        width: `${Math.min(100, (selectedCard.score_breakdown.skills / 50) * 100)}%`,
                      }}
                    ></div>
                  </div>
                </div>

                {/* 2. Academics */}
                <div className="p-3 rounded-xl bg-slate-50/70 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
                  <div className="flex justify-between font-semibold mb-1">
                    <span className="flex items-center gap-1.5 text-slate-700 dark:text-slate-200">
                      <BookOpen className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" /> Academic Standing & Backlogs
                    </span>
                    <span className="text-slate-900 dark:text-slate-100 font-bold">
                      {selectedCard.score_breakdown.academics.toFixed(1)} / 20 pts
                    </span>
                  </div>
                  <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2 overflow-hidden">
                    <div
                      className="bg-indigo-600 h-2 rounded-full transition-all"
                      style={{
                        width: `${Math.min(100, (selectedCard.score_breakdown.academics / 20) * 100)}%`,
                      }}
                    ></div>
                  </div>
                </div>

                {/* 3. Projects */}
                <div className="p-3 rounded-xl bg-slate-50/70 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
                  <div className="flex justify-between font-semibold mb-1">
                    <span className="flex items-center gap-1.5 text-slate-700 dark:text-slate-200">
                      <Layers className="w-3.5 h-3.5 text-sky-600 dark:text-sky-400" /> Projects Relevance
                    </span>
                    <span className="text-slate-900 dark:text-slate-100 font-bold">
                      {selectedCard.score_breakdown.projects.toFixed(1)} / 15 pts
                    </span>
                  </div>
                  <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2 overflow-hidden">
                    <div
                      className="bg-sky-600 h-2 rounded-full transition-all"
                      style={{
                        width: `${Math.min(100, (selectedCard.score_breakdown.projects / 15) * 100)}%`,
                      }}
                    ></div>
                  </div>
                </div>

                {/* 4. Experience */}
                <div className="p-3 rounded-xl bg-slate-50/70 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
                  <div className="flex justify-between font-semibold mb-1">
                    <span className="flex items-center gap-1.5 text-slate-700 dark:text-slate-200">
                      <Briefcase className="w-3.5 h-3.5 text-purple-600 dark:text-purple-400" /> Industry Internships & Experience
                    </span>
                    <span className="text-slate-900 dark:text-slate-100 font-bold">
                      {selectedCard.score_breakdown.experience.toFixed(1)} / 7 pts
                    </span>
                  </div>
                  <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2 overflow-hidden">
                    <div
                      className="bg-purple-600 h-2 rounded-full transition-all"
                      style={{
                        width: `${Math.min(100, (selectedCard.score_breakdown.experience / 7) * 100)}%`,
                      }}
                    ></div>
                  </div>
                </div>

                {/* 5. Certifications */}
                <div className="p-3 rounded-xl bg-slate-50/70 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 sm:col-span-2">
                  <div className="flex justify-between font-semibold mb-1">
                    <span className="flex items-center gap-1.5 text-slate-700 dark:text-slate-200">
                      <Award className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" /> Verified Certifications
                    </span>
                    <span className="text-slate-900 dark:text-slate-100 font-bold">
                      {selectedCard.score_breakdown.certifications.toFixed(1)} / 5 pts
                    </span>
                  </div>
                  <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2 overflow-hidden">
                    <div
                      className="bg-emerald-600 h-2 rounded-full transition-all"
                      style={{
                        width: `${Math.min(
                          100,
                          (selectedCard.score_breakdown.certifications / 5) * 100
                        )}%`,
                      }}
                    ></div>
                  </div>
                </div>
              </div>
            </div>

            {/* Match Rationale / Explanation */}
            {isEvaluating ? (
              <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-center text-xs text-slate-400 dark:text-slate-500">
                Evaluating deep match rationale...
              </div>
            ) : evaluation ? (
              <div className="p-4 rounded-xl bg-brand-50/60 dark:bg-brand-950/30 border border-brand-200/80 dark:border-brand-800/60 space-y-2">
                <span className="text-[11px] font-bold uppercase tracking-wider text-brand-800 dark:text-brand-300 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-brand-600 dark:text-brand-400" />
                  Deterministic Match Assessment Rationale
                </span>
                <p className="text-xs text-slate-800 dark:text-slate-200 leading-relaxed font-mono whitespace-pre-line bg-white/80 dark:bg-slate-900/90 p-3 rounded-lg border border-brand-100 dark:border-brand-900/60">
                  {evaluation.match_rationale}
                </p>
              </div>
            ) : null}

            {/* Criteria Evaluation Breakdown */}
            {evaluation && evaluation.criteria && (
              <div className="space-y-2.5">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  Itemized Cutoff Criteria Checklist
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                  {Object.values(evaluation.criteria).map((crit, idx) => (
                    <div
                      key={idx}
                      className={`p-3 rounded-xl border flex items-start justify-between gap-2 ${crit.passed
                          ? 'bg-emerald-50/40 dark:bg-emerald-950/30 border-emerald-200/80 dark:border-emerald-800/60 text-emerald-950 dark:text-emerald-200'
                          : 'bg-rose-50/50 dark:bg-rose-950/30 border-rose-200 dark:border-rose-800/60 text-rose-950 dark:text-rose-200'
                        }`}
                    >
                      <div>
                        <div className="font-bold text-[11px]">{crit.criterion}</div>
                        <div className="text-[10px] text-slate-600 dark:text-slate-400 mt-0.5">{crit.message}</div>
                      </div>
                      {crit.passed ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400 flex-shrink-0 mt-0.5" />
                      ) : (
                        <XCircle className="w-4 h-4 text-rose-500 dark:text-rose-400 flex-shrink-0 mt-0.5" />
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Skills Alignment Analysis */}
            <div className="space-y-2 text-xs">
              <h4 className="font-bold text-slate-900 dark:text-slate-100">Technical Skills Compatibility</h4>
              <div className="space-y-2">
                {/* Matched */}
                <div>
                  <span className="text-[11px] font-semibold text-emerald-700 dark:text-emerald-400 block mb-1">
                    Matched Skills in Your Profile:
                  </span>
                  {selectedCard.matched_skills && selectedCard.matched_skills.length > 0 ? (
                    <div className="flex flex-wrap gap-1.5">
                      {selectedCard.matched_skills.map((s, idx) => (
                        <span
                          key={idx}
                          className="px-2.5 py-1 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-300 text-xs font-semibold border border-emerald-200 dark:border-emerald-800/60"
                        >
                          ✓ {s}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <span className="text-slate-400 dark:text-slate-500 italic text-[11px]">No skill overlaps found.</span>
                  )}
                </div>

                {/* Missing Mandatory */}
                {selectedCard.missing_mandatory_skills &&
                  selectedCard.missing_mandatory_skills.length > 0 && (
                    <div className="pt-1">
                      <span className="text-[11px] font-semibold text-rose-700 dark:text-rose-400 block mb-1">
                        Missing Mandatory Prerequisites:
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {selectedCard.missing_mandatory_skills.map((s, idx) => (
                          <span
                            key={idx}
                            className="px-2.5 py-1 rounded-lg bg-rose-50 dark:bg-rose-950/40 text-rose-800 dark:text-rose-300 text-xs font-semibold border border-rose-200 dark:border-rose-800/60"
                          >
                            ✕ {s}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                {/* Recommended */}
                {selectedCard.recommended_skills && selectedCard.recommended_skills.length > 0 && (
                  <div className="pt-1">
                    <span className="text-[11px] font-semibold text-indigo-700 dark:text-indigo-400 block mb-1">
                      Recommended Skills to Boost Score:
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {selectedCard.recommended_skills.map((s, idx) => (
                        <span
                          key={idx}
                          className="px-2.5 py-1 rounded-lg bg-indigo-50 dark:bg-indigo-950/40 text-indigo-800 dark:text-indigo-300 text-xs font-semibold border border-indigo-200 dark:border-indigo-800/60"
                        >
                          + {s}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Apply Feedback Banner */}
            {applyFeedback && (
              <div
                className={`p-3 rounded-xl border text-xs flex items-center gap-2 ${
                  applyFeedback.type === 'success'
                    ? 'bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-800/60 text-emerald-800 dark:text-emerald-300'
                    : 'bg-rose-50 dark:bg-rose-950/40 border-rose-200 dark:border-rose-800/60 text-rose-800 dark:text-rose-300'
                }`}
              >
                {applyFeedback.type === 'success' ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400 flex-shrink-0" />
                ) : (
                  <AlertCircle className="w-4 h-4 text-rose-600 dark:text-rose-400 flex-shrink-0" />
                )}
                <span>{applyFeedback.text}</span>
              </div>
            )}

            {/* Modal Actions */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-4 border-t border-slate-200 dark:border-slate-800">
              {appliedMap[selectedCard.job_id] ? (
                <div className="flex flex-wrap items-center gap-3 text-xs">
                  <div className="flex items-center gap-2 text-emerald-700 dark:text-emerald-400 font-semibold">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                    <span>
                      Applied (Status:{' '}
                      {appliedMap[selectedCard.job_id].current_status.replace(/_/g, ' ').toUpperCase()})
                    </span>
                  </div>
                  {appliedMap[selectedCard.job_id].current_status === 'offered' && (
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="primary"
                        disabled={respondingAppId === appliedMap[selectedCard.job_id].id}
                        onClick={() => handleOfferResponse(appliedMap[selectedCard.job_id].id, true)}
                      >
                        Accept Offer
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={respondingAppId === appliedMap[selectedCard.job_id].id}
                        onClick={() => handleOfferResponse(appliedMap[selectedCard.job_id].id, false)}
                      >
                        Decline Offer
                      </Button>
                    </div>
                  )}
                </div>
              ) : selectedCard.is_eligible ? (
                approvedResumes.length > 0 ? (
                  <div className="flex flex-wrap items-center gap-2">
                    {approvedResumes.length > 1 && (
                      <select
                        value={selectedResumeId ?? ''}
                        onChange={(e) => setSelectedResumeId(Number(e.target.value))}
                        className="text-xs border border-slate-200 dark:border-slate-700 rounded-lg px-2 py-1.5 bg-white dark:bg-slate-950 text-slate-700 dark:text-slate-200"
                      >
                        {approvedResumes.map((r) => (
                          <option key={r.id} value={r.id}>
                            {r.file_name}
                          </option>
                        ))}
                      </select>
                    )}
                    <Button
                      size="sm"
                      onClick={handleApplyToJob}
                      isLoading={isApplying}
                    >
                      Apply Now
                    </Button>
                  </div>
                ) : (
                  <Link
                    to="/student/resumes"
                    className="text-xs font-semibold text-brand-700 dark:text-brand-400 hover:underline"
                  >
                    Approve a resume in Resume Intelligence to apply →
                  </Link>
                )
              ) : (
                <span className="text-[11px] text-slate-500 dark:text-slate-400">
                  Eligibility criteria must be satisfied before applying.
                </span>
              )}

              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  setSelectedCard(null);
                  setEvaluation(null);
                  setApplyFeedback(null);
                }}
              >
                Close Analysis
              </Button>
            </div>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
};
