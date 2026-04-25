"""
Feedback service — records thumbs up/down per recommendation section
and aggregates highly-rated examples into a few-shot file consumed by
the synthesizer prompt.
"""

from __future__ import annotations

import json
import logging
import os
from collections import defaultdict
from typing import Any, Dict, List, Optional

from django.conf import settings

from recommendations.models import (
    Recommendation,
    RecommendationFeedback,
)

logger = logging.getLogger(__name__)


class FeedbackService:
    """Thin wrapper around RecommendationFeedback for the API + agent."""

    @staticmethod
    def record(recommendation_id: str, section: str, rating: int,
               comment: str = '') -> RecommendationFeedback:
        if rating not in (-1, 1):
            raise ValueError("rating must be +1 (thumbs up) or -1 (thumbs down)")
        rec = Recommendation.objects.get(pk=recommendation_id)
        return RecommendationFeedback.objects.create(
            recommendation=rec,
            section=section,
            rating=rating,
            comment=comment or '',
        )

    @staticmethod
    def aggregate_top_examples(sector: str, country: str, k: int = 2) -> List[dict]:
        """Return up to `k` recent thumbs-up examples for (sector, country)."""
        rows = (
            RecommendationFeedback.objects
            .select_related('recommendation')
            .filter(rating=1, recommendation__sector=sector)
            .order_by('-created_at')[: k * 6]  # widen pool, dedupe later
        )
        examples: List[dict] = []
        seen = set()
        for fb in rows:
            rec = fb.recommendation
            country_lower = (country or '').lower()
            if country_lower:
                ctx_country = (rec.coordinates or {}).get('country') or ''
                # We do not store country directly; rely on sector match plus dedup
            key = (rec.id, fb.section)
            if key in seen:
                continue
            seen.add(key)
            content = (rec.content_json or {}).get(fb.section)
            if not content:
                continue
            examples.append({
                'recommendation_id': str(rec.id),
                'section': fb.section,
                'content': content,
                'area_name': rec.area_name,
                'sector': rec.sector,
            })
            if len(examples) >= k:
                break
        return examples

    @staticmethod
    def load_few_shot_file() -> Dict[str, List[dict]]:
        path = getattr(settings, 'RECOMMENDATION_FEW_SHOT_PATH', '')
        if not path or not os.path.exists(path):
            return {}
        try:
            with open(path, encoding='utf-8') as f:
                return json.load(f) or {}
        except Exception as exc:
            logger.warning("Failed to load few-shot file %s: %s", path, exc)
            return {}

    @staticmethod
    def write_few_shot_file(data: Dict[str, List[dict]]) -> str:
        path = getattr(settings, 'RECOMMENDATION_FEW_SHOT_PATH', '')
        if not path:
            raise RuntimeError("RECOMMENDATION_FEW_SHOT_PATH not configured")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return path

    @staticmethod
    def rebuild_few_shot_index(k_per_group: int = 2) -> Dict[str, List[dict]]:
        """Aggregate all positive feedback grouped by (sector, country) and persist."""
        groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        rows = (
            RecommendationFeedback.objects
            .select_related('recommendation')
            .filter(rating=1)
            .order_by('-created_at')
        )
        seen = set()
        for fb in rows:
            rec = fb.recommendation
            sector = rec.sector or 'unknown'
            country = (rec.coordinates or {}).get('country') or 'Pakistan'
            key = f"{sector}|{country}"
            seen_id = (rec.id, fb.section)
            if seen_id in seen:
                continue
            seen.add(seen_id)
            content = (rec.content_json or {}).get(fb.section)
            if not content:
                continue
            if len(groups[key]) >= k_per_group:
                continue
            groups[key].append({
                'recommendation_id': str(rec.id),
                'section': fb.section,
                'content': content,
                'area_name': rec.area_name,
                'sector': rec.sector,
            })
            RecommendationFeedback.objects.filter(pk=fb.pk).update(used_in_prompt=True)

        FeedbackService.write_few_shot_file(dict(groups))
        return dict(groups)

    @staticmethod
    def get_examples_for(sector: str, country: str = 'Pakistan',
                        max_examples: int = 2) -> List[dict]:
        """Read few-shot file plus top-k from DB; return up to max_examples."""
        data = FeedbackService.load_few_shot_file()
        key = f"{sector}|{country}"
        from_file = data.get(key, []) or []
        from_db = FeedbackService.aggregate_top_examples(sector, country, k=max_examples)
        merged: List[dict] = []
        seen = set()
        for ex in (from_file + from_db):
            sig = (ex.get('recommendation_id'), ex.get('section'))
            if sig in seen:
                continue
            seen.add(sig)
            merged.append(ex)
            if len(merged) >= max_examples:
                break
        return merged
