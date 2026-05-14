"""Evidence retrieval.

Two steps so each does one job well:

  1. Tavily ranks the open web and returns top URLs (we don't trust its
     content snippet — too short to fact-check from).
  2. WebBaseLoader (langchain_community) fetches the full HTML of each URL
     and extracts text. Heavier, but gives the reranker real content to work
     with.

Both steps degrade gracefully:
  * If Tavily key is missing → empty results, pipeline still completes.
  * If WebBaseLoader / its deps aren't installed → fall back to Tavily's
    own raw_content for that URL.
  * Per-URL failures are logged and skipped (no whole-job aborts).

The pipeline calls `gather_evidence(queries)` which dedupes URL fetches
across all queries — so two claims sharing a hit only cost one HTTP load.
"""
from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, Iterable

import httpx

from ..core.config import get_settings
from ..core.logging import get_logger

log = get_logger(__name__)

ProgressCB = Callable[[int, int, str], Awaitable[None]]


async def tavily_search(query: str, *, max_results: int | None = None) -> list[dict]:
    """Return list of {url, title, content_fallback, score} for one query.

    `content_fallback` holds Tavily's own snippet; we use it only when the
    web loader fails for that URL.
    """
    settings = get_settings()
    if not settings.tavily_api_key:
        log.warning("TAVILY_API_KEY missing — returning empty evidence")
        return []

    payload = {
        "api_key": settings.tavily_api_key,
        "query": query,
        "search_depth": settings.tavily_search_depth,
        "max_results": max_results or settings.tavily_max_results,
        "include_answer": False,
        "include_raw_content": True,
    }
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            r = await client.post("https://api.tavily.com/search", json=payload)
            r.raise_for_status()
            data = r.json()
    except Exception as exc:
        log.warning("Tavily search failed for %r: %s", query, exc)
        return []

    out: list[dict] = []
    for item in (data.get("results") or []):
        url = item.get("url") or ""
        if not url:
            continue
        out.append({
            "url": url,
            "title": item.get("title") or url,
            "content_fallback": (item.get("raw_content") or item.get("content") or "").strip(),
            "score": float(item.get("score", 0.0)),
        })
    return out


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
    on_tavily_progress: ProgressCB | None = None,
    on_load_progress: ProgressCB | None = None,
) -> list[list[dict]]:
    """End-to-end evidence retrieval for many queries.

    Two reporting hooks:
      * `on_tavily_progress(done, total, msg)` ticks as each Tavily query returns.
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
            r = await tavily_search(q)
        async with lock:
            done_q += 1
            n = done_q
        if on_tavily_progress:
            await on_tavily_progress(n, total_q, f"Searched {n}/{total_q}")
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
