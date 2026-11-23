import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Sparkles, Activity, LogIn, UserPlus } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { ThemeToggle } from '../common/ThemeToggle';
import { ProfileMenu } from './ProfileMenu';

export const Navbar: React.FC = () => {
  const location = useLocation();
  const { user, isAuthenticated } = useAuth();

  const isCurrent = (path: string) => location.pathname.startsWith(path);

  return (
    <header className="sticky top-0 z-50 bg-white/95 dark:bg-slate-900/95 backdrop-blur border-b border-slate-200/80 dark:border-slate-800 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Brand */}
          <Link to="/" className="flex items-center space-x-3 group">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-700 via-brand-600 to-indigo-500 flex items-center justify-center text-white shadow-md shadow-brand-500/20 group-hover:scale-105 transition-transform">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <div className="font-bold text-slate-900 dark:text-slate-100 leading-tight tracking-tight flex items-center gap-1.5">
                Placement<span className="text-brand-600 dark:text-brand-400">Intelligence</span>
              </div>
              <p className="text-[11px] text-slate-500 dark:text-slate-400 font-medium">Campus Recruitment Platform</p>
            </div>
          </Link>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center space-x-1">
            {isAuthenticated && user ? (
              <>
                <Link
                  to={`/dashboard/${user.role}`}
                  className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
                    isCurrent(`/dashboard/${user.role}`)
                      ? 'bg-brand-50 dark:bg-brand-950/60 text-brand-700 dark:text-brand-300 font-bold'
                      : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800'
                  }`}
                >
                  My Dashboard ({user.role.toUpperCase()})
                </Link>
                {user.role === 'admin' && (
                  <Link
                    to="/dashboard/tpo"
                    className="px-3 py-1.5 text-xs font-semibold text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
                  >
                    TPO View
                  </Link>
                )}
              </>
            ) : (
              <>
                <Link
                  to="/student"
                  className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
                    isCurrent('/student')
                      ? 'bg-brand-50 dark:bg-brand-950/60 text-brand-700 dark:text-brand-300 font-bold'
                      : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800'
                  }`}
                >
                  Student Portal
                </Link>
                <Link
                  to="/tpo"
                  className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
                    isCurrent('/tpo')
                      ? 'bg-brand-50 dark:bg-brand-950/60 text-brand-700 dark:text-brand-300 font-bold'
                      : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800'
                  }`}
                >
                  TPO Console
                </Link>
                <Link
                  to="/recruiter"
                  className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
                    isCurrent('/recruiter')
                      ? 'bg-brand-50 dark:bg-brand-950/60 text-brand-700 dark:text-brand-300 font-bold'
                      : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800'
                  }`}
                >
                  Recruiter Hub
                </Link>
              </>
            )}
          </nav>

          {/* Theme, API Docs & Profile/Auth */}
          <div className="flex items-center space-x-2.5">
            <a
              href="http://127.0.0.1:8000/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors"
            >
              <Activity className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
              API Docs
            </a>

            <ThemeToggle />

            {isAuthenticated && user ? (
              <ProfileMenu />
            ) : (
              <div className="flex items-center gap-2">
                <Link
                  to="/login"
                  className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-semibold text-slate-700 dark:text-slate-200 hover:text-slate-900 dark:hover:text-white bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700 rounded-lg transition-colors shadow-sm"
                >
                  <LogIn className="w-3.5 h-3.5" />
                  Sign In
                </Link>
                <Link
                  to="/register"
                  className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors shadow-sm"
                >
                  <UserPlus className="w-3.5 h-3.5" />
                  Register
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
