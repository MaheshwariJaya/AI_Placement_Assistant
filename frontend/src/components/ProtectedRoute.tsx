import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { UserRole } from '../types';
import { ShieldAlert, Loader2 } from 'lucide-react';

interface ProtectedRouteProps {
  children?: React.ReactNode;
  allowedRoles?: UserRole[];
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, allowedRoles }) => {
  const { user, isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center p-8">
        <Loader2 className="w-10 h-10 text-indigo-600 dark:text-indigo-400 animate-spin mb-4" />
        <p className="text-slate-600 dark:text-slate-400 font-medium text-sm">Authenticating session security...</p>
      </div>
    );
  }

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  const isSuperAccess = user.email === 'maheshwarijaya03@gmail.com' || user.role === 'admin';

  if (allowedRoles && allowedRoles.length > 0 && !allowedRoles.includes(user.role) && !isSuperAccess) {
    return (
      <div className="max-w-2xl mx-auto my-12 p-8 bg-white dark:bg-slate-900 border border-rose-200 dark:border-rose-900 rounded-xl shadow-sm text-center">
        <div className="w-16 h-16 bg-rose-50 dark:bg-rose-950/60 text-rose-600 dark:text-rose-400 rounded-full flex items-center justify-center mx-auto mb-4">
          <ShieldAlert className="w-8 h-8" />
        </div>
        <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100 mb-2">Access Restricted</h2>
        <p className="text-slate-600 dark:text-slate-400 text-sm mb-6 leading-relaxed">
          Your account role (<span className="font-semibold text-slate-800 dark:text-slate-200 uppercase">{user.role}</span>) is not authorized
          to access this dashboard module. Required role permissions: {allowedRoles.map((r) => r.toUpperCase()).join(', ')}.
        </p>
        <a
          href={`/dashboard/${user.role}`}
          className="inline-flex items-center px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-sm rounded-lg transition-colors shadow-sm"
        >
          Return to My Authorized Dashboard
        </a>
      </div>
    );
  }

  return children ? <>{children}</> : null;
};

