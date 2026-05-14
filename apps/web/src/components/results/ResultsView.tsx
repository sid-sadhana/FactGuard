"use client";

import { useMemo, useState } from "react";

import { cn } from "@/lib/cn";
import { ClaimList } from "@/components/results/ClaimList";
import type { Job } from "@/types/api";

type Tab = "answers" | "transcript";

export function ResultsView({ job }: { job: Job }) {
  const result = job.result;
  const [tab, setTab] = useState<Tab>("answers");

  const totals = useMemo(() => {
    const points = result?.verifications.length ?? 0;
    const sources = (result?.verifications ?? []).reduce(
      (acc, v) => acc + v.citations.length,
      0,
    );
    const grounded = (result?.verifications ?? []).filter((v) => v.citations.length > 0).length;
    return { points, sources, grounded };
  }, [result]);

  if (!result) return null;

  return (
    <section className="mt-8 animate-fade-in">
      <div className="rounded-2xl border border-border bg-bg-raised/70 p-5 sm:p-6">
        <p className="text-xs uppercase tracking-[0.2em] text-brand">Overall fact-check</p>
        <p className="mt-2 text-sm leading-relaxed text-fg sm:text-base">
          {renderSummary(result.summary, result.summary_citations ?? [])}
        </p>
        {result.summary_citations && result.summary_citations.length > 0 && (
          <ol className="mt-4 space-y-1 text-xs text-fg-muted">
            {result.summary_citations.map((c, i) => (
              <li key={`${i}-${c.url}`}>
                <span className="mr-1 font-mono text-fg-subtle">[{i}]</span>
                <a
                  href={c.url}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="text-brand hover:underline"
                >
                  {c.title || c.url}
                </a>
              </li>
            ))}
          </ol>
        )}
        <dl className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat label="Points" value={totals.points.toString()} />
          <Stat label="Cited sources" value={totals.sources.toString()} />
          <Stat label="Grounded" value={`${totals.grounded}/${totals.points}`} />
          <Stat
            label="Duration"
            value={formatDuration(result.duration_seconds)}
          />
        </dl>
      </div>

      <div role="tablist" className="mt-6 inline-flex w-full max-w-xs gap-1 rounded-xl bg-bg-overlay p-1 text-sm">
        <TabBtn active={tab === "answers"} onClick={() => setTab("answers")}>
          Answers · {totals.points}
        </TabBtn>
        <TabBtn active={tab === "transcript"} onClick={() => setTab("transcript")}>
          Transcript
        </TabBtn>
      </div>

      <div className="mt-4">
        {tab === "answers" && <ClaimList items={result.verifications} />}
        {tab === "transcript" && (
          <pre className="scrollbar-thin max-h-[60vh] overflow-auto whitespace-pre-wrap rounded-xl border border-border bg-bg-raised/70 p-4 text-sm leading-relaxed text-fg-muted sm:p-6">
            {result.transcript || "No transcript was extracted."}
          </pre>
        )}
      </div>
    </section>
  );
}

function TabBtn({
  active,
  children,
  onClick,
}: {
  active: boolean;
  children: React.ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={cn(
        "flex-1 rounded-lg px-3 py-1.5 text-center transition-all",
        active ? "bg-bg-raised text-fg shadow-sm" : "text-fg-muted hover:text-fg",
      )}
    >
      {children}
    </button>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border/60 bg-bg-overlay/40 px-3 py-2.5">
      <dt className="text-[10px] uppercase tracking-wide text-fg-subtle">{label}</dt>
      <dd className="mt-0.5 truncate text-lg font-semibold tabular-nums text-fg">{value}</dd>
    </div>
  );
}

function renderSummary(summary: string, citations: { url: string; title: string }[]): React.ReactNode {
  if (!summary) return "No overall summary was produced.";
  const parts = summary.split(/(\[\d+\])/g);
  return parts.map((part, i) => {
    const m = part.match(/^\[(\d+)\]$/);
    if (!m) return <span key={i}>{part}</span>;
    const idx = parseInt(m[1], 10);
    const c = citations[idx];
    if (!c) return <span key={i}>{part}</span>;
    return (
      <a
        key={i}
        href={c.url}
        target="_blank"
        rel="noreferrer noopener"
        title={c.title || c.url}
        className="mx-0.5 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-brand/15 px-1.5 align-middle font-mono text-[10px] font-semibold text-brand hover:bg-brand/25"
      >
        {idx}
      </a>
    );
  });
}

function formatDuration(seconds: number | null): string {
  if (!seconds || seconds <= 0) return "—";
  const total = Math.round(seconds);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  return `${m}:${String(s).padStart(2, "0")}`;
}
