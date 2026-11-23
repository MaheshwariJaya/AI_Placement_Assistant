import React, { useState, useEffect, useCallback } from 'react';
import { DashboardLayout } from '../../components/layout/DashboardLayout';
import { Card, CardHeader } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import {
  ShieldCheck,
  Search,
  RefreshCw,
  Filter,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  User,
  Clock,
  Briefcase,
  ChevronLeft,
  ChevronRight,
  Eye,
  FileCode,
  X,
  GraduationCap,
  Calendar,
} from 'lucide-react';
import { auditApi } from '../../services/api';
import {
  AuditLogItem,
  AuditLogListResponse,
  AuditFilterParams,
} from '../../types';

export const TpoActivityLogPage: React.FC = () => {
  const [logsResponse, setLogsResponse] = useState<AuditLogListResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filter States
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [currentPage, setCurrentPage] = useState<number>(1);
  const pageSize = 15;

  // Selected Log for Diff Modal
  const [selectedLog, setSelectedLog] = useState<AuditLogItem | null>(null);

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

      const response = await auditApi.getLogs(params);
      setLogsResponse(response);
    } catch (err: any) {
      console.error('Failed to query TPO activity logs:', err);
      setError(err?.response?.data?.detail?.message || 'Failed to load institutional activity logs.');
    } finally {
      setLoading(false);
    }
  }, [currentPage, searchTerm, selectedCategory]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  const getCategoryBadgeClass = (category: string) => {
    switch (category) {
      case 'ACADEMIC':
        return 'bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300 border-purple-200 dark:border-purple-800';
      case 'RECRUITMENT':
        return 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-300 border-indigo-200 dark:border-indigo-800';
      case 'RESUME':
        return 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800';
      case 'AUTHENTICATION':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300 border-blue-200 dark:border-blue-800';
      default:
        return 'bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-300 border-slate-200 dark:border-slate-700';
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
      });
    } catch {
      return isoString;
    }
  };

  return (
    <DashboardLayout
      role="tpo"
      title="Campus Activity & Governance Log"
      subtitle="Institutional audit trail of academic metrics, placement drive registrations, screenings, and offer workflows."
    >
      <div className="space-y-6">
        {/* Banner */}
        <div className="bg-gradient-to-r from-indigo-900 to-slate-900 border border-indigo-800/40 rounded-2xl p-6 text-white shadow-lg flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5">
              <GraduationCap className="w-6 h-6 text-indigo-300" />
              <h1 className="text-xl font-bold">Institutional Governance Trail</h1>
            </div>
            <p className="text-sm text-slate-300 mt-1">
              Tracks all student CGPA edits, drive operations, TPO screenings, and interview updates strictly within your campus.
            </p>
          </div>
          <Button
            variant="outline"
            onClick={fetchLogs}
            className="bg-indigo-800/50 border-indigo-600/50 hover:bg-indigo-800 text-white"
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh Trail
          </Button>
        </div>

        {/* Filter Bar */}
        <Card className="border-slate-200 dark:border-slate-800 p-4 shadow-sm">
          <div className="flex flex-col sm:flex-row gap-4 items-center justify-between">
            <div className="relative w-full sm:w-80">
              <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
              <input
                type="text"
                placeholder="Search action or student email..."
                value={searchTerm}
                onChange={(e) => {
                  setSearchTerm(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-full pl-9 pr-4 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <div className="flex items-center gap-3 w-full sm:w-auto">
              <select
                value={selectedCategory}
                onChange={(e) => {
                  setSelectedCategory(e.target.value);
                  setCurrentPage(1);
                }}
                className="text-sm px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">All Categories</option>
                <option value="ACADEMIC">Academic Governance</option>
                <option value="RECRUITMENT">Recruitment & Pipeline</option>
                <option value="RESUME">Resume Verifications</option>
                <option value="AUTHENTICATION">Authentication</option>
              </select>

              {(searchTerm || selectedCategory) && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setSearchTerm('');
                    setSelectedCategory('');
                    setCurrentPage(1);
                  }}
                  className="text-xs"
                >
                  <X className="w-3.5 h-3.5 mr-1" />
                  Clear
                </Button>
              )}
            </div>
          </div>
        </Card>

        {/* Activity Table */}
        <Card className="border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
          <CardHeader
            title="Institutional Events"
            subtitle={
              logsResponse
                ? `Showing ${logsResponse.items.length} of ${logsResponse.total} events`
                : 'Loading...'
            }
          />

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-700 dark:text-slate-300">
              <thead className="text-xs uppercase bg-slate-50 dark:bg-slate-800/80 text-slate-500 dark:text-slate-400 border-y border-slate-200 dark:border-slate-700">
                <tr>
                  <th scope="col" className="px-4 py-3">Timestamp</th>
                  <th scope="col" className="px-4 py-3">Category</th>
                  <th scope="col" className="px-4 py-3">Action</th>
                  <th scope="col" className="px-4 py-3">Actor</th>
                  <th scope="col" className="px-4 py-3">Target Entity</th>
                  <th scope="col" className="px-4 py-3">Result</th>
                  <th scope="col" className="px-4 py-3 text-right">Inspect</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                {loading ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-12 text-center text-slate-500">
                      <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-500" />
                      Loading activity records...
                    </td>
                  </tr>
                ) : logsResponse?.items.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-12 text-center text-slate-500">
                      No campus activities found matching the query.
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
                        <span className="font-medium text-slate-800 dark:text-slate-200 block text-xs">
                          {log.user_name || log.user_email || 'System'}
                        </span>
                        <span className="text-[11px] text-slate-400 uppercase font-mono">
                          {log.user_role || 'system'}
                        </span>
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
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                          <CheckCircle2 className="w-3 h-3" />
                          {log.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right whitespace-nowrap">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setSelectedLog(log)}
                          className="h-8 text-xs text-indigo-600 dark:text-indigo-400"
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

          {/* Pagination */}
          {logsResponse && logsResponse.total_pages > 1 && (
            <div className="px-4 py-3 bg-slate-50 dark:bg-slate-800/50 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between">
              <span className="text-xs text-slate-500">
                Page {logsResponse.page} of {logsResponse.total_pages}
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

        {/* Diff Inspection Modal */}
        {selectedLog && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn">
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-3xl w-full max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
              <div className="p-5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50/50 dark:bg-slate-800/40">
                <div>
                  <h2 className="text-base font-bold text-slate-900 dark:text-white">
                    {selectedLog.action}
                  </h2>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Target: {selectedLog.entity_type} #{selectedLog.entity_id} | {formatDate(selectedLog.timestamp)}
                  </p>
                </div>
                <button
                  onClick={() => setSelectedLog(null)}
                  className="p-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="p-6 overflow-y-auto space-y-4 flex-1">
                {(selectedLog.previous_values || selectedLog.updated_values) ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="p-4 rounded-xl border border-rose-200 dark:border-rose-950/60 bg-rose-50/50 dark:bg-rose-950/20">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-rose-800 dark:text-rose-400 mb-2">
                        Previous State
                      </h4>
                      <pre className="text-xs font-mono text-rose-950 dark:text-rose-200 whitespace-pre-wrap break-all bg-white dark:bg-slate-950 p-3 rounded-lg border border-rose-200 dark:border-rose-900/60 max-h-56 overflow-y-auto">
                        {selectedLog.previous_values
                          ? JSON.stringify(selectedLog.previous_values, null, 2)
                          : '// Initial creation'}
                      </pre>
                    </div>

                    <div className="p-4 rounded-xl border border-emerald-200 dark:border-emerald-950/60 bg-emerald-50/50 dark:bg-emerald-950/20">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-800 dark:text-emerald-400 mb-2">
                        Updated State
                      </h4>
                      <pre className="text-xs font-mono text-emerald-950 dark:text-emerald-200 whitespace-pre-wrap break-all bg-white dark:bg-slate-950 p-3 rounded-lg border border-emerald-200 dark:border-emerald-900/60 max-h-56 overflow-y-auto">
                        {selectedLog.updated_values
                          ? JSON.stringify(selectedLog.updated_values, null, 2)
                          : '// Unchanged'}
                      </pre>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-slate-500 italic">No state diff recorded for this event.</p>
                )}

                {selectedLog.metadata && Object.keys(selectedLog.metadata).length > 0 && (
                  <div>
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-2">
                      Event Metadata
                    </h3>
                    <pre className="text-xs font-mono text-slate-800 dark:text-slate-200 whitespace-pre-wrap break-all bg-slate-50 dark:bg-slate-950 p-3 rounded-xl border border-slate-200 dark:border-slate-800">
                      {JSON.stringify(selectedLog.metadata, null, 2)}
                    </pre>
                  </div>
                )}
              </div>

              <div className="p-4 border-t border-slate-200 dark:border-slate-800 flex justify-end bg-slate-50/50 dark:bg-slate-800/40">
                <Button variant="outline" size="sm" onClick={() => setSelectedLog(null)}>
                  Close
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
};
export default TpoActivityLogPage;

