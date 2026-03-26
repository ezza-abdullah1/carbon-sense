"""
Generic loader: insert any CarbonSense forecast JSON into Supabase.

Usage:
    python load_supabase.py data/power_new.json
    python load_supabase.py data/transport.json
    python load_supabase.py data/waste.json
    python load_supabase.py data/transport_new.json

- Deletes any existing forecast_run for the same sector+region (cascade)
- Inserts forecast_run, aggregate points, locations, model info, summaries, emission points
- Marks the new run as active
- Handles v1 (LSTM), v2 (XGBoost+Prophet), v3 (waste), and v5 (transport_new) JSON formats

NOTE: Before loading transport_new.json for the first time, run in Supabase SQL editor:
    ALTER TABLE location_summaries ADD COLUMN IF NOT EXISTS sub_sector_data jsonb;
    ALTER TABLE locations ADD COLUMN IF NOT EXISTS uc_code text;
"""

import json
import os
import sys
from datetime import datetime
from dateutil.relativedelta import relativedelta
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("SUPABASE_DB_URL")


def load_json(filepath):
    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


def normalize_transport_new_format(data):
    """
    Normalize transport_new.json (v1.5 format with uc_emissions + division_total)
    into the standard format expected by the rest of the loader.
    """
    meta = data["metadata"]
    div_total = data["division_total"]
    uc_list = data["uc_emissions"]
    dates = div_total["dates"]  # 12 forecast date strings

    # --- Normalize metadata ---
    forecast_period = meta.get("forecast_period", "")
    fp_parts = [p.strip() for p in forecast_period.split(" to ")] if forecast_period else []
    if len(fp_parts) == 2:
        fc_start = datetime.strptime(fp_parts[0], "%Y-%m")
        hist_end = fc_start - relativedelta(months=1)
        retrain_months = meta.get("retrain_basis_months", 60)
        hist_start = hist_end - relativedelta(months=retrain_months - 1)
        meta["forecast_window"] = forecast_period
        meta["historical_period"] = (
            f"{hist_start.strftime('%Y-%m')} to {hist_end.strftime('%Y-%m')}"
        )
        meta["forecast_horizon_months"] = 12

    meta.setdefault("region", meta.get("location", "Lahore District"))
    meta.setdefault(
        "model_architecture",
        meta.get("champion_model") or meta.get("production_model", "Prophet"),
    )

    # --- Normalize aggregate: division_total → aggregate_forecast ---
    agg = {
        "dates": dates,
        "values": div_total["total_t"],
        "lower": div_total.get("ci_lower_t", []),
        "upper": div_total.get("ci_upper_t", []),
        "weather": [{} for _ in dates],
    }

    # CI scale for road (dominant sub-sector) used to derive per-UC monthly CI
    road_ci = meta.get("sub_sector_ci_scales", {}).get("road", 0.04)

    # --- Normalize each UC → location ---
    locations = []
    yoy_pct = meta.get("yoy_pct", 0)
    trend = "increasing" if yoy_pct > 0 else ("declining" if yoy_pct < 0 else "stable")

    for uc in uc_list:
        monthly_t = uc["monthly_t"]  # 12 forecast values aligned with dates
        annual_t = uc.get("annual_t", sum(monthly_t))

        forecast_pts = []
        for i, date in enumerate(dates):
            val = monthly_t[i]
            forecast_pts.append({
                "date": date,
                "month": datetime.strptime(date, "%Y-%m-%d").strftime("%b %Y"),
                "emissions": val,
                "lower_bound": round(val * (1 - road_ci), 2),
                "upper_bound": round(val * (1 + road_ci), 2),
            })

        loc = {
            "source": uc["uc_name"],
            "uc_code": uc.get("uc_code", ""),
            "type": "union_council",
            "coordinates": {
                "lat": uc["centroid_lat"],
                "lng": uc["centroid_lon"],
            },
            "chart_data": {
                "historical": [],
                "forecast": forecast_pts,
            },
            "summary": {
                "last_historical_date": "",
                "last_historical_emissions": 0,
                "forecast_12m_last": monthly_t[-1],
                "forecast_12m_average": round(annual_t / 12, 2),
                "forecast_12m_total": annual_t,
                "change_pct": yoy_pct,
                "change_tonnes": 0,
                "trend": trend,
                "total_historical_tonnes": 0,
            },
            "sub_sector_data": {
                "road": uc.get("road_annual_t", 0),
                "dom_avi": uc.get("dom_avi_annual_t", 0),
                "intl_avi": uc.get("intl_avi_annual_t", 0),
                "railways": uc.get("rail_annual_t", 0),
                "road_pct": uc.get("road_pct", 0),
                "intensity_t_per_km2": uc.get("intensity_t_per_km2", 0),
                "dominant_source": uc.get("dominant_source", "road"),
                "risk_flags": uc.get("risk_flags", []),
                "rank_in_division": uc.get("rank_in_division"),
            },
        }
        locations.append(loc)

    return {
        "metadata": meta,
        "aggregate_forecast": agg,
        "locations": locations,
    }


