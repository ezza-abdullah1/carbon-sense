"""
CarbonSense: Per-Location XGBoost + Prophet Pipeline v2.1
Lahore Division - Power Sector | 2021-2025 | Production

Converted from Colab notebook PI_model_json.ipynb.

Architecture:
  - One XGBoost + one Prophet trained independently per physical location
  - XGBoost features: lag_1, lag_2, lag_12, CDD, HDD, humidity, capacity_factor (7 feats)
  - Prophet regressors: CDD, HDD, humidity, capacity_factor
  - Forecast: 12-month rolling (XGBoost recursive | Prophet native)

Usage:
  python power_model.py --input-dir ./data --output-dir ./output
  python power_model.py --input-dir ./data --output-dir ./output --use-synthetic
"""

# --- Standard Library --------------------------------------------------------
import argparse
import json
import logging
import os
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# --- Core --------------------------------------------------------------------
import numpy as np
import pandas as pd

# --- Statistical models ------------------------------------------------------
from statsmodels.tsa.stattools import adfuller

# --- Machine Learning --------------------------------------------------------
from sklearn.metrics import (
    mean_absolute_error,
    mean_absolute_percentage_error,
    mean_squared_error,
    r2_score,
)
from sklearn.model_selection import TimeSeriesSplit

# --- Gradient Boosting -------------------------------------------------------
from xgboost import XGBRegressor

# --- Prophet -----------------------------------------------------------------
from prophet import Prophet

# =============================================================================
# GLOBAL CONFIG
# =============================================================================
RANDOM_STATE = 42
TARGET_GAS = "co2"
FORECAST_MONTHS = 12
TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
MIN_MONTHS = 18  # minimum months needed to train a location
LAT = 31.5204  # Lahore
LON = 74.3587

# --- Feature sets (single source of truth) -----------------------------------
WEATHER_COLS = ["CDD", "HDD", "humidity"]
CAPACITY_COLS = ["capacity_factor"]
XGB_LAGS = [1, 2, 12]
XGB_FEATURES = WEATHER_COLS + CAPACITY_COLS
PROPHET_REGS = WEATHER_COLS + CAPACITY_COLS
N_XGB_FEATS = len(XGB_LAGS) + len(XGB_FEATURES)
XGB_FEAT_NAMES = [f"lag_{l}" for l in XGB_LAGS] + XGB_FEATURES

# --- XGBoost hyperparameter grid ---------------------------------------------
XGB_GRID = {
    "n_estimators": [50, 100, 200, 300],
    "max_depth": [3, 5, 7],
    "learning_rate": [0.01, 0.05, 0.1, 0.2],
}

# --- Prophet hyperparameter grid ---------------------------------------------
PROPHET_GRID = [
    {
        "changepoint_prior_scale": cps,
        "seasonality_prior_scale": sps,
        "seasonality_mode": smode,
    }
    for cps in [0.01, 0.1, 0.5]
    for sps in [1.0, 10.0]
    for smode in ["additive", "multiplicative"]
]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def smape(a: np.ndarray, p: np.ndarray) -> float:
    """Symmetric MAPE."""
    a, p = np.asarray(a).flatten(), np.asarray(p).flatten()
    denom = np.abs(a) + np.abs(p)
    mask = denom > 0
    return float(np.mean(2 * np.abs(p[mask] - a[mask]) / denom[mask]) * 100)


def compute_metrics(actual, predicted) -> dict:
    """MAE, RMSE, MAPE, sMAPE, R2."""
    a = np.asarray(actual).flatten()
    p = np.asarray(predicted).flatten()
    n = min(len(a), len(p))
    a, p = a[:n], p[:n]
    mask = a > 0
    mape = (
        float(mean_absolute_percentage_error(a[mask], p[mask]) * 100)
        if mask.sum() > 0
        else np.nan
    )
    return {
        "MAE": float(mean_absolute_error(a, p)),
        "RMSE": float(np.sqrt(mean_squared_error(a, p))),
        "MAPE": mape,
        "sMAPE": smape(a, p),
        "R2": float(r2_score(a, p)),
    }


def grid_score(actual: np.ndarray, predicted: np.ndarray) -> float:
    """
    Unified model selection score robust to near-zero and near-constant series.

    Uses MAPE when well-defined (finite and < 500%), falls back to nRMSE
    (normalised RMSE) otherwise. Lower score = better model in both cases.
    """
    a = np.asarray(actual).flatten()
    p = np.asarray(predicted).flatten()
    n = min(len(a), len(p))
    a, p = a[:n], p[:n]

    # Try MAPE first
    mask = a > 0
    if mask.sum() > 0:
        mape = float(mean_absolute_percentage_error(a[mask], p[mask]) * 100)
        if np.isfinite(mape) and mape < 500.0:
            return mape

    # Fallback: nRMSE
    rmse = float(np.sqrt(mean_squared_error(a, p)))
    mean_act = float(np.mean(np.abs(a)))
    if mean_act > 0:
        return rmse / mean_act * 100
    return rmse


def safe_float(v, precision: int = 4):
    if v is None:
        return None
    try:
        f = float(v)
        return None if (np.isnan(f) or np.isinf(f)) else round(f, precision)
    except Exception:
        return None


# =============================================================================
# WEATHER UTILITIES
# =============================================================================


