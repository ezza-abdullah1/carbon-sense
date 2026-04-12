"""
Step 3: Run forecasting models.

All three models are independent and can run in parallel:
  - Power model  (Climate TRACE CSVs → JSON)
  - Waste model  (Climate TRACE CSVs → JSON)
  - Transport model (its own input JSON + shapefiles → JSON)

Each model reads from data/raw/ and writes JSON to data/outputs/.
"""

import logging
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger("carbonsense-pipeline")


def run_script(script_path: str, args: list, timeout: int = 7200) -> bool:
    """
    Run a Python script as a subprocess, streaming output in real time.

    Default timeout: 2 hours (Prophet + XGBoost grid search on 71 locations
    takes 15-40 minutes depending on hardware).

    Returns True if successful, False otherwise.
    """
    cmd = [sys.executable, script_path] + args
    logger.info(f"Running: {' '.join(cmd)}")

    try:
        # Use Popen to stream stdout/stderr live instead of buffering
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.path.dirname(script_path),
        )

        import threading

        def stream(pipe, level):
            for line in pipe:
                line = line.rstrip()
                if line:
                    if level == "err":
                        logger.warning(f"  {line}")
                    else:
                        logger.info(f"  {line}")

        t_out = threading.Thread(target=stream, args=(proc.stdout, "out"))
        t_err = threading.Thread(target=stream, args=(proc.stderr, "err"))
        t_out.start()
        t_err.start()

        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            logger.error(
                f"Model timed out after {timeout//60}min: {script_path}\n"
                f"  Consider reducing grid search configs in the model script."
            )
            return False
        finally:
            t_out.join()
            t_err.join()

        if proc.returncode != 0:
            logger.error(f"Script failed with exit code {proc.returncode}")
            return False

        return True

    except Exception as e:
        logger.error(f"Failed to run {script_path}: {e}")
        return False


def _build_sector_args(sector, raw_dir, output_dir, shapefile_path):
    """Build CLI args for a sector's model script."""
    models_dir = os.path.join(os.path.dirname(__file__), "models")

    if sector == "transport":
        script = os.path.join(models_dir, "transport_model.py")
        # Transport reads its own input JSON
        transport_input = os.path.join(
            os.path.dirname(__file__), "..", "data", "transport_new.json"
        )
        args = ["--input-json", transport_input, "--output-dir", output_dir]
        if shapefile_path:
            args += ["--shapefile", shapefile_path]
    else:
        script = os.path.join(models_dir, f"{sector}_model.py")
        args = ["--input-dir", raw_dir, "--output-dir", output_dir]
        if sector == "waste" and shapefile_path:
            args += ["--shapefile", shapefile_path]

    return script, args


def run_models(
    raw_dir: str,
    output_dir: str,
    shapefile_path: str = None,
    sectors: list = None,
) -> dict:
    """
    Run model scripts for specified sectors in parallel.

    All three sectors are independent — no dependency between them.

    Args:
        raw_dir: Directory containing downloaded CSVs
        output_dir: Directory for model output JSONs
        shapefile_path: Path to Union Council shapefile (for waste/transport)
        sectors: List of sectors to run. None = all.

    Returns:
        Dict of {sector: success_bool}
    """
    os.makedirs(output_dir, exist_ok=True)
    models_dir = os.path.join(os.path.dirname(__file__), "models")

    if sectors is None:
        sectors = ["power", "waste", "transport"]

    # Validate scripts exist
    tasks = {}
    for sector in sectors:
        script, args = _build_sector_args(sector, raw_dir, output_dir, shapefile_path)
        if not os.path.exists(script):
            logger.error(f"Model script not found: {script}")
            continue
        tasks[sector] = (script, args)

    if not tasks:
        logger.error("No model scripts found to run")
        return {s: False for s in sectors}

    # Run all sectors in parallel
    results = {}
    logger.info(f"Running {len(tasks)} models in parallel: {list(tasks.keys())}")

    with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
        futures = {
            executor.submit(run_script, script, args): sector
            for sector, (script, args) in tasks.items()
        }

        for future in as_completed(futures):
            sector = futures[future]
            try:
                success = future.result()
                results[sector] = success
                if success:
                    logger.info(f"{sector} model completed successfully")
                else:
                    logger.error(f"{sector} model FAILED")
            except Exception as e:
                logger.error(f"{sector} model raised exception: {e}")
                results[sector] = False

    # Mark missing sectors as failed
    for sector in sectors:
        if sector not in results:
            results[sector] = False

    return results


if __name__ == "__main__":
    import argparse

    sys.path.insert(0, os.path.dirname(__file__))
    from utils.logger import setup_logger

    setup_logger()

    parser = argparse.ArgumentParser(description="Run forecasting models")
    parser.add_argument("--raw-dir", default="data/raw")
    parser.add_argument("--output-dir", default="data/outputs")
    parser.add_argument("--shapefile", default=None)
    parser.add_argument("--sectors", nargs="+", default=None)
    args = parser.parse_args()

    results = run_models(args.raw_dir, args.output_dir, args.shapefile, args.sectors)
    for sector, success in results.items():
        status = "OK" if success else "FAILED"
        print(f"  {sector}: {status}")
