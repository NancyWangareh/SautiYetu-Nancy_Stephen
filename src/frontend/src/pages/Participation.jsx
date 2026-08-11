import { useState, useRef, useEffect } from "react";
import {
  Upload, Loader2, CheckCircle2, AlertCircle,
  ArrowRight, Landmark, Sparkles, MessageSquare,
} from "lucide-react";

const API_BASE = "http://localhost:8000";
const SESSION_KEY = "participation_last_results";

const STATUS_CONFIG = {
  matched: { label: "Funded", className: "bg-emerald-100 text-emerald-800 border-emerald-300" },
  partial: { label: "Partial", className: "bg-amber-100 text-amber-800 border-amber-300" },
  ignored: { label: "Not Funded", className: "bg-red-100 text-red-800 border-red-300" },
};

function Participation() {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [matching, setMatching] = useState(false);
  // ★★★ Load from sessionStorage on mount ★★★
  const [results, setResults] = useState(() => {
    try {
      const saved = sessionStorage.getItem(SESSION_KEY);
      return saved ? JSON.parse(saved) : null;
    } catch { return null; }
  });
  const [toast, setToast] = useState(null);
  const [pdfName, setPdfName] = useState("");
  const [sessionId, setSessionId] = useState(null);
  const fileRef = useRef(null);

  function showToast(message, isError = false) {
    setToast({ message, isError, visible: true });
    setTimeout(() => setToast(null), 4000);
  }

  function handleFileChange(e) {
    const f = e.target.files?.[0];
    if (f && f.type === "application/pdf") {
      setFile(f);
      setPdfName(f.name);
    } else if (f) {
      showToast("Please select a PDF file", true);
    }
  }

  async function handleUpload() {
    if (!file) return;
    setUploading(true);
    setResults(null);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("county", "Nairobi");

      const res = await fetch(`${API_BASE}/api/participation/upload`, {
        method: "POST", body: formData,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || err.detail || `Upload failed: ${res.status}`);
      }

      const data = await res.json();
      const extractedPoints = data.points || [];
      setSessionId(data.session_id);

      if (extractedPoints.length === 0) {
        showToast("No citizen input points found in the PDF.", true);
        setUploading(false);
        return;
      }

      showToast(`Parsed ${data.pages_parsed} pages, ${data.points_extracted} concerns. Matching...`);
      setMatching(true);

      const allPointIds = extractedPoints.map((p) => p.point_id);
      const matchRes = await fetch(`${API_BASE}/api/participation/match-points`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ point_ids: allPointIds, ward: "Nairobi", session_id: data.session_id }),
      });
      if (!matchRes.ok) {
        const err = await matchRes.json().catch(() => ({}));
        throw new Error(err.error || err.detail || `Matching failed: ${matchRes.status}`);
      }

      const matchData = await matchRes.json();
      setResults(matchData);
      setPdfName(data.filename || file.name);
      // ★★★ Persist to sessionStorage ★★★
      sessionStorage.setItem(SESSION_KEY, JSON.stringify(matchData));

      showToast(`Matched ${matchData.summary.total}: ${matchData.summary.matched} funded, ${matchData.summary.partial} partial, ${matchData.summary.ignored} not funded.`);
    } catch (err) {
      showToast(err.message, true);
    } finally {
      setUploading(false);
      setMatching(false);
    }
  }

  const isLoading = uploading || matching;

  return (
    <div className="relative mx-auto max-w-5xl px-4 py-8 sm:px-6">
      {toast?.visible && (
        <div className={`fixed top-6 right-6 z-50 flex items-center gap-2 rounded-lg border px-4 py-3 text-sm font-medium shadow-lg ${
          toast.isError ? "border-red-200 bg-red-50 text-red-800" : "border-emerald-200 bg-emerald-50 text-emerald-800"}`}>
          {toast.isError ? <AlertCircle className="h-4 w-4 text-red-600" /> : <CheckCircle2 className="h-4 w-4 text-emerald-600" />}
          {toast.message}
        </div>
      )}

      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight text-slate-800">Public Participation Upload</h1>
        <p className="mt-1 text-sm text-slate-500">
          Upload a Nairobi County public participation PDF. All citizen concerns are automatically extracted and matched against the budget.
        </p>
      </div>

      <div className="mb-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex items-center gap-4">
          <div className="flex-1 min-w-0">
            <div onClick={() => fileRef.current?.click()} className="flex cursor-pointer items-center gap-3 rounded-lg border-2 border-dashed border-slate-300 bg-slate-50 px-5 py-6 transition hover:border-emerald-400 hover:bg-emerald-50">
              <Upload className="h-6 w-6 flex-shrink-0 text-slate-400" />
              <span className="truncate text-sm text-slate-500">{pdfName || "Click to select a public participation PDF..."}</span>
            </div>
            <input ref={fileRef} type="file" accept=".pdf" onChange={handleFileChange} className="hidden" />
          </div>
          <button onClick={handleUpload} disabled={!file || isLoading}
            className="flex flex-shrink-0 items-center gap-2 rounded-lg bg-emerald-600 px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50">
            {isLoading ? (<><Loader2 className="h-4 w-4 animate-spin" />{matching ? "Matching..." : "Uploading..."}</>) : (<><Upload className="h-4 w-4" />Upload & Match</>)}
          </button>
        </div>
      </div>

      {results && (
        <>
          <div className="mb-4 flex flex-wrap items-center gap-3 rounded-lg border border-slate-200 bg-white px-5 py-3 shadow-sm">
            <span className="text-sm font-medium text-slate-600">{results.summary.total} concerns matched</span>
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-700"><CheckCircle2 className="h-3 w-3" />{results.summary.matched} funded</span>
            <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-700">{results.summary.partial} partial</span>
            <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-700"><AlertCircle className="h-3 w-3" />{results.summary.ignored} not funded</span>
          </div>
          <div className="space-y-4">
            {(results.results || []).map((r) => {
              const cfg = STATUS_CONFIG[r.status] || STATUS_CONFIG.ignored;
              return (
                <div key={r.point_id} className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 bg-slate-50 px-5 py-3">
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-xs text-slate-500">{r.point_id}</span>
                      {r.page_number && <span className="inline-flex items-center rounded-md border border-slate-200 bg-white px-2 py-0.5 text-xs text-slate-500">p.{r.page_number}</span>}
                    </div>
                    <span className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold ${cfg.className}`}>{cfg.label}</span>
                  </div>
                  <div className="grid gap-0 md:grid-cols-[1fr_auto_1fr]">
                    <div className="p-5">
                      <div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-slate-400"><MessageSquare className="h-3.5 w-3.5" />Citizen Concern</div>
                      <p className="text-sm leading-relaxed text-slate-700">&ldquo;{(r.citizen_input || "").slice(0, 400)}{(r.citizen_input?.length || 0) > 400 ? "..." : ""}&rdquo;</p>
                      <div className="mt-3 flex flex-wrap items-center gap-1.5">
                        <Sparkles className="h-3.5 w-3.5 text-emerald-600" />
                        <span className="inline-flex items-center rounded-md border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-xs text-emerald-700">Sector: {r.sector}</span>
                        <span className="inline-flex items-center rounded-md border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-xs text-emerald-700">{r.sub_sector}</span>
                      </div>
                    </div>
                    <div className="hidden items-center justify-center border-x border-slate-100 px-4 text-slate-300 md:flex"><ArrowRight className="h-5 w-5" /></div>
                    <div className="border-t border-slate-100 p-5 md:border-t-0">
                      <div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-slate-400"><Landmark className="h-3.5 w-3.5" />Budget Result</div>
                      <p className="text-sm leading-relaxed text-slate-700">{r.budget_result?.replace(/^\[.*?\]\s*/, "") || "Pending match..."}</p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}

      {!results && !isLoading && (
        <div className="flex flex-col items-center justify-center rounded-xl border border-slate-200 bg-white py-16 text-slate-400 shadow-sm">
          <Upload className="mb-3 h-12 w-12 opacity-40" />
          <p className="text-sm font-medium">No participation data matched yet</p>
          <p className="text-xs mt-1">Upload a PDF and all citizen concerns will be automatically matched.</p>
        </div>
      )}
    </div>
  );
}

export default Participation;