"""Locate the private hackathon data files, which live outside the repository.

The data directory is resolved from, in order of precedence:

1. the ``AVR_DATA_DIR`` environment variable,
2. ``AVR_DATA_DIR`` in a ``.env`` file at the repository root,
3. the default ``~/dyania-data/raw``.

Example:
    >>> import pandas as pd
    >>> from data_paths import LABS, data_file
    >>> labs = pd.read_excel(data_file(LABS))
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final

__all__ = [
    "LABS",
    "MEDICATIONS",
    "NOTES",
    "ALL_DATA",
    "data_dir",
    "data_file",
    "derived_dir",
    "derived_file",
]

REPO_ROOT: Final[Path] = Path(__file__).resolve().parent.parent
ENV_VAR: Final[str] = "AVR_DATA_DIR"
DERIVED_ENV_VAR: Final[str] = "AVR_DERIVED_DIR"
DEFAULT_DATA_DIR: Final[str] = "~/dyania-data/raw"

LABS: Final[str] = "labs_deidentified.xlsx"
MEDICATIONS: Final[str] = "medications_deidentified.xlsx"
NOTES: Final[str] = "notes_deidentified.xlsx"

ALL_DATA: Final[str] = "all_data_one_sheet.xlsx"
"""The team's consolidated long-format extract: a derived file, not a source one.

It carries verbatim note text in its ``evidence`` column -- some 787,000 characters
of it -- so it is held with the source data outside the repository, not beside it.
"""


def _read_dotenv(key: str) -> str | None:
    """Return the value of ``key`` from the repository ``.env`` file, if present."""
    env_file = REPO_ROOT / ".env"
    if not env_file.is_file():
        return None
    for line in env_file.read_text(encoding="utf-8").splitlines():
        name, sep, value = line.partition("=")
        if sep and name.strip() == key:
            return value.strip().strip("'\"")
    return None


def data_dir() -> Path:
    """Return the resolved data directory.

    Raises:
        RuntimeError: If the directory is inside the repository.
        FileNotFoundError: If the directory does not exist.
    """
    raw = os.environ.get(ENV_VAR) or _read_dotenv(ENV_VAR) or DEFAULT_DATA_DIR
    path = Path(raw).expanduser().resolve()
    if path == REPO_ROOT or REPO_ROOT in path.parents:
        raise RuntimeError(
            f"{ENV_VAR} ({path}) is inside the repository; keep data outside it."
        )
    if not path.is_dir():
        raise FileNotFoundError(f"Data directory not found: {path}. Set {ENV_VAR}.")
    return path


def derived_dir() -> Path:
    """Return the directory holding files derived from the source extract.

    Derived files are treated exactly like source data, because a table carrying
    verbatim note snippets is as identifying as the note it came from.

    Resolved from ``AVR_DERIVED_DIR`` if set, otherwise a ``derived`` directory
    beside the source data.

    Raises:
        RuntimeError: If the directory is inside the repository.
        FileNotFoundError: If the directory does not exist.
    """
    raw = os.environ.get(DERIVED_ENV_VAR) or _read_dotenv(DERIVED_ENV_VAR)
    path = Path(raw).expanduser().resolve() if raw else data_dir().parent / "derived"
    if path == REPO_ROOT or REPO_ROOT in path.parents:
        raise RuntimeError(
            f"{DERIVED_ENV_VAR} ({path}) is inside the repository; keep data outside it."
        )
    if not path.is_dir():
        raise FileNotFoundError(f"Derived data directory not found: {path}. Set {DERIVED_ENV_VAR}.")
    return path


def derived_file(name: str) -> Path:
    """Return the path to a derived file, raising if it does not exist.

    Raises:
        FileNotFoundError: If the file is missing from the derived directory.
    """
    path = derived_dir() / name
    if not path.is_file():
        raise FileNotFoundError(f"Derived data file not found: {path}")
    return path


def data_file(name: str) -> Path:
    """Return the path to a data file, raising if it does not exist.

    Raises:
        FileNotFoundError: If the file is missing from the data directory.
    """
    path = data_dir() / name
    if not path.is_file():
        raise FileNotFoundError(f"Data file not found: {path}")
    return path
