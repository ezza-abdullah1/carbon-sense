import hashlib
from datetime import timedelta

from django.db.models import Avg, Sum
from api.models import AreaInfo, EmissionData


SECTORS = ["transport", "industry", "energy", "waste", "buildings"]


class EmissionsAnalyzer:
    """Queries Django models to analyze emissions data for a given area
    and produces a structured context dict for the LLM prompt."""

    # ------------------------------------------------------------------ #
    #  Public API                                                         #
    # ------------------------------------------------------------------ #

    def analyze(self, area_id: str) -> dict:
        """Return a comprehensive analysis dict for *area_id*.

        Raises ``ValueError`` if the area does not exist.
        """
        try:
            area = AreaInfo.objects.get(pk=area_id)
        except AreaInfo.DoesNotExist:
            raise ValueError(f"Area '{area_id}' not found.")

        all_emissions = EmissionData.objects.filter(area=area).order_by("date")
        historical = all_emissions.filter(data_type="historical")
        forecast = all_emissions.filter(data_type="forecast")

        historical_count = historical.count()
        forecast_count = forecast.count()

        # -- empty data fast-path ------------------------------------ #
        if not all_emissions.exists():
            return self._empty_analysis(area)

        # -- sector totals ------------------------------------------- #
        sector_totals = self._sector_totals(historical)
        total_emissions = sum(sector_totals.values())
        dominant_sector = max(sector_totals, key=sector_totals.get)

        # -- date range ---------------------------------------------- #
        earliest_date = all_emissions.first().date
        latest_date = all_emissions.last().date

        # -- overall trend ------------------------------------------- #
        trend_direction, trend_percentage = self._compute_trend(historical)

        # -- per-sector trends --------------------------------------- #
        sector_trends = {}
        for sector in SECTORS:
            direction, pct = self._compute_trend(historical, sector=sector)
            sector_trends[sector] = {
                "direction": direction,
                "percentage": pct,
            }

        # -- forecast direction -------------------------------------- #
        forecast_direction = self._forecast_direction(forecast)

        # -- monthly averages ---------------------------------------- #
        monthly_averages = self._monthly_averages(historical)

        return {
            "area_name": area.name,
            "coordinates": {"lat": area.latitude, "lng": area.longitude},
            "historical_count": historical_count,
            "forecast_count": forecast_count,
            "sector_totals": sector_totals,
            "dominant_sector": dominant_sector,
            "total_emissions": round(total_emissions, 2),
            "trend_direction": trend_direction,
            "trend_percentage": trend_percentage,
            "sector_trends": sector_trends,
            "latest_date": latest_date.strftime("%Y-%m-%d"),
            "earliest_date": earliest_date.strftime("%Y-%m-%d"),
            "forecast_direction": forecast_direction,
            "monthly_averages": monthly_averages,
        }

    # ------------------------------------------------------------------ #

    def format_for_prompt(self, analysis: dict) -> str:
        """Convert an *analysis* dict into a human-readable text block
        suitable for injection into an LLM prompt."""

        lines: list[str] = []

        # -- header -------------------------------------------------- #
        lines.append(f"=== Emissions Analysis: {analysis['area_name']} ===")
        coords = analysis["coordinates"]
        lines.append(f"Location: ({coords['lat']}, {coords['lng']})")
        lines.append("")

        # -- historical summary -------------------------------------- #
        lines.append("-- Historical Data Summary --")
        lines.append(
            f"Date range: {analysis['earliest_date']} to {analysis['latest_date']}"
        )
        lines.append(f"Total historical records: {analysis['historical_count']}")
        lines.append(f"Total forecast records: {analysis['forecast_count']}")
        lines.append("")

        # -- sector breakdown ---------------------------------------- #
        total = analysis["total_emissions"]
        lines.append("-- Sector Breakdown --")
        for sector in SECTORS:
            value = analysis["sector_totals"].get(sector, 0)
            pct = (value / total * 100) if total else 0
            lines.append(f"  {sector.capitalize():12s}: {value:>12.2f}  ({pct:.1f}%)")
        lines.append(f"  {'Total':12s}: {total:>12.2f}")
        lines.append(f"Dominant sector: {analysis['dominant_sector'].capitalize()}")
        lines.append("")

        # -- trend analysis ------------------------------------------ #
        lines.append("-- Trend Analysis --")
        lines.append(
            f"Overall trend: {analysis['trend_direction']} "
            f"({analysis['trend_percentage']:+.1f}% year-over-year)"
        )
        lines.append("Per-sector trends:")
        for sector in SECTORS:
            st = analysis["sector_trends"].get(sector, {})
            direction = st.get("direction", "stable")
            pct = st.get("percentage", 0.0)
            lines.append(
                f"  {sector.capitalize():12s}: {direction} ({pct:+.1f}%)"
            )
        lines.append("")

        # -- forecast ------------------------------------------------ #
        lines.append("-- Forecast --")
        lines.append(f"Forecast direction: {analysis['forecast_direction']}")

        return "\n".join(lines)

    # ------------------------------------------------------------------ #

    def compute_data_hash(self, area_id: str) -> str:
        """Return a SHA-256 hex digest derived from the latest emissions data
        for *area_id*.  Useful for cache-invalidation checks."""
        try:
            area = AreaInfo.objects.get(pk=area_id)
        except AreaInfo.DoesNotExist:
            raise ValueError(f"Area '{area_id}' not found.")

        latest_records = (
            EmissionData.objects.filter(area=area)
            .order_by("-date", "-updated_at")[:10]
        )

        hash_input_parts: list[str] = []
        for record in latest_records:
            hash_input_parts.append(
                f"{record.date}|{record.data_type}|"
                f"{record.transport}|{record.industry}|{record.energy}|"
                f"{record.waste}|{record.buildings}|{record.total}"
            )

        payload = "\n".join(hash_input_parts)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------ #
    #  Private helpers                                                    #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _empty_analysis(area: AreaInfo) -> dict:
        """Return a minimal analysis dict when no emission data exists."""
        zero_sectors = {s: 0.0 for s in SECTORS}
        zero_trends = {
            s: {"direction": "stable", "percentage": 0.0} for s in SECTORS
        }
        return {
            "area_name": area.name,
            "coordinates": {"lat": area.latitude, "lng": area.longitude},
            "historical_count": 0,
            "forecast_count": 0,
            "sector_totals": zero_sectors,
            "dominant_sector": SECTORS[0],
            "total_emissions": 0.0,
            "trend_direction": "stable",
            "trend_percentage": 0.0,
            "sector_trends": zero_trends,
            "latest_date": "",
            "earliest_date": "",
            "forecast_direction": "no_forecast",
            "monthly_averages": {s: 0.0 for s in SECTORS},
        }

    @staticmethod
    def _sector_totals(qs) -> dict:
        """Aggregate sector sums from a queryset of EmissionData."""
        agg = qs.aggregate(
            transport=Sum("transport"),
            industry=Sum("industry"),
            energy=Sum("energy"),
            waste=Sum("waste"),
            buildings=Sum("buildings"),
        )
        return {
            sector: round(agg.get(sector) or 0.0, 2)
            for sector in SECTORS
        }

    @staticmethod
    def _monthly_averages(qs) -> dict:
        """Compute per-sector monthly averages across the queryset."""
        agg = qs.aggregate(
            transport=Avg("transport"),
            industry=Avg("industry"),
            energy=Avg("energy"),
            waste=Avg("waste"),
            buildings=Avg("buildings"),
        )
        return {
            sector: round(agg.get(sector) or 0.0, 2)
            for sector in SECTORS
        }

    @staticmethod
    def _compute_trend(qs, sector: str | None = None) -> tuple[str, float]:
        """Compare the first-year and last-year averages to determine trend.

        Parameters
        ----------
        qs : QuerySet[EmissionData]
            A date-ordered queryset (historical data).
        sector : str, optional
            If given, compute trend for that sector; otherwise use ``total``.

        Returns
        -------
        (direction, percentage) where direction is one of
        ``"increasing"``, ``"decreasing"``, or ``"stable"``
        and percentage is the year-over-year change.
        """
        field = sector if sector else "total"
        ordered = qs.order_by("date")

        if not ordered.exists():
            return ("stable", 0.0)

        first_record = ordered.first()
        last_record = ordered.last()

        if first_record.pk == last_record.pk:
            # Only one data point
            return ("stable", 0.0)

        first_date = first_record.date
        last_date = last_record.date

        # Define the "first year" as the first 365 days and the "last year"
        # as the final 365 days.  When the full range is shorter than two
        # years, split at the midpoint.
        total_days = (last_date - first_date).days
        if total_days <= 0:
            return ("stable", 0.0)

        if total_days >= 730:
            first_year_end = first_date + timedelta(days=365)
            last_year_start = last_date - timedelta(days=365)
        else:
            midpoint = first_date + timedelta(days=total_days // 2)
            first_year_end = midpoint
            last_year_start = midpoint

        first_avg = (
            ordered.filter(date__lte=first_year_end)
            .aggregate(avg=Avg(field))["avg"]
        )
        last_avg = (
            ordered.filter(date__gte=last_year_start)
            .aggregate(avg=Avg(field))["avg"]
        )

        if first_avg is None or last_avg is None or first_avg == 0:
            return ("stable", 0.0)

        pct_change = round((last_avg - first_avg) / abs(first_avg) * 100, 2)

        if pct_change > 1.0:
            direction = "increasing"
        elif pct_change < -1.0:
            direction = "decreasing"
        else:
            direction = "stable"

        return (direction, pct_change)

    @staticmethod
    def _forecast_direction(forecast_qs) -> str:
        """Determine whether forecasted emissions are going up, down, or flat.

        Returns one of ``"increasing"``, ``"decreasing"``, ``"stable"``,
        or ``"no_forecast"``.
        """
        ordered = forecast_qs.order_by("date")

        if not ordered.exists():
            return "no_forecast"

        first = ordered.first()
        last = ordered.last()

        if first.pk == last.pk:
            return "stable"

        if last.total == 0 and first.total == 0:
            return "stable"

        if first.total == 0:
            return "increasing" if last.total > 0 else "stable"

        pct = (last.total - first.total) / abs(first.total) * 100

        if pct > 1.0:
            return "increasing"
        elif pct < -1.0:
            return "decreasing"
        else:
            return "stable"
