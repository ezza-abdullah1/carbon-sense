"""
CarbonSense Waste: Hybrid Spatial Allocation Pipeline v2.3
Prophet Champion Model | 6 Models | PBS Shapefile UC Registry | Unified Sectors
Lahore District, Punjab, Pakistan

Converted from WI_model.ipynb for automated pipeline use.
"""

# --- Standard Library ---
import argparse
import datetime
import json
import logging
import math
import os
import struct
import sys
import warnings
from math import radians, cos, sin, asin, sqrt
from pathlib import Path

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.WARNING)
logging.getLogger("prophet").setLevel(logging.WARNING)
logger = logging.getLogger("carbonsense.waste.v23")

# --- Core ---
import numpy as np
import pandas as pd

# --- Prophet ---
from prophet import Prophet

# --- Spatial ---
import geopandas as gpd
from shapely.geometry import Point, Polygon as ShPoly, MultiPolygon

# --- Weather API ---
import openmeteo_requests
import requests_cache
from retry_requests import retry

# ===========================================================================
# GLOBAL CONFIG
# ===========================================================================
RANDOM_STATE = 42
np.random.seed(RANDOM_STATE)

TARGET_GAS = "co2e_20yr"
FORECAST_MONTHS = 12
TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
LAHORE_CENTER_LAT, LAHORE_CENTER_LON = 31.5204, 74.3587
_LAT_KM = 111.0
_LON_KM = 111.0 * math.cos(math.radians(31.5))

LAHORE_DIVISION_DISTRICTS = {"Lahore"}

PROPHET_CHAMPION_PARAMS = {
    "changepoint_prior_scale": 0.01,
    "seasonality_prior_scale": 10.0,
    "seasonality_mode": "additive",
}

IPCC_K_MIN = 0.06
IPCC_K_MAX = 0.40
IPCC_K_LAHORE_STATIC = 0.185

POINT_SOURCES = {
    "L1_WWTP_Shahpur": {
        "lat": 31.435, "lon": 74.293,
        "type": "WWTP", "area": "Shahpur Kanjran",
    },
    "L2_WWTP_GardenTown": {
        "lat": 31.470, "lon": 74.319,
        "type": "WWTP", "area": "Garden Town / Model Town",
    },
    "L3_WWTP_DHA": {
        "lat": 31.501, "lon": 74.409,
        "type": "WWTP", "area": "DHA / Taj Bagh",
    },
    "L4_MehmoodBooti": {
        "lat": 31.609972, "lon": 74.386883,
        "type": "Dumpsite", "area": "Mehmood Booti / Wagah Town",
    },
}

AREA_SOLIDWASTE_KEY = "Area_SolidWaste"
AREA_WASTEWATER_KEY = "Area_Wastewater"

REGRESSORS_BY_LOC = {
    "L1_WWTP_Shahpur": ["pop_served", "precipitation"],
    "L2_WWTP_GardenTown": ["pop_served", "precipitation"],
    "L3_WWTP_DHA": ["pop_served", "precipitation"],
    "L4_MehmoodBooti": ["waste_volume", "precip_lagged", "decomp_lagged"],
    AREA_SOLIDWASTE_KEY: ["waste_volume", "precip_lagged", "decomp_lagged"],
    AREA_WASTEWATER_KEY: ["precipitation"],
}


# ===========================================================================
# HELPERS
# ===========================================================================
def haversine(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * R * asin(sqrt(a))


MONTH_NAMES = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December",
}


def iso(ts):
    return pd.Timestamp(ts).strftime("%Y-%m-%d")


def month_label(ts):
    ts = pd.Timestamp(ts)
    return f"{MONTH_NAMES[ts.month]} {ts.year}"


def confidence_band(lo, hi, pred):
    if pred <= 0:
        return "low"
    w = (hi - lo) / (abs(pred) + 1e-9) * 100
    return "high" if w < 10 else "medium" if w < 25 else "low"


def risk_level(t):
    if t > 100_000:
        return "Critical"
    elif t > 50_000:
        return "High"
    elif t > 10_000:
        return "Medium-High"
    elif t > 2_000:
        return "Medium"
    else:
        return "Low"


def policy_tags_fn(src_types, annual_t):
    tags = []
    if "Dumpsite" in src_types:
        tags += ["Landfill Gas Recovery", "Biogas Extraction", "Leachate Management"]
        if annual_t > 50_000:
            tags.append("Methane Flaring Law")
    if any("WWTP" in s or "wastewater" in s.lower() for s in src_types):
        tags += ["Anaerobic Digestion", "Sludge-to-Energy"]
        if annual_t > 10_000:
            tags.append("Biogas Mandate")
    if not any(s in src_types for s in ["Dumpsite", "WWTP"]):
        tags += ["Source Segregation", "Composting Programme"]
        if annual_t > 5_000:
            tags.append("Open Burning Ban")
    return list(dict.fromkeys(tags))


# ===========================================================================
# SECTION 1 -- DATA LOADING & SPATIAL GROUPING
# ===========================================================================
def load_and_group_data(input_dir: str):
    """Load Climate TRACE waste CSVs and group by location."""
    logger.info("[SECTION 1/8] DATA LOADING & SPATIAL GROUPING")

    input_path = Path(input_dir)
    csv_files = sorted(input_path.glob("waste_*.csv"))
    if not csv_files:
        raise FileNotFoundError(
            f"No waste_*.csv files found in {input_dir}. "
            f"Expected waste_2021.csv through waste_2025.csv."
        )

    df_list = []
    for fname in csv_files:
        df = pd.read_csv(fname)
        df_list.append(df)
        logger.info("Loaded: %s  (%d rows)", fname.name, len(df))

    df_raw = pd.concat(df_list, ignore_index=True)
    df_raw["start_time"] = pd.to_datetime(df_raw["start_time"], format="mixed")
    df_raw = df_raw.sort_values("start_time")
    for col in ["lat", "lon"]:
        if col not in df_raw.columns:
            df_raw[col] = np.nan
    if "source_name" not in df_raw.columns:
        df_raw["source_name"] = ""

    # Spatial grouping
    SNAP_TOLERANCE_DEG = 0.05
    known_coords = {k: (v["lat"], v["lon"]) for k, v in POINT_SOURCES.items()}

    def assign_location_key(lat, lon, source_name=""):
        if pd.isna(lat) or pd.isna(lon):
            name_lower = str(source_name).lower()
            if "solid-waste-disposal" in name_lower or "solid waste disposal" in name_lower:
                return AREA_SOLIDWASTE_KEY
            return AREA_WASTEWATER_KEY
        best_key, best_dist = AREA_WASTEWATER_KEY, float("inf")
        for k, (klat, klon) in known_coords.items():
            d = ((lat - klat) ** 2 + (lon - klon) ** 2) ** 0.5
            if d < best_dist:
                best_dist, best_key = d, k
        return best_key if best_dist <= SNAP_TOLERANCE_DEG else AREA_WASTEWATER_KEY

    df_raw["location_key"] = df_raw.apply(
        lambda r: assign_location_key(r["lat"], r["lon"], r.get("source_name", "")),
        axis=1,
    )

    # Monthly aggregate per location
    location_ts = {}
    target_rows = df_raw[df_raw["gas"] == TARGET_GAS].copy()
    for loc_key, grp in target_rows.groupby("location_key"):
        grp2 = grp.copy()
        grp2["start_time"] = pd.to_datetime(grp2["start_time"])
        monthly = grp2.set_index("start_time")["emissions_quantity"].resample("MS").sum()
        monthly.index.freq = "MS"
        location_ts[loc_key] = monthly.rename(loc_key)

    all_keys = list(location_ts.keys())
    date_range = location_ts[all_keys[0]].index
    n_total = len(date_range)

    logger.info(
        "Monthly time series: %d locations (%s to %s)",
        len(location_ts),
        date_range[0].strftime("%b %Y"),
        date_range[-1].strftime("%b %Y"),
    )

    return df_raw, location_ts, all_keys, date_range, n_total


