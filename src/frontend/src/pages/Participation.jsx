import { useState, useRef } from "react";
import {
  Upload,
  FileText,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Search,
  ChevronDown,
  ChevronUp,
  MapPin,
  Building2,
  CheckSquare,
  Square,
  ArrowRight,
  Landmark,
  Sparkles,
  MessageSquare,
} from "lucide-react";

const API_BASE = "http://localhost:8000";

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

function Participation() {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [parsing, setParsing] = useState(false);
  const [points, setPoints] = useState([]);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [matching, setMatching] = useState(false);
  const [results, setResults] = useState(null);
  const [ward, setWard] = useState("Umoja I");
  const [county, setCounty] = useState("Nairobi");
  const [toast, setToast] = useState(null);
  const [pdfName, setPdfName] = useState("");
  const fileRef = useRef(null);

  function showToast(message, isError = false) {
    setToast({ message, isError, visible: true });
    setTimeout(() => setToast(null), 4000);
  }

  /* ─── File selection ─── */
  function handleFileChange(e) {
    const f = e.target.files?.[0];
    if (f && f.type === "application/pdf") {
      setFile(f);
      setPdfName(f.name);
      setPoints([]);
      setSelectedIds(new Set());
      setResults(null);
    } else if (f) {
      showToast("Please select a PDF file", true);
    }
  }

  /* ─── Upload & parse ─── */
  async function handleUpload() {
    if (!file) return;
    setUploading(true);
    setParsing(true);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("county", county);

      const res = await fetch(`${API_BASE}/api/upload-participation`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || `Upload failed: ${res.status}`);
      }

      const data = await res.json();

      if (data.error) {
        throw new Error(data.error);
      }

      setPoints(data.points || []);
      setPdfName(data.filename || file.name);
      showToast(
        `Parsed ${data.pages_parsed} pages, extracted ${data.points_extracted} citizen input points.`
      );
    } catch (err) {
      showToast(err.message, true);
    } finally {
      setUploading(false);
      setParsing(false);
    }
  }

  /* ─── Selection toggle ─── */
  function togglePoint(pointId) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(pointId)) {
        next.delete(pointId);
      } else {
        next.add(pointId);
      }
      return next;
    });
  }

  function toggleAll() {
    if (selectedIds.size === points.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(points.map((p) => p.point_id)));
    }
  }

  /* ─── Match selected ─── */
  async function handleMatch() {
    if (selectedIds.size === 0) {
      showToast("Select at least one point to match", true);
      return;
    }

    setMatching(true);
    try {
      const res = await fetch(`${API_BASE}/api/match-points`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          point_ids: Array.from(selectedIds),
          ward,
          county,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || `Matching failed: ${res.status}`);
      }

      const data = await res.json();
      setResults(data);
      showToast(
        `Matched ${data.summary.total} points: ${data.summary.matched} funded, ${data.summary.partial} partial, ${data.summary.ignored} not funded.`
      );
    } catch (err) {
      showToast(err.message, true);
    } finally {
      setMatching(false);
    }
  }

  return (
    <div className="relative mx-auto max-w-4xl px-4 py-8 sm:px-6">
      {/* ── Toast ── */}
      {toast?.visible && (
        <div
          className={`fixed top-6 right-6 z-50 flex items-center gap-2 rounded-lg border px-4 py-3 text-sm font-medium shadow-lg ${
            toast.isError
              ? "border-red-200 bg-red-50 text-red-800"
              : "border-emerald-200 bg-emerald-50 text-emerald-800"
          }`}
        >
          {toast.isError ? (
            <AlertCircle className="h-4 w-4 text-red-600" />
          ) : (
            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
          )}
          {toast.message}
        </div>
      )}

      {/* ── Header ── */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight text-slate-800">
          Public Participation Upload
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Upload a nationwide public participation PDF. Specify a County (e.g.,
          Nairobi) to extract only grassroots inputs from that county&apos;s
          pages. Select points to match against the enacted budget.
        </p>
      </div>

      {/* ── Upload Card ── */}
      <div className="mb-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-end gap-4">
          {/* File picker */}
          <div className="flex-1 min-w-0">
            <label className="mb-1.5 block text-sm font-medium text-slate-600">
              Participation PDF
            </label>
            <div
              onClick={() => fileRef.current?.click()}
              className="flex cursor-pointer items-center gap-3 rounded-lg border-2 border-dashed border-slate-300 bg-slate-50 px-4 py-5 transition hover:border-emerald-400 hover:bg-emerald-50"
            >
              <Upload className="h-5 w-5 text-slate-400" />
              <span className="truncate text-sm text-slate-500">
                {pdfName || "Click to select a PDF file..."}
              </span>
            </div>
            <input
              ref={fileRef}
              type="file"
              accept=".pdf"
              onChange={handleFileChange}
              className="hidden"
            />
          </div>

          {/* County selector */}
          <div className="w-40">
            <label className="mb-1.5 block text-sm font-medium text-slate-600">
              County
            </label>
            <div className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2.5">
              <Building2 className="h-4 w-4 text-slate-400" />
              <input
                type="text"
                value={county}
                onChange={(e) => setCounty(e.target.value)}
                className="w-full text-sm text-slate-700 outline-none"
                placeholder="County"
              />
            </div>
          </div>

          {/* Ward selector */}
          <div className="w-40">
            <label className="mb-1.5 block text-sm font-medium text-slate-600">
              Ward
            </label>
            <div className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2.5">
              <MapPin className="h-4 w-4 text-slate-400" />
              <input
                type="text"
                value={ward}
                onChange={(e) => setWard(e.target.value)}
                className="w-full text-sm text-slate-700 outline-none"
                placeholder="Ward name"
              />
            </div>
          </div>

          {/* Upload button */}
          <button
            onClick={handleUpload}
            disabled={!file || uploading}
            className="flex h-[42px] items-center gap-2 rounded-lg bg-emerald-600 px-5 text-sm font-semibold text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {uploading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Parsing...
              </>
            ) : (
              <>
                <FileText className="h-4 w-4" />
                Analyze PDF
              </>
            )}
          </button>
        </div>
      </div>

      {/* ── Extracted Points ── */}
      {points.length > 0 && (
        <div className="mb-6 rounded-xl border border-slate-200 bg-white shadow-sm">
          {/* Header with select-all */}
          <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50 px-5 py-3">
            <div className="flex items-center gap-3">
              <FileText className="h-4 w-4 text-emerald-600" />
              <span className="text-sm font-semibold text-slate-700">
                {points.length} Citizen Input Points Extracted
              </span>
              <span className="text-xs text-slate-400">from {pdfName}</span>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={toggleAll}
                className="flex items-center gap-1.5 text-xs font-medium text-emerald-600 hover:text-emerald-800"
              >
                {selectedIds.size === points.length ? (
                  <>
                    <Square className="h-3.5 w-3.5" />
                    Deselect All
                  </>
                ) : (
                  <>
                    <CheckSquare className="h-3.5 w-3.5" />
                    Select All
                  </>
                )}
              </button>
              <span className="text-xs text-slate-400">
                {selectedIds.size} selected
              </span>
            </div>
          </div>

          {/* Points list */}
          <div className="divide-y divide-slate-100 max-h-[500px] overflow-y-auto">
            {points.map((point) => {
              const isSelected = selectedIds.has(point.point_id);
              return (
                <label
                  key={point.point_id}
                  className={`flex cursor-pointer items-start gap-3 px-5 py-3 transition hover:bg-slate-50 ${
                    isSelected ? "bg-emerald-50/50" : ""
                  }`}
                >
                  <div className="mt-0.5 flex-shrink-0">
                    {isSelected ? (
                      <CheckSquare className="h-4 w-4 text-emerald-600" />
                    ) : (
                      <Square className="h-4 w-4 text-slate-300" />
                    )}
                  </div>
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => togglePoint(point.point_id)}
                    className="hidden"
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm leading-relaxed text-slate-700">
                      {point.text}
                    </p>
                    <div className="mt-1 flex flex-wrap items-center gap-2">
                      <span className="inline-flex items-center rounded-md bg-slate-100 px-2 py-0.5 text-xs text-slate-500">
                        {point.point_id}
                      </span>
                      {point.section && (
                        <span className="inline-flex items-center rounded-md bg-blue-50 px-2 py-0.5 text-xs text-blue-600">
                          {point.section}
                        </span>
                      )}
                      <span className="text-xs text-slate-400">
                        p.{point.page_number} · {point.char_count} chars
                      </span>
                    </div>
                  </div>
                </label>
              );
            })}
          </div>

          {/* Match button */}
          <div className="border-t border-slate-100 bg-slate-50 px-5 py-3">
            <button
              onClick={handleMatch}
              disabled={selectedIds.size === 0 || matching}
              className="flex items-center gap-2 rounded-lg bg-[#0B3523] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[#13402A] disabled:cursor-not-allowed disabled:opacity-50"
            >
              {matching ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Matching against budget...
                </>
              ) : (
                <>
                  <Search className="h-4 w-4" />
                  Match {selectedIds.size} Selected Point
                  {selectedIds.size !== 1 ? "s" : ""} Against Budget
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* ── Empty state ── */}
      {!points.length && !uploading && (
        <div className="rounded-xl border border-slate-200 bg-white p-12 text-center shadow-sm">
          <FileText className="mx-auto h-10 w-10 text-slate-300" />
          <p className="mt-3 text-sm font-medium text-slate-500">
            No points extracted yet
          </p>
          <p className="mt-1 text-xs text-slate-400">
            Upload a public participation PDF above to extract citizen input
            points.
          </p>
        </div>
      )}

      {/* ── Results ── */}
      {results && (
        <div className="mb-6">
          <div className="mb-4 flex items-center gap-3">
            <h2 className="text-lg font-bold tracking-tight text-slate-800">
              Budget Match Results
            </h2>
            <div className="flex items-center gap-2 text-xs">
              <span className="inline-flex items-center rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-emerald-700">
                {results.summary.matched} Funded
              </span>
              <span className="inline-flex items-center rounded-full border border-amber-200 bg-amber-50 px-2.5 py-0.5 text-amber-700">
                {results.summary.partial} Partial
              </span>
              <span className="inline-flex items-center rounded-full border border-red-200 bg-red-50 px-2.5 py-0.5 text-red-700">
                {results.summary.ignored} Not Funded
              </span>
            </div>
          </div>

          <div className="space-y-4">
            {results.results.map((r) => {
              const statusCfg = STATUS_CONFIG[r.status] || STATUS_CONFIG.ignored;
              return (
                <MatchResultCard
                  key={r.point_id}
                  result={r}
                  statusCfg={statusCfg}
                />
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

/* ─── Match Result Card ─── */
function MatchResultCard({ result, statusCfg }) {
  const [expanded, setExpanded] = useState(false);

  const keyPoints =
    typeof result.keyPoints === "string" && result.keyPoints
      ? result.keyPoints.split(";").map((p) => p.trim()).filter(Boolean)
      : Array.isArray(result.keyPoints)
        ? result.keyPoints
        : [];
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 bg-slate-50 px-5 py-3">
        <div className="flex items-center gap-3">
          <span className="font-mono text-xs text-slate-500">
            {result.point_id}
          </span>
          <span className="inline-flex items-center rounded-md bg-white border border-slate-200 px-2 py-0.5 text-xs text-slate-600">
            p.{result.page_number}
          </span>
          {result.sector !== "Uncategorized" && (
            <span className="inline-flex items-center rounded-md bg-emerald-50 border border-emerald-200 px-2 py-0.5 text-xs text-emerald-700">
              {result.sector}
            </span>
          )}
        </div>
        <span
          className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold ${statusCfg.className}`}
        >
          {statusCfg.label}
        </span>
      </div>

      {/* Two-column: citizen input | budget result */}
      <div className="grid gap-0 md:grid-cols-[1fr_auto_1fr]">
        {/* Left: citizen point */}
        <div className="p-5">
          <div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-slate-400">
            <MessageSquare className="h-3.5 w-3.5" />
            Citizen Input
          </div>
          <p className="text-sm leading-relaxed text-slate-700">
            &ldquo;{result.citizenInput}&rdquo;
          </p>
          <div className="mt-2 flex flex-wrap items-center gap-1.5">
            <Sparkles className="h-3 w-3 text-emerald-600" />
            <span className="text-xs text-slate-500">
              {result.subSector}
            </span>
          </div>
        </div>

        {/* Center: arrow */}
        <div className="hidden items-center justify-center border-x border-slate-100 px-4 text-slate-300 md:flex">
          <ArrowRight className="h-5 w-5" />
        </div>

        {/* Right: budget result */}
        <div className="border-t border-slate-100 p-5 md:border-t-0">
          <div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-slate-400">
            <Landmark className="h-3.5 w-3.5" />
            Budget Result
          </div>
          <p className="text-sm leading-relaxed text-slate-700">
            {result.budgetResult}
          </p>
          {result.confidence > 0 && (
            <span className="mt-1 inline-flex items-center rounded-md bg-slate-100 px-2 py-0.5 text-xs text-slate-500">
              {(result.confidence * 100).toFixed(0)}% match
            </span>
          )}

          {/* Plain language toggle */}
          {result.simplified && (
            <div className="mt-3">
              <button
                onClick={() => setExpanded(!expanded)}
                className="flex items-center gap-1 text-xs font-medium text-emerald-600 hover:text-emerald-800"
              >
                {expanded ? (
                  <ChevronUp className="h-3.5 w-3.5" />
                ) : (
                  <ChevronDown className="h-3.5 w-3.5" />
                )}
                Plain Language Explanation
              </button>
              {expanded && (
                <div className="mt-2 rounded-lg border border-emerald-100 bg-emerald-50 p-3">
                  <p className="text-sm leading-relaxed text-emerald-800">
                    {result.simplified}
                  </p>
                  {keyPoints.length > 0 && (
                    <ul className="mt-2 space-y-1">
                      {keyPoints.map((kp, i) => (
                        <li
                          key={i}
                          className="flex items-start gap-2 text-xs text-emerald-700"
                        >
                          <span className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-emerald-400" />
                          {kp}
                        </li>
                      ))}
                    </ul>
                  )}
                  {result.category && (
                    <span className="mt-2 inline-flex items-center rounded-md bg-emerald-100 px-2 py-0.5 text-xs text-emerald-700">
                      Category: {result.category}
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

export default Participation;
