"""
RecommendationAgent — orchestrates the Agentic RAG pipeline with full tracing.

Flow: Retrieve policies → Analyze emissions → Build prompt → Call LLM → Format response

Each step is traced with timing, input/output data, and status so the frontend
can display a real-time pipeline visualization.
"""

from recommendations.tools.policy_retriever import PolicyRetriever
from recommendations.tools.emissions_analyzer import EmissionsAnalyzer
from recommendations.tools.response_formatter import ResponseFormatter
from recommendations.llm_client import GeminiClient
from recommendations.prompts import build_prompt
from recommendations.pipeline_tracer import PipelineTracer


class RecommendationAgent:
    """Orchestrates the RAG pipeline for emission recommendations."""

    def __init__(self):
        self.policy_retriever = PolicyRetriever()
        self.emissions_analyzer = EmissionsAnalyzer()
        self.llm = GeminiClient()
        self.formatter = ResponseFormatter()

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
                'target_results': 8,
            })

            policy_results = self.policy_retriever.retrieve(
                area_name=area_name,
                sector=sector,
                coordinates=coordinates,
                n_results=8,
            )

            t.add_data({
                'results_count': len(policy_results),
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

        policy_context_text = self.policy_retriever.format_for_prompt(policy_results)

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
                'overall_trend': emissions_analysis.get('overall_trend', ''),
                'trend_percent': emissions_analysis.get('trend_percent', 0),
                'forecast_direction': emissions_analysis.get('forecast_direction', ''),
                'sector_totals': emissions_analysis.get('sector_totals', {}),
                'date_range': {
                    'start': str(emissions_analysis.get('date_range_start', '')),
                    'end': str(emissions_analysis.get('date_range_end', '')),
                },
                'historical_records': emissions_analysis.get('historical_count', 0),
                'forecast_records': emissions_analysis.get('forecast_count', 0),
            })

        emissions_context_text = self.emissions_analyzer.format_for_prompt(emissions_analysis)

        # ── Step 3: Build prompts ────────────────────────────────────────
        with tracer.step(3, "Building LLM prompts with context") as t:
            system_prompt, user_prompt = build_prompt(
                area_name=area_name,
                sector=sector,
                coordinates=coordinates,
                policy_context_text=policy_context_text,
                emissions_context_text=emissions_context_text,
            )

            t.add_data({
                'action': 'prompt_construction',
                'system_prompt_length': len(system_prompt),
                'user_prompt_length': len(user_prompt),
                'total_tokens_estimate': (len(system_prompt) + len(user_prompt)) // 4,
                'policy_docs_in_context': len(policy_results),
                'prompt_preview': user_prompt[:500] + '...',
            })

        # ── Step 4: Call Gemini LLM ──────────────────────────────────────
        with tracer.step(4, "Generating recommendations via Gemini AI") as t:
            t.add_data({
                'action': 'llm_call',
                'model': 'gemini-2.0-flash',
                'temperature': 0.7,
                'max_tokens': 4096,
            })

            raw_response = self.llm.generate(system_prompt, user_prompt)

            t.add_data({
                'response_length': len(raw_response),
                'response_preview': raw_response[:300] + '...',
            })

        # ── Step 5: Format, validate, score confidence ───────────────────
        with tracer.step(5, "Formatting response and computing confidence scores") as t:
            t.add_data({'action': 'format_and_validate'})

            result = self.formatter.format(
                raw_response=raw_response,
                area_name=area_name,
                area_id=area_id,
                sector=sector,
                coordinates=coordinates,
                policy_results=policy_results,
                emissions_analysis=emissions_analysis,
            )

            t.add_data({
                'confidence': result.get('confidence', {}),
                'sections_generated': {
                    'summary': bool(result.get('recommendations', {}).get('summary')),
                    'immediate_actions': len(result.get('recommendations', {}).get('immediate_actions', [])),
                    'long_term_strategies': len(result.get('recommendations', {}).get('long_term_strategies', [])),
                    'policy_recommendations': len(result.get('recommendations', {}).get('policy_recommendations', [])),
                    'monitoring_metrics': len(result.get('recommendations', {}).get('monitoring_metrics', [])),
                    'risk_factors': len(result.get('recommendations', {}).get('risk_factors', [])),
                },
                'cached': True,
            })

        # Attach trace to result
        if trace:
            result['pipeline_trace'] = tracer.get_trace()

        return result
