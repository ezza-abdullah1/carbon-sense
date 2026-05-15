"""
UC summary endpoint — one entry per Union Council, joining all sector data.

This is the heaviest endpoint by far: it parses four JSON files (transport,
buildings, waste, industry) and joins them into 151 UC entries. The parse
cost is paid once per worker (in-process JSON cache); per-request cost is
the join + the response cache.
"""

from django.core.cache import cache
from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from api.services.data_files import (
    build_buildings_by_uc,
    build_industry_by_uc,
    build_transport_by_uc,
    build_waste_by_uc,
    find_month_index,
    get_monthly_dates,
    load_data_file,
)
from api.services.runs import CACHE_TTL, safe_float


def _build_summary(data_type, view_mode, target_month):
    """Pure function: build the full 151-UC summary list. Cacheable."""
    transport_by_uc = build_transport_by_uc(data_type)
    buildings_by_uc = build_buildings_by_uc(data_type)
    waste_by_uc = build_waste_by_uc(data_type)
    industry_by_uc = build_industry_by_uc(data_type)
    # Energy is *not* allocated to UCs: power plants are point sources with
    # fixed coordinates, not entities that belong to a Union Council. They
    # are exposed separately via /api/power-plants/ so the frontend can
    # render them as map markers. We deliberately set the per-UC energy
    # share to 0 here so the choropleth and totals don't include a
    # misleading uniform value.
    energy_total = 0.0

    sector_dates = get_monthly_dates(data_type)

    month_indices = {}
    month_label = ""
    if view_mode == "monthly" and target_month:
        for sector_key, dates in sector_dates.items():
            month_indices[sector_key] = find_month_index(dates, target_month)
        month_label = target_month

    buildings_data = load_data_file("carbonsense_buildings_v15.json")
    transport_data = load_data_file("carbonsense_transport_v16.json")
    transport_meta = {
        uc["uc_code"]: uc for uc in transport_data.get("uc_emissions", [])
    }
    buildings_meta = {
        uc["uc_code"]: uc for uc in buildings_data.get("uc_data", [])
    }

    all_codes = sorted(set(transport_meta) | set(buildings_meta))
    n_ucs = len(all_codes) or 1

    if view_mode == "monthly":
        n_months_energy = max(len(sector_dates.get("buildings", [])), 1)
        energy_share = (energy_total / n_months_energy) / n_ucs
    else:
        energy_share = energy_total / n_ucs

    all_dates = sorted(
        set(
            sector_dates.get("transport", [])
            + sector_dates.get("buildings", [])
            + sector_dates.get("waste", [])
            + sector_dates.get("industry", [])
        )
    )
    available_months = sorted({d[:7] for d in all_dates})

    def _display(sector_data, sector_key, annual_key="annual_t"):
        if not sector_data:
            return 0.0
        if view_mode == "yearly":
            return safe_float(sector_data.get(annual_key))
        idx = month_indices.get(sector_key, -1)
        mt = sector_data.get("monthly_t", [])
        if 0 <= idx < len(mt):
            return safe_float(mt[idx])
        return 0.0

    results = []
    for uc_code in all_codes:
        tmeta = transport_meta.get(uc_code, {})
        bmeta = buildings_meta.get(uc_code, {})
        uc_name = tmeta.get("uc_name") or bmeta.get("uc_name", "")
        area_km2 = safe_float(tmeta.get("area_km2") or bmeta.get("area_km2"))
        lat = safe_float(
            tmeta.get("centroid_lat")
            or (bmeta.get("coordinates", {}).get("lat"))
        )
        lon = safe_float(
            tmeta.get("centroid_lon")
            or (bmeta.get("coordinates", {}).get("lon"))
        )

        t_data = transport_by_uc.get(uc_code)
        b_data = buildings_by_uc.get(uc_code)
        w_data = waste_by_uc.get(uc_code)
        i_data = industry_by_uc.get(uc_code)

        t_display = _display(t_data, "transport")
        b_display = _display(b_data, "buildings", "total_t")
        w_display = _display(w_data, "waste")
        i_display = _display(i_data, "industry")

        if t_data:
            t_data = {**t_data, "display_t": round(t_display, 2)}
        if b_data:
            b_data = {**b_data, "display_t": round(b_display, 2)}
        if w_data:
            w_data = {**w_data, "display_t": round(w_display, 2)}
        if i_data:
            i_data = {**i_data, "display_t": round(i_display, 2)}

        total_display = (
            t_display + b_display + w_display + i_display + energy_share
        )

        results.append({
            "uc_code": uc_code,
            "uc_name": uc_name,
            "area_km2": area_km2,
            "centroid": [lat, lon],
            "data_type": data_type,
            "view_mode": view_mode,
            "month_label": month_label,
            "sectors": {
                "transport": t_data,
                "buildings": b_data,
                "waste": w_data,
                "industry": i_data,
                "energy": round(energy_share, 2),
            },
            "display_t": round(total_display, 2),
            "total_annual_t": round(
                (t_data["annual_t"] if t_data else 0)
                + (b_data["total_t"] if b_data else 0)
                + (w_data["annual_t"] if w_data else 0)
                + (i_data["annual_t"] if i_data else 0)
                + (energy_total / n_ucs),
                2,
            ),
            "available_months": available_months,
        })

    return results


def _normalize_params(request):
    data_type = request.query_params.get("data_type", "forecast")
    if data_type not in ("historical", "forecast"):
        data_type = "forecast"
    view_mode = request.query_params.get("view_mode", "yearly")
    if view_mode not in ("monthly", "yearly"):
        view_mode = "yearly"
    target_month = request.query_params.get("month", "")
    return data_type, view_mode, target_month


def _get_cached_summary(data_type, view_mode, target_month):
    """Cache the full 151-entry list keyed by params; build on miss."""
    cache_key = f"uc_summary_{data_type}_{view_mode}_{target_month}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    results = _build_summary(data_type, view_mode, target_month)
    cache.set(cache_key, results, CACHE_TTL)
    return results


class UCSummaryViewSet(viewsets.ViewSet):
    """
    One entry per Union Council with all sector data.

    Query params:
        data_type:  'historical' | 'forecast'   (default: 'forecast')
        view_mode:  'monthly'    | 'yearly'     (default: 'yearly')
        month:      'YYYY-MM'                   (only used when view_mode=monthly)
    """

    permission_classes = [AllowAny]

    def list(self, request):
        data_type, view_mode, target_month = _normalize_params(request)
        return Response(_get_cached_summary(data_type, view_mode, target_month))

    def retrieve(self, request, pk=None):
        # Use the cached list (build once, filter in memory) — was previously
        # rebuilding the entire 151-UC list per request.
        data_type, view_mode, target_month = _normalize_params(request)
        for entry in _get_cached_summary(data_type, view_mode, target_month):
            if entry["uc_code"] == pk:
                return Response(entry)
        return Response({"detail": "Not found."}, status=404)
