/** Domain + favicon helpers for Perplexity-style source chips. */

export function domainOf(url: string): string {
  try {
    const u = new URL(url);
    return u.hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

export function faviconOf(url: string, size = 64): string {
  const d = domainOf(url);
  return `https://www.google.com/s2/favicons?domain=${encodeURIComponent(d)}&sz=${size}`;
}

/** Split reasoning text on `[N]` markers so we can render each marker as a chip. */
export type ReasoningChunk =
  | { kind: "text"; value: string }
  | { kind: "cite"; index: number };

export function parseReasoning(text: string): ReasoningChunk[] {
  const out: ReasoningChunk[] = [];
  const re = /\[(\d+)\]/g;
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) {
      out.push({ kind: "text", value: text.slice(last, m.index) });
    }
    out.push({ kind: "cite", index: Number(m[1]) });
    last = m.index + m[0].length;
  }
  if (last < text.length) out.push({ kind: "text", value: text.slice(last) });
  return out;
}
