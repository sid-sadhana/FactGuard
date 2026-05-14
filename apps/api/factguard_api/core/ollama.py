"""Thin async client for the Ollama HTTP API.

Works against both local Ollama (http://localhost:11434) and Ollama Cloud
(https://ollama.com) — set OLLAMA_API_KEY for the cloud path; the client
adds the Bearer header automatically.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

import httpx

from .config import get_settings
from .logging import get_logger

log = get_logger(__name__)


class OllamaClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.api_key = api_key if api_key is not None else settings.ollama_api_key
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else None
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(600.0, connect=10.0),
            headers=headers,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def generate(
        self,
        model: str,
        prompt: str,
        *,
        system: str | None = None,
        images: list[Path] | None = None,
        format: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": options or {"temperature": 0.1},
        }
        if system:
            payload["system"] = system
        if format:
            payload["format"] = format
        if images:
            payload["images"] = [self._encode_image(p) for p in images]

        r = await self._client.post(f"{self.base_url}/api/generate", json=payload)
        r.raise_for_status()
        data = r.json()
        return data.get("response", "").strip()

    async def generate_json(
        self,
        model: str,
        prompt: str,
        *,
        system: str | None = None,
        images: list[Path] | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        raw = await self.generate(
            model=model,
            prompt=prompt,
            system=system,
            images=images,
            format="json",
            options=options,
        )
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            log.warning("Ollama returned non-JSON despite format=json: %s", raw[:200])
            return {}

    async def chat(
        self,
        model: str,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        format: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": options or {"temperature": 0.1},
        }
        if tools:
            payload["tools"] = tools
        if format:
            payload["format"] = format

        r = await self._client.post(f"{self.base_url}/api/chat", json=payload)
        r.raise_for_status()
        return r.json()

    async def embed(self, model: str, text: str) -> list[float]:
        r = await self._client.post(
            f"{self.base_url}/api/embeddings",
            json={"model": model, "prompt": text},
        )
        r.raise_for_status()
        return r.json().get("embedding", [])

    @staticmethod
    def _encode_image(path: Path) -> str:
        return base64.b64encode(path.read_bytes()).decode("ascii")


_singleton: OllamaClient | None = None


def get_ollama() -> OllamaClient:
    global _singleton
    if _singleton is None:
        _singleton = OllamaClient()
    return _singleton