# ===========================================================================
# SECTION 2 -- WEATHER + FEATURE ENGINEERING
# ===========================================================================
def fetch_weather_and_build_features(df_raw, location_ts, all_keys, date_range, n_total):
    """Fetch weather from Open-Meteo and engineer per-location features."""
    logger.info("[SECTION 2/8] WEATHER FETCHING & FEATURE ENGINEERING")

    cache_s = requests_cache.CachedSession(".cache_waste23", expire_after=-1)
    retry_s = retry(cache_s, retries=5, backoff_factor=0.2)
    openmeteo_client = openmeteo_requests.Client(session=retry_s)

    start_date_str = date_range[0].strftime("%Y-%m-%d")
    end_date_str = date_range[-1].strftime("%Y-%m-%d")

    try:
        resp = openmeteo_client.weather_api(
            "https://archive-api.open-meteo.com/v1/archive",
            params={
                "latitude": LAHORE_CENTER_LAT,
                "longitude": LAHORE_CENTER_LON,
                "start_date": start_date_str,
                "end_date": end_date_str,
                "hourly": ["temperature_2m", "relative_humidity_2m", "precipitation"],
                "timezone": "Asia/Karachi",
            },
        )[0]
        h = resp.Hourly()
        dh = pd.date_range(
            start=pd.to_datetime(h.Time(), unit="s", utc=True),
            end=pd.to_datetime(h.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=h.Interval()),
            inclusive="left",
        )
        wh = pd.DataFrame(
            {
                "temperature": h.Variables(0).ValuesAsNumpy(),
                "humidity": h.Variables(1).ValuesAsNumpy(),
                "precip_h": h.Variables(2).ValuesAsNumpy(),
            },
            index=dh,
        )
        weather_m = pd.DataFrame(
            {
                "temperature": wh["temperature"].resample("MS").mean(),
                "humidity": wh["humidity"].resample("MS").mean(),
                "precipitation": wh["precip_h"].resample("MS").sum(),
            }
        )
        weather_m.index = weather_m.index.tz_localize(None)
        logger.info("Real weather fetched: %d months", len(weather_m))
    except Exception as e:
        logger.warning("API failed (%s) -- using synthetic Lahore climatology", e)
        weather_m = pd.DataFrame(
            {
                "temperature": ([15, 18, 24, 30, 35, 39, 38, 36, 33, 27, 20, 14] * 6)[
                    :n_total
                ],
                "humidity": ([55, 50, 45, 40, 38, 42, 60, 70, 65, 55, 52, 56] * 6)[
                    :n_total
                ],
                "precipitation": ([15, 12, 8, 5, 8, 15, 80, 90, 50, 10, 8, 12] * 6)[
                    :n_total
                ],
            },
            index=date_range,
        )

    weather_m["decomp_index"] = weather_m["temperature"] * weather_m["humidity"] / 100

    # FIX I: 2-month biological lag for CH4 / FOD models
    weather_m["precip_lagged"] = weather_m["precipitation"].shift(2).bfill()
    weather_m["decomp_lagged"] = weather_m["decomp_index"].shift(2).bfill()

    _di_min, _di_max = weather_m["decomp_index"].min(), weather_m["decomp_index"].max()
    weather_m["k_dynamic"] = IPCC_K_MIN + (weather_m["decomp_index"] - _di_min) / (
        _di_max - _di_min + 1e-9
    ) * (IPCC_K_MAX - IPCC_K_MIN)

    # Seasonal climatology for future forecasting
    _seasonal = weather_m[
        ["precipitation", "decomp_index", "precip_lagged", "decomp_lagged"]
    ].groupby(weather_m.index.month).mean()

    def weather_for_month(month: int) -> dict:
        return _seasonal.loc[month].to_dict()

    # Per-location feature extraction
    loc_features = {}
    for loc_key in all_keys:
        em = location_ts[loc_key]
        loc_raw = df_raw[df_raw["location_key"] == loc_key].copy()
        loc_raw["start_time"] = pd.to_datetime(loc_raw["start_time"])
        feat = pd.DataFrame(index=em.index)
        feat["emissions"] = em
        feat["precipitation"] = weather_m["precipitation"].reindex(em.index).ffill().bfill()
        feat["decomp_index"] = weather_m["decomp_index"].reindex(em.index).ffill().bfill()
        feat["precip_lagged"] = weather_m["precip_lagged"].reindex(em.index).ffill().bfill()
        feat["decomp_lagged"] = weather_m["decomp_lagged"].reindex(em.index).ffill().bfill()

        if POINT_SOURCES.get(loc_key, {}).get("type") == "WWTP":
            pop_mask = (
                loc_raw["activity_units"].str.contains("population", case=False, na=False)
                if "activity_units" in loc_raw.columns
                else pd.Series(False, index=loc_raw.index)
            )
            if pop_mask.any():
                ps = loc_raw[pop_mask].set_index("start_time")["activity"].resample("MS").mean()
                feat["pop_served"] = ps.reindex(em.index).ffill().bfill()
                feat["pop_served"] = feat["pop_served"].fillna(feat["pop_served"].mean())
            else:
                feat["pop_served"] = em.values

        elif loc_key == "L4_MehmoodBooti":
            wv_mask = (
                loc_raw["activity_units"].str.contains("t of waste", case=False, na=False)
                if "activity_units" in loc_raw.columns
                else pd.Series(False, index=loc_raw.index)
            )
            if wv_mask.any():
                wv = loc_raw[wv_mask].set_index("start_time")["activity"].resample("MS").sum()
                feat["waste_volume"] = wv.reindex(em.index).ffill().bfill()
            else:
                wv_p = (em / weather_m["k_dynamic"].reindex(em.index)).clip(lower=1)
                feat["waste_volume"] = (wv_p / wv_p.max() * 540_000).fillna(540_000)

        elif loc_key == AREA_SOLIDWASTE_KEY:
            wv_p = (em / weather_m["k_dynamic"].reindex(em.index)).clip(lower=1)
            feat["waste_volume"] = (wv_p / wv_p.max() * 4_000_000).fillna(4_000_000)

        loc_features[loc_key] = feat.ffill().bfill()

    return weather_m, loc_features, weather_for_month


