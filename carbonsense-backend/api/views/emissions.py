"""Emission point endpoints — historical + forecast time series."""

from django.core.cache import cache
from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from api.models import EmissionPoint, Location, make_area_id
from api.services.runs import CACHE_TTL, get_active_runs, sector_field


# Pagination guardrails. The endpoint previously returned every point across
# every active run (~54k rows) — slow JSON, slow client. Default to 500 per
# page; clamp the upper bound so a malicious / careless client can't request
# the entire table in one call.
DEFAULT_LIMIT = 500
MAX_LIMIT = 5000


def _empty_emission_row():
    return {
        "transport": 0,
        "industry": 0,
        "energy": 0,
        "waste": 0,
        "buildings": 0,
    }


def _serialize(ep, run_sector):
    sector = run_sector.get(ep.location.forecast_run_id, "energy")
    val = ep.emissions or 0
    row = _empty_emission_row()
    row[sector] = val
    return {
        "id": ep.id,
        "area_id": make_area_id(ep.location.source, sector),
        "area_name": ep.location.source,
        "date": ep.date.isoformat(),
        **row,
        "total": val,
        "type": ep.point_type,
    }


def _parse_int(raw, default, lo=None, hi=None):
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return default
    if lo is not None:
        n = max(lo, n)
    if hi is not None:
        n = min(hi, n)
    return n


def _resolve_area_id_to_location_ids(area_id, runs):
    """
    Translate an `area_id` slug to the matching DB location ids.

    Cached because the slug→id mapping changes only when forecasts reload.
    """
    cache_key = f"area_loc_ids:{area_id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    run_ids = [r.id for r in runs]
    run_sector = {r.id: sector_field(r) for r in runs}

    matching = []
    locs = Location.objects.filter(forecast_run_id__in=run_ids).only(
        "id", "source", "forecast_run_id"
    )
    for loc in locs:
        sector = run_sector.get(loc.forecast_run_id, "energy")
        if make_area_id(loc.source, sector) == area_id:
            matching.append(loc.id)

    cache.set(cache_key, matching, CACHE_TTL)
    return matching


class EmissionDataViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    def list(self, request):
        cache_key = f"emissions:{request.query_params.urlencode()}"
        cached = cache.get(cache_key)
        if cached is not None:
            results, total = cached
            response = Response(results)
            response["X-Total-Count"] = str(total)
            return response

        runs = get_active_runs()
        if not runs:
            return Response([])

        run_ids = [r.id for r in runs]
        run_sector = {r.id: sector_field(r) for r in runs}

        queryset = EmissionPoint.objects.filter(
            location__forecast_run_id__in=run_ids,
        ).select_related("location", "location__forecast_run")

        area_id = request.query_params.get("area_id")
        if area_id:
            loc_ids = _resolve_area_id_to_location_ids(area_id, runs)
            queryset = queryset.filter(location_id__in=loc_ids)

        data_type = request.query_params.get("data_type")
        if data_type:
            queryset = queryset.filter(point_type=data_type)

        start_date = request.query_params.get("start_date")
        if start_date:
            queryset = queryset.filter(date__gte=start_date)

        end_date = request.query_params.get("end_date")
        if end_date:
            queryset = queryset.filter(date__lte=end_date)

        queryset = queryset.order_by("-date")

        # Pagination — default 500/page, clamp at 5000 so no client can request
        # the whole table.
        limit = _parse_int(
            request.query_params.get("limit"),
            default=DEFAULT_LIMIT,
            lo=1,
            hi=MAX_LIMIT,
        )
        offset = _parse_int(request.query_params.get("offset"), default=0, lo=0)

        total = queryset.count()
        page = queryset[offset : offset + limit]
        results = [_serialize(ep, run_sector) for ep in page]

        cache.set(cache_key, (results, total), CACHE_TTL)
        response = Response(results)
        response["X-Total-Count"] = str(total)
        return response

    def retrieve(self, request, pk=None):
        runs = get_active_runs()
        if not runs:
            return Response({"detail": "Not found."}, status=404)

        run_ids = [r.id for r in runs]
        run_sector = {r.id: sector_field(r) for r in runs}

        try:
            ep = EmissionPoint.objects.select_related(
                "location", "location__forecast_run"
            ).get(pk=pk, location__forecast_run_id__in=run_ids)
        except EmissionPoint.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)

        return Response(_serialize(ep, run_sector))
