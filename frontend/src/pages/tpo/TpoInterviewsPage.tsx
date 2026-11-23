import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { DashboardLayout } from '../../components/layout/DashboardLayout';
import { Card } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { interviewApi } from '../../services/api';
import {
  InterviewPortalItem,
  InterviewCalendarResponse,
  CalendarEventItem,
} from '../../types';
import {
  Calendar as CalendarIcon,
  List,
  Search,
  RefreshCw,
  Video,
  MapPin,
  Clock,
  User,
  GraduationCap,
  Building,
  CheckCircle2,
  XCircle,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  ShieldCheck,
  CalendarDays,
  X,
  Eye,
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

export const TpoInterviewsPage: React.FC = () => {
  // View mode
  const [viewMode, setViewMode] = useState<'calendar' | 'table'>('calendar');

  // Calendar month state
  const [currentDate, setCurrentDate] = useState<Date>(() => new Date());

  // Data states
  const [interviews, setInterviews] = useState<InterviewPortalItem[]>([]);
  const [totalInterviews, setTotalInterviews] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [calendarData, setCalendarData] = useState<InterviewCalendarResponse | null>(null);

  // Filters
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [outcomeFilter, setOutcomeFilter] = useState<string>('all');

  // Loading & error states
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Logistic Detail Modal
  const [selectedInterview, setSelectedInterview] = useState<InterviewPortalItem | null>(null);

  // Selected calendar day detail popup
  const [selectedDayEvents, setSelectedDayEvents] = useState<{ date: string; events: CalendarEventItem[] } | null>(null);

  // Month range
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

  // Load monitoring interviews & calendar
  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const params: any = {
        page: currentPage,
        limit: 15,
      };
      if (statusFilter !== 'all') params.status = statusFilter;
      if (outcomeFilter !== 'all') params.outcome = outcomeFilter;
      if (searchTerm.trim()) params.search = searchTerm.trim();

      const listRes = await interviewApi.listTpoMonitoring(params);
      setInterviews(listRes.items);
      setTotalInterviews(listRes.total);
      setTotalPages(listRes.pages || 1);

      const calRes = await interviewApi.getCalendar({
        start_date: monthRange.startStr,
        end_date: monthRange.endStr,
        status: statusFilter !== 'all' ? statusFilter : undefined,
      });
      setCalendarData(calRes);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.message || err.message || 'Failed to load institutional interviews.');
    } finally {
      setIsLoading(false);
    }
  }, [currentPage, statusFilter, outcomeFilter, searchTerm, monthRange]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

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

  // Build calendar matrix
  const calendarDays = useMemo(() => {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();

    const firstDayIndex = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const daysInPrevMonth = new Date(year, month, 0).getDate();

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
      role="tpo"
      title="Campus Interview Schedules"
      subtitle="Campus-wide interview schedules, recruitment pipeline progress, venue coordination, and attendance tracking."
    >
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <CalendarIcon className="w-7 h-7 text-brand-600 dark:text-brand-400" />
              Institutional Interview Supervision
            </h1>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
              Campus-wide interview schedules, recruitment pipeline progress, venue coordination, and attendance tracking.
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
          </div>
        </div>

        {/* Confidentiality Notice */}
        <div className="p-3 bg-brand-50/70 dark:bg-brand-950/40 border border-brand-200/80 dark:border-brand-800/80 rounded-xl text-brand-800 dark:text-brand-200 text-xs flex items-center gap-2.5">
          <ShieldCheck className="w-4 h-4 text-brand-600 dark:text-brand-400 flex-shrink-0" />
          <span>
            <strong>Institutional Privacy Safeguard Active:</strong> Internal recruiter evaluation scorecards and confidential interview notes are strictly redacted in this institutional monitoring view.
          </span>
        </div>

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
                  Campus Total
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

        {/* Filter & View Controls */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200/80 dark:border-slate-800 shadow-sm">
          <div className="flex flex-wrap items-center gap-3 flex-1">
            <div className="relative min-w-[220px] flex-1 max-w-sm">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search candidate, roll #, interviewer, company..."
                className="w-full pl-9 pr-3 py-1.5 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>

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
              Campus Roster
            </button>
          </div>
        </div>

        {/* MAIN VIEW: Calendar vs Table */}
        {viewMode === 'calendar' ? (
          <Card className="bg-white dark:bg-slate-900 border-slate-200/80 dark:border-slate-800 shadow-sm overflow-hidden">
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
                >
                  <ChevronLeft className="w-5 h-5" />
                </button>
                <button
                  onClick={nextMonth}
                  className="p-1.5 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-800 rounded-lg transition-colors"
                >
                  <ChevronRight className="w-5 h-5" />
                </button>
              </div>
            </div>

            <div className="grid grid-cols-7 border-b border-slate-200 dark:border-slate-800 bg-slate-100/50 dark:bg-slate-800/50 text-center py-2 text-xs font-semibold text-slate-500 dark:text-slate-400">
              <div>Sun</div>
              <div>Mon</div>
              <div>Tue</div>
              <div>Wed</div>
              <div>Thu</div>
              <div>Fri</div>
              <div>Sat</div>
            </div>

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

                  <div className="space-y-1 flex-1 overflow-hidden">
                    {day.events.slice(0, 3).map((ev) => (
                      <div
                        key={ev.id}
                        onClick={() => {
                          const matched = interviews.find((i) => i.id === ev.id);
                          if (matched) setSelectedInterview(matched);
                        }}
                        className={`text-[11px] p-1.5 rounded-md cursor-pointer border transition-all truncate flex items-center justify-between gap-1 ${
                          ev.status === 'cancelled'
                            ? 'bg-slate-100 dark:bg-slate-800 text-slate-400 border-slate-200 line-through'
                            : ev.outcome === 'passed'
                            ? 'bg-emerald-50 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-200 border-emerald-200/80 hover:bg-emerald-100'
                            : 'bg-brand-50 dark:bg-brand-950/60 text-brand-800 dark:text-brand-200 border-brand-200/80 hover:bg-brand-100'
                        }`}
                        title={`${ev.company_name} - ${ev.round_title} (${ev.student_name})`}
                      >
                        <div className="truncate flex items-center gap-1">
                          {ev.interview_mode === 'virtual' ? (
                            <Video className="w-3 h-3 flex-shrink-0 text-brand-600" />
                          ) : (
                            <MapPin className="w-3 h-3 flex-shrink-0 text-amber-600" />
                          )}
                          <span className="font-semibold">{ev.company_name}</span>: {ev.student_name.split(' ')[0]}
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
                    <th className="px-4 py-3">Company & Job</th>
                    <th className="px-4 py-3">Round & Mode</th>
                    <th className="px-4 py-3">Scheduled Time</th>
                    <th className="px-4 py-3">Drive Context</th>
                    <th className="px-4 py-3">Status & Outcome</th>
                    <th className="px-4 py-3 text-right">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-800 text-slate-700 dark:text-slate-300">
                  {interviews.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="px-4 py-8 text-center text-slate-500 dark:text-slate-400">
                        {isLoading ? 'Loading campus interviews...' : 'No interviews match the specified criteria.'}
                      </td>
                    </tr>
                  ) : (
                    interviews.map((iv) => (
                      <tr key={iv.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition-colors">
                        <td className="px-4 py-3">
                          <div className="font-semibold text-slate-900 dark:text-white">{iv.student_name}</div>
                          <div className="text-xs text-slate-500 dark:text-slate-400">
                            {iv.roll_number} • {iv.department} (CGPA: {iv.cgpa.toFixed(2)})
                          </div>
                        </td>

                        <td className="px-4 py-3">
                          <div className="font-semibold text-slate-900 dark:text-white">{iv.company_name}</div>
                          <div className="text-xs text-slate-500 dark:text-slate-400">{iv.job_title}</div>
                        </td>

                        <td className="px-4 py-3">
                          <div className="font-medium text-slate-900 dark:text-white">
                            R{iv.round_number}: {iv.round_title}
                          </div>
                          <div className="flex items-center gap-1.5 text-xs text-slate-500 mt-0.5">
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
                          <div className="text-xs text-slate-500">
                            {iv.duration_minutes} min
                            {iv.is_rescheduled && (
                              <span className="ml-1 text-amber-600 dark:text-amber-400 font-medium">(Rescheduled)</span>
                            )}
                          </div>
                        </td>

                        <td className="px-4 py-3 text-xs text-slate-600 dark:text-slate-400">
                          {iv.drive_name || 'Individual Campus Placement'}
                        </td>

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

                        <td className="px-4 py-3 text-right">
                          <Button
                            variant="outline"
                            size="sm"
                            className="text-xs py-1 px-2.5"
                            icon={<Eye className="w-3.5 h-3.5" />}
                            onClick={() => setSelectedInterview(iv)}
                          >
                            Details
                          </Button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {totalPages > 1 && (
              <div className="p-4 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between text-xs text-slate-500">
                <span>
                  Showing page {currentPage} of {totalPages} ({totalInterviews} total campus interviews)
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

        {/* LOGISTIC DETAIL MODAL */}
        {selectedInterview && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
              <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
                <div className="flex items-center gap-2">
                  <Building className="w-5 h-5 text-brand-600" />
                  <div>
                    <h3 className="text-base font-bold text-slate-900 dark:text-white">
                      {selectedInterview.company_name} • Round {selectedInterview.round_number}
                    </h3>
                    <p className="text-xs text-slate-500">{selectedInterview.round_title}</p>
                  </div>
                </div>
                <button
                  onClick={() => setSelectedInterview(null)}
                  className="p-1 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-slate-500"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="space-y-3 text-xs">
                <div className="p-3 bg-slate-50 dark:bg-slate-800/60 rounded-xl space-y-1">
                  <div className="font-semibold text-slate-900 dark:text-white text-sm">
                    {selectedInterview.student_name}
                  </div>
                  <div className="text-slate-500">
                    Roll No: {selectedInterview.roll_number} • Dept: {selectedInterview.department} • CGPA:{' '}
                    {selectedInterview.cgpa.toFixed(2)}
                  </div>
                  <div className="text-slate-500">Email: {selectedInterview.student_email}</div>
                </div>

                <div className="grid grid-cols-2 gap-3 pt-1">
                  <div>
                    <span className="font-semibold text-slate-700 dark:text-slate-300 block">Job Role:</span>
                    <span className="text-slate-900 dark:text-white">{selectedInterview.job_title}</span>
                  </div>
                  <div>
                    <span className="font-semibold text-slate-700 dark:text-slate-300 block">Placement Drive:</span>
                    <span className="text-slate-900 dark:text-white">
                      {selectedInterview.drive_name || 'Individual Placement'}
                    </span>
                  </div>
                  <div>
                    <span className="font-semibold text-slate-700 dark:text-slate-300 block">Mode:</span>
                    <span className="text-slate-900 dark:text-white capitalize">
                      {selectedInterview.interview_mode.replace('_', ' ')}
                    </span>
                  </div>
                  <div>
                    <span className="font-semibold text-slate-700 dark:text-slate-300 block">Scheduled Time:</span>
                    <span className="text-slate-900 dark:text-white">
                      {new Date(selectedInterview.scheduled_start_time).toLocaleString()} ({selectedInterview.duration_minutes} min)
                    </span>
                  </div>
                </div>

                {selectedInterview.meeting_link && (
                  <div className="pt-2">
                    <span className="font-semibold text-slate-700 dark:text-slate-300 block mb-0.5">Meeting URL:</span>
                    <a
                      href={selectedInterview.meeting_link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-brand-600 hover:underline flex items-center gap-1 font-medium break-all"
                    >
                      <ExternalLink className="w-3.5 h-3.5 flex-shrink-0" />
                      {selectedInterview.meeting_link}
                    </a>
                  </div>
                )}

                {selectedInterview.location && (
                  <div className="pt-2">
                    <span className="font-semibold text-slate-700 dark:text-slate-300 block mb-0.5">Venue Location:</span>
                    <span className="text-slate-900 dark:text-white">{selectedInterview.location}</span>
                  </div>
                )}

                {selectedInterview.interviewer_names && (
                  <div className="pt-2">
                    <span className="font-semibold text-slate-700 dark:text-slate-300 block mb-0.5">Panel:</span>
                    <span className="text-slate-900 dark:text-white">{selectedInterview.interviewer_names}</span>
                  </div>
                )}

                {selectedInterview.instructions && (
                  <div className="p-3 bg-slate-50 dark:bg-slate-800/60 rounded-xl mt-2 border border-slate-200 dark:border-slate-700">
                    <span className="font-semibold text-slate-700 dark:text-slate-300 block mb-0.5">Instructions:</span>
                    <span className="text-slate-600 dark:text-slate-300">{selectedInterview.instructions}</span>
                  </div>
                )}

                <div className="flex items-center gap-2 pt-2 border-t border-slate-200 dark:border-slate-800">
                  <span className="font-semibold text-slate-700 dark:text-slate-300">Status:</span>
                  <Badge variant={STATUS_VARIANTS[selectedInterview.status] || 'neutral'} size="sm">
                    {selectedInterview.status}
                  </Badge>
                  <span className="font-semibold text-slate-700 dark:text-slate-300 ml-2">Outcome:</span>
                  <Badge variant={OUTCOME_VARIANTS[selectedInterview.outcome] || 'neutral'} size="sm">
                    {selectedInterview.outcome}
                  </Badge>
                </div>
              </div>

              <div className="flex justify-end pt-3 border-t border-slate-200 dark:border-slate-800">
                <Button variant="outline" size="sm" onClick={() => setSelectedInterview(null)}>
                  Close
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* DAY EVENTS POPUP MODAL */}
        {selectedDayEvents && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
              <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
                <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                  <CalendarIcon className="w-5 h-5 text-brand-600" />
                  Campus Interviews on {new Date(selectedDayEvents.date).toLocaleDateString()}
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
                    className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 space-y-1 text-xs"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-slate-900 dark:text-white">
                        {ev.company_name} • {ev.student_name}
                      </span>
                      <Badge variant={STATUS_VARIANTS[ev.status] || 'neutral'} size="sm">
                        {ev.status}
                      </Badge>
                    </div>
                    <div className="text-slate-600 dark:text-slate-400">
                      R{ev.round_number}: {ev.round_title} ({ev.duration_minutes} min)
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
