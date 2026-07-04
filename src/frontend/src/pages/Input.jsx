import { useState } from "react";
import { Loader2, Send, MessageSquarePlus, Sparkles, CheckCircle2, Mic, Paperclip } from "lucide-react";
import { classifyInput, buildSubmission } from "../data/classify";
import { addSubmission, getSubmissionCount } from "../data/store";

function Input({ onNavigate }) {
  const [input, setInput] = useState("");
  const [processing, setProcessing] = useState(false);
  const [toast, setToast] = useState(null);

  const preview = input.trim() ? classifyInput(input) : null;

  function showToast(message) {
    setToast({ message, visible: true });
    setTimeout(() => setToast({ message, visible: false }), 3000);
  }

  function handleSubmit() {
    if (!input.trim() || processing) return;
    setProcessing(true);
    const raw = input.trim();
    setTimeout(() => {
      addSubmission(buildSubmission(raw, getSubmissionCount()));
      setInput("");
      setProcessing(false);
      showToast("Your input was sent successfully!");
      onNavigate("submissions");
    }, 1500);
  }

  return (
    <div className="relative mx-auto max-w-2xl px-4 py-8 sm:px-6">
      {/* ── Toast ── */}
      {toast?.visible && (
        <div className="fixed top-6 right-6 z-50 flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-800 shadow-lg">
          <CheckCircle2 className="h-4 w-4 text-emerald-600" />
          {toast.message}
        </div>
      )}

      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight text-slate-800">
          Simulate Grassroots Input
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Enter a citizen request. It is auto-classified by sector, then flows
          into the Submissions table and Budget Matches feed.
        </p>
      </div>

      {/* Card */}
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-3 flex items-center gap-2">
          <div className="rounded-lg bg-slate-100 p-2">
            <MessageSquarePlus className="h-5 w-5 text-emerald-600" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-slate-800">
              Citizen Ingestion Portal
            </h2>
            <p className="text-xs text-slate-500">
              Submit on behalf of a community member
            </p>
          </div>
        </div>

        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={processing}
          placeholder="e.g., We need the Umoja dispensary maternity wing expanded..."
          rows={5}
          className="w-full rounded-lg border border-slate-200 bg-white p-3 text-sm text-slate-800 placeholder-slate-400 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-200 disabled:opacity-50 resize-none"
        />

        {/* ── Dummy attachment buttons ── */}
        <div className="mt-2 flex items-center gap-1">
          <button
            type="button"
            disabled
            title="Voice note — coming soon"
            className="inline-flex items-center gap-1.5 rounded-lg border border-dashed border-slate-300 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-400 cursor-not-allowed transition-colors"
          >
            <Mic className="h-3.5 w-3.5" />
            Voice Note
          </button>
          <button
            type="button"
            disabled
            title="Photo upload — coming soon"
            className="inline-flex items-center gap-1.5 rounded-lg border border-dashed border-slate-300 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-400 cursor-not-allowed transition-colors"
          >
            <Paperclip className="h-3.5 w-3.5" />
            Attach Photo
          </button>
        </div>

        {/* Classification preview */}
        {preview && (
          <div className="mt-3 flex flex-wrap items-center gap-1.5">
            <Sparkles className="h-3.5 w-3.5 text-emerald-600" />
            <span className="text-xs text-slate-500">
              Predicted classification:
            </span>
            <span className="inline-flex items-center rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-700">
              {preview.sector}
            </span>
            <span className="inline-flex items-center rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-700">
              {preview.subSector}
            </span>
            {preview.confidence > 0 && (
              <span className="text-xs text-slate-400">
                ({Math.round(preview.confidence * 100)}% confidence)
              </span>
            )}
          </div>
        )}

        <button
          onClick={handleSubmit}
          disabled={processing || !input.trim()}
          className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {processing ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Stripping PII & classifying...
            </>
          ) : (
            <>
              <Send className="h-4 w-4" />
              Submit Feedback
            </>
          )}
        </button>
      </div>
    </div>
  );
}

export default Input;