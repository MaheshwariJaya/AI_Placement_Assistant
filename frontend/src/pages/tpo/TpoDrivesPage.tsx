import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  AlertCircle,
  Award,
  Briefcase,
  Building2,
  Calendar,
  CheckCircle2,
  ClipboardCheck,
  Clock,
  Download,
  Edit3,
  FileSpreadsheet,
  FileText,
  History,
  MapPin,
  Megaphone,
  Plus,
  RefreshCw,
  Search,
  Send,
  ShieldAlert,
  ShieldCheck,
  Trash2,
  UserCheck,
  UserPlus,
  Users,
  X,
} from 'lucide-react';
import { DashboardLayout } from '../../components/layout/DashboardLayout';
import { Card, CardHeader } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { applicationApi, driveApi } from '../../services/api';
import {
  DriveActivityCreatePayload,
  DriveActivityItem,
  DriveActivityStatus,
  DriveActivityType,
  DriveAnnouncementAudience,
  DriveAnnouncementItem,
  DriveApplicationItem,
  DriveAttendanceAuditItem,
  DriveAttendanceRecord,
  DriveAttendanceStatus,
  DriveCandidatesResponse,
  DriveDashboardResponse,
  DriveFormOptionsResponse,
  DriveLifecyclePhase,
  DriveMode,
  DriveRegistrationItem,
  DriveReportResponse,
  PlacementDrive,
  PlacementDriveCreatePayload,
  PlacementDriveDetail,
} from '../../types';

type WorkspaceTab =
  | 'overview'
  | 'candidates'
  | 'schedule'
  | 'attendance'
  | 'announcements'
  | 'reports';

const PHASE_LABELS: Record<DriveLifecyclePhase, string> = {
  draft: 'Draft',
  scheduled: 'Scheduled',
  registration_open: 'Registration Open',
  registration_closed: 'Registration Closed',
  ongoing: 'Ongoing',
  completed: 'Completed',
  cancelled: 'Cancelled',
};

const PHASE_BADGE: Record<
  DriveLifecyclePhase,
  'neutral' | 'info' | 'success' | 'warning' | 'brand' | 'danger'
> = {
  draft: 'neutral',
  scheduled: 'info',
  registration_open: 'success',
  registration_closed: 'warning',
  ongoing: 'brand',
  completed: 'success',
  cancelled: 'danger',
};

const ACTIVITY_TYPE_LABELS: Record<DriveActivityType, string> = {
  pre_placement_talk: 'Pre-Placement Talk (PPT)',
  company_presentation: 'Company Presentation',
  online_assessment: 'Online Assessment',
  offline_assessment: 'Offline Assessment',
  interview_round: 'Interview Round',
  other: 'Other Session',
};

function resolveDrivePhase(drive: PlacementDrive): DriveLifecyclePhase {
  if (drive.lifecycle_phase) return drive.lifecycle_phase;
  switch (drive.status) {
    case 'upcoming':
      return 'scheduled';
    case 'ongoing':
      return 'ongoing';
    case 'completed':
      return 'completed';
    case 'cancelled':
      return 'cancelled';
    default:
      return 'draft';
  }
}

