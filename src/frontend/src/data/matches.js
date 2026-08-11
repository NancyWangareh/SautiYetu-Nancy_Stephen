import { useSubmissions } from "./store";

/**
 * Returns all submissions (now loaded from the backend API).
 * Each submission already contains its budget matching result
 * as determined by the backend (against budget_lines.csv + semantic search).
 *
 * No more mock/template data — all results come from the actual budget data.
 */
export function useBudgetMatches() {
  const submissions = useSubmissions();
  return submissions; 
}