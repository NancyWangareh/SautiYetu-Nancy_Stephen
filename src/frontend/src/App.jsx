import { useState } from "react";
import {
  ShieldCheck, MessageSquarePlus, FileUp, Radio,
  Inbox, GitCompareArrows, BarChart3, FolderOpen,
} from "lucide-react";

import Input from "./pages/Input";
import BudgetUpload from "./pages/BudgetUpload";
import BudgetDocuments from "./pages/BudgetDocuments";
import Matches from "./pages/Matches";
import Submissions from "./pages/Submissions";

function App() {
  const [activeView, setActiveView] = useState("input");

  const renderView = () => {
    switch (activeView) {
      case "input":
        return <Input onNavigate={setActiveView} />;
      case "upload":
        return <BudgetUpload />;
      case "documents":
        return <BudgetDocuments />;
      case "matches":
        return <Matches />;
      case "submissions":
        return <Submissions />;
      case "analytics":
        return <AnalyticsPlaceholder />;
      default:
        return <Input onNavigate={setActiveView} />;
    }
  };

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
              Sauti Tracker
            </h1>
            <p className="text-xs text-[#82A895] mt-1.5">Budget accountability</p>
          </div>
        </div>

        {/* Navigation */}
        <div className="flex-1 overflow-y-auto px-3 py-4 space-y-4">
          {/* DATA INPUTS */}
          <div>
            <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-wider text-[#5A8A72]">
              Data Inputs
            </p>

            <NavButton
              active={activeView === "input"}
              onClick={() => setActiveView("input")}
              icon={<MessageSquarePlus size={18} />}
              label="Simulate Citizen Input"
            />

            <NavButton
              active={activeView === "upload"}
              onClick={() => setActiveView("upload")}
              icon={<FileUp size={18} />}
              label="Upload Budget PDF"
            />

            <NavButton
              active={activeView === "documents"}
              onClick={() => setActiveView("documents")}
              icon={<FolderOpen size={18} />}
              label="Budget Documents"
            />

            <NavButton
              active={false}
              onClick={() => {}}
              icon={<Radio size={18} />}
              label="Channel Webhooks"
              disabled
              badge="soon"
            />
          </div>

          {/* DATA OUTPUTS */}
          <div>
            <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-wider text-[#5A8A72]">
              Data Outputs
            </p>

            <NavButton
              active={activeView === "submissions"}
              onClick={() => setActiveView("submissions")}
              icon={<Inbox size={18} />}
              label="Submissions"
            />

            <NavButton
              active={activeView === "matches"}
              onClick={() => setActiveView("matches")}
              icon={<GitCompareArrows size={18} />}
              label="Budget Matches"
            />

            <NavButton
              active={activeView === "analytics"}
              onClick={() => setActiveView("analytics")}
              icon={<BarChart3 size={18} />}
              label="Analytics"
              badge="beta"
            />
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 shrink-0 border-t border-[#13402A]">
          <div className="text-[11px] text-[#82A895] leading-relaxed">
            County: Nairobi · FY 2025/26
            <br />
            <span className="text-[#5A8A72]">API: localhost:8000</span>
          </div>
        </div>
      </aside>

      {/* Main */}
      <div className="flex flex-col flex-grow h-full overflow-hidden bg-[#FAFAFA]">
        <header className="flex h-14 items-center gap-3 border-b border-gray-200 bg-white px-6 shrink-0">
          <span className="text-sm font-medium text-gray-600">
            Government Budget Accountability Dashboard
          </span>
          <span className="ml-auto text-xs text-gray-400">
            {activeView === "input" && "Citizen Input Simulation"}
            {activeView === "upload" && "Budget Document Ingestion"}
            {activeView === "documents" && "All Budget Documents"}
            {activeView === "submissions" && "All Submissions"}
            {activeView === "matches" && "Budget Match Results"}
            {activeView === "analytics" && "CSO Analytics Dashboard"}
          </span>
        </header>

        <main className="flex-grow overflow-y-auto">{renderView()}</main>
      </div>
    </div>
  );
}

/* ─── Reusable Nav Button ─── */
function NavButton({ active, onClick, icon, label, disabled = false, badge = null }) {
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
      <span className="flex-1 text-left">{label}</span>
      {badge && (
        <span className="text-[10px] font-medium bg-[#14A562]/20 text-[#14A562] px-1.5 py-0.5 rounded">
          {badge}
        </span>
      )}
    </button>
  );
}

/* ─── Placeholder ─── */
function AnalyticsPlaceholder() {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-slate-400">
      <BarChart3 className="h-12 w-12 mb-3 opacity-50" />
      <p className="text-sm font-medium">Analytics Dashboard</p>
      <p className="text-xs mt-1">Coming soon</p>
    </div>
  );
}

export default App;