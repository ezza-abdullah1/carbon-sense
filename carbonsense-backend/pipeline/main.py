"""
CarbonSense Automated Pipeline - Main Entry Point

Orchestrates the full pipeline:
  1. Check if Climate TRACE has published new data (HEAD request)
  2. Download PAK.zip and extract per-year CSVs
  3. Run forecasting models (Power, Waste, Transport) in parallel
  4. Store results in Supabase

Usage:
    python pipeline/main.py                    # Normal run (skip if no new data)
    python pipeline/main.py --force            # Force rerun even if no new data
    python pipeline/main.py --sectors power    # Only run specific sectors
    python pipeline/main.py --skip-check       # Skip check, just run models on existing CSVs
"""

import argparse
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Ensure pipeline package is importable
sys.path.insert(0, os.path.dirname(__file__))

from utils.logger import setup_logger
from utils.state import PipelineState


def run_pipeline(
    force: bool = False,
    skip_check: bool = False,
    sectors: list = None,
    shapefile: str = None,
):
    # Setup
    pipeline_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(pipeline_dir)
    raw_dir = os.path.join(backend_dir, "data", "raw")
    output_dir = os.path.join(backend_dir, "data", "outputs")
    data_dir = os.path.join(backend_dir, "data")
    log_dir = os.path.join(pipeline_dir, "logs")
    state_file = os.path.join(pipeline_dir, "state.json")

    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    logger = setup_logger(log_dir)
    state = PipelineState(state_file)

    logger.info("=" * 60)
    logger.info("CarbonSense Pipeline Started")
    logger.info(f"Time: {datetime.now(timezone.utc).isoformat()}")
    logger.info(f"Force: {force} | Skip check: {skip_check}")
    logger.info("=" * 60)

    start_time = time.time()
    pipeline_sectors = sectors or ["power", "waste", "transport"]

    # ── Step 1: Check for new data ──────────────────────────────
    need_download = False
    if skip_check:
        logger.info("[Step 1] SKIPPED (--skip-check)")
    elif force:
        logger.info("[Step 1] SKIPPED (--force, will download anyway)")
        need_download = True
    else:
        logger.info("[Step 1] Checking Climate TRACE for new data...")
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "check", os.path.join(pipeline_dir, "01_check_new_data.py"))
        check_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(check_mod)

        need_download = check_mod.check_for_new_data(state)
        if not need_download:
            logger.info("No new data detected. Pipeline finished (nothing to do).")
            return True

    # ── Step 2: Download & extract ──────────────────────────────
    if need_download:
        logger.info("[Step 2] Downloading PAK.zip from Climate TRACE...")
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "download", os.path.join(pipeline_dir, "02_download_data.py"))
        dl_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(dl_mod)

        download_results = dl_mod.download_and_extract(raw_dir, state, pipeline_sectors)
        if not download_results:
            logger.error("Download failed. Check network connection.")
            return False
    else:
        logger.info("[Step 2] SKIPPED (using existing CSVs in data/raw/)")

    # Verify we have CSVs to work with
    has_data = any(Path(raw_dir).glob("power_*.csv")) or any(Path(raw_dir).glob("waste_*.csv"))
    if not has_data:
        logger.error("No CSV data found in data/raw/. Run without --skip-check to download.")
        return False

    # ── Check ZIP hash to avoid rerunning identical data ────────
    zip_path = os.path.join(raw_dir, "PAK.zip")
    if not force and os.path.exists(zip_path):
        from utils.hashing import file_hash
        current_hash = file_hash(zip_path)
        already_done = [
            s for s in pipeline_sectors
            if not state.needs_processing(s, current_hash)
        ]
        if already_done:
            logger.info(f"  Hash unchanged for: {already_done} — skipping their models")
            pipeline_sectors = [s for s in pipeline_sectors if s not in already_done]
        if not pipeline_sectors:
            logger.info("All sectors already up to date. Nothing to run.")
            return True

    # ── Step 3: Run models ──────────────────────────────────────
    logger.info("[Step 3] Running forecasting models...")
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "models", os.path.join(pipeline_dir, "03_run_models.py"))
    run_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(run_mod)

    model_results = run_mod.run_models(raw_dir, output_dir, shapefile, pipeline_sectors)

    successful_sectors = [s for s, ok in model_results.items() if ok]
    failed_sectors = [s for s, ok in model_results.items() if not ok]

    if failed_sectors:
        logger.warning(f"Models failed for: {failed_sectors}")
    if not successful_sectors:
        logger.error("All models failed. Skipping database update.")
        for sector in failed_sectors:
            state.update_sector(sector, status="failed",
                                last_run=datetime.now(timezone.utc).isoformat())
        return False

    # ── Step 4: Store results in Supabase ───────────────────────
    logger.info("[Step 4] Storing results in Supabase...")
    spec = importlib.util.spec_from_file_location(
        "store", os.path.join(pipeline_dir, "04_store_results.py"))
    store_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(store_mod)

    store_results = store_mod.store_results(output_dir, successful_sectors)
    store_mod.copy_to_data_dir(output_dir, data_dir, successful_sectors)

    # Update state
    now = datetime.now(timezone.utc).isoformat()
    for sector, success in store_results.items():
        state.update_sector(sector,
                            status="success" if success else "failed",
                            last_run=now)

    # ── Summary ─────────────────────────────────────────────────
    elapsed = time.time() - start_time
    logger.info("=" * 60)
    logger.info(f"Pipeline finished in {elapsed:.1f}s")
    for sector in pipeline_sectors:
        sec_state = state.get_sector(sector)
        logger.info(f"  {sector}: {sec_state.get('status', 'not run')}")
    logger.info("=" * 60)

    return len(failed_sectors) == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="CarbonSense Automated Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pipeline/main.py                     # Normal run (check + download + run)
  python pipeline/main.py --force             # Force download + rerun
  python pipeline/main.py --skip-check        # Use existing CSVs, skip download
  python pipeline/main.py --sectors power     # Only power sector
        """,
    )
    parser.add_argument("--force", action="store_true",
                        help="Force download + rerun even if no new data")
    parser.add_argument("--skip-check", action="store_true",
                        help="Skip check & download, use existing CSVs")
    parser.add_argument("--sectors", nargs="+", default=None,
                        choices=["power", "waste", "transport"])
    parser.add_argument("--shapefile", default=None,
                        help="Path to Union Council shapefile")
    args = parser.parse_args()

    success = run_pipeline(
        force=args.force,
        skip_check=args.skip_check,
        sectors=args.sectors,
        shapefile=args.shapefile,
    )
    sys.exit(0 if success else 1)
