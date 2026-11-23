import React, { useEffect, useRef, useState } from 'react';
import { Card } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { MockInterviewSessionDetail } from '../../types';
import {
  Clock,
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  Pause,
  Flag,
  Send,
  Sparkles,
  AlertCircle,
  CheckCircle2,
  Play,
  ChevronLeft,
  ChevronRight,
  Grid,
} from 'lucide-react';

interface ActiveInterviewRunnerProps {
  session: MockInterviewSessionDetail;
  submitting: boolean;
  onSubmitAnswer: (payload: {
    question_id: number;
    answer_text?: string;
    selected_option_key?: string | null;
    input_mode: 'text' | 'voice';
    response_time_seconds: number;
    elapsed_seconds: number;
  }) => Promise<{ followup_generated: boolean; followup_rationale?: string | null; ready_to_complete: boolean }>;
  onPause: (elapsedSeconds: number) => Promise<void>;
  onResume: () => Promise<void>;
  onComplete: (elapsedSeconds: number) => Promise<void>;
  onExit: () => void;
}

const CATEGORY_LABELS: Record<string, string> = {
  technical: 'Technical',
  hr: 'HR & Fit',
  behavioral: 'Behavioral (STAR)',
  aptitude: 'Aptitude & Logic',
  project_based: 'Project-Based',
};

const formatTimer = (secs: number): string => {
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
};

