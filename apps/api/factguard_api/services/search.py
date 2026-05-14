"""Evidence retrieval.

Two steps so each does one job well:

  1. DuckDuckGo (via the `ddgs` lib) ranks the open web and returns top
     URLs + short snippets. Free, no API key. Optional proxy support via
     DDGS_PROXY env var for when DDG rate-limits.
  2. WebBaseLoader (langchain_community) fetches the full HTML of each URL
     and extracts text. Heavier, but gives the reranker real content to
     work with.

Both steps degrade gracefully:
  * If DDG fails / rate-limits → empty results, pipeline still completes.
  * If WebBaseLoader fails → fall back to DDG's own snippet for that URL.
  * Per-URL failures are logged and skipped (no whole-job aborts).

The pipeline calls `gather_evidence(queries)` which dedupes URL fetches
across all queries — so two claims sharing a hit only cost one HTTP load.
"""
from __future__ import annotations

import asyncio
import re
from typing import Awaitable, Callable, Iterable

from ..core.config import get_settings
from ..core.logging import get_logger

log = get_logger(__name__)

ProgressCB = Callable[[int, int, str], Awaitable[None]]


_STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "of", "in", "on", "at", "to", "for",
    "with", "by", "from", "as", "is", "was", "were", "be", "been", "being",
    "are", "this", "that", "these", "those", "it", "its", "his", "her", "their",
    "he", "she", "they", "them", "him", "we", "us", "you", "your", "i", "me",
    "my", "our", "ours", "so", "if", "then", "than", "also", "just", "very",
    "much", "many", "more", "most", "some", "any", "all", "no", "not", "only",
    "into", "out", "up", "down", "over", "under", "again", "further", "here",
    "there", "when", "where", "why", "how", "what", "which", "who", "whom",
    "whose", "because", "while", "do", "does", "did", "have", "has", "had",
    "will", "would", "should", "could", "may", "might", "can", "must",
})


def _compress_query(text: str, *, max_words: int = 10, max_chars: int = 90) -> str:
    """Squeeze a long claim sentence into a keyword-style search query.

    DDG/Brave/Yahoo time out on 30-word natural-language sentences; they
    expect 5-10 keywords. We strip punctuation + filler stopwords and cap
    at 10 content words / 90 chars. Capitalized tokens are kept verbatim
    (proper nouns) and pushed to the front so the search engine gets the
    most distinctive tokens first.
    """
    if not text:
        return ""
    cleaned = re.sub(r"[^\w\s$%.-]", " ", text)
    tokens = [t for t in cleaned.split() if t]
    if not tokens:
        return text[:max_chars]
    proper: list[str] = []
    other: list[str] = []
    for t in tokens:
        low = t.lower()
        if t[0].isupper() and len(t) > 1:
            proper.append(t)
        elif low in _STOPWORDS:
            continue
        elif any(ch.isdigit() for ch in t):
            proper.append(t)  # numbers / years / amounts → keep as proper
        else:
            other.append(t)
    ordered = proper + other
    out = " ".join(ordered[:max_words])
    if len(out) > max_chars:
        out = out[:max_chars].rsplit(" ", 1)[0]
    return out or text[:max_chars]


def _ddg_search_sync(query: str, max_results: int, proxy: str | None, region: str) -> list[dict]:
    """Blocking DDG call — wrapped in asyncio.to_thread by the async caller."""
    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS  # legacy name
        except ImportError:
            log.warning("Neither `ddgs` nor `duckduckgo_search` is installed")
            return []

    try:
        kwargs: dict = {}
        if proxy:
            kwargs["proxy"] = proxy
        with DDGS(**kwargs) as ddg:
            raw = list(ddg.text(query, region=region, max_results=max_results))
    except Exception as exc:
        log.warning("DDG search failed for %r: %s", query, exc)
        return []

    out: list[dict] = []
    n = len(raw)
    for i, item in enumerate(raw):
        url = item.get("href") or item.get("url") or ""
        if not url:
            continue
        # Synthesize a rank-based score (1.0 for first hit, decreasing).
        score = 1.0 - (i / max(1, n))
        out.append({
            "url": url,
            "title": item.get("title") or url,
            "content_fallback": (item.get("body") or "").strip(),
            "score": score,
        })
    return out


