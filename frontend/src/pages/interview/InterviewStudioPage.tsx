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
import { mockInterviewApi } from '../../services/api';
import {
  MockInterviewAnalyticsResponse,
  MockInterviewCategory,
  MockInterviewDifficulty,
  MockInterviewSessionDetail,
  MockInterviewSessionSummary,
  MockInterviewTargetJob,
} from '../../types';
import { ActiveInterviewRunner } from './ActiveInterviewRunner';
import { EvaluationReportView } from './EvaluationReportView';
import {
  AlertCircle,
  Award,
  BarChart3,
  BookOpen,
  Briefcase,
  CheckCircle2,
  Clock,
  Code2,
  Compass,
  FolderGit2,
  History,
  Mic,
  Play,
  Sliders,
  Sparkles,
  TrendingUp,
  UserCheck,
} from 'lucide-react';

const CATEGORY_OPTIONS: {
  id: MockInterviewCategory;
  label: string;
  desc: string;
  icon: React.ComponentType<{ className?: string }>;
}[] = [
  { id: 'technical', label: 'Technical', desc: 'Core branch concepts, theory & domain stack', icon: Code2 },
  { id: 'project_based', label: 'Project-Based', desc: 'Design, trade-offs & execution in your projects', icon: FolderGit2 },
  { id: 'behavioral', label: 'Behavioral', desc: 'STAR teamwork, ownership & conflict', icon: UserCheck },
  { id: 'hr', label: 'HR & Fit', desc: 'Motivation, strengths & career goals', icon: Briefcase },
  { id: 'aptitude', label: 'Aptitude', desc: 'Quantitative logic, probability & reasoning', icon: Compass },
];

export const CSE_40_CORE_SUBJECTS: string[] = [
  'Introduction to Computer Programming',
  'Maths for Computing',
  'Principles of Programming Languages',
  'Object Oriented Programming',
  'Data Structures and Algorithms',
  'Logic Design',
  'Professional Practice, Cyber Law and Ethics',
  'Design and Analysis of Algorithms',
  'Web Technologies',
  'Computer Networks',
  'Database Management Systems',
  'Computer Organization and Architecture',
  'Software Engineering',
  'Operating Systems',
  'Theory of Computation',
  'Artificial Intelligence and Machine Learning',
  'Microprocessors and Assembly Programming',
  'Computer Graphics',
  'Java Programming',
  'Robotics and Embedded System',
  'Principles of Compiler Design',
  'Image Processing',
  'System Programming',
  'Advanced Machine Learning',
  'Graphs and Social Networks',
  'Natural Language Processing',
  'Ecommerce and Business Intelligence',
  'Wireless and Mobile Computing',
  'Modern Web Development',
  'Distributed Computing',
  'Data Science & Analytics',
  'Cryptography and Network Security',
  'Blockchain',
  'Biometrics and Bio-Signal Processing',
  'Parallel and GPU Computing',
  'Deep Learning',
  'Computer Vision',
  'Internet of Things',
  'Information Retrieval and Big Data',
  'Cyber Security',
];

const extractErrorMessage = (err: any, fallback: string): string => {
  if (err?.response?.data?.detail) {
    if (typeof err.response.data.detail === 'string') return err.response.data.detail;
    if (err.response.data.detail.message) return err.response.data.detail.message;
  }
  if (err?.response?.data?.error?.message) return err.response.data.error.message;
  if (err?.response?.data?.message) return err.response.data.message;
  if (err?.code === 'ERR_NETWORK' || !err?.response) {
    return 'Backend server is unreachable. Please verify the backend service is running on port 8000.';
  }
  if (err?.message) return err.message;
  return fallback;
};

