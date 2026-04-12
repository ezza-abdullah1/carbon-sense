"""
CarbonSense Transport v1.5 -- Spatial Disaggregation Pipeline
Lahore District, Punjab, Pakistan

Inputs:
  - carbonsense_transport_v13.json (hierarchical forecast from v1.3 pipeline)
  - Union_Council.shp (+ .dbf, .shx, .prj sidecar files)

Outputs (written to output_dir):
  - carbonsense_transport_v15.json
  - run_audit_v15.json
  - uc_emissions_v15.csv
  - spatial_weights_v15.csv

Data sources (fetched at runtime):
  - Wind climatology from Open-Meteo archive API (with PAKMET fallback)
  - Road network from OSMNX / Overpass API (with distance-decay proxy fallback)
  - Rail network from OSMNX / Overpass API (with hardcoded fallback)
"""

import argparse
import json
import logging
import math
import os
import struct
import time
import urllib.parse
import urllib.request
import warnings
from collections import Counter
from datetime import datetime
from math import asin, atan2, cos, degrees, radians, sin, sqrt
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString, Point
from shapely.ops import unary_union

warnings.filterwarnings("ignore")
os.environ["SHAPE_RESTORE_SHX"] = "YES"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("carbonsense.v15")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

AIRPORT_LAT, AIRPORT_LON = 31.521601, 74.403603
AIRPORT_NAME = "Allama Iqbal International Airport"
LTO_HEIGHT_M = 100
PG_CLASS = "D"
RAIL_EF_KG_PER_TKM = 0.028
FORECAST_YEAR = 2026
N_FORECAST_MONTHS = 12
LAHORE_CENTER_LAT, LAHORE_CENTER_LON = 31.5204, 74.3587

LAHORE_DIVISION_DISTRICTS = {"Lahore"}
SCOPE_NAME = (
    "Lahore District"
    if LAHORE_DIVISION_DISTRICTS == {"Lahore"}
    else "Lahore Division"
)

ROAD_TYPE_WEIGHTS = {
    "motorway": 12.0, "motorway_link": 10.0,
    "trunk": 8.0, "trunk_link": 6.5,
    "primary": 5.0, "primary_link": 4.0,
    "secondary": 2.0, "secondary_link": 1.5,
    "tertiary": 1.2, "tertiary_link": 1.0,
    "residential": 1.0, "living_street": 0.8, "unclassified": 0.9,
}

SUB_SECTOR_CI = {"road": 0.04, "dom_avi": 0.10, "intl_avi": 0.13, "railways": 0.20}

LAHORE_EXPECTED_JAN_DIR = 310
WIND_DIR_TOL = 90

_LAT_KM = 111.0
_LON_KM = 111.0 * math.cos(math.radians(31.5))

# PEPA core monitoring stations (Gulberg, Jail Road, Township, Town Hall)
_PEPA_STATIONS = [
    (31.5016, 74.3492),
    (31.5204, 74.3268),
    (31.4714, 74.3097),
    (31.5497, 74.3436),
]
_PEPA_RADIUS_KM = 5.0


# ---------------------------------------------------------------------------
# Run audit log (populated during execution)
# ---------------------------------------------------------------------------

