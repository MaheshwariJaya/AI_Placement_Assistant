import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { DashboardLayout } from '../../components/layout/DashboardLayout';
import { Card, CardHeader } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { recruiterCandidateApi } from '../../services/api';
import {
  CandidateWorkspaceDetailResponse,
  CandidateEvaluationCreate,
  CandidateNoteCreate,
  CandidateAISummary,
  EvaluationStage,
  EvaluationRecommendation,
  CandidateNoteCategory,
} from '../../types';
import {
  ArrowLeft,
  User,
  GraduationCap,
  Award,
  Briefcase,
  FileText,
  Calendar,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Star,
  Plus,
  Trash2,
  Pin,
  Sparkles,
  RefreshCw,
  ExternalLink,
  Github,
  Download,
  Building,
  Clock,
  Send,
  MessageSquare,
  ShieldCheck,
  Check,
  AlertTriangle,
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

const RECOMMENDATION_LABELS: Record<string, { label: string; variant: 'success' | 'brand' | 'warning' | 'danger' | 'neutral' }> = {
  strong_hire: { label: 'Strong Hire', variant: 'success' },
  hire: { label: 'Hire', variant: 'brand' },
  hold: { label: 'Hold', variant: 'warning' },
  no_hire: { label: 'No Hire', variant: 'danger' },
  strong_no_hire: { label: 'Strong No Hire', variant: 'danger' },
};

type ActiveTab = 'dossier' | 'compatibility' | 'evaluations' | 'notes' | 'timeline' | 'ai_synthesis';

export const CandidateWorkspacePage: React.FC = () => {
  const { applicationId } = useParams<{ applicationId: string }>();
  const navigate = useNavigate();

  const [workspace, setWorkspace] = useState<CandidateWorkspaceDetailResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<ActiveTab>('dossier');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Status transition state
  const [isTransitioning, setIsTransitioning] = useState<boolean>(false);
  const [offerModalOpen, setOfferModalOpen] = useState<boolean>(false);
  const [offerLpa, setOfferLpa] = useState<number>(12);
  const [offerDeadline, setOfferDeadline] = useState<string>('');
  const [offerNotes, setOfferNotes] = useState<string>('');

  // Evaluation form modal state
  const [evalModalOpen, setEvalModalOpen] = useState<boolean>(false);
  const [evalSubmitting, setEvalSubmitting] = useState<boolean>(false);
  const [evalStage, setEvalStage] = useState<EvaluationStage>('technical');
  const [evalTech, setEvalTech] = useState<number>(4);
  const [evalProb, setEvalProb] = useState<number>(4);
  const [evalComm, setEvalComm] = useState<number>(4);
  const [evalProj, setEvalProj] = useState<number>(4);
  const [evalCulture, setEvalCulture] = useState<number>(4);
  const [evalOverall, setEvalOverall] = useState<number>(4);
  const [evalRec, setEvalRec] = useState<EvaluationRecommendation>('hire');
  const [evalFeedback, setEvalFeedback] = useState<string>('');
  const [evalStrengthInput, setEvalStrengthInput] = useState<string>('');
  const [evalWeaknessInput, setEvalWeaknessInput] = useState<string>('');

  // Note form state
  const [noteContent, setNoteContent] = useState<string>('');
  const [noteCategory, setNoteCategory] = useState<CandidateNoteCategory>('general');
  const [notePinned, setNotePinned] = useState<boolean>(false);
  const [noteSubmitting, setNoteSubmitting] = useState<boolean>(false);

  // AI summary state
  const [aiSummary, setAiSummary] = useState<CandidateAISummary | null>(null);
  const [aiGenerating, setAiGenerating] = useState<boolean>(false);

  const loadWorkspace = useCallback(async () => {
    if (!applicationId) return;
    setLoading(true);
    setErrorMsg(null);
    try {
      const data = await recruiterCandidateApi.getCandidateWorkspace(Number(applicationId));
      setWorkspace(data);
    } catch (err: any) {
      console.error('Failed to load candidate workspace', err);
      setErrorMsg(err?.response?.data?.detail || 'Failed to load candidate evaluation workspace.');
    } finally {
      setLoading(false);
    }
  }, [applicationId]);

  useEffect(() => {
    loadWorkspace();
  }, [loadWorkspace]);

  // Handle status transition
  const handleStatusChange = async (
    toStatus: string,
    decisionNotes?: string,
    extra?: { offer_package_lpa?: number; offer_deadline_at?: string; offer_notes?: string }
  ) => {
    if (!applicationId) return;
    setIsTransitioning(true);
    setErrorMsg(null);
    try {
      await recruiterCandidateApi.transitionStatus(Number(applicationId), {
        to_status: toStatus,
        decision_notes: decisionNotes,
        ...extra,
      });
      await loadWorkspace();
      setOfferModalOpen(false);
    } catch (err: any) {
      console.error('Status transition failed', err);
      setErrorMsg(err?.response?.data?.detail || 'Status transition failed.');
    } finally {
      setIsTransitioning(false);
    }
  };

  // Handle evaluation submission
  const handleSubmitEvaluation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!applicationId || !evalFeedback.trim()) return;
    setEvalSubmitting(true);
    try {
      const payload: CandidateEvaluationCreate = {
        stage: evalStage,
        technical_proficiency: evalTech,
        problem_solving: evalProb,
        communication: evalComm,
        project_depth: evalProj,
        cultural_fit: evalCulture,
        overall_rating: evalOverall,
        recommendation: evalRec,
        written_feedback: evalFeedback.trim(),
        strengths: evalStrengthInput
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean),
        weaknesses: evalWeaknessInput
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean),
      };
      await recruiterCandidateApi.submitEvaluation(Number(applicationId), payload);
      setEvalModalOpen(false);
      setEvalFeedback('');
      setEvalStrengthInput('');
      setEvalWeaknessInput('');
      await loadWorkspace();
    } catch (err: any) {
      console.error('Evaluation submit failed', err);
      alert(err?.response?.data?.detail || 'Failed to submit evaluation.');
    } finally {
      setEvalSubmitting(false);
    }
  };

  // Handle Note Creation
  const handleCreateNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!applicationId || !noteContent.trim()) return;
    setNoteSubmitting(true);
    try {
      const payload: CandidateNoteCreate = {
        category: noteCategory,
        content: noteContent.trim(),
        is_pinned: notePinned,
      };
      await recruiterCandidateApi.createNote(Number(applicationId), payload);
      setNoteContent('');
      setNotePinned(false);
      await loadWorkspace();
    } catch (err: any) {
      console.error('Failed to create note', err);
      alert(err?.response?.data?.detail || 'Failed to create note.');
    } finally {
      setNoteSubmitting(false);
    }
  };

  // Handle Note Deletion
  const handleDeleteNote = async (noteId: number) => {
    if (!applicationId || !window.confirm('Delete this recruiter note?')) return;
    try {
      await recruiterCandidateApi.deleteNote(Number(applicationId), noteId);
      await loadWorkspace();
    } catch (err: any) {
      console.error('Failed to delete note', err);
      alert(err?.response?.data?.detail || 'Failed to delete note.');
    }
  };

  // Handle AI Summary Generation
  const handleGenerateAiSummary = async () => {
    if (!applicationId) return;
    setAiGenerating(true);
    try {
      const res = await recruiterCandidateApi.generateAISummary(Number(applicationId));
      setAiSummary(res);
    } catch (err: any) {
      console.error('AI summary generation failed', err);
      alert(err?.response?.data?.detail || 'Failed to generate AI evaluation synthesis.');
    } finally {
      setAiGenerating(false);
    }
  };

  if (loading) {
    return (
      <DashboardLayout
        role="recruiter"
        title="Candidate Evaluation Workspace"
        subtitle="Loading candidate dossier and scorecards..."
      >
        <div className="py-20 text-center text-slate-500">
          <RefreshCw className="w-8 h-8 animate-spin mx-auto text-sky-500 mb-3" />
          <p className="font-semibold text-sm">Loading candidate evaluation workspace...</p>
        </div>
      </DashboardLayout>
    );
  }

  if (!workspace) {
    return (
      <DashboardLayout
        role="recruiter"
        title="Candidate Evaluation Workspace"
        subtitle="Candidate application details"
      >
        <div className="py-20 text-center text-slate-500">
          <AlertCircle className="w-10 h-10 text-rose-500 mx-auto mb-3" />
          <p className="font-bold text-base text-slate-800 dark:text-slate-200">Candidate Not Found</p>
          <p className="text-xs text-slate-500 mt-1">{errorMsg || 'The requested application could not be loaded.'}</p>
          <Button
            size="sm"
            variant="outline"
            className="mt-4"
            onClick={() => navigate('/recruiter/candidates')}
            icon={<ArrowLeft className="w-3.5 h-3.5" />}
          >
            Back to Candidate Pipeline
          </Button>
        </div>
      </DashboardLayout>
    );
  }

  const {
    job_title,
    company_name,
    is_campus_drive_application,
    drive_name,
    tpo_screening_status,
    current_status,
    compatibility_score,
    score_breakdown,
    eligibility_checklist,
    profile,
    academics,
    skills,
    projects,
    experiences,
    certifications,
    resume,
    evaluations,
    notes,
    activity_timeline,
  } = workspace;

  const candidateName = String(profile?.full_name || 'Candidate');
  const candidateEmail = String(profile?.email || '');
  const candidateRoll = String(profile?.roll_number || '');
  const candidateDept = String(profile?.department || 'General');
  const candidateBatch = Number(profile?.graduation_year || 2026);

  // Campus drive shortlisting restriction check
  const isCampusDrivePending =
    is_campus_drive_application &&
    (tpo_screening_status === 'pending' || tpo_screening_status === 'rejected');

  const compatScore = Math.round(compatibility_score || 0);

  return (
    <DashboardLayout
      role="recruiter"
      title="Candidate Evaluation Workspace"
      subtitle={`Evaluating ${candidateName} for ${job_title} at ${company_name}`}
    >
      {/* Back button & Breadcrumb */}
      <div className="flex items-center justify-between mb-4">
        <button
          onClick={() => navigate('/recruiter/candidates')}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 dark:text-slate-400 hover:text-sky-600 dark:hover:text-sky-400 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to Candidate Pipeline
        </button>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={loadWorkspace}
            icon={<RefreshCw className="w-3.5 h-3.5" />}
          >
            Refresh
          </Button>
        </div>
      </div>

      {errorMsg && (
        <div className="mb-4 p-3 rounded-lg bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Main Candidate Header Card */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-xl p-5 mb-6 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          {/* Candidate Primary Info */}
          <div className="flex items-start gap-4">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-sky-500 to-indigo-600 text-white flex items-center justify-center font-bold text-xl shadow-md flex-shrink-0">
              {candidateName.charAt(0)}
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2.5">
                <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">
                  {candidateName}
                </h2>
                <Badge variant={STATUS_BADGE_VARIANTS[current_status] || 'neutral'}>
                  {current_status.replace(/_/g, ' ').toUpperCase()}
                </Badge>
                {eligibility_checklist.is_eligible ? (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800">
                    <CheckCircle2 className="w-3 h-3" />
                    Eligible
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-rose-50 dark:bg-rose-950/60 text-rose-600 dark:text-rose-400 border border-rose-200 dark:border-rose-800">
                    <XCircle className="w-3 h-3" />
                    Ineligible
                  </span>
                )}
              </div>

              <div className="text-xs text-slate-500 dark:text-slate-400 mt-1 flex flex-wrap items-center gap-x-3 gap-y-1">
                <span>Roll: {candidateRoll}</span>
                <span>•</span>
                <span>Dept: {candidateDept}</span>
                <span>•</span>
                <span>Batch: {candidateBatch}</span>
                <span>•</span>
                <span>CGPA: {Number(academics.cgpa).toFixed(2)}</span>
              </div>

              {is_campus_drive_application && (
                <div className="mt-2 text-xs flex items-center gap-2 text-slate-600 dark:text-slate-400">
                  <span className="px-2 py-0.5 rounded bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 font-semibold border border-indigo-200 dark:border-indigo-800">
                    Campus Drive: {drive_name || 'Active Drive'}
                  </span>
                  <span>
                    TPO Screening:{' '}
                    <strong className="uppercase">{tpo_screening_status}</strong>
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Compatibility Pill & Quick Human Decision Actions */}
          <div className="flex flex-col sm:flex-row sm:items-center gap-3">
            <div className="flex items-center gap-2.5 px-4 py-2.5 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
              <Award className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
              <div>
                <div className="text-[11px] uppercase tracking-wider font-semibold text-slate-400">
                  Compatibility Score
                </div>
                <div className="text-lg font-bold text-slate-900 dark:text-slate-100">
                  {compatScore}%
                </div>
              </div>
            </div>

            {/* Decision Actions */}
            <div className="flex flex-wrap items-center gap-2">
              {current_status === 'applied' && (
                <Button
                  size="sm"
                  variant="primary"
                  disabled={isTransitioning || isCampusDrivePending}
                  onClick={() => handleStatusChange('shortlisted', 'Candidate shortlisted for interview round.')}
                >
                  Shortlist Candidate
                </Button>
              )}

              {['shortlisted', 'applied'].includes(current_status) && (
                <Button
                  size="sm"
                  variant="outline"
                  disabled={isTransitioning || isCampusDrivePending}
                  onClick={() =>
                    handleStatusChange('interview_scheduled', 'Interview round scheduled by recruiter.')
                  }
                >
                  Schedule Interview
                </Button>
              )}

              {['shortlisted', 'interview_scheduled', 'interview_completed'].includes(current_status) && (
                <Button
                  size="sm"
                  variant="primary"
                  className="bg-emerald-600 hover:bg-emerald-700 text-white"
                  disabled={isTransitioning}
                  onClick={() => setOfferModalOpen(true)}
                >
                  Extend Job Offer
                </Button>
              )}

              {current_status !== 'rejected' && current_status !== 'offer_accepted' && (
                <Button
                  size="sm"
                  variant="danger"
                  disabled={isTransitioning}
                  onClick={() => {
                    const notes = prompt('Enter rejection feedback (optional):');
                    if (notes !== null) {
                      handleStatusChange('rejected', notes || 'Application not selected for advancement.');
                    }
                  }}
                >
                  Reject
                </Button>
              )}
            </div>
          </div>
        </div>

        {isCampusDrivePending && (
          <div className="mt-4 p-3 rounded-lg bg-amber-50 dark:bg-amber-950/60 border border-amber-200 dark:border-amber-800 text-amber-800 dark:text-amber-200 text-xs flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 flex-shrink-0" />
            <span>
              <strong>Campus Drive Screening Gate:</strong> This candidate was submitted through an institutional campus drive ({drive_name}). TPO screening is currently <strong>{tpo_screening_status.toUpperCase()}</strong>. Recruiter advancement is blocked until the TPO marks the candidate as shortlisted.
            </span>
          </div>
        )}
      </div>

      {/* Tabs Navigation */}
      <div className="flex border-b border-slate-200 dark:border-slate-800 mb-6 gap-2 overflow-x-auto text-xs">
        <button
          onClick={() => setActiveTab('dossier')}
          className={`py-2.5 px-4 font-semibold border-b-2 flex items-center gap-2 transition-colors whitespace-nowrap ${
            activeTab === 'dossier'
              ? 'border-sky-600 text-sky-600 dark:text-sky-400'
              : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
          }`}
        >
          <User className="w-4 h-4" />
          Candidate Dossier
        </button>

        <button
          onClick={() => setActiveTab('compatibility')}
          className={`py-2.5 px-4 font-semibold border-b-2 flex items-center gap-2 transition-colors whitespace-nowrap ${
            activeTab === 'compatibility'
              ? 'border-sky-600 text-sky-600 dark:text-sky-400'
              : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
          }`}
        >
          <ShieldCheck className="w-4 h-4" />
          Compatibility & Eligibility ({compatScore}%)
        </button>

        <button
          onClick={() => setActiveTab('evaluations')}
          className={`py-2.5 px-4 font-semibold border-b-2 flex items-center gap-2 transition-colors whitespace-nowrap ${
            activeTab === 'evaluations'
              ? 'border-sky-600 text-sky-600 dark:text-sky-400'
              : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
          }`}
        >
          <Star className="w-4 h-4" />
          Interview Evaluations ({evaluations.length})
        </button>

        <button
          onClick={() => setActiveTab('notes')}
          className={`py-2.5 px-4 font-semibold border-b-2 flex items-center gap-2 transition-colors whitespace-nowrap ${
            activeTab === 'notes'
              ? 'border-sky-600 text-sky-600 dark:text-sky-400'
              : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
          }`}
        >
          <MessageSquare className="w-4 h-4" />
          Internal Recruiter Notes ({notes.length})
        </button>

        <button
          onClick={() => setActiveTab('timeline')}
          className={`py-2.5 px-4 font-semibold border-b-2 flex items-center gap-2 transition-colors whitespace-nowrap ${
            activeTab === 'timeline'
              ? 'border-sky-600 text-sky-600 dark:text-sky-400'
              : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
          }`}
        >
          <History className="w-4 h-4" />
          Activity Audit History
        </button>

        <button
          onClick={() => setActiveTab('ai_synthesis')}
          className={`py-2.5 px-4 font-semibold border-b-2 flex items-center gap-2 transition-colors whitespace-nowrap ${
            activeTab === 'ai_synthesis'
              ? 'border-sky-600 text-sky-600 dark:text-sky-400'
              : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
          }`}
        >
          <Sparkles className="w-4 h-4 text-amber-500" />
          AI Talent Synthesis
        </button>
      </div>

      {/* TAB 1: CANDIDATE DOSSIER */}
      {activeTab === 'dossier' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Academics & Resume */}
          <div className="space-y-6">
            {/* Verified Academics Card */}
            <Card>
              <CardHeader
                title="Verified Academic Record"
                subtitle="Institutionally verified metrics"
              />
              <div className="mt-4 space-y-3 text-xs">
                <div className="flex justify-between items-center py-1.5 border-b border-slate-100 dark:border-slate-800">
                  <span className="text-slate-500">Current CGPA</span>
                  <span className="font-bold text-slate-900 dark:text-slate-100 text-sm">
                    {Number(academics.cgpa).toFixed(2)} / 10.0
                  </span>
                </div>
                <div className="flex justify-between items-center py-1.5 border-b border-slate-100 dark:border-slate-800">
                  <span className="text-slate-500">Class X Score</span>
                  <span className="font-semibold text-slate-800 dark:text-slate-200">
                    {academics.tenth_percentage ? `${academics.tenth_percentage}%` : '—'}
                  </span>
                </div>
                <div className="flex justify-between items-center py-1.5 border-b border-slate-100 dark:border-slate-800">
                  <span className="text-slate-500">Class XII / Diploma</span>
                  <span className="font-semibold text-slate-800 dark:text-slate-200">
                    {academics.twelfth_percentage ? `${academics.twelfth_percentage}%` : '—'}
                  </span>
                </div>
                <div className="flex justify-between items-center py-1.5 border-b border-slate-100 dark:border-slate-800">
                  <span className="text-slate-500">Active Backlogs</span>
                  <span
                    className={`font-semibold ${
                      academics.active_backlogs > 0 ? 'text-rose-600 font-bold' : 'text-slate-800 dark:text-slate-200'
                    }`}
                  >
                    {academics.active_backlogs}
                  </span>
                </div>
                <div className="flex justify-between items-center py-1.5 border-b border-slate-100 dark:border-slate-800">
                  <span className="text-slate-500">Total Historic Backlogs</span>
                  <span className="font-semibold text-slate-800 dark:text-slate-200">
                    {academics.total_backlogs}
                  </span>
                </div>
                <div className="flex justify-between items-center py-1.5">
                  <span className="text-slate-500">Placement Readiness</span>
                  <Badge variant={academics.is_placement_ready ? 'success' : 'warning'}>
                    {academics.is_placement_ready ? 'Ready' : 'Pending Verification'}
                  </Badge>
                </div>
              </div>
            </Card>

            {/* Resume Card */}
            <Card>
              <CardHeader
                title="Submitted Resume"
                subtitle="Applicant document dossier"
              />
              <div className="mt-4 text-xs">
                {resume ? (
                  <div className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <FileText className="w-5 h-5 text-sky-600 dark:text-sky-400" />
                        <div>
                          <div className="font-semibold text-slate-900 dark:text-slate-100">
                            {resume.file_name}
                          </div>
                          <div className="text-[11px] text-slate-500">
                            {resume.file_type || 'PDF'}
                            {resume.file_size_bytes
                              ? ` • ${(resume.file_size_bytes / 1024).toFixed(1)} KB`
                              : ''}
                          </div>
                        </div>
                      </div>
                      {resume.resume_score && (
                        <span className="px-2 py-1 rounded bg-sky-100 dark:bg-sky-900 text-sky-800 dark:text-sky-200 font-bold text-xs">
                          {Math.round(resume.resume_score)} ATS
                        </span>
                      )}
                    </div>
                    {resume.download_url && (
                      <a
                        href={resume.download_url}
                        target="_blank"
                        rel="noreferrer"
                        className="mt-3 inline-flex items-center gap-1.5 text-sky-600 dark:text-sky-400 font-semibold hover:underline text-xs"
                      >
                        <Download className="w-3.5 h-3.5" />
                        Download PDF Resume
                      </a>
                    )}
                  </div>
                ) : (
                  <p className="text-slate-400 italic">No structured resume attached.</p>
                )}
              </div>
            </Card>

            {/* Candidate Online Links */}
            <Card>
              <CardHeader title="Online Profiles" subtitle="External portfolios & codebases" />
              <div className="mt-3 space-y-2 text-xs">
                {profile?.github_url ? (
                  <a
                    href={String(profile.github_url)}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-2 text-slate-700 dark:text-slate-300 hover:text-sky-600 p-2 rounded border border-slate-100 dark:border-slate-800"
                  >
                    <Github className="w-4 h-4" />
                    <span className="truncate">{String(profile.github_url)}</span>
                  </a>
                ) : null}
                {profile?.linkedin_url ? (
                  <a
                    href={String(profile.linkedin_url)}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-2 text-slate-700 dark:text-slate-300 hover:text-sky-600 p-2 rounded border border-slate-100 dark:border-slate-800"
                  >
                    <ExternalLink className="w-4 h-4" />
                    <span className="truncate">{String(profile.linkedin_url)}</span>
                  </a>
                ) : null}
                {profile?.portfolio_url ? (
                  <a
                    href={String(profile.portfolio_url)}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-2 text-slate-700 dark:text-slate-300 hover:text-sky-600 p-2 rounded border border-slate-100 dark:border-slate-800"
                  >
                    <ExternalLink className="w-4 h-4" />
                    <span className="truncate">{String(profile.portfolio_url)}</span>
                  </a>
                ) : null}
                {!profile?.github_url && !profile?.linkedin_url && !profile?.portfolio_url && (
                  <p className="text-slate-400 italic">No external URLs provided.</p>
                )}
              </div>
            </Card>
          </div>

          {/* Right Column: Skills, Projects, Experience, Certifications */}
          <div className="lg:col-span-2 space-y-6">
            {/* Skills Card */}
            <Card>
              <CardHeader
                title="Skills & Technical Proficiency"
                subtitle="Confirmed and institutionally verified competencies"
              />
              <div className="mt-4 flex flex-wrap gap-2 text-xs">
                {skills.length === 0 ? (
                  <p className="text-slate-400 italic">No skills listed in profile.</p>
                ) : (
                  skills.map((s, idx) => (
                    <div
                      key={idx}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 shadow-sm"
                    >
                      <span className="font-semibold text-slate-900 dark:text-slate-100">
                        {s.skill_name}
                      </span>
                      <span className="text-[10px] text-slate-400 uppercase tracking-wider">
                        ({s.proficiency_level})
                      </span>
                      {s.is_verified && (
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0" />
                      )}
                    </div>
                  ))
                )}
              </div>
            </Card>

            {/* Technical Projects */}
            <Card>
              <CardHeader
                title="Technical Projects"
                subtitle="Demonstrated engineering capability & architecture"
              />
              <div className="mt-4 space-y-4 text-xs">
                {projects.length === 0 ? (
                  <p className="text-slate-400 italic">No projects recorded.</p>
                ) : (
                  projects.map((p, idx) => (
                    <div
                      key={idx}
                      className="p-4 rounded-xl border border-slate-200 dark:border-slate-700/80 bg-slate-50/50 dark:bg-slate-800/40"
                    >
                      <div className="flex items-center justify-between">
                        <h4 className="font-bold text-slate-900 dark:text-slate-100 text-sm">
                          {p.title}
                        </h4>
                        <div className="flex items-center gap-2">
                          {p.repo_url && (
                            <a
                              href={p.repo_url}
                              target="_blank"
                              rel="noreferrer"
                              className="inline-flex items-center gap-1 text-sky-600 dark:text-sky-400 hover:underline font-semibold"
                            >
                              <Github className="w-3.5 h-3.5" />
                              Repo
                            </a>
                          )}
                          {p.demo_url && (
                            <a
                              href={p.demo_url}
                              target="_blank"
                              rel="noreferrer"
                              className="inline-flex items-center gap-1 text-sky-600 dark:text-sky-400 hover:underline font-semibold"
                            >
                              <ExternalLink className="w-3.5 h-3.5" />
                              Live Demo
                            </a>
                          )}
                        </div>
                      </div>
                      <p className="text-slate-600 dark:text-slate-300 mt-2 leading-relaxed">
                        {p.description || 'No detailed description provided.'}
                      </p>
                      {p.technologies && p.technologies.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 mt-3">
                          {p.technologies.map((t, tidx) => (
                            <span
                              key={tidx}
                              className="px-2 py-0.5 rounded bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 text-[11px] font-medium"
                            >
                              {t}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </Card>

            {/* Work & Internship Experience */}
            <Card>
              <CardHeader
                title="Work & Internship Experience"
                subtitle="Practical industry background"
              />
              <div className="mt-4 space-y-4 text-xs">
                {experiences.length === 0 ? (
                  <p className="text-slate-400 italic">No professional experiences listed.</p>
                ) : (
                  experiences.map((exp, idx) => (
                    <div
                      key={idx}
                      className="p-4 rounded-xl border border-slate-200 dark:border-slate-700/80 bg-slate-50/50 dark:bg-slate-800/40"
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <h4 className="font-bold text-slate-900 dark:text-slate-100 text-sm">
                            {exp.job_title}
                          </h4>
                          <div className="text-slate-600 dark:text-slate-400 font-medium">
                            {exp.company_name}
                          </div>
                        </div>
                        <span className="text-slate-500 font-mono text-[11px]">
                          {exp.start_date || 'Start'} — {exp.is_current ? 'Present' : exp.end_date || 'End'}
                        </span>
                      </div>
                      {exp.description && (
                        <p className="text-slate-600 dark:text-slate-300 mt-2 leading-relaxed">
                          {exp.description}
                        </p>
                      )}
                    </div>
                  ))
                )}
              </div>
            </Card>

            {/* Certifications */}
            <Card>
              <CardHeader
                title="Professional Certifications"
                subtitle="External credentials and licenses"
              />
              <div className="mt-4 space-y-3 text-xs">
                {certifications.length === 0 ? (
                  <p className="text-slate-400 italic">No certifications listed.</p>
                ) : (
                  certifications.map((c, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between p-3 rounded-lg border border-slate-100 dark:border-slate-800"
                    >
                      <div>
                        <div className="font-semibold text-slate-900 dark:text-slate-100">
                          {c.name}
                        </div>
                        <div className="text-slate-500">
                          {c.issuing_organization} {c.issue_date ? `• Issued ${c.issue_date}` : ''}
                        </div>
                      </div>
                      {c.credential_url && (
                        <a
                          href={c.credential_url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-sky-600 dark:text-sky-400 hover:underline inline-flex items-center gap-1 font-semibold"
                        >
                          Verify <ExternalLink className="w-3 h-3" />
                        </a>
                      )}
                    </div>
                  ))
                )}
              </div>
            </Card>
          </div>
        </div>
      )}

      {/* TAB 2: COMPATIBILITY & ELIGIBILITY */}
      {activeTab === 'compatibility' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Deterministic Compatibility Breakdown */}
          <Card>
            <CardHeader
              title="Deterministic Compatibility Score Breakdown"
              subtitle="Mathematical score computed from verified job requirements"
            />
            <div className="mt-4 space-y-4 text-xs">
              <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 flex items-center justify-between">
                <div>
                  <div className="text-xs uppercase tracking-wider font-semibold text-slate-500">
                    Aggregate Compatibility
                  </div>
                  <div className="text-3xl font-bold text-slate-900 dark:text-slate-100 mt-1">
                    {compatScore}%
                  </div>
                  <p className="text-[11px] text-slate-500 mt-1">
                    Weighted across skills matching, academic benchmarks, and project depth.
                  </p>
                </div>
                <div className="w-16 h-16 rounded-full bg-indigo-50 dark:bg-indigo-950 flex items-center justify-center border-2 border-indigo-500 font-bold text-lg text-indigo-600 dark:text-indigo-400">
                  {compatScore}
                </div>
              </div>

              {score_breakdown && (
                <div className="space-y-3 pt-2">
                  <h4 className="font-semibold text-slate-800 dark:text-slate-200">
                    Component Breakdown
                  </h4>
                  {Object.entries(score_breakdown).map(([k, v]) => (
                    <div
                      key={k}
                      className="flex items-center justify-between p-2.5 rounded-lg border border-slate-100 dark:border-slate-800"
                    >
                      <span className="capitalize text-slate-600 dark:text-slate-400">
                        {k.replace(/_/g, ' ')}
                      </span>
                      <span className="font-bold text-slate-900 dark:text-slate-100">
                        {typeof v === 'number' ? `${v.toFixed(1)}%` : String(v)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </Card>

          {/* Pass/Fail Eligibility Checklist */}
          <Card>
            <CardHeader
              title="Pass/Fail Academic Eligibility Checklist"
              subtitle="Authoritative criteria verified deterministically against institutional policies"
            />
            <div className="mt-4 space-y-3 text-xs">
              <div
                className={`p-3.5 rounded-xl border flex items-center gap-3 ${
                  eligibility_checklist.is_eligible
                    ? 'bg-emerald-50 dark:bg-emerald-950/50 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-200'
                    : 'bg-rose-50 dark:bg-rose-950/50 border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-200'
                }`}
              >
                {eligibility_checklist.is_eligible ? (
                  <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
                ) : (
                  <XCircle className="w-5 h-5 flex-shrink-0" />
                )}
                <div>
                  <div className="font-bold">
                    {eligibility_checklist.is_eligible
                      ? 'Candidate Meets All Job Eligibility Cutoffs'
                      : 'Candidate Failed One or More Eligibility Cutoffs'}
                  </div>
                  <div className="text-[11px] opacity-90 mt-0.5">
                    {eligibility_checklist.reasons?.join(', ') || 'Evaluated against job rules.'}
                  </div>
                </div>
              </div>

              <div className="space-y-2 pt-2">
                <h4 className="font-semibold text-slate-800 dark:text-slate-200">
                  Individual Verification Rules
                </h4>
                {eligibility_checklist.criteria?.map((crit, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex items-center justify-between"
                  >
                    <div className="flex items-center gap-2.5">
                      {crit.status === 'passed' ? (
                        <Check className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                      ) : crit.status === 'failed' ? (
                        <XCircle className="w-4 h-4 text-rose-600 flex-shrink-0" />
                      ) : (
                        <AlertCircle className="w-4 h-4 text-slate-400 flex-shrink-0" />
                      )}
                      <div>
                        <div className="font-semibold text-slate-900 dark:text-slate-100">
                          {crit.criterion}
                        </div>
                        <div className="text-[11px] text-slate-500">
                          Candidate: {crit.candidate_value} • Required: {crit.required_value}
                        </div>
                      </div>
                    </div>
                    <Badge variant={crit.status === 'passed' ? 'success' : crit.status === 'failed' ? 'danger' : 'neutral'}>
                      {crit.status.toUpperCase()}
                    </Badge>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* TAB 3: INTERVIEW EVALUATIONS */}
      {activeTab === 'evaluations' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                Interviewer Scorecards & Feedback
              </h3>
              <p className="text-xs text-slate-500">
                Multiple interviewers, structured evaluations, and recommendations.
              </p>
            </div>
            <Button
              size="sm"
              variant="primary"
              onClick={() => setEvalModalOpen(true)}
              icon={<Plus className="w-3.5 h-3.5" />}
            >
              Submit Evaluation
            </Button>
          </div>

          {evaluations.length === 0 ? (
            <Card>
              <div className="py-12 text-center text-slate-400">
                <Star className="w-8 h-8 mx-auto text-slate-300 dark:text-slate-600 mb-2" />
                <p className="font-semibold text-slate-700 dark:text-slate-300 text-xs">
                  No evaluations submitted yet
                </p>
                <p className="text-[11px] text-slate-500 mt-1">
                  Click "Submit Evaluation" to log feedback for this candidate.
                </p>
              </div>
            </Card>
          ) : (
            evaluations.map((ev) => (
              <Card key={ev.id}>
                <div className="p-4 border-b border-slate-100 dark:border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-slate-900 dark:text-slate-100 text-sm">
                        {ev.interviewer_name}
                      </span>
                      <span className="px-2 py-0.5 rounded bg-sky-50 dark:bg-sky-950 text-sky-700 dark:text-sky-300 uppercase tracking-wider font-semibold text-[10px]">
                        {ev.stage}
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-500 mt-0.5">
                      Submitted: {new Date(ev.created_at).toLocaleString()}
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-amber-50 dark:bg-amber-950 text-amber-800 dark:text-amber-200 font-bold text-xs">
                      <Star className="w-4 h-4 fill-amber-400 text-amber-400" />
                      {Number(ev.overall_rating).toFixed(1)} / 5.0
                    </div>
                    {RECOMMENDATION_LABELS[ev.recommendation] && (
                      <Badge variant={RECOMMENDATION_LABELS[ev.recommendation].variant}>
                        {RECOMMENDATION_LABELS[ev.recommendation].label}
                      </Badge>
                    )}
                  </div>
                </div>

                <div className="p-4 space-y-4 text-xs">
                  {/* Rating Breakdown Grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-center">
                    <div className="p-2 rounded bg-slate-50 dark:bg-slate-800">
                      <div className="text-[10px] text-slate-400">Technical</div>
                      <div className="font-bold text-slate-900 dark:text-slate-100 mt-0.5">
                        {ev.technical_proficiency ?? '—'}/5
                      </div>
                    </div>
                    <div className="p-2 rounded bg-slate-50 dark:bg-slate-800">
                      <div className="text-[10px] text-slate-400">Problem Solving</div>
                      <div className="font-bold text-slate-900 dark:text-slate-100 mt-0.5">
                        {ev.problem_solving ?? '—'}/5
                      </div>
                    </div>
                    <div className="p-2 rounded bg-slate-50 dark:bg-slate-800">
                      <div className="text-[10px] text-slate-400">Communication</div>
                      <div className="font-bold text-slate-900 dark:text-slate-100 mt-0.5">
                        {ev.communication ?? '—'}/5
                      </div>
                    </div>
                    <div className="p-2 rounded bg-slate-50 dark:bg-slate-800">
                      <div className="text-[10px] text-slate-400">Project Depth</div>
                      <div className="font-bold text-slate-900 dark:text-slate-100 mt-0.5">
                        {ev.project_depth ?? '—'}/5
                      </div>
                    </div>
                    <div className="p-2 rounded bg-slate-50 dark:bg-slate-800">
                      <div className="text-[10px] text-slate-400">Cultural Fit</div>
                      <div className="font-bold text-slate-900 dark:text-slate-100 mt-0.5">
                        {ev.cultural_fit ?? '—'}/5
                      </div>
                    </div>
                  </div>

                  {/* Written Feedback */}
                  <div>
                    <h5 className="font-semibold text-slate-800 dark:text-slate-200 mb-1">
                      Written Qualitative Feedback
                    </h5>
                    <p className="text-slate-700 dark:text-slate-300 leading-relaxed p-3 rounded-lg bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-800">
                      {ev.written_feedback}
                    </p>
                  </div>

                  {/* Strengths & Weaknesses */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <h5 className="font-semibold text-emerald-700 dark:text-emerald-400 mb-1">
                        Strengths Identified
                      </h5>
                      <div className="flex flex-wrap gap-1.5">
                        {ev.strengths?.length ? (
                          ev.strengths.map((s, sidx) => (
                            <span
                              key={sidx}
                              className="px-2 py-0.5 rounded bg-emerald-50 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 font-medium text-[11px]"
                            >
                              {s}
                            </span>
                          ))
                        ) : (
                          <span className="text-slate-400 italic">None noted</span>
                        )}
                      </div>
                    </div>

                    <div>
                      <h5 className="font-semibold text-rose-700 dark:text-rose-400 mb-1">
                        Areas for Development
                      </h5>
                      <div className="flex flex-wrap gap-1.5">
                        {ev.weaknesses?.length ? (
                          ev.weaknesses.map((w, widx) => (
                            <span
                              key={widx}
                              className="px-2 py-0.5 rounded bg-rose-50 dark:bg-rose-950 text-rose-700 dark:text-rose-300 font-medium text-[11px]"
                            >
                              {w}
                            </span>
                          ))
                        ) : (
                          <span className="text-slate-400 italic">None noted</span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </Card>
            ))
          )}
        </div>
      )}

      {/* TAB 4: INTERNAL NOTES */}
      {activeTab === 'notes' && (
        <div className="space-y-6">
          {/* Note Input Card */}
          <Card>
            <CardHeader
              title="Add Confidential Recruiter Note"
              subtitle="Notes are strictly internal to company recruiters and NEVER shared with candidate."
            />
            <form onSubmit={handleCreateNote} className="mt-3 space-y-3 text-xs">
              <textarea
                rows={3}
                placeholder="Write interview observations, compensation considerations, or hiring thoughts..."
                value={noteContent}
                onChange={(e) => setNoteContent(e.target.value)}
                required
                className="w-full p-3 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-1 focus:ring-sky-500 text-xs"
              />

              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <select
                    value={noteCategory}
                    onChange={(e) => setNoteCategory(e.target.value as CandidateNoteCategory)}
                    className="py-1 px-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200 text-xs"
                  >
                    <option value="general">General</option>
                    <option value="interview">Interview</option>
                    <option value="compensation">Compensation</option>
                    <option value="decision">Decision</option>
                    <option value="reference">Reference</option>
                  </select>

                  <label className="flex items-center gap-1.5 cursor-pointer text-slate-700 dark:text-slate-300">
                    <input
                      type="checkbox"
                      checked={notePinned}
                      onChange={(e) => setNotePinned(e.target.checked)}
                      className="rounded text-sky-600 focus:ring-sky-500"
                    />
                    <Pin className="w-3.5 h-3.5 text-amber-500" />
                    <span>Pin to top</span>
                  </label>
                </div>

                <Button
                  size="sm"
                  variant="primary"
                  type="submit"
                  disabled={noteSubmitting || !noteContent.trim()}
                  icon={<Send className="w-3.5 h-3.5" />}
                >
                  Save Note
                </Button>
              </div>
            </form>
          </Card>

          {/* Notes List */}
          <div className="space-y-3">
            {notes.length === 0 ? (
              <p className="text-slate-400 italic text-xs py-4 text-center">
                No recruiter notes created yet.
              </p>
            ) : (
              notes.map((n) => (
                <div
                  key={n.id}
                  className={`p-4 rounded-xl border text-xs transition-colors ${
                    n.is_pinned
                      ? 'bg-amber-50/50 dark:bg-amber-950/20 border-amber-200 dark:border-amber-800/60'
                      : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {n.is_pinned && <Pin className="w-3.5 h-3.5 text-amber-500 flex-shrink-0" />}
                      <span className="font-bold text-slate-900 dark:text-slate-100">
                        {n.author_name}
                      </span>
                      <span className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 uppercase tracking-wider text-[10px] font-semibold">
                        {n.category}
                      </span>
                      <span className="text-slate-400 text-[11px]">
                        • {new Date(n.created_at).toLocaleString()}
                      </span>
                    </div>

                    <button
                      onClick={() => handleDeleteNote(n.id)}
                      className="text-slate-400 hover:text-rose-500 p-1 transition-colors"
                      title="Delete note"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                  <p className="mt-2 text-slate-700 dark:text-slate-300 leading-relaxed whitespace-pre-wrap">
                    {n.content}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* TAB 5: ACTIVITY AUDIT TIMELINE */}
      {activeTab === 'timeline' && (
        <Card>
          <CardHeader
            title="Recruitment Activity Audit Trail"
            subtitle="Chronological sequence of all interactions, transitions, and evaluations"
          />
          <div className="mt-6 pl-4 border-l-2 border-slate-200 dark:border-slate-700 space-y-6 text-xs">
            {activity_timeline.length === 0 ? (
              <p className="text-slate-400 italic">No events recorded in audit timeline.</p>
            ) : (
              activity_timeline.map((act, idx) => (
                <div key={idx} className="relative pl-6">
                  <div className="absolute -left-[25px] top-0.5 w-4 h-4 rounded-full bg-white dark:bg-slate-900 border-2 border-sky-500" />
                  <div className="flex items-center justify-between">
                    <h5 className="font-bold text-slate-900 dark:text-slate-100 text-sm">
                      {act.title}
                    </h5>
                    <span className="text-slate-400 font-mono text-[11px]">
                      {new Date(act.timestamp).toLocaleString()}
                    </span>
                  </div>
                  <div className="text-slate-500 mt-0.5">
                    Actor: <span className="font-medium text-slate-700 dark:text-slate-300">{act.actor_name}</span>
                  </div>
                  {act.details && (
                    <p className="text-slate-600 dark:text-slate-400 mt-1.5 p-2 rounded bg-slate-50 dark:bg-slate-800">
                      {act.details}
                    </p>
                  )}
                </div>
              ))
            )}
          </div>
        </Card>
      )}

      {/* TAB 6: AI TALENT SYNTHESIS */}
      {activeTab === 'ai_synthesis' && (
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-xl bg-gradient-to-r from-sky-50 to-indigo-50 dark:from-sky-950/40 dark:to-indigo-950/40 border border-sky-100 dark:border-sky-900">
            <div>
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-amber-500" />
                <h3 className="font-bold text-sm text-slate-900 dark:text-slate-100">
                  AI-Powered Evidence-Grounded Candidate Evaluation Synthesis
                </h3>
              </div>
              <p className="text-xs text-slate-600 dark:text-slate-400 mt-1 max-w-2xl">
                Grounds strictly on verified academic metrics, evaluated interview scorecards, and deterministic compatibility. Never invents facts or infers demographic factors.
              </p>
            </div>
            <Button
              size="sm"
              variant="primary"
              disabled={aiGenerating}
              onClick={handleGenerateAiSummary}
              icon={<Sparkles className="w-3.5 h-3.5" />}
            >
              {aiGenerating ? 'Generating...' : aiSummary ? 'Regenerate Synthesis' : 'Generate Synthesis'}
            </Button>
          </div>

          {!aiSummary ? (
            <Card>
              <div className="py-16 text-center text-slate-400">
                <Sparkles className="w-10 h-10 text-amber-400 mx-auto mb-3 opacity-60" />
                <h4 className="font-semibold text-slate-800 dark:text-slate-200 text-sm">
                  Ready to Synthesize Candidate Evaluation
                </h4>
                <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
                  Click the button above to generate a synthesized view across verified facts, deterministic metrics, and qualitative interviewer notes.
                </p>
              </div>
            </Card>
          ) : (
            <div className="space-y-6">
              {/* Headline */}
              <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
                <span className="text-[10px] font-bold uppercase tracking-wider text-sky-600 dark:text-sky-400">
                  Readiness Headline
                </span>
                <h3 className="text-base font-bold text-slate-900 dark:text-slate-100 mt-1">
                  {aiSummary.ai_observations.readiness_headline}
                </h3>
                <p className="text-xs text-slate-600 dark:text-slate-300 mt-2 leading-relaxed">
                  {aiSummary.ai_observations.overall_synthesis}
                </p>
              </div>

              {/* 3-Column Grounded Breakdown */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* 1. Verified Facts */}
                <Card>
                  <CardHeader
                    title="1. Grounded Verified Facts"
                    subtitle="Confirmed candidate credentials"
                  />
                  <div className="mt-3 space-y-2 text-xs">
                    <div className="p-2.5 rounded bg-slate-50 dark:bg-slate-800/60">
                      <div className="text-slate-400">Academics</div>
                      <div className="font-semibold text-slate-800 dark:text-slate-200 mt-0.5">
                        CGPA {String(aiSummary.verified_facts.cgpa || academics.cgpa)} •{' '}
                        {String(aiSummary.verified_facts.department || candidateDept)}
                      </div>
                    </div>
                    <div className="p-2.5 rounded bg-slate-50 dark:bg-slate-800/60">
                      <div className="text-slate-400">Confirmed Skills</div>
                      <div className="font-semibold text-slate-800 dark:text-slate-200 mt-0.5">
                        {Array.isArray(aiSummary.verified_facts.confirmed_skills)
                          ? aiSummary.verified_facts.confirmed_skills.join(', ')
                          : 'None'}
                      </div>
                    </div>
                    <div className="p-2.5 rounded bg-slate-50 dark:bg-slate-800/60">
                      <div className="text-slate-400">Verified Projects</div>
                      <div className="font-semibold text-slate-800 dark:text-slate-200 mt-0.5">
                        {Array.isArray(aiSummary.verified_facts.verified_projects)
                          ? aiSummary.verified_facts.verified_projects.join(', ')
                          : 'None'}
                      </div>
                    </div>
                  </div>
                </Card>

                {/* 2. Calculated Metrics */}
                <Card>
                  <CardHeader
                    title="2. Calculated Metrics"
                    subtitle="Deterministic engine values"
                  />
                  <div className="mt-3 space-y-2 text-xs">
                    <div className="p-2.5 rounded bg-slate-50 dark:bg-slate-800/60 flex justify-between">
                      <span className="text-slate-500">Compatibility Score</span>
                      <span className="font-bold text-slate-900 dark:text-slate-100">
                        {String(aiSummary.calculated_metrics.compatibility_score || compatScore)}%
                      </span>
                    </div>
                    <div className="p-2.5 rounded bg-slate-50 dark:bg-slate-800/60 flex justify-between">
                      <span className="text-slate-500">Eligibility Verdict</span>
                      <span className="font-bold text-emerald-600">
                        {aiSummary.calculated_metrics.is_eligible ? 'PASSED' : 'FAILED'}
                      </span>
                    </div>
                    <div className="p-2.5 rounded bg-slate-50 dark:bg-slate-800/60 flex justify-between">
                      <span className="text-slate-500">Avg Interviewer Rating</span>
                      <span className="font-bold text-amber-600">
                        {aiSummary.calculated_metrics.average_interviewer_rating
                          ? `${aiSummary.calculated_metrics.average_interviewer_rating} / 5.0`
                          : 'Not evaluated'}
                      </span>
                    </div>
                  </div>
                </Card>

                {/* 3. Interview Probe Questions */}
                <Card>
                  <CardHeader
                    title="3. Suggested Interview Probes"
                    subtitle="Targeted questions for interviewers"
                  />
                  <div className="mt-3 space-y-2 text-xs">
                    {aiSummary.ai_observations.suggested_interview_probes?.map((probe, pidx) => (
                      <div
                        key={pidx}
                        className="p-2.5 rounded-lg border border-slate-100 dark:border-slate-800 bg-sky-50/50 dark:bg-sky-950/20 text-slate-700 dark:text-slate-300 leading-snug"
                      >
                        • {probe}
                      </div>
                    ))}
                  </div>
                </Card>
              </div>

              {/* Strengths & Development Areas */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Card>
                  <CardHeader title="Synthesized Strengths" subtitle="Demonstrated technical strengths" />
                  <ul className="mt-3 space-y-1.5 text-xs text-slate-700 dark:text-slate-300">
                    {aiSummary.ai_observations.synthesized_strengths?.map((str, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
                        <span>{str}</span>
                      </li>
                    ))}
                  </ul>
                </Card>

                <Card>
                  <CardHeader
                    title="Areas for Development"
                    subtitle="Identified gaps and learning curves"
                  />
                  <ul className="mt-3 space-y-1.5 text-xs text-slate-700 dark:text-slate-300">
                    {aiSummary.ai_observations.areas_for_development?.map((dev, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <AlertCircle className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
                        <span>{dev}</span>
                      </li>
                    ))}
                  </ul>
                </Card>
              </div>

              {/* Safety Disclaimer */}
              <div className="p-3.5 rounded-lg bg-slate-100 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 text-[11px] flex items-center gap-2.5">
                <ShieldCheck className="w-4 h-4 text-slate-500 flex-shrink-0" />
                <span>{aiSummary.safety_disclaimer}</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* MODAL: SUBMIT EVALUATION FORM */}
      {evalModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto p-6 shadow-2xl border border-slate-200 dark:border-slate-800">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100 dark:border-slate-800">
              <h3 className="font-bold text-base text-slate-900 dark:text-slate-100">
                Submit Candidate Evaluation
              </h3>
              <button
                onClick={() => setEvalModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSubmitEvaluation} className="mt-4 space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Evaluation Stage
                </label>
                <select
                  value={evalStage}
                  onChange={(e) => setEvalStage(e.target.value as EvaluationStage)}
                  className="w-full p-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-xs"
                >
                  <option value="technical">Technical Round</option>
                  <option value="problem_solving">Problem Solving / Coding</option>
                  <option value="project_discussion">Project Architecture Discussion</option>
                  <option value="communication">Communication & Soft Skills</option>
                  <option value="hr">HR & Cultural Alignment</option>
                  <option value="overall">Overall Hiring Synthesis</option>
                </select>
              </div>

              {/* Rating Sliders */}
              <div className="space-y-3 p-3 rounded-lg bg-slate-50 dark:bg-slate-800">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-slate-700 dark:text-slate-300">
                    Technical Proficiency: {evalTech}/5
                  </span>
                  <input
                    type="range"
                    min="1"
                    max="5"
                    value={evalTech}
                    onChange={(e) => setEvalTech(Number(e.target.value))}
                    className="accent-sky-600"
                  />
                </div>
                <div className="flex items-center justify-between">
                  <span className="font-medium text-slate-700 dark:text-slate-300">
                    Problem Solving: {evalProb}/5
                  </span>
                  <input
                    type="range"
                    min="1"
                    max="5"
                    value={evalProb}
                    onChange={(e) => setEvalProb(Number(e.target.value))}
                    className="accent-sky-600"
                  />
                </div>
                <div className="flex items-center justify-between">
                  <span className="font-medium text-slate-700 dark:text-slate-300">
                    Communication: {evalComm}/5
                  </span>
                  <input
                    type="range"
                    min="1"
                    max="5"
                    value={evalComm}
                    onChange={(e) => setEvalComm(Number(e.target.value))}
                    className="accent-sky-600"
                  />
                </div>
                <div className="flex items-center justify-between">
                  <span className="font-medium text-slate-700 dark:text-slate-300">
                    Project Depth: {evalProj}/5
                  </span>
                  <input
                    type="range"
                    min="1"
                    max="5"
                    value={evalProj}
                    onChange={(e) => setEvalProj(Number(e.target.value))}
                    className="accent-sky-600"
                  />
                </div>
                <div className="flex items-center justify-between">
                  <span className="font-medium text-slate-700 dark:text-slate-300">
                    Cultural Fit: {evalCulture}/5
                  </span>
                  <input
                    type="range"
                    min="1"
                    max="5"
                    value={evalCulture}
                    onChange={(e) => setEvalCulture(Number(e.target.value))}
                    className="accent-sky-600"
                  />
                </div>
              </div>

              {/* Overall Rating & Recommendation */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Overall Rating (1.0 - 5.0)
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="5"
                    step="0.5"
                    value={evalOverall}
                    onChange={(e) => setEvalOverall(Number(e.target.value))}
                    required
                    className="w-full p-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-xs"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Hiring Recommendation
                  </label>
                  <select
                    value={evalRec}
                    onChange={(e) => setEvalRec(e.target.value as EvaluationRecommendation)}
                    className="w-full p-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-xs"
                  >
                    <option value="strong_hire">Strong Hire</option>
                    <option value="hire">Hire</option>
                    <option value="hold">Hold</option>
                    <option value="no_hire">No Hire</option>
                    <option value="strong_no_hire">Strong No Hire</option>
                  </select>
                </div>
              </div>

              {/* Written Feedback */}
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Qualitative Written Feedback
                </label>
                <textarea
                  rows={4}
                  placeholder="Summarize candidate's technical responses, behavioral observations, and rationale..."
                  value={evalFeedback}
                  onChange={(e) => setEvalFeedback(e.target.value)}
                  required
                  className="w-full p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-xs"
                />
              </div>

              {/* Strengths & Weaknesses Inputs */}
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Key Strengths (comma-separated)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Distributed system design, Async programming, Clear articulation"
                  value={evalStrengthInput}
                  onChange={(e) => setEvalStrengthInput(e.target.value)}
                  className="w-full p-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-xs"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Areas for Development (comma-separated)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Needs deeper caching knowledge, Unit testing coverage"
                  value={evalWeaknessInput}
                  onChange={(e) => setEvalWeaknessInput(e.target.value)}
                  className="w-full p-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-xs"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <Button
                  size="sm"
                  variant="outline"
                  type="button"
                  onClick={() => setEvalModalOpen(false)}
                >
                  Cancel
                </Button>
                <Button
                  size="sm"
                  variant="primary"
                  type="submit"
                  disabled={evalSubmitting || !evalFeedback.trim()}
                >
                  {evalSubmitting ? 'Submitting...' : 'Save Evaluation'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: EXTEND OFFER */}
      {offerModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 dark:border-slate-800">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100 dark:border-slate-800">
              <h3 className="font-bold text-base text-slate-900 dark:text-slate-100">
                Extend Job Offer
              </h3>
              <button
                onClick={() => setOfferModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
              >
                ✕
              </button>
            </div>

            <div className="mt-4 space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Annual Compensation Package (CTC in LPA)
                </label>
                <input
                  type="number"
                  min="1"
                  step="0.5"
                  value={offerLpa}
                  onChange={(e) => setOfferLpa(Number(e.target.value))}
                  className="w-full p-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-xs"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Candidate Acceptance Deadline
                </label>
                <input
                  type="date"
                  value={offerDeadline}
                  onChange={(e) => setOfferDeadline(e.target.value)}
                  className="w-full p-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-xs"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Offer Letter Notes / Stipulations
                </label>
                <textarea
                  rows={3}
                  placeholder="Joining dates, probation conditions, or bonus structure..."
                  value={offerNotes}
                  onChange={(e) => setOfferNotes(e.target.value)}
                  className="w-full p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-xs"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <Button
                  size="sm"
                  variant="outline"
                  type="button"
                  onClick={() => setOfferModalOpen(false)}
                >
                  Cancel
                </Button>
                <Button
                  size="sm"
                  variant="primary"
                  className="bg-emerald-600 hover:bg-emerald-700 text-white"
                  disabled={isTransitioning}
                  onClick={() =>
                    handleStatusChange(
                      'offered',
                      `Formal offer extended at ${offerLpa} LPA.`,
                      {
                        offer_package_lpa: offerLpa,
                        offer_deadline_at: offerDeadline ? new Date(offerDeadline).toISOString() : undefined,
                        offer_notes: offerNotes,
                      }
                    )
                  }
                >
                  {isTransitioning ? 'Extending...' : 'Release Formal Offer'}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
};
