import React, { useState } from 'react';
import { Card, CardHeader } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { MockInterviewSessionDetail } from '../../types';
import {
  Award,
  BookOpen,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Info,
  Lightbulb,
  RotateCcw,
  ShieldAlert,
  TrendingUp,
} from 'lucide-react';

interface EvaluationReportViewProps {
  session: MockInterviewSessionDetail;
  onBackToStudio: () => void;
  onStartSimilar: () => void;
}

const scoreVariant = (score: number): 'success' | 'brand' | 'warning' | 'danger' => {
  if (score >= 80) return 'success';
  if (score >= 65) return 'brand';
  if (score >= 50) return 'warning';
  return 'danger';
};

export const EvaluationReportView: React.FC<EvaluationReportViewProps> = ({
  session,
  onBackToStudio,
  onStartSimilar,
}) => {
  const evaluation = session.evaluation;
  const [expandedOrder, setExpandedOrder] = useState<number | null>(1);

  if (!evaluation) {
    return (
      <Card>
        <div className="py-10 text-center space-y-3">
          <Info className="w-8 h-8 text-slate-400 mx-auto" />
          <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
            Session Ended Without Submitted Answers
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 max-w-md mx-auto">
            This session was closed before any responses were submitted, so no performance score was recorded.
          </p>
          <Button variant="primary" size="sm" onClick={onBackToStudio}>
            Return to Interview Studio
          </Button>
        </div>
      </Card>
    );
  }

  const criteriaRows: { label: string; score: number }[] = [
    { label: 'Technical Correctness', score: evaluation.criteria_scores.technical_correctness },
    { label: 'Conceptual Understanding', score: evaluation.criteria_scores.conceptual_understanding },
    { label: 'Problem-Solving Approach', score: evaluation.criteria_scores.problem_solving_approach },
    { label: 'Communication Clarity', score: evaluation.criteria_scores.communication_clarity },
    { label: 'Answer Structure', score: evaluation.criteria_scores.answer_structure },
    { label: 'Relevance to Question', score: evaluation.criteria_scores.relevance },
  ];
  if (evaluation.criteria_scores.project_knowledge != null) {
    criteriaRows.push({
      label: 'Project Knowledge',
      score: evaluation.criteria_scores.project_knowledge,
    });
  }

  return (
    <div className="space-y-6">
      {/* Advisory Disclaimer Banner */}
      <div className="p-3.5 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 flex items-start gap-2.5 text-xs text-amber-900 dark:text-amber-200">
        <ShieldAlert className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
        <div>
          <strong className="font-semibold">Advisory Practice Evaluation: </strong>
          {evaluation.advisory_disclaimer}
        </div>
      </div>

      {/* Executive Score Header */}
      <Card>
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-5">
          <div className="flex items-start gap-4">
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-brand-600 to-indigo-600 text-white flex flex-col items-center justify-center shrink-0 shadow-md">
              <span className="text-2xl font-black leading-none">{Math.round(evaluation.overall_score)}</span>
              <span className="text-[10px] opacity-85 mt-1">/ 100</span>
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2 mb-1">
                <Badge variant={scoreVariant(evaluation.overall_score)}>
                  {evaluation.overall_score >= 80
                    ? 'Strong Performance'
                    : evaluation.overall_score >= 65
                    ? 'Good Foundation'
                    : evaluation.overall_score >= 50
                    ? 'Developing'
                    : 'Needs Focused Practice'}
                </Badge>
                <Badge variant="neutral" className="capitalize">
                  {session.category.replace('_', ' ')} • {session.difficulty}
                </Badge>
                {session.ai_provider && (
                  <span className="text-[11px] font-mono text-slate-400 dark:text-slate-500">
                    Engine: {session.ai_provider}
                  </span>
                )}
              </div>
              <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">
                {session.job_title
                  ? `${session.job_title}${session.company_name ? ` — ${session.company_name}` : ''}`
                  : session.target_role || 'Mock Interview Assessment'}
              </h2>
              <p className="text-xs text-slate-600 dark:text-slate-300 mt-1.5 leading-relaxed max-w-3xl">
                {evaluation.executive_summary}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <Button variant="outline" size="sm" onClick={onBackToStudio}>
              All History &amp; Analytics
            </Button>
            <Button variant="primary" size="sm" icon={<RotateCcw className="w-3.5 h-3.5" />} onClick={onStartSimilar}>
              Practice Another Round
            </Button>
          </div>
        </div>
      </Card>

      {/* 7-Criteria Breakdown + Strengths / Weaknesses */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader
            title="7-Criteria Rubric Breakdown"
            subtitle="Structured scoring across technical accuracy, reasoning, and communication"
          />
          <div className="space-y-3">
            {criteriaRows.map((row) => (
              <div key={row.label} className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-medium text-slate-700 dark:text-slate-300">{row.label}</span>
                  <span className="font-bold text-slate-900 dark:text-slate-100">{row.score.toFixed(1)}%</span>
                </div>
                <div className="w-full h-2 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${
                      row.score >= 75
                        ? 'bg-emerald-500'
                        : row.score >= 55
                        ? 'bg-brand-500'
                        : 'bg-amber-500'
                    }`}
                    style={{ width: `${Math.min(100, Math.max(0, row.score))}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader title="Key Strengths & Areas to Improve" />
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div>
                <h4 className="font-bold text-emerald-700 dark:text-emerald-400 flex items-center gap-1.5 mb-2">
                  <CheckCircle2 className="w-4 h-4" /> Strengths
                </h4>
                <ul className="space-y-1.5 text-slate-700 dark:text-slate-300">
                  {evaluation.strengths.map((s, idx) => (
                    <li key={idx} className="flex items-start gap-1.5">
                      <span className="text-emerald-500 mt-0.5">•</span>
                      <span>{s}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h4 className="font-bold text-amber-700 dark:text-amber-400 flex items-center gap-1.5 mb-2">
                  <TrendingUp className="w-4 h-4" /> Weaknesses / Gaps
                </h4>
                <ul className="space-y-1.5 text-slate-700 dark:text-slate-300">
                  {evaluation.weaknesses.map((w, idx) => (
                    <li key={idx} className="flex items-start gap-1.5">
                      <span className="text-amber-500 mt-0.5">•</span>
                      <span>{w}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </Card>

          <Card>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div>
                <h4 className="font-bold text-brand-700 dark:text-brand-400 flex items-center gap-1.5 mb-2">
                  <Lightbulb className="w-4 h-4" /> Suggested Improvements
                </h4>
                <ul className="space-y-1.5 text-slate-700 dark:text-slate-300">
                  {evaluation.suggested_improvements.map((imp, idx) => (
                    <li key={idx} className="flex items-start gap-1.5">
                      <span className="text-brand-500 mt-0.5">{idx + 1}.</span>
                      <span>{imp}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h4 className="font-bold text-indigo-700 dark:text-indigo-400 flex items-center gap-1.5 mb-2">
                  <BookOpen className="w-4 h-4" /> Recommended Topics to Study
                </h4>
                <div className="flex flex-wrap gap-1.5">
                  {evaluation.recommended_topics.map((topic, idx) => (
                    <Badge key={idx} variant="info" size="sm">
                      {topic}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>

      {/* Question-Wise Review */}
      <Card>
        <CardHeader
          title="Question-by-Question Review & Model Answers"
          subtitle="Inspect your submitted responses, rubric feedback, and advisory model explanations"
        />
        <div className="space-y-3">
          {evaluation.question_evaluations.map((qe) => {
            const isExpanded = expandedOrder === qe.question_order;
            return (
              <div
                key={qe.question_order}
                className="rounded-xl border border-slate-200 dark:border-slate-800 overflow-hidden"
              >
                <button
                  type="button"
                  onClick={() => setExpandedOrder(isExpanded ? null : qe.question_order)}
                  className="w-full px-4 py-3 bg-slate-50/70 dark:bg-slate-800/50 flex items-center justify-between gap-3 text-left hover:bg-slate-100/70 dark:hover:bg-slate-800 transition-colors"
                >
                  <div className="flex flex-wrap items-center gap-2 min-w-0">
                    <span className="text-xs font-bold text-slate-800 dark:text-slate-100">
                      Q{qe.question_order}
                    </span>
                    {qe.is_followup && (
                      <Badge variant="info" size="sm">
                        Follow-Up
                      </Badge>
                    )}
                    <span className="text-xs font-medium text-slate-700 dark:text-slate-300 truncate">
                      {qe.topic || qe.question_text}
                    </span>
                  </div>
                  <div className="flex items-center gap-2.5 shrink-0">
                    <Badge variant={scoreVariant(qe.score)} size="sm">
                      <Award className="w-3 h-3 mr-1" />
                      {qe.score.toFixed(0)} / 100
                    </Badge>
                    {isExpanded ? (
                      <ChevronUp className="w-4 h-4 text-slate-400" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-slate-400" />
                    )}
                  </div>
                </button>

                {isExpanded && (
                  <div className="p-4 space-y-4 text-xs bg-white dark:bg-slate-900">
                    {qe.question_text && (
                      <div>
                        <div className="font-semibold text-slate-500 dark:text-slate-400 uppercase text-[10px] mb-1">
                          Prompt
                        </div>
                        <p className="text-sm font-medium text-slate-900 dark:text-slate-100">
                          {qe.question_text}
                        </p>
                      </div>
                    )}

                    <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/70 border border-slate-200/80 dark:border-slate-700">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-semibold text-slate-500 dark:text-slate-400 uppercase text-[10px]">
                          Your Submitted Answer
                        </span>
                        {(qe.selected_option_key || qe.correct_option_key) && (
                          <div className="flex items-center gap-2">
                            {qe.selected_option_key === qe.correct_option_key ? (
                              <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-300">
                                ✓ Correct Choice ({qe.selected_option_key})
                              </span>
                            ) : (
                              <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold bg-rose-100 text-rose-800 dark:bg-rose-900/50 dark:text-rose-300">
                                ✗ Your Choice: {qe.selected_option_key || 'Skipped'} | Key: {qe.correct_option_key}
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                      <p className="text-slate-800 dark:text-slate-200 whitespace-pre-wrap leading-relaxed">
                        {qe.student_answer || 'No answer submitted for this prompt.'}
                      </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <div className="p-3 rounded-lg bg-brand-50/50 dark:bg-brand-950/30 border border-brand-200/60 dark:border-brand-800/60">
                        <div className="font-bold text-brand-800 dark:text-brand-300 mb-1">
                          AI Assessor Feedback
                        </div>
                        <p className="text-slate-700 dark:text-slate-300 leading-relaxed">{qe.feedback}</p>
                        <p className="mt-2 text-brand-700 dark:text-brand-300 font-medium">
                          Tip: {qe.improvement_tip}
                        </p>
                      </div>

                      <div className="p-3 rounded-lg bg-emerald-50/50 dark:bg-emerald-950/30 border border-emerald-200/60 dark:border-emerald-800/60">
                        <div className="font-bold text-emerald-800 dark:text-emerald-300 mb-1">
                          Model Answer / Explanation
                        </div>
                        <p className="text-slate-700 dark:text-slate-300 leading-relaxed">
                          {qe.model_answer}
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
};

