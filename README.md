# FactGuard

A fact-checker for online video. Drop a YouTube URL or upload a clip, and FactGuard:

1. Pulls the transcript (captions API first, faster-whisper fallback).
2. Feeds the whole transcript to an LLM that picks every checkworthy point and
   flags which ones need a fresh web search vs. can be answered from its own
   training.
3. For each flagged point: Tavily search → WebBaseLoader fetches the full page
   text → chunk + embed + rerank against the point → pack the top chunks.
4. The LLM writes a 2-4 sentence cited answer with inline `[N]` markers.
5. Unflagged points get the LLM's preliminary answer directly, no web round-trip.
6. Optional Ragas eval over the (point, answer, evidence) triples produces a
   blended accuracy score.

## Architecture

```
apps/
├── web/        Next.js 14 (App Router) — UI + thin /api/proxy passthrough
└── api/        FastAPI — pipeline, RAG, Ragas eval
docker-compose.yml   ollama + api + web
```

External services / runtimes:

| Concern           | Choice                                  |
|-------------------|-----------------------------------------|
| LLM               | Ollama — local (`qwen3-vl`) or Ollama Cloud (`gemma4:31b-cloud`) via `OLLAMA_API_KEY` |
| Embeddings        | Ollama, `nomic-embed-text`              |
| Vector store      | Qdrant Cloud (production only, per-job collections dropped at end of run) |
| Web search        | Tavily                                  |
| Page fetch        | langchain `WebBaseLoader`               |
| RAG eval          | Ragas (faithfulness, relevancy, ctx P/R) |
| Transcript        | youtube-transcript-api → faster-whisper |
| Video pull        | yt-dlp + ffprobe (duration only)        |

## Environments

`APP_ENV` picks which env file `pydantic-settings` loads:

| `APP_ENV`      | File                       | Ollama target          | Qdrant |
|----------------|----------------------------|------------------------|--------|
| `local` (default) | `apps/api/.env.local`   | `http://localhost:11434` | off — inline cosine |
| `production`   | `apps/api/.env.production` | `https://ollama.com` (Bearer auth) | on — per-job collections, deleted at end of run |

```bash
# local dev
APP_ENV=local uvicorn factguard_api.main:app --reload --port 8000

# production
APP_ENV=production uvicorn factguard_api.main:app --port 8000

# docker
APP_ENV=production docker compose up --build
```

Both files are gitignored; commit secrets nowhere. Use `apps/api/.env.example` as the template.

## Quick start (Docker)

```bash
cp apps/api/.env.example apps/api/.env   # fill in TAVILY_API_KEY
docker compose up --build
# in a second shell, pull the models on the running Ollama:
docker compose exec ollama ollama pull qwen3-vl
docker compose exec ollama ollama pull nomic-embed-text
```

Open http://localhost:3000.

## Local dev (no Docker)

```bash
# 1. Ollama (in its own shell)
ollama serve
ollama pull qwen3-vl
ollama pull nomic-embed-text

# 2. API
cd apps/api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set TAVILY_API_KEY
uvicorn factguard_api.main:app --reload --port 8000

# 3. Web
cd apps/web
npm install
cp .env.example .env
npm run dev
```

You also need `yt-dlp` and `ffprobe` (from ffmpeg) on `PATH`.

## Endpoints

| Method | Path                            | Purpose                                       |
|--------|---------------------------------|-----------------------------------------------|
| POST   | `/analyze/youtube`              | Create job from a YouTube URL                 |
| POST   | `/analyze/upload`               | Create job from a multipart video upload      |
| GET    | `/jobs/{job_id}`                | Snapshot of a job                             |
| GET    | `/jobs/{job_id}/events`         | Server-sent events of progress + final result |
| GET    | `/health`                       | Liveness                                      |

The Next.js app forwards `/api/proxy/*` to the API (`API_BASE_URL`), so the
browser never talks to FastAPI directly.

## How it answers a point

* **LLM-driven point selection** — one LLM call reads the whole transcript and
  returns `{text, needs_search, prelim_answer}` for every checkworthy point. No
  hardcoded cap; the LLM decides how many points and whether each needs a fresh
  search.
* **Per-point search** — flagged points each get their own Tavily query so
  retrieval is scoped to what's being verified.
* **Chunked-and-reranked evidence** — each fetched page is split into
  overlapping chunks; chunks are ranked by claim-embedding cosine similarity
  blended with the Tavily source score, then greedily packed under a per-point
  character budget. URLs are deduped so one source can't dominate.
* **JSON-mode answer** — the answerer returns
  `{answer, supporting_indices}`, with inline `[N]` markers tied to the
  evidence indices passed in.
* **Parametric shortcut** — when the picker says `needs_search=false` we skip
  Tavily entirely and use the preliminary answer the picker already produced.
* **Ragas eval** (optional) — `faithfulness`, `answer_relevancy`,
  `context_precision`, `context_recall` run over the point/answer/context
  triples and feed the blended score.

## License

MIT.
