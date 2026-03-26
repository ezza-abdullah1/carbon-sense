"""
Lightweight web search fallback — used when RAG returns poor results.

Does a single DuckDuckGo news search and returns results formatted
like PolicyRetriever output so the rest of the pipeline works unchanged.
"""

import logging

from ddgs import DDGS

logger = logging.getLogger(__name__)


class WebSearchFallback:
    """Quick DuckDuckGo search for policy context when vector DB has no good matches."""

    def search(self, area_name, sector, n_results=5):
        """Search web for relevant climate policy articles.

        Args:
            area_name: Name of the area (e.g., "Gulberg").
            sector: Primary sector (e.g., "transport").
            n_results: Max results to return.

        Returns:
            List of dicts with keys: text, metadata, score
            (same shape as PolicyRetriever.retrieve() output).
        """
        query = (
            f"{area_name} Lahore Pakistan {sector} carbon emission "
            f"reduction policy 2024 2025"
        )

        try:
            raw = DDGS().news(query, max_results=n_results, timelimit='y')
            results = list(raw) if raw else []
        except Exception as e:
            logger.warning(f"Web search fallback failed: {e}")
            return []

        formatted = []
        for r in results:
            title = r.get('title', '').strip()
            body = r.get('body', '').strip()
            if not title or not body:
                continue

            formatted.append({
                'text': f"{title}. {body}",
                'metadata': {
                    'document_title': title[:120],
                    'country': 'Pakistan',
                    'year': '2025',
                    'source': 'web_search',
                    'policy_type': 'news_article',
                    'sectors': sector,
                    'city': '',
                },
                'score': 0.5,
            })

        return formatted[:n_results]
