# FactGuard

A cited-summary fact-checker for online video. Drop a YouTube URL or upload a clip and FactGuard:

1. Pulls the transcript (YouTube captions first, faster-whisper fallback on audio).
2. **Splits the transcript into ~25-word utterances** — punctuation when present, hard word-window otherwise so unpunctuated auto-captions don't collapse into one blob.
3. **Walks every utterance** with `gemma4:e4b` and emits a self-contained checkworthy point per worthy sentence, resolving pronouns to their named antecedents.
4. **Fact-checks every point against the live web** — no parametric shortcut. Per claim: DuckDuckGo search → WebBaseLoader page fetch → chunk + Qdrant Cloud Inference rerank → `gemma4:e4b` writes a JSON-mode answer with inline `[N]` citations.
5. **Synthesizes one overall answer** — all per-point citations are pooled into a deduped global evidence list; `gemma4:e4b` writes a 4-8 sentence cited summary with inline `[N]` markers referencing the global list. The UI renders those markers as clickable pills linking to the sources.
6. Optional Ragas eval over `(point, answer, evidence)` triples → blended accuracy score.

## Architecture

```
apps/
├── web/        Next.js 14 (App Router) — UI + /api/proxy passthrough
└── api/        FastAPI — pipeline, retrieval, synthesis
docker-compose.yml   ollama + api + web
```

| Concern        | Choice                                                                 |
|----------------|------------------------------------------------------------------------|
| LLM            | Ollama, local, `gemma4:e4b` (only model used end-to-end)               |
| Embeddings     | Qdrant Cloud Inference — server-side, no local embed model              |
| Vector store   | Qdrant Cloud — per-job collection, dropped at end of run                |
| Web search     | DuckDuckGo via [`ddgs`](https://pypi.org/project/ddgs/) (no API key)    |
| Page fetch     | langchain `WebBaseLoader`                                              |
| Transcript     | youtube-transcript-api → faster-whisper                                |
| Video pull     | yt-dlp + ffprobe (duration only)                                       |
| RAG eval       | Ragas (faithfulness, relevancy, ctx P/R) — optional                    |

## Environments

`pydantic-settings` loads `apps/api/.env.local` when `APP_ENV=local` (the default).

```bash
# local dev (no docker)
APP_ENV=local uvicorn factguard_api.main:app --reload --port 8000

# docker
docker compose up --build
```

Only two env files: [`apps/api/.env.local`](apps/api/.env.local) (gitignored, holds your real secrets) and [`apps/api/.env.example`](apps/api/.env.example) (template, committed). Required keys: `QDRANT_URL`, `QDRANT_API_KEY`. Everything else has defaults.

## Quick start (Docker)

```bash
cp apps/api/.env.example apps/api/.env.local
# edit apps/api/.env.local: fill in QDRANT_URL + QDRANT_API_KEY

docker compose up --build
# in a second shell, pull gemma4 on the running Ollama:
docker compose exec ollama ollama pull gemma4:e4b
```

Open http://localhost:3000.

## Local dev (no Docker)

```bash
# 1. Ollama (in its own shell)
ollama serve
ollama pull gemma4:e4b

# 2. API
cd apps/api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env.local   # fill in QDRANT_URL + QDRANT_API_KEY
uvicorn factguard_api.main:app --reload --port 8000

# 3. Web
cd apps/web
npm install
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

The Next.js app forwards `/api/proxy/*` to the API (`API_BASE_URL`), so the browser never talks to FastAPI directly.

## Implementation notes

- **Every point is web-grounded.** There is no parametric memory shortcut: every checkworthy sentence gets its own DDG round-trip.
- **Search queries are compressed.** Long claim sentences are reduced to keyword-style queries (~10 words, proper nouns front-loaded) before hitting DDG — otherwise every backend engine (Yahoo, Brave, Mojeek, …) times out.
- **Qdrant Cloud Inference does the embeddings.** `qmodels.Document(text=..., model=...)` is passed as the vector; the cloud embeds during upsert and query. No local embed model.
- **Race-safe collection creation.** N concurrent claims target the same job-id collection; `ensure_collection` treats 409 Conflict as success.
- **Generous timeouts + one retry.** Qdrant client timeout is 60s, and `_with_retry` retries upsert/query once on transient errors with a 1.5s backoff.
- **Streaming progress.** SSE responses ship with `Cache-Control: no-cache, no-store, no-transform` and `X-Accel-Buffering: no` so Next.js dev rewrites stream chunks instead of buffering until EOF. A background creep task nudges the bar between real ticks.
- **Global citation remap.** The synthesizer pools every per-point `Evidence` (deduped by URL), remaps each point's local `[i]` markers to the new global indices, then asks the LLM for the overall answer using the global list.

## License

MIT.
