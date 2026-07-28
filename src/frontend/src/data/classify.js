const API_BASE = "http://localhost:8000";

/**
 * Classify citizen input text using the backend API.
 * Falls back to a simple local guess if the backend is unreachable.
 */
export async function classifyInput(text) {
  try {
    const res = await fetch(`${API_BASE}/api/classify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn("Classification API unavailable, using fallback:", err.message);
  }

  // Fallback classification if API is down
  return fallbackClassify(text);
}

/** Simple local fallback — tries to guess sector from keywords */
function fallbackClassify(text) {
  const lower = text.toLowerCase();
  if (/maternity|maternal|birth|pregnan|newborn|dispensary|hospital|clinic|health|doctor|nurse/.test(lower))
    return { sector: "Health", subSector: "Service Delivery", confidence: 0.7 };
  if (/school|classroom|teacher|pupil|student|bursary|education|ecd|toddler/.test(lower))
    return { sector: "Education", subSector: "Schools & Learning", confidence: 0.7 };
  if (/road|grading|murram|bridge|transport|tarmac/.test(lower))
    return { sector: "Infrastructure", subSector: "Roads & Transport", confidence: 0.7 };
  if (/water|borehole|well|tap|sewer|sanitation|toilet/.test(lower))
    return { sector: "Water & Sanitation", subSector: "Water Supply", confidence: 0.7 };
  if (/cattle|livestock|dip|tick|goat|cow|farm|crop|seed|fertiliz/.test(lower))
    return { sector: "Agriculture", subSector: "Livestock Health", confidence: 0.7 };
  if (/electric|power|solar|streetlight|lighting/.test(lower))
    return { sector: "Energy", subSector: "Rural Electrification", confidence: 0.7 };
  if (/security|police|crime|chief|safety/.test(lower))
    return { sector: "Security", subSector: "Community Safety", confidence: 0.7 };
  return { sector: "Uncategorized", subSector: "Needs Review", confidence: 0 };
}

/**
 * Build a full submission record (used as fallback if offline).
 * Prefer submitToBackend() from store.js for normal use.
 */
export function buildSubmission(rawInput, existingCount) {
  return {
    id: `SUB-${10300 + existingCount + 1}`,
    ward: "Umoja I",
    channel: "Web Form",
    citizenInput: rawInput.trim(),
    sector: "Uncategorized",
    subSector: "Needs Review",
    budgetResult: "Pending budget match via backend...",
    status: "ignored",
    submittedAt: new Date().toISOString().slice(0, 10),
  };
}