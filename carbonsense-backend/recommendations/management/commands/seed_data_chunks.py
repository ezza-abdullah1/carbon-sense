"""
Seed the Supabase `data_chunks` table from the bundled JSON datasets.

Reads:
  data/carbonsense_transport_v16.json
  data/carbonsense_buildings_v15.json
  data/carbonsense_per_location_waste_v2_3.json
  data/carbonsense_lahore_spatial_v1.2.json

Produces one human-readable, numerically dense chunk per UC per sector, plus
a handful of peer-band and city-wide aggregate chunks, then embeds them with
OpenAI text-embedding-3-small and upserts into Supabase.

Run:
  python manage.py seed_data_chunks
  python manage.py seed_data_chunks --dry-run        # render only, no API calls
  python manage.py seed_data_chunks --limit 5        # sanity check on small batch
  python manage.py seed_data_chunks --only transport # one sector at a time
"""

import json
import os
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


DATA_DIR = Path(settings.BASE_DIR) / 'data'

FILES = {
    'transport': 'carbonsense_transport_v16.json',
    'buildings': 'carbonsense_buildings_v15.json',
    'waste':     'carbonsense_per_location_waste_v2_3.json',
    'spatial':   'carbonsense_lahore_spatial_v1.2.json',
}


# ───────────────────────────────────────────────────────────────────────────
# Chunk renderers — each returns a list of dicts with the shape:
#   {
#     'source_dataset': str,
#     'uc_code':        str | None,
#     'uc_name':        str | None,
#     'sector':         str,
#     'chunk_type':     str,
#     'chunk_text':     str,
#     'numeric_facts':  dict,
#   }
# ───────────────────────────────────────────────────────────────────────────

def _safe(v, default=0.0):
    if v is None:
        return default
    if isinstance(v, float) and (v != v):
        return default
    return v


def _fmt(n, default='—'):
    try:
        return f"{float(n):,.0f}"
    except (TypeError, ValueError):
        return default


def render_transport_chunks(path):
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    out = []
    for uc in data.get('uc_emissions', []):
        fc = uc.get('forecast', {}) or {}
        hist = uc.get('historical', {}) or {}
        name = uc.get('uc_name', 'Unknown')
        code = uc.get('uc_code', '')
        area_km2 = _safe(uc.get('area_km2'))
        annual = _safe(fc.get('annual_t'))
        road = _safe(fc.get('road_annual_t'))
        dom_avi = _safe(fc.get('dom_avi_annual_t'))
        intl_avi = _safe(fc.get('intl_avi_annual_t'))
        rail = _safe(fc.get('rail_annual_t'))
        road_pct = _safe(fc.get('road_pct'))
        intensity = _safe(fc.get('intensity_t_per_km2'))
        rank = fc.get('rank_in_division', 0)
        hist_total = _safe(hist.get('total_t'))
        hist_period = hist.get('period', '')
        dominant = uc.get('dominant_source', '')
        risk_flags = uc.get('risk_flags', []) or []

        # Trend
        if hist_total and annual:
            # historical is total across n_months; normalise to annualised
            n_months = hist.get('n_months') or 60
            hist_annualised = hist_total * 12 / max(n_months, 1)
            trend_pct = (annual - hist_annualised) / hist_annualised * 100
        else:
            trend_pct = 0.0

        text = (
            f"TRANSPORT EMISSIONS — {name} Union Council ({code}), "
            f"Lahore District, Punjab, Pakistan.\n\n"
            f"Forecast annual emissions: {_fmt(annual)} t CO2e across "
            f"{area_km2:.2f} km² (intensity {_fmt(intensity)} t/km²).\n"
            f"Breakdown: road transport {road_pct:.0f}% ({_fmt(road)} t), "
            f"domestic aviation {_fmt(dom_avi)} t, "
            f"international aviation {_fmt(intl_avi)} t, "
            f"rail {_fmt(rail)} t.\n"
            f"Rank: #{rank} of 151 UCs in Lahore District for transport emissions.\n"
            f"Historical ({hist_period}): {_fmt(hist_total)} t total — "
            f"trend {trend_pct:+.1f}% vs forecast.\n"
            f"Dominant source: {dominant or 'road transport'}.\n"
            f"Risk flags: {', '.join(risk_flags) if risk_flags else 'none'}.\n"
        )

        out.append({
            'source_dataset': 'transport_v16',
            'uc_code': code,
            'uc_name': name,
            'sector': 'transport',
            'chunk_type': 'uc_profile',
            'chunk_text': text,
            'numeric_facts': {
                'annual_t': annual, 'road_pct': road_pct, 'intensity': intensity,
                'rank': rank, 'area_km2': area_km2, 'risk_flags': risk_flags,
                'trend_pct': trend_pct,
            },
        })

    # Peer bands — group top emitters by intensity tier
    ucs = data.get('uc_emissions', [])
    if ucs:
        top10 = sorted(
            ucs,
            key=lambda u: -_safe((u.get('forecast') or {}).get('annual_t'))
        )[:10]
        top_names = [u.get('uc_name', '?') for u in top10]
        top_total = sum(_safe((u.get('forecast') or {}).get('annual_t')) for u in top10)
        division_total_t = _safe(
            (data.get('division_total') or {}).get('annual_total_t')
        )
        share_pct = (top_total / division_total_t * 100) if division_total_t else 0
        out.append({
            'source_dataset': 'transport_v16',
            'uc_code': None,
            'uc_name': None,
            'sector': 'transport',
            'chunk_type': 'peer_band',
            'chunk_text': (
                f"PEER BAND — Top-10 transport-emitting UCs in Lahore District.\n"
                f"Combined annual: {_fmt(top_total)} t CO2e "
                f"({share_pct:.0f}% of district total).\n"
                f"UCs: {', '.join(top_names)}.\n"
                f"Common profile: dense road-dominated UCs, several with airport-"
                f"adjacent risk flags. Interventions targeting these 10 UCs would "
                f"address the majority of Lahore's road transport emissions."
            ),
            'numeric_facts': {'uc_names': top_names, 'combined_t': top_total},
        })

    return out


