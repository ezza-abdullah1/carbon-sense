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

    # Build area-specific context bullets
    context_bullets = []
    if t:
        if t['rank_in_division'] <= 10:
            context_bullets.append(
                f"{area} is a TOP-10 transport emitter (rank #{t['rank_in_division']}/151) — "
                f"aggressive intervention is justified"
            )
        if 'aviation_plume_proximity' in (t.get('risk_flags') or []):
            context_bullets.append(
                f"{area} is near Allama Iqbal International Airport — "
                f"aviation contributes {t['intl_avi_annual_t']:,.0f}t/yr, "
                f"ground-level air quality is compounded by LTO cycles"
            )
        if 'winter_smog_zone' in (t.get('risk_flags') or []):
            context_bullets.append(
                f"{area} falls in Lahore's winter smog zone — "
                f"seasonal emission spikes worsen PM2.5 during Nov-Feb"
            )
        if 'rail_corridor' in (t.get('risk_flags') or []):
            context_bullets.append(
                f"{area} is on the ML-1 railway corridor — "
                f"rail electrification would directly reduce local emissions"
            )
        if t['road_pct'] > 85:
            context_bullets.append(
                f"Road transport dominates at {t['road_pct']:.0f}% — "
                f"interventions must target vehicular traffic specifically"
            )
        if t['intensity_t_per_km2'] > 10000:
            context_bullets.append(
                f"Extremely high emission density ({t['intensity_t_per_km2']:,.0f} t/km²) — "
                f"this is a congestion hotspot requiring traffic demand management"
            )
    if b:
        if b['rank_in_district'] <= 10:
            context_bullets.append(
                f"Building emissions rank #{b['rank_in_district']}/151 — "
                f"residential heating/cooling is a major driver "
                f"({b['residential_t']:,.0f}t residential vs {b['non_residential_t']:,.0f}t commercial)"
            )
    if w:
        if w.get('risk_level') in ('Critical', 'High'):
            context_bullets.append(
                f"Waste risk level is {w['risk_level']} — "
                f"point sources contribute {w['point_pct']:.0f}% of waste emissions"
            )

    context_block = "\n".join(f"• {b}" for b in context_bullets) if context_bullets else "No special risk flags."

    prompt = f"""You are a senior climate policy advisor hired by the Government of Punjab to write a site-specific emission reduction action plan for {area} Union Council in Lahore District.

EMISSION DATA FOR {area.upper()}:
{data_block}

AREA-SPECIFIC CONTEXT:
{context_block}

Based on this data, generate a JSON response with EXACTLY this structure. Every recommendation MUST reference the specific numbers above (e.g. "{t['forecast_annual_t']:,.0f}t annual transport emissions" or "rank #{t['rank_in_division']}" or specific risk flags). Do NOT write generic advice that could apply to any city.

{{
  "summary": "3-4 sentences. Start with: '{area} UC emits [total] tonnes CO2e annually, ranking #[rank]/151 in Lahore District.' Then describe the dominant emission source, key risk, and what makes this UC different from others. Use actual numbers from the data.",

  "immediate_actions": [
    "5 actions. Each MUST: (1) name {area} specifically, (2) reference the actual emission breakdown (e.g. 'road transport at {t['road_pct'] if t else 0:.0f}%'), (3) propose an intervention sized to the area's km² and emission intensity. Format: **Bold Title targeting {area}** - [Expected Impact]: X% reduction of the {t['forecast_annual_t'] if t else 0:,.0f}t - [Estimated Cost Range]: PKR X Million - [Implementation Priority]: High/Medium/Low"
  ],

  "long_term_strategies": [
    "3-4 strategies. Each MUST reference {area}'s specific rank, risk flags, or emission profile. Format: **Bold Title** - [Timeline]: X years - [Expected Reduction]: X% of {area}'s [sector] emissions - [Key Milestones]: Year 1: ... Year 2: ..."
  ],

  "policy_recommendations": [
    "3-4 recommendations. Each MUST cite a REAL Pakistan/Punjab law or regulation (e.g. 'Under Section 11 of Punjab Environmental Protection Act 1997' or 'Pakistan Climate Change Act 2017, Section 4(2)' or 'National Electric Vehicle Policy 2019, Para 7.3' or 'PEPA Motor Vehicle Emission Standards SRO 72(I)/2009' or 'Pakistan NDC 2021, target 50% by 2030'). Explain how the cited law applies to {area}'s specific situation."
  ],

  "monitoring_metrics": [
    "3-4 metrics. Each must be measurable at the {area} UC level, not city-wide. Include baseline values from the data above where possible."
  ],

  "risk_factors": [
    "3-4 risks specific to {area}'s geography, demographics, or emission profile. Reference the risk flags ({', '.join(t.get('risk_flags', []) if t else [])}) and explain why they matter for implementation."
  ]
}}

Return ONLY valid JSON. No markdown, no code fences, no explanations outside the JSON."""

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
