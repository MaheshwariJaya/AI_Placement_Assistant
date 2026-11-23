import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { DashboardLayout } from '../../components/layout/DashboardLayout';
import { Card, CardHeader } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { useAuth } from '../../context/AuthContext';
import { useAcademicContext } from '../../context/AcademicContext';
import { userApi, resumeApi, intelligenceApi, applicationApi } from '../../services/api';
import {
  StudentProfile,
  Resume,
  JobRecommendationCard,
  JobRecommendationListResponse,
  RecruiterOverviewApplication,
} from '../../types';
import {
  GraduationCap,
  Briefcase,
  Sparkles,
  TrendingUp,
  ArrowRight,
  FileText,
  AlertCircle,
  RefreshCw,
  Building,
  CheckCircle2,
  XCircle,
  Clock,
  MapPin,
  Target,
  Layers,
  Mic,
} from 'lucide-react';

export const StudentDashboard: React.FC = () => {
  const { user } = useAuth();
  const { officialBranchName, officialBranchCode, isBranchVerified } = useAcademicContext();
  const [profile, setProfile] = useState<StudentProfile | null>(null);
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [recommendations, setRecommendations] = useState<JobRecommendationListResponse | null>(null);
  const [myApplications, setMyApplications] = useState<RecruiterOverviewApplication[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboardData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [profileData, resumesData, recsData, appsData] = await Promise.allSettled([
        userApi.getStudentProfile(),
        resumeApi.getResumes(),
        intelligenceApi.getRecommendations(),
        applicationApi.getMyApplications(),
      ]);

      if (profileData.status === 'fulfilled') {
        setProfile(profileData.value);
      } else {
        console.warn('Student profile fetch error:', profileData.reason);
      }

      if (resumesData.status === 'fulfilled') {
        setResumes(resumesData.value);
      } else {
        console.warn('Student resumes fetch error:', resumesData.reason);
      }

      if (recsData.status === 'fulfilled') {
        setRecommendations(recsData.value);
      } else {
        console.warn('Job recommendations fetch error:', recsData.reason);
      }

      if (appsData.status === 'fulfilled') {
        setMyApplications(appsData.value.items);
      }
    } catch (err: any) {
      console.error('Failed to load dashboard data:', err);
      setError('Unable to load latest placement information.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  // Compute actual profile completion dynamically
  const calculateProfileHealth = (): { percentage: number; statusText: string } => {
    let score = 0;
    const maxScore = 100;

    // 1. Base Identity (30 points)
    if (user?.full_name) score += 10;
    if (user?.email) score += 10;
    if (user?.phone) score += 10;

    // 2. Academic Enrollment Scoping (40 points)
    const effectiveRoll = profile?.roll_number || user?.roll_number;
    const effectiveGrad = profile?.graduation_year;
    const effectiveCgpa = profile?.cgpa;

    if (effectiveRoll) score += 15;
    if (effectiveGrad) score += 10;
    if (effectiveCgpa !== undefined && effectiveCgpa !== null) score += 15;

    // 3. Institutional Scoping (10 points)
    if (user?.institution_id || profile?.user?.institution_id) score += 5;
    if (user?.department_id || profile?.user?.department_id) score += 5;

    // 4. Career Readiness & Resume Verification (20 points)
    if (resumes.length > 0) score += 10;
    if (profile?.linkedin_url || profile?.github_url || profile?.portfolio_url) score += 10;

    let statusText = 'Academic profile complete';
    if (resumes.length === 0) {
      statusText = 'Upload resume to boost profile health to 90%';
    } else if (!profile?.linkedin_url && !profile?.github_url) {
      statusText = 'Add LinkedIn / GitHub URLs to reach 100%';
    } else {
      statusText = 'Placement profile complete & verified';
    }

    return { percentage: Math.min(score, maxScore), statusText };
  };

  const health = calculateProfileHealth();

  // Student display attributes from user context or DB profile
  const studentName = user?.full_name || profile?.user?.full_name || 'Student Candidate';
  const departmentName =
    profile?.user?.department_name || user?.department_name || 'Enrolled Department';
  const institutionName =
    profile?.user?.institution_name || user?.institution_name || 'Campus Placement Cell';
  const rollNumber = profile?.roll_number || user?.roll_number || 'Pending Assignment';
  const graduationYear = profile?.graduation_year || user?.student_profile?.graduation_year || '—';
  const cgpaValue =
    profile?.cgpa !== undefined && profile?.cgpa !== null
      ? Number(profile.cgpa).toFixed(2)
      : '—';
  const activeBacklogs = profile?.active_backlogs ?? 0;
  const isPlacementReady = profile?.is_placement_ready ?? true;

  // Determine top 3 recommended jobs: prioritize eligible jobs, fallback to top ineligible with notice
  const getTopRecommendations = (): { jobs: JobRecommendationCard[]; isShowingIneligibleFallback: boolean } => {
    if (!recommendations) return { jobs: [], isShowingIneligibleFallback: false };

    if (recommendations.eligible_jobs && recommendations.eligible_jobs.length > 0) {
      return {
        jobs: recommendations.eligible_jobs.slice(0, 3),
        isShowingIneligibleFallback: false,
      };
    }

    if (recommendations.ineligible_jobs && recommendations.ineligible_jobs.length > 0) {
      return {
        jobs: recommendations.ineligible_jobs.slice(0, 3),
        isShowingIneligibleFallback: true,
      };
    }

    return { jobs: [], isShowingIneligibleFallback: false };
  };

  const { jobs: topJobs, isShowingIneligibleFallback } = getTopRecommendations();

  return (
    <DashboardLayout
      role="student"
      title="Student Placement Intelligence Portal"
      subtitle="Analyze resume compatibility, inspect academic eligibility cutoffs, and discover high-match campus placement opportunities."
    >
      {/* Welcome Banner */}
      <div className="bg-gradient-to-r from-brand-700 via-brand-600 to-indigo-600 rounded-xl p-6 text-white mb-6 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-white/20 text-white text-[11px] font-semibold mb-2 backdrop-blur">
              <Sparkles className="w-3 h-3" />
              <span>Placement Intelligence Active</span>
            </div>
            <h2 className="text-xl font-bold tracking-tight">
              Welcome back, {studentName}
            </h2>
            <p className="text-xs text-brand-100 mt-1 flex items-center gap-1.5 flex-wrap">
              <span className="font-semibold">{officialBranchName || departmentName}</span>
              {officialBranchCode && <span className="opacity-80">({officialBranchCode})</span>}
              <span>• Class of {graduationYear}</span>
              <span>• Roll: {rollNumber}</span>
              {isBranchVerified ? (
                <span className="text-[10px] bg-emerald-400/25 text-emerald-100 px-1.5 py-0.2 rounded border border-emerald-300/40">
                  Verified Branch
                </span>
              ) : (
                <span className="text-[10px] bg-amber-400/25 text-amber-100 px-1.5 py-0.2 rounded border border-amber-300/40">
                  Unverified
                </span>
              )}
            </p>
            <p className="text-[11px] text-brand-200 mt-0.5 flex items-center gap-1">
              <Building className="w-3 h-3" />
              <span>{institutionName}</span>
            </p>
          </div>
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-2">
            <span className="text-xs bg-white/10 px-3 py-1.5 rounded-lg border border-white/20 backdrop-blur">
              CGPA: <strong className="text-white">{cgpaValue}</strong> ({activeBacklogs} Backlogs)
            </span>
            {isPlacementReady && (
              <span className="text-xs bg-emerald-500/20 text-emerald-100 px-2.5 py-1.5 rounded-lg border border-emerald-400/30 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-300" />
                Placement Ready
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Unverified Academic Branch Alert */}
      {!isBranchVerified && (
        <div className="mb-6 p-4 rounded-xl bg-amber-50 dark:bg-amber-950/60 border border-amber-300 dark:border-amber-700 flex items-start gap-3 text-xs text-amber-900 dark:text-amber-200">
          <AlertCircle className="w-5 h-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
          <div>
            <h4 className="font-bold text-sm">Official Academic Branch Verification Required</h4>
            <p className="mt-1 leading-relaxed">
              Your official academic branch is currently unverified in institutional records. Please contact your Training &amp; Placement Office (TPO) to complete official academic branch verification. Placement recommendations and branch-specific preparation are operating in limited mode.
            </p>
          </div>
        </div>
      )}

      {/* Placement / Application Status Banner */}
      {(() => {
        const acceptedOffer = myApplications.find((a) => a.current_status === 'offer_accepted');
        const pendingOffer = myApplications.find((a) => a.current_status === 'offered');
        if (acceptedOffer) {
          return (
            <div className="mb-6 p-4 rounded-xl bg-emerald-50 dark:bg-emerald-950/50 border border-emerald-200 dark:border-emerald-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-start gap-2.5 text-xs">
                <CheckCircle2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <div className="font-bold text-emerald-950 dark:text-emerald-200">
                    Placement Offer Accepted: {acceptedOffer.job_title} at {acceptedOffer.company_name}
                  </div>
                  <p className="text-emerald-800 dark:text-emerald-300 mt-0.5">
                    Your hiring status is recorded as placed ({myApplications.length} total application
                    {myApplications.length === 1 ? '' : 's'}).
                  </p>
                </div>
              </div>
              <Link to="/student/jobs">
                <Button size="sm" variant="outline">
                  View My Applications
                </Button>
              </Link>
            </div>
          );
        }
        if (pendingOffer) {
          return (
            <div className="mb-6 p-4 rounded-xl bg-brand-50 dark:bg-brand-950/50 border border-brand-200 dark:border-brand-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-start gap-2.5 text-xs">
                <Sparkles className="w-5 h-5 text-brand-600 dark:text-brand-400 shrink-0 mt-0.5" />
                <div>
                  <div className="font-bold text-brand-950 dark:text-brand-200">
                    Official Offer Extended: {pendingOffer.job_title} at {pendingOffer.company_name}
                  </div>
                  <p className="text-brand-800 dark:text-brand-300 mt-0.5">
                    Review and accept or decline your offer in Explore Jobs -&gt; My Applications.
                  </p>
                </div>
              </div>
              <Link to="/student/jobs">
                <Button size="sm" variant="primary">
                  Respond to Offer
                </Button>
              </Link>
            </div>
          );
        }
        if (myApplications.length > 0) {
          const latest = myApplications[0];
          return (
            <div className="mb-6 p-3.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
              <div className="flex items-center gap-2 text-slate-700 dark:text-slate-300">
                <Briefcase className="w-4 h-4 text-brand-600 dark:text-brand-400 shrink-0" />
                <span>
                  <strong>{myApplications.length} Submitted Application{myApplications.length === 1 ? '' : 's'}</strong> · Latest:{' '}
                  {latest.job_title} ({latest.company_name}) —{' '}
                  <strong className="uppercase">{latest.current_status.replace(/_/g, ' ')}</strong>
                </span>
              </div>
              <Link to="/student/jobs" className="text-brand-600 dark:text-brand-400 font-semibold hover:underline">
                Track Applications -&gt;
              </Link>
            </div>
          );
        }
        return null;
      })()}

      {/* KPI Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Card>
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Profile Health
            </span>
            <span className="w-8 h-8 rounded-lg bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 flex items-center justify-center">
              <GraduationCap className="w-4 h-4" />
            </span>
          </div>
          <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-2">
            {loading ? '—' : `${health.percentage}%`}
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
            {loading ? 'Calculating health...' : health.statusText}
          </p>
        </Card>

        <Card>
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Eligible Campus Drives
            </span>
            <span className="w-8 h-8 rounded-lg bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 flex items-center justify-center">
              <CheckCircle2 className="w-4 h-4" />
            </span>
          </div>
          <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-2">
            {loading ? '—' : recommendations?.total_eligible ?? 0}
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
            {recommendations?.total_eligible
              ? 'Satisfies all cutoffs & policies'
              : 'No eligible drives currently'}
          </p>
        </Card>

        <Card>
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Total Opportunities
            </span>
            <span className="w-8 h-8 rounded-lg bg-sky-50 dark:bg-sky-950/60 text-sky-600 dark:text-sky-400 flex items-center justify-center">
              <TrendingUp className="w-4 h-4" />
            </span>
          </div>
          <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-2">
            {loading
              ? '—'
              : (recommendations?.total_eligible ?? 0) + (recommendations?.total_ineligible ?? 0)}
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">Continuous matching evaluated</p>
        </Card>

        <Card>
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Matching Engine
            </span>
            <span className="w-8 h-8 rounded-lg bg-brand-50 dark:bg-brand-950/60 text-brand-600 dark:text-brand-400 flex items-center justify-center">
              <Target className="w-4 h-4" />
            </span>
          </div>
          <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-2">
            {loading ? '—' : topJobs.length > 0 ? `${topJobs[0].compatibility_score.toFixed(0)}% Peak` : 'Active'}
          </div>
          <p className="text-[11px] text-brand-600 dark:text-brand-400 mt-1">5-Factor Weighted Compatibility</p>
        </Card>
      </div>

      {/* Main Grid: Top Recommended Placement Opportunities & Resume Tools */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <Card>
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3 mb-4">
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
                  <Sparkles className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                  Top Recommended Placement Opportunities
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  Ranked by continuous compatibility and evaluated against institutional cutoffs
                </p>
              </div>

              <Link to="/student/jobs">
                <Button size="sm" variant="outline" icon={<ArrowRight className="w-3.5 h-3.5" />}>
                  View All ({recommendations ? recommendations.total_eligible + recommendations.total_ineligible : 0})
                </Button>
              </Link>
            </div>

            {loading ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 animate-pulse space-y-2">
                    <div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-1/3"></div>
                    <div className="h-3 bg-slate-100 dark:bg-slate-800/70 rounded w-1/2"></div>
                  </div>
                ))}
              </div>
            ) : topJobs.length === 0 ? (
              <div className="py-12 px-6 text-center border border-dashed border-slate-200 dark:border-slate-700 rounded-xl bg-slate-50/50 dark:bg-slate-800/30">
                <div className="w-12 h-12 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-400 flex items-center justify-center mx-auto mb-3">
                  <Briefcase className="w-6 h-6" />
                </div>
                <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                  No Placement Drives Published Yet
                </h4>
                <p className="text-xs text-slate-500 dark:text-slate-400 max-w-md mx-auto mt-1 leading-relaxed">
                  Campus recruitment drives published by partner companies and your institution TPO will appear
                  here. Upload your resume and verify skills to be instantly evaluated upon publication.
                </p>
                <div className="mt-5 flex justify-center">
                  <Link to="/student/resumes">
                    <Button variant="primary" size="sm" icon={<FileText className="w-3.5 h-3.5" />}>
                      Upload & Verify Resume for Placement Matching
                    </Button>
                  </Link>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                {isShowingIneligibleFallback && (
                  <div className="p-3 rounded-lg bg-amber-50 dark:bg-amber-950/50 border border-amber-200 dark:border-amber-800 text-xs text-amber-900 dark:text-amber-200 flex items-start gap-2 mb-2">
                    <AlertCircle className="w-4 h-4 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
                    <div>
                      <span className="font-semibold">Notice:</span> Showing top profile-compatible drives
                      even though you do not currently satisfy one or more academic cutoffs (CGPA / backlogs / batch).
                      Check the missing requirements on each card below.
                    </div>
                  </div>
                )}

                {topJobs.map((job) => (
                  <div
                    key={job.job_id}
                    className={`p-4 rounded-xl border transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-4 ${
                      job.is_eligible
                        ? 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/80 hover:border-brand-300 dark:hover:border-brand-700'
                        : 'border-rose-200 dark:border-rose-900/70 bg-rose-50/30 dark:bg-rose-950/20'
                    }`}
                  >
                    <div className="space-y-1.5 flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 flex items-center gap-1 truncate">
                          <Building className="w-3 h-3 text-slate-400 dark:text-slate-500" />
                          {job.company_name}
                        </span>
                        <span className="text-[10px] px-2 py-0.2 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 capitalize">
                          {job.work_mode.replace(/_/g, ' ')}
                        </span>
                        {job.relevance_tier === 'directly_relevant' && (
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-950/70 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                            Branch Match
                          </span>
                        )}
                        {job.relevance_tier === 'interdisciplinary' && (
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-purple-50 dark:bg-purple-950/70 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800">
                            Interdisciplinary
                          </span>
                        )}
                        {job.relevance_tier === 'open_to_all' && (
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-50 dark:bg-blue-950/70 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
                            Open to All
                          </span>
                        )}
                      </div>

                      <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100 truncate">{job.title}</h4>
                      {job.relevance_reason && (
                        <p className="text-[11px] text-slate-500 dark:text-slate-400 line-clamp-1">
                          {job.relevance_reason}
                        </p>
                      )}

                      <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500 dark:text-slate-400">
                        <span className="flex items-center gap-1">
                          <MapPin className="w-3 h-3 text-slate-400 dark:text-slate-500" />
                          {job.location}
                        </span>
                        {job.ctc_lpa && (
                          <span className="font-bold text-slate-800 dark:text-slate-200">• ₹ {job.ctc_lpa} LPA</span>
                        )}
                        {job.salary_range && !job.ctc_lpa && (
                          <span className="font-bold text-slate-800 dark:text-slate-200">• ₹ {job.salary_range}</span>
                        )}
                      </div>

                      {/* Skills match overview */}
                      <div className="flex flex-wrap items-center gap-1.5 pt-1 text-[10px]">
                        {job.matched_skills && job.matched_skills.length > 0 && (
                          <span className="text-emerald-700 dark:text-emerald-400 font-medium">
                            ✓ {job.matched_skills.slice(0, 2).join(', ')}
                            {job.matched_skills.length > 2 ? ` +${job.matched_skills.length - 2}` : ''}
                          </span>
                        )}

                        {job.missing_mandatory_skills && job.missing_mandatory_skills.length > 0 && (
                          <span className="text-rose-700 dark:text-rose-400 font-medium ml-1">
                            Missing: {job.missing_mandatory_skills.slice(0, 2).join(', ')}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Right Column: Score & Status & Action */}
                    <div className="flex sm:flex-col items-center sm:items-end justify-between sm:justify-center gap-2 flex-shrink-0">
                      <div className="flex items-center gap-2">
                        {/* Separate Eligibility Badge */}
                        {job.is_eligible ? (
                          <Badge variant="success">Eligible</Badge>
                        ) : (
                          <Badge variant="danger">Cutoff Gap</Badge>
                        )}

                        {/* Compatibility Score Pill */}
                        <div className="px-2.5 py-1 rounded-lg bg-brand-50 dark:bg-brand-950/60 border border-brand-200 dark:border-brand-800 text-brand-800 dark:text-brand-300 font-black text-xs">
                          {job.compatibility_score.toFixed(1)}% Match
                        </div>
                      </div>

                      <Link to="/student/jobs">
                        <Button size="sm" variant="ghost" className="text-xs text-brand-600 dark:text-brand-400 hover:text-brand-800 dark:hover:text-brand-300">
                          Inspect Match <ArrowRight className="w-3 h-3 ml-1" />
                        </Button>
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>

        {/* Right Sidebar: Placement Readiness Checklist */}
        <div className="space-y-4">
          <Card>
            <CardHeader
              title="Placement Readiness Checklist"
              subtitle="Keep your profile updated for automated evaluation"
            />
            <div className="space-y-3 text-xs">
              <div className="flex items-center justify-between p-2 rounded-lg bg-slate-50 dark:bg-slate-800/70">
                <span className="font-medium text-slate-700 dark:text-slate-300">Verified Academic CGPA</span>
                <span className="font-bold text-slate-900 dark:text-slate-100">{cgpaValue}</span>
              </div>
              <div className="flex items-center justify-between p-2 rounded-lg bg-slate-50 dark:bg-slate-800/70">
                <span className="font-medium text-slate-700 dark:text-slate-300">Active Backlogs Recorded</span>
                <span className={`font-bold ${activeBacklogs > 0 ? 'text-amber-600 dark:text-amber-400' : 'text-emerald-600 dark:text-emerald-400'}`}>
                  {activeBacklogs}
                </span>
              </div>
              <div className="flex items-center justify-between p-2 rounded-lg bg-slate-50 dark:bg-slate-800/70">
                <span className="font-medium text-slate-700 dark:text-slate-300">Resumes Uploaded</span>
                <span className="font-bold text-slate-900 dark:text-slate-100">{resumes.length}</span>
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800 space-y-2">
              <Link to="/student/profile" className="w-full block">
                <Button variant="secondary" size="sm" className="w-full text-xs">
                  <GraduationCap className="w-3.5 h-3.5 mr-1.5 text-brand-600 dark:text-brand-400" />
                  View Academic Profile & Portfolio
                </Button>
              </Link>
              <Link to="/student/resumes" className="w-full block">
                <Button variant="outline" size="sm" className="w-full text-xs">
                  <FileText className="w-3.5 h-3.5 mr-1.5" />
                  Manage Resume & Skills
                </Button>
              </Link>
              <Link to="/student/interview-studio" className="w-full block">
                <Button variant="primary" size="sm" className="w-full text-xs">
                  <Mic className="w-3.5 h-3.5 mr-1.5" />
                  Launch AI Mock Interview Studio
                </Button>
              </Link>
              <Link to="/student/applications" className="w-full block">
                <Button variant="secondary" size="sm" className="w-full text-xs">
                  <Briefcase className="w-3.5 h-3.5 mr-1.5 text-brand-600 dark:text-brand-400" />
                  Smart Application & Interview Tracker
                </Button>
              </Link>
              <Link to="/student/readiness" className="w-full block">
                <Button variant="secondary" size="sm" className="w-full text-xs">
                  <Target className="w-3.5 h-3.5 mr-1.5 text-brand-600 dark:text-brand-400" />
                  Check Placement Readiness Index
                </Button>
              </Link>
              <Link to="/student/arena" className="w-full block">
                <Button variant="secondary" size="sm" className="w-full text-xs">
                  <Layers className="w-3.5 h-3.5 mr-1.5 text-brand-600 dark:text-brand-400" />
                  Open Placement Preparation Arena
                </Button>
              </Link>
            </div>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  );
};
