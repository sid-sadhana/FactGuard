"use client";

import { useEffect, useRef } from "react";
import { gsap } from "gsap";
import { Check, CircleAlert, CircleDashed, Loader2 } from "lucide-react";

import { cn } from "@/lib/cn";
import { STAGE_LABEL, STAGE_ORDER, type JobStage } from "@/types/api";

interface Props {
  stage: JobStage;
  percent: number;
  message: string;
}

export function ProgressTimeline({ stage, percent, message }: Props) {
  const barRef = useRef<HTMLDivElement | null>(null);
  const pctRef = useRef<HTMLSpanElement | null>(null);
  const lastPct = useRef(0);

  useEffect(() => {
    if (!barRef.current) return;
    const target = Math.max(0, Math.min(100, percent));
    gsap.to(barRef.current, {
      width: `${target}%`,
      duration: 0.5,
      ease: "expo.out",
    });
    if (pctRef.current) {
      const obj = { v: lastPct.current };
      gsap.to(obj, {
        v: target,
        duration: 0.5,
        ease: "expo.out",
        onUpdate: () => {
          if (pctRef.current) pctRef.current.textContent = Math.round(obj.v).toString();
        },
      });
    }
    lastPct.current = target;
  }, [percent]);

  const failed = stage === "failed";
  const completedIdx =
    stage === "completed" ? STAGE_ORDER.length : STAGE_ORDER.indexOf(stage);

  return (
    <div className="rounded-2xl border border-border bg-bg-raised/70 p-4 sm:p-6">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-xs uppercase tracking-[0.2em] text-brand">
            {failed ? "Failed" : stage === "completed" ? "Done" : STAGE_LABEL[stage]}
          </p>
          <p
            key={message}
            className="mt-2 min-h-[1.75rem] truncate text-base font-medium text-fg sm:text-lg animate-fade-in"
          >
            {message || (stage === "completed" ? "Finished" : "Starting…")}
          </p>
        </div>
        <div className="shrink-0 text-right">
          <p className="text-3xl font-semibold leading-none tabular-nums">
            <span ref={pctRef}>0</span>
            <span className="ml-0.5 text-base text-fg-subtle">%</span>
          </p>
        </div>
      </div>

      <div className="relative mt-4 h-2 w-full overflow-hidden rounded-full bg-bg-overlay">
        <div
          ref={barRef}
          className={cn(
            "h-full rounded-full bg-gradient-to-r from-brand/80 via-brand to-brand-strong shadow-[0_0_12px_rgba(141,236,180,0.45)]",
            failed && "from-verdict-refuted via-verdict-refuted to-verdict-refuted shadow-none",
          )}
          style={{ width: "0%" }}
        />
        {!failed && stage !== "completed" && (
          <div className="pointer-events-none absolute inset-y-0 left-0 w-full">
            <div className="h-full w-1/3 -translate-x-full animate-[shimmer_1.6s_ease-in-out_infinite] bg-gradient-to-r from-transparent via-white/15 to-transparent" />
          </div>
        )}
      </div>

      <ol className="mt-5 grid gap-1.5 sm:grid-cols-2">
        {STAGE_ORDER.slice(0, -1).map((s, i) => {
          const done = i < completedIdx;
          const active = i === completedIdx && !failed;
          return (
            <li
              key={s}
              className={cn(
                "flex items-center gap-2 rounded-lg border border-transparent px-2 py-1.5 text-sm transition-colors",
                active && "border-brand/30 bg-brand/5",
              )}
            >
              <span
                className={cn(
                  "grid h-5 w-5 place-items-center rounded-full",
                  done && "bg-brand/15 text-brand",
                  active && "bg-brand/20 text-brand",
                  !done && !active && "bg-bg-overlay text-fg-subtle",
                )}
              >
                {failed && active ? (
                  <CircleAlert className="h-3.5 w-3.5 text-verdict-refuted" />
                ) : done ? (
                  <Check className="h-3 w-3" />
                ) : active ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : (
                  <CircleDashed className="h-3 w-3" />
                )}
              </span>
              <span
                className={cn(
                  "truncate",
                  done ? "text-fg" : active ? "text-fg" : "text-fg-muted",
                )}
              >
                {STAGE_LABEL[s]}
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
