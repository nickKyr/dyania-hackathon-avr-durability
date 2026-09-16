"""Internal validation: can the injected effects be recovered from the output?

A calibrated cohort can still be produced by broken code. The check that catches
that is a **recovery test**: hazard ratios are injected into the generator, a
proportional-hazards model is fitted to the cohort it produces, and the estimates
are compared with what went in. It validates the generative model and the
analysis path at once, which is why it is worth more than either alone.

The Cox model here is implemented directly against the Breslow partial likelihood
rather than taken from ``lifelines`` or ``scikit-survival``. That is deliberate.
The modelling workstream fits its models with those libraries; validating the
generator with the same library would let a shared misunderstanding -- of a tie
convention, of how a competing risk is encoded -- pass unnoticed in both places.
An independent implementation cannot agree with the generator by accident.

The test has two levels, and the difference between them is itself a result.

**Level 1, the latent hazard.** Fitting the latent onset times, which are
uncensored and free of any detection process, must recover the injected hazard
ratios. This is a test of correctness, and failure means a bug.

**Level 2, the observed events.** Fitting what an analyst actually sees --
interval-censored detections at scheduled examinations, with death competing and
patients dropping out -- recovers **attenuated** estimates. That is not a bug. It
quantifies how much sparse surveillance biases effect estimates toward the null,
and it belongs in the protocol's limitations because it applies equally to any
real study built on guideline-interval echocardiography.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import optimize

from .generator import DAYS_PER_YEAR, _draw_patients, _latent_times
from .parameters import DEFAULT, Parameters

__all__ = ["CoxFit", "fit_cox", "recovery_test", "coverage_test"]


@dataclass(frozen=True, slots=True)
class CoxFit:
    """Result of a Cox proportional-hazards fit."""

    names: tuple[str, ...]
    coefficients: np.ndarray
    standard_errors: np.ndarray
    n_events: int

    def frame(self) -> pd.DataFrame:
        """Return the fit as hazard ratios with 95% confidence intervals."""
        lower = self.coefficients - 1.96 * self.standard_errors
        upper = self.coefficients + 1.96 * self.standard_errors
        return pd.DataFrame(
            {
                "covariate": self.names,
                "hazard_ratio": np.exp(self.coefficients),
                "ci_low": np.exp(lower),
                "ci_high": np.exp(upper),
            }
        )


def _partial_likelihood(
    beta: np.ndarray, x: np.ndarray, event: np.ndarray, tied_blocks: list[np.ndarray]
) -> tuple[float, np.ndarray, np.ndarray]:
    """Negative Breslow log partial likelihood with its gradient and Hessian.

    Risk sets are accumulated from the longest time downward, so each unique event
    time sees exactly the patients still at risk at that moment.
    """
    n, p = x.shape
    weight = np.exp(x @ beta)
    s0 = 0.0
    s1 = np.zeros(p)
    s2 = np.zeros((p, p))
    loglik = 0.0
    grad = np.zeros(p)
    hess = np.zeros((p, p))

    for members in tied_blocks:
        block = x[members]
        block_weight = weight[members]
        s0 += block_weight.sum()
        s1 += block_weight @ block
        s2 += (block * block_weight[:, None]).T @ block

        failures = members[event[members]]
        d = len(failures)
        if not d:
            continue
        mean = s1 / s0
        loglik += x[failures].sum(axis=0) @ beta - d * np.log(s0)
        grad += x[failures].sum(axis=0) - d * mean
        hess -= d * (s2 / s0 - np.outer(mean, mean))

    return -loglik, -grad, -hess


def _risk_set_index(time: np.ndarray) -> list[np.ndarray]:
    """Group tied times, walking from the longest downward to build risk sets.

    Args:
        time: Follow-up times, sorted ascending.

    Returns:
        One array of positions per distinct time, longest time first. Consuming
        them in that order lets the risk set be accumulated rather than rebuilt:
        after k blocks it holds exactly the subjects still at risk at the k-th
        distinct time from the end.
    """
    blocks: list[np.ndarray] = []
    i = len(time)
    while i > 0:
        j = i - 1
        while j > 0 and time[j - 1] == time[i - 1]:
            j -= 1
        blocks.append(np.arange(j, i))
        i = j
    return blocks


def fit_cox(
    time: np.ndarray, event: np.ndarray, x: pd.DataFrame, strata: np.ndarray | None = None
) -> CoxFit:
    """Fit a Cox proportional-hazards model by maximising the partial likelihood.

    Args:
        time: Follow-up time per subject, in any consistent unit.
        event: Boolean, True where the subject experienced the event of interest.
            Competing events are encoded as censoring, which makes this the
            **cause-specific** hazard model.
        x: Covariates, one column per covariate.
        strata: Optional stratum label per subject. Each stratum keeps its own
            baseline hazard and contributes its own risk sets, while the
            coefficients are shared. Use it when groups are **not** proportional to
            one another -- for example when they are generated by processes with
            different Weibull shapes -- because then no single coefficient can
            express the difference between them and forcing one biases every other
            estimate.

    Returns:
        The fitted coefficients and their standard errors, taken from the inverse
        of the observed information matrix.

    Raises:
        ValueError: If there are no events to fit.
    """
    event = np.asarray(event, dtype=bool)
    if not event.any():
        raise ValueError("Cannot fit a Cox model: no events.")

    values = x.to_numpy(dtype=float)
    time = np.asarray(time, dtype=float)
    labels = np.zeros(len(time), dtype=int) if strata is None else np.asarray(strata)

    blocks: list[tuple[np.ndarray, np.ndarray, list[np.ndarray]]] = []
    for label in np.unique(labels):
        member = np.flatnonzero(labels == label)
        order = member[np.argsort(time[member], kind="mergesort")]
        blocks.append((values[order], event[order], _risk_set_index(time[order])))

    def evaluate(beta: np.ndarray) -> tuple[float, np.ndarray, np.ndarray]:
        """Sum the negative log partial likelihood over strata."""
        p = values.shape[1]
        total, gradient, hessian = 0.0, np.zeros(p), np.zeros((p, p))
        for block_values, block_event, index in blocks:
            v, g, h = _partial_likelihood(beta, block_values, block_event, index)
            total, gradient, hessian = total + v, gradient + g, hessian + h
        return total, gradient, hessian

    def objective(beta: np.ndarray) -> tuple[float, np.ndarray]:
        """Negative log partial likelihood and its gradient at ``beta``."""
        value, gradient, _ = evaluate(beta)
        return value, gradient

    result = optimize.minimize(objective, np.zeros(values.shape[1]), jac=True, method="BFGS")
    _, _, hessian = evaluate(result.x)
    standard_errors = np.sqrt(np.diag(np.linalg.inv(hessian)))
    return CoxFit(tuple(x.columns), result.x, standard_errors, int(event.sum()))


def _design(patients: pd.DataFrame, params: Parameters) -> pd.DataFrame:
    """Build the covariate matrix, centred exactly as the generator centres it."""
    h = params.hazard
    ppm = patients["ppm_grade"].to_numpy()
    return pd.DataFrame(
        {
            "age_at_implant": patients["age_at_implant"].to_numpy() - h.age_centre,
            "bsa_m2": patients["bsa_m2"].to_numpy() - h.bsa_centre,
            "ppm_moderate": (ppm == "moderate").astype(float),
            "ppm_severe": (ppm == "severe").astype(float),
            "smoking": patients["smoking"].to_numpy().astype(float),
            "diabetes": patients["diabetes"].to_numpy().astype(float),
            "ckd": patients["ckd"].to_numpy().astype(float),
        }
    )


def _injected(params: Parameters) -> dict[str, float]:
    h = params.hazard
    return {
        "age_at_implant": h.hr_age_per_year,
        "bsa_m2": h.hr_bsa_per_m2,
        "ppm_moderate": h.hr_ppm_moderate,
        "ppm_severe": h.hr_ppm_severe,
        "smoking": h.hr_smoking,
        "diabetes": h.hr_diabetes,
        "ckd": h.hr_ckd,
    }


def recovery_test(
    params: Parameters = DEFAULT, *, seed: int = 20260917, n_patients: int = 20_000
) -> pd.DataFrame:
    """Recover the injected hazard ratios from a generated cohort.

    Args:
        params: Parameter set whose hazard ratios are the ground truth.
        seed: Seed of the cohort. Must match the seed used by
            :func:`synthetic.generator.build_cohort` for the latent times to
            correspond to the same patients.
        n_patients: Cohort size. Large by default: recovering seven hazard ratios
            to within a few percent needs more events than the study cohort has.

    Returns:
        One row per covariate, with the injected hazard ratio, the estimate from
        the latent onset times with its confidence interval, whether that interval
        covers the injected value, and the estimate from the observed events with
        its attenuation relative to the injected value.
    """
    from dataclasses import replace

    large = replace(params, cohort=replace(params.cohort, n_patients=n_patients))
    rng = np.random.default_rng(seed)
    patients = _draw_patients(rng, large)
    onset_years, death_years, is_early = _latent_times(rng, patients, large)

    # Four baseline hazards, one per (phenotype, approach) cell. The two phenotypes
    # are generated with different Weibull shapes, so they are not proportional to
    # each other and no coefficient could express the difference; and approach
    # changes the scale only in the late phenotype. Stratifying lets each cell keep
    # its own baseline while the covariate effects, which are shared by
    # construction, are estimated from all of the data at once.
    strata = is_early.astype(int) * 2 + (patients["approach"].to_numpy() == "TAVR").astype(int)

    design = _design(patients, large)
    latent = fit_cox(onset_years, np.ones(len(patients), dtype=bool), design, strata=strata).frame()

    from . import generate

    cohort = generate("ideal", seed=seed, n_patients=n_patients, params=params)
    events = cohort["events"]
    first = (
        events[events["event_type"].isin(("svd_stage2", "svd_stage3"))]
        .groupby("patient_id")["days_from_implant"]
        .min()
    )
    followup = cohort["followup"].set_index("patient_id")["last_contact_days"]
    ids = cohort["patients"]["patient_id"]
    event_day = first.reindex(ids).to_numpy(dtype=float)
    censor_day = followup.reindex(ids).to_numpy(dtype=float)
    observed_event = ~np.isnan(event_day)
    observed_time = np.where(observed_event, np.nan_to_num(event_day), censor_day) / DAYS_PER_YEAR
    observed = fit_cox(
        observed_time,
        observed_event,
        _design(cohort["patients"], params),
        strata=(cohort["patients"]["approach"].to_numpy() == "TAVR").astype(int),
    ).frame()

    injected = _injected(params)
    out = pd.DataFrame({"covariate": latent["covariate"], "injected_hr": [injected[c] for c in latent["covariate"]]})
    out["latent_hr"] = latent["hazard_ratio"].to_numpy()
    out["latent_ci_low"] = latent["ci_low"].to_numpy()
    out["latent_ci_high"] = latent["ci_high"].to_numpy()
    out["recovered"] = (out["latent_ci_low"] <= out["injected_hr"]) & (out["injected_hr"] <= out["latent_ci_high"])
    out["observed_hr"] = observed["hazard_ratio"].to_numpy()
    out["attenuation"] = np.log(out["observed_hr"]) / np.log(out["injected_hr"])
    return out.round(4)


def coverage_test(
    seeds: tuple[int, ...] = (20260917, 1, 2, 3, 4),
    *,
    params: Parameters = DEFAULT,
    n_patients: int = 20_000,
) -> pd.DataFrame:
    """Measure how often the 95% interval actually covers the injected value.

    Asking whether every hazard ratio was recovered in one run is the wrong
    question: a 95% interval is *supposed* to miss about one time in twenty, so a
    run in which all seven are covered is no more reassuring than one in which six
    are, and treating a single miss as a failure invites tuning until it passes.
    The right question is whether coverage over many fits is near nominal.

    Args:
        seeds: Seeds to repeat the recovery test with.
        params: Parameter set whose hazard ratios are the ground truth.
        n_patients: Size of each cohort.

    Returns:
        One row per covariate, with how many seeds covered the injected value, plus
        a final ``ALL`` row giving overall coverage against the nominal 0.95.
    """
    runs = [recovery_test(params, seed=seed, n_patients=n_patients).set_index("covariate") for seed in seeds]
    covered = pd.concat([run["recovered"] for run in runs], axis=1)
    bias = pd.concat([np.log(run["latent_hr"] / run["injected_hr"]) for run in runs], axis=1)

    out = pd.DataFrame(
        {
            "seeds_covering": covered.sum(axis=1).astype(int),
            "seeds": len(seeds),
            "coverage": covered.mean(axis=1).round(3),
            "mean_log_bias": bias.mean(axis=1).round(4),
        }
    ).reset_index()
    total = pd.DataFrame(
        [{
            "covariate": "ALL",
            "seeds_covering": int(covered.values.sum()),
            "seeds": int(covered.size),
            "coverage": round(float(covered.values.mean()), 3),
            "mean_log_bias": round(float(bias.values.mean()), 4),
        }]
    )
    return pd.concat([out, total], ignore_index=True)
