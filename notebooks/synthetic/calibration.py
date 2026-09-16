"""Calibration of the cohort against published durability evidence.

**What was fitted, and what that does and does not prove.** Nine parameters were
chosen using the anchors in :data:`synthetic.parameters.ANCHORS`: three scales
solved by bisection -- two for deterioration against the NOTION moderate-or-severe
figures, one for competing mortality against NOTION's all-cause death -- and six
shape parameters governing onset, the rapidly progressive phenotype and gradient
progression, selected from small grids.

Nine parameters against ten anchors is close to a saturated fit, so **agreement
with the anchors is not independent evidence that the cohort is correct**. It
establishes only that the cohort is plausible: that it lands where published series
land, so a pipeline exercised on it runs at realistic event rates. The evidence of
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
from typing import Final

import numpy as np
import pandas as pd

from .generator import DAYS_PER_YEAR, build_cohort
from .parameters import ANCHORS, DEFAULT, Anchor, Parameters

__all__ = [
    "REGISTRY_ASCERTAINED",
    "cumulative_incidence",
    "endpoint_times",
    "observed",
    "incidence_by_family",
    "solve_scales",
    "solve_death_scale",
    "calibration_report",
    "calibration_across_seeds",
]


@dataclass(frozen=True, slots=True)
class _Endpoint:
    """Per-patient outcome reduced to a time and a cause."""

    time_years: np.ndarray
    cause: np.ndarray
    """1 for the endpoint of interest, 2 for the competing death, 0 for censored."""


def endpoint_times(
    cohort: dict[str, pd.DataFrame],
    event_types: tuple[str, ...],
    *,
    horizon_days: float | None = None,
) -> _Endpoint:
    """Reduce a cohort to time-to-first-event for a given endpoint definition.

    Whichever of the endpoint or death happens first is what the patient
    contributes; a patient censored before either contributes neither.

    **Two follow-up clocks, because the cohort has two.** Deterioration is
    ascertained at echocardiography, so it can only be observed while the patient
    still attends, and an endpoint that depends on imaging is censored at
    ``last_contact_days``. Death is ascertained by registry linkage, so it is known
    whether or not the patient still attends, and an endpoint made only of
    registry-ascertained events is censored at the administrative horizon instead.
    Using clinical follow-up for both would discard about one death in five and
    make the cohort's own mortality disagree with the figure it is calibrated to.

    The asymmetry does not run the other way. A patient last imaged at three years
    who dies at seven contributes a death to the mortality estimate, but is still
    censored at three years for deterioration: nobody knows whether their valve
    failed in between, and counting them as a competing death at seven would assert
    four years of deterioration-free follow-up that was never observed.

    Args:
        cohort: Tables as returned by :func:`synthetic.generator.build_cohort`.
        event_types: Event types that together constitute the endpoint, for
            example ``("svd_stage2", "svd_stage3")``.
        horizon_days: Administrative horizon, used as the censoring time when every
            requested event type is registry-ascertained. Defaults to the
            protocol's ten years.

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
    for pid, day in zip(selected["patient_id"], selected["days_from_implant"], strict=True):
        i = order[pid]
        endpoint_day[i] = min(endpoint_day[i], float(day))

    deaths = events[events["event_type"] == "death"]
    for pid, day in zip(deaths["patient_id"], deaths["days_from_implant"], strict=True):
        death_day[order[pid]] = float(day)

    followup = cohort["followup"]
    if set(event_types) <= REGISTRY_ASCERTAINED:
        horizon = DEFAULT.visit.horizon_years * DAYS_PER_YEAR if horizon_days is None else horizon_days
        censor_day = np.full(n, float(horizon))
    else:
        censor_day = np.empty(n)
        for pid, day in zip(followup["patient_id"], followup["last_contact_days"], strict=True):
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


REGISTRY_ASCERTAINED: Final[frozenset[str]] = frozenset({"death"})
"""Event types known after a patient stops attending clinic.

Vital status reaches the study through registry linkage rather than through the
clinic, so these events are not lost when follow-up is. Everything else in the
cohort is established at an examination or an operation and is therefore only as
complete as attendance.
"""

_ARMS: Final[tuple[str, ...]] = ("SAVR", "TAVR")
"""The two implant approaches, each with its own solved deterioration scale."""

