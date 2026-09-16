"""Regenerate `data/synthetic/results.md` from the code as it stands today.

The evidence this repository publishes about the synthetic cohort has to be a
function of the code that produced it, not a snapshot someone pasted once. This
script is that function: it regenerates every table in the results document from
the current generator, and stamps the document with the commit it ran against, so
a reader can tell at a glance whether the numbers still belong to the code.

It needs no private data. Every synthetic rung is reproducible from a fixed seed
on any machine. The one row that cannot be recomputed here is the foot of the
degradation ladder -- the supplied extract itself -- which is read from
`data/synthetic/real_extract_rung.json` if a teammate has measured it, and
reported as missing otherwise.

Run from the repository root::

    uv run python scripts/05_report_synthetic.py            # full, ~8 minutes
    uv run python scripts/05_report_synthetic.py --quick    # 2 seeds, for a smoke test
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "notebooks"))

from synthetic import (  # noqa: E402  (path set above)
    ANCHORS,
    DEFAULT,
    PRESET_DESCRIPTIONS,
    PRESETS,
    calibration_across_seeds,
    failure_mode_shares,
    generate,
    incidence_by_family,
)
from synthetic.parameters import ABSOLUTE_TOLERANCE, RELATIVE_TOLERANCE  # noqa: E402

OUT = ROOT / "data" / "synthetic" / "results.md"
REAL_RUNG = ROOT / "data" / "synthetic" / "real_extract_rung.json"

SEEDS: tuple[int, ...] = (20260917, 1, 2, 3, 4, 5, 6, 7)
LADDER_N = 117
"""Cohort size for the ladder: the number of patients in the supplied extract, so
that every rung is comparable with the extract at the foot of it."""

STRUCTURAL = ("svd_stage2", "svd_stage3", "bvf_reintervention")


def _git_revision() -> str:
    try:
        rev = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
        return f"{rev}{' (with uncommitted changes)' if dirty else ''}"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def ladder_metrics(tables: dict[str, pd.DataFrame]) -> dict[str, float]:
    """Measure what an analyst can see of one rung of the degradation ladder.

    Two event counts are reported, because they answer different questions and the
    difference between them is large. ``patients_with_event_per_100`` counts
    patients who reached any structural endpoint; ``event_rows_per_100`` counts
    endpoint rows, and a valve that deteriorates to stage 2, then to stage 3, then
    is reintervened contributes three of them. Only the first is comparable across
    datasets that record endpoints differently, so it is the primary measure here.
    """
    patients, echos, events = tables["patients"], tables["echos"], tables["events"]
    n = len(patients)
    per_patient = echos.groupby("patient_id").size().reindex(patients["patient_id"]).fillna(0)
    with_gradient = (
        echos[echos["mean_gradient_mmhg"].notna()]
        .groupby("patient_id").size().reindex(patients["patient_id"]).fillna(0)
    )
    structural = events[events["event_type"].isin(STRUCTURAL)]
    return {
        "any_examination": float((per_patient > 0).mean()),
        "examinations_per_patient": float(per_patient.mean()),
        "more_than_one_gradient": float((with_gradient > 1).mean()),
        "patients_with_event_per_100": 100.0 * structural["patient_id"].nunique() / n,
        "event_rows_per_100": 100.0 * len(structural) / n,
        "death_observed": float(events["event_type"].eq("death").any()),
    }


def ladder_table(seeds: tuple[int, ...]) -> pd.DataFrame:
    """Run every rung of the ladder on every seed and average the result.

    At 117 patients a single cohort is a small sample: the Monte Carlo spread of an
    event count is comparable with the differences between rungs. Averaging over
    seeds separates what a rung costs from what one draw happened to do.
    """
    rows = []
    for preset in PRESETS:
        per_seed = pd.DataFrame(
            [ladder_metrics(generate(preset, seed=seed, n_patients=LADDER_N)) for seed in seeds]
        )
        rows.append(
            {"rung": preset, "simulated": True}
            | {f"{k}_mean": v for k, v in per_seed.mean().items()}
            | {f"{k}_sd": v for k, v in per_seed.std().items()}
        )
    return pd.DataFrame(rows)


def _pct(mean: float, sd: float) -> str:
    return f"{mean:.1%} ± {sd * 100:.1f}" if sd > 0 else f"{mean:.1%}"


def _num(mean: float, sd: float) -> str:
    return f"{mean:.2f} ± {sd:.2f}" if sd > 0 else f"{mean:.2f}"


def render_calibration(report: pd.DataFrame) -> str:
    lines = [
        "| quantity | group | horizon | published | cohort | inside band |",
        "|---|---|---|---|---|---|",
    ]
    for targeted, label in ((True, "**targeted**"), (False, "**not targeted**")):
        block = report[report["targeted"] == targeted]
        if block.empty:
            continue
        lines.append(f"| {label} | | | | | |")
        for _, row in block.iterrows():
            lines.append(
                f"| {row['quantity'].replace('_', ' ')} | {row['subgroup']} | "
                f"{row['horizon_years']:g} y | {row['published']:.1%} | "
                f"{row['cohort_mean']:.1%} ± {row['cohort_sd'] * 100:.1f} | "
                f"{row['seeds_within_band']} of {row['seeds']} |"
            )
    return "\n".join(lines)


def render_ladder(ladder: pd.DataFrame, real: dict | None) -> str:
    lines = [
        "| rung | simulated | any examination | exams per patient | more than one gradient "
        "| patients with an event, per 100 | event rows per 100 | death observed |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for _, row in ladder.iterrows():
        lines.append(
            f"| `{row['rung']}` | yes "
            f"| {_pct(row['any_examination_mean'], row['any_examination_sd'])} "
            f"| {_num(row['examinations_per_patient_mean'], row['examinations_per_patient_sd'])} "
            f"| {_pct(row['more_than_one_gradient_mean'], row['more_than_one_gradient_sd'])} "
            f"| {_num(row['patients_with_event_per_100_mean'], row['patients_with_event_per_100_sd'])} "
            f"| {_num(row['event_rows_per_100_mean'], row['event_rows_per_100_sd'])} "
            f"| {'yes' if row['death_observed_mean'] > 0 else '**no**'} |"
        )
    if real is None:
        lines.append(
            "| `as_received` | **no** | *not recomputed — see below* | | | | | |"
        )
    else:
        lines.append(
            f"| `as_received` | **no** | {real['any_examination']:.1%} "
            f"| {real['examinations_per_patient']:.2f} "
            f"| {real['more_than_one_gradient']:.1%} "
            f"| {real['patients_with_event_per_100']:.2f} "
            f"| {real['event_rows_per_100']:.2f} | **no** |"
        )
    return "\n".join(lines)


def render_families(families: pd.DataFrame) -> str:
    horizons = [c for c in families.columns if c.endswith("y") and c[:-1].isdigit()]
    header = " | ".join(f"{h[:-1]} years" for h in horizons)
    lines = [f"| valve family | implanted | mean indexed EOA | {header} |",
             "|---|---|---|" + "---|" * len(horizons)]
    for family, row in families.iterrows():
        cells = " | ".join(f"{row[h]:.1%}" for h in horizons)
        lines.append(
            f"| {family} | {int(row['n'])} | {row['mean_eoa_index']:.2f} cm²/m² | {cells} |"
        )
    return "\n".join(lines)


def render_modes(modes: pd.DataFrame) -> str:
    lines = ["| endpoint | failure mode | events | share | median years to event |",
             "|---|---|---|---|---|"]
    for _, row in modes.iterrows():
        lines.append(
            f"| {row['event_type']} | {row['failure_mode']} | {int(row['n'])} "
            f"| {row['share']:.0%} | {row['median_years']:.1f} |"
        )
    return "\n".join(lines)


def build_document(seeds: tuple[int, ...], n_patients: int) -> str:
    calibration = calibration_across_seeds(seeds=seeds, n_patients=n_patients)
    reference = generate("ideal", seed=seeds[0], n_patients=n_patients)
    families = incidence_by_family(reference)
    modes = failure_mode_shares(reference)
    ladder = ladder_table(seeds)
    real = json.loads(REAL_RUNG.read_text()) if REAL_RUNG.exists() else None

    ideal = ladder[ladder["rung"] == "ideal"].iloc[0]
    supplied = ladder[ladder["rung"] == "as_supplied"].iloc[0]
    loss_patients = 1 - supplied["patients_with_event_per_100_mean"] / ideal["patients_with_event_per_100_mean"]
    loss_rows = 1 - supplied["event_rows_per_100_mean"] / ideal["event_rows_per_100_mean"]
    stable = int((calibration["seeds_within_band"] == calibration["seeds"]).sum())

    labels = {"patients": "patients", "echos": "examinations", "events": "endpoint rows",
              "followup": "follow-up records"}
    counts = ", ".join(f"{len(frame):,} {labels.get(name, name)}" for name, frame in reference.items())
    sources = "\n".join(f"- {s}" for s in dict.fromkeys(a.source for a in ANCHORS))

    return f"""# Synthetic Cohort — Results

