"""Measure the foot of the degradation ladder: the supplied extract itself.

Every rung of the ladder above this one is synthetic and reproducible anywhere. This
one is the extract, so it can only be measured on a machine that holds the private
data — and it must be measured with *exactly* the definitions the synthetic rungs
use, or the comparison that the whole ladder exists to make is not a comparison at
all. That is why this script imports `ladder_metrics` from
`scripts/05_report_synthetic.py` rather than restating it.

It reads the prepared tables that `notebooks/02_preprocessing.ipynb` writes, and
writes `data/synthetic/real_extract_rung.json`: six aggregate numbers, no patient-level
value, which `scripts/05_report_synthetic.py` then places in the ladder table.

Run from the repository root, after notebook 02::

    uv run python scripts/09_real_extract_rung.py
    uv run python scripts/05_report_synthetic.py      # picks up the new row
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "notebooks"))

from pipeline import landmarks  # noqa: E402

from _inputs import require  # noqa: E402

PREPARED = ROOT / "data" / "processed"
OUT = ROOT / "data" / "synthetic" / "real_extract_rung.json"
TABLES = ("implants", "echo_timeline", "events", "follow_up", "covariates")


def _ladder_metrics():
    """Import the measurement used for every synthetic rung, from the script that defines it."""
    path = ROOT / "scripts" / "05_report_synthetic.py"
    spec = importlib.util.spec_from_file_location("report_synthetic", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["report_synthetic"] = module
    spec.loader.exec_module(module)
    return module.ladder_metrics


def main() -> int:
    require(
        *[PREPARED / f"{name}.parquet" for name in TABLES],
        hint="Run notebooks/02_preprocessing.ipynb first; it writes these tables.",
    )
    prepared = {name: pd.read_parquet(PREPARED / f"{name}.parquet") for name in TABLES}
    prepared |= {"source": "real", "time_resolution": "year"}
    tables = landmarks.from_preprocessing(prepared)

    measured = _ladder_metrics()(tables)
    measured |= {
        "measured_on": date.today().isoformat(),
        "patients": int(len(tables["patients"])),
        "note": (
            "Aggregates only, measured on the supplied extract with the same definitions as the "
            "synthetic rungs. No patient-level value appears in this file."
        ),
    }
    OUT.write_text(json.dumps(measured, indent=2) + "\n")
    print(f"written to {OUT.relative_to(ROOT)}")
    for key, value in measured.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.3f}")
    print("\nNow rerun scripts/05_report_synthetic.py to place this row in the ladder.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