def fetch_weather(global_min, global_max, complete_idx):
    """
    Fetch real Lahore weather from Open-Meteo archive API.
    Returns (weather_monthly DataFrame, source string).
    Falls back to synthetic seasonal proxy on failure.
    """
    try:
        import openmeteo_requests
        import requests_cache
        from retry_requests import retry

        cache_session = requests_cache.CachedSession(".omcache_v2", expire_after=-1)
        retry_session = retry(cache_session, retries=5, backoff_factor=0.3)
        om_client = openmeteo_requests.Client(session=retry_session)

        resp = om_client.weather_api(
            "https://archive-api.open-meteo.com/v1/archive",
            params={
                "latitude": LAT,
                "longitude": LON,
                "start_date": global_min.strftime("%Y-%m-%d"),
                "end_date": global_max.strftime("%Y-%m-%d"),
                "hourly": ["temperature_2m", "relative_humidity_2m"],
                "timezone": "Asia/Karachi",
            },
        )
        hourly = resp[0].Hourly()
        weather_df = pd.DataFrame(
            {
                "date": pd.date_range(
                    start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
                    end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
                    freq=pd.Timedelta(seconds=hourly.Interval()),
                    inclusive="left",
                ),
                "temp": hourly.Variables(0).ValuesAsNumpy(),
                "humidity": hourly.Variables(1).ValuesAsNumpy(),
            }
        ).set_index("date")

        weather_monthly = weather_df.resample("MS").mean()
        weather_monthly.index = weather_monthly.index.tz_localize(None)
        weather_monthly["CDD"] = weather_monthly["temp"].apply(
            lambda x: max(0, x - 18)
        )
        weather_monthly["HDD"] = weather_monthly["temp"].apply(
            lambda x: max(0, 18 - x)
        )

        logger.info("Real Lahore weather fetched: %d months", len(weather_monthly))
        return weather_monthly, "open_meteo_archive"

    except Exception as e:
        logger.warning("Weather fetch failed (%s). Using synthetic seasonal proxy.", e)
        months = complete_idx
        temp_syn = 22 + 12 * np.sin((months.month - 5) / 12 * 2 * np.pi)
        weather_monthly = pd.DataFrame(
            {
                "temp": temp_syn,
                "humidity": 55 + 15 * np.cos((months.month - 7) / 12 * 2 * np.pi),
                "CDD": np.maximum(0, temp_syn - 18),
                "HDD": np.maximum(0, 18 - temp_syn),
            },
            index=months,
        )
        return weather_monthly, "synthetic_proxy"


# =============================================================================
# MAIN PIPELINE
# =============================================================================


