import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { DashboardLayout } from '../../components/layout/DashboardLayout';
import { Card, CardHeader } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { Input } from '../../components/common/Input';
import { recruiterCandidateApi, jobApi } from '../../services/api';
import { CandidateListItem, CandidateFilterParams, Job } from '../../types';
import {
  Users,
  Search,
  Filter,
  Briefcase,
  GraduationCap,
  Award,
  CheckCircle2,
  XCircle,
  AlertCircle,
  ArrowRight,
  RefreshCw,
  SlidersHorizontal,
  ChevronRight,
  ShieldCheck,
  Star,
  Building,
  UserCheck,
  Sparkles,
} from 'lucide-react';

const STATUS_BADGE_VARIANTS: Record<string, 'success' | 'warning' | 'danger' | 'brand' | 'neutral'> = {
  applied: 'neutral',
  tpo_screened: 'brand',
  shortlisted: 'brand',
  interview_scheduled: 'warning',
  interview_completed: 'warning',
  offered: 'success',
  offer_accepted: 'success',
  offer_declined: 'danger',
  rejected: 'danger',
  withdrawn: 'neutral',
};

const RECOMMENDATION_LABELS: Record<string, { label: string; variant: 'success' | 'brand' | 'warning' | 'danger' | 'neutral' }> = {
  strong_hire: { label: 'Strong Hire', variant: 'success' },
  hire: { label: 'Hire', variant: 'brand' },
  hold: { label: 'Hold', variant: 'warning' },
  no_hire: { label: 'No Hire', variant: 'danger' },
  strong_no_hire: { label: 'Strong No Hire', variant: 'danger' },
};

