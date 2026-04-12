"""
Pipeline step wrappers — thin glue that main.py calls.
Each function handles one step and updates state.
"""

import importlib.util
import os
import logging
from datetime import datetime, timezone

from utils.state import PipelineState

logger = logging.getLogger("carbonsense-pipeline")

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_module(filename):
    """Load a pipeline step module by filename (handles numeric prefixes)."""
    path = os.path.join(PIPELINE_DIR, filename)
    spec = importlib.util.spec_from_file_location(filename.replace(".py", ""), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def step_01_check(state):
    """Check Climate TRACE API for new data."""
    mod = _load_module("01_check_new_data.py")
    return mod.check_for_new_data(state)


def step_01_check_all(state):
    """Get ALL available years from Climate TRACE (for --force mode)."""
    mod = _load_module("01_check_new_data.py")
    all_data = {}
    for sector in ["power", "waste", "transport"]:
        years = mod.get_available_years(sector)
        if years:
            all_data[sector] = years
            logger.info(f"  {sector}: all available years {years}")
    return all_data


def step_02_download(new_data: dict, raw_dir: str, state: PipelineState) -> dict:
    """Download new data from Climate TRACE."""
    mod = _load_module("02_download_data.py")

    results = {}
    for sector, years in new_data.items():
        if sector == "transport":
            continue  # Transport doesn't download from Climate TRACE directly

        if not years:
            logger.info(f"  {sector}: no specific years to download (force mode)")
            continue

        downloaded = mod.download_sector_data(sector, years, raw_dir)
        results[sector] = downloaded

        if downloaded:
            new_hash = mod.compute_download_hash(raw_dir, sector)
            if not state.needs_processing(sector, new_hash):
                logger.info(f"  {sector}: data unchanged (hash match), skipping")
            else:
                state.update_sector(sector, last_data_hash=new_hash)

    return results


def step_03_run_models(
    raw_dir: str, output_dir: str, shapefile: str, sectors: list
) -> dict:
    """Run forecasting models."""
    mod = _load_module("03_run_models.py")
    return mod.run_models(raw_dir, output_dir, shapefile, sectors)


def step_04_store(
    output_dir: str, data_dir: str, sectors: list, state: PipelineState
) -> dict:
    """Store results in Supabase and update state."""
    mod = _load_module("04_store_results.py")

    results = mod.store_results(output_dir, sectors)

    # Copy outputs to main data dir
    mod.copy_to_data_dir(output_dir, data_dir, sectors)

    # Update state for successful sectors
    now = datetime.now(timezone.utc).isoformat()
    for sector, success in results.items():
        if success:
            state.update_sector(sector, status="success", last_run=now)
        else:
            state.update_sector(sector, status="failed", last_run=now)

    return results
