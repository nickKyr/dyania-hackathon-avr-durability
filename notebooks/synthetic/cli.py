"""Command line interface: generate a cohort, report its calibration, write CSVs.

Run from the ``notebooks`` directory::

    python -m synthetic --preset ideal --out ../data/synthetic/ideal
    python -m synthetic --ladder --out ../data/synthetic
    python -m synthetic --sample 50 --out ../data/synthetic/sample
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from . import DEFAULT, PRESET_DESCRIPTIONS, PRESETS, calibration_report, generate


def _write(tables: dict[str, pd.DataFrame], destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for name, frame in tables.items():
        frame.to_csv(destination / f"{name}.csv", index=False)


def _summarise(tables: dict[str, pd.DataFrame]) -> str:
    counts = ", ".join(f"{name} {len(frame):,}" for name, frame in tables.items())
    events = tables["events"].groupby("event_type").size().to_dict()
    return f"{counts}\n    events: " + ", ".join(f"{k} {v:,}" for k, v in sorted(events.items()))


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns a process exit code."""
    parser = argparse.ArgumentParser(
        prog="python -m synthetic",
        description="Generate the synthetic AVR durability cohort.",
    )
    parser.add_argument("--preset", default="ideal", choices=sorted(PRESETS), help="Rung of the degradation ladder.")
    parser.add_argument("--ladder", action="store_true", help="Generate every rung, each into its own directory.")
    parser.add_argument("--seed", type=int, default=20260917)
    parser.add_argument("--n-patients", type=int, default=None, help="Cohort size; defaults to the protocol's 1,800.")
    parser.add_argument("--sample", type=int, default=None, help="Write only the first N patients, for a committed sample.")
    parser.add_argument("--out", type=Path, default=None, help="Directory to write CSVs into. Omit to print only.")
    parser.add_argument("--no-calibration", action="store_true", help="Skip the calibration table.")
    args = parser.parse_args(argv)

    presets = tuple(PRESETS) if args.ladder else (args.preset,)
    for preset in presets:
        tables = generate(preset, seed=args.seed, n_patients=args.n_patients)

        if args.sample is not None:
            keep = set(tables["patients"]["patient_id"].head(args.sample))
            tables = {name: frame[frame["patient_id"].isin(keep)].reset_index(drop=True) for name, frame in tables.items()}

        print(f"\n=== {preset} ===\n    {PRESET_DESCRIPTIONS[preset]}\n    {_summarise(tables)}")

        if preset == "ideal" and not args.no_calibration and args.sample is None:
            report = calibration_report(tables)
            print("\n    Calibration against published anchors "
                  f"({int(report['within_band'].sum())} of {len(report)} within band):\n")
            print(report.drop(columns=["source"]).to_string(index=False))
            print("\n    Sources:")
            for _, row in report.drop_duplicates("source").iterrows():
                print(f"      - {row['source']}")

        if args.out is not None:
            destination = args.out / preset if args.ladder else args.out
            _write(tables, destination)
            print(f"\n    written to {destination}")

    print(f"\nSeed {args.seed}; cohort size {args.n_patients or DEFAULT.cohort.n_patients}. "
          "Every row is simulated. No value in these tables came from a patient.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
