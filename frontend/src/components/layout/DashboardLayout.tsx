import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  Sparkles,
  LayoutDashboard,
  User,
  FileText,
  Briefcase,
  Bot,
  Users,
  Building,
  Calendar,
  BarChart3,
  ShieldCheck,
  Server,
  Menu,
  X,
  Settings,
  Mic,
  ListChecks,
  Bell,
  Code2,
  TrendingUp,
  FileSpreadsheet,
} from 'lucide-react';
import { healthApi, notificationApi } from '../../services/api';
import { HealthReadyResponse } from '../../types';
import { useAuth } from '../../context/AuthContext';
import { ThemeToggle } from '../common/ThemeToggle';
import { ProfileMenu } from './ProfileMenu';

interface NavItem {
  label: string;
  path: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
}

interface DashboardLayoutProps {
  role: 'student' | 'tpo' | 'recruiter' | 'admin';
  title: string;
  subtitle: string;
  children: React.ReactNode;
}

export const DashboardLayout: React.FC<DashboardLayoutProps> = ({
  role,
  title,
  subtitle,
  children,
}) => {
  const { user } = useAuth();
  const [health, setHealth] = useState<HealthReadyResponse | null>(null);
  const [unreadNotifications, setUnreadNotifications] = useState<number>(0);
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);
  const location = useLocation();

  useEffect(() => {
    let isMounted = true;
    healthApi.getReady().then((res) => {
      if (isMounted) setHealth(res);
    });
    if (role === 'student') {
      notificationApi
        .getUnreadCount()
        .then((res) => {
          if (isMounted) setUnreadNotifications(res.unread_count);
        })
        .catch(() => {
          // Silently ignore unread polling errors on public/transitional mounts
        });
    }
    return () => {
      isMounted = false;
    };
  }, [role, location.pathname]);

  // Close mobile menu on route changes
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [location.pathname]);

  const navItemsByRole: Record<'student' | 'tpo' | 'recruiter' | 'admin', NavItem[]> = {
    student: [
      { label: 'Overview', path: '/student', icon: LayoutDashboard },
      { label: 'My Academic Profile', path: '/student/profile', icon: User },
      { label: 'Resume Intelligence', path: '/student/resumes', icon: FileText },
      { label: 'Explore Jobs', path: '/student/jobs', icon: Briefcase },
      { label: 'Application Tracker', path: '/student/applications', icon: ListChecks },
      { label: 'AI Career Assistant', path: '/student/career-assistant', icon: Bot },
      { label: 'Interview Studio', path: '/student/interview-studio', icon: Mic },
      { label: 'Preparation Arena', path: '/student/arena', icon: Code2 },
      { label: 'Readiness Index', path: '/student/readiness', icon: ShieldCheck },
    ],
    tpo: [
      { label: 'Command Center', path: '/tpo', icon: LayoutDashboard },
      { label: 'Intelligence & Forecasting', path: '/tpo/intelligence', icon: TrendingUp },
      { label: 'Placement Reports', path: '/tpo/reports', icon: FileSpreadsheet },
      { label: 'Placement Drives', path: '/tpo/drives', icon: Calendar },
      { label: 'Campus Interviews', path: '/tpo/interviews', icon: Calendar },
      { label: 'Campus Jobs', path: '/tpo/jobs', icon: Briefcase },
      { label: 'Readiness Analytics', path: '/tpo/readiness', icon: BarChart3 },
      { label: 'Arena Assessments', path: '/tpo/arena', icon: Code2 },
      { label: 'Company Partners', path: '/tpo/companies', icon: Building },
      { label: 'Campus Activity Log', path: '/tpo/activity-logs', icon: ShieldCheck },
      { label: 'Student Cohort Simulator', path: '/tpo', icon: Users },
    ],
    recruiter: [
      { label: 'Hiring Dashboard', path: '/recruiter', icon: LayoutDashboard },
      { label: 'Candidate Pipeline', path: '/recruiter/candidates', icon: Users },
      { label: 'Candidate Comparison', path: '/recruiter/candidate-comparisons', icon: Sparkles },
      { label: 'Job Postings', path: '/recruiter/jobs', icon: Briefcase },
      { label: 'Company Profile', path: '/recruiter/jobs', icon: Building },
      { label: 'Interview Calendar', path: '/recruiter/interviews', icon: Calendar },
    ],
    admin: [
      { label: 'System Overview', path: '/admin', icon: LayoutDashboard },
      { label: 'Audit Logs', path: '/admin/audit-logs', icon: ShieldCheck },
      { label: 'Placement Reports', path: '/tpo/reports', icon: FileSpreadsheet },
      { label: 'User Directory', path: '/admin', icon: Users },
      { label: 'Institutions & Branches', path: '/admin', icon: Building },
      { label: 'AI Diagnostics', path: '/admin', icon: Server },
    ],
  };

  const roleLabels = {
    student: { name: 'Student Portal', badge: 'Private Scope' },
    tpo: { name: 'TPO Console', badge: 'Institutional Scope' },
    recruiter: { name: 'Recruiter Hub', badge: 'Corporate Scope' },
    admin: { name: 'System Admin', badge: 'Platform Scope' },
  };

  const isPathActive = (itemPath: string) => {
    // Root role path requires exact match
    if (['/student', '/tpo', '/recruiter', '/admin'].includes(itemPath)) {
      return location.pathname === itemPath;
    }
    // Sub-paths match prefix or exact
    return location.pathname === itemPath || location.pathname.startsWith(itemPath + '/');
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex flex-col w-full overflow-x-hidden transition-colors">
      {/* Top Header */}
      <header className="sticky top-0 z-40 bg-white/95 dark:bg-slate-900/95 backdrop-blur border-b border-slate-200/90 dark:border-slate-800 h-16 flex items-center justify-between px-4 sm:px-6 transition-colors">
        <div className="flex items-center space-x-3">
          {/* Mobile hamburger toggle */}
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-1.5 rounded-lg text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800"
            aria-label="Toggle navigation menu"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>

          <Link to="/" className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center text-white shadow-sm shrink-0">
              <Sparkles className="w-4 h-4" />
            </div>
            <span className="font-bold text-sm tracking-tight text-slate-900 dark:text-slate-100 hidden sm:inline">
              Placement<span className="text-brand-600 dark:text-brand-400">Intelligence</span>
            </span>
          </Link>
          <span className="text-slate-300 dark:text-slate-700">/</span>
          <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 shrink-0">
            {roleLabels[role].name}
          </span>
          <span className="text-[11px] text-slate-400 dark:text-slate-500 hidden lg:inline">
            ({roleLabels[role].badge})
          </span>
        </div>

        {/* Multi-Platform Fast Switcher for Admin / Full Access Accounts */}
        {(user?.email === 'maheshwarijaya03@gmail.com' || user?.role === 'admin') && (
          <div className="hidden lg:flex items-center gap-1 p-1 bg-slate-100 dark:bg-slate-800/80 rounded-xl border border-slate-200 dark:border-slate-700/80 shadow-xs">
            <Link
              to="/student"
              className={`px-2.5 py-1 text-[11px] font-semibold rounded-lg transition-all ${
                role === 'student'
                  ? 'bg-white dark:bg-slate-900 text-brand-600 dark:text-brand-400 shadow-xs'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
              }`}
            >
              Student Portal
            </Link>
            <Link
              to="/tpo"
              className={`px-2.5 py-1 text-[11px] font-semibold rounded-lg transition-all ${
                role === 'tpo'
                  ? 'bg-white dark:bg-slate-900 text-brand-600 dark:text-brand-400 shadow-xs'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
              }`}
            >
              TPO Console
            </Link>
            <Link
              to="/recruiter"
              className={`px-2.5 py-1 text-[11px] font-semibold rounded-lg transition-all ${
                role === 'recruiter'
                  ? 'bg-white dark:bg-slate-900 text-brand-600 dark:text-brand-400 shadow-xs'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
              }`}
            >
              Recruiter Hub
            </Link>
            <Link
              to="/admin"
              className={`px-2.5 py-1 text-[11px] font-semibold rounded-lg transition-all ${
                role === 'admin'
                  ? 'bg-white dark:bg-slate-900 text-brand-600 dark:text-brand-400 shadow-xs'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
              }`}
            >
              Admin Center
            </Link>
          </div>
        )}

        {/* System Health, Theme Toggle & Profile Menu */}
        <div className="flex items-center space-x-2.5 text-xs">
          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300">
            {health?.database.status === 'connected' ? (
              <>
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                <span className="text-[11px] font-medium text-emerald-700 dark:text-emerald-400">DB: Connected</span>
              </>
            ) : (
              <>
                <span className="w-2 h-2 rounded-full bg-amber-500"></span>
                <span className="text-[11px] font-medium text-amber-700 dark:text-amber-400">DB: Standby / Configuring</span>
              </>
            )}
          </div>

          {role === 'student' && (
            <Link
              to="/student/applications"
              aria-label="Application Tracker & Notifications"
              className="relative p-2 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-200/80 dark:border-slate-700/80 transition-colors"
              title="Application Tracker & Smart Notifications"
            >
              <Bell className="w-4 h-4" />
              {unreadNotifications > 0 && (
                <span className="absolute -top-1 -right-1 min-w-[16px] h-4 px-1 rounded-full bg-rose-600 text-white text-[10px] font-bold flex items-center justify-center">
                  {unreadNotifications > 99 ? '99+' : unreadNotifications}
                </span>
              )}
            </Link>
          )}

          <ThemeToggle />

          <ProfileMenu />
        </div>
      </header>

      {/* Mobile Drawer Navigation */}
      {mobileMenuOpen && (
        <div className="md:hidden bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 px-4 py-3 shadow-md z-30 space-y-1">
          <div className="text-[11px] uppercase tracking-wider font-semibold text-slate-400 dark:text-slate-500 px-3 py-1">
            Navigation
          </div>
          {navItemsByRole[role].map((item) => {
            const Icon = item.icon;
            const active = isPathActive(item.path);
            return (
              <Link
                key={item.label}
                to={item.path}
                onClick={() => setMobileMenuOpen(false)}
                className={`flex items-center justify-between px-3 py-2 text-xs font-medium rounded-lg transition-colors ${
                  active
                    ? 'bg-brand-50 dark:bg-brand-950/60 text-brand-700 dark:text-brand-300 font-semibold'
                    : 'text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-slate-100'
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <Icon className={`w-4 h-4 ${active ? 'text-brand-600 dark:text-brand-400' : 'text-slate-400 dark:text-slate-500'}`} />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span className="text-[9px] uppercase px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-400 font-semibold">
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
          <div className="pt-2 mt-2 border-t border-slate-100 dark:border-slate-800">
            <Link
              to="/settings"
              onClick={() => setMobileMenuOpen(false)}
              className={`flex items-center gap-2.5 px-3 py-2 text-xs font-medium rounded-lg transition-colors ${
                location.pathname.endsWith('/settings')
                  ? 'bg-brand-50 dark:bg-brand-950/60 text-brand-700 dark:text-brand-300 font-semibold'
                  : 'text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-slate-100'
              }`}
            >
              <Settings className={`w-4 h-4 ${location.pathname.endsWith('/settings') ? 'text-brand-600 dark:text-brand-400' : 'text-slate-400 dark:text-slate-500'}`} />
              <span>App Settings</span>
            </Link>
          </div>
        </div>
      )}

      {/* Main Container */}
      <div className="flex-1 flex max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 gap-6">
        {/* Desktop Sidebar */}
        <aside className="w-56 shrink-0 hidden md:block">
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-3 shadow-xs sticky top-24 transition-colors">
            <div className="text-[11px] uppercase tracking-wider font-semibold text-slate-400 dark:text-slate-500 px-3 py-2">
              Navigation
            </div>
            <nav className="space-y-1">
              {navItemsByRole[role].map((item) => {
                const Icon = item.icon;
                const active = isPathActive(item.path);
                return (
                  <Link
                    key={item.label}
                    to={item.path}
                    className={`flex items-center justify-between px-3 py-2 text-xs font-medium rounded-lg transition-colors ${
                      active
                        ? 'bg-brand-50 dark:bg-brand-950/60 text-brand-700 dark:text-brand-300 font-semibold'
                        : 'text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-slate-100'
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      <Icon className={`w-4 h-4 ${active ? 'text-brand-600 dark:text-brand-400' : 'text-slate-400 dark:text-slate-500'}`} />
                      <span>{item.label}</span>
                    </div>
                    {item.badge && (
                      <span className="text-[9px] uppercase px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-400 font-semibold">
                        {item.badge}
                      </span>
                    )}
                  </Link>
                );
              })}
            </nav>

            <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-800">
              <div className="text-[10px] uppercase tracking-wider font-semibold text-slate-400 dark:text-slate-500 px-3 pb-1.5">
                Preferences
              </div>
              <Link
                to="/settings"
                className={`flex items-center gap-2.5 px-3 py-2 text-xs font-medium rounded-lg transition-colors ${
                  location.pathname.endsWith('/settings')
                    ? 'bg-brand-50 dark:bg-brand-950/60 text-brand-700 dark:text-brand-300 font-semibold'
                    : 'text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-slate-100'
                }`}
              >
                <Settings className={`w-4 h-4 ${location.pathname.endsWith('/settings') ? 'text-brand-600 dark:text-brand-400' : 'text-slate-400 dark:text-slate-500'}`} />
                <span>App Settings</span>
              </Link>
            </div>
          </div>
        </aside>

        {/* Main Content Area */}
        <main className="flex-1 min-w-0 w-full overflow-hidden">
          <div className="mb-6">
            <h1 className="text-xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">{title}</h1>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{subtitle}</p>
          </div>
          {children}
        </main>
      </div>
    </div>
  );
};
