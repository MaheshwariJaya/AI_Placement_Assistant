import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  AlertTriangle,
  Award,
  BarChart3,
  Briefcase,
  Building2,
  Download,
  FileSpreadsheet,
  Filter,
  GitBranch,
  Info,
  Layers,
  RefreshCw,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  Users,
} from 'lucide-react';
import { DashboardLayout } from '../../components/layout/DashboardLayout';
import { Card, CardHeader } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { useTheme } from '../../context/ThemeContext';
import { tpoIntelligenceApi, TpoIntelligenceQueryParams } from '../../services/api';
import {
  ForecastMetricEstimate,
  TpoPlacementIntelligenceResponse,
} from '../../types';

const CONFIDENCE_BADGE: Record<
  ForecastMetricEstimate['confidence_level'],
  'success' | 'brand' | 'warning' | 'neutral'
> = {
  high: 'success',
  moderate: 'brand',
  low: 'warning',
  exploratory: 'neutral',
};

const TREND_BADGE: Record<
  'upward' | 'stable' | 'downward' | 'insufficient_history',
  'success' | 'brand' | 'danger' | 'neutral'
> = {
  upward: 'success',
  stable: 'brand',
  downward: 'danger',
  insufficient_history: 'neutral',
};

const formatLpa = (val?: number | null): string =>
  val !== null && val !== undefined ? `${val.toFixed(2)} LPA` : 'N/A';

const triggerBlobDownload = (blob: Blob, filename: string) => {
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(url);
};

