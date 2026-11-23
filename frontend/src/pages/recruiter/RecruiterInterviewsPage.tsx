import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { DashboardLayout } from '../../components/layout/DashboardLayout';
import { Card, CardHeader } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { interviewApi } from '../../services/api';
import {
  InterviewPortalItem,
  InterviewListPortalResponse,
  InterviewCalendarResponse,
  InterviewRoundTemplate,
  InterviewWorkspaceDetailResponse,
  CalendarEventItem,
} from '../../types';
import {
  Calendar as CalendarIcon,
  List,
  Plus,
  Search,
  RefreshCw,
  Video,
  MapPin,
  Clock,
  User,
  GraduationCap,
  Award,
  CheckCircle2,
  XCircle,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Filter,
  FileText,
  Star,
  Building,
  Check,
  ShieldCheck,
  CalendarDays,
  X,
} from 'lucide-react';

const STATUS_VARIANTS: Record<string, 'brand' | 'success' | 'warning' | 'danger' | 'info' | 'neutral'> = {
  scheduled: 'warning',
  completed: 'success',
  cancelled: 'neutral',
  no_show: 'danger',
};

const OUTCOME_VARIANTS: Record<string, 'brand' | 'success' | 'warning' | 'danger' | 'info' | 'neutral'> = {
  pending: 'info',
  passed: 'success',
  failed: 'danger',
  on_hold: 'warning',
};

