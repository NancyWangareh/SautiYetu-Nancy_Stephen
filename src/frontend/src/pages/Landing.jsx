import { useState, useEffect } from "react";
import {
  ShieldCheck,
  FileUp,
  Users,
  Search,
  CheckCircle2,
  XCircle,
  BarChart3,
  ArrowRight,
  Landmark,
  FileText,
  MessageSquare,
} from "lucide-react";

const EXAMPLES = [
  {
    status: "present",
    text: "Construction of Embakasi Traders market at Riverbank.",
    detail: "Matched: county market infrastructure",
  },
  {
    status: "absent",
    text: "Millennium and Karong'a roads in Mountain View Ward.",
    detail: "No matching budget line found",
  },
  {
    status: "present",
    text: "Completion of an ECD centre.",
    detail: "Matched: early childhood development facilities",
  },
  {
    status: "absent",
    text: "Installation of streetlights and masts in Dagoretti North.",
    detail: "No matching budget line found",
  },
  {
    status: "present",
    text: "Construction of a borehole.",
    detail: "Matched: water supply infrastructure",
  },
  {
    status: "absent",
    text: "Construction of sewer lines.",
    detail: "No matching budget line found",
  },
];

function MatchCarousel() {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => setIndex((i) => (i + 1) % EXAMPLES.length), 2800);
    return () => clearInterval(timer);
  }, []);

  const ex = EXAMPLES[index];
  const present = ex.status === "present";

  return (
    <div className="flex flex-col gap-4">
      <div
        key={index}
        className="animate-fade-in-up flex min-h-[210px] flex-col justify-center rounded-xl border border-[#2B5A40] bg-[#0F3D28] p-6 shadow-lg"
      >
        <p className="text-xs font-medium uppercase tracking-wide text-[#82A895]">
          Citizen concern · {index + 1} of {EXAMPLES.length}
        </p>
        <p className="mt-2 text-base leading-relaxed text-white">&ldquo;{ex.text}&rdquo;</p>
        <div className="mt-4 flex items-center gap-2">
          {present ? (
            <>
              <CheckCircle2 className="h-5 w-5 text-emerald-400" />
              <span className="text-sm font-semibold text-emerald-300">Present in budget</span>
            </>
          ) : (
            <>
              <XCircle className="h-5 w-5 text-red-400" />
              <span className="text-sm font-semibold text-red-300">Absent from budget</span>
            </>
          )}
        </div>
        <p className={`mt-1.5 text-xs ${present ? "text-[#9FD5B4]" : "text-[#E4B7B7]"}`}>
          {ex.detail}
        </p>
      </div>
      <div className="flex justify-center gap-2">
        {EXAMPLES.map((e, i) => (
          <button
            key={i}
            onClick={() => setIndex(i)}
            aria-label={`Example ${i + 1}`}
            className={`h-1.5 rounded-full transition-all ${
              i === index ? "w-6 bg-[#14A562]" : "w-1.5 bg-[#2B5A40]"
            }`}
          />
        ))}
      </div>
    </div>
  );
}

