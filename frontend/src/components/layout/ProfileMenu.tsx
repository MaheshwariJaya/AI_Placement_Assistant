import React, { useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  Activity,
  BadgeCheck,
  Briefcase,
  Calendar,
  ChevronDown,
  ExternalLink,
  GraduationCap,
  KeyRound,
  LogOut,
  Settings,
  ShieldCheck,
  User as UserIcon,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { UserRole } from '../../types';

const ROLE_DISPLAY: Record<UserRole, string> = {
  student: 'Student',
  tpo: 'TPO Officer',
  recruiter: 'Recruiter',
  admin: 'Admin',
};

const ROLE_WORKSPACE_ITEM: Record<
  UserRole,
  { label: string; to: string; icon: React.ComponentType<{ className?: string }> }
> = {
  student: { label: 'Academic Profile', to: '/student/profile', icon: GraduationCap },
  tpo: { label: 'Recruitment Drives', to: '/tpo/jobs', icon: Calendar },
  recruiter: { label: 'Company & Postings', to: '/recruiter/jobs', icon: Briefcase },
  admin: { label: 'System Registry', to: '/admin', icon: ShieldCheck },
};

const getInitials = (name?: string): string => {
  if (!name) return 'U';
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
  return `${parts[0].charAt(0)}${parts[parts.length - 1].charAt(0)}`.toUpperCase();
};

export const ProfileMenu: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setOpen(false);
  }, [location.pathname, location.search]);

  useEffect(() => {
    if (!open) return;
    const handleOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleOutside);
    document.addEventListener('keydown', handleKey);
    return () => {
      document.removeEventListener('mousedown', handleOutside);
      document.removeEventListener('keydown', handleKey);
    };
  }, [open]);

  if (!user) return null;

  const workspaceItem = ROLE_WORKSPACE_ITEM[user.role];
  const WorkspaceIcon = workspaceItem.icon;

  const handleLogout = async () => {
    setSigningOut(true);
    try {
      await logout();
      setOpen(false);
      navigate('/login');
    } finally {
      setSigningOut(false);
    }
  };

  return (
    <div ref={menuRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="Open profile menu"
        className="inline-flex items-center gap-2 pl-1.5 pr-2.5 py-1 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700/80 transition-colors cursor-pointer shadow-xs"
      >
        <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-brand-700 via-brand-600 to-indigo-500 text-white flex items-center justify-center font-bold text-[11px] shrink-0">
          {getInitials(user.full_name)}
        </div>
        <div className="hidden sm:block text-left leading-tight max-w-[140px]">
          <div className="text-xs font-semibold text-slate-900 dark:text-slate-100 truncate">
            {user.full_name}
          </div>
          <div className="text-[10px] font-medium text-slate-500 dark:text-slate-400">
            {ROLE_DISPLAY[user.role]}
          </div>
        </div>
        <ChevronDown
          className={`w-3.5 h-3.5 text-slate-400 dark:text-slate-400 transition-transform duration-150 ${
            open ? 'rotate-180' : ''
          }`}
        />
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 mt-2 w-72 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xl py-2 z-50"
        >
          {/* User Identity Card */}
          <div className="px-4 py-3 border-b border-slate-100 dark:border-slate-800">
            <div className="flex items-start gap-2.5">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-brand-700 via-brand-600 to-indigo-500 text-white flex items-center justify-center font-bold text-xs shrink-0">
                {getInitials(user.full_name)}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1">
                  <span className="text-sm font-bold text-slate-900 dark:text-slate-100 truncate">
                    {user.full_name}
                  </span>
                  {user.is_verified && (
                    <span title="Verified Account">
                      <BadgeCheck className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                    </span>
                  )}
                </div>
                <div className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
                  {user.email}
                </div>
                <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wide bg-brand-50 text-brand-700 dark:bg-brand-950/70 dark:text-brand-300 border border-brand-200/70 dark:border-brand-800">
                    {ROLE_DISPLAY[user.role]}
                  </span>
                  {(user.email === 'maheshwarijaya03@gmail.com' || user.role === 'admin') && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 dark:bg-emerald-950/70 dark:text-emerald-300 border border-emerald-200/70 dark:border-emerald-800">
                      Master Full Access
                    </span>
                  )}
                  {user.roll_number && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                      {user.roll_number}
                    </span>
                  )}
                </div>
                {user.institution_name && (
                  <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-1 truncate">
                    {user.institution_name}
                    {user.department_name ? ` • ${user.department_name}` : ''}
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Account & Profile Links */}
          <div className="py-1.5 px-1.5 space-y-0.5">
            <Link
              role="menuitem"
              to="/settings?tab=profile"
              onClick={() => setOpen(false)}
              className="flex items-center gap-2.5 px-3 py-2 text-xs font-medium rounded-lg text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            >
              <UserIcon className="w-4 h-4 text-slate-400 dark:text-slate-400 shrink-0" />
              <div className="flex-1">
                <div>My Profile</div>
                <div className="text-[10px] text-slate-400 dark:text-slate-500">
                  Name, phone &amp; account details
                </div>
              </div>
            </Link>

            <Link
              role="menuitem"
              to={workspaceItem.to}
              onClick={() => setOpen(false)}
              className="flex items-center gap-2.5 px-3 py-2 text-xs font-medium rounded-lg text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            >
              <WorkspaceIcon className="w-4 h-4 text-slate-400 dark:text-slate-400 shrink-0" />
              <span>{workspaceItem.label}</span>
            </Link>

            <Link
              role="menuitem"
              to="/settings?tab=appearance"
              onClick={() => setOpen(false)}
              className="flex items-center gap-2.5 px-3 py-2 text-xs font-medium rounded-lg text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            >
              <Settings className="w-4 h-4 text-slate-400 dark:text-slate-400 shrink-0" />
              <div className="flex-1">
                <div>App Settings</div>
                <div className="text-[10px] text-slate-400 dark:text-slate-500">
                  Theme, layout density &amp; preferences
                </div>
              </div>
            </Link>

            <Link
              role="menuitem"
              to="/settings?tab=security"
              onClick={() => setOpen(false)}
              className="flex items-center gap-2.5 px-3 py-2 text-xs font-medium rounded-lg text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            >
              <KeyRound className="w-4 h-4 text-slate-400 dark:text-slate-400 shrink-0" />
              <span>Security &amp; Password</span>
            </Link>
          </div>

          {/* Master Platform Portals Switcher */}
          {(user.email === 'maheshwarijaya03@gmail.com' || user.role === 'admin') && (
            <div className="py-2 px-2 border-t border-slate-100 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-800/40">
              <div className="px-1.5 pb-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 flex items-center justify-between">
                <span>Multi-Platform Portals</span>
                <span className="text-[9px] px-1.5 py-0.2 bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 rounded font-semibold">Unlocked</span>
              </div>
              <div className="grid grid-cols-2 gap-1.5">
                <Link
                  role="menuitem"
                  to="/student"
                  onClick={() => setOpen(false)}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 text-[11px] font-semibold rounded-lg bg-white dark:bg-slate-800 border border-slate-200/80 dark:border-slate-700/80 text-slate-800 dark:text-slate-100 hover:border-brand-500 hover:text-brand-600 dark:hover:text-brand-400 transition-all shadow-xs"
                >
                  <GraduationCap className="w-3.5 h-3.5 text-brand-600 dark:text-brand-400 shrink-0" />
                  <span>Student Portal</span>
                </Link>
                <Link
                  role="menuitem"
                  to="/tpo"
                  onClick={() => setOpen(false)}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 text-[11px] font-semibold rounded-lg bg-white dark:bg-slate-800 border border-slate-200/80 dark:border-slate-700/80 text-slate-800 dark:text-slate-100 hover:border-indigo-500 hover:text-indigo-600 dark:hover:text-indigo-400 transition-all shadow-xs"
                >
                  <Calendar className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400 shrink-0" />
                  <span>TPO Console</span>
                </Link>
                <Link
                  role="menuitem"
                  to="/recruiter"
                  onClick={() => setOpen(false)}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 text-[11px] font-semibold rounded-lg bg-white dark:bg-slate-800 border border-slate-200/80 dark:border-slate-700/80 text-slate-800 dark:text-slate-100 hover:border-blue-500 hover:text-blue-600 dark:hover:text-blue-400 transition-all shadow-xs"
                >
                  <Briefcase className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400 shrink-0" />
                  <span>Recruiter Hub</span>
                </Link>
                <Link
                  role="menuitem"
                  to="/admin"
                  onClick={() => setOpen(false)}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 text-[11px] font-semibold rounded-lg bg-white dark:bg-slate-800 border border-slate-200/80 dark:border-slate-700/80 text-slate-800 dark:text-slate-100 hover:border-purple-500 hover:text-purple-600 dark:hover:text-purple-400 transition-all shadow-xs"
                >
                  <ShieldCheck className="w-3.5 h-3.5 text-purple-600 dark:text-purple-400 shrink-0" />
                  <span>Admin Center</span>
                </Link>
              </div>
            </div>
          )}

          {/* Utility Links */}
          <div className="py-1.5 px-1.5 border-t border-slate-100 dark:border-slate-800">
            <a
              role="menuitem"
              href="http://127.0.0.1:8000/docs"
              target="_blank"
              rel="noopener noreferrer"
              onClick={() => setOpen(false)}
              className="flex items-center justify-between px-3 py-2 text-xs font-medium rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            >
              <span className="flex items-center gap-2.5">
                <Activity className="w-4 h-4 text-emerald-500 shrink-0" />
                API Documentation
              </span>
              <ExternalLink className="w-3.5 h-3.5 text-slate-400" />
            </a>
          </div>

          {/* Sign Out */}
          <div className="pt-1.5 px-1.5 border-t border-slate-100 dark:border-slate-800">
            <button
              type="button"
              role="menuitem"
              disabled={signingOut}
              onClick={handleLogout}
              className="w-full flex items-center gap-2.5 px-3 py-2 text-xs font-semibold rounded-lg text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/50 transition-colors disabled:opacity-50"
            >
              <LogOut className="w-4 h-4 shrink-0" />
              <span>{signingOut ? 'Signing Out...' : 'Sign Out'}</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

