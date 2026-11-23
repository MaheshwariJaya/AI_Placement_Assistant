import React, { useEffect, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Card, CardHeader } from '../common/Card';
import { Badge } from '../common/Badge';
import { Button } from '../common/Button';
import { useTheme } from '../../context/ThemeContext';
import { readinessApi } from '../../services/api';
import { ReadinessCategory, TpoReadinessAnalyticsResponse } from '../../types';
import { AlertCircle, BarChart3, Filter, RefreshCw, ShieldCheck, Users } from 'lucide-react';

const CATEGORY_BADGE: Record<ReadinessCategory, 'success' | 'brand' | 'warning' | 'danger'> = {
  excellent_preparation: 'success',
  placement_ready: 'brand',
  needs_improvement: 'warning',
  requires_significant_preparation: 'danger',
};

export const TpoReadinessPanel: React.FC = () => {
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === 'dark';

  const [data, setData] = useState<TpoReadinessAnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [departmentId, setDepartmentId] = useState<string>('');
  const [graduationYear, setGraduationYear] = useState<string>('');
  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const [skillCategory, setSkillCategory] = useState<string>('');

  const loadAnalytics = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await readinessApi.getTpoAnalytics({
        department_id: departmentId ? Number(departmentId) : undefined,
        graduation_year: graduationYear ? Number(graduationYear) : undefined,
        category: (categoryFilter as ReadinessCategory) || undefined,
        skill_category: skillCategory || undefined,
      });
      setData(res);
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.detail?.message || 'Unable to load cohort readiness analytics.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAnalytics();
  }, [departmentId, graduationYear, categoryFilter, skillCategory]);

  return (
    <div className="space-y-6">
      {/* Transparency & Non-Ranking Policy Banner */}
      <div className="p-4 rounded-xl bg-brand-50 dark:bg-brand-950/40 border border-brand-200 dark:border-brand-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-start gap-2.5 text-xs text-brand-950 dark:text-brand-200">
          <ShieldCheck className="w-4 h-4 text-brand-600 dark:text-brand-400 shrink-0 mt-0.5" />
          <span>
            {data?.transparency_notice ||
              'Institutional Cohort Readiness View: Aggregated preparation metrics are strictly advisory, alphabetically ordered (non-ranking), and do not modify official academic eligibility decisions.'}
          </span>
        </div>
        <Button size="sm" variant="outline" onClick={loadAnalytics} disabled={loading}>
          <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {errorMsg && (
        <div className="p-3.5 rounded-xl bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-200 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Filters */}
      <Card>
        <div className="flex items-center gap-2 text-xs font-bold text-slate-800 dark:text-slate-200 mb-3">
          <Filter className="w-4 h-4 text-brand-600 dark:text-brand-400" />
          Cohort Readiness Filters
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
          <select
            value={departmentId}
            onChange={(e) => setDepartmentId(e.target.value)}
            className="px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100"
          >
            <option value="">All Departments</option>
            {(data?.available_departments ?? []).map((d) => (
              <option key={d.id} value={d.id}>
                {d.label}
              </option>
            ))}
          </select>

          <select
            value={graduationYear}
            onChange={(e) => setGraduationYear(e.target.value)}
            className="px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100"
          >
            <option value="">All Graduation Batches</option>
            {(data?.available_batches ?? []).map((yr) => (
              <option key={yr} value={String(yr)}>
                Batch {yr}
              </option>
            ))}
          </select>

          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100"
          >
            <option value="">All Readiness Categories</option>
            <option value="excellent_preparation">Excellent Preparation (85+)</option>
            <option value="placement_ready">Placement Ready (70-84)</option>
            <option value="needs_improvement">Needs Improvement (50-69)</option>
            <option value="requires_significant_preparation">Requires Significant Prep (&lt;50)</option>
          </select>

          <select
            value={skillCategory}
            onChange={(e) => setSkillCategory(e.target.value)}
            className="px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100"
          >
            <option value="">All Skill Categories</option>
            {(data?.available_skill_categories ?? []).map((sc) => (
              <option key={sc} value={sc}>
                {sc.toUpperCase()}
              </option>
            ))}
          </select>
        </div>
      </Card>

      {/* KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <div className="text-[11px] font-semibold uppercase text-slate-500">Evaluated Cohort</div>
          <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-1">
            {data?.total_students_evaluated ?? '—'}
          </div>
          <p className="text-[11px] text-slate-500 mt-0.5">Institutional active students</p>
        </Card>
        <Card>
          <div className="text-[11px] font-semibold uppercase text-slate-500">Cohort Avg Readiness</div>
          <div className="text-2xl font-bold text-brand-600 dark:text-brand-400 mt-1">
            {data ? `${data.cohort_average_readiness.toFixed(1)} / 100` : '—'}
          </div>
          <p className="text-[11px] text-slate-500 mt-0.5">Formula {data?.formula_version ?? 'v1.0'}</p>
        </Card>
        <Card>
          <div className="text-[11px] font-semibold uppercase text-slate-500">Ready / Excellent Share</div>
          <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-1">
            {data ? `${data.placement_ready_or_above_pct.toFixed(1)}%` : '—'}
          </div>
          <p className="text-[11px] text-slate-500 mt-0.5">
            {data ? `${data.placement_ready_or_above_count} students >= 70 pts` : ''}
          </p>
        </Card>
        <Card>
          <div className="text-[11px] font-semibold uppercase text-slate-500">Profiles With Missing Data</div>
          <div className="text-2xl font-bold text-amber-600 dark:text-amber-400 mt-1">
            {data?.profiles_with_missing_data_count ?? '—'}
          </div>
          <p className="text-[11px] text-slate-500 mt-0.5">Unrecorded sections noted fairly</p>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader title="Readiness by Department" subtitle="Average preparation score per academic branch" />
          <div className="h-[240px]">
            {data && data.department_stats.length > 0 ? (
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={data.department_stats} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={isDark ? '#1e293b' : '#f1f5f9'} />
                  <XAxis dataKey="department_code" tick={{ fill: isDark ? '#94a3b8' : '#64748b', fontSize: 11 }} />
                  <YAxis domain={[0, 100]} tick={{ fill: isDark ? '#94a3b8' : '#64748b', fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{
                      borderRadius: '10px',
                      border: `1px solid ${isDark ? '#334155' : '#e2e8f0'}`,
                      backgroundColor: isDark ? '#0f172a' : '#ffffff',
                      fontSize: '12px',
                    }}
                  />
                  <Bar dataKey="average_readiness_score" fill="#4f46e5" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-slate-400">
                No department readiness records matching filters.
              </div>
            )}
          </div>
        </Card>

        <Card>
          <CardHeader title="Category & Skill Category Coverage" subtitle="Distribution across readiness bands and skill categories" />
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-2.5">
              {(data?.category_distribution ?? []).map((c) => (
                <div key={c.category} className="p-2.5 rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-800/40">
                  <div className="flex items-center justify-between text-[11px] font-bold text-slate-800 dark:text-slate-200">
                    <span>{c.label}</span>
                    <span>{c.student_count}</span>
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">{c.percentage.toFixed(1)}% of filtered cohort</div>
                </div>
              ))}
            </div>
            <div className="pt-2 border-t border-slate-100 dark:border-slate-800">
              <div className="text-[11px] font-semibold text-slate-700 dark:text-slate-300 mb-2">
                Skill Category Coverage
              </div>
              <div className="flex flex-wrap gap-2">
                {(data?.skill_category_stats ?? []).map((sc) => (
                  <span
                    key={sc.skill_category}
                    className="px-2.5 py-1 rounded-full text-[11px] bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 font-medium"
                  >
                    {sc.skill_category}: {sc.cohort_coverage_pct.toFixed(0)}% ({sc.students_with_skill_count} students)
                  </span>
                ))}
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Permitted Alphabetical (Non-Ranking) Student Readiness Overview */}
      <Card>
        <CardHeader
          title="Cohort Preparation Overview (Alphabetical — Advisory Only)"
          subtitle="Permitted institutional staff view; incomplete profiles indicate unrecorded data, not inability"
        />
        <div className="overflow-x-auto max-h-[420px] overflow-y-auto border border-slate-100 dark:border-slate-800 rounded-xl">
          <table className="w-full text-left text-xs border-collapse">
            <thead className="sticky top-0 bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
              <tr className="text-[10px] uppercase text-slate-500 font-semibold">
                <th className="py-2.5 px-3">Student</th>
                <th className="py-2.5 px-3">Branch / Batch</th>
                <th className="py-2.5 px-3">Official CGPA</th>
                <th className="py-2.5 px-3">Readiness Index</th>
                <th className="py-2.5 px-3">Category</th>
                <th className="py-2.5 px-3">Data Completeness Note</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800 bg-white dark:bg-slate-900">
              {(data?.students ?? []).map((st) => (
                <tr key={st.student_id}>
                  <td className="py-2.5 px-3">
                    <div className="font-semibold text-slate-900 dark:text-slate-100">{st.full_name}</div>
                    <div className="text-[10px] text-slate-500 font-mono">{st.roll_number}</div>
                  </td>
                  <td className="py-2.5 px-3">
                    {st.department_code} · {st.graduation_year}
                  </td>
                  <td className="py-2.5 px-3 font-mono">
                    {st.cgpa != null ? st.cgpa.toFixed(2) : '—'} ({st.active_backlogs} BL)
                  </td>
                  <td className="py-2.5 px-3 font-bold text-slate-900 dark:text-slate-100">
                    {st.readiness_score.toFixed(1)} / 100
                  </td>
                  <td className="py-2.5 px-3">
                    <Badge variant={CATEGORY_BADGE[st.category]}>{st.category_label}</Badge>
                  </td>
                  <td className="py-2.5 px-3 text-[11px] text-slate-600 dark:text-slate-400">
                    {st.data_completeness_note}
                  </td>
                </tr>
              ))}
              {(!data || data.students.length === 0) && (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-xs text-slate-400">
                    No institutional student records match the active filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};

