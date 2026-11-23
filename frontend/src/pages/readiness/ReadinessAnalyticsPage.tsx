import React, { useEffect, useState } from 'react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { DashboardLayout } from '../../components/layout/DashboardLayout';
import { Card, CardHeader } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { useTheme } from '../../context/ThemeContext';
import { mockInterviewApi, readinessApi } from '../../services/api';
import {
  JobReadinessCheckResponse,
  MockInterviewTargetJob,
  ReadinessCategory,
  ReadinessHistoryResponse,
  ReadinessIndicatorWeights,
  ReadinessSnapshot,
} from '../../types';
import {
  AlertCircle,
  AlertTriangle,
  Award,
  BarChart3,
  BookOpen,
  Briefcase,
  CheckCircle2,
  Compass,
  Info,
  RefreshCw,
  ShieldCheck,
  Sliders,
  Sparkles,
  Target,
  TrendingUp,
  XCircle,
} from 'lucide-react';

const CATEGORY_BADGE: Record<ReadinessCategory, 'success' | 'brand' | 'warning' | 'danger'> = {
  excellent_preparation: 'success',
  placement_ready: 'brand',
  needs_improvement: 'warning',
  requires_significant_preparation: 'danger',
};

const DEFAULT_WEIGHTS: ReadinessIndicatorWeights = {
  verified_skills: 20,
  project_portfolio: 15,
  internship_experience: 10,
  certifications: 8,
  resume_quality: 15,
  mock_interview_performance: 12,
  aptitude_technical_assessment: 10,
  profile_completeness: 10,
};

const WEIGHT_LABELS: { key: keyof ReadinessIndicatorWeights; label: string }[] = [
  { key: 'verified_skills', label: 'Verified Skills' },
  { key: 'project_portfolio', label: 'Projects' },
  { key: 'internship_experience', label: 'Internships' },
  { key: 'certifications', label: 'Certifications' },
  { key: 'resume_quality', label: 'Resume Quality' },
  { key: 'mock_interview_performance', label: 'Mock Interviews' },
  { key: 'aptitude_technical_assessment', label: 'Aptitude / Tech Tests' },
  { key: 'profile_completeness', label: 'Profile Completeness' },
];

