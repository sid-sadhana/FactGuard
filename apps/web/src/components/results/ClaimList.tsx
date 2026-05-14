"use client";

import { useEffect, useRef, useState } from "react";
import { gsap } from "gsap";
import { Brain, ChevronDown, Globe, Quote } from "lucide-react";

import { cn } from "@/lib/cn";
import { domainOf, parseReasoning } from "@/lib/sources";
import type { ClaimVerification } from "@/types/api";

import { CitationMarker, SourceChip } from "./SourceChip";

export function ClaimList({ items }: { items: ClaimVerification[] }) {
  const root = useRef<HTMLUListElement | null>(null);

  useEffect(() => {
    if (!root.current) return;
    const ctx = gsap.context(() => {
      gsap.from("[data-claim-card]", {
        y: 18,
        opacity: 0,
        duration: 0.55,
        stagger: 0.06,
        ease: "expo.out",
      });
    }, root);
    return () => ctx.revert();
  }, []);

  if (!items.length) {
    return (
      <p className="rounded-lg border border-dashed border-border px-4 py-6 text-center text-sm text-fg-muted">
        No points were extracted from this video.
      </p>
    );
  }

  return (
    <ul ref={root} className="space-y-5">
      {items.map((v, i) => (
        <li key={v.claim.id} data-claim-card>
          <ClaimCard index={i + 1} v={v} />
        </li>
      ))}
    </ul>
  );
}

function ClaimCard({ index, v }: { index: number; v: ClaimVerification }) {
  const [showAllSources, setShowAllSources] = useState(false);
  const cites = v.citations;
  const visibleSources = showAllSources ? cites : cites.slice(0, 6);
  const chunks = parseReasoning(v.reasoning);
  const hasAnswer = v.reasoning && v.reasoning.trim().length > 0;

  return (
    <article className="overflow-hidden rounded-2xl border border-border bg-bg-raised/60 backdrop-blur transition-colors hover:border-border-muted">
      <header className="flex items-start gap-3 px-4 py-4 sm:px-6">
        <span className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-brand/10 text-xs font-semibold text-brand">
          {index}
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-balance text-base font-medium leading-snug text-fg sm:text-[17px]">
            {v.claim.text}
          </p>
          <span
            className={cn(
              "mt-2 inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[10px] uppercase tracking-[0.18em]",
              cites.length > 0
                ? "bg-brand/10 text-brand"
                : "bg-bg-overlay text-fg-subtle",
            )}
            title={
              cites.length > 0
                ? "Agent invoked web search and grounded the answer in sources."
                : "Agent answered from the model's own knowledge — no web search."
            }
          >
            {cites.length > 0 ? (
              <>
                <Globe className="h-3 w-3" /> Web-grounded
              </>
            ) : (
              <>
                <Brain className="h-3 w-3" /> Model knowledge
              </>
            )}
          </span>
        </div>
      </header>

      {cites.length > 0 && (
        <section className="border-t border-border/60 px-4 py-3 sm:px-6">
          <p className="mb-2 text-[10px] uppercase tracking-[0.2em] text-fg-subtle">
            Sources · {cites.length}
          </p>
          <div className="flex flex-wrap gap-2">
            {visibleSources.map((c, i) => (
              <SourceChip key={`${v.claim.id}-${i}`} index={i} url={c.url} title={c.title} />
            ))}
            {cites.length > 6 && !showAllSources && (
              <button
                onClick={() => setShowAllSources(true)}
                className="inline-flex items-center gap-1 rounded-lg border border-border bg-bg-overlay/40 px-2.5 py-1.5 text-xs text-fg-muted transition-colors hover:text-fg"
              >
                <ChevronDown className="h-3 w-3" />
                {cites.length - 6} more
              </button>
            )}
          </div>
        </section>
      )}

      <section className="border-t border-border/60 px-4 py-4 sm:px-6">
        <div className="mb-2 flex items-center gap-2 text-[10px] uppercase tracking-[0.2em] text-fg-subtle">
          <Quote className="h-3 w-3" />
          Answer
        </div>
        <p className="text-[15px] leading-relaxed text-fg sm:text-base">
          {!hasAnswer ? (
            <span className="text-fg-muted">No grounded answer produced.</span>
          ) : chunks.length === 0 ? (
            <span>{v.reasoning}</span>
          ) : (
            chunks.map((c, i) =>
              c.kind === "text" ? (
                <span key={i}>{c.value}</span>
              ) : (
                <CitationMarker
                  key={i}
                  index={c.index}
                  url={cites[c.index]?.url}
                />
              ),
            )
          )}
        </p>

        {cites.length > 0 && (
          <details className="group mt-4 rounded-lg border border-border/60 bg-bg-overlay/30 [&_summary::-webkit-details-marker]:hidden">
            <summary className="flex cursor-pointer list-none items-center justify-between gap-2 px-3 py-2 text-xs text-fg-muted hover:text-fg">
              <span>Show source snippets</span>
              <ChevronDown className="h-3.5 w-3.5 transition-transform group-open:rotate-180" />
            </summary>
            <ol className="space-y-2 px-3 pb-3">
              {cites.map((c, i) => (
                <li key={`${v.claim.id}-snip-${i}`} className="rounded-md border border-border/60 bg-bg-raised/40 p-2.5">
                  <a
                    href={c.url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 text-xs font-medium text-brand hover:underline"
                  >
                    <span className="grid h-4 w-4 place-items-center rounded-full bg-brand/15 text-[9px]">
                      {i}
                    </span>
                    <span className="truncate">{domainOf(c.url)} · {c.title}</span>
                  </a>
                  <p className={cn("mt-1.5 line-clamp-3 text-xs text-fg-muted")}>
                    {c.snippet}
                  </p>
                </li>
              ))}
            </ol>
          </details>
        )}
      </section>
    </article>
  );
}
