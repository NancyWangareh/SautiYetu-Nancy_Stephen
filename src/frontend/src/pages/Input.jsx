import { useState, useEffect, useRef } from "react";
<<<<<<< HEAD
import { Loader2, Send, MessageSquarePlus, Sparkles, CheckCircle2, AlertCircle, MapPin, Radio } from "lucide-react";
=======
import { Loader2, Send, MessageSquarePlus, Sparkles, CheckCircle2, Paperclip, AlertCircle, MapPin, Radio } from "lucide-react";
>>>>>>> 49a3f42739e9d47cb6cfb6133f7ab2dd9a65f243
import { classifyInput } from "../data/classify";
import { submitToBackend, useWards } from "../data/store";

const CHANNELS = ["Web Form", "SMS", "USSD", "Baraza"];

function Input({ onNavigate }) {
  const [input, setInput] = useState("");
  const [processing, setProcessing] = useState(false);
  const [toast, setToast] = useState(null);
  const [preview, setPreview] = useState(null);
  const [classifying, setClassifying] = useState(false);
  const [error, setError] = useState("");
  const [ward, setWard] = useState("Umoja I");
  const [channel, setChannel] = useState("Web Form");
  const debounceRef = useRef(null);
  const wards = useWards();

  // Debounced classification preview
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);

    const text = input.trim();
    if (!text) {
      setPreview(null);
      return;
    }

    setClassifying(true);
    debounceRef.current = setTimeout(async () => {
      try {
        const result = await classifyInput(text);
        setPreview(result);
      } catch {
        setPreview(null);
      } finally {
        setClassifying(false);
      }
    }, 500);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [input]);

  function showToast(message, isError = false) {
    setToast({ message, isError, visible: true });
    setTimeout(() => setToast({ message: "", visible: false }), 4000);
  }

  async function handleSubmit() {
    if (!input.trim() || processing) return;
    setProcessing(true);
    setError("");

    try {
      await submitToBackend(input.trim(), ward, channel);
      setInput("");
      setPreview(null);
      showToast(`Submitted from ${ward}! Classified and matched against the enacted budget.`);
      setTimeout(() => onNavigate("submissions"), 800);
    } catch (err) {
      setError(err.message);
      showToast(err.message, true);
    } finally {
      setProcessing(false);
    }
  }

  return (
    <div className="relative mx-auto max-w-2xl px-4 py-8 sm:px-6">
      {/* ── Toast ── */}
      {toast?.visible && (
        <div className={`fixed top-6 right-6 z-50 flex items-center gap-2 rounded-lg border px-4 py-3 text-sm font-medium shadow-lg ${
          toast.isError
            ? "border-red-200 bg-red-50 text-red-800"
            : "border-emerald-200 bg-emerald-50 text-emerald-800"
        }`}>
          {toast.isError ? (
            <AlertCircle className="h-4 w-4 text-red-600" />
          ) : (
            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
          )}
          {toast.message}
        </div>
      )}

      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight text-slate-800">
          Citizen Input Portal
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Submit a citizen request. It is auto-classified by sector, matched
          against the enacted Nairobi County budget, and stored for review.
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
              Citizen request intake — matched against enacted budget lines
            </p>
          </div>
        </div>

        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={processing}
          placeholder="Describe the community need or budget request..."
          rows={5}
          className="w-full rounded-lg border border-slate-200 bg-white p-3 text-sm text-slate-800 placeholder-slate-400 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-200 disabled:opacity-50 resize-none"
        />

        {/* ── Ward & Channel Selectors ── */}
        <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
          {/* Ward Dropdown */}
          <div>
            <label className="mb-1 flex items-center gap-1 text-xs font-medium text-slate-500">
              <MapPin className="h-3 w-3" />
              Ward
            </label>
            <select
              value={ward}
              onChange={(e) => setWard(e.target.value)}
              disabled={processing}
              className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-200 disabled:opacity-50"
            >
              {wards.length === 0 ? (
                <option value="Umoja I">Umoja I</option>
              ) : (
                wards.map((w) => (
                  <option key={w.ward_name} value={w.ward_name}>
                    {w.ward_name} ({w.constituency})
                  </option>
                ))
              )}
            </select>
          </div>

          {/* Channel Selector */}
          <div>
            <label className="mb-1 flex items-center gap-1 text-xs font-medium text-slate-500">
              <Radio className="h-3 w-3" />
              Channel
            </label>
            <select
              value={channel}
              onChange={(e) => setChannel(e.target.value)}
              disabled={processing}
              className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-200 disabled:opacity-50"
            >
              {CHANNELS.map((ch) => (
                <option key={ch} value={ch}>{ch}</option>
              ))}
            </select>
          </div>
<<<<<<< HEAD
=======
        </div>

        {/* ── Dummy attachment button ── */}
        <div className="mt-2 flex items-center gap-1">
          <button
            type="button"
            disabled
            title="Photo upload — coming soon"
            className="inline-flex items-center gap-1.5 rounded-lg border border-dashed border-slate-300 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-400 cursor-not-allowed transition-colors"
          >
            <Paperclip className="h-3.5 w-3.5" />
            Attach Photo
          </button>
>>>>>>> 49a3f42739e9d47cb6cfb6133f7ab2dd9a65f243
        </div>

        {/* Classification preview */}
        {(preview || classifying) && (
          <div className="mt-3 flex flex-wrap items-center gap-1.5">
            <Sparkles className="h-3.5 w-3.5 text-emerald-600" />
            <span className="text-xs text-slate-500">
              Predicted classification:
            </span>
            {classifying ? (
              <span className="text-xs text-slate-400 italic">analyzing...</span>
            ) : (
              <>
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
              </>
            )}
          </div>
        )}

        {error && (
          <div className="mt-3 flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
            {error}
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
              Classifying & matching budget...
            </>
          ) : (
            <>
              <Send className="h-4 w-4" />
              Submit Request
            </>
          )}
        </button>
      </div>
    </div>
  );
}

export default Input;