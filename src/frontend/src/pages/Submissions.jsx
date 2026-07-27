import { Loader2, AlertCircle } from "lucide-react";
import { useSubmissions } from "../data/store";

function Submissions() {
  const { submissions, loading, error, refresh } = useSubmissions();

  return (
    <div className="mx-auto max-w-6xl space-y-6 px-4 py-8 sm:px-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-800">
            Submissions
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Raw citizen requests captured across channels, before budget matching.
          </p>
        </div>
        <button
          onClick={refresh}
          disabled={loading}
          className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50"
        >
          {loading ? "Refreshing..." : "↻ Refresh"}
        </button>
      </div>

      {/* Loading state */}
      {loading && (
        <div className="flex items-center justify-center py-16 text-slate-400">
          <Loader2 className="h-6 w-6 animate-spin mr-2" />
          <span className="text-sm">Loading submissions from database...</span>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <AlertCircle className="h-4 w-4 text-red-500" />
          {error}
        </div>
      )}

      {/* Table card — only show when not loading and no error */}
      {!loading && !error && (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          {submissions.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-slate-400">
              <span className="text-4xl mb-3">📋</span>
              <p className="text-sm font-medium">No submissions yet</p>
              <p className="text-xs mt-1">
                Submit a citizen request from the Input page.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50">
                    <th className="px-4 py-3 font-semibold text-slate-600">ID</th>
                    <th className="px-4 py-3 font-semibold text-slate-600">Ward</th>
                    <th className="px-4 py-3 font-semibold text-slate-600">Channel</th>
                    <th className="px-4 py-3 font-semibold text-slate-600">Request</th>
                    <th className="px-4 py-3 font-semibold text-slate-600">Sector</th>
                    <th className="px-4 py-3 font-semibold text-slate-600">Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {submissions.map((s) => (
                    <tr key={s.id} className="transition-colors hover:bg-slate-50">
                      <td className="px-4 py-3 font-mono text-xs text-slate-500">
                        {s.id}
                      </td>
                      <td className="px-4 py-3 text-slate-700">{s.ward}</td>
                      <td className="px-4 py-3">
                        <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600">
                          {s.channel}
                        </span>
                      </td>
                      <td className="max-w-xs truncate px-4 py-3 text-slate-500">
                        {s.citizenInput}
                      </td>
                      <td className="px-4 py-3">
                        <span className="inline-flex items-center rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-700">
                          {s.sector}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-slate-500">
                        {s.submittedAt}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default Submissions;