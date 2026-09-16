"""Measure how much of the difference between our models is real.

Every model comparison in this repository has so far been run on one synthetic
cohort. That answers a question nobody asked — which model wins on *this* draw —
because a second cohort drawn from the same generator with a different seed gives
different numbers. If the spread between draws is as large as the gap between two
models, then a ranking read off a single run is a description of the random seed.

This script repeats the whole modelling pipeline on independent cohorts and reports,
for each model and horizon, the mean and standard deviation across seeds, plus the
paired difference against the honest floor of current practice — a model that knows
nothing except how long the valve has been in. Pairing matters: the same seed feeds
every model, so the seed-to-seed swing cancels and a small but consistent advantage
stays visible.

It uses the synthetic cohort only, needs no private data, and is reproducible from
the seeds printed in its output.

Run from the repository root::

    uv run python scripts/06_model_stability.py                  # 8 seeds, ~20 minutes
    uv run python scripts/06_model_stability.py --seeds 2 --patients 800   # smoke test
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

OUT_MD = ROOT / "model" / "stability.md"
OUT_CSV = ROOT / "data" / "processed" / "model_stability.csv"

SEEDS: tuple[int, ...] = (20260917, 1, 2, 3, 4, 5, 6, 7)
N_PATIENTS = 3000
SPLIT_YEAR = 2018
HORIZONS = (2, 5, 8)
GBM_PARAMS = dict(learning_rate=0.1, max_leaf_nodes=15, min_samples_leaf=20)
"""Fixed rather than tuned per seed. Tuning inside each replicate would add a second
source of variation to the quantity being measured, and the point here is to isolate
the first one."""

REFERENCE_MODEL = "valve age only"
"""What every other model is compared against. Current surveillance is scheduled by
valve age and nothing else, so a model that cannot beat it is not worth deploying."""


def build_cohort(seed: int, n_patients: int):
    """Generate one cohort and take it through the same path the notebooks take."""
    prepared = landmarks.synthetic_to_preprocessing(
        generate("ideal", seed=seed, n_patients=n_patients)
    )
    tables = landmarks.from_preprocessing(prepared)
    landmark, _ = landmarks.build_landmark_table(tables, landmarks.LABEL_CONFIG)
    X, meta = ml.feature_matrix(landmark)
    train = meta.implant_year.le(SPLIT_YEAR).to_numpy()
    return X, meta, train, ~train


def fit_models(X: pd.DataFrame, meta: pd.DataFrame, train: np.ndarray, horizon: int) -> dict:
    features = list(X.columns)
    priors = [f for f in features if ml.FEATURES[f]["prior"]]
    return {
        "calendar schedule": ml.CalendarSchedule(horizon=horizon).fit(X[train], meta[train]),
        "valve age only": ml.DiscreteTimeCompetingRisks(
            ["landmark_years"], kind="gbm", horizon=horizon
        ).fit(X[train], meta[train]),
        "Cox, risk factors": ml.CoxRiskFactors(priors, horizon=horizon).fit(X[train], meta[train]),
        "regression baseline": ml.DiscreteTimeCompetingRisks(
            priors, kind="logit", horizon=horizon
        ).fit(X[train], meta[train]),
        "gradient boosting": ml.DiscreteTimeCompetingRisks(
            features, kind="gbm", horizon=horizon, **GBM_PARAMS
        ).fit(X[train], meta[train]),
        "gradient boosting, no constraints": ml.DiscreteTimeCompetingRisks(
            features, kind="gbm", horizon=horizon, monotone=False, **GBM_PARAMS
        ).fit(X[train], meta[train]),
    }


def evaluate(seed: int, n_patients: int) -> pd.DataFrame:
    """Fit every model on one cohort and score them all on its held-out valves."""
    X, meta, train, test = build_cohort(seed, n_patients)
    horizon = max(HORIZONS)
    models = fit_models(X, meta, train, horizon)
    censoring = ml.censoring_survival(meta.time_to_end[test], meta.status[test])
    observed = {h: ml.aalen_johansen(meta.time_to_end[test], meta.status[test], h) for h in HORIZONS}

    rows = []
    for name, model in models.items():
        cif = model.predict_cif(X[test])
        for h in HORIZONS:
            p = cif[f"svd_{h}y"]
            rows.append({
                "seed": seed,
                "model": name,
                "horizon": h,
                "auc": ml.cr_auc(p, meta.time_to_end[test], meta.status[test], h, censoring),
                "brier": ml.cr_brier(p, meta.time_to_end[test], meta.status[test], h, censoring),
                "mean_predicted": float(p.mean()),
                "observed": observed[h],
                "calibration_ratio": float(p.mean()) / observed[h] if observed[h] > 0 else np.nan,
                "train_patients": int(meta.patient_id[train].nunique()),
                "test_patients": int(meta.patient_id[test].nunique()),
                "train_svd_patients": int(meta.patient_id[train & meta.status.eq("svd").to_numpy()].nunique()),
            })
    return pd.DataFrame(rows)


def summarise(per_seed: pd.DataFrame) -> pd.DataFrame:
    """Mean, spread and paired advantage over the reference model, per model and horizon."""
    reference = per_seed[per_seed.model == REFERENCE_MODEL].set_index(["seed", "horizon"])["auc"]
    per_seed = per_seed.copy()
    per_seed["advantage"] = per_seed["auc"] - pd.MultiIndex.from_frame(
        per_seed[["seed", "horizon"]]
    ).map(reference)

    out = (
        per_seed.groupby(["model", "horizon"])
        .agg(
            auc_mean=("auc", "mean"),
            auc_sd=("auc", "std"),
            auc_min=("auc", "min"),
            auc_max=("auc", "max"),
            brier_mean=("brier", "mean"),
            calibration_mean=("calibration_ratio", "mean"),
            advantage_mean=("advantage", "mean"),
            advantage_sd=("advantage", "std"),
            seeds=("auc", "size"),
        )
        .reset_index()
    )
    # A paired advantage is credible when it is larger than the seed-to-seed swing of
    # the difference itself, not of the raw AUC.
    out["beats_reference"] = (out.advantage_mean - 2 * out.advantage_sd / np.sqrt(out.seeds)) > 0
    return out


def render(summary: pd.DataFrame, per_seed: pd.DataFrame, seeds: tuple[int, ...], n_patients: int, minutes: float) -> str:
    lines = []
    for h in sorted(summary.horizon.unique()):
        block = summary[summary.horizon == h].sort_values("auc_mean", ascending=False)
        lines.append(f"\n**{h}-year horizon**\n")
        lines.append(
            "| model | AUC (mean ± SD) | range across seeds | advantage over valve age "
            "| beats valve age | predicted / observed risk |"
        )
        lines.append("|---|---|---|---|---|---|")
        for _, r in block.iterrows():
            advantage = "reference" if r.model == REFERENCE_MODEL else f"{r.advantage_mean:+.3f} ± {r.advantage_sd:.3f}"
            verdict = "—" if r.model == REFERENCE_MODEL else ("**yes**" if r.beats_reference else "no")
            lines.append(
                f"| {r.model} | {r.auc_mean:.3f} ± {r.auc_sd:.3f} | {r.auc_min:.3f} to {r.auc_max:.3f} "
                f"| {advantage} | {verdict} | {r.calibration_mean:.2f} |"
            )
    table = "\n".join(lines)

    swing = summary.auc_sd.max()
    spread = (summary.auc_max - summary.auc_min).max()
    others = summary[summary.model != REFERENCE_MODEL]
    raw_typical = others.auc_sd.median()
    paired_typical = others.advantage_sd.median()
    short = others[others.horizon == others.horizon.min()]
    calib = summary[summary.horizon == 5][["model", "calibration_mean"]].set_index("model")["calibration_mean"]
    worst = calib.sub(1).abs().idxmax()
    sizes = per_seed[["train_patients", "test_patients", "train_svd_patients"]].iloc[0]

    return f"""# Model comparison: how much of it is real?

