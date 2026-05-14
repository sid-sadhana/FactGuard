"use client";

import Link from "next/link";
import { ShieldCheck } from "lucide-react";

export function Header() {
  return (
    <header className="sticky top-0 z-30 border-b border-border/60 bg-bg/70 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight">
          <ShieldCheck className="h-5 w-5 text-brand" />
          <span>
            Fact<span className="text-brand">Guard</span>
          </span>
        </Link>
        <nav className="flex items-center gap-1 text-sm">
          <Link
            href="/analyze"
            className="rounded-lg px-3 py-1.5 text-fg-muted transition-colors hover:bg-bg-overlay hover:text-fg"
          >
            Analyze
          </Link>
          <Link
            href="/#how-it-works"
            className="hidden rounded-lg px-3 py-1.5 text-fg-muted transition-colors hover:bg-bg-overlay hover:text-fg sm:block"
          >
            How it works
          </Link>
          <a
            href="https://ollama.com/library/qwen3-vl"
            target="_blank"
            rel="noreferrer"
            className="hidden rounded-lg px-3 py-1.5 text-fg-muted transition-colors hover:bg-bg-overlay hover:text-fg md:block"
          >
            Model
          </a>
        </nav>
      </div>
    </header>
  );
}
