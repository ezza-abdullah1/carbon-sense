"""
RecommendationAgent — orchestrates the Agentic RAG pipeline with full tracing.

Flow:
  1. Retrieve policies from vector DB  (k=5, strict similarity threshold)
  2. Analyze emissions from database
  3. Build recommendations from templates  (NO LLM required)
  4. Optional: Enhance summary via Gemini  (~150 tokens, graceful fallback)
  5. Format, validate, score confidence

The template builder does 95% of the work.  Gemini only polishes the summary
with minimal tokens so we stay well within free-tier limits (~50 recs/key).
If Gemini is unavailable, the template response is returned as-is.
"""

from recommendations.tools.policy_retriever import PolicyRetriever
from recommendations.tools.emissions_analyzer import EmissionsAnalyzer
from recommendations.tools.response_formatter import ResponseFormatter
from recommendations.tools.web_search import WebSearchFallback
from recommendations.llm_client import GeminiClient
from recommendations.pipeline_tracer import PipelineTracer

# Minimum number of good RAG results before we fall back to web search
MIN_RAG_RESULTS = 2


class RecommendationAgent:
    """Orchestrates the RAG pipeline for emission recommendations."""

    def __init__(self):
        self.policy_retriever = PolicyRetriever()
        self.emissions_analyzer = EmissionsAnalyzer()
        self.formatter = ResponseFormatter()
        self.web_search = WebSearchFallback()
        self.llm = GeminiClient()

    def generate(self, area_id, area_name, sector, coordinates, trace=True):
        """Generate comprehensive emission reduction recommendations.

        Args:
            area_id: The area identifier (e.g., "gulberg_transport").
            area_name: Human-readable area name (e.g., "Gulberg").
            sector: Primary sector (transport/industry/energy/waste/buildings).
            coordinates: Dict with 'lat' and 'lng'.
            trace: Whether to include pipeline trace in the response.

        Returns:
            Dict matching the RecommendationsResponse interface expected
            by the frontend, with an optional 'pipeline_trace' key.
        """
        tracer = PipelineTracer()

        # ── Step 1: Retrieve policies from vector DB ─────────────────────
        with tracer.step(1, "Retrieving relevant policies from vector database") as t:
            query_text = self.policy_retriever._build_query(area_name, sector)
            t.add_data({
                'action': 'vector_search',
                'query': query_text,
                'target_results': 5,
            })

            policy_results = self.policy_retriever.retrieve(
                area_name=area_name,
                sector=sector,
                coordinates=coordinates,
                n_results=5,
            )

            # Web search fallback if RAG results are poor
            used_web_search = False
            if len(policy_results) < MIN_RAG_RESULTS:
                web_results = self.web_search.search(area_name, sector, n_results=5)
                if web_results:
                    policy_results = policy_results + web_results
                    used_web_search = True

            t.add_data({
                'results_count': len(policy_results),
                'used_web_search_fallback': used_web_search,
                'policies_retrieved': [
                    {
                        'title': r['metadata'].get('document_title', 'Unknown'),
                        'country': r['metadata'].get('country', ''),
                        'year': r['metadata'].get('year', ''),
                        'relevance_score': r['score'],
                        'sectors': r['metadata'].get('sectors', ''),
                        'policy_type': r['metadata'].get('policy_type', ''),
                    }
                    for r in policy_results
                ],
            })

        # ── Step 2: Analyze emissions from database ──────────────────────
        with tracer.step(2, "Analyzing emissions data from database") as t:
            t.add_data({
                'action': 'db_query',
                'area_id': area_id,
            })

            emissions_analysis = self.emissions_analyzer.analyze(area_id)

            t.add_data({
                'area_name': emissions_analysis.get('area_name', ''),
                'coordinates': emissions_analysis.get('coordinates', {}),
                'dominant_sector': emissions_analysis.get('dominant_sector', ''),
                'overall_trend': emissions_analysis.get('trend_direction', ''),
                'trend_percent': emissions_analysis.get('trend_percentage', 0),
                'forecast_direction': emissions_analysis.get('forecast_direction', ''),
                'sector_totals': emissions_analysis.get('sector_totals', {}),
                'date_range': {
                    'start': str(emissions_analysis.get('earliest_date', '')),
                    'end': str(emissions_analysis.get('latest_date', '')),
                },
                'historical_records': emissions_analysis.get('historical_count', 0),
                'forecast_records': emissions_analysis.get('forecast_count', 0),
            })

        # ── Step 3: Build recommendations from templates ─────────────────
        with tracer.step(3, "Building recommendations from data templates") as t:
            t.add_data({
                'action': 'template_generation',
                'policy_docs_available': len(policy_results),
                'emissions_data_available': emissions_analysis.get('historical_count', 0) > 0,
            })

            result = self.formatter.build_from_template(
                area_name=area_name,
                area_id=area_id,
                sector=sector,
                coordinates=coordinates,
                policy_results=policy_results,
                emissions_analysis=emissions_analysis,
            )

            t.add_data({
                'sections_generated': {
                    'summary': bool(result.get('recommendations', {}).get('summary')),
                    'immediate_actions': len(result.get('recommendations', {}).get('immediate_actions', [])),
                    'long_term_strategies': len(result.get('recommendations', {}).get('long_term_strategies', [])),
                    'policy_recommendations': len(result.get('recommendations', {}).get('policy_recommendations', [])),
                    'monitoring_metrics': len(result.get('recommendations', {}).get('monitoring_metrics', [])),
                    'risk_factors': len(result.get('recommendations', {}).get('risk_factors', [])),
                },
            })

        # ── Step 4: Optional AI enhancement (summary only, ~150 tokens) ─
        with tracer.step(4, "Enhancing summary via Gemini AI (optional)") as t:
            template_summary = result['recommendations']['summary']
            enhanced = None

            if self.llm.available:
                t.add_data({
                    'action': 'llm_enhance',
                    'model': 'gemini-1.5-flash',
                    'max_tokens': 150,
                    'mode': 'summary_polish_only',
                })

                enhanced = self.llm.enhance_summary(
                    template_summary=template_summary,
                    area_name=area_name,
                    sector=sector,
                )

            if enhanced:
                result['recommendations']['summary'] = enhanced
                t.add_data({
                    'enhanced': True,
                    'enhanced_length': len(enhanced),
                })
            else:
                t.add_data({
                    'enhanced': False,
                    'reason': 'gemini_unavailable' if not self.llm.available else 'fallback_to_template',
                    'using': 'template_summary',
                })

        # ── Step 5: Finalize confidence scores ───────────────────────────
        with tracer.step(5, "Computing confidence scores") as t:
            t.add_data({'action': 'confidence_scoring'})

            t.add_data({
                'confidence': result.get('confidence', {}),
                'ai_enhanced': enhanced is not None,
                'data_sources': {
                    'rag_policies': len([r for r in policy_results if r['metadata'].get('source') != 'web_search']),
                    'web_search': len([r for r in policy_results if r['metadata'].get('source') == 'web_search']),
                    'emissions_records': emissions_analysis.get('historical_count', 0),
                },
                'cached': True,
            })

        # Attach trace to result
        if trace:
            result['pipeline_trace'] = tracer.get_trace()

        return result
