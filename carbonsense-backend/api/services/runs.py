"""
Forecast-run helpers shared by all data endpoints.

`SECTOR_MAP` collapses the many sector aliases the upstream pipelines emit
(`power`, `electricity-generation`, `manufacturing`, …) onto the five
canonical buckets the frontend understands.

`get_active_runs()` is the single source of truth for "which forecast runs
should we show?" — it caches because the answer changes only when somebody
reloads data via `manage.py load_forecast_json`.
"""

import math

from django.core.cache import cache

from api.models import ForecastRun

# Forecasts are stable until a new data load — an hour of cache is fine and
# cuts a lot of repeat DB hits on the dashboard.
CACHE_TTL = 3600


SECTOR_MAP = {
    "power": "energy",
    "electricity-generation": "energy",
    "energy": "energy",
    "transportation": "transport",
    "transport": "transport",
    "industrial": "industry",
    "industry": "industry",
    "manufacturing": "industry",
    "waste": "waste",
    "buildings": "buildings",
    "residential": "buildings",
    "commercial": "buildings",
}


def get_active_runs():
    """Return all currently-active forecast runs (one per sector, cached)."""
    runs = cache.get("active_forecast_runs")
    if runs is None:
        runs = list(ForecastRun.objects.filter(is_active=True))
        if runs:
            cache.set("active_forecast_runs", runs, CACHE_TTL)
    return runs


def sector_field(run):
    """Map a ForecastRun's raw sector string to a canonical bucket."""
    return SECTOR_MAP.get(run.sector.lower(), "energy") if run else "energy"


def safe_float(val, default=0.0):
    """Coerce NaN / inf / None to a numeric default."""
    if val is None or (
        isinstance(val, float) and (math.isnan(val) or math.isinf(val))
    ):
        return default
    return val
