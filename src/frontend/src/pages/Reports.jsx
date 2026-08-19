import { useState, useEffect, useCallback } from "react";
import {
  FileText,
  Download,
  Filter,
  Loader2,
  AlertCircle,
  CheckCircle2,
  XCircle,
  TrendingUp,
  MapPin,
  Layers,
  BarChart3,
  RefreshCw,
} from "lucide-react";

import { API_BASE } from "../config"; 

const STATUS_COLORS = {
  present: "bg-emerald-100 text-emerald-800 border-emerald-300",
  absent: "bg-red-100 text-red-800 border-red-300",
};

const STATUS_ICONS = {
  present: CheckCircle2,
  absent: XCircle,
};

function Reports() {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Filters
  const [wardFilter, setWardFilter] = useState("");
  const [sectorFilter, setSectorFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const fetchReport = useCallback(async () => {
    setLoading(true);
    setError("");

    const params = new URLSearchParams();
    if (wardFilter) params.set("ward", wardFilter);
    if (sectorFilter) params.set("sector", sectorFilter);
    if (statusFilter) params.set("status", statusFilter);

    try {
      const res = await fetch(`${API_BASE}/api/reports?${params.toString()}`);
      if (!res.ok) throw new Error(`Server error: ${res.status}`);
      const data = await res.json();
      setReport(data);
    } catch (err) {
      setError(
        err.message === "Failed to fetch"
          ? "Cannot reach the backend. Make sure the server is running on port 8000."
          : err.message
      );
    } finally {
      setLoading(false);
    }
  }, [wardFilter, sectorFilter, statusFilter]);

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  const handleExportCSV = async () => {
    const params = new URLSearchParams();
    if (wardFilter) params.set("ward", wardFilter);
    if (sectorFilter) params.set("sector", sectorFilter);
    if (statusFilter) params.set("status", statusFilter);
    params.set("format", "csv");

    try {
      const res = await fetch(`${API_BASE}/api/reports?${params.toString()}`);
      const data = await res.json();
      const blob = new Blob([data.csv], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = data.filename || "sauti_yetu_report.csv";
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setError("Failed to download CSV report.");
    }
  };

  const clearFilters = () => {
    setWardFilter("");
    setSectorFilter("");
    setStatusFilter("");
  };

  const hasFilters = wardFilter || sectorFilter || statusFilter;

  // ── Bar chart helper ──
  const BarRow = ({ label, value, max, color, subLabel }) => {
    const pct = max > 0 ? (value / max) * 100 : 0;
    return (
      <div className="flex items-center gap-3 text-sm">
        <span className="w-40 shrink-0 truncate text-slate-700 font-medium">{label}</span>
        <div className="flex-1 h-6 bg-slate-100 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${color}`}
            style={{ width: `${Math.max(pct, 2)}%` }}
          />
        </div>
        <span className="w-12 text-right font-semibold text-slate-700">{value}</span>
        {subLabel && <span className="text-xs text-slate-400 w-32 shrink-0">{subLabel}</span>}
      </div>
    );
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6 px-4 py-8 sm:px-6">
      {/* ── Header ── */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-800">
            CSO Reports
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Aggregated citizen concerns vs. the enacted budget — filterable by sector
            and ward, ready to export.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleExportCSV}
            disabled={!report || report.summary.total === 0}
            className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Download className="h-4 w-4" />
            Export CSV
          </button>
        </div>
      </div>

      {/* ── Filters ── */}
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-3 flex items-center gap-2">
          <Filter className="h-4 w-4 text-slate-500" />
          <h2 className="text-sm font-semibold text-slate-700">Filters</h2>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-500">Ward</label>
            <select
              value={wardFilter}
              onChange={(e) => setWardFilter(e.target.value)}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-700 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
            >
              <option value="">All Wards</option>
              {report?.filters?.available?.wards?.map((w) => (
                <option key={w} value={w}>{w}</option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-500">Sector</label>
            <select
              value={sectorFilter}
              onChange={(e) => setSectorFilter(e.target.value)}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-700 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
            >
              <option value="">All Sectors</option>
              {report?.filters?.available?.sectors?.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-500">Status</label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-700 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
            >
              <option value="">All Statuses</option>
              <option value="present">Present</option>
              <option value="absent">Absent</option>
            </select>
          </div>
          {hasFilters && (
            <button
              onClick={clearFilters}
              className="flex items-center gap-1 rounded-lg px-3 py-2 text-sm text-slate-500 hover:text-slate-700 hover:bg-slate-100 transition-colors"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Clear
            </button>
          )}
        </div>
      </div>

      {/* ── Loading ── */}
      {loading && (
        <div className="flex items-center justify-center py-16 text-slate-400">
          <Loader2 className="mr-3 h-6 w-6 animate-spin" />
          <span className="text-sm">Generating report...</span>
        </div>
      )}

      {/* ── Error ── */}
      {error && !loading && (
        <div className="flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 p-5 text-sm text-red-700">
          <AlertCircle className="h-5 w-5 shrink-0" />
          {error}
        </div>
      )}

      {/* ── Report Content ── */}
      {report && !loading && (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            <SummaryCard
              label="Total Submissions"
              value={report.summary.total}
              icon={FileText}
              color="text-blue-600"
              bg="bg-blue-50"
            />
            <SummaryCard
              label="Present in Budget"
              value={report.summary.present}
              icon={CheckCircle2}
              color="text-emerald-600"
              bg="bg-emerald-50"
            />
            <SummaryCard
              label="Absent from Budget"
              value={report.summary.absent}
              icon={XCircle}
              color="text-red-600"
              bg="bg-red-50"
            />
          </div>

          {/* Funding Gap Highlight */}
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center gap-2 mb-3">
              <TrendingUp className="h-4 w-4 text-emerald-600" />
              <h2 className="text-sm font-semibold text-slate-700">Funding Gap Analysis</h2>
            </div>
            <div className="flex items-center gap-6">
              <div className="text-center">
                <p className="text-3xl font-bold text-emerald-600">
                  {report.fundingGap.pctAddressed}%
                </p>
                <p className="text-xs text-slate-500 mt-1">Budget Addressed</p>
              </div>
              <div className="flex-1 h-4 bg-slate-100 rounded-full overflow-hidden">
                <div className="flex h-full">
                  <div
                    className="bg-emerald-500 transition-all duration-500"
                    style={{ width: `${report.fundingGap.pctAddressed}%` }}
                  />
                  <div
                    className="bg-red-400 transition-all duration-500"
                    style={{ width: `${report.fundingGap.pctUnaddressed}%` }}
                  />
                </div>
              </div>
              <div className="text-center">
                <p className="text-3xl font-bold text-red-500">
                  {report.fundingGap.pctUnaddressed}%
                </p>
                <p className="text-xs text-slate-500 mt-1">Unaddressed</p>
              </div>
            </div>
            <p className="mt-3 text-xs text-slate-400">
              Based on {report.summary.total} citizen submissions. &ldquo;Addressed&rdquo; = present in the enacted budget.
            </p>
          </div>

          {/* Charts Grid */}
          <div className="grid gap-6 lg:grid-cols-2">
            {/* By Sector */}
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex items-center gap-2 mb-4">
                <Layers className="h-4 w-4 text-slate-500" />
                <h2 className="text-sm font-semibold text-slate-700">By Sector</h2>
              </div>
              {report.bySector.length === 0 ? (
                <p className="text-sm text-slate-400 py-4">No data.</p>
              ) : (
                <div className="space-y-2">
                  {report.bySector.map((s) => (
                    <BarRow
                      key={s.sector}
                      label={s.sector}
                      value={s.count}
                      max={report.bySector[0]?.count || 0}
                      color="bg-emerald-500"
                      subLabel={`✓${s.present} present · ✗${s.absent} absent`}
                    />
                  ))}
                </div>
              )}
            </div>

            {/* By Ward */}
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex items-center gap-2 mb-4">
                <MapPin className="h-4 w-4 text-slate-500" />
                <h2 className="text-sm font-semibold text-slate-700">By Ward</h2>
              </div>
              {report.byWard.length === 0 ? (
                <p className="text-sm text-slate-400 py-4">No data.</p>
              ) : (
                <div className="space-y-2">
                  {report.byWard.map((w) => (
                    <BarRow
                      key={w.ward}
                      label={w.ward}
                      value={w.count}
                      max={report.byWard[0]?.count || 0}
                      color="bg-blue-500"
                      subLabel={`✓${w.present} present · ✗${w.absent} absent`}
                    />
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Top Citizen Requests */}
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex items-center gap-2 mb-4">
                <BarChart3 className="h-4 w-4 text-slate-500" />
                <h2 className="text-sm font-semibold text-slate-700">Top Citizen Requests</h2>
              </div>
              {report.topRequests.length === 0 ? (
                <p className="text-sm text-slate-400 py-4">No data.</p>
              ) : (
                <div className="space-y-2">
                  {report.topRequests.map((r, i) => (
                    <div key={i} className="flex items-start gap-3 text-sm">
                      <span className="mt-0.5 font-mono text-xs text-slate-400 w-5 shrink-0">
                        {i + 1}.
                      </span>
                      <span className="flex-1 text-slate-700 truncate">{r.text}</span>
                      <span className="shrink-0 font-semibold text-slate-600">{r.count}×</span>
                      <span className={`shrink-0 inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[r.status] || "bg-slate-100 text-slate-600 border-slate-200"}`}>
                        {r.status}
                      </span>
                    </div>
                  ))}
                </div>
              )}
          </div>

          {/* Detailed Submissions Table */}
          <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
            <div className="flex items-center gap-2 border-b border-slate-100 bg-slate-50 px-5 py-3">
              <FileText className="h-4 w-4 text-slate-500" />
              <h2 className="text-sm font-semibold text-slate-700">
                Detailed Submissions ({report.submissions.length})
              </h2>
            </div>
            {report.submissions.length === 0 ? (
              <div className="py-12 text-center text-sm text-slate-400">
                No submissions match the selected filters.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50">
                      <th className="px-4 py-3 font-semibold text-slate-600">ID</th>
                      <th className="px-4 py-3 font-semibold text-slate-600">Ward</th>
                      <th className="px-4 py-3 font-semibold text-slate-600">Request</th>
                      <th className="px-4 py-3 font-semibold text-slate-600">Sector</th>
                      <th className="px-4 py-3 font-semibold text-slate-600">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {report.submissions.map((s) => {
                      const StatusIcon = STATUS_ICONS[s.status] || XCircle;
                      return (
                        <tr key={s.id} className="transition-colors hover:bg-slate-50">
                          <td className="px-4 py-3 font-mono text-xs text-slate-500">{s.id}</td>
                          <td className="px-4 py-3 text-slate-700">{s.ward}</td>
                          <td className="max-w-xs truncate px-4 py-3 text-slate-500">{s.citizenInput}</td>
                          <td className="px-4 py-3">
                            <span className="inline-flex items-center rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-700">
                              {s.sector}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium ${STATUS_COLORS[s.status] || ""}`}>
                              <StatusIcon className="h-3 w-3" />
                              {s.status}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}

      {/* ── Empty state (no report, no error, not loading) ── */}
      {!report && !loading && !error && (
        <div className="flex flex-col items-center justify-center py-16 text-slate-400">
          <FileText className="h-12 w-12 mb-3" />
          <p className="text-sm font-medium">No report data yet</p>
          <p className="text-xs mt-1">Adjust filters and try again.</p>
        </div>
      )}
    </div>
  );
}

/* ─── Summary Card ─── */
function SummaryCard({ label, value, icon: Icon, color, bg }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center gap-3">
        <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${bg}`}>
          <Icon className={`h-5 w-5 ${color}`} />
        </div>
        <div>
          <p className="text-2xl font-bold text-slate-800">{value}</p>
          <p className="text-xs text-slate-500">{label}</p>
        </div>
      </div>
    </div>
  );
}

export default Reports;