def insert_forecast_run(cur, meta):
    """Insert forecast_run row, return its id."""
    hist_parts = meta["historical_period"].split(" to ")
    hist_start = hist_parts[0] + "-01"
    hist_end = hist_parts[1] + "-01"

    # forecast_window may not exist — derive from historical_end + horizon
    if "forecast_window" in meta:
        fc_parts = meta["forecast_window"].split(" to ")
        fc_start = fc_parts[0] + "-01"
        fc_end = fc_parts[1] + "-01"
    else:
        h_end = datetime.strptime(hist_end, "%Y-%m-%d")
        fc_s = h_end + relativedelta(months=1)
        fc_e = fc_s + relativedelta(months=meta.get("forecast_horizon_months", 12) - 1)
        fc_start = fc_s.strftime("%Y-%m-%d")
        fc_end = fc_e.strftime("%Y-%m-%d")

    # Handle all metadata field variations
    model_arch = (
        meta.get("model_architecture")
        or ", ".join(meta.get("models", meta.get("models_used", [])))
    )
    input_features = (
        meta.get("lstm_input_features")
        or meta.get("xgb_features")
        or meta.get("prophet_regressors")
        or []
    )
    weather_fields = (
        meta.get("json_weather_fields")
        or meta.get("prophet_regressors")
        or []
    )
    design_notes = meta.get("design_notes") or meta.get("upgrades_v4_3") or meta.get("v2_1_fixes")
    pipeline = meta.get("pipeline") or f"CarbonSense {meta['sector']} forecast"

    cur.execute("""
        INSERT INTO forecast_runs (
            pipeline, generated_at, data_source, sector, region,
            historical_start, historical_end,
            forecast_horizon_months, forecast_start, forecast_end,
            model_architecture, lstm_input_features, json_weather_fields,
            weather_source, confidence_intervals, design_notes,
            is_active
        ) VALUES (
            %s, %s, %s, %s, %s,
            %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            TRUE
        ) RETURNING id
    """, (
        pipeline, meta["generated_at"], meta.get("data_source", ""),
        meta["sector"], meta.get("region", ""),
        hist_start, hist_end,
        meta.get("forecast_horizon_months", 12), fc_start, fc_end,
        model_arch,
        json.dumps(input_features),
        json.dumps(weather_fields),
        meta.get("weather_source", ""),
        meta.get("confidence_intervals", ""),
        json.dumps(design_notes),
    ))
    return cur.fetchone()[0]