def _make_run_log():
    return {
        "pipeline_version": "1.5",
        "run_timestamp": datetime.utcnow().isoformat() + "Z",
        "data_sources": {},
        "api_attempts": {},
        "assertions": {},
        "warnings": [],
        "errors": [],
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _log_source(run_log, key, source, detail=""):
    run_log["data_sources"][key] = {"source": source, "detail": detail}
    logger.info(f"[DATA] {key}: {source}" + (f" -- {detail}" if detail else ""))


def _log_api(run_log, name, status, detail=""):
    run_log["api_attempts"][name] = {"status": status, "detail": detail}
    logger.log(
        logging.INFO if status == "SUCCESS" else logging.WARNING,
        f"[API]  {name}: {status}" + (f" -- {detail}" if detail else ""),
    )


def haversine(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * R * asin(sqrt(a))


def compass_bearing(lat1, lon1, lat2, lon2) -> float:
    dlon = radians(lon2 - lon1)
    x = sin(dlon) * cos(radians(lat2))
    y = cos(radians(lat1)) * sin(radians(lat2)) - sin(radians(lat1)) * cos(
        radians(lat2)
    ) * cos(dlon)
    return (degrees(atan2(x, y)) + 360) % 360


def _get_road_weight(hw) -> float:
    if isinstance(hw, list):
        return max(ROAD_TYPE_WEIGHTS.get(str(t), 0.9) for t in hw)
    return ROAD_TYPE_WEIGHTS.get(str(hw), 0.9)


# ---------------------------------------------------------------------------
# Section 1: Load v1.3 JSON
# ---------------------------------------------------------------------------

def load_v13_json(v13_json_path: str, features_csv_path: str | None, run_log: dict):
    """Load hierarchical forecast from v1.3 JSON and optional features CSV."""
    logger.info("[S1] Loading v1.3 JSON...")

    v13_path = Path(v13_json_path)
    if not v13_path.exists():
        raise FileNotFoundError(
            f"v1.3 JSON not found at {v13_json_path}. Run v1.3 pipeline first."
        )

    with open(v13_path) as f:
        v13 = json.load(f)
    logger.info(f"Loaded v1.3 JSON: {v13_path.stat().st_size / 1e3:.1f} KB")

    hfc = v13["hierarchical_forecast"]
    future_dates = pd.DatetimeIndex(hfc["dates"])
    total_fc = np.array(hfc["total_t"], dtype=float)
    road_fc = np.array(hfc["road_t"], dtype=float)
    dom_avi_fc = np.array(hfc["dom_avi_t"], dtype=float)
    intl_avi_fc = np.array(hfc["intl_avi_t"], dtype=float)
    railways_fc = np.array(hfc["railways_t"], dtype=float)

    # Pro-rata closure correction if sub-sectors don't sum to total
    fc_sum = road_fc + dom_avi_fc + intl_avi_fc + railways_fc
    if np.abs(fc_sum - total_fc).max() > 1.0:
        _scale = total_fc / (fc_sum + 1e-9)
        road_fc *= _scale
        dom_avi_fc *= _scale
        intl_avi_fc *= _scale
        railways_fc *= _scale
        logger.info(
            f"[S1] Closure correction applied (max err was {np.abs(fc_sum - total_fc).max():.1f} t)"
        )

    # Per-sector CI
    def _sector_ci(fc, key):
        s = SUB_SECTOR_CI[key]
        return np.round(fc * (1 - s), 2), np.round(fc * (1 + s), 2)

    if hfc.get("ci_lower_t") and len(hfc["ci_lower_t"]) == N_FORECAST_MONTHS:
        ci_total_lower = np.array(hfc["ci_lower_t"], dtype=float)
        ci_total_upper = np.array(hfc["ci_upper_t"], dtype=float)
        ci_source = "Prophet 95% CI from v1.3 JSON"
    else:
        lo_r, hi_r = _sector_ci(road_fc, "road")
        lo_d, hi_d = _sector_ci(dom_avi_fc, "dom_avi")
        lo_i, hi_i = _sector_ci(intl_avi_fc, "intl_avi")
        lo_rl, hi_rl = _sector_ci(railways_fc, "railways")
        ci_total_lower = lo_r + lo_d + lo_i + lo_rl
        ci_total_upper = hi_r + hi_d + hi_i + hi_rl
        ci_source = "Per-sector scales (road+-4%, dom_avi+-10%, intl_avi+-13%, rail+-20%)"
        run_log["warnings"].append(
            "ci_lower_t absent in v1.3 JSON -- per-sector scales used"
        )
    _log_source(run_log, "forecast_ci", ci_source)

    # YOY vs 2025 actual
    feat_path = Path(features_csv_path) if features_csv_path else None
    if feat_path and feat_path.exists():
        df_feat = pd.read_csv(feat_path, index_col=0, parse_dates=True)
        last_year_mean = df_feat["y"].iloc[-12:].mean()
        vkt_growth_pct = round(
            (df_feat["y"].iloc[-1] - df_feat["y"].iloc[0])
            / df_feat["y"].iloc[0]
            * 100,
            1,
        )
        monthly_mean = df_feat["y"].groupby(df_feat.index.month).mean()
        peak_month_name = pd.Timestamp(
            f"2000-{int(monthly_mean.idxmax()):02d}-01"
        ).strftime("%B")
    else:
        road_pct = v13["sub_sector_share"]["road"]["pct_of_total"] / 100
        last_year_mean = v13["sub_sector_share"]["road"]["mean_monthly_t"] / road_pct
        vkt_growth_pct = None
        peak_month_name = "July"
        run_log["warnings"].append("transport_features_v13.csv not found")

    yoy_pct = round((total_fc.mean() / last_year_mean - 1) * 100, 1)
    forecast_peak_month = pd.Timestamp(
        f"2000-{int(total_fc.argmax()) + 1:02d}-01"
    ).strftime("%B")

    return {
        "v13": v13,
        "future_dates": future_dates,
        "total_fc": total_fc,
        "road_fc": road_fc,
        "dom_avi_fc": dom_avi_fc,
        "intl_avi_fc": intl_avi_fc,
        "railways_fc": railways_fc,
        "ci_total_lower": ci_total_lower,
        "ci_total_upper": ci_total_upper,
        "ci_source": ci_source,
        "yoy_pct": yoy_pct,
        "vkt_growth_pct": vkt_growth_pct,
        "peak_month_name": peak_month_name,
        "forecast_peak_month": forecast_peak_month,
    }


# ---------------------------------------------------------------------------
# Section 2: UC Registry
# ---------------------------------------------------------------------------

def _parse_dbf(shp):
    with open(str(Path(shp).with_suffix(".dbf")), "rb") as f:
        f.seek(4)
        n = struct.unpack("<i", f.read(4))[0]
        hs = struct.unpack("<H", f.read(2))[0]
        rs = struct.unpack("<H", f.read(2))[0]
        f.seek(32)
        fields = []
        while True:
            raw = f.read(32)
            if not raw or raw[0] == 0x0D:
                break
            fields.append(
                (
                    raw[:11].decode("utf-8", errors="replace").rstrip("\x00"),
                    chr(raw[11]),
                    raw[16],
                )
            )
        rows = []
        for i in range(n):
            f.seek(hs + i * rs + 1)
            rows.append(
                {
                    "_idx": i,
                    **{
                        fn: f.read(fl).decode("utf-8", errors="replace").strip()
                        for fn, ft, fl in fields
                    },
                }
            )
    return fields, rows


def _shp_centroids(shp, indices):
    with open(str(Path(shp).with_suffix(".shx")), "rb") as f:
        f.seek(100)
        shx = f.read()
    offsets = [
        struct.unpack(">i", shx[i * 8 : i * 8 + 4])[0] * 2
        for i in range(len(shx) // 8)
    ]
    lats, lons = [], []
    with open(str(shp), "rb") as f:
        for idx in indices:
            f.seek(offsets[idx] + 8)
            stype = struct.unpack("<i", f.read(4))[0]
            if stype == 5:
                xmn, ymn, xmx, ymx = struct.unpack("<4d", f.read(32))
                lats.append((ymn + ymx) / 2)
                lons.append((xmn + xmx) / 2)
            else:
                lats.append(None)
                lons.append(None)
    return np.array(lats, dtype=float), np.array(lons, dtype=float)


def load_uc_registry(shp_path: str):
    """Load Union Council registry from shapefile. Returns (gdf_geo, df_uc)."""
    logger.info("[S2] Loading UC registry from Union_Council.shp...")

    shp = Path(shp_path)
    for ext in [".dbf", ".shx"]:
        if not shp.with_suffix(ext).exists():
            raise FileNotFoundError(f"Missing: {shp.with_suffix(ext).name}")

    gdf_geo = None

    try:
        gdf = gpd.read_file(str(shp))
        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326")
        elif gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs("EPSG:4326")

        gdf_ld = gdf[gdf["DISTRICT"].isin(LAHORE_DIVISION_DISTRICTS)].copy()
        if len(gdf_ld) == 0:
            gdf["_D"] = gdf["DISTRICT"].str.strip().str.title()
            gdf_ld = gdf[
                gdf["_D"].isin({d.strip().title() for d in LAHORE_DIVISION_DISTRICTS})
            ].drop(columns=["_D"])

        gdf_utm = gdf_ld.to_crs("EPSG:32642")
        area_km2 = (gdf_utm.geometry.area / 1e6).values
        cents = gdf_utm.geometry.centroid.to_crs("EPSG:4326")
        clat, clon = cents.y.values, cents.x.values

        uc_names_raw = (
            gdf_ld.get("UC_NAME", pd.Series([""] * len(gdf_ld))).fillna("").values
        )
        uc_col = gdf_ld.get("UC", pd.Series([""] * len(gdf_ld))).fillna("").values
        uc_names = np.where(
            (uc_names_raw == "") | (uc_names_raw == "0"), uc_col, uc_names_raw
        )

        tehsil = (
            gdf_ld.get("TEHSIL", pd.Series([""] * len(gdf_ld))).fillna("").values
        )
        district = gdf_ld["DISTRICT"].values
        n = len(gdf_ld)
        load_method = "geopandas"

    except Exception as e:
        logger.warning(f"geopandas load failed ({e}) -- pure-Python fallback")
        _, all_rows = _parse_dbf(shp)
        lahore_rows = [
            r for r in all_rows if r.get("DISTRICT", "").strip() == "Lahore"
        ]
        n = len(lahore_rows)
        clat, clon = _shp_centroids(shp, [r["_idx"] for r in lahore_rows])
        area_km2 = np.clip(
            [
                float(r.get("Shape_Area", 0) or 0) * _LAT_KM * _LON_KM
                for r in lahore_rows
            ],
            0.01,
            None,
        )
        uc_names = np.array(
            [
                r.get("UC_NAME", "").strip() or r.get("UC", "").strip()
                for r in lahore_rows
            ]
        )
        tehsil = np.array([r.get("TEHSIL", "").strip() for r in lahore_rows])
        district = np.array(
            [r.get("DISTRICT", "Lahore") for r in lahore_rows]
        )
        gdf_ld = None
        load_method = "pure-python"

    # Sort for reproducible uc_code assignment
    si = np.lexsort((clon, clat))
    clat, clon, area_km2, uc_names, tehsil, district = (
        clat[si],
        clon[si],
        np.array(area_km2)[si],
        np.array(uc_names)[si],
        np.array(tehsil)[si],
        np.array(district)[si],
    )
    if gdf_ld is not None:
        gdf_ld = gdf_ld.iloc[si].reset_index(drop=True)

    uc_codes = [f"PB-LAH-UC{i + 1:03d}" for i in range(n)]
    dist_l = [
        haversine(la, lo, LAHORE_CENTER_LAT, LAHORE_CENTER_LON)
        for la, lo in zip(clat, clon)
    ]
    dist_a = [
        haversine(la, lo, AIRPORT_LAT, AIRPORT_LON)
        for la, lo in zip(clat, clon)
    ]

    df_uc = pd.DataFrame(
        {
            "uc_code": uc_codes,
            "uc_name": uc_names,
            "district": district,
            "tehsil": tehsil,
            "centroid_lat": np.round(clat, 6),
            "centroid_lon": np.round(clon, 6),
            "area_km2": np.round(area_km2, 3),
            "dist_lahore_km": np.round(dist_l, 2),
            "dist_airport_km": np.round(dist_a, 2),
        }
    )

    assert df_uc["area_km2"].min() > 0
    assert df_uc["centroid_lat"].between(30.0, 33.0).all()
    assert df_uc["centroid_lon"].between(72.0, 77.0).all()
    assert df_uc["uc_code"].nunique() == len(df_uc)

    # Attach uc_code to GeoDataFrame for spatial joins
    if gdf_ld is not None:
        gdf_geo = gdf_ld.copy()
        gdf_geo["uc_code"] = uc_codes
        gdf_geo["uc_name"] = uc_names
        gdf_geo["area_km2"] = area_km2
        gdf_geo["centroid_lat"] = clat
        gdf_geo["centroid_lon"] = clon

    logger.info(
        f"[S2] {n} UCs loaded via [{load_method}]  uc_code on gdf: {gdf_geo is not None}"
    )
    return gdf_geo, df_uc


# ---------------------------------------------------------------------------
# Section 3: Road Weights (OSMNX -> Overpass bulk -> proxy)
# ---------------------------------------------------------------------------

def build_road_weights_osmnx(gdf_uc, df_uc, ld_bbox, run_log):
    try:
        import osmnx as ox
    except ImportError:
        logger.warning("[S3] osmnx not installed: pip install osmnx")
        return None

    ox.settings.user_agent = "CarbonSense_Spatial_Intelligence_v1.5"
    ox.settings.timeout = 300

    if "uc_code" not in gdf_uc.columns:
        if len(gdf_uc) == len(df_uc):
            gdf_uc = gdf_uc.copy()
            gdf_uc["uc_code"] = df_uc["uc_code"].values
        else:
            return None

    try:
        poly = unary_union(gdf_uc.geometry)
    except Exception:
        from shapely.geometry import box as shp_box
        poly = shp_box(*ld_bbox)

    try:
        G = ox.graph_from_polygon(poly, network_type="drive", retain_all=False)
    except Exception as e:
        logger.warning(f"[S3] graph_from_polygon failed ({e}), trying bbox...")
        try:
            G = ox.graph_from_bbox(
                north=ld_bbox[3],
                south=ld_bbox[1],
                east=ld_bbox[2],
                west=ld_bbox[0],
                network_type="drive",
            )
        except Exception as e2:
            logger.warning(f"[S3] bbox also failed: {e2}")
            return None

    edges = ox.graph_to_gdfs(G, nodes=False).reset_index()
    edges["wt_len"] = edges["length"] * edges["highway"].apply(_get_road_weight)

    uc_utm = gdf_uc[["uc_code", "geometry"]].to_crs("EPSG:32642")
    joined = gpd.sjoin(
        edges[["wt_len", "geometry"]].to_crs("EPSG:32642"),
        uc_utm,
        how="left",
        predicate="intersects",
    ).dropna(subset=["uc_code"])
    scores = joined.groupby("uc_code")["wt_len"].sum()
    total = scores.sum()
    if total <= 0:
        return None

    floor = scores[scores > 0].min() * 0.01
    scores = scores.reindex(df_uc["uc_code"]).fillna(floor)
    weights = (scores / scores.sum()).rename("road_weight")
    _log_api(
        run_log,
        "OSMNX",
        "SUCCESS",
        f"top={weights.idxmax()} ({weights.max() * 100:.2f}%)",
    )
    return weights


def build_road_weights_overpass_bulk(df_uc, gdf_uc, bbox, run_log):
    lon_min, lat_min, lon_max, lat_max = bbox
    ROAD_FILTER = '["highway"]["highway"!~"footway|path|cycleway|steps|service|track"]'
    query = (
        f"[out:json][timeout:90];(way{ROAD_FILTER}"
        f"({lat_min:.4f},{lon_min:.4f},{lat_max:.4f},{lon_max:.4f}););out geom;"
    )
    try:
        data = ("data=" + urllib.parse.quote(query)).encode()
        req = urllib.request.Request(
            "https://overpass-api.de/api/interpreter",
            data=data,
            headers={
                "User-Agent": "CarbonSense/1.5",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
    except Exception as e:
        logger.warning(f"[S3] Overpass failed: {e}")
        return None

    ways = [e for e in result.get("elements", []) if e.get("type") == "way"]
    if not ways:
        return None

    rows = []
    for way in ways:
        if "geometry" not in way:
            continue
        coords = [(n["lon"], n["lat"]) for n in way["geometry"]]
        if len(coords) < 2:
            continue
        hw = way.get("tags", {}).get("highway", "unclassified")
        rows.append({"wt": _get_road_weight(hw), "geometry": LineString(coords)})

    if not rows:
        return None

    roads_gdf = gpd.GeoDataFrame(rows, crs="EPSG:4326").to_crs("EPSG:32642")
    roads_gdf["wt_len"] = roads_gdf.geometry.length / 1000 * roads_gdf["wt"]

    # Build UC layer
    if gdf_uc is not None and "uc_code" in gdf_uc.columns:
        uc_layer = gdf_uc[["uc_code", "geometry"]].to_crs("EPSG:32642")
    elif gdf_uc is not None and len(gdf_uc) == len(df_uc):
        _g = gdf_uc.copy()
        _g["uc_code"] = df_uc["uc_code"].values
        uc_layer = _g[["uc_code", "geometry"]].to_crs("EPSG:32642")
    else:
        from shapely.geometry import box as shp_box

        half = 0.018
        geoms = [
            shp_box(lo - half, la - half, lo + half, la + half)
            for la, lo in zip(df_uc["centroid_lat"], df_uc["centroid_lon"])
        ]
        uc_layer = gpd.GeoDataFrame(
            {"uc_code": df_uc["uc_code"], "geometry": geoms}, crs="EPSG:4326"
        ).to_crs("EPSG:32642")

    joined = gpd.sjoin(
        roads_gdf, uc_layer, how="left", predicate="intersects"
    ).dropna(subset=["uc_code"])
    scores = joined.groupby("uc_code")["wt_len"].sum()
    total = scores.sum()
    if total <= 0:
        return None

    floor = scores[scores > 0].min() * 0.01
    scores = scores.reindex(df_uc["uc_code"]).fillna(floor)
    weights = (scores / scores.sum()).rename("road_weight")
    _log_api(
        run_log,
        "Overpass_bulk",
        "SUCCESS",
        f"top={weights.idxmax()} ({weights.max() * 100:.2f}%)",
    )
    return weights


def build_road_weights_proxy(df_uc):
    logger.warning("[S3] Both OSM sources unavailable -- distance-decay proxy")
    decay = 1.0 / (1 + df_uc["dist_lahore_km"] / 8) ** 1.5
    scores = decay * df_uc["area_km2"]
    return pd.Series(
        (scores / scores.sum()).values, index=df_uc["uc_code"], name="road_weight"
    )


def compute_road_weights(gdf_uc_geo, df_uc, ld_bbox, run_log):
    """Try OSMNX -> Overpass bulk -> proxy. Returns (weights, source_str)."""
    logger.info("[S3] Road weight engine...")

    w_road = None
    road_source = ""

    if gdf_uc_geo is not None:
        _t0 = time.time()
        w_road = build_road_weights_osmnx(gdf_uc_geo, df_uc, ld_bbox, run_log)
        if w_road is not None:
            road_source = f"OSMNX graph_from_polygon + ROAD_TYPE_WEIGHTS | {time.time() - _t0:.0f}s"
            _log_source(run_log, "road_weights", road_source)

    if w_road is None:
        _t0 = time.time()
        w_road = build_road_weights_overpass_bulk(df_uc, gdf_uc_geo, ld_bbox, run_log)
        if w_road is not None:
            road_source = f"Overpass bulk + ROAD_TYPE_WEIGHTS sjoin | {time.time() - _t0:.0f}s"
            _log_source(run_log, "road_weights", road_source)

    if w_road is None:
        w_road = build_road_weights_proxy(df_uc)
        road_source = "distance-decay proxy (OSM unavailable)"
        _log_source(run_log, "road_weights", road_source)

    w_road = (w_road / w_road.sum()).rename("road_weight")
    logger.info(f"  Road engine: {road_source[:70]}")
    return w_road, road_source


# ---------------------------------------------------------------------------
# Section 4: Aviation Weights
# ---------------------------------------------------------------------------

def _lahore_climatology() -> dict:
    return {
        1: {"speed": 6.2, "from_deg": 310},
        2: {"speed": 6.8, "from_deg": 300},
        3: {"speed": 7.5, "from_deg": 285},
        4: {"speed": 8.5, "from_deg": 270},
        5: {"speed": 9.0, "from_deg": 220},
        6: {"speed": 9.5, "from_deg": 200},
        7: {"speed": 9.2, "from_deg": 195},
        8: {"speed": 8.0, "from_deg": 210},
        9: {"speed": 7.0, "from_deg": 240},
        10: {"speed": 6.5, "from_deg": 280},
        11: {"speed": 5.8, "from_deg": 315},
        12: {"speed": 5.5, "from_deg": 330},
    }


def fetch_wind_openmeteo(lat, lon, run_log) -> dict | None:
    try:
        import openmeteo_requests
        import requests_cache
        from retry_requests import retry

        cache = requests_cache.CachedSession(".cache_wind_v15", expire_after=-1)
        session = retry(cache, retries=3, backoff_factor=0.4)
        oc = openmeteo_requests.Client(session=session)
        resp = oc.weather_api(
            "https://archive-api.open-meteo.com/v1/archive",
            params={
                "latitude": lat,
                "longitude": lon,
                "start_date": "2021-01-01",
                "end_date": "2025-12-31",
                "hourly": ["wind_speed_10m", "wind_direction_10m"],
                "timezone": "Asia/Karachi",
            },
        )[0]
        hourly = resp.Hourly()
        dates = pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left",
        ).tz_localize(None)
        wh = pd.DataFrame(
            {
                "speed": hourly.Variables(0).ValuesAsNumpy(),
                "dir": hourly.Variables(1).ValuesAsNumpy(),
            },
            index=dates,
        )
        wh["month"] = wh.index.month
        clim = wh.groupby("month").agg(speed=("speed", "mean"), from_deg=("dir", "mean"))
        result = {
            m: {
                "speed": round(float(clim.loc[m, "speed"]), 2),
                "from_deg": round(float(clim.loc[m, "from_deg"]), 1),
            }
            for m in range(1, 13)
        }

        # Plausibility check
        jan_dir = result[1]["from_deg"]
        ddiff = min(
            abs(jan_dir - LAHORE_EXPECTED_JAN_DIR) % 360,
            360 - abs(jan_dir - LAHORE_EXPECTED_JAN_DIR) % 360,
        )
        if ddiff > WIND_DIR_TOL:
            logger.warning(
                f"[S4] Jan wind {jan_dir} differs from PAKMET {LAHORE_EXPECTED_JAN_DIR} "
                f"by {ddiff} -- TO/FROM mismatch, using climatology"
            )
            run_log["warnings"].append(
                f"wind_plausibility_fail: Jan={jan_dir} expected~{LAHORE_EXPECTED_JAN_DIR}"
            )
            return None
        return result
    except Exception as e:
        logger.warning(f"[S4] Open-Meteo failed: {e}")
        return None


def _avi_weight_point(x_km, y_km, area_km2, wind_deg, r_mix=15.0):
    r = max(math.sqrt(x_km**2 + y_km**2), 0.1)
    base = area_km2 if r <= r_mix else area_km2 / (r / r_mix) ** 2
    plume = (wind_deg + 180) % 360
    uc_a = (math.degrees(math.atan2(y_km, x_km)) + 360) % 360
    adiff = min(abs(plume - uc_a) % 360, 360 - abs(plume - uc_a) % 360)
    return base * (1.0 + 0.2 * math.cos(math.radians(adiff)))


def _avi_weight_for_uc(uc_row, geom, wind_deg, n_grid=4):
    def _score_pt(lat, lon):
        dist = haversine(AIRPORT_LAT, AIRPORT_LON, lat, lon)
        brng = compass_bearing(AIRPORT_LAT, AIRPORT_LON, lat, lon)
        pb = (wind_deg + 180) % 360
        ang = math.radians(brng - pb)
        return _avi_weight_point(
            dist * math.cos(ang), dist * math.sin(ang), 1.0, wind_deg
        )

    if geom is None:
        return (
            _score_pt(uc_row["centroid_lat"], uc_row["centroid_lon"])
            * uc_row["area_km2"]
        )

    minx, miny, maxx, maxy = geom.bounds
    xs = np.linspace(minx, maxx, n_grid)
    ys = np.linspace(miny, maxy, n_grid)
    scores = [
        _score_pt(py, px)
        for px in xs
        for py in ys
        if geom.contains(Point(px, py))
    ]
    if not scores:
        return (
            _score_pt(uc_row["centroid_lat"], uc_row["centroid_lon"])
            * uc_row["area_km2"]
        )
    return np.mean(scores) * uc_row["area_km2"]


def compute_aviation_weights(gdf_uc_geo, df_uc, run_log):
    """Compute monthly aviation weight vectors. Returns (avi_weights dict, wind_clim, wind_source)."""
    logger.info("[S4] Aviation weight engine...")

    wind_api = fetch_wind_openmeteo(LAHORE_CENTER_LAT, LAHORE_CENTER_LON, run_log)
    if wind_api:
        wind_clim = wind_api
        wind_source = "Open-Meteo archive API (plausibility-checked)"
        _log_api(run_log, "Open-Meteo", "SUCCESS", f"Jan={wind_clim[1]['from_deg']}")
    else:
        wind_clim = _lahore_climatology()
        wind_source = "PAKMET Lahore climatology fallback"
        _log_api(run_log, "Open-Meteo", "FALLBACK")
    _log_source(run_log, "wind_climatology", wind_source)

    # Build geometry lookup
    _uc_geom = {}
    if gdf_uc_geo is not None:
        for _, gr in gdf_uc_geo.iterrows():
            if "uc_code" in gr:
                _uc_geom[gr["uc_code"]] = gr.geometry

    avi_weights: dict[int, pd.Series] = {}
    for month_idx, wind in wind_clim.items():
        scores = np.zeros(len(df_uc))
        for i, row in df_uc.iterrows():
            scores[i] = _avi_weight_for_uc(
                row, _uc_geom.get(row["uc_code"]), wind["from_deg"]
            )
        total = scores.sum()
        avi_weights[month_idx] = pd.Series(
            scores / total if total > 0 else np.ones(len(df_uc)) / len(df_uc),
            index=df_uc["uc_code"],
        )

    return avi_weights, wind_clim, wind_source


# ---------------------------------------------------------------------------
# Section 5: Railway Weights
# ---------------------------------------------------------------------------

def _normalise_way(way_geom) -> list:
    """Overpass geometry is [{lon:x,lat:y}] -- swap to (lat,lon) for haversine."""
    return [(n["lat"], n["lon"]) for n in way_geom]


def fetch_rail_osmnx(gdf_uc, bbox, run_log) -> list | None:
    try:
        import osmnx as ox

        ox.settings.user_agent = "CarbonSense_Spatial_Intelligence_v1.5"
        poly = unary_union(gdf_uc.geometry) if gdf_uc is not None else None
        if poly is None:
            from shapely.geometry import box as shp_box
            poly = shp_box(*bbox)
        rail = ox.features_from_polygon(
            poly, tags={"railway": ["rail", "light_rail"]}
        )
        lines = rail[rail.geometry.geom_type.isin(["LineString", "MultiLineString"])]
        if len(lines) == 0:
            return None
        pts = []
        for geom in lines.geometry:
            if geom.geom_type == "LineString":
                pts.extend([(lat, lon) for lon, lat in geom.coords])
            elif geom.geom_type == "MultiLineString":
                for ln in geom.geoms:
                    pts.extend([(lat, lon) for lon, lat in ln.coords])
        result = sorted(set(pts), key=lambda p: p[0])
        _log_api(
            run_log,
            "OSMNX_Rail",
            "SUCCESS",
            f"{len(lines)} features -> {len(result)} pts",
        )
        return result
    except Exception as e:
        logger.warning(f"[S5] osmnx rail failed: {e}")
        return None


def fetch_rail_overpass(bbox, run_log) -> list | None:
    lo, la_min, lx, la_max = bbox
    query = (
        f'[out:json][timeout:60];'
        f'(way["railway"="rail"]({la_min:.4f},{lo:.4f},{la_max:.4f},{lx:.4f});'
        f'way["railway"="light_rail"]({la_min:.4f},{lo:.4f},{la_max:.4f},{lx:.4f}););'
        f'out geom;'
    )
    try:
        data = ("data=" + urllib.parse.quote(query)).encode()
        req = urllib.request.Request(
            "https://overpass-api.de/api/interpreter",
            data=data,
            headers={
                "User-Agent": "CarbonSense/1.5",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        with urllib.request.urlopen(req, timeout=90) as resp:
            result = json.loads(resp.read())
        ways = [e for e in result.get("elements", []) if e.get("type") == "way"]
        if not ways:
            return None
        all_pts = []
        for way in ways:
            if "geometry" in way:
                all_pts.extend(_normalise_way(way["geometry"]))
        result_pts = sorted(set(all_pts), key=lambda p: p[0])
        _log_api(
            run_log,
            "Overpass_Rail",
            "SUCCESS",
            f"{len(ways)} ways -> {len(result_pts)} pts (lat,lon)",
        )
        return result_pts
    except Exception as e:
        logger.warning(f"[S5] Overpass rail failed: {e}")
        return None


def _hardcoded_rail() -> list:
    """ML-1 + Ferozepore branch: verified (lat,lon) from OSM."""
    return sorted(
        set(
            [
                (31.12, 74.35), (31.26, 74.41), (31.38, 74.42), (31.46, 74.38),
                (31.52, 74.36), (31.57, 74.33), (31.65, 74.28), (31.72, 74.24),
                (31.52, 74.36), (31.50, 74.29), (31.48, 74.08), (31.52, 73.82),
            ]
        ),
        key=lambda p: p[0],
    )


def rail_dist(uc_lat, uc_lon, coords) -> float:
    min_d = float("inf")
    for j in range(len(coords) - 1):
        la1, lo1 = coords[j]
        la2, lo2 = coords[j + 1]
        for t in np.linspace(0, 1, 15):
            d = haversine(uc_lat, uc_lon, la1 + t * (la2 - la1), lo1 + t * (lo2 - lo1))
            if d < min_d:
                min_d = d
    return min_d


def compute_rail_weights(gdf_uc_geo, df_uc, ld_bbox, run_log):
    """Try osmnx -> Overpass -> hardcoded. Returns (w_rail, rail_coords, nearest_km, rail_source)."""
    logger.info("[S5] Railway weight engine...")

    rail_coords = None
    rail_source = ""

    if gdf_uc_geo is not None:
        rail_coords = fetch_rail_osmnx(gdf_uc_geo, ld_bbox, run_log)
        if rail_coords:
            rail_source = f"osmnx features_from_polygon -- {len(rail_coords)} pts"

    if rail_coords is None:
        rail_coords = fetch_rail_overpass(ld_bbox, run_log)
        if rail_coords:
            rail_source = f"Overpass (lat,lon normalised, all ways merged) -- {len(rail_coords)} pts"

    if rail_coords is None:
        rail_coords = _hardcoded_rail()
        rail_source = "Hardcoded ML-1+Ferozepore branch (lat,lon) -- fallback"
        run_log["warnings"].append("rail: using hardcoded fallback")

    _log_source(run_log, "rail_geometry", rail_source)

    # Sanity assertion
    nearest = min(haversine(la, lo, 31.52, 74.36) for la, lo in rail_coords)
    if nearest > 200:
        raise RuntimeError(
            f"Rail coordinate sanity FAILED: nearest = {nearest:.0f}km "
            f"(expected <200km). Likely (lon,lat) inversion -- check _normalise_way()."
        )
    logger.info(f"[S5] Rail sanity: nearest to LHE Jct = {nearest:.2f}km")

    rail_scores = np.zeros(len(df_uc))
    for i, row in df_uc.iterrows():
        d = rail_dist(row["centroid_lat"], row["centroid_lon"], rail_coords)
        rail_scores[i] = (
            1 / max(d, 0.5) ** 2 if d < 3 else 1 / d**2 if d < 20 else 1 / d**3
        )
    rail_scores *= df_uc["area_km2"].values
    w_rail = pd.Series(rail_scores / rail_scores.sum(), index=df_uc["uc_code"])

    logger.info(f"  Rail source: {rail_source}")
    return w_rail, rail_coords, nearest, rail_source


# ---------------------------------------------------------------------------
# Section 6: Disaggregation
# ---------------------------------------------------------------------------

def disaggregate(
    df_uc, future_dates, road_fc, dom_avi_fc, intl_avi_fc, railways_fc, total_fc,
    w_road, avi_weights, w_rail,
):
    """Disaggregate monthly forecasts to UCs. Returns (all_records, df_ann, monthly_series)."""
    logger.info(
        f"[S6] Disaggregating {len(future_dates)} months x {len(df_uc)} UCs..."
    )

    def disaggregate_month(date, road_t, dom_avi_t, intl_avi_t, railways_t):
        wa = avi_weights[date.month]
        records = []
        for _, uc in df_uc.iterrows():
            uc_code = uc["uc_code"]
            wr = float(w_road.get(uc_code, 0))
            wai = float(wa.get(uc_code, 0))
            wrl = float(w_rail.get(uc_code, 0))
            road_e = road_t * wr
            dom_e = dom_avi_t * wai
            intl_e = intl_avi_t * wai
            rail_e = railways_t * wrl
            total_e = road_e + dom_e + intl_e + rail_e
            records.append(
                {
                    "uc_code": uc_code,
                    "date": date.strftime("%Y-%m-%d"),
                    "road_t": round(road_e, 2),
                    "dom_avi_t": round(dom_e, 4),
                    "intl_avi_t": round(intl_e, 3),
                    "railways_t": round(rail_e, 2),
                    "total_t": round(total_e, 2),
                    "road_pct": round(road_e / total_e * 100, 1) if total_e > 0 else 0.0,
                    "ci_lower_t": round(
                        road_e * (1 - SUB_SECTOR_CI["road"])
                        + dom_e * (1 - SUB_SECTOR_CI["dom_avi"])
                        + intl_e * (1 - SUB_SECTOR_CI["intl_avi"])
                        + rail_e * (1 - SUB_SECTOR_CI["railways"]),
                        2,
                    ),
                    "ci_upper_t": round(
                        road_e * (1 + SUB_SECTOR_CI["road"])
                        + dom_e * (1 + SUB_SECTOR_CI["dom_avi"])
                        + intl_e * (1 + SUB_SECTOR_CI["intl_avi"])
                        + rail_e * (1 + SUB_SECTOR_CI["railways"]),
                        2,
                    ),
                }
            )
        return records

    all_records = []
    for i, date in enumerate(future_dates):
        all_records.extend(
            disaggregate_month(
                date,
                float(road_fc[i]),
                float(dom_avi_fc[i]),
                float(intl_avi_fc[i]),
                float(railways_fc[i]),
            )
        )

    df_all = pd.DataFrame(all_records)
    df_ann = (
        df_all.groupby("uc_code")
        .agg(
            annual_t=("total_t", "sum"),
            road_annual=("road_t", "sum"),
            dom_avi_annual=("dom_avi_t", "sum"),
            intl_avi_annual=("intl_avi_t", "sum"),
            rail_annual=("railways_t", "sum"),
            ci_lower_ann=("ci_lower_t", "sum"),
            ci_upper_ann=("ci_upper_t", "sum"),
        )
        .reset_index()
    )

    merge_cols = [
        "uc_code", "uc_name", "district", "tehsil", "centroid_lat", "centroid_lon",
        "area_km2", "dist_lahore_km", "dist_airport_km",
    ]
    df_ann = df_ann.merge(
        df_uc[[c for c in merge_cols if c in df_uc.columns]], on="uc_code", how="left"
    )
    if "uc_name" not in df_ann.columns:
        df_ann["uc_name"] = df_ann["uc_code"]

    df_ann["road_pct"] = (df_ann["road_annual"] / df_ann["annual_t"] * 100).round(1)
    df_ann["intensity_t_per_km2"] = (df_ann["annual_t"] / df_ann["area_km2"]).round(1)
    df_ann["rank_in_division"] = df_ann["annual_t"].rank(ascending=False).astype(int)

    try:
        monthly_series = (
            df_all.groupby(["uc_code", "date"])
            .agg(total_t=("total_t", "sum"))
            .reset_index()
            .groupby("uc_code")
            .apply(
                lambda g: g.sort_values("date")["total_t"].tolist(),
                include_groups=False,
            )
            .to_dict()
        )
    except TypeError:
        monthly_series = (
            df_all.groupby(["uc_code", "date"])
            .agg(total_t=("total_t", "sum"))
            .reset_index()
            .groupby("uc_code")
            .apply(lambda g: g.sort_values("date")["total_t"].tolist())
            .to_dict()
        )

    recon_err = abs(df_ann["annual_t"].sum() - total_fc.sum()) / total_fc.sum() * 100
    logger.info(f"  Reconstruction error: {recon_err:.4f}%")

    return all_records, df_ann, monthly_series, recon_err


# ---------------------------------------------------------------------------
# Section 7: Risk Flags
# ---------------------------------------------------------------------------

def is_smog_zone(lat, lon, dist_lahore_km) -> bool:
    if any(
        haversine(lat, lon, s[0], s[1]) <= _PEPA_RADIUS_KM for s in _PEPA_STATIONS
    ):
        return True
    # Raiwind brick kiln / industrial corridor (SE Lahore)
    if 31.28 <= lat <= 31.37 and 74.30 <= lon <= 74.42:
        return True
    return False


def assign_risk_flags(df_ann, railways_fc, total_fc):
    """Assign risk flags and dominant source to each UC. Modifies df_ann in-place."""
    logger.info("[S7] Assigning risk flags...")

    intensity_p90 = df_ann["intensity_t_per_km2"].quantile(0.90)
    absolute_p75 = df_ann["annual_t"].quantile(0.75)
    rail_threshold = max(railways_fc.sum() / total_fc.sum() * 3.0, 0.05)

    def _assign_flags(row):
        f = []
        if row["intensity_t_per_km2"] >= intensity_p90:
            f.append("high_intensity")
        if row["annual_t"] >= absolute_p75:
            f.append("high_absolute")
        if is_smog_zone(
            row["centroid_lat"], row["centroid_lon"], row["dist_lahore_km"]
        ):
            f.append("winter_smog_zone")
        if row["road_pct"] >= 92:
            f.append("road_dominant")
        if row["rail_annual"] / row["annual_t"] > rail_threshold:
            f.append("rail_corridor")
        if row["dist_airport_km"] <= 8:
            f.append("aviation_plume_proximity")
        return f

    df_ann["risk_flags"] = df_ann.apply(_assign_flags, axis=1)
    df_ann["dominant_source"] = df_ann.apply(
        lambda r: (
            "road"
            if r["road_pct"] > 80
            else "aviation"
            if r["intl_avi_annual"] > r["road_annual"]
            else "mixed"
        ),
        axis=1,
    )

    flag_counts = Counter(f for flags in df_ann["risk_flags"] for f in flags)
    for flag, count in sorted(flag_counts.items(), key=lambda x: -x[1]):
        logger.info(
            f"  {flag:30} {count:3} UCs  ({count / len(df_ann) * 100:.0f}%)"
        )


# ---------------------------------------------------------------------------
# Section 8: JSON Output
# ---------------------------------------------------------------------------

def build_and_save_output(
    output_dir,
    v13, df_uc, df_ann, monthly_series,
    future_dates, total_fc, road_fc, dom_avi_fc, intl_avi_fc, railways_fc,
    ci_total_lower, ci_total_upper,
    w_road, w_rail, avi_weights, wind_clim,
    road_source, wind_source, rail_source, ci_source,
    yoy_pct, vkt_growth_pct, peak_month_name, forecast_peak_month,
    nearest, recon_err, run_log,
):
    """Build the full output JSON and CSV files."""
    logger.info("[S8] Building JSON output...")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    vkt_str = f"{vkt_growth_pct:+.1f}%" if vkt_growth_pct is not None else "N/A"

    sub_sector_shares = {
        "road": round(float(road_fc.sum() / total_fc.sum() * 100), 2),
        "intl_avi": round(float(intl_avi_fc.sum() / total_fc.sum() * 100), 2),
        "railways": round(float(railways_fc.sum() / total_fc.sum() * 100), 2),
        "dom_avi": round(float(dom_avi_fc.sum() / total_fc.sum() * 100), 2),
    }

    smog_ucs = df_ann[
        df_ann["risk_flags"].apply(lambda x: "winter_smog_zone" in x)
    ]["uc_code"].tolist()
    rail_corr_ucs = df_ann[
        df_ann["risk_flags"].apply(lambda x: "rail_corridor" in x)
    ]["uc_code"].tolist()
    top10_intensity = df_ann.nlargest(10, "intensity_t_per_km2")["uc_code"].tolist()
    top10_absolute = df_ann.nlargest(10, "annual_t")["uc_code"].tolist()
    top5_intensity_names = df_ann.nlargest(5, "intensity_t_per_km2")["uc_name"].tolist()

    mitigation_text = (
        f"Road transport dominates at {sub_sector_shares['road']:.1f}% "
        f"({road_fc.sum() / 1e6:.2f} Mt) in {SCOPE_NAME} {FORECAST_YEAR}. "
        f"Emission trend: {vkt_str}. Highest-intensity UCs: "
        f"{', '.join(top5_intensity_names)}. "
        f"Priorities: BRT/LRT on high-intensity corridors, EV motorcycle incentives, "
        f"reversing CNG drift, odd-even routing Dec/Jan for {len(smog_ucs)} smog-zone UCs."
    )

    metadata = {
        "version": "1.5",
        "scope": f"{SCOPE_NAME} -- {len(df_uc)} UCs",
        "sector": "transport",
        "location": f"{SCOPE_NAME}, Punjab, Pakistan",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "forecast_period": f"{future_dates[0].strftime('%Y-%m')} to {future_dates[-1].strftime('%Y-%m')}",
        "champion_model": v13["metadata"]["champion"],
        "production_model": v13["metadata"]["production_model"],
        "test_mape_pct": v13["metadata"]["test_mape_pct"],
        "test_r2": v13["metadata"]["test_r2"],
        "retrain_basis_months": v13["metadata"]["n_months"],
        "n_uc_total": len(df_uc),
        "uc_source": "Union_Council.shp (PBS, real polygon geometry)",
        "spatial_method": {
            "road": road_source,
            "aviation": "ICAO LTO 15km PG-D + polygon sampling",
            "railways": f"line-source proximity IPCC Tier1 EF={RAIL_EF_KG_PER_TKM}",
        },
        "road_type_weights": ROAD_TYPE_WEIGHTS,
        "sub_sector_ci_scales": SUB_SECTOR_CI,
        "wind_source": wind_source,
        "rail_source": rail_source,
        "rail_sanity_km": round(nearest, 3),
        "ci_source": ci_source,
        "yoy_pct": yoy_pct,
        "yoy_base": "2025 actual mean",
        "emission_trend_pct": vkt_growth_pct,
        "peak_month_hist": peak_month_name,
        "peak_month_fc": forecast_peak_month,
        "smog_zone_method": "12km urban core + Raiwind + Shahdara/GT Road corridor",
        "aviation_note": "International aviation = LHE-origin fuel only; bilateral policy scope.",
        "ipcc_railway_ef": RAIL_EF_KG_PER_TKM,
    }

    division_total = {
        "dates": [d.strftime("%Y-%m-%d") for d in future_dates],
        "total_t": [round(float(v), 2) for v in total_fc],
        "ci_lower_t": [round(float(v), 2) for v in ci_total_lower],
        "ci_upper_t": [round(float(v), 2) for v in ci_total_upper],
        "road_t": [round(float(v), 2) for v in road_fc],
        "dom_avi_t": [round(float(v), 2) for v in dom_avi_fc],
        "intl_avi_t": [round(float(v), 2) for v in intl_avi_fc],
        "railways_t": [round(float(v), 2) for v in railways_fc],
        "annual_total_t": int(total_fc.sum()),
        "trend_pct_yoy": yoy_pct,
        "yoy_base_note": "vs 2025 actual (not 5yr mean)",
        "peak_month_hist": peak_month_name,
        "peak_month_fc": forecast_peak_month,
        "smog_risk_months": ["December", "January"],
        "sub_sector_shares": sub_sector_shares,
        "eid_peak_months": ["April", "July"],
    }

    uc_emissions_arr = []
    for _, row in df_ann.sort_values("rank_in_division").iterrows():
        uc_code = row["uc_code"]
        uc_emissions_arr.append(
            {
                "uc_code": uc_code,
                "uc_name": row.get("uc_name", uc_code),
                "district": row["district"],
                "centroid_lat": row["centroid_lat"],
                "centroid_lon": row["centroid_lon"],
                "area_km2": round(row["area_km2"], 3),
                "annual_t": round(row["annual_t"], 0),
                "road_annual_t": round(row["road_annual"], 0),
                "dom_avi_annual_t": round(row["dom_avi_annual"], 2),
                "intl_avi_annual_t": round(row["intl_avi_annual"], 1),
                "rail_annual_t": round(row["rail_annual"], 2),
                "ci_lower_annual_t": round(row["ci_lower_ann"], 0),
                "ci_upper_annual_t": round(row["ci_upper_ann"], 0),
                "monthly_t": [round(v, 2) for v in monthly_series.get(uc_code, [])],
                "road_pct": row["road_pct"],
                "intensity_t_per_km2": row["intensity_t_per_km2"],
                "rank_in_division": int(row["rank_in_division"]),
                "road_weight": round(float(w_road.get(uc_code, 0)), 7),
                "rail_weight": round(float(w_rail.get(uc_code, 0)), 7),
                "avi_weight_jan": round(float(avi_weights[1].get(uc_code, 0)), 9),
                "avi_weight_jul": round(float(avi_weights[7].get(uc_code, 0)), 9),
                "dominant_source": row["dominant_source"],
                "risk_flags": row["risk_flags"],
            }
        )

    # RAG chunks
    rag_chunks = [
        {
            "chunk_id": f"div-total-{FORECAST_YEAR}",
            "chunk_type": "division_summary",
            "entity": SCOPE_NAME,
            "period": str(FORECAST_YEAR),
            "text": (
                f"{SCOPE_NAME} transport forecast: {total_fc.sum() / 1e6:.2f} Mt CO2e in {FORECAST_YEAR} "
                f"({yoy_pct:+.1f}% vs 2025). Road {sub_sector_shares['road']:.1f}% "
                f"({road_fc.sum() / 1e6:.2f} Mt). Intl aviation {sub_sector_shares['intl_avi']:.1f}% "
                f"(LHE-origin fuel, bilateral scope). Railways {sub_sector_shares['railways']:.1f}%. "
                f"Dom aviation {sub_sector_shares['dom_avi']:.1f}%. "
                f"{len(df_uc)} real UCs (Union_Council.shp). "
                f"Model: {v13['metadata']['champion']} MAPE={v13['metadata']['test_mape_pct']:.2f}% "
                f"R2={v13['metadata']['test_r2']:.4f}."
            ),
            "numeric_context": {
                "annual_t": int(total_fc.sum()),
                "yoy_pct": yoy_pct,
                "n_uc": len(df_uc),
                "road_t": int(road_fc.sum()),
            },
            "policy_tags": ["road_dominant", "winter_smog", "eid_peak"],
            "retrieval_hints": [
                f"{SCOPE_NAME} transport {FORECAST_YEAR}",
                "CO2 Pakistan transport",
            ],
        },
        {
            "chunk_id": f"mitigation-road-{FORECAST_YEAR}",
            "chunk_type": "mitigation_recommendation",
            "entity": "Road transport",
            "period": str(FORECAST_YEAR),
            "text": mitigation_text,
            "numeric_context": {
                "road_share_pct": sub_sector_shares["road"],
                "road_annual_t": int(road_fc.sum()),
                "smog_uc_count": len(smog_ucs),
                "top5_intensity_ucs": top10_intensity[:5],
            },
            "policy_tags": ["brt", "ev", "cng", "odd_even", "road_dominant"],
            "retrieval_hints": [
                "road mitigation",
                "BRT LRT",
                "winter smog",
                "motorcycle EV",
            ],
        },
    ]

    for sector_key in ["road", "intl_avi", "railways", "dom_avi"]:
        fc_arr = {
            "road": road_fc,
            "intl_avi": intl_avi_fc,
            "railways": railways_fc,
            "dom_avi": dom_avi_fc,
        }[sector_key]
        rag_chunks.append(
            {
                "chunk_id": f"subsector-{sector_key}-{FORECAST_YEAR}",
                "chunk_type": "subsector_summary",
                "entity": sector_key,
                "period": str(FORECAST_YEAR),
                "text": (
                    f"{sector_key.replace('_', ' ')} in {SCOPE_NAME}: "
                    f"{fc_arr.sum() / 1e3:.0f}k t CO2e ({sub_sector_shares.get(sector_key, 0):.1f}%) "
                    f"in {FORECAST_YEAR}. Peak month: {int(fc_arr.argmax()) + 1}."
                ),
                "numeric_context": {
                    "annual_t": int(fc_arr.sum()),
                    "share_pct": sub_sector_shares.get(sector_key, 0),
                    "peak_month": int(fc_arr.argmax()) + 1,
                },
                "policy_tags": [sector_key],
                "retrieval_hints": [f"{sector_key} {SCOPE_NAME}"],
            }
        )

    for _, row in df_ann.nlargest(30, "annual_t").iterrows():
        flags = row["risk_flags"]
        rag_chunks.append(
            {
                "chunk_id": f"uc-{row['uc_code']}-{FORECAST_YEAR}",
                "chunk_type": "uc_summary",
                "entity": f"{row.get('uc_name', '?')}, {row['district']}",
                "period": str(FORECAST_YEAR),
                "text": (
                    f"{row.get('uc_name', '?')} UC ({row['district']}): "
                    f"{row['annual_t']:,.0f} t CO2e, rank {row['rank_in_division']}/{len(df_ann)}. "
                    f"Road {row['road_pct']:.1f}%. Intensity {row['intensity_t_per_km2']:,.0f} t/km2. "
                    f"CI [{row['ci_lower_ann']:,.0f}-{row['ci_upper_ann']:,.0f}] t/yr. "
                    f"Risk: {', '.join(flags) if flags else 'none'}."
                ),
                "numeric_context": {
                    "annual_t": round(row["annual_t"]),
                    "road_pct": row["road_pct"],
                    "intensity_t_per_km2": row["intensity_t_per_km2"],
                    "rank": int(row["rank_in_division"]),
                },
                "policy_tags": flags,
                "retrieval_hints": [
                    row.get("uc_name", "?"),
                    row["district"],
                    f"{SCOPE_NAME} transport",
                ],
            }
        )

    run_log["run_summary"] = {
        "n_uc": len(df_uc),
        "total_annual_fc_t": int(total_fc.sum()),
        "reconstruction_err_pct": round(recon_err, 6),
        "road_engine": road_source[:60],
        "rail_sanity_km": round(nearest, 3),
        "yoy_pct": yoy_pct,
        "smog_zone_pct": round(len(smog_ucs) / len(df_ann) * 100, 1),
        "rail_corridor_pct": round(len(rail_corr_ucs) / len(df_ann) * 100, 1),
        "warnings_count": len(run_log["warnings"]),
    }

    output_doc = {
        "metadata": metadata,
        "run_audit": run_log,
        "division_total": division_total,
        "uc_emissions": uc_emissions_arr,
        "spatial_weights": {
            "road": {
                "method": road_source,
                "road_type_weights": ROAD_TYPE_WEIGHTS,
                "weights": {
                    r["uc_code"]: round(float(w_road.get(r["uc_code"], 0)), 8)
                    for _, r in df_uc.iterrows()
                },
            },
            "aviation": {
                "method": "ICAO_LTO_15km_PG-D_polygon_sampling",
                "wind_source": wind_source,
                "monthly_wind": {str(m): v for m, v in wind_clim.items()},
                "monthly_weights": {
                    str(m): {
                        uc: round(float(v), 9) for uc, v in avi_weights[m].items()
                    }
                    for m in range(1, 13)
                },
            },
            "railways": {
                "method": "line_source_proximity",
                "rail_source": rail_source,
                "sanity_km": round(nearest, 3),
                "ef_kg_co2_per_tonne_km": RAIL_EF_KG_PER_TKM,
                "weights": {
                    r["uc_code"]: round(float(w_rail.get(r["uc_code"], 0)), 8)
                    for _, r in df_uc.iterrows()
                },
            },
        },
        "rag_chunks": rag_chunks,
        "mitigation_index": {
            "top10_intensity": top10_intensity,
            "top10_absolute": top10_absolute,
            "smog_zone_ucs": smog_ucs,
            "rail_corridor_ucs": rail_corr_ucs,
            "aviation_top5": df_ann.assign(
                aw=df_ann["uc_code"].map(avi_weights[7])
            )
            .nlargest(5, "aw")["uc_code"]
            .tolist(),
        },
    }

    # Write main JSON
    out_json = output_dir / "carbonsense_transport_v15.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(output_doc, f, indent=2, ensure_ascii=False, default=str)
    logger.info(f"  carbonsense_transport_v15.json  ({out_json.stat().st_size / 1e6:.2f} MB)")

    # Write audit JSON
    audit_path = output_dir / "run_audit_v15.json"
    with open(audit_path, "w", encoding="utf-8") as f:
        json.dump(run_log, f, indent=2, default=str)
    logger.info("  run_audit_v15.json")

    # Write emissions CSV
    df_export = df_ann[
        [
            "uc_code", "uc_name", "district", "centroid_lat", "centroid_lon",
            "area_km2", "annual_t", "road_annual", "dom_avi_annual",
            "intl_avi_annual", "rail_annual", "ci_lower_ann", "ci_upper_ann",
            "road_pct", "intensity_t_per_km2", "rank_in_division", "dominant_source",
        ]
    ].copy()
    df_export["risk_flags"] = df_ann["risk_flags"].apply(lambda x: "|".join(x))
    df_export.to_csv(output_dir / "uc_emissions_v15.csv", index=False)
    logger.info(f"  uc_emissions_v15.csv  ({len(df_export)} rows)")

    # Write spatial weights CSV
    pd.DataFrame(
        {
            "uc_code": df_uc["uc_code"],
            "road_weight": w_road.values,
            "rail_weight": w_rail.values,
            "avi_weight_jan": [
                float(avi_weights[1].get(c, 0)) for c in df_uc["uc_code"]
            ],
            "avi_weight_jul": [
                float(avi_weights[7].get(c, 0)) for c in df_uc["uc_code"]
            ],
        }
    ).to_csv(output_dir / "spatial_weights_v15.csv", index=False)
    logger.info("  spatial_weights_v15.csv")

    return output_doc, uc_emissions_arr, audit_path


# ---------------------------------------------------------------------------
# Section 9: Assertion Suite
# ---------------------------------------------------------------------------

def run_assertions(
    df_uc, df_ann, w_road, w_rail, avi_weights, wind_clim,
    nearest, recon_err, yoy_pct, uc_emissions_arr,
    run_log, audit_path,
):
    """Run post-pipeline assertion suite. Returns (passed, total)."""
    logger.info("[S9] Post-fix assertion suite...")

    passed = 0
    total_count = 0

    def _assert(cond, name, msg):
        nonlocal passed, total_count
        total_count += 1
        if cond:
            passed += 1
            logger.info(f"  PASS  [{name}]  {msg}")
            run_log["assertions"][name] = {"passed": True}
        else:
            logger.warning(f"  FAIL  [{name}]  {msg}")
            run_log["assertions"][name] = {"passed": False, "message": msg}
            run_log["errors"].append(f"ASSERTION [{name}]: {msg}")

    smog_ucs = df_ann[
        df_ann["risk_flags"].apply(lambda x: "winter_smog_zone" in x)
    ]["uc_code"].tolist()
    rail_corr_ucs = df_ann[
        df_ann["risk_flags"].apply(lambda x: "rail_corridor" in x)
    ]["uc_code"].tolist()

    _assert(
        nearest < 200,
        "C1_rail",
        f"rail nearest to LHE Jct = {nearest:.2f}km (<200 = ok; ~5000 = coord inversion)",
    )
    top5_mean_dist = np.array(
        [
            df_uc[df_uc["uc_code"] == uc]["dist_lahore_km"].values[0]
            for uc in w_road.nlargest(5).index
        ]
    ).mean()
    _assert(
        top5_mean_dist < df_uc["dist_lahore_km"].median() * 1.8,
        "M1_road_urban",
        f"top-5 road UCs mean dist={top5_mean_dist:.1f}km < 1.8x median",
    )
    _assert(
        0.10 < len(smog_ucs) / len(df_ann) < 0.60,
        "M2_smog",
        f"smog zone {len(smog_ucs) / len(df_ann) * 100:.0f}% (expect 10-60%)",
    )
    _assert(
        len(rail_corr_ucs) / len(df_ann) < 0.35,
        "M3_rail_corridor",
        f"rail corridor {len(rail_corr_ucs) / len(df_ann) * 100:.0f}% (expect <35%)",
    )
    _assert(
        (250 <= wind_clim[1]["from_deg"] <= 360)
        or (0 <= wind_clim[1]["from_deg"] <= 30),
        "A2_wind",
        f"Jan wind FROM {wind_clim[1]['from_deg']} is NW-ish",
    )
    _assert(
        -10 <= yoy_pct <= 30,
        "A5_yoy",
        f"YOY={yoy_pct:+.1f}% plausible",
    )
    _assert(
        abs(w_road.sum() - 1.0) < 1e-6,
        "closure_road",
        f"road sum={w_road.sum():.8f}",
    )
    _assert(
        abs(w_rail.sum() - 1.0) < 1e-6,
        "closure_rail",
        f"rail sum={w_rail.sum():.8f}",
    )
    for m in [1, 4, 7, 10]:
        _assert(
            abs(avi_weights[m].sum() - 1.0) < 1e-5,
            f"closure_avi_{m}",
            f"avi mo={m} sum={avi_weights[m].sum():.8f}",
        )
    _assert(recon_err < 0.01, "reconstruction", f"error={recon_err:.4f}%")
    _assert(
        "yoy_change_pct" not in uc_emissions_arr[0],
        "A6_no_random_yoy",
        "per-UC random yoy removed",
    )

    # Save final audit with assertion results
    with open(audit_path, "w", encoding="utf-8") as f:
        json.dump(run_log, f, indent=2, default=str)

    logger.info(f"  {passed}/{total_count} assertions passed")
    return passed, total_count


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main(input_json_path: str, shapefile_path: str, output_dir: str, features_csv_path: str | None = None):
    """
    Run the CarbonSense Transport v1.5 spatial disaggregation pipeline.

    Args:
        input_json_path: Path to carbonsense_transport_v13.json
        shapefile_path: Path to Union_Council.shp
        output_dir: Directory for output files
        features_csv_path: Optional path to transport_features_v13.csv
    """
    run_log = _make_run_log()

    logger.info("=" * 80)
    logger.info(f"  CarbonSense Transport v1.5 | {SCOPE_NAME}")
    logger.info("=" * 80)

    # S1: Load v1.3 JSON
    fc_data = load_v13_json(input_json_path, features_csv_path, run_log)

    # S2: Load UC registry
    gdf_uc_geo, df_uc = load_uc_registry(shapefile_path)
    _log_source(run_log, "uc_registry", "Union_Council.shp", f"{len(df_uc)} real polygons")

    ld_bbox = (
        df_uc["centroid_lon"].min() - 0.05,
        df_uc["centroid_lat"].min() - 0.05,
        df_uc["centroid_lon"].max() + 0.05,
        df_uc["centroid_lat"].max() + 0.05,
    )

    # S3: Road weights
    w_road, road_source = compute_road_weights(gdf_uc_geo, df_uc, ld_bbox, run_log)

    # S4: Aviation weights
    avi_weights, wind_clim, wind_source = compute_aviation_weights(
        gdf_uc_geo, df_uc, run_log
    )

    # S5: Railway weights
    w_rail, rail_coords, nearest, rail_source = compute_rail_weights(
        gdf_uc_geo, df_uc, ld_bbox, run_log
    )

    # S6: Disaggregation
    all_records, df_ann, monthly_series, recon_err = disaggregate(
        df_uc,
        fc_data["future_dates"],
        fc_data["road_fc"],
        fc_data["dom_avi_fc"],
        fc_data["intl_avi_fc"],
        fc_data["railways_fc"],
        fc_data["total_fc"],
        w_road,
        avi_weights,
        w_rail,
    )

    # S7: Risk flags
    assign_risk_flags(df_ann, fc_data["railways_fc"], fc_data["total_fc"])

    # S8: Output
    output_doc, uc_emissions_arr, audit_path = build_and_save_output(
        output_dir,
        fc_data["v13"], df_uc, df_ann, monthly_series,
        fc_data["future_dates"],
        fc_data["total_fc"], fc_data["road_fc"], fc_data["dom_avi_fc"],
        fc_data["intl_avi_fc"], fc_data["railways_fc"],
        fc_data["ci_total_lower"], fc_data["ci_total_upper"],
        w_road, w_rail, avi_weights, wind_clim,
        road_source, wind_source, rail_source, fc_data["ci_source"],
        fc_data["yoy_pct"], fc_data["vkt_growth_pct"],
        fc_data["peak_month_name"], fc_data["forecast_peak_month"],
        nearest, recon_err, run_log,
    )

    # S9: Assertions
    passed, total_count = run_assertions(
        df_uc, df_ann, w_road, w_rail, avi_weights, wind_clim,
        nearest, recon_err, fc_data["yoy_pct"], uc_emissions_arr,
        run_log, audit_path,
    )

    logger.info("=" * 80)
    logger.info(
        f"  CarbonSense Transport v1.5 -- COMPLETE  |  "
        f"{SCOPE_NAME}  |  {len(df_uc)} UCs  |  {passed}/{total_count} assertions"
    )
    logger.info("=" * 80)

    return output_doc


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="CarbonSense Transport v1.5 -- Spatial Disaggregation Pipeline"
    )
    parser.add_argument(
        "--input-json",
        required=True,
        help="Path to carbonsense_transport_v13.json",
    )
    parser.add_argument(
        "--shapefile",
        required=True,
        help="Path to Union_Council.shp (with .dbf, .shx, .prj sidecars)",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory for output files",
    )
    parser.add_argument(
        "--features-csv",
        default=None,
        help="Optional path to transport_features_v13.csv",
    )
    args = parser.parse_args()

    main(
        input_json_path=args.input_json,
        shapefile_path=args.shapefile,
        output_dir=args.output_dir,
        features_csv_path=args.features_csv,
    )
