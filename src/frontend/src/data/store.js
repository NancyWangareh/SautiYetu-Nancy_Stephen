import { useSyncExternalStore } from "react";

const API_BASE = "http://localhost:8000";

/* ─── Submissions Store ─── */
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

export function useSubmissions() {
  const data = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
  if (!loaded && !loading) {
    fetchSubmissions();
  }
  return data;
}

/* ─── Wards Store ─── */
let wards = [];
let wardsLoaded = false;
const wardListeners = new Set();

function wardEmit() {
  for (const fn of wardListeners) fn();
}

export async function fetchWards() {
  if (wardsLoaded) return;
  try {
    const res = await fetch(`${API_BASE}/api/wards`);
    if (res.ok) {
      wards = await res.json();
      wardsLoaded = true;
    }
  } catch (err) {
    console.warn("Failed to load wards from API:", err.message);
  }
  wardEmit();
}

function wardsSubscribe(cb) {
  wardListeners.add(cb);
  return () => wardListeners.delete(cb);
}

function wardsGetSnapshot() {
  return wards;
}

export function useWards() {
  const data = useSyncExternalStore(wardsSubscribe, wardsGetSnapshot, wardsGetSnapshot);
  if (!wardsLoaded) {
    fetchWards();
  }
  return data;
}