def insert_aggregate_points(cur, run_id, agg):
    """Insert aggregate forecast points. Handles v1 (values/lower/upper) and v2 (xgb_values/prophet_values)."""
    rows = []
    dates = agg["dates"]

    # v2 format: use xgb_values as primary, fall back to v1 "values"
    values = agg.get("xgb_values") or agg.get("values", [])
    lower = agg.get("xgb_lower") or agg.get("lower", [])
    upper = agg.get("xgb_upper") or agg.get("upper", [])

    for i, date in enumerate(dates):
        w = agg["weather"][i] if i < len(agg.get("weather", [])) else {}
        rows.append((
            run_id, date,
            values[i] if i < len(values) else 0,
            lower[i] if i < len(lower) else 0,
            upper[i] if i < len(upper) else 0,
            w.get("temp"), w.get("cdd"), w.get("humidity"),
        ))

    execute_values(cur, """
        INSERT INTO aggregate_forecast_points
            (forecast_run_id, date, value, lower_bound, upper_bound,
             temperature, cdd, humidity)
        VALUES %s
    """, rows)
    return len(rows)


def insert_location(cur, run_id, loc):
    """Insert a location row, return its id."""
    coords = loc.get("coordinates") or {}
    source = loc.get("source") or loc.get("source_name") or "unknown"
    lat = coords.get("lat") or loc.get("lat") or 0.0
    lng = coords.get("lng") or loc.get("lon") or loc.get("lng") or 0.0
    loc_type = loc.get("type") or loc.get("source_type") or "other"
    uc_code = loc.get("uc_code") or None

    if uc_code is not None:
        cur.execute("""
            INSERT INTO locations (forecast_run_id, source, type, latitude, longitude, uc_code)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (run_id, source, loc_type, lat, lng, uc_code))
    else:
        cur.execute("""
            INSERT INTO locations (forecast_run_id, source, type, latitude, longitude)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (run_id, source, loc_type, lat, lng))
    return cur.fetchone()[0]


def insert_model_info(cur, location_id, loc):
    """Insert model info. Handles all JSON format variations."""
    # v2 format: loc["models"] with xgboost/prophet sub-dicts
    if "models" in loc and isinstance(loc["models"], dict):
        winner = loc.get("winner", "xgboost")
        mi = loc["models"].get(winner) or loc["models"].get("xgboost") or loc["models"].get("prophet") or {}
    # v3/waste format: loc["model_info"] with selected_model + all_models_tested
    elif "model_info" in loc:
        mi_raw = loc["model_info"]
        if "all_models_tested" in mi_raw:
            # Flatten: pick the selected model's metrics
            selected = mi_raw.get("selected_model", "")
            tested = mi_raw.get("all_models_tested", {})
            best = tested.get(selected) or next(iter(tested.values()), {})
            mi = {
                "architecture": selected,
                "metrics": {"test": {
                    "MAE": best.get("mae") or best.get("MAE"),
                    "RMSE": best.get("rmse") or best.get("RMSE"),
                    "MAPE": best.get("mape") or best.get("MAPE"),
                    "R2": best.get("r2") or best.get("R2"),
                }},
            }
        else:
            mi = mi_raw
    else:
        return

    hp = mi.get("hyperparameters", {})
    metrics = mi.get("metrics", {})
    cv = mi.get("cross_validation", {})
    train = metrics.get("train", {})
    val = metrics.get("val", {})
    test = metrics.get("test", {})

    input_features = mi.get("input_features") or mi.get("regressors") or []
    json_weather = mi.get("json_weather") or mi.get("regressors") or []

    cur.execute("""
        INSERT INTO location_model_info (
            location_id, architecture, input_features, json_weather,
            units, dropout, look_back, batch_size,
            train_mae, train_rmse, train_mape, train_r2,
            val_mae, val_rmse, val_mape, val_r2,
            test_mae, test_rmse, test_mape, test_r2,
            cv_mape, cv_std, stability_score
        ) VALUES (
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s
        )
    """, (
        location_id, mi.get("architecture", "unknown"),
        json.dumps(input_features),
        json.dumps(json_weather),
        hp.get("units") or hp.get("n_estimators"),
        hp.get("dropout") or hp.get("learning_rate"),
        hp.get("look_back") or hp.get("max_depth"),
        hp.get("batch_size"),
        train.get("MAE"), train.get("RMSE"), train.get("MAPE"), train.get("R2"),
        val.get("MAE"), val.get("RMSE"), val.get("MAPE"), val.get("R2"),
        test.get("MAE"), test.get("RMSE"), test.get("MAPE"), test.get("R2"),
        cv.get("cv_mape"), cv.get("cv_std"),
        cv.get("stability_score") or cv.get("stability"),
    ))


