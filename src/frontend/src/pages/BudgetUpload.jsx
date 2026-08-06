import { useState } from "react";
import { FileUp, Loader2, CheckCircle2, AlertCircle, FileText, Grid, Brain, Database } from "lucide-react";

const API = "http://localhost:8000";

// Updated stages to match the NEW fast pipeline
const STAGES = [
  { key: "parsing", label: "Parsing PDF pages...", icon: FileText },
  { key: "chunking", label: "Splitting into searchable chunks...", icon: Grid },
  { key: "embedding", label: "Generating AI embeddings...", icon: Brain },
  { key: "storing", label: "Indexing for semantic search...", icon: Database },
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
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Upload failed" }));
        throw new Error(err.detail || "Upload failed");
      }
      const data = await res.json();
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
    }, 1500);
  }

  function getCurrentStageIndex() {
    if (!status || !status.status) return -1;
    const idx = STAGES.findIndex((s) => s.key === status.status);
    return idx >= 0 ? idx : status.status === "complete" ? STAGES.length : -1;
  }

  const currentStage = getCurrentStageIndex();
  const isComplete = status?.status === "complete";
  const isFailed = status?.status === "failed";

  return (
    <div className="mx-auto max-w-2xl px-4 py-8 sm:px-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight text-slate-800">
          Upload County Budget PDF
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Upload a Nairobi City County budget PDF. It will be parsed, chunked,
          and indexed in ~30 seconds for AI-powered semantic search.
        </p>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        {/* Upload area — shown before upload starts */}
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
                  Fast ingestion — no AI structuring needed
                </p>
              </div>
            </div>

            <label className="flex cursor-pointer flex-col items-center gap-2 rounded-lg border-2 border-dashed border-slate-200 bg-slate-50 p-8 hover:border-emerald-300 hover:bg-emerald-50/30 transition-colors">
              <FileUp className="h-8 w-8 text-slate-400" />
              <span className="text-sm font-medium text-slate-600">
                {file ? file.name : "Click to select a PDF file"}
              </span>
              <span className="text-xs text-slate-400">
                {file
                  ? `${(file.size / (1024 * 1024)).toFixed(1)} MB`
                  : "Max 50MB — takes ~30 sec to ingest"}
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
                  Ingesting...
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

        {/* Progress */}
        {status && !isComplete && !isFailed && (
          <div className="space-y-4">
            <div className="text-xs text-slate-400">
              Job: <code className="bg-slate-100 px-1 rounded">{jobId}</code>
            </div>

            {/* Stages list */}
            <div className="space-y-3">
              {STAGES.map((stage, i) => {
                const Icon = stage.icon;
                const isCurrent = i === currentStage;
                const isDone = i < currentStage;
                const isPending = i > currentStage;

                return (
                  <div
                    key={stage.key}
                    className={`flex items-center gap-3 rounded-lg p-3 transition-colors ${
                      isCurrent
                        ? "bg-emerald-50 border border-emerald-200"
                        : isDone
                        ? "bg-slate-50"
                        : "opacity-40"
                    }`}
                  >
                    <div
                      className={`flex h-8 w-8 items-center justify-center rounded-lg ${
                        isDone
                          ? "bg-emerald-100"
                          : isCurrent
                          ? "bg-emerald-600"
                          : "bg-slate-200"
                      }`}
                    >
                      {isDone ? (
                        <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                      ) : isCurrent ? (
                        <Loader2 className="h-4 w-4 animate-spin text-white" />
                      ) : (
                        <Icon className="h-4 w-4 text-slate-400" />
                      )}
                    </div>
                    <div>
                      <p
                        className={`text-sm font-medium ${
                          isCurrent ? "text-emerald-700" : "text-slate-600"
                        }`}
                      >
                        {stage.label}
                      </p>
                      {isCurrent && (
                        <p className="text-xs text-slate-400">
                          {Math.round((status.progress || 0) * 100)}% complete
                        </p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Progress bar */}
            <div className="h-2 w-full rounded-full bg-slate-200">
              <div
                className="h-2 rounded-full bg-emerald-500 transition-all duration-500"
                style={{ width: `${Math.round((status.progress || 0) * 100)}%` }}
              />
            </div>
          </div>
        )}

        {/* Complete */}
        {isComplete && (
          <div className="text-center py-6 space-y-3">
            <CheckCircle2 className="h-12 w-12 text-emerald-500 mx-auto" />
            <h3 className="text-lg font-semibold text-slate-800">
              Ingestion Complete!
            </h3>
            <p className="text-sm text-slate-500">
              {status.stats?.vectors_stored || 0} chunks indexed for semantic search
            </p>
            {status.stats && (
              <div className="text-xs text-slate-400 space-y-1">
                <p>{status.stats.total_pages} pages processed</p>
                <p>{status.stats.chunks_created} chunks created</p>
                <p>Embedding dim: {status.stats.vector_dim}</p>
              </div>
            )}
            <button
              onClick={() => { setStatus(null); setFile(null); setJobId(null); }}
              className="mt-2 text-sm text-emerald-600 hover:underline"
            >
              Upload another
            </button>
          </div>
        )}

        {/* Failed */}
        {isFailed && (
          <div className="text-center py-6 space-y-3">
            <AlertCircle className="h-12 w-12 text-red-500 mx-auto" />
            <h3 className="text-lg font-semibold text-red-700">Ingestion Failed</h3>
            <p className="text-sm text-red-500 max-w-md mx-auto">
              {status.error}
            </p>
            <button
              onClick={() => { setStatus(null); setFile(null); setJobId(null); }}
              className="mt-2 text-sm text-red-600 hover:underline"
            >
              Try again
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default BudgetUpload;