export const ActiveInterviewRunner: React.FC<ActiveInterviewRunnerProps> = ({
  session,
  submitting,
  onSubmitAnswer,
  onPause,
  onResume,
  onComplete,
  onExit,
}) => {
  const isMcq = session.question_format === 'mcq' || session.questions.some((q) => q.question_type === 'mcq' || (q.options && q.options.length > 0));
  const [selectedOrder, setSelectedOrder] = useState<number | null>(null);
  const currentQ = (selectedOrder != null ? session.questions.find((q) => q.question_order === selectedOrder) : null) || session.current_question || session.questions[0];

  const [answerText, setAnswerText] = useState('');
  const [selectedOptionKey, setSelectedOptionKey] = useState<string | null>(null);
  const [inputMode, setInputMode] = useState<'text' | 'voice'>('text');
  const [elapsedSeconds, setElapsedSeconds] = useState<number>(session.elapsed_seconds || 0);
  const [questionElapsed, setQuestionElapsed] = useState<number>(0);
  const [followupNotice, setFollowupNotice] = useState<string | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  const [confirmEnd, setConfirmEnd] = useState<boolean>(false);

  // Optional browser Web Speech API dictation + TTS read-aloud
  const SpeechRecognitionCtor =
    typeof window !== 'undefined'
      ? (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
      : null;
  const speechSupported = Boolean(SpeechRecognitionCtor);
  const ttsSupported = typeof window !== 'undefined' && 'speechSynthesis' in window;

  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const recognitionRef = useRef<any>(null);

  const isPaused = session.status === 'paused';

  useEffect(() => {
    setElapsedSeconds(session.elapsed_seconds || 0);
  }, [session.id]);

  useEffect(() => {
    if (currentQ?.answer) {
      setAnswerText(currentQ.answer.answer_text || '');
      setSelectedOptionKey(currentQ.answer.selected_option_key || null);
    } else {
      setAnswerText('');
      setSelectedOptionKey(null);
    }
    setInputMode('text');
    setQuestionElapsed(0);
    setLocalError(null);
    stopListening();
    if (ttsSupported) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
    }
  }, [currentQ?.id]);

  useEffect(() => {
    if (isPaused || session.status !== 'in_progress') return;
    const interval = window.setInterval(() => {
      setElapsedSeconds((prev) => prev + 1);
      setQuestionElapsed((prev) => prev + 1);
    }, 1000);
    return () => window.clearInterval(interval);
  }, [isPaused, session.status]);

  useEffect(() => {
    return () => {
      stopListening();
      if (ttsSupported) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  const stopListening = () => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {
        // Ignore already stopped recognition
      }
      recognitionRef.current = null;
    }
    setIsListening(false);
  };

  const toggleVoiceDictation = () => {
    if (!SpeechRecognitionCtor) return;
    if (isListening) {
      stopListening();
      return;
    }
    try {
      const recognition = new SpeechRecognitionCtor();
      recognition.continuous = true;
      recognition.interimResults = false;
      recognition.lang = 'en-US';
      recognition.onresult = (event: any) => {
        let transcript = '';
        for (let i = event.resultIndex; i < event.results.length; i += 1) {
          if (event.results[i].isFinal) {
            transcript += event.results[i][0].transcript + ' ';
          }
        }
        if (transcript.trim()) {
          setAnswerText((prev) => (prev ? `${prev.trim()} ${transcript.trim()}` : transcript.trim()));
          setInputMode('voice');
        }
      };
      recognition.onerror = () => {
        setIsListening(false);
      };
      recognition.onend = () => {
        setIsListening(false);
      };
      recognition.start();
      recognitionRef.current = recognition;
      setIsListening(true);
    } catch {
      setLocalError('Microphone dictation could not be started in this browser.');
    }
  };

  const toggleReadAloud = () => {
    if (!ttsSupported || !currentQ) return;
    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      return;
    }
    const utterance = new SpeechSynthesisUtterance(currentQ.question_text);
    utterance.rate = 1.0;
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);
    setIsSpeaking(true);
    window.speechSynthesis.speak(utterance);
  };

  const handleSelectOption = async (optKey: string, optText: string) => {
    if (!currentQ || submitting || isPaused) return;
    setSelectedOptionKey(optKey);
    setAnswerText(optText);
    setLocalError(null);
    try {
      await onSubmitAnswer({
        question_id: currentQ.id,
        answer_text: optText,
        selected_option_key: optKey,
        input_mode: 'text',
        response_time_seconds: questionElapsed,
        elapsed_seconds: elapsedSeconds,
      });
    } catch (err: any) {
      setLocalError(err?.response?.data?.error?.message || err?.message || 'Failed to record choice.');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentQ || submitting || isPaused) return;
    const trimmed = answerText.trim();
    if (!trimmed && !selectedOptionKey) {
      setLocalError('Please enter an answer or select an option before proceeding.');
      return;
    }
    setLocalError(null);
    setFollowupNotice(null);
    stopListening();
    try {
      const res = await onSubmitAnswer({
        question_id: currentQ.id,
        answer_text: trimmed || (selectedOptionKey ? `Option ${selectedOptionKey}` : ''),
        selected_option_key: selectedOptionKey,
        input_mode: inputMode,
        response_time_seconds: questionElapsed,
        elapsed_seconds: elapsedSeconds,
      });
      if (res.followup_generated) {
        setFollowupNotice(
          res.followup_rationale ||
            'AI Interviewer added a targeted follow-up question based on your response.'
        );
      } else if (currentQ.question_order < totalQs) {
        setSelectedOrder(currentQ.question_order + 1);
      }
    } catch (err: any) {
      setLocalError(err?.response?.data?.error?.message || err?.message || 'Failed to submit answer.');
    }
  };

  const totalQs = Math.max(1, session.questions.length);
  const answeredCount = session.questions.filter((q) => q.answer != null).length;
  const progressPct = Math.min(100, Math.round((answeredCount / totalQs) * 100));
  const timeLimitSecs = session.time_limit_minutes ? session.time_limit_minutes * 60 : null;
  const isOverTime = timeLimitSecs !== null && elapsedSeconds > timeLimitSecs;

  return (
    <div className="space-y-5">
      {/* Session Header Bar */}
      <Card>
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="brand" size="sm">
                {CATEGORY_LABELS[session.category] || session.category}
              </Badge>
              <Badge variant="neutral" size="sm" className="capitalize">
                {session.difficulty}
              </Badge>
              {isPaused && (
                <Badge variant="warning" size="sm">
                  Paused
                </Badge>
              )}
              {session.job_title && (
                <span className="text-xs font-medium text-slate-600 dark:text-slate-300">
                  Target: {session.job_title}
                  {session.company_name ? ` (${session.company_name})` : ''}
                </span>
              )}
              {!session.job_title && session.target_role && (
                <span className="text-xs font-medium text-slate-600 dark:text-slate-300">
                  Role: {session.target_role}
                </span>
              )}
            </div>

            <div className="mt-2 flex items-center gap-4 text-xs text-slate-500 dark:text-slate-400">
              <span>
                Progress: <strong className="text-slate-800 dark:text-slate-100">{answeredCount}</strong> / {totalQs} answered
              </span>
              <span className={`inline-flex items-center gap-1 font-mono font-semibold ${isOverTime ? 'text-rose-600 dark:text-rose-400' : 'text-slate-700 dark:text-slate-200'}`}>
                <Clock className="w-3.5 h-3.5" />
                {formatTimer(elapsedSeconds)}
                {session.time_limit_minutes ? ` / ${session.time_limit_minutes}:00` : ''}
              </span>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {isPaused ? (
              <Button size="sm" variant="primary" icon={<Play className="w-3.5 h-3.5" />} onClick={onResume} disabled={submitting}>
                Resume Interview
              </Button>
            ) : (
              <Button size="sm" variant="outline" icon={<Pause className="w-3.5 h-3.5" />} onClick={() => onPause(elapsedSeconds)} disabled={submitting}>
                Pause &amp; Save
              </Button>
            )}

            {!confirmEnd ? (
              <Button size="sm" variant="danger" icon={<Flag className="w-3.5 h-3.5" />} onClick={() => setConfirmEnd(true)} disabled={submitting}>
                End Interview
              </Button>
            ) : (
              <div className="flex items-center gap-1.5 bg-rose-50 dark:bg-rose-950/50 border border-rose-200 dark:border-rose-800 px-2.5 py-1 rounded-lg">
                <span className="text-[11px] font-medium text-rose-800 dark:text-rose-200">
                  {answeredCount > 0 ? 'Finish & evaluate answered prompts?' : 'Exit with 0 answers (unscored)?'}
                </span>
                <Button size="sm" variant="danger" onClick={() => onComplete(elapsedSeconds)} isLoading={submitting}>
                  Confirm
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setConfirmEnd(false)} disabled={submitting}>
                  Cancel
                </Button>
              </div>
            )}

            <Button size="sm" variant="ghost" onClick={onExit} disabled={submitting}>
              Studio Home
            </Button>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mt-4 w-full h-2 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-brand-600 dark:bg-brand-500 transition-all duration-300"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </Card>

      {followupNotice && (
        <div className="p-3.5 rounded-xl bg-indigo-50 dark:bg-indigo-950/50 border border-indigo-200 dark:border-indigo-800 flex items-center gap-2.5 text-xs text-indigo-900 dark:text-indigo-200">
          <Sparkles className="w-4 h-4 text-indigo-600 dark:text-indigo-400 shrink-0" />
          <span>{followupNotice}</span>
        </div>
      )}

      {isPaused && (
        <div className="p-4 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 flex items-center justify-between gap-3 text-xs text-amber-900 dark:text-amber-200">
          <span>Your session timer is paused and all previous answers are saved. Click Resume Interview whenever you are ready.</span>
          <Button size="sm" variant="primary" onClick={onResume}>
            Resume
          </Button>
        </div>
      )}

      {/* Question Palette Grid for 30 / 50 questions */}
      {isMcq && (
        <Card className="p-3 sm:p-4">
          <div className="flex items-center justify-between mb-2.5">
            <span className="text-xs font-bold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
              <Grid className="w-3.5 h-3.5 text-brand-600 dark:text-brand-400" />
              Question Navigation Palette ({totalQs} Questions)
            </span>
            <div className="flex items-center gap-3 text-[11px] text-slate-500 dark:text-slate-400">
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block" /> Answered ({answeredCount})
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded-full bg-slate-300 dark:bg-slate-700 inline-block" /> Remaining ({totalQs - answeredCount})
              </span>
            </div>
          </div>
          <div className="flex flex-wrap gap-1.5 max-h-36 overflow-y-auto p-1">
            {session.questions.map((q) => {
              const isAnswered = q.answer != null;
              const isCurrent = q.question_order === currentQ?.question_order;
              return (
                <button
                  key={q.id}
                  type="button"
                  onClick={() => setSelectedOrder(q.question_order)}
                  className={`w-8 h-8 rounded-lg text-xs font-bold transition-all flex items-center justify-center shrink-0 ${
                    isCurrent
                      ? 'ring-2 ring-brand-500 bg-brand-600 text-white shadow-xs'
                      : isAnswered
                      ? 'bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700'
                      : 'bg-slate-50 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700 hover:border-slate-400'
                  }`}
                >
                  {q.question_order}
                </button>
              );
            })}
          </div>
        </Card>
      )}

      {/* Question Card OR Ready-to-Complete Card */}
      {currentQ ? (
        <Card>
          <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-slate-100 dark:border-slate-800">
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-1 rounded-lg bg-brand-50 dark:bg-brand-950/60 text-brand-700 dark:text-brand-300 text-xs font-bold">
                Question {currentQ.question_order} of {totalQs}
              </span>
              {currentQ.options && currentQ.options.length > 0 && (
                <Badge variant="brand" size="sm">
                  MCQ Option
                </Badge>
              )}
              {currentQ.is_followup && (
                <Badge variant="info" size="sm">
                  Adaptive Follow-Up
                </Badge>
              )}
              <span className="text-xs font-semibold text-slate-600 dark:text-slate-300">
                Topic: {currentQ.topic}
              </span>
            </div>

            {ttsSupported && (
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={toggleReadAloud}
                icon={isSpeaking ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
              >
                {isSpeaking ? 'Stop Audio' : 'Read Question'}
              </Button>
            )}
          </div>

          <div className="py-5">
            <p className="text-base sm:text-lg font-semibold text-slate-900 dark:text-slate-100 leading-relaxed">
              {currentQ.question_text}
            </p>
          </div>

          {currentQ.options && currentQ.options.length > 0 ? (
            /* MCQ Option Selection Interface */
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {currentQ.options.map((opt) => {
                  const isSelected = selectedOptionKey === opt.key;
                  return (
                    <button
                      key={opt.key}
                      type="button"
                      disabled={isPaused || submitting}
                      onClick={() => handleSelectOption(opt.key, opt.text)}
                      className={`p-4 rounded-xl border text-left transition-all flex items-start gap-3 cursor-pointer ${
                        isSelected
                          ? 'bg-brand-50/90 dark:bg-brand-950/70 border-brand-600 dark:border-brand-500 shadow-xs ring-2 ring-brand-500'
                          : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-850'
                      }`}
                    >
                      <div
                        className={`w-7 h-7 rounded-lg font-bold text-xs flex items-center justify-center shrink-0 ${
                          isSelected
                            ? 'bg-brand-600 text-white'
                            : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300'
                        }`}
                      >
                        {opt.key}
                      </div>
                      <div className="text-sm font-medium text-slate-800 dark:text-slate-200 leading-snug pt-0.5">
                        {opt.text}
                      </div>
                    </button>
                  );
                })}
              </div>

              {localError && (
                <div className="p-3 rounded-lg bg-rose-50 dark:bg-rose-950/50 border border-rose-200 dark:border-rose-800 flex items-center gap-2 text-xs text-rose-700 dark:text-rose-300">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{localError}</span>
                </div>
              )}

              {/* Navigation Controls */}
              <div className="flex flex-wrap items-center justify-between gap-3 pt-4 border-t border-slate-100 dark:border-slate-800">
                <div className="flex items-center gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={currentQ.question_order <= 1 || isPaused || submitting}
                    onClick={() => setSelectedOrder(currentQ.question_order - 1)}
                    icon={<ChevronLeft className="w-3.5 h-3.5" />}
                  >
                    Previous
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={currentQ.question_order >= totalQs || isPaused || submitting}
                    onClick={() => setSelectedOrder(currentQ.question_order + 1)}
                  >
                    Next <ChevronRight className="w-3.5 h-3.5 ml-1 inline" />
                  </Button>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-500 dark:text-slate-400">
                    {answeredCount} / {totalQs} answered
                  </span>
                  <Button
                    type="button"
                    variant="primary"
                    size="sm"
                    onClick={() => setConfirmEnd(true)}
                    disabled={isPaused || submitting}
                  >
                    Submit Test &amp; Review
                  </Button>
                </div>
              </div>
            </div>
          ) : (
            /* Open-ended Conversational Textarea Form */
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label
                    htmlFor="mock-answer-input"
                    className="text-xs font-semibold text-slate-700 dark:text-slate-300"
                  >
                    Your Response {inputMode === 'voice' ? '(Includes Voice Dictation)' : ''}
                  </label>
                  {speechSupported && !isPaused && (
                    <button
                      type="button"
                      onClick={toggleVoiceDictation}
                      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border transition-colors ${
                        isListening
                          ? 'bg-rose-50 dark:bg-rose-950/60 border-rose-300 dark:border-rose-700 text-rose-700 dark:text-rose-300 animate-pulse'
                          : 'bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700'
                      }`}
                    >
                      {isListening ? <MicOff className="w-3.5 h-3.5" /> : <Mic className="w-3.5 h-3.5" />}
                      <span>{isListening ? 'Stop Dictation' : 'Voice Input (Optional)'}</span>
                    </button>
                  )}
                </div>

                <textarea
                  id="mock-answer-input"
                  rows={7}
                  disabled={isPaused || submitting}
                  value={answerText}
                  onChange={(e) => setAnswerText(e.target.value)}
                  placeholder="Structure your explanation clearly: state your approach, key trade-offs or STAR context, and expected outcome..."
                  className="w-full rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 p-3.5 text-sm text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-brand-500 disabled:opacity-60"
                />
                <div className="mt-1.5 flex items-center justify-between text-[11px] text-slate-400 dark:text-slate-500">
                  <span>Response timer: {formatTimer(questionElapsed)}</span>
                  <span>{answerText.length} / 6000 characters</span>
                </div>
              </div>

              {localError && (
                <div className="p-3 rounded-lg bg-rose-50 dark:bg-rose-950/50 border border-rose-200 dark:border-rose-800 flex items-center gap-2 text-xs text-rose-700 dark:text-rose-300">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{localError}</span>
                </div>
              )}

              <div className="flex items-center justify-between pt-2">
                <span className="text-[11px] text-slate-500 dark:text-slate-400">
                  Advisory practice mode · Answers are evaluated after session completion
                </span>
                <Button
                  type="submit"
                  variant="primary"
                  isLoading={submitting}
                  disabled={isPaused || !answerText.trim()}
                  icon={<Send className="w-4 h-4" />}
                >
                  {currentQ.question_order === totalQs ? 'Submit Final Answer' : 'Submit Answer & Next'}
                </Button>
              </div>
            </form>
          )}
        </Card>
      ) : (
        <Card className="text-center py-10">
          <div className="w-12 h-12 rounded-full bg-emerald-100 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 flex items-center justify-center mx-auto mb-3">
            <CheckCircle2 className="w-6 h-6" />
          </div>
          <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">
            All Interview Questions Answered!
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 max-w-md mx-auto mt-1 mb-5">
            Run the 7-criteria AI evaluation to generate your overall score, question-by-question feedback, improvement areas, and model answers.
          </p>
          <Button
            variant="primary"
            size="lg"
            isLoading={submitting}
            onClick={() => onComplete(elapsedSeconds)}
            icon={<Sparkles className="w-4 h-4" />}
          >
            Generate Structured Evaluation
          </Button>
        </Card>
      )}
    </div>
  );
};

