"""
Web search tool — fetches current 2026-relevant references for the agent.

Tavily is the recommended provider (free 1000 calls/month, clean
LLM-friendly summaries). DuckDuckGo is the no-key fallback.

The output shape matches PolicyRetriever.retrieve() so the synthesizer
prompt builder treats both sources uniformly.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from django.conf import settings

logger = logging.getLogger(__name__)


class WebSearch:
    """Tavily-first web search with DuckDuckGo fallback."""

    def __init__(self):
        self._provider = (getattr(settings, 'WEB_SEARCH_PROVIDER', 'tavily') or 'tavily').lower()
        self._tavily = self._init_tavily()

    def _init_tavily(self):
        api_key = getattr(settings, 'TAVILY_API_KEY', '') or ''
        if not api_key or api_key.startswith('your-'):
            return None
        try:
            from tavily import TavilyClient
            return TavilyClient(api_key=api_key)
        except ImportError:
            logger.warning("tavily-python not installed; falling back to DDG")
            return None
        except Exception as exc:
            logger.warning("Tavily init failed: %s", exc)
            return None

    @property
    def available(self) -> bool:
        return self._tavily is not None or self._provider != 'tavily'

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def search(self, query: str, *, max_results: int = 4,
               days: int = 180) -> List[Dict[str, Any]]:
        """Run a search and return up to `max_results` formatted hits."""
        if self._provider == 'tavily' and self._tavily is not None:
            results = self._tavily_search(query, max_results=max_results, days=days)
            if results:
                return results
            logger.info("Tavily returned no results, falling back to DDG")
        return self._ddg_search(query, max_results=max_results)

    def search_for_context(self, place_context: Dict[str, Any], *,
                           max_results: int = 4) -> List[Dict[str, Any]]:
        """Convenience wrapper that builds a query from the place context."""
        sector = place_context.get('sector') or ''
        area = place_context.get('area_name') or ''
        risks = ' '.join(place_context.get('risk_flags') or [])
        query = (
            f"{area} Lahore Pakistan {sector} carbon emission reduction "
            f"policy 2025 2026 {risks}"
        ).strip()
        return self.search(query, max_results=max_results, days=365)

    # ------------------------------------------------------------------ #
    # Backends
    # ------------------------------------------------------------------ #

    def _tavily_search(self, query: str, *, max_results: int, days: int) -> List[Dict[str, Any]]:
        try:
            response = self._tavily.search(
                query=query,
                search_depth='basic',
                topic='news',
                days=max(1, min(days, 365)),
                max_results=max_results,
                include_answer=False,
            )
        except Exception as exc:
            logger.warning("Tavily search failed: %s", exc)
            return []

        formatted: List[Dict[str, Any]] = []
        for r in (response.get('results') or [])[:max_results]:
            title = (r.get('title') or '').strip()
            content = (r.get('content') or '').strip()
            url = (r.get('url') or '').strip()
            if not title or not content:
                continue
            formatted.append({
                'text': f"{title}. {content}",
                'metadata': {
                    'document_title': title[:160],
                    'country': '',
                    'year': str(_extract_year(r.get('published_date') or '') or 2026),
                    'source': 'tavily',
                    'source_url': url,
                    'policy_type': 'news_article',
                    'sectors': '',
                    'city': '',
                },
                'score': float(r.get('score') or 0.5),
            })
        return formatted

    def _ddg_search(self, query: str, *, max_results: int) -> List[Dict[str, Any]]:
        try:
            from ddgs import DDGS
        except ImportError:
            logger.warning("ddgs not installed; web search unavailable")
            return []
        try:
            raw = DDGS().news(query, max_results=max_results, timelimit='y')
            results = list(raw) if raw else []
        except Exception as exc:
            logger.warning("DDG search failed: %s", exc)
            return []

        formatted: List[Dict[str, Any]] = []
        for r in results[:max_results]:
            title = (r.get('title') or '').strip()
            body = (r.get('body') or '').strip()
            url = (r.get('url') or '').strip()
            if not title or not body:
                continue
            formatted.append({
                'text': f"{title}. {body}",
                'metadata': {
                    'document_title': title[:160],
                    'country': '',
                    'year': str(_extract_year(r.get('date') or '') or 2025),
                    'source': 'ddg',
                    'source_url': url,
                    'policy_type': 'news_article',
                    'sectors': '',
                    'city': '',
                },
                'score': 0.5,
            })
        return formatted


def _extract_year(value: str) -> Optional[int]:
    if not value:
        return None
    for token in str(value).split('-'):
        if token.isdigit() and 2020 <= int(token) <= 2030:
            return int(token)
    return None


# Backwards-compatible alias
class WebSearchFallback(WebSearch):
    """Deprecated alias kept for older imports."""

    def search(self, area_name: str = '', sector: str = '', n_results: int = 5,
               *, max_results: Optional[int] = None, days: int = 180):
        if not area_name and not sector:
            return super().search('', max_results=max_results or n_results, days=days)
        query = f"{area_name} Lahore Pakistan {sector} carbon emission reduction policy 2025 2026"
        return super().search(query, max_results=max_results or n_results, days=days)
