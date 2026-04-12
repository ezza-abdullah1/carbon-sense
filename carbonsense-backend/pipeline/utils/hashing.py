"""
Hashing utilities for deduplication.
Computes SHA-256 of files or API responses to detect changes.
"""

import hashlib
import json


def file_hash(path: str) -> str:
    """SHA-256 hash of a file's contents."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def data_hash(data) -> str:
    """SHA-256 hash of a JSON-serializable object."""
    content = json.dumps(data, sort_keys=True, default=str).encode()
    return hashlib.sha256(content).hexdigest()
