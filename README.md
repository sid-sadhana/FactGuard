
---

## 2. 🧠 FactGuard — Real-Time YouTube Fact Checker

```markdown
# 🧠 FactGuard

A scalable AI platform that combats misinformation on YouTube by validating video content using Retrieval-Augmented Generation (RAG) and real-time fact-checking.

## ⚡ Features

- Scrapes and analyzes YouTube transcripts
- Real-time fact validation via trusted knowledge sources
- Uses LLaMA via Groq inference + GPT for cross-checking
- Responsive UI with Next.js
- Supports scalable multimedia pipelines

## 🛠️ Tech Stack

- Next.js frontend
- LLaMA and GPT models
- Groq for high-speed inference
- Backend: Python, FastAPI
- RAG + verified source referencing

## 🧪 Architecture

- Extract transcripts → Generate chunks
- Embed + store in vector DB
- Query LLMs with RAG context
- Return validation scores and responses

## 📜 License

MIT
