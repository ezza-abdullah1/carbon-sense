"""
RecommendationAgent — orchestrates n8n RAG generation with template fallback.

Flow:
  1. Load UC emission data from the bundled JSON files (transport, buildings, waste)
  2. Build an emissions_summary the n8n workflow can consume
  3. POST to n8n /generate-recs; n8n does retrieval + Claude Sonnet generation
  4. If n8n is unreachable OR RECOMMENDATIONS_BACKEND='template', fall back to
     ResponseFormatter.build_from_template so the API still returns a payload.
"""

import json
import logging
from datetime import datetime

from django.conf import settings

from recommendations.n8n_client import N8nClient, N8nUnavailable
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
                    'risk_level': risk.get('risk_level', ''),
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


def _uc_to_emissions_analysis(uc_data):
    """Map UC-data into the dict shape ResponseFormatter.build_from_template expects."""
    t = uc_data.get('transport') or {}
    b = uc_data.get('buildings') or {}
    w = uc_data.get('waste') or {}

    sector_totals = {
        'transport': t.get('forecast_annual_t', 0) or 0,
        'buildings': b.get('forecast_total_t', 0) or 0,
        'waste': w.get('forecast_annual_t', 0) or 0,
        'industry': 0,
        'energy': 0,
    }
    total = sum(sector_totals.values())

    hist_total = t.get('historical_total_t', 0) or 0
    fc_total = t.get('forecast_annual_t', 0) or 0
    if hist_total and fc_total:
        trend_pct = (fc_total - hist_total) / hist_total * 100
        if trend_pct > 5:
            trend = 'increasing'
        elif trend_pct < -5:
            trend = 'decreasing'
        else:
            trend = 'stable'
    else:
        trend = 'stable'
        trend_pct = 0.0

    return {
        'total_emissions': total,
        'sector_totals': sector_totals,
        'trend_direction': trend,
        'trend_percentage': trend_pct,
        'historical_count': 12 if hist_total else 0,
        'forecast_direction': 'increasing' if trend == 'increasing' else 'stable',
        'forecast_count': 1 if fc_total else 0,
    }


class RecommendationAgent:
    """Calls n8n /generate-recs; falls back to template builder on failure."""

    def __init__(self):
        self.formatter = ResponseFormatter()
        self.n8n = N8nClient()

    def generate(self, area_id, area_name, sector, coordinates, trace=True):
        tracer = PipelineTracer()

        # ── 1. Load UC emission data ──────────────────────────────────────
        with tracer.step(1, "Loading UC emission data from JSON files") as t:
            uc_data = _load_uc_data(area_name, sector, coordinates)
            t.add_data({
                'has_transport': 'transport' in uc_data,
                'has_buildings': 'buildings' in uc_data,
                'has_waste': 'waste' in uc_data,
            })

        # ── 2. Build emissions_summary for n8n ────────────────────────────
        with tracer.step(2, "Preparing emissions summary"):
            emissions_summary = _uc_to_emissions_analysis(uc_data)
            emissions_summary['uc_data'] = uc_data  # risk flags, ranks, sub-breakdowns

        backend = getattr(settings, 'RECOMMENDATIONS_BACKEND', 'n8n')

        # ── 3. Call n8n if enabled ────────────────────────────────────────
        n8n_result = None
        if backend == 'n8n' and self.n8n.configured:
            with tracer.step(3, "Calling n8n /generate-recs") as t:
                try:
                    n8n_result = self.n8n.generate({
                        'area_id': area_id,
                        'area_name': area_name,
                        'sector': sector,
                        'coordinates': coordinates,
                        'emissions_summary': emissions_summary,
                    })
                    t.add_data({
                        'source': n8n_result.get('source'),
                        'run_id': n8n_result.get('run_id'),
                        'from_cache': n8n_result.get('from_cache', False),
                    })
                except N8nUnavailable as e:
                    logger.warning(f"n8n unavailable, falling back to template: {e}")
                    t.add_data({'status': 'unavailable', 'error': str(e)})
        else:
            with tracer.step(3, "n8n disabled, going to template fallback") as t:
                t.add_data({
                    'backend': backend,
                    'configured': self.n8n.configured,
                })

        # ── 4. Build final response ───────────────────────────────────────
        with tracer.step(4, "Formatting final response") as t:
            if n8n_result and 'recommendations' in n8n_result:
                result = n8n_result
                # Stamp Django-side metadata that n8n won't have
                result.setdefault('query', {
                    'area_name': area_name,
                    'area_id': area_id,
                    'sector': sector,
                    'coordinates': coordinates,
                })
                result.setdefault('generated_at', datetime.utcnow().isoformat() + 'Z')
                result['success'] = True
                t.add_data({'path': 'n8n'})
            else:
                fallback = self.formatter.build_from_template(
                    area_name=area_name,
                    area_id=area_id,
                    sector=sector,
                    coordinates=coordinates,
                    policy_results=[],
                    emissions_analysis=emissions_summary,
                )
                result = fallback
                result['source'] = 'template_fallback'
                t.add_data({'path': 'template_fallback'})

        if trace:
            result['pipeline_trace'] = tracer.get_trace()

        return result
