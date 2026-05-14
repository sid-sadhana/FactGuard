"use client";

import { useEffect, useRef } from "react";
import { gsap } from "gsap";
import {
  Film,
  ScrollText,
  Scissors,
  ListChecks,
  Search,
  Sparkles,
} from "lucide-react";

const STEPS = [
  {
    icon: Film,
    title: "Ingest",
    body: "Paste a YouTube URL or upload a clip. yt-dlp pulls a 720p source; uploads stream to disk with a size guard.",
  },
  {
    icon: ScrollText,
    title: "Transcript",
    body: "YouTube captions first; faster-whisper transcribes the audio when captions are missing. Output is one timed transcript.",
  },
  {
    icon: Scissors,
    title: "Sentence split",
    body: "The transcript is broken into ~25-word utterances — sentence punctuation when present, hard word-window otherwise so unpunctuated auto-captions don't collapse into one blob.",
  },
  {
    icon: ListChecks,
    title: "Atomic claims",
    body: "Ollama gemma4:e4b walks every utterance and emits a self-contained checkworthy point. Pronouns are resolved to their named antecedents so each claim stands alone.",
  },
  {
    icon: Search,
    title: "Cited evidence",
    body: "DuckDuckGo web search per claim. Pages are fetched, chunked, and reranked by Qdrant Cloud Inference — embeddings run server-side, no local embed model.",
  },
  {
    icon: Sparkles,
    title: "Synthesize · score",
    body: "gemma4:e4b writes a cited answer per claim, then a single overall synthesis pools all citations into one global list with inline [N] markers linking back to the sources. Ragas (optional) scores faithfulness and retrieval precision.",
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
            Six stages, every point grounded on the live web.
          </h2>
          <p className="mt-3 text-fg-muted">
            Every checkworthy sentence in the transcript is fact-checked
            independently, then synthesized into a single cited answer.
            gemma4:e4b runs locally; embeddings run server-side on Qdrant
            Cloud Inference. No source, no answer.
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