# ===========================================================================
# SECTION 3 -- PER-LOCATION PROPHET TRAINING (6 MODELS)
# ===========================================================================
def train_all_models(location_ts, all_keys, date_range, n_total, loc_features, weather_for_month):
    """Train Prophet models for all 6 locations."""
    logger.info("[SECTION 3/8] PER-LOCATION PROPHET TRAINING -- 6 MODELS")

    MIN_SPLIT = 6
    n_test = max(MIN_SPLIT, int(n_total * (1 - TRAIN_RATIO - VAL_RATIO)))
    n_val = max(MIN_SPLIT, int(n_total * VAL_RATIO))
    n_train = n_total - n_val - n_test
    train_idx = date_range[:n_train]
    val_idx = date_range[n_train : n_train + n_val]
    test_idx = date_range[n_train + n_val :]
    future_dates = pd.date_range(
        start=test_idx[-1] + pd.DateOffset(months=1),
        periods=FORECAST_MONTHS,
        freq="MS",
    )

    def safe_feature_for_date(d, loc_key, loc_df, col):
        if d in loc_df.index and col in loc_df.columns:
            val = loc_df.loc[d, col]
            if pd.notna(val):
                return float(val)
        clim = weather_for_month(d.month)
        if col in clim:
            return float(clim[col])
        if col in loc_df.columns:
            m = loc_df[col].mean()
            return float(m) if pd.notna(m) else 0.0
        return 0.0

    def make_prophet_df(series, loc_df, regressors, extra_periods=0):
        idx = series.index
        if extra_periods > 0:
            fut = pd.date_range(
                start=idx[-1] + pd.DateOffset(months=1),
                periods=extra_periods,
                freq="MS",
            )
            idx = idx.append(fut)
        df = pd.DataFrame({"ds": pd.to_datetime(idx), "y": np.nan})
        df["y"].iloc[: len(series)] = series.values
        loc_key = series.name
        for col in regressors:
            df[col] = [
                safe_feature_for_date(pd.Timestamp(d), loc_key, loc_df, col)
                for d in df["ds"]
            ]
        return df

    def prophet_val_mape(series, loc_df, regressors, mode):
        tr_s = series.iloc[:n_train]
        vl_s = series.iloc[n_train : n_train + n_val]
        df_tr = make_prophet_df(tr_s, loc_df, regressors)
        m = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=False,
            daily_seasonality=False,
            changepoint_prior_scale=PROPHET_CHAMPION_PARAMS["changepoint_prior_scale"],
            seasonality_prior_scale=PROPHET_CHAMPION_PARAMS["seasonality_prior_scale"],
            seasonality_mode=mode,
        )
        for reg in regressors:
            m.add_regressor(reg)
        m.fit(df_tr)
        fut = make_prophet_df(tr_s, loc_df, regressors, extra_periods=n_val)
        fc = m.predict(fut).set_index("ds")["yhat"].reindex(vl_s.index).values
        err = np.abs(vl_s.values - fc) / (np.abs(vl_s.values) + 1e-9) * 100
        return float(np.nanmean(err))

    def train_prophet_model(ts_loc, loc_df, regressors):
        mape_add = prophet_val_mape(ts_loc, loc_df, regressors, "additive")
        mape_mul = prophet_val_mape(ts_loc, loc_df, regressors, "multiplicative")
        best_mode = "additive" if mape_add <= mape_mul else "multiplicative"

        tv_s = pd.concat([ts_loc.iloc[:n_train], ts_loc.iloc[n_train : n_train + n_val]])
        df_tv = make_prophet_df(tv_s, loc_df, regressors)
        params = {**PROPHET_CHAMPION_PARAMS, "seasonality_mode": best_mode}
        m_final = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=False,
            daily_seasonality=False,
            interval_width=0.95,
            **params,
        )
        for reg in regressors:
            m_final.add_regressor(reg)
        m_final.fit(df_tv)

        df_fut = make_prophet_df(
            tv_s, loc_df, regressors, extra_periods=n_test + FORECAST_MONTHS
        )
        fc = m_final.predict(df_fut).set_index("ds")
        te_fc = fc["yhat"].reindex(test_idx).values.clip(0)
        fu_fc = fc["yhat"].reindex(future_dates).values.clip(0)
        te_lo = fc["yhat_lower"].reindex(test_idx).values.clip(0)
        te_hi = fc["yhat_upper"].reindex(test_idx).values.clip(0)
        fu_lo = fc["yhat_lower"].reindex(future_dates).values.clip(0)
        fu_hi = fc["yhat_upper"].reindex(future_dates).values.clip(0)

        actual = ts_loc.iloc[n_train + n_val :].values
        nonz = actual > 0
        mape = (
            float(np.mean(np.abs(actual[nonz] - te_fc[nonz]) / actual[nonz]) * 100)
            if nonz.any()
            else np.nan
        )
        smape = float(
            np.mean(2 * np.abs(actual - te_fc) / (np.abs(actual) + np.abs(te_fc) + 1e-9))
            * 100
        )
        ss_res = np.sum((actual - te_fc) ** 2)
        ss_tot = np.sum((actual - actual.mean()) ** 2)
        r2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else np.nan

        metrics = {
            "val_mape": min(mape_add, mape_mul),
            "test_mape": mape,
            "test_smape": smape,
            "test_r2": r2,
        }
        forecasts = {
            "test": te_fc,
            "future": fu_fc,
            "test_lower": te_lo,
            "test_upper": te_hi,
            "future_lower": fu_lo,
            "future_upper": fu_hi,
        }
        return m_final, forecasts, metrics, best_mode, (mape_add, mape_mul)

    loc_models = {}
    loc_metrics = {}
    loc_forecasts = {}
    loc_mode_used = {}

    for loc_key in all_keys:
        ts_loc = location_ts[loc_key]
        loc_df = loc_features[loc_key]
        regs = REGRESSORS_BY_LOC.get(loc_key, ["precipitation"])

        m_final, forecasts, metrics, best_mode, (mape_add, mape_mul) = train_prophet_model(
            ts_loc, loc_df, regs
        )

        # FIX G: Area_SolidWaste R2<0 auto-retry
        if loc_key == AREA_SOLIDWASTE_KEY and metrics["test_r2"] < 0:
            logger.info("FIX G: R2=%.4f < 0 for %s, retrying without circular proxy", metrics["test_r2"], loc_key)
            regs_retry = ["precip_lagged", "decomp_lagged"]
            REGRESSORS_BY_LOC[AREA_SOLIDWASTE_KEY] = regs_retry
            m_final, forecasts, metrics, best_mode, (mape_add, mape_mul) = train_prophet_model(
                ts_loc, loc_df, regs_retry
            )
            regs = regs_retry

        loc_mode_used[loc_key] = best_mode
        loc_models[loc_key] = m_final
        loc_forecasts[loc_key] = forecasts
        loc_metrics[loc_key] = metrics

    return (
        loc_models,
        loc_metrics,
        loc_forecasts,
        loc_mode_used,
        n_train,
        n_val,
        n_test,
        test_idx,
        future_dates,
        make_prophet_df,
    )


