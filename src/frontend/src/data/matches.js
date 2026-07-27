import { useState, useEffect } from "react";
import { fetchMatches } from "./api";

/**
 * React hook — fetches all budget matches from the backend API.
 * This replaces the dummy BUDGET_TEMPLATES + pickFromId.
 */
export function useBudgetMatches(params = {}) {
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  async function refresh() {
    setLoading(true);
    try {
      const data = await fetchMatches(params);
      const mapped = data.matches.map((m) => ({
        id: m.id,
        ward: m.ward,
        channel: m.channel,
        citizenInput: m.citizen_input ?? m.citizenInput,
        sector: m.sector,
        subSector: m.sub_sector ?? m.subSector,
        confidence: m.classification_confidence ?? m.confidence ?? 0,
        budgetResult: m.budget_result ?? m.budgetResult,
        status: m.status ?? "ignored",
        similarityScore: m.similarity_score ?? m.similarityScore,
        matchedLineId: m.matched_line_id ?? m.matchedLineId,
        matchedAmountKsh: m.matched_amount_ksh ?? m.matchedAmountKsh,
        submittedAt: m.submitted_at
          ? m.submitted_at.slice(0, 10)
          : m.submittedAt,
      }));
      setMatches(mapped);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, [JSON.stringify(params)]);

  return { matches, loading, error, refresh };
}