_SOLVED_QUANTITY: Final[str] = "moderate_or_severe_svd"
"""The quantity :func:`solve_scales` solves against; mortality has its own solver."""

_ENDPOINT_TYPES: dict[str, tuple[str, ...]] = {
    "moderate_or_severe_svd": ("svd_stage2", "svd_stage3"),
    "severe_svd": ("svd_stage3",),
    # VARC-3 bioprosthetic valve failure stage 2/3 is severe haemodynamic
    # deterioration OR reintervention OR valve-related death -- not reintervention
    # alone. Comparing a reintervention-only rate against the PARTNER 3 figure
    # would be comparing two different endpoints.
    "bioprosthetic_valve_failure": ("svd_stage3", "bvf_reintervention"),
    "all_cause_death": ("death",),
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


def incidence_by_family(
    cohort: dict[str, pd.DataFrame],
    *,
    quantity: str = "moderate_or_severe_svd",
    horizons: tuple[float, ...] = (5.0, 8.0, 10.0),
) -> pd.DataFrame:
    """Cumulative incidence of ``quantity`` by valve family.

    The realised effect of :attr:`HazardParameters.hr_tear_by_family` and
    :attr:`HazardParameters.hr_calcific_by_family` is this table, not the
    multipliers themselves: a family's incidence is the combination of its hazard
    multipliers, its orifice-area row and the size and approach mix it is implanted
    in. Quote the table; a multiplier on its own says nothing about what the cohort
    actually does.

    Args:
        cohort: Tables as returned by :func:`synthetic.generate`.
        quantity: Any key of the endpoint table, such as
            ``"bioprosthetic_valve_failure"``.
        horizons: Years at which to report incidence.

    Returns:
        One row per valve family, with the number implanted, the mean indexed
        orifice area at implant, and cumulative incidence at each horizon. Sorted
        by the last horizon, so the least durable family is last.
    """
    patients = cohort["patients"]
    rows = {}
    for family, group in patients.groupby("valve_model"):
        keep = set(group["patient_id"])
        subset = {n: f[f["patient_id"].isin(keep)] if "patient_id" in f else f for n, f in cohort.items()}
        endpoint = endpoint_times(subset, _ENDPOINT_TYPES[quantity])
        rows[family] = {
            "n": len(group),
            "mean_eoa_index": group["eoa_index_cm2_m2"].mean(),
            **{f"{h:g}y": cumulative_incidence(endpoint, h) for h in horizons},
        }
    return pd.DataFrame(rows).T.sort_values(f"{horizons[-1]:g}y")


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

    Because a larger Weibull scale can only postpone onset, incidence is decreasing
    in the scale *in expectation*, which is what makes bisection the right search.
    It is not monotone exactly: changing a scale changes how many examinations each
    patient receives and therefore how many random draws they consume, so every
    candidate scale is evaluated on a differently shuffled cohort and the objective
    carries Monte Carlo noise of about one percentage point at ``n_solve`` = 20,000.
    Bisection tolerates that as long as the noise is small against the distance to
    the target, which is why the search runs on a cohort far larger than the study
    cohort -- and why it verifies that it converged instead of trusting that it did.

    Args:
        params: Parameter set whose scales are to be replaced.
        seed: Seed used for every cohort drawn during the search. Holding it fixed
            makes the objective deterministic, which bisection requires.
        n_solve: Size of the cohort used for solving.
        tolerance: Convergence tolerance on cumulative incidence.
        max_iterations: Maximum bisection steps; at least one.

    Returns:
        The solved scales in years, for SAVR and TAVR respectively.

    Raises:
        ValueError: If ``max_iterations`` is less than one, or if the search ends
            without reaching ``tolerance`` on both arms. A bisection that has not
            converged returns whatever midpoint it stopped at, which may be a
            bracket bound rather than a solution; returning that silently would put
            an arbitrary number into the parameter file under the word SOLVED.
    """
    if max_iterations < 1:
        raise ValueError("max_iterations must be at least 1.")

    from dataclasses import replace as _replace

    # Select on the quantity as well as the flag. Three anchors are targeted and
    # two of them are transcatheter, so a dictionary keyed by subgroup alone lets
    # the all-cause mortality anchor overwrite the transcatheter deterioration
    # target -- and the search then chases 62.7% deterioration, which no scale can
    # produce, all the way to the bracket bound. Mortality is solved separately by
    # solve_death_scale; this function solves the deterioration scales only.
    deterioration = [a for a in ANCHORS if a.targeted and a.quantity == _SOLVED_QUANTITY]
    targets = {a.subgroup: a.value for a in deterioration}
    horizon = {a.subgroup: a.horizon_years for a in deterioration}
    if set(targets) != set(_ARMS):
        raise ValueError(
            f"solve_scales needs one targeted {_SOLVED_QUANTITY!r} anchor per arm; "
            f"found {sorted(targets)} instead of {sorted(_ARMS)}."
        )
    large = _replace(params, cohort=_replace(params.cohort, n_patients=n_solve))

    low = dict.fromkeys(_ARMS, 6.0)
    high = dict.fromkeys(_ARMS, 60.0)

    for _ in range(max_iterations):
        middle = {arm: 0.5 * (low[arm] + high[arm]) for arm in _ARMS}
        cohort = build_cohort(large.with_scales(middle["SAVR"], middle["TAVR"]), seed=seed)
        gap = {}
        for arm in _ARMS:
            subset = _subset(cohort, arm)
            value = cumulative_incidence(endpoint_times(subset, _ENDPOINT_TYPES["moderate_or_severe_svd"]), horizon[arm])
            gap[arm] = value - targets[arm]
            if gap[arm] > 0:
                low[arm] = middle[arm]      # too many events: postpone onset
            else:
                high[arm] = middle[arm]
        if all(abs(g) < tolerance for g in gap.values()):
            return middle["SAVR"], middle["TAVR"]

    raise ValueError(
        f"solve_scales did not converge in {max_iterations} iterations: "
        + ", ".join(f"{arm} off target by {gap[arm]:+.4f} at scale {middle[arm]:.4f}" for arm in gap)
        + f" (tolerance {tolerance}). Widen the bracket, raise n_solve so the objective is "
        "less noisy, or check whether an upstream parameter has made the target unreachable."
    )


def solve_death_scale(
    params: Parameters,
    *,
    target: float = 0.627,
    seed: int = 20260917,
    n_solve: int = 20_000,
    tolerance: float = 0.002,
    max_iterations: int = 40,
) -> float:
    """Solve the competing-mortality scale against a published survival figure.

    Mortality is calibrated on the **transcatheter arm only**, because that is the
    arm whose age distribution matches the trial's: this cohort's transcatheter
    recipients average 79.5 years against NOTION's 79, while its surgical
    recipients are deliberately a decade younger, as they are in real practice but
    not in a randomised trial of one population. Calibrating on the pooled cohort
    would force the model to reproduce a mortality it should not have.

    Getting this right matters more than it might appear. Death is the competing
    risk, so the mortality rate governs how many patients remain at risk to
    deteriorate; a cohort that dies too fast understates every cumulative incidence
    and one that dies too slowly overstates them.

    Args:
        params: Parameter set whose death scale is to be replaced.
        target: Published all-cause mortality at ten years.
        seed: Seed held fixed so the objective is deterministic.
        n_solve: Size of the cohort used for solving.
        tolerance: Convergence tolerance on cumulative incidence.
        max_iterations: Maximum bisection steps; at least one.

    Returns:
        The solved scale in years.

    Raises:
        ValueError: If ``max_iterations`` is less than one, or if the search ends
            without reaching ``tolerance``. See :func:`solve_scales`.
    """
    from dataclasses import replace as _replace

    if max_iterations < 1:
        raise ValueError("max_iterations must be at least 1.")

    large = _replace(params, cohort=_replace(params.cohort, n_patients=n_solve))
    low, high = 5.0, 40.0
    for _ in range(max_iterations):
        middle = 0.5 * (low + high)
        candidate = _replace(large, hazard=_replace(large.hazard, death_scale_years_at_centre=middle))
        cohort = build_cohort(candidate, seed=seed)
        value = cumulative_incidence(endpoint_times(_subset(cohort, "TAVR"), ("death",)), 10.0)
        if value > target:
            low = middle       # dying too fast: lengthen the scale
        else:
            high = middle
        if abs(value - target) < tolerance:
            return middle

    raise ValueError(
        f"solve_death_scale did not converge in {max_iterations} iterations: "
        f"{value:.4f} against a target of {target} at scale {middle:.4f} "
        f"(tolerance {tolerance})."
    )


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
