"""Calibration of the cohort against published durability evidence.

**What was fitted, and what that does and does not prove.** Nine parameters were
chosen using the anchors in :data:`synthetic.parameters.ANCHORS`: two Weibull
scales solved by bisection against the two NOTION moderate-or-severe figures, and
seven shape parameters governing onset, the rapidly progressive phenotype and
gradient progression, selected from small grids.

Nine parameters against seven anchors is a saturated fit, so **agreement with the
anchors is not independent evidence that the cohort is correct**. It establishes
only that the cohort is plausible: that it lands where published series land, so a
pipeline exercised on it runs at realistic event rates. The evidence of
correctness is the recovery test in :mod:`synthetic.validation`, which no amount
of curve-fitting can pass.

Bands come from one rule, fixed before any cohort existed and applied uniformly to
every anchor; see :attr:`synthetic.parameters.Anchor.tolerance`. Replacing the
earlier hand-picked bands with that rule dropped the cohort from six anchors
inside to three, which is what exposed the deficiency the two-component onset
model then fixed. A tolerance chosen per anchor is not a standard, it is a
description of the result.

**The published anchors contradict one another, so no cohort can satisfy all of
them.** NOTION reports severe deterioration in 10.0% of surgical and 1.5% of
transcatheter patients at ten years, against moderate-or-severe figures of 20.8%
and 15.4%. Those imply that 48% of deteriorated surgical valves become severe
within ten years but only 10% of transcatheter ones -- a five-fold difference in
progression *conditional on having deteriorated*, between two arms of one
randomised trial. Meanwhile the UK TAVI registry reports severe deterioration in
5.9% of transcatheter patients at a median of 7.8 years, roughly four times the
NOTION figure at a shorter horizon.

This cohort sides with the registry. It reproduces the UK TAVI figure closely and
misses the NOTION transcatheter severe figure, and that single miss is reported in
every calibration table rather than tuned away. The alternative -- a second
progression process fitted per arm -- would reproduce both numbers and would be
fitting the sampling noise of a trial with a few dozen transcatheter patients still
under echocardiographic follow-up at ten years.

Incidence is reported as an **Aalen-Johansen cumulative incidence function**, not
as one minus Kaplan-Meier. Under a competing risk, Kaplan-Meier answers the
question "what would the incidence be if nobody could die?", which for an elderly
valve population is not a question anyone needs answered, and it overstates
deterioration substantially.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .generator import DAYS_PER_YEAR, build_cohort
from .parameters import ANCHORS, Anchor, Parameters

__all__ = ["cumulative_incidence", "endpoint_times", "solve_scales", "calibration_report"]


@dataclass(frozen=True, slots=True)
class _Endpoint:
    """Per-patient outcome reduced to a time and a cause."""

    time_years: np.ndarray
    cause: np.ndarray
    """1 for the endpoint of interest, 2 for the competing death, 0 for censored."""


def endpoint_times(cohort: dict[str, pd.DataFrame], event_types: tuple[str, ...]) -> _Endpoint:
    """Reduce a cohort to time-to-first-event for a given endpoint definition.

    Whichever of the endpoint or death happens first is what the patient
    contributes; a patient censored before either contributes neither.

    Args:
        cohort: Tables as returned by :func:`synthetic.generator.build_cohort`.
        event_types: Event types that together constitute the endpoint, for
            example ``("svd_stage2", "svd_stage3")``.

    Returns:
        Times in years and causes, aligned with the ``patients`` table.
    """
    patients = cohort["patients"]
    events = cohort["events"]
    order = {pid: i for i, pid in enumerate(patients["patient_id"])}
    n = len(patients)

    endpoint_day = np.full(n, np.inf)
    death_day = np.full(n, np.inf)

    selected = events[events["event_type"].isin(event_types)]
    for pid, day in zip(selected["patient_id"], selected["days_from_implant"]):
        i = order[pid]
        endpoint_day[i] = min(endpoint_day[i], float(day))

    deaths = events[events["event_type"] == "death"]
    for pid, day in zip(deaths["patient_id"], deaths["days_from_implant"]):
        death_day[order[pid]] = float(day)

    censor_day = np.empty(n)
    followup = cohort["followup"]
    for pid, day in zip(followup["patient_id"], followup["last_contact_days"]):
        censor_day[order[pid]] = float(day)

    time = np.minimum(np.minimum(endpoint_day, death_day), censor_day)
    cause = np.where(endpoint_day <= time, 1, np.where(death_day <= time, 2, 0))
    return _Endpoint(time_years=time / DAYS_PER_YEAR, cause=cause)


def cumulative_incidence(endpoint: _Endpoint, horizon_years: float) -> float:
    """Aalen-Johansen cumulative incidence of cause 1 by ``horizon_years``.

    The estimator weights each cause-1 hazard increment by the probability of
    still being event-free just before it, so that patients removed by the
    competing cause cannot contribute incidence they never had the chance to
    experience.
    """
    order = np.argsort(endpoint.time_years, kind="mergesort")
    times = endpoint.time_years[order]
    causes = endpoint.cause[order]

    at_risk = len(times)
    survival = 1.0
    incidence = 0.0
    i = 0
    while i < len(times) and times[i] <= horizon_years:
        t = times[i]
        j = i
        while j < len(times) and times[j] == t:
            j += 1
        tied = causes[i:j]
        d1 = int((tied == 1).sum())
        d2 = int((tied == 2).sum())
        if at_risk > 0 and d1:
            incidence += survival * d1 / at_risk
        if at_risk > 0 and (d1 + d2):
            survival *= 1.0 - (d1 + d2) / at_risk
        at_risk -= j - i
        i = j
    return float(incidence)


_ENDPOINT_TYPES: dict[str, tuple[str, ...]] = {
    "moderate_or_severe_svd": ("svd_stage2", "svd_stage3"),
    "severe_svd": ("svd_stage3",),
    # VARC-3 bioprosthetic valve failure stage 2/3 is severe haemodynamic
    # deterioration OR reintervention OR valve-related death -- not reintervention
    # alone. Comparing a reintervention-only rate against the PARTNER 3 figure
    # would be comparing two different endpoints.
    "bioprosthetic_valve_failure": ("svd_stage3", "bvf_reintervention"),
}


def _subset(cohort: dict[str, pd.DataFrame], subgroup: str) -> dict[str, pd.DataFrame]:
    """Restrict a cohort to one approach, or return it unchanged for ``"all"``."""
    if subgroup == "all":
        return cohort
    keep = set(cohort["patients"].loc[cohort["patients"]["approach"] == subgroup, "patient_id"])
    return {name: frame[frame["patient_id"].isin(keep)] if "patient_id" in frame else frame for name, frame in cohort.items()}


def observed(cohort: dict[str, pd.DataFrame], anchor: Anchor) -> float:
    """Cumulative incidence in ``cohort`` corresponding to ``anchor``."""
    subset = _subset(cohort, anchor.subgroup)
    endpoint = endpoint_times(subset, _ENDPOINT_TYPES[anchor.quantity])
    return cumulative_incidence(endpoint, anchor.horizon_years)


def solve_scales(
    params: Parameters,
    *,
    seed: int = 20260917,
    n_solve: int = 20_000,
    tolerance: float = 0.0015,
    max_iterations: int = 40,
) -> tuple[float, float]:
    """Solve the two deterioration scales against the targeted anchors.

    The scales are solved on a cohort far larger than the study cohort, so that
    the solution is driven by the generating process rather than by Monte Carlo
    noise: at n = 1,800 the standard error of a 20% incidence is about 1
    percentage point, which is the size of the effect being solved for.

    Because a larger Weibull scale can only postpone onset, incidence is monotone
    decreasing in the scale, and bisection is guaranteed to converge.

    Args:
        params: Parameter set whose scales are to be replaced.
        seed: Seed used for every cohort drawn during the search. Holding it fixed
            makes the objective deterministic, which bisection requires.
        n_solve: Size of the cohort used for solving.
        tolerance: Convergence tolerance on cumulative incidence.
        max_iterations: Maximum bisection steps.

    Returns:
        The solved scales in years, for SAVR and TAVR respectively.
    """
    from dataclasses import replace as _replace

    targets = {a.subgroup: a.value for a in ANCHORS if a.targeted}
    horizon = {a.subgroup: a.horizon_years for a in ANCHORS if a.targeted}
    large = _replace(params, cohort=_replace(params.cohort, n_patients=n_solve))

    low = {"SAVR": 6.0, "TAVR": 6.0}
    high = {"SAVR": 60.0, "TAVR": 60.0}

    for _ in range(max_iterations):
        middle = {arm: 0.5 * (low[arm] + high[arm]) for arm in ("SAVR", "TAVR")}
        cohort = build_cohort(large.with_scales(middle["SAVR"], middle["TAVR"]), seed=seed)
        gap = {}
        for arm in ("SAVR", "TAVR"):
            subset = _subset(cohort, arm)
            value = cumulative_incidence(endpoint_times(subset, _ENDPOINT_TYPES["moderate_or_severe_svd"]), horizon[arm])
            gap[arm] = value - targets[arm]
            if gap[arm] > 0:
                low[arm] = middle[arm]      # too many events: postpone onset
            else:
                high[arm] = middle[arm]
        if all(abs(g) < tolerance for g in gap.values()):
            break

    return middle["SAVR"], middle["TAVR"]


def calibration_across_seeds(
    seeds: tuple[int, ...] = (20260917, 1, 2, 3, 4, 5, 6, 7),
    *,
    n_patients: int = 1800,
    params: Parameters | None = None,
) -> pd.DataFrame:
    """Repeat the calibration over several seeds and report the spread.

    A calibration table from a single cohort confounds two things: whether the
    generating process is right, and whether that particular draw was lucky. At
    1,800 patients the Monte Carlo standard error of a 20% incidence is around one
    percentage point, which is the size of the differences being judged. Reporting
    a mean and a standard deviation across seeds separates the two, and the count
    of seeds inside the band shows whether a verdict is stable or borderline.

    Args:
        seeds: Seeds to draw cohorts with.
        n_patients: Size of each cohort.
        params: Parameter set; defaults to the calibrated one.

    Returns:
        One row per anchor, with the published value, the mean and standard
        deviation across seeds, the range, and how many seeds fell inside the band.
    """
    from . import generate

    per_seed = [
        calibration_report(generate("ideal", seed=seed, n_patients=n_patients, params=params))
        for seed in seeds
    ]
    key = ["quantity", "subgroup", "horizon_years", "published", "targeted"]
    values = pd.concat([frame.set_index(key)["cohort"] for frame in per_seed], axis=1)
    inside = pd.concat([frame.set_index(key)["within_band"] for frame in per_seed], axis=1)
    summary = pd.DataFrame(
        {
            "cohort_mean": values.mean(axis=1).round(4),
            "cohort_sd": values.std(axis=1).round(4),
            "cohort_min": values.min(axis=1).round(4),
            "cohort_max": values.max(axis=1).round(4),
            "seeds_within_band": inside.sum(axis=1).astype(int),
            "seeds": len(seeds),
        }
    ).reset_index()
    summary["difference"] = (summary["cohort_mean"] - summary["published"]).round(4)
    return summary


def calibration_report(cohort: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Compare a cohort against every published anchor.

    Returns:
        One row per anchor, with the published value, the value observed in the
        cohort, whether it falls inside the stated band, whether it was targeted
        by the scale solver, and the source. This table is printed by the
        command line interface and pasted into the data plan; it is the evidence
        that the cohort is calibrated rather than invented.
    """
    rows = []
    for anchor in ANCHORS:
        value = observed(cohort, anchor)
        rows.append(
            {
                "quantity": anchor.quantity,
                "subgroup": anchor.subgroup,
                "horizon_years": anchor.horizon_years,
                "published": round(anchor.value, 4),
                "cohort": round(value, 4),
                "difference": round(value - anchor.value, 4),
                "within_band": bool(abs(value - anchor.value) <= anchor.tolerance),
                "targeted": anchor.targeted,
                "source": anchor.source,
            }
        )
    return pd.DataFrame(rows)
