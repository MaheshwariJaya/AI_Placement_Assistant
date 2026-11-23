import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { DashboardLayout } from '../../components/layout/DashboardLayout';
import { Card, CardHeader } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { careerAssistantApi, jobApi } from '../../services/api';
import {
  ChatMessage,
  CareerAssistantResponse,
  CareerContextSummary,
  CareerPromptSuggestion,
  Job,
} from '../../types';
import {
  Sparkles,
  Send,
  Bot,
  User as UserIcon,
  AlertCircle,
  CheckCircle2,
  ArrowRight,
  RefreshCw,
  BookOpen,
  Briefcase,
  GraduationCap,
  Award,
  ShieldCheck,
  ChevronRight,
  Code2,
  Compass,
} from 'lucide-react';

interface DisplayTurn {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  responsePayload?: CareerAssistantResponse;
  timestamp: string;
}

export const CareerAssistantPage: React.FC = () => {
  const [messages, setMessages] = useState<DisplayTurn[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Context & Options
  const [contextSummary, setContextSummary] = useState<CareerContextSummary | null>(null);
  const [promptSuggestions, setPromptSuggestions] = useState<CareerPromptSuggestion[]>([]);
  const [availableJobs, setAvailableJobs] = useState<Job[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<number | undefined>(undefined);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadInitialData();
  }, [selectedJobId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const loadInitialData = async () => {
    try {
      const [ctx, prompts, jobsData] = await Promise.all([
        careerAssistantApi.getContext(selectedJobId),
        careerAssistantApi.getPrompts(selectedJobId),
        jobApi.list({ status: 'published' }).catch(() => []),
      ]);
      setContextSummary(ctx);
      setPromptSuggestions(prompts);
      setAvailableJobs(jobsData);
    } catch (err: any) {
      console.warn('Could not load career assistant context snapshot:', err);
    }
  };

  const handleSendMessage = async (textToSend?: string) => {
    const query = (textToSend || inputMessage).trim();
    if (!query || isLoading) return;

    setInputMessage('');
    setErrorMessage(null);

    const userTurn: DisplayTurn = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userTurn]);
    setIsLoading(true);

    // Build conversation history for API
    const historyPayload: ChatMessage[] = messages.slice(-6).map((m) => ({
      role: m.role,
      content: m.content,
    }));

    try {
      const res = await careerAssistantApi.chat(query, selectedJobId, historyPayload);

      const assistantTurn: DisplayTurn = {
        id: `asst-${Date.now()}`,
        role: 'assistant',
        content: res.data.answer,
        responsePayload: res,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev) => [...prev, assistantTurn]);
      setContextSummary(res.context_summary);
    } catch (err: any) {
      const detail = err.response?.data?.error?.message || err.message || 'Failed to get career guidance.';
      setErrorMessage(detail);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearHistory = () => {
    setMessages([]);
    setErrorMessage(null);
  };

  const formatAdviceType = (type: string) => {
    switch (type) {
      case 'skill_gap_analysis':
        return { label: 'Skill Gap Analysis', variant: 'warning' as const };
      case 'eligibility_explanation':
        return { label: 'Eligibility Explanation', variant: 'info' as const };
      case 'score_interpretation':
        return { label: 'Score Breakdown', variant: 'success' as const };
      case 'learning_roadmap':
        return { label: 'Learning Roadmap', variant: 'brand' as const };
      case 'placement_preparation':
        return { label: 'Placement Prep', variant: 'success' as const };
      default:
        return { label: 'Career Advisory', variant: 'neutral' as const };
    }
  };

  return (
    <DashboardLayout
      role="student"
      title="AI Career Assistant"
      subtitle="Personalized placement coaching, skill gap analysis, and grounded learning roadmaps"
    >
      <div className="max-w-5xl mx-auto space-y-6">
        {/* Header Banner */}
        <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 rounded-2xl p-6 text-white shadow-md border border-slate-800">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="w-8 h-8 rounded-lg bg-indigo-500/20 text-indigo-400 flex items-center justify-center border border-indigo-400/30">
                  <Sparkles className="w-4 h-4" />
                </span>
                <h1 className="text-xl font-bold tracking-tight">AI Career Assistant</h1>
                <Badge variant="info">Grounded Advisory</Badge>
              </div>
              <p className="text-xs text-slate-300">
                Personalized placement guidance strictly grounded in your verified academic record, approved skills, and deterministic eligibility rules.
              </p>
            </div>

            {/* Target Job Selector */}
            <div className="flex items-center gap-2 bg-slate-800/80 p-2 rounded-xl border border-slate-700/80 text-xs">
              <Briefcase className="w-4 h-4 text-indigo-400 shrink-0" />
              <select
                value={selectedJobId || ''}
                onChange={(e) => setSelectedJobId(e.target.value ? Number(e.target.value) : undefined)}
                className="bg-transparent text-slate-200 text-xs focus:outline-none cursor-pointer"
              >
                <option value="" className="bg-slate-900 text-slate-200">
                  All Open Roles (General Advice)
                </option>
                {availableJobs.map((job) => (
                  <option key={job.id} value={job.id} className="bg-slate-900 text-slate-200">
                    {job.title} — {job.company?.name || 'Partner'}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Student Profile Snapshot Pill */}
          {contextSummary && (
            <div className="mt-4 pt-3 border-t border-slate-800 flex flex-wrap items-center gap-3 text-xs text-slate-300">
              <span className="text-slate-400">Context:</span>
              <span className="bg-slate-800/70 px-2 py-0.5 rounded border border-slate-700/50">
                {contextSummary.department_name || 'Department N/A'}
              </span>
              <span className="bg-slate-800/70 px-2 py-0.5 rounded border border-slate-700/50">
                CGPA: {contextSummary.cgpa !== null && contextSummary.cgpa !== undefined ? contextSummary.cgpa.toFixed(2) : 'N/A'}
              </span>
              <span className="bg-slate-800/70 px-2 py-0.5 rounded border border-slate-700/50">
                Backlogs: {contextSummary.active_backlogs ?? 0}
              </span>
              <span className="bg-slate-800/70 px-2 py-0.5 rounded border border-slate-700/50">
                Skills: {contextSummary.skills_count} verified
              </span>
              <span className="bg-slate-800/70 px-2 py-0.5 rounded border border-slate-700/50">
                Projects: {contextSummary.projects_count}
              </span>
            </div>
          )}
        </div>

        {/* Incomplete Profile Alert Banner (if applicable) */}
        {contextSummary && !contextSummary.is_profile_complete && (
          <div className="bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800/60 rounded-xl p-4 flex items-start justify-between gap-3 text-xs text-amber-900">
            <div className="flex items-start gap-2.5">
              <AlertCircle className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-amber-900 dark:text-amber-200">Notice: Incomplete Profile Information</span>
                <p className="text-amber-800 dark:text-amber-300/90 mt-0.5">
                  Your profile is missing{' '}
                  <span className="font-medium underline">{contextSummary.missing_sections.join(', ')}</span>.
                  The AI assistant will provide guidance, but advice precision is restricted until your portfolio is complete.
                </p>
              </div>
            </div>
            <Link to="/student/profile">
              <Button size="sm" variant="outline" className="bg-white dark:bg-slate-900 border-amber-300 dark:border-amber-700 text-amber-800 dark:text-amber-300 hover:bg-amber-100 dark:hover:bg-amber-950/60 text-xs shrink-0">
                Update Profile
              </Button>
            </Link>
          </div>
        )}

        {/* Chat Stream & Interaction Card */}
        <Card className="min-h-[500px] flex flex-col justify-between shadow-sm border-slate-200/80 dark:border-slate-800">
          <CardHeader
            title="Advisory Conversation"
            subtitle="Ask questions about your skill readiness, eligibility, or learning roadmaps."
            action={
              messages.length > 0 && (
                <Button size="sm" variant="ghost" onClick={handleClearHistory} className="text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 text-xs gap-1">
                  <RefreshCw className="w-3.5 h-3.5" />
                  Reset Session
                </Button>
              )
            }
          />

          {/* Messages Container */}
          <div className="p-4 sm:p-6 flex-1 space-y-6 overflow-y-auto max-h-[600px]">
            {messages.length === 0 ? (
              /* Empty State with Suggested Prompts */
              <div className="py-8 text-center space-y-6 max-w-xl mx-auto">
                <div className="w-12 h-12 rounded-2xl bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-100 dark:border-indigo-800/60 text-indigo-600 dark:text-indigo-300 flex items-center justify-center mx-auto shadow-sm">
                  <Compass className="w-6 h-6" />
                </div>
                <div className="space-y-1">
                  <h3 className="text-base font-semibold text-slate-800">How can I assist your placement journey today?</h3>
                  <p className="text-xs text-slate-500">
                    Select a suggested question below or type your own question regarding job compatibility, learning roadmaps, or skill prerequisites.
                  </p>
                </div>

                {/* Suggested Prompt Chips */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-left">
                  {promptSuggestions.map((item) => (
                    <button
                      key={item.id}
                      onClick={() => handleSendMessage(item.prompt)}
                      className="p-3 rounded-xl border border-slate-200/90 dark:border-slate-800 bg-white dark:bg-slate-900 hover:bg-slate-50/80 dark:hover:bg-slate-800/80 hover:border-indigo-300 transition text-xs space-y-1 group"
                    >
                      <div className="flex items-center justify-between text-indigo-600 font-medium">
                        <span>{item.title}</span>
                        <ChevronRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-indigo-600 group-hover:translate-x-0.5 transition" />
                      </div>
                      <p className="text-[11px] text-slate-500 line-clamp-2">{item.prompt}</p>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              /* Message Bubbles */
              messages.map((m) => (
                <div
                  key={m.id}
                  className={`flex items-start gap-3 ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  {m.role === 'assistant' && (
                    <div className="w-8 h-8 rounded-full bg-indigo-600 text-white flex items-center justify-center shrink-0 shadow-sm mt-1">
                      <Bot className="w-4 h-4" />
                    </div>
                  )}

                  <div className={`max-w-2xl ${m.role === 'user' ? 'items-end' : 'items-start'} flex flex-col space-y-2`}>
                    {m.role === 'user' ? (
                      /* User Message Bubble */
                      <div className="bg-slate-900 dark:bg-brand-600 text-white px-4 py-2.5 rounded-2xl rounded-tr-sm text-xs leading-relaxed shadow-sm">
                        {m.content}
                      </div>
                    ) : (
                      /* Assistant Structured Response Card */
                      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl rounded-tl-sm p-4 sm:p-5 text-xs shadow-sm space-y-4 text-slate-800 dark:text-slate-200">
                        {/* Advice Type Badge & Timestamp */}
                        {m.responsePayload?.data && (
                          <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-2">
                            <Badge variant={formatAdviceType(m.responsePayload.data.advice_type).variant}>
                              {formatAdviceType(m.responsePayload.data.advice_type).label}
                            </Badge>
                            <span className="text-[10px] text-slate-400 dark:text-slate-500">{m.timestamp}</span>
                          </div>
                        )}

                        {/* Main Answer Body */}
                        <div className="prose prose-xs dark:prose-invert text-slate-800 dark:text-slate-200 leading-relaxed whitespace-pre-line">
                          {m.content}
                        </div>

                        {/* Key Points */}
                        {m.responsePayload?.data.key_points && m.responsePayload.data.key_points.length > 0 && (
                          <div className="bg-slate-50/80 dark:bg-slate-800/60 rounded-xl p-3 border border-slate-200/80 dark:border-slate-700/80 space-y-1.5">
                            <span className="text-[11px] font-semibold text-slate-700 dark:text-slate-200 flex items-center gap-1.5">
                              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                              Key Findings
                            </span>
                            <ul className="space-y-1 text-slate-600 dark:text-slate-300">
                              {m.responsePayload.data.key_points.map((pt, i) => (
                                <li key={i} className="flex items-start gap-1.5">
                                  <span className="text-slate-400 dark:text-slate-500">•</span>
                                  <span>{pt}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Suggested Next Actions */}
                        {m.responsePayload?.data.suggested_next_actions && m.responsePayload.data.suggested_next_actions.length > 0 && (
                          <div className="bg-indigo-50/50 dark:bg-indigo-950/30 rounded-xl p-3 border border-indigo-100 dark:border-indigo-900/60 space-y-1.5">
                            <span className="text-[11px] font-semibold text-indigo-950 dark:text-indigo-200 flex items-center gap-1.5">
                              <ArrowRight className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
                              Recommended Actions
                            </span>
                            <ul className="space-y-1 text-slate-700 dark:text-slate-300">
                              {m.responsePayload.data.suggested_next_actions.map((act, i) => (
                                <li key={i} className="flex items-start gap-1.5">
                                  <span className="text-indigo-500 dark:text-indigo-400 font-bold">{i + 1}.</span>
                                  <span>{act}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Skills to Acquire Pills */}
                        {m.responsePayload?.data.relevant_skills_to_acquire && m.responsePayload.data.relevant_skills_to_acquire.length > 0 && (
                          <div className="space-y-1.5 pt-1">
                            <span className="text-[11px] font-semibold text-slate-700 dark:text-slate-200 flex items-center gap-1.5">
                              <Code2 className="w-3.5 h-3.5 text-slate-600 dark:text-slate-400" />
                              Prioritized Skills to Study
                            </span>
                            <div className="flex flex-wrap gap-1.5">
                              {m.responsePayload.data.relevant_skills_to_acquire.map((sk, i) => (
                                <span key={i} className="px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 text-[11px]">
                                  {sk}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Missing Context Warning */}
                        {m.responsePayload?.data.limitations_or_missing_context && (
                          <div className="text-[11px] text-amber-700 dark:text-amber-300 bg-amber-50/80 dark:bg-amber-950/30 p-2.5 rounded-lg border border-amber-200/80 dark:border-amber-800/60 flex items-start gap-1.5">
                            <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5 text-amber-600 dark:text-amber-400" />
                            <span>{m.responsePayload.data.limitations_or_missing_context}</span>
                          </div>
                        )}

                        {/* Disclaimer */}
                        <div className="pt-2 border-t border-slate-100 dark:border-slate-800 text-[10px] text-slate-400 dark:text-slate-500 flex items-center gap-1">
                          <ShieldCheck className="w-3 h-3 text-slate-400 dark:text-slate-500" />
                          <span>{m.responsePayload?.data.disclaimer || 'Advisory guidance only. Placement rules governed by institution.'}</span>
                        </div>
                      </div>
                    )}
                  </div>

                  {m.role === 'user' && (
                    <div className="w-8 h-8 rounded-full bg-slate-700 text-white flex items-center justify-center shrink-0 shadow-sm mt-1">
                      <UserIcon className="w-4 h-4" />
                    </div>
                  )}
                </div>
              ))
            )}

            {/* Loading Indicator */}
            {isLoading && (
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-full bg-indigo-600 text-white flex items-center justify-center shrink-0 shadow-sm animate-pulse">
                  <Bot className="w-4 h-4" />
                </div>
                <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl rounded-tl-sm p-4 text-xs text-slate-500 dark:text-slate-400 shadow-sm flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-indigo-500 dark:text-indigo-400 animate-spin" />
                  <span>AI Career Assistant is formulating grounded advice from your profile...</span>
                </div>
              </div>
            )}

            {/* Error Message */}
            {errorMessage && (
              <div className="bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800/60 rounded-xl p-3 text-xs text-red-800 dark:text-red-300 flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-red-600 dark:text-red-400 shrink-0 mt-0.5" />
                <div className="flex-1">
                  <span className="font-semibold">Unable to process request</span>
                  <p className="mt-0.5">{errorMessage}</p>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Quick Prompt Chips (When messages exist) */}
          {messages.length > 0 && promptSuggestions.length > 0 && (
            <div className="px-4 py-2 bg-slate-50 dark:bg-slate-800/60 border-t border-slate-200/80 dark:border-slate-800 flex items-center gap-2 overflow-x-auto text-xs">
              <span className="text-[11px] text-slate-400 dark:text-slate-500 font-medium shrink-0">Follow-up:</span>
              {promptSuggestions.slice(0, 3).map((item) => (
                <button
                  key={item.id}
                  onClick={() => handleSendMessage(item.prompt)}
                  disabled={isLoading}
                  className="px-2.5 py-1 rounded-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:text-indigo-600 dark:hover:text-indigo-400 hover:border-indigo-300 dark:hover:border-indigo-700 text-[11px] shrink-0 transition"
                >
                  {item.title}
                </button>
              ))}
            </div>
          )}

          {/* Input Form */}
          <div className="p-4 border-t border-slate-200/90 dark:border-slate-800 bg-white dark:bg-slate-900 rounded-b-2xl">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendMessage();
              }}
              className="flex items-center gap-2"
            >
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                placeholder={
                  selectedJobId
                    ? "Ask a question about your match or skill gap for this role..."
                    : "Ask about career roadmaps, skill gaps, or placement preparation..."
                }
                disabled={isLoading}
                className="flex-1 text-xs border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 dark:placeholder:text-slate-500 rounded-xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-500 disabled:bg-slate-50 dark:disabled:bg-slate-900 transition"
              />
              <Button
                type="submit"
                disabled={!inputMessage.trim() || isLoading}
                className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2.5 rounded-xl shrink-0 flex items-center gap-1.5 text-xs shadow-sm"
              >
                <Send className="w-3.5 h-3.5" />
                <span>Send</span>
              </Button>
            </form>
          </div>
        </Card>
      </div>
    </DashboardLayout>
  );
};
