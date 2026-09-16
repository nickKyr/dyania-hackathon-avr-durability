"""The generative model: covariates, latent times, surveillance, observed events.

The cohort is built as a causal chain, in this order.

1. **Covariates at implant** -- age, sex, body surface area, approach, valve model
   and size, and from those the effective orifice area and the patient-prosthesis
   mismatch grade.
2. **Latent times.** A Weibull time to the *onset* of structural deterioration,
   with a log-linear covariate effect, and an independent Weibull time to death.
   Onset is a biological event; nobody observes it.
3. **A surveillance process.** Guideline echocardiographic visits, extra studies
   triggered by symptoms once deterioration has begun, and informative dropout.
4. **Haemodynamics at each visit**, drifting gently before onset and accelerating
   after it, with measurement error.
5. **Observed events**, established by applying the VARC-3 criteria to each
   examination against that patient's own reference examination.

Step 5 is the one that makes the cohort honest. An event is recorded at the
examination that *detects* it, never at the latent onset, so the outcome is
interval-censored exactly as it is in a real surveillance cohort. A generator
that emitted the latent onset time would produce a dataset on which any model
looks better than it could ever be in clinic.

Why a mechanistic model rather than a learned one such as CTGAN or synthpop: a
generative model learns the joint distribution of the data you already hold. What
this study needs is structure the prototype extract does **not** hold -- serial
dated examinations, exact event times, age. You cannot learn a trajectory from a
dataset that contains one trajectory.
"""

from __future__ import annotations

from typing import Final

import numpy as np
import pandas as pd

from .parameters import DEFAULT, EchoParameters, Parameters

__all__ = ["build_cohort", "VARC3_STAGE2", "VARC3_STAGE3"]

DAYS_PER_YEAR: Final[float] = 365.25

VARC3_STAGE2: Final[str] = (
    "mean gradient rise >= 10 mmHg from the reference echo resulting in >= 20 mmHg, "
    "together with an EOA fall >= 0.3 cm2 or >= 25%, and/or a DVI fall >= 0.1 or >= 20%; "
    "or new or one-grade-worse intraprosthetic regurgitation that is at least moderate"
)
VARC3_STAGE3: Final[str] = (
    "mean gradient rise >= 20 mmHg resulting in >= 30 mmHg, together with an EOA fall "
    ">= 0.6 cm2 or >= 50%, and/or a DVI fall >= 0.2 or >= 40%; or severe intraprosthetic "
    "regurgitation"
)

_AR_GRADES: Final[tuple[str, ...]] = ("none", "trace", "mild", "moderate", "severe")

# Effective orifice area in cm2 by model and label size. Supra-annular
# transcatheter designs achieve a larger area for the same annulus, which is why
# the Evolut row sits above the Sapien row at every size.
_EOA_TABLE: Final[dict[str, dict[int, float]]] = {
    "Trifecta":  {19: 1.25, 21: 1.45, 23: 1.70, 25: 1.95, 27: 2.15},
    "Perimount": {19: 1.10, 21: 1.30, 23: 1.55, 25: 1.80, 27: 2.00},
    "Magna":     {19: 1.20, 21: 1.40, 23: 1.65, 25: 1.85, 27: 2.05},
    "Epic":      {19: 1.05, 21: 1.20, 23: 1.45, 25: 1.70, 27: 1.90},
    "Inspiris":  {19: 1.15, 21: 1.35, 23: 1.60, 25: 1.85, 27: 2.05},
    "Sapien 3":  {20: 1.30, 23: 1.55, 26: 1.85, 29: 2.15},
    "Evolut":    {23: 1.75, 26: 2.05, 29: 2.30, 34: 2.50},
}


def _choose(rng: np.random.Generator, options: tuple[tuple[str, float], ...], size: int) -> np.ndarray:
    names = [name for name, _ in options]
    weights = np.array([weight for _, weight in options], dtype=float)
    return rng.choice(names, size=size, p=weights / weights.sum())


def _label_size(rng: np.random.Generator, model: str, bsa: float) -> int:
    """Pick a label size for a patient, larger annuli going with larger patients.

    A jitter is applied so that size is not a deterministic function of body
    surface area; in practice the annulus, not the body, decides.
    """
    sizes = sorted(_EOA_TABLE[model])
    position = (bsa - 1.45) / 0.75 + rng.normal(0.0, 0.16)
    index = int(np.clip(round(position * (len(sizes) - 1)), 0, len(sizes) - 1))
    return sizes[index]


