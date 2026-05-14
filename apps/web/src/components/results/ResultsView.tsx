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
        <p className="text-xs uppercase tracking-[0.2em] text-brand">Summary</p>
        <p className="mt-2 text-sm leading-relaxed text-fg sm:text-base">{result.summary}</p>
        <dl className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat label="Points" value={totals.points.toString()} />
          <Stat label="Cited sources" value={totals.sources.toString()} />
          <Stat label="Grounded" value={`${totals.grounded}/${totals.points}`} />
          <Stat
            label="Duration"
            value={result.duration_seconds ? `${Math.round(result.duration_seconds)}s` : "—"}
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