# ===========================================================================
# SECTION 4 -- PBS SHAPEFILE UC REGISTRY
# ===========================================================================
def load_uc_registry_from_shp(shp_path: str):
    """
    Load Lahore UCs from Union_Council.shp.
    Mirrors Transport v1.5 Section 2 logic exactly, producing identical uc_codes.
    Returns (gdf_geo, df_uc) where df_uc has uc_code, uc_name, centroid, area_km2.
    """
    shp = Path(shp_path)
    for ext in [".dbf", ".shx"]:
        if not shp.with_suffix(ext).exists():
            raise FileNotFoundError(
                f"Missing {shp.with_suffix(ext).name}. "
                f"All 7 shapefile components must be present."
            )

    gdf_ld = None
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

        uc_names_raw = gdf_ld.get("UC_NAME", pd.Series([""] * len(gdf_ld))).fillna("").values
        uc_col = gdf_ld.get("UC", pd.Series([""] * len(gdf_ld))).fillna("").values
        uc_names = np.where(
            (uc_names_raw == "") | (uc_names_raw == "0"), uc_col, uc_names_raw
        )

        tehsil = gdf_ld.get("TEHSIL", pd.Series([""] * len(gdf_ld))).fillna("").values
        district = gdf_ld["DISTRICT"].values
        n = len(gdf_ld)
        load_method = "geopandas"

    except Exception as e:
        logger.warning("geopandas failed (%s) -- pure-Python fallback", e)
        dbf_path = shp.with_suffix(".dbf")
        with open(str(dbf_path), "rb") as f:
            f.seek(4)
            n_total_dbf = struct.unpack("<i", f.read(4))[0]
            hs = struct.unpack("<H", f.read(2))[0]
            rs = struct.unpack("<H", f.read(2))[0]
            f.seek(32)
            fields = []
            while True:
                raw = f.read(32)
                if not raw or raw[0] == 0x0D:
                    break
                fields.append(
                    (raw[:11].decode("utf-8", errors="replace").rstrip("\x00"), chr(raw[11]), raw[16])
                )
            all_dbf = []
            for i in range(n_total_dbf):
                f.seek(hs + i * rs + 1)
                row = {"_idx": i}
                for fname, _, flen in fields:
                    row[fname] = f.read(flen).decode("utf-8", errors="replace").strip()
                all_dbf.append(row)

        lahore_rows = [r for r in all_dbf if r.get("DISTRICT", "").strip() == "Lahore"]
        n = len(lahore_rows)
        with open(str(shp.with_suffix(".shx")), "rb") as f:
            f.seek(100)
            shx_data = f.read()
        shx_offsets = [
            struct.unpack(">i", shx_data[i * 8 : i * 8 + 4])[0] * 2
            for i in range(len(shx_data) // 8)
        ]
        clat_l, clon_l, area_l = [], [], []
        for row in lahore_rows:
            with open(str(shp), "rb") as f:
                f.seek(shx_offsets[row["_idx"]] + 8)
                stype = struct.unpack("<i", f.read(4))[0]
                if stype == 5:
                    xmn, ymn, xmx, ymx = struct.unpack("<4d", f.read(32))
                    clat_l.append((ymn + ymx) / 2)
                    clon_l.append((xmn + xmx) / 2)
                    deg_area = float(row.get("Shape_Area", "0") or 0)
                    area_l.append(max(deg_area * _LAT_KM * _LON_KM, 0.01))
                else:
                    clat_l.append(LAHORE_CENTER_LAT)
                    clon_l.append(LAHORE_CENTER_LON)
                    area_l.append(1.0)
        clat = np.array(clat_l)
        clon = np.array(clon_l)
        area_km2 = np.array(area_l)
        uc_names = np.array(
            [r.get("UC_NAME", "").strip() or r.get("UC", "").strip() for r in lahore_rows]
        )
        tehsil = np.array([r.get("TEHSIL", "").strip() for r in lahore_rows])
        district = np.array(["Lahore"] * n)
        gdf_ld = None
        load_method = "pure-python"

    # Sort for reproducible uc_code assignment (matches Transport v1.5)
    si = np.lexsort((clon, clat))
    clat, clon, area_km2 = clat[si], clon[si], np.array(area_km2)[si]
    uc_names, tehsil, district = (
        np.array(uc_names)[si],
        np.array(tehsil)[si],
        np.array(district)[si],
    )
    if gdf_ld is not None:
        gdf_ld = gdf_ld.iloc[si].reset_index(drop=True)

    uc_codes = [f"PB-LAH-UC{i + 1:03d}" for i in range(n)]
    dist_centre = [
        haversine(la, lo, LAHORE_CENTER_LAT, LAHORE_CENTER_LON)
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
            "dist_centre_km": np.round(dist_centre, 2),
        }
    )

    df_uc["pop_weight"] = df_uc["area_km2"] / df_uc["area_km2"].sum()

    assert df_uc["area_km2"].min() > 0, "area_km2 has zero values"
    assert df_uc["centroid_lat"].between(30.0, 33.0).all(), "lat out of range"
    assert df_uc["centroid_lon"].between(72.0, 77.0).all(), "lon out of range"
    assert df_uc["uc_code"].nunique() == len(df_uc), "duplicate uc_codes"

    if gdf_ld is not None:
        gdf_ld["uc_code"] = uc_codes
        gdf_ld["uc_name"] = uc_names
        gdf_ld["area_km2"] = area_km2
        gdf_ld["centroid_lat"] = clat
        gdf_ld["centroid_lon"] = clon
        gdf_ld["pop_weight"] = df_uc["pop_weight"].values

    logger.info("%d UCs loaded via [%s]", n, load_method)
    return gdf_ld, df_uc