def _ppm_grade(eoa_index: np.ndarray) -> np.ndarray:
    """Classify patient-prosthesis mismatch at the VARC-3 indexed-EOA cut-offs."""
    return np.where(eoa_index <= 0.65, "severe", np.where(eoa_index <= 0.85, "moderate", "none"))


def _draw_patients(rng: np.random.Generator, params: Parameters) -> pd.DataFrame:
    """Draw the covariates of the cohort at implant."""
    cohort = params.cohort
    n = cohort.n_patients

    approach = np.where(rng.random(n) < cohort.savr_fraction, "SAVR", "TAVR")
    is_savr = approach == "SAVR"

    age = np.where(
        is_savr,
        rng.normal(cohort.age_mean_savr, cohort.age_sd_savr, n),
        rng.normal(cohort.age_mean_tavr, cohort.age_sd_tavr, n),
    ).clip(cohort.age_min, cohort.age_max)

    sex = np.where(rng.random(n) < cohort.female_fraction, "female", "male")
    is_female = sex == "female"
    bsa = np.where(
        is_female,
        rng.normal(cohort.bsa_mean_female, cohort.bsa_sd_female, n),
        rng.normal(cohort.bsa_mean_male, cohort.bsa_sd_male, n),
    ).clip(1.25, 2.75)

    model = np.empty(n, dtype=object)
    model[is_savr] = _choose(rng, cohort.savr_models, int(is_savr.sum()))
    model[~is_savr] = _choose(rng, cohort.tavr_models, int((~is_savr).sum()))

    size = np.array([_label_size(rng, m, b) for m, b in zip(model, bsa)], dtype=int)
    eoa_nominal = np.array([_EOA_TABLE[m][s] for m, s in zip(model, size)], dtype=float)
    eoa = (eoa_nominal * rng.lognormal(0.0, 0.11, n)).clip(0.45, 3.4)
    eoa_index = eoa / bsa

    bicuspid_p = np.where(is_savr, cohort.bicuspid_prevalence_savr, cohort.bicuspid_prevalence_tavr)

    return pd.DataFrame(
        {
            "patient_id": [f"SYN-{i + 1:05d}" for i in range(n)],
            "implant_year": rng.integers(cohort.implant_year_first, cohort.implant_year_last + 1, n),
            "age_at_implant": np.round(age, 1),
            "sex": sex,
            "bsa_m2": np.round(bsa, 3),
            "approach": approach,
            "valve_model": model,
            "valve_size_mm": size,
            "eoa_cm2": np.round(eoa, 3),
            "eoa_index_cm2_m2": np.round(eoa_index, 3),
            "ppm_grade": _ppm_grade(eoa_index),
            "diabetes": rng.random(n) < cohort.diabetes_prevalence,
            "ckd": rng.random(n) < cohort.ckd_prevalence,
            "smoking": rng.random(n) < cohort.smoking_prevalence,
            "bicuspid": rng.random(n) < bicuspid_p,
            "source": "simulated",
            "time_resolution": "day",
        }
    )


def _log_hazard_ratio(patients: pd.DataFrame, params: Parameters) -> np.ndarray:
    """Linear predictor of the deterioration hazard.

    Covariates are centred so that the Weibull scale describes a patient at the
    centring point -- a 75-year-old of average body surface area -- rather than
    the biologically impossible patient with every covariate at zero.
    """
    h = params.hazard
    ppm = patients["ppm_grade"].to_numpy()
    return (
        np.log(h.hr_age_per_year) * (patients["age_at_implant"].to_numpy() - h.age_centre)
        + np.log(h.hr_bsa_per_m2) * (patients["bsa_m2"].to_numpy() - h.bsa_centre)
        + np.log(h.hr_ppm_moderate) * (ppm == "moderate")
        + np.log(h.hr_ppm_severe) * (ppm == "severe")
        + np.log(h.hr_smoking) * patients["smoking"].to_numpy()
        + np.log(h.hr_diabetes) * patients["diabetes"].to_numpy()
        + np.log(h.hr_ckd) * patients["ckd"].to_numpy()
    )


