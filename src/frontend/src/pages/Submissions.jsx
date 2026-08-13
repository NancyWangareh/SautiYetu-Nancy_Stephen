import { useSubmissions } from "../data/store";
import { Megaphone, CheckCircle2, AlertTriangle, XCircle } from "lucide-react";

const STATUS_CONFIG = {
  matched: {
    label: "Funded",
    icon: CheckCircle2,
    className: "bg-emerald-100 text-emerald-800 border-emerald-300",
  },
  partial: {
    label: "Partial",
    icon: AlertTriangle,
    className: "bg-amber-100 text-amber-800 border-amber-300",
  },
  ignored: {
    label: "Not Funded",
    icon: XCircle,
    className: "bg-red-100 text-red-800 border-red-300",
  },
};

function Submissions() {
  const submissions = useSubmissions();

  return (
    <div className="mx-auto max-w-6xl space-y-6 px-4 py-8 sm:px-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-800">Submissions</h1>
        <p className="mt-1 text-sm text-slate-500">
          Every citizen concern extracted from public participation documents,
          classified by sector, and matched against the enacted budget.
        </p>
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        {submissions.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-slate-400">
            <span className="text-4xl mb-3">📋</span>
            <p className="text-sm font-medium">No submissions yet</p>
            <p className="text-xs mt-1">
              Upload a participation PDF to extract and match citizen concerns.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50">
                  <th className="px-4 py-3 font-semibold text-slate-600">ID</th>
                  <th className="px-4 py-3 font-semibold text-slate-600">Ward</th>
                  <th className="px-4 py-3 font-semibold text-slate-600">Citizen Concern</th>
                  <th className="px-4 py-3 font-semibold text-slate-600">Sector</th>
                  <th className="px-4 py-3 font-semibold text-slate-600">Budget Result</th>
                  <th className="px-4 py-3 font-semibold text-slate-600">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {submissions.map((s) => {
                  const status = s.match?.status || "ignored";
                  const statusCfg = STATUS_CONFIG[status] || STATUS_CONFIG.ignored;
                  const StatusIcon = statusCfg.icon;
                  return (
                    <tr key={s.id} className="transition-colors hover:bg-slate-50">
                      <td className="px-4 py-3 font-mono text-xs text-slate-500">{s.id}</td>
                      <td className="px-4 py-3 text-slate-700">{s.ward}</td>
                      <td className="max-w-md px-4 py-3 text-slate-500">
                        <p className="line-clamp-2">
                          {s.citizen_input?.slice(0, 250)}
                          {(s.citizen_input?.length || 0) > 250 ? "…" : ""}
                        </p>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-col gap-1">
                          <span className="inline-flex items-center rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-700 w-fit">
                            {s.sector}
                          </span>
                          {s.sub_sector && (
                            <span className="text-[10px] text-slate-400">{s.sub_sector}</span>
                          )}
                        </div>
                      </td>
                      <td className="max-w-xs px-4 py-3 text-xs text-slate-500">
                        <p className="line-clamp-2">
                          {s.match?.budget_result?.replace(/^\[.*?\]\s*/, "") || "Pending match..."}
                        </p>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium ${statusCfg.className}`}>
                          <StatusIcon className="h-3 w-3" />
                          {statusCfg.label}
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
    </div>
  );
}

export default Submissions;