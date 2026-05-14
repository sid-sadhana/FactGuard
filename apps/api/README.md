# FactGuard API

FastAPI service that runs the fact-check pipeline:

```
ingest → transcript (youtube-transcript-api / faster-whisper)
       → LLM point selection (whole transcript → list of checkworthy points,
         each flagged needs_search or answerable from memory)
       → for flagged points: Tavily search → WebBaseLoader page fetch
         → chunk + embed-rerank → top evidence
       → LLM writes a cited JSON answer; unflagged points use the picker's
         preliminary answer directly
       → Ragas eval (optional) → blended score
```

## Run locally

```bash
cd apps/api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in TAVILY_API_KEY
uvicorn factguard_api.main:app --reload --port 8000
```

You also need:
* `yt-dlp` and `ffprobe` (from ffmpeg) on PATH
* an Ollama server reachable at `OLLAMA_BASE_URL` with the LLM and embedding
  models pulled

```bash
ollama pull qwen3-vl              # or any text LLM you prefer
ollama pull nomic-embed-text
```

## Layout

```
factguard_api/
  core/        config, logging, ollama client, progress reporter
  models/      pydantic schemas
  store/       in-process job + pub/sub
  services/    pipeline steps (youtube, frames [ffprobe only], transcript,
               claims [LLM picker], search, rag, agent, eval, score, pipeline)
  routes/      FastAPI routers (analyze, jobs)
  prompts/     LLM prompt templates
  main.py      FastAPI app factory
```