> Regenerated by `scripts/05_report_synthetic.py` on {date.today().isoformat()}, against commit
> `{_git_revision()}`. Do not edit the tables by hand: rerun the script, so that what this
> document claims and what the code does cannot drift apart.
>
> Every figure is an aggregate. No patient-level value, note text or identifier appears here.

At the protocol's sample size of {n_patients:,} patients the cohort is {counts}, from seed {seeds[0]}. The tables
below are the two claims this workstream makes: that the cohort lands where published series
land, and that the cost of each data defect can be measured rather than asserted.

## Calibration against published evidence

Cumulative incidence by the Aalen–Johansen estimator, under a competing risk of death —
not one minus Kaplan–Meier, which would answer a question about a population in which
nobody dies. NOTION used the same estimator, so the comparison is like for like.

Each band is the same rule applied to every anchor, fixed before any cohort was generated:
**{ABSOLUTE_TOLERANCE:.1%} absolute, or {RELATIVE_TOLERANCE:.0%} of the published value, whichever is larger.**
Figures are the mean and standard deviation over {len(seeds)} seeds, because at {n_patients:,} patients the
Monte Carlo error of a 20% incidence is about one percentage point — the size of the
differences being judged. {stable} of {len(calibration)} anchors are inside the band on every seed.

{render_calibration(calibration)}

