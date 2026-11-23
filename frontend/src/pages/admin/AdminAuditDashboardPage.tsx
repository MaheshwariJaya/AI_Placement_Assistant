import React, { useState, useEffect, useCallback } from 'react';
import { DashboardLayout } from '../../components/layout/DashboardLayout';
import { Card, CardHeader } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import {
  ShieldCheck,
  ShieldAlert,
  Search,
  RefreshCw,
  Filter,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  User,
  Clock,
  KeyRound,
  FileText,
  Briefcase,
  SlidersHorizontal,
  ChevronLeft,
  ChevronRight,
  Eye,
  Hash,
  Database,
  Lock,
  ExternalLink,
  X,
  FileCode,
  Calendar,
} from 'lucide-react';
import { auditApi } from '../../services/api';
import {
  AuditLogItem,
  AuditLogListResponse,
  AuditSummaryStats,
  AuditIntegrityVerificationResponse,
  AuditCategoriesResponse,
  AuditFilterParams,
} from '../../types';

export const AdminAuditDashboardPage: React.FC = () => {
  // Main Data States
  const [logsResponse, setLogsResponse] = useState<AuditLogListResponse | null>(null);
  const [stats, setStats] = useState<AuditSummaryStats | null>(null);
  const [taxonomy, setTaxonomy] = useState<AuditCategoriesResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Verification States
  const [verifying, setVerifying] = useState<boolean>(false);
  const [verificationResult, setVerificationResult] = useState<AuditIntegrityVerificationResponse | null>(null);

  // Filter States
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [selectedStatus, setSelectedStatus] = useState<string>('');
  const [dateFrom, setDateFrom] = useState<string>('');
  const [dateTo, setDateTo] = useState<string>('');
  const [currentPage, setCurrentPage] = useState<number>(1);
  const pageSize = 15;

  // Selected Item for Diff Modal
  const [selectedLog, setSelectedLog] = useState<AuditLogItem | null>(null);

  // Fetch Summary Stats & Taxonomy
  const loadInitialData = async () => {
    try {
      const [statsData, taxonomyData] = await Promise.all([
        auditApi.getStats(),
        auditApi.getCategories(),
      ]);
      setStats(statsData);
      setTaxonomy(taxonomyData);
    } catch (err: any) {
      console.error('Failed to load initial audit stats:', err);
    }
  };

  // Fetch Audit Logs with current filters
  const fetchLogs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: AuditFilterParams = {
        page: currentPage,
        limit: pageSize,
      };
      if (searchTerm.trim()) params.search = searchTerm.trim();
      if (selectedCategory) params.category = selectedCategory;
      if (selectedStatus) params.status = selectedStatus;
      if (dateFrom) params.date_from = new Date(dateFrom).toISOString();
      if (dateTo) params.date_to = new Date(dateTo).toISOString();

      const response = await auditApi.getLogs(params);
      setLogsResponse(response);
    } catch (err: any) {
      console.error('Failed to query audit logs:', err);
      setError(err?.response?.data?.detail?.message || 'Failed to fetch centralized audit logs.');
    } finally {
      setLoading(false);
    }
  }, [currentPage, searchTerm, selectedCategory, selectedStatus, dateFrom, dateTo]);

  useEffect(() => {
    loadInitialData();
  }, []);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  // Run Tamper-Evident Chain Integrity Verification
  const handleVerifyIntegrity = async () => {
    setVerifying(true);
    try {
      const res = await auditApi.verifyIntegrity(1000);
      setVerificationResult(res);
      // Reload stats to update status pill
      const updatedStats = await auditApi.getStats();
      setStats(updatedStats);
    } catch (err: any) {
      console.error('Integrity verification failed:', err);
    } finally {
      setVerifying(false);
    }
  };

  // Reset Filters
  const handleResetFilters = () => {
    setSearchTerm('');
    setSelectedCategory('');
    setSelectedStatus('');
    setDateFrom('');
    setDateTo('');
    setCurrentPage(1);
  };

  // Category Styling Helpers
  const getCategoryBadgeClass = (category: string) => {
    switch (category) {
      case 'AUTHENTICATION':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300 border-blue-200 dark:border-blue-800';
      case 'ACADEMIC':
        return 'bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300 border-purple-200 dark:border-purple-800';
      case 'RECRUITMENT':
        return 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-300 border-indigo-200 dark:border-indigo-800';
      case 'RESUME':
        return 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800';
      case 'ADMINISTRATION':
        return 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300 border-amber-200 dark:border-amber-800';
      default:
        return 'bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-300 border-slate-200 dark:border-slate-700';
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'SUCCESS':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
            <CheckCircle2 className="w-3.5 h-3.5" />
            SUCCESS
          </span>
        );
      case 'FAILURE':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-800 dark:bg-rose-950/50 dark:text-rose-300 border border-rose-200 dark:border-rose-800">
            <XCircle className="w-3.5 h-3.5" />
            FAILURE
          </span>
        );
      case 'WARNING':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 dark:bg-amber-950/50 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
            <AlertTriangle className="w-3.5 h-3.5" />
            WARNING
          </span>
        );
      default:
        return <Badge variant="neutral">{status}</Badge>;
    }
  };

  const formatDate = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
      return isoString;
    }
  };

  const truncateHash = (hashStr?: string | null) => {
    if (!hashStr) return 'Genesis';
    return `${hashStr.substring(0, 8)}...${hashStr.substring(hashStr.length - 8)}`;
  };

  return (
    <DashboardLayout
      role="admin"
      title="Centralized Audit Logging & Activity Monitoring"
      subtitle="Cryptographically verified, append-only immutable audit trail across identity, academics, and recruitment."
    >
      <div className="space-y-6">
        {/* Top Header Card & Integrity Verifier Trigger */}
        <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 border border-slate-800 rounded-2xl p-6 text-white shadow-xl">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-indigo-500/20 border border-indigo-400/30 rounded-xl">
                  <ShieldCheck className="w-6 h-6 text-indigo-400" />
                </div>
                <div>
                  <h1 className="text-2xl font-bold tracking-tight">Institutional Audit & Activity Trail</h1>
                  <p className="text-sm text-slate-300 mt-1">
                    SHA-256 hash chaining ensures complete tamper evidence. Secret data is automatically sanitized.
                  </p>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <Button
                variant="outline"
                onClick={handleVerifyIntegrity}
                disabled={verifying}
                className="bg-indigo-600/30 border-indigo-400/40 hover:bg-indigo-600/50 text-white font-medium shadow-md"
              >
                {verifying ? (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    Verifying Chain...
                  </>
                ) : (
                  <>
                    <ShieldCheck className="w-4 h-4 mr-2 text-indigo-300" />
                    Verify Chain Integrity
                  </>
                )}
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  fetchLogs();
                  loadInitialData();
                }}
                className="bg-slate-800/60 border-slate-700 hover:bg-slate-800 text-slate-200"
              >
                <RefreshCw className="w-4 h-4" />
              </Button>
            </div>
          </div>

          {/* Verification Results Alert */}
          {verificationResult && (
            <div
              className={`mt-4 p-4 rounded-xl border flex items-start gap-3 transition-all ${
                verificationResult.is_valid
                  ? 'bg-emerald-950/60 border-emerald-500/40 text-emerald-200'
                  : 'bg-rose-950/60 border-rose-500/40 text-rose-200'
              }`}
            >
              {verificationResult.is_valid ? (
                <ShieldCheck className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
              ) : (
                <ShieldAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
              )}
              <div className="text-sm flex-1">
                <p className="font-semibold">
                  {verificationResult.is_valid
                    ? 'Cryptographic Hash Chain 100% Intact'
                    : 'Chain Integrity Violation Detected!'}
                </p>
                <p className="mt-0.5 text-xs opacity-90">{verificationResult.details}</p>
                {verificationResult.invalid_records.length > 0 && (
                  <p className="mt-1 font-mono text-xs">
                    Compromised Record IDs: {verificationResult.invalid_records.join(', ')}
                  </p>
                )}
              </div>
              <button
                onClick={() => setVerificationResult(null)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>

        {/* KPI Metrics Summary Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="border-slate-200 dark:border-slate-800 shadow-sm hover:shadow-md transition">
            <div className="p-5 flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  Total Audit Records
                </p>
                <p className="text-2xl font-bold text-slate-900 dark:text-white mt-1">
                  {stats ? stats.total_events.toLocaleString() : '...'}
                </p>
                <span className="text-xs text-slate-500 dark:text-slate-400 mt-1 block">
                  Append-only immutable log
                </span>
              </div>
              <div className="p-3 bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-xl">
                <Database className="w-6 h-6" />
              </div>
            </div>
          </Card>

          <Card className="border-slate-200 dark:border-slate-800 shadow-sm hover:shadow-md transition">
            <div className="p-5 flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  Security & Auth Events
                </p>
                <p className="text-2xl font-bold text-slate-900 dark:text-white mt-1">
                  {stats ? stats.security_events.toLocaleString() : '...'}
                </p>
                <span className="text-xs text-slate-500 dark:text-slate-400 mt-1 block">
                  Logins, logouts & tokens
                </span>
              </div>
              <div className="p-3 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 rounded-xl">
                <KeyRound className="w-6 h-6" />
              </div>
            </div>
          </Card>

          <Card className="border-slate-200 dark:border-slate-800 shadow-sm hover:shadow-md transition">
            <div className="p-5 flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  Critical Governance
                </p>
                <p className="text-2xl font-bold text-slate-900 dark:text-white mt-1">
                  {stats ? stats.critical_changes.toLocaleString() : '...'}
                </p>
                <span className="text-xs text-slate-500 dark:text-slate-400 mt-1 block">
                  Academics & offer decisions
                </span>
              </div>
              <div className="p-3 bg-purple-50 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 rounded-xl">
                <Briefcase className="w-6 h-6" />
              </div>
            </div>
          </Card>

          <Card className="border-slate-200 dark:border-slate-800 shadow-sm hover:shadow-md transition">
            <div className="p-5 flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  Chain Tamper Status
                </p>
                <div className="mt-1 flex items-center gap-2">
                  <span
                    className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold ${
                      stats?.integrity_status === 'VERIFIED'
                        ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700'
                        : 'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300 border border-rose-300 dark:border-rose-700'
                    }`}
                  >
                    <ShieldCheck className="w-3.5 h-3.5" />
                    {stats?.integrity_status || 'CHECKING'}
                  </span>
                </div>
                <span className="text-xs text-slate-500 dark:text-slate-400 mt-1 block">
                  {stats?.failed_operations ?? 0} failed ops logged
                </span>
              </div>
              <div className="p-3 bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 rounded-xl">
                <Lock className="w-6 h-6" />
              </div>
            </div>
          </Card>
        </div>

        {/* Filter Toolbar */}
        <Card className="border-slate-200 dark:border-slate-800 p-4 shadow-sm">
          <div className="flex flex-col lg:flex-row gap-4 items-center justify-between">
            {/* Search Input */}
            <div className="relative w-full lg:w-96">
              <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
              <input
                type="text"
                placeholder="Search action, user, or entity..."
                value={searchTerm}
                onChange={(e) => {
                  setSearchTerm(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-full pl-9 pr-4 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            {/* Dropdown Filters */}
            <div className="flex flex-wrap items-center gap-3 w-full lg:w-auto">
              {/* Category */}
              <select
                value={selectedCategory}
                onChange={(e) => {
                  setSelectedCategory(e.target.value);
                  setCurrentPage(1);
                }}
                className="text-sm px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">All Categories</option>
                {taxonomy?.categories.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
                ))}
              </select>

              {/* Status */}
              <select
                value={selectedStatus}
                onChange={(e) => {
                  setSelectedStatus(e.target.value);
                  setCurrentPage(1);
                }}
                className="text-sm px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">All Statuses</option>
                <option value="SUCCESS">Success</option>
                <option value="FAILURE">Failure</option>
                <option value="WARNING">Warning</option>
              </select>

              {/* Date From */}
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => {
                  setDateFrom(e.target.value);
                  setCurrentPage(1);
                }}
                className="text-sm px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                title="Date From"
              />

              {/* Date To */}
              <input
                type="date"
                value={dateTo}
                onChange={(e) => {
                  setDateTo(e.target.value);
                  setCurrentPage(1);
                }}
                className="text-sm px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                title="Date To"
              />

              {/* Reset */}
              {(searchTerm || selectedCategory || selectedStatus || dateFrom || dateTo) && (
                <Button variant="outline" size="sm" onClick={handleResetFilters} className="text-xs">
                  <X className="w-3.5 h-3.5 mr-1" />
                  Reset
                </Button>
              )}
            </div>
          </div>
        </Card>

        {/* Audit Log Table */}
        <Card className="border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
          <CardHeader
            title="Audit Trail Records"
            subtitle={
              logsResponse
                ? `Displaying ${logsResponse.items.length} of ${logsResponse.total} events (Page ${logsResponse.page} of ${logsResponse.total_pages})`
                : 'Loading records...'
            }
          />

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-700 dark:text-slate-300">
              <thead className="text-xs uppercase bg-slate-50 dark:bg-slate-800/80 text-slate-500 dark:text-slate-400 border-y border-slate-200 dark:border-slate-700">
                <tr>
                  <th scope="col" className="px-4 py-3">
                    Timestamp
                  </th>
                  <th scope="col" className="px-4 py-3">
                    Domain
                  </th>
                  <th scope="col" className="px-4 py-3">
                    Action
                  </th>
                  <th scope="col" className="px-4 py-3">
                    Actor / User
                  </th>
                  <th scope="col" className="px-4 py-3">
                    Target Entity
                  </th>
                  <th scope="col" className="px-4 py-3">
                    Result
                  </th>
                  <th scope="col" className="px-4 py-3">
                    Record Hash
                  </th>
                  <th scope="col" className="px-4 py-3 text-right">
                    Inspect
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                {loading ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-12 text-center text-slate-500">
                      <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-500" />
                      Loading audit entries...
                    </td>
                  </tr>
                ) : logsResponse?.items.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-12 text-center text-slate-500">
                      No audit events match the specified query filters.
                    </td>
                  </tr>
                ) : (
                  logsResponse?.items.map((log) => (
                    <tr
                      key={log.id}
                      className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
                    >
                      <td className="px-4 py-3 font-mono text-xs whitespace-nowrap text-slate-600 dark:text-slate-400">
                        {formatDate(log.timestamp)}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span
                          className={`inline-block px-2 py-0.5 text-xs font-semibold rounded-md border ${getCategoryBadgeClass(
                            log.category
                          )}`}
                        >
                          {log.category}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-semibold text-slate-900 dark:text-white">
                        {log.action}
                      </td>
                      <td className="px-4 py-3">
                        {log.user_name || log.user_email ? (
                          <div>
                            <span className="font-medium text-slate-800 dark:text-slate-200 block text-xs">
                              {log.user_name || log.user_email}
                            </span>
                            <span className="text-[11px] text-slate-400 uppercase font-mono">
                              {log.user_role || 'user'}
                            </span>
                          </div>
                        ) : (
                          <span className="text-slate-400 text-xs italic">System / Anonymous</span>
                        )}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className="font-medium text-slate-800 dark:text-slate-200 text-xs">
                          {log.entity_type}
                        </span>
                        {log.entity_id && (
                          <span className="text-slate-400 text-[11px] font-mono ml-1">
                            #{log.entity_id}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">{getStatusBadge(log.status)}</td>
                      <td className="px-4 py-3 font-mono text-[11px] text-slate-500 whitespace-nowrap" title={log.record_hash}>
                        {truncateHash(log.record_hash)}
                      </td>
                      <td className="px-4 py-3 text-right whitespace-nowrap">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setSelectedLog(log)}
                          className="h-8 text-xs hover:bg-indigo-50 dark:hover:bg-indigo-950/40 text-indigo-600 dark:text-indigo-400"
                        >
                          <Eye className="w-3.5 h-3.5 mr-1" />
                          Diff
                        </Button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination Footer */}
          {logsResponse && logsResponse.total_pages > 1 && (
            <div className="px-4 py-3 bg-slate-50 dark:bg-slate-800/50 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between">
              <span className="text-xs text-slate-500">
                Page {logsResponse.page} of {logsResponse.total_pages} ({logsResponse.total} total items)
              </span>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={currentPage <= 1}
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  className="h-8 text-xs"
                >
                  <ChevronLeft className="w-3.5 h-3.5 mr-1" />
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={currentPage >= logsResponse.total_pages}
                  onClick={() => setCurrentPage((p) => Math.min(logsResponse.total_pages, p + 1))}
                  className="h-8 text-xs"
                >
                  Next
                  <ChevronRight className="w-3.5 h-3.5 ml-1" />
                </Button>
              </div>
            </div>
          )}
        </Card>

        {/* Detailed Diff & Metadata Inspector Modal */}
        {selectedLog && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn">
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-4xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
              {/* Modal Header */}
              <div className="p-6 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50/50 dark:bg-slate-800/40">
                <div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`inline-block px-2.5 py-0.5 text-xs font-semibold rounded-md border ${getCategoryBadgeClass(
                        selectedLog.category
                      )}`}
                    >
                      {selectedLog.category}
                    </span>
                    <h2 className="text-lg font-bold text-slate-900 dark:text-white">
                      {selectedLog.action}
                    </h2>
                    {getStatusBadge(selectedLog.status)}
                  </div>
                  <p className="text-xs text-slate-500 mt-1 font-mono">
                    Event UUID: {selectedLog.event_id} | Recorded {formatDate(selectedLog.timestamp)}
                  </p>
                </div>
                <button
                  onClick={() => setSelectedLog(null)}
                  className="p-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Modal Body */}
              <div className="p-6 overflow-y-auto space-y-6 flex-1">
                {/* Actor & Request Metadata */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 bg-slate-50 dark:bg-slate-800/50 p-4 rounded-xl border border-slate-200 dark:border-slate-700/60 text-xs">
                  <div>
                    <span className="text-slate-500 block">Actor Identity:</span>
                    <span className="font-semibold text-slate-800 dark:text-slate-200">
                      {selectedLog.user_name || selectedLog.user_email || 'System Operation'}
                    </span>
                    {selectedLog.user_role && (
                      <span className="block text-[11px] text-indigo-600 dark:text-indigo-400 font-mono">
                        Role: {selectedLog.user_role}
                      </span>
                    )}
                  </div>
                  <div>
                    <span className="text-slate-500 block">Target Entity:</span>
                    <span className="font-semibold text-slate-800 dark:text-slate-200">
                      {selectedLog.entity_type} {selectedLog.entity_id && `(#${selectedLog.entity_id})`}
                    </span>
                    {selectedLog.institution_id && (
                      <span className="block text-[11px] text-slate-500">
                        Institution ID: #{selectedLog.institution_id}
                      </span>
                    )}
                  </div>
                  <div>
                    <span className="text-slate-500 block">Correlation & IP:</span>
                    <span className="font-mono text-slate-800 dark:text-slate-200 block truncate">
                      IP: {selectedLog.ip_address || 'Internal/Direct'}
                    </span>
                    {selectedLog.correlation_id && (
                      <span className="font-mono text-[11px] text-slate-400 block truncate">
                        Corr: {selectedLog.correlation_id}
                      </span>
                    )}
                  </div>
                </div>

                {/* Cryptographic Chain Hashes */}
                <div className="bg-slate-900 text-slate-100 p-4 rounded-xl border border-slate-800 space-y-2 text-xs font-mono">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400 flex items-center gap-1.5 font-sans font-semibold">
                      <Lock className="w-4 h-4 text-indigo-400" />
                      Cryptographic Chain Verification Hashes:
                    </span>
                    <span className="text-[11px] text-emerald-400 font-semibold bg-emerald-950 px-2 py-0.5 rounded border border-emerald-800">
                      SHA-256 Validated
                    </span>
                  </div>
                  <div className="pt-2 border-t border-slate-800">
                    <span className="text-slate-400 block text-[11px]">Previous Block Hash (prev_hash):</span>
                    <span className="text-indigo-300 break-all select-all">
                      {selectedLog.prev_hash || '0000000000000000000000000000000000000000000000000000000000000000 (GENESIS)'}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[11px]">Current Record Hash (record_hash):</span>
                    <span className="text-emerald-300 break-all select-all">{selectedLog.record_hash}</span>
                  </div>
                </div>

                {/* Diff Viewer (Previous vs Updated Values) */}
                {(selectedLog.previous_values || selectedLog.updated_values) && (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
                        <FileCode className="w-4 h-4 text-indigo-500" />
                        State Change Diff (Before vs After)
                      </h3>
                      <span className="text-[11px] text-slate-500 italic">
                        Sensitive tokens and credentials automatically redacted
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* Previous Values */}
                      <div className="p-4 rounded-xl border border-rose-200 dark:border-rose-950/60 bg-rose-50/50 dark:bg-rose-950/20">
                        <h4 className="text-xs font-bold uppercase tracking-wider text-rose-800 dark:text-rose-400 mb-2">
                          Previous State
                        </h4>
                        <pre className="text-xs font-mono text-rose-950 dark:text-rose-200 whitespace-pre-wrap break-all bg-white dark:bg-slate-950 p-3 rounded-lg border border-rose-200 dark:border-rose-900/60 max-h-56 overflow-y-auto">
                          {selectedLog.previous_values
                            ? JSON.stringify(selectedLog.previous_values, null, 2)
                            : '// No previous record (New Entity Creation)'}
                        </pre>
                      </div>

                      {/* Updated Values */}
                      <div className="p-4 rounded-xl border border-emerald-200 dark:border-emerald-950/60 bg-emerald-50/50 dark:bg-emerald-950/20">
                        <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-800 dark:text-emerald-400 mb-2">
                          Updated State
                        </h4>
                        <pre className="text-xs font-mono text-emerald-950 dark:text-emerald-200 whitespace-pre-wrap break-all bg-white dark:bg-slate-950 p-3 rounded-lg border border-emerald-200 dark:border-emerald-900/60 max-h-56 overflow-y-auto">
                          {selectedLog.updated_values
                            ? JSON.stringify(selectedLog.updated_values, null, 2)
                            : '// No state modification recorded'}
                        </pre>
                      </div>
                    </div>
                  </div>
                )}

                {/* Additional Metadata */}
                {selectedLog.metadata && Object.keys(selectedLog.metadata).length > 0 && (
                  <div>
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-2">
                      Event Metadata
                    </h3>
                    <pre className="text-xs font-mono text-slate-800 dark:text-slate-200 whitespace-pre-wrap break-all bg-slate-50 dark:bg-slate-950 p-4 rounded-xl border border-slate-200 dark:border-slate-800 max-h-48 overflow-y-auto">
                      {JSON.stringify(selectedLog.metadata, null, 2)}
                    </pre>
                  </div>
                )}
              </div>

              {/* Modal Footer */}
              <div className="p-4 border-t border-slate-200 dark:border-slate-800 flex justify-end bg-slate-50/50 dark:bg-slate-800/40">
                <Button variant="outline" onClick={() => setSelectedLog(null)}>
                  Close Details
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
};
export default AdminAuditDashboardPage;

