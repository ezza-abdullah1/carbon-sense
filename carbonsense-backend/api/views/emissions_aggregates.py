"""
Pre-aggregated emission endpoints.

These exist so the frontend never has to fetch every emission point just to
compute "the latest value per area" or "the monthly total across all areas".
Both jobs are cheap aggregate queries on the DB and return tiny payloads.
"""

from django.core.cache import cache
from django.db.models import Max, Sum
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from api.models import EmissionPoint, Location, make_area_id
from api.services.runs import CACHE_TTL, get_active_runs, sector_field


def _validate_data_type(raw):
    if raw not in ("historical", "forecast"):
        return "historical"
    return raw


@api_view(["GET"])
@permission_classes([AllowAny])
def latest_emissions_by_area(request):
    """
    Returns `{area_id: latest_emission_value}` — one entry per area.

    Replaces the frontend's old pattern of fetching every emission point and
    grouping in JavaScript. We do the grouping in Postgres with a single
    query (latest date per location) and serialize ~750 entries instead of
    ~54,000.

    Query params:
        data_type: 'historical' | 'forecast'  (default 'historical')
    """
    data_type = _validate_data_type(request.query_params.get("data_type"))
    cache_key = f"latest_by_area:{data_type}"
    cached = cache.get(cache_key)
    if cached is not None:
        return Response(cached)

    runs = get_active_runs()
    if not runs:
        return Response({})

    run_ids = [r.id for r in runs]
    run_sector = {r.id: sector_field(r) for r in runs}

    # Latest emission date per location, then look up that row's value.
    # Two queries (one to find max-date-per-location, one to fetch the rows)
    # is far cheaper than streaming every point.
    latest_dates = (
        EmissionPoint.objects.filter(
            location__forecast_run_id__in=run_ids,
            point_type=data_type,
        )
        .values("location_id")
        .annotate(latest=Max("date"))
    )
    latest_map = {row["location_id"]: row["latest"] for row in latest_dates}
    if not latest_map:
        return Response({})

    # Fetch the (location_id, date) pairs in one query.
    points = (
        EmissionPoint.objects.filter(
            location_id__in=list(latest_map.keys()),
            point_type=data_type,
        )
        .select_related("location")
    )

    locs_meta = {
        loc.id: (loc.source, loc.forecast_run_id)
        for loc in Location.objects.filter(id__in=list(latest_map.keys())).only(
            "id", "source", "forecast_run_id"
        )
    }

    result = {}
    for ep in points:
        if ep.date != latest_map.get(ep.location_id):
            continue
        meta = locs_meta.get(ep.location_id)
        if not meta:
            continue
        source, run_id = meta
        sector = run_sector.get(run_id, "energy")
        area_id = make_area_id(source, sector)
        result[area_id] = ep.emissions

    cache.set(cache_key, result, CACHE_TTL)
    return Response(result)


@api_view(["GET"])
@permission_classes([AllowAny])
def emissions_timeline(request):
    """
    Returns a date-bucketed total across every area for the given data_type.

    Format: list of `{date, total}` objects, ordered oldest → newest.

    Query params:
        data_type: 'historical' | 'forecast'  (default 'historical')
    """
    data_type = _validate_data_type(request.query_params.get("data_type"))
    cache_key = f"emissions_timeline:{data_type}"
    cached = cache.get(cache_key)
    if cached is not None:
        return Response(cached)

    runs = get_active_runs()
    if not runs:
        return Response([])

    run_ids = [r.id for r in runs]

    rows = (
        EmissionPoint.objects.filter(
            location__forecast_run_id__in=run_ids,
            point_type=data_type,
        )
        .values("date")
        .annotate(total=Sum("emissions"))
        .order_by("date")
    )
    result = [
        {"date": row["date"].isoformat(), "total": float(row["total"] or 0.0)}
        for row in rows
    ]

    cache.set(cache_key, result, CACHE_TTL)
    return Response(result)