def _weibull_time(rng: np.random.Generator, scale: np.ndarray, shape: float, log_hr: np.ndarray) -> np.ndarray:
    """Draw Weibull survival times under proportional hazards.

    Inverting the survival function ``S(t) = exp(-(t/scale)**shape * exp(log_hr))``
    gives ``t = scale * (-log(U) / exp(log_hr)) ** (1/shape)``.
    """
    uniform = rng.random(len(scale))
    return scale * np.power(-np.log(uniform) / np.exp(log_hr), 1.0 / shape)


def _latent_times(
    rng: np.random.Generator, patients: pd.DataFrame, params: Parameters
) -> tuple[np.ndarray, np.ndarray]:
    """Return latent years to deterioration onset and to death."""
    h = params.hazard
    is_savr = (patients["approach"] == "SAVR").to_numpy()
    svd_scale = np.where(is_savr, h.svd_scale_savr_years, h.svd_scale_tavr_years)
    onset = _weibull_time(rng, svd_scale, h.svd_shape, _log_hazard_ratio(patients, params))

    log_hr_death = (
        np.log(h.hr_death_per_year_age) * (patients["age_at_implant"].to_numpy() - h.age_centre)
        + np.log(h.hr_death_ckd) * patients["ckd"].to_numpy()
        + np.log(h.hr_death_diabetes) * patients["diabetes"].to_numpy()
    )
    death_scale = np.full(len(patients), h.death_scale_years_at_centre)
    death = _weibull_time(rng, death_scale, h.death_shape, log_hr_death)
    return onset, death


def _visit_days(
    rng: np.random.Generator, params: Parameters, onset_years: float, end_years: float
) -> list[float]:
    """Return examination times in days, for one patient, up to ``end_years``.

    The reference examination always occurs. Routine examinations follow the
    guideline schedule with jitter. Symptom-triggered examinations occur only
    after onset, which is what produces verification bias.
    """
    visit = params.visit
    days = [float(rng.integers(visit.reference_min_days, visit.reference_max_days + 1))]
    end_days = end_years * DAYS_PER_YEAR

    for year in visit.routine_years:
        day = year * DAYS_PER_YEAR + rng.integers(-visit.jitter_days, visit.jitter_days + 1)
        if days[0] < day <= end_days:
            days.append(float(day))

    if np.isfinite(onset_years):
        year = onset_years + rng.exponential(1.0 / max(visit.symptom_echo_probability_per_year, 1e-9))
        while year * DAYS_PER_YEAR <= end_days:
            days.append(year * DAYS_PER_YEAR)
            year += rng.exponential(1.0 / max(visit.symptom_echo_probability_per_year, 1e-9))

    return sorted(set(days))


def _gradient_at(
    rng: np.random.Generator,
    echo: EchoParameters,
    baseline: float,
    drift: float,
    progression: float,
    years: float,
    onset_years: float,
) -> float:
    """Mean gradient at ``years`` after implant, before measurement error.

    Two phases: a gentle linear drift that every bioprosthesis shows, and, after
    the latent onset, an additional accelerating term. The post-onset term is
    quadratic in time since onset because deterioration compounds -- a stiffer
    leaflet calcifies faster.
    """
    value = baseline + drift * years
    if years > onset_years:
        elapsed = years - onset_years
        value += progression * elapsed + echo.progression_quadratic_coefficient * progression * elapsed**2
    return float(value)


def _worsens_by_one_grade(rng: np.random.Generator, grade_index: int, rate: float, years: float) -> int:
    """Advance a regurgitation grade stochastically over ``years``."""
    if rng.random() < 1.0 - np.exp(-rate * years):
        return min(grade_index + 1, len(_AR_GRADES) - 1)
    return grade_index


