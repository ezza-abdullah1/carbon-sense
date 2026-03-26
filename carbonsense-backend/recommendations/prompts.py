"""
Prompt templates for the Recommendation Agent.

The output format must match what the frontend parser expects in
recommendations-modal.tsx (parseActionString and parseStrategyString).
"""

SYSTEM_PROMPT = """Environmental policy advisor for Lahore, Pakistan. Respond with ONLY valid JSON:
{"summary":"1-2 paragraph analysis","immediate_actions":["**Title** - [Expected Impact]: desc - [Estimated Cost Range]: PKR - [Implementation Priority]: High/Medium/Low"],"long_term_strategies":["**Title** - [Timeline]: X-Y years - [Expected Reduction]: % - [Key Milestones]: Year 1: x. Year 2: y."],"policy_recommendations":["**Name**: description"],"monitoring_metrics":["**Name**: description"],"risk_factors":["**Name**: description and mitigation"]}
Rules: 3-4 items per category. Costs in PKR. Use CO2e. Cite policy docs by name. Be specific to the area and sector."""


USER_PROMPT_TEMPLATE = """Area: {area_name}, Lahore Pakistan ({lat},{lng}) | Sector: {sector}

EMISSIONS:
{emissions_context}

POLICIES (from RAG knowledge base):
{policy_context}

Generate recommendations for {area_name} ({sector} sector). Ground in the policies above. Include quick wins (0-6mo) and long-term (1-5yr). Be specific to Lahore, Pakistan context."""


def build_prompt(area_name, sector, coordinates, policy_context_text, emissions_context_text):
    """Build the complete user prompt for the LLM.

    Args:
        area_name: Name of the area (e.g., "Gulberg")
        sector: Primary sector (e.g., "transport")
        coordinates: Dict with 'lat' and 'lng'
        policy_context_text: Formatted string of retrieved policy chunks
        emissions_context_text: Formatted string of emissions analysis

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    user_prompt = USER_PROMPT_TEMPLATE.format(
        area_name=area_name,
        lat=coordinates['lat'],
        lng=coordinates['lng'],
        sector=sector,
        emissions_context=emissions_context_text,
        policy_context=policy_context_text,
    )

    return SYSTEM_PROMPT, user_prompt