export const TpoIntelligencePage: React.FC = () => {
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === 'dark';

  const [data, setData] = useState<TpoPlacementIntelligenceResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [exportingPdf, setExportingPdf] = useState(false);
  const [exportingExcel, setExportingExcel] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Filter controls
  const [academicYear, setAcademicYear] = useState('');
  const [graduationYear, setGraduationYear] = useState('');
  const [departmentId, setDepartmentId] = useState('');
  const [companyId, setCompanyId] = useState('');
  const [jobCategory, setJobCategory] = useState('');
  const [employmentType, setEmploymentType] = useState('');

  const buildQueryParams = useCallback(
    (refresh = false): TpoIntelligenceQueryParams => ({
      academic_year: academicYear || undefined,
      graduation_year: graduationYear ? Number(graduationYear) : undefined,
      department_id: departmentId ? Number(departmentId) : undefined,
      company_id: companyId ? Number(companyId) : undefined,
      job_category: jobCategory || undefined,
      employment_type: employmentType || undefined,
      refresh: refresh || undefined,
    }),
    [academicYear, graduationYear, departmentId, companyId, jobCategory, employmentType]
  );

  const loadIntelligence = useCallback(
    async (refresh = false) => {
      setLoading(true);
      setErrorMsg(null);
      try {
        const res = await tpoIntelligenceApi.getDashboard(buildQueryParams(refresh));
        setData(res);
      } catch (err: unknown) {
        const msg =
          err instanceof Error
            ? err.message
            : 'Unable to load placement intelligence and forecasting analytics.';
        setErrorMsg(msg);
      } finally {
        setLoading(false);
      }
    },
    [buildQueryParams]
  );

  useEffect(() => {
    loadIntelligence(false);
  }, [loadIntelligence]);

  const handleResetFilters = () => {
    setAcademicYear('');
    setGraduationYear('');
    setDepartmentId('');
    setCompanyId('');
    setJobCategory('');
    setEmploymentType('');
  };

  const handleExportPdf = async () => {
    setExportingPdf(true);
    try {
      const blob = await tpoIntelligenceApi.exportPdf(buildQueryParams(false));
      triggerBlobDownload(blob, 'placement_intelligence_report.pdf');
    } catch {
      setErrorMsg('Failed to generate PDF placement report.');
    } finally {
      setExportingPdf(false);
    }
  };

  const handleExportExcel = async () => {
    setExportingExcel(true);
    try {
      const blob = await tpoIntelligenceApi.exportExcel(buildQueryParams(false));
      triggerBlobDownload(blob, 'placement_intelligence_report.xlsx');
    } catch {
      setErrorMsg('Failed to generate Excel workbook report.');
    } finally {
      setExportingExcel(false);
    }
  };

  const gridStroke = isDark ? '#334155' : '#e2e8f0';
  const axisTickColor = isDark ? '#94a3b8' : '#475569';
  const tooltipStyle = useMemo(
    () => ({
      backgroundColor: isDark ? '#0f172a' : '#ffffff',
      borderColor: isDark ? '#334155' : '#e2e8f0',
      borderRadius: '0.75rem',
      color: isDark ? '#f1f5f9' : '#0f172a',
      fontSize: '12px',
    }),
    [isDark]
  );

  const renderForecastCard = (fc: ForecastMetricEstimate) => (
    <Card key={fc.metric_key} className="flex flex-col justify-between">
      <div>
        <div className="flex items-start justify-between gap-2 mb-3">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Target Period: {fc.target_period}
            </p>
            <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100 mt-0.5">
              {fc.metric_label}
            </h4>
          </div>
          <Badge variant={CONFIDENCE_BADGE[fc.confidence_level]}>
            {fc.confidence_level} confidence
          </Badge>
        </div>

        <div className="flex items-baseline gap-2 mb-2">
          <span className="text-3xl font-extrabold text-brand-600 dark:text-brand-400">
            {fc.projected_value}
          </span>
          <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
            {fc.unit}
          </span>
        </div>

        <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/70 border border-slate-200 dark:border-slate-700 text-xs space-y-1 mb-3">
          <div className="flex justify-between">
            <span className="text-slate-500 dark:text-slate-400">95% Confidence Interval:</span>
            <span className="font-semibold text-slate-800 dark:text-slate-200">
              {fc.ci_lower_95} – {fc.ci_upper_95} {fc.unit}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500 dark:text-slate-400">Historical Sample Size:</span>
            <span className="font-semibold text-slate-800 dark:text-slate-200">
              {fc.sample_size} cohort(s)
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500 dark:text-slate-400">Model Fit (R²):</span>
            <span className="font-semibold text-slate-800 dark:text-slate-200">
              {fc.r_squared !== null && fc.r_squared !== undefined ? fc.r_squared.toFixed(3) : 'N/A'}
            </span>
          </div>
          <div className="pt-1 border-t border-slate-200 dark:border-slate-700 text-[11px] text-slate-500 dark:text-slate-400">
            Method: <span className="font-medium text-slate-700 dark:text-slate-300">{fc.methodology}</span>
          </div>
        </div>
      </div>

      {fc.limitations.length > 0 && (
        <div className="text-[11px] text-amber-700 dark:text-amber-300 bg-amber-50/70 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800/60 rounded-lg p-2.5">
          <div className="font-semibold mb-1 flex items-center gap-1">
            <Info className="w-3.5 h-3.5 shrink-0" />
            Model Limitations
          </div>
          <ul className="list-disc pl-4 space-y-0.5">
            {fc.limitations.map((lim, idx) => (
              <li key={idx}>{lim}</li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );

  return (
    <DashboardLayout
      role="tpo"
      title="Placement Intelligence & Statistical Forecasting"
      subtitle="Historical cohort analytics, package distributions, skill-demand intelligence, statistical regression forecasts, and PDF/Excel reporting."
    >
      {/* Top Toolbar: Actions & Exports */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
        <div className="flex items-center gap-2">
          <Badge variant="brand" className="text-xs">
            Institutional Analytics Engine
          </Badge>
          {data && (
            <span className="text-[11px] text-slate-500 dark:text-slate-400">
              Generated {new Date(data.generated_at).toLocaleString()}
              {data.cache_hit ? ' (cached)' : ' (live)'}
            </span>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => loadIntelligence(true)}
            disabled={loading}
            className="text-xs"
          >
            <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh Live Data
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={handleExportPdf}
            disabled={loading || exportingPdf || !data}
            className="text-xs"
          >
            <Download className="w-3.5 h-3.5 mr-1.5" />
            {exportingPdf ? 'Exporting PDF...' : 'Export PDF'}
          </Button>
          <Button
            size="sm"
            variant="primary"
            onClick={handleExportExcel}
            disabled={loading || exportingExcel || !data}
            className="text-xs"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 mr-1.5" />
            {exportingExcel ? 'Exporting Excel...' : 'Export Excel (.xlsx)'}
          </Button>
        </div>
      </div>

      {/* Filters Panel */}
      <Card className="mb-5">
        <div className="flex items-center justify-between gap-2 mb-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-800 dark:text-slate-200">
            <Filter className="w-4 h-4 text-brand-500" />
            Cohort & Recruitment Filters
          </div>
          <Button size="sm" variant="ghost" onClick={handleResetFilters} className="text-xs">
            <RotateCcw className="w-3.5 h-3.5 mr-1" />
            Reset All
          </Button>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-3">
          <div>
            <label className="block text-[11px] font-medium text-slate-500 dark:text-slate-400 mb-1">
              Academic Year
            </label>
            <select
              value={academicYear}
              onChange={(e) => setAcademicYear(e.target.value)}
              className="w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-2.5 py-1.5 text-xs text-slate-800 dark:text-slate-200"
            >
              <option value="">All Academic Years</option>
              {data?.filter_options.academic_years.map((ay) => (
                <option key={ay} value={ay}>
                  {ay}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-[11px] font-medium text-slate-500 dark:text-slate-400 mb-1">
              Graduation Batch
            </label>
            <select
              value={graduationYear}
              onChange={(e) => setGraduationYear(e.target.value)}
              className="w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-2.5 py-1.5 text-xs text-slate-800 dark:text-slate-200"
            >
              <option value="">All Batches</option>
              {data?.filter_options.graduation_batches.map((yr) => (
                <option key={yr} value={String(yr)}>
                  Batch {yr}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-[11px] font-medium text-slate-500 dark:text-slate-400 mb-1">
              Department
            </label>
            <select
              value={departmentId}
              onChange={(e) => setDepartmentId(e.target.value)}
              className="w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-2.5 py-1.5 text-xs text-slate-800 dark:text-slate-200"
            >
              <option value="">All Departments</option>
              {data?.filter_options.departments.map((d) => (
                <option key={d.id} value={String(d.id)}>
                  {d.code ? `${d.code} — ${d.name}` : d.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-[11px] font-medium text-slate-500 dark:text-slate-400 mb-1">
              Company Partner
            </label>
            <select
              value={companyId}
              onChange={(e) => setCompanyId(e.target.value)}
              className="w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-2.5 py-1.5 text-xs text-slate-800 dark:text-slate-200"
            >
              <option value="">All Companies</option>
              {data?.filter_options.companies.map((c) => (
                <option key={c.id} value={String(c.id)}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-[11px] font-medium text-slate-500 dark:text-slate-400 mb-1">
              Job Category
            </label>
            <select
              value={jobCategory}
              onChange={(e) => setJobCategory(e.target.value)}
              className="w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-2.5 py-1.5 text-xs text-slate-800 dark:text-slate-200"
            >
              <option value="">All Categories</option>
              {data?.filter_options.job_categories.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-[11px] font-medium text-slate-500 dark:text-slate-400 mb-1">
              Employment Type
            </label>
            <select
              value={employmentType}
              onChange={(e) => setEmploymentType(e.target.value)}
              className="w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-2.5 py-1.5 text-xs text-slate-800 dark:text-slate-200"
            >
              <option value="">All Types</option>
              {data?.filter_options.employment_types.map((et) => (
                <option key={et} value={et}>
                  {et.replace(/_/g, ' ')}
                </option>
              ))}
            </select>
          </div>
        </div>
      </Card>

      {errorMsg && (
        <div className="mb-5 p-4 rounded-xl bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-200 text-xs flex items-center justify-between">
          <span>{errorMsg}</span>
          <Button size="sm" variant="outline" onClick={() => loadIntelligence(false)}>
            Retry
          </Button>
        </div>
      )}

      {loading && !data ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i} className="h-28 animate-pulse bg-slate-100 dark:bg-slate-800/50">
              <div className="h-full" />
            </Card>
          ))}
        </div>
      ) : (
        data && (
          <div className="space-y-6">
            {/* Counting Policy & Data Completeness Warnings */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div className="p-3.5 rounded-xl bg-emerald-50/70 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800/70 text-xs text-emerald-900 dark:text-emerald-200 flex gap-2.5">
                <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <div className="font-semibold mb-0.5">Official Placement Definition Policy</div>
                  <p className="leading-relaxed opacity-90">{data.policy_summary}</p>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-amber-50/70 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800/70 text-xs text-amber-900 dark:text-amber-200 flex gap-2.5">
                <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
                <div>
                  <div className="font-semibold mb-0.5">
                    Data Completeness & Sample Coverage ({data.data_completeness.historical_years_available} cohort year
                    {data.data_completeness.historical_years_available === 1 ? '' : 's'})
                  </div>
                  {data.data_completeness.warnings.length > 0 ? (
                    <ul className="list-disc pl-4 space-y-0.5">
                      {data.data_completeness.warnings.map((w, idx) => (
                        <li key={idx}>{w}</li>
                      ))}
                    </ul>
                  ) : (
                    <p>No missing compensation, department, or drive metadata issues detected in this slice.</p>
                  )}
                </div>
              </div>
            </div>

            {/* 1. Placement Overview KPI Grid */}
            <section>
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-600 dark:text-slate-300 mb-3 flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-brand-500" />
                1. Placement Overview
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <Card>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">
                      Eligible Students
                    </span>
                    <Users className="w-4 h-4 text-brand-500" />
                  </div>
                  <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-2">
                    {data.overview.total_eligible_students}
                  </div>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                    Out of {data.overview.total_registered_students} registered students
                  </p>
                </Card>

                <Card>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">
                      Placed Students
                    </span>
                    <Award className="w-4 h-4 text-emerald-500" />
                  </div>
                  <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-2">
                    {data.overview.total_placed_students}
                  </div>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                    Placement Rate: <span className="font-semibold">{data.overview.placement_rate_pct}%</span>
                  </p>
                </Card>

                <Card>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">
                      In Recruitment Pipeline
                    </span>
                    <GitBranch className="w-4 h-4 text-sky-500" />
                  </div>
                  <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-2">
                    {data.overview.students_in_pipeline}
                  </div>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                    Not yet placed: {data.overview.students_not_yet_placed}
                  </p>
                </Card>

                <Card>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">
                      Drives & Companies
                    </span>
                    <Building2 className="w-4 h-4 text-violet-500" />
                  </div>
                  <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-2">
                    {data.overview.total_participating_companies} Companies
                  </div>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                    {data.overview.total_active_drives} active/ongoing drives · {data.overview.total_published_jobs} jobs
                  </p>
                </Card>

                <Card>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">
                      Offers Released vs Accepted
                    </span>
                    <Briefcase className="w-4 h-4 text-amber-500" />
                  </div>
                  <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-2">
                    {data.overview.total_accepted_offers} / {data.overview.total_offers_released}
                  </div>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                    {data.overview.offer_acceptance_rate_pct}% acceptance · {data.overview.total_declined_offers} declined · {data.overview.pending_offers} pending
                  </p>
                </Card>

                <Card>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">
                      Average Package
                    </span>
                    <TrendingUp className="w-4 h-4 text-emerald-500" />
                  </div>
                  <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-2">
                    {formatLpa(data.overview.average_package_lpa)}
                  </div>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                    Deduplicated highest offer per placed student
                  </p>
                </Card>

                <Card>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">
                      Median Package
                    </span>
                    <Layers className="w-4 h-4 text-brand-500" />
                  </div>
                  <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-2">
                    {formatLpa(data.overview.median_package_lpa)}
                  </div>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                    50th percentile among priced offers
                  </p>
                </Card>

                <Card>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">
                      Highest Package
                    </span>
                    <Sparkles className="w-4 h-4 text-rose-500" />
                  </div>
                  <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-2">
                    {formatLpa(data.overview.highest_package_lpa)}
                  </div>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                    Offers missing CTC: {data.overview.offers_missing_package_count}
                  </p>
                </Card>
              </div>
            </section>

            {/* 2. Department-Wise Analytics */}
            <section className="grid grid-cols-1 xl:grid-cols-12 gap-5">
              <Card className="xl:col-span-5">
                <CardHeader
                  title="Department Placement Comparison"
                  subtitle="Eligible vs placed students per department"
                />
                {data.department_analytics.length === 0 ? (
                  <p className="text-xs text-slate-500 dark:text-slate-400 py-8 text-center">
                    No department student cohorts match the active filters.
                  </p>
                ) : (
                  <div className="h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={data.department_analytics}
                        margin={{ top: 10, right: 12, left: -12, bottom: 5 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
                        <XAxis dataKey="department_code" stroke={axisTickColor} fontSize={11} />
                        <YAxis stroke={axisTickColor} fontSize={11} allowDecimals={false} />
                        <Tooltip contentStyle={tooltipStyle} />
                        <Legend wrapperStyle={{ fontSize: '11px' }} />
                        <Bar
                          dataKey="eligible_students"
                          name="Eligible"
                          fill="#6366f1"
                          radius={[4, 4, 0, 0]}
                        />
                        <Bar
                          dataKey="placed_students"
                          name="Placed"
                          fill="#10b981"
                          radius={[4, 4, 0, 0]}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </Card>

              <Card className="xl:col-span-7">
                <CardHeader
                  title="Department Performance, Packages & Skill Gaps"
                  subtitle="Cohort breakdown including skill demand and gaps"
                />
                <div className="overflow-x-auto">
                  <table className="w-full text-xs text-left">
                    <thead>
                      <tr className="border-b border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400">
                        <th className="py-2 pr-3 font-semibold">Dept</th>
                        <th className="py-2 px-2 font-semibold">Eligible</th>
                        <th className="py-2 px-2 font-semibold">Placed</th>
                        <th className="py-2 px-2 font-semibold">Pipeline</th>
                        <th className="py-2 px-2 font-semibold">Rate %</th>
                        <th className="py-2 px-2 font-semibold">Avg / High LPA</th>
                        <th className="py-2 pl-2 font-semibold">Demanded &amp; Gap Skills</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                      {data.department_analytics.map((d) => (
                        <tr key={d.department_id}>
                          <td className="py-2.5 pr-3 font-semibold text-slate-800 dark:text-slate-200">
                            {d.department_code}
                          </td>
                          <td className="py-2.5 px-2">{d.eligible_students}</td>
                          <td className="py-2.5 px-2 font-semibold text-emerald-600 dark:text-emerald-400">
                            {d.placed_students}
                          </td>
                          <td className="py-2.5 px-2">{d.in_pipeline_students}</td>
                          <td className="py-2.5 px-2">
                            <Badge variant={d.placement_rate_pct >= 60 ? 'success' : 'brand'}>
                              {d.placement_rate_pct}%
                            </Badge>
                          </td>
                          <td className="py-2.5 px-2 whitespace-nowrap">
                            {d.average_package_lpa !== null && d.average_package_lpa !== undefined
                              ? `${d.average_package_lpa} / ${d.highest_package_lpa ?? '-'} LPA`
                              : 'N/A'}
                          </td>
                          <td className="py-2.5 pl-2">
                            <div className="flex flex-wrap gap-1">
                              {d.top_demanded_skills.slice(0, 3).map((sk) => (
                                <span
                                  key={sk}
                                  className="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-[10px]"
                                >
                                  {sk}
                                </span>
                              ))}
                              {d.skill_gaps.slice(0, 2).map((gap) => (
                                <span
                                  key={gap}
                                  className="px-1.5 py-0.5 rounded bg-rose-50 dark:bg-rose-950/60 text-rose-700 dark:text-rose-300 text-[10px]"
                                >
                                  Gap: {gap}
                                </span>
                              ))}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            </section>

            {/* 3. Historical Trends, Salary Distribution & Recruitment Funnel */}
            <section className="grid grid-cols-1 lg:grid-cols-12 gap-5">
              <Card className="lg:col-span-6">
                <CardHeader
                  title="Historical Placement Rate & Participating Companies"
                  subtitle="Batch-wise comparison across academic years"
                />
                {data.historical_trends.length === 0 ? (
                  <p className="text-xs text-slate-500 dark:text-slate-400 py-8 text-center">
                    No historical batch records available yet.
                  </p>
                ) : (
                  <div className="h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart
                        data={data.historical_trends}
                        margin={{ top: 10, right: 16, left: -8, bottom: 5 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
                        <XAxis dataKey="academic_year" stroke={axisTickColor} fontSize={11} />
                        <YAxis yAxisId="left" stroke={axisTickColor} fontSize={11} domain={[0, 100]} />
                        <YAxis
                          yAxisId="right"
                          orientation="right"
                          stroke={axisTickColor}
                          fontSize={11}
                          allowDecimals={false}
                        />
                        <Tooltip contentStyle={tooltipStyle} />
                        <Legend wrapperStyle={{ fontSize: '11px' }} />
                        <Line
                          yAxisId="left"
                          type="monotone"
                          dataKey="placement_rate_pct"
                          name="Placement Rate (%)"
                          stroke="#10b981"
                          strokeWidth={2.5}
                          dot={{ r: 4 }}
                        />
                        <Line
                          yAxisId="right"
                          type="monotone"
                          dataKey="participating_companies"
                          name="Companies"
                          stroke="#6366f1"
                          strokeWidth={2}
                          dot={{ r: 4 }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </Card>

              <Card className="lg:col-span-3">
                <CardHeader
                  title="Salary Distribution"
                  subtitle="Accepted offers across CTC tiers"
                />
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={data.salary_distribution}
                      margin={{ top: 10, right: 8, left: -16, bottom: 5 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
                      <XAxis dataKey="bucket_label" stroke={axisTickColor} fontSize={10} />
                      <YAxis stroke={axisTickColor} fontSize={11} allowDecimals={false} />
                      <Tooltip contentStyle={tooltipStyle} />
                      <Bar
                        dataKey="accepted_offer_count"
                        name="Accepted Offers"
                        fill="#0ea5e9"
                        radius={[4, 4, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </Card>

              <Card className="lg:col-span-3">
                <CardHeader
                  title="Recruitment Funnel"
                  subtitle="Stage conversion from applied"
                />
                <div className="space-y-3 mt-1">
                  {data.recruitment_funnel.map((stage) => (
                    <div key={stage.stage_key}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="font-medium text-slate-700 dark:text-slate-300">
                          {stage.stage_label}
                        </span>
                        <span className="font-semibold text-slate-900 dark:text-slate-100">
                          {stage.application_count} ({stage.conversion_from_applied_pct}%)
                        </span>
                      </div>
                      <div className="w-full h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-brand-500 to-emerald-500 transition-all"
                          style={{ width: `${Math.min(100, Math.max(2, stage.conversion_from_applied_pct))}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            </section>

            {/* Year-over-Year Department Comparison Matrix */}
            {data.year_department_comparisons.length > 0 && (
              <Card>
                <CardHeader
                  title="Year-wise Department Comparison"
                  subtitle="Cross-batch placement rate and average compensation by department"
                />
                <div className="overflow-x-auto">
                  <table className="w-full text-xs text-left">
                    <thead>
                      <tr className="border-b border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400">
                        <th className="py-2 pr-3 font-semibold">Academic Year</th>
                        <th className="py-2 px-2 font-semibold">Batch</th>
                        <th className="py-2 px-2 font-semibold">Department</th>
                        <th className="py-2 px-2 font-semibold">Eligible</th>
                        <th className="py-2 px-2 font-semibold">Placed</th>
                        <th className="py-2 px-2 font-semibold">Placement Rate</th>
                        <th className="py-2 pl-2 font-semibold">Avg Package</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                      {data.year_department_comparisons.map((row, idx) => (
                        <tr key={`${row.graduation_year}-${row.department_code}-${idx}`}>
                          <td className="py-2 pr-3 font-medium">{row.academic_year}</td>
                          <td className="py-2 px-2">{row.graduation_year}</td>
                          <td className="py-2 px-2 font-semibold">
                            {row.department_code} — {row.department_name}
                          </td>
                          <td className="py-2 px-2">{row.eligible_students}</td>
                          <td className="py-2 px-2">{row.placed_students}</td>
                          <td className="py-2 px-2">{row.placement_rate_pct}%</td>
                          <td className="py-2 pl-2">{formatLpa(row.average_package_lpa)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            )}

            {/* 4. Statistical Forecasting Engine */}
            <section>
              <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                <h3 className="text-sm font-bold uppercase tracking-wider text-slate-600 dark:text-slate-300 flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-brand-500" />
                  4. Statistical Forecasting Engine ({data.forecasting.target_academic_year})
                </h3>
                <Badge variant="neutral">
                  Sample Horizon: {data.forecasting.overall_sample_years} year(s)
                </Badge>
              </div>

              <div className="mb-4 p-3.5 rounded-xl bg-sky-50/70 dark:bg-sky-950/30 border border-sky-200 dark:border-sky-800/70 text-xs text-sky-900 dark:text-sky-200 flex gap-2.5">
                <Info className="w-4 h-4 text-sky-600 dark:text-sky-400 shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold">Statistical Non-Guarantee Disclaimer: </span>
                  {data.forecasting.disclaimer}
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-5">
                {renderForecastCard(data.forecasting.placement_forecast)}
                {renderForecastCard(data.forecasting.company_participation_forecast)}
                {renderForecastCard(data.forecasting.offer_volume_forecast)}
              </div>

              {data.forecasting.department_forecasts.length > 0 && (
                <Card>
                  <CardHeader
                    title="Department-Wise Hiring & Placement Projections"
                    subtitle={`Statistical projection for ${data.forecasting.target_academic_year} with 95% confidence bounds`}
                  />
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs text-left">
                      <thead>
                        <tr className="border-b border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400">
                          <th className="py-2 pr-3 font-semibold">Department</th>
                          <th className="py-2 px-2 font-semibold">Latest Rate</th>
                          <th className="py-2 px-2 font-semibold">Projected Rate</th>
                          <th className="py-2 px-2 font-semibold">95% CI Range</th>
                          <th className="py-2 px-2 font-semibold">Est. Placed Volume</th>
                          <th className="py-2 px-2 font-semibold">Samples</th>
                          <th className="py-2 px-2 font-semibold">Trend</th>
                          <th className="py-2 pl-2 font-semibold">Confidence</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                        {data.forecasting.department_forecasts.map((df) => (
                          <tr key={df.department_code}>
                            <td className="py-2.5 pr-3 font-semibold text-slate-800 dark:text-slate-200">
                              {df.department_code} — {df.department_name}
                            </td>
                            <td className="py-2.5 px-2">{df.latest_placement_rate_pct}%</td>
                            <td className="py-2.5 px-2 font-bold text-brand-600 dark:text-brand-400">
                              {df.projected_placement_rate_pct}%
                            </td>
                            <td className="py-2.5 px-2">
                              {df.ci_lower_95}% – {df.ci_upper_95}%
                            </td>
                            <td className="py-2.5 px-2">{df.projected_placed_students} students</td>
                            <td className="py-2.5 px-2">{df.sample_size} yr(s)</td>
                            <td className="py-2.5 px-2">
                              <Badge variant={TREND_BADGE[df.trend_direction]}>
                                {df.trend_direction.replace(/_/g, ' ')}
                              </Badge>
                            </td>
                            <td className="py-2.5 pl-2">
                              <Badge variant={CONFIDENCE_BADGE[df.confidence_level]}>
                                {df.confidence_level}
                              </Badge>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card>
              )}
            </section>

            {/* 5. Skill Demand Intelligence */}
            <section>
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-600 dark:text-slate-300 mb-3 flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-brand-500" />
                5. Skill Demand &amp; Outcome Intelligence
              </h3>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                <Card>
                  <CardHeader
                    title="Most Requested & Winning Outcome Skills"
                    subtitle="Job posting frequency and accepted-offer outcomes"
                  />
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs text-left">
                      <thead>
                        <tr className="border-b border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400">
                          <th className="py-2 pr-2 font-semibold">Skill</th>
                          <th className="py-2 px-2 font-semibold">Job Postings</th>
                          <th className="py-2 px-2 font-semibold">Mandatory</th>
                          <th className="py-2 px-2 font-semibold">Accepted Offers</th>
                          <th className="py-2 pl-2 font-semibold">Outcome Rate</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                        {data.skill_intelligence.most_requested_skills.map((sk) => (
                          <tr key={sk.skill_name}>
                            <td className="py-2 pr-2 font-semibold text-slate-800 dark:text-slate-200">
                              {sk.skill_name}
                            </td>
                            <td className="py-2 px-2">{sk.job_postings_count}</td>
                            <td className="py-2 px-2">{sk.mandatory_count}</td>
                            <td className="py-2 px-2 text-emerald-600 dark:text-emerald-400 font-semibold">
                              {sk.accepted_offer_count}
                            </td>
                            <td className="py-2 pl-2">{sk.outcome_success_rate_pct}%</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card>

                <div className="space-y-5">
                  <Card>
                    <CardHeader
                      title="Emerging Skill Requirements"
                      subtitle="Rising demand comparing recent vs prior job cohorts"
                    />
                    {data.skill_intelligence.emerging_skills.length === 0 ? (
                      <p className="text-xs text-slate-500 dark:text-slate-400">
                        Insufficient time-series job postings to isolate emerging skills yet.
                      </p>
                    ) : (
                      <div className="flex flex-wrap gap-2">
                        {data.skill_intelligence.emerging_skills.map((em) => (
                          <div
                            key={em.skill_name}
                            className="px-3 py-1.5 rounded-lg border border-emerald-200 dark:border-emerald-800 bg-emerald-50/70 dark:bg-emerald-950/30 text-xs flex items-center gap-2"
                          >
                            <span className="font-semibold text-emerald-900 dark:text-emerald-200">
                              {em.skill_name}
                            </span>
                            {em.growth_delta_pct !== null && em.growth_delta_pct !== undefined && (
                              <Badge variant="success">+{em.growth_delta_pct}%</Badge>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </Card>

                  <Card>
                    <CardHeader
                      title="Department Skill Coverage & Gaps"
                      subtitle="Student profile skill coverage against demanded skills"
                    />
                    <div className="space-y-3">
                      {data.skill_intelligence.department_skill_gaps.map((g) => (
                        <div
                          key={g.department_code}
                          className="p-2.5 rounded-lg border border-slate-200 dark:border-slate-700/80 text-xs"
                        >
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-semibold text-slate-800 dark:text-slate-200">
                              {g.department_code} — {g.department_name}
                            </span>
                            <Badge variant={g.verified_coverage_pct >= 60 ? 'success' : 'warning'}>
                              {g.verified_coverage_pct}% coverage
                            </Badge>
                          </div>
                          <div className="text-[11px] text-slate-500 dark:text-slate-400">
                            Gaps:{' '}
                            {g.missing_or_low_supply_skills.length > 0
                              ? g.missing_or_low_supply_skills.join(', ')
                              : 'None detected'}
                          </div>
                        </div>
                      ))}
                    </div>
                  </Card>
                </div>
              </div>
            </section>
          </div>
        )
      )}
    </DashboardLayout>
  );
};