def render_buildings_chunks(path):
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    out = []
    for uc in data.get('uc_data', []):
        ae = uc.get('annual_emissions', {}) or {}
        risk = uc.get('risk', {}) or {}
        name = uc.get('uc_name', 'Unknown')
        code = uc.get('uc_code', '')
        area_km2 = _safe(uc.get('area_km2'))
        total = _safe(ae.get('total_t'))
        res = _safe(ae.get('residential_t'))
        non_res = _safe(ae.get('non_residential_t'))
        intensity = _safe(ae.get('intensity_t_km2'))
        rank = ae.get('rank_in_district', 0)
        risk_level = risk.get('risk_level', '')
        flags = [k for k, v in risk.items() if v is True]

        res_pct = (res / total * 100) if total else 0
        com_pct = risk.get('com_pct', 0)

        text = (
            f"BUILDINGS EMISSIONS — {name} Union Council ({code}), "
            f"Lahore District.\n\n"
            f"Forecast annual emissions: {_fmt(total)} t CO2e across "
            f"{area_km2:.2f} km² (intensity {_fmt(intensity)} t/km²).\n"
            f"Split: residential {res_pct:.0f}% ({_fmt(res)} t), "
            f"non-residential {_fmt(non_res)} t (commercial share ≈ {com_pct:.1f}%).\n"
            f"Rank: #{rank} of 151 UCs in Lahore District for building emissions.\n"
            f"Risk level: {risk_level or 'unknown'}.\n"
            f"Risk flags: {', '.join(flags) if flags else 'none'}.\n"
            f"Implications: residential-dominated UCs need cool-roof / passive-"
            f"cooling programmes; commercial-loaded UCs benefit from BEEC code "
            f"compliance and HVAC efficiency upgrades."
        )

        out.append({
            'source_dataset': 'buildings_v15',
            'uc_code': code,
            'uc_name': name,
            'sector': 'buildings',
            'chunk_type': 'uc_profile',
            'chunk_text': text,
            'numeric_facts': {
                'total_t': total, 'residential_pct': res_pct,
                'intensity': intensity, 'rank': rank, 'risk_level': risk_level,
                'flags': flags,
            },
        })
    return out


def render_waste_chunks(path):
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    out = []
    allocations = (data.get('aggregate_forecast') or {}).get('uc_allocation', [])
    for uc in allocations:
        em = uc.get('emissions', {}) or {}
        mc = uc.get('mitigation_context', {}) or {}
        name = uc.get('uc_name', 'Unknown')
        code = uc.get('uc_code', '')
        area_km2 = _safe(uc.get('area_km2'))
        total = _safe(em.get('total_annual_t'))
        point = _safe(em.get('point_source_t'))
        sw = _safe(em.get('area_sw_t'))
        ww = _safe(em.get('area_ww_t'))
        point_pct = _safe(em.get('point_pct'))
        risk_level = em.get('risk_level', '')
        geo_type = uc.get('geo_type', '')
        intensity = _safe(uc.get('intensity_t_per_km2'))
        rank = uc.get('rank_in_district', 0)
        source_types = mc.get('source_types', []) or []
        policy_tags = mc.get('policy_tags', []) or []
        rag_context = mc.get('rag_context', '')

        text = (
            f"WASTE EMISSIONS — {name} Union Council ({code}), "
            f"Lahore District. Geo type: {geo_type or 'distributed'}.\n\n"
            f"Forecast annual emissions: {_fmt(total)} t CO2e across "
            f"{area_km2:.2f} km² (intensity {_fmt(intensity)} t/km²).\n"
            f"Breakdown: point sources {point_pct:.0f}% ({_fmt(point)} t), "
            f"solid waste {_fmt(sw)} t, wastewater {_fmt(ww)} t.\n"
            f"Rank: #{rank} of 151 UCs. Risk level: {risk_level or 'unknown'}.\n"
            f"Identified source types: {', '.join(source_types) if source_types else 'distributed'}.\n"
            f"Mitigation policy tags: {', '.join(policy_tags) if policy_tags else 'general MSW management'}.\n"
            f"Context: {rag_context}"
        )

        out.append({
            'source_dataset': 'waste_v2_3',
            'uc_code': code,
            'uc_name': name,
            'sector': 'waste',
            'chunk_type': 'uc_profile',
            'chunk_text': text,
            'numeric_facts': {
                'total_t': total, 'point_pct': point_pct,
                'intensity': intensity, 'rank': rank,
                'risk_level': risk_level, 'source_types': source_types,
                'policy_tags': policy_tags,
            },
        })
    return out


