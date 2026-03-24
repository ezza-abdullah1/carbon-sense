"""
Load carbonsense_per_location_v1.json into Supabase PostgreSQL database.
Maps JSON structure to the CarbonSense Forecast Database Schema.
"""

import json
import os
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("SUPABASE_DB_URL")


def main():
    with open("data/carbonsense_per_location_v1.json", encoding="utf-8") as f:
        data = json.load(f)

    meta = data["metadata"]
    agg = data["aggregate_forecast"]
    locations = data["locations"]

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    try:
        # ── 0. Clean up any previous partial runs ───────────────────
        cur.execute("DELETE FROM forecast_runs WHERE pipeline = %s AND sector = %s AND region = %s", (
            meta["pipeline"], meta["sector"], meta["region"],
        ))
        if cur.rowcount:
            print(f"[CLEANUP] Deleted {cur.rowcount} previous run(s) (cascade cleans related rows)")

        # ── 1. Insert forecast_run ──────────────────────────────────
        hist_start = meta["historical_period"].split(" to ")[0] + "-01"
        hist_end = meta["historical_period"].split(" to ")[1] + "-01"
        fc_start = meta["forecast_window"].split(" to ")[0] + "-01"
        fc_end = meta["forecast_window"].split(" to ")[1] + "-01"

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
            meta["pipeline"], meta["generated_at"], meta["data_source"],
            meta["sector"], meta["region"],
            hist_start, hist_end,
            meta["forecast_horizon_months"], fc_start, fc_end,
            meta["model_architecture"],
            json.dumps(meta["lstm_input_features"]),
            json.dumps(meta["json_weather_fields"]),
            meta["weather_source"], meta["confidence_intervals"],
            json.dumps(meta.get("design_notes")),
        ))
        forecast_run_id = cur.fetchone()[0]
        print(f"[OK] forecast_run inserted (id={forecast_run_id})")

        # ── 2. Insert aggregate_forecast_points ─────────────────────
        agg_rows = []
        for i, date in enumerate(agg["dates"]):
            w = agg["weather"][i] if i < len(agg.get("weather", [])) else {}
            agg_rows.append((
                forecast_run_id, date,
                agg["values"][i], agg["lower"][i], agg["upper"][i],
                w.get("temp"), w.get("cdd"), w.get("humidity"),
            ))

        execute_values(cur, """
            INSERT INTO aggregate_forecast_points
                (forecast_run_id, date, value, lower_bound, upper_bound,
                 temperature, cdd, humidity)
            VALUES %s
        """, agg_rows)
        print(f"[OK] {len(agg_rows)} aggregate_forecast_points inserted")

        # ── 3. Insert locations + related tables ────────────────────
        total_emissions = 0

        for loc in locations:
            coords = loc.get("coordinates") or {}
            cur.execute("""
                INSERT INTO locations (forecast_run_id, source, type, latitude, longitude)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (
                forecast_run_id, loc["source"],
                loc.get("type") or "other",
                coords.get("lat") or 0.0,
                coords.get("lng") or 0.0,
            ))
            location_id = cur.fetchone()[0]

            # ── 3a. location_model_info ─────────────────────────────
            mi = loc["model_info"]
            hp = mi.get("hyperparameters", {})
            metrics = mi.get("metrics", {})
            cv = mi.get("cross_validation", {})
            train = metrics.get("train", {})
            val = metrics.get("val", {})
            test = metrics.get("test", {})

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
                location_id, mi["architecture"],
                json.dumps(mi["input_features"]),
                json.dumps(mi["json_weather"]),
                hp.get("units"), hp.get("dropout"),
                hp.get("look_back"), hp.get("batch_size"),
                train.get("MAE"), train.get("RMSE"),
                train.get("MAPE"), train.get("R2"),
                val.get("MAE"), val.get("RMSE"),
                val.get("MAPE"), val.get("R2"),
                test.get("MAE"), test.get("RMSE"),
                test.get("MAPE"), test.get("R2"),
                cv.get("cv_mape"), cv.get("cv_std"),
                cv.get("stability_score"),
            ))

            # ── 3b. location_summaries ──────────────────────────────
            s = loc["summary"]
            cur.execute("""
                INSERT INTO location_summaries (
                    location_id, last_historical_date, last_historical_emissions,
                    forecast_12m_last, forecast_12m_average, forecast_12m_total,
                    change_pct, change_tonnes, trend, total_historical_tonnes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                location_id, s["last_historical_date"],
                s.get("last_historical_emissions") or 0,
                s.get("forecast_12m_last") or 0, s.get("forecast_12m_average") or 0,
                s.get("forecast_12m_total") or 0,
                s.get("change_pct") or 0, s.get("change_tonnes") or 0,
                s.get("trend") or "stable", s.get("total_historical_tonnes") or 0,
            ))

            # ── 3c. emission_points (historical + forecast) ────────
            ep_rows = []
            chart = loc["chart_data"]

            for pt in chart.get("historical", []):
                ep_rows.append((
                    location_id, pt["date"], pt["month"], pt["emissions"],
                    "historical",
                    pt.get("temp"), pt.get("cdd"), pt.get("humidity"),
                    None, None, None,  # lower_ci, upper_ci, confidence
                    None, None, None,  # actual, predicted, residual
                ))

            for pt in chart.get("forecast", []):
                ep_rows.append((
                    location_id, pt["date"], pt["month"], pt["emissions"],
                    "forecast",
                    pt.get("temp"), pt.get("cdd"), pt.get("humidity"),
                    pt.get("lower_ci"), pt.get("upper_ci"), pt.get("confidence"),
                    None, None, None,
                ))

            for pt in chart.get("test_predictions", []):
                ep_rows.append((
                    location_id, pt["date"], pt["month"],
                    pt.get("emissions", pt.get("predicted", 0)),
                    "test_prediction",
                    pt.get("temp"), pt.get("cdd"), pt.get("humidity"),
                    None, None, None,
                    pt.get("actual"), pt.get("predicted"), pt.get("residual"),
                ))

            execute_values(cur, """
                INSERT INTO emission_points
                    (location_id, date, month_label, emissions, point_type,
                     temperature, cdd, humidity,
                     lower_ci, upper_ci, confidence,
                     actual, predicted, residual)
                VALUES %s
            """, ep_rows)

            total_emissions += len(ep_rows)
            print(f"  [OK] {loc['source']}: location + model_info + summary + {len(ep_rows)} emission_points")

        conn.commit()
        print(f"\n=== DONE ===")
        print(f"  forecast_run:  1")
        print(f"  aggregate:     {len(agg_rows)} points")
        print(f"  locations:     {len(locations)}")
        print(f"  emission_pts:  {total_emissions}")

    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] {e}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