export const InterviewStudioPage: React.FC = () => {
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === 'dark';
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Overview state
  const [targetJobs, setTargetJobs] = useState<MockInterviewTargetJob[]>([]);
  const [sessions, setSessions] = useState<MockInterviewSessionSummary[]>([]);
  const [analytics, setAnalytics] = useState<MockInterviewAnalyticsResponse | null>(null);
  const [historyFilter, setHistoryFilter] = useState<'all' | MockInterviewCategory>('all');

  // Builder form state
  const [category, setCategory] = useState<MockInterviewCategory>('technical');
  const [difficulty, setDifficulty] = useState<MockInterviewDifficulty>('intermediate');
  const [questionFormat, setQuestionFormat] = useState<'conversational' | 'mcq'>('conversational');
  const [questionCount, setQuestionCount] = useState<number>(5);
  const [timeLimitMinutes, setTimeLimitMinutes] = useState<number>(20);
  const [includeFollowups, setIncludeFollowups] = useState<boolean>(true);
  const [selectedJobId, setSelectedJobId] = useState<number | ''>('');
  const [targetRole, setTargetRole] = useState<string>('');
  const [subjectFocus, setSubjectFocus] = useState<string>('');

  const handleFormatChange = (fmt: 'conversational' | 'mcq') => {
    setQuestionFormat(fmt);
    if (fmt === 'mcq') {
      setQuestionCount(30);
      setTimeLimitMinutes(45);
    } else {
      setQuestionCount(5);
      setTimeLimitMinutes(20);
    }
  };

  const handleQuestionCountChange = (cnt: number) => {
    setQuestionCount(cnt);
    if (questionFormat === 'mcq') {
      if (cnt === 50) setTimeLimitMinutes(60);
      else if (cnt === 30) setTimeLimitMinutes(45);
      else if (cnt === 15) setTimeLimitMinutes(20);
    }
  };

  // Active workspace mode
  const [activeSession, setActiveSession] = useState<MockInterviewSessionDetail | null>(null);

  const loadStudioData = async () => {
    setLoading(true);
    try {
      const [jobsData, sessionsData, analyticsData] = await Promise.all([
        mockInterviewApi.getTargetJobs().catch(() => []),
        mockInterviewApi.listSessions(),
        mockInterviewApi.getAnalytics(),
      ]);
      setTargetJobs(jobsData);
      setSessions(sessionsData);
      setAnalytics(analyticsData);
    } catch (err: any) {
      setErrorMsg(extractErrorMessage(err, 'Unable to load Mock Interview Studio data.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStudioData();
  }, []);

  const handleCreateInterview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (creating) return;
    setErrorMsg(null);
    setCreating(true);
    try {
      const detail = await mockInterviewApi.createSession({
        category,
        difficulty,
        question_format: questionFormat,
        question_count: questionCount,
        job_id: selectedJobId === '' ? null : Number(selectedJobId),
        target_role: targetRole.trim() || null,
        subject_focus: subjectFocus.trim() || null,
        time_limit_minutes: timeLimitMinutes > 0 ? timeLimitMinutes : null,
        include_followups: questionFormat === 'mcq' ? false : includeFollowups,
      });
      setActiveSession(detail);
    } catch (err: any) {
      setErrorMsg(
        extractErrorMessage(err, 'Failed to generate mock interview questions. Check AI configuration.')
      );
    } finally {
      setCreating(false);
    }
  };

  const handleOpenSession = async (sessionId: number, resumeIfPaused: boolean = false) => {
    setErrorMsg(null);
    setLoading(true);
    try {
      const detail = resumeIfPaused
        ? await mockInterviewApi.resumeSession(sessionId)
        : await mockInterviewApi.getSession(sessionId);
      setActiveSession(detail);
    } catch (err: any) {
      setErrorMsg(extractErrorMessage(err, 'Failed to open session.'));
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitAnswer = async (payload: {
    question_id: number;
    answer_text?: string;
    selected_option_key?: string | null;
    input_mode: 'text' | 'voice';
    response_time_seconds: number;
    elapsed_seconds: number;
  }) => {
    if (!activeSession) throw new Error('No active session');
    setSubmitting(true);
    try {
      const res = await mockInterviewApi.submitAnswer(activeSession.id, payload);
      setActiveSession(res.session);
      return {
        followup_generated: res.followup_generated,
        followup_rationale: res.followup_rationale,
        ready_to_complete: res.ready_to_complete,
      };
    } finally {
      setSubmitting(false);
    }
  };

  const handlePause = async (elapsedSeconds: number) => {
    if (!activeSession) return;
    setSubmitting(true);
    try {
      const updated = await mockInterviewApi.pauseSession(activeSession.id, elapsedSeconds);
      setActiveSession(updated);
      await loadStudioData();
    } finally {
      setSubmitting(false);
    }
  };

  const handleResume = async () => {
    if (!activeSession) return;
    setSubmitting(true);
    try {
      const updated = await mockInterviewApi.resumeSession(activeSession.id);
      setActiveSession(updated);
    } finally {
      setSubmitting(false);
    }
  };

  const handleComplete = async (elapsedSeconds: number) => {
    if (!activeSession) return;
    setSubmitting(true);
    setErrorMsg(null);
    try {
      const completed = await mockInterviewApi.completeSession(activeSession.id, elapsedSeconds);
      setActiveSession(completed);
      await loadStudioData();
    } catch (err: any) {
      setErrorMsg(extractErrorMessage(err, 'Failed to evaluate interview session.'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleExitToStudio = async () => {
    setActiveSession(null);
    await loadStudioData();
  };

  const filteredHistory =
    historyFilter === 'all' ? sessions : sessions.filter((s) => s.category === historyFilter);

  return (
    <DashboardLayout
      role="student"
      title="AI Mock Interview & Assessment Studio"
      subtitle="Practice role-specific interviews grounded in your verified skills, projects, and approved resume."
    >
      {errorMsg && (
        <div className="mb-5 p-3.5 rounded-xl bg-rose-50 dark:bg-rose-950/50 border border-rose-200 dark:border-rose-800 flex items-center gap-2.5 text-xs text-rose-800 dark:text-rose-200">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Mode 1: Completed / Ended Evaluation View */}
      {activeSession && (activeSession.status === 'completed' || activeSession.status === 'abandoned') && (
        <EvaluationReportView
          session={activeSession}
          onBackToStudio={handleExitToStudio}
          onStartSimilar={() => setActiveSession(null)}
        />
      )}

      {/* Mode 2: Active / Paused Interview Runner */}
      {activeSession && (activeSession.status === 'in_progress' || activeSession.status === 'paused') && (
        <ActiveInterviewRunner
          session={activeSession}
          submitting={submitting}
          onSubmitAnswer={handleSubmitAnswer}
          onPause={handlePause}
          onResume={handleResume}
          onComplete={handleComplete}
          onExit={handleExitToStudio}
        />
      )}

      {/* Mode 3: Studio Hub (Setup + Analytics + History) */}
      {!activeSession && (
        <div className="space-y-6">
          {/* KPI Summary Row */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <div className="flex items-center justify-between text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">
                <span>Completed Practices</span>
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
              </div>
              <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-2">
                {loading ? '—' : analytics?.completed_sessions ?? 0}
              </div>
              <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                {analytics?.in_progress_or_paused_sessions ?? 0} paused / active
              </p>
            </Card>

            <Card>
              <div className="flex items-center justify-between text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">
                <span>Average Score</span>
                <BarChart3 className="w-4 h-4 text-brand-500" />
              </div>
              <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-2">
                {analytics?.average_score != null ? `${analytics.average_score}%` : '—'}
              </div>
              <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                Across all completed categories
              </p>
            </Card>

            <Card>
              <div className="flex items-center justify-between text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">
                <span>Peak Score</span>
                <Award className="w-4 h-4 text-amber-500" />
              </div>
              <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-2">
                {analytics?.best_score != null ? `${analytics.best_score}%` : '—'}
              </div>
              <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                Advisory rubric assessment
              </p>
            </Card>

            <Card>
              <div className="flex items-center justify-between text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">
                <span>Latest Trend</span>
                <TrendingUp className="w-4 h-4 text-indigo-500" />
              </div>
              <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-2">
                {analytics?.improvement_delta != null
                  ? `${analytics.improvement_delta >= 0 ? '+' : ''}${analytics.improvement_delta} pts`
                  : analytics?.latest_score != null
                  ? `${analytics.latest_score}%`
                  : '—'}
              </div>
              <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                Delta vs. previous attempt
              </p>
            </Card>
          </div>

          {/* Start New Interview + Performance Trend */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Builder Form */}
            <div className="lg:col-span-2">
              <Card>
                <CardHeader
                  title="Start New Mock Interview"
                  subtitle="Configure category, difficulty, length, and optional target job posting"
                  action={
                    <Badge variant="brand" size="sm">
                      <Mic className="w-3 h-3 mr-1" /> Text + Optional Voice
                    </Badge>
                  }
                />
                <form onSubmit={handleCreateInterview} className="space-y-5">
                  {/* Categories */}
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2">
                      1. Interview Category
                    </label>
                    <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-5 gap-2.5">
                      {CATEGORY_OPTIONS.map((opt) => {
                        const Icon = opt.icon;
                        const active = category === opt.id;
                        return (
                          <button
                            key={opt.id}
                            type="button"
                            onClick={() => setCategory(opt.id)}
                            className={`p-3 rounded-xl border text-left transition-all ${
                              active
                                ? 'border-brand-600 bg-brand-50/70 dark:bg-brand-950/50 shadow-xs'
                                : 'border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 bg-white dark:bg-slate-900'
                            }`}
                          >
                            <Icon
                              className={`w-4 h-4 mb-1.5 ${
                                active ? 'text-brand-600 dark:text-brand-400' : 'text-slate-500 dark:text-slate-400'
                              }`}
                            />
                            <div className="text-xs font-bold text-slate-900 dark:text-slate-100">{opt.label}</div>
                            <div className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5 leading-snug">
                              {opt.desc}
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* 2. Assessment Style / Mode Selector */}
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2">
                      2. Assessment Style &amp; Format
                    </label>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <button
                        type="button"
                        onClick={() => handleFormatChange('conversational')}
                        className={`p-3 rounded-xl border text-left transition-all ${
                          questionFormat === 'conversational'
                            ? 'border-brand-600 bg-brand-50/70 dark:bg-brand-950/50 shadow-xs'
                            : 'border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 bg-white dark:bg-slate-900'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <Mic className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                          <span className="text-xs font-bold text-slate-900 dark:text-slate-100">
                            Conversational AI Interview
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                          Interactive round with voice/text dictation, STAR evaluation &amp; adaptive follow-ups
                        </p>
                      </button>

                      <button
                        type="button"
                        onClick={() => handleFormatChange('mcq')}
                        className={`p-3 rounded-xl border text-left transition-all ${
                          questionFormat === 'mcq'
                            ? 'border-brand-600 bg-brand-50/70 dark:bg-brand-950/50 shadow-xs ring-1 ring-brand-500'
                            : 'border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 bg-white dark:bg-slate-900'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                          <span className="text-xs font-bold text-slate-900 dark:text-slate-100">
                            Timed MCQ Screening Test (30 / 50 Ques)
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                          Standard placement exam format: objective multiple-choice, timed accuracy &amp; instant scoring
                        </p>
                      </button>
                    </div>
                  </div>

                  {/* 3. Core Subject Focus (Specifically for 40 CSE Subjects & Engineering Core) */}
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <label htmlFor="mock-subject-focus" className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                        3. Core Technical Subject / Focus Topic ({CSE_40_CORE_SUBJECTS.length} Official CSE Subjects Available)
                      </label>
                      {subjectFocus && (
                        <button
                          type="button"
                          onClick={() => setSubjectFocus('')}
                          className="text-[11px] text-brand-600 dark:text-brand-400 hover:underline"
                        >
                          Clear Selection
                        </button>
                      )}
                    </div>
                    <select
                      id="mock-subject-focus"
                      value={subjectFocus}
                      onChange={(e) => setSubjectFocus(e.target.value)}
                      className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-brand-500 font-medium"
                    >
                      <option value="">Comprehensive / All Core Subjects Practice</option>
                      <optgroup label="CSE Core Curriculum (40 Subjects)">
                        {CSE_40_CORE_SUBJECTS.map((subj) => (
                          <option key={subj} value={subj}>
                            {subj}
                          </option>
                        ))}
                      </optgroup>
                    </select>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                      Select any of the 40 official Computer Science &amp; Engineering subjects to focus your interview questions specifically on that discipline.
                    </p>
                  </div>

                  {/* Target Job & Role */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="mock-job-select" className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                        4. Target Job Posting (Optional)
                      </label>
                      <select
                        id="mock-job-select"
                        value={selectedJobId}
                        onChange={(e) => setSelectedJobId(e.target.value ? Number(e.target.value) : '')}
                        className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-brand-500"
                      >
                        <option value="">General Campus Placement Practice</option>
                        {targetJobs.map((j) => (
                          <option key={j.id} value={j.id}>
                            {j.title} — {j.company_name}
                            {j.compatibility_score != null ? ` (${j.compatibility_score.toFixed(0)}% match)` : ''}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label htmlFor="mock-target-role" className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                        Target Role Focus (Optional)
                      </label>
                      <input
                        id="mock-target-role"
                        type="text"
                        value={targetRole}
                        onChange={(e) => setTargetRole(e.target.value)}
                        placeholder="e.g., Structural Engineer, Process Trainee, Site Engineer, Software Dev"
                        maxLength={200}
                        className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-xs text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
                      />
                    </div>
                  </div>

                  {/* Difficulty, Length, Time Limit */}
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                        5. Difficulty Level
                      </label>
                      <div className="grid grid-cols-3 gap-1.5">
                        {(['beginner', 'intermediate', 'advanced'] as MockInterviewDifficulty[]).map((lvl) => (
                          <button
                            key={lvl}
                            type="button"
                            onClick={() => setDifficulty(lvl)}
                            className={`py-2 px-2 rounded-lg text-xs font-semibold capitalize border transition-colors ${
                              difficulty === lvl
                                ? 'bg-slate-900 dark:bg-brand-600 text-white border-slate-900 dark:border-brand-600'
                                : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800'
                            }`}
                          >
                            {lvl}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div>
                      <label htmlFor="mock-length-select" className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                        {questionFormat === 'mcq' ? 'MCQ Test Length' : 'Interview Length'}
                      </label>
                      {questionFormat === 'mcq' ? (
                        <select
                          id="mock-length-select"
                          value={questionCount}
                          onChange={(e) => handleQuestionCountChange(Number(e.target.value))}
                          className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-xs text-slate-900 dark:text-slate-100"
                        >
                          <option value={30}>Full Screening Exam (30 Questions)</option>
                          <option value={50}>Mega Campus Assessment (50 Questions)</option>
                          <option value={15}>Speed Drill (15 Questions)</option>
                        </select>
                      ) : (
                        <select
                          id="mock-length-select"
                          value={questionCount}
                          onChange={(e) => handleQuestionCountChange(Number(e.target.value))}
                          className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-xs text-slate-900 dark:text-slate-100"
                        >
                          <option value={3}>Quick Drill (3 Questions)</option>
                          <option value={5}>Standard Round (5 Questions)</option>
                          <option value={7}>Deep Assessment (7 Questions)</option>
                          <option value={10}>Full Panel Simulation (10 Questions)</option>
                        </select>
                      )}
                    </div>

                    <div>
                      <label htmlFor="mock-timer-select" className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                        Timer Target
                      </label>
                      <select
                        id="mock-timer-select"
                        value={timeLimitMinutes}
                        onChange={(e) => setTimeLimitMinutes(Number(e.target.value))}
                        className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-xs text-slate-900 dark:text-slate-100"
                      >
                        <option value={20}>20 Minutes</option>
                        <option value={30}>30 Minutes</option>
                        <option value={45}>45 Minutes (Recommended for 30 Ques)</option>
                        <option value={60}>60 Minutes (Recommended for 50 Ques)</option>
                        <option value={90}>90 Minutes</option>
                        <option value={0}>Untimed Stopwatch</option>
                      </select>
                    </div>
                  </div>

                  {/* Adaptive Follow-ups & Submit */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2 border-t border-slate-100 dark:border-slate-800">
                    <label className="inline-flex items-center gap-2 text-xs text-slate-700 dark:text-slate-300 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={includeFollowups}
                        onChange={(e) => setIncludeFollowups(e.target.checked)}
                        className="w-4 h-4 rounded border-slate-300 dark:border-slate-700 text-brand-600 focus:ring-brand-500"
                      />
                      <span>Enable adaptive AI follow-up questions based on my answers</span>
                    </label>

                    <Button
                      type="submit"
                      variant="primary"
                      size="md"
                      isLoading={creating}
                      icon={<Sparkles className="w-4 h-4" />}
                    >
                      {creating ? 'Generating Questions...' : 'Start Mock Interview'}
                    </Button>
                  </div>
                </form>
              </Card>
            </div>

            {/* Areas Requiring Improvement & Topics */}
            <div className="space-y-4">
              <Card>
                <CardHeader
                  title="Areas Requiring Improvement"
                  subtitle="Computed across completed mock assessments"
                />
                {analytics && analytics.areas_requiring_improvement.length > 0 ? (
                  <ul className="space-y-2 text-xs text-slate-700 dark:text-slate-300">
                    {analytics.areas_requiring_improvement.map((area, i) => (
                      <li
                        key={i}
                        className="p-2.5 rounded-lg bg-amber-50/70 dark:bg-amber-950/30 border border-amber-200/70 dark:border-amber-900/60 flex items-start gap-2"
                      >
                        <Sliders className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
                        <span>{area}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-slate-500 dark:text-slate-400 py-4">
                    Complete at least one mock interview to unlock targeted rubric diagnostics.
                  </p>
                )}
              </Card>

              <Card>
                <CardHeader title="Priority Study Topics" />
                {analytics && analytics.top_recommended_topics.length > 0 ? (
                  <div className="flex flex-wrap gap-1.5">
                    {analytics.top_recommended_topics.map((topic, idx) => (
                      <Badge key={idx} variant="brand" size="sm">
                        <BookOpen className="w-3 h-3 mr-1" />
                        {topic}
                      </Badge>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Recommended revision topics appear here after evaluation.
                  </p>
                )}
              </Card>
            </div>
          </div>

          {/* Analytics Trend Chart */}
          {analytics && analytics.score_trend.length > 0 && (
            <Card>
              <CardHeader
                title="Performance Improvement Trend"
                subtitle="Chronological score progression across completed practice interviews"
              />
              <div className="h-64 w-full pt-2">
                <ResponsiveContainer width="100%" height={240}>
                  <AreaChart data={analytics.score_trend} margin={{ top: 10, right: 16, left: -16, bottom: 0 }}>
                    <defs>
                      <linearGradient id="mockScoreGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#4F46E5" stopOpacity={0.35} />
                        <stop offset="95%" stopColor="#4F46E5" stopOpacity={0.0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={isDark ? '#334155' : '#E2E8F0'} />
                    <XAxis
                      dataKey="attempt_number"
                      tickFormatter={(v) => `#${v}`}
                      stroke={isDark ? '#94A3B8' : '#64748B'}
                      fontSize={12}
                    />
                    <YAxis domain={[0, 100]} unit="%" stroke={isDark ? '#94A3B8' : '#64748B'} fontSize={12} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: isDark ? '#0F172A' : '#FFFFFF',
                        borderRadius: '8px',
                        border: isDark ? '1px solid #334155' : '1px solid #E2E8F0',
                        color: isDark ? '#F1F5F9' : '#0F172A',
                        fontSize: '12px',
                      }}
                      formatter={(val: any) => [`${val}%`, 'Score']}
                      labelFormatter={(attempt) => {
                        const pt = analytics.score_trend.find((p) => p.attempt_number === attempt);
                        return pt ? `Attempt #${attempt} · ${pt.target_label} (${pt.category})` : `Attempt #${attempt}`;
                      }}
                    />
                    <Area
                      type="monotone"
                      dataKey="overall_score"
                      stroke="#6366F1"
                      strokeWidth={2.5}
                      fillOpacity={1}
                      fill="url(#mockScoreGrad)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </Card>
          )}

          {/* Interview History Table */}
          <Card>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 mb-4 border-b border-slate-100 dark:border-slate-800">
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                  <History className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                  <span>Interview History &amp; Saved Attempts</span>
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  Review past answers and rubric feedback, or resume paused sessions
                </p>
              </div>

              <div className="flex flex-wrap gap-1.5 text-xs">
                {(['all', 'technical', 'project_based', 'behavioral', 'hr', 'aptitude'] as const).map((cat) => (
                  <button
                    key={cat}
                    type="button"
                    onClick={() => setHistoryFilter(cat)}
                    className={`px-2.5 py-1 rounded-lg font-medium border capitalize transition-colors ${
                      historyFilter === cat
                        ? 'bg-slate-900 dark:bg-brand-600 text-white border-slate-900 dark:border-brand-600'
                        : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800'
                    }`}
                  >
                    {cat.replace('_', ' ')}
                  </button>
                ))}
              </div>
            </div>

            {filteredHistory.length === 0 ? (
              <div className="py-10 text-center text-xs text-slate-500 dark:text-slate-400">
                {loading ? 'Loading saved interview history...' : 'No mock interviews recorded yet. Start your first session above!'}
              </div>
            ) : (
              <div className="space-y-2.5">
                {filteredHistory.map((s) => (
                  <div
                    key={s.id}
                    className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                  >
                    <div className="space-y-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant="brand" size="sm" className="capitalize">
                          {s.category.replace('_', ' ')}
                        </Badge>
                        <Badge variant="neutral" size="sm" className="capitalize">
                          {s.difficulty}
                        </Badge>
                        <Badge
                          variant={
                            s.status === 'completed'
                              ? 'success'
                              : s.status === 'paused'
                              ? 'warning'
                              : s.status === 'abandoned'
                              ? 'danger'
                              : 'info'
                          }
                          size="sm"
                          className="capitalize"
                        >
                          {s.status.replace('_', ' ')}
                        </Badge>
                        <span className="text-xs font-bold text-slate-900 dark:text-slate-100 truncate">
                          {s.job_title
                            ? `${s.job_title}${s.company_name ? ` (${s.company_name})` : ''}`
                            : s.target_role || 'Campus Placement Practice'}
                        </span>
                      </div>
                      <div className="flex flex-wrap items-center gap-3 text-[11px] text-slate-500 dark:text-slate-400">
                        <span>
                          Answered: {s.answered_count} / {s.total_questions_generated}
                        </span>
                        <span className="inline-flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {Math.floor(s.elapsed_seconds / 60)}m {s.elapsed_seconds % 60}s
                        </span>
                        <span>{new Date(s.started_at).toLocaleDateString()}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 shrink-0">
                      {s.overall_score != null && (
                        <div className="text-right">
                          <div className="text-sm font-black text-slate-900 dark:text-slate-100">
                            {s.overall_score.toFixed(1)}%
                          </div>
                          {s.score_delta_from_previous != null && (
                            <div
                              className={`text-[10px] font-semibold ${
                                s.score_delta_from_previous >= 0
                                  ? 'text-emerald-600 dark:text-emerald-400'
                                  : 'text-rose-600 dark:text-rose-400'
                              }`}
                            >
                              {s.score_delta_from_previous >= 0 ? '+' : ''}
                              {s.score_delta_from_previous.toFixed(1)} vs prev
                            </div>
                          )}
                        </div>
                      )}

                      {s.status === 'in_progress' || s.status === 'paused' ? (
                        <Button
                          size="sm"
                          variant="primary"
                          icon={<Play className="w-3.5 h-3.5" />}
                          onClick={() => handleOpenSession(s.id, s.status === 'paused')}
                        >
                          {s.status === 'paused' ? 'Resume' : 'Continue'}
                        </Button>
                      ) : (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleOpenSession(s.id)}
                        >
                          Review Feedback
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      )}
    </DashboardLayout>
  );
};
