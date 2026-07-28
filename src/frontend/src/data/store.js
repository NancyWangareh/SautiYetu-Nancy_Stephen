import { useSyncExternalStore } from "react";

const API_BASE = "http://localhost:8000";

/* ─── Store ─── */
let records = [];
let loaded = false;
let loading = false;
const listeners = new Set();

function emit() {
  for (const fn of listeners) fn();
}

/** Fetch all submissions from the backend */
export async function fetchSubmissions() {
  if (loading) return;
  loading = true;

  try {
    const res = await fetch(`${API_BASE}/api/submissions`);
    if (res.ok) {
      records = await res.json();
      loaded = true;
    }
  } catch (err) {
    console.warn("Failed to load submissions from API:", err.message);
    // Keep whatever records we had
  } finally {
    loading = false;
    emit();
  }
}

/** Submit a new citizen input via the backend */
export async function submitToBackend(text, ward = "Umoja I", channel = "Web Form") {
  const res = await fetch(`${API_BASE}/api/submissions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, ward, channel }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `Server error: ${res.status}`);
  }

  const record = await res.json();
  records = [record, ...records];
  emit();
  return record;
}

export function getSubmissionCount() {
  return records.length;
}

function subscribe(cb) {
  listeners.add(cb);
  return () => listeners.delete(cb);
}

function getSnapshot() {
  return records;
}

/**
 * React hook — returns all submissions reactively.
 * Auto-fetches from the backend on first use.
 */
export function useSubmissions() {
  const data = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);

  // Trigger fetch on first mount
  if (!loaded && !loading) {
    fetchSubmissions();
  }

  return data;
}