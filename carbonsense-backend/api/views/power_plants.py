"""
Power-plant point-source endpoint.

The energy sector is the only one whose underlying data is *not* per-UC —
it's a set of named generation facilities at fixed lat/lng. We surface
them here as a list of `{name, lat, lng, type, emissions}` rows so the
frontend can render them as point markers rather than trying to colour
UC polygons (which would be misleading — power demand doesn't map cleanly
to UC geography).
"""

from django.core.cache import cache
from django.db.models import Sum
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from api.models import EmissionPoint, Location, LocationSummary
from api.services.runs import CACHE_TTL, get_active_runs, sector_field


@api_view(["GET"])
@permission_classes([AllowAny])
def power_plants_view(request):
    """
    Returns `[{source, type, lat, lng, emissions, summary}]` — one entry
    per power-plant point source.

    `summary` carries the forecast/historical totals + trend that drive
    the detail panel:
        forecast_12m_total, total_historical_tonnes, change_pct, trend

    Query params:
        data_type: 'historical' | 'forecast'  (default 'historical')
                   Selects which `point_type` to sum for the top-level
                   `emissions` field (the same row is in both responses
                   under different period scopes).
    """
    data_type = request.query_params.get("data_type", "historical")
    if data_type not in ("historical", "forecast"):
        data_type = "historical"

    cache_key = f"power_plants:{data_type}"
    cached = cache.get(cache_key)
    if cached is not None:
        return Response(cached)

    energy_run_ids = [
        r.id for r in get_active_runs() if sector_field(r) == "energy"
    ]
    if not energy_run_ids:
        return Response([])

    totals = {
        row["location_id"]: float(row["t"] or 0.0)
        for row in EmissionPoint.objects.filter(
            location__forecast_run_id__in=energy_run_ids,
            point_type=data_type,
        )
        .values("location_id")
        .annotate(t=Sum("emissions"))
    }

    locations = list(
        Location.objects.filter(id__in=list(totals.keys())).only(
            "id", "source", "type", "latitude", "longitude"
        )
    )
    summaries = {
        s.location_id: s
        for s in LocationSummary.objects.filter(
            location_id__in=[loc.id for loc in locations]
        )
    }

    result = []
    for loc in locations:
        s = summaries.get(loc.id)
        result.append({
            "source": loc.source,
            "type": loc.type or "",
            "lat": loc.latitude,
            "lng": loc.longitude,
            "emissions": totals.get(loc.id, 0.0),
            "summary": {
                "last_historical_date": s.last_historical_date if s else "",
                "last_historical_emissions": (
                    s.last_historical_emissions if s else 0.0
                ),
                "forecast_12m_total": s.forecast_12m_total if s else 0.0,
                "forecast_12m_average": s.forecast_12m_average if s else 0.0,
                "total_historical_tonnes": (
                    s.total_historical_tonnes if s else 0.0
                ),
                "change_pct": s.change_pct if s else 0.0,
                "trend": s.trend if s else "stable",
            } if s else None,
        })
    # Largest first so the renderer can size markers without re-sorting.
    result.sort(key=lambda x: x["emissions"], reverse=True)

    cache.set(cache_key, result, CACHE_TTL)
    return Response(result)
