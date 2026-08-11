import { useState } from "react";
import {
  MessageSquare,
  Sparkles,
  Landmark,
  ArrowRight,
  Search,
  Loader2,
  FileText,
  AlertCircle,
  BookOpen,
  Lightbulb,
  ChevronDown,
  ChevronUp,
  Megaphone,
} from "lucide-react";
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

/** Parse the participation JSON field from a submission record */
function getParticipation(record) {
  try {
    if (record.participation) {
      return typeof record.participation === "string"
        ? JSON.parse(record.participation)
        : record.participation;
    }
  } catch {
    // ignore parse errors
  }
  return null;
}

/* ─── MatchCard component ─── */
function MatchCard({ record }) {
  const statusCfg = STATUS_CONFIG[record.status] || STATUS_CONFIG.ignored;
  const [showSimplified, setShowSimplified] = useState(false);
  const part = getParticipation(record);

  // Parse key points from CSV (semicolon-separated) or from API (array)
  const keyPoints =
    typeof record.keyPoints === "string" && record.keyPoints
      ? record.keyPoints.split(";").map((p) => p.trim()).filter(Boolean)
      : Array.isArray(record.keyPoints)
        ? record.keyPoints
        : [];

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
        {part?.hasMatch && (
          <span className="inline-flex items-center gap-1 rounded-full border border-amber-300 bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-700">
            <Megaphone className="h-3 w-3" />
            🗣️ +{((part.boostFactor || 0) * 100).toFixed(0)}% priority boost
          </span>
        )}
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

          {/* ── Plain Language Explanation ── */}
          {record.simplified && (
            <div className="mt-3 rounded-lg border border-emerald-200 bg-emerald-50/50">
              <button
                onClick={() => setShowSimplified(!showSimplified)}
                className="flex w-full items-center justify-between rounded-t-lg px-4 py-2.5 text-left text-xs font-semibold text-emerald-700 transition-colors hover:bg-emerald-50"
              >
                <span className="flex items-center gap-1.5">
                  <BookOpen className="h-3.5 w-3.5" />
                  Plain Language Explanation
                </span>
                {showSimplified ? (
                  <ChevronUp className="h-3.5 w-3.5" />
                ) : (
                  <ChevronDown className="h-3.5 w-3.5" />
                )}
              </button>

              {showSimplified && (
                <div className="space-y-2 border-t border-emerald-200 px-4 py-3">
                  <p className="text-sm leading-relaxed text-slate-700">
                    {record.simplified}
                  </p>

                  {keyPoints.length > 0 && (
                    <ul className="space-y-1.5">
                      {keyPoints.map((point, i) => (
                        <li
                          key={i}
                          className="flex items-start gap-2 text-sm text-slate-600"
                        >
                          <Lightbulb className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-amber-500" />
                          <span>{point}</span>
                        </li>
                      ))}
                    </ul>
                  )}

                  {record.category && (
                    <span className="inline-flex items-center rounded-full border border-emerald-300 bg-white px-2.5 py-0.5 text-xs text-emerald-700">
                      Category: {record.category}
                    </span>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ─── Page component ─── */
function Matches() {
  const matches = useBudgetMatches();

  // ── Semantic search state ──────────────────────────────────────────
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState("");
  const [hasSearched, setHasSearched] = useState(false);
  const [simplifiedResults, setSimplifiedResults] = useState({});
  const [simplifyingIdx, setSimplifyingIdx] = useState(null);

  const handleSimplifyResult = async (idx, text) => {
    setSimplifyingIdx(idx);
    try {
      const res = await fetch("http://localhost:8000/api/budget/simplify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      if (res.ok) {
        const data = await res.json();
        setSimplifiedResults((prev) => ({ ...prev, [idx]: data }));
      }
    } catch {
      // Silently fail — simplification is optional
    } finally {
      setSimplifyingIdx(null);
    }
  };

  const handleSearch = async () => {
    const query = searchQuery.trim();
    if (!query) return;

    setIsSearching(true);
    setSearchError("");
    setHasSearched(true);

    try {
      const res = await fetch("http://localhost:8000/api/budget/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, top_k: 5 }),
      });

      if (!res.ok) throw new Error(`Server error: ${res.status}`);

      const data = await res.json();
      setSearchResults(data?.results ?? []);
    } catch (err) {
      setSearchError(err.message || "Search failed");
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") handleSearch();
  };

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

      {/* ── Semantic Search Bar ─────────────────────────────────── */}
      <div className="rounded-xl border border-emerald-200 bg-gradient-to-br from-emerald-50/50 to-white p-5 shadow-sm">
        <div className="mb-3 flex items-center gap-2">
          <Search className="h-4 w-4 text-emerald-600" />
          <h2 className="text-sm font-semibold text-slate-700">
            Search the Enacted Budget
          </h2>
          <span className="hidden text-xs text-slate-400 sm:inline">
            AI-powered semantic search across the full Nairobi County budget
            document
          </span>
        </div>

        <div className="flex gap-2">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder='e.g. "maternity health budget", "road construction funds", "water supply allocation"'
            className="flex-1 rounded-lg border border-slate-300 px-4 py-2.5 text-sm text-slate-700 placeholder:text-slate-400 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
          />
          <button
            onClick={handleSearch}
            disabled={isSearching || !searchQuery.trim()}
            className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isSearching ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Search className="h-4 w-4" />
            )}
            {isSearching ? "Searching..." : "Search"}
          </button>
        </div>

        {/* ── Search Results ──────────────────────────────────── */}
        {hasSearched && (
          <div className="mt-4">
            {isSearching && (
              <div className="flex items-center justify-center py-8 text-slate-400">
                <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                <span className="text-sm">Searching budget document...</span>
              </div>
            )}

            {searchError && (
              <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                <AlertCircle className="h-4 w-4 flex-shrink-0" />
                {searchError}
              </div>
            )}

            {!isSearching && !searchError && searchResults.length === 0 && (
              <div className="flex flex-col items-center justify-center py-8 text-slate-400">
                <FileText className="mb-2 h-8 w-8" />
                <p className="text-sm font-medium">
                  No matching budget lines found
                </p>
                <p className="mt-1 text-xs">
                  Try a different search term related to county budget
                  allocations.
                </p>
              </div>
            )}

            {!isSearching && !searchError && searchResults.length > 0 && (
              <div className="space-y-3">
                <p className="text-xs text-slate-500">
                  Found {searchResults.length} result
                  {searchResults.length !== 1 ? "s" : ""} &middot; Semantic
                  search
                </p>
                {searchResults.map((result, idx) => {
                  const simplified = simplifiedResults[idx];
                  return (
                  <div
                    key={idx}
                    className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm transition-shadow hover:shadow"
                  >
                    <div className="mb-2 flex items-center justify-between">
                      <span className="inline-flex items-center gap-1 text-xs text-slate-500">
                        <FileText className="h-3 w-3" />
                        Page {result.page_number}
                      </span>
                      <span className="inline-flex items-center rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-700">
                        {Math.round(result.score * 100)}% match
                      </span>
                    </div>
                    <p className="text-sm leading-relaxed text-slate-700 whitespace-pre-line">
                      {result.text}
                    </p>

                    {/* Simplify button */}
                    {!simplified && (
                      <button
                        onClick={() => handleSimplifyResult(idx, result.text)}
                        disabled={simplifyingIdx === idx}
                        className="mt-2 inline-flex items-center gap-1.5 rounded-md border border-emerald-200 bg-white px-3 py-1.5 text-xs font-medium text-emerald-700 transition-colors hover:bg-emerald-50 disabled:opacity-50"
                      >
                        {simplifyingIdx === idx ? (
                          <Loader2 className="h-3 w-3 animate-spin" />
                        ) : (
                          <BookOpen className="h-3 w-3" />
                        )}
                        {simplifyingIdx === idx
                          ? "Translating..."
                          : "Translate to Plain Language"}
                      </button>
                    )}

                    {/* Simplified explanation */}
                    {simplified && (
                      <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50/60 p-3">
                        <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-amber-700">
                          <Lightbulb className="h-3.5 w-3.5" />
                          Plain Language
                        </div>
                        <p className="text-sm leading-relaxed text-slate-700">
                          {simplified.simplified}
                        </p>
                        {simplified.keyPoints?.length > 0 && (
                          <ul className="mt-2 space-y-1">
                            {simplified.keyPoints.map((point, i) => (
                              <li
                                key={i}
                                className="flex items-start gap-1.5 text-xs text-slate-600"
                              >
                                <span className="mt-0.5 text-amber-500">•</span>
                                {point}
                              </li>
                            ))}
                          </ul>
                        )}
                      </div>
                    )}
                  </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── Existing Budget Match Cards ─────────────────────────── */}
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