export const ReadinessAnalyticsPage: React.FC = () => {
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === 'dark';

  const [loading, setLoading] = useState(true);
  const [calculating, setCalculating] = useState(false);
  const [checkingJob, setCheckingJob] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [snapshot, setSnapshot] = useState<ReadinessSnapshot | null>(null);
  const [history, setHistory] = useState<ReadinessHistoryResponse | null>(null);
  const [targetJobs, setTargetJobs] = useState<MockInterviewTargetJob[]>([]);

  // Custom Weight Tuning
  const [showWeightsPanel, setShowWeightsPanel] = useState(false);
  const [weights, setWeights] = useState<ReadinessIndicatorWeights>(DEFAULT_WEIGHTS);

  // Job-Specific Check
  const [selectedJobId, setSelectedJobId] = useState<number | ''>('');
  const [customTargetRole, setCustomTargetRole] = useState('');
  const [jobCheck, setJobCheck] = useState<JobReadinessCheckResponse | null>(null);

  const loadAll = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const [overviewData, historyData, jobsData] = await Promise.all([
        readinessApi.getOverview(),
        readinessApi.getHistory(),
        mockInterviewApi.getTargetJobs(),
      ]);
      setSnapshot(overviewData);
      setHistory(historyData);
      setTargetJobs(jobsData);
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.detail?.message || err?.response?.data?.detail || 'Unable to load placement readiness analytics.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  const handleRecalculate = async () => {
    setCalculating(true);
    setErrorMsg(null);
    try {
      const newSnap = await readinessApi.calculateSnapshot({
        job_id: selectedJobId === '' ? null : Number(selectedJobId),
        target_role: customTargetRole.trim() || null,
        custom_weights: weights,
        include_ai_recommendations: true,
      });
      setSnapshot(newSnap);
      const updatedHistory = await readinessApi.getHistory();
      setHistory(updatedHistory);
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.detail?.message || 'Failed to calculate new readiness snapshot.');
    } finally {
      setCalculating(false);
    }
  };

  const handleCheckJobReadiness = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedJobId === '' && !customTargetRole.trim()) {
      setErrorMsg('Select a published job posting or enter a target role to check job-specific readiness.');
      return;
    }
    setCheckingJob(true);
    setErrorMsg(null);
    try {
      const res = await readinessApi.checkJobReadiness({
        job_id: selectedJobId === '' ? null : Number(selectedJobId),
        target_role: customTargetRole.trim() || null,
        custom_weights: weights,
      });
      setJobCheck(res);
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.detail?.message || 'Failed to evaluate job-specific readiness.');
    } finally {
      setCheckingJob(false);
    }
  };

  const handleToggleRecommendation = async (recId: string, nextCompleted: boolean) => {
    if (!snapshot) return;
    try {
      const updated = await readinessApi.toggleRecommendation(snapshot.id, recId, nextCompleted);
      setSnapshot(updated);
      const updatedHistory = await readinessApi.getHistory();
      setHistory(updatedHistory);
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.detail?.message || 'Could not update recommendation status.');
    }
  };

  const trendData = (history?.trend ?? []).map((pt, idx) => ({
    label: `#${idx + 1}`,
    score: pt.overall_score,
    target: pt.target_label,
    category: pt.category_label,
  }));

  const weightTotal = Object.values(weights).reduce((acc, v) => acc + v, 0);

  return (
    <DashboardLayout
      role="student"
      title="Placement Readiness Prediction & Analytics"
      subtitle="Transparent preparation index across 8 portfolio, resume, and practice indicators — strictly separate from official academic eligibility."
    >
      {/* Top Action Bar & Transparency Banner */}
      <div className="mb-6 space-y-3">
        <div className="p-4 rounded-xl bg-brand-50 dark:bg-brand-950/40 border border-brand-200 dark:border-brand-800 flex flex-col lg:flex-row lg:items-center justify-between gap-3">
          <div className="flex items-start gap-2.5 text-xs text-brand-950 dark:text-brand-200">
            <ShieldCheck className="w-4 h-4 text-brand-600 dark:text-brand-400 shrink-0 mt-0.5" />
            <p className="leading-relaxed">
              {snapshot?.transparency_notice ||
                'Advisory Preparation Indicator Only: Readiness is NOT a hiring probability and does not modify verified CGPA or official eligibility decisions.'}
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <Button
              size="sm"
              variant="outline"
              onClick={() => setShowWeightsPanel((prev) => !prev)}
            >
              <Sliders className="w-3.5 h-3.5 mr-1.5" />
              {showWeightsPanel ? 'Hide Weights' : 'Configure Weights'}
            </Button>
            <Button size="sm" onClick={handleRecalculate} isLoading={calculating}>
              <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${calculating ? 'animate-spin' : ''}`} />
              Save New Snapshot
            </Button>
          </div>
        </div>

        {errorMsg && (
          <div className="p-3.5 rounded-xl bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-200 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}
      </div>

      {/* Configurable Weights Drawer */}
      {showWeightsPanel && (
        <Card className="mb-6">
          <CardHeader
            title="Configurable Readiness Indicator Weights"
            subtitle={`Adjust relative emphasis (raw total: ${weightTotal.toFixed(0)} pts — normalized automatically to 100.0)`}
            action={
              <Button size="sm" variant="outline" onClick={() => setWeights(DEFAULT_WEIGHTS)}>
                Reset Default
              </Button>
            }
          />
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {WEIGHT_LABELS.map(({ key, label }) => (
              <div key={key} className="p-3 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
                <div className="flex items-center justify-between text-xs font-semibold text-slate-700 dark:text-slate-200 mb-1">
                  <span>{label}</span>
                  <span className="font-mono">{weights[key]} pts</span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={40}
                  step={1}
                  value={weights[key]}
                  onChange={(e) => setWeights((prev) => ({ ...prev, [key]: Number(e.target.value) }))}
                  className="w-full accent-brand-600"
                />
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Top Overview Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        {/* Readiness Index Card */}
        <Card>
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Preparation Readiness Index
            </span>
            {snapshot && (
              <Badge variant={CATEGORY_BADGE[snapshot.category]}>
                {snapshot.category_label}
              </Badge>
            )}
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-extrabold text-slate-900 dark:text-slate-100">
              {loading ? '—' : `${snapshot?.overall_score.toFixed(1) ?? 0}`}
            </span>
            <span className="text-sm font-semibold text-slate-400">/ 100</span>
            {snapshot?.score_delta_from_previous != null && (
              <span
                className={`ml-auto text-xs font-bold ${
                  snapshot.score_delta_from_previous >= 0
                    ? 'text-emerald-600 dark:text-emerald-400'
                    : 'text-rose-600 dark:text-rose-400'
                }`}
              >
                {snapshot.score_delta_from_previous >= 0 ? '+' : ''}
                {snapshot.score_delta_from_previous.toFixed(1)} vs prior
              </span>
            )}
          </div>
          <div className="w-full h-2.5 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden mt-3">
            <div
              className="h-full bg-brand-600 transition-all"
              style={{ width: `${Math.min(100, snapshot?.overall_score ?? 0)}%` }}
            />
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800 text-[11px] text-slate-500 dark:text-slate-400 space-y-1">
            <div>
              Formula Version: <strong className="font-mono text-slate-700 dark:text-slate-300">{snapshot?.formula_version ?? 'v1.0'}</strong>
            </div>
            <div>
              Completed Actions: <strong className="text-slate-700 dark:text-slate-300">{snapshot?.completed_recommendations_count ?? 0}/{snapshot?.total_recommendations_count ?? 0}</strong>
            </div>
          </div>
        </Card>

        {/* Read-Only Official Academic Record Card (Strictly Separated) */}
        <Card>
          <CardHeader
            title="Official Academic Profile (Read-Only)"
            subtitle="Evaluated separately by institutional cutoffs; excluded from preparation readiness"
          />
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800">
              <div className="text-slate-500 dark:text-slate-400 text-[11px]">Verified CGPA</div>
              <div className="text-lg font-bold text-slate-900 dark:text-slate-100 mt-0.5">
                {snapshot?.academic_summary.cgpa != null ? snapshot.academic_summary.cgpa.toFixed(2) : 'Unrecorded'}
              </div>
            </div>
            <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800">
              <div className="text-slate-500 dark:text-slate-400 text-[11px]">Active Backlogs</div>
              <div className="text-lg font-bold text-slate-900 dark:text-slate-100 mt-0.5">
                {snapshot?.academic_summary.active_backlogs ?? 0}
              </div>
            </div>
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-3 leading-relaxed">
            {snapshot?.academic_summary.read_only_notice}
          </p>
        </Card>

        {/* Readiness Categories & Thresholds Guide */}
        <Card>
          <CardHeader
            title="Category Thresholds & Criteria"
            subtitle="Transparent score bands out of 100"
          />
          <div className="space-y-2 text-[11px]">
            {(snapshot?.category_definitions ?? []).map((def) => {
              const active = snapshot?.category === def.category;
              return (
                <div
                  key={def.category}
                  className={`p-2 rounded-lg border ${
                    active
                      ? 'border-brand-400 bg-brand-50/70 dark:bg-brand-950/40'
                      : 'border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/30'
                  }`}
                >
                  <div className="flex items-center justify-between font-bold text-slate-800 dark:text-slate-200">
                    <span>{def.label}</span>
                    <span className="font-mono text-[10px]">
                      {def.min_score}–{def.max_score}
                    </span>
                  </div>
                  <p className="text-slate-500 dark:text-slate-400 mt-0.5">{def.summary}</p>
                </div>
              );
            })}
          </div>
        </Card>
      </div>

      {/* Missing Data & Limitations Notice */}
      {snapshot && (snapshot.missing_data_fields.length > 0 || snapshot.limitations.length > 0) && (
        <Card className="mb-6">
          <CardHeader
            title="Missing Data & Score Limitations"
            subtitle="Incomplete sections reflect unrecorded data rather than poor candidate ability"
          />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div>
              <div className="font-semibold text-amber-700 dark:text-amber-300 flex items-center gap-1.5 mb-2">
                <AlertTriangle className="w-4 h-4" />
                Unrecorded / Incomplete Sections ({snapshot.missing_data_fields.length})
              </div>
              {snapshot.missing_data_fields.length === 0 ? (
                <p className="text-slate-500 dark:text-slate-400">All 8 readiness sections contain recorded data.</p>
              ) : (
                <ul className="space-y-1 list-disc list-inside text-slate-700 dark:text-slate-300">
                  {snapshot.missing_data_fields.map((field) => (
                    <li key={field}>{field}</li>
                  ))}
                </ul>
              )}
            </div>
            <div>
              <div className="font-semibold text-slate-700 dark:text-slate-200 flex items-center gap-1.5 mb-2">
                <Info className="w-4 h-4 text-brand-500" />
                Scope & Fairness Limitations
              </div>
              <ul className="space-y-1 list-disc list-inside text-slate-600 dark:text-slate-400">
                {snapshot.limitations.map((lim, idx) => (
                  <li key={idx}>{lim}</li>
                ))}
              </ul>
            </div>
          </div>
        </Card>
      )}

      {/* 8-Indicator Breakdown + Historical Analytics Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <Card>
          <CardHeader
            title="8-Indicator Breakdown"
            subtitle="How each weighted preparation signal contributes to your total score"
          />
          <div className="space-y-3.5">
            {(snapshot?.indicators ?? []).map((ind) => (
              <div key={ind.key} className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-slate-800 dark:text-slate-200">{ind.label}</span>
                    {!ind.data_present && (
                      <Badge variant="warning" className="text-[10px]">
                        Missing Data
                      </Badge>
                    )}
                  </div>
                  <span className="font-mono font-bold text-slate-700 dark:text-slate-300">
                    {ind.weighted_points.toFixed(1)} / {ind.weight.toFixed(0)} pts ({ind.raw_score_pct.toFixed(0)}%)
                  </span>
                </div>
                <div className="w-full h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                  <div
                    className={`h-full ${
                      !ind.data_present
                        ? 'bg-slate-400'
                        : ind.raw_score_pct >= 75
                        ? 'bg-emerald-500'
                        : ind.raw_score_pct >= 50
                        ? 'bg-brand-500'
                        : 'bg-amber-500'
                    }`}
                    style={{ width: `${Math.min(100, ind.raw_score_pct)}%` }}
                  />
                </div>
                <p className="text-[11px] text-slate-500 dark:text-slate-400">
                  {ind.evidence_summary}
                  {ind.limitation_note ? ` — ${ind.limitation_note}` : ''}
                </p>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <CardHeader
            title="Historical Readiness Progress"
            subtitle="Track preparation snapshots, completed actions, and net score growth"
          />
          {trendData.length === 0 ? (
            <div className="h-[240px] flex flex-col items-center justify-center text-xs text-slate-400">
              <BarChart3 className="w-8 h-8 mb-2 text-slate-300" />
              Save snapshots over time to chart readiness progression.
            </div>
          ) : (
            <div className="h-[240px] w-full">
              <ResponsiveContainer width="100%" height={240}>
                <AreaChart data={trendData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={isDark ? '#1e293b' : '#f1f5f9'} />
                  <XAxis dataKey="label" tick={{ fill: isDark ? '#94a3b8' : '#64748b', fontSize: 11 }} />
                  <YAxis domain={[0, 100]} tick={{ fill: isDark ? '#94a3b8' : '#64748b', fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{
                      borderRadius: '10px',
                      border: `1px solid ${isDark ? '#334155' : '#e2e8f0'}`,
                      backgroundColor: isDark ? '#0f172a' : '#ffffff',
                      fontSize: '12px',
                    }}
                  />
                  <Area type="monotone" dataKey="score" stroke="#4f46e5" strokeWidth={2.5} fill="#4f46e5" fillOpacity={0.18} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}

          {history && history.total_snapshots > 0 && (
            <div className="grid grid-cols-3 gap-3 mt-4 pt-3 border-t border-slate-100 dark:border-slate-800 text-xs">
              <div>
                <div className="text-slate-500 dark:text-slate-400 text-[11px]">Snapshots</div>
                <div className="font-bold text-slate-900 dark:text-slate-100">{history.total_snapshots}</div>
              </div>
              <div>
                <div className="text-slate-500 dark:text-slate-400 text-[11px]">Best Score</div>
                <div className="font-bold text-slate-900 dark:text-slate-100">{history.best_score?.toFixed(1) ?? '—'}</div>
              </div>
              <div>
                <div className="text-slate-500 dark:text-slate-400 text-[11px]">Net Change</div>
                <div className="font-bold text-emerald-600 dark:text-emerald-400">
                  {history.net_change != null ? `${history.net_change >= 0 ? '+' : ''}${history.net_change.toFixed(1)}` : '—'}
                </div>
              </div>
            </div>
          )}
        </Card>
      </div>

      {/* Job-Specific Readiness Diagnostic + Personalized AI Recommendations */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <Card>
          <CardHeader
            title="Job-Specific Readiness Analyzer"
            subtitle="Inspect role skill alignment, portfolio gaps, interview gaps, and separate eligibility status"
          />
          <form onSubmit={handleCheckJobReadiness} className="space-y-3 mb-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-semibold text-slate-600 dark:text-slate-300 mb-1">
                  Published Job Posting
                </label>
                <select
                  value={selectedJobId}
                  onChange={(e) => setSelectedJobId(e.target.value ? Number(e.target.value) : '')}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100"
                >
                  <option value="">-- Choose Published Role --</option>
                  {targetJobs.map((job) => (
                    <option key={job.id} value={job.id}>
                      {job.title} — {job.company_name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-600 dark:text-slate-300 mb-1">
                  Or Custom Target Role
                </label>
                <input
                  type="text"
                  value={customTargetRole}
                  onChange={(e) => setCustomTargetRole(e.target.value)}
                  placeholder="e.g., Data Analyst / Backend Engineer"
                  className="w-full px-3 py-2 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100"
                />
              </div>
            </div>
            <Button type="submit" size="sm" isLoading={checkingJob}>
              <Target className="w-3.5 h-3.5 mr-1.5" />
              Analyze Job Readiness
            </Button>
          </form>

          {jobCheck ? (
            <div className="space-y-3 pt-3 border-t border-slate-100 dark:border-slate-800 text-xs">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="font-bold text-slate-900 dark:text-slate-100">{jobCheck.target_label}</div>
                <div className="flex items-center gap-2">
                  <Badge variant={CATEGORY_BADGE[jobCheck.readiness_category]}>
                    Readiness: {jobCheck.readiness_score.toFixed(1)}/100
                  </Badge>
                  {jobCheck.academic_eligibility_checked && (
                    <Badge variant={jobCheck.is_academically_eligible ? 'success' : 'danger'}>
                      {jobCheck.is_academically_eligible ? 'Academically Eligible' : 'Cutoff Not Met'}
                    </Badge>
                  )}
                </div>
              </div>

              {jobCheck.academic_eligibility_checked && !jobCheck.is_academically_eligible && jobCheck.eligibility_reasons.length > 0 && (
                <div className="p-2.5 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-200 text-[11px]">
                  <strong>Academic Eligibility Reasons (Deterministic Engine):</strong>{' '}
                  {jobCheck.eligibility_reasons.join('; ')}
                </div>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/50">
                  <div className="font-semibold text-slate-700 dark:text-slate-200 mb-1">
                    Skill Alignment: {jobCheck.skill_alignment_pct.toFixed(0)}%
                  </div>
                  <div className="text-[11px] text-emerald-700 dark:text-emerald-400">
                    Matched: {jobCheck.matched_skills.length > 0 ? jobCheck.matched_skills.join(', ') : 'None yet'}
                  </div>
                  <div className="text-[11px] text-rose-600 dark:text-rose-400 mt-1">
                    Missing Mandatory:{' '}
                    {jobCheck.missing_mandatory_skills.length > 0 ? jobCheck.missing_mandatory_skills.join(', ') : 'None'}
                  </div>
                  <div className="text-[11px] text-amber-600 dark:text-amber-400 mt-1">
                    Missing Preferred:{' '}
                    {jobCheck.missing_preferred_skills.length > 0 ? jobCheck.missing_preferred_skills.join(', ') : 'None'}
                  </div>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/50 space-y-1.5">
                  <div className="font-semibold text-slate-700 dark:text-slate-200">Portfolio & Interview Gaps</div>
                  {[...jobCheck.portfolio_gaps, ...jobCheck.interview_preparation_gaps].length === 0 ? (
                    <div className="text-[11px] text-emerald-600 dark:text-emerald-400">No major portfolio or interview gaps detected!</div>
                  ) : (
                    <ul className="list-disc list-inside text-[11px] text-slate-600 dark:text-slate-300 space-y-0.5">
                      {[...jobCheck.portfolio_gaps, ...jobCheck.interview_preparation_gaps].map((g, i) => (
                        <li key={i}>{g}</li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Run a target check to compare role requirements against verified skills, portfolio depth, and academic cutoffs.
            </p>
          )}
        </Card>

        {/* Actionable AI Recommendations Checklist */}
        <Card>
          <CardHeader
            title="Personalized Action Plan"
            subtitle="Advisory recommendations powered by AI Provider Engine — check off actions as you complete them"
          />
          <div className="space-y-2.5">
            {(snapshot?.recommendations ?? []).map((rec) => (
              <div
                key={rec.id}
                className={`p-3 rounded-xl border transition-colors ${
                  rec.completed
                    ? 'bg-emerald-50/50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800'
                    : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800'
                }`}
              >
                <div className="flex items-start gap-2.5">
                  <input
                    type="checkbox"
                    checked={rec.completed}
                    onChange={(e) => handleToggleRecommendation(rec.id, e.target.checked)}
                    className="mt-1 accent-brand-600 w-4 h-4 shrink-0 cursor-pointer"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span
                        className={`text-xs font-bold ${
                          rec.completed ? 'line-through text-slate-500' : 'text-slate-900 dark:text-slate-100'
                        }`}
                      >
                        {rec.title}
                      </span>
                      <Badge
                        variant={rec.priority === 'high' ? 'danger' : rec.priority === 'medium' ? 'warning' : 'neutral'}
                        className="text-[10px]"
                      >
                        {rec.priority}
                      </Badge>
                    </div>
                    <p className="text-[11px] text-slate-600 dark:text-slate-300 mt-1">{rec.description}</p>
                    <div className="text-[10px] text-brand-600 dark:text-brand-400 font-semibold mt-1">
                      Impact: {rec.estimated_impact}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Historical Snapshot Log */}
      {history && history.snapshots.length > 0 && (
        <Card>
          <CardHeader
            title="Saved Readiness Snapshots"
            subtitle="Versioned historical ledger of scores, targets, and remaining skill gaps"
          />
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-700 text-[11px] uppercase text-slate-500">
                  <th className="py-2 pr-3">Calculated</th>
                  <th className="py-2 pr-3">Target Scope</th>
                  <th className="py-2 pr-3">Score</th>
                  <th className="py-2 pr-3">Delta</th>
                  <th className="py-2 pr-3">Category</th>
                  <th className="py-2 pr-3">Actions Done</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {history.snapshots.map((item) => (
                  <tr key={item.id}>
                    <td className="py-2.5 pr-3 text-slate-600 dark:text-slate-300">
                      {new Date(item.calculated_at).toLocaleString()}
                    </td>
                    <td className="py-2.5 pr-3 font-medium text-slate-800 dark:text-slate-200">
                      {item.job_title || item.target_role || 'General Campus Readiness'}
                    </td>
                    <td className="py-2.5 pr-3 font-bold text-slate-900 dark:text-slate-100">
                      {item.overall_score.toFixed(1)}
                    </td>
                    <td className="py-2.5 pr-3">
                      {item.score_delta_from_previous == null ? (
                        <span className="text-slate-400">—</span>
                      ) : (
                        <span
                          className={
                            item.score_delta_from_previous >= 0
                              ? 'text-emerald-600 dark:text-emerald-400 font-semibold'
                              : 'text-rose-600 dark:text-rose-400 font-semibold'
                          }
                        >
                          {item.score_delta_from_previous >= 0 ? '+' : ''}
                          {item.score_delta_from_previous.toFixed(1)}
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 pr-3">
                      <Badge variant={CATEGORY_BADGE[item.category]}>{item.category_label}</Badge>
                    </td>
                    <td className="py-2.5 pr-3 text-slate-600 dark:text-slate-300">
                      {item.completed_recommendations_count} / {item.total_recommendations_count}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </DashboardLayout>
  );
};

