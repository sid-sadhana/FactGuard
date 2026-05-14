import { cn } from "@/lib/cn";
import type { Verdict } from "@/types/api";

const styles: Record<Verdict, string> = {
  supported: "bg-verdict-supported/15 text-verdict-supported ring-verdict-supported/30",
  refuted: "bg-verdict-refuted/15 text-verdict-refuted ring-verdict-refuted/30",
  unverifiable: "bg-verdict-unverifiable/15 text-verdict-unverifiable ring-verdict-unverifiable/30",
};

const labels: Record<Verdict, string> = {
  supported: "Supported",
  refuted: "Refuted",
  unverifiable: "Unverifiable",
};

export function VerdictBadge({ verdict, className }: { verdict: Verdict; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset",
        styles[verdict],
        className,
      )}
    >
      {labels[verdict]}
    </span>
  );
}

export function Pill({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full bg-bg-overlay px-2.5 py-0.5 text-[10px] uppercase tracking-wide text-fg-muted",
        className,
      )}
    >
      {children}
    </span>
  );
}
