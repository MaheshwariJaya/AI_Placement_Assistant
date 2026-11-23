import React, { useState, useEffect, useRef } from 'react';
import { DashboardLayout } from '../../components/layout/DashboardLayout';
import { Card, CardHeader } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { Input } from '../../components/common/Input';
import { resumeApi } from '../../services/api';
import {
  Resume,
  ResumeStructuredData,
  ParsingStatus,
  SkillItem,
  ProjectItem,
  ExperienceItem,
  CertificationItem,
} from '../../types';
import {
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertCircle,
  Trash2,
  Download,
  RefreshCw,
  Sparkles,
  Plus,
  X,
  ShieldCheck,
  Briefcase,
  GraduationCap,
  Award,
  Code2,
  ExternalLink,
} from 'lucide-react';
import { ResumeFeedbackSection } from './ResumeFeedbackSection';

export const ResumeIntelligencePage: React.FC = () => {
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [selectedResume, setSelectedResume] = useState<Resume | null>(null);
  const [editingData, setEditingData] = useState<ResumeStructuredData | null>(null);
  const [mainView, setMainView] = useState<'entities' | 'feedback'>('entities');
  const [activeTab, setActiveTab] = useState<'skills' | 'projects' | 'experiences' | 'certifications' | 'personal' | 'education'>('skills');

  // UI States
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // New Skill Form State
  const [newSkillName, setNewSkillName] = useState('');
  const [newSkillCategory, setNewSkillCategory] = useState('technical');
  const [newSkillLevel, setNewSkillLevel] = useState('intermediate');

  useEffect(() => {
    fetchResumes();
  }, []);

  const fetchResumes = async () => {
    setIsLoading(true);
    try {
      const data = await resumeApi.getResumes();
      setResumes(data);
      if (selectedResume) {
        const fresh = data.find((r) => r.id === selectedResume.id);
        if (fresh) {
          setSelectedResume(fresh);
        }
      } else if (data.length > 0) {
        selectResumeForReview(data[0]);
      }
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: err.response?.data?.error?.message || 'Failed to fetch resume list.',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const selectResumeForReview = (resume: Resume) => {
    setSelectedResume(resume);
    if (resume.parsed_entities) {
      setEditingData(JSON.parse(JSON.stringify(resume.parsed_entities)));
    } else {
      setEditingData(null);
    }
  };

  const handleFileUpload = async (file: File) => {
    // 1. Client-side Size Validation (5MB max)
    if (file.size > 5242880) {
      setStatusMessage({
        type: 'error',
        text: `File exceeds maximum limit of 5 MB (${(file.size / (1024 * 1024)).toFixed(2)} MB). Please select a smaller resume.`,
      });
      return;
    }

    // 2. Client-side Extension Validation
    const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    if (!['.pdf', '.docx'].includes(ext)) {
      setStatusMessage({
        type: 'error',
        text: `Unsupported file type (${ext}). Only PDF and DOCX documents are supported.`,
      });
      return;
    }

    setIsUploading(true);
    setStatusMessage({ type: 'info', text: 'Uploading document and running AI entity extraction...' });

    try {
      const uploaded = await resumeApi.uploadResume(file, true);
      if (uploaded.parsing_status === 'failed') {
        const failureReason = uploaded.raw_text_preview?.startsWith('[FAILED]')
          ? uploaded.raw_text_preview.replace('[FAILED]', '').trim()
          : null;
        setStatusMessage({
          type: 'error',
          text: `Resume "${file.name}" was uploaded, but AI entity extraction failed${failureReason ? `: ${failureReason}` : ''}. Click "Re-Extract" below to retry.`,
        });
      } else if (uploaded.parsing_status === 'review_required' || uploaded.parsing_status === 'extracted') {
        setStatusMessage({
          type: 'success',
          text: `Resume "${file.name}" uploaded and extracted successfully. Please review the structured entities below.`,
        });
      } else {
        setStatusMessage({
          type: 'info',
          text: `Resume "${file.name}" uploaded. Extraction status: ${uploaded.parsing_status}.`,
        });
      }
      await fetchResumes();
      selectResumeForReview(uploaded);
    } catch (err: any) {
      const errDetail = err.response?.data?.error?.message || err.message || 'Upload failed.';
      setStatusMessage({
        type: 'error',
        text: `Upload failed: ${errDetail}`,
      });
      await fetchResumes();
    } finally {
      setIsUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  const handleDelete = async (resumeId: number) => {
    if (!window.confirm('Are you sure you want to delete this resume? This cannot be undone.')) {
      return;
    }
    try {
      await resumeApi.deleteResume(resumeId);
      setStatusMessage({ type: 'success', text: 'Resume deleted successfully.' });
      if (selectedResume?.id === resumeId) {
        setSelectedResume(null);
        setEditingData(null);
      }
      await fetchResumes();
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: err.response?.data?.error?.message || 'Failed to delete resume.',
      });
    }
  };

  const handleDownload = async (resume: Resume) => {
    try {
      await resumeApi.downloadResume(resume.id, resume.file_name);
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: err.response?.data?.error?.message || 'Failed to download resume file.',
      });
    }
  };

  const handleReExtract = async (resumeId: number) => {
    setIsLoading(true);
    setStatusMessage({ type: 'info', text: 'Re-extracting structured entities...' });
    try {
      const updated = await resumeApi.triggerExtraction(resumeId);
      setStatusMessage({ type: 'success', text: 'Entities successfully re-extracted.' });
      await fetchResumes();
      selectResumeForReview(updated);
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: err.response?.data?.error?.message || 'Re-extraction failed.',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveEdits = async () => {
    if (!selectedResume || !editingData) return;
    setIsLoading(true);
    try {
      const updated = await resumeApi.reviewResume(selectedResume.id, editingData);
      setSelectedResume(updated);
      setStatusMessage({ type: 'success', text: 'Extracted review edits saved successfully.' });
      await fetchResumes();
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: err.response?.data?.error?.message || 'Failed to save review edits.',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleApproveSync = async () => {
    if (!selectedResume) return;
    setIsSyncing(true);
    try {
      const res = await resumeApi.approveResume(selectedResume.id, {
        verified_data: editingData || undefined,
        sync_education: true,
        sync_skills: true,
        sync_projects: true,
        sync_experiences: true,
        sync_certifications: true,
        sync_links: true,
        update_existing_links: true,
      });

      setSelectedResume((prev) => (prev ? { ...prev, parsing_status: 'approved' } : null));

      setStatusMessage({
        type: 'success',
        text: `${res.message} (Education: ${res.synced_counts.education || 0}, Skills: ${res.synced_counts.skills}, Projects: ${res.synced_counts.projects}, Experiences: ${res.synced_counts.experiences}). Verified academic metrics were preserved!`,
      });
      await fetchResumes();
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: err.response?.data?.error?.message || 'Failed to approve and synchronize profile.',
      });
    } finally {
      setIsSyncing(false);
    }
  };

  const handleReject = async () => {
    if (!selectedResume) return;
    try {
      await resumeApi.rejectResume(selectedResume.id);
      setStatusMessage({ type: 'info', text: 'Resume extraction marked as rejected.' });
      await fetchResumes();
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: err.response?.data?.error?.message || 'Failed to reject resume.',
      });
    }
  };

  // Skill Management Helpers
  const addSkill = () => {
    if (!newSkillName.trim() || !editingData) return;
    const updatedSkills = [
      ...(editingData.skills || []),
      {
        skill_name: newSkillName.trim(),
        category: newSkillCategory,
        proficiency_level: newSkillLevel,
      },
    ];
    setEditingData({ ...editingData, skills: updatedSkills });
    setNewSkillName('');
  };

  const removeSkill = (index: number) => {
    if (!editingData?.skills) return;
    const updated = editingData.skills.filter((_, i) => i !== index);
    setEditingData({ ...editingData, skills: updated });
  };

  const getStatusBadge = (status: ParsingStatus) => {
    switch (status) {
      case 'approved':
        return <Badge variant="success">Approved & Synced</Badge>;
      case 'review_required':
      case 'extracted':
        return <Badge variant="info">Review Required</Badge>;
      case 'processing':
        return <Badge variant="warning">Processing...</Badge>;
      case 'failed':
        return <Badge variant="danger">Extraction Failed</Badge>;
      case 'rejected':
        return <Badge variant="danger">Rejected</Badge>;
      default:
        return <Badge variant="neutral">Uploaded</Badge>;
    }
  };

  const getConfidenceBadge = (confidence?: string) => {
    switch (confidence) {
      case 'high':
        return <Badge variant="success">High Confidence</Badge>;
      case 'medium':
        return <Badge variant="warning">Medium Confidence</Badge>;
      case 'low':
        return <Badge variant="danger">Low Confidence (Verify)</Badge>;
      default:
        return <Badge variant="neutral">Verified Text</Badge>;
    }
  };

  return (
    <DashboardLayout
      role="student"
      title="Resume Intelligence & Verification"
      subtitle="Upload your collegiate resume. AI extracts skills, projects, and experiences with human-in-the-loop review."
    >
      {/* Alert / Notification Banner */}
      {statusMessage && (
        <div
          className={`p-4 rounded-lg mb-6 flex items-start justify-between ${
            statusMessage.type === 'success'
              ? 'bg-emerald-50 dark:bg-emerald-950/30 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/60'
              : statusMessage.type === 'error'
              ? 'bg-rose-50 dark:bg-rose-950/30 text-rose-800 dark:text-rose-300 border border-rose-200 dark:border-rose-800/60'
              : 'bg-sky-50 dark:bg-sky-950/30 text-sky-800 dark:text-sky-300 border border-sky-200 dark:border-sky-800/60'
          }`}
        >
          <div className="flex items-center space-x-2">
            {statusMessage.type === 'success' ? (
              <CheckCircle2 className="w-5 h-5 flex-shrink-0 text-emerald-600 dark:text-emerald-400" />
            ) : (
              <AlertCircle className="w-5 h-5 flex-shrink-0 text-rose-600 dark:text-rose-400" />
            )}
            <span className="text-xs font-medium">{statusMessage.text}</span>
          </div>
          <button
            onClick={() => setStatusMessage(null)}
            className="text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-300 p-1"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Grid: Upload & File Management */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 mb-6">
        {/* Upload Dropzone */}
        <div className="xl:col-span-1">
          <Card>
            <CardHeader
              title="Upload New Resume"
              subtitle="PDF or DOCX format (Max 5 MB)"
            />
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all ${
                isDragging
                  ? 'border-brand-500 bg-brand-50/50 dark:bg-brand-950/30'
                  : 'border-slate-300 dark:border-slate-700 hover:border-brand-400 dark:hover:border-brand-500 bg-slate-50/50 dark:bg-slate-800/40'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    handleFileUpload(e.target.files[0]);
                  }
                }}
              />
              <div className="w-12 h-12 rounded-full bg-brand-100 dark:bg-brand-950/60 text-brand-600 dark:text-brand-400 flex items-center justify-center mx-auto mb-3">
                {isUploading ? (
                  <RefreshCw className="w-6 h-6 animate-spin" />
                ) : (
                  <UploadCloud className="w-6 h-6" />
                )}
              </div>
              <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                {isUploading ? 'Extracting Resume...' : 'Drop your resume here, or browse'}
              </p>
              <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                Supports PDF and DOCX with magic-byte verification
              </p>
              <div className="mt-4 inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 text-[10px] font-medium border border-emerald-200 dark:border-emerald-800/60">
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>Private & Secure Storage</span>
              </div>
            </div>

            {/* Academic Safety Notice */}
            <div className="mt-4 p-3 rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800/60 text-[11px] text-amber-800 dark:text-amber-300 flex items-start gap-2">
              <ShieldCheck className="w-4 h-4 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
              <span>
                <strong>Verified Profile Protection:</strong> Official academic metrics (CGPA, roll number, backlogs) are preserved and cannot be overwritten by resume uploads.
              </span>
            </div>
          </Card>
        </div>

        {/* Uploaded Resumes List */}
        <div className="xl:col-span-2">
          <Card>
            <CardHeader
              title="Your Uploaded Resumes"
              subtitle="Select a resume below to review extracted entities before syncing."
            />
            {resumes.length === 0 ? (
              <div className="text-center py-10 text-slate-400 dark:text-slate-500">
                <FileText className="w-10 h-10 mx-auto mb-2 opacity-50" />
                <p className="text-xs">No resumes uploaded yet. Upload your first resume above.</p>
              </div>
            ) : (
              <div className="divide-y divide-slate-100 dark:divide-slate-800">
                {resumes.map((r) => (
                  <div
                    key={r.id}
                    onClick={() => selectResumeForReview(r)}
                    className={`p-3.5 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-3 cursor-pointer transition-colors ${
                      selectedResume?.id === r.id
                        ? 'bg-brand-50/70 dark:bg-brand-950/30 border border-brand-200 dark:border-brand-800/60'
                        : 'hover:bg-slate-50 dark:hover:bg-slate-800/50'
                    }`}
                  >
                    <div className="flex items-center space-x-3 min-w-0 flex-1">
                      <div className="w-9 h-9 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 flex items-center justify-center flex-shrink-0 font-bold uppercase text-[10px]">
                        {r.file_type}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="text-xs font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2 flex-wrap">
                          <span className="truncate max-w-[200px] sm:max-w-xs" title={r.file_name}>{r.file_name}</span>
                          {getStatusBadge(r.parsing_status)}
                        </div>
                        <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                          {(r.file_size_bytes / 1024).toFixed(1)} KB • Uploaded {new Date(r.created_at).toLocaleDateString()}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5 flex-wrap sm:flex-nowrap shrink-0">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          selectResumeForReview(r);
                          setMainView('feedback');
                        }}
                        className={`!text-[11px] !py-1 ${
                          selectedResume?.id === r.id && mainView === 'feedback'
                            ? 'bg-brand-50 dark:bg-brand-950/50 text-brand-700 dark:text-brand-300 border-brand-300 dark:border-brand-700 font-semibold'
                            : 'text-slate-600 dark:text-slate-300'
                        }`}
                      >
                        <Sparkles className="w-3.5 h-3.5 mr-1 text-brand-600 dark:text-brand-400" /> Feedback
                      </Button>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDownload(r);
                        }}
                        className="!text-[11px] !py-1"
                      >
                        <Download className="w-3.5 h-3.5 mr-1" /> Download
                      </Button>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleReExtract(r.id);
                        }}
                        className="!text-[11px] !py-1"
                      >
                        <RefreshCw className="w-3.5 h-3.5 mr-1" /> Re-Extract
                      </Button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(r.id);
                        }}
                        className="p-1.5 text-slate-400 dark:text-slate-500 hover:text-rose-600 dark:hover:text-rose-400 rounded-lg hover:bg-rose-50 dark:hover:bg-rose-950/40"
                        title="Delete resume"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>

      {/* Top-Level Mode Switcher: Entity Review vs Resume Feedback & Scoring */}
      {selectedResume && (
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200 dark:border-slate-800 mb-6 pb-3">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setMainView('entities')}
              className={`flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-lg transition-colors ${
                mainView === 'entities'
                  ? 'bg-slate-900 dark:bg-brand-600 text-white shadow-sm'
                  : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-700'
              }`}
            >
              <FileText className="w-4 h-4" />
              AI Entity Review & Profile Sync
            </button>
            <button
              type="button"
              onClick={() => setMainView('feedback')}
              className={`flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-lg transition-colors ${
                mainView === 'feedback'
                  ? 'bg-brand-600 text-white shadow-sm'
                  : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-700'
              }`}
            >
              <Sparkles className="w-4 h-4 text-amber-300" />
              Resume Feedback & Scoring
              <span
                className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                  mainView === 'feedback' ? 'bg-brand-700 text-brand-100' : 'bg-brand-50 dark:bg-brand-950/50 text-brand-700 dark:text-brand-300'
                }`}
              >
                Advisory
              </span>
            </button>
          </div>

          <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
            <span>Selected:</span>
            <span className="font-semibold text-slate-800 dark:text-slate-200 bg-slate-100 dark:bg-slate-800 px-2.5 py-1 rounded-md text-[11px] truncate max-w-[200px]">
              {selectedResume.file_name}
            </span>
            {getStatusBadge(selectedResume.parsing_status)}
          </div>
        </div>
      )}

      {/* View 1: AI Resume Feedback & Presentation Scoring */}
      {mainView === 'feedback' && selectedResume && (
        <ResumeFeedbackSection
          resume={selectedResume}
          onSwitchToEntities={() => setMainView('entities')}
        />
      )}

      {/* View 2: Human-in-the-Loop Extraction Review & Approval Interface */}
      {mainView === 'entities' && selectedResume && !editingData && (
        <Card className="mb-8 p-8 text-center text-slate-500 dark:text-slate-400">
          <AlertCircle className={`w-8 h-8 mx-auto mb-2 ${selectedResume.parsing_status === 'failed' ? 'text-rose-500 dark:text-rose-400' : 'text-slate-400 dark:text-slate-500'}`} />
          <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-200">
            {selectedResume.parsing_status === 'failed' ? 'AI Entity Extraction Failed' : 'No Structured Entities Available'}
          </h4>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-md mx-auto">
            {selectedResume.parsing_status === 'failed'
              ? (selectedResume.raw_text_preview?.startsWith('[FAILED]')
                  ? selectedResume.raw_text_preview.replace('[FAILED]', '').trim()
                  : 'An error occurred during AI entity extraction. Click "Re-Extract" on the card above to retry.')
              : 'This resume has not undergone entity extraction yet or is currently processing. Click "Re-Extract" on the card above to extract skills, projects, and experiences.'}
          </p>
          {selectedResume.parsing_status === 'failed' && (
            <div className="mt-4 flex justify-center">
              <Button
                variant="primary"
                size="sm"
                onClick={() => handleReExtract(selectedResume.id)}
                disabled={isLoading}
              >
                <RefreshCw className="w-3.5 h-3.5 mr-1.5" /> Retry Extraction
              </Button>
            </div>
          )}
        </Card>
      )}

      {mainView === 'entities' && selectedResume && editingData && (
        <Card className="mb-8">
          <div className="border-b border-slate-200 dark:border-slate-800 pb-4 mb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                  AI Entity Review: {selectedResume.file_name}
                </h3>
                {getStatusBadge(selectedResume.parsing_status)}
              </div>
              <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                Review and edit extracted entities before synchronizing to your profile.
              </p>
            </div>

            {/* Top Action Buttons */}
            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={handleSaveEdits}
                disabled={isLoading}
              >
                Save Edits
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={handleApproveSync}
                disabled={isSyncing}
                className={selectedResume.parsing_status === 'approved' ? 'bg-emerald-700 hover:bg-emerald-800' : 'bg-emerald-600 hover:bg-emerald-700'}
              >
                <CheckCircle2 className="w-4 h-4 mr-1.5" />
                {isSyncing ? 'Syncing...' : selectedResume.parsing_status === 'approved' ? 'Profile Synchronized (Re-Sync)' : 'Approve & Sync Profile'}
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={handleReject}
                className="!text-rose-600 dark:!text-rose-400 hover:!bg-rose-50 dark:hover:!bg-rose-950/40"
              >
                Reject
              </Button>
            </div>
          </div>

          {/* Verification Guardrail Warning Banner */}
          {selectedResume.parsing_status === 'approved' ? (
            <div className="p-3.5 mb-5 rounded-lg bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800/60 text-xs text-emerald-900 dark:text-emerald-200 flex items-start gap-2.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400 flex-shrink-0 mt-0.5" />
              <div className="space-y-0.5">
                <span className="font-bold">Resume Approved & Synchronized to Academic Profile</span>
                <p className="text-[11px] text-emerald-800 dark:text-emerald-300/90 leading-relaxed">
                  Extracted skills, projects, and experiences are committed to your profile. You can edit items and click &quot;Profile Synchronized (Re-Sync)&quot; anytime to update your records. Official academic records remain protected.
                </p>
              </div>
            </div>
          ) : (
            <div className="p-3.5 mb-5 rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800/60 text-xs text-amber-900 dark:text-amber-200 flex items-start gap-2.5">
              <AlertCircle className="w-4 h-4 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
              <div className="space-y-0.5">
                <span className="font-bold">Human-in-the-Loop Verification Required:</span>
                <p className="text-[11px] text-amber-800 dark:text-amber-300/90 leading-relaxed">
                  Review each extracted field below against the verbatim supporting evidence quoted from your resume. 
                  You can edit, add, or delete any item. <strong>Official academic records (Roll Number, Institutional CGPA, Backlogs) are permanently protected and will never be overwritten.</strong>
                </p>
              </div>
            </div>
          )}

          {/* Extraction Audit Metadata Strip */}
          <div className="flex flex-wrap items-center gap-3 px-3.5 py-2.5 mb-6 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-xs text-slate-600 dark:text-slate-300">
            <div className="flex items-center gap-1.5">
              <span className="font-semibold text-slate-700 dark:text-slate-200">Extractor:</span>
              <span className="px-2 py-0.5 rounded bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 font-mono text-[11px] text-slate-800 dark:text-slate-200">
                {editingData.extraction_method === 'mock_rule_based'
                  ? 'Rule-Based Offline Extractor'
                  : editingData.extraction_method === 'gemini_ai'
                  ? 'Gemini 3.5 Flash Lite (Grounded)'
                  : editingData.extraction_method === 'openai_ai'
                  ? 'OpenAI GPT-4o-mini (Grounded)'
                  : 'Deterministic Engine'}
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="font-semibold text-slate-700 dark:text-slate-200">Confidence:</span>
              {getConfidenceBadge(editingData.overall_confidence)}
            </div>
            {editingData.hallucinations_purged !== undefined && editingData.hallucinations_purged > 0 && (
              <div className="flex items-center gap-1 text-emerald-700 dark:text-emerald-400 text-[11px] font-semibold">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                <span>{editingData.hallucinations_purged} unsupported item(s) filtered out</span>
              </div>
            )}
          </div>

          {/* Section Navigation Tabs */}
          <div className="flex space-x-1 border-b border-slate-200 dark:border-slate-800 mb-6 overflow-x-auto pb-1">
            {[
              { id: 'skills', label: `Skills (${editingData.skills?.length || 0})`, icon: Code2 },
              { id: 'projects', label: `Projects (${editingData.projects?.length || 0})`, icon: Briefcase },
              { id: 'experiences', label: `Experience (${editingData.experiences?.length || 0})`, icon: Award },
              { id: 'certifications', label: `Certifications (${editingData.certifications?.length || 0})`, icon: Award },
              { id: 'education', label: `Education (${editingData.education?.length || 0})`, icon: GraduationCap },
              { id: 'personal', label: 'Contact & Links', icon: FileText },
            ].map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-lg transition-colors whitespace-nowrap ${
                    activeTab === tab.id
                      ? 'bg-brand-50 dark:bg-brand-950/40 text-brand-700 dark:text-brand-300 border border-brand-200 dark:border-brand-800/60'
                      : 'text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>

          {/* Tab 1: Skills Editor */}
          {activeTab === 'skills' && (
            <div className="space-y-4">
              {(!editingData.skills || editingData.skills.length === 0) ? (
                <div className="p-6 text-center text-slate-500 dark:text-slate-400 text-xs bg-slate-50 dark:bg-slate-800/50 border border-dashed border-slate-200 dark:border-slate-700 rounded-lg">
                  No technical skills explicitly matched from the resume text. Use the input below to add verified skills.
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5 mb-4">
                  {editingData.skills.map((s, idx) => (
                    <div
                      key={idx}
                      className="p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 flex flex-col justify-between hover:border-brand-300 dark:hover:border-brand-600 transition-colors"
                    >
                      <div className="flex items-center justify-between gap-1">
                        <div className="flex items-center gap-1.5 truncate">
                          <span className="text-xs font-bold text-slate-800 dark:text-slate-200 truncate">{s.skill_name}</span>
                          <span className="text-[10px] text-slate-400 dark:text-slate-500">({s.proficiency_level})</span>
                        </div>
                        <button
                          onClick={() => removeSkill(idx)}
                          className="text-slate-400 dark:text-slate-500 hover:text-rose-600 dark:hover:text-rose-400 p-0.5 ml-1"
                          title="Remove skill"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      </div>
                      <div className="mt-1.5 flex items-center justify-between text-[10px]">
                        <span className="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 uppercase font-medium">
                          {s.category}
                        </span>
                        {getConfidenceBadge(s.confidence)}
                      </div>
                      {s.evidence && (
                        <div className="mt-1.5 text-[10px] text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-slate-800/60 px-1.5 py-1 rounded border border-slate-100 dark:border-slate-700/70 italic truncate" title={s.evidence}>
                          "{s.evidence}"
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Add Skill Row */}
              <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 flex flex-col sm:flex-row items-center gap-3">
                <input
                  type="text"
                  placeholder="New Skill (e.g. Next.js, Docker, NLP)"
                  value={newSkillName}
                  onChange={(e) => setNewSkillName(e.target.value)}
                  className="flex-1 text-xs px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 focus:outline-none focus:ring-1 focus:ring-brand-500 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 dark:placeholder:text-slate-500"
                />
                <select
                  value={newSkillCategory}
                  onChange={(e) => setNewSkillCategory(e.target.value)}
                  className="text-xs px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 focus:outline-none"
                >
                  <option value="technical">Technical</option>
                  <option value="tool">Tool / Library</option>
                  <option value="database">Database</option>
                  <option value="soft">Soft Skill</option>
                </select>
                <select
                  value={newSkillLevel}
                  onChange={(e) => setNewSkillLevel(e.target.value)}
                  className="text-xs px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 focus:outline-none"
                >
                  <option value="beginner">Beginner</option>
                  <option value="intermediate">Intermediate</option>
                  <option value="advanced">Advanced</option>
                  <option value="expert">Expert</option>
                </select>
                <Button size="sm" onClick={addSkill} disabled={!newSkillName.trim()}>
                  <Plus className="w-3.5 h-3.5 mr-1" /> Add Skill
                </Button>
              </div>
            </div>
          )}

          {/* Tab 2: Projects Editor */}
          {activeTab === 'projects' && (
            <div className="space-y-4">
              {(!editingData.projects || editingData.projects.length === 0) ? (
                <div className="p-6 text-center text-slate-500 dark:text-slate-400 text-xs bg-slate-50 dark:bg-slate-800/50 border border-dashed border-slate-200 dark:border-slate-700 rounded-lg">
                  No projects detected in resume. Click &quot;Add Project&quot; below to manually add your projects.
                </div>
              ) : (
                editingData.projects.map((p, idx) => (
                  <div key={idx} className="p-4 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 space-y-2 hover:border-brand-300 dark:hover:border-brand-600 transition-colors">
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex-1 flex items-center gap-2">
                        <input
                          type="text"
                          value={p.title}
                          placeholder="Project Title"
                          onChange={(e) => {
                            const updated = [...(editingData.projects || [])];
                            updated[idx].title = e.target.value;
                            setEditingData({ ...editingData, projects: updated });
                          }}
                          className="text-xs font-bold text-slate-800 dark:text-slate-100 bg-transparent border-b border-transparent hover:border-slate-300 dark:hover:border-slate-600 focus:border-brand-500 focus:outline-none flex-1"
                        />
                        {getConfidenceBadge(p.confidence)}
                      </div>
                      <button
                        onClick={() => {
                          const updated = editingData.projects?.filter((_, i) => i !== idx);
                          setEditingData({ ...editingData, projects: updated });
                        }}
                        className="text-slate-400 dark:text-slate-500 hover:text-rose-600 dark:hover:text-rose-400 text-xs p-1"
                        title="Remove project"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                    <input
                      type="text"
                      value={p.technologies || ''}
                      placeholder="Technologies (e.g. React, Node, PostgreSQL)"
                      onChange={(e) => {
                        const updated = [...(editingData.projects || [])];
                        updated[idx].technologies = e.target.value;
                        setEditingData({ ...editingData, projects: updated });
                      }}
                      className="text-[11px] text-brand-600 dark:text-brand-400 bg-transparent w-full focus:outline-none border-b border-transparent hover:border-slate-300 dark:hover:border-slate-600"
                    />
                    <textarea
                      rows={2}
                      value={p.description || ''}
                      placeholder="Project description, architecture, and impact"
                      onChange={(e) => {
                        const updated = [...(editingData.projects || [])];
                        updated[idx].description = e.target.value;
                        setEditingData({ ...editingData, projects: updated });
                      }}
                      className="text-xs text-slate-600 dark:text-slate-200 bg-transparent dark:bg-slate-950 w-full p-2 rounded border border-slate-200 dark:border-slate-700 focus:outline-none focus:border-brand-500"
                    />
                    {p.evidence && (
                      <div className="text-[10px] text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-slate-800/60 p-2 rounded border border-slate-100 dark:border-slate-700/70 flex items-start gap-1">
                        <span className="font-semibold text-slate-600 dark:text-slate-300 flex-shrink-0">Quoted Evidence:</span>
                        <span className="italic truncate">&quot;{p.evidence}&quot;</span>
                      </div>
                    )}
                    {p.confidence === 'low' && (
                      <div className="text-[10px] text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/30 p-1.5 rounded flex items-center gap-1">
                        <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                        <span>Low extraction confidence. Please verify all details before approving.</span>
                      </div>
                    )}
                  </div>
                ))
              )}
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  const updated = [
                    ...(editingData.projects || []),
                    { title: 'New Project', description: '', technologies: '', confidence: 'medium' as const },
                  ];
                  setEditingData({ ...editingData, projects: updated });
                }}
              >
                <Plus className="w-3.5 h-3.5 mr-1" /> Add Project
              </Button>
            </div>
          )}

          {/* Tab 3: Experiences Editor */}
          {activeTab === 'experiences' && (
            <div className="space-y-4">
              {(!editingData.experiences || editingData.experiences.length === 0) ? (
                <div className="p-6 text-center text-slate-500 dark:text-slate-400 text-xs bg-slate-50 dark:bg-slate-800/50 border border-dashed border-slate-200 dark:border-slate-700 rounded-lg">
                  No work experience or internships detected in resume. If you have internship or work experience, click &quot;Add Experience&quot; below.
                </div>
              ) : (
                editingData.experiences.map((exp, idx) => (
                  <div key={idx} className="p-4 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 space-y-2 hover:border-brand-300 dark:hover:border-brand-600 transition-colors">
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2 flex-1">
                        <input
                          type="text"
                          value={exp.role_title}
                          placeholder="Role Title"
                          onChange={(e) => {
                            const updated = [...(editingData.experiences || [])];
                            updated[idx].role_title = e.target.value;
                            setEditingData({ ...editingData, experiences: updated });
                          }}
                          className="text-xs font-bold text-slate-800 dark:text-slate-100 bg-transparent border-b border-transparent hover:border-slate-300 dark:hover:border-slate-600 focus:border-brand-500 focus:outline-none"
                        />
                        <span className="text-slate-400 dark:text-slate-500 text-xs">at</span>
                        <input
                          type="text"
                          value={exp.company_name}
                          placeholder="Company Name"
                          onChange={(e) => {
                            const updated = [...(editingData.experiences || [])];
                            updated[idx].company_name = e.target.value;
                            setEditingData({ ...editingData, experiences: updated });
                          }}
                          className="text-xs font-bold text-slate-800 dark:text-slate-100 bg-transparent border-b border-transparent hover:border-slate-300 dark:hover:border-slate-600 focus:border-brand-500 focus:outline-none"
                        />
                        {getConfidenceBadge(exp.confidence)}
                      </div>
                      <button
                        onClick={() => {
                          const updated = editingData.experiences?.filter((_, i) => i !== idx);
                          setEditingData({ ...editingData, experiences: updated });
                        }}
                        className="text-slate-400 dark:text-slate-500 hover:text-rose-600 dark:hover:text-rose-400 p-1"
                        title="Remove experience"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                    <textarea
                      rows={2}
                      value={exp.description || ''}
                      placeholder="Description of duties, responsibilities, and achievements"
                      onChange={(e) => {
                        const updated = [...(editingData.experiences || [])];
                        updated[idx].description = e.target.value;
                        setEditingData({ ...editingData, experiences: updated });
                      }}
                      className="text-xs text-slate-600 dark:text-slate-200 bg-transparent dark:bg-slate-950 w-full p-2 rounded border border-slate-200 dark:border-slate-700 focus:outline-none focus:border-brand-500"
                    />
                    {exp.evidence && (
                      <div className="text-[10px] text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-slate-800/60 p-2 rounded border border-slate-100 dark:border-slate-700/70 flex items-start gap-1">
                        <span className="font-semibold text-slate-600 dark:text-slate-300 flex-shrink-0">Quoted Evidence:</span>
                        <span className="italic truncate">&quot;{exp.evidence}&quot;</span>
                      </div>
                    )}
                    {exp.confidence === 'low' && (
                      <div className="text-[10px] text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/30 p-1.5 rounded flex items-center gap-1">
                        <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                        <span>Low extraction confidence. Please verify company and role before approving.</span>
                      </div>
                    )}
                  </div>
                ))
              )}
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  const updated = [
                    ...(editingData.experiences || []),
                    { company_name: 'Company', role_title: 'Intern', description: '', confidence: 'medium' as const },
                  ];
                  setEditingData({ ...editingData, experiences: updated });
                }}
              >
                <Plus className="w-3.5 h-3.5 mr-1" /> Add Experience
              </Button>
            </div>
          )}

          {/* Tab 4: Certifications Editor */}
          {activeTab === 'certifications' && (
            <div className="space-y-4">
              {(!editingData.certifications || editingData.certifications.length === 0) ? (
                <div className="p-6 text-center text-slate-500 dark:text-slate-400 text-xs bg-slate-50 dark:bg-slate-800/50 border border-dashed border-slate-200 dark:border-slate-700 rounded-lg">
                  No certifications detected in resume. Click &quot;Add Certification&quot; below to add verified credentials.
                </div>
              ) : (
                editingData.certifications.map((c, idx) => (
                  <div key={idx} className="p-4 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 space-y-2 hover:border-brand-300 dark:hover:border-brand-600 transition-colors">
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <input
                          type="text"
                          value={c.certificate_name}
                          placeholder="Certificate Name"
                          onChange={(e) => {
                            const updated = [...(editingData.certifications || [])];
                            updated[idx].certificate_name = e.target.value;
                            setEditingData({ ...editingData, certifications: updated });
                          }}
                          className="text-xs font-semibold text-slate-800 dark:text-slate-100 bg-transparent dark:bg-slate-950 p-2 rounded border border-slate-200 dark:border-slate-700 focus:outline-none focus:border-brand-500"
                        />
                        <input
                          type="text"
                          value={c.issuing_organization}
                          placeholder="Issuing Organization"
                          onChange={(e) => {
                            const updated = [...(editingData.certifications || [])];
                            updated[idx].issuing_organization = e.target.value;
                            setEditingData({ ...editingData, certifications: updated });
                          }}
                          className="text-xs text-slate-600 dark:text-slate-200 bg-transparent dark:bg-slate-950 p-2 rounded border border-slate-200 dark:border-slate-700 focus:outline-none focus:border-brand-500"
                        />
                      </div>
                      <div className="flex items-center gap-2">
                        {getConfidenceBadge(c.confidence)}
                        <button
                          onClick={() => {
                            const updated = editingData.certifications?.filter((_, i) => i !== idx);
                            setEditingData({ ...editingData, certifications: updated });
                          }}
                          className="text-slate-400 dark:text-slate-500 hover:text-rose-600 dark:hover:text-rose-400 p-1"
                          title="Remove certification"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                    {c.evidence && (
                      <div className="text-[10px] text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-slate-800/60 p-2 rounded border border-slate-100 dark:border-slate-700/70 flex items-start gap-1">
                        <span className="font-semibold text-slate-600 dark:text-slate-300 flex-shrink-0">Quoted Evidence:</span>
                        <span className="italic truncate">&quot;{c.evidence}&quot;</span>
                      </div>
                    )}
                  </div>
                ))
              )}
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  const updated = [
                    ...(editingData.certifications || []),
                    { certificate_name: 'Certificate', issuing_organization: 'Issuer', confidence: 'medium' as const },
                  ];
                  setEditingData({ ...editingData, certifications: updated });
                }}
              >
                <Plus className="w-3.5 h-3.5 mr-1" /> Add Certification
              </Button>
            </div>
          )}

          {/* Tab 5: Education Editor */}
          {activeTab === 'education' && (
            <div className="space-y-4">
              {(!editingData.education || editingData.education.length === 0) ? (
                <div className="p-6 text-center text-slate-500 dark:text-slate-400 text-xs bg-slate-50 dark:bg-slate-800/50 border border-dashed border-slate-200 dark:border-slate-700 rounded-lg">
                  No education entries detected in resume. Click &quot;Add Education&quot; below to add your academic qualifications.
                </div>
              ) : (
                editingData.education.map((edu, idx) => (
                  <div key={idx} className="p-4 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 space-y-3 hover:border-brand-300 dark:hover:border-brand-600 transition-colors">
                    <div className="flex items-center justify-between">
                      <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <input
                          type="text"
                          value={edu.degree}
                          placeholder="Degree / Qualification"
                          onChange={(e) => {
                            const updated = [...(editingData.education || [])];
                            updated[idx].degree = e.target.value;
                            setEditingData({ ...editingData, education: updated });
                          }}
                          className="text-xs font-bold text-slate-800 dark:text-slate-100 bg-transparent dark:bg-slate-950 p-2 rounded border border-slate-200 dark:border-slate-700 focus:outline-none focus:border-brand-500"
                        />
                        <input
                          type="text"
                          value={edu.institution}
                          placeholder="Institution Name"
                          onChange={(e) => {
                            const updated = [...(editingData.education || [])];
                            updated[idx].institution = e.target.value;
                            setEditingData({ ...editingData, education: updated });
                          }}
                          className="text-xs text-slate-700 dark:text-slate-200 bg-transparent dark:bg-slate-950 p-2 rounded border border-slate-200 dark:border-slate-700 focus:outline-none focus:border-brand-500"
                        />
                      </div>
                      <div className="flex items-center gap-2 ml-2">
                        {getConfidenceBadge(edu.confidence)}
                        <button
                          onClick={() => {
                            const updated = editingData.education?.filter((_, i) => i !== idx);
                            setEditingData({ ...editingData, education: updated });
                          }}
                          className="text-slate-400 dark:text-slate-500 hover:text-rose-600 dark:hover:text-rose-400 p-1"
                          title="Remove education"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      <input
                        type="text"
                        value={edu.field_of_study || ''}
                        placeholder="Specialization / Branch"
                        onChange={(e) => {
                          const updated = [...(editingData.education || [])];
                          updated[idx].field_of_study = e.target.value;
                          setEditingData({ ...editingData, education: updated });
                        }}
                        className="text-xs text-slate-600 dark:text-slate-200 bg-transparent dark:bg-slate-950 p-2 rounded border border-slate-200 dark:border-slate-700 focus:outline-none focus:border-brand-500"
                      />
                      <div className="flex gap-2">
                        <input
                          type="number"
                          value={edu.start_year || ''}
                          placeholder="Start Year"
                          onChange={(e) => {
                            const updated = [...(editingData.education || [])];
                            updated[idx].start_year = parseInt(e.target.value) || undefined;
                            setEditingData({ ...editingData, education: updated });
                          }}
                          className="text-xs text-slate-600 dark:text-slate-200 bg-transparent dark:bg-slate-950 p-2 rounded border border-slate-200 dark:border-slate-700 focus:outline-none focus:border-brand-500 w-1/2"
                        />
                        <input
                          type="number"
                          value={edu.end_year || ''}
                          placeholder="End Year"
                          onChange={(e) => {
                            const updated = [...(editingData.education || [])];
                            updated[idx].end_year = parseInt(e.target.value) || undefined;
                            setEditingData({ ...editingData, education: updated });
                          }}
                          className="text-xs text-slate-600 dark:text-slate-200 bg-transparent dark:bg-slate-950 p-2 rounded border border-slate-200 dark:border-slate-700 focus:outline-none focus:border-brand-500 w-1/2"
                        />
                      </div>
                      <div>
                        <input
                          type="text"
                          value={edu.cgpa_or_percentage || ''}
                          placeholder="Score (e.g. 8.45 CGPA / 85%)"
                          onChange={(e) => {
                            const updated = [...(editingData.education || [])];
                            updated[idx].cgpa_or_percentage = e.target.value;
                            setEditingData({ ...editingData, education: updated });
                          }}
                          className="text-xs text-brand-600 dark:text-brand-400 bg-transparent dark:bg-slate-950 p-2 rounded border border-slate-200 dark:border-slate-700 focus:outline-none focus:border-brand-500 w-full"
                        />
                        {!edu.cgpa_or_percentage && (
                          <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-0.5">
                            CGPA not detected in resume. Official profile CGPA will remain unchanged.
                          </p>
                        )}
                      </div>
                    </div>
                    {edu.evidence && (
                      <div className="text-[10px] text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-slate-800/60 p-2 rounded border border-slate-100 dark:border-slate-700/70 flex items-start gap-1">
                        <span className="font-semibold text-slate-600 dark:text-slate-300 flex-shrink-0">Quoted Evidence:</span>
                        <span className="italic truncate">&quot;{edu.evidence}&quot;</span>
                      </div>
                    )}
                  </div>
                ))
              )}
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  const updated = [
                    ...(editingData.education || []),
                    { institution: 'Institution', degree: 'Degree', field_of_study: 'Engineering', confidence: 'medium' as const },
                  ];
                  setEditingData({ ...editingData, education: updated });
                }}
              >
                <Plus className="w-3.5 h-3.5 mr-1" /> Add Education
              </Button>
            </div>
          )}

          {/* Tab 6: Contact & Links Editor */}
          {activeTab === 'personal' && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <div className="flex items-center justify-between">
                    <label className="text-[11px] font-semibold text-slate-600 dark:text-slate-300">Full Name</label>
                    {!editingData.personal_info?.full_name && (
                      <span className="text-[10px] text-slate-400 dark:text-slate-500 italic">Not detected in resume</span>
                    )}
                  </div>
                  <input
                    type="text"
                    value={editingData.personal_info?.full_name || ''}
                    placeholder="Candidate Full Name"
                    onChange={(e) => {
                      setEditingData({
                        ...editingData,
                        personal_info: { ...editingData.personal_info, full_name: e.target.value },
                      });
                    }}
                    className="w-full text-xs p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 mt-1 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                </div>
                <div>
                  <div className="flex items-center justify-between">
                    <label className="text-[11px] font-semibold text-slate-600 dark:text-slate-300">Email Address</label>
                    {!editingData.personal_info?.email && (
                      <span className="text-[10px] text-slate-400 dark:text-slate-500 italic">Not detected in resume</span>
                    )}
                  </div>
                  <input
                    type="text"
                    value={editingData.personal_info?.email || ''}
                    placeholder="student@example.com"
                    onChange={(e) => {
                      setEditingData({
                        ...editingData,
                        personal_info: { ...editingData.personal_info, email: e.target.value },
                      });
                    }}
                    className="w-full text-xs p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 mt-1 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                </div>
                <div>
                  <div className="flex items-center justify-between">
                    <label className="text-[11px] font-semibold text-slate-600 dark:text-slate-300">LinkedIn Profile URL</label>
                    {!editingData.personal_info?.linkedin_url && (
                      <span className="text-[10px] text-slate-400 dark:text-slate-500 italic">Not detected</span>
                    )}
                  </div>
                  <input
                    type="text"
                    placeholder="https://linkedin.com/in/username"
                    value={editingData.personal_info?.linkedin_url || ''}
                    onChange={(e) => {
                      setEditingData({
                        ...editingData,
                        personal_info: { ...editingData.personal_info, linkedin_url: e.target.value },
                      });
                    }}
                    className="w-full text-xs p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 mt-1 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                </div>
                <div>
                  <div className="flex items-center justify-between">
                    <label className="text-[11px] font-semibold text-slate-600 dark:text-slate-300">GitHub Profile URL</label>
                    {!editingData.personal_info?.github_url && (
                      <span className="text-[10px] text-slate-400 dark:text-slate-500 italic">Not detected</span>
                    )}
                  </div>
                  <input
                    type="text"
                    placeholder="https://github.com/username"
                    value={editingData.personal_info?.github_url || ''}
                    onChange={(e) => {
                      setEditingData({
                        ...editingData,
                        personal_info: { ...editingData.personal_info, github_url: e.target.value },
                      });
                    }}
                    className="w-full text-xs p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 mt-1 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                </div>
              </div>
              {editingData.personal_info?.evidence && (
                <div className="text-[10px] text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-slate-800/60 p-2 rounded border border-slate-100 dark:border-slate-700/70 flex items-start gap-1 mt-2">
                  <span className="font-semibold text-slate-600 dark:text-slate-300 flex-shrink-0">Quoted Evidence:</span>
                  <span className="italic truncate">&quot;{editingData.personal_info.evidence}&quot;</span>
                </div>
              )}
            </div>
          )}

          {/* Bottom Callout & Approval Action */}
          <div className="mt-8 pt-4 border-t border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="text-[11px] text-slate-500 dark:text-slate-400">
              Syncing will commit confirmed skills, projects, and experiences to your normalized profile.
            </div>
            <div className="flex items-center gap-3">
              <Button variant="secondary" size="sm" onClick={handleSaveEdits}>
                Save Progress
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={handleApproveSync}
                disabled={isSyncing}
                className={selectedResume.parsing_status === 'approved' ? 'bg-emerald-700 hover:bg-emerald-800' : 'bg-emerald-600 hover:bg-emerald-700'}
              >
                <CheckCircle2 className="w-4 h-4 mr-1.5" />
                {isSyncing ? 'Synchronizing...' : selectedResume.parsing_status === 'approved' ? 'Profile Synchronized (Re-Sync)' : 'Approve & Synchronize to Profile'}
              </Button>
            </div>
          </div>
        </Card>
      )}
    </DashboardLayout>
  );
};

