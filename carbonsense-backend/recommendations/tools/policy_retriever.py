"""
PolicyRetriever — retrieves and re-ranks relevant policy chunks from ChromaDB.

The retriever is now driven by a place_context dict (built by
recommendations.tools.emission_context.build_place_context). The context
shapes both the semantic query and the ChromaDB metadata `where` filter so
two different UCs receive materially different policy citations.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import chromadb
from django.conf import settings

from recommendations.vector_store import VectorStore
from recommendations.tools.emission_context import context_keywords


SECTOR_KEYWORDS = {
    'transport': 'transportation mobility vehicles transit BRT electric vehicles emissions',
    'industry': 'industrial manufacturing factories pollution emissions standards',
    'energy': 'electricity generation renewable solar wind power grid decarbonization',
    'waste': 'solid waste management landfill recycling methane circular economy',
    'buildings': 'building efficiency insulation green construction energy code HVAC',
}


MIN_SIMILARITY_SCORE = 0.25  # Loosened slightly because we're now metadata-filtering pre-rank


class PolicyRetriever:
    """Retrieves policy document chunks tightly conditioned on a place context."""

    def __init__(self, collection_name: Optional[str] = None):
        self.store = VectorStore()
        self._collection_name = collection_name  # None = default policy_documents

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def retrieve(self, place_context: Dict[str, Any], n_results: int = 5) -> List[dict]:
        """Retrieve and re-rank policies relevant to this place context."""
        query_text = self._build_query(place_context)
        where = self._build_where_filter(place_context)

        fetch_count = min(n_results * 4, 20)
        try:
            results = self._query(query_text, fetch_count, where=where)
        except Exception:
            return []

        if not results or not results.get('ids') or not results['ids'][0]:
            # Retry without the where filter — collection may be sparse
            try:
                results = self._query(query_text, fetch_count, where=None)
            except Exception:
                return []
            if not results or not results.get('ids') or not results['ids'][0]:
                return []

        candidates = self._materialize(results)
        ranked = self._rerank(candidates, place_context)
        ranked = [r for r in ranked if r['score'] >= MIN_SIMILARITY_SCORE]
        return ranked[:n_results]

    def format_for_prompt(self, results: List[dict]) -> str:
        """Format retrieved policy chunks into a compact text block for the LLM."""
        if not results:
            return (
                "No relevant policy documents found. Provide recommendations "
                "based on general climate policy best practices for Pakistan."
            )

        parts = []
        for i, item in enumerate(results, 1):
            meta = item['metadata']
            title = meta.get('document_title', 'Unknown')
            country = meta.get('country', '')
            year = meta.get('year', '')
            policy_type = meta.get('policy_type', '')

            text_snippet = (item['text'] or '')[:240].strip()
            last_period = text_snippet.rfind('.')
            if last_period > 80:
                text_snippet = text_snippet[:last_period + 1]

            parts.append(
                f"[{i}] {title} ({year}, {country}, {policy_type}): {text_snippet}"
            )

        return "\n".join(parts)

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    def _build_query(self, ctx: Dict[str, Any]) -> str:
        sector = ctx.get('sector') or ''
        sector_keywords = SECTOR_KEYWORDS.get(sector, '')
        ctx_kw = context_keywords(ctx)
        area = ctx.get('area_name') or ''
        return (
            f"Carbon emission reduction policies and case studies for {sector} sector "
            f"in {area}, Lahore, Pakistan. {ctx_kw}. Climate change mitigation in "
            f"South Asian urban areas. {sector_keywords}"
        )

    def _build_where_filter(self, ctx: Dict[str, Any]) -> Optional[dict]:
        """Restrict to chunks whose metadata mentions the place's geo bucket
        OR whose scale is national/international (so we don't over-localize)."""
        country = (ctx.get('country') or 'Pakistan').strip()
        region = (ctx.get('region') or 'South Asia').strip()
        clauses = [
            {'country': {'$eq': country}},
            {'region': {'$eq': region}},
            {'scale': {'$eq': 'international'}},
            {'scale': {'$eq': 'national'}},
        ]
        return {'$or': clauses}

    def _query(self, query_text: str, n_results: int, where: Optional[dict]):
        if self._collection_name and self._collection_name != 'policy_documents':
            client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
            try:
                collection = client.get_collection(name=self._collection_name)
            except Exception:
                return None
            kwargs = {'query_texts': [query_text], 'n_results': n_results}
            if where:
                kwargs['where'] = where
            return collection.query(**kwargs)
        return self.store.query(query_text=query_text, n_results=n_results, where=where)

    def _materialize(self, results) -> List[dict]:
        out = []
        for i in range(len(results['ids'][0])):
            out.append({
                'id': results['ids'][0][i],
                'text': results['documents'][0][i],
                'metadata': results['metadatas'][0][i] or {},
                'distance': results['distances'][0][i],
            })
        return out

    def _rerank(self, candidates: List[dict], ctx: Dict[str, Any]) -> List[dict]:
        sector = (ctx.get('sector') or '').lower()
        country = (ctx.get('country') or '').lower()
        region = (ctx.get('region') or '').lower()
        city = (ctx.get('city') or '').lower()

        scored = []
        for item in candidates:
            meta = item['metadata']
            base_score = max(0.0, 1.0 - float(item.get('distance') or 1.0))

            # Geographic boost
            geo_boost = 1.0
            mcity = (meta.get('city') or '').lower()
            mcountry = (meta.get('country') or '').lower()
            mregion = (meta.get('region') or '').lower()
            if city and city in mcity:
                geo_boost = 1.5
            elif country and country == mcountry:
                geo_boost = 1.3
            elif region and region in mregion:
                geo_boost = 1.15

            # Sector match boost
            sectors_str = str(meta.get('sectors', '') or '')
            sector_boost = 1.3 if sector and sector in sectors_str.lower() else 1.0

            # Recency boost (2020+)
            year = meta.get('year', 2020)
            try:
                year_int = int(year)
            except (TypeError, ValueError):
                year_int = 2020
            recency_boost = 1.0 + max(0, (year_int - 2020)) * 0.05

            # Effectiveness boost
            eff = (meta.get('effectiveness_rating') or '').lower()
            eff_boost = {'proven': 1.2, 'promising': 1.1, 'theoretical': 1.0}.get(eff, 1.0)

            final_score = base_score * geo_boost * sector_boost * recency_boost * eff_boost
            scored.append({
                'text': item['text'],
                'metadata': meta,
                'score': round(final_score, 4),
            })

        scored.sort(key=lambda x: x['score'], reverse=True)
        return scored


class NewsRetriever(PolicyRetriever):
    """Retrieves recent news/articles from the `recent_news` ChromaDB collection."""

    def __init__(self):
        super().__init__(
            collection_name=getattr(settings, 'RECOMMENDATION_RECENT_NEWS_COLLECTION', 'recent_news')
        )
