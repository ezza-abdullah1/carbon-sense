"""Area (location) endpoints — one entry per forecast location across all sectors."""

from django.core.cache import cache
from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from api.models import Location, LocationSummary, make_area_id
from api.services.runs import CACHE_TTL, get_active_runs, safe_float, sector_field


def _build_area_payload(loc, sector, summary):
    """Shared payload shape for both list and retrieve."""
    lat = safe_float(loc.latitude)
    lng = safe_float(loc.longitude)
    return {
        "id": make_area_id(loc.source, sector),
        "name": loc.source,
        "coordinates": [lat, lng],
        "bounds": [
            [lat - 0.1, lng - 0.1],
            [lat + 0.1, lng + 0.1],
        ],
        "subSectorData": (summary.sub_sector_data if summary else None),
        "ucCode": loc.uc_code or "",
    }


class AreaInfoViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    def list(self, request):
        cached = cache.get("areas_list")
        if cached is not None:
            return Response(cached)

        runs = get_active_runs()
        if not runs:
            return Response([])

        run_ids = [r.id for r in runs]
        run_sector = {r.id: sector_field(r) for r in runs}

        # One query for all locations, one for all summaries — no per-run loop.
        locs = list(Location.objects.filter(forecast_run_id__in=run_ids))
        summary_map = {
            s.location_id: s
            for s in LocationSummary.objects.filter(
                location_id__in=[loc.id for loc in locs]
            )
        }

        results = [
            _build_area_payload(
                loc,
                run_sector.get(loc.forecast_run_id, "energy"),
                summary_map.get(loc.id),
            )
            for loc in locs
        ]

        cache.set("areas_list", results, CACHE_TTL)
        return Response(results)

    def retrieve(self, request, pk=None):
        runs = get_active_runs()
        if not runs:
            return Response({"detail": "Not found."}, status=404)

        run_ids = [r.id for r in runs]
        run_sector = {r.id: sector_field(r) for r in runs}

        # Direct filter using `make_area_id`'s sector suffix to avoid
        # scanning every location.
        # `pk` is `<source_lower_with_underscores>_<sector>` — split off the
        # sector suffix and search by source.
        for sector in {"energy", "transport", "industry", "waste", "buildings"}:
            suffix = f"_{sector}"
            if pk.endswith(suffix):
                source_slug = pk[: -len(suffix)]
                # Match a location whose `make_area_id` matches `pk`. We
                # filter by run_id (active runs) and sector — since
                # different runs may share a `source`, we still verify
                # the slug matches in Python.
                candidates = Location.objects.filter(
                    forecast_run_id__in=run_ids,
                ).only("id", "source", "latitude", "longitude", "uc_code", "forecast_run_id")
                for loc in candidates:
                    loc_sector = run_sector.get(loc.forecast_run_id, "energy")
                    if loc_sector == sector and make_area_id(loc.source, sector) == pk:
                        summary = LocationSummary.objects.filter(
                            location=loc
                        ).first()
                        return Response(_build_area_payload(loc, sector, summary))
                break

        return Response({"detail": "Not found."}, status=404)
