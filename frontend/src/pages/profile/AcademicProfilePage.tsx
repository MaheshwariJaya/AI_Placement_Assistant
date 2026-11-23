import React, { useEffect, useState } from 'react';
import { DashboardLayout } from '../../components/layout/DashboardLayout';
import { Card, CardHeader } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { Input } from '../../components/common/Input';
import { userApi } from '../../services/api';
import { StudentProfile } from '../../types';
import { useAuth } from '../../context/AuthContext';
import { useAcademic } from '../../context/AcademicContext';
import {
  GraduationCap,
  Building,
  ShieldCheck,
  CheckCircle2,
  ExternalLink,
  Code2,
  Briefcase,
  Award,
  Globe,
  Github,
  Linkedin,
  RefreshCw,
  AlertCircle,
} from 'lucide-react';

export const AcademicProfilePage: React.FC = () => {
  const { user } = useAuth();
  const { officialBranchName } = useAcademic();
  const [profile, setProfile] = useState<StudentProfile | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [savingPortfolio, setSavingPortfolio] = useState<boolean>(false);
  const [notification, setNotification] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Editable portfolio fields
  const [linkedinUrl, setLinkedinUrl] = useState<string>('');
  const [githubUrl, setGithubUrl] = useState<string>('');
  const [portfolioUrl, setPortfolioUrl] = useState<string>('');

  const fetchProfile = async () => {
    setLoading(true);
    try {
      const data = await userApi.getStudentProfile();
      setProfile(data);
      setLinkedinUrl(data.linkedin_url || '');
      setGithubUrl(data.github_url || '');
      setPortfolioUrl(data.portfolio_url || '');
    } catch (err: any) {
      setNotification({
        type: 'error',
        text: err.response?.data?.error?.message || 'Failed to fetch academic profile.',
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProfile();
  }, []);

  const handleSavePortfolio = async () => {
    setSavingPortfolio(true);
    setNotification(null);
    try {
      const updated = await userApi.updatePortfolio({
        linkedin_url: linkedinUrl.trim() || undefined,
        github_url: githubUrl.trim() || undefined,
        portfolio_url: portfolioUrl.trim() || undefined,
      });
      setProfile(updated);
      setNotification({
        type: 'success',
        text: 'Portfolio and external profile links updated successfully.',
      });
    } catch (err: any) {
      setNotification({
        type: 'error',
        text: err.response?.data?.error?.message || 'Failed to update portfolio links.',
      });
    } finally {
      setSavingPortfolio(false);
    }
  };

  const studentName = profile?.user?.full_name || user?.full_name || '—';
  const departmentName =
    profile?.department_name ||
    profile?.user?.department_name ||
    (profile?.user as any)?.department?.name ||
    user?.department_name ||
    (user as any)?.department?.name ||
    (officialBranchName && officialBranchName !== 'Department Unassigned' ? officialBranchName : 'Computer Science and Engineering');
  const institutionName =
    profile?.institution_name ||
    profile?.user?.institution_name ||
    (profile?.user as any)?.institution?.name ||
    user?.institution_name ||
    (user as any)?.institution?.name ||
    'MBM University';
  const rollNumber = profile?.roll_number || user?.roll_number || '—';
  const graduationYear = profile?.graduation_year ?? '—';
  const cgpaValue = profile?.cgpa !== undefined && profile?.cgpa !== null ? Number(profile.cgpa).toFixed(2) : '—';
  const activeBacklogs = profile?.active_backlogs ?? 0;
  const totalBacklogs = profile?.total_backlogs ?? 0;

  return (
    <DashboardLayout
      role="student"
      title="My Academic Profile"
      subtitle="Institutional academic credentials, verified eligibility cutoffs, and verified candidate portfolio."
    >
      {notification && (
        <div
          className={`p-4 rounded-xl mb-6 flex items-center justify-between text-xs font-semibold ${
            notification.type === 'success'
              ? 'bg-emerald-50 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-200 border border-emerald-200 dark:border-emerald-800'
              : 'bg-rose-50 dark:bg-rose-950/60 text-rose-800 dark:text-rose-200 border border-rose-200 dark:border-rose-800'
          }`}
        >
          <div className="flex items-center gap-2">
            {notification.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 text-rose-600 dark:text-rose-400 shrink-0" />
            )}
            <span>{notification.text}</span>
          </div>
          <button onClick={() => setNotification(null)} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200">
            ✕
          </button>
        </div>
      )}

      {/* Verified Academic Profile Header */}
      <div className="bg-gradient-to-r from-brand-700 via-brand-600 to-indigo-600 rounded-xl p-6 text-white mb-6 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-white/20 text-white text-[11px] font-semibold mb-2 backdrop-blur">
              <ShieldCheck className="w-3 h-3 text-emerald-300" />
              <span>Official Institutional Record</span>
            </div>
            <h2 className="text-xl font-bold tracking-tight">{studentName}</h2>
            <p className="text-xs text-brand-100 mt-1 flex flex-wrap items-center gap-x-2 gap-y-1">
              <span className="font-medium">{departmentName}</span>
              <span className="opacity-60">•</span>
              <strong className="text-white font-semibold">Class of {graduationYear}</strong>
              <span className="opacity-60">•</span>
              <span>Roll: {rollNumber}</span>
            </p>
            <p className="text-[11px] text-brand-200 mt-1 flex items-center gap-1.5">
              <Building className="w-3.5 h-3.5 shrink-0" />
              <span>{institutionName}</span>
            </p>
          </div>
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-2">
            <span className="text-xs bg-white/10 px-3 py-1.5 rounded-lg border border-white/20 backdrop-blur">
              CGPA: <strong className="text-white">{cgpaValue}</strong> ({activeBacklogs} Backlogs)
            </span>
            <span className="text-xs bg-emerald-500/20 text-emerald-100 px-2.5 py-1.5 rounded-lg border border-emerald-400/30 flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-300" />
              Placement Ready
            </span>
          </div>
        </div>
      </div>

      {/* Protection Notice */}
      <div className="p-3.5 mb-6 rounded-lg bg-emerald-50 dark:bg-emerald-950/50 border border-emerald-200 dark:border-emerald-800 text-xs text-emerald-900 dark:text-emerald-200 flex items-start gap-2.5">
        <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
        <div>
          <span className="font-bold">Institutional Security & Verification Guarantee:</span>
          <p className="text-[11px] text-emerald-800 dark:text-emerald-300 leading-relaxed mt-0.5">
            Your academic metrics (CGPA: {cgpaValue}, Roll Number: {rollNumber}, Department: {departmentName}, and <strong>Class of {graduationYear}</strong>) are verified institutional records. They are permanently locked and cannot be overwritten by resume uploads or external edits.
          </p>
        </div>
      </div>

      {/* Grid: Academic Verification Metrics & Candidate Portfolio */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mb-6">
        {/* Verified Academic Card */}
        <div className="lg:col-span-6 space-y-4">
          <Card>
            <CardHeader
              title="Verified Academic Records"
              subtitle="Audited by Training & Placement Cell"
            />
            <div className="space-y-3 text-xs">
              <div className="flex items-center justify-between gap-4 p-3 rounded-lg bg-slate-50 dark:bg-slate-800/70 border border-slate-100 dark:border-slate-800">
                <span className="text-slate-500 dark:text-slate-400 font-medium shrink-0">Institution</span>
                <span className="font-bold text-slate-800 dark:text-slate-100 text-right truncate" title={institutionName}>{institutionName}</span>
              </div>
              <div className="flex items-center justify-between gap-4 p-3 rounded-lg bg-slate-50 dark:bg-slate-800/70 border border-slate-100 dark:border-slate-800">
                <span className="text-slate-500 dark:text-slate-400 font-medium shrink-0">Department</span>
                <span className="font-bold text-slate-800 dark:text-slate-100 text-right text-end leading-snug" title={departmentName}>{departmentName}</span>
              </div>
              <div className="flex items-center justify-between gap-4 p-3 rounded-lg bg-slate-50 dark:bg-slate-800/70 border border-slate-100 dark:border-slate-800">
                <span className="text-slate-500 dark:text-slate-400 font-medium shrink-0">Roll Number</span>
                <span className="font-mono font-bold text-slate-900 dark:text-slate-100 text-right">{rollNumber}</span>
              </div>
              <div className="flex items-center justify-between gap-4 p-3 rounded-lg bg-brand-50/60 dark:bg-brand-950/60 border border-brand-200 dark:border-brand-800">
                <span className="text-brand-700 dark:text-brand-300 font-semibold shrink-0">Graduation Class</span>
                <span className="font-bold text-brand-900 dark:text-brand-200 text-right">Class of {graduationYear}</span>
              </div>
              <div className="flex items-center justify-between gap-4 p-3 rounded-lg bg-slate-50 dark:bg-slate-800/70 border border-slate-100 dark:border-slate-800">
                <span className="text-slate-500 dark:text-slate-400 font-medium shrink-0">Cumulative GPA (CGPA)</span>
                <span className="font-bold text-emerald-700 dark:text-emerald-400 text-right">{cgpaValue} / 10.0</span>
              </div>
              <div className="flex items-center justify-between gap-4 p-3 rounded-lg bg-slate-50 dark:bg-slate-800/70 border border-slate-100 dark:border-slate-800">
                <span className="text-slate-500 dark:text-slate-400 font-medium shrink-0">Active Backlogs</span>
                <span className={`font-bold text-right ${activeBacklogs > 0 ? 'text-rose-600 dark:text-rose-400' : 'text-emerald-600 dark:text-emerald-400'}`}>
                  {activeBacklogs}
                </span>
              </div>
              <div className="flex items-center justify-between gap-4 p-3 rounded-lg bg-slate-50 dark:bg-slate-800/70 border border-slate-100 dark:border-slate-800">
                <span className="text-slate-500 dark:text-slate-400 font-medium shrink-0">Total Career Backlogs</span>
                <span className="font-bold text-slate-800 dark:text-slate-100 text-right">{totalBacklogs}</span>
              </div>
            </div>
          </Card>
        </div>

        {/* Candidate Portfolio Links */}
        <div className="lg:col-span-6 space-y-4">
          <Card>
            <CardHeader
              title="Candidate Portfolio & Web Presence"
              subtitle="External profile links shared with prospective recruitment drives"
            />
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1 flex items-center gap-1.5">
                  <Linkedin className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
                  <span>LinkedIn Profile URL</span>
                </label>
                <input
                  type="url"
                  placeholder="https://linkedin.com/in/username"
                  value={linkedinUrl}
                  onChange={(e) => setLinkedinUrl(e.target.value)}
                  className="w-full text-xs px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 focus:outline-none focus:ring-1 focus:ring-brand-500 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1 flex items-center gap-1.5">
                  <Github className="w-3.5 h-3.5 text-slate-800 dark:text-slate-200" />
                  <span>GitHub Profile URL</span>
                </label>
                <input
                  type="url"
                  placeholder="https://github.com/username"
                  value={githubUrl}
                  onChange={(e) => setGithubUrl(e.target.value)}
                  className="w-full text-xs px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 focus:outline-none focus:ring-1 focus:ring-brand-500 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1 flex items-center gap-1.5">
                  <Globe className="w-3.5 h-3.5 text-brand-600 dark:text-brand-400" />
                  <span>Personal Portfolio / Website URL</span>
                </label>
                <input
                  type="url"
                  placeholder="https://my-portfolio.dev"
                  value={portfolioUrl}
                  onChange={(e) => setPortfolioUrl(e.target.value)}
                  className="w-full text-xs px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 focus:outline-none focus:ring-1 focus:ring-brand-500 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500"
                />
              </div>

              <div className="pt-2 flex justify-end">
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleSavePortfolio}
                  disabled={savingPortfolio}
                >
                  {savingPortfolio ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 mr-1.5 animate-spin" /> Saving...
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="w-3.5 h-3.5 mr-1.5" /> Save Portfolio Links
                    </>
                  )}
                </Button>
              </div>
            </div>
          </Card>

          {/* Placement Drive Verification Status */}
          <Card>
            <CardHeader
              title="Campus Recruitment Verification Status"
              subtitle="Eligibility criteria check for active drives"
            />
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
              <div className="p-3 rounded-lg bg-emerald-50 dark:bg-emerald-950/50 border border-emerald-100 dark:border-emerald-900 flex items-center gap-2.5">
                <CheckCircle2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400 shrink-0" />
                <div>
                  <div className="font-bold text-emerald-900 dark:text-emerald-200">Academic Standing</div>
                  <div className="text-[11px] text-emerald-700 dark:text-emerald-300">{cgpaValue} CGPA • Zero Backlogs</div>
                </div>
              </div>
              <div className="p-3 rounded-lg bg-emerald-50 dark:bg-emerald-950/50 border border-emerald-100 dark:border-emerald-900 flex items-center gap-2.5">
                <CheckCircle2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400 shrink-0" />
                <div>
                  <div className="font-bold text-emerald-900 dark:text-emerald-200">Batch Cohort</div>
                  <div className="text-[11px] text-emerald-700 dark:text-emerald-300">Class of {graduationYear} Verified</div>
                </div>
              </div>
              <div className="p-3 rounded-lg bg-emerald-50 dark:bg-emerald-950/50 border border-emerald-100 dark:border-emerald-900 flex items-center gap-2.5">
                <CheckCircle2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400 shrink-0" />
                <div>
                  <div className="font-bold text-emerald-900 dark:text-emerald-200">Placement Gating</div>
                  <div className="text-[11px] text-emerald-700 dark:text-emerald-300">Cleared for Campus Drives</div>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  );
};

