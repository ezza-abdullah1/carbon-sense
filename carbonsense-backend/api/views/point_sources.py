"""
Point-source endpoint — energy/industry facilities with real lat/lng.

Some sectors (energy, industry) have data at the **facility** level: each
location is a physical plant at a fixed coordinate. Other sectors
(transport, buildings) are UC-level only — their rows have
`type = "union_council"` and live on the choropleth, not as markers.

This endpoint returns only true point sources for a given sector,
explicitly excluding `union_council` and area-aggregate rows.
"""

from django.core.cache import cache
from django.db.models import Sum
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from api.models import EmissionPoint, Location, LocationSummary
from api.services.runs import CACHE_TTL, SECTOR_MAP, get_active_runs, sector_field


# Row types that are *not* point sources and must be excluded.
# - `union_council`: UC-level allocations (the choropleth's job).
# - `Area Source` / `area_source`: bulk aggregates over a polygon.
# - `Distributed`: waste rows spread across UCs via population weights.
# - `nan` / `NaN`: stringified pandas NaN — appears on regional-summary rows
#   masquerading as point sources (e.g. transport.json's "Lahore Division").
_NON_POINT_TYPES = {
    "union_council",
    "Area Source",
    "area_source",
    "Distributed",
    "distributed",
    "nan",
    "NaN",
}


@api_view(["GET"])
@permission_classes([AllowAny])
def point_sources_view(request):
    """
    Returns `[{source, type, lat, lng, emissions, summary, sector}]` for
    a given sector's facility-level locations.

    Query params:
        sector:    'energy' | 'industry' | 'transport' | 'waste' | 'buildings'
                   (default 'energy'). Aliases like 'power' or 'industrial'
                   map onto the canonical bucket.
        data_type: 'historical' | 'forecast' (default 'historical')
    """
    raw_sector = request.query_params.get("sector", "energy").lower()
    sector = SECTOR_MAP.get(raw_sector, raw_sector)

    data_type = request.query_params.get("data_type", "historical")
    if data_type not in ("historical", "forecast"):
        data_type = "historical"

    cache_key = f"point_sources:{sector}:{data_type}"
    cached = cache.get(cache_key)
    if cached is not None:
        return Response(cached)

    run_ids = [r.id for r in get_active_runs() if sector_field(r) == sector]
    if not run_ids:
        return Response([])

    # Pull historical *and* forecast totals from EmissionPoint up front. Some
    # loaders (notably waste) don't populate LocationSummary.forecast_12m_total
    # or .total_historical_tonnes, so the panel would render empty rows
    # without these — we override the (possibly-zero) summary fields below.
    def _totals_by_loc(point_type: str) -> dict[int, float]:
        return {
            row["location_id"]: float(row["t"] or 0.0)
            for row in EmissionPoint.objects.filter(
                location__forecast_run_id__in=run_ids,
                point_type=point_type,
            )
            .values("location_id")
            .annotate(t=Sum("emissions"))
        }

    totals_hist = _totals_by_loc("historical")
    totals_fc = _totals_by_loc("forecast")
    totals_active = totals_hist if data_type == "historical" else totals_fc

    candidate_ids = set(totals_hist) | set(totals_fc)
    locations = list(
        Location.objects.filter(id__in=list(candidate_ids)).only(
            "id", "source", "type", "latitude", "longitude"
        )
    )
    # Drop UC-level / area-aggregate / NaN-typed rows so the FE only renders real points.
    locations = [loc for loc in locations if (loc.type or "") not in _NON_POINT_TYPES]

    summaries = {
        s.location_id: s
        for s in LocationSummary.objects.filter(
            location_id__in=[loc.id for loc in locations]
        )
    }

    result = []
    for loc in locations:
        s = summaries.get(loc.id)
        hist_total = totals_hist.get(loc.id, 0.0)
        fc_total = totals_fc.get(loc.id, 0.0)
        # Prefer the summary's curated value if it has one, otherwise fall
        # back to the live aggregate so the panel always shows real numbers.
        summary_hist = (
            s.total_historical_tonnes
            if s and s.total_historical_tonnes
            else hist_total
        )
        summary_fc = (
            s.forecast_12m_total if s and s.forecast_12m_total else fc_total
        )
        result.append({
            "source": loc.source,
            "type": loc.type or "",
            "lat": loc.latitude,
            "lng": loc.longitude,
            "emissions": totals_active.get(loc.id, 0.0),
            "sector": sector,
            "summary": {
                "last_historical_date": s.last_historical_date if s else "",
                "last_historical_emissions": (
                    s.last_historical_emissions if s else 0.0
                ),
                "forecast_12m_total": summary_fc,
                "forecast_12m_average": s.forecast_12m_average if s else 0.0,
                "total_historical_tonnes": summary_hist,
                "change_pct": s.change_pct if s else 0.0,
                "trend": s.trend if s else "stable",
            },
        })
    result.sort(key=lambda x: x["emissions"], reverse=True)

    cache.set(cache_key, result, CACHE_TTL)
    return Response(result)
