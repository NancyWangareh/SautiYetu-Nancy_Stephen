import { useSyncExternalStore } from "react";

/* ─── Seed data ─── */
const SEED = [
  {
    id: "SUB-10241",
    ward: "Umoja I",
    channel: "SMS",
    citizenInput:
      "We need a maternity wing at the Umoja dispensary. Women are traveling too far to give birth.",
    sector: "Health",
    subSector: "Maternal Care",
    budgetResult:
      "Enacted Budget Line 42-B: Ksh 5,000,000 allocated for Umoja Dispensary Expansion.",
    status: "matched",
    submittedAt: "2025-06-14",
  },
  {
    id: "SUB-10188",
    ward: "Ruai",
    channel: "USSD",
    citizenInput:
      "Our cattle keep falling sick. We requested a cattle dip near Ruai market to control ticks.",
    sector: "Agriculture",
    subSector: "Livestock Health",
    budgetResult:
      "Enacted Budget Line 17-C: Ksh 800,000 allocated of the Ksh 2,000,000 requested for Ruai Cattle Dip.",
    status: "partial",
    submittedAt: "2025-06-09",
  },
  {
    id: "SUB-10156",
    ward: "Kayole North",
    channel: "Baraza",
    citizenInput:
      "The Kayole–Soweto access road is impassable when it rains. We asked for grading and murraming.",
    sector: "Infrastructure",
    subSector: "Roads & Transport",
    budgetResult:
      "No matching line found in the enacted budget. Request was not carried into FY 2025/26.",
    status: "ignored",
    submittedAt: "2025-05-28",
  },
  {
    id: "SUB-10122",
    ward: "Dandora Area II",
    channel: "Web Form",
    citizenInput:
      "We need two more ECD classrooms at Dandora Primary. Toddlers are learning under a tree.",
    sector: "Education",
    subSector: "Early Childhood Development",
    budgetResult:
      "Enacted Budget Line 09-A: Ksh 3,200,000 allocated for ECD Classroom Construction, Dandora Area II.",
    status: "matched",
    submittedAt: "2025-05-21",
  },
];

/* ─── Store ─── */
let records = [...SEED];
const listeners = new Set();

function emit() {
  for (const fn of listeners) fn();
}

export function addSubmission(record) {
  records = [record, ...records];
  emit();
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

/**
 * React hook — returns all submissions reactively.
 */
export function useSubmissions() {
  return useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
}