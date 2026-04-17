"""
RecommendationAgent — generates actionable emission reduction recommendations
using Groq (Llama 3.3 70B) with real UC-level emission data.

Flow:
  1. Fetch UC emission data from JSON files (transport, buildings, waste)
  2. Build a structured prompt with the actual data + area context
  3. Send to Groq (Llama 3.3 70B) for generation
  4. Parse response into the expected format
  5. Fall back to templates if LLM is unavailable

Uses the cheapest Gemini model (2.0 Flash) to minimize token usage.
"""

import json
import logging
from datetime import datetime

from recommendations.llm_client import GeminiClient
from recommendations.tools.response_formatter import ResponseFormatter
from recommendations.pipeline_tracer import PipelineTracer

logger = logging.getLogger(__name__)


def _load_uc_data(area_name, sector, coordinates):
    """Load real UC emission data from JSON files for the given area."""
    import os
    from django.conf import settings

    data_dir = os.path.join(settings.BASE_DIR, 'data')
    uc_data = {
        'area_name': area_name,
        'sector': sector,
        'coordinates': coordinates,
    }

    def _safe(val, default=0.0):
        if val is None:
            return default
        if isinstance(val, float) and (val != val or val == float('inf')):
            return default
        return val

    # Match by area_name (case-insensitive)
    name_lower = area_name.lower().strip()

    # Transport
    try:
        with open(os.path.join(data_dir, 'carbonsense_transport_v16.json'), encoding='utf-8') as f:
            t = json.load(f)
        for uc in t.get('uc_emissions', []):
            if uc.get('uc_name', '').lower().strip() == name_lower:
                fc = uc.get('forecast', {})
                hist = uc.get('historical', {})
                uc_data['transport'] = {
                    'uc_code': uc.get('uc_code', ''),
                    'area_km2': _safe(uc.get('area_km2')),
                    'forecast_annual_t': _safe(fc.get('annual_t')),
                    'road_annual_t': _safe(fc.get('road_annual_t')),
                    'dom_avi_annual_t': _safe(fc.get('dom_avi_annual_t')),
                    'intl_avi_annual_t': _safe(fc.get('intl_avi_annual_t')),
                    'rail_annual_t': _safe(fc.get('rail_annual_t')),
                    'road_pct': _safe(fc.get('road_pct')),
                    'intensity_t_per_km2': _safe(fc.get('intensity_t_per_km2')),
                    'rank_in_division': fc.get('rank_in_division', 0),
                    'historical_total_t': _safe(hist.get('total_t')),
                    'historical_period': hist.get('period', ''),
                    'dominant_source': uc.get('dominant_source', ''),
                    'risk_flags': uc.get('risk_flags', []),
                }
                break
    except Exception as e:
        logger.warning(f"Could not load transport data: {e}")

    # Buildings
    try:
        with open(os.path.join(data_dir, 'carbonsense_buildings_v15.json'), encoding='utf-8') as f:
            b = json.load(f)
        for uc in b.get('uc_data', []):
            if uc.get('uc_name', '').lower().strip() == name_lower:
                ae = uc.get('annual_emissions', {})
                risk = uc.get('risk', {})
                uc_data['buildings'] = {
                    'uc_code': uc.get('uc_code', ''),
                    'forecast_total_t': _safe(ae.get('total_t')),
                    'residential_t': _safe(ae.get('residential_t')),
                    'non_residential_t': _safe(ae.get('non_residential_t')),
                    'intensity_t_km2': _safe(ae.get('intensity_t_km2')),
                    'rank_in_district': ae.get('rank_in_district', 0),
                    'risk_flags': [k for k, v in risk.items() if v is True],
                }
                break
    except Exception as e:
        logger.warning(f"Could not load buildings data: {e}")

    # Waste
    try:
        with open(os.path.join(data_dir, 'carbonsense_per_location_waste_v2_3.json'), encoding='utf-8') as f:
            w = json.load(f)
        for uc in w.get('aggregate_forecast', {}).get('uc_allocation', []):
            if uc.get('uc_name', '').lower().strip() == name_lower:
                em = uc.get('emissions', {})
                uc_data['waste'] = {
                    'uc_code': uc.get('uc_code', ''),
                    'forecast_annual_t': _safe(em.get('total_annual_t')),
                    'point_source_t': _safe(em.get('point_source_t')),
                    'area_sw_t': _safe(em.get('area_sw_t')),
                    'area_ww_t': _safe(em.get('area_ww_t')),
                    'point_pct': _safe(em.get('point_pct')),
                    'risk_level': em.get('risk_level', ''),
                }
                break
    except Exception as e:
        logger.warning(f"Could not load waste data: {e}")

    return uc_data


