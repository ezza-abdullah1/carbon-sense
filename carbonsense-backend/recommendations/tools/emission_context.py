"""
Build a structured place context from coordinates + UC emission JSON files.

The same context object feeds:
  - the policy retriever (so retrieval is conditioned on the place's profile)
  - the synthesizer prompt (so the LLM grounds every recommendation in real numbers)
  - the conversation manager (so follow-up Q&A stays on-topic)
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

from django.conf import settings

logger = logging.getLogger(__name__)


def _safe(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    if isinstance(val, float) and (val != val or val == float('inf')):
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _load_json(filename: str) -> Optional[dict]:
    path = os.path.join(str(settings.BASE_DIR), 'data', filename)
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning("UC data file not found: %s", path)
    except Exception as exc:
        logger.warning("Failed to load %s: %s", filename, exc)
    return None


def _find_uc(records: List[dict], name_lower: str, key: str = 'uc_name') -> Optional[dict]:
    for uc in records:
        if (uc.get(key, '') or '').lower().strip() == name_lower:
            return uc
    return None


def build_place_context(area_name: str, sector: str,
                        coordinates: Optional[dict]) -> Dict[str, Any]:
    """Return a place-context dict with the fields needed by retrieval and synthesis."""

    coords = coordinates or {}
    name_lower = (area_name or '').lower().strip()

    ctx: Dict[str, Any] = {
        'area_name': area_name,
        'sector': sector,
        'country': 'Pakistan',
        'region': 'South Asia',
        'city': 'Lahore',
        'coordinates': {
            'lat': coords.get('lat'),
            'lng': coords.get('lng'),
        },
        'risk_flags': [],
        'top_emitters': [],
        'dominant_source': '',
        'rank_in_division': None,
        'intensity_t_per_km2': 0.0,
        'transport': None,
        'buildings': None,
        'waste': None,
    }

    # Transport
    transport = _load_json('carbonsense_transport_v16.json')
    if transport:
        uc = _find_uc(transport.get('uc_emissions', []), name_lower)
        if uc:
            fc = uc.get('forecast', {}) or {}
            hist = uc.get('historical', {}) or {}
            ctx['transport'] = {
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
                'risk_flags': list(uc.get('risk_flags', []) or []),
            }
            ctx['risk_flags'].extend(ctx['transport']['risk_flags'])
            ctx['intensity_t_per_km2'] = ctx['transport']['intensity_t_per_km2']
            ctx['rank_in_division'] = ctx['transport']['rank_in_division']
            ctx['dominant_source'] = ctx['transport']['dominant_source'] or 'road'

    # Buildings
    buildings = _load_json('carbonsense_buildings_v15.json')
    if buildings:
        uc = _find_uc(buildings.get('uc_data', []), name_lower)
        if uc:
            ae = uc.get('annual_emissions', {}) or {}
            risk = uc.get('risk', {}) or {}
            ctx['buildings'] = {
                'uc_code': uc.get('uc_code', ''),
                'forecast_total_t': _safe(ae.get('total_t')),
                'residential_t': _safe(ae.get('residential_t')),
                'non_residential_t': _safe(ae.get('non_residential_t')),
                'intensity_t_km2': _safe(ae.get('intensity_t_km2')),
                'rank_in_district': ae.get('rank_in_district', 0),
                'risk_flags': [k for k, v in risk.items() if v is True],
            }
            ctx['risk_flags'].extend(ctx['buildings']['risk_flags'])

    # Waste
    waste = _load_json('carbonsense_per_location_waste_v2_3.json')
    if waste:
        uc_list = waste.get('aggregate_forecast', {}).get('uc_allocation', []) or []
        uc = _find_uc(uc_list, name_lower)
        if uc:
            em = uc.get('emissions', {}) or {}
            ctx['waste'] = {
                'uc_code': uc.get('uc_code', ''),
                'forecast_annual_t': _safe(em.get('total_annual_t')),
                'point_source_t': _safe(em.get('point_source_t')),
                'area_sw_t': _safe(em.get('area_sw_t')),
                'area_ww_t': _safe(em.get('area_ww_t')),
                'point_pct': _safe(em.get('point_pct')),
                'risk_level': em.get('risk_level', ''),
            }
            if ctx['waste']['risk_level'] in ('Critical', 'High'):
                ctx['risk_flags'].append(f"waste_risk_{ctx['waste']['risk_level'].lower()}")

    # Top emitters across sectors
    emitters = []
    if ctx['transport']:
        emitters.append(('transport', ctx['transport']['forecast_annual_t']))
    if ctx['buildings']:
        emitters.append(('buildings', ctx['buildings']['forecast_total_t']))
    if ctx['waste']:
        emitters.append(('waste', ctx['waste']['forecast_annual_t']))
    emitters.sort(key=lambda x: x[1], reverse=True)
    ctx['top_emitters'] = [name for name, _ in emitters[:3]]

    # Deduplicate risk_flags preserving order
    seen = set()
    deduped = []
    for f in ctx['risk_flags']:
        if f not in seen:
            seen.add(f)
            deduped.append(f)
    ctx['risk_flags'] = deduped

    return ctx


def summarize_for_prompt(ctx: Dict[str, Any]) -> str:
    """Render a compact human-readable summary block for inclusion in prompts."""

    area = ctx.get('area_name') or 'Unknown'
    coords = ctx.get('coordinates') or {}
    lines = [
        f"Union Council: {area}",
        f"Location: Lahore, Pakistan ({coords.get('lat')}, {coords.get('lng')})",
        f"Primary sector: {ctx.get('sector')}",
        f"Top emitters here: {', '.join(ctx.get('top_emitters') or []) or 'unknown'}",
        f"Risk flags: {', '.join(ctx.get('risk_flags') or []) or 'none'}",
        '',
    ]

    t = ctx.get('transport')
    if t:
        lines += [
            '--- TRANSPORT ---',
            f"Forecast annual: {t['forecast_annual_t']:,.0f} t CO2e",
            f"  Road {t['road_annual_t']:,.0f} t ({t['road_pct']:.1f}%)",
            f"  Dom. Aviation {t['dom_avi_annual_t']:,.0f} t",
            f"  Intl. Aviation {t['intl_avi_annual_t']:,.0f} t",
            f"  Rail {t['rail_annual_t']:,.0f} t",
            f"Intensity: {t['intensity_t_per_km2']:,.0f} t/km2  | Rank: #{t['rank_in_division']}/151",
            f"Historical {t['historical_period']}: {t['historical_total_t']:,.0f} t",
            f"Dominant source: {t['dominant_source']}",
            '',
        ]

    b = ctx.get('buildings')
    if b:
        lines += [
            '--- BUILDINGS ---',
            f"Forecast: {b['forecast_total_t']:,.0f} t (Res {b['residential_t']:,.0f} / Non-res {b['non_residential_t']:,.0f})",
            f"Intensity: {b['intensity_t_km2']:,.0f} t/km2 | Rank #{b['rank_in_district']}/151",
            '',
        ]

    w = ctx.get('waste')
    if w:
        lines += [
            '--- WASTE ---',
            f"Forecast: {w['forecast_annual_t']:,.0f} t (Point {w['point_source_t']:,.0f} / SW {w['area_sw_t']:,.0f} / WW {w['area_ww_t']:,.0f})",
            f"Risk: {w['risk_level'] or 'unknown'}",
            '',
        ]

    return "\n".join(lines)


def context_keywords(ctx: Dict[str, Any]) -> str:
    """Distill the place context into a short keyword string for retrieval queries."""

    bits: List[str] = []
    bits.append(ctx.get('sector') or '')
    if ctx.get('dominant_source'):
        bits.append(f"dominant {ctx['dominant_source']}")
    for flag in ctx.get('risk_flags') or []:
        bits.append(flag.replace('_', ' '))
    for emitter in ctx.get('top_emitters') or []:
        bits.append(emitter)
    return ' '.join(b for b in bits if b)
