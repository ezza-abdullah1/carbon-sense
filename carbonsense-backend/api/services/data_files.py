"""
Per-UC sector builders that read forecast JSON files in `data/`.

The dashboard's UC-summary endpoint joins four files (transport, buildings,
waste, industry) at request time. Parsing is expensive — these files run
into the megabytes — so each file is parsed once per worker and held in an
in-process dict (`_json_cache`). After the first request, all subsequent
ones are dict lookups.

The energy total still comes from the DB but uses an aggregate query, not
a per-location loop.
"""

import json
import math
import os

from django.conf import settings
from django.db.models import Sum

from api.models import EmissionPoint, Location

from .runs import get_active_runs, safe_float, sector_field


DATA_DIR = os.path.join(settings.BASE_DIR, "data")

_json_cache: dict = {}


def load_data_file(filename):
    """Load + cache a JSON file under `data/`."""
    if filename not in _json_cache:
        with open(os.path.join(DATA_DIR, filename), encoding="utf-8") as f:
            _json_cache[filename] = json.load(f)
    return _json_cache[filename]


# ----------------------------------------------------------------------------
# Per-sector UC builders. Each returns a {uc_code: {…}} dict keyed by code.
# ----------------------------------------------------------------------------


def build_transport_by_uc(data_type):
    """Transport: 151 UCs from carbonsense_transport_v16.json."""
    data = load_data_file("carbonsense_transport_v16.json")
    result = {}
    for uc in data.get("uc_emissions", []):
        code = uc.get("uc_code", "")
        sw = uc.get("spatial_weights", {})

        if data_type == "forecast":
            fc = uc.get("forecast", {})
            monthly = fc.get("monthly_t", [])
            result[code] = {
                "annual_t": safe_float(fc.get("annual_t")),
                "road_annual_t": safe_float(fc.get("road_annual_t")),
                "dom_avi_annual_t": safe_float(fc.get("dom_avi_annual_t")),
                "intl_avi_annual_t": safe_float(fc.get("intl_avi_annual_t")),
                "rail_annual_t": safe_float(fc.get("rail_annual_t")),
                "road_pct": safe_float(fc.get("road_pct")),
                "road_weight": safe_float(sw.get("road_weight")),
                "rail_weight": safe_float(sw.get("rail_weight")),
                "intensity_t_per_km2": safe_float(fc.get("intensity_t_per_km2")),
                "rank_in_division": fc.get("rank_in_division", 0),
                "ci_lower_annual_t": safe_float(fc.get("ci_lower_annual_t")),
                "ci_upper_annual_t": safe_float(fc.get("ci_upper_annual_t")),
                "dominant_source": uc.get("dominant_source", ""),
                "risk_flags": uc.get("risk_flags", []),
                "monthly_t": monthly,
            }
        else:
            hist = uc.get("historical", {})
            series = hist.get("monthly_series", [])
            monthly = [safe_float(m.get("total_t")) for m in series]
            last12 = monthly[-12:] if len(monthly) >= 12 else monthly
            annual = sum(last12)
            result[code] = {
                "annual_t": round(annual, 2),
                "road_annual_t": safe_float(hist.get("road_t")),
                "dom_avi_annual_t": safe_float(hist.get("dom_avi_t")),
                "intl_avi_annual_t": safe_float(hist.get("intl_avi_t")),
                "rail_annual_t": safe_float(hist.get("rail_t")),
                "road_pct": 0.0,
                "road_weight": safe_float(sw.get("road_weight")),
                "rail_weight": safe_float(sw.get("rail_weight")),
                "intensity_t_per_km2": round(
                    annual / max(safe_float(uc.get("area_km2")), 0.01), 1
                ),
                "rank_in_division": 0,
                "ci_lower_annual_t": safe_float(hist.get("ci_lower_t")),
                "ci_upper_annual_t": safe_float(hist.get("ci_upper_t")),
                "dominant_source": uc.get("dominant_source", ""),
                "risk_flags": uc.get("risk_flags", []),
                "monthly_t": monthly,
            }
    return result


