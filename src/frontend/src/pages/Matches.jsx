import { MessageSquare, Sparkles, Landmark, ArrowRight } from "lucide-react";
import { useBudgetMatches } from "../data/matches";

/* ─── Status badge config ─── */
const STATUS_CONFIG = {
  matched: {
    label: "Matched / Funded",
    className: "bg-emerald-100 text-emerald-800 border-emerald-300",
  },
  partial: {
    label: "Partially Funded",
    className: "bg-amber-100 text-amber-800 border-amber-300",
  },
  ignored: {
    label: "Ignored / Not Funded",
    className: "bg-red-100 text-red-800 border-red-300",
  },
};

/* ─── MatchCard component ─── */
function MatchCard({ record }) {
  const statusCfg = STATUS_CONFIG[record.status] || STATUS_CONFIG.ignored;

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      {/* Header bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 bg-slate-50 px-5 py-3">
        <div className="flex items-center gap-3">
          <span className="font-mono text-xs text-slate-500">{record.id}</span>
          <span className="inline-flex items-center rounded-md border border-slate-200 bg-white px-2 py-0.5 text-xs text-slate-600">
            {record.ward}
          </span>
          <span className="text-xs text-slate-400">{record.submittedAt}</span>
        </div>
        <span
          className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold ${statusCfg.className}`}
        >
          {statusCfg.label}
        </span>
      </div>

      {/* Three-column grid: citizen input | arrow | budget result */}
      <div className="grid gap-0 md:grid-cols-[1fr_auto_1fr]">
        {/* Left: Bottom-up */}
        <div className="p-5">
          <div className="mb-2 flex flex-wrap items-center gap-2 text-xs font-medium uppercase tracking-wide text-slate-400">
            <MessageSquare className="h-3.5 w-3.5" />
            Citizen Input · Bottom-Up
            <span className="inline-flex items-center rounded-md bg-slate-100 px-2 py-0.5 text-xs font-normal text-slate-500">
              via {record.channel}
            </span>
          </div>
          <p className="text-sm leading-relaxed text-slate-700">
            &ldquo;{record.citizenInput}&rdquo;
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-1.5">
            <Sparkles className="h-3.5 w-3.5 text-emerald-600" />
            <span className="inline-flex items-center rounded-md border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-xs text-emerald-700">
              Sector: {record.sector}
            </span>
            <span className="inline-flex items-center rounded-md border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-xs text-emerald-700">
              Sub-sector: {record.subSector}
            </span>
          </div>
        </div>

        {/* Center: Arrow */}
        <div className="hidden items-center justify-center border-x border-slate-100 px-4 text-slate-300 md:flex">
          <ArrowRight className="h-5 w-5" />
        </div>

        {/* Right: Top-down */}
        <div className="border-t border-slate-100 p-5 md:border-t-0">
          <div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-slate-400">
            <Landmark className="h-3.5 w-3.5" />
            Budget Result · Top-Down
          </div>
          <p className="text-sm leading-relaxed text-slate-700">
            {record.budgetResult}
          </p>
        </div>
      </div>
    </div>
  );
}

/* ─── Page component ─── */
function Matches() {
  const matches = useBudgetMatches();

  return (
    <div className="mx-auto max-w-6xl space-y-6 px-4 py-8 sm:px-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-800">
          Budget Matches
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Every citizen request mapped to its enacted budget outcome.
        </p>
      </div>

      {matches.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-slate-200 bg-white py-16 text-slate-400 shadow-sm">
          <span className="mb-3 text-4xl">🔗</span>
          <p className="text-sm font-medium">No budget matches yet</p>
          <p className="mt-1 text-xs">
            Submit citizen requests from the Input page to see budget matching.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {matches.map((record) => (
            <MatchCard key={record.id} record={record} />
          ))}
        </div>
      )}
    </div>
  );
}

export default Matches;