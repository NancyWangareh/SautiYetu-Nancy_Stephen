import { useSubmissions } from "./store";

const DEFAULT_IGNORED =
  "No matching line found yet in the enacted budget. This request is not yet funded.";

const BUDGET_TEMPLATES = {
  Health: [
    { status: "matched", budgetResult: "Enacted Budget Line 42‑B: Ksh 5,000,000 allocated for dispensary expansion and maternal health services." },
    { status: "matched", budgetResult: "Enacted Budget Line 33‑A: Ksh 2,800,000 allocated for primary healthcare outreach in the ward." },
    { status: "partial", budgetResult: "Enacted Budget Line 42‑B: Ksh 1,200,000 allocated of the Ksh 5,000,000 requested for health facility upgrades." },
  ],
  Education: [
    { status: "matched", budgetResult: "Enacted Budget Line 09‑A: Ksh 3,200,000 allocated for ECD Classroom Construction." },
    { status: "matched", budgetResult: "Enacted Budget Line 11‑C: Ksh 1,500,000 allocated for primary school infrastructure improvement." },
    { status: "partial", budgetResult: "Enacted Budget Line 09‑B: Ksh 900,000 allocated of the Ksh 2,500,000 requested for learning materials." },
  ],
  "Water & Sanitation": [
    { status: "partial", budgetResult: "Enacted Budget Line 21‑D: Ksh 1,800,000 allocated of the Ksh 4,000,000 requested for water pipeline extension." },
    { status: "matched", budgetResult: "Enacted Budget Line 19‑A: Ksh 3,500,000 allocated for borehole drilling and sanitation facilities." },
  ],
  Infrastructure: [
    { status: "ignored", budgetResult: "No matching line found in the enacted budget. Request was not carried into FY 2025/26." },
    { status: "partial", budgetResult: "Enacted Budget Line 15‑A: Ksh 2,000,000 allocated for road grading and murraming across selected wards." },
  ],
  Agriculture: [
    { status: "partial", budgetResult: "Enacted Budget Line 17‑C: Ksh 800,000 allocated of the Ksh 2,000,000 requested for livestock health services." },
    { status: "matched", budgetResult: "Enacted Budget Line 18‑A: Ksh 1,200,000 allocated for agricultural extension and input subsidies." },
  ],
  Energy: [
    { status: "partial", budgetResult: "Enacted Budget Line 28‑A: Ksh 1,500,000 allocated for rural electrification and solar streetlights." },
    { status: "ignored", budgetResult: "No matching line found in the enacted budget. Request was not carried into FY 2025/26." },
  ],
  Security: [
    { status: "ignored", budgetResult: "No matching line found in the enacted budget. Request was not carried into FY 2025/26." },
    { status: "partial", budgetResult: "Enacted Budget Line 55‑B: Ksh 600,000 allocated for community policing and floodlights." },
  ],
  Uncategorized: [
    { status: "ignored", budgetResult: "No matching line found yet in the enacted budget. This request is not yet funded." },
  ],
};

function pickFromId(arr, id) {
  const hash = id.split("").reduce((acc, ch) => acc + ch.charCodeAt(0), 0);
  return arr[hash % arr.length];
}

/**
 * Returns submissions enriched with budget match data.
 * - Seed records keep their original budgetResult & status.
 * - New submissions (with the default "ignored" text) get dynamically generated results.
 */
export function useBudgetMatches() {
  const submissions = useSubmissions();

  return submissions.map((sub) => {
    // Keep pre-existing results (seed data has real budget outcomes)
    if (sub.budgetResult !== DEFAULT_IGNORED) {
      return sub;
    }

    // Generate a simulated budget outcome for new submissions
    const templates = BUDGET_TEMPLATES[sub.sector] || BUDGET_TEMPLATES["Uncategorized"];
    const outcome = pickFromId(templates, sub.id);
    return {
      ...sub,
      status: outcome.status,
      budgetResult: outcome.budgetResult,
    };
  });
}