import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { DashboardLayout } from '../../components/layout/DashboardLayout';
import { Card, CardHeader } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { candidateComparisonApi, recruiterCandidateApi, jobApi } from '../../services/api';
import {
  CandidateComparisonItem,
  CandidateComparisonResponse,
  CandidateComparisonAISummary,
  ComparisonSessionResponse,
  CandidateListItem,
  Job,
} from '../../types';
import {
  Users,
  Search,
  Sparkles,
  Bookmark,
  CheckCircle2,
  XCircle,
  AlertCircle,
  GraduationCap,
  Award,
  Briefcase,
  FileText,
  Star,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Plus,
  Trash2,
  Edit2,
  Save,
  Clock,
  ArrowRight,
  ShieldCheck,
  Building,
  FolderGit2,
  Check,
  X,
  History,
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

export const CandidateComparisonPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  // URL Query Params
  const queryJobId = searchParams.get('job_id');
  const queryAppIds = searchParams.get('app_ids');

  // Main state
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<number | null>(queryJobId ? Number(queryJobId) : null);
  const [availableCandidates, setAvailableCandidates] = useState<CandidateListItem[]>([]);
  const [selectedAppIds, setSelectedAppIds] = useState<number[]>(() => {
    if (queryAppIds) {
      return queryAppIds
        .split(',')
        .map((s) => Number(s.trim()))
        .filter((n) => !isNaN(n) && n > 0)
        .slice(0, 5);
    }
    return [];
  });

  // Comparison result
  const [comparison, setComparison] = useState<CandidateComparisonResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isAiLoading, setIsAiLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Saved sessions drawer / state
  const [savedSessions, setSavedSessions] = useState<ComparisonSessionResponse[]>([]);
  const [showSessionsDrawer, setShowSessionsDrawer] = useState<boolean>(false);
  const [showSaveModal, setShowSaveModal] = useState<boolean>(false);
  const [saveTitle, setSaveTitle] = useState<string>('');
  const [saveNotes, setSaveNotes] = useState<string>('');
  const [includeAiInSave, setIncludeAiInSave] = useState<boolean>(false);
  const [isSaving, setIsSaving] = useState<boolean>(false);

  // Active accordion tabs in matrix
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    academics: true,
    compatibility: true,
    skills: true,
    projects: true,
    experience: true,
    evaluations: true,
    skill_matrix: true,
  });

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => ({ ...prev, [section]: !prev[section] }));
  };

  // 1. Fetch Recruiter Jobs on Mount
  useEffect(() => {
    const fetchJobs = async () => {
      try {
        const jList = await jobApi.list({ my_company_only: true });
        setJobs(jList || []);
        if (!selectedJobId && jList && jList.length > 0) {
          setSelectedJobId(jList[0].id);
        }
      } catch (err) {
        console.error('Failed to load company jobs:', err);
      }
    };
    fetchJobs();
  }, []);

  // 2. Fetch Candidates for Selected Job
  useEffect(() => {
    if (!selectedJobId) {
      setAvailableCandidates([]);
      return;
    }
    const fetchJobCandidates = async () => {
      try {
        const res = await recruiterCandidateApi.listCandidates({
          job_id: selectedJobId,
          limit: 100,
        });
        setAvailableCandidates(res.items || []);
      } catch (err) {
        console.error('Failed to load candidates for job:', err);
      }
    };
    fetchJobCandidates();
    loadSavedSessions(selectedJobId);
  }, [selectedJobId]);

  // Load saved comparison sessions for job
  const loadSavedSessions = async (jobId?: number) => {
    try {
      const res = await candidateComparisonApi.listSessions(jobId);
      setSavedSessions(res.items || []);
    } catch (err) {
      console.error('Failed to load comparison sessions:', err);
    }
  };

  // 3. Execute Comparison
  const runComparison = useCallback(
    async (appIdsToCompare: number[], withAi: boolean = false) => {
      if (!selectedJobId) {
        setErrorMsg('Please select a target job posting.');
        return;
      }
      if (appIdsToCompare.length < 2) {
        setErrorMsg('Please select at least 2 candidates to compare side-by-side.');
        setComparison(null);
        return;
      }
      if (appIdsToCompare.length > 5) {
        setErrorMsg('You can compare a maximum of 5 candidates at a time.');
        return;
      }

      setErrorMsg(null);
      if (withAi) {
        setIsAiLoading(true);
      } else {
        setIsLoading(true);
      }

      try {
        const res = await candidateComparisonApi.compareCandidates({
          job_id: selectedJobId,
          application_ids: appIdsToCompare,
          generate_ai_insights: withAi,
        });
        setComparison(res);

        // Update URL query params without reloading
        setSearchParams({
          job_id: String(selectedJobId),
          app_ids: appIdsToCompare.join(','),
        });
      } catch (err: any) {
        setErrorMsg(err.response?.data?.message || err.message || 'Failed to compare candidates.');
      } finally {
        setIsLoading(false);
        setIsAiLoading(false);
      }
    },
    [selectedJobId, setSearchParams]
  );

  // Trigger comparison when query params or selection changes
  useEffect(() => {
    if (selectedJobId && selectedAppIds.length >= 2) {
      runComparison(selectedAppIds, false);
    }
  }, [selectedJobId]);

  // Candidate selection checkbox handler
  const handleToggleCandidate = (appId: number) => {
    let next: number[];
    if (selectedAppIds.includes(appId)) {
      next = selectedAppIds.filter((id) => id !== appId);
    } else {
      if (selectedAppIds.length >= 5) {
        alert('You can select a maximum of 5 candidates for side-by-side comparison.');
        return;
      }
      next = [...selectedAppIds, appId];
    }
    setSelectedAppIds(next);
    if (next.length >= 2) {
      runComparison(next, false);
    } else {
      setComparison(null);
    }
  };

  // Generate AI Insights on Demand
  const handleGenerateAiInsights = async () => {
    if (!comparison || selectedAppIds.length < 2) return;
    await runComparison(selectedAppIds, true);
  };

  // Save Comparison Session
  const handleSaveSession = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedJobId || selectedAppIds.length < 2) return;
    if (!saveTitle.trim()) {
      alert('Please enter a session title.');
      return;
    }

    setIsSaving(true);
    try {
      await candidateComparisonApi.createSession({
        job_id: selectedJobId,
        title: saveTitle.trim(),
        application_ids: selectedAppIds,
        notes: saveNotes.trim() || undefined,
        include_ai_insights: includeAiInSave || Boolean(comparison?.ai_insights),
      });
      setShowSaveModal(false);
      setSaveTitle('');
      setSaveNotes('');
      setSuccessMsg('Comparison session saved successfully.');
      loadSavedSessions(selectedJobId);
    } catch (err: any) {
      alert(err.response?.data?.message || err.message || 'Failed to save session.');
    } finally {
      setIsSaving(false);
    }
  };

  // Load a Saved Session
  const handleLoadSavedSession = async (sessionId: number) => {
    setIsLoading(true);
    try {
      const { session: sess, comparison: comp } = await candidateComparisonApi.getSession(sessionId);
      setSelectedJobId(sess.job_id);
      setSelectedAppIds(sess.application_ids);
      setComparison(comp);
      setShowSessionsDrawer(false);
      setSuccessMsg(`Loaded saved session: "${sess.title}".`);
    } catch (err: any) {
      alert(err.response?.data?.message || err.message || 'Failed to load saved session.');
    } finally {
      setIsLoading(false);
    }
  };

  // Delete a Saved Session
  const handleDeleteSavedSession = async (sessionId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this saved comparison session?')) return;
    try {
      await candidateComparisonApi.deleteSession(sessionId);
      setSavedSessions((prev) => prev.filter((s) => s.id !== sessionId));
    } catch (err: any) {
      alert(err.response?.data?.message || 'Failed to delete session.');
    }
  };

  return (
    <DashboardLayout
      role="recruiter"
      title="Candidate Comparison & Hiring Insights"
      subtitle="Objective multi-dimensional side-by-side candidate comparison, skill coverage matrix, and evidence-grounded hiring insights."
    >
      <div className="space-y-6">
        {/* Top Control Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <Users className="w-7 h-7 text-brand-600 dark:text-brand-400" />
              Candidate Comparison & Hiring Insights
            </h1>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
              Select 2 to 5 candidates for a specific job posting to compare academic eligibility, skill coverage, portfolios, and evaluation scores.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              icon={<Bookmark className="w-4 h-4" />}
              onClick={() => setShowSessionsDrawer(true)}
            >
              Saved Sessions ({savedSessions.length})
            </Button>

            {comparison && (
              <Button
                variant="primary"
                size="sm"
                icon={<Save className="w-4 h-4" />}
                onClick={() => {
                  setSaveTitle(`Shortlist Comparison - ${comparison.job_title}`);
                  setShowSaveModal(true);
                }}
              >
                Save Session
              </Button>
            )}
          </div>
        </div>

        {/* Alerts */}
        {successMsg && (
          <div className="flex items-center justify-between p-4 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 rounded-xl text-emerald-800 dark:text-emerald-200 text-sm">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400 flex-shrink-0" />
              <span>{successMsg}</span>
            </div>
            <button onClick={() => setSuccessMsg(null)} className="p-1 hover:bg-emerald-100 dark:hover:bg-emerald-900/40 rounded">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {errorMsg && (
          <div className="flex items-center justify-between p-4 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 rounded-xl text-rose-800 dark:text-rose-200 text-sm">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-rose-600 dark:text-rose-400 flex-shrink-0" />
              <span>{errorMsg}</span>
            </div>
            <button onClick={() => setErrorMsg(null)} className="p-1 hover:bg-rose-100 dark:hover:bg-rose-900/40 rounded">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Job & Candidate Selection Bar */}
        <Card className="p-5 bg-white dark:bg-slate-900 border-slate-200/80 dark:border-slate-800 shadow-sm space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Target Job Selector */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Target Job Posting *
              </label>
              <select
                value={selectedJobId || ''}
                onChange={(e) => {
                  const jid = Number(e.target.value);
                  setSelectedJobId(jid);
                  setSelectedAppIds([]);
                  setComparison(null);
                }}
                className="w-full py-2 px-3 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
              >
                {jobs.map((j) => (
                  <option key={j.id} value={j.id}>
                    {j.title} ({j.ctc_lpa ? `${j.ctc_lpa} LPA` : 'Competitive'})
                  </option>
                ))}
              </select>
            </div>

            {/* Selection Counter & Action */}
            <div className="md:col-span-2 flex flex-col justify-end">
              <div className="flex items-center justify-between mb-1 text-xs">
                <span className="font-semibold text-slate-700 dark:text-slate-300">
                  Select Candidates to Compare ({selectedAppIds.length} of 5 selected)
                </span>
                {selectedAppIds.length >= 2 && (
                  <button
                    onClick={() => runComparison(selectedAppIds, false)}
                    className="text-brand-600 dark:text-brand-400 hover:underline font-semibold flex items-center gap-1"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
                    Refresh Comparison
                  </button>
                )}
              </div>

              {availableCandidates.length === 0 ? (
                <div className="text-xs text-slate-500 italic py-2">
                  No applicants found for this job posting yet.
                </div>
              ) : (
                <div className="flex flex-wrap gap-2 max-h-32 overflow-y-auto p-2 bg-slate-50 dark:bg-slate-800/40 rounded-lg border border-slate-200 dark:border-slate-700">
                  {availableCandidates.map((cand) => {
                    const isSelected = selectedAppIds.includes(cand.application_id);
                    return (
                      <button
                        key={cand.application_id}
                        type="button"
                        onClick={() => handleToggleCandidate(cand.application_id)}
                        className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs rounded-lg border transition-all ${
                          isSelected
                            ? 'bg-brand-50 text-brand-700 border-brand-500 dark:bg-brand-950/60 dark:text-brand-300 font-semibold shadow-sm'
                            : 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:border-brand-300'
                        }`}
                      >
                        <span
                          className={`w-3.5 h-3.5 rounded flex items-center justify-center text-[10px] ${
                            isSelected
                              ? 'bg-brand-600 text-white'
                              : 'border border-slate-300 dark:border-slate-600'
                          }`}
                        >
                          {isSelected && '✓'}
                        </span>
                        <span>{cand.student_name}</span>
                        <span className="text-[10px] text-slate-400">({cand.cgpa.toFixed(1)})</span>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </Card>

        {/* COMPARISON RESULTS */}
        {isLoading ? (
          <Card className="p-12 text-center text-slate-500 flex flex-col items-center justify-center space-y-2">
            <RefreshCw className="w-8 h-8 animate-spin text-brand-500" />
            <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">
              Aggregating candidate dimensions, historical scorecards, and skill matrices...
            </p>
          </Card>
        ) : !comparison || comparison.candidates.length < 2 ? (
          <Card className="p-12 text-center text-slate-500 space-y-3 bg-white dark:bg-slate-900">
            <Users className="w-12 h-12 mx-auto text-slate-300 dark:text-slate-600" />
            <h3 className="text-base font-bold text-slate-800 dark:text-slate-200">
              Select 2 to 5 Candidates to Compare
            </h3>
            <p className="text-xs text-slate-500 max-w-md mx-auto">
              Choose candidates from the checklist above or select applicants directly from the Candidate Pipeline to view side-by-side eligibility, skill coverage, projects, and interview ratings.
            </p>
          </Card>
        ) : (
          <div className="space-y-6">
            {/* Top Comparative Standout Highlights */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {comparison.highlights.highest_compatibility && (
                <Card className="p-4 bg-white dark:bg-slate-900 border-slate-200/80 dark:border-slate-800">
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 bg-brand-50 dark:bg-brand-950/60 text-brand-600 dark:text-brand-400 rounded-xl">
                      <Award className="w-5 h-5" />
                    </div>
                    <div>
                      <p className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">
                        Top Compatibility Match
                      </p>
                      <p className="text-base font-bold text-slate-900 dark:text-white truncate">
                        {comparison.highlights.highest_compatibility.candidate_name}
                      </p>
                      <p className="text-xs font-semibold text-brand-600 dark:text-brand-400">
                        {comparison.highlights.highest_compatibility.score.toFixed(1)}% match
                      </p>
                    </div>
                  </div>
                </Card>
              )}

              {comparison.highlights.highest_cgpa && (
                <Card className="p-4 bg-white dark:bg-slate-900 border-slate-200/80 dark:border-slate-800">
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 rounded-xl">
                      <GraduationCap className="w-5 h-5" />
                    </div>
                    <div>
                      <p className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">
                        Highest Academic CGPA
                      </p>
                      <p className="text-base font-bold text-slate-900 dark:text-white truncate">
                        {comparison.highlights.highest_cgpa.candidate_name}
                      </p>
                      <p className="text-xs font-semibold text-emerald-600 dark:text-emerald-400">
                        {comparison.highlights.highest_cgpa.cgpa.toFixed(2)} CGPA
                      </p>
                    </div>
                  </div>
                </Card>
              )}

              {comparison.highlights.most_experience && (
                <Card className="p-4 bg-white dark:bg-slate-900 border-slate-200/80 dark:border-slate-800">
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 bg-amber-50 dark:bg-amber-950/60 text-amber-600 dark:text-amber-400 rounded-xl">
                      <Briefcase className="w-5 h-5" />
                    </div>
                    <div>
                      <p className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">
                        Most Work Experience
                      </p>
                      <p className="text-base font-bold text-slate-900 dark:text-white truncate">
                        {comparison.highlights.most_experience.candidate_name}
                      </p>
                      <p className="text-xs font-semibold text-amber-600 dark:text-amber-400">
                        {comparison.highlights.most_experience.months} months practical
                      </p>
                    </div>
                  </div>
                </Card>
              )}

              {comparison.highlights.highest_rating && (
                <Card className="p-4 bg-white dark:bg-slate-900 border-slate-200/80 dark:border-slate-800">
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 bg-purple-50 dark:bg-purple-950/60 text-purple-600 dark:text-purple-400 rounded-xl">
                      <Star className="w-5 h-5" />
                    </div>
                    <div>
                      <p className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">
                        Top Interview Rating
                      </p>
                      <p className="text-base font-bold text-slate-900 dark:text-white truncate">
                        {comparison.highlights.highest_rating.candidate_name}
                      </p>
                      <p className="text-xs font-semibold text-purple-600 dark:text-purple-400">
                        ★ {comparison.highlights.highest_rating.rating.toFixed(1)}/5.0
                      </p>
                    </div>
                  </div>
                </Card>
              )}
            </div>

            {/* AI-Assisted Evidence-Grounded Hiring Insights */}
            <Card className="p-5 bg-gradient-to-br from-white to-brand-50/20 dark:from-slate-900 dark:to-brand-950/20 border-brand-200/80 dark:border-brand-800/80 shadow-sm space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-brand-100 dark:border-brand-800/60 pb-3">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-brand-600 dark:text-brand-400" />
                  <h3 className="text-base font-bold text-slate-900 dark:text-white">
                    Evidence-Grounded AI Hiring Insights
                  </h3>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  isLoading={isAiLoading}
                  icon={<Sparkles className="w-3.5 h-3.5 text-brand-500" />}
                  onClick={handleGenerateAiInsights}
                >
                  {comparison.ai_insights ? 'Regenerate AI Synthesis' : 'Synthesize Hiring Insights'}
                </Button>
              </div>

              {!comparison.ai_insights ? (
                <p className="text-xs text-slate-500 italic">
                  Click 'Synthesize Hiring Insights' to generate evidence-grounded comparative summaries, shared strengths, candidate-specific differentiators, and suggested interview probing areas.
                </p>
              ) : (
                <div className="space-y-4 text-xs">
                  {/* Shared Strengths */}
                  <div className="p-3 bg-white dark:bg-slate-800/80 rounded-xl border border-slate-200 dark:border-slate-700 space-y-1.5">
                    <span className="font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider text-[11px] block">
                      Shared Candidate Strengths
                    </span>
                    <ul className="list-disc list-inside space-y-1 text-slate-700 dark:text-slate-300">
                      {comparison.ai_insights.shared_strengths.map((str, idx) => (
                        <li key={idx}>{str}</li>
                      ))}
                    </ul>
                  </div>

                  {/* Candidate-by-Candidate Differentiators */}
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    {comparison.candidates.map((c) => {
                      const cName = c.candidate_name;
                      const cStrengths = comparison.ai_insights?.candidate_strengths?.[cName] || [];
                      const cMissing = comparison.ai_insights?.missing_requirements?.[cName] || [];
                      const cProbes = comparison.ai_insights?.recommended_interview_focus?.[cName] || [];

                      return (
                        <div
                          key={c.application_id}
                          className="p-3 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 space-y-2 flex flex-col justify-between"
                        >
                          <div>
                            <div className="font-bold text-slate-900 dark:text-white pb-1 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between">
                              <span>{cName}</span>
                              <Badge variant="brand" size="sm">
                                {c.compatibility_score_at_application.toFixed(1)}% match
                              </Badge>
                            </div>

                            {/* Standout Strengths */}
                            <div className="mt-2 space-y-1">
                              <span className="text-[10px] font-semibold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider block">
                                Key Differentiators
                              </span>
                              <ul className="list-disc list-inside space-y-0.5 text-slate-600 dark:text-slate-300 text-[11px]">
                                {cStrengths.map((s, i) => (
                                  <li key={i}>{s}</li>
                                ))}
                              </ul>
                            </div>

                            {/* Missing / Focus */}
                            {cMissing.length > 0 && (
                              <div className="mt-2 space-y-1">
                                <span className="text-[10px] font-semibold text-rose-600 dark:text-rose-400 uppercase tracking-wider block">
                                  Requirements & Gaps
                                </span>
                                <ul className="list-disc list-inside space-y-0.5 text-slate-600 dark:text-slate-300 text-[11px]">
                                  {cMissing.map((m, i) => (
                                    <li key={i}>{m}</li>
                                  ))}
                                </ul>
                              </div>
                            )}

                            {/* Recommended Interview Focus */}
                            {cProbes.length > 0 && (
                              <div className="mt-2 space-y-1">
                                <span className="text-[10px] font-semibold text-brand-600 dark:text-brand-400 uppercase tracking-wider block">
                                  Interview Focus Probes
                                </span>
                                <ul className="list-disc list-inside space-y-0.5 text-slate-600 dark:text-slate-300 text-[11px] italic">
                                  {cProbes.map((p, i) => (
                                    <li key={i}>"{p}"</li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {/* Safety & Grounding Disclaimer */}
                  <div className="flex items-center gap-2 p-2.5 bg-slate-50 dark:bg-slate-800 rounded-lg text-[11px] text-slate-500">
                    <ShieldCheck className="w-4 h-4 text-brand-500 flex-shrink-0" />
                    <span>{comparison.ai_insights.evidence_grounding_notes}</span>
                  </div>
                </div>
              )}
            </Card>

            {/* SIDE-BY-SIDE COMPARISON TABLE */}
            <Card className="bg-white dark:bg-slate-900 border-slate-200/80 dark:border-slate-800 shadow-sm overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  {/* Sticky Table Header: Candidate Profile Cards */}
                  <thead>
                    <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/80">
                      <th className="py-4 px-4 min-w-[200px] w-1/5 font-bold text-slate-700 dark:text-slate-200 uppercase tracking-wider">
                        Comparative Dimension
                      </th>
                      {comparison.candidates.map((c) => (
                        <th
                          key={c.application_id}
                          className="py-4 px-4 min-w-[240px] font-normal align-top border-l border-slate-200 dark:border-slate-800"
                        >
                          <div className="space-y-2">
                            <div>
                              <div className="font-bold text-sm text-slate-900 dark:text-white">
                                {c.candidate_name}
                              </div>
                              <div className="text-[11px] text-slate-500">
                                {c.roll_number} • {c.department}
                              </div>
                              <div className="text-[11px] text-slate-500">
                                Batch of {c.graduation_year}
                              </div>
                            </div>

                            <div className="flex items-center gap-1.5 flex-wrap">
                              <Badge variant={STATUS_BADGE_VARIANTS[c.current_status] || 'neutral'} size="sm">
                                {c.current_status.replace('_', ' ')}
                              </Badge>
                              {c.is_eligible ? (
                                <Badge variant="success" size="sm">
                                  Eligible
                                </Badge>
                              ) : (
                                <Badge variant="danger" size="sm">
                                  Ineligible
                                </Badge>
                              )}
                            </div>

                            {/* Quick Actions */}
                            <div className="flex items-center gap-1 pt-1">
                              <Button
                                variant="outline"
                                size="sm"
                                className="text-[11px] py-1 px-2"
                                icon={<ExternalLink className="w-3 h-3" />}
                                onClick={() => navigate(`/recruiter/candidates/${c.application_id}`)}
                              >
                                Dossier
                              </Button>
                              <Button
                                variant="secondary"
                                size="sm"
                                className="text-[11px] py-1 px-2"
                                icon={<Clock className="w-3 h-3" />}
                                onClick={() =>
                                  navigate(`/recruiter/interviews?application_id=${c.application_id}`)
                                }
                              >
                                Interview
                              </Button>
                            </div>
                          </div>
                        </th>
                      ))}
                    </tr>
                  </thead>

                  <tbody className="divide-y divide-slate-200 dark:divide-slate-800 text-slate-700 dark:text-slate-300">
                    {/* SECTION 1: ACADEMIC & ELIGIBILITY */}
                    <tr className="bg-slate-100/60 dark:bg-slate-800/40 font-bold">
                      <td colSpan={comparison.candidates.length + 1} className="py-2.5 px-4 text-slate-800 dark:text-slate-200">
                        1. Academic Credentials & Verified Eligibility
                      </td>
                    </tr>

                    <tr>
                      <td className="py-3 px-4 font-semibold text-slate-600 dark:text-slate-400">
                        College CGPA
                      </td>
                      {comparison.candidates.map((c) => (
                        <td key={c.application_id} className="py-3 px-4 border-l border-slate-200 dark:border-slate-800">
                          <span className="text-sm font-bold text-slate-900 dark:text-white">
                            {c.academics.cgpa.toFixed(2)}
                          </span>
                          <span className="text-slate-400 text-[11px]"> / 10.0</span>
                        </td>
                      ))}
                    </tr>

                    <tr>
                      <td className="py-3 px-4 font-semibold text-slate-600 dark:text-slate-400">
                        Active & Total Backlogs
                      </td>
                      {comparison.candidates.map((c) => (
                        <td key={c.application_id} className="py-3 px-4 border-l border-slate-200 dark:border-slate-800">
                          <span className={c.academics.active_backlogs > 0 ? 'text-rose-600 font-bold' : ''}>
                            {c.academics.active_backlogs} active
                          </span>{' '}
                          <span className="text-slate-400 text-[11px]">
                            ({c.academics.total_backlogs} historical total)
                          </span>
                        </td>
                      ))}
                    </tr>

                    <tr>
                      <td className="py-3 px-4 font-semibold text-slate-600 dark:text-slate-400">
                        10th & 12th Percentages
                      </td>
                      {comparison.candidates.map((c) => (
                        <td key={c.application_id} className="py-3 px-4 border-l border-slate-200 dark:border-slate-800">
                          <div>
                            10th:{' '}
                            <span className="font-semibold text-slate-800 dark:text-slate-200">
                              {c.academics.tenth_percentage ? `${c.academics.tenth_percentage}%` : 'Not recorded'}
                            </span>
                          </div>
                          <div>
                            12th:{' '}
                            <span className="font-semibold text-slate-800 dark:text-slate-200">
                              {c.academics.twelfth_percentage ? `${c.academics.twelfth_percentage}%` : 'Not recorded'}
                            </span>
                          </div>
                        </td>
                      ))}
                    </tr>

                    {/* SECTION 2: COMPATIBILITY SCORING */}
                    <tr className="bg-slate-100/60 dark:bg-slate-800/40 font-bold">
                      <td colSpan={comparison.candidates.length + 1} className="py-2.5 px-4 text-slate-800 dark:text-slate-200">
                        2. Deterministic Compatibility Scoring & Historical Snapshot
                      </td>
                    </tr>

                    <tr>
                      <td className="py-3 px-4 font-semibold text-slate-600 dark:text-slate-400">
                        Application-Time Snapshot
                      </td>
                      {comparison.candidates.map((c) => (
                        <td key={c.application_id} className="py-3 px-4 border-l border-slate-200 dark:border-slate-800">
                          <span className="text-base font-bold text-brand-600 dark:text-brand-400">
                            {c.compatibility_score_at_application.toFixed(1)}%
                          </span>
                          <span className="text-[10px] text-slate-400 block">Authoritative historical record</span>
                        </td>
                      ))}
                    </tr>

                    <tr>
                      <td className="py-3 px-4 font-semibold text-slate-600 dark:text-slate-400">
                        Current Profile Re-Check
                      </td>
                      {comparison.candidates.map((c) => (
                        <td key={c.application_id} className="py-3 px-4 border-l border-slate-200 dark:border-slate-800">
                          <span className="font-semibold text-slate-700 dark:text-slate-300">
                            {c.current_compatibility_score.toFixed(1)}%
                          </span>
                          {c.current_compatibility_score !== c.compatibility_score_at_application && (
                            <span className="text-[10px] text-amber-500 block">Portfolio updated since applying</span>
                          )}
                        </td>
                      ))}
                    </tr>

                    <tr>
                      <td className="py-3 px-4 font-semibold text-slate-600 dark:text-slate-400">
                        Component Breakdown
                      </td>
                      {comparison.candidates.map((c) => (
                        <td key={c.application_id} className="py-3 px-4 border-l border-slate-200 dark:border-slate-800 space-y-1">
                          <div className="flex justify-between text-[11px]">
                            <span>Skills:</span>
                            <span className="font-bold">{c.score_breakdown.skills}%</span>
                          </div>
                          <div className="flex justify-between text-[11px]">
                            <span>Academics:</span>
                            <span className="font-bold">{c.score_breakdown.academics}%</span>
                          </div>
                          <div className="flex justify-between text-[11px]">
                            <span>Projects:</span>
                            <span className="font-bold">{c.score_breakdown.projects}%</span>
                          </div>
                          <div className="flex justify-between text-[11px]">
                            <span>Experience:</span>
                            <span className="font-bold">{c.score_breakdown.experience}%</span>
                          </div>
                        </td>
                      ))}
                    </tr>

                    {/* SECTION 3: SKILL COVERAGE */}
                    <tr className="bg-slate-100/60 dark:bg-slate-800/40 font-bold">
                      <td colSpan={comparison.candidates.length + 1} className="py-2.5 px-4 text-slate-800 dark:text-slate-200">
                        3. Skill Requirements & Coverage Ratios
                      </td>
                    </tr>

                    <tr>
                      <td className="py-3 px-4 font-semibold text-slate-600 dark:text-slate-400">
                        Mandatory Skill Coverage
                      </td>
                      {comparison.candidates.map((c) => (
                        <td key={c.application_id} className="py-3 px-4 border-l border-slate-200 dark:border-slate-800 space-y-1.5">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-slate-900 dark:text-white">
                              {c.mandatory_skills_coverage.coverage_percentage.toFixed(0)}%
                            </span>
                            <span className="text-[10px] text-slate-400">
                              ({c.mandatory_skills_coverage.matched.length} of{' '}
                              {c.mandatory_skills_coverage.required.length})
                            </span>
                          </div>

                          {c.mandatory_skills_coverage.missing.length > 0 && (
                            <div className="text-[10px] text-rose-600 dark:text-rose-400 font-medium">
                              Missing: {c.mandatory_skills_coverage.missing.join(', ')}
                            </div>
                          )}
                        </td>
                      ))}
                    </tr>

                    <tr>
                      <td className="py-3 px-4 font-semibold text-slate-600 dark:text-slate-400">
                        Preferred Skill Coverage
                      </td>
                      {comparison.candidates.map((c) => (
                        <td key={c.application_id} className="py-3 px-4 border-l border-slate-200 dark:border-slate-800 space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-slate-900 dark:text-white">
                              {c.preferred_skills_coverage.coverage_percentage.toFixed(0)}%
                            </span>
                            <span className="text-[10px] text-slate-400">
                              ({c.preferred_skills_coverage.matched.length} of{' '}
                              {c.preferred_skills_coverage.required.length})
                            </span>
                          </div>
                        </td>
                      ))}
                    </tr>

                    <tr>
                      <td className="py-3 px-4 font-semibold text-slate-600 dark:text-slate-400">
                        Verified Technical Skills
                      </td>
                      {comparison.candidates.map((c) => (
                        <td key={c.application_id} className="py-3 px-4 border-l border-slate-200 dark:border-slate-800">
                          <div className="flex flex-wrap gap-1 max-h-28 overflow-y-auto">
                            {c.skills.map((s, idx) => (
                              <span
                                key={idx}
                                className="px-1.5 py-0.5 rounded text-[10px] bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700"
                              >
                                {s.skill_name}
                              </span>
                            ))}
                          </div>
                        </td>
                      ))}
                    </tr>

                    {/* SECTION 4: PROJECTS */}
                    <tr className="bg-slate-100/60 dark:bg-slate-800/40 font-bold">
                      <td colSpan={comparison.candidates.length + 1} className="py-2.5 px-4 text-slate-800 dark:text-slate-200">
                        4. Portfolio Projects & Technical Ownership
                      </td>
                    </tr>

                    <tr>
                      <td className="py-3 px-4 font-semibold text-slate-600 dark:text-slate-400">
                        Key Projects
                      </td>
                      {comparison.candidates.map((c) => (
                        <td key={c.application_id} className="py-3 px-4 border-l border-slate-200 dark:border-slate-800 space-y-2">
                          {c.projects.length === 0 ? (
                            <span className="text-slate-400 italic">No portfolio projects listed</span>
                          ) : (
                            c.projects.map((p, idx) => (
                              <div
                                key={idx}
                                className="p-2 bg-slate-50 dark:bg-slate-800/60 rounded border border-slate-200/60 dark:border-slate-700/60 space-y-1"
                              >
                                <div className="font-semibold text-slate-900 dark:text-white truncate">
                                  {p.title}
                                </div>
                                {p.technologies?.length > 0 && (
                                  <div className="text-[10px] text-brand-600 dark:text-brand-400 font-medium truncate">
                                    {p.technologies.join(', ')}
                                  </div>
                                )}
                              </div>
                            ))
                          )}
                        </td>
                      ))}
                    </tr>

                    {/* SECTION 5: EXPERIENCE */}
                    <tr className="bg-slate-100/60 dark:bg-slate-800/40 font-bold">
                      <td colSpan={comparison.candidates.length + 1} className="py-2.5 px-4 text-slate-800 dark:text-slate-200">
                        5. Internships & Work Experience
                      </td>
                    </tr>

                    <tr>
                      <td className="py-3 px-4 font-semibold text-slate-600 dark:text-slate-400">
                        Total Experience
                      </td>
                      {comparison.candidates.map((c) => (
                        <td key={c.application_id} className="py-3 px-4 border-l border-slate-200 dark:border-slate-800">
                          <span className="font-bold text-slate-900 dark:text-white">
                            {c.total_experience_months} months
                          </span>
                          <span className="text-slate-400 text-[11px]"> across {c.experiences.length} roles</span>
                        </td>
                      ))}
                    </tr>

                    <tr>
                      <td className="py-3 px-4 font-semibold text-slate-600 dark:text-slate-400">
                        Work History
                      </td>
                      {comparison.candidates.map((c) => (
                        <td key={c.application_id} className="py-3 px-4 border-l border-slate-200 dark:border-slate-800 space-y-2">
                          {c.experiences.length === 0 ? (
                            <span className="text-slate-400 italic">No formal internships listed</span>
                          ) : (
                            c.experiences.map((e, idx) => (
                              <div
                                key={idx}
                                className="p-2 bg-slate-50 dark:bg-slate-800/60 rounded border border-slate-200/60 dark:border-slate-700/60 space-y-0.5"
                              >
                                <div className="font-semibold text-slate-900 dark:text-white">
                                  {e.job_title}
                                </div>
                                <div className="text-[11px] text-slate-500">{e.company_name}</div>
                              </div>
                            ))
                          )}
                        </td>
                      ))}
                    </tr>

                    {/* SECTION 6: INTERVIEW EVALUATIONS */}
                    <tr className="bg-slate-100/60 dark:bg-slate-800/40 font-bold">
                      <td colSpan={comparison.candidates.length + 1} className="py-2.5 px-4 text-slate-800 dark:text-slate-200">
                        6. Interview Performance & Evaluation Scores
                      </td>
                    </tr>

                    <tr>
                      <td className="py-3 px-4 font-semibold text-slate-600 dark:text-slate-400">
                        Average Interviewer Rating
                      </td>
                      {comparison.candidates.map((c) => (
                        <td key={c.application_id} className="py-3 px-4 border-l border-slate-200 dark:border-slate-800">
                          {c.average_rating ? (
                            <div className="flex items-center gap-1 font-bold text-amber-500">
                              <Star className="w-4 h-4 fill-current" />
                              <span className="text-sm text-slate-900 dark:text-white">
                                {c.average_rating.toFixed(1)}/5.0
                              </span>
                              <span className="text-slate-400 text-[10px]">
                                ({c.evaluations_count} evaluations)
                              </span>
                            </div>
                          ) : (
                            <span className="text-slate-400 italic">Pending evaluation</span>
                          )}
                        </td>
                      ))}
                    </tr>

                    <tr>
                      <td className="py-3 px-4 font-semibold text-slate-600 dark:text-slate-400">
                        Latest Recommendation
                      </td>
                      {comparison.candidates.map((c) => (
                        <td key={c.application_id} className="py-3 px-4 border-l border-slate-200 dark:border-slate-800">
                          {c.latest_recommendation ? (
                            <Badge variant="brand" size="sm">
                              {c.latest_recommendation.replace('_', ' ').toUpperCase()}
                            </Badge>
                          ) : (
                            <span className="text-slate-400 italic">None submitted</span>
                          )}
                        </td>
                      ))}
                    </tr>
                  </tbody>
                </table>
              </div>
            </Card>

            {/* INTERACTIVE SKILL MATRIX */}
            {comparison.skill_matrix.length > 0 && (
              <Card className="bg-white dark:bg-slate-900 border-slate-200/80 dark:border-slate-800 shadow-sm overflow-hidden p-5 space-y-3">
                <h3 className="text-base font-bold text-slate-900 dark:text-white">
                  Cross-Candidate Skill Matrix
                </h3>
                <p className="text-xs text-slate-500">
                  Compare specific technical competencies side-by-side against mandatory and preferred job prerequisites.
                </p>

                <div className="overflow-x-auto pt-2">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800 text-slate-500 uppercase tracking-wider font-semibold">
                        <th className="py-2.5 px-3">Skill Requirement</th>
                        <th className="py-2.5 px-3">Requirement Type</th>
                        {comparison.candidates.map((c) => (
                          <th key={c.application_id} className="py-2.5 px-3 text-center">
                            {c.candidate_name.split(' ')[0]}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                      {comparison.skill_matrix.map((row, idx) => (
                        <tr key={idx} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30">
                          <td className="py-2.5 px-3 font-semibold text-slate-900 dark:text-white">
                            {row.skill_name}
                          </td>
                          <td className="py-2.5 px-3">
                            {row.is_mandatory ? (
                              <Badge variant="danger" size="sm">
                                Mandatory
                              </Badge>
                            ) : (
                              <Badge variant="neutral" size="sm">
                                Preferred
                              </Badge>
                            )}
                          </td>
                          {comparison.candidates.map((c) => {
                            const hasSkill = row.candidate_coverage[String(c.application_id)];
                            return (
                              <td key={c.application_id} className="py-2.5 px-3 text-center">
                                {hasSkill ? (
                                  <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-emerald-100 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 font-bold text-xs">
                                    ✓
                                  </span>
                                ) : (
                                  <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-400 text-xs">
                                    ✕
                                  </span>
                                )}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            )}
          </div>
        )}

        {/* MODAL: Save Comparison Session */}
        {showSaveModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
              <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
                <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                  <Bookmark className="w-5 h-5 text-brand-600" />
                  Save Candidate Comparison Session
                </h3>
                <button onClick={() => setShowSaveModal(false)} className="p-1 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-slate-500">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <form onSubmit={handleSaveSession} className="space-y-4 text-xs">
                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Session Title *
                  </label>
                  <input
                    type="text"
                    required
                    value={saveTitle}
                    onChange={(e) => setSaveTitle(e.target.value)}
                    placeholder="e.g. Final 3 Shortlist - Senior Backend"
                    className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Internal Hiring Deliberations & Notes
                  </label>
                  <textarea
                    rows={4}
                    value={saveNotes}
                    onChange={(e) => setSaveNotes(e.target.value)}
                    placeholder="Record hiring committee feedback, discussion points, trade-offs between candidates..."
                    className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none"
                  />
                </div>

                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="save_ai"
                    checked={includeAiInSave}
                    onChange={(e) => setIncludeAiInSave(e.target.checked)}
                    className="rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                  />
                  <label htmlFor="save_ai" className="text-slate-700 dark:text-slate-300">
                    Include cached AI hiring insights in this saved snapshot
                  </label>
                </div>

                <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-200 dark:border-slate-800">
                  <Button variant="outline" size="sm" type="button" onClick={() => setShowSaveModal(false)}>
                    Cancel
                  </Button>
                  <Button variant="primary" size="sm" type="submit" isLoading={isSaving} icon={<Check className="w-4 h-4" />}>
                    Save Session
                  </Button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* DRAWER / MODAL: Saved Sessions List */}
        {showSessionsDrawer && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-xl w-full p-6 shadow-2xl space-y-4">
              <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
                <div className="flex items-center gap-2">
                  <Bookmark className="w-5 h-5 text-brand-600" />
                  <h3 className="text-base font-bold text-slate-900 dark:text-white">
                    Saved Comparison Sessions
                  </h3>
                </div>
                <button onClick={() => setShowSessionsDrawer(false)} className="p-1 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-slate-500">
                  <X className="w-5 h-5" />
                </button>
              </div>

              {savedSessions.length === 0 ? (
                <div className="py-8 text-center text-slate-500 text-xs">
                  No saved comparison sessions found for this job. Save a session from the comparison view to review later.
                </div>
              ) : (
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {savedSessions.map((s) => (
                    <div
                      key={s.id}
                      onClick={() => handleLoadSavedSession(s.id)}
                      className="p-3 rounded-xl border border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/60 cursor-pointer transition-colors space-y-1.5"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-900 dark:text-white text-sm">
                          {s.title}
                        </span>
                        <button
                          onClick={(e) => handleDeleteSavedSession(s.id, e)}
                          className="p-1 text-slate-400 hover:text-rose-600 transition-colors"
                          title="Delete session"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>

                      <div className="text-xs text-slate-500">
                        {s.job_title} • {s.application_ids.length} candidates compared
                      </div>

                      {s.notes && (
                        <p className="text-xs text-slate-600 dark:text-slate-300 line-clamp-2 italic">
                          "{s.notes}"
                        </p>
                      )}

                      <div className="text-[10px] text-slate-400 pt-1 flex items-center justify-between">
                        <span>Created by {s.created_by_name}</span>
                        <span>{new Date(s.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
};
