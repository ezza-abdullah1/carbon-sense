"""
Pipeline state management.
Tracks what data has been processed to avoid reruns.
"""

import json
import os
from datetime import datetime, timezone

DEFAULT_STATE = {
    "last_checked": None,
    "sectors": {
        "power": {
            "last_year_processed": None,
            "last_data_hash": None,
            "last_run": None,
            "status": None,
        },
        "waste": {
            "last_year_processed": None,
            "last_data_hash": None,
            "last_run": None,
            "status": None,
        },
        "transport": {
            "last_year_processed": None,
            "last_data_hash": None,
            "last_run": None,
            "status": None,
        },
    },
}


class PipelineState:
    def __init__(self, state_file: str):
        self.state_file = state_file
        self.state = self._load()

    def _load(self) -> dict:
        if os.path.exists(self.state_file):
            with open(self.state_file, "r") as f:
                return json.load(f)
        return json.loads(json.dumps(DEFAULT_STATE))

    def save(self):
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, "w") as f:
            json.dump(self.state, f, indent=2, default=str)

    def get_sector(self, sector: str) -> dict:
        return self.state["sectors"].get(sector, {})

    def update_sector(self, sector: str, **kwargs):
        if sector not in self.state["sectors"]:
            self.state["sectors"][sector] = {}
        self.state["sectors"][sector].update(kwargs)
        self.save()

    def mark_checked(self):
        self.state["last_checked"] = datetime.now(timezone.utc).isoformat()
        self.save()

    def needs_processing(self, sector: str, data_hash: str) -> bool:
        """Returns True if this sector has new data that hasn't been processed."""
        sec = self.get_sector(sector)
        if sec.get("last_data_hash") == data_hash and sec.get("status") == "success":
            return False
        return True
