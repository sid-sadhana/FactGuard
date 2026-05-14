"use client";

import { useEffect, useRef } from "react";
import { gsap } from "gsap";

import type { RagasScores } from "@/types/api";

const METRICS: { key: keyof RagasScores; label: string; hint: string }[] = [
  { key: "faithfulness", label: "Faithfulness", hint: "Answers backed by retrieved context" },
  { key: "answer_relevancy", label: "Answer relevancy", hint: "Answer addresses the claim" },
  { key: "context_precision", label: "Context precision", hint: "Retrieved context is on-topic" },
  { key: "context_recall", label: "Context recall", hint: "Retrieval covers what the claim needs" },
];

export function RagasPanel({ ragas }: { ragas: RagasScores | null }) {
  const root = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!root.current || !ragas) return;
    const ctx = gsap.context(() => {
      gsap.utils.toArray<HTMLElement>("[data-bar]").forEach((bar) => {
        const target = Number(bar.dataset.value) || 0;
        gsap.fromTo(bar, { width: 0 }, { width: `${target}%`, duration: 1.1, ease: "expo.out" });
      });
    }, root);
    return () => ctx.revert();
  }, [ragas]);

  if (!ragas) {
    return (
      <p className="rounded-lg border border-dashed border-border px-4 py-6 text-center text-sm text-fg-muted">
        Ragas eval was not run for this job.
      </p>
    );
  }

  return (
    <div ref={root} className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      {METRICS.map((m) => {
        const v = ragas[m.key];
        const pct = v == null ? null : Math.round(v * 100);
        return (
          <div key={m.key} className="rounded-xl border border-border bg-bg-raised/70 p-4">
            <div className="flex items-baseline justify-between gap-2">
              <p className="text-sm font-medium">{m.label}</p>
              <p className="text-xl font-semibold tabular-nums text-brand">
                {pct == null ? "—" : `${pct}`}
                {pct != null && <span className="ml-0.5 text-xs text-fg-subtle">%</span>}
              </p>
            </div>
            <p className="mt-0.5 text-xs text-fg-subtle">{m.hint}</p>
            <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-bg-overlay">
              <div
                data-bar
                data-value={pct ?? 0}
                className="h-full rounded-full bg-gradient-to-r from-brand/70 via-brand to-brand-strong"
                style={{ width: 0 }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