def render_aggregate_chunks(path):
    """Division-level summary chunks (sector='aggregate')."""
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    out = []
    meta = data.get('metadata', {}) or {}
    df = data.get('division_forecast', {}) or {}
    dh = data.get('division_historical', {}) or {}

    total_fc = _safe(df.get('annual_t') or df.get('total_t'))
    total_hist = _safe(dh.get('total_t'))
    period = dh.get('period', '')

    if total_fc:
        out.append({
            'source_dataset': 'spatial_v1.2',
            'uc_code': None,
            'uc_name': 'Lahore District',
            'sector': 'aggregate',
            'chunk_type': 'sector_total',
            'chunk_text': (
                f"LAHORE DISTRICT — division-wide emission aggregate.\n\n"
                f"Forecast annual: {_fmt(total_fc)} t CO2e across 151 UCs.\n"
                f"Historical baseline ({period}): {_fmt(total_hist)} t total.\n"
                f"This is the city-scale denominator for any UC-level "
                f"intervention impact estimate."
            ),
            'numeric_facts': {
                'forecast_annual_t': total_fc,
                'historical_total_t': total_hist,
                'period': period,
            },
        })
    return out


def collect_chunks(only=None):
    chunks = []
    if not only or only == 'transport':
        p = DATA_DIR / FILES['transport']
        if p.exists():
            chunks.extend(render_transport_chunks(p))
    if not only or only == 'buildings':
        p = DATA_DIR / FILES['buildings']
        if p.exists():
            chunks.extend(render_buildings_chunks(p))
    if not only or only == 'waste':
        p = DATA_DIR / FILES['waste']
        if p.exists():
            chunks.extend(render_waste_chunks(p))
    if not only or only == 'aggregate':
        p = DATA_DIR / FILES['spatial']
        if p.exists():
            chunks.extend(render_aggregate_chunks(p))
    return chunks


# ───────────────────────────────────────────────────────────────────────────
# Embedding + upsert
# ───────────────────────────────────────────────────────────────────────────

def embed_batch(texts, model):
    from openai import OpenAI
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    resp = client.embeddings.create(model=model, input=texts)
    return [item.embedding for item in resp.data]


def supabase_client():
    from supabase import create_client
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
        raise CommandError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


# ───────────────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = "Embed and upsert UC emission data into Supabase data_chunks."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help="Render chunks and print sample; skip API calls.")
        parser.add_argument('--limit', type=int, default=None,
                            help="Only process the first N chunks (sanity check).")
        parser.add_argument('--only', choices=['transport', 'buildings', 'waste', 'aggregate'],
                            help="Process only one sector.")
        parser.add_argument('--batch-size', type=int, default=100,
                            help="Embedding + upsert batch size (default 100).")

    def handle(self, *args, **opts):
        chunks = collect_chunks(only=opts.get('only'))
        if opts.get('limit'):
            chunks = chunks[:opts['limit']]

        self.stdout.write(f"Collected {len(chunks)} chunks.")
        if not chunks:
            self.stdout.write(self.style.WARNING("Nothing to do."))
            return

        if opts['dry_run']:
            self.stdout.write("\n=== Sample chunk ===\n")
            self.stdout.write(chunks[0]['chunk_text'])
            self.stdout.write("\n=== Sectors / types ===")
            from collections import Counter
            counts = Counter((c['sector'], c['chunk_type']) for c in chunks)
            for (sec, typ), n in counts.most_common():
                self.stdout.write(f"  {sec:12s} {typ:14s} {n}")
            return

        if not settings.OPENAI_API_KEY:
            raise CommandError("OPENAI_API_KEY not set")

        model = settings.OPENAI_EMBEDDING_MODEL
        sb = supabase_client()
        batch_size = opts['batch_size']

        total = 0
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            texts = [c['chunk_text'] for c in batch]
            self.stdout.write(f"Embedding batch {i // batch_size + 1} "
                              f"({len(batch)} chunks)…")
            vectors = embed_batch(texts, model)

            rows = []
            for c, vec in zip(batch, vectors):
                rows.append({
                    'source_dataset': c['source_dataset'],
                    'uc_code': c['uc_code'],
                    'uc_name': c['uc_name'],
                    'sector': c['sector'],
                    'chunk_type': c['chunk_type'],
                    'chunk_text': c['chunk_text'],
                    'numeric_facts': c['numeric_facts'],
                    'embedding': vec,
                })

            sb.table('data_chunks').upsert(
                rows,
                on_conflict='source_dataset,uc_code,sector,chunk_type',
            ).execute()
            total += len(rows)

        self.stdout.write(self.style.SUCCESS(f"Upserted {total} chunks into Supabase."))