export const CandidatePipelinePage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const [candidates, setCandidates] = useState<CandidateListItem[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [jobs, setJobs] = useState<Job[]>([]);

  // Filter state
  const [search, setSearch] = useState<string>(searchParams.get('search') || '');
  const [selectedJobId, setSelectedJobId] = useState<string>(searchParams.get('job_id') || '');
  const [department, setDepartment] = useState<string>(searchParams.get('department') || '');
  const [graduationYear, setGraduationYear] = useState<string>(searchParams.get('graduation_year') || '');
  const [eligibility, setEligibility] = useState<'all' | 'eligible_only' | 'ineligible_only'>(
    (searchParams.get('eligibility') as 'all' | 'eligible_only' | 'ineligible_only') || 'all'
  );
  const [status, setStatus] = useState<string>(searchParams.get('status') || '');
  const [minScore, setMinScore] = useState<number>(
    searchParams.get('min_score') ? Number(searchParams.get('min_score')) : 0
  );
  const [skill, setSkill] = useState<string>(searchParams.get('skill') || '');
  const [selectedForComparison, setSelectedForComparison] = useState<number[]>([]);

  const toggleSelectForComparison = (appId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (selectedForComparison.includes(appId)) {
      setSelectedForComparison((prev) => prev.filter((id) => id !== appId));
    } else {
      if (selectedForComparison.length >= 5) {
        alert('You can select a maximum of 5 candidates for side-by-side comparison.');
        return;
      }
      setSelectedForComparison((prev) => [...prev, appId]);
    }
  };

  // Load recruiter published jobs for filter
  useEffect(() => {
    const fetchJobs = async () => {
      try {
        const res = await jobApi.list({ my_company_only: true });
        setJobs(res || []);
      } catch (err) {
        console.error('Failed to load recruiter jobs', err);
      }
    };
    fetchJobs();
  }, []);

  const loadCandidates = useCallback(async () => {
    setLoading(true);
    try {
      const params: CandidateFilterParams = {
        limit: 100,
        eligibility,
      };
      if (search.trim()) params.search = search.trim();
      if (selectedJobId) params.job_id = Number(selectedJobId);
      if (department.trim()) params.department = department.trim();
      if (graduationYear) params.graduation_year = Number(graduationYear);
      if (status) params.status = status;
      if (minScore > 0) params.min_compatibility_score = minScore;
      if (skill.trim()) params.skill = skill.trim();

      const res = await recruiterCandidateApi.listCandidates(params);
      setCandidates(res.items || []);
      setTotalCount(res.total || 0);
    } catch (err) {
      console.error('Failed to load candidate pipeline', err);
      setCandidates([]);
      setTotalCount(0);
    } finally {
      setLoading(false);
    }
  }, [search, selectedJobId, department, graduationYear, eligibility, status, minScore, skill]);

  useEffect(() => {
    loadCandidates();
  }, [loadCandidates]);

  const handleResetFilters = () => {
    setSearch('');
    setSelectedJobId('');
    setDepartment('');
    setGraduationYear('');
    setEligibility('all');
    setStatus('');
    setMinScore(0);
    setSkill('');
    setSearchParams({});
  };

  // Pipeline summary statistics
  const eligibleCount = candidates.filter((c) => c.is_eligible).length;
  const inInterviewCount = candidates.filter((c) =>
    ['shortlisted', 'interview_scheduled', 'interview_completed'].includes(c.current_status)
  ).length;
  const offeredCount = candidates.filter((c) =>
    ['offered', 'offer_accepted'].includes(c.current_status)
  ).length;
  const avgScore =
    candidates.length > 0
      ? (candidates.reduce((sum, c) => sum + (c.compatibility_score || 0), 0) / candidates.length).toFixed(1)
      : '0.0';

  return (
    <DashboardLayout
      role="recruiter"
      title="Candidate Evaluation Workspace"
      subtitle="Corporate Scope: Review verified candidate profiles, deterministic compatibility scores, interview evaluations, and advance candidates."
    >
      {/* Top Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Card>
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Total Applicants
            </span>
            <span className="w-8 h-8 rounded-lg bg-sky-50 dark:bg-sky-950/60 text-sky-600 dark:text-sky-400 flex items-center justify-center">
              <Users className="w-4 h-4" />
            </span>
          </div>
          <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-2">
            {loading ? '...' : totalCount}
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
            Applications across active job postings
          </p>
        </Card>

        <Card>
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Eligible Candidates
            </span>
            <span className="w-8 h-8 rounded-lg bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 flex items-center justify-center">
              <CheckCircle2 className="w-4 h-4" />
            </span>
          </div>
          <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-2">
            {loading ? '...' : eligibleCount}
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
            Met all academic & backlog cutoffs
          </p>
        </Card>

        <Card>
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Active In Pipeline
            </span>
            <span className="w-8 h-8 rounded-lg bg-amber-50 dark:bg-amber-950/60 text-amber-600 dark:text-amber-400 flex items-center justify-center">
              <UserCheck className="w-4 h-4" />
            </span>
          </div>
          <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-2">
            {loading ? '...' : inInterviewCount}
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
            Shortlisted or in active interviews
          </p>
        </Card>

        <Card>
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Avg Compatibility
            </span>
            <span className="w-8 h-8 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 flex items-center justify-center">
              <Award className="w-4 h-4" />
            </span>
          </div>
          <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-2">
            {loading ? '...' : `${avgScore}%`}
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
            Deterministic matching algorithm
          </p>
        </Card>
      </div>

      {/* Filter Toolbar */}
      <Card className="mb-6">
        <div className="p-4 border-b border-slate-100 dark:border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <SlidersHorizontal className="w-4 h-4 text-sky-600 dark:text-sky-400" />
            <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">
              Pipeline Candidate Filters
            </h3>
            <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 font-medium">
              {candidates.length} of {totalCount}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => navigate('/recruiter/candidate-comparisons')}
              icon={<Sparkles className="w-3.5 h-3.5 text-brand-500" />}
            >
              Compare Workspace
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={handleResetFilters}
              icon={<RefreshCw className="w-3.5 h-3.5" />}
            >
              Reset Filters
            </Button>
            <Button
              size="sm"
              variant="primary"
              onClick={loadCandidates}
              disabled={loading}
              icon={<Search className="w-3.5 h-3.5" />}
            >
              Apply
            </Button>
          </div>
        </div>

        <div className="p-4 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3.5 text-xs">
          {/* Keyword Search */}
          <div>
            <label className="block font-medium text-slate-700 dark:text-slate-300 mb-1">
              Search Candidate / Roll
            </label>
            <div className="relative">
              <input
                type="text"
                placeholder="Name, roll number, or job title..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && loadCandidates()}
                className="w-full pl-8 pr-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-1 focus:ring-sky-500 text-xs"
              />
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-400" />
            </div>
          </div>

          {/* Job Filter */}
          <div>
            <label className="block font-medium text-slate-700 dark:text-slate-300 mb-1">
              Target Job Opening
            </label>
            <select
              value={selectedJobId}
              onChange={(e) => setSelectedJobId(e.target.value)}
              className="w-full py-1.5 px-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-1 focus:ring-sky-500 text-xs"
            >
              <option value="">All Job Postings</option>
              {jobs.map((j) => (
                <option key={j.id} value={j.id}>
                  {j.title} ({j.employment_type || `#${j.id}`})
                </option>
              ))}
            </select>
          </div>

          {/* Eligibility Filter */}
          <div>
            <label className="block font-medium text-slate-700 dark:text-slate-300 mb-1">
              Academic Eligibility
            </label>
            <select
              value={eligibility}
              onChange={(e) => setEligibility(e.target.value as 'all' | 'eligible_only' | 'ineligible_only')}
              className="w-full py-1.5 px-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-1 focus:ring-sky-500 text-xs font-medium"
            >
              <option value="all">All Candidates</option>
              <option value="eligible_only">Eligible Only (Passed Criteria)</option>
              <option value="ineligible_only">Ineligible Only (Criterion Failed)</option>
            </select>
          </div>

          {/* Application Pipeline Stage */}
          <div>
            <label className="block font-medium text-slate-700 dark:text-slate-300 mb-1">
              Recruitment Stage
            </label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="w-full py-1.5 px-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-1 focus:ring-sky-500 text-xs"
            >
              <option value="">All Recruitment Stages</option>
              <option value="applied">Applied (Initial)</option>
              <option value="tpo_screened">TPO Screened</option>
              <option value="shortlisted">Shortlisted</option>
              <option value="interview_scheduled">Interview Scheduled</option>
              <option value="interview_completed">Interview Completed</option>
              <option value="offered">Offer Extended</option>
              <option value="offer_accepted">Offer Accepted</option>
              <option value="offer_declined">Offer Declined</option>
              <option value="rejected">Rejected</option>
            </select>
          </div>

          {/* Department Filter */}
          <div>
            <label className="block font-medium text-slate-700 dark:text-slate-300 mb-1">
              Department
            </label>
            <input
              type="text"
              placeholder="e.g. Computer Science, Electronics..."
              value={department}
              onChange={(e) => setDepartment(e.target.value)}
              className="w-full py-1.5 px-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-1 focus:ring-sky-500 text-xs"
            />
          </div>

          {/* Graduation Year */}
          <div>
            <label className="block font-medium text-slate-700 dark:text-slate-300 mb-1">
              Graduation Batch
            </label>
            <input
              type="number"
              placeholder="e.g. 2025, 2026..."
              value={graduationYear}
              onChange={(e) => setGraduationYear(e.target.value)}
              className="w-full py-1.5 px-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-1 focus:ring-sky-500 text-xs"
            />
          </div>

          {/* Min Compatibility Score */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="font-medium text-slate-700 dark:text-slate-300">
                Min Compatibility
              </label>
              <span className="font-bold text-sky-600 dark:text-sky-400">
                {minScore > 0 ? `${minScore}%` : 'Any'}
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              step="5"
              value={minScore}
              onChange={(e) => setMinScore(Number(e.target.value))}
              className="w-full accent-sky-600 h-1.5 bg-slate-200 dark:bg-slate-700 rounded-lg cursor-pointer"
            />
          </div>

          {/* Required Skill */}
          <div>
            <label className="block font-medium text-slate-700 dark:text-slate-300 mb-1">
              Key Technical Skill
            </label>
            <input
              type="text"
              placeholder="e.g. Python, React, SQL..."
              value={skill}
              onChange={(e) => setSkill(e.target.value)}
              className="w-full py-1.5 px-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-1 focus:ring-sky-500 text-xs"
            />
          </div>
        </div>
      </Card>

      {/* Candidate Pipeline Table */}
      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400 font-semibold uppercase tracking-wider bg-slate-50/75 dark:bg-slate-800/70">
                <th className="py-3 px-3 w-8 text-center">
                  <span className="sr-only">Select</span>
                </th>
                <th className="py-3 px-4">Candidate Profile</th>
                <th className="py-3 px-3">Role Applied</th>
                <th className="py-3 px-3">Academics & Batch</th>
                <th className="py-3 px-3">Compatibility</th>
                <th className="py-3 px-3">Eligibility</th>
                <th className="py-3 px-3">TPO Screening</th>
                <th className="py-3 px-3">Interviews & Evaluations</th>
                <th className="py-3 px-3">Pipeline Status</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {loading ? (
                <tr>
                  <td colSpan={10} className="py-12 text-center text-slate-500 dark:text-slate-400">
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto text-sky-500 mb-2" />
                    Loading candidates from evaluation workspace...
                  </td>
                </tr>
              ) : candidates.length === 0 ? (
                <tr>
                  <td colSpan={10} className="py-12 text-center text-slate-500 dark:text-slate-400">
                    <Users className="w-8 h-8 mx-auto text-slate-300 dark:text-slate-600 mb-2" />
                    <p className="font-semibold text-slate-700 dark:text-slate-300">
                      No candidates match your filter criteria
                    </p>
                    <p className="text-[11px] mt-1 text-slate-500">
                      Try adjusting the compatibility score slider or clearing filter criteria.
                    </p>
                  </td>
                </tr>
              ) : (
                candidates.map((cand) => {
                  const compatScore = Math.round(cand.compatibility_score || 0);
                  const isChecked = selectedForComparison.includes(cand.application_id);
                  const scoreColor =
                    compatScore >= 80
                      ? 'text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/60 border-emerald-200 dark:border-emerald-800'
                      : compatScore >= 60
                      ? 'text-sky-600 dark:text-sky-400 bg-sky-50 dark:bg-sky-950/60 border-sky-200 dark:border-sky-800'
                      : 'text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/60 border-amber-200 dark:border-amber-800';

                  return (
                    <tr
                      key={cand.application_id}
                      className={`hover:bg-slate-50/80 dark:hover:bg-slate-800/50 transition-colors cursor-pointer group ${
                        isChecked ? 'bg-brand-50/40 dark:bg-brand-950/20' : ''
                      }`}
                      onClick={() => navigate(`/recruiter/candidates/${cand.application_id}`)}
                    >
                      {/* Comparison Checkbox */}
                      <td className="py-3 px-3 text-center" onClick={(e) => toggleSelectForComparison(cand.application_id, e)}>
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => {}}
                          className="rounded border-slate-300 text-brand-600 focus:ring-brand-500 cursor-pointer"
                        />
                      </td>

                      {/* Candidate Profile */}
                      <td className="py-3 px-4">
                        <div className="font-semibold text-slate-900 dark:text-slate-100 group-hover:text-sky-600 dark:group-hover:text-sky-400 transition-colors">
                          {cand.student_name}
                        </div>
                        <div className="text-[11px] text-slate-500 dark:text-slate-400 font-mono flex items-center gap-1.5 mt-0.5">
                          <span>{cand.roll_number}</span>
                          <span>•</span>
                          <span>{cand.email}</span>
                        </div>
                      </td>

                      {/* Target Job */}
                      <td className="py-3 px-3">
                        <div className="font-medium text-slate-800 dark:text-slate-200">
                          {cand.job_title}
                        </div>
                        <div className="text-[11px] text-slate-500 dark:text-slate-400">
                          Applied: {new Date(cand.applied_at).toLocaleDateString()}
                        </div>
                      </td>

                      {/* Academics & Batch */}
                      <td className="py-3 px-3">
                        <div className="font-semibold text-slate-800 dark:text-slate-200">
                          CGPA: {Number(cand.cgpa).toFixed(2)}
                        </div>
                        <div className="text-[11px] text-slate-500 dark:text-slate-400">
                          {cand.department} ({cand.graduation_year})
                        </div>
                      </td>

                      {/* Compatibility Score */}
                      <td className="py-3 px-3">
                        <span
                          className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full font-bold text-xs border ${scoreColor}`}
                        >
                          <Award className="w-3.5 h-3.5" />
                          {compatScore}%
                        </span>
                      </td>

                      {/* Eligibility */}
                      <td className="py-3 px-3">
                        {cand.is_eligible ? (
                          <span className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-medium">
                            <CheckCircle2 className="w-4 h-4" />
                            Eligible
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-rose-500 dark:text-rose-400 font-medium">
                            <XCircle className="w-4 h-4" />
                            Ineligible
                          </span>
                        )}
                      </td>

                      {/* TPO Screening */}
                      <td className="py-3 px-3">
                        <Badge
                          variant={
                            cand.tpo_screening_status === 'shortlisted'
                              ? 'success'
                              : cand.tpo_screening_status === 'rejected'
                              ? 'danger'
                              : cand.tpo_screening_status === 'pending'
                              ? 'warning'
                              : 'neutral'
                          }
                        >
                          {cand.tpo_screening_status === 'bypassed'
                            ? 'DIRECT'
                            : cand.tpo_screening_status.replace(/_/g, ' ').toUpperCase()}
                        </Badge>
                      </td>

                      {/* Interviews & Evaluations */}
                      <td className="py-3 px-3">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-slate-700 dark:text-slate-300">
                            {cand.evaluations_count} eval{cand.evaluations_count !== 1 ? 's' : ''}
                          </span>
                          {cand.average_rating ? (
                            <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 font-semibold text-[11px]">
                              <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
                              {cand.average_rating.toFixed(1)}
                            </span>
                          ) : null}
                        </div>
                        {cand.latest_recommendation && RECOMMENDATION_LABELS[cand.latest_recommendation] && (
                          <div className="mt-1">
                            <Badge
                              variant={RECOMMENDATION_LABELS[cand.latest_recommendation].variant}
                            >
                              {RECOMMENDATION_LABELS[cand.latest_recommendation].label}
                            </Badge>
                          </div>
                        )}
                      </td>

                      {/* Pipeline Status */}
                      <td className="py-3 px-3">
                        <Badge variant={STATUS_BADGE_VARIANTS[cand.current_status] || 'neutral'}>
                          {cand.current_status.replace(/_/g, ' ').toUpperCase()}
                        </Badge>
                      </td>

                      {/* Actions */}
                      <td className="py-3 px-4 text-right" onClick={(e) => e.stopPropagation()}>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => navigate(`/recruiter/candidates/${cand.application_id}`)}
                          icon={<ArrowRight className="w-3.5 h-3.5" />}
                        >
                          Evaluate
                        </Button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Floating Selection Bar for Multi-Candidate Comparison */}
      {selectedForComparison.length >= 2 && (
        <div className="fixed bottom-6 right-8 z-40 bg-slate-900 text-white dark:bg-white dark:text-slate-900 px-5 py-3 rounded-2xl shadow-2xl flex items-center gap-4 border border-slate-700 dark:border-slate-300 animate-in fade-in slide-in-from-bottom-4">
          <div className="text-xs font-semibold">
            {selectedForComparison.length} Candidates Selected
          </div>
          <button
            onClick={() => {
              const targetJobId =
                selectedJobId ||
                candidates.find((c) => selectedForComparison.includes(c.application_id))?.job_id;
              navigate(
                `/recruiter/candidate-comparisons?job_id=${targetJobId}&app_ids=${selectedForComparison.join(
                  ','
                )}`
              );
            }}
            className="px-3.5 py-1.5 bg-brand-600 text-white rounded-lg text-xs font-bold hover:bg-brand-700 transition-colors flex items-center gap-1.5 shadow-sm"
          >
            <Sparkles className="w-3.5 h-3.5" />
            Compare Side-by-Side
          </button>
          <button
            onClick={() => setSelectedForComparison([])}
            className="text-xs text-slate-400 hover:text-white dark:hover:text-slate-900"
          >
            Clear
          </button>
        </div>
      )}
    </DashboardLayout>
  );
};
