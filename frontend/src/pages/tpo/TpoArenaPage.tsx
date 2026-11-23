import React, { useEffect, useState } from 'react';
import { DashboardLayout } from '../../components/layout/DashboardLayout';
import { Card, CardHeader } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { arenaApi, orgApi } from '../../services/api';
import {
  ArenaAssessmentSummary,
  ArenaCategory,
  ArenaDifficulty,
  ArenaPerformanceAnalytics,
  ArenaQuestionView,
  ArenaStudentPerformanceItem,
  ArenaTopicProficiencyItem,
  ArenaTpoAnalyticsResponse,
  ArenaTpoStudentRosterResponse,
  Department,
} from '../../types';
import { useAuth } from '../../context/AuthContext';
import {
  BarChart3,
  CheckCircle2,
  FilePlus2,
  Layers,
  PlusCircle,
  Users,
  Search,
  Award,
  Activity,
  ChevronRight,
  GraduationCap,
  X,
  Target,
  Filter,
  AlertCircle,
  Clock,
} from 'lucide-react';

const CATEGORY_OPTIONS: { value: ArenaCategory; label: string }[] = [
  { value: 'dsa', label: 'Data Structures & Algorithms' },
  { value: 'programming_fundamentals', label: 'Programming Fundamentals' },
  { value: 'dbms', label: 'Database Management Systems' },
  { value: 'operating_systems', label: 'Operating Systems' },
  { value: 'computer_networks', label: 'Computer Networks' },
  { value: 'oop', label: 'Object-Oriented Programming' },
  { value: 'aptitude_logical', label: 'Aptitude & Logical Reasoning' },
  { value: 'quantitative', label: 'Quantitative Ability' },
  { value: 'verbal', label: 'Verbal Ability' },
  { value: 'technical_mcqs', label: 'Technical MCQs' },
  { value: 'hr_behavioral', label: 'HR & Behavioral Preparation' },
];