def build_buildings_by_uc(data_type):
    """Buildings: 151 UCs from carbonsense_buildings_v15.json."""
    data = load_data_file("carbonsense_buildings_v15.json")
    result = {}
    for uc in data.get("uc_data", []):
        code = uc.get("uc_code", "")
        ae = uc.get("annual_emissions", {})
        risk = uc.get("risk", {})

        series = uc.get("forecast" if data_type == "forecast" else "historical", [])
        monthly_t = []
        monthly_res_t = []
        monthly_nonres_t = []
        for row in (series if isinstance(series, list) else []):
            monthly_t.append(safe_float(row.get("total_t")))
            monthly_res_t.append(safe_float(row.get("residential_t")))
            monthly_nonres_t.append(safe_float(row.get("non_residential_t")))

        if data_type == "historical" and monthly_t:
            last12 = monthly_t[-12:] if len(monthly_t) >= 12 else monthly_t
            total_t = sum(last12)
            res_t = sum(monthly_res_t[-12:]) if monthly_res_t else 0.0
            nonres_t = sum(monthly_nonres_t[-12:]) if monthly_nonres_t else 0.0
        else:
            total_t = safe_float(ae.get("total_t"))
            res_t = safe_float(ae.get("residential_t"))
            nonres_t = safe_float(ae.get("non_residential_t"))

        result[code] = {
            "residential_t": round(res_t, 2),
            "non_residential_t": round(nonres_t, 2),
            "total_t": round(total_t, 2),
            "intensity_t_km2": safe_float(ae.get("intensity_t_km2")),
            "ci_lower_90_t": safe_float(ae.get("ci_lower_90_t")),
            "ci_upper_90_t": safe_float(ae.get("ci_upper_90_t")),
            "rank_in_district": ae.get("rank_in_district", 0),
            "monthly_t": monthly_t,
            "risk": {k: v for k, v in risk.items() if isinstance(v, bool)},
        }
    return result


def build_waste_by_uc(data_type):
    """Waste: 108 UCs from carbonsense_per_location_waste_v2_3.json."""
    data = load_data_file("carbonsense_per_location_waste_v2_3.json")
    alloc = data.get("aggregate_forecast", {}).get("uc_allocation", [])
    result = {}

    for uc in alloc:
        code = uc.get("uc_code", "")
        if not code:
            continue

        if data_type == "forecast":
            em = uc.get("emissions", {})
            cd = uc.get("chart_data", [])
            monthly = [
                safe_float(m.get("predicted")) for m in cd if isinstance(m, dict)
            ]
            result[code] = {
                "annual_t": safe_float(em.get("total_annual_t")),
                "monthly_t": monthly,
                "point_source_t": safe_float(em.get("point_source_t")),
                "solid_waste_t": safe_float(em.get("area_sw_t")),
                "wastewater_t": safe_float(em.get("area_ww_t")),
                "point_pct": safe_float(em.get("point_pct")),
                "risk_level": em.get("risk_level", ""),
                "rank_in_district": uc.get("rank_in_district", 0),
                "intensity_t_per_km2": safe_float(uc.get("intensity_t_per_km2")),
            }
        else:
            hist = uc.get("historical", [])
            ha = uc.get("historical_annual", {})
            monthly = [safe_float(m.get("total_t")) for m in hist]
            result[code] = {
                "annual_t": safe_float(ha.get("total_t")),
                "monthly_t": monthly,
                "point_source_t": safe_float(ha.get("point_source_t")),
                "solid_waste_t": safe_float(ha.get("area_sw_t")),
                "wastewater_t": safe_float(ha.get("area_ww_t")),
                "point_pct": 0.0,
                "risk_level": uc.get("emissions", {}).get("risk_level", ""),
                "rank_in_district": uc.get("rank_in_district", 0),
                "intensity_t_per_km2": safe_float(uc.get("intensity_t_per_km2")),
            }
    return result


