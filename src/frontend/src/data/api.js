const API = import.meta.env.VITE_API_URL || "";

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

// ── Classification
export const classifyInput = (text) =>
  request("/api/submissions/classify", {
    method: "POST",
    body: JSON.stringify({ text }),
  });

// ── Participation check
export const checkParticipation = (text) =>
  request("/api/participation/check", {
    method: "POST",
    body: JSON.stringify({ text }),
  });

// ── Submissions
export const createSubmission = ({ text, ward, channel }) =>
  request("/api/submissions", {
    method: "POST",
    body: JSON.stringify({ text, ward, channel }),
  });

export const fetchSubmissions = (params = {}) => {
  const qs = new URLSearchParams(params).toString();
  return request(`/api/submissions${qs ? `?${qs}` : ""}`);
};

// ── Matches
export const fetchMatches = (params = {}) => {
  const qs = new URLSearchParams(params).toString();
  return request(`/api/matches${qs ? `?${qs}` : ""}`);
};

export const fetchMatchStats = (ward) =>
  request(`/api/matches/stats${ward ? `?ward=${encodeURIComponent(ward)}` : ""}`);

export const rematchSubmission = (id) =>
  request(`/api/matches/rematch/${id}`, { method: "POST" });

// ── Budget
export const searchBudget = (query, topK = 5) =>
  request("/api/budget/search", {
    method: "POST",
    body: JSON.stringify({ query, top_k: topK }),
  });

export const simplifyBudget = (text, useLlm = false) =>
  request("/api/budget/simplify", {
    method: "POST",
    body: JSON.stringify({ text, use_llm: useLlm }),
  });

export const uploadBudget = (file, fiscalYear = "2024/25") => {
  const formData = new FormData();
  formData.append("file", file);
  return fetch(`${API}/api/budget/upload?fiscal_year=${encodeURIComponent(fiscalYear)}`, {
    method: "POST",
    body: formData,
  }).then((res) => {
    if (!res.ok) throw new Error("Upload failed");
    return res.json();
  });
};

export const fetchDocuments = () => request("/api/budget/documents");
export const deleteDocument = (id) =>
  request(`/api/budget/documents/${id}`, { method: "DELETE" });

// ── Participation
export const uploadParticipation = (file, county = "") => {
  const formData = new FormData();
  formData.append("file", file);
  if (county) formData.append("county", county);
  return fetch(`${API}/api/participation/upload`, {
    method: "POST",
    body: formData,
  }).then((res) => {
    if (!res.ok) throw new Error("Upload failed");
    return res.json();
  });
};

export const matchPoints = (pointIds, sessionId, ward = "Umoja I") =>
  request("/api/participation/match-points", {
    method: "POST",
    body: JSON.stringify({ point_ids: pointIds, session_id: sessionId, ward }),
  });

// ── Reports
export const fetchReport = (params = {}) => {
  const qs = new URLSearchParams(params).toString();
  return request(`/api/reports${qs ? `?${qs}` : ""}`);
};

// ── Wards
export const fetchWards = () => request("/api/wards");