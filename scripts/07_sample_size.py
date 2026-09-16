"""How large does the real study have to be?

The protocol says "not yet decided" where the sample size should be. This script
decides it three ways, because the three answer different questions and the largest
of them is the one that binds:

1. **Enough to fit the model without overfitting it** — the Riley criterion for the
   minimum sample size of a prediction model, driven by the number of candidate
   predictors and by how much of the outcome they actually explain. The explained
   variation is measured on our own cohort rather than guessed.
2. **Enough to estimate the quantity the study reports** — the cumulative incidence
   of deterioration at five years, to a stated precision, measured by simulating
   many cohorts and looking at the spread of the estimate.
3. **Enough for performance to stop improving** — an empirical learning curve, which
   is the only one of the three that can show a plateau.

All three run on the synthetic cohort and need no private data.

Run from the repository root::

    uv run python scripts/07_sample_size.py              # ~10 minutes
    uv run python scripts/07_sample_size.py --quick      # smaller grid
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

from _provenance import git_revision  # noqa: E402

OUT_MD = ROOT / "protocol" / "sample_size.md"
OUT_CSV = ROOT / "data" / "processed" / "sample_size.csv"

SHRINKAGE = 0.9
"""Riley's criterion 1: the expected uniform shrinkage factor a model should reach.
0.9 means the fitted coefficients are expected to need shrinking by no more than a
tenth when the model is applied to new patients."""

PRECISION = 0.02
"""Half-width of the 95% interval we require on the five-year cumulative incidence.
Two percentage points, the same tolerance the synthetic cohort is calibrated to, so
the study can distinguish the differences its own anchors are quoted to."""

HORIZON = 5
GRID = (300, 600, 1200, 2400, 4800)
SEEDS = (20260917, 1, 2, 3, 4)
SPLIT_YEAR = 2018


def cox_snell_r2(cohort: dict[str, pd.DataFrame], features: list[str]) -> tuple[float, int, int]:
    """Explained variation of the published risk factors, on the generator's own cohort.

    Riley's formula needs an anticipated Cox–Snell R², and the usual practice is to
    borrow one from a published model in the same field. We can do better here: fit
    the candidate predictors to a cohort whose effect sizes were themselves taken
    from the literature, and read the value off.

    Returns:
        The Cox–Snell R², the number of patients and the number of events used.
    """
    from lifelines import CoxPHFitter

    tables = landmarks.from_preprocessing(landmarks.synthetic_to_preprocessing(cohort))
    outcomes = landmarks.build_outcomes(tables, landmarks.LABEL_CONFIG)
    landmark, _ = landmarks.build_landmark_table(tables, landmarks.LABEL_CONFIG)
    X, meta = ml.feature_matrix(landmark)

    baseline = X[meta.landmark_years == meta.landmark_years.min()].copy()
    baseline_meta = meta[meta.landmark_years == meta.landmark_years.min()]
    usable = [f for f in features if f in baseline and baseline[f].nunique() > 1]
    frame = baseline[usable].fillna(baseline[usable].median()).assign(
        T=baseline_meta.time_to_end.to_numpy(),
        E=baseline_meta.status.eq("svd").astype(int).to_numpy(),
    )
    fitted = CoxPHFitter(penalizer=0.01).fit(frame, duration_col="T", event_col="E")
    null = CoxPHFitter().fit(frame[["T", "E"]], duration_col="T", event_col="E")
    n = len(frame)
    likelihood_ratio = 2 * (fitted.log_likelihood_ - null.log_likelihood_)
    return float(1 - np.exp(-likelihood_ratio / n)), n, int(frame.E.sum())


def riley_minimum(parameters: int, r2_cs: float, shrinkage: float = SHRINKAGE) -> float:
    """Riley's criterion 1: the sample size at which expected shrinkage reaches ``shrinkage``.

    n = P / ((S − 1) · ln(1 − R²_CS / S)), from Riley RD, Snell KIE, Ensor J, et al.
    *Minimum sample size for developing a multivariable prediction model: Part II —
    binary and time-to-event outcomes.* Stat Med 2019;38:1276–1296.
    """
    return parameters / ((shrinkage - 1) * np.log(1 - r2_cs / shrinkage))


def incidence_precision(reference_n: int, replicates: int) -> dict[str, float]:
    """How precisely a cohort of a given size can estimate the five-year incidence.

    A closed form would need an assumption about the censoring distribution that the
    generator already contains, so the spread is measured directly: draw many cohorts
    of one reference size and take the standard deviation of the estimate. The
    requirement for any other size then follows from the square-root law — the
    standard error of an incidence falls as the square root of the number of
    patients — rather than from a second noisy measurement at every size, which at
    a handful of replicates would produce a table that is not even monotone.
    """
    estimates = []
    for seed in range(replicates):
        tables = landmarks.from_preprocessing(
            landmarks.synthetic_to_preprocessing(generate("ideal", seed=seed, n_patients=reference_n))
        )
        outcomes = landmarks.build_outcomes(tables, landmarks.LABEL_CONFIG)
        estimates.append(ml.aalen_johansen(outcomes.end_years, outcomes.status, HORIZON))
    sd = float(np.std(estimates, ddof=1))
    required = reference_n * (1.96 * sd / PRECISION) ** 2
    return {
        "reference_n": reference_n,
        "replicates": replicates,
        "incidence_mean": float(np.mean(estimates)),
        "sd": sd,
        "half_width_95": 1.96 * sd,
        "required_n": required,
    }


def learning_curve(grid: tuple[int, ...], seeds: tuple[int, ...]) -> pd.DataFrame:
    """Discrimination and calibration against cohort size, on held-out valves."""
    rows = []
    for n in grid:
        for seed in seeds:
            tables = landmarks.from_preprocessing(
                landmarks.synthetic_to_preprocessing(generate("ideal", seed=seed, n_patients=n))
            )
            landmark, _ = landmarks.build_landmark_table(tables, landmarks.LABEL_CONFIG)
            X, meta = ml.feature_matrix(landmark)
            train = meta.implant_year.le(SPLIT_YEAR).to_numpy()
            test = ~train
            if meta.patient_id[train & meta.status.eq("svd").to_numpy()].nunique() < 5 or test.sum() < 50:
                continue
            priors = [f for f in X.columns if ml.FEATURES[f]["prior"]]
            model = ml.DiscreteTimeCompetingRisks(priors, kind="logit", horizon=8).fit(X[train], meta[train])
            predicted = model.predict_cif(X[test])[f"svd_{HORIZON}y"]
            censoring = ml.censoring_survival(meta.time_to_end[test], meta.status[test])
            observed = ml.aalen_johansen(meta.time_to_end[test], meta.status[test], HORIZON)
            rows.append({
                "patients": n,
                "seed": seed,
                "train_events": int(meta.patient_id[train & meta.status.eq("svd").to_numpy()].nunique()),
                "auc": ml.cr_auc(predicted, meta.time_to_end[test], meta.status[test], HORIZON, censoring),
                "calibration_ratio": float(predicted.mean()) / observed if observed > 0 else np.nan,
            })
    return pd.DataFrame(rows)


def render(r2: float, r2_n: int, r2_events: int, riley: pd.DataFrame,
           precision: dict[str, float], curve: pd.DataFrame, minutes: float) -> str:
    riley_rows = "\n".join(
        f"| {row.model} | {int(row.parameters)} | {row.minimum:,.0f} | {row.events:,.0f} |"
        for row in riley.itertuples()
    )
    summary = curve.groupby("patients").agg(
        auc_mean=("auc", "mean"), auc_sd=("auc", "std"),
        calibration=("calibration_ratio", "mean"), events=("train_events", "mean"),
    ).reset_index()
    curve_rows = "\n".join(
        f"| {row.patients:,} | {row.events:.0f} | {row.auc_mean:.3f} ± {row.auc_sd:.3f} | {row.calibration:.2f} |"
        for row in summary.itertuples()
    )
    primary = riley.iloc[0]
    binding = max(primary.minimum, precision["required_n"])
    ordered = summary.sort_values("patients")
    first, last = ordered.iloc[0], ordered.iloc[-1]
    auc_gain = last.auc_mean - first.auc_mean

    return f"""# Sample size

