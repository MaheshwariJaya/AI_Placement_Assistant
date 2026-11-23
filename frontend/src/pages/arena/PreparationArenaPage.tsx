import React, { useEffect, useState } from 'react';
import { DashboardLayout } from '../../components/layout/DashboardLayout';
import { Card, CardHeader } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { arenaApi } from '../../services/api';
import { useTheme } from '../../context/ThemeContext';
import {
  ArenaAssessmentSummary,
  ArenaAttemptDetail,
  ArenaCategory,
  ArenaCategorySummary,
  ArenaCodeLanguage,
  ArenaDifficulty,
  ArenaLeaderboardResponse,
  ArenaPerformanceAnalytics,
  ArenaPersonalizedPracticeResponse,
  ArenaUserPreference,
  SandboxRunResponse,
} from '../../types';
import {
  Award,
  BarChart3,
  BookOpen,
  Building2,
  CheckCircle2,
  Clock,
  Code2,
  Compass,
  Eye,
  EyeOff,
  Lock,
  Play,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Terminal,
  Trophy,
  XCircle,
} from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

type ArenaTab = 'categories' | 'assessments' | 'personalized' | 'analytics' | 'leaderboard';

export const PreparationArenaPage: React.FC = () => {
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === 'dark';

  const [activeTab, setActiveTab] = useState<ArenaTab>('categories');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [categories, setCategories] = useState<ArenaCategorySummary[]>([]);
  const [assessments, setAssessments] = useState<ArenaAssessmentSummary[]>([]);
  const [analytics, setAnalytics] = useState<ArenaPerformanceAnalytics | null>(null);
  const [personalized, setPersonalized] = useState<ArenaPersonalizedPracticeResponse | null>(null);
  const [preferences, setPreferences] = useState<ArenaUserPreference | null>(null);
  const [leaderboard, setLeaderboard] = useState<ArenaLeaderboardResponse | null>(null);
  const [leaderboardScope, setLeaderboardScope] = useState<'department' | 'batch' | 'institution'>('department');

  // Practice launcher controls
  const [selectedDifficulty, setSelectedDifficulty] = useState<ArenaDifficulty | ''>('');

  // Active Attempt Runner State
  const [activeAttempt, setActiveAttempt] = useState<ArenaAttemptDetail | null>(null);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [mcqChoice, setMcqChoice] = useState<string>('');
  const [codeLang, setCodeLang] = useState<ArenaCodeLanguage>('python');
  const [codeText, setCodeText] = useState<string>('');
  const [customStdin, setCustomStdin] = useState<string>('');
  const [behavioralText, setBehavioralText] = useState<string>('');
  const [sandboxRunResult, setSandboxRunResult] = useState<SandboxRunResponse | null>(null);
  const [isRunningCode, setIsRunningCode] = useState(false);
  const [isSubmittingAnswer, setIsSubmittingAnswer] = useState(false);
  const [isSubmittingAttempt, setIsSubmittingAttempt] = useState(false);
  const [questionStartMs, setQuestionStartMs] = useState<number>(Date.now());
  const [remainingSeconds, setRemainingSeconds] = useState<number | null>(null);
  const [answerFeedbackBanner, setAnswerFeedbackBanner] = useState<string | null>(null);

  const loadArenaOverview = async () => {
    setLoading(true);
    setError(null);
    try {
      const [cats, assess, ana, recs, prefs] = await Promise.all([
        arenaApi.getCategories(),
        arenaApi.listAssessments(),
        arenaApi.getAnalytics(),
        arenaApi.getRecommendations(),
        arenaApi.getPreferences(),
      ]);
      setCategories(cats);
      setAssessments(assess);
      setAnalytics(ana);
      setPersonalized(recs);
      setPreferences(prefs);
      setCodeLang(prefs.preferred_language || 'python');
    } catch (err: any) {
      setError(err?.response?.data?.detail?.message || err?.response?.data?.detail || 'Failed to load Preparation Arena.');
    } finally {
      setLoading(false);
    }
  };

  const loadLeaderboard = async (scope: 'department' | 'batch' | 'institution') => {
    try {
      const lb = await arenaApi.getLeaderboard(scope);
      setLeaderboard(lb);
    } catch (err) {
      console.warn('Leaderboard fetch failed:', err);
    }
  };

  useEffect(() => {
    loadArenaOverview();
  }, []);

  useEffect(() => {
    if (activeTab === 'leaderboard') {
      loadLeaderboard(leaderboardScope);
    }
  }, [activeTab, leaderboardScope]);

  // Countdown timer for active timed attempts
  useEffect(() => {
    if (!activeAttempt || activeAttempt.status !== 'in_progress' || !activeAttempt.expires_at) {
      setRemainingSeconds(null);
      return;
    }
    const tick = () => {
      const secs = Math.max(0, Math.floor((new Date(activeAttempt.expires_at!).getTime() - Date.now()) / 1000));
      setRemainingSeconds(secs);
    };
    tick();
    const timer = window.setInterval(tick, 1000);
    return () => window.clearInterval(timer);
  }, [activeAttempt]);

  const syncQuestionEditors = (attempt: ArenaAttemptDetail, idx: number, preferredLang: ArenaCodeLanguage) => {
    const slot = attempt.questions[idx];
    if (!slot) return;
    setQuestionStartMs(Date.now());
    setSandboxRunResult(slot.answer?.execution_result || null);
    setAnswerFeedbackBanner(null);

    const existing = slot.answer;
    setMcqChoice(existing?.selected_option_key || '');
    setBehavioralText(existing?.behavioral_response || '');

    const lang = (existing?.code_language as ArenaCodeLanguage) || preferredLang;
    setCodeLang(lang);
    setCodeText(
      existing?.submitted_code ||
        slot.question.starter_code?.[lang] ||
        slot.question.starter_code?.python ||
        ''
    );
  };

  const handleStartTopicPractice = async (cat: ArenaCategory, timed = false) => {
    setError(null);
    try {
      const attempt = await arenaApi.startAttempt({
        mode: timed ? 'timed_test' : 'topic_practice',
        category: cat,
        difficulty: selectedDifficulty || undefined,
        question_count: 5,
        time_limit_minutes: timed ? 10 : undefined,
      });
      setActiveAttempt(attempt);
      setCurrentIdx(0);
      syncQuestionEditors(attempt, 0, preferences?.preferred_language || 'python');
    } catch (err: any) {
      setError(err?.response?.data?.detail?.message || 'Unable to start practice session.');
    }
  };

  const handleStartAssessment = async (assessmentId: number) => {
    setError(null);
    try {
      const attempt = await arenaApi.startAttempt({ assessment_id: assessmentId });
      setActiveAttempt(attempt);
      setCurrentIdx(0);
      syncQuestionEditors(attempt, 0, preferences?.preferred_language || 'python');
    } catch (err: any) {
      setError(err?.response?.data?.detail?.message || 'Unable to start assessment.');
    }
  };

  const handleOpenAttempt = async (attemptId: number) => {
    setError(null);
    try {
      const detail = await arenaApi.getAttemptDetail(attemptId);
      setActiveAttempt(detail);
      setCurrentIdx(0);
      syncQuestionEditors(detail, 0, preferences?.preferred_language || 'python');
    } catch (err: any) {
      setError(err?.response?.data?.detail?.message || 'Unable to open attempt details.');
    }
  };

  const handleLanguageChange = (newLang: ArenaCodeLanguage) => {
    setCodeLang(newLang);
    if (!activeAttempt) return;
    const slot = activeAttempt.questions[currentIdx];
    if (slot && !slot.answer?.submitted_code) {
      setCodeText(slot.question.starter_code?.[newLang] || '');
    }
  };

  const handleRunSampleCode = async () => {
    if (!activeAttempt) return;
    const slot = activeAttempt.questions[currentIdx];
    if (!slot) return;
    setIsRunningCode(true);
    setSandboxRunResult(null);
    try {
      const res = await arenaApi.runCode(activeAttempt.id, {
        question_id: slot.question.id,
        language: codeLang,
        source_code: codeText,
        custom_stdin: customStdin.trim() ? customStdin : undefined,
      });
      setSandboxRunResult(res);
    } catch (err: any) {
      setError(err?.response?.data?.detail?.message || 'Code sandbox execution failed.');
    } finally {
      setIsRunningCode(false);
    }
  };

  const handleSubmitAnswer = async () => {
    if (!activeAttempt) return;
    const slot = activeAttempt.questions[currentIdx];
    if (!slot) return;

    const spent = Math.max(1, Math.round((Date.now() - questionStartMs) / 1000));
    setIsSubmittingAnswer(true);
    setError(null);
    try {
      const payload: any = {
        question_id: slot.question.id,
        time_spent_seconds: spent,
      };
      if (slot.question.question_type === 'mcq') {
        payload.selected_option_key = mcqChoice;
      } else if (slot.question.question_type === 'coding') {
        payload.submitted_code = codeText;
        payload.code_language = codeLang;
      } else {
        payload.behavioral_response = behavioralText;
      }

      const res = await arenaApi.submitAnswer(activeAttempt.id, payload);
      const updated = await arenaApi.getAttemptDetail(activeAttempt.id);
      setActiveAttempt(updated);
      if (res.answer.execution_result) {
        setSandboxRunResult(res.answer.execution_result);
      }
      setAnswerFeedbackBanner(
        res.immediate_review_unlocked
          ? res.answer.is_correct
            ? 'Correct! Explanation unlocked below.'
            : 'Submitted — review explanation and solution below.'
          : 'Answer saved. Full explanations unlock upon final test submission.'
      );
    } catch (err: any) {
      setError(err?.response?.data?.detail?.message || 'Failed to save answer.');
    } finally {
      setIsSubmittingAnswer(false);
    }
  };

  const handleSubmitFinalAttempt = async () => {
    if (!activeAttempt) return;
    setIsSubmittingAttempt(true);
    try {
      const finalized = await arenaApi.submitAttempt(activeAttempt.id);
      setActiveAttempt(finalized);
      await loadArenaOverview();
    } catch (err: any) {
      setError(err?.response?.data?.detail?.message || 'Failed to finalize attempt.');
    } finally {
      setIsSubmittingAttempt(false);
    }
  };

  const handleUpdatePrivacy = async (patch: Partial<ArenaUserPreference>) => {
    try {
      const updated = await arenaApi.updatePreferences(patch);
      setPreferences(updated);
      if (activeTab === 'leaderboard') {
        loadLeaderboard(leaderboardScope);
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail?.message || 'Could not update privacy settings.');
    }
  };

  const formatTimer = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  };

  // Active Attempt Runner / Review View
  if (activeAttempt) {
    const slot = activeAttempt.questions[currentIdx];
    const isFinalized = activeAttempt.status !== 'in_progress';

    return (
      <DashboardLayout
        role="student"
        title={activeAttempt.title}
        subtitle={activeAttempt.provenance_notice}
      >
        <div className="space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4">
            <div className="flex flex-wrap items-center gap-3">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setActiveAttempt(null);
                  loadArenaOverview();
                }}
              >
                Back to Arena Hub
              </Button>
              <Badge variant={isFinalized ? 'success' : 'brand'}>
                {activeAttempt.status.replace('_', ' ').toUpperCase()}
              </Badge>
              <span className="text-sm text-slate-600 dark:text-slate-300 font-medium">
                {activeAttempt.attempted_count}/{activeAttempt.total_questions} Answered
              </span>
              {isFinalized && (
                <Badge variant="info">
                  Score: {activeAttempt.score_pct}% • Accuracy: {activeAttempt.accuracy_pct}%
                </Badge>
              )}
            </div>

            <div className="flex items-center gap-3">
              {remainingSeconds !== null && activeAttempt.status === 'in_progress' && (
                <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800 font-mono text-sm font-semibold">
                  <Clock className="w-4 h-4" />
                  {formatTimer(remainingSeconds)}
                </div>
              )}
              {activeAttempt.status === 'in_progress' && (
                <Button
                  variant="primary"
                  size="sm"
                  isLoading={isSubmittingAttempt}
                  onClick={handleSubmitFinalAttempt}
                >
                  Finish & Unlock Review
                </Button>
              )}
            </div>
          </div>

          {/* Question Navigator */}
          <div className="flex flex-wrap gap-2">
            {activeAttempt.questions.map((qSlot, i) => (
              <button
                key={qSlot.question.id}
                onClick={() => {
                  setCurrentIdx(i);
                  syncQuestionEditors(activeAttempt, i, preferences?.preferred_language || 'python');
                }}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition ${
                  i === currentIdx
                    ? 'bg-indigo-600 text-white border-indigo-600'
                    : qSlot.answered
                    ? qSlot.answer?.is_correct
                      ? 'bg-emerald-50 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800'
                      : 'bg-amber-50 dark:bg-amber-950/30 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-800'
                    : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700'
                }`}
              >
                Q{qSlot.question_order} ({qSlot.question.question_type.toUpperCase()})
              </button>
            ))}
          </div>

          {error && (
            <div className="p-3 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 text-sm">
              {error}
            </div>
          )}

          {answerFeedbackBanner && (
            <div className="p-3 rounded-lg bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-800 text-indigo-700 dark:text-indigo-300 text-sm">
              {answerFeedbackBanner}
            </div>
          )}

          {slot && (
            <Card>
              <div className="space-y-5">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      <Badge variant="neutral">{slot.question.category.replace('_', ' ')}</Badge>
                      <Badge
                        variant={
                          slot.question.difficulty === 'easy'
                            ? 'success'
                            : slot.question.difficulty === 'medium'
                            ? 'warning'
                            : 'danger'
                        }
                      >
                        {slot.question.difficulty.toUpperCase()}
                      </Badge>
                      {slot.question.company_tag && (
                        <Badge variant="info">{slot.question.company_tag} (Original Pattern)</Badge>
                      )}
                    </div>
                    <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                      Q{slot.question_order}. {slot.question.title}
                    </h3>
                  </div>
                  <span className="text-xs text-slate-500 dark:text-slate-400">
                    Max Marks: {slot.question.max_marks} • Target Time: {slot.question.expected_time_seconds}s
                  </span>
                </div>

                <p className="text-sm whitespace-pre-wrap text-slate-700 dark:text-slate-200 leading-relaxed bg-slate-50 dark:bg-slate-800/60 p-4 rounded-xl border border-slate-200 dark:border-slate-700">
                  {slot.question.prompt_text}
                </p>

                {/* MCQ Input */}
                {slot.question.question_type === 'mcq' && (
                  <div className="space-y-2.5">
                    {slot.question.options.map((opt) => {
                      const chosen = mcqChoice === opt.key;
                      const isCorrectKey = slot.question.correct_option_key === opt.key;
                      const reviewUnlocked = Boolean(slot.question.explanation_text);
                      return (
                        <label
                          key={opt.key}
                          className={`flex items-start gap-3 p-3.5 rounded-xl border cursor-pointer transition ${
                            reviewUnlocked && isCorrectKey
                              ? 'border-emerald-500 bg-emerald-50/70 dark:bg-emerald-950/30'
                              : chosen
                              ? 'border-indigo-500 bg-indigo-50/70 dark:bg-indigo-950/30'
                              : 'border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800/50'
                          }`}
                        >
                          <input
                            type="radio"
                            name={`mcq-${slot.question.id}`}
                            value={opt.key}
                            checked={chosen}
                            disabled={isFinalized}
                            onChange={() => setMcqChoice(opt.key)}
                            className="mt-1"
                          />
                          <div className="text-sm text-slate-800 dark:text-slate-100">
                            <span className="font-bold mr-2">{opt.key}.</span>
                            {opt.text}
                          </div>
                        </label>
                      );
                    })}
                  </div>
                )}

                {/* Coding Input + Isolated Sandbox Runner */}
                {slot.question.question_type === 'coding' && (
                  <div className="space-y-4">
                    {slot.question.sample_test_cases.length > 0 && (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {slot.question.sample_test_cases.map((tc, idx) => (
                          <div
                            key={idx}
                            className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/70 border border-slate-200 dark:border-slate-700 text-xs font-mono"
                          >
                            <div className="font-semibold text-slate-600 dark:text-slate-300 mb-1">
                              Sample Case #{idx + 1}
                            </div>
                            <div className="text-slate-700 dark:text-slate-200">
                              <span className="text-slate-400">stdin:</span> {tc.stdin.trim()}
                            </div>
                            <div className="text-emerald-700 dark:text-emerald-300 mt-0.5">
                              <span className="text-slate-400">expected:</span> {tc.expected_stdout}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <Terminal className="w-4 h-4 text-indigo-500" />
                        <span className="text-xs font-semibold text-slate-700 dark:text-slate-200">
                          Isolated Sandbox Runtime (CPU/Memory/Network Restricted)
                        </span>
                      </div>
                      <select
                        value={codeLang}
                        disabled={isFinalized}
                        onChange={(e) => handleLanguageChange(e.target.value as ArenaCodeLanguage)}
                        className="px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-800 dark:text-slate-100"
                      >
                        <option value="python">Python 3</option>
                        <option value="javascript">JavaScript (Node.js)</option>
                        <option value="java">Java 21</option>
                      </select>
                    </div>

                    <textarea
                      value={codeText}
                      disabled={isFinalized}
                      onChange={(e) => setCodeText(e.target.value)}
                      rows={12}
                      spellCheck={false}
                      className="w-full font-mono text-xs p-4 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-950 text-slate-100 focus:ring-2 focus:ring-indigo-500"
                    />

                    <div className="flex flex-col sm:flex-row gap-3">
                      <input
                        type="text"
                        value={customStdin}
                        disabled={isFinalized}
                        onChange={(e) => setCustomStdin(e.target.value)}
                        placeholder="Optional custom stdin for quick sandbox test..."
                        className="flex-1 px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs font-mono text-slate-800 dark:text-slate-100"
                      />
                      {!isFinalized && (
                        <Button
                          variant="secondary"
                          size="sm"
                          isLoading={isRunningCode}
                          onClick={handleRunSampleCode}
                        >
                          <Play className="w-3.5 h-3.5 mr-1.5" />
                          Run Sample Tests
                        </Button>
                      )}
                    </div>

                    {sandboxRunResult && (
                      <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 space-y-2">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <span className="text-xs font-semibold text-slate-700 dark:text-slate-200">
                            Sandbox Result ({sandboxRunResult.sandbox_provider}) — Passed{' '}
                            {sandboxRunResult.passed_count}/{sandboxRunResult.total_count} cases ({sandboxRunResult.runtime_ms}ms)
                          </span>
                          <Badge variant={sandboxRunResult.all_passed ? 'success' : 'danger'}>
                            {sandboxRunResult.security_violation
                              ? 'SECURITY BLOCKED'
                              : sandboxRunResult.compile_error
                              ? 'COMPILE ERROR'
                              : sandboxRunResult.all_passed
                              ? 'ALL PASSED'
                              : 'CHECK CASES'}
                          </Badge>
                        </div>
                        {sandboxRunResult.security_violation && (
                          <div className="text-xs text-rose-600 dark:text-rose-400 font-mono">
                            {sandboxRunResult.security_violation}
                          </div>
                        )}
                        {sandboxRunResult.compile_error && (
                          <pre className="text-xs text-rose-600 dark:text-rose-400 whitespace-pre-wrap">
                            {sandboxRunResult.compile_error}
                          </pre>
                        )}
                        {sandboxRunResult.custom_stdout !== null && sandboxRunResult.custom_stdout !== undefined && (
                          <div className="text-xs font-mono bg-slate-900 text-emerald-300 p-2 rounded">
                            Custom stdout: {sandboxRunResult.custom_stdout || '(empty)'}
                          </div>
                        )}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                          {sandboxRunResult.test_results.map((tr) => (
                            <div
                              key={tr.test_index}
                              className="p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs"
                            >
                              <div className="flex items-center justify-between font-semibold mb-1">
                                <span>
                                  Test #{tr.test_index} {tr.is_sample ? '(Sample)' : '(Hidden)'}
                                </span>
                                <span className={tr.passed ? 'text-emerald-600' : 'text-rose-600'}>
                                  {tr.status.toUpperCase()}
                                </span>
                              </div>
                              {tr.actual_stdout && (
                                <div className="font-mono text-slate-600 dark:text-slate-300 truncate">
                                  out: {tr.actual_stdout}
                                </div>
                              )}
                              {tr.stderr && (
                                <div className="font-mono text-rose-500 truncate">err: {tr.stderr}</div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Behavioral Input */}
                {slot.question.question_type === 'behavioral' && (
                  <div className="space-y-3">
                    <textarea
                      value={behavioralText}
                      disabled={isFinalized}
                      onChange={(e) => setBehavioralText(e.target.value)}
                      rows={6}
                      placeholder="Write your STAR response (Situation, Task, Action, measurable Result)..."
                      className="w-full p-3.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-800 dark:text-slate-100"
                    />
                    {slot.answer?.ai_feedback && (
                      <div className="p-3.5 rounded-xl bg-indigo-50/70 dark:bg-indigo-950/30 border border-indigo-200 dark:border-indigo-800 text-xs space-y-1">
                        <div className="font-semibold text-indigo-700 dark:text-indigo-300">
                          Behavioral Evaluation ({slot.answer.ai_feedback.score_out_of_100}/100):{' '}
                          {slot.answer.ai_feedback.summary}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {!isFinalized && (
                  <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-200 dark:border-slate-800">
                    <Button
                      variant="primary"
                      isLoading={isSubmittingAnswer}
                      disabled={
                        (slot.question.question_type === 'mcq' && !mcqChoice) ||
                        (slot.question.question_type === 'coding' && !codeText.trim()) ||
                        (slot.question.question_type === 'behavioral' && behavioralText.trim().length < 5)
                      }
                      onClick={handleSubmitAnswer}
                    >
                      Save & Evaluate Answer
                    </Button>

                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={currentIdx === 0}
                        onClick={() => {
                          const next = currentIdx - 1;
                          setCurrentIdx(next);
                          syncQuestionEditors(activeAttempt, next, preferences?.preferred_language || 'python');
                        }}
                      >
                        Previous
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={currentIdx >= activeAttempt.questions.length - 1}
                        onClick={() => {
                          const next = currentIdx + 1;
                          setCurrentIdx(next);
                          syncQuestionEditors(activeAttempt, next, preferences?.preferred_language || 'python');
                        }}
                      >
                        Next
                      </Button>
                    </div>
                  </div>
                )}

                {/* Post-Submission Explanation & Solution Review */}
                {slot.question.explanation_text && (
                  <div className="p-4 rounded-xl bg-emerald-50/60 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-800 space-y-2">
                    <div className="flex items-center gap-2 text-sm font-bold text-emerald-800 dark:text-emerald-300">
                      <CheckCircle2 className="w-4 h-4" />
                      Explanation & Answer Review
                      {slot.question.correct_option_key && (
                        <Badge variant="success">Correct Option: {slot.question.correct_option_key}</Badge>
                      )}
                    </div>
                    <p className="text-sm text-slate-700 dark:text-slate-200">{slot.question.explanation_text}</p>
                    {slot.question.sample_solution_text && (
                      <div className="text-xs text-slate-600 dark:text-slate-300 pt-1">
                        <span className="font-semibold">Reference Approach: </span>
                        {slot.question.sample_solution_text}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </Card>
          )}
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout
      role="student"
      title="Placement Preparation Arena"
      subtitle="Master core placement preparation tailored to your academic branch, with aptitude drills, branch-specific technical challenges, and real-time performance diagnostics."
    >
      <div className="space-y-6">
        {/* Top Navigation Tabs */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap gap-2">
            {(
              [
                ['categories', `Categories (${categories.length})`, BookOpen],
                ['assessments', 'Timed & Company Prep', Building2],
                ['personalized', 'Personalized Practice', Compass],
                ['analytics', 'Analytics & History', BarChart3],
                ['leaderboard', 'Leaderboard & Privacy', Trophy],
              ] as const
            ).map(([key, label, Icon]) => (
              <button
                key={key}
                onClick={() => setActiveTab(key)}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition ${
                  activeTab === key
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800'
                }`}
              >
                <Icon className="w-4 h-4" />
                {label}
              </button>
            ))}
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={loadArenaOverview}
          >
            <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
            Refresh
          </Button>
        </div>

        {error && (
          <div className="p-3.5 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-sm text-rose-700 dark:text-rose-300">
            {error}
          </div>
        )}

        {loading ? (
          <Card>
            <div className="py-12 text-center text-sm text-slate-500">Loading Placement Preparation Arena...</div>
          </Card>
        ) : (
          <>
            {/* TAB 1: ALL 11 PREPARATION CATEGORIES */}
            {activeTab === 'categories' && (
              <div className="space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-3 bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800">
                  <div>
                    <h2 className="text-sm font-semibold text-slate-900 dark:text-white">
                      Topic Practice Difficulty Filter
                    </h2>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      Launch instant interactive practice (immediate explanations) or a 10-minute timed drill.
                    </p>
                  </div>
                  <select
                    value={selectedDifficulty}
                    onChange={(e) => setSelectedDifficulty(e.target.value as ArenaDifficulty | '')}
                    className="px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-800 dark:text-slate-100"
                  >
                    <option value="">All Difficulties</option>
                    <option value="easy">Easy</option>
                    <option value="medium">Medium</option>
                    <option value="hard">Hard</option>
                  </select>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {categories.map((cat) => (
                    <Card key={cat.category} className="hover:border-indigo-300 dark:hover:border-indigo-700 transition">
                      <div className="flex flex-col h-full justify-between space-y-4">
                        <div>
                          <div className="flex items-start justify-between gap-2 mb-2">
                            <div>
                              <div className="flex items-center gap-2 mb-1">
                                <h3 className="text-base font-bold text-slate-900 dark:text-white">{cat.label}</h3>
                                {cat.track_type === 'branch_core' && (
                                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-950/70 text-emerald-800 dark:text-emerald-300">
                                    Branch Core
                                  </span>
                                )}
                                {cat.track_type === 'common' && (
                                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-950/70 text-blue-800 dark:text-blue-300">
                                    Placement Common
                                  </span>
                                )}
                                {cat.track_type === 'career_elective' && (
                                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-purple-100 dark:bg-purple-950/70 text-purple-800 dark:text-purple-300">
                                    Elective Track
                                  </span>
                                )}
                              </div>
                            </div>
                            <Badge
                              variant={
                                cat.proficiency_label === 'Strong'
                                  ? 'success'
                                  : cat.proficiency_label === 'Developing'
                                  ? 'warning'
                                  : cat.proficiency_label === 'Needs Focus'
                                  ? 'danger'
                                  : 'neutral'
                              }
                            >
                              {cat.proficiency_label}
                            </Badge>
                          </div>
                          <p className="text-xs text-slate-600 dark:text-slate-300 mb-3">{cat.description}</p>
                          <div className="flex flex-wrap gap-1.5 text-[11px] text-slate-500 dark:text-slate-400">
                            <span className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800">
                              {cat.total_questions} Questions
                            </span>
                            {cat.coding_count > 0 && (
                              <span className="px-2 py-0.5 rounded bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300">
                                {cat.coding_count} Coding
                              </span>
                            )}
                            {cat.attempted_questions > 0 && (
                              <span className="px-2 py-0.5 rounded bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300">
                                Accuracy {cat.accuracy_pct}%
                              </span>
                            )}
                          </div>
                        </div>

                        <div className="flex gap-2 pt-2 border-t border-slate-100 dark:border-slate-800">
                          <Button
                            variant="primary"
                            size="sm"
                            className="flex-1"
                            onClick={() => handleStartTopicPractice(cat.category, false)}
                          >
                            Practice Topic
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleStartTopicPractice(cat.category, true)}
                          >
                            Timed Drill
                          </Button>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              </div>
            )}

            {/* TAB 2: TIMED TESTS, COMPANY-STYLE PREP & INSTITUTIONAL TESTS */}
            {activeTab === 'assessments' && (
              <div className="space-y-4">
                <div className="p-3.5 rounded-xl bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 text-xs text-amber-800 dark:text-amber-300 flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 shrink-0" />
                  <span>
                    Company-style preparation tracks feature original, curated problems modeled on typical industry engineering rounds — never confidential or leaked company test questions.
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {assessments.map((assess) => (
                    <Card key={assess.id} className="hover:border-indigo-300 dark:hover:border-indigo-700 transition">
                      <div className="flex flex-col justify-between h-full space-y-4">
                        <div>
                          <div className="flex flex-wrap items-center gap-2 mb-2">
                            <Badge
                              variant={
                                assess.mode === 'institutional_test'
                                  ? 'brand'
                                  : assess.mode === 'company_prep'
                                  ? 'info'
                                  : 'warning'
                              }
                            >
                              {assess.mode === 'institutional_test'
                                ? 'INSTITUTIONAL TEST'
                                : assess.mode === 'company_prep'
                                ? 'COMPANY-STYLE TRACK'
                                : 'TIMED MOCK'}
                            </Badge>
                            <Badge variant="neutral">{assess.difficulty.toUpperCase()}</Badge>
                            {assess.department_name ? (
                              <Badge variant="brand">{assess.department_name}</Badge>
                            ) : (
                              <Badge variant="neutral">All Engineering Branches</Badge>
                            )}
                            {assess.company_name_style && (
                              <Badge variant="info">{assess.company_name_style}</Badge>
                            )}
                          </div>
                          <h3 className="text-base font-bold text-slate-900 dark:text-white">{assess.title}</h3>
                          <p className="text-xs text-slate-600 dark:text-slate-300 mt-1">{assess.description}</p>
                          <p className="text-[11px] text-slate-400 mt-2 italic">{assess.provenance_notice}</p>
                        </div>

                        <div className="flex items-center justify-between pt-3 border-t border-slate-100 dark:border-slate-800">
                          <div className="flex items-center gap-3 text-xs text-slate-600 dark:text-slate-300">
                            <span className="flex items-center gap-1">
                              <Clock className="w-3.5 h-3.5" /> {assess.duration_minutes} mins
                            </span>
                            <span>{assess.question_count} Questions</span>
                          </div>
                          <Button variant="primary" size="sm" onClick={() => handleStartAssessment(assess.id)}>
                            Start Assessment
                          </Button>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              </div>
            )}

            {/* TAB 3: PERSONALIZED PRACTICE RECOMMENDATIONS */}
            {activeTab === 'personalized' && personalized && (
              <div className="space-y-5">
                <Card>
                  <CardHeader
                    title="Personalized Practice Engine"
                    subtitle={personalized.advisory_notice}
                    action={<Sparkles className="w-5 h-5 text-indigo-500" />}
                  />
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
                      <div className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1.5">
                        Target Job Roles Considered
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {personalized.target_roles_considered.length > 0 ? (
                          personalized.target_roles_considered.map((r) => (
                            <Badge key={r} variant="info">
                              {r}
                            </Badge>
                          ))
                        ) : (
                          <span className="text-xs text-slate-500">General campus software & core tracks</span>
                        )}
                      </div>
                    </div>

                    <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
                      <div className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1.5">
                        Skill & Preparation Gaps Linked
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {personalized.missing_skills_detected.length > 0 ? (
                          personalized.missing_skills_detected.map((s) => (
                            <Badge key={s} variant="warning">
                              {s}
                            </Badge>
                          ))
                        ) : (
                          <span className="text-xs text-emerald-600">All baseline published role skills covered</span>
                        )}
                      </div>
                    </div>
                  </div>
                  {personalized.ai_study_tip && (
                    <div className="mt-4 p-3 rounded-xl bg-indigo-50/70 dark:bg-indigo-950/30 border border-indigo-200 dark:border-indigo-800 text-xs text-indigo-800 dark:text-indigo-200">
                      <strong>Advisory Study Tip:</strong> {personalized.ai_study_tip}
                    </div>
                  )}
                </Card>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {personalized.recommendations.map((rec) => (
                    <Card key={rec.recommendation_id} className="hover:border-indigo-300 dark:hover:border-indigo-700 transition">
                      <div className="flex flex-col justify-between h-full space-y-3">
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <Badge variant="brand">{rec.source_signal.replace('_', ' ').toUpperCase()}</Badge>
                            <Badge variant="neutral">{rec.category_label}</Badge>
                          </div>
                          <h3 className="text-base font-bold text-slate-900 dark:text-white">{rec.title}</h3>
                          <p className="text-xs text-slate-600 dark:text-slate-300 mt-1">{rec.reason}</p>
                        </div>
                        <div className="pt-2 border-t border-slate-100 dark:border-slate-800 flex justify-end">
                          <Button
                            variant="primary"
                            size="sm"
                            onClick={() => handleStartTopicPractice(rec.category, false)}
                          >
                            Launch Recommended Practice
                          </Button>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              </div>
            )}

            {/* TAB 4: PERFORMANCE ANALYTICS & TEST HISTORY */}
            {activeTab === 'analytics' && analytics && (
              <div className="space-y-6">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <Card>
                    <div className="text-xs text-slate-500">Questions Attempted</div>
                    <div className="text-2xl font-bold text-slate-900 dark:text-white mt-1">
                      {analytics.total_questions_attempted}
                    </div>
                    <div className="text-[11px] text-emerald-600 mt-1">
                      {analytics.total_correct} correct • {analytics.total_incorrect} incorrect
                    </div>
                  </Card>
                  <Card>
                    <div className="text-xs text-slate-500">Overall Accuracy</div>
                    <div className="text-2xl font-bold text-indigo-600 dark:text-indigo-400 mt-1">
                      {analytics.overall_accuracy_pct}%
                    </div>
                    <div className="text-[11px] text-slate-400 mt-1">
                      {analytics.completed_attempts} completed sessions
                    </div>
                  </Card>
                  <Card>
                    <div className="text-xs text-slate-500">Avg Solving Time</div>
                    <div className="text-2xl font-bold text-slate-900 dark:text-white mt-1">
                      {analytics.avg_solving_time_seconds}s
                    </div>
                    <div className="text-[11px] text-slate-400 mt-1">Per question average</div>
                  </Card>
                  <Card>
                    <div className="text-xs text-slate-500">Coding Solved</div>
                    <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-1">
                      {analytics.coding_problems_solved}
                    </div>
                    <div className="text-[11px] text-slate-400 mt-1">All test cases passed</div>
                  </Card>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <Card>
                    <CardHeader title="Topic Proficiency Breakdown" subtitle="Accuracy across your branch placement categories" />
                    <div className="h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart
                          data={analytics.topic_proficiency.map((t) => ({
                            name: t.label.split(' ')[0],
                            accuracy: t.accuracy_pct,
                          }))}
                        >
                          <CartesianGrid strokeDasharray="3 3" stroke={isDark ? '#334155' : '#e2e8f0'} />
                          <XAxis dataKey="name" tick={{ fontSize: 10, fill: isDark ? '#cbd5e1' : '#475569' }} />
                          <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: isDark ? '#cbd5e1' : '#475569' }} />
                          <Tooltip />
                          <Bar dataKey="accuracy" fill="#6366f1" radius={[4, 4, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </Card>

                  <Card>
                    <CardHeader title="Score Improvement Trend" subtitle="Chronological completed test scores" />
                    {analytics.improvement_trend.length === 0 ? (
                      <div className="h-64 flex items-center justify-center text-xs text-slate-500">
                        Complete an assessment or practice session to plot your improvement trend.
                      </div>
                    ) : (
                      <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={analytics.improvement_trend}>
                            <CartesianGrid strokeDasharray="3 3" stroke={isDark ? '#334155' : '#e2e8f0'} />
                            <XAxis dataKey="title" tick={{ fontSize: 10, fill: isDark ? '#cbd5e1' : '#475569' }} />
                            <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: isDark ? '#cbd5e1' : '#475569' }} />
                            <Tooltip />
                            <Line type="monotone" dataKey="score_pct" stroke="#10b981" strokeWidth={2.5} />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                    )}
                  </Card>
                </div>

                <Card>
                  <CardHeader title="Recent Practice & Assessment History" />
                  {analytics.recent_attempts.length === 0 ? (
                    <p className="text-sm text-slate-500 py-4">No Arena attempts recorded yet.</p>
                  ) : (
                    <div className="divide-y divide-slate-100 dark:divide-slate-800">
                      {analytics.recent_attempts.map((a) => (
                        <div key={a.id} className="py-3 flex flex-wrap items-center justify-between gap-3">
                          <div>
                            <div className="text-sm font-semibold text-slate-900 dark:text-white">{a.title}</div>
                            <div className="text-xs text-slate-500">
                              {a.mode.replace('_', ' ')} • {a.attempted_count}/{a.total_questions} answered • Score {a.score_pct}%
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <Badge variant={a.status === 'submitted' ? 'success' : 'warning'}>{a.status}</Badge>
                            <Button variant="outline" size="sm" onClick={() => handleOpenAttempt(a.id)}>
                              {a.status === 'in_progress' ? 'Resume' : 'Review Answers'}
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </Card>
              </div>
            )}

            {/* TAB 5: PRIVACY-PRESERVING LEADERBOARD */}
            {activeTab === 'leaderboard' && (
              <div className="space-y-5">
                {preferences && (
                  <Card>
                    <CardHeader
                      title="Leaderboard Privacy Controls"
                      subtitle={preferences.privacy_notice}
                      action={<Lock className="w-5 h-5 text-emerald-500" />}
                    />
                    <div className="flex flex-wrap items-center gap-6">
                      <label className="flex items-center gap-2.5 text-sm font-medium text-slate-700 dark:text-slate-200 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={preferences.leaderboard_opt_in}
                          onChange={(e) => handleUpdatePrivacy({ leaderboard_opt_in: e.target.checked })}
                        />
                        Include my Arena scores on peer leaderboards (Opt-In)
                      </label>

                      <label className="flex items-center gap-2.5 text-sm font-medium text-slate-700 dark:text-slate-200 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={preferences.anonymize_name}
                          disabled={!preferences.leaderboard_opt_in}
                          onChange={(e) => handleUpdatePrivacy({ anonymize_name: e.target.checked })}
                        />
                        {preferences.anonymize_name ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        Mask my name with an anonymous Scholar alias
                      </label>
                    </div>
                  </Card>
                )}

                <Card>
                  <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                    <div>
                      <h3 className="text-base font-bold text-slate-900 dark:text-white">
                        Opted-In Peer Standings
                      </h3>
                      <p className="text-xs text-slate-500">
                        {leaderboard?.privacy_guarantee ||
                          'Zero sensitive academic data (CGPA, backlogs, emails, roll numbers) is ever displayed.'}
                      </p>
                    </div>

                    <div className="flex gap-2">
                      {(['department', 'batch', 'institution'] as const).map((sc) => (
                        <Button
                          key={sc}
                          size="sm"
                          variant={leaderboardScope === sc ? 'primary' : 'outline'}
                          onClick={() => setLeaderboardScope(sc)}
                        >
                          {sc.charAt(0).toUpperCase() + sc.slice(1)}
                        </Button>
                      ))}
                    </div>
                  </div>

                  {!leaderboard || leaderboard.entries.length === 0 ? (
                    <div className="py-8 text-center text-sm text-slate-500">
                      No students in this scope have opted into the leaderboard yet. Toggle opt-in above to join!
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="text-left text-xs text-slate-500 border-b border-slate-200 dark:border-slate-800">
                            <th className="py-2 pr-3">Rank</th>
                            <th className="py-2 pr-3">Participant</th>
                            <th className="py-2 pr-3">Department</th>
                            <th className="py-2 pr-3">Batch</th>
                            <th className="py-2 pr-3">Attempted</th>
                            <th className="py-2 pr-3">Accuracy</th>
                            <th className="py-2">Avg Score</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                          {leaderboard.entries.map((entry) => (
                            <tr
                              key={`${entry.rank}-${entry.display_name}`}
                              className={entry.is_current_user ? 'bg-indigo-50/50 dark:bg-indigo-950/20 font-semibold' : ''}
                            >
                              <td className="py-2.5 pr-3">#{entry.rank}</td>
                              <td className="py-2.5 pr-3">
                                {entry.display_name} {entry.is_current_user && <Badge variant="brand">You</Badge>}
                              </td>
                              <td className="py-2.5 pr-3 text-slate-600 dark:text-slate-300">
                                {entry.department_name || '—'}
                              </td>
                              <td className="py-2.5 pr-3">{entry.graduation_year || '—'}</td>
                              <td className="py-2.5 pr-3">{entry.questions_attempted}</td>
                              <td className="py-2.5 pr-3">{entry.accuracy_pct}%</td>
                              <td className="py-2.5 text-emerald-600 dark:text-emerald-400">{entry.avg_score_pct}%</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </Card>
              </div>
            )}
          </>
        )}
      </div>
    </DashboardLayout>
  );
};
