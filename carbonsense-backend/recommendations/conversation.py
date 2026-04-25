"""
ConversationManager — handles cross-questioning about a stored Recommendation.

The user asks follow-up questions about the recommendation; the LLM answers
grounded in the original Recommendation.content_json plus the original
retrieved_context. New retrieval is triggered only if the user asks for
new examples or comparisons.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from django.conf import settings

from recommendations.llm_client import LLMClient
from recommendations.models import (
    Recommendation,
    RecommendationConversation,
)
from recommendations.tools.policy_retriever import PolicyRetriever, NewsRetriever
from recommendations.tools.emission_context import build_place_context

logger = logging.getLogger(__name__)


CHAT_SYSTEM_PROMPT = (
    "You are a senior climate policy advisor answering follow-up questions "
    "about a recommendation that has ALREADY been delivered to the user for "
    "a specific Union Council in Lahore, Pakistan.\n\n"
    "RULES:\n"
    "1. Treat the original recommendation JSON and the retrieved policy "
    "snippets as ground truth — do not contradict them.\n"
    "2. Cite specific numbers from the place context (forecast tonnes, "
    "rank, intensity, risk flags) whenever you justify a point.\n"
    "3. If the user asks about another country / case study and the data is "
    "not in the retrieved context, say so explicitly before offering a best-"
    "effort answer.\n"
    "4. Be concise (under 200 words unless the user asks for more).\n"
    "5. Reply in plain prose, NOT JSON. Do not use markdown headings."
)


_NEW_LOOKUP_TRIGGERS = ('example', 'case study', 'another country', 'compare',
                        'similar city', 'best practice', 'recent', '2025',
                        '2026', 'latest')


class ConversationManager:
    """Handle one chat turn against a stored Recommendation."""

    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or LLMClient()
        self.history_turns = int(
            getattr(settings, 'RECOMMENDATION_CHAT_HISTORY_TURNS', 6)
        )

    def handle_turn(self, recommendation_id: str, user_message: str) -> Dict[str, Any]:
        rec = Recommendation.objects.get(pk=recommendation_id)
        conv, _ = RecommendationConversation.objects.get_or_create(
            recommendation=rec,
            defaults={'messages': []},
        )

        messages: List[Dict[str, Any]] = list(conv.messages or [])
        # Optional in-conversation retrieval
        extra_context = self._maybe_retrieve(user_message, rec)

        prompt = self._build_user_prompt(rec, messages, user_message, extra_context)
        try:
            reply = self.llm.generate(
                CHAT_SYSTEM_PROMPT,
                prompt,
                json_mode=False,
                max_tokens=600,
                temperature=0.4,
            )
        except Exception as exc:
            logger.exception("Chat LLM call failed: %s", exc)
            return {
                'recommendation_id': str(rec.id),
                'reply': "I couldn't reach the LLM provider right now. Please try again in a moment.",
                'history': messages,
                'error': str(exc),
            }

        now_iso = datetime.now(timezone.utc).isoformat()
        messages.append({'role': 'user', 'content': user_message, 'ts': now_iso})
        messages.append({
            'role': 'assistant',
            'content': reply,
            'ts': datetime.now(timezone.utc).isoformat(),
            'extra_context_count': len(extra_context),
        })
        conv.messages = messages
        conv.save(update_fields=['messages', 'updated_at'])

        return {
            'recommendation_id': str(rec.id),
            'reply': reply,
            'history': messages,
            'used_extra_lookup': bool(extra_context),
        }

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    def _maybe_retrieve(self, user_message: str, rec: Recommendation) -> List[dict]:
        text = (user_message or '').lower()
        if not any(trigger in text for trigger in _NEW_LOOKUP_TRIGGERS):
            return []
        try:
            ctx = build_place_context(rec.area_name, rec.sector, rec.coordinates)
            policy = PolicyRetriever().retrieve(ctx, n_results=3)
            if not policy:
                policy = NewsRetriever().retrieve(ctx, n_results=3)
            return policy or []
        except Exception as exc:
            logger.warning("In-conversation retrieval failed: %s", exc)
            return []

    def _build_user_prompt(self, rec: Recommendation,
                           history: List[Dict[str, Any]],
                           user_message: str,
                           extra_context: List[dict]) -> str:
        parts: List[str] = []

        parts.append(f"PLACE: {rec.area_name} ({rec.sector}), Lahore, Pakistan")
        parts.append(
            f"COORDINATES: {(rec.coordinates or {}).get('lat')}, "
            f"{(rec.coordinates or {}).get('lng')}"
        )
        parts.append('')
        parts.append("ORIGINAL RECOMMENDATION (ground truth):")
        parts.append(json.dumps(rec.content_json or {}, indent=2)[:3500])

        # Pinned policy chunks
        retrieved = (rec.retrieved_context or {}).get('policies') or []
        if retrieved:
            parts.append('')
            parts.append("RETRIEVED POLICY CONTEXT (the original sources):")
            for i, item in enumerate(retrieved[:3], 1):
                meta = item.get('metadata') or {}
                parts.append(
                    f"[{i}] {meta.get('document_title', '?')} "
                    f"({meta.get('year', '')}, {meta.get('country', '')})"
                )
                parts.append((item.get('text') or '')[:500])

        if extra_context:
            parts.append('')
            parts.append("ADDITIONAL CONTEXT JUST RETRIEVED FOR THIS QUESTION:")
            for i, item in enumerate(extra_context, 1):
                meta = item.get('metadata') or {}
                parts.append(
                    f"[N{i}] {meta.get('document_title', '?')} "
                    f"({meta.get('year', '')}, {meta.get('country', '')})"
                )
                parts.append((item.get('text') or '')[:400])

        # Recent chat history (last N turns)
        keep = max(0, self.history_turns) * 2  # user+assistant per turn
        recent = history[-keep:] if keep else []
        if recent:
            parts.append('')
            parts.append("RECENT CHAT HISTORY:")
            for msg in recent:
                role = msg.get('role', 'user').upper()
                parts.append(f"{role}: {msg.get('content', '')}")

        parts.append('')
        parts.append(f"USER: {user_message}")
        parts.append("ASSISTANT:")
        return "\n".join(parts)