function toDatetimeLocalValue(iso?: string | null): string {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(
    d.getHours()
  )}:${pad(d.getMinutes())}`;
}

function triggerBlobDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function getApiErrorMessage(err: unknown, fallback: string): string {
  if (err && typeof err === 'object') {
    const anyErr = err as {
      response?: { data?: { detail?: string; message?: string } };
      message?: string;
    };
    return (
      anyErr.response?.data?.message ||
      anyErr.response?.data?.detail ||
      anyErr.message ||
      fallback
    );
  }
  return fallback;
}

export const TpoDrivesPage: React.FC = () => {
  const [formOptions, setFormOptions] = useState<DriveFormOptionsResponse | null>(null);
  const [drives, setDrives] = useState<PlacementDrive[]>([]);
  const [selectedDriveId, setSelectedDriveId] = useState<number | null>(null);
  const [driveDetail, setDriveDetail] = useState<PlacementDriveDetail | null>(null);
  const [dashboard, setDashboard] = useState<DriveDashboardResponse | null>(null);
  const [candidates, setCandidates] = useState<DriveCandidatesResponse | null>(null);
  const [registrations, setRegistrations] = useState<DriveRegistrationItem[]>([]);
  const [driveApps, setDriveApps] = useState<DriveApplicationItem[]>([]);
  const [activities, setActivities] = useState<DriveActivityItem[]>([]);
  const [announcements, setAnnouncements] = useState<DriveAnnouncementItem[]>([]);
  const [report, setReport] = useState<DriveReportResponse | null>(null);

  const [selectedActivityId, setSelectedActivityId] = useState<number | null>(null);
  const [attendanceRecords, setAttendanceRecords] = useState<DriveAttendanceRecord[]>([]);
  const [attendanceAudit, setAttendanceAudit] = useState<DriveAttendanceAuditItem[]>([]);
  const [draftAttendance, setDraftAttendance] = useState<
    Record<number, { status: DriveAttendanceStatus; remarks: string }>
  >({});

  const [activeTab, setActiveTab] = useState<WorkspaceTab>('overview');
  const [candidateSubTab, setCandidateSubTab] = useState<'eligible' | 'ineligible' | 'applications'>(
    'eligible'
  );
  const [candidateSearch, setCandidateSearch] = useState('');
  const [selectedStudentIds, setSelectedStudentIds] = useState<number[]>([]);
  const [driveSearch, setDriveSearch] = useState('');
  const [phaseFilter, setPhaseFilter] = useState<string>('all');

  const [loadingList, setLoadingList] = useState(true);
  const [loadingWorkspace, setLoadingWorkspace] = useState(false);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);
  const [successBanner, setSuccessBanner] = useState<string | null>(null);

  // Create / Edit Drive Modal State
  const [showDriveModal, setShowDriveModal] = useState(false);
  const [editingDriveId, setEditingDriveId] = useState<number | null>(null);
  const [driveForm, setDriveForm] = useState<{
    name: string;
    academic_year: string;
    target_graduation_year: number;
    registration_start_date: string;
    registration_end_date: string;
    drive_start_date: string;
    drive_end_date: string;
    drive_mode: DriveMode;
    lifecycle_phase: DriveLifecyclePhase;
    venue_location: string;
    description: string;
    instructions: string;
    required_documents_text: string;
    target_graduation_batches: number[];
    participating_company_ids: number[];
    eligible_department_ids: number[];
    job_ids: number[];
  }>({
    name: '',
    academic_year: '2025-2026',
    target_graduation_year: new Date().getFullYear(),
    registration_start_date: '',
    registration_end_date: '',
    drive_start_date: '',
    drive_end_date: '',
    drive_mode: 'on_campus',
    lifecycle_phase: 'draft',
    venue_location: '',
    description: '',
    instructions: '',
    required_documents_text: 'Updated Resume\nCollege Photo ID',
    target_graduation_batches: [],
    participating_company_ids: [],
    eligible_department_ids: [],
    job_ids: [],
  });

  // Add Job Inline State
  const [jobToAddId, setJobToAddId] = useState<string>('');

  // Activity Form State
  const [activityForm, setActivityForm] = useState<{
    title: string;
    activity_type: DriveActivityType;
    mode: DriveMode;
    scheduled_start: string;
    scheduled_end: string;
    venue: string;
    meeting_link: string;
    description: string;
    job_id: string;
    company_id: string;
    coordinator_user_id: string;
    coordinator_name: string;
    coordinator_contact: string;
  }>({
    title: '',
    activity_type: 'pre_placement_talk',
    mode: 'on_campus',
    scheduled_start: '',
    scheduled_end: '',
    venue: '',
    meeting_link: '',
    description: '',
    job_id: '',
    company_id: '',
    coordinator_user_id: '',
    coordinator_name: '',
    coordinator_contact: '',
  });

  // Announcement Form State
  const [announcementForm, setAnnouncementForm] = useState<{
    title: string;
    message: string;
    target_audience: DriveAnnouncementAudience;
    job_id: string;
  }>({
    title: '',
    message: '',
    target_audience: 'all_registered',
    job_id: '',
  });

  const loadInitialData = useCallback(async () => {
    setLoadingList(true);
    setErrorBanner(null);
    try {
      const [opts, list] = await Promise.all([
        driveApi.getFormOptions(),
        driveApi.listDrives({ limit: 100 }),
      ]);
      setFormOptions(opts);
      setDrives(list);
      if (list.length > 0) {
        setSelectedDriveId((prev) =>
          prev && list.some((d) => d.id === prev) ? prev : list[0].id
        );
      } else {
        setSelectedDriveId(null);
      }
    } catch (err) {
      setErrorBanner(getApiErrorMessage(err, 'Failed to load placement drives workspace.'));
    } finally {
      setLoadingList(false);
    }
  }, []);

  const loadDriveWorkspace = useCallback(async (driveId: number) => {
    setLoadingWorkspace(true);
    setErrorBanner(null);
    try {
      const [detail, dash, cand, regs, apps, acts, anns] = await Promise.all([
        driveApi.getDrive(driveId),
        driveApi.getDashboard(driveId),
        driveApi.getCandidates(driveId),
        driveApi.getRegistrations(driveId),
        driveApi.getDriveApplications(driveId),
        driveApi.listActivities(driveId),
        driveApi.listAnnouncements(driveId),
      ]);
      setDriveDetail(detail);
      setDashboard(dash);
      setCandidates(cand);
      setRegistrations(regs);
      setDriveApps(apps.items);
      setActivities(acts);
      setAnnouncements(anns);
      setSelectedStudentIds([]);
      if (acts.length > 0) {
        setSelectedActivityId((prev) =>
          prev && acts.some((a) => a.id === prev) ? prev : acts[0].id
        );
      } else {
        setSelectedActivityId(null);
        setAttendanceRecords([]);
        setAttendanceAudit([]);
      }
    } catch (err) {
      setErrorBanner(getApiErrorMessage(err, 'Failed to load placement drive details.'));
    } finally {
      setLoadingWorkspace(false);
    }
  }, []);

  const loadActivityAttendance = useCallback(async (driveId: number, activityId: number) => {
    try {
      const [recs, audit] = await Promise.all([
        driveApi.getActivityAttendance(driveId, activityId),
        driveApi.getAttendanceAudit(driveId, activityId),
      ]);
      setAttendanceRecords(recs);
      setAttendanceAudit(audit);
      const nextDraft: Record<number, { status: DriveAttendanceStatus; remarks: string }> = {};
      recs.forEach((r) => {
        nextDraft[r.student_id] = {
          status: r.attendance_status,
          remarks: r.remarks || '',
        };
      });
      setDraftAttendance(nextDraft);
    } catch (err) {
      setErrorBanner(getApiErrorMessage(err, 'Failed to load attendance records.'));
    }
  }, []);

  const loadReport = useCallback(async (driveId: number) => {
    try {
      const rep = await driveApi.getReport(driveId);
      setReport(rep);
    } catch (err) {
      setErrorBanner(getApiErrorMessage(err, 'Failed to load drive report.'));
    }
  }, []);

  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  useEffect(() => {
    if (selectedDriveId !== null) {
      loadDriveWorkspace(selectedDriveId);
      setReport(null);
    }
  }, [selectedDriveId, loadDriveWorkspace]);

  useEffect(() => {
    if (selectedDriveId !== null && selectedActivityId !== null && activeTab === 'attendance') {
      loadActivityAttendance(selectedDriveId, selectedActivityId);
    }
  }, [selectedDriveId, selectedActivityId, activeTab, loadActivityAttendance]);

  useEffect(() => {
    if (selectedDriveId !== null && activeTab === 'reports' && !report) {
      loadReport(selectedDriveId);
    }
  }, [selectedDriveId, activeTab, report, loadReport]);

  const filteredDrives = useMemo(() => {
    return drives.filter((d) => {
      const phase = resolveDrivePhase(d);
      if (phaseFilter !== 'all' && phase !== phaseFilter) return false;
      if (driveSearch.trim()) {
        const q = driveSearch.trim().toLowerCase();
        return (
          d.name.toLowerCase().includes(q) ||
          d.academic_year.toLowerCase().includes(q) ||
          (d.venue_location || '').toLowerCase().includes(q)
        );
      }
      return true;
    });
  }, [drives, phaseFilter, driveSearch]);

  const openCreateModal = () => {
    const now = new Date();
    const regEnd = new Date(now.getTime() + 7 * 86400000);
    const drvStart = new Date(now.getTime() + 8 * 86400000);
    const drvEnd = new Date(now.getTime() + 10 * 86400000);
    const defaultBatch =
      formOptions?.graduation_batches[0] || new Date().getFullYear();

    setEditingDriveId(null);
    setDriveForm({
      name: '',
      academic_year: `${now.getFullYear() - 1}-${now.getFullYear()}`,
      target_graduation_year: defaultBatch,
      registration_start_date: toDatetimeLocalValue(now.toISOString()),
      registration_end_date: toDatetimeLocalValue(regEnd.toISOString()),
      drive_start_date: toDatetimeLocalValue(drvStart.toISOString()),
      drive_end_date: toDatetimeLocalValue(drvEnd.toISOString()),
      drive_mode: 'on_campus',
      lifecycle_phase: 'draft',
      venue_location: 'Campus Placement Cell / Seminar Hall',
      description: '',
      instructions: 'Carry college ID card and two hard copies of your updated resume.',
      required_documents_text: 'Updated Resume\nCollege Photo ID\nAcademic Transcripts',
      target_graduation_batches: defaultBatch ? [defaultBatch] : [],
      participating_company_ids: [],
      eligible_department_ids: [],
      job_ids: [],
    });
    setShowDriveModal(true);
  };

  const openEditModal = () => {
    if (!driveDetail) return;
    setEditingDriveId(driveDetail.id);
    setDriveForm({
      name: driveDetail.name,
      academic_year: driveDetail.academic_year,
      target_graduation_year: driveDetail.target_graduation_year,
      registration_start_date: toDatetimeLocalValue(driveDetail.registration_start_date),
      registration_end_date: toDatetimeLocalValue(driveDetail.registration_end_date),
      drive_start_date: toDatetimeLocalValue(driveDetail.drive_start_date),
      drive_end_date: toDatetimeLocalValue(driveDetail.drive_end_date),
      drive_mode: driveDetail.drive_mode,
      lifecycle_phase: resolveDrivePhase(driveDetail),
      venue_location: driveDetail.venue_location || '',
      description: driveDetail.description || '',
      instructions: driveDetail.instructions || driveDetail.guidelines || '',
      required_documents_text: (driveDetail.required_documents || []).join('\n'),
      target_graduation_batches: driveDetail.target_graduation_batches || [],
      participating_company_ids: driveDetail.participating_company_ids || [],
      eligible_department_ids: driveDetail.eligible_department_ids || [],
      job_ids: (driveDetail.jobs || []).filter((j) => j.is_active).map((j) => j.job_id),
    });
    setShowDriveModal(true);
  };

  const handleSaveDrive = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusyAction('save-drive');
    setErrorBanner(null);
    setSuccessBanner(null);
    try {
      const docs = driveForm.required_documents_text
        .split('\n')
        .map((s) => s.trim())
        .filter(Boolean);
      const regStartIso = new Date(driveForm.registration_start_date).toISOString();
      const regEndIso = new Date(driveForm.registration_end_date).toISOString();
      const drvStartIso = driveForm.drive_start_date
        ? new Date(driveForm.drive_start_date).toISOString()
        : null;
      const drvEndIso = driveForm.drive_end_date
        ? new Date(driveForm.drive_end_date).toISOString()
        : null;

      if (editingDriveId === null) {
        const payload: PlacementDriveCreatePayload = {
          name: driveForm.name.trim(),
          academic_year: driveForm.academic_year.trim(),
          target_graduation_year: Number(driveForm.target_graduation_year),
          registration_start_date: regStartIso,
          registration_end_date: regEndIso,
          drive_mode: driveForm.drive_mode,
          lifecycle_phase: driveForm.lifecycle_phase,
          drive_start_date: drvStartIso,
          drive_end_date: drvEndIso,
          venue_location: driveForm.venue_location.trim() || null,
          description: driveForm.description.trim() || null,
          instructions: driveForm.instructions.trim() || null,
          guidelines: driveForm.instructions.trim() || null,
          required_documents: docs,
          target_graduation_batches: driveForm.target_graduation_batches,
          participating_company_ids: driveForm.participating_company_ids,
          eligible_department_ids: driveForm.eligible_department_ids,
          job_ids: driveForm.job_ids,
        };
        const created = await driveApi.createDrive(payload);
        setShowDriveModal(false);
        setSuccessBanner(`Created placement drive "${created.name}".`);
        await loadInitialData();
        setSelectedDriveId(created.id);
      } else {
        const updated = await driveApi.updateDrive(editingDriveId, {
          name: driveForm.name.trim(),
          academic_year: driveForm.academic_year.trim(),
          target_graduation_year: Number(driveForm.target_graduation_year),
          registration_start_date: regStartIso,
          registration_end_date: regEndIso,
          drive_mode: driveForm.drive_mode,
          drive_start_date: drvStartIso,
          drive_end_date: drvEndIso,
          venue_location: driveForm.venue_location.trim() || null,
          description: driveForm.description.trim() || null,
          instructions: driveForm.instructions.trim() || null,
          guidelines: driveForm.instructions.trim() || null,
          required_documents: docs,
          target_graduation_batches: driveForm.target_graduation_batches,
          participating_company_ids: driveForm.participating_company_ids,
          eligible_department_ids: driveForm.eligible_department_ids,
        });
        setShowDriveModal(false);
        setSuccessBanner(`Updated placement drive "${updated.name}".`);
        await loadInitialData();
        await loadDriveWorkspace(updated.id);
      }
    } catch (err) {
      setErrorBanner(getApiErrorMessage(err, 'Could not save placement drive.'));
    } finally {
      setBusyAction(null);
    }
  };

  const handleLifecycleTransition = async (targetPhase: DriveLifecyclePhase) => {
    if (!driveDetail) return;
    setBusyAction(`transition-${targetPhase}`);
    setErrorBanner(null);
    setSuccessBanner(null);
    try {
      await driveApi.transitionLifecycle(driveDetail.id, targetPhase);
      setSuccessBanner(`Drive transitioned to "${PHASE_LABELS[targetPhase]}".`);
      await loadInitialData();
      await loadDriveWorkspace(driveDetail.id);
    } catch (err) {
      setErrorBanner(getApiErrorMessage(err, 'Drive lifecycle transition rejected.'));
    } finally {
      setBusyAction(null);
    }
  };

  const handleAddJob = async () => {
    if (!driveDetail || !jobToAddId) return;
    setBusyAction('add-job');
    setErrorBanner(null);
    try {
      await driveApi.addJobToDrive(driveDetail.id, Number(jobToAddId));
      setJobToAddId('');
      setSuccessBanner('Associated job with drive.');
      await loadDriveWorkspace(driveDetail.id);
    } catch (err) {
      setErrorBanner(getApiErrorMessage(err, 'Failed to associate job with drive.'));
    } finally {
      setBusyAction(null);
    }
  };

  const handleRemoveJob = async (jobId: number) => {
    if (!driveDetail) return;
    setBusyAction(`remove-job-${jobId}`);
    setErrorBanner(null);
    try {
      await driveApi.removeJobFromDrive(driveDetail.id, jobId);
      setSuccessBanner('Removed job from drive.');
      await loadDriveWorkspace(driveDetail.id);
    } catch (err) {
      setErrorBanner(getApiErrorMessage(err, 'Failed to remove job from drive.'));
    } finally {
      setBusyAction(null);
    }
  };

  const handleTpoBatchRegister = async () => {
    if (!driveDetail || selectedStudentIds.length === 0) return;
    setBusyAction('batch-register');
    setErrorBanner(null);
    setSuccessBanner(null);
    try {
      const created = await driveApi.tpoRegisterStudents(driveDetail.id, selectedStudentIds);
      setSuccessBanner(`Registered ${created.length} student(s) into the drive.`);
      await loadDriveWorkspace(driveDetail.id);
    } catch (err) {
      setErrorBanner(getApiErrorMessage(err, 'Failed to register selected students.'));
    } finally {
      setBusyAction(null);
    }
  };

  const handleScreenApplication = async (
    applicationId: number,
    decision: 'shortlisted' | 'rejected'
  ) => {
    if (!driveDetail) return;
    setBusyAction(`screen-${applicationId}`);
    setErrorBanner(null);
    try {
      await applicationApi.screenApplication(
        applicationId,
        decision,
        decision === 'shortlisted'
          ? 'Shortlisted by TPO institutional screening'
          : 'Did not clear TPO institutional screening'
      );
      setSuccessBanner(`Application #${applicationId} marked ${decision}.`);
      await loadDriveWorkspace(driveDetail.id);
    } catch (err) {
      setErrorBanner(getApiErrorMessage(err, 'Failed to update screening status.'));
    } finally {
      setBusyAction(null);
    }
  };

  const handleCreateActivity = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!driveDetail) return;
    setBusyAction('create-activity');
    setErrorBanner(null);
    setSuccessBanner(null);
    try {
      const payload: DriveActivityCreatePayload = {
        title: activityForm.title.trim(),
        activity_type: activityForm.activity_type,
        mode: activityForm.mode,
        scheduled_start: new Date(activityForm.scheduled_start).toISOString(),
        scheduled_end: new Date(activityForm.scheduled_end).toISOString(),
        venue: activityForm.venue.trim() || null,
        meeting_link: activityForm.meeting_link.trim() || null,
        description: activityForm.description.trim() || null,
        job_id: activityForm.job_id ? Number(activityForm.job_id) : null,
        company_id: activityForm.company_id ? Number(activityForm.company_id) : null,
        coordinator_user_id: activityForm.coordinator_user_id
          ? Number(activityForm.coordinator_user_id)
          : null,
        coordinator_name: activityForm.coordinator_name.trim(),
        coordinator_contact: activityForm.coordinator_contact.trim() || null,
      };
      const created = await driveApi.createActivity(driveDetail.id, payload);
      setActivityForm({
        title: '',
        activity_type: 'pre_placement_talk',
        mode: 'on_campus',
        scheduled_start: '',
        scheduled_end: '',
        venue: '',
        meeting_link: '',
        description: '',
        job_id: '',
        company_id: '',
        coordinator_user_id: '',
        coordinator_name: '',
        coordinator_contact: '',
      });
      setSelectedActivityId(created.id);
      setSuccessBanner(`Scheduled "${created.title}".`);
      await loadDriveWorkspace(driveDetail.id);
    } catch (err) {
      setErrorBanner(getApiErrorMessage(err, 'Failed to schedule drive activity.'));
    } finally {
      setBusyAction(null);
    }
  };

  const handleUpdateActivityStatus = async (
    activityId: number,
    nextStatus: DriveActivityStatus
  ) => {
    if (!driveDetail) return;
    setBusyAction(`act-status-${activityId}`);
    setErrorBanner(null);
    try {
      await driveApi.updateActivityStatus(driveDetail.id, activityId, nextStatus);
      setSuccessBanner(`Activity marked ${nextStatus.replace('_', ' ')}.`);
      await loadDriveWorkspace(driveDetail.id);
    } catch (err) {
      setErrorBanner(getApiErrorMessage(err, 'Failed to update activity status.'));
    } finally {
      setBusyAction(null);
    }
  };

  const handleSaveAttendanceBatch = async () => {
    if (!driveDetail || !selectedActivityId) return;
    const entries = Object.entries(draftAttendance).map(([studentId, val]) => ({
      student_id: Number(studentId),
      attendance_status: val.status,
      remarks: val.remarks.trim() || undefined,
    }));
    if (entries.length === 0) return;

    setBusyAction('save-attendance');
    setErrorBanner(null);
    setSuccessBanner(null);
    try {
      await driveApi.markActivityAttendance(driveDetail.id, selectedActivityId, entries);
      setSuccessBanner(`Recorded attendance for ${entries.length} student(s).`);
      await loadActivityAttendance(driveDetail.id, selectedActivityId);
      await loadDriveWorkspace(driveDetail.id);
    } catch (err) {
      setErrorBanner(getApiErrorMessage(err, 'Failed to record attendance.'));
    } finally {
      setBusyAction(null);
    }
  };

  const handleSendAnnouncement = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!driveDetail) return;
    setBusyAction('send-announcement');
    setErrorBanner(null);
    setSuccessBanner(null);
    try {
      const created = await driveApi.createAnnouncement(driveDetail.id, {
        title: announcementForm.title.trim(),
        message: announcementForm.message.trim(),
        target_audience: announcementForm.target_audience,
        job_id:
          announcementForm.target_audience === 'specific_job_applicants' &&
          announcementForm.job_id
            ? Number(announcementForm.job_id)
            : null,
      });
      setAnnouncementForm({
        title: '',
        message: '',
        target_audience: 'all_registered',
        job_id: '',
      });
      setSuccessBanner(`Announcement delivered to ${created.recipients_count} student(s).`);
      await loadDriveWorkspace(driveDetail.id);
    } catch (err) {
      setErrorBanner(getApiErrorMessage(err, 'Failed to dispatch drive announcement.'));
    } finally {
      setBusyAction(null);
    }
  };

  const handleExportPdf = async () => {
    if (!driveDetail) return;
    setBusyAction('export-pdf');
    try {
      const blob = await driveApi.exportReportPdf(driveDetail.id);
      triggerBlobDownload(blob, `placement_drive_${driveDetail.id}_report.pdf`);
    } catch (err) {
      setErrorBanner(getApiErrorMessage(err, 'Failed to export PDF report.'));
    } finally {
      setBusyAction(null);
    }
  };

  const handleExportExcel = async () => {
    if (!driveDetail) return;
    setBusyAction('export-excel');
    try {
      const blob = await driveApi.exportReportExcel(driveDetail.id);
      triggerBlobDownload(blob, `placement_drive_${driveDetail.id}_report.xlsx`);
    } catch (err) {
      setErrorBanner(getApiErrorMessage(err, 'Failed to export Excel report.'));
    } finally {
      setBusyAction(null);
    }
  };

  // Candidates filtered list
  const filteredEligible = useMemo(() => {
    const list = candidates?.eligible_candidates || [];
    if (!candidateSearch.trim()) return list;
    const q = candidateSearch.trim().toLowerCase();
    return list.filter(
      (c) =>
        c.full_name.toLowerCase().includes(q) ||
        c.roll_number.toLowerCase().includes(q) ||
        (c.department_code || '').toLowerCase().includes(q)
    );
  }, [candidates, candidateSearch]);

  const filteredIneligible = useMemo(() => {
    const list = candidates?.ineligible_audit_records || [];
    if (!candidateSearch.trim()) return list;
    const q = candidateSearch.trim().toLowerCase();
    return list.filter(
      (c) =>
        c.full_name.toLowerCase().includes(q) ||
        c.roll_number.toLowerCase().includes(q) ||
        (c.department_code || '').toLowerCase().includes(q)
    );
  }, [candidates, candidateSearch]);

  // Combined roster for attendance marking (registered + eligible candidates)
  const attendanceRoster = useMemo(() => {
    const map = new Map<
      number,
      { student_id: number; name: string; roll_number: string; dept?: string | null; is_registered: boolean }
    >();
    registrations.forEach((r) => {
      map.set(r.student_id, {
        student_id: r.student_id,
        name: r.student_name,
        roll_number: r.roll_number,
        dept: r.department_code,
        is_registered: true,
      });
    });
    (candidates?.eligible_candidates || []).forEach((c) => {
      if (!map.has(c.student_id)) {
        map.set(c.student_id, {
          student_id: c.student_id,
          name: c.full_name,
          roll_number: c.roll_number,
          dept: c.department_code,
          is_registered: c.is_registered,
        });
      }
    });
    return Array.from(map.values()).sort((a, b) => a.roll_number.localeCompare(b.roll_number));
  }, [registrations, candidates]);

  const availableJobsToAttach = useMemo(() => {
    const existingIds = new Set(
      (driveDetail?.jobs || []).filter((j) => j.is_active).map((j) => j.job_id)
    );
    return (formOptions?.jobs || []).filter((j) => !existingIds.has(j.id));
  }, [formOptions, driveDetail]);

  const toggleNumberInFormArray = (
    key:
      | 'participating_company_ids'
      | 'eligible_department_ids'
      | 'job_ids'
      | 'target_graduation_batches',
    val: number
  ) => {
    setDriveForm((prev) => {
      const exists = prev[key].includes(val);
      return {
        ...prev,
        [key]: exists ? prev[key].filter((x) => x !== val) : [...prev[key], val],
      };
    });
  };

  return (
    <DashboardLayout
      role="tpo"
      title="Placement Drive Management Workspace"
      subtitle="End-to-end campus drive lifecycle, deterministic candidate eligibility, activity scheduling, attendance audit & outcomes."
    >
      <div className="space-y-6">
        {/* Top Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
              Placement Drive Management Workspace
            </h1>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
              End-to-end campus drive lifecycle, deterministic candidate eligibility, activity scheduling, attendance audit & outcomes.
            </p>
          </div>
          <div className="flex items-center gap-2.5">
            <Button
              variant="outline"
              size="sm"
              onClick={loadInitialData}
              icon={<RefreshCw className="w-4 h-4" />}
            >
              Refresh
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={openCreateModal}
              icon={<Plus className="w-4 h-4" />}
            >
              Create Drive
            </Button>
          </div>
        </div>

        {/* Alerts */}
        {errorBanner && (
          <div className="flex items-start justify-between gap-3 rounded-xl border border-rose-200 dark:border-rose-800 bg-rose-50 dark:bg-rose-950/40 px-4 py-3 text-sm text-rose-700 dark:text-rose-300">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{errorBanner}</span>
            </div>
            <button onClick={() => setErrorBanner(null)} className="text-rose-500 hover:text-rose-700">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}
        {successBanner && (
          <div className="flex items-start justify-between gap-3 rounded-xl border border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950/40 px-4 py-3 text-sm text-emerald-700 dark:text-emerald-300">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{successBanner}</span>
            </div>
            <button onClick={() => setSuccessBanner(null)} className="text-emerald-500 hover:text-emerald-700">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Main 2-Column Workspace */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Drive Selector Sidebar */}
          <Card className="lg:col-span-4 xl:col-span-3">
            <CardHeader
              title="Campus Drives"
              subtitle={`${drives.length} institutional drive(s)`}
            />
            <div className="space-y-3 mb-4">
              <div className="relative">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="text"
                  value={driveSearch}
                  onChange={(e) => setDriveSearch(e.target.value)}
                  placeholder="Search drives..."
                  className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
              </div>
              <select
                value={phaseFilter}
                onChange={(e) => setPhaseFilter(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
              >
                <option value="all">All Lifecycle Stages</option>
                {(Object.keys(PHASE_LABELS) as DriveLifecyclePhase[]).map((p) => (
                  <option key={p} value={p}>
                    {PHASE_LABELS[p]}
                  </option>
                ))}
              </select>
            </div>

            {loadingList ? (
              <div className="py-10 text-center text-sm text-slate-500">Loading drives...</div>
            ) : filteredDrives.length === 0 ? (
              <div className="py-10 text-center text-sm text-slate-500">
                No placement drives match your filter.
              </div>
            ) : (
              <div className="space-y-2 max-h-[620px] overflow-y-auto pr-1">
                {filteredDrives.map((d) => {
                  const phase = resolveDrivePhase(d);
                  const active = d.id === selectedDriveId;
                  return (
                    <button
                      key={d.id}
                      onClick={() => setSelectedDriveId(d.id)}
                      className={`w-full text-left p-3 rounded-xl border transition-all ${
                        active
                          ? 'border-brand-500 bg-brand-50/70 dark:bg-brand-950/40 dark:border-brand-500'
                          : 'border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 bg-white dark:bg-slate-900'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <span className="font-semibold text-sm text-slate-900 dark:text-slate-100 line-clamp-2">
                          {d.name}
                        </span>
                        <Badge variant={PHASE_BADGE[phase]} size="sm">
                          {PHASE_LABELS[phase]}
                        </Badge>
                      </div>
                      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500 dark:text-slate-400">
                        <span>{d.academic_year}</span>
                        <span>Batch {d.target_graduation_year}</span>
                        <span>{d.total_jobs} jobs</span>
                        <span>{d.total_applications} apps</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </Card>

          {/* Right Selected Drive Workspace */}
          <div className="lg:col-span-8 xl:col-span-9 space-y-6">
            {!selectedDriveId || !driveDetail ? (
              <Card>
                <div className="py-16 text-center space-y-3">
                  <Calendar className="w-10 h-10 text-slate-400 mx-auto" />
                  <h3 className="text-lg font-semibold text-slate-800 dark:text-slate-200">
                    Select or Create a Placement Drive
                  </h3>
                  <p className="text-sm text-slate-500 dark:text-slate-400 max-w-md mx-auto">
                    Create a new campus recruitment drive or choose an existing drive on the left to manage eligibility, schedule rounds, record attendance, and publish reports.
                  </p>
                  <Button variant="primary" size="sm" onClick={openCreateModal} icon={<Plus className="w-4 h-4" />}>
                    Create First Drive
                  </Button>
                </div>
              </Card>
            ) : (
              <>
                {/* Selected Drive Top Header & Lifecycle Transitions */}
                <Card>
                  <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
                    <div>
                      <div className="flex flex-wrap items-center gap-2.5">
                        <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">
                          {driveDetail.name}
                        </h2>
                        <Badge variant={PHASE_BADGE[resolveDrivePhase(driveDetail)]}>
                          {PHASE_LABELS[resolveDrivePhase(driveDetail)]}
                        </Badge>
                        <Badge variant="neutral">
                          {driveDetail.drive_mode.replace('_', ' ').toUpperCase()}
                        </Badge>
                      </div>
                      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500 dark:text-slate-400">
                        <span className="inline-flex items-center gap-1">
                          <Calendar className="w-3.5 h-3.5" />
                          Reg: {new Date(driveDetail.registration_start_date).toLocaleDateString()} –{' '}
                          {new Date(driveDetail.registration_end_date).toLocaleDateString()}
                        </span>
                        {driveDetail.venue_location && (
                          <span className="inline-flex items-center gap-1">
                            <MapPin className="w-3.5 h-3.5" />
                            {driveDetail.venue_location}
                          </span>
                        )}
                        <span>
                          Batches:{' '}
                          {(driveDetail.target_graduation_batches?.length
                            ? driveDetail.target_graduation_batches
                            : [driveDetail.target_graduation_year]
                          ).join(', ')}
                        </span>
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={openEditModal}
                        icon={<Edit3 className="w-3.5 h-3.5" />}
                      >
                        Edit Drive
                      </Button>
                      {(dashboard?.allowed_next_phases || []).map((nextPhase) => (
                        <Button
                          key={nextPhase}
                          variant={nextPhase === 'cancelled' ? 'danger' : 'primary'}
                          size="sm"
                          disabled={busyAction !== null}
                          onClick={() => handleLifecycleTransition(nextPhase)}
                        >
                          Move to {PHASE_LABELS[nextPhase]}
                        </Button>
                      ))}
                    </div>
                  </div>

                  {/* Workspace Tabs */}
                  <div className="mt-6 pt-4 border-t border-slate-100 dark:border-slate-800 flex flex-wrap gap-2">
                    {(
                      [
                        { id: 'overview', label: 'Overview & Funnel', icon: Briefcase },
                        { id: 'candidates', label: 'Candidates & Screening', icon: Users },
                        { id: 'schedule', label: 'Schedule & Coordinators', icon: Clock },
                        { id: 'attendance', label: 'Attendance & Audit', icon: ClipboardCheck },
                        { id: 'announcements', label: 'Announcements', icon: Megaphone },
                        { id: 'reports', label: 'Reports & Export', icon: FileText },
                      ] as const
                    ).map((tab) => {
                      const Icon = tab.icon;
                      const active = activeTab === tab.id;
                      return (
                        <button
                          key={tab.id}
                          onClick={() => setActiveTab(tab.id)}
                          className={`inline-flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-colors ${
                            active
                              ? 'bg-brand-600 text-white'
                              : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
                          }`}
                        >
                          <Icon className="w-4 h-4" />
                          {tab.label}
                        </button>
                      );
                    })}
                  </div>
                </Card>

                {loadingWorkspace && (
                  <div className="text-xs text-slate-500 dark:text-slate-400">
                    Syncing drive telemetry...
                  </div>
                )}

                {/* TAB 1: OVERVIEW & FUNNEL */}
                {activeTab === 'overview' && dashboard && (
                  <div className="space-y-6">
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                      {[
                        { label: 'Registered Students', value: dashboard.total_registered_students, icon: UserPlus },
                        { label: 'Eligible Students', value: dashboard.eligible_students, icon: ShieldCheck },
                        { label: 'Ineligible Students', value: dashboard.ineligible_students, icon: ShieldAlert },
                        { label: 'Applications Received', value: dashboard.applications_received, icon: FileText },
                        { label: 'Shortlisted Candidates', value: dashboard.shortlisted_candidates, icon: UserCheck },
                        {
                          label: 'Interviews (Sched / Done)',
                          value: `${dashboard.interview_scheduled_count} / ${dashboard.interview_completed_count}`,
                          icon: Calendar,
                        },
                        { label: 'Offers Released', value: dashboard.offers_released, icon: Megaphone },
                        { label: 'Final Placements', value: dashboard.final_placements, icon: Award },
                      ].map((kpi) => {
                        const Icon = kpi.icon;
                        return (
                          <Card key={kpi.label} className="p-4">
                            <div className="flex items-center justify-between">
                              <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
                                {kpi.label}
                              </span>
                              <Icon className="w-4 h-4 text-brand-500" />
                            </div>
                            <div className="mt-2 text-2xl font-bold text-slate-900 dark:text-slate-100">
                              {kpi.value}
                            </div>
                          </Card>
                        );
                      })}
                    </div>

                    {/* Associated Jobs + Add Job */}
                    <Card>
                      <CardHeader
                        title="Participating Job Roles"
                        subtitle="Roles attached to this placement drive and recruitment funnel per role"
                      />
                      <div className="flex flex-col sm:flex-row gap-2 mb-4">
                        <select
                          value={jobToAddId}
                          onChange={(e) => setJobToAddId(e.target.value)}
                          className="flex-1 px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                        >
                          <option value="">Select published/eligible job to attach...</option>
                          {availableJobsToAttach.map((j) => (
                            <option key={j.id} value={j.id}>
                              {j.title} — {j.company_name} (Min CGPA {j.min_cgpa})
                            </option>
                          ))}
                        </select>
                        <Button
                          variant="primary"
                          size="sm"
                          disabled={!jobToAddId || busyAction !== null}
                          onClick={handleAddJob}
                          icon={<Plus className="w-4 h-4" />}
                        >
                          Attach Job
                        </Button>
                      </div>

                      {dashboard.job_breakdown.length === 0 ? (
                        <p className="text-sm text-slate-500">No active jobs attached yet.</p>
                      ) : (
                        <div className="overflow-x-auto">
                          <table className="w-full text-sm">
                            <thead>
                              <tr className="border-b border-slate-200 dark:border-slate-800 text-left text-xs uppercase text-slate-500">
                                <th className="py-2 pr-4">Role & Company</th>
                                <th className="py-2 px-3">Apps</th>
                                <th className="py-2 px-3">Shortlisted</th>
                                <th className="py-2 px-3">Interviews</th>
                                <th className="py-2 px-3">Offered</th>
                                <th className="py-2 px-3">Accepted</th>
                                <th className="py-2 pl-3 text-right">Action</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                              {dashboard.job_breakdown.map((jb) => (
                                <tr key={jb.job_id}>
                                  <td className="py-2.5 pr-4">
                                    <div className="font-medium text-slate-900 dark:text-slate-100">
                                      {jb.title}
                                    </div>
                                    <div className="text-xs text-slate-500">{jb.company_name}</div>
                                  </td>
                                  <td className="py-2.5 px-3">{jb.applications_count}</td>
                                  <td className="py-2.5 px-3">{jb.shortlisted_count}</td>
                                  <td className="py-2.5 px-3">{jb.interview_count}</td>
                                  <td className="py-2.5 px-3">{jb.offered_count}</td>
                                  <td className="py-2.5 px-3 font-semibold text-emerald-600 dark:text-emerald-400">
                                    {jb.accepted_count}
                                  </td>
                                  <td className="py-2.5 pl-3 text-right">
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      disabled={busyAction !== null}
                                      onClick={() => handleRemoveJob(jb.job_id)}
                                      icon={<Trash2 className="w-3.5 h-3.5 text-rose-500" />}
                                    >
                                      Remove
                                    </Button>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </Card>

                    {/* Instructions & Required Documents */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <Card>
                        <CardHeader title="Drive Instructions" />
                        <p className="text-sm text-slate-600 dark:text-slate-300 whitespace-pre-line">
                          {driveDetail.instructions || driveDetail.guidelines || 'No instructions configured.'}
                        </p>
                      </Card>
                      <Card>
                        <CardHeader title="Required Documents" />
                        {driveDetail.required_documents?.length ? (
                          <ul className="space-y-1.5 text-sm text-slate-700 dark:text-slate-300">
                            {driveDetail.required_documents.map((doc) => (
                              <li key={doc} className="flex items-center gap-2">
                                <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                                <span>{doc}</span>
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p className="text-sm text-slate-500">No document checklist set.</p>
                        )}
                      </Card>
                    </div>
                  </div>
                )}

                {/* TAB 2: CANDIDATES & SCREENING */}
                {activeTab === 'candidates' && candidates && (
                  <Card>
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
                      <div className="flex flex-wrap gap-2">
                        <Button
                          variant={candidateSubTab === 'eligible' ? 'primary' : 'outline'}
                          size="sm"
                          onClick={() => setCandidateSubTab('eligible')}
                        >
                          Eligible ({candidates.eligible_candidates.length})
                        </Button>
                        <Button
                          variant={candidateSubTab === 'ineligible' ? 'primary' : 'outline'}
                          size="sm"
                          onClick={() => setCandidateSubTab('ineligible')}
                        >
                          Ineligible Audit ({candidates.ineligible_audit_records.length})
                        </Button>
                        <Button
                          variant={candidateSubTab === 'applications' ? 'primary' : 'outline'}
                          size="sm"
                          onClick={() => setCandidateSubTab('applications')}
                        >
                          Drive Applications ({driveApps.length})
                        </Button>
                      </div>

                      <div className="flex items-center gap-2">
                        {candidateSubTab === 'eligible' && selectedStudentIds.length > 0 && (
                          <Button
                            variant="primary"
                            size="sm"
                            disabled={busyAction !== null}
                            onClick={handleTpoBatchRegister}
                            icon={<UserPlus className="w-4 h-4" />}
                          >
                            Register Selected ({selectedStudentIds.length})
                          </Button>
                        )}
                        <div className="relative">
                          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                          <input
                            type="text"
                            value={candidateSearch}
                            onChange={(e) => setCandidateSearch(e.target.value)}
                            placeholder="Filter name / roll no..."
                            className="pl-9 pr-3 py-1.5 text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                          />
                        </div>
                      </div>
                    </div>

                    {candidateSubTab === 'eligible' && (
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="border-b border-slate-200 dark:border-slate-800 text-left text-xs uppercase text-slate-500">
                              <th className="py-2 pr-2">Select</th>
                              <th className="py-2 px-3">Student</th>
                              <th className="py-2 px-3">Dept / Batch</th>
                              <th className="py-2 px-3">CGPA / Backlogs</th>
                              <th className="py-2 px-3">Registration</th>
                              <th className="py-2 px-3">Pipeline Status</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                            {filteredEligible.map((c) => {
                              const checked = selectedStudentIds.includes(c.student_id);
                              return (
                                <tr key={c.student_id}>
                                  <td className="py-2.5 pr-2">
                                    <input
                                      type="checkbox"
                                      disabled={c.is_registered}
                                      checked={checked}
                                      onChange={() =>
                                        setSelectedStudentIds((prev) =>
                                          prev.includes(c.student_id)
                                            ? prev.filter((x) => x !== c.student_id)
                                            : [...prev, c.student_id]
                                        )
                                      }
                                    />
                                  </td>
                                  <td className="py-2.5 px-3">
                                    <div className="font-medium text-slate-900 dark:text-slate-100">
                                      {c.full_name}
                                    </div>
                                    <div className="text-xs text-slate-500">{c.roll_number}</div>
                                  </td>
                                  <td className="py-2.5 px-3">
                                    {c.department_code || '—'} · {c.graduation_year}
                                  </td>
                                  <td className="py-2.5 px-3">
                                    {c.cgpa.toFixed(2)} CGPA · {c.active_backlogs} backlogs
                                  </td>
                                  <td className="py-2.5 px-3">
                                    {c.is_registered ? (
                                      <Badge variant="success" size="sm">
                                        Registered
                                      </Badge>
                                    ) : (
                                      <Badge variant="neutral" size="sm">
                                        Not Registered
                                      </Badge>
                                    )}
                                  </td>
                                  <td className="py-2.5 px-3">
                                    {c.final_outcome ? (
                                      <Badge variant="success" size="sm">
                                        {c.final_outcome}
                                      </Badge>
                                    ) : c.latest_application_status ? (
                                      <Badge variant="info" size="sm">
                                        {c.latest_application_status.replace(/_/g, ' ')}
                                      </Badge>
                                    ) : (
                                      <span className="text-xs text-slate-400">No applications</span>
                                    )}
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    )}

                    {candidateSubTab === 'ineligible' && (
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="border-b border-slate-200 dark:border-slate-800 text-left text-xs uppercase text-slate-500">
                              <th className="py-2 pr-3">Student</th>
                              <th className="py-2 px-3">Dept / CGPA</th>
                              <th className="py-2 px-3">Deterministic Audit Reasons</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                            {filteredIneligible.map((c) => (
                              <tr key={c.student_id}>
                                <td className="py-2.5 pr-3">
                                  <div className="font-medium text-slate-900 dark:text-slate-100">
                                    {c.full_name}
                                  </div>
                                  <div className="text-xs text-slate-500">{c.roll_number}</div>
                                </td>
                                <td className="py-2.5 px-3">
                                  {c.department_code || '—'} · {c.cgpa.toFixed(2)} CGPA ({c.active_backlogs} backlogs)
                                </td>
                                <td className="py-2.5 px-3">
                                  <ul className="list-disc pl-4 text-xs text-rose-600 dark:text-rose-400 space-y-0.5">
                                    {c.ineligible_reasons.map((r) => (
                                      <li key={r}>{r}</li>
                                    ))}
                                  </ul>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}

                    {candidateSubTab === 'applications' && (
                      <div className="overflow-x-auto">
                        {driveApps.length === 0 ? (
                          <p className="text-sm text-slate-500 py-6 text-center">
                            No applications submitted under this drive yet.
                          </p>
                        ) : (
                          <table className="w-full text-sm">
                            <thead>
                              <tr className="border-b border-slate-200 dark:border-slate-800 text-left text-xs uppercase text-slate-500">
                                <th className="py-2 pr-3">Applicant</th>
                                <th className="py-2 px-3">Job Role</th>
                                <th className="py-2 px-3">Match</th>
                                <th className="py-2 px-3">TPO Screening</th>
                                <th className="py-2 px-3">Stage</th>
                                <th className="py-2 pl-3 text-right">TPO Action</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                              {driveApps.map((app) => (
                                <tr key={app.id}>
                                  <td className="py-2.5 pr-3">
                                    <div className="font-medium text-slate-900 dark:text-slate-100">
                                      {app.student_name || `Student #${app.student_id}`}
                                    </div>
                                    <div className="text-xs text-slate-500">
                                      {app.student_roll_number} · {app.student_department || '—'}
                                    </div>
                                  </td>
                                  <td className="py-2.5 px-3">
                                    <div>{app.job_title}</div>
                                    <div className="text-xs text-slate-500">{app.company_name}</div>
                                  </td>
                                  <td className="py-2.5 px-3">
                                    {app.compatibility_score_at_application != null
                                      ? `${app.compatibility_score_at_application.toFixed(0)}%`
                                      : '—'}
                                  </td>
                                  <td className="py-2.5 px-3">
                                    <Badge
                                      variant={
                                        app.tpo_screening_status === 'shortlisted'
                                          ? 'success'
                                          : app.tpo_screening_status === 'rejected'
                                          ? 'danger'
                                          : 'warning'
                                      }
                                      size="sm"
                                    >
                                      {app.tpo_screening_status}
                                    </Badge>
                                  </td>
                                  <td className="py-2.5 px-3 text-xs">
                                    {app.current_status.replace(/_/g, ' ')}
                                  </td>
                                  <td className="py-2.5 pl-3 text-right">
                                    {app.tpo_screening_status === 'pending' ? (
                                      <div className="inline-flex gap-1.5">
                                        <Button
                                          variant="primary"
                                          size="sm"
                                          disabled={busyAction !== null}
                                          onClick={() => handleScreenApplication(app.id, 'shortlisted')}
                                        >
                                          Shortlist
                                        </Button>
                                        <Button
                                          variant="danger"
                                          size="sm"
                                          disabled={busyAction !== null}
                                          onClick={() => handleScreenApplication(app.id, 'rejected')}
                                        >
                                          Reject
                                        </Button>
                                      </div>
                                    ) : (
                                      <span className="text-xs text-slate-400">Screened</span>
                                    )}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        )}
                      </div>
                    )}
                  </Card>
                )}

                {/* TAB 3: SCHEDULE & COORDINATORS */}
                {activeTab === 'schedule' && (
                  <div className="space-y-6">
                    <Card>
                      <CardHeader
                        title="Schedule Drive Session & Assign Coordinator"
                        subtitle="Pre-placement talks, company presentations, assessments & interview rounds"
                      />
                      <form onSubmit={handleCreateActivity} className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">
                            Activity Title *
                          </label>
                          <input
                            required
                            value={activityForm.title}
                            onChange={(e) => setActivityForm((p) => ({ ...p, title: e.target.value }))}
                            placeholder="e.g. Acme Corp Pre-Placement Talk"
                            className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800"
                          />
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                          <div>
                            <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">
                              Activity Type
                            </label>
                            <select
                              value={activityForm.activity_type}
                              onChange={(e) =>
                                setActivityForm((p) => ({
                                  ...p,
                                  activity_type: e.target.value as DriveActivityType,
                                }))
                              }
                              className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800"
                            >
                              {(Object.keys(ACTIVITY_TYPE_LABELS) as DriveActivityType[]).map((t) => (
                                <option key={t} value={t}>
                                  {ACTIVITY_TYPE_LABELS[t]}
                                </option>
                              ))}
                            </select>
                          </div>
                          <div>
                            <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">
                              Mode
                            </label>
                            <select
                              value={activityForm.mode}
                              onChange={(e) =>
                                setActivityForm((p) => ({ ...p, mode: e.target.value as DriveMode }))
                              }
                              className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800"
                            >
                              <option value="on_campus">On-Campus</option>
                              <option value="virtual">Virtual / Online</option>
                              <option value="hybrid">Hybrid</option>
                            </select>
                          </div>
                        </div>

                        <div>
                          <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">
                            Start Time *
                          </label>
                          <input
                            type="datetime-local"
                            required
                            value={activityForm.scheduled_start}
                            onChange={(e) =>
                              setActivityForm((p) => ({ ...p, scheduled_start: e.target.value }))
                            }
                            className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800"
                          />
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">
                            End Time *
                          </label>
                          <input
                            type="datetime-local"
                            required
                            value={activityForm.scheduled_end}
                            onChange={(e) =>
                              setActivityForm((p) => ({ ...p, scheduled_end: e.target.value }))
                            }
                            className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800"
                          />
                        </div>

                        <div>
                          <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">
                            Venue / Lab Room
                          </label>
                          <input
                            value={activityForm.venue}
                            onChange={(e) => setActivityForm((p) => ({ ...p, venue: e.target.value }))}
                            placeholder="Seminar Hall B / CS Lab 2"
                            className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800"
                          />
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">
                            Online Meeting Link (optional)
                          </label>
                          <input
                            value={activityForm.meeting_link}
                            onChange={(e) =>
                              setActivityForm((p) => ({ ...p, meeting_link: e.target.value }))
                            }
                            placeholder="https://meet.google.com/..."
                            className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800"
                          />
                        </div>

                        <div>
                          <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">
                            Assign Institutional Coordinator (for Attendance Authority)
                          </label>
                          <select
                            value={activityForm.coordinator_user_id}
                            onChange={(e) => {
                              const uid = e.target.value;
                              const match = formOptions?.coordinators.find(
                                (c) => String(c.id) === uid
                              );
                              setActivityForm((p) => ({
                                ...p,
                                coordinator_user_id: uid,
                                coordinator_name: match ? match.full_name : p.coordinator_name,
                                coordinator_contact: match ? match.email : p.coordinator_contact,
                              }));
                            }}
                            className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800"
                          >
                            <option value="">Select staff coordinator (optional)...</option>
                            {(formOptions?.coordinators || []).map((c) => (
                              <option key={c.id} value={c.id}>
                                {c.full_name} ({c.email})
                              </option>
                            ))}
                          </select>
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                          <div>
                            <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">
                              Coordinator Name *
                            </label>
                            <input
                              required
                              value={activityForm.coordinator_name}
                              onChange={(e) =>
                                setActivityForm((p) => ({
                                  ...p,
                                  coordinator_name: e.target.value,
                                }))
                              }
                              placeholder="Dr. Anita Verma"
                              className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800"
                            />
                          </div>
                          <div>
                            <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">
                              Coordinator Contact
                            </label>
                            <input
                              value={activityForm.coordinator_contact}
                              onChange={(e) =>
                                setActivityForm((p) => ({
                                  ...p,
                                  coordinator_contact: e.target.value,
                                }))
                              }
                              placeholder="Ext 204 / email"
                              className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800"
                            />
                          </div>
                        </div>

                        <div className="md:col-span-2 flex justify-end">
                          <Button
                            type="submit"
                            variant="primary"
                            size="sm"
                            disabled={busyAction !== null}
                            icon={<Plus className="w-4 h-4" />}
                          >
                            Schedule Session
                          </Button>
                        </div>
                      </form>
                    </Card>

                    <Card>
                      <CardHeader
                        title="Scheduled Drive Sessions"
                        subtitle={`${activities.length} session(s) configured`}
                      />
                      {activities.length === 0 ? (
                        <p className="text-sm text-slate-500">No sessions scheduled yet.</p>
                      ) : (
                        <div className="space-y-3">
                          {activities.map((act) => (
                            <div
                              key={act.id}
                              className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 flex flex-col md:flex-row md:items-center md:justify-between gap-3"
                            >
                              <div>
                                <div className="flex flex-wrap items-center gap-2">
                                  <span className="font-semibold text-slate-900 dark:text-slate-100">
                                    {act.title}
                                  </span>
                                  <Badge variant="info" size="sm">
                                    {ACTIVITY_TYPE_LABELS[act.activity_type]}
                                  </Badge>
                                  <Badge
                                    variant={
                                      act.status === 'completed'
                                        ? 'success'
                                        : act.status === 'cancelled'
                                        ? 'danger'
                                        : 'brand'
                                    }
                                    size="sm"
                                  >
                                    {act.status.replace('_', ' ')}
                                  </Badge>
                                </div>
                                <div className="mt-1.5 text-xs text-slate-500 dark:text-slate-400 flex flex-wrap gap-x-4 gap-y-1">
                                  <span>
                                    {new Date(act.scheduled_start).toLocaleString()} –{' '}
                                    {new Date(act.scheduled_end).toLocaleTimeString()}
                                  </span>
                                  {act.venue && <span>Venue: {act.venue}</span>}
                                  <span>Coordinator: {act.coordinator_name}</span>
                                  <span>
                                    Attendance: {act.present_count} P / {act.absent_count} A /{' '}
                                    {act.late_count} L / {act.excused_count} E
                                  </span>
                                </div>
                              </div>
                              <div className="flex flex-wrap items-center gap-1.5">
                                {act.status === 'scheduled' && (
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    disabled={busyAction !== null}
                                    onClick={() => handleUpdateActivityStatus(act.id, 'in_progress')}
                                  >
                                    Start
                                  </Button>
                                )}
                                {(act.status === 'scheduled' || act.status === 'in_progress') && (
                                  <>
                                    <Button
                                      variant="primary"
                                      size="sm"
                                      disabled={busyAction !== null}
                                      onClick={() => handleUpdateActivityStatus(act.id, 'completed')}
                                    >
                                      Complete
                                    </Button>
                                    <Button
                                      variant="danger"
                                      size="sm"
                                      disabled={busyAction !== null}
                                      onClick={() => handleUpdateActivityStatus(act.id, 'cancelled')}
                                    >
                                      Cancel
                                    </Button>
                                  </>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </Card>
                  </div>
                )}

                {/* TAB 4: ATTENDANCE & AUDIT */}
                {activeTab === 'attendance' && (
                  <div className="space-y-6">
                    <Card>
                      <CardHeader
                        title="Record Activity Attendance"
                        subtitle="Coordinator-authorized attendance tracking with immutable audit history"
                      />
                      {activities.length === 0 ? (
                        <p className="text-sm text-slate-500">
                          Schedule at least one activity in the Schedule tab before recording attendance.
                        </p>
                      ) : (
                        <>
                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
                            <select
                              value={selectedActivityId ?? ''}
                              onChange={(e) => setSelectedActivityId(Number(e.target.value))}
                              className="flex-1 px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800"
                            >
                              {activities.map((a) => (
                                <option key={a.id} value={a.id}>
                                  {a.title} ({new Date(a.scheduled_start).toLocaleString()})
                                </option>
                              ))}
                            </select>
                            <Button
                              variant="primary"
                              size="sm"
                              disabled={busyAction !== null || Object.keys(draftAttendance).length === 0}
                              onClick={handleSaveAttendanceBatch}
                              icon={<ClipboardCheck className="w-4 h-4" />}
                            >
                              Save Attendance ({Object.keys(draftAttendance).length})
                            </Button>
                          </div>

                          <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                              <thead>
                                <tr className="border-b border-slate-200 dark:border-slate-800 text-left text-xs uppercase text-slate-500">
                                  <th className="py-2 pr-3">Student</th>
                                  <th className="py-2 px-3">Dept</th>
                                  <th className="py-2 px-3">Status</th>
                                  <th className="py-2 px-3">Remarks</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                                {attendanceRoster.map((st) => {
                                  const current = draftAttendance[st.student_id] || {
                                    status: '' as DriveAttendanceStatus,
                                    remarks: '',
                                  };
                                  return (
                                    <tr key={st.student_id}>
                                      <td className="py-2.5 pr-3">
                                        <div className="font-medium text-slate-900 dark:text-slate-100">
                                          {st.name}
                                        </div>
                                        <div className="text-xs text-slate-500">{st.roll_number}</div>
                                      </td>
                                      <td className="py-2.5 px-3">{st.dept || '—'}</td>
                                      <td className="py-2.5 px-3">
                                        <div className="flex flex-wrap gap-1.5">
                                          {(
                                            ['present', 'absent', 'late', 'excused'] as DriveAttendanceStatus[]
                                          ).map((stVal) => (
                                            <button
                                              key={stVal}
                                              type="button"
                                              onClick={() =>
                                                setDraftAttendance((prev) => ({
                                                  ...prev,
                                                  [st.student_id]: {
                                                    status: stVal,
                                                    remarks: prev[st.student_id]?.remarks || '',
                                                  },
                                                }))
                                              }
                                              className={`px-2.5 py-1 rounded-md text-xs font-medium capitalize border ${
                                                current.status === stVal
                                                  ? 'bg-brand-600 text-white border-brand-600'
                                                  : 'border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300'
                                              }`}
                                            >
                                              {stVal}
                                            </button>
                                          ))}
                                        </div>
                                      </td>
                                      <td className="py-2.5 px-3">
                                        <input
                                          type="text"
                                          value={current.remarks}
                                          onChange={(e) =>
                                            setDraftAttendance((prev) => ({
                                              ...prev,
                                              [st.student_id]: {
                                                status: prev[st.student_id]?.status || 'present',
                                                remarks: e.target.value,
                                              },
                                            }))
                                          }
                                          placeholder="Optional note..."
                                          className="w-full px-2.5 py-1 text-xs rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800"
                                        />
                                      </td>
                                    </tr>
                                  );
                                })}
                              </tbody>
                            </table>
                          </div>
                        </>
                      )}
                    </Card>

                    {/* Immutable Attendance Audit History */}
                    <Card>
                      <CardHeader
                        title="Attendance Audit History (Immutable)"
                        subtitle={`${attendanceAudit.length} audit entry(ies) for this session`}
                      />
                      {attendanceAudit.length === 0 ? (
                        <p className="text-sm text-slate-500">
                          {attendanceRecords.length
                            ? 'Audit history synced.'
                            : 'No attendance updates logged yet.'}
                        </p>
                      ) : (
                        <div className="overflow-x-auto">
                          <table className="w-full text-xs">
                            <thead>
                              <tr className="border-b border-slate-200 dark:border-slate-800 text-left uppercase text-slate-500">
                                <th className="py-2 pr-3">Timestamp</th>
                                <th className="py-2 px-3">Student</th>
                                <th className="py-2 px-3">Change</th>
                                <th className="py-2 px-3">Changed By</th>
                                <th className="py-2 px-3">Remarks</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                              {attendanceAudit.map((aud) => (
                                <tr key={aud.id}>
                                  <td className="py-2 pr-3 whitespace-nowrap">
                                    {new Date(aud.changed_at).toLocaleString()}
                                  </td>
                                  <td className="py-2 px-3">
                                    {aud.student_name} ({aud.roll_number})
                                  </td>
                                  <td className="py-2 px-3">
                                    <span className="inline-flex items-center gap-1">
                                      <History className="w-3 h-3 text-slate-400" />
                                      {aud.previous_status ? `${aud.previous_status} → ` : ''}
                                      <strong>{aud.new_status}</strong>
                                    </span>
                                  </td>
                                  <td className="py-2 px-3">{aud.changed_by_name}</td>
                                  <td className="py-2 px-3">{aud.remarks || '—'}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </Card>
                  </div>
                )}

                {/* TAB 5: ANNOUNCEMENTS */}
                {activeTab === 'announcements' && (
                  <div className="space-y-6">
                    <Card>
                      <CardHeader
                        title="Send Drive Announcement"
                        subtitle="Dispatches deduplicated in-app notifications respecting student announcement preferences"
                      />
                      <form onSubmit={handleSendAnnouncement} className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div>
                            <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">
                              Announcement Title *
                            </label>
                            <input
                              required
                              value={announcementForm.title}
                              onChange={(e) =>
                                setAnnouncementForm((p) => ({ ...p, title: e.target.value }))
                              }
                              placeholder="e.g. Lab Reporting Time Updated"
                              className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800"
                            />
                          </div>
                          <div>
                            <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">
                              Target Audience
                            </label>
                            <select
                              value={announcementForm.target_audience}
                              onChange={(e) =>
                                setAnnouncementForm((p) => ({
                                  ...p,
                                  target_audience: e.target.value as DriveAnnouncementAudience,
                                }))
                              }
                              className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800"
                            >
                              <option value="all_registered">All Registered Students</option>
                              <option value="eligible_students">All Eligible Students</option>
                              <option value="shortlisted_candidates">Shortlisted Candidates</option>
                              <option value="specific_job_applicants">Specific Job Applicants</option>
                            </select>
                          </div>
                        </div>

                        {announcementForm.target_audience === 'specific_job_applicants' && (
                          <div>
                            <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">
                              Select Job Role
                            </label>
                            <select
                              required
                              value={announcementForm.job_id}
                              onChange={(e) =>
                                setAnnouncementForm((p) => ({ ...p, job_id: e.target.value }))
                              }
                              className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800"
                            >
                              <option value="">Choose drive job...</option>
                              {(driveDetail.jobs || [])
                                .filter((j) => j.is_active)
                                .map((j) => (
                                  <option key={j.job_id} value={j.job_id}>
                                    {j.job_title} ({j.company_name})
                                  </option>
                                ))}
                            </select>
                          </div>
                        )}

                        <div>
                          <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">
                            Message *
                          </label>
                          <textarea
                            required
                            rows={3}
                            value={announcementForm.message}
                            onChange={(e) =>
                              setAnnouncementForm((p) => ({ ...p, message: e.target.value }))
                            }
                            placeholder="Write official drive instructions or schedule updates..."
                            className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800"
                          />
                        </div>

                        <div className="flex justify-end">
                          <Button
                            type="submit"
                            variant="primary"
                            size="sm"
                            disabled={busyAction !== null}
                            icon={<Send className="w-4 h-4" />}
                          >
                            Send Announcement
                          </Button>
                        </div>
                      </form>
                    </Card>

                    <Card>
                      <CardHeader title="Announcement Log" subtitle={`${announcements.length} sent`} />
                      {announcements.length === 0 ? (
                        <p className="text-sm text-slate-500">No announcements sent for this drive yet.</p>
                      ) : (
                        <div className="space-y-3">
                          {announcements.map((a) => (
                            <div
                              key={a.id}
                              className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800"
                            >
                              <div className="flex flex-wrap items-center justify-between gap-2">
                                <span className="font-semibold text-sm text-slate-900 dark:text-slate-100">
                                  {a.title}
                                </span>
                                <div className="flex items-center gap-2">
                                  <Badge variant="info" size="sm">
                                    {a.target_audience.replace(/_/g, ' ')}
                                  </Badge>
                                  <Badge variant="success" size="sm">
                                    {a.recipients_count} notified
                                  </Badge>
                                </div>
                              </div>
                              <p className="mt-1.5 text-sm text-slate-600 dark:text-slate-300">
                                {a.message}
                              </p>
                              <div className="mt-2 text-xs text-slate-400">
                                Sent by {a.sender_name} · {new Date(a.created_at).toLocaleString()}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </Card>
                  </div>
                )}

                {/* TAB 6: REPORTS & EXPORT */}
                {activeTab === 'reports' && (
                  <div className="space-y-6">
                    <Card>
                      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                        <div>
                          <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">
                            Drive Audit & Outcomes Report
                          </h3>
                          <p className="text-xs text-slate-500 dark:text-slate-400">
                            Includes participation, eligibility counts, session attendance rates, and accepted placement offers.
                          </p>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            disabled={busyAction !== null}
                            onClick={handleExportPdf}
                            icon={<Download className="w-4 h-4" />}
                          >
                            Export PDF
                          </Button>
                          <Button
                            variant="primary"
                            size="sm"
                            disabled={busyAction !== null}
                            onClick={handleExportExcel}
                            icon={<FileSpreadsheet className="w-4 h-4" />}
                          >
                            Export Excel (.xlsx)
                          </Button>
                        </div>
                      </div>
                    </Card>

                    {report && (
                      <>
                        <Card>
                          <CardHeader title="Session Attendance Summary" />
                          {report.attendance_summary.length === 0 ? (
                            <p className="text-sm text-slate-500">No activities recorded.</p>
                          ) : (
                            <div className="overflow-x-auto">
                              <table className="w-full text-sm">
                                <thead>
                                  <tr className="border-b border-slate-200 dark:border-slate-800 text-left text-xs uppercase text-slate-500">
                                    <th className="py-2 pr-3">Session</th>
                                    <th className="py-2 px-3">Coordinator</th>
                                    <th className="py-2 px-3">Marked</th>
                                    <th className="py-2 px-3">Present / Late</th>
                                    <th className="py-2 px-3">Absent</th>
                                    <th className="py-2 px-3">Rate</th>
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                                  {report.attendance_summary.map((s) => (
                                    <tr key={s.activity_id}>
                                      <td className="py-2.5 pr-3 font-medium">{s.title}</td>
                                      <td className="py-2.5 px-3">{s.coordinator_name}</td>
                                      <td className="py-2.5 px-3">{s.total_marked}</td>
                                      <td className="py-2.5 px-3">
                                        {s.present_count} / {s.late_count}
                                      </td>
                                      <td className="py-2.5 px-3">{s.absent_count}</td>
                                      <td className="py-2.5 px-3 font-semibold">
                                        {s.attendance_rate_pct.toFixed(1)}%
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          )}
                        </Card>

                        <Card>
                          <CardHeader title="Final Placed Outcomes" />
                          {report.placed_outcomes.length === 0 ? (
                            <p className="text-sm text-slate-500">No accepted offers recorded yet.</p>
                          ) : (
                            <div className="overflow-x-auto">
                              <table className="w-full text-sm">
                                <thead>
                                  <tr className="border-b border-slate-200 dark:border-slate-800 text-left text-xs uppercase text-slate-500">
                                    <th className="py-2 pr-3">Student</th>
                                    <th className="py-2 px-3">Company</th>
                                    <th className="py-2 px-3">Role</th>
                                    <th className="py-2 px-3">Package (LPA)</th>
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                                  {report.placed_outcomes.map((o) => (
                                    <tr key={o.application_id}>
                                      <td className="py-2.5 pr-3">
                                        <div className="font-medium">{o.student_name}</div>
                                        <div className="text-xs text-slate-500">
                                          {o.roll_number} · {o.department || '—'}
                                        </div>
                                      </td>
                                      <td className="py-2.5 px-3">{o.company_name}</td>
                                      <td className="py-2.5 px-3">{o.job_title}</td>
                                      <td className="py-2.5 px-3 font-semibold text-emerald-600 dark:text-emerald-400">
                                        {o.package_lpa != null ? `${o.package_lpa} LPA` : '—'}
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          )}
                        </Card>
                      </>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>

      {/* Create / Edit Drive Modal */}
      {showDriveModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4 overflow-y-auto">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto p-6 space-y-5">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">
                {editingDriveId ? 'Edit Placement Drive' : 'Create Placement Drive'}
              </h3>
              <button
                onClick={() => setShowDriveModal(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveDrive} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="md:col-span-2">
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">
                    Drive Name *
                  </label>
                  <input
                    required
                    value={driveForm.name}
                    onChange={(e) => setDriveForm((p) => ({ ...p, name: e.target.value }))}
                    placeholder="e.g. Spring Engineering Campus Drive 2026"
                    className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">
                    Academic Year *
                  </label>
                  <input
                    required
                    value={driveForm.academic_year}
                    onChange={(e) => setDriveForm((p) => ({ ...p, academic_year: e.target.value }))}
                    placeholder="2025-2026"
                    className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">
                    Primary Graduation Year *
                  </label>
                  <input
                    type="number"
                    required
                    value={driveForm.target_graduation_year}
                    onChange={(e) =>
                      setDriveForm((p) => ({ ...p, target_graduation_year: Number(e.target.value) }))
                    }
                    className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">
                    Registration Open *
                  </label>
                  <input
                    type="datetime-local"
                    required
                    value={driveForm.registration_start_date}
                    onChange={(e) =>
                      setDriveForm((p) => ({ ...p, registration_start_date: e.target.value }))
                    }
                    className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">
                    Registration Close *
                  </label>
                  <input
                    type="datetime-local"
                    required
                    value={driveForm.registration_end_date}
                    onChange={(e) =>
                      setDriveForm((p) => ({ ...p, registration_end_date: e.target.value }))
                    }
                    className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">
                    Drive Start Date
                  </label>
                  <input
                    type="datetime-local"
                    value={driveForm.drive_start_date}
                    onChange={(e) =>
                      setDriveForm((p) => ({ ...p, drive_start_date: e.target.value }))
                    }
                    className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">
                    Drive End Date
                  </label>
                  <input
                    type="datetime-local"
                    value={driveForm.drive_end_date}
                    onChange={(e) => setDriveForm((p) => ({ ...p, drive_end_date: e.target.value }))}
                    className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">
                    Drive Mode
                  </label>
                  <select
                    value={driveForm.drive_mode}
                    onChange={(e) =>
                      setDriveForm((p) => ({ ...p, drive_mode: e.target.value as DriveMode }))
                    }
                    className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800"
                  >
                    <option value="on_campus">On-Campus</option>
                    <option value="virtual">Virtual</option>
                    <option value="hybrid">Hybrid</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">
                    Venue / Location
                  </label>
                  <input
                    value={driveForm.venue_location}
                    onChange={(e) =>
                      setDriveForm((p) => ({ ...p, venue_location: e.target.value }))
                    }
                    placeholder="Main Auditorium & Zoom"
                    className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800"
                  />
                </div>

                {!editingDriveId && (
                  <div>
                    <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">
                      Initial Lifecycle Stage
                    </label>
                    <select
                      value={driveForm.lifecycle_phase}
                      onChange={(e) =>
                        setDriveForm((p) => ({
                          ...p,
                          lifecycle_phase: e.target.value as DriveLifecyclePhase,
                        }))
                      }
                      className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800"
                    >
                      <option value="draft">Draft</option>
                      <option value="scheduled">Scheduled</option>
                      <option value="registration_open">Registration Open</option>
                    </select>
                  </div>
                )}
              </div>

              {/* Batches & Departments */}
              {formOptions && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">
                      Target Graduation Batches
                    </label>
                    <div className="flex flex-wrap gap-2 p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 max-h-28 overflow-y-auto">
                      {formOptions.graduation_batches.map((yr) => (
                        <label key={yr} className="inline-flex items-center gap-1.5 text-xs">
                          <input
                            type="checkbox"
                            checked={driveForm.target_graduation_batches.includes(yr)}
                            onChange={() =>
                              toggleNumberInFormArray('target_graduation_batches', yr)
                            }
                          />
                          {yr}
                        </label>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">
                      Eligible Departments (leave unchecked for all)
                    </label>
                    <div className="flex flex-wrap gap-2 p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 max-h-28 overflow-y-auto">
                      {formOptions.departments.map((d) => (
                        <label key={d.id} className="inline-flex items-center gap-1.5 text-xs">
                          <input
                            type="checkbox"
                            checked={driveForm.eligible_department_ids.includes(d.id)}
                            onChange={() =>
                              toggleNumberInFormArray('eligible_department_ids', d.id)
                            }
                          />
                          {d.code}
                        </label>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Participating Companies & Jobs */}
              {formOptions && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">
                      Participating Companies
                    </label>
                    <div className="space-y-1.5 p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 max-h-36 overflow-y-auto">
                      {formOptions.companies.map((c) => (
                        <label key={c.id} className="flex items-center gap-2 text-xs">
                          <input
                            type="checkbox"
                            checked={driveForm.participating_company_ids.includes(c.id)}
                            onChange={() =>
                              toggleNumberInFormArray('participating_company_ids', c.id)
                            }
                          />
                          <Building2 className="w-3.5 h-3.5 text-slate-400" />
                          <span>{c.name}</span>
                        </label>
                      ))}
                    </div>
                  </div>

                  {!editingDriveId && (
                    <div>
                      <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">
                        Associate Published / Eligible Jobs
                      </label>
                      <div className="space-y-1.5 p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 max-h-36 overflow-y-auto">
                        {formOptions.jobs.map((j) => (
                          <label key={j.id} className="flex items-center gap-2 text-xs">
                            <input
                              type="checkbox"
                              checked={driveForm.job_ids.includes(j.id)}
                              onChange={() => toggleNumberInFormArray('job_ids', j.id)}
                            />
                            <span>
                              {j.title} — {j.company_name}
                            </span>
                          </label>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">
                    Instructions
                  </label>
                  <textarea
                    rows={3}
                    value={driveForm.instructions}
                    onChange={(e) => setDriveForm((p) => ({ ...p, instructions: e.target.value }))}
                    className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">
                    Required Documents (one per line)
                  </label>
                  <textarea
                    rows={3}
                    value={driveForm.required_documents_text}
                    onChange={(e) =>
                      setDriveForm((p) => ({ ...p, required_documents_text: e.target.value }))
                    }
                    className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setShowDriveModal(false)}
                >
                  Cancel
                </Button>
                <Button type="submit" variant="primary" size="sm" disabled={busyAction !== null}>
                  {editingDriveId ? 'Save Changes' : 'Create Drive'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
};

export default TpoDrivesPage;
