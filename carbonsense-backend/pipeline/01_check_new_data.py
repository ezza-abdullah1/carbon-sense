"""
Step 1: Check if Climate TRACE has released new data.

Climate TRACE publishes country data packages as ZIP files at:
  https://downloads.climatetrace.org/latest/country_packages/bc/{COUNTRY}.zip

To detect new data, we compare the remote file's Last-Modified header
(or Content-Length) against what we last downloaded. If it's changed,
new data is available.
"""

import logging
import requests
from typing import Optional

logger = logging.getLogger("carbonsense-pipeline")

DOWNLOAD_URL = "https://downloads.climatetrace.org/latest/country_packages/co2/PAK.zip"


def get_remote_metadata() -> Optional[dict]:
    """
    HEAD request to check the remote ZIP's Last-Modified date and size.
    Returns dict with 'last_modified' and 'content_length', or None on failure.
    """
    try:
        resp = requests.head(DOWNLOAD_URL, timeout=15)
        resp.raise_for_status()
        return {
            "last_modified": resp.headers.get("Last-Modified", ""),
            "content_length": resp.headers.get("Content-Length", ""),
            "etag": resp.headers.get("ETag", ""),
        }
    except requests.RequestException as e:
        logger.error(f"Failed to check Climate TRACE download: {e}")
        return None


def check_for_new_data(state) -> bool:
    """
    Check if Climate TRACE has published new data since our last download.

    Args:
        state: PipelineState instance

    Returns:
        True if new data is available (or first run), False if unchanged.
    """
    logger.info(f"Checking {DOWNLOAD_URL} ...")

    remote = get_remote_metadata()
    if not remote:
        logger.warning("Could not reach Climate TRACE. Skipping check.")
        return False

    logger.info(f"  Remote Last-Modified: {remote['last_modified']}")
    logger.info(f"  Remote Size: {remote['content_length']} bytes")

    last_modified = state.state.get("remote_last_modified", "")
    last_etag = state.state.get("remote_etag", "")

    if remote["etag"] and remote["etag"] == last_etag:
        logger.info("  No change (ETag matches). No new data.")
        return False

    if remote["last_modified"] and remote["last_modified"] == last_modified:
        logger.info("  No change (Last-Modified matches). No new data.")
        return False

    if not last_modified and not last_etag:
        logger.info("  First run — new data available.")
    else:
        logger.info("  Data has changed since last download!")

    state.mark_checked()
    return True


if __name__ == "__main__":
    import sys
    import os

    sys.path.insert(0, os.path.dirname(__file__))
    from utils.logger import setup_logger
    from utils.state import PipelineState

    setup_logger()
    state = PipelineState(os.path.join(os.path.dirname(__file__), "state.json"))
    result = check_for_new_data(state)

    if result:
        print("\nNew data available! Pipeline should run.")
    else:
        print("\nNo new data. Pipeline will not run.")
