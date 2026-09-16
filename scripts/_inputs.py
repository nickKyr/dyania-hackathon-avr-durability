"""Input checks shared by the data build scripts.

The three supplied extracts are patient data and are never committed, so a fresh
clone of this repository cannot run steps 01 to 04 until someone puts them in
`data/`. Without a check, that situation surfaces as a bare `FileNotFoundError`
from inside pandas, which tells a new teammate nothing about what to do. These
helpers turn it into one sentence that names the missing file and the fix.
"""

from __future__ import annotations

import sys
from pathlib import Path

DATA = Path("data")

EXTRACTS = ("notes_deidentified.xlsx", "labs_deidentified.xlsx", "medications_deidentified.xlsx")


def require(*paths: Path | str, hint: str = "") -> None:
    """Exit with a readable message if any of ``paths`` is missing.

    Args:
        paths: Files or directories the caller is about to read.
        hint: What the reader should do about it, appended to the message.
    """
    missing = [str(p) for p in paths if not Path(p).exists()]
    if not missing:
        return
    lines = ["Missing input:" if len(missing) == 1 else "Missing inputs:"]
    lines += [f"  - {m}" for m in missing]
    if hint:
        lines.append(hint)
    sys.exit("\n".join(lines))


def require_extracts(data: Path = DATA) -> None:
    """Check for the three supplied Excel extracts before reading them."""
    require(
        *[data / name for name in EXTRACTS],
        hint=(
            f"The supplied extracts are patient data: they are never committed, and every\n"
            f"spreadsheet under {data}/ is gitignored. Copy the three files a teammate holds into\n"
            f"{data}/ and rerun. See scripts/README.md."
        ),
    )
