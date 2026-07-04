import { useState } from "react";
import { 
  ShieldCheck, 
  MessageSquarePlus, 
  Inbox, 
  GitCompareArrows,
  PanelLeft
} from "lucide-react";

import Input from "./pages/Input";
import Matches from "./pages/Matches";
import Submissions from "./pages/Submissions";

function App() {
  const [activeView, setActiveView] = useState('input');

  const renderView = () => {
    switch (activeView) {
      case 'input':
        return <Input />;
      case 'matches':
        return <Matches />;
      case 'submissions':
        return <Submissions />;
      default:
        return <Input />;
    }
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-white">

      {/* Sidebar - Deep Green Theme */}
      <aside className="w-64 h-full flex flex-col flex-shrink-0 bg-[#0B3523] text-white">
        
        {/* Brand Header */}
        <div className="flex items-center gap-3 px-6 py-6">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#14A562]">
            <ShieldCheck size={20} className="text-white" />
          </div>
          <div>
            <h1 className="text-base font-semibold leading-none tracking-tight">Sauti Tracker</h1>
            <p className="text-xs text-[#82A895] mt-1.5">Budget accountability</p>
          </div>
        </div>

        {/* Navigation Section */}
        <div className="space-y-1 flex-1 overflow-y-auto px-3 mt-4">
          <br className="text-gray-500 w-90" />
          {/* <p className="mb-2 px-3 text-xs font-medium text-[#82A895]">Navigation</p> */}

          <button
            onClick={() => setActiveView('input')}
            className={`cursor-pointer w-full flex items-center gap-3 px-3 py-2 rounded-md transition-colors text-sm font-medium ${
              activeView === 'input' 
                ? 'bg-[#1A4B35] text-white' 
                : 'text-[#E2E8F0] hover:bg-[#13402A]'
            }`}
          >
            <MessageSquarePlus size={18} />
            Simulate Input
          </button>

          <button
            onClick={() => setActiveView('submissions')}
            className={`cursor-pointer w-full flex items-center gap-3 px-3 py-2 rounded-md transition-colors text-sm font-medium ${
              activeView === 'submissions' 
                ? 'bg-[#1A4B35] text-white' 
                : 'text-[#E2E8F0] hover:bg-[#13402A]'
            }`}
          >
            <Inbox size={18} />
            Submissions
          </button>

          <button
            onClick={() => setActiveView('matches')}
            className={`cursor-pointer w-full flex items-center gap-3 px-3 py-2 rounded-md transition-colors text-sm font-medium ${
              activeView === 'matches' 
                ? 'bg-[#1A4B35] text-white' 
                : 'text-[#E2E8F0] hover:bg-[#13402A]'
            }`}
          >
            <GitCompareArrows size={18} />
            Budget Matches
          </button>
        </div>

        {/* Sidebar Footer */}
        <div className="p-6 mt-auto shrink-0 border-t border-[#13402A]">
          <div className="text-xs text-[#82A895]">
            County: Nairobi · FY 2025/26
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex flex-col flex-grow h-full overflow-hidden bg-[#FAFAFA]">
        
        {/* Top Header Bar */}
        <header className="flex h-14 items-center gap-3 border-b border-gray-200 bg-white px-6 shrink-0">
          {/* <button className="text-gray-500 hover:text-gray-700 transition-colors">
            <PanelLeft size={20} strokeWidth={1.5} />
          </button> */}
          <span className="text-sm font-medium text-gray-600">
            Government Budget Accountability Dashboard
          </span>
        </header>

        {/* Dynamic Page Content */}
        <main className="flex-grow overflow-y-auto p-4">
          {renderView()}
        </main>
      </div>

    </div>
  );
}

export default App;