def _build_gemini_prompt(uc_data, sector):
    """Build a structured prompt for Gemini with real emission data."""
    area = uc_data.get('area_name', 'Unknown')
    coords = uc_data.get('coordinates', {})

    # Build data summary
    data_lines = [
        f"Union Council: {area}",
        f"Location: Lahore District, Punjab, Pakistan ({coords.get('lat', '')}, {coords.get('lng', '')})",
        f"Primary sector for analysis: {sector}",
        "",
    ]

    t = uc_data.get('transport')
    if t:
        data_lines += [
            "--- TRANSPORT EMISSIONS ---",
            f"Forecast annual: {t['forecast_annual_t']:,.0f} tonnes CO2e",
            f"  Road: {t['road_annual_t']:,.0f} t ({t['road_pct']:.1f}%)",
            f"  Dom. Aviation: {t['dom_avi_annual_t']:,.0f} t",
            f"  Intl. Aviation: {t['intl_avi_annual_t']:,.0f} t",
            f"  Railways: {t['rail_annual_t']:,.0f} t",
            f"Intensity: {t['intensity_t_per_km2']:,.0f} t/km2",
            f"District rank: #{t['rank_in_division']}/151",
            f"Historical total ({t['historical_period']}): {t['historical_total_t']:,.0f} t",
            f"Dominant source: {t['dominant_source']}",
            f"Risk flags: {', '.join(t['risk_flags']) if t['risk_flags'] else 'none'}",
            "",
        ]

    b = uc_data.get('buildings')
    if b:
        data_lines += [
            "--- BUILDINGS EMISSIONS ---",
            f"Forecast annual: {b['forecast_total_t']:,.0f} tonnes CO2e",
            f"  Residential: {b['residential_t']:,.0f} t",
            f"  Non-residential: {b['non_residential_t']:,.0f} t",
            f"Intensity: {b['intensity_t_km2']:,.0f} t/km2",
            f"District rank: #{b['rank_in_district']}/151",
            f"Risk flags: {', '.join(b['risk_flags']) if b['risk_flags'] else 'none'}",
            "",
        ]

    w = uc_data.get('waste')
    if w:
        data_lines += [
            "--- WASTE EMISSIONS ---",
            f"Forecast annual: {w['forecast_annual_t']:,.0f} tonnes CO2e",
            f"  Point sources: {w['point_source_t']:,.0f} t ({w['point_pct']:.1f}%)",
            f"  Solid waste: {w['area_sw_t']:,.0f} t",
            f"  Wastewater: {w['area_ww_t']:,.0f} t",
            f"Risk level: {w['risk_level']}",
            "",
        ]

    data_block = "\n".join(data_lines)

    prompt = f"""You are an expert climate policy advisor for Pakistan's urban areas. Based on the following REAL emission data for {area} Union Council in Lahore, generate actionable recommendations for government officials and policymakers.

{data_block}

Generate a JSON response with EXACTLY this structure:
{{
  "summary": "A 3-4 sentence executive summary of the emission situation and key priorities for this UC",
  "immediate_actions": [
    "4-5 specific, implementable actions with **Bold Title** - [Expected Impact]: X% reduction - [Estimated Cost Range]: PKR X Million - [Implementation Priority]: High/Medium/Low"
  ],
  "long_term_strategies": [
    "3-4 strategies with **Bold Title** - [Timeline]: X years - [Expected Reduction]: X% - [Key Milestones]: Year 1: ... Year 2: ..."
  ],
  "policy_recommendations": [
    "3-4 policy recommendations referencing real Pakistan/Punjab regulations such as: Punjab Environmental Protection Act 1997, Pakistan Climate Change Act 2017, National Electric Vehicle Policy 2019, Punjab Clean Air Action Plan, PEPA Motor Vehicle Emission Standards, National Energy Efficiency & Conservation Act 2016, Pakistan NDC commitments under Paris Agreement. Each should cite the specific regulation."
  ],
  "monitoring_metrics": [
    "3-4 specific measurable metrics relevant to {area} with description of how to track them"
  ],
  "risk_factors": [
    "3-4 risks specific to implementing these recommendations in {area}, Lahore"
  ]
}}

IMPORTANT RULES:
- Focus on the {sector} sector primarily but consider cross-sector impacts
- All cost estimates should be in PKR (Pakistani Rupees)
- Reference REAL Pakistani/Punjab policies and regulations, not generic ones
- Make recommendations specific to {area}'s emission profile (rank, intensity, risk flags)
- Return ONLY valid JSON, no markdown code fences or explanations"""

    return prompt