async def web_search(query: str, *, max_results: int | None = None) -> list[dict]:
    """Return list of {url, title, content_fallback, score} for one query.

    Compresses long claim sentences into a keyword query before hitting
    DDG — full-sentence queries cause every backend engine to timeout.
    """
    settings = get_settings()
    limit = max_results or settings.search_max_results
    compressed = _compress_query(query)
    if compressed != query:
        log.info("Search query compressed: %r → %r", query[:60], compressed)
    return await asyncio.to_thread(
        _ddg_search_sync, compressed, limit, settings.ddgs_proxy, settings.search_region,
    )




def _load_one_sync(url: str) -> str:
    try:
        from langchain_community.document_loaders import WebBaseLoader
    except ImportError:
        return ""
    try:
        loader = WebBaseLoader(url)
        loader.requests_kwargs = {
            "timeout": 15,
            "headers": {"User-Agent": "Mozilla/5.0 (FactGuard)"},
        }
        docs = loader.load()
        if docs and docs[0].page_content.strip():
            return docs[0].page_content.strip()
    except Exception as exc:
        log.info("WebBaseLoader failed for %s: %s", url[:80], exc)
    return ""


def _domain(url: str) -> str:
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc.replace("www.", "") or url
    except Exception:
        return url


async def load_documents(
    urls: Iterable[str],
    *,
    on_progress: ProgressCB | None = None,
    concurrency: int = 4,
) -> dict[str, str]:
    """Parallel WebBaseLoader fetch with per-URL progress reporting.

    Reports `(done, total, "Loaded N/M · domain")` as each URL completes,
    so the UI bar advances continuously instead of in one big jump.
    """
    unique = list(dict.fromkeys(u for u in urls if u))
    total = len(unique) or 1
    if not unique:
        return {}

    sem = asyncio.Semaphore(concurrency)
    results: dict[str, str] = {}
    done = 0
    lock = asyncio.Lock()

    async def fetch(url: str) -> None:
        nonlocal done
        async with sem:
            content = await asyncio.to_thread(_load_one_sync, url)
        async with lock:
            done += 1
            n = done
            if content:
                results[url] = content
        if on_progress:
            await on_progress(n, total, f"Loaded {n}/{total} · {_domain(url)}")

    await asyncio.gather(*(fetch(u) for u in unique))
    return results


async def gather_evidence(
    queries: list[str],
    *,
    on_search_progress: ProgressCB | None = None,
    on_load_progress: ProgressCB | None = None,
) -> list[list[dict]]:
    """End-to-end evidence retrieval for many queries.

    Two reporting hooks:
      * `on_search_progress(done, total, msg)` ticks as each DDG query returns.
      * `on_load_progress(done, total, msg)` ticks as each unique URL is loaded.
    """
    settings = get_settings()
    sem = asyncio.Semaphore(4)
    total_q = len(queries) or 1
    done_q = 0
    lock = asyncio.Lock()

    async def search(q: str) -> list[dict]:
        nonlocal done_q
        async with sem:
            r = await web_search(q)
        async with lock:
            done_q += 1
            n = done_q
        if on_search_progress:
            await on_search_progress(n, total_q, f"Searched {n}/{total_q}")
        return r

    per_query = await asyncio.gather(*(search(q) for q in queries))

    if settings.use_web_base_loader:
        all_urls = [r["url"] for results in per_query for r in results]
        loaded = await load_documents(all_urls, on_progress=on_load_progress)
    else:
        loaded = {}

    enriched: list[list[dict]] = []
    for results in per_query:
        rows: list[dict] = []
        for r in results:
            content = loaded.get(r["url"]) or r["content_fallback"]
            if not content:
                continue
            rows.append({
                "url": r["url"],
                "title": r["title"],
                "content": content,
                "score": r["score"],
            })
        enriched.append(rows)
    return enriched


# Backwards-compatible alias for any external callers.
async def search_many(queries: list[str], *, max_results: int | None = None) -> list[list[dict]]:
    return await gather_evidence(queries)
