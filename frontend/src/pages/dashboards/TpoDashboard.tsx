import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { DashboardLayout } from '../../components/layout/DashboardLayout';
import { Card, CardHeader } from '../../components/common/Card';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import {
  Users,
  Calendar,
  TrendingUp,
  Award,
  Filter,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  GraduationCap,
  Search,
  Briefcase,
  Clock,
  XCircle,
  FileSpreadsheet,
  AlertTriangle,
  ShieldCheck,
  X,
  Edit,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import { placementApi, userApi, organizationApi } from '../../services/api';
import { useTheme } from '../../context/ThemeContext';
import {
  TpoOverviewResponse,
  TpoStudentRosterResponse,
  TpoStudentRosterItem,
  EligibilitySimulationResponse,
  Department,
} from '../../types';

export const TpoDashboard: React.FC = () => {
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === 'dark';
  const [overview, setOverview] = useState<TpoOverviewResponse | null>(null);
  const [roster, setRoster] = useState<TpoStudentRosterResponse | null>(null);
  const [rosterFilter, setRosterFilter] = useState<'all' | 'unverified' | 'hired' | 'in_pipeline' | 'not_hired'>('all');
  const [rosterDept, setRosterDept] = useState<string>('all');
  const [rosterSearch, setRosterSearch] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Verification & Department State
  const [departments, setDepartments] = useState<Department[]>([]);
  const [verificationModalStudent, setVerificationModalStudent] = useState<TpoStudentRosterItem | null>(null);
  const [verificationDeptId, setVerificationDeptId] = useState<number | ''>('');
  const [verificationCgpa, setVerificationCgpa] = useState<string>('');
  const [verificationActiveBacklogs, setVerificationActiveBacklogs] = useState<string>('0');
  const [verificationTotalBacklogs, setVerificationTotalBacklogs] = useState<string>('0');
  const [verificationReason, setVerificationReason] = useState<string>('Official institutional marksheet and university branch records verified');
  const [isSubmittingVerification, setIsSubmittingVerification] = useState<boolean>(false);
  const [verificationAlert, setVerificationAlert] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Simulator State
  const [targetBatch, setTargetBatch] = useState<number | null>(null);
  const [minCgpa, setMinCgpa] = useState<number>(7.5);
  const [maxBacklogs, setMaxBacklogs] = useState<number>(0);
  const [selectedBranches, setSelectedBranches] = useState<string[]>([]);
  const [simResult, setSimResult] = useState<EligibilitySimulationResponse | null>(null);
  const [isSimulating, setIsSimulating] = useState<boolean>(false);
  const [showStudentList, setShowStudentList] = useState<boolean>(false);

  const availableBranches = overview?.department_stats.map((d) => d.name) ?? [];
  const availableBatches = overview?.available_batches ?? [];

  const fetchDepartments = async () => {
    try {
      const depts = await organizationApi.getDepartments(1);
      setDepartments(depts.filter((d: Department) => d.is_active));
    } catch (err) {
      console.warn('Failed to load departments list:', err);
    }
  };

  const fetchOverview = async () => {
    setLoading(true);
    setError(null);
    try {
      const [data, rosterData] = await Promise.all([
        placementApi.getTpoOverview(),
        placementApi.getTpoStudents(),
      ]);
      setOverview(data);
      setRoster(rosterData);
      const branchCodes = data.department_stats.map((d) => d.name);
      setSelectedBranches((prev) => (prev.length > 0 ? prev : branchCodes));
      runSimulation(targetBatch, minCgpa, maxBacklogs, branchCodes);
    } catch (err: any) {
      console.error('Failed to load TPO overview:', err);
      setError(err?.response?.data?.detail || 'Failed to connect to placement analytics service.');
    } finally {
      setLoading(false);
    }
  };

  const runSimulation = async (
    batch = targetBatch,
    cgpa = minCgpa,
    backlogs = maxBacklogs,
    branches = selectedBranches
  ) => {
    setIsSimulating(true);
    try {
      const result = await placementApi.simulateEligibility({
        target_batch: batch,
        min_cgpa: cgpa,
        max_active_backlogs: backlogs,
        department_codes: branches.length > 0 ? branches : null,
      });
      setSimResult(result);
    } catch (err: any) {
      console.error('Eligibility simulation query failed:', err);
    } finally {
      setIsSimulating(false);
    }
  };

  useEffect(() => {
    fetchOverview();
    fetchDepartments();
  }, []);

  const handleOpenVerification = (st: TpoStudentRosterItem) => {
    setVerificationModalStudent(st);
    const matchDept = departments.find(
      (d) => d.id === st.department_id || d.code.toUpperCase() === st.department_code.toUpperCase() || d.name === st.department_name
    );
    setVerificationDeptId(matchDept ? matchDept.id : (departments[0]?.id || ''));
    setVerificationCgpa(st.cgpa != null ? String(st.cgpa) : '8.50');
    setVerificationActiveBacklogs(String(st.active_backlogs ?? 0));
    setVerificationTotalBacklogs(String(st.total_backlogs ?? 0));
    setVerificationReason('Official institutional marksheet and university branch records verified');
    setVerificationAlert(null);
  };

  const handleSaveVerification = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!verificationModalStudent || !verificationDeptId) return;

    setIsSubmittingVerification(true);
    setVerificationAlert(null);
    try {
      await userApi.tpoUpdateStudentBranch(
        verificationModalStudent.student_id,
        Number(verificationDeptId),
        verificationReason.trim() || 'Official institutional marksheet verified',
        {
          cgpa: parseFloat(verificationCgpa) || undefined,
          active_backlogs: parseInt(verificationActiveBacklogs, 10),
          total_backlogs: parseInt(verificationTotalBacklogs, 10),
        }
      );
      setVerificationAlert({
        type: 'success',
        message: `Successfully verified official academic record for ${verificationModalStudent.full_name}!`,
      });
      // Refresh roster data
      const updatedRoster = await placementApi.getTpoStudents();
      setRoster(updatedRoster);
      setTimeout(() => {
        setVerificationModalStudent(null);
        setVerificationAlert(null);
      }, 1000);
    } catch (err: any) {
      console.error('Failed to verify student academic record:', err);
      setVerificationAlert({
        type: 'error',
        message: err?.response?.data?.detail || 'Failed to update student official academic branch.',
      });
    } finally {
      setIsSubmittingVerification(false);
    }
  };

  const toggleBranch = (branch: string) => {
    if (selectedBranches.includes(branch)) {
      if (selectedBranches.length > 1) {
        setSelectedBranches(selectedBranches.filter((b) => b !== branch));
      }
    } else {
      setSelectedBranches([...selectedBranches, branch]);
    }
  };

  return (
    <DashboardLayout
      role="tpo"
      title="Training & Placement Officer (TPO) Command Center"
      subtitle="Institutional Scope: Monitor campus recruitment drives, student eligibility, and placement statistics."
    >
      {/* Top Banner & Refresh */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
          <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
            MBM University Recruitment Intelligence
          </span>
          <Badge variant="neutral" className="text-[10px] font-mono">
            Live Database Synced
          </Badge>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => {
              setRosterFilter('unverified');
              const el = document.getElementById('student-roster-section');
              if (el) el.scrollIntoView({ behavior: 'smooth' });
            }}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-amber-500/15 hover:bg-amber-500/25 text-amber-700 dark:text-amber-300 border border-amber-300 dark:border-amber-700/80 transition-colors cursor-pointer"
          >
            <ShieldCheck className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
            <span>Verify Students</span>
            {(roster?.unverified_count ?? 0) > 0 && (
              <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-amber-600 text-white font-bold">
                {roster?.unverified_count}
              </span>
            )}
          </button>
          <Link to="/tpo/drives">
            <Button size="sm" variant="primary" className="text-xs flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5" />
              Manage Placement Drives
            </Button>
          </Link>
          <Link to="/tpo/reports">
            <Button size="sm" variant="outline" className="text-xs flex items-center gap-1.5">
              <FileSpreadsheet className="w-3.5 h-3.5 text-brand-600 dark:text-brand-400" />
              Placement Reports
            </Button>
          </Link>
          <Link to="/tpo/intelligence">
            <Button size="sm" variant="outline" className="text-xs flex items-center gap-1.5">
              <TrendingUp className="w-3.5 h-3.5" />
              Intelligence & Forecasting
            </Button>
          </Link>
          <Link to="/tpo/readiness">
            <Button size="sm" variant="outline" className="text-xs flex items-center gap-1.5">
              <TrendingUp className="w-3.5 h-3.5" />
              Cohort Readiness Analytics
            </Button>
          </Link>
          <Button
            size="sm"
            variant="outline"
            onClick={() => {
              fetchOverview();
              runSimulation();
            }}
            disabled={loading || isSimulating}
            className="text-xs flex items-center gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh Stats
          </Button>
        </div>
      </div>

      {error && (
        <div className="p-4 mb-6 rounded-xl bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-200 text-xs flex items-center justify-between">
          <span>{error}</span>
          <Button size="sm" variant="outline" onClick={fetchOverview}>
            Retry
          </Button>
        </div>
      )}

      {/* KPI Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Card>
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Total Eligible Cohort
            </span>
            <span className="w-8 h-8 rounded-lg bg-brand-50 dark:bg-brand-950/60 text-brand-600 dark:text-brand-400 flex items-center justify-center">
              <Users className="w-4 h-4" />
            </span>
          </div>
          <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-2">
            {overview ? overview.total_cohort : '...'}
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
            {overview ? overview.target_batch : 'Verified Students'}
          </p>
        </Card>

        <Card>
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Overall Placement Rate
            </span>
            <span className="w-8 h-8 rounded-lg bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 flex items-center justify-center">
              <TrendingUp className="w-4 h-4" />
            </span>
          </div>
          <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-2">
            {overview ? `${overview.placement_rate}%` : '...'}
          </div>
          <p className="text-[11px] text-emerald-600 dark:text-emerald-400 mt-1">
            {overview ? `${overview.placed_students} Students Placed` : 'Loading offers...'}
          </p>
        </Card>

        <Card>
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Active Drives
            </span>
            <span className="w-8 h-8 rounded-lg bg-sky-50 dark:bg-sky-950/60 text-sky-600 dark:text-sky-400 flex items-center justify-center">
              <Calendar className="w-4 h-4" />
            </span>
          </div>
          <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-2">
            {overview ? overview.active_drives : '...'}
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
            {overview
              ? `${overview.published_jobs ?? 0} published roles (${overview.visiting_this_week} closing this week)`
              : 'Live campus drives'}
          </p>
        </Card>

        <Card>
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Average Package
            </span>
            <span className="w-8 h-8 rounded-lg bg-amber-50 dark:bg-amber-950/60 text-amber-600 dark:text-amber-400 flex items-center justify-center">
              <Award className="w-4 h-4" />
            </span>
          </div>
          <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-2">
            {overview ? `${overview.average_package_lpa} LPA` : '...'}
          </div>
          <p className="text-[11px] text-amber-600 dark:text-amber-400 mt-1">
            {overview
              ? overview.placed_students > 0
                ? `Highest offered: ${overview.highest_package_lpa} LPA`
                : overview.top_open_ctc_lpa && overview.top_open_ctc_lpa > 0
                ? `No offers yet · Top open: ${overview.top_open_ctc_lpa} LPA`
                : 'No offers extended yet'
              : 'Verified CTC'}
          </p>
        </Card>
      </div>

      {/* Analytics Chart & Interactive Simulator */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <div className="lg:col-span-2">
          <Card className="h-full flex flex-col justify-between">
            <CardHeader
              title="Department-Wise Placement Rate (%)"
              subtitle="Live branch performance computed from verified student offer outcomes"
            />
            <div className="min-h-[270px] w-full pt-2">
              {overview?.department_stats && overview.department_stats.length > 0 ? (
                <ResponsiveContainer width="100%" height={270}>
                  <BarChart
                    data={overview.department_stats}
                    margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={isDark ? '#334155' : '#E2E8F0'} />
                    <XAxis
                      dataKey="name"
                      stroke={isDark ? '#94A3B8' : '#64748B'}
                      fontSize={12}
                      tickLine={false}
                    />
                    <YAxis
                      stroke={isDark ? '#94A3B8' : '#64748B'}
                      fontSize={12}
                      tickLine={false}
                      unit="%"
                      domain={[0, 100]}
                    />
                    <Tooltip
                      cursor={{ fill: isDark ? '#1E293B' : '#F1F5F9' }}
                      contentStyle={{
                        backgroundColor: isDark ? '#0F172A' : '#FFFFFF',
                        borderRadius: '8px',
                        border: isDark ? '1px solid #334155' : '1px solid #E2E8F0',
                        color: isDark ? '#F1F5F9' : '#0F172A',
                        fontSize: '12px',
                        boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
                      }}
                      formatter={(val: any, _name: any, item: any) => [
                        `${val}% (${item.payload.placed_count} / ${item.payload.total} placed)`,
                        'Placement Rate',
                      ]}
                      labelFormatter={(label) => {
                        const dept = overview.department_stats.find((d) => d.name === label);
                        return dept ? `${label} - ${dept.dept_name}` : label;
                      }}
                    />
                    <Bar
                      dataKey="placed"
                      fill={isDark ? '#6366F1' : '#4F46E5'}
                      radius={[4, 4, 0, 0]}
                      name="Placement %"
                    />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-slate-400 dark:text-slate-500 text-xs">
                  {loading ? 'Computing department rates...' : 'No department data available'}
                </div>
              )}
            </div>
          </Card>
        </div>

        {/* Interactive Student Eligibility Simulator */}
        <div>
          <Card className="h-full">
            <CardHeader
              title="Student Eligibility Simulator"
              subtitle="Deterministic pre-drive query builder"
            />
            <div className="space-y-3.5 text-xs">
              {/* Form Controls */}
              <div className="p-3 bg-slate-50 dark:bg-slate-800/70 rounded-xl border border-slate-200/80 dark:border-slate-700 space-y-3">
                {/* Target Batch */}
                <div className="flex items-center justify-between">
                  <label htmlFor="target-batch-select" className="text-slate-600 dark:text-slate-300 font-medium">Target Batch:</label>
                  <select
                    id="target-batch-select"
                    value={targetBatch ?? ''}
                    onChange={(e) => setTargetBatch(e.target.value ? Number(e.target.value) : null)}
                    className="border border-slate-200 dark:border-slate-700 rounded-md px-2 py-1 text-xs bg-white dark:bg-slate-900 font-semibold text-slate-800 dark:text-slate-100 focus:outline-hidden focus:ring-1 focus:ring-brand-500"
                  >
                    <option value="">All Batches</option>
                    {availableBatches.map((yr) => (
                      <option key={yr} value={yr}>
                        Class of {yr}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Min CGPA Cutoff */}
                <div className="flex items-center justify-between">
                  <label htmlFor="min-cgpa-input" className="text-slate-600 dark:text-slate-300 font-medium">Min CGPA Cutoff:</label>
                  <div className="flex items-center gap-1">
                    <span className="text-slate-400 dark:text-slate-500 text-[11px]">&gt;=</span>
                    <input
                      id="min-cgpa-input"
                      type="number"
                      step="0.1"
                      min="0"
                      max="10"
                      value={minCgpa}
                      onChange={(e) => setMinCgpa(Number(e.target.value))}
                      className="w-16 border border-slate-200 dark:border-slate-700 rounded-md px-2 py-1 text-xs text-right font-semibold text-slate-800 dark:text-slate-100 bg-white dark:bg-slate-900 focus:outline-hidden focus:ring-1 focus:ring-brand-500"
                    />
                  </div>
                </div>

                {/* Max Active Backlogs */}
                <div className="flex items-center justify-between">
                  <label htmlFor="max-backlogs-select" className="text-slate-600 dark:text-slate-300 font-medium">Max Backlogs:</label>
                  <select
                    id="max-backlogs-select"
                    value={maxBacklogs}
                    onChange={(e) => setMaxBacklogs(Number(e.target.value))}
                    className="border border-slate-200 dark:border-slate-700 rounded-md px-2 py-1 text-xs bg-white dark:bg-slate-900 font-semibold text-slate-800 dark:text-slate-100 focus:outline-hidden focus:ring-1 focus:ring-brand-500"
                  >
                    <option value="0">0 (Zero tolerance)</option>
                    <option value="1">At most 1</option>
                    <option value="2">At most 2</option>
                  </select>
                </div>

                {/* Branch Selection Pills */}
                <div>
                  <div className="text-slate-600 dark:text-slate-300 font-medium mb-1.5 flex items-center justify-between">
                    <span>Branches:</span>
                    <span className="text-[10px] text-slate-400 dark:text-slate-500">
                      {selectedBranches.length} of {availableBranches.length} selected
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {availableBranches.length === 0 ? (
                      <span className="text-[10px] text-slate-400">Loading departments...</span>
                    ) : (
                      availableBranches.map((b) => {
                        const isSel = selectedBranches.includes(b);
                        return (
                          <button
                            key={b}
                            type="button"
                            onClick={() => toggleBranch(b)}
                            className={`px-2 py-0.5 rounded text-[10px] font-semibold transition-colors ${
                              isSel
                                ? 'bg-brand-600 text-white shadow-xs'
                                : 'bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
                            }`}
                          >
                            {b}
                          </button>
                        );
                      })
                    )}
                  </div>
                </div>
              </div>

              {/* Simulation Result Card */}
              <div className="p-3.5 bg-emerald-50 dark:bg-emerald-950/50 rounded-xl border border-emerald-200 dark:border-emerald-800 text-center">
                <div className="text-2xl font-bold text-emerald-800 dark:text-emerald-200">
                  {simResult ? `${simResult.eligible_count} Students` : '...'}
                </div>
                <div className="text-[11px] text-emerald-700 dark:text-emerald-300 mt-0.5 font-medium">
                  {simResult
                    ? `${simResult.eligible_percentage}% of ${simResult.total_cohort_count} students qualify`
                    : 'Awaiting simulation query'}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="space-y-2">
                <Button
                  size="sm"
                  variant="primary"
                  className="w-full text-xs flex items-center justify-center gap-1.5"
                  onClick={() => runSimulation()}
                  disabled={isSimulating}
                >
                  <Filter className={`w-3.5 h-3.5 ${isSimulating ? 'animate-spin' : ''}`} />
                  {isSimulating ? 'Simulating Cohort...' : 'Run Simulation Query'}
                </Button>

                {simResult && simResult.matching_students.length > 0 && (
                  <Button
                    size="sm"
                    variant="outline"
                    className="w-full text-xs flex items-center justify-center gap-1"
                    onClick={() => setShowStudentList(!showStudentList)}
                  >
                    {showStudentList ? (
                      <>
                        <ChevronUp className="w-3.5 h-3.5" />
                        Hide Candidate List ({simResult.matching_students.length})
                      </>
                    ) : (
                      <>
                        <ChevronDown className="w-3.5 h-3.5" />
                        View Qualified Candidates ({simResult.matching_students.length})
                      </>
                    )}
                  </Button>
                )}
              </div>
            </div>
          </Card>
        </div>
      </div>

      {/* Expandable Candidate Drawer */}
      {showStudentList && simResult && simResult.matching_students.length > 0 && (
        <Card className="mb-6">
          <CardHeader
            title={`Qualified Students (${simResult.matching_students.length} Candidates)`}
            subtitle={`Students meeting: CGPA >= ${minCgpa}, Max Backlogs <= ${maxBacklogs}, Branches: ${selectedBranches.join(', ')}`}
          />
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/70 text-slate-500 dark:text-slate-400 font-semibold uppercase text-[10px] tracking-wider">
                  <th className="py-2.5 px-3">Student Name</th>
                  <th className="py-2.5 px-3">Roll Number</th>
                  <th className="py-2.5 px-3">Branch</th>
                  <th className="py-2.5 px-3">CGPA</th>
                  <th className="py-2.5 px-3">Backlogs</th>
                  <th className="py-2.5 px-3">Top Skills</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {simResult.matching_students.map((st) => (
                  <tr key={st.student_id} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/50 transition-colors">
                    <td className="py-2.5 px-3 font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                      <GraduationCap className="w-4 h-4 text-brand-600 dark:text-brand-400 shrink-0" />
                      <div>
                        <div>{st.name}</div>
                        <div className="text-[10px] text-slate-400 dark:text-slate-500 font-normal">{st.email}</div>
                      </div>
                    </td>
                    <td className="py-2.5 px-3 font-mono text-slate-600 dark:text-slate-400">{st.roll_number}</td>
                    <td className="py-2.5 px-3">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                        {st.department}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 font-bold text-slate-800 dark:text-slate-200">{st.cgpa.toFixed(2)}</td>
                    <td className="py-2.5 px-3">
                      {st.active_backlogs === 0 ? (
                        <span className="text-emerald-600 dark:text-emerald-400 font-medium flex items-center gap-1">
                          <CheckCircle2 className="w-3.5 h-3.5" /> 0
                        </span>
                      ) : (
                        <span className="text-amber-600 dark:text-amber-400 font-medium">{st.active_backlogs}</span>
                      )}
                    </td>
                    <td className="py-2.5 px-3">
                      <div className="flex flex-wrap gap-1 max-w-xs">
                        {st.skills.slice(0, 3).map((sk) => (
                          <span
                            key={sk}
                            className="px-1.5 py-0.5 rounded text-[9px] bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 font-medium"
                          >
                            {sk}
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
      )}

      {/* Institutional Student Cohort & Placement Outcomes Roster */}
      <div id="student-roster-section" className="mb-6">
      <Card>
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 pb-4 mb-4 border-b border-slate-200 dark:border-slate-800">
          <div>
            <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <Users className="w-4 h-4 text-brand-600 dark:text-brand-400" />
              <span>Student Cohort &amp; Placement Outcomes</span>
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Live institutional directory showing hired offers, active interview pipelines, and official academic branch verification.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-1.5 text-xs">
            {(
              [
                { id: 'all' as const, label: `All (${roster?.total_students ?? 0})`, isWarning: false },
                {
                  id: 'unverified' as const,
                  label: `Needs Verification (${roster?.unverified_count ?? 0})`,
                  isWarning: (roster?.unverified_count ?? 0) > 0,
                },
                { id: 'hired' as const, label: `Hired (${roster?.hired_count ?? 0})`, isWarning: false },
                { id: 'in_pipeline' as const, label: `In Pipeline (${roster?.in_pipeline_count ?? 0})`, isWarning: false },
                { id: 'not_hired' as const, label: `Not Hired (${roster?.not_hired_count ?? 0})`, isWarning: false },
              ]
            ).map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setRosterFilter(tab.id)}
                className={`px-3 py-1.5 rounded-lg font-semibold border transition-colors flex items-center gap-1.5 cursor-pointer ${
                  rosterFilter === tab.id
                    ? 'bg-slate-900 dark:bg-brand-600 text-white border-slate-900 dark:border-brand-600'
                    : tab.isWarning
                    ? 'bg-amber-50 dark:bg-amber-950/40 text-amber-800 dark:text-amber-300 border-amber-200 dark:border-amber-800 hover:bg-amber-100'
                    : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800'
                }`}
              >
                {tab.id === 'unverified' && <AlertTriangle className="w-3.5 h-3.5 text-amber-500 shrink-0" />}
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Unverified Students Notice Banner */}
        {(roster?.unverified_count ?? 0) > 0 && (
          <div className="mb-4 p-3.5 rounded-xl bg-amber-50/90 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-start sm:items-center gap-2.5">
              <span className="p-1.5 rounded-lg bg-amber-100 dark:bg-amber-900/60 text-amber-700 dark:text-amber-300 shrink-0">
                <AlertTriangle className="w-4 h-4" />
              </span>
              <div>
                <div className="text-xs font-bold text-amber-900 dark:text-amber-200">
                  {roster?.unverified_count} Student{roster?.unverified_count === 1 ? '' : 's'} Pending Official Academic Verification
                </div>
                <div className="text-[11px] text-amber-700 dark:text-amber-300/90">
                  Students without an authorized academic branch cannot be matched accurately to company eligibility criteria. Click "Verify Student" in the roster below to confirm official records.
                </div>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setRosterFilter('unverified')}
              className="text-xs px-3 py-1.5 font-semibold rounded-lg bg-amber-600 hover:bg-amber-700 text-white transition-colors shrink-0 shadow-2xs cursor-pointer"
            >
              Filter Unverified ({roster?.unverified_count})
            </button>
          </div>
        )}

        {/* Search & Branch Controls */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <div className="relative flex-1 max-w-md">
            <Search className="w-4 h-4 text-slate-400 dark:text-slate-500 absolute left-3 top-2.5" />
            <input
              type="text"
              value={rosterSearch}
              onChange={(e) => setRosterSearch(e.target.value)}
              placeholder="Search student, roll number, skill, or hired company..."
              className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50/70 dark:bg-slate-800/70 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-hidden focus:ring-1 focus:ring-brand-500"
            />
          </div>

          <div className="flex items-center gap-2 text-xs">
            <select
              value={rosterDept}
              onChange={(e) => setRosterDept(e.target.value)}
              className="border border-slate-200 dark:border-slate-700 rounded-lg px-2.5 py-2 text-xs bg-white dark:bg-slate-900 font-medium text-slate-700 dark:text-slate-200"
            >
              <option value="all">All Branches</option>
              {availableBranches.map((b) => (
                <option key={b} value={b}>
                  {b}
                </option>
              ))}
            </select>
            {roster && (
              <span className="text-[11px] text-slate-500 dark:text-slate-400 whitespace-nowrap">
                {roster.offer_accepted_count} Accepted · {roster.offer_pending_count} Pending Offer
              </span>
            )}
          </div>
        </div>

        {/* Roster Table */}
        {(() => {
          const q = rosterSearch.trim().toLowerCase();
          const filteredRoster = (roster?.students ?? []).filter((s) => {
            const matchStatus =
              rosterFilter === 'all'
                ? true
                : rosterFilter === 'unverified'
                ? !s.is_branch_verified || s.department_code === 'GEN'
                : s.placement_status === rosterFilter;
            const matchDept = rosterDept === 'all' || s.department_code === rosterDept;
            const matchSearch =
              !q ||
              s.full_name.toLowerCase().includes(q) ||
              s.roll_number.toLowerCase().includes(q) ||
              s.email.toLowerCase().includes(q) ||
              (s.hired_company || '').toLowerCase().includes(q) ||
              (s.hired_role || '').toLowerCase().includes(q) ||
              s.skills.some((sk) => sk.toLowerCase().includes(q));
            return matchStatus && matchDept && matchSearch;
          });

          if (!roster) {
            return (
              <div className="py-10 text-center text-xs text-slate-400 dark:text-slate-500">
                Loading cohort placement records...
              </div>
            );
          }
          if (filteredRoster.length === 0) {
            return (
              <div className="py-10 text-center text-xs text-slate-500 dark:text-slate-400">
                No student records match the current filter criteria.
              </div>
            );
          }

          return (
            <div className="overflow-x-auto max-h-[460px] overflow-y-auto border border-slate-100 dark:border-slate-800 rounded-xl">
              <table className="w-full text-left text-xs border-collapse">
                <thead className="sticky top-0 bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 z-10">
                  <tr className="text-slate-500 dark:text-slate-400 font-semibold uppercase text-[10px] tracking-wider">
                    <th className="py-2.5 px-3">Student</th>
                    <th className="py-2.5 px-3">Branch / Batch</th>
                    <th className="py-2.5 px-3">Verification</th>
                    <th className="py-2.5 px-3">CGPA / Backlogs</th>
                    <th className="py-2.5 px-3">Verified Skills</th>
                    <th className="py-2.5 px-3">Apps</th>
                    <th className="py-2.5 px-3">Placement Outcome</th>
                    <th className="py-2.5 px-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800 bg-white dark:bg-slate-900">
                  {filteredRoster.map((st) => (
                    <tr key={st.student_id} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/50 transition-colors">
                      <td className="py-2.5 px-3">
                        <div className="font-semibold text-slate-900 dark:text-slate-100">{st.full_name}</div>
                        <div className="text-[10px] text-slate-500 dark:text-slate-400 font-mono">
                          {st.roll_number} · {st.email}
                        </div>
                      </td>
                      <td className="py-2.5 px-3">
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                          {st.department_code}
                        </span>
                        <span className="text-[11px] text-slate-500 dark:text-slate-400 ml-1.5">{st.graduation_year}</span>
                      </td>
                      <td className="py-2.5 px-3">
                        {st.is_branch_verified && st.department_code !== 'GEN' ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                            <CheckCircle2 className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
                            Verified
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-700 animate-pulse">
                            <AlertTriangle className="w-3 h-3 text-amber-600 dark:text-amber-400" />
                            Needs Verification
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 px-3">
                        <span className="font-bold text-slate-800 dark:text-slate-200">{st.cgpa.toFixed(2)}</span>
                        <span
                          className={`ml-2 text-[10px] font-medium ${
                            st.active_backlogs === 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'
                          }`}
                        >
                          ({st.active_backlogs} BL)
                        </span>
                      </td>
                      <td className="py-2.5 px-3">
                        <div className="flex flex-wrap gap-1 max-w-[220px]">
                          {st.skills.slice(0, 3).map((sk) => (
                            <span
                              key={sk}
                              className="px-1.5 py-0.5 rounded text-[10px] bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 font-medium"
                            >
                              {sk}
                            </span>
                          ))}
                          {st.skills.length > 3 && (
                            <span className="text-[10px] text-slate-400 dark:text-slate-500">+{st.skills.length - 3}</span>
                          )}
                        </div>
                      </td>
                      <td className="py-2.5 px-3 font-semibold text-slate-700 dark:text-slate-300">
                        {st.applications_count}
                      </td>
                      <td className="py-2.5 px-3">
                        {st.placement_status === 'hired' ? (
                          <div className="space-y-0.5">
                            <div className="flex items-center gap-1.5">
                              <Badge variant={st.offer_state === 'offer_accepted' ? 'success' : 'brand'}>
                                {st.offer_state === 'offer_accepted' ? 'Hired · Accepted' : 'Offer Extended'}
                              </Badge>
                              {st.hired_ctc_lpa != null && (
                                <span className="font-bold text-emerald-700 dark:text-emerald-400 text-[11px]">
                                  ₹{st.hired_ctc_lpa.toFixed(1)} LPA
                                </span>
                              )}
                            </div>
                            <div className="text-[11px] text-slate-700 dark:text-slate-300 font-medium flex items-center gap-1">
                              <Briefcase className="w-3 h-3 text-slate-400 dark:text-slate-500 shrink-0" />
                              <span>
                                {st.hired_company} — {st.hired_role}
                              </span>
                            </div>
                          </div>
                        ) : st.placement_status === 'in_pipeline' ? (
                          <div className="space-y-0.5">
                            <Badge variant="warning" className="inline-flex items-center gap-1">
                              <Clock className="w-3 h-3" />
                              {st.offer_state.replace(/_/g, ' ').toUpperCase()}
                            </Badge>
                            {st.active_pipeline_roles[0] && (
                              <div className="text-[10px] text-slate-500 dark:text-slate-400 truncate max-w-[230px]">
                                {st.active_pipeline_roles[0]}
                              </div>
                            )}
                          </div>
                        ) : (
                          <Badge variant={st.offer_state === 'unapplied' ? 'neutral' : 'danger'} className="inline-flex items-center gap-1">
                            {st.offer_state !== 'unapplied' && <XCircle className="w-3 h-3" />}
                            {st.offer_state === 'unapplied'
                              ? 'Not Hired · Unapplied'
                              : `Not Hired · ${st.offer_state.replace(/_/g, ' ').toUpperCase()}`}
                          </Badge>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        <button
                          type="button"
                          onClick={() => handleOpenVerification(st)}
                          className={`inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-semibold rounded-md transition-colors cursor-pointer ${
                            !st.is_branch_verified || st.department_code === 'GEN'
                              ? 'bg-amber-500 hover:bg-amber-600 text-white shadow-xs'
                              : 'bg-brand-50 hover:bg-brand-100 text-brand-700 dark:bg-brand-950/60 dark:hover:bg-brand-900/60 dark:text-brand-300 border border-brand-200 dark:border-brand-800'
                          }`}
                        >
                          {!st.is_branch_verified || st.department_code === 'GEN' ? (
                            <>
                              <ShieldCheck className="w-3 h-3" />
                              Verify Student
                            </>
                          ) : (
                            <>
                              <Edit className="w-3 h-3" />
                              Edit Branch
                            </>
                          )}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        })()}
      </Card>
      </div>

      {/* Student Academic Record Verification Modal */}
      {verificationModalStudent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
          <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-800 max-w-lg w-full p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
              <div className="flex items-center gap-2.5">
                <span className="p-2 rounded-xl bg-brand-50 dark:bg-brand-950/70 text-brand-600 dark:text-brand-400">
                  <ShieldCheck className="w-5 h-5" />
                </span>
                <div>
                  <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                    Verify Student Academic Record
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Authoritative TPO branch verification and cutoff record audit.
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setVerificationModalStudent(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {verificationAlert && (
              <div
                className={`p-3 rounded-lg text-xs font-medium flex items-center gap-2 ${
                  verificationAlert.type === 'success'
                    ? 'bg-emerald-50 text-emerald-800 border border-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-200 dark:border-emerald-800'
                    : 'bg-rose-50 text-rose-800 border border-rose-200 dark:bg-rose-950/60 dark:text-rose-200 dark:border-rose-800'
                }`}
              >
                {verificationAlert.type === 'success' ? (
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                ) : (
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                )}
                <span>{verificationAlert.message}</span>
              </div>
            )}

            {/* Target Student Identity Pill */}
            <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/80 dark:border-slate-700/80">
              <div className="text-xs font-bold text-slate-900 dark:text-slate-100">
                {verificationModalStudent.full_name}
              </div>
              <div className="text-[11px] text-slate-500 dark:text-slate-400 flex flex-wrap gap-x-3 gap-y-0.5 mt-0.5 font-mono">
                <span>Roll: {verificationModalStudent.roll_number}</span>
                <span>Email: {verificationModalStudent.email}</span>
                <span>Batch: {verificationModalStudent.graduation_year}</span>
              </div>
              <div className="mt-1.5 flex items-center gap-2 text-[11px]">
                <span className="text-slate-500 dark:text-slate-400">Current Status:</span>
                {verificationModalStudent.is_branch_verified && verificationModalStudent.department_code !== 'GEN' ? (
                  <Badge variant="success" className="text-[10px]">
                    Verified ({verificationModalStudent.department_name})
                  </Badge>
                ) : (
                  <Badge variant="warning" className="text-[10px]">
                    Unverified ({verificationModalStudent.department_name})
                  </Badge>
                )}
              </div>
            </div>

            <form onSubmit={handleSaveVerification} className="space-y-3.5">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Official Academic Department &amp; Branch *
                </label>
                <select
                  value={verificationDeptId}
                  onChange={(e) => setVerificationDeptId(Number(e.target.value))}
                  required
                  className="w-full text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-slate-900 dark:text-slate-100 font-medium focus:ring-2 focus:ring-brand-500"
                >
                  <option value="" disabled>Select official department...</option>
                  {departments.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name} ({d.code})
                    </option>
                  ))}
                </select>
                <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-1">
                  This binds the student's authoritative department in institutional records.
                </p>
              </div>

              <div className="grid grid-cols-3 gap-2.5">
                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Official CGPA
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    max="10"
                    value={verificationCgpa}
                    onChange={(e) => setVerificationCgpa(e.target.value)}
                    required
                    className="w-full text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-2.5 py-1.5 text-slate-900 dark:text-slate-100 font-mono font-bold focus:ring-1 focus:ring-brand-500"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Active Backlogs
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="30"
                    value={verificationActiveBacklogs}
                    onChange={(e) => setVerificationActiveBacklogs(e.target.value)}
                    required
                    className="w-full text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-2.5 py-1.5 text-slate-900 dark:text-slate-100 font-mono focus:ring-1 focus:ring-brand-500"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Total Backlogs
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="50"
                    value={verificationTotalBacklogs}
                    onChange={(e) => setVerificationTotalBacklogs(e.target.value)}
                    required
                    className="w-full text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-2.5 py-1.5 text-slate-900 dark:text-slate-100 font-mono focus:ring-1 focus:ring-brand-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Verification Note / Reason *
                </label>
                <textarea
                  value={verificationReason}
                  onChange={(e) => setVerificationReason(e.target.value)}
                  required
                  rows={2}
                  placeholder="e.g. Verified against university registrar marksheet and semester grade card"
                  className="w-full text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-2.5 py-1.5 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:ring-1 focus:ring-brand-500"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100 dark:border-slate-800">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setVerificationModalStudent(null)}
                  disabled={isSubmittingVerification}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  size="sm"
                  disabled={isSubmittingVerification || !verificationDeptId}
                  className="flex items-center gap-1.5"
                >
                  <ShieldCheck className="w-3.5 h-3.5" />
                  {isSubmittingVerification ? 'Authorizing & Saving...' : 'Confirm & Authorize Verification'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
};
