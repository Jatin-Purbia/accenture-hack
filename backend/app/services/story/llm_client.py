"""Story layer — the ONLY place in this codebase that calls an LLM.

Every other layer (data/signal/reasoning) is deterministic pandas/NumPy/
statsmodels. This module exists so that boundary is enforceable in code, not
just in prose: `LLMClient` is the single interface every narrative call goes
through, so provider swaps, cost tracking, and the grounding-check middleware
(grounding.py) all have exactly one chokepoint to hook into.

Two providers are implemented:
  - OpenAIClient   — used when OPENAI_API_KEY is configured.
  - OllamaClient   — a free, local, no-API-key fallback (this dev machine
    already has qwen2.5 models pulled). Used automatically when no OpenAI
    key is configured, so the system is runnable out of the box, and
    available as an explicit choice via LLM_PROVIDER=ollama.

Neither client is ever called by the Signal or Reasoning layers — grep for
`LLMClient` usage outside `services/story/` should always come up empty.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

import httpx

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)

Tier = Literal["cheap", "strong"]

# Approximate published per-token pricing (USD per 1M tokens), used only for
# the telemetry panel's cost estimate — not billing-accurate, illustrative.
_PRICING_USD_PER_1M_TOKENS: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "qwen2.5:1.5b": (0.0, 0.0),
    "qwen2.5:3b": (0.0, 0.0),
    "qwen2.5:7b": (0.0, 0.0),
}


def estimate_cost_usd(model: str, tokens_in: int, tokens_out: int) -> float:
    in_rate, out_rate = _PRICING_USD_PER_1M_TOKENS.get(model, (0.0, 0.0))
    return (tokens_in / 1_000_000) * in_rate + (tokens_out / 1_000_000) * out_rate


@dataclass
class LLMResponse:
    text: str
    provider: str
    model: str
    tier: Tier
    tokens_in: int
    tokens_out: int
    latency_ms: float
    estimated_cost_usd: float


class LLMClient(ABC):
    provider_name: str

    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str, tier: Tier) -> LLMResponse: ...


class OpenAIClient(LLMClient):
    provider_name = "openai"

    def __init__(self, api_key: str, model_cheap: str, model_strong: str):
        from openai import OpenAI  # deferred import — keeps the module importable without the package installed

        self._client = OpenAI(api_key=api_key)
        self._models = {"cheap": model_cheap, "strong": model_strong}

    def complete(self, system_prompt: str, user_prompt: str, tier: Tier) -> LLMResponse:
        model = self._models[tier]
        start = time.perf_counter()
        response = self._client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )
        latency_ms = (time.perf_counter() - start) * 1000
        text = response.choices[0].message.content or ""
        tokens_in = response.usage.prompt_tokens if response.usage else 0
        tokens_out = response.usage.completion_tokens if response.usage else 0
        return LLMResponse(
            text=text,
            provider=self.provider_name,
            model=model,
            tier=tier,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            estimated_cost_usd=estimate_cost_usd(model, tokens_in, tokens_out),
        )


class OllamaClient(LLMClient):
    provider_name = "ollama"

    def __init__(self, base_url: str, model_cheap: str, model_strong: str):
        self._base_url = base_url.rstrip("/")
        self._models = {"cheap": model_cheap, "strong": model_strong}

    def complete(self, system_prompt: str, user_prompt: str, tier: Tier) -> LLMResponse:
        model = self._models[tier]
        start = time.perf_counter()
        # CPU-only local inference is genuinely slow for a several-hundred-
        # token prompt (measured 30-90s on a dev laptop even with a warm
        # model) — this is a real cost/latency tradeoff of the free local
        # fallback tier, not a bug. See README "Cost, latency & scaling".
        with httpx.Client(timeout=240.0) as client:
            resp = client.post(
                f"{self._base_url}/api/chat",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "stream": False,
                    "options": {"temperature": 0.3},
                },
            )
            resp.raise_for_status()
            payload = resp.json()
        latency_ms = (time.perf_counter() - start) * 1000
        text = payload.get("message", {}).get("content", "")
        tokens_in = payload.get("prompt_eval_count", 0)
        tokens_out = payload.get("eval_count", 0)
        return LLMResponse(
            text=text,
            provider=self.provider_name,
            model=model,
            tier=tier,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            estimated_cost_usd=0.0,
        )


def build_llm_client(settings: Settings) -> LLMClient:
    provider = settings.llm_provider
    has_openai_key = bool(settings.openai_api_key) and not settings.openai_api_key.startswith("sk-replace")

    if provider == "openai" and not has_openai_key:
        logger.warning(
            "openai_key_missing_falling_back_to_ollama",
            note="Set OPENAI_API_KEY in backend/.env to use OpenAI instead.",
        )
        provider = "ollama"

    if provider == "openai":
        return OpenAIClient(settings.openai_api_key, settings.openai_model_cheap, settings.openai_model_strong)
    return OllamaClient(settings.ollama_base_url, settings.ollama_model_cheap, settings.ollama_model_strong)