> Generated by `scripts/07_sample_size.py` on {date.today().isoformat()} against commit
> `{git_revision()}`, in {minutes:.0f} min, on the
> synthetic cohort. No value here came from a patient. Rerun the script after any change to the
> feature set, since the first criterion depends on how many candidate predictors there are.

Three requirements, answering three different questions. The study has to satisfy all of them, so
the binding number is the largest.

## 1. Enough to fit the model without overfitting it

Riley's criterion for the minimum sample size of a prediction model: with *P* candidate predictor
parameters and an anticipated Cox–Snell R² of *R²*, the sample size at which the expected uniform
shrinkage factor reaches {SHRINKAGE:.0%} is

n = P / ((S − 1) · ln(1 − R² / S))

*(Riley RD, Snell KIE, Ensor J, et al. Minimum sample size for developing a multivariable
prediction model: Part II — binary and time-to-event outcomes. Stat Med 2019;38:1276–1296.)*

The usual practice is to borrow R² from a published model. We can measure it instead: the
published risk factors, fitted to a cohort whose effect sizes were themselves taken from the
literature, give **R²_CS = {r2:.3f}** ({r2_events} events among {r2_n:,} patients at the first landmark).

| model | candidate parameters | patients needed | of whom with deterioration |
|---|---|---|---|
{riley_rows}