def _meets_stage(
    mean_gradient: float,
    reference_gradient: float,
    eoa: float,
    reference_eoa: float,
    dvi: float,
    reference_dvi: float,
    ar_index: float,
    reference_ar_index: float,
    *,
    severe: bool,
) -> bool:
    """Apply the VARC-3 haemodynamic deterioration criteria to one examination.

    The criteria are transcribed from :data:`VARC3_STAGE2` and :data:`VARC3_STAGE3`.
    Note the structure: the gradient arm requires a rise **and** an absolute level
    **and** a corroborating fall in area or dimensionless valve index. A gradient
    rise on its own is not deterioration -- it may simply be higher flow.
    """
    if severe:
        rise_ok = (mean_gradient - reference_gradient) >= 20.0 and mean_gradient >= 30.0
        area_ok = (reference_eoa - eoa) >= 0.6 or (eoa <= 0.5 * reference_eoa)
        dvi_ok = (reference_dvi - dvi) >= 0.2 or (dvi <= 0.6 * reference_dvi)
        regurgitation_ok = ar_index >= _AR_GRADES.index("severe")
    else:
        rise_ok = (mean_gradient - reference_gradient) >= 10.0 and mean_gradient >= 20.0
        area_ok = (reference_eoa - eoa) >= 0.3 or (eoa <= 0.75 * reference_eoa)
        dvi_ok = (reference_dvi - dvi) >= 0.1 or (dvi <= 0.8 * reference_dvi)
        regurgitation_ok = ar_index >= _AR_GRADES.index("moderate") and ar_index > reference_ar_index

    return (rise_ok and (area_ok or dvi_ok)) or regurgitation_ok