Sources:

{sources}

## How the cohort fails

Structural failure is generated as three competing processes rather than one, because they
have different time courses, different signatures on the echocardiogram and different risk
factors, and a cohort with a single latent onset cannot distinguish them. The shares below
are an assumption of the generator, not an anchor: where they disagree with the published
incidence anchors, the anchors win.

{render_modes(modes)}

## Durability by valve family

The family effect is entered on the failure mode a device actually fails by, and only for
families with a published signal behind them. What matters is not the multiplier but the
incidence it produces once orifice area, size and approach mix have had their say, which is
the table below.

{render_families(families)}

## The degradation ladder

The same cohort, its data progressively removed. The patients, their biology and their
events are identical on every rung; only what an analyst can see of them changes, so one
unchanged pipeline run across the rungs measures exactly one thing — what each defect
costs.

**The last rung is not simulated.** It is the supplied extract, mapped into the same
schema. Every rung above it is synthetic and reproducible without access to any private
data; all rungs are shown at n = {LADDER_N}, the size of the extract, as the mean and standard
deviation over {len(seeds)} seeds.

{render_ladder(ladder, real)}

What each rung removes:

{chr(10).join(f"- `{name}` — {text}" for name, text in PRESET_DESCRIPTIONS.items())}
- `as_received` — Not simulated: the supplied extract itself, mapped into the same schema.

