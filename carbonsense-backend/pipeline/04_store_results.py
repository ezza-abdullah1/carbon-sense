"""
Step 4: Store model results in Supabase.

Calls load_supabase.py once per sector with the model output JSON.

Output filenames produced by each model script:
  power     → data/outputs/carbonsense_power_forecast.json
  waste     → data/outputs/waste_new.json
  transport → data/outputs/carbonsense_transport_v15.json

load_supabase.py handles:
  - Deleting the existing forecast_run for that sector (cascade)
  - Inserting forecast_run, aggregate_forecast_points, locations,
    location_model_info, location_summaries, emission_points
  - Setting is_active=True on the new run

DB tables written:
  forecast_runs, aggregate_forecast_points, locations,
  location_model_info, location_summaries, emission_points
"""

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger("carbonsense-pipeline")

# Exact filenames each model script writes to output_dir
# First match wins
OUTPUT_FILE_MAP = {
    "power": [
        "carbonsense_power_forecast.json",  # what power_model.py writes
        "power_new.json",                   # fallback (manually placed)
    ],
    "waste": [
        "waste_new.json",                   # what waste_model.py writes
        "carbonsense_per_location_waste_v2_3.json",
    ],
    "transport": [
        "carbonsense_transport_v15.json",   # what transport_model.py writes
        "transport_new.json",               # fallback
    ],
}

# What load_supabase.py expects the sector field in JSON metadata to be
# (used in its DELETE + INSERT logic). These must match the `sector` key
# in the model output JSON metadata.
EXPECTED_SECTORS = {
    "power": "power",
    "waste": "waste",
    "transport": "transport",
}


def find_output_json(output_dir: str, sector: str) -> str:
    """Find the model output JSON for a sector. Returns path or None."""
    for filename in OUTPUT_FILE_MAP.get(sector, []):
        path = os.path.join(output_dir, filename)
        if os.path.exists(path):
            return path
    return None


def validate_json_sector(json_path: str, expected_sector: str) -> bool:
    """
    Quick sanity check: make sure the JSON has the right sector field
    so we don't accidentally load power data into the waste slot.
    """
    import json
    try:
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        actual = (
            data.get("metadata", {}).get("sector", "")
            or data.get("sector", "")
        )
        if actual and actual.lower() != expected_sector.lower():
            logger.error(
                f"  Sector mismatch in {json_path}: "
                f"expected '{expected_sector}', got '{actual}'"
            )
            return False
        return True
    except Exception as e:
        logger.error(f"  Failed to read {json_path}: {e}")
        return False


def store_results(output_dir: str, sectors: list = None) -> dict:
    """
    Load model output JSONs into Supabase using load_supabase.py.

    Args:
        output_dir: Directory containing model output JSONs
        sectors: List of sectors to store. None = all.

    Returns:
        Dict of {sector: success_bool}
    """
    loader_script = os.path.join(
        os.path.dirname(__file__), "..", "load_supabase.py"
    )

    if not os.path.exists(loader_script):
        logger.error(f"load_supabase.py not found at {loader_script}")
        return {}

    if sectors is None:
        sectors = ["power", "waste", "transport"]

    results = {}

    for sector in sectors:
        json_path = find_output_json(output_dir, sector)

        if not json_path:
            logger.warning(
                f"No output JSON found for {sector} in {output_dir}\n"
                f"  Expected one of: {OUTPUT_FILE_MAP.get(sector, [])}"
            )
            results[sector] = False
            continue

        # Sanity check sector field before loading
        if not validate_json_sector(json_path, EXPECTED_SECTORS[sector]):
            results[sector] = False
            continue

        logger.info(f"Storing {sector} results: {os.path.basename(json_path)}")

        try:
            result = subprocess.run(
                [sys.executable, loader_script, json_path],
                capture_output=True,
                text=True,
                timeout=180,
            )

            if result.stdout:
                for line in result.stdout.strip().split("\n"):
                    logger.info(f"  [loader] {line}")

            if result.returncode != 0:
                logger.error(f"Loader failed for {sector} (exit {result.returncode})")
                if result.stderr:
                    for line in result.stderr.strip().split("\n")[-5:]:
                        logger.error(f"  [stderr] {line}")
                results[sector] = False
            else:
                logger.info(f"{sector}: stored successfully in Supabase")
                results[sector] = True

        except subprocess.TimeoutExpired:
            logger.error(f"Loader timed out for {sector}")
            results[sector] = False
        except Exception as e:
            logger.error(f"Failed to run loader for {sector}: {e}")
            results[sector] = False

    return results


def copy_to_data_dir(output_dir: str, data_dir: str, sectors: list = None):
    """
    Copy model outputs to the main data/ directory so the backend
    JSON files stay in sync (used as fallback source by load_supabase.py).
    """
    if sectors is None:
        sectors = ["power", "waste", "transport"]

    # Canonical filenames used by backend
    canonical_names = {
        "power": "power_new.json",
        "waste": "waste_new.json",
        "transport": "transport_new.json",
    }

    for sector in sectors:
        json_path = find_output_json(output_dir, sector)
        if json_path:
            target = os.path.join(data_dir, canonical_names[sector])
            shutil.copy2(json_path, target)
            logger.info(f"Copied {sector} output → {target}")


if __name__ == "__main__":
    import argparse

    sys.path.insert(0, os.path.dirname(__file__))
    from utils.logger import setup_logger

    setup_logger()

    parser = argparse.ArgumentParser(description="Store model results in Supabase")
    parser.add_argument("--output-dir", default="data/outputs")
    parser.add_argument("--sectors", nargs="+", default=None,
                        choices=["power", "waste", "transport"])
    args = parser.parse_args()

    results = store_results(args.output_dir, args.sectors)
    for sector, success in results.items():
        print(f"  {sector}: {'OK' if success else 'FAILED'}")
