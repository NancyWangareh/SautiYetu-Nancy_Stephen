const API_BASE = "http://localhost:8000";

/**
 * Classify citizen input text using the backend API.
 * No fallback — if the API is unreachable, the error propagates.
 */
export async function classifyInput(text) {
  const res = await fetch(`${API_BASE}/api/submissions/classify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Classification failed (${res.status})`);
  }
  return res.json();
}

/**
 * Check if the citizen input matches any existing public participation data.
 * No fallback — if the API is unreachable, the error propagates.
 */
export async function checkParticipation(text) {
  if (!text || text.trim().length < 10) {
    return { hasMatch: false, boostFactor: 0.0, matches: [] };
  }
  const res = await fetch(`${API_BASE}/api/participation/check`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Participation check failed (${res.status})`);
  }
  return res.json();
}