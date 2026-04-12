"""
Step 2: Download Climate TRACE data and extract sector CSVs.

Downloads the Pakistan country package ZIP from:
  https://downloads.climatetrace.org/latest/country_packages/bc/PAK.zip

Then extracts the relevant sector CSVs and splits them into per-year
files matching the format the model scripts expect:
  power_2021.csv, power_2022.csv, ...
  waste_2021.csv, waste_2022.csv, ...
"""

import csv
import io
import logging
import os
import zipfile
from pathlib import Path

import requests

from utils.hashing import file_hash

logger = logging.getLogger("carbonsense-pipeline")

DOWNLOAD_URL = "https://downloads.climatetrace.org/latest/country_packages/co2/PAK.zip"

# Which CSVs to extract from the ZIP, mapped to our sector names
SECTOR_FILES = {
    "power": [
        "DATA/power/electricity-generation_emissions_sources_v5_5_0.csv",
    ],
    "waste": [
        "DATA/waste/solid-waste-disposal_emissions_sources_v5_5_0.csv",
        "DATA/waste/domestic-wastewater-treatment-and-discharge_emissions_sources_v5_5_0.csv",
    ],
    "transport": [
        "DATA/transportation/road-transportation_emissions_sources_v5_5_0.csv",
        "DATA/transportation/domestic-aviation_emissions_sources_v5_5_0.csv",
        "DATA/transportation/international-aviation_emissions_sources_v5_5_0.csv",
    ],
}

# Column mapping: Climate TRACE ZIP CSV -> format models expect
# ZIP has: source_id, source_name, source_type, iso3_country, sector, subsector, start_time, ...
# Models expect: source_id, source_name, source_type, iso3_country, original_inventory_sector, start_time, ...
COLUMN_RENAME = {
    "subsector": "original_inventory_sector",
}

# Columns to keep in the output CSVs (matching your existing CSV format)
OUTPUT_COLUMNS = [
    "source_id", "source_name", "source_type", "iso3_country",
    "original_inventory_sector", "start_time", "end_time",
    "temporal_granularity", "gas", "emissions_quantity",
    "emissions_factor", "emissions_factor_units",
    "capacity", "capacity_units", "capacity_factor",
    "activity", "activity_units",
    "created_date", "modified_date", "lat", "lon",
]


def download_zip(output_path: str) -> bool:
    """Download the Pakistan country package ZIP with streaming."""
    logger.info(f"Downloading {DOWNLOAD_URL} ...")
    try:
        resp = requests.get(DOWNLOAD_URL, stream=True, timeout=120)
        resp.raise_for_status()

        total = int(resp.headers.get("Content-Length", 0))
        downloaded = 0

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)

        size_mb = os.path.getsize(output_path) / 1024 / 1024
        logger.info(f"  Downloaded {size_mb:.1f}MB -> {output_path}")
        return True

    except requests.RequestException as e:
        logger.error(f"Download failed: {e}")
        return False