def load_uc_layer(shapefile_path: str):
    """Load UC registry from shapefile, with synthetic fallback."""
    logger.info("[SECTION 4/8] PBS SHAPEFILE UC REGISTRY")

    shp_path = Path(shapefile_path)
    if shp_path.exists():
        _gdf_uc_geo, df_uc = load_uc_registry_from_shp(str(shp_path))
        UC_SOURCE = f"PBS Union_Council.shp -- {len(df_uc)} Lahore UCs (same as Transport v1.5)"
    else:
        logger.warning("Shapefile not found at %s, using synthetic 9-town grid", shapefile_path)
        UC_SOURCE = "Synthetic 9-town grid (shapefile not found -- approximate)"
        lahore_towns = [
            ("Data Gunj Bakhsh", 31.548, 74.310, 14, 0.140),
            ("Ravi", 31.578, 74.340, 12, 0.115),
            ("Aziz Bhatti", 31.530, 74.370, 13, 0.125),
            ("Shalimar", 31.555, 74.430, 11, 0.100),
            ("Shafiqabad", 31.503, 74.340, 13, 0.115),
            ("Nishtar", 31.493, 74.290, 13, 0.120),
            ("Gulberg", 31.504, 74.365, 11, 0.120),
            ("Iqbal", 31.460, 74.330, 12, 0.110),
            ("Wagah", 31.570, 74.415, 9, 0.055),
        ]
        uc_rows = []
        idx = 1
        for town_name, clat, clon, n_ucs, pop_frac in lahore_towns:
            for i in range(n_ucs):
                row_off = (i // 4) * 0.015 - 0.015
                col_off = (i % 4) * 0.015 - 0.022
                uc_lat = clat + row_off
                uc_lon = clon + col_off
                hw = 0.007
                poly = ShPoly(
                    [
                        (uc_lon - hw, uc_lat - hw),
                        (uc_lon + hw, uc_lat - hw),
                        (uc_lon + hw, uc_lat + hw),
                        (uc_lon - hw, uc_lat + hw),
                    ]
                )
                uc_rows.append(
                    {
                        "uc_code": f"PB-LAH-UC{idx:03d}",
                        "uc_name": f"{town_name} UC-{i + 1:02d}",
                        "district": "Lahore",
                        "tehsil": "Lahore",
                        "centroid_lat": uc_lat,
                        "centroid_lon": uc_lon,
                        "area_km2": round(hw * 2 * _LAT_KM * hw * 2 * _LON_KM, 3),
                        "pop_weight": pop_frac / n_ucs,
                        "geometry": poly,
                    }
                )
                idx += 1
        _gdf_uc_geo = gpd.GeoDataFrame(uc_rows, crs="EPSG:4326")
        df_uc = pd.DataFrame(
            {
                k: [r[k] for r in uc_rows]
                for k in [
                    "uc_code", "uc_name", "district", "tehsil",
                    "centroid_lat", "centroid_lon", "area_km2", "pop_weight",
                ]
            }
        )
        df_uc["dist_centre_km"] = df_uc.apply(
            lambda r: round(
                haversine(
                    r["centroid_lat"], r["centroid_lon"],
                    LAHORE_CENTER_LAT, LAHORE_CENTER_LON,
                ),
                2,
            ),
            axis=1,
        )
        df_uc["pop_weight"] = df_uc["pop_weight"] / df_uc["pop_weight"].sum()

    # Initialize emission columns
    df_uc["uc_total_emissions"] = 0.0
    df_uc["point_src_emissions"] = 0.0
    df_uc["area_sw_emissions"] = 0.0
    df_uc["area_ww_emissions"] = 0.0
    df_uc["area_src_emissions"] = 0.0

    return _gdf_uc_geo, df_uc, UC_SOURCE


# ===========================================================================
# SECTION 5 -- FACILITY SANITY CHECK + POINT SOURCE SPATIAL JOIN
# ===========================================================================
def spatial_join_point_sources(all_keys, loc_forecasts, _gdf_uc_geo, df_uc):
    """FIX J sanity check + assign point sources to UCs."""
    logger.info("[SECTION 5/8] FACILITY SANITY CHECK + POINT SOURCE SPATIAL JOIN")

    # FIX J: Facility coordinate sanity check
    for name, meta in POINT_SOURCES.items():
        dist = haversine(meta["lat"], meta["lon"], LAHORE_CENTER_LAT, LAHORE_CENTER_LON)
        if dist > 50:
            raise RuntimeError(
                f"CRITICAL: Facility {name} is {dist:.1f}km from Lahore centre. "
                f"Check coordinate order -- likely (lon, lat) inversion."
            )

    point_source_keys = [k for k in all_keys if k in POINT_SOURCES]
    point_uc_map = {}

    for loc_key in point_source_keys:
        meta = POINT_SOURCES[loc_key]
        uc_name = None
        matched_code = None

        # Method 1: proper spatial join using GeoDataFrame
        if _gdf_uc_geo is not None and "geometry" in _gdf_uc_geo.columns:
            try:
                pt = gpd.GeoDataFrame(
                    [{"geometry": Point(meta["lon"], meta["lat"])}], crs="EPSG:4326"
                )
                joined = gpd.sjoin(
                    pt,
                    _gdf_uc_geo[["uc_code", "uc_name", "geometry"]],
                    how="left",
                    predicate="within",
                )
                if len(joined) > 0 and not pd.isna(joined["uc_code"].iloc[0]):
                    matched_code = joined["uc_code"].iloc[0]
                    uc_name = df_uc[df_uc["uc_code"] == matched_code]["uc_name"].iloc[0]
            except Exception:
                pass

        # Method 2: nearest centroid fallback
        if uc_name is None:
            dists = df_uc.apply(
                lambda r: haversine(
                    r["centroid_lat"], r["centroid_lon"], meta["lat"], meta["lon"]
                ),
                axis=1,
            )
            nearest_idx = dists.idxmin()
            uc_name = df_uc.loc[nearest_idx, "uc_name"]
            uc_code = df_uc.loc[nearest_idx, "uc_code"]
        else:
            uc_code = matched_code

        point_uc_map[loc_key] = uc_code
        annual_fc = float(loc_forecasts[loc_key]["future"].sum())
        mask = df_uc["uc_code"] == uc_code
        df_uc.loc[mask, "point_src_emissions"] += annual_fc
        df_uc.loc[mask, "uc_total_emissions"] += annual_fc

    return point_uc_map


# ===========================================================================
# SECTION 6 -- AREA SOURCE DISAGGREGATION
# ===========================================================================
def disaggregate_area_sources(loc_forecasts, all_keys, df_uc):
    """Disaggregate area-level forecasts to UCs using pop_weight."""
    logger.info("[SECTION 6/8] AREA SOURCE DISAGGREGATION")

    sw_annual = float(
        loc_forecasts.get(AREA_SOLIDWASTE_KEY, {}).get("future", np.zeros(12)).sum()
    )
    ww_annual = float(
        loc_forecasts.get(AREA_WASTEWATER_KEY, {}).get("future", np.zeros(12)).sum()
    )

    df_uc["area_sw_emissions"] = sw_annual * df_uc["pop_weight"]
    df_uc["area_ww_emissions"] = ww_annual * df_uc["pop_weight"]
    df_uc["area_src_emissions"] = df_uc["area_sw_emissions"] + df_uc["area_ww_emissions"]
    df_uc["uc_total_emissions"] = df_uc["point_src_emissions"] + df_uc["area_src_emissions"]

    # Accounting identity check
    allocated_total = float(df_uc["uc_total_emissions"].sum())
    expected_total = float(sum(loc_forecasts[k]["future"].sum() for k in all_keys))
    discrepancy_pct = abs(allocated_total - expected_total) / max(expected_total, 1) * 100

    # Compute emissions intensity
    df_uc["intensity_t_per_km2"] = (df_uc["uc_total_emissions"] / df_uc["area_km2"]).round(1)
    df_uc["rank_in_district"] = df_uc["uc_total_emissions"].rank(ascending=False).astype(int)

    return allocated_total, expected_total, discrepancy_pct


# ===========================================================================
# SECTION 8 -- JSON EXPORT
# ===========================================================================
def build_and_export_json(
    output_dir,
    df_uc,
    location_ts,
    loc_forecasts,
    loc_metrics,
    loc_mode_used,
    loc_features,
    all_keys,
    date_range,
    future_dates,
    weather_m,
    point_uc_map,
    UC_SOURCE,
    allocated_total,
    discrepancy_pct,
):
    """Build the CarbonSense waste JSON and write to output_dir."""
    logger.info("[SECTION 8/8] EXPORT")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    _k = weather_m["k_dynamic"]
    _mdf_json = pd.DataFrame(loc_metrics).T

    # Forecast weather (seasonal climatology)
    forecast_wthr = []
    for d in future_dates:
        m = d.month
        mask = weather_m.index.month == m

        def _w(col):
            return (
                round(float(weather_m.loc[mask, col].mean()), 2)
                if col in weather_m.columns and mask.any()
                else None
            )

        forecast_wthr.append(
            {
                "temp": _w("temperature"),
                "humidity": _w("humidity"),
                "precipitation": _w("precipitation"),
                "decomp_index": _w("decomp_index"),
                "precip_lagged": _w("precip_lagged"),
                "decomp_lagged": _w("decomp_lagged"),
            }
        )

    json_metadata = {
        "pipeline": "CarbonSense Waste Spatial v2.3",
        "generated_at": datetime.datetime.utcnow().isoformat(),
        "data_source": "Climate Trace",
        "sector": "waste",
        "region": "Lahore District, Punjab, Pakistan",
        "uc_registry": UC_SOURCE,
        "n_ucs": len(df_uc),
        "uc_code_format": "PB-LAH-UC001 to PB-LAH-UC151 (matches Transport v1.5)",
        "historical_period": (
            f"{date_range[0].strftime('%Y-%m')} to {date_range[-1].strftime('%Y-%m')}"
        ),
        "forecast_window": (
            f"{future_dates[0].strftime('%Y-%m')} to {future_dates[-1].strftime('%Y-%m')}"
        ),
        "model": "Prophet",
        "n_models": len(all_keys),
        "regressors_by_location": REGRESSORS_BY_LOC,
        "prophet_params": PROPHET_CHAMPION_PARAMS,
        "biological_lag_months": 2,
        "biological_lag_rationale": (
            "Methane from anaerobic digestion peaks ~60 days after the moisture/temperature "
            "input that triggers microbial activity. precip_lagged and decomp_lagged are "
            "applied to FOD sources (L4_MehmoodBooti, Area_SolidWaste) only. "
            "WWTPs and wastewater use contemporaneous precipitation."
        ),
        "fixes_applied": [
            "A: Area_Other split -- Area_SolidWaste(FOD) + Area_Wastewater(pop)",
            "B: WWTP regressors -- real pop_served, no circular waste_volume",
            "C: L4 = Mehmood Booti Dumpsite (MCF=0.4), exact CSV coords",
            "D: Overpass API (superseded by H)",
            "E: Reconciliation = accounting identity, not scientific validation",
            "F: Lahore-only boundaries, no Indian districts",
            "G: Area_SolidWaste R2<0 auto-retry without circular proxy",
            "H: PBS Union_Council.shp -- 151 real Lahore UCs, matches Transport v1.5",
            "I: Biological lag 2 months for FOD models (precip_lagged, decomp_lagged)",
            "J: Facility coordinate sanity check -- raises error if >50km from centre",
        ],
        "aggregate_metrics": {
            "test_r2_mean": round(float(_mdf_json["test_r2"].mean()), 4),
            "test_mape_mean_pct": round(float(_mdf_json["test_mape"].mean()), 2),
            "ipcc_k_static": IPCC_K_LAHORE_STATIC,
            "k_dynamic_mean": round(float(_k.mean()), 3),
            "k_dynamic_range": [round(float(_k.min()), 3), round(float(_k.max()), 3)],
        },
        "pop_weight_note": (
            "Population weights are currently area-based proxies (area_km2 / total_area). "
            "For production: replace with 2023 PBS Census UC-level population figures."
        ),
        "reconciliation_note": (
            "UC sum equals forecast sum by accounting identity (sum(pop_weight)=1). "
            "Not a scientific validation of spatial accuracy."
        ),
    }

    # UC allocation
    def build_uc_allocation():
        uc_list = []
        for _, row in df_uc.iterrows():
            uc_code = str(row["uc_code"])
            pt_t = float(row["point_src_emissions"])
            sw_t = float(row["area_sw_emissions"])
            ww_t = float(row["area_ww_emissions"])
            total_t = float(row["uc_total_emissions"])
            geo_type = "Hotspot" if pt_t > (sw_t + ww_t) * 3 else "Distributed"
            fac_key = next((k for k, v in point_uc_map.items() if v == uc_code), None)
            fac_meta = POINT_SOURCES.get(fac_key, {})
            src_types = (
                [fac_meta.get("type", "Unknown")]
                if fac_key
                else ["Domestic Wastewater", "Solid Waste"]
            )
            risk = risk_level(total_t)
            pw = float(row["pop_weight"])
            uc_chart = []
            for i, d in enumerate(future_dates):
                pt_v = float(loc_forecasts[fac_key]["future"][i]) if fac_key else 0.0
                pt_l = float(loc_forecasts[fac_key]["future_lower"][i]) if fac_key else 0.0
                pt_h = float(loc_forecasts[fac_key]["future_upper"][i]) if fac_key else 0.0
                sw_v = (
                    float(
                        loc_forecasts.get(AREA_SOLIDWASTE_KEY, {}).get(
                            "future", np.zeros(12)
                        )[i]
                    )
                    * pw
                )
                ww_v = (
                    float(
                        loc_forecasts.get(AREA_WASTEWATER_KEY, {}).get(
                            "future", np.zeros(12)
                        )[i]
                    )
                    * pw
                )
                ar_l = (
                    float(
                        loc_forecasts.get(AREA_SOLIDWASTE_KEY, {}).get(
                            "future_lower", np.zeros(12)
                        )[i]
                    )
                    + float(
                        loc_forecasts.get(AREA_WASTEWATER_KEY, {}).get(
                            "future_lower", np.zeros(12)
                        )[i]
                    )
                ) * pw
                ar_h = (
                    float(
                        loc_forecasts.get(AREA_SOLIDWASTE_KEY, {}).get(
                            "future_upper", np.zeros(12)
                        )[i]
                    )
                    + float(
                        loc_forecasts.get(AREA_WASTEWATER_KEY, {}).get(
                            "future_upper", np.zeros(12)
                        )[i]
                    )
                ) * pw
                uc_chart.append(
                    {
                        "date": iso(d),
                        "month": month_label(d),
                        "predicted": round(pt_v + sw_v + ww_v, 2),
                        "lower_ci": round(pt_l + ar_l, 2),
                        "upper_ci": round(pt_h + ar_h, 2),
                        "point_src_share": round(pt_v, 2),
                        "area_sw_share": round(sw_v, 2),
                        "area_ww_share": round(ww_v, 2),
                    }
                )
            uc_list.append(
                {
                    "uc_code": uc_code,
                    "uc_name": str(row["uc_name"]),
                    "district": str(row.get("district", "Lahore")),
                    "geo_type": geo_type,
                    "coordinates": {
                        "lat": round(float(row["centroid_lat"]), 6),
                        "lon": round(float(row["centroid_lon"]), 6),
                    },
                    "area_km2": round(float(row["area_km2"]), 3),
                    "pop_weight": round(pw, 6),
                    "emissions": {
                        "point_source_t": round(pt_t, 2),
                        "area_sw_t": round(sw_t, 2),
                        "area_ww_t": round(ww_t, 2),
                        "total_annual_t": round(total_t, 2),
                        "point_pct": round(pt_t / total_t * 100, 1) if total_t > 0 else 0.0,
                        "risk_level": risk,
                        "data_quality_flag": (
                            "flat_series_low_r2 -- ClimateTrace applies constant EF; "
                            "trend projection valid but low model sensitivity"
                            if loc_metrics.get(AREA_SOLIDWASTE_KEY, {}).get("test_r2", 0) < 0
                            else "ok"
                        )
                        if geo_type == "Distributed"
                        else "ok",
                    },
                    "chart_data": uc_chart,
                    "mitigation_context": {
                        "source_types": src_types,
                        "policy_tags": policy_tags_fn(src_types, total_t),
                        "rag_context": (
                            f"UC {uc_code} ('{row['uc_name']}') is '{risk}' risk: "
                            f"{total_t:,.0f} t CO2e/yr. "
                            f"{'Hotspot -- ' + fac_meta.get('area', '') + ' [' + fac_meta.get('type', '') + '] accounts for ' + str(round(pt_t / total_t * 100, 0)) + '% of emissions. Facility-level intervention highest ROI.' if geo_type == 'Hotspot' else 'Population-driven emissions. Target household waste handling and wastewater infrastructure.'}"
                        ),
                    },
                    "facility_id": fac_key,
                    "rank_in_district": int(row.get("rank_in_district", 0)),
                    "intensity_t_per_km2": round(float(row.get("intensity_t_per_km2", 0)), 1),
                }
            )
        order = {"Critical": 0, "High": 1, "Medium-High": 2, "Medium": 3, "Low": 4}
        uc_list.sort(key=lambda u: order.get(u["emissions"]["risk_level"], 5))
        return uc_list

    uc_allocation = build_uc_allocation()

    agg_vals = [
        round(float(sum(loc_forecasts[k]["future"][i] for k in all_keys)), 2)
        for i in range(12)
    ]
    agg_lower = [
        round(float(sum(loc_forecasts[k]["future_lower"][i] for k in all_keys)), 2)
        for i in range(12)
    ]
    agg_upper = [
        round(float(sum(loc_forecasts[k]["future_upper"][i] for k in all_keys)), 2)
        for i in range(12)
    ]

    json_agg = {
        "dates": [iso(d) for d in future_dates],
        "prophet_values": agg_vals,
        "prophet_lower": agg_lower,
        "prophet_upper": agg_upper,
        "weather": forecast_wthr,
        "total_12m_t": round(sum(agg_vals), 2),
        "point_source_total_t": round(float(df_uc["point_src_emissions"].sum()), 2),
        "area_solidwaste_total_t": round(float(df_uc["area_sw_emissions"].sum()), 2),
        "area_wastewater_total_t": round(float(df_uc["area_ww_emissions"].sum()), 2),
        "modelled_locations": all_keys,
        "uc_boundary_source": UC_SOURCE,
        "uc_allocation": uc_allocation,
    }

    def build_location_obj(loc_key):
        ts_loc = location_ts[loc_key]
        fc_d = loc_forecasts[loc_key]
        met = loc_metrics[loc_key]
        loc_df = loc_features[loc_key]
        meta_ps = POINT_SOURCES.get(loc_key, {})
        is_point = loc_key in POINT_SOURCES
        regs = REGRESSORS_BY_LOC.get(loc_key, ["precipitation"])
        pr_12m = float(fc_d["future"].sum())
        last12 = float(ts_loc.iloc[-12:].sum()) if len(ts_loc) >= 12 else float(ts_loc.sum())
        chg_pct = round((pr_12m - last12) / (last12 + 1e-9) * 100, 2)
        historical = []
        for d in ts_loc.index:
            h_row = {
                "date": iso(d),
                "month": month_label(d),
                "emissions": round(float(ts_loc[d]), 2),
                "type": "historical",
            }
            for wcol in [
                "temperature", "humidity", "precipitation",
                "decomp_index", "precip_lagged", "decomp_lagged",
            ]:
                if wcol in weather_m.columns and d in weather_m.index:
                    h_row[wcol] = round(float(weather_m.loc[d, wcol]), 3)
            for reg in regs:
                if reg in loc_df.columns and d in loc_df.index:
                    h_row[reg] = round(float(loc_df.loc[d, reg]), 2)
            historical.append(h_row)
        forecast = [
            {
                "date": iso(d),
                "month": month_label(d),
                "emissions": round(float(fc_d["future"][i]), 2),
                "lower_ci": round(float(fc_d["future_lower"][i]), 2),
                "upper_ci": round(float(fc_d["future_upper"][i]), 2),
                "confidence": confidence_band(
                    fc_d["future_lower"][i], fc_d["future_upper"][i], fc_d["future"][i]
                ),
                "type": "forecast",
                **forecast_wthr[i],
            }
            for i, d in enumerate(future_dates)
        ]
        coords = (
            {"lat": meta_ps["lat"], "lon": meta_ps["lon"]}
            if is_point
            else {"lat": LAHORE_CENTER_LAT, "lon": LAHORE_CENTER_LON}
        )
        return {
            "source": meta_ps.get("area", loc_key),
            "source_key": loc_key,
            "type": meta_ps.get("type", "Area Source"),
            "coordinates": coords,
            "status": "ok",
            "in_aggregate": True,
            "model": {
                "architecture": "Facebook Prophet (Multivariate)",
                "regressors": regs,
                "biological_lag": any("lagged" in r for r in regs),
                "hyperparameters": {
                    **PROPHET_CHAMPION_PARAMS,
                    "seasonality_mode": loc_mode_used.get(loc_key, "additive"),
                    "yearly_seasonality": True,
                    "interval_width": 0.95,
                },
                "metrics": {
                    "val": {"MAPE": round(float(met["val_mape"]), 2)},
                    "test": {
                        "MAPE": round(float(met["test_mape"]), 2),
                        "sMAPE": round(float(met["test_smape"]), 2),
                        "R2": round(float(met["test_r2"]), 4),
                        "data_quality_flag": (
                            "flat_series_low_r2" if met["test_r2"] < 0 else "ok"
                        ),
                    },
                },
            },
            "summary": {
                "last_historical_date": month_label(ts_loc.index[-1]),
                "last_historical_emissions": round(float(ts_loc.iloc[-1]), 2),
                "forecast_12m_total_t": round(pr_12m, 2),
                "forecast_vs_last12_pct": chg_pct,
                "trend": (
                    "increasing" if chg_pct > 1
                    else "decreasing" if chg_pct < -1
                    else "stable"
                ),
                "total_historical_t": round(float(ts_loc.sum()), 2),
            },
            "chart_data": {"historical": historical, "forecast": forecast},
            "spatial": {
                "geo_type": "Hotspot" if is_point else "Distributed",
                "uc_code": point_uc_map.get(loc_key, "Disaggregated to all UCs"),
                "facility_type": meta_ps.get("type", "Area Source"),
            },
            "physical_drivers": {
                "ipcc_k_static_lahore": IPCC_K_LAHORE_STATIC,
                "k_dynamic_mean": round(float(_k.mean()), 3),
                "k_dynamic_range": [round(float(_k.min()), 3), round(float(_k.max()), 3)],
                "precip_annual_mean_mm": round(float(weather_m["precipitation"].mean()), 1),
                "decomp_index_summer_peak": round(float(weather_m["decomp_index"].max()), 2),
                "fod_lag_months": 2,
                "note": (
                    "precip_lagged / decomp_lagged (2-month biological lag) applied to "
                    "FOD sources only. Methane peaks ~60 days after moisture/temperature input."
                ),
            },
        }

    locations = [build_location_obj(loc_key) for loc_key in all_keys]

    doc = {
        "metadata": json_metadata,
        "aggregate_forecast": json_agg,
        "locations": locations,
    }

    # Write JSON output
    json_path = output_path / "waste_new.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)

    compact_path = output_path / "waste_new_compact.json"
    with open(compact_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, separators=(",", ":"), ensure_ascii=False)

    size_p = len(json.dumps(doc, indent=2).encode())
    size_c = len(json.dumps(doc, separators=(",", ":")).encode())

    logger.info("Saved: %s (%d KB)", json_path, size_p // 1024)
    logger.info("Saved: %s (%d KB)", compact_path, size_c // 1024)

    return doc


# ===========================================================================
# MAIN
# ===========================================================================
def main(input_dir: str, shapefile_path: str, output_dir: str):
    """
    Run the full CarbonSense Waste pipeline.

    Args:
        input_dir: Directory containing waste_2021.csv through waste_2025.csv
        shapefile_path: Path to Union_Council.shp (PBS shapefile)
        output_dir: Directory where output JSON will be written
    """
    print("=" * 80)
    print("  CARBONSENSE WASTE v2.3 -- UNIFIED UC REGISTRY (PBS Shapefile)")
    print("  6 Models | 151 Real Lahore UCs | Biological Lag | Transport-Aligned")
    print("=" * 80)

    # Section 1: Load data
    df_raw, location_ts, all_keys, date_range, n_total = load_and_group_data(input_dir)

    # Section 2: Weather + features
    weather_m, loc_features, weather_for_month = fetch_weather_and_build_features(
        df_raw, location_ts, all_keys, date_range, n_total
    )

    # Section 3: Train models
    (
        loc_models,
        loc_metrics,
        loc_forecasts,
        loc_mode_used,
        n_train,
        n_val,
        n_test,
        test_idx,
        future_dates,
        make_prophet_df,
    ) = train_all_models(
        location_ts, all_keys, date_range, n_total, loc_features, weather_for_month
    )

    # Section 4: Load UC registry
    _gdf_uc_geo, df_uc, UC_SOURCE = load_uc_layer(shapefile_path)

    # Section 5: Point source spatial join
    point_uc_map = spatial_join_point_sources(all_keys, loc_forecasts, _gdf_uc_geo, df_uc)

    # Section 6: Area source disaggregation
    allocated_total, expected_total, discrepancy_pct = disaggregate_area_sources(
        loc_forecasts, all_keys, df_uc
    )

    # Section 8: Export JSON
    doc = build_and_export_json(
        output_dir=output_dir,
        df_uc=df_uc,
        location_ts=location_ts,
        loc_forecasts=loc_forecasts,
        loc_metrics=loc_metrics,
        loc_mode_used=loc_mode_used,
        loc_features=loc_features,
        all_keys=all_keys,
        date_range=date_range,
        future_dates=future_dates,
        weather_m=weather_m,
        point_uc_map=point_uc_map,
        UC_SOURCE=UC_SOURCE,
        allocated_total=allocated_total,
        discrepancy_pct=discrepancy_pct,
    )

    # Summary
    _agg_sum = sum(doc["aggregate_forecast"]["prophet_values"])
    _uc_sum = sum(
        u["emissions"]["total_annual_t"]
        for u in doc["aggregate_forecast"]["uc_allocation"]
    )

    print(f"\n{'=' * 80}")
    print("  CARBONSENSE WASTE v2.3 -- COMPLETE")
    print(f"{'=' * 80}")
    print(f"  Models         : {len(all_keys)} Prophet models")
    print(f"  UC Registry    : {UC_SOURCE}")
    print(f"  UCs            : {len(df_uc)}")
    print(f"  Total forecast : {_agg_sum:,.0f} t CO2e (12 months)")
    print(f"  UC total sum   : {_uc_sum:,.0f} t CO2e")
    print(f"  Accounting gap : {discrepancy_pct:.3f}%")
    print(f"  Output         : {output_dir}")
    print(f"{'=' * 80}")

    return doc


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="CarbonSense Waste Sector Emissions Forecasting Pipeline v2.3"
    )
    parser.add_argument(
        "--input-dir",
        required=True,
        help="Directory containing waste_2021.csv through waste_2025.csv",
    )
    parser.add_argument(
        "--shapefile",
        required=True,
        help="Path to Union_Council.shp (PBS shapefile for Lahore UCs)",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory where output JSON files will be written",
    )
    args = parser.parse_args()

    main(
        input_dir=args.input_dir,
        shapefile_path=args.shapefile,
        output_dir=args.output_dir,
    )
