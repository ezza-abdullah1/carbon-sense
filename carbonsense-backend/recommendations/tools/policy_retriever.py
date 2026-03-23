"""
PolicyRetriever — retrieves and re-ranks relevant policy chunks from ChromaDB.
"""

from recommendations.vector_store import VectorStore


SECTOR_KEYWORDS = {
    'transport': 'transportation mobility vehicles transit BRT electric vehicles emissions',
    'industry': 'industrial manufacturing factories pollution emissions standards',
    'energy': 'electricity generation renewable solar wind power grid decarbonization',
    'waste': 'solid waste management landfill recycling methane circular economy',
    'buildings': 'building efficiency insulation green construction energy code HVAC',
}


class PolicyRetriever:
    """Retrieves relevant policy document chunks from the vector store."""

    def __init__(self):
        self.store = VectorStore()

    def retrieve(self, area_name, sector, coordinates, n_results=8):
        """Retrieve and re-rank relevant policy chunks.

        Args:
            area_name: Name of the area (e.g., "Gulberg")
            sector: Primary sector (e.g., "transport")
            coordinates: Dict with 'lat' and 'lng'
            n_results: Number of final results to return after re-ranking.

        Returns:
            List of dicts with keys: text, metadata, score
        """
        # Step 1: Construct semantic query
        query_text = self._build_query(area_name, sector)

        # Step 2: Retrieve candidates from ChromaDB (fetch more than needed for re-ranking)
        fetch_count = min(n_results * 3, 20)

        try:
            results = self.store.query(
                query_text=query_text,
                n_results=fetch_count,
            )
        except Exception:
            # If collection is empty or query fails, return empty
            return []

        if not results or not results['ids'] or not results['ids'][0]:
            return []

        # Step 3: Re-rank candidates
        candidates = []
        for i in range(len(results['ids'][0])):
            candidates.append({
                'id': results['ids'][0][i],
                'text': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'distance': results['distances'][0][i],
            })

        ranked = self._rerank(candidates, sector, area_name)

        # Step 4: Return top N
        return ranked[:n_results]

    def _build_query(self, area_name, sector):
        """Build a semantic search query string."""
        sector_keywords = SECTOR_KEYWORDS.get(sector, '')
        return (
            f"Carbon emission reduction policies and strategies for {sector} sector "
            f"in {area_name}, Lahore, Pakistan. Climate change mitigation measures "
            f"for urban areas in South Asia. {sector_keywords}"
        )

    def _rerank(self, candidates, sector, area_name):
        """Re-rank candidates by geographic, sector, recency, and effectiveness relevance."""
        scored = []

        for item in candidates:
            meta = item['metadata']
            # Base similarity score (convert distance to similarity)
            base_score = max(0, 1.0 - item['distance'])

            # Geographic boost
            geo_boost = 1.0
            city = meta.get('city', '')
            country = meta.get('country', '')
            region = meta.get('region', '')

            if city and 'lahore' in city.lower():
                geo_boost = 1.5
            elif country and country.lower() == 'pakistan':
                geo_boost = 1.3
            elif region and 'south asia' in region.lower():
                geo_boost = 1.15
            elif meta.get('scale') == 'regional' and 'asia' in region.lower():
                geo_boost = 1.1

            # Sector match boost
            sectors_str = meta.get('sectors', '')
            sector_boost = 1.3 if sector in sectors_str else 1.0

            # Recency boost (all docs are 2020+, but newer still preferred)
            year = meta.get('year', 2020)
            if isinstance(year, str):
                try:
                    year = int(year)
                except (ValueError, TypeError):
                    year = 2020
            recency_boost = 1.0 + max(0, (year - 2020)) * 0.05

            # Effectiveness boost
            eff = meta.get('effectiveness_rating', '')
            eff_boost = {'proven': 1.2, 'promising': 1.1, 'theoretical': 1.0}.get(eff, 1.0)

            final_score = base_score * geo_boost * sector_boost * recency_boost * eff_boost

            scored.append({
                'text': item['text'],
                'metadata': meta,
                'score': round(final_score, 4),
            })

        scored.sort(key=lambda x: x['score'], reverse=True)
        return scored

    def format_for_prompt(self, results):
        """Format retrieved policy chunks into a text block for the LLM prompt.

        Args:
            results: List of dicts from retrieve().

        Returns:
            Formatted string with numbered policy excerpts and source info.
        """
        if not results:
            return "No relevant policy documents found in the knowledge base. Provide recommendations based on your general knowledge of climate policy best practices."

        parts = []
        for i, item in enumerate(results, 1):
            meta = item['metadata']
            title = meta.get('document_title', 'Unknown Document')
            country = meta.get('country', 'Unknown')
            year = meta.get('year', 'Unknown')
            org = meta.get('source_organization', 'Unknown')
            policy_type = meta.get('policy_type', '')
            scale = meta.get('scale', '')

            header = f"[{i}] {title} ({year}, {country}, {org})"
            if policy_type:
                header += f" [{policy_type}, {scale}]"

            parts.append(f"{header}\n{item['text']}\n")

        return "\n---\n".join(parts)