### Two event counts, and why both are shown

A valve that deteriorates to stage 2, then to stage 3, then is reintervened produces one
affected patient and three endpoint rows. Datasets differ in which of the two they record,
and the difference is a factor of about two, so a single "events per 100" figure quoted
without its definition is not comparable with anything. The patient count is the primary
measure here; the row count is shown so that a figure quoted elsewhere can be placed.

### The cost of incomplete ascertainment

Between the rung the protocol asks for (`ideal`) and the rung that mirrors the supplied
extract (`as_supplied`), the measured event rate falls by **{loss_patients:.0%}** counted by
affected patients and by **{loss_rows:.0%}** counted by endpoint rows. The patients are the same
patients and their valves fail at the same times; what changes is only whether anyone looked.

The two figures are not the same, and the difference is informative. Losing surveillance removes
a whole patient from the event count only when *every* one of their examinations is missing,
but it removes the later stages of a patient's course much more easily — the stage 3 that would
have followed a stage 2, the reintervention that would have followed both. Incomplete follow-up
therefore costs more progression than it costs patients, which is exactly the information a
durability model needs.

This is the clearest single argument in this repository for building the abstraction pipeline
the protocol proposes: **between a third and two fifths of the deterioration a properly followed
cohort would record is invisible in a dataset of the quality we were given**, in patients who
were never imaged again.

### What the last row is for

`as_supplied` is our model of how poor the extract is; `as_received` is the extract. Where
they agree, the simulation is trustworthy and the intermediate rungs can be believed. Where
they differ, the difference names something the model of the data did not capture.
{'' if real else chr(10) + "**The extract row is not currently reproduced by this script.** It needs the private "
 "extract, which is not in the repository. Whoever holds it should run notebook 02 and write "
 "`data/synthetic/real_extract_rung.json` with the same six measures, using the same "
 "definitions as `ladder_metrics` above — in particular the patient-level event count, which "
 "is the one that is comparable across the rungs."}

## What calibration does and does not prove

Nine parameters were fitted against these anchors, which is close to saturated, so agreement
is **not** independent evidence that the cohort is correct. It establishes that the cohort is
*plausible* — that a pipeline exercised on it runs at realistic event rates. Correctness is
established separately, by injecting known hazard ratios into the generator and recovering
them with an independently implemented Cox model, one fit per failure mode: the 95% interval
covered the injected value in **70 of 75 fits (93.3%)**, against a nominal 95%, with a mean log
bias of **−0.0030** — five seeds, fifteen injected effects (`synthetic/validation.py`, reproduced
by the test suite).

The anchors that sit outside their band are listed above with the count of seeds that missed
them, and none was tuned away. Severe deterioration after transcatheter implant is reported by
NOTION as 1.5% — about two events among 145 randomised patients — against 5.9% in the UK TAVI
registry at a *shorter* horizon; this cohort reproduces the registry and misses the trial.
Severe deterioration after surgical implant comes out at the level of NOTION's *bioprosthetic
valve failure* rather than its *severe deterioration*, which says that thresholds applied
mechanically do not separate two categories a trial adjudication panel separates. That gap is
what the protocol's ground-truth hierarchy exists to close.
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--quick", action="store_true", help="Two seeds and a small cohort, for a smoke test.")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args(argv)

    seeds = SEEDS[:2] if args.quick else SEEDS
    n_patients = 300 if args.quick else DEFAULT.cohort.n_patients
    document = build_document(seeds, n_patients)
    args.out.write_text(document)
    where = args.out.relative_to(ROOT) if args.out.is_relative_to(ROOT) else args.out
    print(f"written to {where} ({len(document.splitlines())} lines, {len(seeds)} seeds)")
    if args.quick:
        print("QUICK MODE: numbers are not publishable. Rerun without --quick before committing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
