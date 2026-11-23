import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  AlertCircle,
  Archive,
  ArrowDownToLine,
  BarChart3,
  Building2,
  Calendar,
  CheckCircle2,
  Clock,
  Download,
  Eye,
  FileCheck,
  FileSpreadsheet,
  FileText,
  Filter,
  GraduationCap,
  Layers,
  Play,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  Trash2,
  TrendingUp,
  UserCheck,
  UserX,
  Users,
} from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { DashboardLayout } from '../../components/layout/DashboardLayout';
import { Card, CardHeader } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { useTheme } from '../../context/ThemeContext';
import { reportApi } from '../../services/api';
import {
  PlacementReportResponse,
  ReportDataPayload,
  ReportFilterParams,
  ReportFormat,
  ReportFormOptionsResponse,
  ReportGenerateRequest,
  ReportStatus,
  ReportType,
} from '../../types';

const REPORT_TYPE_CONFIG: Record<
  ReportType,
  { label: string; description: string; icon: typeof FileText }
> = {
  overall_institutional: {
    label: 'Overall Institutional Placement Report',
    description: 'Comprehensive macro analysis of institutional placements, CTC statistics, and conversion benchmarks.',
    icon: Building2,
  },
  academic_year_wise: {
    label: 'Academic Year-Wise Placement Report',
    description: 'Aggregated placement ratios and recruiting outcomes segmented across academic calendar years.',
    icon: Calendar,
  },
  department_wise: {
    label: 'Department-Wise Placement Report',
    description: 'Comparative performance, eligible student metrics, and package distribution by academic department.',
    icon: Layers,
  },
  graduation_batch: {
    label: 'Graduation Batch Report',
    description: 'Batch-specific placement tracking, readiness distributions, and historical cohort comparisons.',
    icon: GraduationCap,
  },
  company_wise: {
    label: 'Company-Wise Recruitment Report',
    description: 'Corporate hiring profiles, offers released, acceptance rates, and campus participation analytics.',
    icon: TrendingUp,
  },
  placement_drive: {
    label: 'Placement Drive Report',
    description: 'Drive operational report with stage attendance, scheduled activities, and drive offer outcomes.',
    icon: Play,
  },
  student_placement_status: {
    label: 'Student-Wise Placement Status Report',
    description: 'Granular student ledger detailing roll numbers, departments, CGPA, application counts, and final status.',
    icon: UserCheck,
  },
  salary_package_analysis: {
    label: 'Salary & Package Analysis Report',
    description: 'Statistical CTC breakdown, highest/median/average compensation, and salary band distributions.',
    icon: BarChart3,
  },
  unplaced_students: {
    label: 'Unplaced Student Focus Report',
    description: 'Dedicated intervention list of eligible unplaced candidates and active pipeline participants for priority outreach.',
    icon: UserX,
  },
  offer_acceptance: {
    label: 'Offer Acceptance & Conversion Report',
    description: 'Offer release versus acceptance tracking, multi-offer distributions, and corporate offer turnaround.',
    icon: FileCheck,
  },
};

const FORMAT_CONFIG: Record<
  ReportFormat,
  { label: string; extension: string; mime: string; icon: typeof FileText; badgeClass: string }
> = {
  pdf: {
    label: 'PDF Document',
    extension: 'pdf',
    mime: 'application/pdf',
    icon: FileText,
    badgeClass: 'bg-rose-100 text-rose-800 dark:bg-rose-900/30 dark:text-rose-300 border-rose-200 dark:border-rose-800',
  },
  xlsx: {
    label: 'Excel Workbook (.xlsx)',
    extension: 'xlsx',
    mime: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    icon: FileSpreadsheet,
    badgeClass: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800',
  },
  csv: {
    label: 'Standard CSV',
    extension: 'csv',
    mime: 'text/csv; charset=utf-8',
    icon: ArrowDownToLine,
    badgeClass: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300 border-blue-200 dark:border-blue-800',
  },
  json: {
    label: 'JSON Payload',
    extension: 'json',
    mime: 'application/json',
    icon: FileText,
    badgeClass: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300 border-purple-200 dark:border-purple-800',
  },
};

const STATUS_BADGE: Record<ReportStatus, { label: string; variant: 'success' | 'warning' | 'danger' | 'neutral' }> = {
  completed: { label: 'Ready', variant: 'success' },
  processing: { label: 'Processing', variant: 'warning' },
  pending: { label: 'Queued', variant: 'neutral' },
  failed: { label: 'Failed', variant: 'danger' },
};

const triggerBlobDownload = (blob: Blob, filename: string) => {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  setTimeout(() => {
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  }, 1000);
};

const formatFileSize = (bytes?: number | null): string => {
  if (!bytes || bytes <= 0) return '0 KB';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
};

