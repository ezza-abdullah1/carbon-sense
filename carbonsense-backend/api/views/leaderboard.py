"""Leaderboard — every (sector, location) summary ranked by 12-month forecast."""

from django.core.cache import cache
from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from api.models import LocationSummary, make_area_id
from api.services.runs import CACHE_TTL, get_active_runs, sector_field


_TREND_MAP = {"increasing": "up", "declining": "down", "stable": "stable"}


class LeaderboardViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    def list(self, request):
        cached = cache.get("leaderboard_list")
        if cached is not None:
            return Response(cached)

        runs = get_active_runs()
        if not runs:
            return Response([])

        run_ids = [r.id for r in runs]
        run_sector = {r.id: sector_field(r) for r in runs}

        # Single join: pull every summary across every active run in one query.
        summaries = (
            LocationSummary.objects.filter(location__forecast_run_id__in=run_ids)
            .select_related("location")
        )

        entries = [
            {
                "area_id": make_area_id(
                    s.location.source,
                    run_sector.get(s.location.forecast_run_id, "energy"),
                ),
                "area_name": s.location.source,
                "emissions": s.forecast_12m_average,
                "trend": _TREND_MAP.get(s.trend, "stable"),
                "trend_percentage": abs(s.change_pct),
            }
            for s in summaries
        ]
        entries.sort(key=lambda x: x["emissions"], reverse=True)
        results = [{"rank": i + 1, **e} for i, e in enumerate(entries)]

        cache.set("leaderboard_list", results, CACHE_TTL)
        return Response(results)