export const RecruiterInterviewsPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const prefillApplicationId = searchParams.get('application_id');

  // View state: calendar vs table
  const [viewMode, setViewMode] = useState<'calendar' | 'table'>('calendar');

  // Calendar date range state (Defaults to current month)
  const [currentDate, setCurrentDate] = useState<Date>(() => new Date());

  // Data states
  const [interviews, setInterviews] = useState<InterviewPortalItem[]>([]);
  const [totalInterviews, setTotalInterviews] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [calendarData, setCalendarData] = useState<InterviewCalendarResponse | null>(null);
  const [roundTemplates, setRoundTemplates] = useState<InterviewRoundTemplate[]>([]);

  // Filter states
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [outcomeFilter, setOutcomeFilter] = useState<string>('all');

  // Loading & error states
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Modals state
  const [showScheduleModal, setShowScheduleModal] = useState<boolean>(Boolean(prefillApplicationId));
  const [scheduleApplicationId, setScheduleApplicationId] = useState<string>(prefillApplicationId || '');
  const [scheduleRoundNumber, setScheduleRoundNumber] = useState<number>(1);
  const [scheduleRoundTitle, setScheduleRoundTitle] = useState<string>('');
  const [scheduleMode, setScheduleMode] = useState<'virtual' | 'in_person'>('virtual');
  const [scheduleMeetingLink, setScheduleMeetingLink] = useState<string>('');
  const [scheduleLocation, setScheduleLocation] = useState<string>('');
  const [scheduleStartTime, setScheduleStartTime] = useState<string>('');
  const [scheduleDuration, setScheduleDuration] = useState<number>(60);
  const [scheduleInterviewers, setScheduleInterviewers] = useState<string>('');
  const [scheduleInstructions, setScheduleInstructions] = useState<string>('');
  const [scheduleSubmitting, setScheduleSubmitting] = useState<boolean>(false);
  const [scheduleError, setScheduleError] = useState<string | null>(null);

  // Reschedule modal state
  const [rescheduleTarget, setRescheduleTarget] = useState<InterviewPortalItem | null>(null);
  const [rescheduleStartTime, setRescheduleStartTime] = useState<string>('');
  const [rescheduleDuration, setRescheduleDuration] = useState<number>(60);
  const [rescheduleLink, setRescheduleLink] = useState<string>('');
  const [rescheduleLocation, setRescheduleLocation] = useState<string>('');
  const [rescheduleInstructions, setRescheduleInstructions] = useState<string>('');
  const [rescheduleReason, setRescheduleReason] = useState<string>('');
  const [rescheduleSubmitting, setRescheduleSubmitting] = useState<boolean>(false);
  const [rescheduleError, setRescheduleError] = useState<string | null>(null);

  // Cancel modal state
  const [cancelTarget, setCancelTarget] = useState<InterviewPortalItem | null>(null);
  const [cancelReason, setCancelReason] = useState<string>('');
  const [cancelSubmitting, setCancelSubmitting] = useState<boolean>(false);
  const [cancelError, setCancelError] = useState<string | null>(null);

  // Outcome modal state
  const [outcomeTarget, setOutcomeTarget] = useState<InterviewPortalItem | null>(null);
  const [outcomeSelection, setOutcomeSelection] = useState<'passed' | 'failed' | 'on_hold'>('passed');
  const [outcomeFeedback, setOutcomeFeedback] = useState<string>('');
  const [outcomeSubmitting, setOutcomeSubmitting] = useState<boolean>(false);
  const [outcomeError, setOutcomeError] = useState<string | null>(null);

  // Workspace detail drawer / modal state
  const [workspaceTargetId, setWorkspaceTargetId] = useState<number | null>(null);
  const [workspaceDetail, setWorkspaceDetail] = useState<InterviewWorkspaceDetailResponse | null>(null);
  const [workspaceLoading, setWorkspaceLoading] = useState<boolean>(false);

  // Selected calendar day detail popup
  const [selectedDayEvents, setSelectedDayEvents] = useState<{ date: string; events: CalendarEventItem[] } | null>(null);

  // Fetch round templates on initial mount
  useEffect(() => {
    const fetchTemplates = async () => {
      try {
        const templates = await interviewApi.getRoundTemplates();
        setRoundTemplates(templates);
        if (templates.length > 0 && !scheduleRoundTitle) {
          setScheduleRoundTitle(templates[0].round_title);
          setScheduleDuration(templates[0].default_duration_minutes);
          setScheduleInstructions(templates[0].description);
        }
      } catch (err) {
        console.error('Failed to load round templates:', err);
      }
    };
    fetchTemplates();
  }, []);

  // Calculate start/end date for current month
  const monthRange = useMemo(() => {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0, 23, 59, 59);

    const pad = (n: number) => String(n).padStart(2, '0');
    const startStr = `${firstDay.getFullYear()}-${pad(firstDay.getMonth() + 1)}-01T00:00:00Z`;
    const endStr = `${lastDay.getFullYear()}-${pad(lastDay.getMonth() + 1)}-${pad(lastDay.getDate())}T23:59:59Z`;

    return { startStr, endStr };
  }, [currentDate]);

  // Load interviews & calendar data
  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      // 1. Fetch table items
      const params: any = {
        page: currentPage,
        limit: 15,
      };
      if (statusFilter !== 'all') params.status = statusFilter;
      if (outcomeFilter !== 'all') params.outcome = outcomeFilter;
      if (searchTerm.trim()) params.search = searchTerm.trim();

      const listRes = await interviewApi.listCompanyInterviews(params);
      setInterviews(listRes.items);
      setTotalInterviews(listRes.total);
      setTotalPages(listRes.pages || 1);

      // 2. Fetch calendar events for current month
      const calRes = await interviewApi.getCalendar({
        start_date: monthRange.startStr,
        end_date: monthRange.endStr,
        status: statusFilter !== 'all' ? statusFilter : undefined,
      });
      setCalendarData(calRes);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.message || err.message || 'Failed to load interviews.');
    } finally {
      setIsLoading(false);
    }
  }, [currentPage, statusFilter, outcomeFilter, searchTerm, monthRange]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Open Workspace detail
  const handleOpenWorkspace = async (interviewId: number) => {
    setWorkspaceTargetId(interviewId);
    setWorkspaceLoading(true);
    try {
      const data = await interviewApi.getInterviewWorkspace(interviewId);
      setWorkspaceDetail(data);
    } catch (err: any) {
      alert(err.response?.data?.message || 'Failed to load interview workspace dossier.');
      setWorkspaceTargetId(null);
    } finally {
      setWorkspaceLoading(false);
    }
  };

  // Handle template selection in scheduling modal
  const handleSelectTemplate = (template: InterviewRoundTemplate) => {
    setScheduleRoundNumber(template.round_number);
    setScheduleRoundTitle(template.round_title);
    setScheduleDuration(template.default_duration_minutes);
    setScheduleInstructions(template.description);
  };

  // Submit Schedule Interview
  const handleScheduleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setScheduleError(null);

    const appId = parseInt(scheduleApplicationId, 10);
    if (isNaN(appId) || appId <= 0) {
      setScheduleError('Please enter a valid numeric Application ID.');
      return;
    }
    if (!scheduleStartTime) {
      setScheduleError('Please select interview date and start time.');
      return;
    }

    setScheduleSubmitting(true);
    try {
      await interviewApi.scheduleInterview(appId, {
        round_number: scheduleRoundNumber,
        round_title: scheduleRoundTitle,
        interview_mode: scheduleMode,
        meeting_link: scheduleMode === 'virtual' ? scheduleMeetingLink : undefined,
        location: scheduleMode === 'in_person' ? scheduleLocation : undefined,
        scheduled_start_time: new Date(scheduleStartTime).toISOString(),
        duration_minutes: scheduleDuration,
        interviewer_names: scheduleInterviewers || undefined,
        instructions: scheduleInstructions || undefined,
      });

      setShowScheduleModal(false);
      setSuccessMsg(`Round ${scheduleRoundNumber} interview scheduled successfully.`);
      fetchData();
    } catch (err: any) {
      setScheduleError(err.response?.data?.message || err.message || 'Failed to schedule interview.');
    } finally {
      setScheduleSubmitting(false);
    }
  };

  // Open Reschedule Modal
  const handleOpenReschedule = (iv: InterviewPortalItem) => {
    setRescheduleTarget(iv);
    setRescheduleStartTime(iv.scheduled_start_time ? iv.scheduled_start_time.slice(0, 16) : '');
    setRescheduleDuration(iv.duration_minutes || 60);
    setRescheduleLink(iv.meeting_link || '');
    setRescheduleLocation(iv.location || '');
    setRescheduleInstructions(iv.instructions || '');
    setRescheduleReason('');
    setRescheduleError(null);
  };

  // Submit Reschedule
  const handleRescheduleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rescheduleTarget) return;
    if (!rescheduleStartTime) {
      setRescheduleError('Please specify the new start date and time.');
      return;
    }
    if (!rescheduleReason || rescheduleReason.trim().length < 5) {
      setRescheduleError('Please provide a mandatory reason for rescheduling (at least 5 characters).');
      return;
    }

    setRescheduleSubmitting(true);
    try {
      await interviewApi.rescheduleInterview(rescheduleTarget.id, {
        scheduled_start_time: new Date(rescheduleStartTime).toISOString(),
        duration_minutes: rescheduleDuration,
        meeting_link: rescheduleLink || undefined,
        location: rescheduleLocation || undefined,
        instructions: rescheduleInstructions || undefined,
        reason: rescheduleReason.trim(),
      });

      setRescheduleTarget(null);
      setSuccessMsg('Interview successfully rescheduled.');
      fetchData();
      if (workspaceTargetId === rescheduleTarget.id) {
        handleOpenWorkspace(rescheduleTarget.id);
      }
    } catch (err: any) {
      setRescheduleError(err.response?.data?.message || err.message || 'Failed to reschedule.');
    } finally {
      setRescheduleSubmitting(false);
    }
  };

  // Open Cancel Modal
  const handleOpenCancel = (iv: InterviewPortalItem) => {
    setCancelTarget(iv);
    setCancelReason('');
    setCancelError(null);
  };

  // Submit Cancel
  const handleCancelSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!cancelTarget) return;
    if (!cancelReason || cancelReason.trim().length < 5) {
      setCancelError('Please provide a cancellation reason (minimum 5 characters).');
      return;
    }

    setCancelSubmitting(true);
    try {
      await interviewApi.cancelInterview(cancelTarget.id, {
        reason: cancelReason.trim(),
      });

      setCancelTarget(null);
      setSuccessMsg('Interview round cancelled successfully.');
      fetchData();
      if (workspaceTargetId === cancelTarget.id) {
        handleOpenWorkspace(cancelTarget.id);
      }
    } catch (err: any) {
      setCancelError(err.response?.data?.message || err.message || 'Failed to cancel interview.');
    } finally {
      setCancelSubmitting(false);
    }
  };

  // Open Outcome Modal
  const handleOpenOutcome = (iv: InterviewPortalItem) => {
    setOutcomeTarget(iv);
    setOutcomeSelection(iv.outcome !== 'pending' ? (iv.outcome as any) : 'passed');
    setOutcomeFeedback(iv.feedback_notes || '');
    setOutcomeError(null);
  };

  // Submit Outcome
  const handleOutcomeSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!outcomeTarget) return;

    setOutcomeSubmitting(true);
    try {
      await interviewApi.recordOutcome(outcomeTarget.id, {
        outcome: outcomeSelection,
        feedback_notes: outcomeFeedback.trim() || undefined,
      });

      setOutcomeTarget(null);
      setSuccessMsg(`Interview outcome recorded as '${outcomeSelection.toUpperCase()}'.`);
      fetchData();
      if (workspaceTargetId === outcomeTarget.id) {
        handleOpenWorkspace(outcomeTarget.id);
      }
    } catch (err: any) {
      setOutcomeError(err.response?.data?.message || err.message || 'Failed to record outcome.');
    } finally {
      setOutcomeSubmitting(false);
    }
  };

  // Calendar month navigation
  const prevMonth = () => {
    setCurrentDate((d) => new Date(d.getFullYear(), d.getMonth() - 1, 1));
  };
  const nextMonth = () => {
    setCurrentDate((d) => new Date(d.getFullYear(), d.getMonth() + 1, 1));
  };
  const goToToday = () => {
    setCurrentDate(new Date());
  };

  // Build calendar matrix (Days of the current month view)
  const calendarDays = useMemo(() => {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();

    const firstDayIndex = new Date(year, month, 1).getDay(); // 0 is Sunday
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const daysInPrevMonth = new Date(year, month, 0).getDate();

    // Map existing events by date key YYYY-MM-DD
    const eventMap = new Map<string, CalendarEventItem[]>();
    if (calendarData?.days) {
      for (const d of calendarData.days) {
        eventMap.set(d.date, d.events);
      }
    }

    const pad = (n: number) => String(n).padStart(2, '0');
    const matrix: Array<{
      dayNumber: number;
      dateKey: string;
      isCurrentMonth: boolean;
      isToday: boolean;
      events: CalendarEventItem[];
    }> = [];

    const todayStr = new Date().toISOString().slice(0, 10);

    // Prev month padding
    for (let i = firstDayIndex - 1; i >= 0; i--) {
      const dNum = daysInPrevMonth - i;
      const prevDateKey = `${year}-${pad(month === 0 ? 12 : month)}-${pad(dNum)}`;
      matrix.push({
        dayNumber: dNum,
        dateKey: prevDateKey,
        isCurrentMonth: false,
        isToday: prevDateKey === todayStr,
        events: eventMap.get(prevDateKey) || [],
      });
    }

    // Current month days
    for (let i = 1; i <= daysInMonth; i++) {
      const dateKey = `${year}-${pad(month + 1)}-${pad(i)}`;
      matrix.push({
        dayNumber: i,
        dateKey,
        isCurrentMonth: true,
        isToday: dateKey === todayStr,
        events: eventMap.get(dateKey) || [],
      });
    }

    // Next month padding to reach multiple of 7
    const remaining = (7 - (matrix.length % 7)) % 7;
    for (let i = 1; i <= remaining; i++) {
      const nextDateKey = `${year}-${pad(month + 2 > 12 ? 1 : month + 2)}-${pad(i)}`;
      matrix.push({
        dayNumber: i,
        dateKey: nextDateKey,
        isCurrentMonth: false,
        isToday: nextDateKey === todayStr,
        events: eventMap.get(nextDateKey) || [],
      });
    }

    return matrix;
  }, [currentDate, calendarData]);

  const monthYearLabel = currentDate.toLocaleString('default', { month: 'long', year: 'numeric' });

  return (
    <DashboardLayout
      role="recruiter"
      title="Interview Management & Calendar"
      subtitle="Multi-round interview scheduling, collision protection, interviewer scorecards, and live calendar tracking."
    >
      <div className="space-y-6">
        {/* Header with Title & Action */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <CalendarIcon className="w-7 h-7 text-brand-600 dark:text-brand-400" />
              Interview Management & Calendar
            </h1>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
              Multi-round interview scheduling, collision protection, interviewer scorecards, and live calendar tracking.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              icon={<RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />}
              onClick={fetchData}
              disabled={isLoading}
            >
              Refresh
            </Button>
            <Button
              variant="primary"
              size="sm"
              icon={<Plus className="w-4 h-4" />}
              onClick={() => {
                setShowScheduleModal(true);
                setScheduleError(null);
              }}
            >
              Schedule Interview
            </Button>
          </div>
        </div>

        {/* Success / Error Alerts */}
        {successMsg && (
          <div className="flex items-center justify-between p-4 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800/80 rounded-xl text-emerald-800 dark:text-emerald-200 text-sm">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400 flex-shrink-0" />
              <span>{successMsg}</span>
            </div>
            <button
              onClick={() => setSuccessMsg(null)}
              className="p-1 hover:bg-emerald-100 dark:hover:bg-emerald-900/40 rounded"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {errorMsg && (
          <div className="flex items-center justify-between p-4 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800/80 rounded-xl text-rose-800 dark:text-rose-200 text-sm">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-rose-600 dark:text-rose-400 flex-shrink-0" />
              <span>{errorMsg}</span>
            </div>
            <button
              onClick={() => setErrorMsg(null)}
              className="p-1 hover:bg-rose-100 dark:hover:bg-rose-900/40 rounded"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Metric Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card className="p-4 bg-white dark:bg-slate-900 border-slate-200/80 dark:border-slate-800">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-brand-50 dark:bg-brand-950/60 text-brand-600 dark:text-brand-400 rounded-xl">
                <CalendarDays className="w-5 h-5" />
              </div>
              <div>
                <p className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Total Interviews
                </p>
                <p className="text-2xl font-bold text-slate-900 dark:text-white">
                  {calendarData?.total_events ?? totalInterviews}
                </p>
              </div>
            </div>
          </Card>

          <Card className="p-4 bg-white dark:bg-slate-900 border-slate-200/80 dark:border-slate-800">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-amber-50 dark:bg-amber-950/60 text-amber-600 dark:text-amber-400 rounded-xl">
                <Clock className="w-5 h-5" />
              </div>
              <div>
                <p className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Scheduled
                </p>
                <p className="text-2xl font-bold text-slate-900 dark:text-white">
                  {calendarData?.scheduled_count ?? 0}
                </p>
              </div>
            </div>
          </Card>

          <Card className="p-4 bg-white dark:bg-slate-900 border-slate-200/80 dark:border-slate-800">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 rounded-xl">
                <CheckCircle2 className="w-5 h-5" />
              </div>
              <div>
                <p className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Completed
                </p>
                <p className="text-2xl font-bold text-slate-900 dark:text-white">
                  {calendarData?.completed_count ?? 0}
                </p>
              </div>
            </div>
          </Card>

          <Card className="p-4 bg-white dark:bg-slate-900 border-slate-200/80 dark:border-slate-800">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-rose-50 dark:bg-rose-950/60 text-rose-600 dark:text-rose-400 rounded-xl">
                <XCircle className="w-5 h-5" />
              </div>
              <div>
                <p className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Rescheduled / Cancelled
                </p>
                <p className="text-2xl font-bold text-slate-900 dark:text-white">
                  {(calendarData?.rescheduled_count ?? 0) + (calendarData?.cancelled_count ?? 0)}
                </p>
              </div>
            </div>
          </Card>
        </div>

        {/* Controls Bar: Search, Filters, View Switcher */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200/80 dark:border-slate-800 shadow-sm">
          <div className="flex flex-wrap items-center gap-3 flex-1">
            {/* Search */}
            <div className="relative min-w-[220px] flex-1 max-w-sm">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search candidate, roll #, interviewer..."
                className="w-full pl-9 pr-3 py-1.5 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>

            {/* Status Filter */}
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="py-1.5 px-3 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              <option value="all">All Statuses</option>
              <option value="scheduled">Scheduled</option>
              <option value="completed">Completed</option>
              <option value="cancelled">Cancelled</option>
              <option value="no_show">No Show</option>
            </select>

            {/* Outcome Filter */}
            <select
              value={outcomeFilter}
              onChange={(e) => setOutcomeFilter(e.target.value)}
              className="py-1.5 px-3 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              <option value="all">All Outcomes</option>
              <option value="pending">Pending</option>
              <option value="passed">Passed</option>
              <option value="failed">Failed</option>
              <option value="on_hold">On Hold</option>
            </select>
          </div>

          {/* View Toggle */}
          <div className="flex items-center gap-1 bg-slate-100 dark:bg-slate-800 p-1 rounded-lg border border-slate-200 dark:border-slate-700">
            <button
              onClick={() => setViewMode('calendar')}
              className={`flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${
                viewMode === 'calendar'
                  ? 'bg-white dark:bg-slate-900 text-brand-600 dark:text-brand-400 shadow-sm'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <CalendarIcon className="w-3.5 h-3.5" />
              Calendar View
            </button>
            <button
              onClick={() => setViewMode('table')}
              className={`flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${
                viewMode === 'table'
                  ? 'bg-white dark:bg-slate-900 text-brand-600 dark:text-brand-400 shadow-sm'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <List className="w-3.5 h-3.5" />
              Roster Table
            </button>
          </div>
        </div>

        {/* MAIN VIEW: Calendar vs Roster Table */}
        {viewMode === 'calendar' ? (
          <Card className="bg-white dark:bg-slate-900 border-slate-200/80 dark:border-slate-800 shadow-sm overflow-hidden">
            {/* Calendar Month Header */}
            <div className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50">
              <div className="flex items-center gap-3">
                <h2 className="text-lg font-bold text-slate-900 dark:text-white">{monthYearLabel}</h2>
                <button
                  onClick={goToToday}
                  className="px-2.5 py-1 text-xs font-medium text-slate-600 dark:text-slate-300 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700"
                >
                  Today
                </button>
              </div>

              <div className="flex items-center gap-1">
                <button
                  onClick={prevMonth}
                  className="p-1.5 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-800 rounded-lg transition-colors"
                  aria-label="Previous Month"
                >
                  <ChevronLeft className="w-5 h-5" />
                </button>
                <button
                  onClick={nextMonth}
                  className="p-1.5 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-800 rounded-lg transition-colors"
                  aria-label="Next Month"
                >
                  <ChevronRight className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Days of week */}
            <div className="grid grid-cols-7 border-b border-slate-200 dark:border-slate-800 bg-slate-100/50 dark:bg-slate-800/50 text-center py-2 text-xs font-semibold text-slate-500 dark:text-slate-400">
              <div>Sun</div>
              <div>Mon</div>
              <div>Tue</div>
              <div>Wed</div>
              <div>Thu</div>
              <div>Fri</div>
              <div>Sat</div>
            </div>

            {/* Calendar Grid */}
            <div className="grid grid-cols-7 auto-rows-fr divide-x divide-y divide-slate-200 dark:divide-slate-800 bg-white dark:bg-slate-900">
              {calendarDays.map((day, idx) => (
                <div
                  key={`${day.dateKey}-${idx}`}
                  className={`min-h-[120px] p-2 flex flex-col justify-between transition-colors ${
                    !day.isCurrentMonth
                      ? 'bg-slate-50/40 dark:bg-slate-950/40 text-slate-400 dark:text-slate-600'
                      : 'hover:bg-slate-50/70 dark:hover:bg-slate-800/30'
                  } ${day.isToday ? 'bg-brand-50/30 dark:bg-brand-950/20' : ''}`}
                >
                  {/* Day Header */}
                  <div className="flex items-center justify-between mb-1">
                    <span
                      className={`text-xs font-semibold inline-flex items-center justify-center w-6 h-6 rounded-full ${
                        day.isToday
                          ? 'bg-brand-600 text-white font-bold'
                          : day.isCurrentMonth
                          ? 'text-slate-800 dark:text-slate-200'
                          : 'text-slate-400 dark:text-slate-600'
                      }`}
                    >
                      {day.dayNumber}
                    </span>
                    {day.events.length > 0 && (
                      <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                        {day.events.length}
                      </span>
                    )}
                  </div>

                  {/* Events preview list */}
                  <div className="space-y-1 flex-1 overflow-hidden">
                    {day.events.slice(0, 3).map((ev) => (
                      <div
                        key={ev.id}
                        onClick={() => handleOpenWorkspace(ev.id)}
                        className={`text-[11px] p-1.5 rounded-md cursor-pointer border transition-all truncate flex items-center justify-between gap-1 ${
                          ev.status === 'cancelled'
                            ? 'bg-slate-100 dark:bg-slate-800 text-slate-400 border-slate-200 line-through'
                            : ev.outcome === 'passed'
                            ? 'bg-emerald-50 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-200 border-emerald-200/80 hover:bg-emerald-100'
                            : ev.outcome === 'failed'
                            ? 'bg-rose-50 dark:bg-rose-950/60 text-rose-800 dark:text-rose-200 border-rose-200/80 hover:bg-rose-100'
                            : 'bg-brand-50 dark:bg-brand-950/60 text-brand-800 dark:text-brand-200 border-brand-200/80 hover:bg-brand-100'
                        }`}
                        title={`${ev.round_title} - ${ev.student_name} (${new Date(
                          ev.scheduled_start_time
                        ).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })})`}
                      >
                        <div className="truncate flex items-center gap-1">
                          {ev.interview_mode === 'virtual' ? (
                            <Video className="w-3 h-3 flex-shrink-0 text-brand-600 dark:text-brand-400" />
                          ) : (
                            <MapPin className="w-3 h-3 flex-shrink-0 text-amber-600 dark:text-amber-400" />
                          )}
                          <span className="font-semibold">{ev.student_name.split(' ')[0]}</span>: {ev.round_title}
                        </div>
                      </div>
                    ))}
                    {day.events.length > 3 && (
                      <button
                        onClick={() => setSelectedDayEvents({ date: day.dateKey, events: day.events })}
                        className="text-[10px] text-brand-600 dark:text-brand-400 hover:underline font-semibold block text-center w-full"
                      >
                        +{day.events.length - 3} more
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        ) : (
          /* Table Roster View */
          <Card className="bg-white dark:bg-slate-900 border-slate-200/80 dark:border-slate-800 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 dark:bg-slate-800/60 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider border-b border-slate-200 dark:border-slate-800">
                  <tr>
                    <th className="px-4 py-3">Candidate</th>
                    <th className="px-4 py-3">Role & Drive</th>
                    <th className="px-4 py-3">Round & Mode</th>
                    <th className="px-4 py-3">Scheduled Time</th>
                    <th className="px-4 py-3">Status & Outcome</th>
                    <th className="px-4 py-3">Evaluations</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-800 text-slate-700 dark:text-slate-300">
                  {interviews.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="px-4 py-8 text-center text-slate-500 dark:text-slate-400">
                        {isLoading ? 'Loading interviews...' : 'No interview rounds match the specified filters.'}
                      </td>
                    </tr>
                  ) : (
                    interviews.map((iv) => (
                      <tr key={iv.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition-colors">
                        {/* Candidate */}
                        <td className="px-4 py-3">
                          <div className="font-semibold text-slate-900 dark:text-white">{iv.student_name}</div>
                          <div className="text-xs text-slate-500 dark:text-slate-400">
                            {iv.roll_number} • {iv.department} (CGPA: {iv.cgpa.toFixed(2)})
                          </div>
                        </td>

                        {/* Role & Drive */}
                        <td className="px-4 py-3">
                          <div className="font-medium text-slate-900 dark:text-white">{iv.job_title}</div>
                          <div className="text-xs text-slate-500 dark:text-slate-400">
                            {iv.drive_name || 'Direct Recruitment'}
                          </div>
                        </td>

                        {/* Round & Mode */}
                        <td className="px-4 py-3">
                          <div className="font-medium text-slate-900 dark:text-white">
                            R{iv.round_number}: {iv.round_title}
                          </div>
                          <div className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                            {iv.interview_mode === 'virtual' ? (
                              <span className="inline-flex items-center gap-1 text-brand-600 dark:text-brand-400">
                                <Video className="w-3.5 h-3.5" /> Virtual
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 text-amber-600 dark:text-amber-400">
                                <MapPin className="w-3.5 h-3.5" /> In-Person
                              </span>
                            )}
                            {iv.interviewer_names && <span>• {iv.interviewer_names}</span>}
                          </div>
                        </td>

                        {/* Scheduled Time */}
                        <td className="px-4 py-3">
                          <div className="font-medium text-slate-900 dark:text-white flex items-center gap-1">
                            <Clock className="w-3.5 h-3.5 text-slate-400" />
                            {new Date(iv.scheduled_start_time).toLocaleString([], {
                              month: 'short',
                              day: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit',
                            })}
                          </div>
                          <div className="text-xs text-slate-500 dark:text-slate-400">
                            {iv.duration_minutes} min
                            {iv.is_rescheduled && (
                              <span className="ml-1 text-amber-600 dark:text-amber-400 font-medium">(Rescheduled)</span>
                            )}
                          </div>
                        </td>

                        {/* Status & Outcome */}
                        <td className="px-4 py-3">
                          <div className="flex flex-col gap-1 items-start">
                            <Badge variant={STATUS_VARIANTS[iv.status] || 'neutral'} size="sm">
                              {iv.status.replace('_', ' ')}
                            </Badge>
                            <Badge variant={OUTCOME_VARIANTS[iv.outcome] || 'neutral'} size="sm">
                              {iv.outcome.replace('_', ' ')}
                            </Badge>
                          </div>
                        </td>

                        {/* Evaluations */}
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-1 text-xs">
                            <span className="font-semibold text-slate-900 dark:text-white">
                              {iv.evaluations_count}
                            </span>
                            <span className="text-slate-500 dark:text-slate-400">forms</span>
                          </div>
                          {iv.average_rating ? (
                            <div className="flex items-center gap-1 text-amber-500 text-xs mt-0.5">
                              <Star className="w-3.5 h-3.5 fill-current" />
                              <span className="font-medium text-slate-800 dark:text-slate-200">
                                {iv.average_rating.toFixed(1)}/5.0
                              </span>
                            </div>
                          ) : (
                            <span className="text-[11px] text-slate-400">Pending review</span>
                          )}
                        </td>

                        {/* Actions */}
                        <td className="px-4 py-3 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            <Button
                              variant="outline"
                              size="sm"
                              className="text-xs py-1 px-2"
                              icon={<User className="w-3 h-3" />}
                              onClick={() => handleOpenWorkspace(iv.id)}
                              title="Open Candidate Workspace Dossier"
                            >
                              Dossier
                            </Button>

                            {iv.status !== 'cancelled' && (
                              <>
                                <Button
                                  variant="secondary"
                                  size="sm"
                                  className="text-xs py-1 px-2"
                                  icon={<CheckCircle2 className="w-3 h-3" />}
                                  onClick={() => handleOpenOutcome(iv)}
                                  title="Record Interview Outcome"
                                >
                                  Outcome
                                </Button>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="text-xs py-1 px-2"
                                  onClick={() => handleOpenReschedule(iv)}
                                  title="Reschedule Interview"
                                >
                                  Reschedule
                                </Button>
                                <Button
                                  variant="danger"
                                  size="sm"
                                  className="text-xs py-1 px-2"
                                  onClick={() => handleOpenCancel(iv)}
                                  title="Cancel Round"
                                >
                                  Cancel
                                </Button>
                              </>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="p-4 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between text-xs text-slate-500">
                <span>
                  Showing page {currentPage} of {totalPages} ({totalInterviews} total)
                </span>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={currentPage <= 1}
                    onClick={() => setCurrentPage((p) => p - 1)}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={currentPage >= totalPages}
                    onClick={() => setCurrentPage((p) => p + 1)}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </Card>
        )}

        {/* MODAL 1: Schedule Interview Modal */}
        {showScheduleModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm overflow-y-auto">
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-2xl w-full p-6 shadow-2xl space-y-4 my-8">
              <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
                <div>
                  <h3 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
                    <CalendarIcon className="w-5 h-5 text-brand-600" />
                    Schedule Interview Round
                  </h3>
                  <p className="text-xs text-slate-500">
                    Schedule multi-round interviews with automated collision checks and template guidance.
                  </p>
                </div>
                <button
                  onClick={() => setShowScheduleModal(false)}
                  className="p-1 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-slate-500"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {scheduleError && (
                <div className="p-3 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 rounded-xl text-xs text-rose-700 dark:text-rose-300 flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                  <span>{scheduleError}</span>
                </div>
              )}

              {/* Template quick-picker */}
              {roundTemplates.length > 0 && (
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                    Pre-Configured Round Template
                  </label>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                    {roundTemplates.map((t) => (
                      <button
                        key={t.round_number}
                        type="button"
                        onClick={() => handleSelectTemplate(t)}
                        className={`p-2 text-left rounded-lg border text-xs transition-all ${
                          scheduleRoundNumber === t.round_number
                            ? 'bg-brand-50 border-brand-500 text-brand-700 dark:bg-brand-950/60 dark:border-brand-500 dark:text-brand-300 font-semibold shadow-sm'
                            : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:border-brand-300'
                        }`}
                      >
                        <div className="font-bold">R{t.round_number}: {t.round_title}</div>
                        <div className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5 truncate">
                          {t.default_duration_minutes} min • {t.stage}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <form onSubmit={handleScheduleSubmit} className="space-y-4 text-xs">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {/* Application ID */}
                  <div>
                    <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                      Candidate Application ID *
                    </label>
                    <input
                      type="number"
                      required
                      value={scheduleApplicationId}
                      onChange={(e) => setScheduleApplicationId(e.target.value)}
                      placeholder="e.g. 104"
                      className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                    />
                  </div>

                  {/* Round Number */}
                  <div>
                    <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                      Round Sequence Number *
                    </label>
                    <input
                      type="number"
                      required
                      min={1}
                      max={20}
                      value={scheduleRoundNumber}
                      onChange={(e) => setScheduleRoundNumber(parseInt(e.target.value, 10) || 1)}
                      className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {/* Round Title */}
                  <div>
                    <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                      Round Title *
                    </label>
                    <input
                      type="text"
                      required
                      value={scheduleRoundTitle}
                      onChange={(e) => setScheduleRoundTitle(e.target.value)}
                      placeholder="e.g. Technical Screening"
                      className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                    />
                  </div>

                  {/* Interview Mode */}
                  <div>
                    <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                      Interview Mode *
                    </label>
                    <select
                      value={scheduleMode}
                      onChange={(e) => setScheduleMode(e.target.value as any)}
                      className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                    >
                      <option value="virtual">Virtual (Video Meeting)</option>
                      <option value="in_person">In-Person (On Campus / Office)</option>
                    </select>
                  </div>
                </div>

                {/* Meeting link or location */}
                {scheduleMode === 'virtual' ? (
                  <div>
                    <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                      Meeting Link (Google Meet, Zoom, Teams)
                    </label>
                    <input
                      type="url"
                      value={scheduleMeetingLink}
                      onChange={(e) => setScheduleMeetingLink(e.target.value)}
                      placeholder="https://meet.google.com/xyz-abc"
                      className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                    />
                  </div>
                ) : (
                  <div>
                    <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                      Venue / Room Location
                    </label>
                    <input
                      type="text"
                      value={scheduleLocation}
                      onChange={(e) => setScheduleLocation(e.target.value)}
                      placeholder="e.g. Placement Cell Conference Room B-204"
                      className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                    />
                  </div>
                )}

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {/* Start time */}
                  <div>
                    <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                      Scheduled Start Time *
                    </label>
                    <input
                      type="datetime-local"
                      required
                      value={scheduleStartTime}
                      onChange={(e) => setScheduleStartTime(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                    />
                  </div>

                  {/* Duration */}
                  <div>
                    <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                      Duration (Minutes) *
                    </label>
                    <input
                      type="number"
                      required
                      min={15}
                      max={240}
                      value={scheduleDuration}
                      onChange={(e) => setScheduleDuration(parseInt(e.target.value, 10) || 45)}
                      className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                    />
                  </div>
                </div>

                {/* Interviewer Names */}
                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Interviewer Names / Panel Description
                  </label>
                  <input
                    type="text"
                    value={scheduleInterviewers}
                    onChange={(e) => setScheduleInterviewers(e.target.value)}
                    placeholder="e.g. Sarah Jenkins (Tech Lead), David Roy (Senior Eng)"
                    className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                </div>

                {/* Instructions */}
                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Candidate Preparation Instructions
                  </label>
                  <textarea
                    rows={3}
                    value={scheduleInstructions}
                    onChange={(e) => setScheduleInstructions(e.target.value)}
                    placeholder="Preparation expectations, environment setup, required identification..."
                    className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none"
                  />
                </div>

                <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-200 dark:border-slate-800">
                  <Button
                    variant="outline"
                    size="sm"
                    type="button"
                    onClick={() => setShowScheduleModal(false)}
                    disabled={scheduleSubmitting}
                  >
                    Cancel
                  </Button>
                  <Button
                    variant="primary"
                    size="sm"
                    type="submit"
                    isLoading={scheduleSubmitting}
                    icon={<Check className="w-4 h-4" />}
                  >
                    Schedule Round
                  </Button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* MODAL 2: Reschedule Modal */}
        {rescheduleTarget && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
              <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
                <div>
                  <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                    <Clock className="w-5 h-5 text-amber-500" />
                    Reschedule Round {rescheduleTarget.round_number}
                  </h3>
                  <p className="text-xs text-slate-500">
                    Candidate: {rescheduleTarget.student_name} ({rescheduleTarget.roll_number})
                  </p>
                </div>
                <button
                  onClick={() => setRescheduleTarget(null)}
                  className="p-1 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-slate-500"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {rescheduleError && (
                <div className="p-3 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 rounded-xl text-xs text-rose-700 dark:text-rose-300 flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                  <span>{rescheduleError}</span>
                </div>
              )}

              <form onSubmit={handleRescheduleSubmit} className="space-y-3 text-xs">
                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    New Start Date & Time *
                  </label>
                  <input
                    type="datetime-local"
                    required
                    value={rescheduleStartTime}
                    onChange={(e) => setRescheduleStartTime(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Duration (Minutes)
                  </label>
                  <input
                    type="number"
                    min={15}
                    max={240}
                    value={rescheduleDuration}
                    onChange={(e) => setRescheduleDuration(parseInt(e.target.value, 10) || 60)}
                    className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                </div>

                {rescheduleTarget.interview_mode === 'virtual' ? (
                  <div>
                    <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                      Updated Meeting Link
                    </label>
                    <input
                      type="url"
                      value={rescheduleLink}
                      onChange={(e) => setRescheduleLink(e.target.value)}
                      placeholder="https://..."
                      className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                    />
                  </div>
                ) : (
                  <div>
                    <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                      Updated Venue / Location
                    </label>
                    <input
                      type="text"
                      value={rescheduleLocation}
                      onChange={(e) => setRescheduleLocation(e.target.value)}
                      placeholder="Room number..."
                      className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                    />
                  </div>
                )}

                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Mandatory Rescheduling Reason (Min 5 chars) *
                  </label>
                  <textarea
                    rows={2}
                    required
                    value={rescheduleReason}
                    onChange={(e) => setRescheduleReason(e.target.value)}
                    placeholder="Explain why the round is being rescheduled (audit requirement)..."
                    className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none"
                  />
                </div>

                <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-200 dark:border-slate-800">
                  <Button
                    variant="outline"
                    size="sm"
                    type="button"
                    onClick={() => setRescheduleTarget(null)}
                    disabled={rescheduleSubmitting}
                  >
                    Cancel
                  </Button>
                  <Button
                    variant="primary"
                    size="sm"
                    type="submit"
                    isLoading={rescheduleSubmitting}
                    icon={<Clock className="w-4 h-4" />}
                  >
                    Confirm Reschedule
                  </Button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* MODAL 3: Cancel Interview Modal */}
        {cancelTarget && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
              <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
                <div>
                  <h3 className="text-base font-bold text-rose-600 flex items-center gap-2">
                    <XCircle className="w-5 h-5 text-rose-600" />
                    Cancel Interview Round
                  </h3>
                  <p className="text-xs text-slate-500">
                    Candidate: {cancelTarget.student_name} (Round {cancelTarget.round_number})
                  </p>
                </div>
                <button
                  onClick={() => setCancelTarget(null)}
                  className="p-1 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-slate-500"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {cancelError && (
                <div className="p-3 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 rounded-xl text-xs text-rose-700 dark:text-rose-300 flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                  <span>{cancelError}</span>
                </div>
              )}

              <p className="text-xs text-slate-600 dark:text-slate-400">
                Cancelling this round will revert the application state to its previous stage if no prior completed rounds exist.
              </p>

              <form onSubmit={handleCancelSubmit} className="space-y-3 text-xs">
                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Cancellation Reason (Min 5 chars) *
                  </label>
                  <textarea
                    rows={3}
                    required
                    value={cancelReason}
                    onChange={(e) => setCancelReason(e.target.value)}
                    placeholder="Provide justification for cancelling this interview..."
                    className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-rose-500 resize-none"
                  />
                </div>

                <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-200 dark:border-slate-800">
                  <Button
                    variant="outline"
                    size="sm"
                    type="button"
                    onClick={() => setCancelTarget(null)}
                    disabled={cancelSubmitting}
                  >
                    Keep Interview
                  </Button>
                  <Button
                    variant="danger"
                    size="sm"
                    type="submit"
                    isLoading={cancelSubmitting}
                    icon={<XCircle className="w-4 h-4" />}
                  >
                    Confirm Cancellation
                  </Button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* MODAL 4: Record Outcome Modal */}
        {outcomeTarget && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
              <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
                <div>
                  <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                    <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                    Record Round Outcome
                  </h3>
                  <p className="text-xs text-slate-500">
                    Round {outcomeTarget.round_number}: {outcomeTarget.round_title} • {outcomeTarget.student_name}
                  </p>
                </div>
                <button
                  onClick={() => setOutcomeTarget(null)}
                  className="p-1 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-slate-500"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {outcomeError && (
                <div className="p-3 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 rounded-xl text-xs text-rose-700 dark:text-rose-300 flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                  <span>{outcomeError}</span>
                </div>
              )}

              <form onSubmit={handleOutcomeSubmit} className="space-y-4 text-xs">
                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                    Interview Decision *
                  </label>
                  <div className="grid grid-cols-3 gap-2">
                    <button
                      type="button"
                      onClick={() => setOutcomeSelection('passed')}
                      className={`p-2.5 rounded-xl border text-center transition-all ${
                        outcomeSelection === 'passed'
                          ? 'bg-emerald-50 border-emerald-500 text-emerald-700 dark:bg-emerald-950/60 dark:border-emerald-500 dark:text-emerald-300 font-bold ring-2 ring-emerald-500/20'
                          : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300'
                      }`}
                    >
                      <CheckCircle2 className="w-5 h-5 mx-auto mb-1 text-emerald-500" />
                      Passed
                    </button>

                    <button
                      type="button"
                      onClick={() => setOutcomeSelection('on_hold')}
                      className={`p-2.5 rounded-xl border text-center transition-all ${
                        outcomeSelection === 'on_hold'
                          ? 'bg-amber-50 border-amber-500 text-amber-700 dark:bg-amber-950/60 dark:border-amber-500 dark:text-amber-300 font-bold ring-2 ring-amber-500/20'
                          : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300'
                      }`}
                    >
                      <Clock className="w-5 h-5 mx-auto mb-1 text-amber-500" />
                      On Hold
                    </button>

                    <button
                      type="button"
                      onClick={() => setOutcomeSelection('failed')}
                      className={`p-2.5 rounded-xl border text-center transition-all ${
                        outcomeSelection === 'failed'
                          ? 'bg-rose-50 border-rose-500 text-rose-700 dark:bg-rose-950/60 dark:border-rose-500 dark:text-rose-300 font-bold ring-2 ring-rose-500/20'
                          : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300'
                      }`}
                    >
                      <XCircle className="w-5 h-5 mx-auto mb-1 text-rose-500" />
                      Failed
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Confidential Feedback Notes
                  </label>
                  <textarea
                    rows={4}
                    value={outcomeFeedback}
                    onChange={(e) => setOutcomeFeedback(e.target.value)}
                    placeholder="Candidate strengths, gaps, technical depth, interview summary..."
                    className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none"
                  />
                </div>

                <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-200 dark:border-slate-800">
                  <Button
                    variant="outline"
                    size="sm"
                    type="button"
                    onClick={() => setOutcomeTarget(null)}
                    disabled={outcomeSubmitting}
                  >
                    Cancel
                  </Button>
                  <Button
                    variant="primary"
                    size="sm"
                    type="submit"
                    isLoading={outcomeSubmitting}
                    icon={<Check className="w-4 h-4" />}
                  >
                    Save Outcome
                  </Button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* MODAL 5: Workspace Dossier Drawer / Modal */}
        {workspaceTargetId && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm overflow-y-auto">
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-4xl w-full p-6 shadow-2xl space-y-6 my-8">
              <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 bg-brand-50 dark:bg-brand-950/60 text-brand-600 dark:text-brand-400 rounded-xl">
                    <User className="w-6 h-6" />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                      Interviewer Workspace Dossier
                    </h3>
                    <p className="text-xs text-slate-500">
                      Comprehensive candidate profile, round schedule, scorecards, and past round history.
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => {
                    setWorkspaceTargetId(null);
                    setWorkspaceDetail(null);
                  }}
                  className="p-1 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-slate-500"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {workspaceLoading || !workspaceDetail ? (
                <div className="py-12 text-center text-slate-500 flex items-center justify-center gap-2">
                  <RefreshCw className="w-5 h-5 animate-spin text-brand-500" />
                  <span>Loading candidate workspace dossier...</span>
                </div>
              ) : (
                <div className="space-y-6 text-sm">
                  {/* Top Candidate & Job Banner */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-slate-50 dark:bg-slate-800/40 p-4 rounded-xl border border-slate-200/80 dark:border-slate-800">
                    <div className="space-y-1.5">
                      <div className="flex items-center gap-2">
                        <span className="text-base font-bold text-slate-900 dark:text-white">
                          {workspaceDetail.candidate_profile.full_name}
                        </span>
                        <Badge variant="brand" size="sm">
                          {workspaceDetail.candidate_profile.roll_number}
                        </Badge>
                      </div>
                      <div className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-2">
                        <GraduationCap className="w-4 h-4 text-slate-400" />
                        <span>
                          {workspaceDetail.candidate_profile.department} • Batch of{' '}
                          {workspaceDetail.candidate_profile.graduation_year} (CGPA:{' '}
                          <span className="font-semibold text-slate-900 dark:text-white">
                            {workspaceDetail.candidate_profile.cgpa.toFixed(2)}
                          </span>
                          )
                        </span>
                      </div>
                      {workspaceDetail.candidate_profile.skills?.length > 0 && (
                        <div className="flex flex-wrap gap-1 pt-1">
                          {workspaceDetail.candidate_profile.skills.slice(0, 6).map((sk, idx) => (
                            <span
                              key={idx}
                              className="px-2 py-0.5 text-[11px] bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-200 rounded border border-slate-200 dark:border-slate-600 font-medium"
                            >
                              {sk}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>

                    <div className="space-y-1.5 border-t md:border-t-0 md:border-l border-slate-200 dark:border-slate-700 md:pl-4 pt-2 md:pt-0">
                      <div className="text-xs text-slate-500 uppercase tracking-wider font-semibold">
                        Role & Company
                      </div>
                      <div className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
                        <Building className="w-4 h-4 text-brand-500" />
                        {workspaceDetail.job.title}
                      </div>
                      <div className="text-xs text-slate-500 dark:text-slate-400">
                        {workspaceDetail.job.company_name} • {workspaceDetail.job.ctc_lpa ? `${workspaceDetail.job.ctc_lpa} LPA` : 'Competitive'} ({workspaceDetail.job.work_mode})
                      </div>
                      {workspaceDetail.candidate_profile.compatibility_score && (
                        <div className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-brand-50 dark:bg-brand-950/60 text-brand-700 dark:text-brand-300 rounded-md text-xs font-semibold">
                          <Award className="w-4 h-4 text-brand-500" />
                          Compatibility Score: {workspaceDetail.candidate_profile.compatibility_score.toFixed(1)}%
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Current Round Details */}
                  <div className="p-4 border border-slate-200 dark:border-slate-800 rounded-xl space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <h4 className="font-bold text-slate-900 dark:text-white">
                          Round {workspaceDetail.interview.round_number}: {workspaceDetail.interview.round_title}
                        </h4>
                        <Badge variant={STATUS_VARIANTS[workspaceDetail.interview.status] || 'neutral'} size="sm">
                          {workspaceDetail.interview.status.replace('_', ' ')}
                        </Badge>
                        <Badge variant={OUTCOME_VARIANTS[workspaceDetail.interview.outcome] || 'neutral'} size="sm">
                          {workspaceDetail.interview.outcome.replace('_', ' ')}
                        </Badge>
                      </div>

                      <div className="flex items-center gap-2">
                        {workspaceDetail.interview.status !== 'cancelled' && (
                          <>
                            <Button
                              variant="secondary"
                              size="sm"
                              className="text-xs py-1"
                              onClick={() => handleOpenOutcome(workspaceDetail.interview)}
                            >
                              Record Outcome
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              className="text-xs py-1"
                              onClick={() => handleOpenReschedule(workspaceDetail.interview)}
                            >
                              Reschedule
                            </Button>
                          </>
                        )}
                      </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-slate-600 dark:text-slate-400">
                      <div>
                        <span className="font-semibold text-slate-700 dark:text-slate-300">Scheduled Time:</span>{' '}
                        {new Date(workspaceDetail.interview.scheduled_start_time).toLocaleString()} (
                        {workspaceDetail.interview.duration_minutes} min)
                      </div>
                      <div>
                        <span className="font-semibold text-slate-700 dark:text-slate-300">Interview Mode:</span>{' '}
                        {workspaceDetail.interview.interview_mode === 'virtual' ? 'Virtual (Online)' : 'In-Person'}
                      </div>
                      {workspaceDetail.interview.meeting_link && (
                        <div className="col-span-full flex items-center gap-2">
                          <span className="font-semibold text-slate-700 dark:text-slate-300">Meeting Link:</span>
                          <a
                            href={workspaceDetail.interview.meeting_link}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-brand-600 dark:text-brand-400 hover:underline flex items-center gap-1 font-medium"
                          >
                            <ExternalLink className="w-3.5 h-3.5" />
                            {workspaceDetail.interview.meeting_link}
                          </a>
                        </div>
                      )}
                      {workspaceDetail.interview.location && (
                        <div className="col-span-full">
                          <span className="font-semibold text-slate-700 dark:text-slate-300">Venue:</span>{' '}
                          {workspaceDetail.interview.location}
                        </div>
                      )}
                      {workspaceDetail.interview.instructions && (
                        <div className="col-span-full p-2.5 bg-slate-50 dark:bg-slate-800/60 rounded-lg border border-slate-200 dark:border-slate-700">
                          <span className="font-semibold text-slate-700 dark:text-slate-300">Instructions:</span>{' '}
                          {workspaceDetail.interview.instructions}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Past Rounds Timeline */}
                  {workspaceDetail.past_rounds?.length > 0 && (
                    <div className="space-y-2">
                      <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                        Round Progression History
                      </h4>
                      <div className="space-y-2">
                        {workspaceDetail.past_rounds.map((pr) => (
                          <div
                            key={pr.id}
                            className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 flex items-center justify-between text-xs"
                          >
                            <div>
                              <span className="font-semibold text-slate-900 dark:text-white">
                                Round {pr.round_number}: {pr.round_title}
                              </span>
                              <div className="text-[11px] text-slate-500">
                                {new Date(pr.scheduled_start_time).toLocaleDateString()} • {pr.interview_mode}
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              <Badge variant={OUTCOME_VARIANTS[pr.outcome] || 'neutral'} size="sm">
                                {pr.outcome}
                              </Badge>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Evaluations & Scorecards */}
                  <div className="space-y-3">
                    <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center justify-between">
                      <span>Interviewer Evaluations ({workspaceDetail.evaluations?.length || 0})</span>
                    </h4>

                    {(!workspaceDetail.evaluations || workspaceDetail.evaluations.length === 0) ? (
                      <div className="p-4 bg-slate-50 dark:bg-slate-800/30 rounded-xl text-xs text-slate-500 text-center">
                        No evaluation scorecards submitted yet for this round.
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {workspaceDetail.evaluations.map((ev, idx) => (
                          <div
                            key={idx}
                            className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-800/60 space-y-2.5"
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <span className="font-semibold text-slate-900 dark:text-white">
                                  {ev.interviewer_name}
                                </span>
                                <Badge variant="info" size="sm">
                                  {ev.stage}
                                </Badge>
                              </div>
                              <div className="flex items-center gap-2">
                                <span className="px-2 py-0.5 bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 font-bold rounded text-xs">
                                  {ev.recommendation.replace('_', ' ').toUpperCase()}
                                </span>
                                <div className="flex items-center text-amber-500 font-bold text-xs gap-1">
                                  <Star className="w-3.5 h-3.5 fill-current" />
                                  {ev.overall_rating}/5.0
                                </div>
                              </div>
                            </div>

                            {/* Criteria rating breakdown */}
                            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-xs pt-1">
                              {ev.technical_rating && (
                                <div className="p-2 bg-slate-50 dark:bg-slate-800 rounded">
                                  <span className="text-slate-400 block text-[10px]">Technical</span>
                                  <span className="font-bold text-slate-800 dark:text-slate-200">
                                    {ev.technical_rating}/5
                                  </span>
                                </div>
                              )}
                              {ev.problem_solving_rating && (
                                <div className="p-2 bg-slate-50 dark:bg-slate-800 rounded">
                                  <span className="text-slate-400 block text-[10px]">Problem Solving</span>
                                  <span className="font-bold text-slate-800 dark:text-slate-200">
                                    {ev.problem_solving_rating}/5
                                  </span>
                                </div>
                              )}
                              {ev.communication_rating && (
                                <div className="p-2 bg-slate-50 dark:bg-slate-800 rounded">
                                  <span className="text-slate-400 block text-[10px]">Communication</span>
                                  <span className="font-bold text-slate-800 dark:text-slate-200">
                                    {ev.communication_rating}/5
                                  </span>
                                </div>
                              )}
                              {ev.project_depth_rating && (
                                <div className="p-2 bg-slate-50 dark:bg-slate-800 rounded">
                                  <span className="text-slate-400 block text-[10px]">Project Depth</span>
                                  <span className="font-bold text-slate-800 dark:text-slate-200">
                                    {ev.project_depth_rating}/5
                                  </span>
                                </div>
                              )}
                              {ev.cultural_fit_rating && (
                                <div className="p-2 bg-slate-50 dark:bg-slate-800 rounded">
                                  <span className="text-slate-400 block text-[10px]">Cultural Fit</span>
                                  <span className="font-bold text-slate-800 dark:text-slate-200">
                                    {ev.cultural_fit_rating}/5
                                  </span>
                                </div>
                              )}
                            </div>

                            {ev.written_feedback && (
                              <p className="text-xs text-slate-600 dark:text-slate-300 italic pt-1 border-t border-slate-100 dark:border-slate-800">
                                "{ev.written_feedback}"
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* DAY EVENTS POPUP MODAL (When clicking +X more in calendar cell) */}
        {selectedDayEvents && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
              <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
                <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                  <CalendarIcon className="w-5 h-5 text-brand-600" />
                  Interviews on {new Date(selectedDayEvents.date).toLocaleDateString()}
                </h3>
                <button
                  onClick={() => setSelectedDayEvents(null)}
                  className="p-1 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-slate-500"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="space-y-2 max-h-80 overflow-y-auto">
                {selectedDayEvents.events.map((ev) => (
                  <div
                    key={ev.id}
                    onClick={() => {
                      setSelectedDayEvents(null);
                      handleOpenWorkspace(ev.id);
                    }}
                    className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800 cursor-pointer transition-colors space-y-1"
                  >
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold text-slate-900 dark:text-white">
                        {ev.student_name} ({ev.roll_number})
                      </span>
                      <Badge variant={STATUS_VARIANTS[ev.status] || 'neutral'} size="sm">
                        {ev.status}
                      </Badge>
                    </div>
                    <div className="text-xs text-slate-600 dark:text-slate-400">
                      R{ev.round_number}: {ev.round_title} • {ev.duration_minutes} min
                    </div>
                    <div className="text-[11px] text-slate-500 flex items-center gap-1">
                      <Clock className="w-3 h-3 text-slate-400" />
                      {new Date(ev.scheduled_start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
};
