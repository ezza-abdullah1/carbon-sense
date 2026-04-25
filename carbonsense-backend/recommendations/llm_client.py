"""
Multi-provider LLM client for the agentic RAG pipeline.

Backends:
  - GeminiBackend (default, free at aistudio.google.com)
  - OpenRouterBackend (free models such as deepseek/deepseek-chat:free)
  - GroqBackend (kept for compatibility; currently not working in target env)

All backends expose the same interface:
  generate(system_prompt, user_prompt, *, json_mode=True, max_tokens=2048,
           temperature=0.5)  -> str
"""

from __future__ import annotations

import logging
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)


class _BaseBackend:
    name = 'base'

    def __init__(self):
        self._configured = False

    @property
    def available(self) -> bool:
        return self._configured

    def generate(self, system_prompt: str, user_prompt: str, *,
                 json_mode: bool = True, max_tokens: int = 2048,
                 temperature: float = 0.5) -> str:
        raise NotImplementedError


class GeminiBackend(_BaseBackend):
    name = 'gemini'

    def __init__(self):
        super().__init__()
        api_key = getattr(settings, 'GEMINI_API_KEY', '') or ''
        self._model_name = getattr(settings, 'GEMINI_MODEL', 'gemini-2.0-flash')
        if not api_key or api_key.startswith('your-'):
            self._client = None
            return
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self._genai = genai
            self._configured = True
        except ImportError:
            logger.warning("google-generativeai not installed; Gemini backend unavailable")
            self._client = None

    def generate(self, system_prompt, user_prompt, *,
                 json_mode=True, max_tokens=2048, temperature=0.5):
        if not self._configured:
            raise RuntimeError("Gemini API key is not configured.")

        generation_config = {
            'temperature': temperature,
            'max_output_tokens': max_tokens,
            'top_p': 0.9,
        }
        if json_mode:
            generation_config['response_mime_type'] = 'application/json'

        model = self._genai.GenerativeModel(
            model_name=self._model_name,
            system_instruction=system_prompt,
            generation_config=generation_config,
        )
        response = model.generate_content(user_prompt)
        return (response.text or '').strip()


class OpenRouterBackend(_BaseBackend):
    name = 'openrouter'

    # Hard-coded fallback used only if the live API discovery fails. These
    # are slugs that have historically been free; ordered roughly by quality.
    # Live discovery via /api/v1/models is preferred — see _discover_free_models.
    FREE_MODEL_FALLBACKS = [
        'meta-llama/llama-3.3-70b-instruct:free',
        'google/gemma-4-31b-it:free',
        'google/gemma-4-26b-a4b-it:free',
        'nvidia/nemotron-3-super-120b-a12b:free',
        'minimax/minimax-m2.5:free',
        'inclusionai/ling-2.6-flash:free',
        'inclusionai/ling-2.6-1t:free',
    ]

    # Quality-ordered prefixes — earlier prefixes preferred when ranking
    # discovered free models.
    PREFERRED_VENDOR_ORDER = (
        'meta-llama/',
        'google/gemma',
        'nvidia/',
        'qwen/',
        'deepseek/',
        'mistralai/',
        'minimax/',
        'inclusionai/',
        'tencent/',
        'baidu/',
        'liquid/',
    )

    _DISCOVERY_CACHE: list[str] | None = None  # process-wide cache

    def __init__(self):
        super().__init__()
        api_key = getattr(settings, 'OPENROUTER_API_KEY', '') or ''
        self._model_name = getattr(settings, 'OPENROUTER_MODEL', '') or self.FREE_MODEL_FALLBACKS[0]
        if not api_key or api_key.startswith('your-'):
            self._client = None
            return
        try:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=api_key,
                base_url='https://openrouter.ai/api/v1',
            )
            self._configured = True
        except ImportError:
            logger.warning("openai SDK not installed; OpenRouter backend unavailable")
            self._client = None

    def _discover_free_models(self) -> list[str]:
        """Fetch the current list of free models from OpenRouter (cached for the process)."""
        if OpenRouterBackend._DISCOVERY_CACHE is not None:
            return OpenRouterBackend._DISCOVERY_CACHE
        try:
            import requests
            resp = requests.get(
                'https://openrouter.ai/api/v1/models',
                timeout=8,
            )
            resp.raise_for_status()
            data = resp.json().get('data', [])
            free = []
            for m in data:
                pricing = (m.get('pricing') or {})
                prompt_p = str(pricing.get('prompt', '')).strip()
                completion_p = str(pricing.get('completion', '')).strip()
                if prompt_p == '0' and completion_p == '0':
                    mid = m.get('id') or ''
                    if mid:
                        free.append(mid)
            # Sort by preferred vendor prefix.
            def rank(slug: str) -> int:
                for i, prefix in enumerate(self.PREFERRED_VENDOR_ORDER):
                    if slug.startswith(prefix):
                        return i
                return len(self.PREFERRED_VENDOR_ORDER) + 1
            free.sort(key=rank)
            if free:
                logger.info("Discovered %d free OpenRouter models", len(free))
                OpenRouterBackend._DISCOVERY_CACHE = free
                return free
        except Exception as exc:
            logger.warning("OpenRouter free-model discovery failed: %s", exc)
        # Fall back to the hard-coded list if discovery fails.
        OpenRouterBackend._DISCOVERY_CACHE = list(self.FREE_MODEL_FALLBACKS)
        return OpenRouterBackend._DISCOVERY_CACHE

    def _ordered_models(self):
        """Configured model first, then live-discovered free models, then hard-coded fallbacks."""
        seen = set()
        ordered = []
        candidates = [self._model_name] + self._discover_free_models() + list(self.FREE_MODEL_FALLBACKS)
        for m in candidates:
            if not m or m in seen:
                continue
            seen.add(m)
            ordered.append(m)
        return ordered

    def generate(self, system_prompt, user_prompt, *,
                 json_mode=True, max_tokens=2048, temperature=0.5):
        if not self._configured:
            raise RuntimeError("OpenRouter API key is not configured.")

        last_exc = None
        for model in self._ordered_models():
            kwargs = {
                'model': model,
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt},
                ],
                'temperature': temperature,
                'max_tokens': max_tokens,
                'top_p': 0.9,
            }
            if json_mode:
                kwargs['response_format'] = {'type': 'json_object'}

            try:
                response = self._client.chat.completions.create(**kwargs)
                content = (response.choices[0].message.content or '').strip()
                if content:
                    if model != self._model_name:
                        logger.info("OpenRouter served via fallback model %s", model)
                    return content
                logger.warning("OpenRouter %s returned empty content; trying next model", model)
            except Exception as exc:
                msg = str(exc)
                # Retry on transient/free-tier issues; abort on hard config errors.
                transient_markers = (
                    '429', 'rate-limit', 'rate_limit', 'temporarily',
                    'No endpoints found', 'overloaded', 'timeout', '503', '502',
                    'upstream', 'is not a valid model', '404',
                )
                if any(marker.lower() in msg.lower() for marker in transient_markers):
                    logger.warning(
                        "OpenRouter model %s transient failure (%s); trying next",
                        model, msg.split('\n', 1)[0][:200],
                    )
                    last_exc = exc
                    continue
                # Hard error (auth, malformed request, etc.) — re-raise immediately.
                raise

        raise RuntimeError(
            "All OpenRouter free models are currently rate-limited or unavailable. "
            "Last error: " + (str(last_exc) if last_exc else 'unknown')
        )


