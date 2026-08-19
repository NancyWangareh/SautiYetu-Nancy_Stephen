import { useState } from "react";
import { 
  ShieldCheck, 
  FileUp, 
  Users,
  FolderOpen,
  BarChart3,
  Inbox,
  Search,
  ChevronDown,
  ChevronUp,
  ExternalLink,
} from "lucide-react";

import Participation from "./pages/Participation";
import Submissions from "./pages/Submissions";
import Matches from "./pages/Matches";
import Reports from "./pages/Reports";
import BudgetUpload from "./pages/BudgetUpload";
import BudgetDocuments from "./pages/BudgetDocuments";
import Landing from "./pages/Landing";

function App() {
  const [activeView, setActiveView] = useState('landing');
  const [moreOpen, setMoreOpen] = useState(false);

  if (activeView === 'landing') {
    return <Landing onLaunch={() => setActiveView('upload')} />;
  }

  const renderView = () => {
    switch (activeView) {
      case 'upload':
        return <BudgetUpload />;
      case 'participation':
        return <Participation />;
      case 'documents':
        return <BudgetDocuments />;
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
            {/* <p className="text-xs text-[#82A895] mt-1.5">Budget accountability</p> */}
          </div>
        </div>

        {/* Navigation */}
        <div className="flex-1 overflow-y-auto px-3 py-4">
          <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-wider text-[#5A8A72]">
            Your workflow
          </p>

          <div className="space-y-1">
            <NavButton
              step="1"
              active={activeView === 'upload'}
              onClick={() => setActiveView('upload')}
              icon={<FileUp size={18} />}
              label="Upload Budget PDF"
              sub="Enacted budget"
            />
            <NavButton
              step="2"
              active={activeView === 'participation'}
              onClick={() => setActiveView('participation')}
              icon={<Users size={18} />}
              label="Upload Participation Data"
              sub="Extract & auto-match"
            />
            <NavButton
              step="3"
              active={activeView === 'matches'}
              onClick={() => setActiveView('matches')}
              icon={<Search size={18} />}
              label="Matches"
              sub="Present vs Absent"
            />
            <NavButton
              step="4"
              active={activeView === 'reports'}
              onClick={() => setActiveView('reports')}
              icon={<BarChart3 size={18} />}
              label="CSO Reports"
              sub="Export & analysis"
            />
          </div>

          {/* Where to get the documents */}
          <a
            href="https://nairobiassembly.go.ke/papers-laid/"
            target="_blank"
            rel="noreferrer"
            className="mt-4 flex items-start gap-2.5 rounded-lg border border-[#13402A] bg-[#0F3D28] px-3 py-3 text-xs text-[#9FD5B4] transition-colors hover:bg-[#13402A]"
          >
            <ExternalLink size={14} className="mt-0.5 shrink-0" />
            <span>
              Get the budget &amp; participation PDFs from the Nairobi County Assembly —{" "}
              <span className="font-semibold text-white">Papers Laid</span>.
            </span>
          </a>

          {/* More info (collapsible) */}
          <div className="mt-4">
            <button
              onClick={() => setMoreOpen(!moreOpen)}
              className="flex w-full items-center justify-between px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-[#5A8A72] transition-colors hover:text-[#9FD5B4]"
            >
              More info
              {moreOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </button>
            {moreOpen && (
              <div className="mt-1 space-y-1">
                <NavButton
                  active={activeView === 'documents'}
                  onClick={() => setActiveView('documents')}
                  icon={<FolderOpen size={18} />}
                  label="Budget Documents"
                  sub="Manage uploads"
                />
                <NavButton
                  active={activeView === 'submissions'}
                  onClick={() => setActiveView('submissions')}
                  icon={<Inbox size={18} />}
                  label="Submissions"
                  sub="Raw citizen points"
                />
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex flex-col flex-grow h-full overflow-hidden bg-[#FAFAFA]">
        
        {/* Top Header */}
        <header className="flex h-14 items-center gap-3 border-b border-gray-200 bg-white px-6 shrink-0">
          <button
            onClick={() => setActiveView('landing')}
            className="text-xs font-medium text-gray-400 transition-colors hover:text-emerald-700"
          >
            ← Home
          </button>
          <span className="text-sm font-medium text-gray-600">
            Dashboard
          </span>
          <span className="ml-auto text-xs text-gray-400">
            {activeView === 'upload' && "Step 1 of 4 · Upload Enacted Budget PDF"}
            {activeView === 'participation' && "Step 2 of 4 · Upload Participation Data"}
            {activeView === 'matches' && "Step 3 of 4 · Matches"}
            {activeView === 'reports' && "Step 4 of 4 · CSO Reports"}
            {activeView === 'documents' && "Budget Documents"}
            {activeView === 'submissions' && "Submissions"}
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
function NavButton({ active, onClick, icon, label, sub = null, disabled = false, step = null }) {
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
      {step && (
        <span
          className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold ${
            active ? "bg-[#14A562] text-white" : "bg-[#13402A] text-[#82A895]"
          }`}
        >
          {step}
        </span>
      )}
      {icon}
      <div className="flex-1 text-left">
        <div>{label}</div>
        {sub && <div className="text-[10px] text-[#82A895] leading-tight">{sub}</div>}
      </div>
    </button>
  );
}

export default App;