import { useState, useEffect } from "react";
import { Loader2, Send, MessageSquarePlus, Sparkles, CheckCircle2, Mic, Paperclip } from "lucide-react";
import { classifyInput, createSubmission } from "../data/api";
import { addSubmissionToCache } from "../data/store";

const WARDS = [
  "Umoja I", "Umoja II", "Ruai",
  "Kayole North", "Kayole South",
  "Dandora Area I", "Dandora Area II", "Dandora Area III", "Dandora Area IV",
  "Embakasi Central",
  "Kariobangi North", "Kariobangi South",
  "Mihango", "Njiru",
];

const CHANNELS = [
  { value: "Web Form", label: "Web Form" },
  { value: "SMS", label: "SMS" },
  { value: "USSD", label: "USSD" },
  { value: "WhatsApp", label: "WhatsApp" },
  { value: "Baraza", label: "Baraza" },
  { value: "Voice", label: "Voice Note" },
  { value: "Image", label: "Photo / Memo" },
];

// ── Progress steps ──
const STEPS = [
  { key: "translating", label: "Translating Sheng/Swahili..." },
  { key: "classifying", label: "Classifying with AI..." },
  { key: "embedding", label: "Finding matching budget lines..." },
  { key: "saving", label: "Saving to database..." },
];

function Input({ onNavigate }) {
  const [input, setInput] = useState("");
  const [ward, setWard] = useState("Umoja I");
  const [channel, setChannel] = useState("Web Form");
  const [processing, setProcessing] = useState(false);
  const [progressStep, setProgressStep] = useState(0);
  const [toast, setToast] = useState(null);

  // Live classification preview (debounced)
  const [preview, setPreview] = useState(null);
  useEffect(() => {
    if (!input.trim()) { setPreview(null); return; }
    const timer = setTimeout(async () => {
      try {
        const result = await classifyInput(input.trim());
        setPreview(result);
      } catch { setPreview(null); }
    }, 600);
    return () => clearTimeout(timer);
  }, [input]);

  function showToast(message, isError = false) {
    setToast({ message, visible: true, isError });
    setTimeout(() => setToast({ message, visible: false }), 4000);
  }

  async function handleSubmit() {
    if (!input.trim() || processing) return;
    setProcessing(true);
    setProgressStep(0);

    // Simulate step progression while the API works
    const stepInterval = setInterval(() => {
      setProgressStep((prev) => Math.min(prev + 1, STEPS.length - 1));
    }, 800);

    try {
      const result = await createSubmission({ text: input.trim(), ward, channel });

      clearInterval(stepInterval);
      setProgressStep(STEPS.length); // all done
      addSubmissionToCache(result);
      setInput("");

      showToast(
        result.status === "matched"
          ? `✅ Matched! ${(result.budget_result ?? "").slice(0, 80)}...`
          : `📋 Submitted. Status: ${result.status}`
      );
      onNavigate("matches");
    } catch (err) {
      clearInterval(stepInterval);
      showToast(`Error: ${err.message}`, true);
    } finally {
      setProcessing(false);
      setProgressStep(0);
    }
  }

  return (
    <div className="relative mx-auto max-w-2xl px-4 py-8 sm:px-6">
      {/* Toast */}
      {toast?.visible && (
        <div
          className={`fixed top-6 right-6 z-50 flex items-center gap-2 rounded-lg border px-4 py-3 text-sm font-medium shadow-lg ${
            toast.isError
              ? "border-red-200 bg-red-50 text-red-800"
              : "border-emerald-200 bg-emerald-50 text-emerald-800"
          }`}
        >
          <CheckCircle2 className={`h-4 w-4 ${toast.isError ? "text-red-600" : "text-emerald-600"}`} />
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

      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        {/* Header */}
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

        {/* Ward + Channel row */}
        <div className="mb-3 grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">Ward</label>
            <select
              value={ward}
              onChange={(e) => setWard(e.target.value)}
              disabled={processing}
              className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-200 disabled:opacity-50"
            >
              {WARDS.map((w) => (<option key={w} value={w}>{w}</option>))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">Channel</label>
            <select
              value={channel}
              onChange={(e) => setChannel(e.target.value)}
              disabled={processing}
              className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-200 disabled:opacity-50"
            >
              {CHANNELS.map((c) => (<option key={c.value} value={c.value}>{c.label}</option>))}
            </select>
          </div>
        </div>

        {/* Text input */}
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={processing}
          placeholder="e.g., We need the Umoja dispensary maternity wing expanded..."
          rows={5}
          className="w-full rounded-lg border border-slate-200 bg-white p-3 text-sm text-slate-800 placeholder-slate-400 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-200 disabled:opacity-50 resize-none"
        />

        {/* Attachment buttons */}
        <div className="mt-2 flex items-center gap-1">
          <button type="button" disabled title="Voice note — coming soon"
            className="inline-flex items-center gap-1.5 rounded-lg border border-dashed border-slate-300 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-400 cursor-not-allowed">
            <Mic className="h-3.5 w-3.5" /> Voice Note
          </button>
          <button type="button" disabled title="Photo upload — coming soon"
            className="inline-flex items-center gap-1.5 rounded-lg border border-dashed border-slate-300 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-400 cursor-not-allowed">
            <Paperclip className="h-3.5 w-3.5" /> Attach Photo
          </button>
        </div>

        {/* Live AI classification preview */}
        {preview && (
          <div className="mt-3 flex flex-wrap items-center gap-1.5">
            <Sparkles className="h-3.5 w-3.5 text-emerald-600" />
            <span className="text-xs text-slate-500">Predicted classification:</span>
            <span className="inline-flex items-center rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-700">
              {preview.sector}
            </span>
            <span className="inline-flex items-center rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-700">
              {preview.sub_sector}
            </span>
            {preview.confidence > 0 && (
              <span className="text-xs text-slate-400">
                ({Math.round(preview.confidence * 100)}% confidence)
              </span>
            )}
          </div>
        )}

        {/* ── NEW: Step progress during submission ── */}
        {processing && (
          <div className="mt-3 rounded-lg border border-emerald-100 bg-emerald-50/50 p-3">
            <div className="mb-2 flex items-center gap-2 text-xs font-medium text-emerald-700">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Processing your submission...
            </div>
            <div className="space-y-1.5">
              {STEPS.map((step, i) => (
                <div key={step.key} className="flex items-center gap-2 text-xs">
                  {i < progressStep ? (
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 flex-shrink-0" />
                  ) : i === progressStep ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin text-emerald-600 flex-shrink-0" />
                  ) : (
                    <div className="h-3.5 w-3.5 rounded-full border border-slate-200 flex-shrink-0" />
                  )}
                  <span className={
                    i < progressStep ? "text-emerald-600" :
                    i === progressStep ? "text-slate-700 font-medium" :
                    "text-slate-400"
                  }>
                    {step.label}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Submit button */}
        <button
          onClick={handleSubmit}
          disabled={processing || !input.trim()}
          className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {processing ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Processing...
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