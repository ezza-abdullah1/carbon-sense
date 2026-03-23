"""
RecommendationAgent — orchestrates the Agentic RAG pipeline.

Flow: Retrieve policies → Analyze emissions → Build prompt → Call LLM → Format response
"""

from recommendations.tools.policy_retriever import PolicyRetriever
from recommendations.tools.emissions_analyzer import EmissionsAnalyzer
from recommendations.tools.response_formatter import ResponseFormatter
from recommendations.llm_client import GeminiClient
from recommendations.prompts import build_prompt


class RecommendationAgent:
    """Orchestrates the RAG pipeline for emission recommendations."""

    def __init__(self):
        self.policy_retriever = PolicyRetriever()
        self.emissions_analyzer = EmissionsAnalyzer()
        self.llm = GeminiClient()
        self.formatter = ResponseFormatter()

    def generate(self, area_id, area_name, sector, coordinates):
        """Generate comprehensive emission reduction recommendations.

        Args:
            area_id: The area identifier (e.g., "gulberg_transport").
            area_name: Human-readable area name (e.g., "Gulberg").
            sector: Primary sector (transport/industry/energy/waste/buildings).
            coordinates: Dict with 'lat' and 'lng'.

        Returns:
            Dict matching the RecommendationsResponse interface expected
            by the frontend.
        """
        # Step 1: Retrieve relevant policy documents from vector store
        policy_results = self.policy_retriever.retrieve(
            area_name=area_name,
            sector=sector,
            coordinates=coordinates,
            n_results=8,
        )
        policy_context_text = self.policy_retriever.format_for_prompt(policy_results)

        # Step 2: Analyze emissions data from Django DB
        emissions_analysis = self.emissions_analyzer.analyze(area_id)
        emissions_context_text = self.emissions_analyzer.format_for_prompt(emissions_analysis)

        # Step 3: Build prompts and call the LLM
        system_prompt, user_prompt = build_prompt(
            area_name=area_name,
            sector=sector,
            coordinates=coordinates,
            policy_context_text=policy_context_text,
            emissions_context_text=emissions_context_text,
        )

        raw_response = self.llm.generate(system_prompt, user_prompt)

        # Step 4: Validate, format, compute confidence, and cache
        result = self.formatter.format(
            raw_response=raw_response,
            area_name=area_name,
            area_id=area_id,
            sector=sector,
            coordinates=coordinates,
            policy_results=policy_results,
            emissions_analysis=emissions_analysis,
        )

        return result
