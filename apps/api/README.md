# FactGuard API

FastAPI service that runs the fact-check pipeline:

```
ingest → transcript (youtube-transcript-api / faster-whisper)
       → sentence-split into ~25-word utterances (handles unpunctuated
         auto-captions) → gemma4:e4b extracts every checkworthy point as
         a self-contained sentence with pronouns resolved
       → per point: DuckDuckGo search (via ddgs) → WebBaseLoader fetch
         → chunk + Qdrant Cloud Inference rerank (server-side embeddings,
         no local embed model) → gemma4:e4b writes a JSON-mode answer
         with inline [N] citations
       → pool every per-point citation into a deduped global list →
         gemma4:e4b writes a single cited overall synthesis with
         inline [N] markers referencing the global list
       → Ragas eval (optional) → blended score
```

## Run locally

```bash
cd apps/api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env.local   # then fill in QDRANT_URL + QDRANT_API_KEY
uvicorn factguard_api.main:app --reload --port 8000
```

You also need:
* `yt-dlp` and `ffprobe` (from ffmpeg) on PATH
* an Ollama server reachable at `OLLAMA_BASE_URL` with the LLM pulled
* a Qdrant Cloud account (URL + API key) — Cloud Inference handles every
  embedding server-side, so no local embed model is required

```bash
ollama pull gemma4:e4b            # only LLM used end-to-end
```

## Layout

```
factguard_api/
  core/        config, logging, ollama client, qdrant client, progress reporter
  models/      pydantic schemas
  store/       in-process job + pub/sub for SSE
  services/    pipeline steps:
                 youtube     yt-dlp download + metadata
                 frames      ffprobe (duration only)
                 transcript  youtube-transcript-api → faster-whisper
                 claims      sentence-split + LLM checkworthy-point extraction
                 search      DDG via ddgs + query compression
                 rag         per-claim Qdrant Cloud Inference rerank
                 agent       per-claim cited answerer
                 synthesize  single overall cited synthesis with
                             global citation remap
                 eval        optional Ragas
                 score       blended accuracy score
                 pipeline    orchestration + creep progress task
  routes/      FastAPI routers (analyze, jobs)
  prompts/     LLM prompt templates
  main.py      FastAPI app factory
```
