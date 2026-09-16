"""Is a risk-guided surveillance schedule worth using, and at what threshold?

An AUC says the model ranks patients. It does not say whether acting on the ranking
is better than what the clinic does today, and it cannot choose the risk above which
a patient should be scanned more often. Decision-curve analysis answers both, in the
one unit that matters here: how many deteriorations are caught per hundred patients,
after paying for the extra examinations at the exchange rate the threshold implies.

Net benefit at threshold *p* is

    NB(p) = TP/n − (FP/n) · p/(1 − p)

where the true and false positives are counted at the reporting horizon under the
competing risk of death, so a patient who dies before deteriorating is not scored as
a deterioration the model missed. The comparators are the two policies that need no
model: scan everyone on the guideline calendar (*all*), and scan no one earlier than
routine (*none*). A model is worth deploying over the range of thresholds where its
curve is above both.

The threshold is a clinical statement, not a statistical one: *p* = 0.10 means a
clinician is willing to bring forward ten examinations to catch one deterioration.
This script reports the curve; choosing the operating point on it belongs to the
clinical lead.

Synthetic cohort only, no private data.

Run from the repository root::

    uv run python scripts/08_decision_curve.py            # ~5 minutes
    uv run python scripts/08_decision_curve.py --quick
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "notebooks"))

from pipeline import landmarks, ml  # noqa: E402
from synthetic import generate  # noqa: E402

OUT_MD = ROOT / "model" / "decision_curve.md"
OUT_CSV = ROOT / "data" / "processed" / "decision_curve.csv"

SEEDS = (20260917, 1, 2, 3, 4)
N_PATIENTS = 3000
SPLIT_YEAR = 2018
HORIZON = 5
TIERS = (0.05, 0.15)
"""The tier boundaries `approach.md` currently uses. They are forced into the grid
below so the decision this analysis exists to inform can be read off the table
directly rather than interpolated."""

THRESHOLDS = tuple(sorted(set(np.round(np.arange(0.02, 0.51, 0.02), 2)) | set(TIERS)))


def net_benefit(predicted: pd.Series, time_to_end: pd.Series, status: pd.Series,
                horizon: int, threshold: float) -> float:
    """Net benefit of acting on ``predicted >= threshold``, with death competing.

    The flagged group's true-positive rate is its cumulative incidence of
    deterioration by the horizon, estimated by Aalen–Johansen so that patients who
    die first are neither counted as events nor dropped as if they had never been at
    risk. Everything is expressed per patient in the whole cohort, which is what
    makes the curves comparable with "scan everyone" and "scan no one".
    """
    flagged = (predicted >= threshold).to_numpy()
    if not flagged.any():
        return 0.0
    share_flagged = flagged.mean()
    incidence = ml.aalen_johansen(time_to_end[flagged], status[flagged], horizon)
    true_positives = share_flagged * incidence
    false_positives = share_flagged * (1 - incidence)
    return true_positives - false_positives * threshold / (1 - threshold)


def evaluate(seed: int, n_patients: int) -> pd.DataFrame:
    tables = landmarks.from_preprocessing(
        landmarks.synthetic_to_preprocessing(generate("ideal", seed=seed, n_patients=n_patients))
    )
    landmark, _ = landmarks.build_landmark_table(tables, landmarks.LABEL_CONFIG)
    X, meta = ml.feature_matrix(landmark)
    train = meta.implant_year.le(SPLIT_YEAR).to_numpy()
    test = ~train
    priors = [f for f in X.columns if ml.FEATURES[f]["prior"]]

    models = {
        "regression baseline": ml.DiscreteTimeCompetingRisks(priors, kind="logit", horizon=8),
        "gradient boosting": ml.DiscreteTimeCompetingRisks(list(X.columns), kind="gbm", horizon=8),
        "valve age only": ml.DiscreteTimeCompetingRisks(["landmark_years"], kind="gbm", horizon=8),
    }
    time_to_end, status = meta.time_to_end[test], meta.status[test]
    overall = ml.aalen_johansen(time_to_end, status, HORIZON)

    rows = []
    for name, model in models.items():
        predicted = model.fit(X[train], meta[train]).predict_cif(X[test])[f"svd_{HORIZON}y"]
        for threshold in THRESHOLDS:
            rows.append({
                "seed": seed, "model": name, "threshold": threshold,
                "net_benefit": net_benefit(predicted, time_to_end, status, HORIZON, threshold),
                "share_flagged": float((predicted >= threshold).mean()),
            })
    for threshold in THRESHOLDS:
        rows.append({
            "seed": seed, "model": "scan everyone", "threshold": threshold,
            "net_benefit": overall - (1 - overall) * threshold / (1 - threshold),
            "share_flagged": 1.0,
        })
        rows.append({"seed": seed, "model": "scan no one", "threshold": threshold,
                     "net_benefit": 0.0, "share_flagged": 0.0})
    return pd.DataFrame(rows)


def render(curve: pd.DataFrame, minutes: float, n_patients: int) -> str:
    mean = curve.groupby(["model", "threshold"]).net_benefit.mean().unstack("model")
    flagged = curve.groupby(["model", "threshold"]).share_flagged.mean().unstack("model")
    models = [c for c in mean.columns if c not in ("scan everyone", "scan no one")]
    best = mean[models].idxmax(axis=1)

    header = " | ".join(mean.columns)
    lines = [f"| threshold | {header} | best | flagged by the best |", "|---" * (len(mean.columns) + 3) + "|"]
    for threshold, row in mean.iterrows():
        winner = best[threshold]
        cells = " | ".join(f"{row[c]:+.4f}" for c in mean.columns)
        lines.append(f"| {threshold:.0%} | {cells} | {winner} | {flagged.loc[threshold, winner]:.0%} |")
    table = "\n".join(lines)

    useful = mean.index[(mean[models].max(axis=1) > mean["scan everyone"]) &
                        (mean[models].max(axis=1) > 0)]
    if len(useful):
        lower, upper = useful.min(), useful.max()
        top = "the top of the range examined" if upper >= max(THRESHOLDS) else f"{upper:.0%}"
        tier_lines = ["| threshold | policy it replaces | best model | extra true positives per 100 | patients flagged |",
                      "|---|---|---|---|---|"]
        for tier in TIERS:
            if tier not in mean.index:
                continue
            winner = best[tier]
            reference = max(mean.loc[tier, "scan everyone"], 0.0)
            replaced = "scan everyone" if mean.loc[tier, "scan everyone"] > 0 else "change nothing"
            tier_lines.append(
                f"| {tier:.0%} | {replaced} | {winner} | {(mean.loc[tier, winner] - reference) * 100:+.2f} "
                f"| {flagged.loc[tier, winner]:.0%} |"
            )
        verdict = (
            f"**A risk-guided schedule beats both model-free policies from {lower:.0%} up to {top}.** "
            f"Below {lower:.0%} the honest advice is to scan everyone: a clinician that averse to a "
            f"missed deterioration should not be filtering patients at all.\n\n"
            "At the two tier boundaries `approach.md` currently uses:\n\n"
            + "\n".join(tier_lines)
            + "\n\nRead each row as a statement about willingness: at a threshold of *p*, a clinician "
              f"is bringing forward about {(1 - TIERS[0]) / TIERS[0]:.0f} examinations per deterioration "
              f"caught at {TIERS[0]:.0%}, and about {(1 - TIERS[-1]) / TIERS[-1]:.0f} at {TIERS[-1]:.0%}."
        )
    else:
        verdict = (
            "**No threshold in the range examined puts any model above both model-free policies.** "
            "That is a result, not a bug: at this event rate and this level of discrimination, a "
            "risk-guided schedule cannot be justified by net benefit alone, and the honest "
            "recommendation is to keep the guideline calendar until the model is recalibrated."
        )

    return f"""# Decision curve: is the model worth acting on?

