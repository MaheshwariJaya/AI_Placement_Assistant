import React, { useState, useEffect } from 'react';
import { DashboardLayout } from '../../components/layout/DashboardLayout';
import { Card, CardHeader } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import {
  ShieldCheck,
  Users,
  Building,
  Lock,
  RefreshCw,
  Server,
  Briefcase,
} from 'lucide-react';
import { placementApi, healthApi } from '../../services/api';
import { AdminOverviewResponse, HealthReadyResponse } from '../../types';

export const AdminDashboard: React.FC = () => {
  const [stats, setStats] = useState<AdminOverviewResponse | null>(null);
  const [health, setHealth] = useState<HealthReadyResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [overviewData, healthData] = await Promise.all([
        placementApi.getAdminOverview(),
        healthApi.getReady(),
      ]);
      setStats(overviewData);
      setHealth(healthData);
    } catch (err: any) {
      console.error('Failed to load admin stats:', err);
      setError(err?.response?.data?.detail || 'Failed to fetch platform registry metrics.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const roleColors: Record<string, string> = {
    Students: 'bg-brand-600',
    Recruiters: 'bg-sky-600',
    'TPO Coordinators': 'bg-indigo-600',
    'System Administrators': 'bg-slate-700',
  };

  return (
    <DashboardLayout
      role="admin"
      title="System Administration & Multi-Tenant Registry"
      subtitle="Platform Scope: User directory management, institutional metadata, and AI provider diagnostics."
    >
      {/* Top Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
          <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
            Multi-Tenant PostgreSQL Instance
          </span>
          <Badge variant="neutral" className="text-[10px] font-mono">
            Schema: {health?.database?.schema || '—'}
          </Badge>
        </div>
        <Button
          size="sm"
          variant="outline"
          onClick={fetchData}
          disabled={loading}
          className="text-xs flex items-center gap-1.5"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh Registry
        </Button>
      </div>

      {error && (
        <div className="p-4 mb-6 rounded-xl bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-200 text-xs flex items-center justify-between">
          <span>{error}</span>
          <Button size="sm" variant="outline" onClick={fetchData}>
            Retry
          </Button>
        </div>
      )}

      {/* System KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Card>
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Total Registered Users
            </span>
            <span className="w-8 h-8 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 flex items-center justify-center">
              <Users className="w-4 h-4" />
            </span>
          </div>
          <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-2">
            {stats ? stats.total_users : '...'}
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">Across 4 System Roles</p>
        </Card>

        <Card>
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Collegiate Institutions
            </span>
            <span className="w-8 h-8 rounded-lg bg-brand-50 dark:bg-brand-950/60 text-brand-600 dark:text-brand-400 flex items-center justify-center">
              <Building className="w-4 h-4" />
            </span>
          </div>
          <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-2">
            {stats ? `${stats.institutions_count} Active` : '...'}
          </div>
          <p className="text-[11px] text-brand-600 dark:text-brand-400 mt-1">
            {stats ? `${stats.departments_count} Academic Branches` : 'MBM University'}
          </p>
        </Card>

        <Card>
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Hiring Partners
            </span>
            <span className="w-8 h-8 rounded-lg bg-sky-50 dark:bg-sky-950/60 text-sky-600 dark:text-sky-400 flex items-center justify-center">
              <Building className="w-4 h-4" />
            </span>
          </div>
          <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-2">
            {stats ? `${stats.companies_count} Companies` : '...'}
          </div>
          <p className="text-[11px] text-sky-600 dark:text-sky-400 mt-1">
            {stats ? `${stats.jobs_count} Published Jobs` : 'Corporate Accounts'}
          </p>
        </Card>

        <Card>
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Security & Audit
            </span>
            <span className="w-8 h-8 rounded-lg bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 flex items-center justify-center">
              <ShieldCheck className="w-4 h-4" />
            </span>
          </div>
          <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-2">Enforced</div>
          <p className="text-[11px] text-emerald-600 dark:text-emerald-400 mt-1">
            {stats ? `${stats.applications_count} Secured Applications` : 'RBAC + Tenancy Scoping'}
          </p>
        </Card>
      </div>

      {/* AI Diagnostic Card & User Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader
            title="AI Engine Configuration & Status"
            subtitle="Environment-driven multi-provider switchboard"
          />
          <div className="space-y-3 text-xs">
            <div className="p-3 bg-slate-50 dark:bg-slate-800/70 rounded-lg border border-slate-200/80 dark:border-slate-700 space-y-2.5">
              <div className="flex items-center justify-between">
                <span className="text-slate-500 dark:text-slate-400 font-medium">Active AI Engine:</span>
                <Badge variant={health?.ai_engine?.active_provider ? 'brand' : 'neutral'}>
                  {health?.ai_engine?.active_provider
                    ? `${health.ai_engine.active_provider.toUpperCase()} (${health.status === 'ready' ? 'Online' : 'Standby'})`
                    : 'Loading...'}
                </Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-500 dark:text-slate-400 font-medium">Model Deployment:</span>
                <span className="font-mono text-slate-800 dark:text-slate-200">
                  {health?.ai_engine?.active_provider === 'openai'
                    ? health.ai_engine.openai_model || 'Configured via env'
                    : health?.ai_engine?.active_provider === 'gemini'
                    ? health.ai_engine.gemini_model || 'Configured via env'
                    : health?.ai_engine?.active_provider || '—'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-500 dark:text-slate-400 font-medium">Database Target:</span>
                <span className="font-mono text-slate-800 dark:text-slate-200">
                  {health?.database?.database_name || '—'} ({health?.database?.host || '—'})
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-500 dark:text-slate-400 font-medium">Database Latency:</span>
                <span
                  className={`font-semibold ${
                    health?.database?.status === 'connected' ? 'text-emerald-700 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400'
                  }`}
                >
                  {health?.database?.status === 'connected'
                    ? `Connected (${health.database.latency_ms ?? 0} ms)`
                    : 'Disconnected'}
                </span>
              </div>
            </div>

            <div className="p-3 bg-emerald-50 dark:bg-emerald-950/50 rounded-lg border border-emerald-100 dark:border-emerald-900 flex items-start gap-2.5">
              <Lock className="w-4 h-4 text-emerald-600 dark:text-emerald-400 mt-0.5 shrink-0" />
              <div className="text-[11px] text-emerald-800 dark:text-emerald-200 leading-relaxed">
                <strong>Zero Secret Leakage:</strong> All API keys and database credentials are read
                strictly from server <code>.env</code> and excluded from version control and browser state.
              </div>
            </div>
          </div>
        </Card>

        <Card>
          <CardHeader
            title="User Role Distribution (Tenancy Matrix)"
            subtitle="Normalized live counts across PostgreSQL 'users' table"
          />
          <div className="space-y-3 text-xs">
            {stats?.role_distribution && stats.role_distribution.length > 0 ? (
              stats.role_distribution.map((r) => (
                <div
                  key={r.role}
                  className="flex items-center justify-between p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/70 border border-slate-100 dark:border-slate-800 hover:bg-slate-100/60 dark:hover:bg-slate-800 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <span
                      className={`w-2.5 h-2.5 rounded-full ${roleColors[r.role] || 'bg-slate-500'}`}
                    ></span>
                    <span className="font-semibold text-slate-800 dark:text-slate-200">{r.role}</span>
                  </div>
                  <span className="font-bold text-slate-900 dark:text-slate-100">
                    {r.count} ({r.percentage}%)
                  </span>
                </div>
              ))
            ) : (
              <div className="text-center py-6 text-slate-400 dark:text-slate-500 text-xs">
                {loading ? 'Reading user directory...' : 'No users found'}
              </div>
            )}
          </div>
        </Card>
      </div>
    </DashboardLayout>
  );
};