def insert_summary(cur, location_id, loc):
    """Insert location summary. Handles all format variations."""
    s = loc.get("summary", {})
    if not s:
        return

    last_date = s.get("last_historical_date") or s.get("current_date") or ""
    last_emissions = s.get("last_historical_emissions") or s.get("current_emissions_tonnes") or 0
    fc_last = s.get("forecast_12m_last") or s.get("forecast_12month_tonnes") or 0
    fc_avg = s.get("forecast_12m_average") or s.get("forecast_average_tonnes") or 0
    fc_total = (
        s.get("forecast_12m_total")
        or s.get("winner_forecast_12m_total")
        or s.get("xgb_forecast_12m_total")
        or 0
    )
    change_pct = s.get("change_pct") or s.get("winner_change_pct") or s.get("change_percent") or 0
    change_tonnes = s.get("change_tonnes") or 0
    trend = s.get("trend", "stable")
    if trend not in ("increasing", "declining", "stable"):
        trend = "stable"
    total_hist = s.get("total_historical_tonnes") or s.get("total_historical_emissions") or 0

    sub_sector_data = loc.get("sub_sector_data")
    sub_sector_json = json.dumps(sub_sector_data) if sub_sector_data else None

    if sub_sector_json is not None:
        cur.execute("""
            INSERT INTO location_summaries (
                location_id, last_historical_date, last_historical_emissions,
                forecast_12m_last, forecast_12m_average, forecast_12m_total,
                change_pct, change_tonnes, trend, total_historical_tonnes,
                sub_sector_data
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            location_id, last_date, last_emissions,
            fc_last, fc_avg, fc_total,
            change_pct, change_tonnes, trend, total_hist,
            sub_sector_json,
        ))
    else:
        cur.execute("""
            INSERT INTO location_summaries (
                location_id, last_historical_date, last_historical_emissions,
                forecast_12m_last, forecast_12m_average, forecast_12m_total,
                change_pct, change_tonnes, trend, total_historical_tonnes
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            location_id, last_date, last_emissions,
            fc_last, fc_avg, fc_total,
            change_pct, change_tonnes, trend, total_hist,
        ))


