import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertCircle,
  Award,
  Bell,
  BellRing,
  Briefcase,
  Building,
  Calendar as CalendarIcon,
  Check,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock,
  ExternalLink,
  Filter,
  GitBranch,
  History,
  List as ListIcon,
  MapPin,
  RefreshCw,
  RotateCcw,
  Search,
  Settings2,
  SlidersHorizontal,
  Sparkles,
  UserCheck,
  Video,
  X,
  XCircle,
} from 'lucide-react';
import { DashboardLayout } from '../../components/layout/DashboardLayout';
import { Card } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { applicationApi, interviewApi, notificationApi } from '../../services/api';
import {
  ApplicationStageStatus,
  ApplicationTrackerResponse,
  NotificationPreference,
  PlacementNotification,
  StudentInterviewListResponse,
  StudentInterviewTrackingItem,
  TrackerApplicationItem,
  TrackerCalendarEvent,
} from '../../types';

type ActiveTab = 'overview' | 'interviews' | 'calendar' | 'notifications';
type CalendarMode = 'month' | 'list';

const STATUS_OPTIONS: Array<{ value: ApplicationStageStatus | ''; label: string }> = [
  { value: '', label: 'All Application Stages' },
  { value: 'applied', label: 'Applied' },
  { value: 'under_review', label: 'Under Review' },
  { value: 'shortlisted', label: 'Shortlisted' },
  { value: 'interview_scheduled', label: 'Interview Scheduled' },
  { value: 'interviewed', label: 'Interviewed' },
  { value: 'offered', label: 'Offered' },
  { value: 'offer_accepted', label: 'Offer Accepted' },
  { value: 'offer_declined', label: 'Offer Declined' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'withdrawn', label: 'Withdrawn' },
];

const INTERVIEW_STATUS_OPTIONS = [
  { value: '', label: 'All Interview States' },
  { value: 'upcoming', label: 'Has Upcoming Interview' },
  { value: 'scheduled', label: 'Has Scheduled Interview' },
  { value: 'completed', label: 'Has Completed Interview' },
  { value: 'cancelled', label: 'Has Cancelled Interview' },
  { value: 'none', label: 'No Interviews Yet' },
];

const formatStatusLabel = (value: string) => value.replace(/_/g, ' ').toUpperCase();

const getStatusBadgeVariant = (
  status: string
): 'brand' | 'success' | 'warning' | 'danger' | 'info' | 'neutral' => {
  switch (status) {
    case 'offered':
    case 'offer_accepted':
    case 'passed':
      return 'success';
    case 'shortlisted':
    case 'interview_scheduled':
    case 'interviewed':
    case 'on_hold':
      return 'warning';
    case 'under_review':
    case 'scheduled':
      return 'info';
    case 'rejected':
    case 'offer_declined':
    case 'failed':
    case 'cancelled':
      return 'danger';
    default:
      return 'neutral';
  }
};