class GroqBackend(_BaseBackend):
    name = 'groq'

    def __init__(self):
        super().__init__()
        api_key = getattr(settings, 'GROQ_API_KEY', '') or ''
        self._model_name = 'llama-3.3-70b-versatile'
        if not api_key or api_key.startswith('your-'):
            self._client = None
            return
        try:
            from groq import Groq
            self._client = Groq(api_key=api_key)
            self._configured = True
        except ImportError:
            logger.warning("groq SDK not installed; Groq backend unavailable")
            self._client = None

    def generate(self, system_prompt, user_prompt, *,
                 json_mode=True, max_tokens=2048, temperature=0.5):
        if not self._configured:
            raise RuntimeError("Groq API key is not configured.")

        kwargs = {
            'model': self._model_name,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
            'temperature': temperature,
            'max_tokens': max_tokens,
            'top_p': 0.9,
        }
        if json_mode:
            kwargs['response_format'] = {'type': 'json_object'}

        response = self._client.chat.completions.create(**kwargs)
        return (response.choices[0].message.content or '').strip()


_BACKENDS = {
    'gemini': GeminiBackend,
    'openrouter': OpenRouterBackend,
    'groq': GroqBackend,
}


def _resolve_backend(provider: Optional[str]) -> _BaseBackend:
    provider = (provider or getattr(settings, 'LLM_PROVIDER', 'openrouter') or 'openrouter').lower()
    cls = _BACKENDS.get(provider, OpenRouterBackend)
    return cls()


class LLMClient:
    """Unified LLM client. Chooses backend by `provider` or settings.LLM_PROVIDER.

    Default and fallback are both OpenRouter — Gemini is only used when the
    caller (or env) explicitly sets LLM_PROVIDER=gemini.
    """

    def __init__(self, provider: Optional[str] = None):
        self._backend = _resolve_backend(provider)
        self._provider_name = self._backend.name
        if not self._backend.available:
            # Auto-fallback only to OpenRouter (never silently to Gemini).
            for fallback in ('openrouter', 'groq'):
                if fallback == self._backend.name:
                    continue
                candidate = _BACKENDS[fallback]()
                if candidate.available:
                    logger.info(
                        "LLM provider %s unavailable; falling back to %s",
                        self._backend.name, fallback,
                    )
                    self._backend = candidate
                    self._provider_name = fallback
                    break

    @property
    def available(self) -> bool:
        return self._backend.available

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def model_name(self) -> str:
        return getattr(self._backend, '_model_name', 'unknown')

    def generate(self, system_prompt: str, user_prompt: str, *,
                 json_mode: bool = True, max_tokens: int = 2048,
                 temperature: float = 0.5) -> str:
        return self._backend.generate(
            system_prompt, user_prompt,
            json_mode=json_mode, max_tokens=max_tokens, temperature=temperature,
        )


# Backwards-compatible alias used by the old agent / serializers
class GeminiClient(LLMClient):
    """Deprecated alias kept for compatibility with legacy imports."""

    def __init__(self):
        super().__init__()
