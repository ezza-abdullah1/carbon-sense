"""
Groq LLM client — uses Llama 3.3 70B via Groq for recommendation generation
and optional summary enhancement.
"""

import json
import logging

from groq import Groq
from django.conf import settings

logger = logging.getLogger(__name__)

GROQ_MODEL = 'llama-3.3-70b-versatile'


class GeminiClient:
    """Wraps the Groq SDK (Llama 3.3 70B). Class name kept for compatibility."""

    def __init__(self):
        api_key = getattr(settings, 'GROQ_API_KEY', '')
        if not api_key or api_key == 'your-groq-api-key-here':
            self._configured = False
            self._client = None
            return
        self._client = Groq(api_key=api_key)
        self._configured = True

    @property
    def available(self):
        return self._configured

    # ------------------------------------------------------------------ #
    # Lightweight summary enhancer
    # ------------------------------------------------------------------ #

    def enhance_summary(self, template_summary, area_name, sector):
        """Enhance a template-generated summary with LLM polish.

        Returns:
            Enhanced summary string, or None on any failure.
        """
        if not self._configured:
            return None

        try:
            response = self._client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "user", "content": (
                        f"Improve this environmental summary for {area_name} ({sector}) "
                        f"in Lahore, Pakistan. Make it more natural and insightful. "
                        f"Keep under 4 sentences. Return ONLY the improved text.\n\n"
                        f"{template_summary}"
                    )},
                ],
                temperature=0.5,
                max_tokens=150,
            )

            text = response.choices[0].message.content.strip()
            if len(text) > 20:
                return text
            return None

        except Exception as e:
            logger.warning(f"Groq enhance_summary failed (will use template): {e}")
            return None

    # ------------------------------------------------------------------ #
    # Full generation
    # ------------------------------------------------------------------ #

    def generate(self, system_prompt, user_prompt):
        """Generate a full response from Groq (Llama 3.3 70B)."""
        if not self._configured:
            raise RuntimeError("Groq API key is not configured.")

        response = self._client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            top_p=0.9,
            max_tokens=2048,
            response_format={"type": "json_object"},
        )

        return response.choices[0].message.content