def build_cohort(params: Parameters = DEFAULT, *, seed: int = 20260917) -> dict[str, pd.DataFrame]:
    """Generate a complete cohort.

    Args:
        params: Parameter set; defaults to :data:`synthetic.parameters.DEFAULT`.
        seed: Seed of the random generator. The same seed and parameters always
            reproduce the same cohort, byte for byte.

    Returns:
        Mapping with keys ``patients``, ``echos``, ``events`` and ``followup``.
        The frames satisfy :func:`synthetic.schema.validate_all`.
    """
    rng = np.random.default_rng(seed)
    echo_params = params.echo
    visit = params.visit

    patients = _draw_patients(rng, params)
    onset_years, death_years = _latent_times(rng, patients, params)

    baseline_gradient = (
        echo_params.gradient_reference_at_eoa
        * np.power(
            echo_params.gradient_eoa_reference_cm2 / patients["eoa_cm2"].to_numpy(),
            echo_params.gradient_eoa_exponent,
        )
        * rng.lognormal(0.0, echo_params.gradient_lognormal_sd, len(patients))
    ).clip(3.0, 40.0)
    drift = rng.normal(echo_params.drift_mmhg_per_year, echo_params.drift_sd_mmhg_per_year, len(patients))
    progression = rng.lognormal(
        np.log(echo_params.progression_mmhg_per_year_mean), echo_params.progression_lognormal_sd, len(patients)
    )
    lvef_baseline = rng.normal(echo_params.lvef_mean, echo_params.lvef_sd, len(patients)).clip(25.0, 75.0)
    dvi_baseline = rng.normal(echo_params.dvi_reference, echo_params.dvi_sd, len(patients)).clip(0.25, 0.75)

    dropout_years = rng.exponential(
        1.0
        / (
            visit.dropout_rate_per_year
            * np.power(visit.dropout_hr_per_year_age, patients["age_at_implant"].to_numpy() - params.hazard.age_centre)
        )
    )

    echo_rows: list[dict] = []
    event_rows: list[dict] = []
    followup_rows: list[dict] = []

    for i, patient_id in enumerate(patients["patient_id"]):
        death = float(death_years[i])
        onset = float(onset_years[i])
        dropout = float(dropout_years[i])
        observation_end = min(death, dropout, visit.horizon_years)

        days = _visit_days(rng, params, onset, observation_end)
        reference: dict[str, float] | None = None
        stage2_day: float | None = None
        stage3_day: float | None = None
        ar_index = 0
        previous_years = 0.0

        for k, day in enumerate(days):
            years = day / DAYS_PER_YEAR
            truth = _gradient_at(rng, echo_params, baseline_gradient[i], drift[i], progression[i], years, onset)
            measured = float(np.clip(truth * rng.lognormal(0.0, echo_params.measurement_cv_gradient), 1.0, 119.0))

            if years > onset:
                ar_index = _worsens_by_one_grade(rng, ar_index, echo_params.ar_progression_rate_per_year, years - previous_years)
            previous_years = years

            # Area and dimensionless index fall as the gradient rises: for a fixed
            # stroke volume, gradient varies roughly with the inverse square of area.
            # The ratio uses the TRUE gradient, and each quantity then carries its
            # own independent measurement error, so that the reference examination
            # reproduces the patient's recorded orifice area rather than a value
            # inflated by the gradient's noise.
            ratio = float(np.sqrt(max(baseline_gradient[i], 1e-6) / max(truth, 1e-6)))
            eoa_here = float(
                np.clip(patients["eoa_cm2"].iat[i] * ratio * rng.lognormal(0.0, echo_params.measurement_cv_eoa), 0.15, 3.4)
            )
            dvi_here = float(
                np.clip(dvi_baseline[i] * ratio * rng.lognormal(0.0, echo_params.measurement_cv_dvi), 0.06, 1.1)
            )
            lvef_here = float(
                np.clip(
                    lvef_baseline[i] - (echo_params.lvef_decline_after_onset_per_year * max(years - onset, 0.0)),
                    11.0,
                    79.0,
                )
            )
            peak = float(np.clip(measured * rng.uniform(echo_params.peak_to_mean_low, echo_params.peak_to_mean_high), 1.0, 199.0))

            is_reference = k == 0
            if is_reference:
                reference = {"gradient": measured, "eoa": eoa_here, "dvi": dvi_here, "ar": float(ar_index)}

            echo_rows.append(
                {
                    "patient_id": patient_id,
                    "echo_id": f"{patient_id}-E{k + 1:02d}",
                    "days_from_implant": int(round(day)),
                    "is_reference": is_reference,
                    "mean_gradient_mmhg": round(measured, 1),
                    "peak_gradient_mmhg": round(peak, 1),
                    "dvi": round(dvi_here, 3),
                    "eoa_cm2": round(eoa_here, 3),
                    "ar_grade": _AR_GRADES[ar_index],
                    "lvef_pct": round(lvef_here, 1),
                    "source": "simulated",
                    "time_resolution": "day",
                }
            )

            if is_reference or reference is None:
                continue

            args = (measured, reference["gradient"], eoa_here, reference["eoa"], dvi_here, reference["dvi"], float(ar_index), reference["ar"])
            if stage2_day is None and _meets_stage(*args, severe=False):
                stage2_day = day
            if stage3_day is None and _meets_stage(*args, severe=True):
                stage3_day = day

        n_echos = len(days)
        if stage2_day is not None:
            event_rows.append({"patient_id": patient_id, "event_type": "svd_stage2", "days_from_implant": int(round(stage2_day)), "ascertainment": "echo"})
        if stage3_day is not None:
            event_rows.append({"patient_id": patient_id, "event_type": "svd_stage3", "days_from_implant": int(round(stage3_day)), "ascertainment": "echo"})
            if rng.random() < visit.reintervention_probability:
                delay = rng.exponential(visit.reintervention_delay_days_mean)
                treated = stage3_day + delay
                if treated <= min(death, visit.horizon_years) * DAYS_PER_YEAR:
                    event_rows.append({"patient_id": patient_id, "event_type": "bvf_reintervention", "days_from_implant": int(round(treated)), "ascertainment": "reintervention"})

        if death <= visit.horizon_years:
            event_rows.append({"patient_id": patient_id, "event_type": "death", "days_from_implant": int(round(death * DAYS_PER_YEAR)), "ascertainment": "registry"})

        if death <= min(dropout, visit.horizon_years):
            reason, last = "death", death
        elif dropout < visit.horizon_years:
            reason, last = "dropout", dropout
        else:
            reason, last = "administrative", visit.horizon_years
        if stage3_day is not None and stage3_day / DAYS_PER_YEAR <= last:
            reason = "event"
        followup_rows.append({"patient_id": patient_id, "last_contact_days": int(round(last * DAYS_PER_YEAR)), "n_echos": n_echos, "censoring_reason": reason})

    governance = {"source": "simulated", "time_resolution": "day"}
    return {
        "patients": patients,
        "echos": pd.DataFrame(echo_rows),
        "events": pd.DataFrame(event_rows).assign(**governance),
        "followup": pd.DataFrame(followup_rows).assign(**governance),
    }
