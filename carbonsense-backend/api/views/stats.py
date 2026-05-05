"""
Aggregate stats endpoint for the dashboard overview.

Returns the four scalars the KPI cards display, computed in the database
rather than by summing thousands of rows in the browser. The response is a
tiny JSON object that's cheap to gzip and cheap to cache.
"""

from django.core.cache import cache
from django.db.models import Max, Min, Sum
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from api.models import EmissionPoint, Location
from api.services.runs import CACHE_TTL, get_active_runs, sector_field


_CACHE_KEY = "api_stats"


_EMPTY_SECTOR_TOTALS = {
    "transport": 0.0,
    "industry": 0.0,
    "energy": 0.0,
    "waste": 0.0,
    "buildings": 0.0,
}


def _empty_stats():
    return {
        "total_sources": 0,
        "sectors_tracked": 0,
        "years_of_data": 0,
        "total_emissions": 0.0,
        "sector_totals": dict(_EMPTY_SECTOR_TOTALS),
        "historical": {"years_of_data": 0, "total_emissions": 0.0},
        "forecast": {"years_of_data": 0, "total_emissions": 0.0},
    }


def _aggregate_for_type(qs, point_type):
    """Date range + total for a single point_type. Returns (years, total)."""
    a = qs.filter(point_type=point_type).aggregate(
        min_date=Min("date"),
        max_date=Max("date"),
        total=Sum("emissions"),
    )
    if a["min_date"] and a["max_date"]:
        years = a["max_date"].year - a["min_date"].year + 1
    else:
        years = 0
    return years, float(a["total"] or 0.0)


def _compute_stats():
    runs = get_active_runs()
    if not runs:
        return _empty_stats()

    run_ids = [r.id for r in runs]
    run_sector = {r.id: sector_field(r) for r in runs}
    sectors = set(run_sector.values())

    total_sources = Location.objects.filter(forecast_run_id__in=run_ids).count()

    points_qs = EmissionPoint.objects.filter(
        location__forecast_run_id__in=run_ids,
    )
    hist_years, hist_total = _aggregate_for_type(points_qs, "historical")
    fc_years, fc_total = _aggregate_for_type(points_qs, "forecast")

    # Per-sector totals computed from historical only — that's what the pie
    # chart is meant to display ("emissions to date by sector"). The forecast
    # totals are exposed separately under `forecast.total_emissions` for any
    # consumer that wants them.
    totals_by_run = (
        points_qs.filter(point_type="historical")
        .values("location__forecast_run_id")
        .annotate(total=Sum("emissions"))
    )
    sector_totals = dict(_EMPTY_SECTOR_TOTALS)
    for row in totals_by_run:
        sector = run_sector.get(row["location__forecast_run_id"], "energy")
        sector_totals[sector] = sector_totals.get(sector, 0.0) + float(
            row["total"] or 0.0
        )

    # Top-level fields default to *historical* — the intended KPI shape that
    # matches the existing UI ("Total Emissions", "Years of Data" mean the
    # data we've measured, not anything we've projected forward).
    return {
        "total_sources": total_sources,
        "sectors_tracked": len(sectors),
        "years_of_data": hist_years,
        "total_emissions": hist_total,
        "sector_totals": sector_totals,
        "historical": {"years_of_data": hist_years, "total_emissions": hist_total},
        "forecast": {"years_of_data": fc_years, "total_emissions": fc_total},
    }


@api_view(["GET"])
@permission_classes([AllowAny])
def stats_view(request):
    cached = cache.get(_CACHE_KEY)
    if cached is not None:
        return Response(cached)
    stats = _compute_stats()
    cache.set(_CACHE_KEY, stats, CACHE_TTL)
    return Response(stats)
