"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";
import { gsap } from "gsap";
import { ArrowRight, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/Button";

export function Hero() {
  const root = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const ctx = gsap.context(() => {
      gsap.from("[data-anim='hero-eyebrow']", { y: 16, opacity: 0, duration: 0.8, ease: "expo.out" });
      gsap.from("[data-anim='hero-title'] > span", {
        y: 28, opacity: 0, duration: 1, stagger: 0.06, ease: "expo.out", delay: 0.05,
      });
      gsap.from("[data-anim='hero-sub']", { y: 18, opacity: 0, duration: 0.9, ease: "expo.out", delay: 0.35 });
      gsap.from("[data-anim='hero-cta']", { y: 18, opacity: 0, duration: 0.9, ease: "expo.out", delay: 0.5 });
      gsap.from("[data-anim='hero-orb']", { scale: 0.7, opacity: 0, duration: 1.4, stagger: 0.18, ease: "expo.out" });
    }, root);

    const onMove = (e: PointerEvent) => {
      const rect = root.current?.getBoundingClientRect();
      if (!rect) return;
      const x = ((e.clientX - rect.left) / rect.width - 0.5) * 2;
      const y = ((e.clientY - rect.top) / rect.height - 0.5) * 2;
      gsap.to("[data-parallax='1']", { x: x * 18, y: y * 12, duration: 0.6, ease: "power3.out" });
      gsap.to("[data-parallax='2']", { x: x * -28, y: y * -20, duration: 0.7, ease: "power3.out" });
      gsap.to("[data-parallax='3']", { x: x * 8, y: y * 6, duration: 0.7, ease: "power3.out" });
      root.current?.style.setProperty("--mx", `${50 + x * 30}%`);
      root.current?.style.setProperty("--my", `${50 + y * 30}%`);
    };
    window.addEventListener("pointermove", onMove);
    return () => {
      window.removeEventListener("pointermove", onMove);
      ctx.revert();
    };
  }, []);

  const title = "Verify what videos claim.";

  return (
    <section
      ref={root}
      className="relative isolate overflow-hidden bg-glow"
    >
      <div data-parallax="1" className="bg-grid absolute inset-0 -z-10 opacity-60" />
      <div
        data-parallax="2"
        data-anim="hero-orb"
        className="pointer-events-none absolute -left-24 top-10 -z-10 h-72 w-72 rounded-full bg-brand/15 blur-3xl sm:h-96 sm:w-96"
      />
      <div
        data-parallax="3"
        data-anim="hero-orb"
        className="pointer-events-none absolute -right-24 top-32 -z-10 h-80 w-80 rounded-full bg-indigo-500/10 blur-3xl sm:h-[26rem] sm:w-[26rem]"
      />

      <div className="mx-auto max-w-6xl px-4 pb-24 pt-16 sm:px-6 sm:pt-24 lg:px-8 lg:pt-28">
        <div
          data-anim="hero-eyebrow"
          className="mx-auto inline-flex items-center gap-2 rounded-full border border-border bg-bg-raised/70 px-3 py-1 text-xs text-fg-muted backdrop-blur"
        >
          <Sparkles className="h-3.5 w-3.5 text-brand" />
          Vision-language fact checking · qwen3-vl + Tavily + Ragas
        </div>

        <h1
          data-anim="hero-title"
          className="mt-6 text-balance text-center text-4xl font-semibold leading-[1.05] tracking-tight sm:text-5xl md:text-6xl lg:text-7xl"
        >
          {title.split(" ").map((word, i) => (
            <span key={i} className="mr-3 inline-block">
              {word === "claim." ? (
                <span className="text-brand">{word}</span>
              ) : (
                word
              )}
            </span>
          ))}
        </h1>

        <p
          data-anim="hero-sub"
          className="mx-auto mt-6 max-w-2xl text-balance text-center text-base text-fg-muted sm:text-lg"
        >
          Drop a YouTube link or upload a clip. FactGuard extracts atomic claims
          from frames and transcript, retrieves cited web evidence, and scores
          factual accuracy with a Ragas-evaluated RAG pipeline.
        </p>

        <div
          data-anim="hero-cta"
          className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row"
        >
          <Link href="/analyze" className="w-full sm:w-auto">
            <Button size="lg" className="w-full sm:w-auto">
              Analyze a video
              <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
          <Link href="/#how-it-works" className="w-full sm:w-auto">
            <Button variant="outline" size="lg" className="w-full sm:w-auto">
              See how it works
            </Button>
          </Link>
        </div>
      </div>
    </section>
  );
}
