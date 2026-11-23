import React, { useState, useEffect } from 'react';
import { DashboardLayout } from '../../components/layout/DashboardLayout';
import { Card, CardHeader } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { companyApi, jobApi, intelligenceApi } from '../../services/api';
import {
  Company,
  Job,
  CandidateIntelligenceResponse,
  CandidateRankedCard,
  CandidateIneligibleCard,
} from '../../types';
import {
  Briefcase,
  Building,
  Search,
  MapPin,
  Calendar,
  ExternalLink,
  Users,
  CheckCircle2,
  XCircle,
  Sparkles,
  AlertCircle,
  Award,
  BookOpen,
  Code2,
  X,
  Layers,
  GraduationCap,
  ShieldAlert,
} from 'lucide-react';

export const TpoJobsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'jobs' | 'companies'>('jobs');
  const [jobs, setJobs] = useState<Job[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [isVerifying, setIsVerifying] = useState<number | null>(null);
  const [jobStatusFilter, setJobStatusFilter] = useState<'all' | 'published' | 'draft' | 'closed'>('all');
  const [updatingJobId, setUpdatingJobId] = useState<number | null>(null);

  // Candidate Intelligence Modal State
  const [selectedJobForIntelligence, setSelectedJobForIntelligence] = useState<Job | null>(null);
  const [candidateData, setCandidateData] = useState<CandidateIntelligenceResponse | null>(null);
  const [isLoadingCandidates, setIsLoadingCandidates] = useState(false);
  const [candidateError, setCandidateError] = useState<string | null>(null);
  const [candidateModalTab, setCandidateModalTab] = useState<'eligible' | 'ineligible'>('eligible');

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [jobList, compList] = await Promise.all([
        jobApi.list(),
        companyApi.list(),
      ]);
      setJobs(jobList);
      setCompanies(compList);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpdateJobStatus = async (job: Job, status: 'published' | 'draft' | 'closed') => {
    setUpdatingJobId(job.id);
    try {
      await jobApi.updateStatus(job.id, status);
      await loadData();
    } catch (err) {
      console.error('Failed to update job status:', err);
    } finally {
      setUpdatingJobId(null);
    }
  };

  const handleToggleVerification = async (companyId: number, currentStatus: boolean) => {
    setIsVerifying(companyId);
    try {
      await companyApi.verify(companyId, !currentStatus);
      await loadData();
    } catch (err) {
      console.error('Failed to toggle company verification:', err);
    } finally {
      setIsVerifying(null);
    }
  };

  const handleOpenCandidateIntelligence = async (job: Job) => {
    setSelectedJobForIntelligence(job);
    setCandidateData(null);
    setCandidateError(null);
    setCandidateModalTab('eligible');
    setIsLoadingCandidates(true);

    try {
      const data = await intelligenceApi.getCandidateIntelligence(job.id);
      setCandidateData(data);
    } catch (err: any) {
      console.error('Failed to load candidate intelligence:', err);
      const msg =
        err.response?.data?.detail?.message ||
        (typeof err.response?.data?.detail === 'string' ? err.response?.data?.detail : null) ||
        'Unable to load candidate pool intelligence. Cross-institution access may be restricted.';
      setCandidateError(msg);
    } finally {
      setIsLoadingCandidates(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const filteredJobs = jobs.filter((j) => {
    const matchesStatus = jobStatusFilter === 'all' || j.status === jobStatusFilter;
    const q = searchQuery.trim().toLowerCase();
    const matchesQuery =
      !q ||
      j.title.toLowerCase().includes(q) ||
      j.company_name.toLowerCase().includes(q) ||
      j.location.toLowerCase().includes(q);
    return matchesStatus && matchesQuery;
  });

  const filteredCompanies = companies.filter(
    (c) =>
      !searchQuery ||
      c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.industry.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (c.location && c.location.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <DashboardLayout
      role="tpo"
      title="Institutional Placement Opportunities & Company Partners"
      subtitle="Institutional Scope: Coordinate campus drives, inspect hiring partner criteria, and monitor student eligibility."
    >
      {/* Tab Navigation & Search */}
      <Card className="mb-6">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 flex-wrap">
          <div className="flex space-x-1">
            <button
              onClick={() => setActiveTab('jobs')}
              className={`px-3.5 py-2 text-xs font-semibold rounded-lg transition-colors flex items-center gap-1.5 ${activeTab === 'jobs'
                  ? 'bg-brand-50 dark:bg-brand-950/40 text-brand-700 dark:text-brand-300 border border-brand-200 dark:border-brand-800/60'
                  : 'text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800'
                }`}
            >
              <Briefcase className="w-3.5 h-3.5" />
              <span>Campus Job Drives ({jobs.length})</span>
            </button>
            <button
              onClick={() => setActiveTab('companies')}
              className={`px-3.5 py-2 text-xs font-semibold rounded-lg transition-colors flex items-center gap-1.5 ${activeTab === 'companies'
                  ? 'bg-brand-50 dark:bg-brand-950/40 text-brand-700 dark:text-brand-300 border border-brand-200 dark:border-brand-800/60'
                  : 'text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800'
                }`}
            >
              <Building className="w-3.5 h-3.5" />
              <span>Corporate Partners ({companies.length})</span>
            </button>
          </div>

          {activeTab === 'jobs' && (
            <div className="flex flex-wrap items-center gap-1.5">
              {(
                [
                  { id: 'all', label: `All (${jobs.length})` },
                  { id: 'published', label: `Published (${jobs.filter((j) => j.status === 'published').length})` },
                  { id: 'draft', label: `Drafts (${jobs.filter((j) => j.status === 'draft').length})` },
                  { id: 'closed', label: `Closed (${jobs.filter((j) => j.status === 'closed').length})` },
                ] as const
              ).map((pill) => (
                <button
                  key={pill.id}
                  type="button"
                  onClick={() => setJobStatusFilter(pill.id)}
                  className={`px-2.5 py-1.5 text-xs font-medium rounded-lg border transition-colors ${
                    jobStatusFilter === pill.id
                      ? 'bg-slate-900 dark:bg-brand-600 text-white border-slate-900 dark:border-brand-600'
                      : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800'
                  }`}
                >
                  {pill.label}
                </button>
              ))}
            </div>
          )}

          <div className="relative w-full sm:w-72">
            <Search className="w-3.5 h-3.5 text-slate-400 dark:text-slate-500 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder={activeTab === 'jobs' ? 'Search job drives...' : 'Search company partners...'}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full text-xs pl-8 pr-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 focus:outline-none focus:ring-1 focus:ring-brand-500 bg-slate-50/50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 dark:placeholder:text-slate-500"
            />
          </div>
        </div>
      </Card>

      {/* Content Feed */}
      {activeTab === 'jobs' ? (
        filteredJobs.length === 0 ? (
          <Card>
            <div className="text-center py-16 text-slate-400 dark:text-slate-500">
              <Briefcase className="w-10 h-10 mx-auto mb-2 opacity-30 text-slate-500 dark:text-slate-400" />
              <h3 className="text-sm font-bold text-slate-700 dark:text-slate-200">No campus job drives found</h3>
              <p className="text-xs text-slate-400 dark:text-slate-500 mt-1 max-w-sm mx-auto">
                No active recruitment drives match the search criteria. Verified company partners will publish roles here.
              </p>
            </div>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredJobs.map((job) => (
              <Card key={job.id} className="space-y-3">
                <div className="flex items-start justify-between">
                  <div>
                    <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 flex items-center gap-1">
                      <Building className="w-3 h-3 text-slate-400 dark:text-slate-500" />
                      {job.company_name}
                    </span>
                    <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 mt-0.5">{job.title}</h3>
                  </div>
                  <Badge variant={job.status === 'published' ? 'success' : 'neutral'}>
                    {job.status.toUpperCase()}
                  </Badge>
                </div>

                <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500 dark:text-slate-400">
                  <span className="flex items-center gap-1">
                    <MapPin className="w-3.5 h-3.5 text-slate-400 dark:text-slate-500" />
                    {job.location}
                  </span>
                  <span>• {job.employment_type.replace(/_/g, ' ')}</span>
                  <span>• {job.work_mode.replace(/_/g, ' ')}</span>
                  {job.salary_range && <span className="font-bold text-slate-800 dark:text-slate-200">• ₹ {job.salary_range}</span>}
                  {job.ctc_lpa && <span className="font-bold text-slate-800 dark:text-slate-200">• ₹ {job.ctc_lpa} LPA</span>}
                </div>

                <div className="flex flex-wrap gap-1.5 text-[11px]">
                  <span className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                    Min CGPA: <strong>{job.min_cgpa.toFixed(2)}</strong>
                  </span>
                  {job.target_graduation_year && (
                    <span className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                      Batch: <strong>{job.target_graduation_year}</strong>
                    </span>
                  )}
                  <span className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                    Max Backlogs: <strong>{job.max_active_backlogs}</strong>
                  </span>
                </div>

                <div className="pt-2 border-t border-slate-100 dark:border-slate-800 flex flex-wrap items-center justify-between gap-2 text-[11px]">
                  <span className="flex items-center gap-1 text-slate-400 dark:text-slate-500">
                    <Calendar className="w-3 h-3" />
                    Deadline: {new Date(job.application_deadline).toLocaleDateString()}
                  </span>

                  <div className="flex items-center gap-2">
                    {job.status === 'draft' && (
                      <Button
                        size="sm"
                        variant="primary"
                        disabled={updatingJobId === job.id}
                        onClick={() => handleUpdateJobStatus(job, 'published')}
                        className="text-xs font-semibold py-1 px-2.5 h-7"
                      >
                        {updatingJobId === job.id ? 'Publishing...' : 'Publish Role'}
                      </Button>
                    )}
                    {job.status === 'published' && (
                      <Button
                        size="sm"
                        variant="secondary"
                        disabled={updatingJobId === job.id}
                        onClick={() => handleUpdateJobStatus(job, 'closed')}
                        className="text-xs font-semibold py-1 px-2.5 h-7"
                      >
                        {updatingJobId === job.id ? 'Closing...' : 'Close Role'}
                      </Button>
                    )}
                    {job.status === 'closed' && (
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={updatingJobId === job.id}
                        onClick={() => handleUpdateJobStatus(job, 'published')}
                        className="text-xs font-semibold py-1 px-2.5 h-7"
                      >
                        {updatingJobId === job.id ? 'Reopening...' : 'Reopen Role'}
                      </Button>
                    )}
                    <Button
                      size="sm"
                      variant="outline"
                      icon={<Sparkles className="w-3.5 h-3.5 text-brand-600 dark:text-brand-400" />}
                      onClick={() => handleOpenCandidateIntelligence(job)}
                      className="text-xs font-semibold py-1 px-2.5 h-7"
                    >
                      Candidate Intelligence
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )
      ) : filteredCompanies.length === 0 ? (
        <Card>
          <div className="text-center py-16 text-slate-400 dark:text-slate-500">
            <Building className="w-10 h-10 mx-auto mb-2 opacity-30 text-slate-500 dark:text-slate-400" />
            <h3 className="text-sm font-bold text-slate-700 dark:text-slate-200">No corporate partners found</h3>
            <p className="text-xs text-slate-400 dark:text-slate-500 mt-1 max-w-sm mx-auto">
              No registered corporate partners match your query.
            </p>
          </div>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredCompanies.map((c) => (
            <Card key={c.id} className="space-y-3">
              <div className="flex items-start justify-between">
                <div className="w-10 h-10 rounded-lg bg-sky-50 dark:bg-sky-950/40 text-sky-600 dark:text-sky-400 flex items-center justify-center font-bold">
                  <Building className="w-5 h-5" />
                </div>
                <Badge variant={c.is_verified ? 'success' : 'neutral'}>
                  {c.is_verified ? 'Verified' : 'Pending'}
                </Badge>
              </div>

              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">{c.name}</h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{c.industry}</p>
                {c.location && <p className="text-[11px] text-slate-400 dark:text-slate-500 mt-0.5">{c.location}</p>}
              </div>

              {c.description && (
                <p className="text-xs text-slate-600 dark:text-slate-300 line-clamp-2 leading-relaxed bg-slate-50 dark:bg-slate-800/60 p-2 rounded">
                  {c.description}
                </p>
              )}

              <div className="pt-2 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-[11px]">
                <span className="text-slate-500 dark:text-slate-400">
                  Active Openings: <strong className="text-slate-800 dark:text-slate-200">{c.active_jobs_count || 0}</strong>
                </span>
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant={c.is_verified ? 'outline' : 'primary'}
                    onClick={() => handleToggleVerification(c.id, c.is_verified)}
                    isLoading={isVerifying === c.id}
                    className="text-[11px] py-0.5 px-2.5 h-6"
                  >
                    {c.is_verified ? 'Revoke Status' : 'Verify Partner'}
                  </Button>
                  {c.website && (
                    <a
                      href={c.website}
                      target="_blank"
                      rel="noreferrer"
                      className="text-brand-600 dark:text-brand-400 font-semibold flex items-center gap-1 hover:underline"
                    >
                      <span>Website</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* TPO Candidate Placement Drive Intelligence Modal */}
      {selectedJobForIntelligence && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 dark:bg-slate-950/70 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-2xl max-w-4xl w-full p-6 space-y-5 my-8 max-h-[92vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="flex items-start justify-between border-b border-slate-200 dark:border-slate-800 pb-4">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider flex items-center gap-1">
                    <Building className="w-3.5 h-3.5 text-slate-400 dark:text-slate-500" />
                    {selectedJobForIntelligence.company_name}
                  </span>
                  <Badge variant="brand">Campus Placement Drive Intelligence</Badge>
                </div>
                <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 mt-0.5">
                  {selectedJobForIntelligence.title}
                </h2>
                <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500 dark:text-slate-400 mt-1">
                  <span>Min CGPA: <strong>{selectedJobForIntelligence.min_cgpa.toFixed(2)}</strong></span>
                  <span>• Max Backlogs: <strong>{selectedJobForIntelligence.max_active_backlogs}</strong></span>
                  {selectedJobForIntelligence.target_graduation_year && (
                    <span>• Target Batch: <strong>{selectedJobForIntelligence.target_graduation_year}</strong></span>
                  )}
                </div>
              </div>

              <button
                onClick={() => {
                  setSelectedJobForIntelligence(null);
                  setCandidateData(null);
                }}
                className="text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-300 p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Error State Banner */}
            {candidateError && (
              <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-800/60 text-xs text-rose-900 dark:text-rose-200 flex items-start gap-3">
                <ShieldAlert className="w-5 h-5 text-rose-600 dark:text-rose-400 flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-bold text-rose-950 dark:text-rose-100">Institutional Access Notice</h4>
                  <p className="mt-0.5">{candidateError}</p>
                </div>
              </div>
            )}

            {/* Loading State */}
            {isLoadingCandidates ? (
              <div className="py-16 text-center space-y-3">
                <div className="w-10 h-10 border-2 border-brand-600 border-t-transparent rounded-full animate-spin mx-auto"></div>
                <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">
                  Evaluating institutional student cohort against job criteria...
                </p>
              </div>
            ) : candidateData ? (
              <div className="space-y-4">
                {/* Cohort Stats Summary */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
                    <span className="text-[10px] font-bold uppercase text-slate-500 dark:text-slate-400">
                      Total Evaluated Cohort
                    </span>
                    <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-1">
                      {candidateData.total_candidates}
                    </div>
                    <span className="text-[10px] text-slate-400 dark:text-slate-500">Institutional Candidates</span>
                  </div>

                  <div className="p-3.5 rounded-xl bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800/60">
                    <span className="text-[10px] font-bold uppercase text-emerald-700 dark:text-emerald-400">
                      Eligible Talent Pool
                    </span>
                    <div className="text-2xl font-bold text-emerald-800 dark:text-emerald-300 mt-1">
                      {candidateData.eligible_count}
                    </div>
                    <span className="text-[10px] text-emerald-600 dark:text-emerald-400/90">Satisfies 100% of Academic Cutoffs</span>
                  </div>

                  <div className="p-3.5 rounded-xl bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-800/60">
                    <span className="text-[10px] font-bold uppercase text-rose-700 dark:text-rose-400">
                      Ineligible Candidates
                    </span>
                    <div className="text-2xl font-bold text-rose-800 dark:text-rose-300 mt-1">
                      {candidateData.ineligible_count}
                    </div>
                    <span className="text-[10px] text-rose-600 dark:text-rose-400/90">Cutoff Gaps Recorded</span>
                  </div>
                </div>

                {/* Sub-tab Navigation */}
                <div className="flex border-b border-slate-200 dark:border-slate-800 gap-4 text-xs font-semibold">
                  <button
                    onClick={() => setCandidateModalTab('eligible')}
                    className={`pb-2.5 flex items-center gap-1.5 transition-colors border-b-2 ${candidateModalTab === 'eligible'
                        ? 'border-brand-600 text-brand-700 dark:text-brand-400'
                        : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200'
                      }`}
                  >
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                    <span>Ranked Eligible Talent Pool ({candidateData.eligible_count})</span>
                  </button>

                  <button
                    onClick={() => setCandidateModalTab('ineligible')}
                    className={`pb-2.5 flex items-center gap-1.5 transition-colors border-b-2 ${candidateModalTab === 'ineligible'
                        ? 'border-brand-600 text-brand-700 dark:text-brand-400'
                        : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200'
                      }`}
                  >
                    <XCircle className="w-4 h-4 text-rose-500 dark:text-rose-400" />
                    <span>Ineligible Audit Log ({candidateData.ineligible_count})</span>
                  </button>
                </div>

                {/* Tab 1: Ranked Eligible Candidates */}
                {candidateModalTab === 'eligible' && (
                  candidateData.ranked_eligible_candidates.length === 0 ? (
                    <div className="py-12 text-center text-slate-400 dark:text-slate-500">
                      <GraduationCap className="w-10 h-10 mx-auto mb-2 opacity-30 text-slate-500 dark:text-slate-400" />
                      <h4 className="text-sm font-bold text-slate-700 dark:text-slate-200">No Eligible Students in Current Cohort</h4>
                      <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-sm mx-auto">
                        None of the students in your institution currently satisfy all mandatory academic cutoffs (CGPA, backlogs, department, batch) for this drive.
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-3 max-h-[50vh] overflow-y-auto pr-1">
                      {candidateData.ranked_eligible_candidates.map((c) => (
                        <div
                          key={c.student_id}
                          className="p-4 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 hover:border-brand-300 dark:hover:border-brand-600 transition-all space-y-2.5"
                        >
                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                            <div className="flex items-center gap-3">
                              <span className="w-8 h-8 rounded-full bg-brand-100 dark:bg-brand-950/60 text-brand-800 dark:text-brand-300 font-bold text-xs flex items-center justify-center flex-shrink-0">
                                #{c.rank}
                              </span>
                              <div>
                                <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100">{c.student_name}</h4>
                                <p className="text-[11px] text-slate-500 dark:text-slate-400">
                                  Roll: {c.roll_number} • {c.department_name || 'Enrolled Department'} • Batch {c.graduation_year}
                                </p>
                              </div>
                            </div>

                            <div className="flex items-center gap-2 self-start sm:self-auto">
                              <span className="text-xs font-bold text-slate-700 dark:text-slate-200 bg-slate-100 dark:bg-slate-800 px-2.5 py-1 rounded-lg">
                                {c.cgpa.toFixed(2)} CGPA
                              </span>
                              <div className="px-2.5 py-1 rounded-lg bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800/60 text-emerald-800 dark:text-emerald-300 font-black text-xs">
                                {c.compatibility_score.toFixed(1)}% Match
                              </div>
                            </div>
                          </div>

                          {/* 5-Dimension Mini Score Summary */}
                          <div className="grid grid-cols-5 gap-1.5 text-[10px] text-slate-600 dark:text-slate-300 bg-slate-50 dark:bg-slate-800/60 p-2 rounded-lg text-center">
                            <div>
                              <span className="text-slate-400 dark:text-slate-500 block">Skills</span>
                              <span className="font-bold">{c.score_breakdown.skills.toFixed(1)}/50</span>
                            </div>
                            <div>
                              <span className="text-slate-400 dark:text-slate-500 block">Academics</span>
                              <span className="font-bold">{c.score_breakdown.academics.toFixed(1)}/20</span>
                            </div>
                            <div>
                              <span className="text-slate-400 dark:text-slate-500 block">Projects</span>
                              <span className="font-bold">{c.score_breakdown.projects.toFixed(1)}/15</span>
                            </div>
                            <div>
                              <span className="text-slate-400 dark:text-slate-500 block">Experience</span>
                              <span className="font-bold">{c.score_breakdown.experience.toFixed(1)}/7</span>
                            </div>
                            <div>
                              <span className="text-slate-400 dark:text-slate-500 block">Certs</span>
                              <span className="font-bold">{c.score_breakdown.certifications.toFixed(1)}/5</span>
                            </div>
                          </div>

                          {/* Matched skills */}
                          {c.matched_skills && c.matched_skills.length > 0 && (
                            <div className="flex flex-wrap items-center gap-1 text-[10px]">
                              <span className="text-emerald-700 dark:text-emerald-400 font-semibold">Matched Skills:</span>
                              {c.matched_skills.map((s, idx) => (
                                <span
                                  key={idx}
                                  className="px-1.5 py-0.2 rounded bg-emerald-50 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/60 font-medium"
                                >
                                  ✓ {s}
                                </span>
                              ))}
                            </div>
                          )}

                          {/* Match Rationale */}
                          <div className="text-[11px] text-slate-600 dark:text-slate-300 bg-slate-50/70 dark:bg-slate-800/50 p-2 rounded border border-slate-100 dark:border-slate-700/80 font-mono">
                            {c.match_rationale}
                          </div>
                        </div>
                      ))}
                    </div>
                  )
                )}

                {/* Tab 2: Ineligible Candidates Audit Log */}
                {candidateModalTab === 'ineligible' && (
                  candidateData.ineligible_candidates.length === 0 ? (
                    <div className="py-12 text-center text-slate-400 dark:text-slate-500">
                      <CheckCircle2 className="w-10 h-10 mx-auto mb-2 opacity-30 text-emerald-500 dark:text-emerald-400" />
                      <h4 className="text-sm font-bold text-slate-700 dark:text-slate-200">Zero Ineligible Candidates</h4>
                      <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                        All evaluated students in your institutional cohort satisfy the criteria for this drive.
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-3 max-h-[50vh] overflow-y-auto pr-1">
                      {candidateData.ineligible_candidates.map((c) => (
                        <div
                          key={c.student_id}
                          className="p-4 rounded-xl border border-rose-200 dark:border-rose-800/60 bg-rose-50/20 dark:bg-rose-950/20 space-y-2"
                        >
                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                            <div>
                              <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100">{c.student_name}</h4>
                              <p className="text-[11px] text-slate-500 dark:text-slate-400">
                                Roll: {c.roll_number} • {c.department_name || 'Enrolled Department'} • CGPA:{' '}
                                {c.cgpa !== null && c.cgpa !== undefined ? c.cgpa.toFixed(2) : 'Unrecorded'}
                              </p>
                            </div>

                            <div className="flex items-center gap-2 self-start sm:self-auto">
                              <Badge variant="danger">Cutoff Gap</Badge>
                              <span className="text-xs font-semibold text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded">
                                {c.compatibility_score.toFixed(1)}% Match
                              </span>
                            </div>
                          </div>

                          {/* Failed Criteria Badges */}
                          {c.failed_criteria && c.failed_criteria.length > 0 && (
                            <div className="flex flex-wrap items-center gap-1 pt-1 text-[10px]">
                              <span className="text-rose-800 dark:text-rose-300 font-bold">Failed Cutoffs:</span>
                              {c.failed_criteria.map((fc, idx) => (
                                <span
                                  key={idx}
                                  className="px-2 py-0.5 rounded-full bg-rose-100 dark:bg-rose-950/50 text-rose-800 dark:text-rose-300 font-semibold uppercase tracking-wider"
                                >
                                  {fc.replace(/_/g, ' ')}
                                </span>
                              ))}
                            </div>
                          )}

                          {/* Specific Rejection Reasons */}
                          {c.reasons && c.reasons.length > 0 && (
                            <ul className="list-disc list-inside text-[11px] text-rose-700 dark:text-rose-300 space-y-0.5 pt-1">
                              {c.reasons.map((r, idx) => (
                                <li key={idx}>{r}</li>
                              ))}
                            </ul>
                          )}
                        </div>
                      ))}
                    </div>
                  )
                )}
              </div>
            ) : null}

            {/* Modal Footer */}
            <div className="flex items-center justify-between pt-4 border-t border-slate-200 dark:border-slate-800">
              <span className="text-[11px] text-slate-400 dark:text-slate-500">
                Institutional candidate intelligence is strictly sandboxed to your enrolled cohort.
              </span>
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  setSelectedJobForIntelligence(null);
                  setCandidateData(null);
                }}
              >
                Close Intelligence Pool
              </Button>
            </div>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
};