def insert_emission_points(cur, location_id, loc):
    """Insert emission points (historical + forecast + test). Handles v1 and v2."""
    rows = []
    chart = loc.get("chart_data", {})
    if not chart:
        return 0

    # Historical points
    for pt in chart.get("historical", []):
        emissions = pt.get("emissions") or pt.get("value") or 0
        rows.append((
            location_id, pt["date"], pt.get("month", ""), emissions,
            "historical",
            pt.get("temp"), pt.get("cdd"), pt.get("humidity"),
            None, None, None,
            None, None, None,
        ))

    # Forecast points
    for pt in chart.get("forecast", []):
        emissions = (
            pt.get("emissions")
            or pt.get("value")
            or pt.get("winner_emissions")
            or pt.get("xgb_emissions")
            or pt.get("prophet_emissions")
            or 0
        )
        lower_ci = pt.get("lower_ci") or pt.get("xgb_lower_ci") or pt.get("prophet_lower_ci") or pt.get("lower_bound")
        upper_ci = pt.get("upper_ci") or pt.get("xgb_upper_ci") or pt.get("prophet_upper_ci") or pt.get("upper_bound")

        rows.append((
            location_id, pt["date"], pt.get("month", ""), emissions,
            "forecast",
            pt.get("temp"), pt.get("cdd"), pt.get("humidity"),
            lower_ci, upper_ci, pt.get("confidence"),
            None, None, None,
        ))

    # Test predictions: v1=test_predictions, v2=test_overlay
    test_pts = chart.get("test_predictions", []) or chart.get("test_overlay", [])
    for pt in test_pts:
        predicted = pt.get("predicted") or pt.get("xgb_predicted") or pt.get("prophet_predicted") or 0
        actual = pt.get("actual") or 0
        residual = pt.get("residual") or pt.get("xgb_residual") or pt.get("prophet_residual")
        emissions = pt.get("emissions") or pt.get("value") or predicted

        rows.append((
            location_id, pt["date"], pt.get("month", ""), emissions,
            "test_prediction",
            pt.get("temp"), pt.get("cdd"), pt.get("humidity"),
            None, None, None,
            actual, predicted, residual,
        ))

    if rows:
        execute_values(cur, """
            INSERT INTO emission_points
                (location_id, date, month_label, emissions, point_type,
                 temperature, cdd, humidity,
                 lower_ci, upper_ci, confidence,
                 actual, predicted, residual)
            VALUES %s
        """, rows)

    return len(rows)


def main():
    if len(sys.argv) < 2:
        print("Usage: python load_supabase.py <json_file>")
        print("  e.g: python load_supabase.py data/power_new.json")
        sys.exit(1)

    filepath = sys.argv[1]
    if not os.path.exists(filepath):
        print(f"[ERROR] File not found: {filepath}")
        sys.exit(1)

    data = load_json(filepath)

    # Detect and normalize transport_new format (v1.5: uc_emissions + division_total)
    if "uc_emissions" in data:
        print(f"[FORMAT] Detected transport_new (v1.5) format — normalizing...")
        data = normalize_transport_new_format(data)

    meta = data["metadata"]
    agg = data.get("aggregate_forecast")
    locations = data["locations"]

    print(f"Loading: {filepath}")
    print(f"  Sector: {meta['sector']}")
    print(f"  Region: {meta.get('region', meta.get('location', ''))}")
    print(f"  Locations: {len(locations)}")
    print()

    conn = psycopg2.connect(DB_URL, sslmode="require")
    cur = conn.cursor()

    try:
        # Delete previous runs for same sector+region
        cur.execute(
            "DELETE FROM forecast_runs WHERE sector = %s AND region = %s",
            (meta["sector"], meta["region"]),
        )
        if cur.rowcount:
            print(f"[CLEANUP] Deleted {cur.rowcount} previous run(s) for {meta['sector']}/{meta['region']}")

        # Insert forecast run
        run_id = insert_forecast_run(cur, meta)
        print(f"[OK] forecast_run inserted (id={run_id})")

        # Insert aggregate points (optional — some sectors don't have them)
        agg_count = 0
        if agg:
            agg_count = insert_aggregate_points(cur, run_id, agg)
            print(f"[OK] {agg_count} aggregate_forecast_points inserted")
        else:
            print("[SKIP] No aggregate_forecast in JSON")

        # Insert locations + related data
        total_ep = 0
        for loc in locations:
            loc_id = insert_location(cur, run_id, loc)
            insert_model_info(cur, loc_id, loc)
            insert_summary(cur, loc_id, loc)
            ep_count = insert_emission_points(cur, loc_id, loc)
            total_ep += ep_count
            status = loc.get("status", "ok")
            name = loc.get("source") or loc.get("source_name") or "unknown"
            print(f"  [OK] {name} ({status}): {ep_count} emission_points")

        conn.commit()
        print(f"\n=== DONE ===")
        print(f"  forecast_run:  {run_id}")
        print(f"  aggregate:     {agg_count} points")
        print(f"  locations:     {len(locations)}")
        print(f"  emission_pts:  {total_ep}")

    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] {e}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
