const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `API error ${res.status}`);
  }
  return res.json();
}

// Classification
export const classifyInput = (text) =>
  request("/api/submissions/classify", {
    method: "POST",
    body: JSON.stringify({ text }),
  });

// Submissions
export const createSubmission = ({ text, ward, channel }) =>
  request("/api/submissions", {
    method: "POST",
    body: JSON.stringify({ text, ward: ward || "Umoja I", channel: channel || "Web Form" }),
  });

export const fetchSubmissions = (params = {}) => {
  const qs = new URLSearchParams(params).toString();
  return request(`/api/submissions${qs ? `?${qs}` : ""}`);
};

export const fetchSubmission = (id) =>
  request(`/api/submissions/${id}`);

// Matches
export const fetchMatches = (params = {}) => {
  const qs = new URLSearchParams(params).toString();
  return request(`/api/matches${qs ? `?${qs}` : ""}`);
};

export const fetchMatchStats = (ward) =>
  request(`/api/matches/stats${ward ? `?ward=${encodeURIComponent(ward)}` : ""}`);

export const rematchSubmission = (id) =>
  request(`/api/matches/rematch/${id}`, { method: "POST" });