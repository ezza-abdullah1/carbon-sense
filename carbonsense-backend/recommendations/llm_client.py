"""
Google Gemini LLM client for generating recommendations.
"""

import google.generativeai as genai
from django.conf import settings


class GeminiClient:
    """Wraps the Google Generative AI SDK for Gemini calls."""

    def __init__(self):
        api_key = settings.GEMINI_API_KEY
        if not api_key or api_key == 'your-gemini-api-key-here':
            raise ValueError(
                "GEMINI_API_KEY is not configured. "
                "Set it in your .env file."
            )
        genai.configure(api_key=api_key)

    def generate(self, system_prompt, user_prompt):
        """Generate a response from Gemini.

        Args:
            system_prompt: The system instruction prompt.
            user_prompt: The user message prompt.

        Returns:
            Raw text response string from the model.
        """
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
                max_output_tokens=4096,
                response_mime_type="application/json",
            ),
        )

        return response.text