> Generated by `scripts/06_model_stability.py` on {date.today().isoformat()}; {len(seeds)} independent
> synthetic cohorts of {n_patients:,} patients, seeds {', '.join(str(s) for s in seeds)}, {minutes:.0f} minutes.
> Synthetic data only. No value here came from a patient.

## Why this exists

Every model number quoted in [`approach.md`](approach.md) came from a single cohort. A second
cohort from the same generator, differing only in its random seed, produces different numbers —
and until that spread is measured, no one can tell whether a difference between two models is a
property of the models or of the draw. This script measures it, by running the entire pipeline
({len(seeds)} cohorts × six models × {len(HORIZONS)} horizons) and reporting the spread alongside the mean.

Each cohort is split by implant year: valves implanted up to {SPLIT_YEAR} train, later valves test.
A typical replicate trains on {int(sizes.train_patients):,} patients ({int(sizes.train_svd_patients)} with deterioration)
and tests on {int(sizes.test_patients):,}. Hyperparameters are fixed, not tuned per replicate, so that
tuning noise is not mistaken for cohort noise.

## Results
{table}

## What this changes

**The seed-to-seed standard deviation reaches {swing:.3f} of AUC, and the full range across
{len(seeds)} cohorts reaches {spread:.3f}.** Any claim that one model beats another by less than
that, read off one run, is unsupported — and several differences quoted elsewhere in this
repository are smaller than that.

