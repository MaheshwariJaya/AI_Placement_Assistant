import React, { useState, useEffect } from 'react';
import { Card, CardHeader } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { resumeApi } from '../../services/api';
import {
  Resume,
  ResumeFeedbackResponse,
  FeedbackTargetJob,
  ResumeSectionEvaluation,
  ResumeRewrittenSnippet,
  FeedbackSectionType,
  RewriteCategory,
} from '../../types';
import {
  Sparkles,
  AlertCircle,
  CheckCircle2,
  Copy,
  Check,
  Clock,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  Target,
  Filter,
  ShieldCheck,
  RefreshCw,
  ExternalLink,
  Info,
  Briefcase,
  Layers,
  Award,
} from 'lucide-react';

interface ResumeFeedbackSectionProps {
  resume: Resume;
  onSwitchToEntities: () => void;
}

export const ResumeFeedbackSection: React.FC<ResumeFeedbackSectionProps> = ({
  resume,
  onSwitchToEntities,
}) => {
  const [feedbackResponse, setFeedbackResponse] = useState<ResumeFeedbackResponse | null>(null);
  const [jobs, setJobs] = useState<FeedbackTargetJob[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null);

  // Loading & Action States
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [cooldownSeconds, setCooldownSeconds] = useState<number | null>(null);

  // Interactive UI States
  const [copiedSnippetId, setCopiedSnippetId] = useState<string | null>(null);
  const [expandedSections, setExpandedSections] = useState<Set<FeedbackSectionType>>(
    new Set(['structure', 'ats_readability', 'action_impact', 'skills_organization', 'project_depth', 'job_alignment'])
  );
  const [selectedRewriteFilter, setSelectedRewriteFilter] = useState<string>('all');

  // Load existing feedback and jobs on mount or resume change
  useEffect(() => {
    loadJobs();
    loadExistingFeedback();
  }, [resume.id]);

  // Cooldown countdown timer
  useEffect(() => {
    if (cooldownSeconds === null || cooldownSeconds <= 0) return;
    const timer = setInterval(() => {
      setCooldownSeconds((prev) => {
        if (prev === null || prev <= 1) {
          clearInterval(timer);
          return null;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [cooldownSeconds]);

  const loadJobs = async () => {
    try {
      const data = await resumeApi.getFeedbackJobs(resume.id);
      setJobs(data);
    } catch {
      // Ignore job listing error if resume not approved yet
    }
  };

  const loadExistingFeedback = async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const cached = await resumeApi.getFeedback(resume.id, selectedJobId || undefined);
      setFeedbackResponse(cached);
    } catch {
      // If 404 FEEDBACK_NOT_FOUND, no cached analysis exists yet
      setFeedbackResponse(null);
    } finally {
      setIsLoading(false);
    }
  };

  const handleGenerateFeedback = async (forceRefresh: boolean = false) => {
    if (forceRefresh) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }
    setErrorMessage(null);

    try {
      const res = await resumeApi.requestFeedback(resume.id, {
        job_id: selectedJobId || null,
        force_refresh: forceRefresh,
      });
      setFeedbackResponse(res);
      setCooldownSeconds(null);
    } catch (err: any) {
      if (err.response?.status === 429) {
        const msg = err.response?.data?.error?.message || 'Cooldown active';
        const match = msg.match(/(\d+)\s*second/i);
        const seconds = match ? parseInt(match[1], 10) : 30;
        setCooldownSeconds(seconds);
        setErrorMessage(
          `Force-refresh cooldown active: please wait ${seconds} seconds before requesting a fresh evaluation.`
        );
      } else {
        setErrorMessage(
          err.response?.data?.error?.message ||
            'Failed to generate resume feedback. Please verify your connection.'
        );
      }
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  const handleCopySnippet = (snippet: ResumeRewrittenSnippet) => {
    navigator.clipboard.writeText(snippet.suggested_rewrite);
    setCopiedSnippetId(snippet.id);
    setTimeout(() => {
      setCopiedSnippetId(null);
    }, 2500);
  };

  const toggleSectionExpand = (section: FeedbackSectionType) => {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(section)) {
        next.delete(section);
      } else {
        next.add(section);
      }
      return next;
    });
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'excellent':
        return <Badge variant="success">Excellent</Badge>;
      case 'good':
        return <Badge variant="info">Good</Badge>;
      case 'needs_work':
        return <Badge variant="warning">Needs Work</Badge>;
      case 'critical_gap':
        return <Badge variant="danger">Critical Gap</Badge>;
      case 'not_assessed':
        return <Badge variant="neutral">Not Assessed</Badge>;
      default:
        return <Badge variant="neutral">{status}</Badge>;
    }
  };

  const getSectionTitle = (section: FeedbackSectionType) => {
    switch (section) {
      case 'structure':
        return 'Structure & Completeness';
      case 'ats_readability':
        return 'ATS Parseability & Formatting';
      case 'action_impact':
        return 'Action Verbs & STAR Impact';
      case 'skills_organization':
        return 'Skills Categorization & Layout';
      case 'project_depth':
        return 'Project & Practical Depth';
      case 'job_alignment':
        return 'Job Alignment & Relevance';
      default:
        return section;
    }
  };

  const getRewriteCategoryBadge = (cat: RewriteCategory) => {
    switch (cat) {
      case 'verb_strengthening':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800">Verb Strengthening</span>;
      case 'quantification_prompt':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800">Quantification Prompt</span>;
      case 'conciseness':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-100 text-purple-800">Conciseness</span>;
      case 'ats_keyword_alignment':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">ATS Keyword</span>;
      case 'grammar_and_tone':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-100 text-indigo-800">Grammar & Tone</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-800">{cat}</span>;
    }
  };

  // If resume is not approved, show guidance prompt
  if (resume.parsing_status !== 'approved') {
    return (
      <Card className="mb-8 p-6 text-center">
        <div className="max-w-xl mx-auto space-y-4">
          <div className="w-12 h-12 rounded-full bg-amber-100 dark:bg-amber-950/50 text-amber-700 dark:text-amber-400 flex items-center justify-center mx-auto">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
            Resume Approval Required for AI Presentation Feedback
          </h3>
          <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
            The AI Resume Quality and Scoring Coach strictly evaluates <strong>verified, approved resume content</strong> to eliminate hallucinations and ground all suggestions in verified coursework and experience.
          </p>
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 text-xs">
            <span>Current Status:</span>
            <Badge variant="warning">{resume.parsing_status.replace('_', ' ')}</Badge>
          </div>
          <div>
            <Button
              variant="primary"
              size="sm"
              onClick={onSwitchToEntities}
              className="bg-brand-600 hover:bg-brand-700"
            >
              Switch to Entity Review & Approve Resume
            </Button>
          </div>
        </div>
      </Card>
    );
  }

  const feedback = feedbackResponse?.feedback;

  return (
    <div className="space-y-6 mb-10">
      {/* Control & Configuration Header Card */}
      <Card>
        <CardHeader
          title="Resume Feedback & Quality Scoring"
          subtitle="Grounded editorial review evaluating structure, ATS parseability, STAR action impact, and target job alignment."
        />

        {/* Advisory Scope Disclaimer Banner */}
        <div className="p-3.5 mb-5 rounded-lg bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800/60 text-xs text-blue-900 dark:text-blue-200 flex items-start gap-2.5">
          <Info className="w-4 h-4 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            <span className="font-bold">AI Resume Presentation Score — Advisory Only:</span>
            <p className="text-[11px] text-blue-800 dark:text-blue-300/90 leading-relaxed">
              This score evaluates the <strong>writing style, formatting, and structural clarity</strong> of your resume document. It is strictly advisory editorial coaching and does not alter your official institutional placement eligibility cutoffs or employer application decisions.
            </p>
          </div>
        </div>

        {/* Error / Cooldown Alert */}
        {errorMessage && (
          <div className="p-3 mb-4 rounded-lg bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-800/60 text-xs text-rose-800 dark:text-rose-300 flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-rose-600 dark:text-rose-400 flex-shrink-0 mt-0.5" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Job Selection & Action Controls */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 pt-2 border-t border-slate-100 dark:border-slate-800">
          <div className="flex-1 max-w-lg space-y-1.5">
            <label className="text-xs font-semibold text-slate-700 dark:text-slate-200 flex items-center gap-1.5">
              <Target className="w-3.5 h-3.5 text-brand-600 dark:text-brand-400" />
              Target Job Posting (Optional)
            </label>
            <select
              value={selectedJobId || ''}
              onChange={(e) => {
                const val = e.target.value ? parseInt(e.target.value, 10) : null;
                setSelectedJobId(val);
              }}
              className="w-full text-xs p-2 rounded-lg border border-slate-300 dark:border-slate-700 focus:outline-none focus:ring-1 focus:ring-brand-500 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
            >
              <option value="">General Resume Evaluation (No target job)</option>
              {jobs.map((j) => (
                <option key={j.id} value={j.id}>
                  {j.title} — {j.company_name} {j.is_campus_exclusive ? '(Campus Drive)' : ''}
                </option>
              ))}
            </select>
            <p className="text-[10px] text-slate-400 dark:text-slate-500">
              Selecting a target job enables domain-specific keyword alignment and skill-gap identification.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="primary"
              size="sm"
              onClick={() => handleGenerateFeedback(false)}
              disabled={isLoading || isRefreshing}
              className="bg-brand-600 hover:bg-brand-700"
            >
              <Sparkles className="w-3.5 h-3.5 mr-1.5" />
              {isLoading ? 'Analyzing Quality...' : feedbackResponse ? 'Re-Analyze Quality' : 'Analyze Resume Quality'}
            </Button>

            {feedbackResponse && (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => handleGenerateFeedback(true)}
                disabled={isLoading || isRefreshing || cooldownSeconds !== null}
                className="!text-slate-600 dark:!text-slate-300 hover:!bg-slate-100 dark:hover:!bg-slate-800"
                title={cooldownSeconds ? `Cooldown active (${cooldownSeconds}s)` : 'Bypass cache and force re-evaluation'}
              >
                <RefreshCw className={`w-3.5 h-3.5 mr-1 ${isRefreshing ? 'animate-spin' : ''}`} />
                {cooldownSeconds !== null ? `Wait ${cooldownSeconds}s` : 'Force Refresh'}
              </Button>
            )}
          </div>
        </div>
      </Card>

      {/* Loading Skeleton Indicator */}
      {isLoading && (
        <Card className="p-8 text-center">
          <div className="inline-flex items-center gap-3 text-sm text-brand-700 dark:text-brand-400 font-semibold">
            <RefreshCw className="w-5 h-5 animate-spin" />
            <span>Evaluating resume presentation, ATS structure, and STAR impact...</span>
          </div>
          <p className="text-xs text-slate-400 dark:text-slate-500 mt-2">
            Verifying sections and grounding rewrites in your approved portfolio evidence.
          </p>
        </Card>
      )}

      {/* Main Feedback Display */}
      {!isLoading && feedbackResponse && feedback && (
        <>
          {/* Metadata Audit & Cache Strip */}
          <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-xs text-slate-600 dark:text-slate-300">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-700 dark:text-slate-200">Cache Status:</span>
              <span className={`px-2 py-0.5 rounded text-[11px] font-mono ${
                feedbackResponse.is_cached
                  ? 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/60'
                  : 'bg-blue-50 dark:bg-blue-950/40 text-blue-800 dark:text-blue-300 border border-blue-200 dark:border-blue-800/60'
              }`}>
                {feedbackResponse.is_cached
                  ? '⚡ Cached Result (0 API tokens consumed)'
                  : `Evaluated via ${feedbackResponse.usage.provider} (${feedbackResponse.usage.total_tokens} tokens)`}
              </span>
            </div>
            <div className="text-[11px] text-slate-500 dark:text-slate-400 flex items-center gap-1">
              <Clock className="w-3.5 h-3.5" />
              <span>Evaluated: {new Date(feedbackResponse.evaluated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
            </div>
          </div>

          {/* Overall Score & Executive Summary Hero Card */}
          <Card className="overflow-hidden border-t-4 border-t-brand-600">
            <div className="p-6 grid grid-cols-1 md:grid-cols-3 gap-6 items-center">
              {/* Score Meter */}
              <div className="text-center md:border-r md:border-slate-100 dark:md:border-slate-800 md:pr-6">
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  AI Resume Presentation Score
                </span>
                <div className="my-2 flex items-baseline justify-center gap-1">
                  <span className={`text-5xl font-black ${
                    feedback.overall_presentation_score >= 85
                      ? 'text-emerald-600 dark:text-emerald-400'
                      : feedback.overall_presentation_score >= 70
                      ? 'text-blue-600 dark:text-blue-400'
                      : feedback.overall_presentation_score >= 50
                      ? 'text-amber-600 dark:text-amber-400'
                      : 'text-rose-600 dark:text-rose-400'
                  }`}>
                    {feedback.overall_presentation_score.toFixed(0)}
                  </span>
                  <span className="text-base text-slate-400 dark:text-slate-500 font-bold">/ 100</span>
                </div>
                <div className="mt-1">
                  {getStatusBadge(
                    feedback.overall_presentation_score >= 85
                      ? 'excellent'
                      : feedback.overall_presentation_score >= 70
                      ? 'good'
                      : feedback.overall_presentation_score >= 50
                      ? 'needs_work'
                      : 'critical_gap'
                  )}
                </div>
                <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-2 font-medium">
                  Advisory Editorial Score — Does not affect placement eligibility
                </p>
              </div>

              {/* Executive Summary & Priority Actions */}
              <div className="md:col-span-2 space-y-4">
                <div>
                  <h4 className="text-xs font-bold text-slate-900 dark:text-slate-100 uppercase tracking-wider mb-1 flex items-center gap-1.5">
                    <Award className="w-4 h-4 text-brand-600 dark:text-brand-400" /> Executive Overview
                  </h4>
                  <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
                    {feedback.executive_summary}
                  </p>
                </div>

                {/* Priority Action Items */}
                <div className="bg-slate-50 dark:bg-slate-800/60 p-3.5 rounded-lg border border-slate-200 dark:border-slate-700">
                  <span className="text-xs font-bold text-slate-800 dark:text-slate-100 block mb-2 flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                    Top Priority Action Items
                  </span>
                  <ul className="space-y-1.5">
                    {feedback.priority_action_items.map((item, idx) => (
                      <li key={idx} className="text-xs text-slate-700 dark:text-slate-300 flex items-start gap-2">
                        <span className="w-4 h-4 rounded-full bg-brand-100 dark:bg-brand-950/60 text-brand-700 dark:text-brand-300 font-bold text-[10px] flex items-center justify-center flex-shrink-0 mt-0.5">
                          {idx + 1}
                        </span>
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          </Card>

          {/* Job Alignment Section (when evaluated against a target job) */}
          {feedback.job_alignment && (
            <Card className="border border-brand-200 dark:border-brand-800/60 bg-gradient-to-br from-brand-50/40 dark:from-brand-950/30 to-white dark:to-slate-900">
              <CardHeader
                title={`Target Job Alignment: ${feedback.job_alignment.job_title}`}
                subtitle={`Targeting ${feedback.job_alignment.company_name}`}
              />

              <div className="p-5 space-y-4">
                {/* Deterministic Compatibility Authority Notice */}
                {feedback.job_alignment.deterministic_compatibility_score !== null &&
                  feedback.job_alignment.deterministic_compatibility_score !== undefined && (
                    <div className="p-3 rounded-lg bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800/60 text-xs text-emerald-900 dark:text-emerald-200 flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400 flex-shrink-0" />
                        <span>
                          <strong>Deterministic Placement Compatibility:</strong> Evaluated by institutional matching engine (5 weighted dimensions).
                        </span>
                      </div>
                      <span className="font-bold font-mono text-sm px-2 py-0.5 rounded bg-white dark:bg-slate-900 border border-emerald-200 dark:border-emerald-800/60">
                        {feedback.job_alignment.deterministic_compatibility_score.toFixed(1)}%
                      </span>
                    </div>
                  )}

                {/* Skills Match vs Not Evidenced Breakdown */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Matched Skills */}
                  <div className="p-3.5 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
                        <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                        Skills Evidenced in Resume
                      </span>
                      <span className="text-[10px] text-slate-400 dark:text-slate-500">
                        {feedback.job_alignment.matching_skills_in_resume.length} matched
                      </span>
                    </div>
                    {feedback.job_alignment.matching_skills_in_resume.length === 0 ? (
                      <p className="text-xs text-slate-400 dark:text-slate-500 italic">No exact matching skills found.</p>
                    ) : (
                      <div className="flex flex-wrap gap-1.5">
                        {feedback.job_alignment.matching_skills_in_resume.map((s, idx) => (
                          <span
                            key={idx}
                            className="px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-100 dark:bg-emerald-950/50 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/60"
                          >
                            ✓ {s}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Skills Not Evidenced */}
                  <div className="p-3.5 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
                        <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                        Mandatory Skills Not Evidenced
                      </span>
                      <span className="text-[10px] text-slate-400 dark:text-slate-500">
                        {feedback.job_alignment.skills_not_evidenced_mandatory.length} missing
                      </span>
                    </div>
                    {feedback.job_alignment.skills_not_evidenced_mandatory.length === 0 ? (
                      <p className="text-xs text-emerald-600 dark:text-emerald-400 font-medium">All mandatory skills are evidenced in your resume!</p>
                    ) : (
                      <div className="space-y-1">
                        <div className="flex flex-wrap gap-1.5">
                          {feedback.job_alignment.skills_not_evidenced_mandatory.map((s, idx) => (
                            <span
                              key={idx}
                              className="px-2 py-0.5 rounded text-[11px] font-medium bg-rose-50 dark:bg-rose-950/40 text-rose-800 dark:text-rose-300 border border-rose-200 dark:border-rose-800/60"
                            >
                              {s}
                            </span>
                          ))}
                        </div>
                        <p className="text-[10px] text-slate-500 dark:text-slate-400 italic mt-1">
                          * Labeled as: <strong>Not evidenced in the approved resume.</strong> (Does not imply you lack the skill in real life).
                        </p>
                      </div>
                    )}
                  </div>
                </div>

                {/* Preferred Skills Not Evidenced */}
                {feedback.job_alignment.skills_not_evidenced_preferred.length > 0 && (
                  <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 space-y-1.5">
                    <span className="text-xs font-semibold text-slate-700 dark:text-slate-200">
                      Preferred / Bonus Skills Not Evidenced in Resume:
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {feedback.job_alignment.skills_not_evidenced_preferred.map((s, idx) => (
                        <span
                          key={idx}
                          className="px-2 py-0.5 rounded text-[11px] bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700"
                        >
                          {s}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Job Tailoring Advice */}
                {feedback.job_alignment.tailoring_advice.length > 0 && (
                  <div className="p-3 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 space-y-1.5">
                    <span className="text-xs font-bold text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
                      <Target className="w-3.5 h-3.5 text-brand-600 dark:text-brand-400" />
                      Role-Specific Tailoring Suggestions
                    </span>
                    <ul className="space-y-1 text-xs text-slate-600 dark:text-slate-300">
                      {feedback.job_alignment.tailoring_advice.map((adv, idx) => (
                        <li key={idx} className="flex items-start gap-1.5">
                          <span className="text-brand-600 dark:text-brand-400">•</span>
                          <span>{adv}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </Card>
          )}

          {/* Dimension Scorecards Grid */}
          <div className="space-y-3">
            <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <Layers className="w-4 h-4 text-brand-600 dark:text-brand-400" />
              Scoring Dimension Scorecards (Additive Total: {feedback.overall_presentation_score.toFixed(0)} / 100)
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {feedback.section_evaluations.map((sec) => {
                const isExpanded = expandedSections.has(sec.section);
                const pct = sec.max_score > 0 ? (sec.score_awarded / sec.max_score) * 100 : 0;

                return (
                  <Card key={sec.section} className="p-4 border border-slate-200 dark:border-slate-800">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <span className="text-xs font-bold text-slate-900 dark:text-slate-100">
                          {getSectionTitle(sec.section)}
                        </span>
                        <div className="flex items-center gap-2 mt-1">
                          {getStatusBadge(sec.status)}
                          <span className="text-xs font-mono font-bold text-slate-700 dark:text-slate-300">
                            {sec.score_awarded.toFixed(1)} / {sec.max_score.toFixed(1)} pts
                          </span>
                          <span className="text-[10px] text-slate-400 dark:text-slate-500">({pct.toFixed(0)}%)</span>
                        </div>
                      </div>

                      <button
                        onClick={() => toggleSectionExpand(sec.section)}
                        className="p-1 rounded text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
                        title={isExpanded ? 'Collapse' : 'Expand'}
                      >
                        {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </button>
                    </div>

                    {/* Progress Bar */}
                    <div className="w-full bg-slate-100 dark:bg-slate-800 h-1.5 rounded-full overflow-hidden mt-3">
                      <div
                        className={`h-full rounded-full transition-all duration-300 ${
                          pct >= 85
                            ? 'bg-emerald-500'
                            : pct >= 70
                            ? 'bg-blue-500'
                            : pct >= 50
                            ? 'bg-amber-500'
                            : 'bg-rose-500'
                        }`}
                        style={{ width: `${Math.min(100, Math.max(0, pct))}%` }}
                      />
                    </div>

                    {/* Expanded Detail (Evidence, Deductions, Suggestions) */}
                    {isExpanded && (
                      <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800 space-y-2.5 text-xs">
                        {/* Evidence Found */}
                        {sec.evidence_found.length > 0 && (
                          <div>
                            <span className="text-[10px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wide block mb-0.5">
                              Evidence Found in Resume
                            </span>
                            <ul className="space-y-0.5">
                              {sec.evidence_found.map((ev, i) => (
                                <li key={i} className="text-slate-700 dark:text-slate-300 flex items-start gap-1.5 text-[11px]">
                                  <span className="text-emerald-600 dark:text-emerald-400 font-bold">✓</span>
                                  <span>{ev}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Deductions */}
                        {sec.deduction_reasons.length > 0 && (
                          <div>
                            <span className="text-[10px] font-bold text-rose-600 dark:text-rose-400 uppercase tracking-wide block mb-0.5">
                              Deduction Explanations
                            </span>
                            <ul className="space-y-0.5">
                              {sec.deduction_reasons.map((ded, i) => (
                                <li key={i} className="text-rose-700 dark:text-rose-300 flex items-start gap-1.5 text-[11px]">
                                  <span className="text-rose-500 dark:text-rose-400 font-bold">•</span>
                                  <span>{ded}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Suggestions */}
                        {sec.suggestions.length > 0 && (
                          <div>
                            <span className="text-[10px] font-bold text-brand-600 dark:text-brand-400 uppercase tracking-wide block mb-0.5">
                              Actionable Suggestions
                            </span>
                            <ul className="space-y-0.5">
                              {sec.suggestions.map((sug, i) => (
                                <li key={i} className="text-slate-700 dark:text-slate-300 flex items-start gap-1.5 text-[11px]">
                                  <span className="text-brand-500 dark:text-brand-400 font-bold">→</span>
                                  <span>{sug}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Limitations Notice */}
                        {sec.limitations_or_unavailable && (
                          <div className="p-2 rounded bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-[10px] text-slate-500 dark:text-slate-400">
                            <strong>Note:</strong> {sec.limitations_or_unavailable}
                          </div>
                        )}
                      </div>
                    )}
                  </Card>
                );
              })}
            </div>
          </div>

          {/* Interactive Rewrite Studio */}
          <Card className="p-6">
            <div className="border-b border-slate-200 dark:border-slate-800 pb-4 mb-4 flex flex-col md:flex-row md:items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                  Interactive Rewrite Studio
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  Line-by-line phrasing enhancements. <strong>Rewrites are suggestions only</strong>; your master resume is never automatically altered.
                </p>
              </div>

              {/* Category Filter */}
              <div className="flex items-center gap-1.5">
                <Filter className="w-3.5 h-3.5 text-slate-400 dark:text-slate-500" />
                <span className="text-[11px] text-slate-500 dark:text-slate-400">Filter:</span>
                <select
                  value={selectedRewriteFilter}
                  onChange={(e) => setSelectedRewriteFilter(e.target.value)}
                  className="text-xs p-1.5 rounded border border-slate-200 dark:border-slate-700 focus:outline-none focus:ring-1 focus:ring-brand-500 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
                >
                  <option value="all">All Categories ({feedback.rewritten_snippets.length})</option>
                  <option value="verb_strengthening">Verb Strengthening</option>
                  <option value="quantification_prompt">Quantification Prompt</option>
                  <option value="conciseness">Conciseness</option>
                  <option value="ats_keyword_alignment">ATS Keywords</option>
                </select>
              </div>
            </div>

            {/* Snippet Cards */}
            {feedback.rewritten_snippets.length === 0 ? (
              <div className="p-6 text-center text-slate-400 dark:text-slate-500 text-xs">
                No specific line rewrites required for this document.
              </div>
            ) : (
              <div className="space-y-4">
                {feedback.rewritten_snippets
                  .filter((s) => selectedRewriteFilter === 'all' || s.category === selectedRewriteFilter)
                  .map((snippet) => (
                    <div
                      key={snippet.id}
                      className="p-4 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/40 space-y-3"
                    >
                      {/* Top Header of Snippet */}
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          {getRewriteCategoryBadge(snippet.category)}
                          <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">
                            Ref: {snippet.evidence_reference}
                          </span>
                        </div>

                        {/* Metric Placeholder Warning Badge */}
                        {snippet.requires_student_metric && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 dark:bg-amber-950/50 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-800/60 flex items-center gap-1">
                            <AlertTriangle className="w-3 h-3 text-amber-600 dark:text-amber-400" />
                            Fill in [placeholder metrics] with your actual data
                          </span>
                        )}
                      </div>

                      {/* Original vs Suggested Grid */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                        {/* Original */}
                        <div className="p-3 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 space-y-1">
                          <span className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider block">
                            Original Resume Text:
                          </span>
                          <p className="text-slate-600 dark:text-slate-300 italic">
                            &quot;{snippet.original_text}&quot;
                          </p>
                        </div>

                        {/* Suggested Rewrite */}
                        <div className="p-3 rounded-lg bg-emerald-50/60 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800/60 space-y-1">
                          <span className="text-[10px] font-bold text-emerald-800 dark:text-emerald-300 uppercase tracking-wider block">
                            Suggested Professional Phrasing:
                          </span>
                          <p className="text-slate-900 dark:text-slate-100 font-medium leading-relaxed">
                            {snippet.suggested_rewrite}
                          </p>
                        </div>
                      </div>

                      {/* Rationale & Action Footer */}
                      <div className="pt-2 border-t border-slate-200 dark:border-slate-700 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                        <p className="text-[11px] text-slate-600 dark:text-slate-300 italic">
                          <strong>Why this change:</strong> {snippet.rationale}
                        </p>

                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => handleCopySnippet(snippet)}
                          className="flex-shrink-0 !text-[11px] !py-1"
                        >
                          {copiedSnippetId === snippet.id ? (
                            <>
                              <Check className="w-3.5 h-3.5 mr-1 text-emerald-600 dark:text-emerald-400" />
                              <span className="text-emerald-700 dark:text-emerald-300 font-bold">Copied!</span>
                            </>
                          ) : (
                            <>
                              <Copy className="w-3.5 h-3.5 mr-1 text-slate-500 dark:text-slate-400" />
                              <span>Copy Suggested Text</span>
                            </>
                          )}
                        </Button>
                      </div>
                    </div>
                  ))}
              </div>
            )}
          </Card>
        </>
      )}

      {/* Initial Empty State (when no feedback generated yet) */}
      {!isLoading && !feedbackResponse && (
        <Card className="p-10 text-center">
          <div className="max-w-md mx-auto space-y-3">
            <div className="w-12 h-12 rounded-full bg-brand-50 dark:bg-brand-950/50 text-brand-600 dark:text-brand-400 flex items-center justify-center mx-auto">
              <Sparkles className="w-6 h-6" />
            </div>
            <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
              Ready to Analyze: {resume.file_name}
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
              Click <strong>Analyze Resume Quality</strong> above to evaluate presentation readiness, ATS readability, and STAR action verbs grounded in your verified portfolio evidence.
            </p>
            <div className="pt-2">
              <Button
                variant="primary"
                size="sm"
                onClick={() => handleGenerateFeedback(false)}
                className="bg-brand-600 hover:bg-brand-700"
              >
                <Sparkles className="w-3.5 h-3.5 mr-1.5" />
                Analyze Resume Quality Now
              </Button>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
};