export const TpoReportsPage: React.FC = () => {
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === 'dark';

  // Navigation tab
  const [activeTab, setActiveTab] = useState<'generator' | 'history'>('generator');

  // Form options state
  const [options, setOptions] = useState<ReportFormOptionsResponse>({
    academic_years: [],
    graduation_batches: [],
    departments: [],
    companies: [],
    drives: [],
    application_statuses: [],
  });
  const [loadingOptions, setLoadingOptions] = useState(false);

  // Configuration form state
  const [selectedType, setSelectedType] = useState<ReportType>('overall_institutional');
  const [selectedFormat, setSelectedFormat] = useState<ReportFormat>('pdf');
  const [customTitle, setCustomTitle] = useState('');
  const [filters, setFilters] = useState<ReportFilterParams>({});

  // Preview state
  const [previewData, setPreviewData] = useState<ReportDataPayload | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);

  // Generation & Async state
  const [generating, setGenerating] = useState(false);
  const [actionMessage, setActionMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // History state
  const [historyReports, setHistoryReports] = useState<PlacementReportResponse[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [historyFilterType, setHistoryFilterType] = useState<string>('all');
  const [historySearch, setHistorySearch] = useState('');

  // Table pagination & search for preview
  const [previewSearch, setPreviewSearch] = useState('');
  const [previewPage, setPreviewPage] = useState(1);
  const rowsPerPage = 10;

  // Load Form Options
  const loadOptions = useCallback(async () => {
    try {
      setLoadingOptions(true);
      const res = await reportApi.getFormOptions();
      setOptions(res);
    } catch (err: unknown) {
      console.error('Failed to load report form options:', err);
    } finally {
      setLoadingOptions(false);
    }
  }, []);

  // Load Report History
  const loadHistory = useCallback(async () => {
    try {
      setLoadingHistory(true);
      const reports = await reportApi.listReports();
      setHistoryReports(reports);
    } catch (err: unknown) {
      console.error('Failed to load report history:', err);
    } finally {
      setLoadingHistory(false);
    }
  }, []);

  useEffect(() => {
    loadOptions();
    loadHistory();
  }, [loadOptions, loadHistory]);

  // Handle Live Preview
  const handlePreview = async () => {
    try {
      setLoadingPreview(true);
      setPreviewError(null);
      setActionMessage(null);
      const req: ReportGenerateRequest = {
        report_type: selectedType,
        file_format: selectedFormat,
        title: customTitle.trim() || undefined,
        filters,
      };
      const result = await reportApi.previewReport(req);
      setPreviewData(result);
      setPreviewPage(1);
    } catch (err: unknown) {
      const msg =
        (err as any)?.response?.data?.detail?.message ||
        (err as any)?.response?.data?.message ||
        (err as any)?.response?.data?.detail ||
        (err instanceof Error ? err.message : 'Failed to compile report preview.');
      setPreviewError(typeof msg === 'string' ? msg : JSON.stringify(msg));
      setPreviewData(null);
    } finally {
      setLoadingPreview(false);
    }
  };

  // Automatically update live preview when selectedType changes
  useEffect(() => {
    handlePreview();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedType]);

  // Handle Synchronous Generate & Direct Download
  const handleGenerateAndDownload = async () => {
    try {
      setGenerating(true);
      setActionMessage(null);
      const req: ReportGenerateRequest = {
        report_type: selectedType,
        file_format: selectedFormat,
        title: customTitle.trim() || undefined,
        filters,
      };

      const blob = (await reportApi.generateReport(req, true)) as Blob;
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
      const filename = `${selectedType}_report_${timestamp}.${selectedFormat}`;
      triggerBlobDownload(blob, filename);

      setActionMessage({
        type: 'success',
        text: `Report "${filename}" generated and downloaded successfully. Record saved to archive.`,
      });
      loadHistory();
    } catch (err: unknown) {
      let msg = 'Report generation failed.';
      if ((err as any)?.response?.data instanceof Blob) {
        try {
          const text = await (err as any).response.data.text();
          const parsed = JSON.parse(text);
          msg = parsed?.detail?.message || parsed?.detail || parsed?.message || text;
        } catch {
          // ignore parsing error
        }
      } else {
        msg =
          (err as any)?.response?.data?.detail?.message ||
          (err as any)?.response?.data?.message ||
          (err as any)?.response?.data?.detail ||
          (err instanceof Error ? err.message : 'Report generation failed.');
      }
      setActionMessage({ type: 'error', text: typeof msg === 'string' ? msg : JSON.stringify(msg) });
    } finally {
      setGenerating(false);
    }
  };

  // Handle Asynchronous Queue
  const handleEnqueueAsync = async () => {
    try {
      setGenerating(true);
      setActionMessage(null);
      const req: ReportGenerateRequest = {
        report_type: selectedType,
        file_format: selectedFormat,
        title: customTitle.trim() || undefined,
        filters,
      };

      const queued = await reportApi.generateAsyncReport(req);
      setActionMessage({
        type: 'success',
        text: `Report enqueued in background (Job #${queued.id}). Check the Report Archive tab as processing finishes.`,
      });
      loadHistory();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to enqueue background report.';
      setActionMessage({ type: 'error', text: msg });
    } finally {
      setGenerating(false);
    }
  };

  // Download Historical File
  const handleDownloadHistorical = async (report: PlacementReportResponse) => {
    try {
      const blob = await reportApi.downloadReportFile(report.id);
      const ext = report.file_format || 'pdf';
      const filename = report.title ? `${report.title.toLowerCase().replace(/\s+/g, '_')}.${ext}` : `report_${report.id}.${ext}`;
      triggerBlobDownload(blob, filename);
    } catch (err: unknown) {
      console.error('Failed to download report file:', err);
      alert('Could not download file. It may still be processing or has expired.');
    }
  };

  // Delete Historical Record
  const handleDeleteReport = async (reportId: number) => {
    if (!window.confirm(`Are you sure you want to delete Report #${reportId}? This will remove the stored file.`)) return;
    try {
      await reportApi.deleteReport(reportId);
      setHistoryReports((prev) => prev.filter((r) => r.id !== reportId));
    } catch (err: unknown) {
      console.error('Failed to delete report:', err);
      alert('Failed to delete report record.');
    }
  };

  // Extract raw rows supporting both table_rows (backend standard) and rows
  const rawRows = useMemo(() => {
    return previewData?.table_rows || previewData?.rows || [];
  }, [previewData]);

  // Filtered Preview Rows
  const filteredRows = useMemo(() => {
    if (!rawRows || rawRows.length === 0) return [];
    if (!previewSearch.trim()) return rawRows;
    const term = previewSearch.toLowerCase();
    return rawRows.filter((row) =>
      Object.values(row).some((val) => String(val ?? '').toLowerCase().includes(term))
    );
  }, [rawRows, previewSearch]);

  const totalPages = Math.ceil(filteredRows.length / rowsPerPage) || 1;
  const paginatedRows = useMemo(() => {
    const start = (previewPage - 1) * rowsPerPage;
    return filteredRows.slice(start, start + rowsPerPage);
  }, [filteredRows, previewPage]);

  // Dynamic columns from preview rows
  const previewColumns = useMemo(() => {
    if (!rawRows || rawRows.length === 0) return [];
    return Object.keys(rawRows[0]);
  }, [rawRows]);

  // Map column keys to human-readable table_headers if supplied by backend
  const colHeaderMap = useMemo(() => {
    const map: Record<string, string> = {};
    if (previewData?.table_headers && previewColumns.length === previewData.table_headers.length) {
      previewColumns.forEach((col, idx) => {
        map[col] = previewData.table_headers![idx];
      });
    }
    return map;
  }, [previewData, previewColumns]);

  // Filtered History
  const filteredHistory = useMemo(() => {
    return historyReports.filter((item) => {
      const matchType = historyFilterType === 'all' || item.report_type === historyFilterType;
      const matchSearch =
        !historySearch.trim() ||
        item.title.toLowerCase().includes(historySearch.toLowerCase()) ||
        item.report_type.toLowerCase().includes(historySearch.toLowerCase());
      return matchType && matchSearch;
    });
  }, [historyReports, historyFilterType, historySearch]);

  const CurrentTypeIcon = REPORT_TYPE_CONFIG[selectedType].icon;

  return (
    <DashboardLayout
      role="tpo"
      title="Placement Reports"
      subtitle="Automated Institutional Placement Report Generator with PDF, Excel, and CSV multi-format exports"
    >
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-neutral-200 dark:border-neutral-800 pb-5">
          <div>
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-brand-50 text-brand-600 dark:bg-brand-950/50 dark:text-brand-400 border border-brand-200 dark:border-brand-800">
                <FileSpreadsheet className="w-6 h-6" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50 tracking-tight">
                  Placement Report Generator
                </h1>
                <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-0.5">
                  Automated institutional compliance, accreditation exports, and multi-format analytics (PDF, Excel, CSV)
                </p>
              </div>
            </div>
          </div>

          {/* Tab Switcher */}
          <div className="flex items-center bg-neutral-100 dark:bg-neutral-800/80 p-1 rounded-xl border border-neutral-200 dark:border-neutral-700">
            <button
              onClick={() => setActiveTab('generator')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === 'generator'
                  ? 'bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white shadow-sm'
                  : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white'
              }`}
            >
              <Sparkles className="w-4 h-4" />
              Generator & Preview
            </button>
            <button
              onClick={() => setActiveTab('history')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === 'history'
                  ? 'bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white shadow-sm'
                  : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white'
              }`}
            >
              <Archive className="w-4 h-4" />
              Report Archive
              {historyReports.length > 0 && (
                <span className="ml-1 px-1.5 py-0.5 text-xs font-semibold rounded-full bg-brand-100 text-brand-700 dark:bg-brand-900 dark:text-brand-300">
                  {historyReports.length}
                </span>
              )}
            </button>
          </div>
        </div>

        {/* Global Action Banner */}
        {actionMessage && (
          <div
            className={`p-4 rounded-xl flex items-start gap-3 border ${
              actionMessage.type === 'success'
                ? 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800'
                : 'bg-rose-50 dark:bg-rose-950/40 text-rose-800 dark:text-rose-300 border-rose-200 dark:border-rose-800'
            }`}
          >
            {actionMessage.type === 'success' ? (
              <CheckCircle2 className="w-5 h-5 flex-shrink-0 mt-0.5 text-emerald-600 dark:text-emerald-400" />
            ) : (
              <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5 text-rose-600 dark:text-rose-400" />
            )}
            <div className="flex-1 text-sm font-medium">{actionMessage.text}</div>
            <button
              onClick={() => setActionMessage(null)}
              className="text-xs opacity-70 hover:opacity-100 uppercase font-semibold"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* TAB 1: GENERATOR & PREVIEW */}
        {activeTab === 'generator' && (
          <div className="space-y-6">
            {/* Top Config Card */}
            <Card>
              <CardHeader
                title="Report Configuration & Scope"
                subtitle="Select from 10 official institutional report types and customize multi-dimensional filters"
              />
              <div className="p-6 space-y-6">
                {/* 1. Report Type Selector Grid */}
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-neutral-500 dark:text-neutral-400 mb-3">
                    1. Select Official Report Type
                  </label>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
                    {(Object.keys(REPORT_TYPE_CONFIG) as ReportType[]).map((typeKey) => {
                      const cfg = REPORT_TYPE_CONFIG[typeKey];
                      const IconComp = cfg.icon;
                      const isSelected = selectedType === typeKey;
                      return (
                        <button
                          key={typeKey}
                          type="button"
                          onClick={() => {
                            setSelectedType(typeKey);
                          }}
                          className={`flex flex-col text-left p-3.5 rounded-xl border transition-all ${
                            isSelected
                              ? 'border-brand-500 bg-brand-50/70 dark:bg-brand-950/40 shadow-sm ring-2 ring-brand-500/20'
                              : 'border-neutral-200 dark:border-neutral-800 hover:border-neutral-300 dark:hover:border-neutral-700 bg-white dark:bg-neutral-800/50'
                          }`}
                        >
                          <div className="flex items-center justify-between w-full mb-2">
                            <div
                              className={`p-2 rounded-lg ${
                                isSelected
                                  ? 'bg-brand-500 text-white'
                                  : 'bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400'
                              }`}
                            >
                              <IconComp className="w-4 h-4" />
                            </div>
                            {isSelected && (
                              <span className="w-2 h-2 rounded-full bg-brand-500 animate-pulse" />
                            )}
                          </div>
                          <span className="text-xs font-semibold text-neutral-900 dark:text-neutral-100 line-clamp-1">
                            {cfg.label}
                          </span>
                          <span className="text-[11px] text-neutral-500 dark:text-neutral-400 line-clamp-2 mt-1">
                            {cfg.description}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* 2. Format Selection & Custom Title */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-2 border-t border-neutral-100 dark:border-neutral-800">
                  <div className="md:col-span-1">
                    <label className="block text-xs font-semibold uppercase tracking-wider text-neutral-500 dark:text-neutral-400 mb-2">
                      2. Export Document Format
                    </label>
                    <div className="grid grid-cols-3 gap-2">
                      {(['pdf', 'xlsx', 'csv'] as ReportFormat[]).map((fmt) => {
                        const fmtCfg = FORMAT_CONFIG[fmt];
                        const FmtIcon = fmtCfg.icon;
                        const isSelected = selectedFormat === fmt;
                        return (
                          <button
                            key={fmt}
                            type="button"
                            onClick={() => setSelectedFormat(fmt)}
                            className={`flex flex-col items-center justify-center p-3 rounded-xl border text-center transition-all ${
                              isSelected
                                ? 'border-brand-500 bg-brand-50/70 dark:bg-brand-950/40 text-brand-700 dark:text-brand-300 font-semibold ring-2 ring-brand-500/20'
                                : 'border-neutral-200 dark:border-neutral-800 hover:border-neutral-300 dark:hover:border-neutral-700 text-neutral-700 dark:text-neutral-300'
                            }`}
                          >
                            <FmtIcon className="w-5 h-5 mb-1" />
                            <span className="text-xs uppercase font-bold">{fmt}</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  <div className="md:col-span-2">
                    <label className="block text-xs font-semibold uppercase tracking-wider text-neutral-500 dark:text-neutral-400 mb-2">
                      Custom Report Title (Optional)
                    </label>
                    <input
                      type="text"
                      placeholder={`e.g. ${REPORT_TYPE_CONFIG[selectedType].label} - Semester 8 Placement Drive`}
                      value={customTitle}
                      onChange={(e) => setCustomTitle(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
                    />
                    <p className="text-[11px] text-neutral-500 dark:text-neutral-400 mt-1">
                      Leaves blank to auto-generate institutional title with timestamp.
                    </p>
                  </div>
                </div>

                {/* 3. Filter Controls */}
                <div className="pt-2 border-t border-neutral-100 dark:border-neutral-800">
                  <div className="flex items-center justify-between mb-3">
                    <label className="text-xs font-semibold uppercase tracking-wider text-neutral-500 dark:text-neutral-400 flex items-center gap-2">
                      <Filter className="w-3.5 h-3.5" />
                      3. Granular Cohort & Placement Filters
                    </label>
                    <button
                      type="button"
                      onClick={() => setFilters({})}
                      className="text-xs text-brand-600 dark:text-brand-400 hover:underline"
                    >
                      Clear All Filters
                    </button>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    {/* Academic Year */}
                    <div>
                      <label className="block text-xs text-neutral-600 dark:text-neutral-400 mb-1">
                        Academic Year
                      </label>
                      <select
                        value={filters.academic_year || ''}
                        onChange={(e) => setFilters((prev) => ({ ...prev, academic_year: e.target.value || undefined }))}
                        className="w-full px-3 py-2 rounded-xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 text-sm focus:outline-none focus:border-brand-500"
                      >
                        <option value="">All Academic Years</option>
                        {options.academic_years.map((yr) => (
                          <option key={yr} value={yr}>
                            {yr}
                          </option>
                        ))}
                      </select>
                    </div>

                    {/* Graduation Batch */}
                    <div>
                      <label className="block text-xs text-neutral-600 dark:text-neutral-400 mb-1">
                        Graduation Batch
                      </label>
                      <select
                        value={filters.graduation_batch || filters.graduation_year || ''}
                        onChange={(e) => {
                          const val = e.target.value ? Number(e.target.value) : undefined;
                          setFilters((prev) => ({
                            ...prev,
                            graduation_batch: val,
                            graduation_year: val,
                          }));
                        }}
                        className="w-full px-3 py-2 rounded-xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 text-sm focus:outline-none focus:border-brand-500"
                      >
                        <option value="">All Batches</option>
                        {options.graduation_batches.map((batch) => (
                          <option key={batch} value={batch}>
                            Batch of {batch}
                          </option>
                        ))}
                      </select>
                    </div>

                    {/* Department */}
                    <div>
                      <label className="block text-xs text-neutral-600 dark:text-neutral-400 mb-1">
                        Academic Department
                      </label>
                      <select
                        value={filters.department_id || ''}
                        onChange={(e) =>
                          setFilters((prev) => ({
                            ...prev,
                            department_id: e.target.value ? Number(e.target.value) : undefined,
                          }))
                        }
                        className="w-full px-3 py-2 rounded-xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 text-sm focus:outline-none focus:border-brand-500"
                      >
                        <option value="">All Departments</option>
                        {options.departments.map((dept) => {
                          const id = typeof dept === 'object' && dept ? dept.id : dept;
                          const label = typeof dept === 'object' && dept ? dept.label : String(dept);
                          return (
                            <option key={String(id)} value={id}>
                              {label}
                            </option>
                          );
                        })}
                      </select>
                    </div>

                    {/* Company */}
                    <div>
                      <label className="block text-xs text-neutral-600 dark:text-neutral-400 mb-1">
                        Recruiting Company
                      </label>
                      <select
                        value={filters.company_id || ''}
                        onChange={(e) =>
                          setFilters((prev) => ({
                            ...prev,
                            company_id: e.target.value ? Number(e.target.value) : undefined,
                          }))
                        }
                        className="w-full px-3 py-2 rounded-xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 text-sm focus:outline-none focus:border-brand-500"
                      >
                        <option value="">All Companies</option>
                        {options.companies.map((c) => (
                          <option key={c.id} value={c.id}>
                            {c.label}
                          </option>
                        ))}
                      </select>
                    </div>

                    {/* Placement Drive */}
                    <div>
                      <label className="block text-xs text-neutral-600 dark:text-neutral-400 mb-1">
                        Placement Drive
                      </label>
                      <select
                        value={filters.drive_id || ''}
                        onChange={(e) =>
                          setFilters((prev) => ({
                            ...prev,
                            drive_id: e.target.value ? Number(e.target.value) : undefined,
                          }))
                        }
                        className="w-full px-3 py-2 rounded-xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 text-sm focus:outline-none focus:border-brand-500"
                      >
                        <option value="">All Placement Drives</option>
                        {options.drives.map((d) => (
                          <option key={d.id} value={d.id}>
                            {d.label}
                          </option>
                        ))}
                      </select>
                    </div>

                    {/* Application Status */}
                    <div>
                      <label className="block text-xs text-neutral-600 dark:text-neutral-400 mb-1">
                        Application Status
                      </label>
                      <select
                        value={filters.application_status || ''}
                        onChange={(e) =>
                          setFilters((prev) => ({
                            ...prev,
                            application_status: e.target.value || undefined,
                          }))
                        }
                        className="w-full px-3 py-2 rounded-xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 text-sm focus:outline-none focus:border-brand-500"
                      >
                        <option value="">All Statuses</option>
                        {options.application_statuses.map((st) => {
                          const id = typeof st === 'object' && st ? st.id : st;
                          const label =
                            typeof st === 'object' && st
                              ? st.label
                              : String(st).replace(/_/g, ' ').toUpperCase();
                          return (
                            <option key={String(id)} value={id}>
                              {label}
                            </option>
                          );
                        })}
                      </select>
                    </div>

                    {/* Minimum CTC */}
                    <div>
                      <label className="block text-xs text-neutral-600 dark:text-neutral-400 mb-1">
                        Min Package (LPA)
                      </label>
                      <input
                        type="number"
                        min="0"
                        step="0.5"
                        placeholder="e.g. 6.0"
                        value={filters.min_package_lpa || ''}
                        onChange={(e) =>
                          setFilters((prev) => ({
                            ...prev,
                            min_package_lpa: e.target.value ? Number(e.target.value) : undefined,
                          }))
                        }
                        className="w-full px-3 py-2 rounded-xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 text-sm focus:outline-none focus:border-brand-500"
                      >
                      </input>
                    </div>

                    {/* Maximum CTC */}
                    <div>
                      <label className="block text-xs text-neutral-600 dark:text-neutral-400 mb-1">
                        Max Package (LPA)
                      </label>
                      <input
                        type="number"
                        min="0"
                        step="0.5"
                        placeholder="e.g. 25.0"
                        value={filters.max_package_lpa || ''}
                        onChange={(e) =>
                          setFilters((prev) => ({
                            ...prev,
                            max_package_lpa: e.target.value ? Number(e.target.value) : undefined,
                          }))
                        }
                        className="w-full px-3 py-2 rounded-xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 text-sm focus:outline-none focus:border-brand-500"
                      >
                      </input>
                    </div>
                  </div>
                </div>

                {/* 4. Action Buttons */}
                <div className="flex flex-wrap items-center justify-between gap-4 pt-4 border-t border-neutral-100 dark:border-neutral-800">
                  <div className="flex items-center gap-2 text-xs text-neutral-500 dark:text-neutral-400">
                    <ShieldCheck className="w-4 h-4 text-brand-500" />
                    <span>Strict Institutional Policy: Placed counts require official accepted offers.</span>
                  </div>

                  <div className="flex flex-wrap items-center gap-3">
                    <Button
                      variant="outline"
                      onClick={handlePreview}
                      disabled={loadingPreview || generating}
                      className="flex items-center gap-2"
                    >
                      {loadingPreview ? (
                        <RefreshCw className="w-4 h-4 animate-spin" />
                      ) : (
                        <Eye className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                      )}
                      Live Interactive Preview
                    </Button>

                    <Button
                      variant="outline"
                      onClick={handleEnqueueAsync}
                      disabled={generating}
                      className="flex items-center gap-2"
                      title="Enqueues the generation in a background worker task"
                    >
                      <Clock className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                      Generate Asynchronously
                    </Button>

                    <Button
                      variant="primary"
                      onClick={handleGenerateAndDownload}
                      disabled={generating}
                      className="flex items-center gap-2"
                    >
                      {generating ? (
                        <RefreshCw className="w-4 h-4 animate-spin" />
                      ) : (
                        <Download className="w-4 h-4" />
                      )}
                      Generate & Download ({selectedFormat.toUpperCase()})
                    </Button>
                  </div>
                </div>
              </div>
            </Card>

            {/* Error in Preview */}
            {previewError && (
              <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 text-sm flex items-center gap-3">
                <AlertCircle className="w-5 h-5 flex-shrink-0" />
                <span>{previewError}</span>
              </div>
            )}

            {/* LIVE PREVIEW SECTION */}
            {previewData && (
              <div className="space-y-6">
                {/* Header Banner for Preview */}
                <div className="p-5 rounded-2xl bg-gradient-to-r from-brand-600 to-indigo-600 text-white shadow-md flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                  <div>
                    <div className="flex items-center gap-2 text-brand-200 text-xs font-semibold uppercase tracking-wider mb-1">
                      <CurrentTypeIcon className="w-4 h-4" />
                      <span>{previewData.institution_name}</span>
                      <span>•</span>
                      <span>{previewData.report_type.replace(/_/g, ' ')}</span>
                    </div>
                    <h2 className="text-xl font-bold">{previewData.title}</h2>
                    <p className="text-xs text-brand-100 mt-1">
                      Calculated on {new Date(previewData.generated_at).toLocaleString()} • {rawRows.length} records extracted
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    <Button
                      variant="secondary"
                      onClick={handleGenerateAndDownload}
                      disabled={generating}
                      className="bg-white text-brand-700 hover:bg-brand-50 border-none shadow-sm flex items-center gap-2 text-xs font-bold"
                    >
                      <Download className="w-3.5 h-3.5" />
                      Export Document ({selectedFormat.toUpperCase()})
                    </Button>
                  </div>
                </div>

                {/* KPI Overview Cards */}
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
                  <div className="p-4 rounded-xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-850 shadow-sm">
                    <span className="text-[11px] font-medium text-neutral-500 dark:text-neutral-400 block mb-1">
                      Eligible Students
                    </span>
                    <span className="text-2xl font-bold text-neutral-900 dark:text-white">
                      {previewData.summary_kpis.total_eligible_students ?? 0}
                    </span>
                    <span className="text-[10px] text-neutral-400 block mt-1">Institutional cohort</span>
                  </div>

                  <div className="p-4 rounded-xl border border-emerald-200 dark:border-emerald-800/40 bg-emerald-50/50 dark:bg-emerald-950/20 shadow-sm">
                    <span className="text-[11px] font-medium text-emerald-700 dark:text-emerald-400 block mb-1">
                      Placed Students
                    </span>
                    <span className="text-2xl font-bold text-emerald-800 dark:text-emerald-300">
                      {previewData.summary_kpis.total_placed_students ?? 0}
                    </span>
                    <span className="text-[10px] text-emerald-600 dark:text-emerald-500 block mt-1">
                      Placement Rate: {(previewData.summary_kpis.placement_rate_pct ?? 0).toFixed(1)}%
                    </span>
                  </div>

                  <div className="p-4 rounded-xl border border-amber-200 dark:border-amber-800/40 bg-amber-50/50 dark:bg-amber-950/20 shadow-sm">
                    <span className="text-[11px] font-medium text-amber-700 dark:text-amber-400 block mb-1">
                      Active In Pipeline
                    </span>
                    <span className="text-2xl font-bold text-amber-800 dark:text-amber-300">
                      {previewData.summary_kpis.active_in_pipeline_students ?? previewData.summary_kpis.students_in_pipeline ?? 0}
                    </span>
                    <span className="text-[10px] text-amber-600 dark:text-amber-500 block mt-1">
                      Unplaced: {previewData.summary_kpis.total_unplaced_students ?? previewData.summary_kpis.students_not_yet_placed ?? 0}
                    </span>
                  </div>

                  <div className="p-4 rounded-xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-850 shadow-sm">
                    <span className="text-[11px] font-medium text-neutral-500 dark:text-neutral-400 block mb-1">
                      Highest Package
                    </span>
                    <span className="text-2xl font-bold text-brand-600 dark:text-brand-400">
                      {previewData.summary_kpis.highest_package_lpa != null && previewData.summary_kpis.highest_package_lpa > 0
                        ? `${previewData.summary_kpis.highest_package_lpa.toFixed(2)} LPA`
                        : 'N/A'}
                    </span>
                    <span className="text-[10px] text-neutral-400 block mt-1">
                      Median: {previewData.summary_kpis.median_package_lpa != null && previewData.summary_kpis.median_package_lpa > 0
                        ? `${previewData.summary_kpis.median_package_lpa.toFixed(2)} LPA`
                        : 'N/A'}
                    </span>
                  </div>

                  <div className="p-4 rounded-xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-850 shadow-sm">
                    <span className="text-[11px] font-medium text-neutral-500 dark:text-neutral-400 block mb-1">
                      Average Package
                    </span>
                    <span className="text-2xl font-bold text-neutral-900 dark:text-white">
                      {previewData.summary_kpis.average_package_lpa != null && previewData.summary_kpis.average_package_lpa > 0
                        ? `${previewData.summary_kpis.average_package_lpa.toFixed(2)} LPA`
                        : 'N/A'}
                    </span>
                    <span className="text-[10px] text-neutral-400 block mt-1">Placed candidates</span>
                  </div>

                  <div className="p-4 rounded-xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-850 shadow-sm">
                    <span className="text-[11px] font-medium text-neutral-500 dark:text-neutral-400 block mb-1">
                      Offers Accepted
                    </span>
                    <span className="text-2xl font-bold text-neutral-900 dark:text-white">
                      {previewData.summary_kpis.total_offers_accepted ?? previewData.summary_kpis.total_accepted_offers ?? 0}
                    </span>
                    <span className="text-[10px] text-neutral-400 block mt-1">
                      Of {previewData.summary_kpis.total_offers_released ?? 0} released ({(previewData.summary_kpis.offer_acceptance_rate_pct ?? 0).toFixed(1)}%)
                    </span>
                  </div>
                </div>

                {/* Department Distribution & Funnel Visualizations */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Department Chart */}
                  <Card>
                    <CardHeader
                      title="Department Placement Rate (%)"
                      subtitle="Comparative placement percentage across academic disciplines"
                    />
                    <div className="p-6">
                      {previewData.department_stats && previewData.department_stats.length > 0 ? (
                        <div className="h-64 w-full">
                          <ResponsiveContainer width="100%" height="100%">
                            <BarChart
                              data={previewData.department_stats.map((d) => ({
                                ...d,
                                department: d.department || d.department_code || d.department_name,
                              }))}
                              margin={{ top: 10, right: 10, left: -20, bottom: 25 }}
                            >
                              <CartesianGrid strokeDasharray="3 3" stroke={isDark ? '#333' : '#eee'} />
                              <XAxis
                                dataKey="department"
                                stroke={isDark ? '#888' : '#666'}
                                fontSize={11}
                                interval={0}
                                angle={-25}
                                textAnchor="end"
                              />
                              <YAxis stroke={isDark ? '#888' : '#666'} fontSize={11} domain={[0, 100]} />
                              <Tooltip
                                contentStyle={{
                                  backgroundColor: isDark ? '#1f2937' : '#ffffff',
                                  borderColor: isDark ? '#374151' : '#e5e7eb',
                                  color: isDark ? '#f3f4f6' : '#111827',
                                }}
                                formatter={(val: number) => [`${(val ?? 0).toFixed(1)}%`, 'Placement Rate']}
                              />
                              <Bar dataKey="placement_rate_pct" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                            </BarChart>
                          </ResponsiveContainer>
                        </div>
                      ) : (
                        <div className="h-64 flex items-center justify-center text-sm text-neutral-400">
                          No department breakdown available for current filters.
                        </div>
                      )}
                    </div>
                  </Card>

                  {/* Recruitment Funnel */}
                  <Card>
                    <CardHeader
                      title="Recruitment Conversion Funnel"
                      subtitle="Attrition from initial application through accepted institutional offers"
                    />
                    <div className="p-6">
                      {previewData.recruitment_funnel && previewData.recruitment_funnel.length > 0 ? (
                        <div className="space-y-3">
                          {previewData.recruitment_funnel.map((stage) => {
                            const isAccepted = stage.stage === 'offer_accepted';
                            const stageName = stage.display_name || stage.label || stage.stage;
                            const stagePct = stage.conversion_from_applied_pct ?? stage.percentage ?? 0;
                            return (
                              <div key={stage.stage} className="space-y-1">
                                <div className="flex justify-between items-center text-xs">
                                  <span className="font-semibold text-neutral-800 dark:text-neutral-200">
                                    {stageName}
                                  </span>
                                  <span className="text-neutral-500 dark:text-neutral-400 font-mono">
                                    {stage.count} candidates ({(stagePct ?? 0).toFixed(1)}%)
                                  </span>
                                </div>
                                <div className="w-full bg-neutral-100 dark:bg-neutral-800 rounded-full h-2.5 overflow-hidden">
                                  <div
                                    className={`h-2.5 rounded-full transition-all duration-500 ${
                                      isAccepted
                                        ? 'bg-emerald-500'
                                        : 'bg-gradient-to-r from-brand-500 to-indigo-500'
                                    }`}
                                    style={{
                                      width: `${Math.max(4, Math.min(100, stagePct ?? 0))}%`,
                                    }}
                                  />
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      ) : (
                        <div className="h-64 flex items-center justify-center text-sm text-neutral-400">
                          No recruitment activity recorded for current scope.
                        </div>
                      )}
                    </div>
                  </Card>
                </div>

                {/* Granular Report Data Table */}
                <Card>
                  <div className="p-5 border-b border-neutral-200 dark:border-neutral-800 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                    <div>
                      <h3 className="text-base font-bold text-neutral-900 dark:text-neutral-100">
                        Extracted Report Ledger Records
                      </h3>
                      <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">
                        Showing {paginatedRows.length} of {filteredRows.length} total rows matching active filters
                      </p>
                    </div>

                    <div className="w-full sm:w-64 relative">
                      <Search className="w-4 h-4 absolute left-3 top-2.5 text-neutral-400" />
                      <input
                        type="text"
                        placeholder="Search records..."
                        value={previewSearch}
                        onChange={(e) => {
                          setPreviewSearch(e.target.value);
                          setPreviewPage(1);
                        }}
                        className="w-full pl-9 pr-3 py-1.5 rounded-xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-xs focus:outline-none focus:border-brand-500"
                      />
                    </div>
                  </div>

                  <div className="overflow-x-auto">
                    {paginatedRows.length > 0 ? (
                      <table className="w-full text-left border-collapse text-xs">
                        <thead>
                          <tr className="bg-neutral-50 dark:bg-neutral-800/60 border-b border-neutral-200 dark:border-neutral-800">
                            {previewColumns.map((col) => (
                              <th
                                key={col}
                                className="px-4 py-3 font-semibold uppercase tracking-wider text-neutral-600 dark:text-neutral-400 whitespace-nowrap"
                              >
                                {colHeaderMap[col] || col.replace(/_/g, ' ')}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-neutral-200 dark:divide-neutral-800">
                          {paginatedRows.map((row, idx) => (
                            <tr
                              key={idx}
                              className="hover:bg-neutral-50/80 dark:hover:bg-neutral-800/40 transition-colors"
                            >
                              {previewColumns.map((col) => {
                                const val = row[col];
                                const isStatusCol = col.toLowerCase().includes('status');
                                const isPkgCol = col.toLowerCase().includes('package') || col.toLowerCase().includes('ctc') || col.toLowerCase().includes('lpa');

                                return (
                                  <td
                                    key={col}
                                    className="px-4 py-2.5 text-neutral-800 dark:text-neutral-200 whitespace-nowrap font-medium"
                                  >
                                    {isStatusCol && typeof val === 'string' ? (
                                      <span
                                        className={`px-2 py-0.5 rounded-md text-[10px] font-semibold uppercase ${
                                          val.includes('accepted') || val.includes('placed')
                                            ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300'
                                            : val.includes('declined') || val.includes('unplaced')
                                            ? 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300'
                                            : 'bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300'
                                        }`}
                                      >
                                        {val}
                                      </span>
                                    ) : isPkgCol && typeof val === 'number' ? (
                                      <span className="font-semibold text-brand-600 dark:text-brand-400">
                                        {val.toFixed(2)} LPA
                                      </span>
                                    ) : (
                                      String(val ?? '—')
                                    )}
                                  </td>
                                );
                              })}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    ) : (
                      <div className="py-12 text-center text-neutral-400 text-xs">
                        No ledger rows matching current search query.
                      </div>
                    )}
                  </div>

                  {/* Pagination */}
                  {totalPages > 1 && (
                    <div className="p-4 border-t border-neutral-200 dark:border-neutral-800 flex items-center justify-between text-xs text-neutral-500">
                      <span>
                        Page {previewPage} of {totalPages}
                      </span>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={previewPage <= 1}
                          onClick={() => setPreviewPage((p) => Math.max(1, p - 1))}
                        >
                          Previous
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={previewPage >= totalPages}
                          onClick={() => setPreviewPage((p) => Math.min(totalPages, p + 1))}
                        >
                          Next
                        </Button>
                      </div>
                    </div>
                  )}
                </Card>
              </div>
            )}
          </div>
        )}

        {/* TAB 2: REPORT ARCHIVE */}
        {activeTab === 'history' && (
          <div className="space-y-6">
            <Card>
              <div className="p-5 border-b border-neutral-200 dark:border-neutral-800 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div>
                  <h2 className="text-lg font-bold text-neutral-900 dark:text-neutral-100">
                    Institutional Placement Report Archive
                  </h2>
                  <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">
                    Historical record of generated and asynchronous documents with secure downloads
                  </p>
                </div>

                <div className="flex flex-wrap items-center gap-3 w-full sm:w-auto">
                  {/* Search */}
                  <div className="relative flex-1 sm:w-60">
                    <Search className="w-4 h-4 absolute left-3 top-2.5 text-neutral-400" />
                    <input
                      type="text"
                      placeholder="Search archive..."
                      value={historySearch}
                      onChange={(e) => setHistorySearch(e.target.value)}
                      className="w-full pl-9 pr-3 py-1.5 rounded-xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-xs focus:outline-none focus:border-brand-500"
                    />
                  </div>

                  {/* Refresh */}
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={loadHistory}
                    disabled={loadingHistory}
                    className="flex items-center gap-1.5"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${loadingHistory ? 'animate-spin' : ''}`} />
                    Refresh
                  </Button>
                </div>
              </div>

              <div className="overflow-x-auto">
                {filteredHistory.length > 0 ? (
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="bg-neutral-50 dark:bg-neutral-800/60 border-b border-neutral-200 dark:border-neutral-800">
                        <th className="px-4 py-3 font-semibold uppercase text-neutral-600 dark:text-neutral-400">ID</th>
                        <th className="px-4 py-3 font-semibold uppercase text-neutral-600 dark:text-neutral-400">Report Title</th>
                        <th className="px-4 py-3 font-semibold uppercase text-neutral-600 dark:text-neutral-400">Type</th>
                        <th className="px-4 py-3 font-semibold uppercase text-neutral-600 dark:text-neutral-400">Format</th>
                        <th className="px-4 py-3 font-semibold uppercase text-neutral-600 dark:text-neutral-400">Status</th>
                        <th className="px-4 py-3 font-semibold uppercase text-neutral-600 dark:text-neutral-400">File Size</th>
                        <th className="px-4 py-3 font-semibold uppercase text-neutral-600 dark:text-neutral-400">Generated</th>
                        <th className="px-4 py-3 font-semibold uppercase text-neutral-600 dark:text-neutral-400 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-neutral-200 dark:divide-neutral-800">
                      {filteredHistory.map((rep) => {
                        const fmtMeta = FORMAT_CONFIG[rep.file_format] || FORMAT_CONFIG.pdf;
                        const statusMeta = STATUS_BADGE[rep.status] || STATUS_BADGE.pending;
                        const FmtIcon = fmtMeta.icon;

                        return (
                          <tr
                            key={rep.id}
                            className="hover:bg-neutral-50/80 dark:hover:bg-neutral-800/40 transition-colors"
                          >
                            <td className="px-4 py-3 font-mono text-neutral-500">#{rep.id}</td>
                            <td className="px-4 py-3">
                              <span className="font-semibold text-neutral-900 dark:text-neutral-100 block">
                                {rep.title}
                              </span>
                              {(rep.generated_by_name || rep.creator_name) && (
                                <span className="text-[10px] text-neutral-400">By {rep.generated_by_name || rep.creator_name}</span>
                              )}
                            </td>
                            <td className="px-4 py-3">
                              <span className="text-neutral-700 dark:text-neutral-300">
                                {REPORT_TYPE_CONFIG[rep.report_type]?.label || rep.report_type}
                              </span>
                            </td>
                            <td className="px-4 py-3">
                              <span
                                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md border text-[10px] font-bold uppercase ${fmtMeta.badgeClass}`}
                              >
                                <FmtIcon className="w-3 h-3" />
                                {rep.file_format}
                              </span>
                            </td>
                            <td className="px-4 py-3">
                              <Badge variant={statusMeta.variant} size="sm">
                                {statusMeta.label}
                              </Badge>
                            </td>
                            <td className="px-4 py-3 text-neutral-500 font-mono">
                              {formatFileSize(rep.file_size_bytes)}
                            </td>
                            <td className="px-4 py-3 text-neutral-500 whitespace-nowrap">
                              {new Date(rep.created_at).toLocaleString([], {
                                year: 'numeric',
                                month: 'short',
                                day: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit',
                              })}
                            </td>
                            <td className="px-4 py-3 text-right whitespace-nowrap">
                              <div className="flex items-center justify-end gap-2">
                                {rep.status === 'completed' && (
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => handleDownloadHistorical(rep)}
                                    className="flex items-center gap-1 text-xs"
                                  >
                                    <Download className="w-3 h-3" />
                                    Download
                                  </Button>
                                )}
                                <button
                                  type="button"
                                  onClick={() => handleDeleteReport(rep.id)}
                                  className="p-1.5 rounded-lg text-neutral-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 transition-colors"
                                  title="Delete Report"
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                </button>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                ) : (
                  <div className="py-16 text-center space-y-3">
                    <FileSpreadsheet className="w-10 h-10 text-neutral-300 dark:text-neutral-600 mx-auto" />
                    <p className="text-sm font-medium text-neutral-600 dark:text-neutral-400">
                      No placement reports found in the archive.
                    </p>
                    <p className="text-xs text-neutral-400">
                      Use the &quot;Generator &amp; Preview&quot; tab to build institutional PDF, Excel, or CSV reports.
                    </p>
                  </div>
                )}
              </div>
            </Card>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
};

export default TpoReportsPage;