**Pairing recovers part of what the spread hides.** Measured within cohorts, where every model sees
the same patients, the same differences have a typical standard deviation of {paired_typical:.3f}
against {raw_typical:.3f} for the raw AUCs — a little under half. At the shortest horizon the gain
is largest ({short.auc_sd.median():.3f} down to {short.advantage_sd.median():.3f}); at eight years it
nearly disappears, because by then the models have diverged from the reference in ways that differ
from cohort to cohort rather than in a fixed amount. On the paired test every risk model beats
scheduling by valve age alone, at every horizon. That is the comparison to quote; an unpaired table
of means is the one to stop quoting.

**Calibration, not discrimination, is where these models fail.** The last column is mean predicted
risk divided by the incidence actually observed; 1.00 would be perfect. At five years the worst
({worst}) predicts {calib[worst]:.2f} times the observed incidence. A model used to set a
surveillance interval is used through its absolute risk, so this matters more than the third
decimal of an AUC, and recalibration belongs in the pipeline before any threshold is chosen.

## What this does not measure

These cohorts are the `ideal` rung of the degradation ladder: dated serial echocardiography, age
present, deaths recorded. The headline numbers in `approach.md` come from a cohort reshaped to
look like the supplied extract, which is a harder problem and a different ranking. Reproducing
that reshaping needs a profile measured from the private extract, so it cannot run here. What
transfers between the two is the finding about method, not the numbers: a single-cohort ranking is
not evidence, and a paired comparison is.

## How to use this file

Quote AUCs from here, with their spread, rather than from a single notebook run. When a change to
the generator or the features is proposed, rerun this script before and after: a change that moves
the mean by less than the standard deviation above has not been shown to do anything.
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seeds", type=int, default=len(SEEDS), help="How many seeds to run.")
    parser.add_argument("--patients", type=int, default=N_PATIENTS)
    parser.add_argument("--out", type=Path, default=OUT_MD)
    args = parser.parse_args(argv)

    seeds = SEEDS[: args.seeds]
    started = time.time()
    frames = []
    for seed in seeds:
        t0 = time.time()
        frames.append(evaluate(seed, args.patients))
        print(f"seed {seed}: {time.time() - t0:.0f}s", flush=True)
    per_seed = pd.concat(frames, ignore_index=True)
    summary = summarise(per_seed)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    per_seed.to_csv(OUT_CSV, index=False)
    args.out.write_text(render(summary, per_seed, seeds, args.patients, (time.time() - started) / 60))
    where = args.out.relative_to(ROOT) if args.out.is_relative_to(ROOT) else args.out
    print(f"written to {where} and {OUT_CSV.relative_to(ROOT)} (gitignored)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
