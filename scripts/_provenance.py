"""Provenance stamp shared by the reporting scripts.

Every generated document says which commit produced it. Without that, a document
and the code can drift apart silently, which is exactly what happened to
`data/synthetic/results.md` before these scripts existed.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def git_revision() -> str:
    """Short commit hash of the working tree, marked if it has uncommitted changes."""
    try:
        rev = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
        return f"{rev}{' plus uncommitted changes' if dirty else ''}"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"
