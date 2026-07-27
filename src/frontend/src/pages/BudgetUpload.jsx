import { useState } from "react";
import { FileUp, Loader2, CheckCircle2, AlertCircle, FileText, Database, Brain, Search } from "lucide-react";

const API = "http://localhost:8000";

// ── Stages that match the backend pipeline ──
const STAGES = [
  { key: "extracting", label: "Extracting tables from PDF...", icon: FileText },
  { key: "structuring", label: "AI structuring budget lines...", icon: Brain },
  { key: "validating", label: "Validating extracted data...", icon: Search },
  { key: "uploading_to_vector_db", label: "Indexing for semantic search...", icon: Database },
];

function BudgetUpload() {
  const [file, setFile] = useState(null);
  const [jobId, setJobId] = useState(null);
  const [status, setStatus] = useState(null);
  const [polling, setPolling] = useState(false);

  async function handleUpload() {
    if (!file) return;
    setStatus(null);
    setPolling(true);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API}/api/budget/upload`, {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      console.log("📋 Job ID:", data.job_id);
      setJobId(data.job_id);
      startPolling(data.job_id);
    } catch (err) {
      setStatus({ status: "failed", error: err.message });
      setPolling(false);
    }
  }

  function startPolling(id) {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API}/api/budget/status/${id}`);
        const data = await res.json();
        setStatus(data);

        if (data.status === "complete" || data.status === "failed") {
          clearInterval(interval);
          setPolling(false);
        }
      } catch {
        // keep polling
      }
    }, 2000);
  }

  function getCurrentStageIndex() {
    if (!status || !status.status) return -1;
    const idx = STAGES.findIndex((s) => s.key === status.status);
    return idx >= 0 ? idx : status.status === "complete" ? STAGES.length : -1;
  }

  const currentStage = getCurrentStageIndex();

  return (
    <div className="mx-auto max-w-2xl px-4 py-8 sm:px-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight text-slate-800">
          Upload County Budget PDF
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Upload a Nairobi City County budget document. The system will extract,
          structure, and index every budget line for AI-powered matching.
        </p>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        {/* Upload area */}
        {!status && (
          <>
            <div className="mb-4 flex items-center gap-2">
              <div className="rounded-lg bg-slate-100 p-2">
                <FileUp className="h-5 w-5 text-emerald-600" />
              </div>
              <div>
                <h2 className="text-base font-semibold text-slate-800">
                  Budget Document Ingestion
                </h2>
                <p className="text-xs text-slate-500">
                  Supports Nairobi City County budget PDFs (digital format)
                </p>
              </div>
            </div>

            <label className="flex cursor-pointer flex-col items-center gap-2 rounded-lg border-2 border-dashed border-slate-200 bg-slate-50 p-8 hover:border-emerald-300 hover:bg-emerald-50/30 transition-colors">
              <FileUp className="h-8 w-8 text-slate-400" />
              <span className="text-sm font-medium text-slate-600">
                {file ? file.name : "Click to select a PDF file"}
              </span>
              <span className="text-xs text-slate-400">
                {file ? `${(file.size / (1024 * 1024)).toFixed(1)} MB` : "Max 50MB"}
              </span>
              <input
                type="file"
                accept=".pdf"
                onChange={(e) => setFile(e.target.files[0])}
                className="hidden"
              />
            </label>

            <button
              onClick={handleUpload}
              disabled={!file || polling}
              className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {polling ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <FileUp className="h-4 w-4" />
                  Upload & Ingest
                </>
              )}
            </button>
          </>
        )}

        {/* Progress display */}
        {status && (
          <div className="space-y-4">
            <div className="text-xs text-slate-400">
              Job ID: <code className="bg-slate-100 px-1 rounded">{jobId}</code>
              {polling && " — polling for updates..."}
            </div>
            <div className="flex items-center gap-2">
              <div className="rounded-lg bg-emerald-100 p-2">
                <FileText className="h-5 w-5 text-emerald-600" />
              </div>
              <div>
                <h2 className="text-base font-semibold text-slate-800">
                  {status.status === "complete" ? "Ingestion Complete" :
                   status.status === "failed" ? "Ingestion Failed" :
                   "Ingesting Budget Document..."}
                </h2>
                <p className="text-xs text-slate-500">
                  {file?.name} · {(file?.size / (1024 * 1024)).toFixed(1)} MB
                </p>
              </div>
            </div>

            {/* Progress bar */}
            <div className="w-full bg-slate-100 rounded-full h-2">
              <div
                className={`h-2 rounded-full transition-all duration-500 ${
                  status.status === "failed" ? "bg-red-500" :
                  status.status === "complete" ? "bg-emerald-500" : "bg-emerald-400"
                }`}
                style={{ width: `${(status.progress * 100).toFixed(0)}%` }}
              />
            </div>

            {/* Stage indicators */}
            <div className="space-y-2">
              {STAGES.map((stage, i) => {
                const Icon = stage.icon;
                const isComplete = currentStage > i || status.status === "complete";
                const isCurrent = currentStage === i;
                const isFailed = status.status === "failed" && isCurrent;

                return (
                  <div key={stage.key} className="flex items-center gap-2.5 text-sm">
                    {isComplete ? (
                      <CheckCircle2 className="h-4 w-4 text-emerald-500 flex-shrink-0" />
                    ) : isFailed ? (
                      <AlertCircle className="h-4 w-4 text-red-500 flex-shrink-0" />
                    ) : isCurrent ? (
                      <Loader2 className="h-4 w-4 animate-spin text-emerald-600 flex-shrink-0" />
                    ) : (
                      <div className="h-4 w-4 rounded-full border-2 border-slate-200 flex-shrink-0" />
                    )}
                    <Icon className={`h-4 w-4 flex-shrink-0 ${
                      isComplete ? "text-emerald-500" :
                      isCurrent ? "text-emerald-600" : "text-slate-300"
                    }`} />
                    <span className={
                      isComplete ? "text-emerald-700 font-medium" :
                      isCurrent ? "text-slate-700 font-medium" :
                      isFailed ? "text-red-600" : "text-slate-400"
                    }>
                      {stage.label}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* Stats on completion */}
            {status.status === "complete" && status.stats && (
              <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3">
                <p className="text-xs font-medium text-emerald-800 mb-2">✅ Ingestion Successful</p>
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div>
                    <p className="text-lg font-bold text-emerald-700">{status.stats.structured_lines || "—"}</p>
                    <p className="text-[10px] text-emerald-600">Budget Lines</p>
                  </div>
                  <div>
                    <p className="text-lg font-bold text-emerald-700">{status.stats.valid_lines || "—"}</p>
                    <p className="text-[10px] text-emerald-600">Valid Lines</p>
                  </div>
                  <div>
                    <p className="text-lg font-bold text-emerald-700">{status.stats.uploaded_to_vectordb || "—"}</p>
                    <p className="text-[10px] text-emerald-600">Indexed in DB</p>
                  </div>
                </div>
              </div>
            )}

            {/* Error on failure */}
            {status.status === "failed" && (
              <div className="rounded-lg border border-red-200 bg-red-50 p-3">
                <p className="text-xs font-medium text-red-800">❌ Ingestion Failed</p>
                <p className="text-xs text-red-600 mt-1">{status.error || "Unknown error"}</p>
              </div>
            )}

            {/* Upload another */}
            {(status.status === "complete" || status.status === "failed") && (
              <button
                onClick={() => { setStatus(null); setFile(null); setJobId(null); }}
                className="w-full rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50"
              >
                Upload Another Document
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default BudgetUpload;