> Generated by `scripts/08_decision_curve.py` on {date.today().isoformat()} in {minutes:.0f} min;
> {len(SEEDS)} synthetic cohorts of {n_patients:,} patients, mean across seeds. Synthetic data only.
> No value here came from a patient.

## What this answers

`approach.md` maps predicted risk to a surveillance interval through three tiers, and says the
thresholds are provisional until a decision curve is run. This is that curve.

Net benefit at threshold *p* is the true-positive rate minus the false-positive rate weighted by
*p*/(1 − *p*), counted at {HORIZON} years with death as a competing risk, and expressed per patient
in the whole cohort. The weight is the exchange rate the threshold implies: at *p* = 10% a
clinician is saying that nine unnecessary examinations are worth one deterioration caught. The two
comparators need no model — scan everyone, or change nothing — and a model is only worth deploying
where it is above both.

## The curve

{table}

## What it says

{verdict}

**The threshold is a clinical decision and stays with the clinical lead.** This document supplies
the exchange rate at each candidate threshold and what it buys; it does not choose one. What it
does settle is the shape of the answer: there is a bounded window of thresholds in which a
risk-guided schedule beats both scanning everyone and changing nothing, and a tier boundary chosen
outside that window is worse than the policy it replaces, however good the model's AUC.

## Caveats

Run on the `ideal` rung of the degradation ladder, so it describes a clinic with dated serial
echocardiography, not the supplied extract. The valve-age-only curve is a step function — it has
one predictor with a handful of distinct values — so averaging it across cohorts produces a jagged
line, and where it wins by a hair at a single threshold that is arithmetic, not a finding. The models over-predict absolute risk (see
[`stability.md`](stability.md) and [`../protocol/sample_size.md`](../protocol/sample_size.md)), and
a decision curve is read off absolute risk, so the thresholds here will move once recalibration is
in the pipeline. Rerun this script after that change before any threshold is fixed.
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--out", type=Path, default=OUT_MD)
    args = parser.parse_args(argv)

    seeds = SEEDS[:2] if args.quick else SEEDS
    n_patients = 800 if args.quick else N_PATIENTS
    started = time.time()
    frames = []
    for seed in seeds:
        t0 = time.time()
        frames.append(evaluate(seed, n_patients))
        print(f"seed {seed}: {time.time() - t0:.0f}s", flush=True)
    curve = pd.concat(frames, ignore_index=True)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    curve.to_csv(OUT_CSV, index=False)
    args.out.write_text(render(curve, (time.time() - started) / 60, n_patients))
    where = args.out.relative_to(ROOT) if args.out.is_relative_to(ROOT) else args.out
    print(f"written to {where}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