class RecommendationAgent:
    """Generates recommendations using Gemini with real UC emission data."""

    def __init__(self):
        self.llm = GeminiClient()
        self.formatter = ResponseFormatter()

    def generate(self, area_id, area_name, sector, coordinates, trace=True):
        tracer = PipelineTracer()

        # ── Step 1: Load real UC emission data ──────────────────────────
        with tracer.step(1, "Loading UC emission data from JSON files") as t:
            uc_data = _load_uc_data(area_name, sector, coordinates)
            t.add_data({
                'has_transport': 'transport' in uc_data,
                'has_buildings': 'buildings' in uc_data,
                'has_waste': 'waste' in uc_data,
            })

        # ── Step 2: Generate via Gemini ─────────────────────────────────
        with tracer.step(2, "Generating recommendations via Gemini") as t:
            gemini_result = None

            if self.llm.available:
                prompt = _build_gemini_prompt(uc_data, sector)
                t.add_data({
                    'model': 'llama-3.3-70b-versatile',
                    'prompt_length': len(prompt),
                })

                try:
                    raw_text = self.llm.generate(
                        system_prompt=(
                            "You are a climate policy expert specializing in "
                            "Pakistan's urban emission reduction strategies. "
                            "Always respond with valid JSON only."
                        ),
                        user_prompt=prompt,
                    )

                    # Parse the JSON response
                    cleaned = raw_text.strip()
                    if cleaned.startswith('```'):
                        cleaned = cleaned.split('\n', 1)[-1]
                        cleaned = cleaned.rsplit('```', 1)[0]

                    gemini_result = json.loads(cleaned)
                    t.add_data({'status': 'success'})

                except json.JSONDecodeError as e:
                    logger.warning(f"Gemini returned invalid JSON: {e}")
                    t.add_data({'status': 'json_parse_error', 'error': str(e)})
                except Exception as e:
                    logger.warning(f"Gemini generation failed: {e}")
                    t.add_data({'status': 'error', 'error': str(e)})
            else:
                t.add_data({'status': 'gemini_unavailable'})

        # ── Step 3: Build final response ────────────────────────────────
        with tracer.step(3, "Formatting final response") as t:
            if gemini_result:
                # Use Gemini's response
                recommendations = {
                    'summary': gemini_result.get('summary', ''),
                    'immediate_actions': gemini_result.get('immediate_actions', []),
                    'long_term_strategies': gemini_result.get('long_term_strategies', []),
                    'policy_recommendations': gemini_result.get('policy_recommendations', []),
                    'monitoring_metrics': gemini_result.get('monitoring_metrics', []),
                    'risk_factors': gemini_result.get('risk_factors', []),
                }
                t.add_data({'source': 'gemini'})
            else:
                # No fallback — raise error so we know Gemini failed
                raise RuntimeError("Gemini generation failed — no fallback enabled for testing")

        # ── Assemble response ───────────────────────────────────────────
        result = {
            'success': True,
            'query': {
                'area_name': area_name,
                'area_id': area_id,
                'sector': sector,
                'coordinates': coordinates,
            },
            'recommendations': recommendations,
            'confidence': {
                'overall': 0.85 if gemini_result else 0.6,
                'evidence_strength': 0.9,
                'data_completeness': min(1.0, sum([
                    0.4 if 'transport' in uc_data else 0,
                    0.3 if 'buildings' in uc_data else 0,
                    0.3 if 'waste' in uc_data else 0,
                ])),
                'geographic_relevance': 0.95,
            },
            'raw_response': json.dumps(gemini_result) if gemini_result else '',
            'generated_at': datetime.now().isoformat(),
        }

        if trace:
            result['pipeline_trace'] = tracer.get_trace()

        return result