function Landing({ onLaunch }) {
  return (
    <div className="min-h-screen bg-white text-slate-800">
      {/* ── Nav ── */}
      <header className="sticky top-0 z-50 border-b border-[#13402A] bg-[#0B3523] text-white">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#14A562]">
              <ShieldCheck size={20} />
            </div>
            <div>
              <p className="text-base font-semibold leading-none tracking-tight">SAUTI YETU</p>
              <p className="mt-1 text-[11px] text-[#82A895]">Citizen budget accountability</p>
            </div>
          </div>
          <button
            onClick={onLaunch}
            className="inline-flex items-center gap-2 rounded-lg bg-[#14A562] px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-[#12b96e]"
          >
            Launch Dashboard
            <ArrowRight size={16} />
          </button>
        </div>
      </header>

      {/* ── Hero ── */}
      <section className="border-b border-[#13402A] bg-[#0B3523] text-white">
        <div className="mx-auto grid max-w-6xl gap-12 px-4 py-20 sm:px-6 lg:grid-cols-2 lg:items-center">
          <div>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-[#2B5A40] bg-[#13402A] px-3 py-1 text-xs font-medium text-[#9FD5B4]">
              <Landmark size={14} />
              For Kenyan County CSOs
            </span>
            <h1 className="mt-5 text-4xl font-bold leading-tight tracking-tight sm:text-5xl">
              Did the enacted budget actually fund what citizens asked for?
            </h1>
            <p className="mt-5 max-w-xl text-lg text-[#C6DACF]">
              SautiYetu connects public participation to the enacted county budget — so
              civil society can see, in seconds, which citizen concerns made it into the
              money, and which ones didn't.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <button
                onClick={onLaunch}
                className="inline-flex items-center gap-2 rounded-lg bg-[#14A562] px-6 py-3 text-base font-semibold text-white transition-colors hover:bg-[#12b96e]"
              >
                Open the CSO Dashboard
                <ArrowRight size={18} />
              </button>
              <a
                href="#how-it-works"
                className="inline-flex items-center gap-2 rounded-lg border border-[#2B5A40] px-6 py-3 text-base font-medium text-[#E2E8F0] transition-colors hover:bg-[#13402A]"
              >
                See how it works
              </a>
            </div>
          </div>

          {/* Rotating example matches */}
          <MatchCarousel />
        </div>
      </section>

      {/* ── Problem ── */}
      <section className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight">The problem today</h2>
          <p className="mt-4 text-slate-500">
            Citizens speak at public participation. But between the minutes and the final
            budget, the thread gets lost.
          </p>
        </div>
        <div className="mx-auto mt-12 grid max-w-4xl gap-6 md:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <FileText className="h-8 w-8 text-emerald-600" />
            <h3 className="mt-4 text-lg font-semibold">500-page PDFs</h3>
            <p className="mt-2 text-sm text-slate-500">
              County budgets are huge, jargon-heavy documents. Finding one line item by
              hand is a full-time job.
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <MessageSquare className="h-8 w-8 text-emerald-600" />
            <h3 className="mt-4 text-lg font-semibold">Unstructured minutes</h3>
            <p className="mt-2 text-sm text-slate-500">
              Public participation reports are long, messy and full of repeated asks. No
              one can quickly tell what was actually heard.
            </p>
          </div>
        </div>
      </section>

      {/* ── How it works ── */}
      <section id="how-it-works" className="bg-slate-50 py-20">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight">How it works</h2>
            <p className="mt-4 text-slate-500">
              Three steps from raw documents to an accountability report.
            </p>
          </div>
          <div className="mt-12 grid gap-6 md:grid-cols-3">
            <div className="relative rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <span className="absolute -top-4 left-6 flex h-8 w-8 items-center justify-center rounded-full bg-[#0B3523] text-sm font-bold text-white">
                1
              </span>
              <FileUp className="mt-2 h-8 w-8 text-emerald-600" />
              <h3 className="mt-4 text-lg font-semibold">Upload the enacted budget</h3>
              <p className="mt-2 text-sm text-slate-500">
                SautiYetu parses the PDF into structured line items — project, location,
                amount — and indexes them for semantic search.
              </p>
            </div>
            <div className="relative rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <span className="absolute -top-4 left-6 flex h-8 w-8 items-center justify-center rounded-full bg-[#0B3523] text-sm font-bold text-white">
                2
              </span>
              <Users className="mt-2 h-8 w-8 text-emerald-600" />
              <h3 className="mt-4 text-lg font-semibold">Upload public participation</h3>
              <p className="mt-2 text-sm text-slate-500">
                Citizen concerns are extracted and classified by sector and location,
                ready to be matched.
              </p>
            </div>
            <div className="relative rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <span className="absolute -top-4 left-6 flex h-8 w-8 items-center justify-center rounded-full bg-[#0B3523] text-sm font-bold text-white">
                3
              </span>
              <Search className="mt-2 h-8 w-8 text-emerald-600" />
              <h3 className="mt-4 text-lg font-semibold">Match &amp; report</h3>
              <p className="mt-2 text-sm text-slate-500">
                Every concern is marked{" "}
                <span className="font-semibold text-emerald-700">Present</span> or{" "}
                <span className="font-semibold text-red-600">Absent</span> in the budget,
                with a funding-gap report for advocacy.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ── Features ── */}
      <section className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight">Built for accountability</h2>
          <p className="mt-4 text-slate-500">
            Purpose-built tooling, not generic AI — tuned to how Kenyan county budgets and
            participation actually look.
          </p>
        </div>
        <div className="mt-12 grid gap-6 md:grid-cols-2">
          <div className="flex gap-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <Search className="h-8 w-8 shrink-0 text-emerald-600" />
            <div>
              <h3 className="text-lg font-semibold">Semantic budget search</h3>
              <p className="mt-2 text-sm text-slate-500">
                Search by meaning, not keywords. Ask for "boreholes" and find "water
                infrastructure" across 500 pages in seconds.
              </p>
            </div>
          </div>
          <div className="flex gap-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <CheckCircle2 className="h-8 w-8 shrink-0 text-emerald-600" />
            <div>
              <h3 className="text-lg font-semibold">Location-aware matching</h3>
              <p className="mt-2 text-sm text-slate-500">
                Matches each concern to the right project <em>and</em> the right ward or
                sub-county — so a Water project in Westlands isn't credited to a complaint
                in Mathare.
              </p>
            </div>
          </div>
          <div className="flex gap-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <BarChart3 className="h-8 w-8 shrink-0 text-emerald-600" />
            <div>
              <h3 className="text-lg font-semibold">Funding-gap reports</h3>
              <p className="mt-2 text-sm text-slate-500">
                Aggregate everything into a CSO-ready report: addressed vs. unaddressed,
                broken down by sector and ward. Exportable to CSV.
              </p>
            </div>
          </div>
          <div className="flex gap-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <FileText className="h-8 w-8 shrink-0 text-emerald-600" />
            <div>
              <h3 className="text-lg font-semibold">Plain-language explanations</h3>
              <p className="mt-2 text-sm text-slate-500">
                Government jargon is translated into plain language, so any citizen or CSO
                can understand what a budget line actually pays for.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ── Final CTA ── */}
      <section className="bg-[#0B3523] py-20 text-white">
        <div className="mx-auto max-w-3xl px-4 text-center sm:px-6">
          <h2 className="text-3xl font-bold tracking-tight">
            Turn citizen voices into budget evidence
          </h2>
          <p className="mt-4 text-[#C6DACF]">
            Upload a budget, upload a participation report, and see exactly what got funded.
          </p>
          <button
            onClick={onLaunch}
            className="mt-8 inline-flex items-center gap-2 rounded-lg bg-[#14A562] px-8 py-3.5 text-base font-semibold text-white transition-colors hover:bg-[#12b96e]"
          >
            Launch the CSO Dashboard
            <ArrowRight size={18} />
          </button>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="border-t border-[#13402A] bg-[#0B3523] py-8 text-center">
        <div className="mx-auto flex max-w-6xl flex-col items-center gap-2 px-4 sm:px-6">
          <div className="flex items-center gap-2">
            <ShieldCheck size={16} className="text-[#14A562]" />
            <span className="text-sm font-semibold tracking-tight text-white">SAUTI YETU</span>
          </div>
          <p className="text-xs text-[#82A895]">
            Citizen budget accountability for Kenyan counties.
          </p>
        </div>
      </footer>
    </div>
  );
}

export default Landing;
