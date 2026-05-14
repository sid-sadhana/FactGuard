"use client";

import { useEffect, useRef } from "react";
import { gsap } from "gsap";
import {
  Film,
  Image as ImageIcon,
  ListChecks,
  Search,
  ScrollText,
  Gauge,
} from "lucide-react";

const STEPS = [
  {
    icon: Film,
    title: "Ingest",
    body: "Paste a YouTube URL or upload a clip. yt-dlp pulls a 720p source; uploads stream to disk with a size guard.",
  },
  {
    icon: ImageIcon,
    title: "Keyframe vision",
    body: "ffmpeg samples keyframes at a uniform interval. Each frame is described by Ollama qwen3-vl in 1–3 grounded sentences.",
  },
  {
    icon: ScrollText,
    title: "Transcript",
    body: "Captions API first; faster-whisper fallback on the audio track. Output is fused with frame text for the next step.",
  },
  {
    icon: ListChecks,
    title: "Atomic claims",
    body: "An LLM atomizes the fused signal into single-sentence factual claims. Opinions, jokes, and self-references are filtered.",
  },
  {
    icon: Search,
    title: "Cited evidence",
    body: "Tavily web search per claim. Chunked, embedded, reranked, and packed into a per-claim context budget — no source dominates.",
  },
  {
    icon: Gauge,
    title: "Verify · evaluate · score",
    body: "JSON-mode verdicts cite specific evidence indices. Ragas (faithfulness, context precision/recall) checks the retrieval. A blended score is produced.",
  },
];

export function HowItWorks() {
  const root = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!root.current) return;
    let ctx: gsap.Context | undefined;
    let cleanup: (() => void) | undefined;

    (async () => {
      const { ScrollTrigger } = await import("gsap/ScrollTrigger");
      gsap.registerPlugin(ScrollTrigger);

      ctx = gsap.context(() => {
        const cards = gsap.utils.toArray<HTMLElement>("[data-step]");
        cards.forEach((card, i) => {
          gsap.fromTo(
            card,
            { y: 36, opacity: 0 },
            {
              y: 0,
              opacity: 1,
              duration: 0.7,
              ease: "expo.out",
              delay: i * 0.04,
              scrollTrigger: { trigger: card, start: "top 88%" },
            },
          );
        });
      }, root);

      ScrollTrigger.refresh();
      cleanup = () => ScrollTrigger.getAll().forEach((t) => t.kill());
    })();

    return () => {
      cleanup?.();
      ctx?.revert();
    };
  }, []);

  return (
    <section id="how-it-works" ref={root} className="border-t border-border/50 py-20 sm:py-28">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
        <div className="max-w-2xl">
          <p className="text-xs uppercase tracking-[0.2em] text-brand">Pipeline</p>
          <h2 className="mt-2 text-balance text-3xl font-semibold tracking-tight sm:text-4xl">
            Six stages, all grounded in evidence.
          </h2>
          <p className="mt-3 text-fg-muted">
            Every claim that gets a verdict is tied to specific URLs from the
            retrieved corpus. No source, no verdict.
          </p>
        </div>

        <div className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {STEPS.map((s, i) => (
            <div
              key={s.title}
              data-step
              className="group relative overflow-hidden rounded-2xl border border-border bg-bg-raised/70 p-5 transition-all hover:-translate-y-1 hover:border-brand/40 hover:shadow-glow"
            >
              <div className="flex items-center gap-3">
                <span className="grid h-9 w-9 place-items-center rounded-lg bg-brand/10 text-brand">
                  <s.icon className="h-4 w-4" />
                </span>
                <span className="text-xs text-fg-subtle">Step {i + 1}</span>
              </div>
              <h3 className="mt-4 text-lg font-medium">{s.title}</h3>
              <p className="mt-2 text-sm text-fg-muted">{s.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