def build_industry_uc_mapping():
    """Build UC_XXXX -> PB-LAH-UCYYY mapping via centroid matching (cached)."""
    cache_key = "_industry_uc_mapping"
    if cache_key in _json_cache:
        return _json_cache[cache_key]

    spatial = load_data_file("carbonsense_lahore_spatial_v1.2.json")
    geo_path = os.path.join(DATA_DIR, "lahore_ucs.geojson")
    with open(geo_path, encoding="utf-8") as f:
        geo = json.load(f)

    def _dist(lat1, lon1, lat2, lon2):
        return math.sqrt((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2)

    mapping = {}
    for suc in spatial.get("uc_emissions", []):
        sc = suc["centroid"]
        best_dist = 999
        best_code = ""
        for gf in geo["features"]:
            gp = gf["properties"]
            d = _dist(sc[0], sc[1], gp["centroid_lat"], gp["centroid_lon"])
            if d < best_dist:
                best_dist = d
                best_code = f"PB-LAH-UC{gp['uc_id']:03d}"
        mapping[suc["uc_id"]] = best_code

    _json_cache[cache_key] = mapping
    return mapping


def build_industry_by_uc(data_type):
    """Industry/Manufacturing: 151 UCs from carbonsense_lahore_spatial_v1.2.json."""
    data = load_data_file("carbonsense_lahore_spatial_v1.2.json")
    uc_mapping = build_industry_uc_mapping()
    result = {}

    for suc in data.get("uc_emissions", []):
        uc_code = uc_mapping.get(suc["uc_id"], "")
        if not uc_code:
            continue

        if data_type == "forecast":
            fc = suc.get("forecast", {})
            series = fc.get("monthly_series", [])
            monthly = [safe_float(m.get("total_t")) for m in series]
            result[uc_code] = {
                "annual_t": safe_float(fc.get("annual_total_t")),
                "by_sector": fc.get("by_sector_annual", {}),
                "intensity_t_per_km2": safe_float(fc.get("intensity_t_per_km2")),
                "rank_in_district": fc.get("rank_in_district", 0),
                "ci_lower_t": safe_float(fc.get("annual_ci_lo")),
                "ci_upper_t": safe_float(fc.get("annual_ci_hi")),
                "monthly_t": monthly,
                "dominant_sector": suc.get("dominant_sector", ""),
                "risk_flags": suc.get("risk_flags", []),
            }
        else:
            hist = suc.get("historical", {})
            series = hist.get("monthly_series", [])
            monthly = [safe_float(m.get("total_t")) for m in series]
            last12 = monthly[-12:] if len(monthly) >= 12 else monthly
            annual = sum(last12)
            result[uc_code] = {
                "annual_t": round(annual, 2),
                "by_sector": hist.get("by_sector_total", {}),
                "intensity_t_per_km2": round(
                    annual / max(safe_float(suc.get("area_km2")), 0.01), 1
                ),
                "rank_in_district": 0,
                "ci_lower_t": 0.0,
                "ci_upper_t": 0.0,
                "monthly_t": monthly,
                "dominant_sector": suc.get("dominant_sector", ""),
                "risk_flags": suc.get("risk_flags", []),
            }
    return result


def build_energy_total(data_type):
    """
    Power/Energy: total emissions across all energy point sources.

    Single aggregate query over `EmissionPoint` (was a per-location loop
    that fired one query per site). Falls back to JSON if the DB has no
    energy data for the requested point type.
    """
    energy_run_ids = [
        run.id for run in get_active_runs() if sector_field(run) == "energy"
    ]
    total = 0.0
    if energy_run_ids:
        agg = (
            EmissionPoint.objects.filter(
                location__forecast_run_id__in=energy_run_ids,
                point_type=data_type,
            )
            .aggregate(total=Sum("emissions"))
        )
        total = safe_float(agg.get("total"))

    if total == 0.0:
        try:
            pdata = load_data_file("power_new.json")
            for loc in pdata.get("locations", []):
                for cd in loc.get("chart_data", []):
                    if isinstance(cd, dict) and cd.get("type") == data_type:
                        total += safe_float(cd.get("value"))
        except Exception:
            pass
    return total


def get_monthly_dates(data_type):
    """Return the list of date strings for each sector's monthly_t arrays."""
    t_data = load_data_file("carbonsense_transport_v16.json")
    if data_type == "forecast":
        t_dates = t_data.get("division_total", {}).get("dates", [])
    else:
        first_uc = t_data["uc_emissions"][0] if t_data.get("uc_emissions") else {}
        series = first_uc.get("historical", {}).get("monthly_series", [])
        t_dates = [m["date"] for m in series]

    b_data = load_data_file("carbonsense_buildings_v15.json")
    first_buc = b_data["uc_data"][0] if b_data.get("uc_data") else {}
    b_series = first_buc.get(
        "forecast" if data_type == "forecast" else "historical", []
    )
    b_dates = [row["date"] for row in b_series if isinstance(row, dict)]

    w_data = load_data_file("carbonsense_per_location_waste_v2_3.json")
    alloc = w_data.get("aggregate_forecast", {}).get("uc_allocation", [])
    first_wuc = alloc[0] if alloc else {}
    if data_type == "forecast":
        w_series = first_wuc.get("chart_data", [])
        w_dates = [row["date"] for row in w_series if isinstance(row, dict)]
    else:
        w_series = first_wuc.get("historical", [])
        w_dates = [row["date"] for row in w_series if isinstance(row, dict)]

    i_data = load_data_file("carbonsense_lahore_spatial_v1.2.json")
    first_iuc = i_data["uc_emissions"][0] if i_data.get("uc_emissions") else {}
    if data_type == "forecast":
        i_series = first_iuc.get("forecast", {}).get("monthly_series", [])
    else:
        i_series = first_iuc.get("historical", {}).get("monthly_series", [])
    i_dates = [m["date"] for m in i_series if isinstance(m, dict)]

    return {
        "transport": t_dates,
        "buildings": b_dates,
        "waste": w_dates,
        "industry": i_dates,
    }


def find_month_index(dates, target_month):
    """Index of the first date in `dates` matching `YYYY-MM`. -1 if absent."""
    for i, d in enumerate(dates):
        if d.startswith(target_month):
            return i
    return -1
