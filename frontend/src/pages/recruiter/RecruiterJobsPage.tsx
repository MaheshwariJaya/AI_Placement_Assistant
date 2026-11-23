import React, { useState, useEffect } from 'react';
import { DashboardLayout } from '../../components/layout/DashboardLayout';
import { Card, CardHeader } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { Input } from '../../components/common/Input';
import { useAuth } from '../../context/AuthContext';
import { companyApi, jobApi, orgApi } from '../../services/api';
import {
  Company,
  CompanyCreate,
  Department,
  Job,
  JobCreate,
  JobStatus,
  RecruiterProfile,
} from '../../types';
import {
  Briefcase,
  Building,
  Plus,
  CheckCircle2,
  Clock,
  AlertCircle,
  X,
  Search,
  MapPin,
  Calendar,
  Sparkles,
  Edit,
  ExternalLink,
  ChevronRight,
} from 'lucide-react';

export const RecruiterJobsPage: React.FC = () => {
  const { user } = useAuth();
  const [profile, setProfile] = useState<RecruiterProfile | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [activeTab, setActiveTab] = useState<'all' | 'published' | 'draft' | 'closed'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Modals
  const [isCompanyModalOpen, setIsCompanyModalOpen] = useState(false);
  const [isJobModalOpen, setIsJobModalOpen] = useState(false);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Company Form State
  const [companyForm, setCompanyForm] = useState<CompanyCreate>({
    name: '',
    industry: '',
    description: '',
    website: '',
    location: '',
    company_size: '51-200',
    contact_email: '',
    contact_phone: '',
  });

  const [jobScope, setJobScope] = useState<'my_company' | 'campus_published'>('my_company');
  const [isLoadingScope, setIsLoadingScope] = useState(false);

  const handleScopeChange = async (nextScope: 'my_company' | 'campus_published') => {
    setJobScope(nextScope);
    setIsLoadingScope(true);
    try {
      const jobList = await jobApi.list(
        nextScope === 'my_company'
          ? { my_company_only: true }
          : { status: 'published', my_company_only: false }
      );
      setJobs(jobList);
    } catch (err) {
      console.error('Failed to switch job scope:', err);
    } finally {
      setIsLoadingScope(false);
    }
  };

  // Job Form State
  const [jobForm, setJobForm] = useState<JobCreate>({
    title: '',
    description: '',
    employment_type: 'full_time',
    work_mode: 'on_site',
    location: '',
    salary_range: '',
    ctc_lpa: 0,
    min_cgpa: 0,
    target_graduation_year: new Date().getFullYear(),
    max_active_backlogs: 0,
    max_total_backlogs: 0,
    application_deadline: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().slice(0, 16),
    status: 'draft',
    required_skills: [],
    preferred_skills: [],
    eligible_department_ids: [],
  });
  const [reqSkillsInput, setReqSkillsInput] = useState('');
  const [prefSkillsInput, setPrefSkillsInput] = useState('');

  const loadData = async () => {
    setIsLoading(true);
    try {
      // 1. Fetch Recruiter Profile and linked Company
      try {
        const prof = await companyApi.getMyProfile();
        setProfile(prof);
        if (prof.company) {
          setCompanyForm({
            name: prof.company.name,
            industry: prof.company.industry,
            description: prof.company.description || '',
            website: prof.company.website || '',
            location: prof.company.location || '',
            company_size: prof.company.company_size || '51-200',
            contact_email: prof.company.contact_email || '',
            contact_phone: prof.company.contact_phone || '',
          });
        }
      } catch (err: any) {
        // Recruiter not yet linked to a company
        setProfile(null);
      }

      // 2. Fetch Jobs
      const jobList = await jobApi.list({ my_company_only: true });
      setJobs(jobList);

      // 3. Fetch Departments for eligibility select
      try {
        const instId = user?.institution_id || 1;
        const depts = await orgApi.getDepartments(instId);
        setDepartments(depts);
      } catch {
        // fallback
      }
    } catch (err: any) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSaveCompany = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setStatusMessage(null);
    try {
      if (profile?.company_id) {
        await companyApi.update(profile.company_id, companyForm);
        setStatusMessage({ type: 'success', text: 'Company profile updated successfully.' });
      } else {
        await companyApi.create(companyForm);
        setStatusMessage({ type: 'success', text: 'Company registered and linked successfully.' });
      }
      setIsCompanyModalOpen(false);
      await loadData();
    } catch (err: any) {
      const msg = err.response?.data?.detail?.message || 'Failed to save company information.';
      setStatusMessage({ type: 'error', text: msg });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleOpenCreateJob = () => {
    if (!profile?.company_id) {
      setStatusMessage({ type: 'error', text: 'Please register your company profile before creating job postings.' });
      setIsCompanyModalOpen(true);
      return;
    }
    setSelectedJob(null);
    setJobForm({
      title: '',
      description: '',
      employment_type: 'full_time',
      work_mode: 'on_site',
      location: profile.company?.location || '',
      salary_range: '',
      ctc_lpa: 0,
      min_cgpa: 0,
      target_graduation_year: new Date().getFullYear(),
      max_active_backlogs: 0,
      max_total_backlogs: 0,
      application_deadline: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().slice(0, 16),
      status: 'draft',
      required_skills: [],
      preferred_skills: [],
      eligible_department_ids: departments.map(d => d.id),
    });
    setReqSkillsInput('');
    setPrefSkillsInput('');
    setIsJobModalOpen(true);
  };

  const handleOpenEditJob = (job: Job) => {
    setSelectedJob(job);
    setJobForm({
      title: job.title,
      description: job.description || '',
      employment_type: job.employment_type,
      work_mode: job.work_mode,
      location: job.location,
      salary_range: job.salary_range || '',
      ctc_lpa: job.ctc_lpa || undefined,
      base_salary_lpa: job.base_salary_lpa || undefined,
      stipend_monthly: job.stipend_monthly || undefined,
      min_cgpa: job.min_cgpa,
      target_graduation_year: job.target_graduation_year || 2026,
      max_active_backlogs: job.max_active_backlogs,
      max_total_backlogs: job.max_total_backlogs,
      application_deadline: new Date(job.application_deadline).toISOString().slice(0, 16),
      status: job.status,
      required_skills: job.all_skills?.filter(s => s.is_mandatory).map(s => s.skill_name) || job.skills || [],
      preferred_skills: job.all_skills?.filter(s => !s.is_mandatory).map(s => s.skill_name) || [],
      eligible_department_ids: job.eligible_departments?.map(d => d.department_id) || [],
    });
    setReqSkillsInput(job.all_skills?.filter(s => s.is_mandatory).map(s => s.skill_name).join(', ') || '');
    setPrefSkillsInput(job.all_skills?.filter(s => !s.is_mandatory).map(s => s.skill_name).join(', ') || '');
    setIsJobModalOpen(true);
  };

  const handleSaveJob = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setStatusMessage(null);
    try {
      const reqSkills = reqSkillsInput.split(',').map(s => s.trim()).filter(Boolean);
      const prefSkills = prefSkillsInput.split(',').map(s => s.trim()).filter(Boolean);

      const payload: JobCreate = {
        ...jobForm,
        required_skills: reqSkills,
        preferred_skills: prefSkills,
        application_deadline: new Date(jobForm.application_deadline).toISOString(),
      };

      if (selectedJob) {
        await jobApi.update(selectedJob.id, payload);
        setStatusMessage({ type: 'success', text: `Job '${payload.title}' updated successfully.` });
      } else {
        await jobApi.create(payload);
        setStatusMessage({ type: 'success', text: `Job '${payload.title}' created successfully.` });
      }

      setIsJobModalOpen(false);
      await loadData();
    } catch (err: any) {
      const msg = err.response?.data?.detail?.message || 'Failed to save job posting.';
      setStatusMessage({ type: 'error', text: msg });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleStatus = async (job: Job, newStatus: JobStatus) => {
    try {
      await jobApi.updateStatus(job.id, newStatus);
      setStatusMessage({ type: 'success', text: `Job status updated to '${newStatus}'.` });
      await loadData();
    } catch (err: any) {
      const msg = err.response?.data?.detail?.message || 'Failed to update job status.';
      setStatusMessage({ type: 'error', text: msg });
    }
  };

  // Filtered Jobs
  const filteredJobs = jobs.filter(j => {
    const matchesTab =
      activeTab === 'all'
        ? true
        : activeTab === 'published'
        ? j.status === 'published'
        : activeTab === 'draft'
        ? j.status === 'draft'
        : j.status === 'closed' || j.status === 'cancelled';
    const matchesSearch =
      !searchQuery ||
      j.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      j.location.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesTab && matchesSearch;
  });

  return (
    <DashboardLayout
      role="recruiter"
      title="Campus Recruitment & Job Management"
      subtitle="Corporate Scope: Author job opportunities, configure strict academic cutoffs, and monitor hiring pipeline."
    >
      {/* Alert Banner */}
      {statusMessage && (
        <div
          className={`p-4 rounded-lg mb-6 flex items-start justify-between ${
            statusMessage.type === 'success'
              ? 'bg-emerald-50 dark:bg-emerald-950/30 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/60'
              : 'bg-rose-50 dark:bg-rose-950/30 text-rose-800 dark:text-rose-300 border border-rose-200 dark:border-rose-800/60'
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
          <button onClick={() => setStatusMessage(null)} className="text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-300">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Top Banner: Company Profile Header */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-xl p-5 mb-6 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-sm">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-xl bg-sky-50 dark:bg-sky-950/40 text-sky-600 dark:text-sky-400 flex items-center justify-center font-bold text-xl border border-sky-100 dark:border-sky-800/60 flex-shrink-0">
            <Building className="w-7 h-7" />
          </div>
          <div>
            {profile?.company ? (
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">{profile.company.name}</h2>
                  {profile.company.is_verified ? (
                    <Badge variant="success">Verified Partner</Badge>
                  ) : (
                    <Badge variant="warning">Verification Pending (TPO / Admin Review)</Badge>
                  )}
                </div>
                <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500 dark:text-slate-400 mt-1">
                  <span>{profile.company.industry}</span>
                  {profile.company.location && <span>• {profile.company.location}</span>}
                  {profile.company.company_size && <span>• {profile.company.company_size} employees</span>}
                  {profile.designation && <span>• Recruiter: {profile.designation}</span>}
                </div>
              </div>
            ) : (
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">Unlinked Recruiter Profile</h2>
                  <Badge variant="warning">Setup Required</Badge>
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                  You are not yet linked to a corporate organization. Register your company to begin posting jobs.
                </p>
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setIsCompanyModalOpen(true)}
            icon={<Edit className="w-3.5 h-3.5" />}
          >
            {profile?.company ? 'Edit Company Profile' : 'Register Company'}
          </Button>
          <Button
            size="sm"
            onClick={handleOpenCreateJob}
            icon={<Plus className="w-3.5 h-3.5" />}
          >
            Create Job Posting
          </Button>
        </div>
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 mb-6">
        <Card>
          <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Total Postings</span>
          <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-1">{jobs.length}</div>
          <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-0.5">All authored opportunities</p>
        </Card>
        <Card>
          <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Published Active</span>
          <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-1">
            {jobs.filter(j => j.status === 'published').length}
          </div>
          <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-0.5">Live for student candidates</p>
        </Card>
        <Card>
          <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Drafts Pending</span>
          <div className="text-2xl font-bold text-amber-600 dark:text-amber-400 mt-1">
            {jobs.filter(j => j.status === 'draft').length}
          </div>
          <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-0.5">Unpublished in review</p>
        </Card>
        <Card>
          <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Closed / Archived</span>
          <div className="text-2xl font-bold text-slate-500 dark:text-slate-400 mt-1">
            {jobs.filter(j => j.status === 'closed' || j.status === 'cancelled').length}
          </div>
          <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-0.5">Applications completed</p>
        </Card>
      </div>

      {/* Main Jobs Card */}
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4 pb-3 border-b border-slate-100 dark:border-slate-800">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => handleScopeChange('my_company')}
              disabled={isLoadingScope}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg border transition-colors ${
                jobScope === 'my_company'
                  ? 'bg-slate-900 dark:bg-brand-600 text-white border-slate-900 dark:border-brand-600'
                  : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800'
              }`}
            >
              My Company Postings
            </button>
            <button
              type="button"
              onClick={() => handleScopeChange('campus_published')}
              disabled={isLoadingScope}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg border transition-colors ${
                jobScope === 'campus_published'
                  ? 'bg-slate-900 dark:bg-brand-600 text-white border-slate-900 dark:border-brand-600'
                  : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800'
              }`}
            >
              Campus Published Jobs
            </button>
          </div>
          <span className="text-[11px] text-slate-500 dark:text-slate-400">
            {jobScope === 'my_company'
              ? 'Manage and publish roles posted by your company.'
              : 'Read-only directory of published campus openings across partner employers.'}
          </span>
        </div>

        <div className="border-b border-slate-200 dark:border-slate-800 pb-4 mb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          {/* Status Tabs */}
          <div className="flex space-x-1">
            {[
              { id: 'all', label: `All (${jobs.length})` },
              { id: 'published', label: `Published (${jobs.filter(j => j.status === 'published').length})` },
              { id: 'draft', label: `Drafts (${jobs.filter(j => j.status === 'draft').length})` },
              { id: 'closed', label: `Closed (${jobs.filter(j => j.status === 'closed').length})` },
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
                  activeTab === tab.id
                    ? 'bg-brand-50 dark:bg-brand-950/40 text-brand-700 dark:text-brand-300 border border-brand-200 dark:border-brand-800/60'
                    : 'text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Search */}
          <div className="relative w-full sm:w-64">
            <Search className="w-3.5 h-3.5 text-slate-400 dark:text-slate-500 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search job title or city..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="w-full text-xs pl-8 pr-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 dark:placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </div>
        </div>

        {/* Jobs List */}
        {filteredJobs.length === 0 ? (
          <div className="text-center py-12 text-slate-400 dark:text-slate-500">
            <Briefcase className="w-10 h-10 mx-auto mb-2 opacity-40" />
            <p className="text-xs font-semibold text-slate-600 dark:text-slate-300">No job postings found</p>
            <p className="text-[11px] text-slate-400 dark:text-slate-500 mt-1 max-w-sm mx-auto">
              {jobs.length === 0
                ? "You haven't created any campus job opportunities yet. Click 'Create Job Posting' above to publish your first role."
                : 'No job postings match the active filter or search query.'}
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100 dark:divide-slate-800">
            {filteredJobs.map(job => (
              <div
                key={job.id}
                className="py-4 flex flex-col lg:flex-row lg:items-center justify-between gap-4 hover:bg-slate-50/50 dark:hover:bg-slate-800/40 p-3 rounded-lg transition-colors"
              >
                <div className="space-y-1.5 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">{job.title}</h3>
                    <Badge
                      variant={
                        job.status === 'published'
                          ? 'success'
                          : job.status === 'draft'
                          ? 'warning'
                          : 'neutral'
                      }
                    >
                      {job.status.toUpperCase()}
                    </Badge>
                    <span className="text-[10px] font-medium px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 capitalize">
                      {job.employment_type.replace(/_/g, ' ')}
                    </span>
                    <span className="text-[10px] font-medium px-2 py-0.5 rounded bg-sky-50 dark:bg-sky-950/40 text-sky-700 dark:text-sky-300 capitalize">
                      {job.work_mode.replace(/_/g, ' ')}
                    </span>
                  </div>

                  <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500 dark:text-slate-400">
                    <div className="flex items-center gap-1">
                      <MapPin className="w-3.5 h-3.5 text-slate-400 dark:text-slate-500" />
                      <span>{job.location}</span>
                    </div>
                    {job.salary_range && (
                      <div className="font-semibold text-slate-700 dark:text-slate-200">
                        ₹ {job.salary_range}
                      </div>
                    )}
                    <div className="flex items-center gap-1">
                      <Calendar className="w-3.5 h-3.5 text-slate-400 dark:text-slate-500" />
                      <span>Deadline: {new Date(job.application_deadline).toLocaleDateString()}</span>
                    </div>
                  </div>

                  {/* Cutoff Badges */}
                  <div className="flex flex-wrap items-center gap-2 pt-1 text-[11px]">
                    <span className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                      Min CGPA: <strong>{job.min_cgpa.toFixed(2)}</strong>
                    </span>
                    {job.target_graduation_year && (
                      <span className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                        Batch: <strong>{job.target_graduation_year}</strong>
                      </span>
                    )}
                    <span className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                      Backlogs: <strong>Max {job.max_active_backlogs}</strong>
                    </span>
                    {job.skills && job.skills.length > 0 && (
                      <div className="flex items-center gap-1 text-[10px] text-brand-600 dark:text-brand-400">
                        <span>Skills:</span>
                        {job.skills.slice(0, 3).map((s, idx) => (
                          <span key={idx} className="bg-brand-50 dark:bg-brand-950/40 px-1.5 py-0.5 rounded">
                            {s}
                          </span>
                        ))}
                        {job.skills.length > 3 && <span>+{job.skills.length - 3}</span>}
                      </div>
                    )}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 self-end lg:self-center">
                  {(jobScope === 'campus_published' || job.company_id !== profile?.company_id) && (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                      {job.company_name}
                    </span>
                  )}
                  {job.company_id === profile?.company_id ? (
                    <>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => handleOpenEditJob(job)}
                        className="!text-xs"
                      >
                        Edit
                      </Button>
                  {job.status === 'draft' ? (
                    <Button
                      size="sm"
                      onClick={() => handleToggleStatus(job, 'published')}
                      className="bg-emerald-600 hover:bg-emerald-700 !text-xs"
                    >
                      Publish
                    </Button>
                  ) : job.status === 'published' ? (
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => handleToggleStatus(job, 'closed')}
                      className="!text-xs text-slate-600 dark:text-slate-300"
                    >
                      Close Posting
                    </Button>
                  ) : (
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => handleToggleStatus(job, 'published')}
                      className="!text-xs text-brand-600 dark:text-brand-400"
                    >
                      Re-open
                    </Button>
                  )}
                    </>
                  ) : (
                    <span className="text-[11px] font-medium text-slate-400 dark:text-slate-500">Read-only Campus View</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Company Modal */}
      {isCompanyModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 dark:bg-slate-950/70 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-xl max-w-lg w-full p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                {profile?.company ? 'Update Corporate Profile' : 'Register Corporate Company'}
              </h3>
              <button onClick={() => setIsCompanyModalOpen(false)} className="text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-300">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSaveCompany} className="space-y-3 text-xs">
              <div>
                <label className="font-semibold text-slate-700 dark:text-slate-300">Company Name *</label>
                <input
                  type="text"
                  required
                  value={companyForm.name}
                  onChange={e => setCompanyForm({ ...companyForm, name: e.target.value })}
                  placeholder="e.g. HexaCorp Technologies"
                  className="w-full mt-1 p-2 border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg focus:outline-none focus:ring-1 focus:ring-brand-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold text-slate-700 dark:text-slate-300">Industry Sector *</label>
                  <input
                    type="text"
                    required
                    value={companyForm.industry}
                    onChange={e => setCompanyForm({ ...companyForm, industry: e.target.value })}
                    placeholder="e.g. Software, FinTech"
                    className="w-full mt-1 p-2 border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-700 dark:text-slate-300">Company Size</label>
                  <select
                    value={companyForm.company_size}
                    onChange={e => setCompanyForm({ ...companyForm, company_size: e.target.value })}
                    className="w-full mt-1 p-2 border border-slate-300 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
                  >
                    <option value="1-50">1-50 employees</option>
                    <option value="51-200">51-200 employees</option>
                    <option value="201-1000">201-1000 employees</option>
                    <option value="1000+">1000+ employees</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold text-slate-700 dark:text-slate-300">Headquarters / Location</label>
                  <input
                    type="text"
                    value={companyForm.location}
                    onChange={e => setCompanyForm({ ...companyForm, location: e.target.value })}
                    placeholder="e.g. Bengaluru, Karnataka"
                    className="w-full mt-1 p-2 border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg"
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-700 dark:text-slate-300">Website</label>
                  <input
                    type="text"
                    value={companyForm.website}
                    onChange={e => setCompanyForm({ ...companyForm, website: e.target.value })}
                    placeholder="https://company.com"
                    className="w-full mt-1 p-2 border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg"
                  />
                </div>
              </div>

              <div>
                <label className="font-semibold text-slate-700 dark:text-slate-300">Overview & Description</label>
                <textarea
                  rows={3}
                  value={companyForm.description}
                  onChange={e => setCompanyForm({ ...companyForm, description: e.target.value })}
                  placeholder="Summary of business domain, engineering culture, and campus recruitment..."
                  className="w-full mt-1 p-2 border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-200 dark:border-slate-800">
                <Button variant="secondary" size="sm" onClick={() => setIsCompanyModalOpen(false)}>
                  Cancel
                </Button>
                <Button size="sm" disabled={isSubmitting}>
                  {isSubmitting ? 'Saving...' : 'Save Profile'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Job Create/Edit Modal */}
      {isJobModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 dark:bg-slate-950/70 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-xl max-w-2xl w-full p-6 space-y-4 my-8 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                {selectedJob ? 'Edit Campus Job Posting' : 'Author New Campus Job Posting'}
              </h3>
              <button onClick={() => setIsJobModalOpen(false)} className="text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-300">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSaveJob} className="space-y-4 text-xs">
              <div>
                <label className="font-semibold text-slate-700 dark:text-slate-300">Job Title *</label>
                <input
                  type="text"
                  required
                  value={jobForm.title}
                  onChange={e => setJobForm({ ...jobForm, title: e.target.value })}
                  placeholder="e.g. Associate Software Engineer (Backend)"
                  className="w-full mt-1 p-2 border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg focus:outline-none focus:ring-1 focus:ring-brand-500"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="font-semibold text-slate-700 dark:text-slate-300">Employment Type *</label>
                  <select
                    value={jobForm.employment_type}
                    onChange={e => setJobForm({ ...jobForm, employment_type: e.target.value as any })}
                    className="w-full mt-1 p-2 border border-slate-300 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
                  >
                    <option value="full_time">Full Time</option>
                    <option value="internship">Internship</option>
                    <option value="intern_to_full_time">Intern to Full Time</option>
                  </select>
                </div>
                <div>
                  <label className="font-semibold text-slate-700 dark:text-slate-300">Work Mode *</label>
                  <select
                    value={jobForm.work_mode}
                    onChange={e => setJobForm({ ...jobForm, work_mode: e.target.value as any })}
                    className="w-full mt-1 p-2 border border-slate-300 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
                  >
                    <option value="on_site">On-Site</option>
                    <option value="hybrid">Hybrid</option>
                    <option value="remote">Remote</option>
                  </select>
                </div>
                <div>
                  <label className="font-semibold text-slate-700 dark:text-slate-300">Location *</label>
                  <input
                    type="text"
                    required
                    value={jobForm.location}
                    onChange={e => setJobForm({ ...jobForm, location: e.target.value })}
                    placeholder="e.g. Bengaluru / Pune"
                    className="w-full mt-1 p-2 border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold text-slate-700 dark:text-slate-300">Salary / Compensation String</label>
                  <input
                    type="text"
                    value={jobForm.salary_range}
                    onChange={e => setJobForm({ ...jobForm, salary_range: e.target.value })}
                    placeholder="e.g. 12 - 16 LPA or ₹45,000/mo"
                    className="w-full mt-1 p-2 border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg"
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-700 dark:text-slate-300">CTC in LPA (Numeric for sorting)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={jobForm.ctc_lpa || ''}
                    onChange={e => setJobForm({ ...jobForm, ctc_lpa: parseFloat(e.target.value) || undefined })}
                    placeholder="14.0"
                    className="w-full mt-1 p-2 border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg"
                  />
                </div>
              </div>

              <div>
                <label className="font-semibold text-slate-700 dark:text-slate-300">Job Description *</label>
                <textarea
                  rows={4}
                  required
                  value={jobForm.description}
                  onChange={e => setJobForm({ ...jobForm, description: e.target.value })}
                  placeholder="Outline core responsibilities, engineering stack, qualification expectations..."
                  className="w-full mt-1 p-2 border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg"
                />
              </div>

              {/* Academic Eligibility Section */}
              <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 space-y-3">
                <span className="font-bold text-slate-800 dark:text-slate-100 flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                  Deterministic Academic Eligibility Cutoffs
                </span>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div>
                    <label className="text-[11px] font-semibold text-slate-600 dark:text-slate-300">Min CGPA (0 - 10)</label>
                    <input
                      type="number"
                      step="0.01"
                      min="0.0"
                      max="10.0"
                      value={jobForm.min_cgpa}
                      onChange={e => setJobForm({ ...jobForm, min_cgpa: parseFloat(e.target.value) || 0 })}
                      className="w-full mt-1 p-1.5 border border-slate-300 dark:border-slate-700 rounded bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 text-xs"
                    />
                  </div>
                  <div>
                    <label className="text-[11px] font-semibold text-slate-600 dark:text-slate-300">Graduating Batch</label>
                    <input
                      type="number"
                      value={jobForm.target_graduation_year || ''}
                      onChange={e => setJobForm({ ...jobForm, target_graduation_year: parseInt(e.target.value) || undefined })}
                      placeholder="2026"
                      className="w-full mt-1 p-1.5 border border-slate-300 dark:border-slate-700 rounded bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 text-xs"
                    />
                  </div>
                  <div>
                    <label className="text-[11px] font-semibold text-slate-600 dark:text-slate-300">Max Active Backlogs</label>
                    <input
                      type="number"
                      min="0"
                      value={jobForm.max_active_backlogs}
                      onChange={e => setJobForm({ ...jobForm, max_active_backlogs: parseInt(e.target.value) || 0 })}
                      className="w-full mt-1 p-1.5 border border-slate-300 dark:border-slate-700 rounded bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 text-xs"
                    />
                  </div>
                  <div>
                    <label className="text-[11px] font-semibold text-slate-600 dark:text-slate-300">Max Total Backlogs</label>
                    <input
                      type="number"
                      min="0"
                      value={jobForm.max_total_backlogs}
                      onChange={e => setJobForm({ ...jobForm, max_total_backlogs: parseInt(e.target.value) || 0 })}
                      className="w-full mt-1 p-1.5 border border-slate-300 dark:border-slate-700 rounded bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 text-xs"
                    />
                  </div>
                </div>

                <div>
                  <label className="text-[11px] font-semibold text-slate-600 dark:text-slate-300">Application Deadline *</label>
                  <input
                    type="datetime-local"
                    required
                    value={jobForm.application_deadline}
                    onChange={e => setJobForm({ ...jobForm, application_deadline: e.target.value })}
                    className="w-full mt-1 p-1.5 border border-slate-300 dark:border-slate-700 rounded bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 text-xs"
                  />
                </div>
              </div>

              {/* Skills Prerequisites */}
              <div className="space-y-2">
                <div>
                  <label className="font-semibold text-slate-700 dark:text-slate-300">Required Skills (Comma-separated) *</label>
                  <input
                    type="text"
                    value={reqSkillsInput}
                    onChange={e => setReqSkillsInput(e.target.value)}
                    placeholder="Python, FastAPI, PostgreSQL, Docker"
                    className="w-full mt-1 p-2 border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg text-xs"
                  />
                  <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-0.5">Mandatory skills verified during student eligibility check</p>
                </div>
                <div>
                  <label className="font-semibold text-slate-700 dark:text-slate-300">Preferred / Bonus Skills (Comma-separated)</label>
                  <input
                    type="text"
                    value={prefSkillsInput}
                    onChange={e => setPrefSkillsInput(e.target.value)}
                    placeholder="Redis, Kubernetes, AWS, GraphQL"
                    className="w-full mt-1 p-2 border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg text-xs"
                  />
                </div>
              </div>

              {/* Initial Status */}
              <div>
                <label className="font-semibold text-slate-700 dark:text-slate-300">Publication Status</label>
                <select
                  value={jobForm.status}
                  onChange={e => setJobForm({ ...jobForm, status: e.target.value as any })}
                  className="w-full mt-1 p-2 border border-slate-300 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
                >
                  <option value="draft">Save as Draft (Private to your company)</option>
                  <option value="published">Publish Immediately (Visible to eligible students)</option>
                </select>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-200 dark:border-slate-800">
                <Button variant="secondary" size="sm" onClick={() => setIsJobModalOpen(false)}>
                  Cancel
                </Button>
                <Button size="sm" disabled={isSubmitting}>
                  {isSubmitting ? 'Saving...' : selectedJob ? 'Update Job' : 'Create Job'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
};
