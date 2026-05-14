"use client";

import { ExternalLink } from "lucide-react";

import { cn } from "@/lib/cn";
import { domainOf, faviconOf } from "@/lib/sources";

interface Props {
  index: number;
  url: string;
  title: string;
  className?: string;
  compact?: boolean;
}

export function SourceChip({ index, url, title, className, compact = false }: Props) {
  return (
    <a
      href={url}
      target="_blank"
      rel="noreferrer"
      className={cn(
        "group inline-flex items-center gap-2 rounded-lg border border-border bg-bg-overlay/70 px-2.5 py-1.5 text-xs transition-all hover:-translate-y-0.5 hover:border-brand/50 hover:bg-bg-overlay",
        compact ? "max-w-[180px]" : "max-w-[260px]",
        className,
      )}
      title={title || domainOf(url)}
    >
      <span className="grid h-4 w-4 shrink-0 place-items-center rounded-full bg-bg text-[10px] font-medium text-brand">
        {index}
      </span>
      <img
        src={faviconOf(url)}
        alt=""
        width={14}
        height={14}
        className="h-3.5 w-3.5 shrink-0 rounded-sm"
        loading="lazy"
      />
      <span className="truncate text-fg-muted group-hover:text-fg">
        {domainOf(url)}
      </span>
      <ExternalLink className="ml-auto h-3 w-3 shrink-0 text-fg-subtle opacity-0 transition-opacity group-hover:opacity-100" />
    </a>
  );
}

export function CitationMarker({
  index,
  url,
  onClick,
}: {
  index: number;
  url?: string;
  onClick?: () => void;
}) {
  const className =
    "mx-0.5 inline-flex h-[18px] min-w-[18px] -translate-y-[1px] items-center justify-center rounded-md bg-brand/15 px-1 text-[10px] font-medium text-brand align-middle transition-colors hover:bg-brand/25 hover:text-brand-strong";
  if (url) {
    return (
      <a href={url} target="_blank" rel="noreferrer" className={className}>
        {index}
      </a>
    );
  }
  return (
    <button onClick={onClick} className={className}>
      {index}
    </button>
  );
}
