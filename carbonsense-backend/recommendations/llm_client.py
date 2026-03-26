"""
Google Gemini LLM client — used ONLY for optional summary enhancement.

The template builder generates 95% of the response.  Gemini polishes the
summary with ~150 output tokens.  If Gemini is down or quota is hit, the
template summary is used as-is.
"""

import logging

import google.generativeai as genai
from django.conf import settings

logger = logging.getLogger(__name__)


class GeminiClient:
    """Wraps the Google Generative AI SDK for lightweight Gemini calls."""

    def __init__(self):
        api_key = getattr(settings, 'GEMINI_API_KEY', '')
        if not api_key or api_key == 'your-gemini-api-key-here':
            self._configured = False
            return
        genai.configure(api_key=api_key)
        self._configured = True

    @property
    def available(self):
        return self._configured

    # ------------------------------------------------------------------ #
    # Lightweight summary enhancer  (~200 input + 150 output tokens)
    # ------------------------------------------------------------------ #

    def enhance_summary(self, template_summary, area_name, sector):
        """Enhance a template-generated summary with LLM polish.

        Args:
            template_summary: The data-driven summary from the template builder.
            area_name: Name of the area.
            sector: Primary sector.

        Returns:
            Enhanced summary string, or None on any failure.
        """
        if not self._configured:
            return None

        try:
            model = genai.GenerativeModel('gemini-2.0-flash')

            prompt = (
                f"Improve this environmental summary for {area_name} ({sector}) "
                f"in Lahore, Pakistan. Make it more natural and insightful. "
                f"Keep under 4 sentences. Return ONLY the improved text.\n\n"
                f"{template_summary}"
            )

            response = model.generate_content(
                contents=[{"role": "user", "parts": [{"text": prompt}]}],
                generation_config=genai.types.GenerationConfig(
                    temperature=0.5,
                    max_output_tokens=150,
                ),
            )

            text = response.text.strip()
            if len(text) > 20:
                return text
            return None

        except Exception as e:
            logger.warning(f"Gemini enhance_summary failed (will use template): {e}")
            return None

    # ------------------------------------------------------------------ #
    # Full generation (legacy — kept for compatibility)
    # ------------------------------------------------------------------ #

    def generate(self, system_prompt, user_prompt):
        """Generate a full response from Gemini (legacy path)."""
        if not self._configured:
            raise RuntimeError("Gemini API key is not configured.")

        model = genai.GenerativeModel(
            'gemini-2.0-flash',
            system_instruction=system_prompt,
        )

        response = model.generate_content(
            contents=[
                {"role": "user", "parts": [{"text": user_prompt}]},
            ],
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                top_p=0.9,
                max_output_tokens=2048,
                response_mime_type="application/json",
            ),
        )

        return response.text