def extract_and_split(zip_path: str, output_dir: str, sectors: list = None) -> dict:
    """
    Extract sector CSVs from the ZIP and split into per-year files.

    The ZIP contains one big CSV per sub-sector with ALL years.
    Models expect per-year files: power_2021.csv, power_2022.csv, etc.

    Args:
        zip_path: Path to downloaded PAK.zip
        output_dir: Where to write the per-year CSVs
        sectors: Which sectors to extract. None = all.

    Returns:
        Dict of {sector: {year: filepath}}
    """
    os.makedirs(output_dir, exist_ok=True)

    if sectors is None:
        sectors = list(SECTOR_FILES.keys())

    z = zipfile.ZipFile(zip_path)
    available_files = set(z.namelist())

    results = {}

    for sector in sectors:
        csv_files = SECTOR_FILES.get(sector, [])
        all_rows = []

        for csv_file in csv_files:
            # Try to find the file - version number might change
            if csv_file not in available_files:
                # Search for similar filename
                base = csv_file.rsplit("_v", 1)[0]
                matches = [f for f in available_files if f.startswith(base) and f.endswith(".csv") and "confidence" not in f and "ownership" not in f]
                if matches:
                    csv_file = matches[0]
                    logger.info(f"  Using {csv_file} (version auto-detected)")
                else:
                    logger.warning(f"  {csv_file} not found in ZIP")
                    continue

            logger.info(f"  Extracting {csv_file}")
            with z.open(csv_file) as f:
                reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8"))
                for row in reader:
                    # Rename columns to match model expectations
                    for old_name, new_name in COLUMN_RENAME.items():
                        if old_name in row:
                            row[new_name] = row.pop(old_name)
                    # Remove extra columns not needed
                    if "sector" in row and "original_inventory_sector" not in row:
                        row["original_inventory_sector"] = row.pop("sector")
                    all_rows.append(row)

        if not all_rows:
            logger.warning(f"  No data found for {sector}")
            continue

        # Group by year and write per-year CSVs
        by_year = {}
        for row in all_rows:
            year = row.get("start_time", "")[:4]
            if year.isdigit():
                by_year.setdefault(year, []).append(row)

        sector_results = {}
        prefix = "power" if sector == "power" else sector
        for year, rows in sorted(by_year.items()):
            out_path = os.path.join(output_dir, f"{prefix}_{year}.csv")
            with open(out_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(rows)
            sector_results[year] = out_path
            logger.info(f"  {prefix}_{year}.csv: {len(rows)} rows")

        results[sector] = sector_results

    return results


def download_and_extract(output_dir: str, state=None, sectors: list = None) -> dict:
    """
    Full download + extract pipeline.

    Skips download entirely if existing PAK.zip hash matches the last
    successful run stored in state.json. Only re-extracts CSVs if the
    ZIP content has actually changed.

    Returns dict of {sector: {year: filepath}} or empty on failure.
    """
    zip_path = os.path.join(output_dir, "PAK.zip")

    # Hash the existing ZIP before downloading (if it exists)
    existing_hash = file_hash(zip_path) if os.path.exists(zip_path) else None
    stored_hash = state.state.get("zip_hash") if state else None

    if existing_hash and existing_hash == stored_hash:
        logger.info(f"  Existing PAK.zip hash matches last run — skipping download")
        # Still extract in case CSVs are missing
        results = extract_and_split(zip_path, output_dir, sectors)
        return results

    # Download fresh copy
    if not download_zip(zip_path):
        return {}

    # Check if newly downloaded ZIP is identical to what we had
    new_hash = file_hash(zip_path)
    if new_hash == existing_hash:
        logger.info("  Downloaded ZIP is identical to existing file — no change")
        results = extract_and_split(zip_path, output_dir, sectors)
        return results

    logger.info(f"  ZIP content changed (hash differs) — extracting fresh CSVs")

    # Save remote metadata + hash to state
    if state:
        try:
            resp = requests.head(DOWNLOAD_URL, timeout=15)
            state.state["remote_last_modified"] = resp.headers.get("Last-Modified", "")
            state.state["remote_etag"] = resp.headers.get("ETag", "")
            state.state["zip_hash"] = new_hash
            state.save()
        except Exception:
            pass

    results = extract_and_split(zip_path, output_dir, sectors)

    if state and results:
        for sector in results:
            state.update_sector(sector, last_data_hash=new_hash)

    return results


if __name__ == "__main__":
    import argparse
    import sys

    sys.path.insert(0, os.path.dirname(__file__))
    from utils.logger import setup_logger

    setup_logger()

    parser = argparse.ArgumentParser(description="Download Climate TRACE data")
    parser.add_argument("--output-dir", default="data/raw")
    parser.add_argument("--sectors", nargs="+", default=None,
                        choices=["power", "waste", "transport"])
    args = parser.parse_args()

    results = download_and_extract(args.output_dir, sectors=args.sectors)
    for sector, years in results.items():
        print(f"  {sector}: {list(years.keys())}")
