"""
EmissionsAnalyzer — queries the Supabase-backed models (Location,
EmissionPoint, LocationSummary) to produce a structured analysis dict
for the recommendation templates.

NOTE: api.models has TWO possible schemas depending on git branch.
This file uses the NEW schema: ForecastRun, Location, EmissionPoint,
LocationSummary, make_area_id.  If you see an ImportError for AreaInfo,
your api/models.py is on the old branch.
"""

import hashlib

from django.db.models import Avg, Sum
from api.models import (
    ForecastRun, Location, EmissionPoint, LocationSummary, make_area_id,
)

SECTORS = ["transport", "industry", "energy", "waste", "buildings"]

SECTOR_MAP = {
    'power': 'energy',
    'electricity-generation': 'energy',
    'energy': 'energy',
    'transportation': 'transport',
    'transport': 'transport',
    'industrial': 'industry',
    'industry': 'industry',
    'manufacturing': 'industry',
    'waste': 'waste',
    'buildings': 'buildings',
    'residential': 'buildings',
    'commercial': 'buildings',
}


class EmissionsAnalyzer:
    """Queries Django models to analyze emissions data for a given area."""

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #

    def analyze(self, area_id: str) -> dict:
        """Return a comprehensive analysis dict for *area_id*.

        Raises ``ValueError`` if the area does not exist.
        """
        location, sector, run = self._find_location(area_id)
        if not location:
            raise ValueError(f"Area '{area_id}' not found.")

        all_points = EmissionPoint.objects.filter(location=location).order_by("date")
        historical = all_points.filter(point_type="historical")
        forecast = all_points.filter(point_type="forecast")

        hist_count = historical.count()
        forecast_count = forecast.count()

        if not all_points.exists():
            return self._empty_analysis(location, sector)

        hist_total = historical.aggregate(total=Sum("emissions"))["total"] or 0

        sector_totals = self._get_sector_totals(location.source)
        if sector_totals[sector] == 0:
            sector_totals[sector] = round(hist_total, 2)

        total_emissions = sum(sector_totals.values())
        dominant_sector = (
            max(sector_totals, key=sector_totals.get)
            if total_emissions > 0
            else sector
        )

        earliest = all_points.first().date
        latest = all_points.last().date

        trend_direction, trend_pct = self._get_trend(location)

        sector_trends = {s: {"direction": "stable", "percentage": 0.0} for s in SECTORS}
        sector_trends[sector] = {"direction": trend_direction, "percentage": trend_pct}

        forecast_direction = self._forecast_direction(forecast)

        monthly_avg = historical.aggregate(avg=Avg("emissions"))["avg"] or 0
        monthly_averages = {s: 0.0 for s in SECTORS}
        monthly_averages[sector] = round(monthly_avg, 2)

        return {
            "area_name": location.source,
            "coordinates": {"lat": location.latitude, "lng": location.longitude},
            "historical_count": hist_count,
            "forecast_count": forecast_count,
            "sector_totals": sector_totals,
            "dominant_sector": dominant_sector,
            "total_emissions": round(total_emissions, 2),
            "trend_direction": trend_direction,
            "trend_percentage": trend_pct,
            "sector_trends": sector_trends,
            "earliest_date": earliest.strftime("%Y-%m-%d"),
            "latest_date": latest.strftime("%Y-%m-%d"),
            "forecast_direction": forecast_direction,
            "monthly_averages": monthly_averages,
        }

    # ------------------------------------------------------------------ #

    def format_for_prompt(self, analysis: dict) -> str:
        """Compact text block for prompts."""
        total = analysis["total_emissions"]
        sectors = []
        for s in SECTORS:
            val = analysis["sector_totals"].get(s, 0)
            pct = (val / total * 100) if total else 0
            if val > 0:
                sectors.append(f"{s}:{val:.0f}t({pct:.0f}%)")

        trend = analysis["trend_direction"]
        trend_pct = analysis["trend_percentage"]

        return (
            f"Total: {total:.0f}t CO2e | Dominant: {analysis['dominant_sector']} | "
            f"Trend: {trend}({trend_pct:+.1f}%) | Forecast: {analysis['forecast_direction']}\n"
            f"Sectors: {', '.join(sectors)}\n"
            f"Period: {analysis['earliest_date']} to {analysis['latest_date']} "
            f"({analysis['historical_count']} records)"
        )

    def summarize(self, analysis: dict) -> str:
        """Brief human-readable summary (~50 tokens)."""
        total = analysis["total_emissions"]
        dominant = analysis["dominant_sector"]
        trend = analysis["trend_direction"]
        trend_pct = analysis["trend_percentage"]
        forecast = analysis["forecast_direction"]

        sectors = analysis["sector_totals"]
        top_sectors = sorted(sectors.items(), key=lambda x: x[1], reverse=True)[:3]
        sector_parts = [f"{s}: {v:.0f}t" for s, v in top_sectors if v > 0]

        return (
            f"{analysis['area_name']} emits {total:.0f}t CO2e. "
            f"Dominant: {dominant}. Trend: {trend} ({trend_pct:+.1f}%). "
            f"Forecast: {forecast}. Top: {', '.join(sector_parts)}."
        )

    def compute_data_hash(self, area_id: str) -> str:
        """SHA-256 hex digest for cache-invalidation."""
        location, sector, run = self._find_location(area_id)
        if not location:
            raise ValueError(f"Area '{area_id}' not found.")

        latest_records = (
            EmissionPoint.objects.filter(location=location).order_by("-date")[:10]
        )
        parts = [f"{r.date}|{r.point_type}|{r.emissions}" for r in latest_records]
        payload = "\n".join(parts)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------ #
    #  Private helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _find_location(area_id: str):
        """Find Location, sector, and ForecastRun by area_id slug."""
        runs = ForecastRun.objects.filter(is_active=True)
        for run in runs:
            sector = SECTOR_MAP.get(run.sector.lower(), "energy")
            for loc in Location.objects.filter(forecast_run=run):
                if make_area_id(loc.source, sector) == area_id:
                    return loc, sector, run
        return None, None, None

    @staticmethod
    def _get_sector_totals(source_name: str) -> dict:
        """Get emission totals across all sectors for a location name."""
        totals = {s: 0.0 for s in SECTORS}
        runs = ForecastRun.objects.filter(is_active=True)
        for run in runs:
            sector = SECTOR_MAP.get(run.sector.lower(), "energy")
            for loc in Location.objects.filter(forecast_run=run, source=source_name):
                hist_total = EmissionPoint.objects.filter(
                    location=loc, point_type="historical"
                ).aggregate(total=Sum("emissions"))["total"]
                if hist_total:
                    totals[sector] = round(hist_total, 2)
        return totals

    @staticmethod
    def _get_trend(location):
        """Get trend from LocationSummary (pre-computed by Supabase)."""
        try:
            summary = LocationSummary.objects.get(location=location)
            raw_trend = (summary.trend or "stable").lower()
            pct = summary.change_pct or 0

            if "increas" in raw_trend:
                direction = "increasing"
            elif "declin" in raw_trend:
                direction = "decreasing"
            else:
                direction = "stable"

            return direction, round(pct, 2)
        except LocationSummary.DoesNotExist:
            return "stable", 0.0

    @staticmethod
    def _empty_analysis(location, sector):
        """Minimal analysis dict when no emission data exists."""
        zero_sectors = {s: 0.0 for s in SECTORS}
        zero_trends = {s: {"direction": "stable", "percentage": 0.0} for s in SECTORS}
        return {
            "area_name": location.source,
            "coordinates": {"lat": location.latitude, "lng": location.longitude},
            "historical_count": 0,
            "forecast_count": 0,
            "sector_totals": zero_sectors,
            "dominant_sector": sector,
            "total_emissions": 0.0,
            "trend_direction": "stable",
            "trend_percentage": 0.0,
            "sector_trends": zero_trends,
            "earliest_date": "",
            "latest_date": "",
            "forecast_direction": "no_forecast",
            "monthly_averages": {s: 0.0 for s in SECTORS},
        }

    @staticmethod
    def _forecast_direction(forecast_qs):
        """Whether forecasted emissions are going up, down, or flat."""
        ordered = forecast_qs.order_by("date")
        if not ordered.exists():
            return "no_forecast"

        first = ordered.first()
        last = ordered.last()

        if first.pk == last.pk:
            return "stable"
        if first.emissions == 0 and last.emissions == 0:
            return "stable"
        if first.emissions == 0:
            return "increasing" if last.emissions > 0 else "stable"

        pct = (last.emissions - first.emissions) / abs(first.emissions) * 100
        if pct > 1.0:
            return "increasing"
        elif pct < -1.0:
            return "decreasing"
        return "stable"
