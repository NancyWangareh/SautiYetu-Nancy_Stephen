import { useState, useEffect, useCallback } from "react";
import { fetchSubmissions, fetchSubmission } from "./api";

// Cache for live-updating after a new submission
let _submissions = [];
const _listeners = new Set();

function _notify(submissions) {
  _submissions = submissions;
  for (const fn of _listeners) fn();
}

/**
 * React hook — fetches all submissions from the backend API.
 */
export function useSubmissions(params = {}) {
  const [submissions, setSubmissions] = useState(_submissions);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchSubmissions(params);
      // Map API snake_case → frontend camelCase for backward compatibility
      const mapped = data.submissions.map(_mapSubmission);
      setSubmissions(mapped);
      _notify(mapped);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [JSON.stringify(params)]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Also listen for push updates
  useEffect(() => {
    const fn = () => setSubmissions(_submissions);
    _listeners.add(fn);
    return () => _listeners.delete(fn);
  }, []);

  return { submissions, loading, error, refresh };
}

/**
 * Get a single submission by ID.
 */
export function useSubmission(id) {
  const [submission, setSubmission] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSubmission(id)
      .then((data) => setSubmission(_mapSubmission(data)))
      .catch(() => setSubmission(null))
      .finally(() => setLoading(false));
  }, [id]);

  return { submission, loading };
}

/**
 * Add a submission to the local cache (for instant UI update after POST).
 */
export function addSubmissionToCache(submission) {
  _submissions = [_mapSubmission(submission), ..._submissions];
  for (const fn of _listeners) fn();
}

/**
 * Get the current count (from cache).
 */
export function getSubmissionCount() {
  return _submissions.length;
}

// ── Helpers ──

function _mapSubmission(s) {
  return {
    id: s.id,
    ward: s.ward,
    channel: s.channel,
    citizenInput: s.citizen_input ?? s.citizenInput,
    sector: s.sector,
    subSector: s.sub_sector ?? s.subSector,
    confidence: s.classification_confidence ?? s.confidence ?? 0,
    budgetResult: s.budget_result ?? s.budgetResult,
    status: s.status,
    similarityScore: s.similarity_score ?? s.similarityScore,
    submittedAt: s.submitted_at
      ? s.submitted_at.slice(0, 10)
      : s.submittedAt,
  };
}