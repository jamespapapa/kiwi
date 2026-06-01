from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from .models import InternalSettings


LOGGER = logging.getLogger(__name__)


class QwenClient:
    def __init__(self, settings: InternalSettings):
        self.settings = settings

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> str:
        endpoint = _chat_endpoint(self.settings.api_base_url)
        model_name = model or self.settings.orchestrator_model
        api_key = self.settings.api_key or "sk-local-qwen35"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        payload: dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        timeout = httpx.Timeout(self.settings.request_timeout_seconds)
        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=timeout, verify=False, trust_env=False) as client:
                response = await client.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            LOGGER.error(
                "Qwen chat HTTP failure status=%s endpoint=%s model=%s elapsed_ms=%s body=%s",
                exc.response.status_code,
                endpoint,
                model_name,
                elapsed_ms,
                exc.response.text[:1000],
            )
            raise
        except httpx.HTTPError:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            LOGGER.exception(
                "Qwen chat transport failure endpoint=%s model=%s elapsed_ms=%s",
                endpoint,
                model_name,
                elapsed_ms,
            )
            raise

        try:
            data = response.json()
        except ValueError as exc:
            raise RuntimeError(f"Qwen 응답이 JSON이 아닙니다: {response.text[:500]}") from exc

        try:
            return data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("Qwen 응답 형식이 OpenAI chat completions와 다릅니다.") from exc


def _chat_endpoint(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/chat/completions"):
        return normalized
    if normalized.endswith("/v1"):
        return f"{normalized}/chat/completions"
    return f"{normalized}/v1/chat/completions"