export const TpoArenaPage: React.FC = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<'roster' | 'management'>('roster');

  // Aggregated analytics & configs
  const [analytics, setAnalytics] = useState<ArenaTpoAnalyticsResponse | null>(null);
  const [assessments, setAssessments] = useState<ArenaAssessmentSummary[]>([]);
  const [questions, setQuestions] = useState<ArenaQuestionView[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Student Roster State
  const [rosterData, setRosterData] = useState<ArenaTpoStudentRosterResponse | null>(null);
  const [loadingRoster, setLoadingRoster] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDeptId, setSelectedDeptId] = useState<string>('');
  const [selectedBatch, setSelectedBatch] = useState<string>('');
  const [participationFilter, setParticipationFilter] = useState<'all' | 'participating' | 'not_started'>('all');

  // Diagnostic Detail Modal State
  const [selectedStudent, setSelectedStudent] = useState<ArenaStudentPerformanceItem | null>(null);
  const [studentDetail, setStudentDetail] = useState<ArenaPerformanceAnalytics | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // Create Assessment Form
  const [assessTitle, setAssessTitle] = useState('');
  const [assessDesc, setAssessDesc] = useState('');
  const [assessDifficulty, setAssessDifficulty] = useState<ArenaDifficulty>('medium');
  const [assessDuration, setAssessDuration] = useState(30);
  const [assessDeptId, setAssessDeptId] = useState<string>('');
  const [assessBatch, setAssessBatch] = useState<string>('');
  const [selectedQIds, setSelectedQIds] = useState<number[]>([]);
  const [creatingAssess, setCreatingAssess] = useState(false);

  // Create Institutional Question Form
  const [qTitle, setQTitle] = useState('');
  const [qPrompt, setQPrompt] = useState('');
  const [qCat, setQCat] = useState<ArenaCategory>('dsa');
  const [qDiff, setQDiff] = useState<ArenaDifficulty>('medium');
  const [optA, setOptA] = useState('');
  const [optB, setOptB] = useState('');
  const [optC, setOptC] = useState('');
  const [optD, setOptD] = useState('');
  const [correctOpt, setCorrectOpt] = useState('A');
  const [qExplanation, setQExplanation] = useState('');
  const [creatingQ, setCreatingQ] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [ana, listA, listQ, depts] = await Promise.all([
        arenaApi.getTpoAnalytics().catch(() => null),
        arenaApi.listTpoAssessments().catch(() => []),
        arenaApi.listTpoQuestions().catch(() => []),
        user?.institution_id ? orgApi.getDepartments(user.institution_id).catch(() => []) : Promise.resolve([]),
      ]);
      setAnalytics(ana);
      setAssessments(listA);
      setQuestions(listQ);
      setDepartments(depts);
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.detail?.message || 'Failed to load Institutional Arena console.');
    } finally {
      setLoading(false);
    }
  };

  const loadRoster = async () => {
    setLoadingRoster(true);
    try {
      const data = await arenaApi.getTpoStudentRoster({
        department_id: selectedDeptId ? Number(selectedDeptId) : undefined,
        graduation_year: selectedBatch ? Number(selectedBatch) : undefined,
        search: searchQuery.trim() || undefined,
      });
      setRosterData(data);
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.detail?.message || 'Failed to load student performance roster.');
    } finally {
      setLoadingRoster(false);
    }
  };

  useEffect(() => {
    loadData();
    loadRoster();
  }, []);

  const handleFilterSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadRoster();
  };

  const openStudentDetail = async (student: ArenaStudentPerformanceItem) => {
    setSelectedStudent(student);
    setLoadingDetail(true);
    try {
      const detail = await arenaApi.getTpoStudentDetail(student.student_id);
      setStudentDetail(detail);
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.detail?.message || 'Could not fetch student diagnostic detail.');
    } finally {
      setLoadingDetail(false);
    }
  };

  const closeStudentDetail = () => {
    setSelectedStudent(null);
    setStudentDetail(null);
  };

  const handleCreateQuestion = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreatingQ(true);
    setErrorMsg(null);
    setStatusMsg(null);
    try {
      const created = await arenaApi.createTpoQuestion({
        title: qTitle,
        prompt_text: qPrompt,
        category: qCat,
        difficulty: qDiff,
        question_type: 'mcq',
        options: [
          { key: 'A', text: optA },
          { key: 'B', text: optB },
          { key: 'C', text: optC },
          { key: 'D', text: optD },
        ].filter((o) => o.text.trim().length > 0),
        correct_option_key: correctOpt,
        explanation_text: qExplanation,
      });
      setStatusMsg(`Created institutional question "${created.title}".`);
      setQTitle('');
      setQPrompt('');
      setOptA('');
      setOptB('');
      setOptC('');
      setOptD('');
      setQExplanation('');
      await loadData();
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.detail?.message || 'Could not create question.');
    } finally {
      setCreatingQ(false);
    }
  };

  const handlePublishAssessment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedQIds.length === 0) {
      setErrorMsg('Select at least one question to publish an institutional test.');
      return;
    }
    setCreatingAssess(true);
    setErrorMsg(null);
    setStatusMsg(null);
    try {
      const created = await arenaApi.createTpoAssessment({
        title: assessTitle,
        description: assessDesc,
        difficulty: assessDifficulty,
        duration_minutes: assessDuration,
        question_ids: selectedQIds,
        department_id: assessDeptId ? Number(assessDeptId) : undefined,
        target_graduation_year: assessBatch ? Number(assessBatch) : undefined,
        is_published: true,
      });
      setStatusMsg(`Published institutional test "${created.title}" to enrolled students.`);
      setAssessTitle('');
      setAssessDesc('');
      setSelectedQIds([]);
      await loadData();
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.detail?.message || 'Could not publish institutional assessment.');
    } finally {
      setCreatingAssess(false);
    }
  };

  const toggleQuestionSelection = (qid: number) => {
    setSelectedQIds((prev) => (prev.includes(qid) ? prev.filter((id) => id !== qid) : [...prev, qid]));
  };

  // Filter roster items in memory based on participation status
  const displayedStudents = (rosterData?.students || []).filter((s) => {
    if (participationFilter === 'participating') return s.completed_attempts > 0;
    if (participationFilter === 'not_started') return s.completed_attempts === 0;
    return true;
  });

  return (
    <DashboardLayout
      role="tpo"
      title="Student Arena Assessments & Diagnostics"
      subtitle="Monitor individual student assessment attempts, evaluate category proficiencies, and publish campus tests."
    >
      <div className="space-y-6">
        {statusMsg && (
          <div className="p-3.5 rounded-xl bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 text-sm text-emerald-700 dark:text-emerald-300 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{statusMsg}</span>
            </div>
            <button onClick={() => setStatusMsg(null)} className="text-slate-400 hover:text-slate-600">
              ✕
            </button>
          </div>
        )}

        {errorMsg && (
          <div className="p-3.5 rounded-xl bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-800 text-sm text-rose-700 dark:text-rose-300 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
            <button onClick={() => setErrorMsg(null)} className="text-slate-400 hover:text-slate-600">
              ✕
            </button>
          </div>
        )}

        {/* Tab Switcher */}
        <div className="flex items-center gap-2 border-b border-slate-200 dark:border-slate-800 pb-2">
          <button
            onClick={() => setActiveTab('roster')}
            className={`px-4 py-2 text-sm font-semibold rounded-lg flex items-center gap-2 transition-colors ${
              activeTab === 'roster'
                ? 'bg-brand-600 text-white shadow-sm'
                : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
            }`}
          >
            <Users className="w-4 h-4" />
            <span>Student Performance & Diagnostics</span>
            {rosterData && (
              <span
                className={`px-2 py-0.5 rounded-full text-xs font-bold ${
                  activeTab === 'roster'
                    ? 'bg-brand-500 text-white'
                    : 'bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-200'
                }`}
              >
                {rosterData.total_students}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('management')}
            className={`px-4 py-2 text-sm font-semibold rounded-lg flex items-center gap-2 transition-colors ${
              activeTab === 'management'
                ? 'bg-brand-600 text-white shadow-sm'
                : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
            }`}
          >
            <Layers className="w-4 h-4" />
            <span>Institutional Tests & Question Authoring</span>
          </button>
        </div>

        {/* TAB 1: Student Roster & Assessment Diagnostics */}
        {activeTab === 'roster' && (
          <div className="space-y-6">
            {/* KPI Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Card>
                <div className="text-xs text-slate-500 font-medium">Total Enrolled Students</div>
                <div className="text-2xl font-bold text-slate-900 dark:text-white mt-1">
                  {rosterData?.total_students ?? (loadingRoster ? '...' : 0)}
                </div>
                <div className="text-[11px] text-slate-400 mt-1">Institutional records</div>
              </Card>

              <Card>
                <div className="text-xs text-slate-500 font-medium">Practicing in Arena</div>
                <div className="text-2xl font-bold text-indigo-600 dark:text-indigo-400 mt-1">
                  {rosterData?.participating_students ?? (loadingRoster ? '...' : 0)}
                </div>
                <div className="text-[11px] text-slate-400 mt-1">
                  {rosterData?.total_students
                    ? `${Math.round(((rosterData.participating_students || 0) / rosterData.total_students) * 100)}% cohort adoption`
                    : 'Active learners'}
                </div>
              </Card>

              <Card>
                <div className="text-xs text-slate-500 font-medium">Cohort Avg Accuracy</div>
                <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-1">
                  {rosterData?.average_accuracy_pct ?? (loadingRoster ? '...' : 0)}%
                </div>
                <div className="text-[11px] text-slate-400 mt-1">Across all question attempts</div>
              </Card>

              <Card>
                <div className="text-xs text-slate-500 font-medium">Total Submitted Attempts</div>
                <div className="text-2xl font-bold text-slate-900 dark:text-white mt-1">
                  {analytics?.total_submitted_attempts ?? 0}
                </div>
                <div className="text-[11px] text-slate-400 mt-1">Timed & practice assessments</div>
              </Card>
            </div>

            {/* Filter and Search Bar */}
            <Card>
              <form onSubmit={handleFilterSubmit} className="flex flex-col md:flex-row gap-3 items-center justify-between">
                <div className="flex-1 w-full md:w-auto relative">
                  <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search by student name or roll number..."
                    className="w-full pl-9 pr-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                </div>

                <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
                  <select
                    value={selectedDeptId}
                    onChange={(e) => setSelectedDeptId(e.target.value)}
                    className="px-2.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-700 dark:text-slate-200"
                  >
                    <option value="">All Departments</option>
                    {departments.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.name} ({d.code})
                      </option>
                    ))}
                  </select>

                  <input
                    type="number"
                    value={selectedBatch}
                    onChange={(e) => setSelectedBatch(e.target.value)}
                    placeholder="Batch Year"
                    className="w-24 px-2.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs"
                  />

                  <select
                    value={participationFilter}
                    onChange={(e) => setParticipationFilter(e.target.value as any)}
                    className="px-2.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-700 dark:text-slate-200"
                  >
                    <option value="all">All Participation</option>
                    <option value="participating">Active Only (&gt;0 Attempts)</option>
                    <option value="not_started">Not Started (0 Attempts)</option>
                  </select>

                  <Button type="submit" variant="primary" size="sm" isLoading={loadingRoster}>
                    <Filter className="w-3.5 h-3.5 mr-1" />
                    Filter
                  </Button>
                </div>
              </form>
            </Card>

            {/* Students Arena Assessment Table */}
            <Card>
              <CardHeader
                title={`Student Arena Performance Directory (${displayedStudents.length})`}
                subtitle="Real-time assessment scores, accuracy ratings, and diagnostic breakdowns per candidate"
                action={<Award className="w-5 h-5 text-brand-600" />}
              />

              {loadingRoster ? (
                <div className="py-12 text-center text-slate-500 text-xs">
                  <Activity className="w-6 h-6 animate-spin mx-auto mb-2 text-brand-600" />
                  Loading candidate assessment statistics...
                </div>
              ) : displayedStudents.length === 0 ? (
                <div className="py-12 text-center text-slate-500 text-xs">
                  No students matched your search or filter criteria.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-left text-slate-500 border-b border-slate-200 dark:border-slate-800">
                        <th className="py-3 px-3 font-semibold">Roll Number & Student</th>
                        <th className="py-3 px-3 font-semibold">Department</th>
                        <th className="py-3 px-3 font-semibold">Batch & CGPA</th>
                        <th className="py-3 px-3 font-semibold text-center">Attempts</th>
                        <th className="py-3 px-3 font-semibold text-center">Questions</th>
                        <th className="py-3 px-3 font-semibold text-center">Accuracy %</th>
                        <th className="py-3 px-3 font-semibold text-center">Avg Score %</th>
                        <th className="py-3 px-3 font-semibold">Top Strength</th>
                        <th className="py-3 px-3 font-semibold text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                      {displayedStudents.map((st) => (
                        <tr
                          key={st.student_id}
                          className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition-colors"
                        >
                          <td className="py-3 px-3">
                            <div className="font-mono font-bold text-slate-900 dark:text-slate-100">
                              {st.roll_number}
                            </div>
                            <div className="text-slate-600 dark:text-slate-300 font-medium">
                              {st.full_name}
                            </div>
                          </td>
                          <td className="py-3 px-3 text-slate-600 dark:text-slate-300">
                            {st.department_name || '—'}
                          </td>
                          <td className="py-3 px-3">
                            <span className="font-medium text-slate-800 dark:text-slate-200">
                              {st.graduation_year || '—'}
                            </span>
                            <span className="text-slate-400 mx-1.5">•</span>
                            <span className="font-semibold text-emerald-600 dark:text-emerald-400">
                              {st.cgpa != null ? st.cgpa.toFixed(2) : '—'} CGPA
                            </span>
                          </td>
                          <td className="py-3 px-3 text-center">
                            {st.completed_attempts > 0 ? (
                              <Badge variant="brand">{st.completed_attempts} tests</Badge>
                            ) : (
                              <Badge variant="neutral">0</Badge>
                            )}
                          </td>
                          <td className="py-3 px-3 text-center">
                            <span className="font-medium text-slate-900 dark:text-slate-100">
                              {st.questions_correct}
                            </span>
                            <span className="text-slate-400"> / {st.questions_attempted}</span>
                          </td>
                          <td className="py-3 px-3 text-center">
                            {st.completed_attempts > 0 ? (
                              <Badge
                                variant={
                                  st.overall_accuracy_pct >= 80
                                    ? 'success'
                                    : st.overall_accuracy_pct >= 60
                                    ? 'brand'
                                    : 'warning'
                                }
                              >
                                {st.overall_accuracy_pct.toFixed(1)}%
                              </Badge>
                            ) : (
                              <span className="text-slate-400">—</span>
                            )}
                          </td>
                          <td className="py-3 px-3 text-center font-bold text-slate-800 dark:text-slate-200">
                            {st.completed_attempts > 0 ? `${st.avg_score_pct.toFixed(1)}%` : '—'}
                          </td>
                          <td className="py-3 px-3">
                            {st.top_category ? (
                              <span className="inline-block px-2 py-0.5 rounded bg-brand-50 dark:bg-brand-950/50 text-brand-700 dark:text-brand-300 font-medium text-[11px]">
                                {st.top_category.toUpperCase()}
                              </span>
                            ) : (
                              <span className="text-slate-400 text-[11px]">No attempts</span>
                            )}
                          </td>
                          <td className="py-3 px-3 text-right">
                            <button
                              onClick={() => openStudentDetail(st)}
                              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-brand-600 dark:text-brand-400 hover:bg-brand-50 dark:hover:bg-brand-950/50 font-semibold text-xs transition-colors"
                            >
                              <span>Diagnostics</span>
                              <ChevronRight className="w-3.5 h-3.5" />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
          </div>
        )}

        {/* TAB 2: Institutional Tests & Question Authoring */}
        {activeTab === 'management' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Publish Institutional Assessment */}
              <Card>
                <CardHeader
                  title="Publish Institution-Specific Assessment"
                  subtitle="Combine curated and institutional questions into a timed campus test."
                  action={<Layers className="w-5 h-5 text-indigo-500" />}
                />
                <form onSubmit={handlePublishAssessment} className="space-y-3">
                  <input
                    required
                    value={assessTitle}
                    onChange={(e) => setAssessTitle(e.target.value)}
                    placeholder="Assessment title (e.g., Campus Core CS Qualifier 2026)"
                    className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm"
                  />
                  <textarea
                    required
                    value={assessDesc}
                    onChange={(e) => setAssessDesc(e.target.value)}
                    rows={2}
                    placeholder="Assessment instructions & scope..."
                    className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm"
                  />
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                    <select
                      value={assessDifficulty}
                      onChange={(e) => setAssessDifficulty(e.target.value as ArenaDifficulty)}
                      className="px-2.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs"
                    >
                      <option value="easy">Easy</option>
                      <option value="medium">Medium</option>
                      <option value="hard">Hard</option>
                    </select>
                    <input
                      type="number"
                      min={1}
                      max={180}
                      value={assessDuration}
                      onChange={(e) => setAssessDuration(Number(e.target.value))}
                      placeholder="Minutes"
                      className="px-2.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs"
                    />
                    <select
                      value={assessDeptId}
                      onChange={(e) => setAssessDeptId(e.target.value)}
                      className="px-2.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs"
                    >
                      <option value="">All Departments</option>
                      {departments.map((d) => (
                        <option key={d.id} value={d.id}>
                          {d.code}
                        </option>
                      ))}
                    </select>
                    <input
                      type="number"
                      value={assessBatch}
                      onChange={(e) => setAssessBatch(e.target.value)}
                      placeholder="Batch Year (opt)"
                      className="px-2.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs"
                    />
                  </div>

                  <div>
                    <div className="text-xs font-semibold text-slate-600 dark:text-slate-300 mb-1.5">
                      Select Questions ({selectedQIds.length} selected)
                    </div>
                    <div className="max-h-44 overflow-y-auto border border-slate-200 dark:border-slate-700 rounded-lg divide-y divide-slate-100 dark:divide-slate-800">
                      {questions.map((q) => (
                        <label
                          key={q.id}
                          className="flex items-center gap-2.5 p-2 text-xs hover:bg-slate-50 dark:hover:bg-slate-800/50 cursor-pointer"
                        >
                          <input
                            type="checkbox"
                            checked={selectedQIds.includes(q.id)}
                            onChange={() => toggleQuestionSelection(q.id)}
                          />
                          <span className="flex-1 truncate font-medium text-slate-800 dark:text-slate-100">
                            {q.title}
                          </span>
                          <Badge variant="neutral">{q.category}</Badge>
                        </label>
                      ))}
                    </div>
                  </div>

                  <Button type="submit" variant="primary" isLoading={creatingAssess}>
                    <FilePlus2 className="w-4 h-4 mr-1.5" />
                    Publish Institutional Test
                  </Button>
                </form>
              </Card>

              {/* Author Custom Question */}
              <Card>
                <CardHeader
                  title="Add Institutional Practice Question (MCQ)"
                  subtitle="Scoped strictly to your institution."
                  action={<PlusCircle className="w-5 h-5 text-emerald-500" />}
                />
                <form onSubmit={handleCreateQuestion} className="space-y-3">
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                    <input
                      required
                      value={qTitle}
                      onChange={(e) => setQTitle(e.target.value)}
                      placeholder="Question title"
                      className="sm:col-span-2 px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm"
                    />
                    <select
                      value={qCat}
                      onChange={(e) => setQCat(e.target.value as ArenaCategory)}
                      className="px-2.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs"
                    >
                      {CATEGORY_OPTIONS.map((c) => (
                        <option key={c.value} value={c.value}>
                          {c.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <textarea
                    required
                    value={qPrompt}
                    onChange={(e) => setQPrompt(e.target.value)}
                    rows={2}
                    placeholder="Question prompt text..."
                    className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm"
                  />
                  <div className="grid grid-cols-2 gap-2">
                    <input
                      required
                      value={optA}
                      onChange={(e) => setOptA(e.target.value)}
                      placeholder="Option A"
                      className="px-2.5 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs"
                    />
                    <input
                      required
                      value={optB}
                      onChange={(e) => setOptB(e.target.value)}
                      placeholder="Option B"
                      className="px-2.5 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs"
                    />
                    <input
                      value={optC}
                      onChange={(e) => setOptC(e.target.value)}
                      placeholder="Option C"
                      className="px-2.5 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs"
                    />
                    <input
                      value={optD}
                      onChange={(e) => setOptD(e.target.value)}
                      placeholder="Option D"
                      className="px-2.5 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <select
                      value={correctOpt}
                      onChange={(e) => setCorrectOpt(e.target.value)}
                      className="px-2.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs"
                    >
                      <option value="A">Correct: A</option>
                      <option value="B">Correct: B</option>
                      <option value="C">Correct: C</option>
                      <option value="D">Correct: D</option>
                    </select>
                    <select
                      value={qDiff}
                      onChange={(e) => setQDiff(e.target.value as ArenaDifficulty)}
                      className="px-2.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs"
                    >
                      <option value="easy">Easy</option>
                      <option value="medium">Medium</option>
                      <option value="hard">Hard</option>
                    </select>
                  </div>
                  <input
                    required
                    value={qExplanation}
                    onChange={(e) => setQExplanation(e.target.value)}
                    placeholder="Post-submission explanation for students..."
                    className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs"
                  />
                  <Button type="submit" variant="secondary" isLoading={creatingQ}>
                    Save Institutional Question
                  </Button>
                </form>
              </Card>
            </div>

            {/* Aggregated Test Results Table */}
            <Card>
              <CardHeader
                title="Published Institutional Assessments & Aggregated Results"
                action={<BarChart3 className="w-5 h-5 text-indigo-500" />}
              />
              {loading ? (
                <p className="text-sm text-slate-500 py-4">Loading...</p>
              ) : assessments.length === 0 ? (
                <p className="text-sm text-slate-500 py-4">No institutional tests published yet.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-xs text-slate-500 border-b border-slate-200 dark:border-slate-800">
                        <th className="py-2 pr-3">Assessment Title</th>
                        <th className="py-2 pr-3">Scope</th>
                        <th className="py-2 pr-3">Submitted</th>
                        <th className="py-2 pr-3">Avg Score</th>
                        <th className="py-2">Pass Rate</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                      {(analytics?.assessment_breakdown || []).map((row) => (
                        <tr key={row.assessment_id}>
                          <td className="py-2.5 pr-3 font-medium text-slate-900 dark:text-white">
                            {row.title}
                          </td>
                          <td className="py-2.5 pr-3 text-xs text-slate-500">
                            {row.department_name || 'All Depts'} • {row.target_graduation_year || 'All Batches'}
                          </td>
                          <td className="py-2.5 pr-3">{row.submitted_attempts}</td>
                          <td className="py-2.5 pr-3">{row.avg_score_pct}%</td>
                          <td className="py-2.5 text-emerald-600 dark:text-emerald-400">
                            {row.pass_rate_pct}%
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
          </div>
        )}

        {/* Candidate Diagnostic Detail Modal */}
        {selectedStudent && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl w-full max-w-3xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
              {/* Modal Header */}
              <div className="p-5 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between bg-slate-50 dark:bg-slate-800/50">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-brand-500/10 text-brand-600 dark:text-brand-400 flex items-center justify-center font-bold">
                    <GraduationCap className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-900 dark:text-white text-base">
                      {selectedStudent.full_name}
                    </h3>
                    <p className="text-xs text-slate-500">
                      Roll: <strong className="font-mono text-slate-700 dark:text-slate-300">{selectedStudent.roll_number}</strong> •{' '}
                      {selectedStudent.department_name || 'Department Unassigned'} • Class of {selectedStudent.graduation_year || '—'}
                    </p>
                  </div>
                </div>
                <button
                  onClick={closeStudentDetail}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-800"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Modal Body */}
              <div className="p-6 overflow-y-auto space-y-6">
                {loadingDetail ? (
                  <div className="py-16 text-center text-slate-500 text-xs">
                    <Activity className="w-6 h-6 animate-spin mx-auto mb-2 text-brand-600" />
                    Loading comprehensive diagnostic assessment profile...
                  </div>
                ) : studentDetail ? (
                  <>
                    {/* Summary Row */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                      <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800">
                        <div className="text-[11px] text-slate-500 font-medium">Completed Tests</div>
                        <div className="text-xl font-bold text-slate-900 dark:text-white mt-0.5">
                          {studentDetail.completed_attempts}
                        </div>
                      </div>
                      <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800">
                        <div className="text-[11px] text-slate-500 font-medium">Questions Attempted</div>
                        <div className="text-xl font-bold text-slate-900 dark:text-white mt-0.5">
                          {studentDetail.total_questions_attempted}
                        </div>
                      </div>
                      <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800">
                        <div className="text-[11px] text-slate-500 font-medium">Accuracy</div>
                        <div className="text-xl font-bold text-emerald-600 dark:text-emerald-400 mt-0.5">
                          {studentDetail.overall_accuracy_pct.toFixed(1)}%
                        </div>
                      </div>
                      <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800">
                        <div className="text-[11px] text-slate-500 font-medium">Correct Answers</div>
                        <div className="text-xl font-bold text-indigo-600 dark:text-indigo-400 mt-0.5">
                          {studentDetail.total_correct}
                        </div>
                      </div>
                    </div>

                    {/* Category Proficiency Breakdown */}
                    <div>
                      <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3 flex items-center gap-1.5">
                        <Target className="w-4 h-4 text-brand-600" />
                        <span>Category Proficiency & Weakness Diagnostics</span>
                      </h4>

                      <div className="space-y-2.5">
                        {(studentDetail.topic_proficiency || []).map((cat: ArenaTopicProficiencyItem) => (
                          <div
                            key={cat.category}
                            className="p-3 rounded-xl border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/30"
                          >
                            <div className="flex items-center justify-between text-xs mb-1.5">
                              <span className="font-semibold text-slate-800 dark:text-slate-200">
                                {cat.label}
                              </span>
                              <div className="flex items-center gap-2">
                                <span className="text-slate-400 text-[11px]">
                                  {cat.correct_count} / {cat.questions_attempted} correct
                                </span>
                                <Badge
                                  variant={
                                    cat.proficiency_band === 'Advanced'
                                      ? 'success'
                                      : cat.proficiency_band === 'Proficient'
                                      ? 'brand'
                                      : 'warning'
                                  }
                                >
                                  {cat.proficiency_band}
                                </Badge>
                              </div>
                            </div>
                            {/* Progress bar */}
                            <div className="w-full bg-slate-200 dark:bg-slate-700 h-2 rounded-full overflow-hidden">
                              <div
                                className={`h-full rounded-full ${
                                  cat.accuracy_pct >= 80
                                    ? 'bg-emerald-500'
                                    : cat.accuracy_pct >= 60
                                    ? 'bg-indigo-500'
                                    : 'bg-amber-500'
                                }`}
                                style={{ width: `${Math.min(100, Math.max(0, cat.accuracy_pct))}%` }}
                              />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Recent Attempts History */}
                    <div>
                      <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3 flex items-center gap-1.5">
                        <Clock className="w-4 h-4 text-brand-600" />
                        <span>Recent Assessment Attempts</span>
                      </h4>

                      {(studentDetail.recent_attempts || []).length === 0 ? (
                        <p className="text-xs text-slate-400">No attempts logged yet for this candidate.</p>
                      ) : (
                        <div className="border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden divide-y divide-slate-100 dark:divide-slate-800 text-xs">
                          {studentDetail.recent_attempts.map((att) => (
                            <div key={att.id} className="p-3 flex items-center justify-between">
                              <div>
                                <div className="font-semibold text-slate-800 dark:text-slate-200">
                                  {att.title || 'General Practice Session'}
                                </div>
                                <div className="text-[11px] text-slate-400">
                                  Category: {att.category?.toUpperCase() || 'Comprehensive'} • {att.total_questions} Questions
                                </div>
                              </div>
                              <div className="text-right">
                                <div className="font-bold text-slate-900 dark:text-white">
                                  {att.score_pct != null ? `${att.score_pct.toFixed(1)}%` : '—'}
                                </div>
                                <div className="text-[11px] text-slate-400">
                                  {att.accuracy_pct != null ? `${att.accuracy_pct.toFixed(1)}% Accuracy` : '—'}
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </>
                ) : (
                  <p className="text-xs text-slate-500">No diagnostic data found for this candidate.</p>
                )}
              </div>

              {/* Modal Footer */}
              <div className="p-4 border-t border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 flex justify-end">
                <Button variant="secondary" size="sm" onClick={closeStudentDetail}>
                  Close Diagnostic
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
};