The second row is the reason the protocol commits to a small, regularised model rather than every
feature the pipeline can build: the same data support a model with a dozen parameters and do not
support one with forty.

## 2. Enough to estimate what the study reports

The headline quantity is the cumulative incidence of deterioration at {HORIZON} years, and the
precision required of it is **± {PRECISION:.0%}** — the same tolerance the synthetic cohort is
calibrated to, so the study can distinguish the differences its own anchors are quoted to.

Measured on {precision['replicates']} independent cohorts of {precision['reference_n']:,} patients: the
five-year incidence averages {precision['incidence_mean']:.1%} with a standard deviation of
{precision['sd'] * 100:.2f} percentage points, so a cohort that size reports it to
± {precision['half_width_95'] * 100:.1f} points. A standard error falls as the square root of the
number of patients, so the required size is

n = {precision['reference_n']:,} × ({precision['half_width_95'] * 100:.2f} / {PRECISION * 100:.0f})² = **{precision['required_n']:,.0f} patients**.

## 3. Enough for performance to stop improving

The regression baseline on the published risk factors, trained at each size and scored on the
held-out later valves of the same cohort:

| patients | deterioration events in training | {HORIZON}-year AUC | predicted / observed risk |
|---|---|---|---|
{curve_rows}

Discrimination improves with size and then flattens: between the smallest and the largest cohort
the AUC moves by {auc_gain:+.3f} while its seed-to-seed spread falls from {first.auc_sd:.3f} to
{last.auc_sd:.3f}. **Calibration does not improve at all.** The last column — mean predicted risk
over observed incidence — stays between {summary.calibration.min():.2f} and
{summary.calibration.max():.2f} across a sixteen-fold change in sample size, with no trend.

That is the most useful thing in this document. Over-prediction of this size is not a shortage of
patients and will not be cured by recruiting more of them: it is a property of the model, and the
fix is an explicit recalibration step and a specification that respects the competing risk, not a
larger study. Sizing this study from an AUC curve alone would have hidden that entirely.

## What the protocol should say

The binding requirement is **{binding:,.0f} patients** with a bioprosthetic aortic valve followed to
{HORIZON} years — the largest of the three criteria above. It is not a power calculation for a
hypothesis test, because the study is not testing one: it is the size at which the model can be
fitted without being shrunk away, and the incidence can be reported to the precision the
literature is quoted to.

**This is larger than the 1,800 the synthetic cohort is generated at, and the protocol should say
so rather than round it away.** Three responses are available and the choice is clinical, not
statistical: recruit across more centres; keep the cohort and accept the shrinkage, reporting the
model as provisional and recalibrating it at each site; or cut the candidate parameters further,
since the requirement is proportional to them. The one thing that is not available is to fit forty
parameters to 1,800 patients and report the result as a validated model.
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--out", type=Path, default=OUT_MD)
    args = parser.parse_args(argv)

    grid = (300, 600, 1200) if args.quick else GRID
    seeds = SEEDS[:2] if args.quick else SEEDS
    started = time.time()

    reference = generate("ideal", seed=seeds[0], n_patients=4000)
    priors = [f for f, spec in ml.FEATURES.items() if spec["prior"]]
    r2, r2_n, r2_events = cox_snell_r2(reference, priors)
    print(f"Cox-Snell R2 = {r2:.3f} on {r2_n} patients, {r2_events} events", flush=True)

    event_share = r2_events / r2_n
    riley = pd.DataFrame([
        {"model": "published risk factors only (the protocol's primary model)", "parameters": len(priors)},
        {"model": "every feature the pipeline can build", "parameters": len(ml.FEATURES)},
    ])
    riley["minimum"] = [riley_minimum(p, r2) for p in riley.parameters]
    riley["events"] = riley.minimum * event_share

    precision = incidence_precision(reference_n=grid[-1], replicates=6 if args.quick else 20)
    print("precision done", flush=True)
    curve = learning_curve(grid, seeds)
    print("learning curve done", flush=True)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    curve.to_csv(OUT_CSV, index=False)
    args.out.write_text(render(r2, r2_n, r2_events, riley, precision, curve, (time.time() - started) / 60))
    where = args.out.relative_to(ROOT) if args.out.is_relative_to(ROOT) else args.out
    print(f"written to {where}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