const formatDateTime = (iso?: string | null) => {
  if (!iso) return 'Not specified';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return 'Not specified';
  return d.toLocaleString([], {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const formatDateOnly = (iso?: string | null) => {
  if (!iso) return 'Not specified';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return 'Not specified';
  return d.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' });
};

const getEventPillStyle = (eventType: TrackerCalendarEvent['event_type']) => {
  switch (eventType) {
    case 'interview':
      return 'bg-indigo-100 text-indigo-800 border-indigo-200 dark:bg-indigo-950/70 dark:text-indigo-300 dark:border-indigo-800';
    case 'offer_deadline':
      return 'bg-emerald-100 text-emerald-800 border-emerald-200 dark:bg-emerald-950/70 dark:text-emerald-300 dark:border-emerald-800';
    case 'application_deadline':
      return 'bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-950/70 dark:text-amber-300 dark:border-amber-800';
    case 'drive_registration':
      return 'bg-sky-100 text-sky-800 border-sky-200 dark:bg-sky-950/70 dark:text-sky-300 dark:border-sky-800';
  }
};

export const ApplicationTrackerPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ActiveTab>('overview');
  const [calendarMode, setCalendarMode] = useState<CalendarMode>('month');
  const [calendarCursor, setCalendarCursor] = useState<Date>(() => {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), 1);
  });

  // Filters & Pagination
  const [statusFilter, setStatusFilter] = useState<ApplicationStageStatus | ''>('');
  const [companyFilter, setCompanyFilter] = useState<string>('');
  const [roleFilter, setRoleFilter] = useState<string>('');
  const [interviewFilter, setInterviewFilter] = useState<string>('');
  const [dateFrom, setDateFrom] = useState<string>('');
  const [dateTo, setDateTo] = useState<string>('');
  const [page, setPage] = useState<number>(0);
  const pageSize = 10;

  // Data States
  const [tracker, setTracker] = useState<ApplicationTrackerResponse | null>(null);
  const [interviewsData, setInterviewsData] = useState<StudentInterviewListResponse | null>(null);
  const [calendarEvents, setCalendarEvents] = useState<TrackerCalendarEvent[]>([]);
  const [notifications, setNotifications] = useState<PlacementNotification[]>([]);
  const [preferences, setPreferences] = useState<NotificationPreference | null>(null);
  const [unreadOnlyFilter, setUnreadOnlyFilter] = useState<boolean>(false);

  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Selected application timeline drawer & modal action states
  const [selectedApp, setSelectedApp] = useState<TrackerApplicationItem | null>(null);
  const [offerNotes, setOfferNotes] = useState<string>('');
  const [offerActionLoading, setOfferActionLoading] = useState<boolean>(false);
  const [withdrawReason, setWithdrawReason] = useState<string>('');
  const [showWithdrawForm, setShowWithdrawForm] = useState<boolean>(false);
  const [withdrawLoading, setWithdrawLoading] = useState<boolean>(false);
  const [savingPrefs, setSavingPrefs] = useState<boolean>(false);

  const buildFilterParams = useCallback(() => {
    const params: {
      status?: ApplicationStageStatus;
      company?: string;
      role?: string;
      interview_status?: string;
      date_from?: string;
      date_to?: string;
    } = {};
    if (statusFilter) params.status = statusFilter;
    if (companyFilter.trim()) params.company = companyFilter.trim();
    if (roleFilter.trim()) params.role = roleFilter.trim();
    if (interviewFilter) params.interview_status = interviewFilter;
    if (dateFrom) params.date_from = new Date(`${dateFrom}T00:00:00Z`).toISOString();
    if (dateTo) params.date_to = new Date(`${dateTo}T23:59:59Z`).toISOString();
    return params;
  }, [statusFilter, companyFilter, roleFilter, interviewFilter, dateFrom, dateTo]);

  const loadAllData = useCallback(
    async (isManualRefresh = false) => {
      try {
        if (isManualRefresh) setRefreshing(true);
        else setLoading(true);

        const filterParams = buildFilterParams();
        const [trackerRes, interviewsRes, calendarRes, notifRes, prefRes] = await Promise.all([
          applicationApi.getTracker({
            ...filterParams,
            skip: page * pageSize,
            limit: pageSize,
            sync_notifications: true,
          }),
          interviewApi.getMyInterviews({
            company: filterParams.company,
          }),
          applicationApi.getCalendarEvents({
            status: filterParams.status,
            company: filterParams.company,
            role: filterParams.role,
            interview_status: filterParams.interview_status,
          }),
          notificationApi.listNotifications({
            unread_only: unreadOnlyFilter,
            limit: 50,
          }),
          notificationApi.getPreferences(),
        ]);

        setTracker(trackerRes);
        setInterviewsData(interviewsRes);
        setCalendarEvents(calendarRes.events);
        setNotifications(notifRes);
        setPreferences(prefRes);

        if (selectedApp) {
          const updatedSelected = trackerRes.items.find((i) => i.id === selectedApp.id);
          if (updatedSelected) {
            setSelectedApp(updatedSelected);
          }
        }
      } catch (err: unknown) {
        console.error('Failed to load application tracker:', err);
        setFeedback({
          type: 'error',
          text: 'Unable to load recruitment tracker data. Please verify connectivity and retry.',
        });
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [buildFilterParams, page, pageSize, unreadOnlyFilter, selectedApp?.id]
  );

  useEffect(() => {
    loadAllData();
  }, [loadAllData]);

  const handleResetFilters = () => {
    setStatusFilter('');
    setCompanyFilter('');
    setRoleFilter('');
    setInterviewFilter('');
    setDateFrom('');
    setDateTo('');
    setPage(0);
  };

  const handleOfferResponse = async (applicationId: number, accept: boolean) => {
    try {
      setOfferActionLoading(true);
      setFeedback(null);
      await applicationApi.respondToOffer(applicationId, accept, offerNotes.trim() || undefined);
      setOfferNotes('');
      setFeedback({
        type: 'success',
        text: accept
          ? 'Official offer accepted! Your recruitment timeline has been updated.'
          : 'Offer declined and recorded in your recruitment timeline.',
      });
      await loadAllData(true);
      const updatedDetail = await applicationApi.getApplicationDetail(applicationId);
      setSelectedApp((prev) => (prev && prev.id === applicationId ? { ...prev, ...updatedDetail } : prev));
    } catch (err: unknown) {
      const apiErr = err as { response?: { data?: { message?: string; detail?: string } } };
      setFeedback({
        type: 'error',
        text: apiErr?.response?.data?.message || apiErr?.response?.data?.detail || 'Offer response failed.',
      });
    } finally {
      setOfferActionLoading(false);
    }
  };

  const handleWithdrawApplication = async (applicationId: number) => {
    if (withdrawReason.trim().length < 5) {
      setFeedback({ type: 'error', text: 'Please provide a withdrawal reason of at least 5 characters.' });
      return;
    }
    try {
      setWithdrawLoading(true);
      setFeedback(null);
      await applicationApi.withdrawApplication(applicationId, withdrawReason.trim());
      setWithdrawReason('');
      setShowWithdrawForm(false);
      setFeedback({
        type: 'success',
        text: 'Application withdrawn cleanly and logged in your chronological history.',
      });
      await loadAllData(true);
      const updatedDetail = await applicationApi.getApplicationDetail(applicationId);
      setSelectedApp((prev) => (prev && prev.id === applicationId ? { ...prev, ...updatedDetail } : prev));
    } catch (err: unknown) {
      const apiErr = err as { response?: { data?: { message?: string; detail?: string } } };
      setFeedback({
        type: 'error',
        text: apiErr?.response?.data?.message || apiErr?.response?.data?.detail || 'Unable to withdraw application.',
      });
    } finally {
      setWithdrawLoading(false);
    }
  };

  const handleMarkNotificationRead = async (id: number) => {
    try {
      await notificationApi.markAsRead(id);
      await loadAllData(true);
    } catch (err) {
      console.error('Failed to mark notification read:', err);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      const res = await notificationApi.markAllAsRead();
      setFeedback({
        type: 'success',
        text: `Marked ${res.marked_read_count} notification(s) as read.`,
      });
      await loadAllData(true);
    } catch (err) {
      console.error('Failed to mark all notifications read:', err);
    }
  };

  const handleSyncNotifications = async () => {
    try {
      const res = await notificationApi.syncSmartNotifications();
      setFeedback({
        type: 'success',
        text:
          res.generated_count > 0
            ? `Generated ${res.generated_count} new smart alert(s) respecting your preferences.`
            : 'All upcoming interview, offer deadline, and placement alerts are already up to date.',
      });
      await loadAllData(true);
    } catch (err) {
      console.error('Failed to sync notifications:', err);
    }
  };

  const handleTogglePreference = async (
    key: keyof Omit<NotificationPreference, 'user_id' | 'updated_at' | 'reminder_hours_before'>,
    nextValue: boolean
  ) => {
    if (!preferences) return;
    try {
      setSavingPrefs(true);
      const updated = await notificationApi.updatePreferences({ [key]: nextValue });
      setPreferences(updated);
      setFeedback({ type: 'success', text: 'Notification preferences saved.' });
    } catch (err) {
      console.error('Failed to update notification preferences:', err);
      setFeedback({ type: 'error', text: 'Failed to update notification preference.' });
    } finally {
      setSavingPrefs(false);
    }
  };

  const handleReminderHoursChange = async (hours: number) => {
    try {
      setSavingPrefs(true);
      const updated = await notificationApi.updatePreferences({ reminder_hours_before: hours });
      setPreferences(updated);
      setFeedback({ type: 'success', text: `Reminder lead time updated to ${hours} hours.` });
    } catch (err) {
      console.error('Failed to update reminder lead hours:', err);
    } finally {
      setSavingPrefs(false);
    }
  };

  // Calendar grid computation
  const calendarDays = useMemo(() => {
    const year = calendarCursor.getFullYear();
    const month = calendarCursor.getMonth();
    const firstDayOfMonth = new Date(year, month, 1);
    const startOffset = firstDayOfMonth.getDay();
    const gridStart = new Date(year, month, 1 - startOffset);
    const days: Date[] = [];
    for (let i = 0; i < 42; i++) {
      days.push(new Date(gridStart.getFullYear(), gridStart.getMonth(), gridStart.getDate() + i));
    }
    return days;
  }, [calendarCursor]);

  const eventsByDateKey = useMemo(() => {
    const map: Record<string, TrackerCalendarEvent[]> = {};
    for (const ev of calendarEvents) {
      const d = new Date(ev.start_at);
      if (Number.isNaN(d.getTime())) continue;
      const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
      if (!map[key]) map[key] = [];
      map[key].push(ev);
    }
    return map;
  }, [calendarEvents]);

  const openTimelineByAppId = async (applicationId?: number | null) => {
    if (!applicationId) return;
    const found = tracker?.items.find((a) => a.id === applicationId);
    if (found) {
      setSelectedApp(found);
      return;
    }
    try {
      const detail = await applicationApi.getApplicationDetail(applicationId);
      setSelectedApp(detail);
    } catch (err) {
      console.error('Unable to open application timeline:', err);
    }
  };

  const totalPages = tracker ? Math.max(1, Math.ceil(tracker.total / pageSize)) : 1;
  const summary = tracker?.summary;

  return (
    <DashboardLayout
      role="student"
      title="Smart Application & Recruitment Tracker"
      subtitle="Centralized tracking for your applications, chronological stage history, interview schedules, offer decisions, and smart alerts."
    >
      <div className="space-y-6">
        {/* Top Action & Navigation Header */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2 bg-white dark:bg-slate-900 p-1.5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
            <button
              type="button"
              onClick={() => setActiveTab('overview')}
              className={`px-3.5 py-2 text-xs font-semibold rounded-lg transition-all flex items-center gap-1.5 ${
                activeTab === 'overview'
                  ? 'bg-brand-600 text-white shadow-sm'
                  : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
              }`}
            >
              <Briefcase className="w-3.5 h-3.5" />
              <span>Applications ({summary?.total_applications ?? 0})</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('interviews')}
              className={`px-3.5 py-2 text-xs font-semibold rounded-lg transition-all flex items-center gap-1.5 ${
                activeTab === 'interviews'
                  ? 'bg-brand-600 text-white shadow-sm'
                  : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
              }`}
            >
              <Video className="w-3.5 h-3.5" />
              <span>Interviews ({interviewsData?.total ?? 0})</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('calendar')}
              className={`px-3.5 py-2 text-xs font-semibold rounded-lg transition-all flex items-center gap-1.5 ${
                activeTab === 'calendar'
                  ? 'bg-brand-600 text-white shadow-sm'
                  : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
              }`}
            >
              <CalendarIcon className="w-3.5 h-3.5" />
              <span>Calendar & Deadlines ({calendarEvents.length})</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('notifications')}
              className={`px-3.5 py-2 text-xs font-semibold rounded-lg transition-all flex items-center gap-1.5 ${
                activeTab === 'notifications'
                  ? 'bg-brand-600 text-white shadow-sm'
                  : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
              }`}
            >
              <Bell className="w-3.5 h-3.5" />
              <span>Smart Alerts</span>
              {(tracker?.unread_notifications_count ?? 0) > 0 && (
                <span className="ml-1 px-1.5 py-0.5 text-[10px] rounded-full bg-rose-500 text-white font-bold">
                  {tracker?.unread_notifications_count}
                </span>
              )}
            </button>
          </div>

          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => loadAllData(true)}
              isLoading={refreshing}
              icon={<RefreshCw className="w-3.5 h-3.5" />}
            >
              Refresh Tracker
            </Button>
            <Link to="/student/jobs">
              <Button size="sm" variant="primary" icon={<Sparkles className="w-3.5 h-3.5" />}>
                Explore Jobs
              </Button>
            </Link>
          </div>
        </div>

        {/* Feedback Banner */}
        {feedback && (
          <div
            className={`p-3.5 rounded-xl border text-xs flex items-center justify-between gap-2 ${
              feedback.type === 'success'
                ? 'bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-200'
                : 'bg-rose-50 dark:bg-rose-950/40 border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-200'
            }`}
          >
            <div className="flex items-center gap-2">
              {feedback.type === 'success' ? (
                <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
              ) : (
                <AlertCircle className="w-4 h-4 shrink-0 text-rose-600 dark:text-rose-400" />
              )}
              <span>{feedback.text}</span>
            </div>
            <button
              type="button"
              onClick={() => setFeedback(null)}
              className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Portfolio KPI Summary Row */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
          <Card className="p-4">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
              Total Applications
            </div>
            <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-1">
              {summary?.total_applications ?? 0}
            </div>
            <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
              {summary?.active_count ?? 0} active in pipeline
            </div>
          </Card>

          <Card className="p-4">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
              Upcoming Interviews
            </div>
            <div className="text-2xl font-bold text-indigo-600 dark:text-indigo-400 mt-1">
              {summary?.upcoming_interviews_count ?? 0}
            </div>
            <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
              {summary?.completed_interviews_count ?? 0} completed rounds
            </div>
          </Card>

          <Card className="p-4">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
              Pending Offers
            </div>
            <div className="text-2xl font-bold text-amber-600 dark:text-amber-400 mt-1">
              {summary?.pending_offers_count ?? 0}
            </div>
            <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
              Awaiting your decision
            </div>
          </Card>

          <Card className="p-4">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
              Offers Accepted
            </div>
            <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-1">
              {summary?.accepted_offers_count ?? 0}
            </div>
            <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
              Confirmed placements
            </div>
          </Card>

          <Card className="p-4 col-span-2 sm:col-span-1">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
              Unread Alerts
            </div>
            <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-1">
              {tracker?.unread_notifications_count ?? 0}
            </div>
            <button
              type="button"
              onClick={() => setActiveTab('notifications')}
              className="text-[11px] font-semibold text-brand-600 dark:text-brand-400 hover:underline mt-0.5"
            >
              Manage alerts & preferences →
            </button>
          </Card>
        </div>

        {/* Pending Offer Spotlight Banner */}
        {tracker && tracker.items.some((i) => i.current_status === 'offered') && (
          <Card className="border-emerald-300 dark:border-emerald-800/80 bg-emerald-50/50 dark:bg-emerald-950/20">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-xl bg-emerald-600 text-white flex items-center justify-center shrink-0">
                  <Award className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                    Official Offer Waiting for Your Response
                  </h3>
                  <p className="text-xs text-slate-600 dark:text-slate-300 mt-0.5">
                    Review your compensation package, response deadline, and submit your decision through the authorized Offer Management workflow.
                  </p>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                {tracker.items
                  .filter((i) => i.current_status === 'offered')
                  .map((offerApp) => (
                    <Button
                      key={offerApp.id}
                      size="sm"
                      variant="primary"
                      onClick={() => setSelectedApp(offerApp)}
                    >
                      Review {offerApp.company_name || 'Offer'} ({offerApp.job_title})
                    </Button>
                  ))}
              </div>
            </div>
          </Card>
        )}

        {/* Multi-Criteria Filter Bar */}
        {(activeTab === 'overview' || activeTab === 'calendar') && (
          <Card className="p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2 text-xs font-bold text-slate-700 dark:text-slate-200 uppercase tracking-wider">
                <SlidersHorizontal className="w-3.5 h-3.5 text-brand-600 dark:text-brand-400" />
                <span>Filter Applications & Timeline</span>
              </div>
              <button
                type="button"
                onClick={handleResetFilters}
                className="text-xs font-semibold text-slate-500 hover:text-brand-600 dark:text-slate-400 dark:hover:text-brand-400 flex items-center gap-1"
              >
                <RotateCcw className="w-3 h-3" />
                <span>Reset Filters</span>
              </button>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-3">
              <div className="relative">
                <Building className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={companyFilter}
                  onChange={(e) => {
                    setCompanyFilter(e.target.value);
                    setPage(0);
                  }}
                  placeholder="Company name..."
                  className="w-full pl-8 pr-3 py-2 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
              </div>

              <div className="relative">
                <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={roleFilter}
                  onChange={(e) => {
                    setRoleFilter(e.target.value);
                    setPage(0);
                  }}
                  placeholder="Job role title..."
                  className="w-full pl-8 pr-3 py-2 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
              </div>

              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value as ApplicationStageStatus | '');
                  setPage(0);
                }}
                aria-label="Filter by application status"
                className="w-full px-3 py-2 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-brand-500"
              >
                {STATUS_OPTIONS.map((opt) => (
                  <option key={opt.value || 'all'} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>

              <select
                value={interviewFilter}
                onChange={(e) => {
                  setInterviewFilter(e.target.value);
                  setPage(0);
                }}
                aria-label="Filter by interview status"
                className="w-full px-3 py-2 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-brand-500"
              >
                {INTERVIEW_STATUS_OPTIONS.map((opt) => (
                  <option key={opt.value || 'all-iv'} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>

              <input
                type="date"
                value={dateFrom}
                onChange={(e) => {
                  setDateFrom(e.target.value);
                  setPage(0);
                }}
                aria-label="Applied from date"
                className="w-full px-3 py-2 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-brand-500"
              />

              <input
                type="date"
                value={dateTo}
                onChange={(e) => {
                  setDateTo(e.target.value);
                  setPage(0);
                }}
                aria-label="Applied to date"
                className="w-full px-3 py-2 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
          </Card>
        )}

        {/* TAB 1: APPLICATIONS OVERVIEW */}
        {activeTab === 'overview' && (
          <div className="space-y-4">
            {loading && !tracker ? (
              <Card className="p-12 text-center text-xs text-slate-500 dark:text-slate-400">
                Loading your application pipelines, interview rounds, and recruitment timelines...
              </Card>
            ) : !tracker || tracker.items.length === 0 ? (
              <Card className="p-12 text-center">
                <Briefcase className="w-12 h-12 mx-auto text-slate-300 dark:text-slate-700 mb-3" />
                <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200">
                  No matching applications found
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-md mx-auto">
                  {summary && summary.total_applications > 0
                    ? 'Try clearing or adjusting your active filters to view your submitted applications.'
                    : 'Explore eligible placement drives and submit your first application to track its complete recruitment lifecycle here.'}
                </p>
                <div className="mt-4 flex justify-center gap-2">
                  {summary && summary.total_applications > 0 && (
                    <Button size="sm" variant="outline" onClick={handleResetFilters}>
                      Clear Filters
                    </Button>
                  )}
                  <Link to="/student/jobs">
                    <Button size="sm" variant="primary">
                      Browse Eligible Jobs
                    </Button>
                  </Link>
                </div>
              </Card>
            ) : (
              <>
                <div className="grid grid-cols-1 gap-4">
                  {tracker.items.map((app) => (
                    <Card
                      key={app.id}
                      className="p-5 hover:border-brand-300 dark:hover:border-brand-700 transition-all"
                    >
                      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                        {/* Left: Role, Company, Stage & Score */}
                        <div className="space-y-2 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="inline-flex items-center gap-1 text-xs font-semibold text-slate-500 dark:text-slate-400">
                              <Building className="w-3.5 h-3.5" />
                              {app.company_name || 'Partner Company'}
                            </span>
                            <span className="text-slate-300 dark:text-slate-700">•</span>
                            <Badge variant={getStatusBadgeVariant(app.current_status)} size="sm">
                              {formatStatusLabel(app.current_status)}
                            </Badge>
                            {app.drive_id && (
                              <Badge variant="neutral" size="sm">
                                TPO: {formatStatusLabel(app.tpo_screening_status)}
                              </Badge>
                            )}
                            {app.drive_name && (
                              <span className="text-[11px] text-slate-500 dark:text-slate-400">
                                {app.drive_name}
                              </span>
                            )}
                          </div>

                          <div className="flex flex-wrap items-baseline justify-between gap-2">
                            <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                              {app.job_title || `Job #${app.job_id}`}
                            </h3>
                            <div className="text-xs font-semibold text-brand-700 dark:text-brand-300 bg-brand-50 dark:bg-brand-950/60 px-2.5 py-1 rounded-full border border-brand-200/70 dark:border-brand-800/70">
                              Match Snapshot: {app.compatibility_score_at_application.toFixed(1)}%
                            </div>
                          </div>

                          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-2 text-xs">
                            <div className="bg-slate-50 dark:bg-slate-800/60 rounded-lg p-2.5 border border-slate-100 dark:border-slate-800">
                              <div className="text-[10px] font-semibold uppercase text-slate-400 dark:text-slate-500">
                                Applied Date
                              </div>
                              <div className="font-semibold text-slate-800 dark:text-slate-200 mt-0.5">
                                {formatDateOnly(app.created_at)}
                              </div>
                            </div>

                            <div className="bg-slate-50 dark:bg-slate-800/60 rounded-lg p-2.5 border border-slate-100 dark:border-slate-800">
                              <div className="text-[10px] font-semibold uppercase text-slate-400 dark:text-slate-500">
                                Application Deadline
                              </div>
                              <div className="font-semibold text-slate-800 dark:text-slate-200 mt-0.5">
                                {formatDateOnly(app.application_deadline)}
                              </div>
                            </div>

                            <div className="bg-slate-50 dark:bg-slate-800/60 rounded-lg p-2.5 border border-slate-100 dark:border-slate-800">
                              <div className="text-[10px] font-semibold uppercase text-slate-400 dark:text-slate-500">
                                Latest Update
                              </div>
                              <div className="font-semibold text-slate-800 dark:text-slate-200 mt-0.5 truncate">
                                {app.latest_update.title}
                              </div>
                              <div className="text-[10px] text-slate-500 dark:text-slate-400">
                                {formatDateOnly(app.latest_update.timestamp)}
                              </div>
                            </div>

                            <div className="bg-indigo-50/60 dark:bg-indigo-950/30 rounded-lg p-2.5 border border-indigo-100 dark:border-indigo-900/60">
                              <div className="text-[10px] font-semibold uppercase text-indigo-600 dark:text-indigo-400">
                                Next Scheduled Activity
                              </div>
                              <div className="font-semibold text-slate-900 dark:text-slate-100 mt-0.5 truncate">
                                {app.next_scheduled_activity.title}
                              </div>
                              {app.next_scheduled_activity.scheduled_at && (
                                <div className="text-[10px] text-indigo-700 dark:text-indigo-300">
                                  {formatDateTime(app.next_scheduled_activity.scheduled_at)}
                                </div>
                              )}
                            </div>
                          </div>
                        </div>

                        {/* Right: Actions */}
                        <div className="flex lg:flex-col items-stretch sm:items-center lg:items-end justify-between gap-2 shrink-0 border-t lg:border-t-0 lg:border-l border-slate-100 dark:border-slate-800 pt-3 lg:pt-0 lg:pl-4">
                          <div className="text-[11px] text-slate-500 dark:text-slate-400 text-left lg:text-right">
                            <div>{app.status_history.length} recorded transition(s)</div>
                            <div>
                              {app.upcoming_interviews_count} upcoming • {app.completed_interviews_count} completed rounds
                            </div>
                          </div>
                          <div className="flex flex-wrap items-center gap-2">
                            {app.current_status === 'offered' && (
                              <Button
                                size="sm"
                                variant="primary"
                                onClick={() => setSelectedApp(app)}
                                icon={<Award className="w-3.5 h-3.5" />}
                              >
                                Respond to Offer
                              </Button>
                            )}
                            <Button
                              size="sm"
                              variant={app.current_status === 'offered' ? 'outline' : 'secondary'}
                              onClick={() => setSelectedApp(app)}
                              icon={<GitBranch className="w-3.5 h-3.5" />}
                            >
                              View Timeline & Details
                            </Button>
                          </div>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>

                {/* Pagination */}
                <div className="flex items-center justify-between pt-2">
                  <span className="text-xs text-slate-500 dark:text-slate-400">
                    Showing {page * pageSize + 1}–{Math.min((page + 1) * pageSize, tracker.total)} of {tracker.total}{' '}
                    application(s)
                  </span>
                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={page === 0}
                      onClick={() => setPage((p) => Math.max(0, p - 1))}
                      icon={<ChevronLeft className="w-3.5 h-3.5" />}
                    >
                      Previous
                    </Button>
                    <span className="text-xs font-semibold text-slate-700 dark:text-slate-300 px-2">
                      Page {page + 1} of {totalPages}
                    </span>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={page + 1 >= totalPages}
                      onClick={() => setPage((p) => p + 1)}
                    >
                      <span>Next</span>
                      <ChevronRight className="w-3.5 h-3.5 ml-1" />
                    </Button>
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {/* TAB 2: INTERVIEW TRACKING */}
        {activeTab === 'interviews' && (
          <div className="space-y-6">
            {/* Upcoming Interviews */}
            <Card>
              <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800 mb-4">
                <div>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                    Upcoming Scheduled Interviews ({interviewsData?.upcoming.length ?? 0})
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Active rounds with meeting links, venue instructions, panel details, and reschedule notices.
                  </p>
                </div>
              </div>

              {!interviewsData || interviewsData.upcoming.length === 0 ? (
                <p className="text-xs text-slate-500 dark:text-slate-400 py-6 text-center">
                  No upcoming scheduled interview rounds at the moment.
                </p>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {interviewsData.upcoming.map((iv) => (
                    <InterviewCard key={iv.id} interview={iv} onOpenApplication={openTimelineByAppId} />
                  ))}
                </div>
              )}
            </Card>

            {/* Completed & Cancelled History */}
            <Card>
              <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800 mb-4">
                <div>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                    Completed & Cancelled Interview History (
                    {(interviewsData?.completed.length ?? 0) + (interviewsData?.cancelled_or_other.length ?? 0)})
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Audit trail of completed rounds, outcomes, and cancelled or past sessions.
                  </p>
                </div>
              </div>

              {!interviewsData ||
              (interviewsData.completed.length === 0 && interviewsData.cancelled_or_other.length === 0) ? (
                <p className="text-xs text-slate-500 dark:text-slate-400 py-6 text-center">
                  No completed or cancelled interviews recorded yet.
                </p>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {[...interviewsData.completed, ...interviewsData.cancelled_or_other].map((iv) => (
                    <InterviewCard key={iv.id} interview={iv} onOpenApplication={openTimelineByAppId} />
                  ))}
                </div>
              )}
            </Card>
          </div>
        )}

        {/* TAB 3: CALENDAR & DEADLINES */}
        {activeTab === 'calendar' && (
          <Card>
            <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-slate-100 dark:border-slate-800 mb-4">
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() =>
                    setCalendarCursor((d) => new Date(d.getFullYear(), d.getMonth() - 1, 1))
                  }
                  icon={<ChevronLeft className="w-3.5 h-3.5" />}
                >
                  Prev
                </Button>
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 min-w-[140px] text-center">
                  {calendarCursor.toLocaleDateString([], { month: 'long', year: 'numeric' })}
                </h3>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() =>
                    setCalendarCursor((d) => new Date(d.getFullYear(), d.getMonth() + 1, 1))
                  }
                >
                  <span>Next</span>
                  <ChevronRight className="w-3.5 h-3.5 ml-1" />
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => {
                    const now = new Date();
                    setCalendarCursor(new Date(now.getFullYear(), now.getMonth(), 1));
                  }}
                >
                  Today
                </Button>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setCalendarMode('month')}
                  className={`px-3 py-1.5 text-xs font-semibold rounded-lg flex items-center gap-1.5 ${
                    calendarMode === 'month'
                      ? 'bg-brand-600 text-white'
                      : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300'
                  }`}
                >
                  <CalendarIcon className="w-3.5 h-3.5" />
                  <span>Month Grid</span>
                </button>
                <button
                  type="button"
                  onClick={() => setCalendarMode('list')}
                  className={`px-3 py-1.5 text-xs font-semibold rounded-lg flex items-center gap-1.5 ${
                    calendarMode === 'list'
                      ? 'bg-brand-600 text-white'
                      : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300'
                  }`}
                >
                  <ListIcon className="w-3.5 h-3.5" />
                  <span>Agenda List</span>
                </button>
              </div>
            </div>

            {/* Event Type Legend */}
            <div className="flex flex-wrap items-center gap-3 mb-4 text-[11px]">
              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded border bg-indigo-100 text-indigo-800 border-indigo-200 dark:bg-indigo-950/70 dark:text-indigo-300 dark:border-indigo-800">
                Interview Round
              </span>
              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded border bg-emerald-100 text-emerald-800 border-emerald-200 dark:bg-emerald-950/70 dark:text-emerald-300 dark:border-emerald-800">
                Offer Response Deadline
              </span>
              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded border bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-950/70 dark:text-amber-300 dark:border-amber-800">
                Application Deadline
              </span>
              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded border bg-sky-100 text-sky-800 border-sky-200 dark:bg-sky-950/70 dark:text-sky-300 dark:border-sky-800">
                Drive Registration
              </span>
            </div>

            {calendarMode === 'month' ? (
              <div className="overflow-x-auto">
                <div className="min-w-[700px] grid grid-cols-7 border-t border-l border-slate-200 dark:border-slate-800 rounded-lg overflow-hidden">
                  {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((d) => (
                    <div
                      key={d}
                      className="bg-slate-50 dark:bg-slate-800/80 px-2 py-2 text-[11px] font-bold text-slate-600 dark:text-slate-300 border-r border-b border-slate-200 dark:border-slate-800 text-center"
                    >
                      {d}
                    </div>
                  ))}
                  {calendarDays.map((dayDate) => {
                    const key = `${dayDate.getFullYear()}-${String(dayDate.getMonth() + 1).padStart(2, '0')}-${String(
                      dayDate.getDate()
                    ).padStart(2, '0')}`;
                    const inCurrentMonth = dayDate.getMonth() === calendarCursor.getMonth();
                    const isToday = new Date().toDateString() === dayDate.toDateString();
                    const dayEvents = eventsByDateKey[key] || [];
                    return (
                      <div
                        key={key}
                        className={`min-h-[100px] p-1.5 border-r border-b border-slate-200 dark:border-slate-800 ${
                          inCurrentMonth
                            ? 'bg-white dark:bg-slate-900'
                            : 'bg-slate-50/70 dark:bg-slate-950/60 text-slate-400'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span
                            className={`text-[11px] font-semibold w-6 h-6 flex items-center justify-center rounded-full ${
                              isToday
                                ? 'bg-brand-600 text-white'
                                : inCurrentMonth
                                ? 'text-slate-700 dark:text-slate-300'
                                : 'text-slate-400 dark:text-slate-600'
                            }`}
                          >
                            {dayDate.getDate()}
                          </span>
                        </div>
                        <div className="space-y-1">
                          {dayEvents.map((ev) => (
                            <button
                              key={ev.event_id}
                              type="button"
                              onClick={() => openTimelineByAppId(ev.application_id)}
                              className={`w-full text-left px-1.5 py-1 rounded border text-[10px] font-medium truncate transition hover:opacity-80 ${getEventPillStyle(
                                ev.event_type
                              )}`}
                              title={`${ev.title} (${formatDateTime(ev.start_at)})`}
                            >
                              {ev.title}
                            </button>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : calendarEvents.length === 0 ? (
              <p className="text-xs text-slate-500 dark:text-slate-400 py-8 text-center">
                No scheduled interviews or deadlines match your current filters.
              </p>
            ) : (
              <div className="space-y-2.5">
                {calendarEvents.map((ev) => (
                  <div
                    key={ev.event_id}
                    className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40"
                  >
                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span
                          className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded border ${getEventPillStyle(
                            ev.event_type
                          )}`}
                        >
                          {ev.event_type.replace(/_/g, ' ')}
                        </span>
                        {ev.is_rescheduled && (
                          <Badge variant="warning" size="sm">
                            RESCHEDULED
                          </Badge>
                        )}
                        <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">
                          {formatDateTime(ev.start_at)}
                        </span>
                      </div>
                      <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100">{ev.title}</h4>
                      {ev.subtitle && (
                        <p className="text-xs text-slate-500 dark:text-slate-400">{ev.subtitle}</p>
                      )}
                      {ev.instructions && (
                        <p className="text-xs text-slate-600 dark:text-slate-300 mt-1">
                          Instructions: {ev.instructions}
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {ev.meeting_link && (
                        <a href={ev.meeting_link} target="_blank" rel="noreferrer">
                          <Button size="sm" variant="outline" icon={<ExternalLink className="w-3.5 h-3.5" />}>
                            Join Link
                          </Button>
                        </a>
                      )}
                      {ev.application_id && (
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => openTimelineByAppId(ev.application_id)}
                        >
                          View Application
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        )}

        {/* TAB 4: SMART NOTIFICATIONS & PREFERENCES */}
        {activeTab === 'notifications' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Notifications Inbox */}
            <Card className="lg:col-span-2">
              <div className="flex flex-wrap items-center justify-between gap-2 pb-4 border-b border-slate-100 dark:border-slate-800 mb-4">
                <div>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                    <BellRing className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                    <span>Smart Recruitment Alerts</span>
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Deduplicated alerts generated from live application changes, interview schedules, offer deadlines, and drives.
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <label className="inline-flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-300 cursor-pointer mr-2">
                    <input
                      type="checkbox"
                      checked={unreadOnlyFilter}
                      onChange={(e) => setUnreadOnlyFilter(e.target.checked)}
                      className="rounded border-slate-300 dark:border-slate-700"
                    />
                    <span>Unread only</span>
                  </label>
                  <Button size="sm" variant="outline" onClick={handleSyncNotifications}>
                    Sync Reminders
                  </Button>
                  <Button size="sm" variant="secondary" onClick={handleMarkAllRead}>
                    Mark All Read
                  </Button>
                </div>
              </div>

              {notifications.length === 0 ? (
                <div className="text-center py-10 text-xs text-slate-500 dark:text-slate-400">
                  <Bell className="w-8 h-8 mx-auto mb-2 opacity-30" />
                  No notifications in this view.
                </div>
              ) : (
                <div className="space-y-3">
                  {notifications.map((n) => (
                    <div
                      key={n.id}
                      className={`p-3.5 rounded-xl border transition-colors ${
                        n.is_read
                          ? 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800'
                          : 'bg-brand-50/50 dark:bg-brand-950/30 border-brand-200 dark:border-brand-800/80'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="space-y-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <Badge variant={n.is_read ? 'neutral' : 'brand'} size="sm">
                              {formatStatusLabel(n.category)}
                            </Badge>
                            <span className="text-[11px] text-slate-400 dark:text-slate-500">
                              {formatDateTime(n.created_at)}
                            </span>
                          </div>
                          <h4 className="text-xs font-bold text-slate-900 dark:text-slate-100">{n.title}</h4>
                          <p className="text-xs text-slate-600 dark:text-slate-300">{n.message}</p>
                        </div>

                        <div className="flex flex-col items-end gap-1.5 shrink-0">
                          {!n.is_read && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleMarkNotificationRead(n.id)}
                              icon={<Check className="w-3 h-3" />}
                            >
                              Mark Read
                            </Button>
                          )}
                          {n.related_application_id && (
                            <button
                              type="button"
                              onClick={() => openTimelineByAppId(n.related_application_id)}
                              className="text-[11px] font-semibold text-brand-600 dark:text-brand-400 hover:underline"
                            >
                              Open Application →
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>

            {/* Preferences Sidebar */}
            <Card>
              <div className="pb-3 border-b border-slate-100 dark:border-slate-800 mb-4">
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                  <Settings2 className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                  <span>Notification Preferences</span>
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  Control which smart alerts are generated for your account.
                </p>
              </div>

              {preferences ? (
                <div className="space-y-3">
                  {(
                    [
                      ['interview_schedules', 'Interview Schedule Updates', 'New rounds, reschedules, cancellations'],
                      ['upcoming_interview_reminders', 'Upcoming Interview Reminders', 'Alerts ahead of interview start time'],
                      ['status_changes', 'Application Status Changes', 'Shortlisting, TPO screening, review updates'],
                      ['offer_alerts', 'Offer Availability', 'Notifications when an offer is released'],
                      ['offer_deadline_reminders', 'Offer Response Deadlines', 'Reminders before offer acceptance cutoffs'],
                      ['placement_announcements', 'Placement Announcements', 'Active institutional placement drives'],
                    ] as const
                  ).map(([key, title, desc]) => (
                    <label
                      key={key}
                      className="flex items-start justify-between gap-3 p-2.5 rounded-lg border border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/40 cursor-pointer"
                    >
                      <div>
                        <div className="text-xs font-semibold text-slate-800 dark:text-slate-200">{title}</div>
                        <div className="text-[11px] text-slate-500 dark:text-slate-400">{desc}</div>
                      </div>
                      <input
                        type="checkbox"
                        checked={preferences[key]}
                        disabled={savingPrefs}
                        onChange={(e) => handleTogglePreference(key, e.target.checked)}
                        className="mt-1 h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                      />
                    </label>
                  ))}

                  <div className="pt-2 border-t border-slate-100 dark:border-slate-800">
                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-200 mb-1.5">
                      Reminder Lead Time
                    </label>
                    <select
                      value={preferences.reminder_hours_before}
                      disabled={savingPrefs}
                      onChange={(e) => handleReminderHoursChange(Number(e.target.value))}
                      className="w-full px-3 py-2 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-800 dark:text-slate-100"
                    >
                      <option value={6}>6 hours before</option>
                      <option value={12}>12 hours before</option>
                      <option value={24}>24 hours before (Recommended)</option>
                      <option value={48}>48 hours before</option>
                      <option value={72}>72 hours before</option>
                    </select>
                  </div>
                </div>
              ) : (
                <p className="text-xs text-slate-500 dark:text-slate-400">Loading preferences...</p>
              )}
            </Card>
          </div>
        )}
      </div>

      {/* APPLICATION DETAIL, CHRONOLOGICAL TIMELINE, INTERVIEWS & OFFER DRAWER */}
      {selectedApp && (
        <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/50 backdrop-blur-sm">
          <div className="w-full max-w-2xl bg-white dark:bg-slate-900 h-full overflow-y-auto shadow-2xl border-l border-slate-200 dark:border-slate-800 p-6 space-y-6">
            <div className="flex items-start justify-between gap-4 pb-4 border-b border-slate-100 dark:border-slate-800">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">
                    {selectedApp.company_name || 'Partner Company'}
                  </span>
                  <Badge variant={getStatusBadgeVariant(selectedApp.current_status)} size="sm">
                    {formatStatusLabel(selectedApp.current_status)}
                  </Badge>
                </div>
                <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 mt-1">
                  {selectedApp.job_title || `Job #${selectedApp.job_id}`}
                </h2>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  Applied {formatDateTime(selectedApp.created_at)} • Match Snapshot:{' '}
                  {selectedApp.compatibility_score_at_application.toFixed(1)}%
                </p>
              </div>
              <button
                type="button"
                onClick={() => {
                  setSelectedApp(null);
                  setShowWithdrawForm(false);
                }}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800"
                aria-label="Close application details"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Offer Management Section */}
            {selectedApp.offer_details && (
              <div className="p-4 rounded-xl border border-emerald-200 dark:border-emerald-800/80 bg-emerald-50/50 dark:bg-emerald-950/20 space-y-3">
                <div className="flex items-center justify-between gap-2">
                  <h3 className="text-sm font-bold text-emerald-900 dark:text-emerald-200 flex items-center gap-2">
                    <Award className="w-4 h-4" />
                    <span>Offer Management</span>
                  </h3>
                  <Badge variant={getStatusBadgeVariant(selectedApp.offer_details.status)} size="sm">
                    {formatStatusLabel(selectedApp.offer_details.status)}
                  </Badge>
                </div>
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <span className="text-slate-500 dark:text-slate-400 block">Compensation Package</span>
                    <strong className="text-slate-900 dark:text-slate-100">
                      {selectedApp.offer_details.package_lpa
                        ? `${selectedApp.offer_details.package_lpa.toFixed(2)} LPA`
                        : selectedApp.offer_details.salary_range || 'As per offer terms'}
                    </strong>
                  </div>
                  <div>
                    <span className="text-slate-500 dark:text-slate-400 block">Response Deadline</span>
                    <strong className="text-slate-900 dark:text-slate-100">
                      {formatDateTime(selectedApp.offer_details.response_deadline)}
                    </strong>
                  </div>
                </div>
                {selectedApp.offer_details.offer_notes && (
                  <p className="text-xs text-slate-700 dark:text-slate-300 bg-white/70 dark:bg-slate-900/60 p-2.5 rounded-lg border border-emerald-100 dark:border-emerald-900/50">
                    {selectedApp.offer_details.offer_notes}
                  </p>
                )}

                {selectedApp.offer_details.can_respond && (
                  <div className="space-y-2 pt-2 border-t border-emerald-200/70 dark:border-emerald-800/60">
                    <input
                      type="text"
                      value={offerNotes}
                      onChange={(e) => setOfferNotes(e.target.value)}
                      placeholder="Optional response note for recruiter..."
                      className="w-full px-3 py-2 text-xs rounded-lg border border-emerald-200 dark:border-emerald-800 bg-white dark:bg-slate-950 text-slate-800 dark:text-slate-100"
                    />
                    <div className="flex flex-wrap gap-2">
                      <Button
                        size="sm"
                        variant="primary"
                        isLoading={offerActionLoading}
                        onClick={() => handleOfferResponse(selectedApp.id, true)}
                        icon={<CheckCircle2 className="w-3.5 h-3.5" />}
                      >
                        Accept Offer
                      </Button>
                      <Button
                        size="sm"
                        variant="danger"
                        isLoading={offerActionLoading}
                        onClick={() => handleOfferResponse(selectedApp.id, false)}
                        icon={<XCircle className="w-3.5 h-3.5" />}
                      >
                        Decline Offer
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Chronological Recorded Recruitment Timeline */}
            <div className="space-y-3">
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                <History className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                <span>Chronological Recruitment Timeline ({selectedApp.status_history.length})</span>
              </h3>

              {selectedApp.status_history.length === 0 ? (
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  No state transitions recorded yet.
                </p>
              ) : (
                <ol className="relative border-l-2 border-slate-200 dark:border-slate-700 ml-3 space-y-4">
                  {selectedApp.status_history.map((entry) => (
                    <li key={entry.id} className="ml-5">
                      <span className="absolute -left-[9px] w-4 h-4 rounded-full bg-brand-600 border-2 border-white dark:border-slate-900" />
                      <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <Badge variant={getStatusBadgeVariant(entry.to_status)} size="sm">
                              {formatStatusLabel(entry.to_status)}
                            </Badge>
                            <span className="text-[11px] font-medium text-slate-500 dark:text-slate-400">
                              {entry.decision_domain === 'tpo_screening' ? 'TPO Screening' : 'Recruitment Pipeline'}
                            </span>
                          </div>
                          <span className="text-[11px] text-slate-400 dark:text-slate-500">
                            {formatDateTime(entry.created_at)}
                          </span>
                        </div>
                        {entry.from_status && (
                          <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                            Transitioned from <span className="font-semibold">{formatStatusLabel(entry.from_status)}</span>
                          </div>
                        )}
                        {entry.notes && (
                          <p className="text-xs text-slate-700 dark:text-slate-300 mt-1.5">{entry.notes}</p>
                        )}
                      </div>
                    </li>
                  ))}
                </ol>
              )}
            </div>

            {/* Interview Rounds Linked to Application */}
            <div className="space-y-3">
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                <UserCheck className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
                <span>Interview Rounds ({selectedApp.interviews.length})</span>
              </h3>
              {selectedApp.interviews.length === 0 ? (
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  No interviews scheduled for this application yet.
                </p>
              ) : (
                <div className="space-y-3">
                  {selectedApp.interviews.map((iv) => (
                    <div
                      key={iv.id}
                      className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950/60 space-y-2"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-slate-900 dark:text-slate-100">
                            Round {iv.round_number}: {iv.round_title}
                          </span>
                          <Badge variant={getStatusBadgeVariant(iv.status)} size="sm">
                            {formatStatusLabel(iv.status)}
                          </Badge>
                          {iv.is_rescheduled && (
                            <Badge variant="warning" size="sm">
                              RESCHEDULED
                            </Badge>
                          )}
                        </div>
                        {iv.status === 'completed' && (
                          <Badge variant={getStatusBadgeVariant(iv.outcome)} size="sm">
                            Outcome: {formatStatusLabel(iv.outcome)}
                          </Badge>
                        )}
                      </div>

                      <div className="text-xs text-slate-600 dark:text-slate-300 flex flex-wrap gap-4">
                        <span className="inline-flex items-center gap-1">
                          <Clock className="w-3.5 h-3.5 text-slate-400" />
                          {formatDateTime(iv.scheduled_start_time)} ({iv.duration_minutes} mins)
                        </span>
                        {iv.location && (
                          <span className="inline-flex items-center gap-1">
                            <MapPin className="w-3.5 h-3.5 text-slate-400" />
                            {iv.location}
                          </span>
                        )}
                        {iv.interviewer_names && (
                          <span className="inline-flex items-center gap-1">
                            Panel: {iv.interviewer_names}
                          </span>
                        )}
                      </div>

                      {iv.instructions && (
                        <div className="text-xs bg-slate-50 dark:bg-slate-800/70 p-2 rounded-lg text-slate-700 dark:text-slate-300">
                          <strong>Instructions:</strong> {iv.instructions}
                        </div>
                      )}
                      {iv.cancellation_reason && (
                        <div className="text-xs text-amber-700 dark:text-amber-300">
                          {iv.cancellation_reason}
                        </div>
                      )}
                      {iv.meeting_link && iv.status === 'scheduled' && (
                        <div>
                          <a
                            href={iv.meeting_link}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1.5 text-xs font-semibold text-brand-600 dark:text-brand-400 hover:underline"
                          >
                            <ExternalLink className="w-3.5 h-3.5" />
                            Join Interview Meeting Link
                          </a>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Candidate Withdrawal Control (for active non-terminal stages) */}
            {!['rejected', 'withdrawn', 'offer_accepted', 'offer_declined'].includes(selectedApp.current_status) && (
              <div className="pt-4 border-t border-slate-100 dark:border-slate-800">
                {!showWithdrawForm ? (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setShowWithdrawForm(true)}
                  >
                    Withdraw Application
                  </Button>
                ) : (
                  <div className="p-3.5 rounded-xl border border-rose-200 dark:border-rose-800/70 bg-rose-50/40 dark:bg-rose-950/20 space-y-2.5">
                    <div className="text-xs font-bold text-rose-800 dark:text-rose-200">
                      Confirm Application Withdrawal
                    </div>
                    <textarea
                      rows={2}
                      value={withdrawReason}
                      onChange={(e) => setWithdrawReason(e.target.value)}
                      placeholder="Mandatory reason (at least 5 characters)..."
                      className="w-full px-3 py-2 text-xs rounded-lg border border-rose-200 dark:border-rose-800 bg-white dark:bg-slate-950 text-slate-800 dark:text-slate-100"
                    />
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="danger"
                        isLoading={withdrawLoading}
                        onClick={() => handleWithdrawApplication(selectedApp.id)}
                      >
                        Confirm Withdrawal
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => setShowWithdrawForm(false)}>
                        Cancel
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </DashboardLayout>
  );
};

const InterviewCard: React.FC<{
  interview: StudentInterviewTrackingItem;
  onOpenApplication: (applicationId?: number | null) => void;
}> = ({ interview, onOpenApplication }) => {
  return (
    <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/40 dark:bg-slate-900 space-y-2.5">
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">
            {interview.company_name || 'Partner Company'} • Round {interview.round_number}
          </div>
          <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100">
            {interview.round_title}
          </h4>
          {interview.job_title && (
            <div className="text-xs text-slate-600 dark:text-slate-300">{interview.job_title}</div>
          )}
        </div>
        <div className="flex flex-col items-end gap-1">
          <Badge variant={getStatusBadgeVariant(interview.status)} size="sm">
            {formatStatusLabel(interview.status)}
          </Badge>
          {interview.is_rescheduled && (
            <Badge variant="warning" size="sm">
              RESCHEDULED
            </Badge>
          )}
          {interview.status === 'completed' && (
            <Badge variant={getStatusBadgeVariant(interview.outcome)} size="sm">
              {formatStatusLabel(interview.outcome)}
            </Badge>
          )}
        </div>
      </div>

      <div className="text-xs text-slate-600 dark:text-slate-300 space-y-1">
        <div className="flex items-center gap-1.5">
          <Clock className="w-3.5 h-3.5 text-slate-400 shrink-0" />
          <span>
            {formatDateTime(interview.scheduled_start_time)} ({interview.duration_minutes} mins •{' '}
            {interview.interview_mode.replace('_', ' ')})
          </span>
        </div>
        {interview.location && (
          <div className="flex items-center gap-1.5">
            <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            <span>{interview.location}</span>
          </div>
        )}
        {interview.interviewer_names && (
          <div className="flex items-center gap-1.5">
            <Filter className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            <span>Panel: {interview.interviewer_names}</span>
          </div>
        )}
      </div>

      {interview.instructions && (
        <div className="text-xs bg-white dark:bg-slate-800/70 p-2.5 rounded-lg border border-slate-100 dark:border-slate-800 text-slate-700 dark:text-slate-300">
          <strong>Instructions:</strong> {interview.instructions}
        </div>
      )}

      {interview.cancellation_reason && (
        <div className="text-xs text-amber-700 dark:text-amber-300 bg-amber-50/70 dark:bg-amber-950/30 p-2 rounded-lg">
          {interview.cancellation_reason}
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-100 dark:border-slate-800">
        {interview.meeting_link && interview.status === 'scheduled' ? (
          <a
            href={interview.meeting_link}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-brand-600 dark:text-brand-400 hover:underline"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            Join Meeting
          </a>
        ) : (
          <span className="text-[11px] text-slate-400 dark:text-slate-500">
            Stage: {formatStatusLabel(interview.application_status)}
          </span>
        )}
        <button
          type="button"
          onClick={() => onOpenApplication(interview.application_id)}
          className="text-xs font-semibold text-slate-700 dark:text-slate-200 hover:text-brand-600 dark:hover:text-brand-400"
        >
          Open Timeline →
        </button>
      </div>
    </div>
  );
};

