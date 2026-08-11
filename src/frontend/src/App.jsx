import { useState, useEffect } from "react";
import { 
  ShieldCheck, 
  FileUp, 
  FileText,
  Users,
  GitCompareArrows,
  FolderOpen,
  BarChart3,
  Inbox,
  Search,
  AlertCircle,
  Loader2,
} from "lucide-react";

import Participation from "./pages/Participation";
import Submissions from "./pages/Submissions";
import Matches from "./pages/Matches";
import Reports from "./pages/Reports";
import BudgetUpload from "./pages/BudgetUpload";
import BudgetDocuments from "./pages/BudgetDocuments";

function App() {
  const [activeView, setActiveView] = useState('upload');

  const renderView = () => {
    switch (activeView) {
      case 'upload':
        return <BudgetUpload />;
      case 'participation':
        return <Participation />;
      case 'documents':
        return <BudgetDocuments />;
      case 'reconciliation':
        return <ReconciliationPage />;
      case 'reports':
        return <Reports />;
      case 'submissions':
        return <Submissions />;
      case 'matches':
        return <Matches />;
      default:
        return <BudgetUpload />;
    }
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-white">

      {/* Sidebar */}
      <aside className="w-64 h-full flex flex-col flex-shrink-0 bg-[#0B3523] text-white">
        
        {/* Brand Header */}
        <div className="flex items-center gap-3 px-6 py-6 border-b border-[#13402A]">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#14A562]">
            <ShieldCheck size={20} className="text-white" />
          </div>
          <div>
            <h1 className="text-base font-semibold leading-none tracking-tight">
              SAUTI YETU
            </h1>
            <p className="text-xs text-[#82A895] mt-1.5">Budget accountability</p>
          </div>
        </div>

        {/* Navigation */}
        <div className="flex-1 overflow-y-auto px-3 py-4 space-y-4">

          {/* STEP 1: Budget Data */}
          <div>
            <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-wider text-[#5A8A72]">
              Step 1 — Budget Data
            </p>

            <NavButton
              active={activeView === 'upload'}
              onClick={() => setActiveView('upload')}
              icon={<FileUp size={18} />}
              label="Upload Budget PDF"
              sub="Proposed or Enacted"
            />

            <NavButton
              active={activeView === 'documents'}
              onClick={() => setActiveView('documents')}
              icon={<FolderOpen size={18} />}
              label="Budget Documents"
              sub="View all uploads"
            />
          </div>

          {/* STEP 2: Citizen Voice */}
          <div>
            <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-wider text-[#5A8A72]">
              Step 2 — Citizen Voice
            </p>

            <NavButton
              active={activeView === 'participation'}
              onClick={() => setActiveView('participation')}
              icon={<Users size={18} />}
              label="Participation Data"
              sub="Upload & auto-match"
            />

                        <NavButton
              active={activeView === 'submissions'}
              onClick={() => setActiveView('submissions')}
              icon={<Inbox size={18} />}
              label="Submissions"
              sub="Extracted citizen points"
            />
          </div>

          {/* STEP 3: Accountability */}
          <div>
            <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-wider text-[#5A8A72]">
              Step 3 — Accountability
            </p>

            <NavButton
              active={activeView === 'reconciliation'}
              onClick={() => setActiveView('reconciliation')}
              icon={<GitCompareArrows size={18} />}
              label="Reconciliation"
              sub="Proposed vs Enacted"
            />
            
            <NavButton
              active={activeView === 'matches'}
              onClick={() => setActiveView('matches')}
              icon={<Search size={18} />}
              label="Budget Search"
              sub="Semantic search"
            />

            <NavButton
              active={activeView === 'reports'}
              onClick={() => setActiveView('reports')}
              icon={<BarChart3 size={18} />}
              label="CSO Reports"
              sub="Export & analysis"
            />
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 shrink-0 border-t border-[#13402A]">
          <div className="text-[11px] text-[#82A895] leading-relaxed">
            County: Nairobi · FY 2025/26
            <br />
            <span className="text-[#5A8A72]">Budget Lifecycle Tracker</span>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex flex-col flex-grow h-full overflow-hidden bg-[#FAFAFA]">
        
        {/* Top Header */}
        <header className="flex h-14 items-center gap-3 border-b border-gray-200 bg-white px-6 shrink-0">
          <span className="text-sm font-medium text-gray-600">
            Budget Accountability Dashboard — Nairobi County
          </span>
          <span className="ml-auto text-xs text-gray-400">
            {activeView === 'upload' && "Upload Proposed or Enacted Budget PDF"}
            {activeView === 'documents' && "All Budget Documents"}
            {activeView === 'participation' && "Public Participation Matching"}
            {activeView === 'reconciliation' && "Proposed vs Enacted Reconciliation"}
            {activeView === 'reports' && "CSO Reports & Analysis"}
          </span>
        </header>

        <main className="flex-grow overflow-y-auto p-4">
          {renderView()}
        </main>
      </div>
    </div>
  );
}

/* ─── Reusable Nav Button ─── */
function NavButton({ active, onClick, icon, label, sub = null, disabled = false }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`cursor-pointer w-full flex items-center gap-3 px-3 py-2 rounded-md transition-colors text-sm font-medium ${
        disabled
          ? "text-[#5A8A72] cursor-not-allowed opacity-50"
          : active
          ? "bg-[#1A4B35] text-white"
          : "text-[#E2E8F0] hover:bg-[#13402A]"
      }`}
    >
      {icon}
      <div className="flex-1 text-left">
        <div>{label}</div>
        {sub && <div className="text-[10px] text-[#82A895] leading-tight">{sub}</div>}
      </div>
    </button>
  );
}

/* ─── Placeholder until reconciliation page is built ─── */
function ReconciliationPage() {
  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("http://localhost:8000/api/submissions?limit=200")
      .then(r => r.json())
      .then(data => setSubmissions(Array.isArray(data) ? data : (data.submissions || [])))
      .finally(() => setLoading(false));
  }, []);

  const funded = submissions.filter(s => s.match?.status === "matched").length;
  const partial = submissions.filter(s => s.match?.status === "partial").length;
  const ignored = submissions.filter(s => s.match?.status === "ignored").length;

  if (loading) return <div className="flex items-center justify-center py-16 text-slate-400">Loading...</div>;

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <h1 className="text-2xl font-bold tracking-tight text-slate-800 mb-2">Reconciliation</h1>
      <p className="text-sm text-slate-500 mb-6">Compare citizen concerns against the budget to see what was funded.</p>

      <div className="grid grid-cols-3 gap-4 mb-8">
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-5 text-center">
          <p className="text-3xl font-bold text-emerald-700">{funded}</p>
          <p className="text-sm text-emerald-600">Funded</p>
        </div>
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-5 text-center">
          <p className="text-3xl font-bold text-amber-700">{partial}</p>
          <p className="text-sm text-amber-600">Partially Funded</p>
        </div>
        <div className="rounded-xl border border-red-200 bg-red-50 p-5 text-center">
          <p className="text-3xl font-bold text-red-700">{ignored}</p>
          <p className="text-sm text-red-600">Not Funded</p>
        </div>
      </div>

      {submissions.length === 0 ? (
        <div className="text-center py-12 text-slate-400">Upload participation data to see reconciliation.</div>
      ) : (
        <div className="space-y-2">
          {submissions.filter(s => s.citizen_input?.length > 10).slice(0, 20).map(s => (
            <div key={s.id} className="flex items-center justify-between rounded-lg border border-slate-200 bg-white p-4 text-sm">
              <div className="flex-1 min-w-0">
                <span className="font-mono text-xs text-slate-400 mr-2">{s.id}</span>
                <span className="text-slate-700">{(s.citizen_input || "").slice(0, 120)}{(s.citizen_input?.length || 0) > 120 ? "…" : ""}</span>
              </div>
              <span className={`shrink-0 ml-3 rounded-full px-2.5 py-0.5 text-xs font-medium ${
                s.match?.status === "matched" ? "bg-emerald-100 text-emerald-700" :
                s.match?.status === "partial" ? "bg-amber-100 text-amber-700" :
                "bg-red-100 text-red-700"}`}>
                {s.match?.status === "matched" ? "Funded" : s.match?.status === "partial" ? "Partial" : "Not Funded"}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default App;