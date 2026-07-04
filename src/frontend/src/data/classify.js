/* ─── Ordered keyword rules — first match with most hits wins ─── */
const RULES = [
  {
    sector: "Health",
    subSector: "Maternal Care",
    keywords: ["maternity", "maternal", "birth", "pregnan", "newborn"],
  },
  {
    sector: "Health",
    subSector: "Service Delivery",
    keywords: ["dispensary", "hospital", "clinic", "health", "doctor", "nurse", "medicine", "drugs"],
  },
  {
    sector: "Education",
    subSector: "Early Childhood Development",
    keywords: ["ecd", "toddler", "kindergarten", "nursery", "pre-school", "preschool"],
  },
  {
    sector: "Education",
    subSector: "Schools & Learning",
    keywords: ["school", "classroom", "teacher", "pupil", "student", "bursary", "education", "library"],
  },
  {
    sector: "Infrastructure",
    subSector: "Roads & Transport",
    keywords: ["road", "grading", "murram", "bridge", "transport", "tarmac", "footpath", "drainage"],
  },
  {
    sector: "Water & Sanitation",
    subSector: "Water Supply",
    keywords: ["water", "borehole", "well", "tap", "sewer", "sanitation", "toilet", "latrine"],
  },
  {
    sector: "Agriculture",
    subSector: "Livestock Health",
    keywords: ["cattle", "livestock", "dip", "tick", "goat", "cow", "poultry", "veterinary"],
  },
  {
    sector: "Agriculture",
    subSector: "Crop Farming",
    keywords: ["farm", "crop", "seed", "fertiliz", "irrigation", "harvest", "maize"],
  },
  {
    sector: "Energy",
    subSector: "Rural Electrification",
    keywords: ["electric", "power", "solar", "streetlight", "lighting", "transformer"],
  },
  {
    sector: "Security",
    subSector: "Community Safety",
    keywords: ["security", "police", "crime", "chief", "safety"],
  },
];

/**
 * Classify citizen input text. Uses hits-based scoring — the rule
 * with the most keyword matches wins. Returns sector, subSector, and confidence.
 */
export function classifyInput(text) {
  const lower = text.toLowerCase();
  let best = null; // { rule, hits }

  for (const rule of RULES) {
    const hits = rule.keywords.reduce((n, kw) => (lower.includes(kw) ? n + 1 : n), 0);
    if (hits > 0 && (!best || hits > best.hits)) {
      best = { rule, hits };
    }
  }

  if (!best) {
    return { sector: "Uncategorized", subSector: "Needs Review", confidence: 0 };
  }

  return {
    sector: best.rule.sector,
    subSector: best.rule.subSector,
    confidence: Math.min(0.98, 0.6 + best.hits * 0.15),
  };
}

/**
 * Build a full submission record. New submissions always start as
 * "Web Form" from "Umoja I", with "ignored" status until budget-matched.
 */
export function buildSubmission(rawInput, existingCount) {
  const { sector, subSector, confidence } = classifyInput(rawInput);
  return {
    id: `SUB-${10300 + existingCount}`,
    ward: "Umoja I",
    channel: "Web Form",
    citizenInput: rawInput.trim(),
    sector,
    subSector,
    confidence,
    budgetResult:
      "No matching line found yet in the enacted budget. This request is not yet funded.",
    status: "ignored",
    submittedAt: new Date().toISOString().slice(0, 10),
  };
}