def main(input_dir: str, output_dir: str, use_synthetic: bool = False):
    """
    Run the full CarbonSense power-sector forecasting pipeline.

    Args:
        input_dir: Directory containing power_2021.csv through power_2025.csv
        output_dir: Directory where output JSON will be written
        use_synthetic: If True, use synthetic demo data instead of CSVs
    """
    # Make mutable copies of the global feature config so we can rename cols
    global CAPACITY_COLS, XGB_FEATURES, PROPHET_REGS, N_XGB_FEATS, XGB_FEAT_NAMES

    np.random.seed(RANDOM_STATE)
    os.makedirs(output_dir, exist_ok=True)

    logger.info("=" * 70)
    logger.info("CarbonSense: Per-Location XGBoost + Prophet v2.1")
    logger.info("=" * 70)

    # =========================================================================
    # SECTION 1 - DATA LOADING
    # =========================================================================
    logger.info("[1/8] DATA LOADING")

    df_list = []

    if use_synthetic:
        logger.info("Generating synthetic Climate TRACE data (3 plants, 2021-2025)")
        dates = pd.date_range("2021-01-01", "2025-12-31", freq="MS")
        n = len(dates)
        plants = {
            "Lahore_CCGT_North": dict(
                base=180_000, amp=35_000, trend=-800, cf_base=0.72
            ),
            "Lahore_Coal_South": dict(
                base=520_000, amp=70_000, trend=-1_500, cf_base=0.81
            ),
            "Lahore_Gas_East": dict(
                base=110_000, amp=20_000, trend=-400, cf_base=0.65
            ),
        }
        rows = []
        for sname, cfg in plants.items():
            em = (
                np.array([cfg["base"] + i * (cfg["trend"] / 12) for i in range(n)])
                + np.sin(np.arange(n) / 12 * 2 * np.pi) * cfg["amp"]
                + np.random.normal(0, cfg["amp"] * 0.07, n)
            )
            cf = np.clip(
                cfg["cf_base"]
                + 0.12 * np.sin(np.arange(n) / 12 * 2 * np.pi)
                + np.random.normal(0, 0.03, n),
                0.2,
                1.0,
            )
            for i in range(n):
                rows.append(
                    {
                        "start_time": dates[i],
                        "gas": TARGET_GAS,
                        "emissions_quantity": max(0, em[i]),
                        "source_name": sname,
                        "original_inventory_sector": "electricity-generation",
                        "source_id": f"SYN_{sname[:3]}",
                        "capacity_factor": float(cf[i]),
                        "lat": LAT + np.random.uniform(-0.1, 0.1),
                        "lon": LON + np.random.uniform(-0.1, 0.1),
                        "source_type": "power_plant",
                    }
                )
        df_list.append(pd.DataFrame(rows))
    else:
        input_path = Path(input_dir)
        csv_files = sorted(input_path.glob("power_*.csv"))
        if not csv_files:
            raise FileNotFoundError(
                f"No power_*.csv files found in {input_dir}. "
                "Expected power_2021.csv through power_2025.csv."
            )
        for fpath in csv_files:
            tmp = pd.read_csv(fpath)
            df_list.append(tmp)
            logger.info("Loaded: %s (%d rows)", fpath.name, len(tmp))

    df_raw = pd.concat(df_list, ignore_index=True)
    df_raw.columns = df_raw.columns.str.strip().str.lower()
    df_raw["start_time"] = pd.to_datetime(df_raw["start_time"], errors="coerce")
    df_raw = df_raw.dropna(subset=["start_time"]).sort_values("start_time")

    # Sector filter: electricity-generation + named plants only
    rows_before = len(df_raw)
    has_sector = "original_inventory_sector" in df_raw.columns
    sector_mask = (
        (df_raw["original_inventory_sector"] == "electricity-generation")
        if has_sector
        else True
    )
    src_mask = df_raw["source_id"].notna() if "source_id" in df_raw.columns else True
    lat_mask = df_raw["lat"].notna() if "lat" in df_raw.columns else True

    df_target = df_raw[
        (df_raw["gas"] == TARGET_GAS) & sector_mask & src_mask & lat_mask
    ].copy()

    logger.info(
        "Sector filter: %d -> %d rows (%d removed)",
        rows_before,
        len(df_target),
        rows_before - len(df_target),
    )

    if len(df_target) == 0:
        raise ValueError(
            "No rows after filter. Check original_inventory_sector values."
        )

    # Aggregate to monthly per source
    agg_dict = {
        "emissions_quantity": "sum",
        "lat": "first",
        "lon": "first",
        "source_type": "first",
    }
    if "capacity_factor" in df_target.columns:
        agg_dict["capacity_factor"] = "mean"

    df_target["month"] = df_target["start_time"].dt.to_period("M").dt.to_timestamp()
    monthly_raw = (
        df_target.groupby(["source_name", "month"]).agg(agg_dict).reset_index()
    )

    # Gap-fill each location's time series
    filled_dfs = []
    global_min = monthly_raw["month"].min()
    global_max = monthly_raw["month"].max()
    complete_idx = pd.date_range(global_min, global_max, freq="MS")

    for src, grp in monthly_raw.groupby("source_name"):
        grp = grp.set_index("month").reindex(complete_idx)
        grp["source_name"] = src
        grp["lat"] = grp["lat"].ffill().bfill()
        grp["lon"] = grp["lon"].ffill().bfill()
        grp["source_type"] = grp["source_type"].ffill().bfill()
        grp["emissions_quantity"] = (
            grp["emissions_quantity"].interpolate("linear").ffill().bfill()
        )
        if "capacity_factor" in grp.columns:
            grp["capacity_factor"] = (
                grp["capacity_factor"].interpolate("linear").ffill().bfill()
            )
        grp.index.name = "month"
        filled_dfs.append(grp.reset_index())

    monthly_all = pd.concat(filled_dfs, ignore_index=True)

    logger.info(
        "Monthly records (gap-filled): %d | Locations: %d | Range: %s -> %s",
        len(monthly_all),
        monthly_all["source_name"].nunique(),
        global_min.strftime("%b %Y"),
        global_max.strftime("%b %Y"),
    )

    # FIX 4: Auto-detect column scale. If mean >> 1, it's MWh activity not 0-1 rate.
    location_cf = {}
    CF_COL_NAME = "capacity_factor"

    if "capacity_factor" in monthly_all.columns:
        sample_mean = monthly_all["capacity_factor"].mean()
        if sample_mean > 5:
            monthly_all = monthly_all.rename(
                columns={"capacity_factor": "activity_mwh"}
            )
            CF_COL_NAME = "activity_mwh"
            CAPACITY_COLS = ["activity_mwh"]
            XGB_FEATURES = WEATHER_COLS + CAPACITY_COLS
            PROPHET_REGS = WEATHER_COLS + CAPACITY_COLS
            N_XGB_FEATS = len(XGB_LAGS) + len(XGB_FEATURES)
            XGB_FEAT_NAMES = [f"lag_{l}" for l in XGB_LAGS] + XGB_FEATURES
            logger.info(
                "[FIX 4] capacity_factor renamed to activity_mwh (mean=%.1f >> 1.0)",
                sample_mean,
            )

    if CF_COL_NAME in monthly_all.columns:
        for src, grp in monthly_all.groupby("source_name"):
            cf_s = pd.Series(
                grp[CF_COL_NAME].values, index=pd.DatetimeIndex(grp["month"])
            )
            location_cf[src] = cf_s

    # =========================================================================
    # SECTION 2 - WEATHER INTEGRATION
    # =========================================================================
    logger.info("[2/8] WEATHER INTEGRATION")

    weather_monthly, WEATHER_SOURCE = fetch_weather(
        global_min, global_max, complete_idx
    )

    # Seasonal climatology for future forecasting (FIX D)
    _lookup_cols = ["temp", "CDD", "HDD", "humidity"]
    _weather_seasonal = weather_monthly[_lookup_cols].groupby(
        weather_monthly.index.month
    ).mean()

    def weather_for_date(dt: pd.Timestamp) -> dict:
        """Actual weather if in history, monthly climatology otherwise."""
        if dt in weather_monthly.index:
            return weather_monthly.loc[dt, _lookup_cols].to_dict()
        return _weather_seasonal.loc[dt.month, _lookup_cols].to_dict()

    def cf_for_date(src: str, dt: pd.Timestamp) -> float:
        """Per-location capacity_factor: actual if known, monthly climatology if future."""
        cf_series = location_cf.get(src)
        if cf_series is None:
            return 0.70
        if dt in cf_series.index:
            return float(cf_series.loc[dt])
        cf_clim = cf_series.groupby(cf_series.index.month).mean()
        return float(cf_clim.get(dt.month, cf_series.mean()))

    # =========================================================================
    # SECTION 3 - ADF STATIONARITY DIAGNOSTIC
    # =========================================================================
    logger.info("[3/8] ADF STATIONARITY DIAGNOSTIC")

    area_total = monthly_all.groupby("month")["emissions_quantity"].sum()
    area_total.index = pd.DatetimeIndex(area_total.index)
    agg_ts = area_total.sort_index()

    for label, series in [
        ("Total area emissions (level)", agg_ts),
        ("First difference", agg_ts.diff().dropna()),
    ]:
        adf_stat, p_val, _, _, crit_vals, _ = adfuller(series, autolag="AIC")
        decision = "STATIONARY" if p_val < 0.05 else "NON-STATIONARY"
        logger.info(
            "%s: ADF=%.4f p=%.4f -> %s", label, adf_stat, p_val, decision
        )

    # =========================================================================
    # MODEL HELPER FUNCTIONS (closures over weather data)
    # =========================================================================

    def build_xgb_features_for_location(ts: pd.Series, src: str) -> pd.DataFrame:
        """Build tabular features for one location's emission series."""
        df = pd.DataFrame({"value": ts.values}, index=ts.index)
        for lag in XGB_LAGS:
            df[f"lag_{lag}"] = df["value"].shift(lag)
        for col in WEATHER_COLS:
            df[col] = weather_monthly[col].reindex(ts.index).values
        df[CAPACITY_COLS[0]] = [cf_for_date(src, d) for d in ts.index]
        return df.dropna()

    def recursive_xgb_forecast(
        model: XGBRegressor,
        last_known_df: pd.DataFrame,
        src: str,
        future_dates: pd.DatetimeIndex,
    ) -> np.ndarray:
        """Recursive one-step-ahead XGBoost forecast."""
        curr_df = last_known_df.copy()
        preds = []
        for nd in future_dates:
            row = {}
            for lag in XGB_LAGS:
                row[f"lag_{lag}"] = curr_df["value"].iloc[-lag]
            w = weather_for_date(nd)
            for col in WEATHER_COLS:
                row[col] = w[col]
            row[CAPACITY_COLS[0]] = cf_for_date(src, nd)
            p = float(model.predict(pd.DataFrame([row]).values)[0])
            preds.append(max(0.0, p))
            new_row = pd.DataFrame({"value": [p], **row}, index=[nd])
            curr_df = pd.concat([curr_df, new_row])
        return np.array(preds)

    def build_prophet_df(ts: pd.Series, src: str) -> pd.DataFrame:
        """Prophet training DataFrame with weather + capacity regressors."""
        df = ts.reset_index()
        df.columns = ["ds", "y"]
        df["ds"] = pd.to_datetime(df["ds"])
        for col in WEATHER_COLS:
            df[col] = weather_monthly[col].reindex(df["ds"]).values
        df[CAPACITY_COLS[0]] = [cf_for_date(src, d) for d in df["ds"]]
        return df

    def add_regressors_to_future(
        future_df: pd.DataFrame, src: str
    ) -> pd.DataFrame:
        """Add weather + capacity to Prophet make_future_dataframe result."""
        fut = future_df.copy()
        for col in WEATHER_COLS:
            fut[col] = [weather_for_date(pd.Timestamp(d))[col] for d in fut["ds"]]
        fut[CAPACITY_COLS[0]] = [
            cf_for_date(src, pd.Timestamp(d)) for d in fut["ds"]
        ]
        return fut

    def fit_prophet(cfg: dict, train_df: pd.DataFrame) -> Prophet:
        """Instantiate, add regressors, and fit Prophet."""
        m = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=False,
            daily_seasonality=False,
            interval_width=0.95,
            **cfg,
        )
        for reg in PROPHET_REGS:
            m.add_regressor(reg)
        m.fit(train_df)
        return m

    def weather_point(dt: pd.Timestamp) -> dict:
        w = weather_for_date(dt)
        return {
            "temp": safe_float(w.get("temp"), 1),
            "cdd": safe_float(w.get("CDD"), 2),
            "hdd": safe_float(w.get("HDD"), 2),
            "humidity": safe_float(w.get("humidity"), 1),
        }

    # =========================================================================
    # SECTION 4 - CHRONOLOGICAL 70/15/15 SPLIT PER LOCATION
    # =========================================================================
    logger.info("[4/8] CHRONOLOGICAL 70/15/15 SPLIT PER LOCATION")

    location_splits = {}
    location_info = {}
    skipped = []

    for src, grp in monthly_all.groupby("source_name"):
        grp = grp.sort_values("month").reset_index(drop=True)
        ts = pd.Series(
            grp["emissions_quantity"].values, index=pd.DatetimeIndex(grp["month"])
        )
        ts.index.freq = "MS"

        if len(ts) < MIN_MONTHS:
            logger.info("SKIP %s - only %d months (need >= %d)", src, len(ts), MIN_MONTHS)
            skipped.append(src)
            continue

        n = len(ts)
        n_test = max(6, int(n * (1 - TRAIN_RATIO - VAL_RATIO)))
        n_val = max(6, int(n * VAL_RATIO))
        n_train = n - n_val - n_test

        train = ts.iloc[:n_train]
        val = ts.iloc[n_train : n_train + n_val]
        test = ts.iloc[n_train + n_val :]
        train_val = pd.concat([train, val])

        xgb_full = build_xgb_features_for_location(ts, src)

        location_splits[src] = dict(
            ts=ts,
            train=train,
            val=val,
            test=test,
            train_val=train_val,
            n=n,
            n_train=n_train,
            n_val=n_val,
            n_test=n_test,
            xgb_full=xgb_full,
        )
        location_info[src] = dict(
            lat=grp["lat"].iloc[0],
            lon=grp["lon"].iloc[0],
            source_type=grp["source_type"].iloc[0],
        )

        logger.info(
            "%s: Train %dm | Val %dm | Test %dm | mean=%.0f t",
            src[:45],
            n_train,
            n_val,
            n_test,
            ts.mean(),
        )

    logger.info("%d locations ready | %d skipped", len(location_splits), len(skipped))

    # =========================================================================
    # SECTION 5 - HYPERPARAMETER TUNING (VAL SET ONLY)
    # =========================================================================
    logger.info("[5/8] HYPERPARAMETER TUNING - XGBoost + Prophet (val set only)")

    tuning = {}

    for src, sp in location_splits.items():
        logger.info("Tuning: %s", src)
        train, val = sp["train"], sp["val"]
        xgb_full = sp["xgb_full"]

        # -- XGBoost tuning --
        train_idx = train.index.intersection(xgb_full.index)
        val_idx = val.index.intersection(xgb_full.index)
        X_tr = xgb_full.loc[train_idx].drop("value", axis=1).values
        y_tr = xgb_full.loc[train_idx]["value"].values
        X_vl = xgb_full.loc[val_idx].drop("value", axis=1).values
        y_vl = xgb_full.loc[val_idx]["value"].values

        best_xgb_score, best_xgb_params, best_xgb_model = float("inf"), {}, None
        for n_est in XGB_GRID["n_estimators"]:
            for depth in XGB_GRID["max_depth"]:
                for lr in XGB_GRID["learning_rate"]:
                    m = XGBRegressor(
                        n_estimators=n_est,
                        max_depth=depth,
                        learning_rate=lr,
                        random_state=RANDOM_STATE,
                        verbosity=0,
                    )
                    m.fit(X_tr, y_tr)
                    s = grid_score(y_vl, m.predict(X_vl))
                    if s < best_xgb_score:
                        best_xgb_score = s
                        best_xgb_params = {
                            "n_estimators": n_est,
                            "max_depth": depth,
                            "learning_rate": lr,
                        }
                        best_xgb_model = m

        # Safety net fallback
        if best_xgb_model is None:
            logger.warning(
                "All XGB configs produced non-finite score for '%s'. Using fallback.", src
            )
            best_xgb_params = {
                "n_estimators": 50,
                "max_depth": 3,
                "learning_rate": 0.1,
            }
            best_xgb_model = XGBRegressor(
                **best_xgb_params, random_state=RANDOM_STATE, verbosity=0
            )
            best_xgb_model.fit(X_tr, y_tr)

        xgb_tr_pred = pd.Series(best_xgb_model.predict(X_tr), index=train_idx)
        xgb_vl_pred = pd.Series(best_xgb_model.predict(X_vl), index=val_idx)
        xgb_tr_m = compute_metrics(y_tr, xgb_tr_pred.values)
        xgb_vl_m = compute_metrics(y_vl, xgb_vl_pred.values)

        # -- Prophet tuning --
        train_prophet_df = build_prophet_df(train, src)
        best_prophet_score, best_prophet_cfg, best_prophet_model = (
            float("inf"),
            {},
            None,
        )
        best_prophet_vl_pred = None

        for cfg in PROPHET_GRID:
            try:
                m = fit_prophet(cfg, train_prophet_df)
                fut = add_regressors_to_future(
                    m.make_future_dataframe(periods=len(val), freq="MS"), src
                )
                fc = m.predict(fut)
                vl_pred = fc.set_index("ds")["yhat"].reindex(val.index).values
                s = grid_score(val.values, vl_pred)
                if s < best_prophet_score:
                    best_prophet_score = s
                    best_prophet_cfg = cfg
                    best_prophet_model = m
                    best_prophet_vl_pred = vl_pred
            except Exception:
                continue

        if best_prophet_model is not None:
            train_fut = add_regressors_to_future(
                best_prophet_model.make_future_dataframe(periods=0, freq="MS"), src
            )
            p_tr_pred = (
                best_prophet_model.predict(train_fut)
                .set_index("ds")["yhat"]
                .reindex(train.index)
                .values
            )
            prophet_tr_m = compute_metrics(train.values, p_tr_pred)
            prophet_vl_m = compute_metrics(val.values, best_prophet_vl_pred)
        else:
            logger.warning("Prophet failed all configs for %s", src)
            prophet_tr_m = {
                "MAPE": np.nan,
                "sMAPE": np.nan,
                "R2": np.nan,
                "RMSE": np.nan,
                "MAE": np.nan,
            }
            prophet_vl_m = prophet_tr_m
            p_tr_pred = np.full(len(train), np.nan)
            best_prophet_vl_pred = np.full(len(val), np.nan)

        tuning[src] = {
            "xgb": {
                "model": best_xgb_model,
                "params": best_xgb_params,
                "train_m": xgb_tr_m,
                "val_m": xgb_vl_m,
                "train_pred": xgb_tr_pred,
                "val_pred": xgb_vl_pred,
                "train_idx": train_idx,
                "val_idx": val_idx,
            },
            "prophet": {
                "model": best_prophet_model,
                "params": best_prophet_cfg,
                "train_m": prophet_tr_m,
                "val_m": prophet_vl_m,
                "train_pred": pd.Series(p_tr_pred, index=train.index),
                "val_pred": pd.Series(best_prophet_vl_pred, index=val.index),
            },
        }

    # =========================================================================
    # SECTION 6 - WALK-FORWARD CV STABILITY AUDIT
    # =========================================================================
    logger.info("[6/8] WALK-FORWARD CV - STABILITY AUDIT")

    cv_results = {}
    tscv = TimeSeriesSplit(n_splits=4, test_size=6)

    for src, sp in location_splits.items():
        train_val = sp["train_val"]
        xgb_full = sp["xgb_full"]
        xgb_params = tuning[src]["xgb"]["params"]
        proph_cfg = tuning[src]["prophet"]["params"]

        xgb_scores, prophet_scores = [], []

        for tr_idx, te_idx in tscv.split(train_val):
            cv_tr, cv_te = train_val.iloc[tr_idx], train_val.iloc[te_idx]

            # XGBoost fold
            # FIX 3: Skip folds with < 15 usable training rows after lag dropping
            try:
                cv_full = build_xgb_features_for_location(cv_tr, src)
                ti = cv_tr.index.intersection(cv_full.index)
                vi = cv_te.index.intersection(cv_full.index)
                if len(ti) < 15:
                    pass  # skip fold
                elif len(ti) > 0 and len(vi) > 0:
                    xm = XGBRegressor(
                        **xgb_params, random_state=RANDOM_STATE, verbosity=0
                    )
                    xm.fit(
                        cv_full.loc[ti].drop("value", axis=1).values,
                        cv_full.loc[ti]["value"].values,
                    )
                    cv_full_te = build_xgb_features_for_location(
                        train_val.iloc[: te_idx[-1] + 1], src
                    )
                    vi2 = cv_te.index.intersection(cv_full_te.index)
                    if len(vi2) > 0:
                        p = xm.predict(
                            cv_full_te.loc[vi2].drop("value", axis=1).values
                        )
                        s = grid_score(cv_te.loc[vi2].values, p)
                        if np.isfinite(s):
                            xgb_scores.append(s)
            except Exception:
                pass

            # Prophet fold
            try:
                if proph_cfg:
                    cv_tr_df = build_prophet_df(cv_tr, src)
                    pm = fit_prophet(proph_cfg, cv_tr_df)
                    fut = add_regressors_to_future(
                        pm.make_future_dataframe(periods=len(cv_te), freq="MS"), src
                    )
                    p_proph = (
                        pm.predict(fut).set_index("ds")["yhat"].reindex(cv_te.index).values
                    )
                    if not np.all(np.isnan(p_proph)):
                        s = grid_score(cv_te.values, p_proph)
                        if np.isfinite(s):
                            prophet_scores.append(s)
            except Exception:
                pass

        def _cv_stats(scores):
            if not scores:
                return {"cv_mape": np.nan, "cv_std": np.nan, "stability": np.nan}
            ms, ss = np.mean(scores), np.std(scores)
            return {"cv_mape": ms, "cv_std": ss, "stability": ms + 2 * ss}

        cv_results[src] = {
            "xgb": _cv_stats(xgb_scores),
            "prophet": _cv_stats(prophet_scores),
        }

        logger.info(
            "%s: XGB CV folds=%d | Prophet CV folds=%d",
            src[:45],
            len(xgb_scores),
            len(prophet_scores),
        )

    # =========================================================================
    # SECTION 7 - RETRAIN ON TRAIN+VAL -> TEST EVALUATION + FORECAST
    # =========================================================================
    logger.info("[7/8] RETRAIN ON TRAIN+VAL - FINAL TEST + 12-MONTH FORECAST")

    retrained = {}
    future_dates = pd.date_range(
        start=global_max + pd.DateOffset(months=1),
        periods=FORECAST_MONTHS,
        freq="MS",
    )

    for src, sp in location_splits.items():
        logger.info("Retraining: %s", src)
        train_val = sp["train_val"]
        test = sp["test"]
        xgb_full = sp["xgb_full"]
        xgb_params = tuning[src]["xgb"]["params"]
        proph_cfg = tuning[src]["prophet"]["params"]
        n_test = sp["n_test"]

        # -- XGBoost retrain --
        tv_xgb = build_xgb_features_for_location(train_val, src)
        tv_idx = train_val.index.intersection(tv_xgb.index)
        te_idx = test.index.intersection(xgb_full.index)

        xgb_rt_model = XGBRegressor(
            **xgb_params, random_state=RANDOM_STATE, verbosity=0
        )
        try:
            xgb_rt_model.fit(
                tv_xgb.loc[tv_idx].drop("value", axis=1).values,
                tv_xgb.loc[tv_idx]["value"].values,
            )
        except Exception as e:
            logger.warning("XGB retrain fit failed for %s: %s", src, e)
            xgb_rt_model = None

        if xgb_rt_model is not None and len(te_idx) > 0:
            xgb_te_pred = pd.Series(
                xgb_rt_model.predict(
                    xgb_full.loc[te_idx].drop("value", axis=1).values
                ),
                index=te_idx,
            )
        else:
            xgb_te_pred = pd.Series(
                np.full(n_test, train_val.mean()), index=test.index
            )

        xgb_te_m = compute_metrics(
            test.loc[xgb_te_pred.index].values, xgb_te_pred.values
        )

        # XGBoost future forecast (recursive)
        if xgb_rt_model is not None:
            xgb_fut_pred = recursive_xgb_forecast(
                xgb_rt_model, tv_xgb, src, future_dates
            )
        else:
            xgb_fut_pred = np.full(FORECAST_MONTHS, train_val.mean())

        # XGBoost feature importance
        xgb_importances = (
            xgb_rt_model.feature_importances_
            if xgb_rt_model is not None
            else np.zeros(N_XGB_FEATS)
        )

        # -- Prophet retrain --
        prophet_te_pred = pd.Series(np.full(n_test, np.nan), index=test.index)
        prophet_fut_pred = np.full(FORECAST_MONTHS, np.nan)
        prophet_fut_lo = np.full(FORECAST_MONTHS, np.nan)
        prophet_fut_hi = np.full(FORECAST_MONTHS, np.nan)
        prophet_te_lo = np.full(n_test, np.nan)
        prophet_te_hi = np.full(n_test, np.nan)
        prophet_rt_model = None
        prophet_te_m = {
            "MAPE": np.nan,
            "sMAPE": np.nan,
            "R2": np.nan,
            "RMSE": np.nan,
            "MAE": np.nan,
        }

        if proph_cfg:
            try:
                tv_proph_df = build_prophet_df(train_val, src)
                prophet_rt_model = fit_prophet(proph_cfg, tv_proph_df)
                fut = add_regressors_to_future(
                    prophet_rt_model.make_future_dataframe(
                        periods=n_test + FORECAST_MONTHS, freq="MS"
                    ),
                    src,
                )
                fc = prophet_rt_model.predict(fut).set_index("ds")
                prophet_te_pred = pd.Series(
                    fc["yhat"].reindex(test.index).values, index=test.index
                )
                prophet_te_lo = fc["yhat_lower"].reindex(test.index).values
                prophet_te_hi = fc["yhat_upper"].reindex(test.index).values
                prophet_fut_pred = fc["yhat"].reindex(future_dates).values
                prophet_fut_lo = fc["yhat_lower"].reindex(future_dates).values
                prophet_fut_hi = fc["yhat_upper"].reindex(future_dates).values
                prophet_te_m = compute_metrics(test.values, prophet_te_pred.values)
            except Exception as e:
                logger.warning("Prophet retrain failed for %s: %s", src, e)

        # Bootstrap CI for XGBoost
        xgb_resid = test.loc[xgb_te_pred.index].values - xgb_te_pred.values
        std_res = (
            xgb_resid.std()
            if len(xgb_resid) > 1
            else xgb_fut_pred.std() * 0.05
        )
        boot = np.random.normal(0, std_res, (500, FORECAST_MONTHS))
        xgb_fut_lo = np.maximum(
            np.percentile(xgb_fut_pred + boot, 2.5, axis=0), 0
        )
        xgb_fut_hi = np.percentile(xgb_fut_pred + boot, 97.5, axis=0)

        # FIX 1: NaN-safe winner assignment
        xgb_valid = np.isfinite(xgb_te_m["MAPE"]) and xgb_te_m["R2"] > 0
        proph_valid = np.isfinite(prophet_te_m["MAPE"]) and prophet_te_m["R2"] > 0

        if xgb_valid and proph_valid:
            winner = (
                "Prophet"
                if prophet_te_m["MAPE"] < xgb_te_m["MAPE"]
                else "XGBoost"
            )
            status = "ok"
        elif proph_valid:
            winner = "Prophet"
            status = "xgb_failed"
        elif xgb_valid:
            winner = "XGBoost"
            status = "prophet_failed"
        else:
            winner = None
            status = "unmodelled"

        retrained[src] = {
            "xgb": {
                "model": xgb_rt_model,
                "test_pred": xgb_te_pred,
                "test_m": xgb_te_m,
                "fut_pred": xgb_fut_pred,
                "fut_lo": xgb_fut_lo,
                "fut_hi": xgb_fut_hi,
                "importances": xgb_importances,
            },
            "prophet": {
                "model": prophet_rt_model,
                "test_pred": prophet_te_pred,
                "test_m": prophet_te_m,
                "test_lo": prophet_te_lo,
                "test_hi": prophet_te_hi,
                "fut_pred": prophet_fut_pred,
                "fut_lo": prophet_fut_lo,
                "fut_hi": prophet_fut_hi,
            },
            "winner": winner,
            "status": status,
        }

        logger.info(
            "%s: XGB MAPE=%.2f%% R2=%.3f | Prophet MAPE=%.2f%% R2=%.3f | Winner=%s (%s)",
            src[:35],
            xgb_te_m["MAPE"] if np.isfinite(xgb_te_m["MAPE"]) else -1,
            xgb_te_m["R2"],
            prophet_te_m["MAPE"] if np.isfinite(prophet_te_m["MAPE"]) else -1,
            prophet_te_m["R2"],
            winner or "NONE",
            status,
        )

    # =========================================================================
    # SECTION 8 - JSON EXPORT
    # =========================================================================
    logger.info("[8/8] JSON EXPORT")

    # Compute aggregate forecasts (FIX 2: only modelled locations)
    agg_xgb_fu = np.zeros(FORECAST_MONTHS)
    agg_proph_fu = np.zeros(FORECAST_MONTHS)
    agg_xgb_lo = np.zeros(FORECAST_MONTHS)
    agg_xgb_hi = np.zeros(FORECAST_MONTHS)
    agg_proph_lo = np.zeros(FORECAST_MONTHS)
    agg_proph_hi = np.zeros(FORECAST_MONTHS)
    modelled_srcs = []
    unmodelled_srcs = []

    for src in location_splits:
        rt = retrained[src]
        if rt["status"] == "unmodelled":
            unmodelled_srcs.append(src)
            continue
        modelled_srcs.append(src)
        agg_xgb_fu += np.nan_to_num(rt["xgb"]["fut_pred"])
        agg_proph_fu += np.nan_to_num(rt["prophet"]["fut_pred"])
        agg_xgb_lo += np.nan_to_num(rt["xgb"]["fut_lo"])
        agg_xgb_hi += np.nan_to_num(rt["xgb"]["fut_hi"])
        agg_proph_lo += np.nan_to_num(rt["prophet"]["fut_lo"])
        agg_proph_hi += np.nan_to_num(rt["prophet"]["fut_hi"])

    if unmodelled_srcs:
        logger.info(
            "Excluded from aggregate (%d unmodelled): %s",
            len(unmodelled_srcs),
            unmodelled_srcs,
        )

    # Build per-location payload
    final_payload = []

    for src in location_splits:
        sp = location_splits[src]
        rt = retrained[src]
        tun = tuning[src]
        cv_ = cv_results[src]
        inf = location_info[src]

        # Historical series
        history = []
        for d, em in zip(sp["ts"].index, sp["ts"].values):
            wp = weather_point(d)
            history.append(
                {
                    "date": d.strftime("%Y-%m-%d"),
                    "month": d.strftime("%B %Y"),
                    "emissions": safe_float(em, 2),
                    "temp": wp["temp"],
                    "cdd": wp["cdd"],
                    "hdd": wp["hdd"],
                    "humidity": wp["humidity"],
                    "capacity_factor": safe_float(cf_for_date(src, d), 3),
                    "type": "historical",
                }
            )

        # Test overlay - both models
        test_overlay = []
        for d, act in zip(sp["test"].index, sp["test"].values):
            wp = weather_point(d)
            xgb_p = safe_float(rt["xgb"]["test_pred"].get(d, np.nan), 2)
            proph_p = safe_float(rt["prophet"]["test_pred"].get(d, np.nan), 2)
            test_overlay.append(
                {
                    "date": d.strftime("%Y-%m-%d"),
                    "month": d.strftime("%B %Y"),
                    "actual": safe_float(act, 2),
                    "xgb_predicted": xgb_p,
                    "prophet_predicted": proph_p,
                    "xgb_residual": safe_float(
                        act - (rt["xgb"]["test_pred"].get(d, np.nan)), 2
                    ),
                    "prophet_residual": safe_float(
                        act - (rt["prophet"]["test_pred"].get(d, np.nan)), 2
                    ),
                    "temp": wp["temp"],
                    "cdd": wp["cdd"],
                    "hdd": wp["hdd"],
                    "humidity": wp["humidity"],
                    "capacity_factor": safe_float(cf_for_date(src, d), 3),
                    "type": "test_overlay",
                }
            )

        # Future forecast - both models per date
        forecast = []
        for i, d in enumerate(future_dates):
            wp = weather_point(d)
            conf = "high" if i < 3 else "medium" if i < 6 else "low"
            forecast.append(
                {
                    "date": d.strftime("%Y-%m-%d"),
                    "month": d.strftime("%B %Y"),
                    "xgb_emissions": safe_float(rt["xgb"]["fut_pred"][i], 2),
                    "xgb_lower_ci": safe_float(rt["xgb"]["fut_lo"][i], 2),
                    "xgb_upper_ci": safe_float(rt["xgb"]["fut_hi"][i], 2),
                    "prophet_emissions": safe_float(
                        rt["prophet"]["fut_pred"][i], 2
                    ),
                    "prophet_lower_ci": safe_float(rt["prophet"]["fut_lo"][i], 2),
                    "prophet_upper_ci": safe_float(rt["prophet"]["fut_hi"][i], 2),
                    "winner_emissions": safe_float(
                        (
                            rt["xgb"]["fut_pred"][i]
                            if rt["winner"] == "XGBoost"
                            else rt["prophet"]["fut_pred"][i]
                        ),
                        2,
                    ),
                    "confidence": conf,
                    "temp": wp["temp"],
                    "cdd": wp["cdd"],
                    "hdd": wp["hdd"],
                    "humidity": wp["humidity"],
                    "capacity_factor_clim": safe_float(cf_for_date(src, d), 3),
                    "type": "forecast",
                }
            )

        # KPI summary
        last_em = float(sp["ts"].iloc[-1])
        is_unmodelled = rt["status"] == "unmodelled"
        winner_fu = (
            rt["xgb"]["fut_pred"]
            if rt["winner"] == "XGBoost"
            else rt["prophet"]["fut_pred"]
            if rt["winner"] == "Prophet"
            else np.full(FORECAST_MONTHS, np.nan)
        )

        loc_obj = {
            "source": src,
            "type": inf["source_type"],
            "coordinates": {
                "lat": safe_float(inf["lat"], 6),
                "lng": safe_float(inf["lon"], 6),
            },
            "winner": rt["winner"],
            "status": rt["status"],
            "in_aggregate": not is_unmodelled,
            "models": {
                "xgboost": {
                    "architecture": "XGBoost (gradient boosting)",
                    "input_features": XGB_FEAT_NAMES,
                    "hyperparameters": tun["xgb"]["params"],
                    "metrics": {
                        "val": {
                            k: safe_float(v)
                            for k, v in tun["xgb"]["val_m"].items()
                        },
                        "test": {
                            k: safe_float(v)
                            for k, v in rt["xgb"]["test_m"].items()
                        },
                    },
                    "cross_validation": {
                        "cv_mape": safe_float(cv_["xgb"]["cv_mape"]),
                        "cv_std": safe_float(cv_["xgb"]["cv_std"]),
                        "stability": safe_float(cv_["xgb"]["stability"]),
                    },
                    "feature_importance": {
                        name: safe_float(imp, 4)
                        for name, imp in zip(
                            XGB_FEAT_NAMES, rt["xgb"]["importances"]
                        )
                    },
                },
                "prophet": {
                    "architecture": "Facebook Prophet",
                    "regressors": PROPHET_REGS,
                    "hyperparameters": tun["prophet"]["params"],
                    "metrics": {
                        "val": {
                            k: safe_float(v)
                            for k, v in tun["prophet"]["val_m"].items()
                        },
                        "test": {
                            k: safe_float(v)
                            for k, v in rt["prophet"]["test_m"].items()
                        },
                    },
                    "cross_validation": {
                        "cv_mape": safe_float(cv_["prophet"]["cv_mape"]),
                        "cv_std": safe_float(cv_["prophet"]["cv_std"]),
                        "stability": safe_float(cv_["prophet"]["stability"]),
                    },
                },
            },
            "summary": {
                "last_historical_date": sp["ts"].index[-1].strftime("%B %Y"),
                "last_historical_emissions": safe_float(last_em, 2),
                "xgb_forecast_12m_total": (
                    None
                    if is_unmodelled
                    else safe_float(float(np.nansum(rt["xgb"]["fut_pred"])), 2)
                ),
                "prophet_forecast_12m_total": (
                    None
                    if is_unmodelled
                    else safe_float(
                        float(np.nansum(rt["prophet"]["fut_pred"])), 2
                    )
                ),
                "winner_forecast_12m_total": (
                    None
                    if is_unmodelled
                    else safe_float(float(np.nansum(winner_fu)), 2)
                ),
                "winner_change_pct": (
                    None
                    if is_unmodelled
                    else safe_float(
                        (float(winner_fu[-1]) - last_em) / last_em * 100
                        if last_em
                        else None,
                        2,
                    )
                ),
                "trend": (
                    "unknown"
                    if is_unmodelled
                    else (
                        "declining"
                        if float(winner_fu[-1]) < last_em
                        else "increasing"
                    )
                ),
                "total_historical_tonnes": safe_float(float(sp["ts"].sum()), 2),
            },
            "chart_data": {
                "historical": history,
                "test_overlay": test_overlay,
                "forecast": forecast,
                "combined_xgb": history
                + [
                    {
                        "date": r["date"],
                        "month": r["month"],
                        "emissions": r["xgb_emissions"],
                        "type": "forecast",
                    }
                    for r in forecast
                ],
                "combined_prophet": history
                + [
                    {
                        "date": r["date"],
                        "month": r["month"],
                        "emissions": r["prophet_emissions"],
                        "type": "forecast",
                    }
                    for r in forecast
                ],
            },
            "table_data": forecast,
        }
        final_payload.append(loc_obj)

    # Sort by total historical emissions (highest emitters first)
    final_payload.sort(
        key=lambda x: x["summary"]["total_historical_tonnes"] or 0, reverse=True
    )

    # Top-level aggregate (FIX 2: only modelled locations)
    agg_output = {
        "dates": [d.strftime("%Y-%m-%d") for d in future_dates],
        "xgb_values": [safe_float(v, 2) for v in agg_xgb_fu],
        "xgb_lower": [safe_float(v, 2) for v in agg_xgb_lo],
        "xgb_upper": [safe_float(v, 2) for v in agg_xgb_hi],
        "prophet_values": [safe_float(v, 2) for v in agg_proph_fu],
        "prophet_lower": [safe_float(v, 2) for v in agg_proph_lo],
        "prophet_upper": [safe_float(v, 2) for v in agg_proph_hi],
        "weather": [weather_point(d) for d in future_dates],
        "modelled_locations": modelled_srcs,
        "excluded_unmodelled": unmodelled_srcs,
        "note": (
            f"Aggregate covers {len(modelled_srcs)} modelled locations. "
            f"{len(unmodelled_srcs)} location(s) excluded: {unmodelled_srcs}"
        ),
    }

    api_output = {
        "metadata": {
            "pipeline": "CarbonSense Per-Location XGBoost + Prophet v2.1",
            "generated_at": pd.Timestamp.now().isoformat(),
            "data_source": "Climate Trace",
            "sector": "power",
            "region": "Lahore Division, Punjab, Pakistan",
            "historical_period": (
                f"{global_min.strftime('%Y-%m')} to {global_max.strftime('%Y-%m')}"
            ),
            "forecast_horizon_months": FORECAST_MONTHS,
            "forecast_window": (
                f"{future_dates[0].strftime('%Y-%m')} to "
                f"{future_dates[-1].strftime('%Y-%m')}"
            ),
            "models": ["XGBoost", "Prophet"],
            "xgb_features": XGB_FEAT_NAMES,
            "prophet_regressors": PROPHET_REGS,
            "weather_source": WEATHER_SOURCE,
            "confidence_intervals": (
                "Prophet: Bayesian 95% | XGBoost: Residual bootstrap 95% (500)"
            ),
        },
        "aggregate_forecast": agg_output,
        "locations": final_payload,
    }

    json_path = os.path.join(output_dir, "carbonsense_power_forecast.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(api_output, f, indent=2, ensure_ascii=False)

    logger.info(
        "Wrote %s (%d locations, %d modelled, %d unmodelled)",
        json_path,
        len(final_payload),
        len(modelled_srcs),
        len(unmodelled_srcs),
    )

    # Summary
    total_xgb_wins = sum(
        1 for s in location_splits if retrained[s]["winner"] == "XGBoost"
    )
    total_proph_wins = sum(
        1 for s in location_splits if retrained[s]["winner"] == "Prophet"
    )
    logger.info(
        "COMPLETE: %d locations | XGBoost wins: %d | Prophet wins: %d | "
        "Unmodelled: %d | Skipped: %d",
        len(location_splits),
        total_xgb_wins,
        total_proph_wins,
        len(unmodelled_srcs),
        len(skipped),
    )

    return api_output


# =============================================================================
# CLI ENTRY POINT
# =============================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="CarbonSense Power Sector Emissions Forecasting Pipeline v2.1"
    )
    parser.add_argument(
        "--input-dir",
        required=True,
        help="Directory containing power_2021.csv through power_2025.csv",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory where output JSON will be written",
    )
    parser.add_argument(
        "--use-synthetic",
        action="store_true",
        default=False,
        help="Use synthetic demo data instead of CSV files",
    )
    args = parser.parse_args()
    main(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        use_synthetic=args.use_synthetic,
    )
