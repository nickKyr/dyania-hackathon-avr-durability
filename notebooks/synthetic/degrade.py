"""The degradation ladder: the same cohort, progressively stripped of data quality.

Every rung removes one property of the data while leaving the patients, their
biology and their events untouched. The cohort's *truth* is identical on every
rung; only what an analyst can see of it changes. Running one unchanged modelling
pipeline across the rungs therefore measures exactly one thing: what each defect
costs in predictive performance.

This turns a statement no panel can act on -- "the data were poor" -- into a
ranked, quantified list of which defect costs most, which is the argument a
hospital needs before it will fund dated, serial, linkable echocardiography.

The rungs are **cumulative**: each adds its defect to all the preceding ones, so
the ladder descends from the data the protocol asks for to the data we were
actually given. Each defect mirrors a specific, measured property of the
prototype extract, named in its docstring.
"""

from __future__ import annotations

from typing import Callable, Final

import numpy as np
import pandas as pd

__all__ = ["PRESETS", "PRESET_DESCRIPTIONS", "apply_preset"]

_Tables = dict[str, pd.DataFrame]


def _drop_age(tables: _Tables, rng: np.random.Generator) -> _Tables:
    """Remove age at implant.

    Mirrors the extract, in which age is redacted as ``[AGE]`` in 194 of 215 notes
    and cannot be recovered by joining the three files. It removes the strongest
    published predictor of deterioration.
    """
    patients = tables["patients"].copy()
    patients["age_at_implant"] = np.nan
    return tables | {"patients": patients}


def _round_to_year(tables: _Tables, rng: np.random.Generator) -> _Tables:
    """Collapse every time to calendar-year resolution.

    Mirrors the date shifting and truncation applied to the extract, where all
    dates are year-only and 119 of 143 gradient mentions sit beside a redacted
    ``[DATE]`` token. Ties within a year become unorderable, which is what
    destroys any within-year trajectory.
    """
    out = dict(tables)
    for name in ("echos", "events", "followup"):
        frame = tables[name].copy()
        column = "last_contact_days" if name == "followup" else "days_from_implant"
        years = np.round(frame[column].to_numpy() / 365.25)
        frame[column] = (years * 365.25).round().astype(int)
        frame["time_resolution"] = "year"
        out[name] = frame
    patients = tables["patients"].copy()
    patients["time_resolution"] = "year"
    return out | {"patients": patients}


def _single_echo(tables: _Tables, rng: np.random.Generator) -> _Tables:
    """Keep one examination per patient, and lose the reference examination.

    Mirrors the measured structure of the extract: only one patient in it has
    gradient values in more than one note or year. The retained examination is the
    last one, and its reference flag is cleared -- because without a baseline, the
    VARC-3 *rise* criteria cannot be evaluated at all and only the weaker
    absolute-threshold arm of the definition survives.
    """
    echos = tables["echos"].sort_values(["patient_id", "days_from_implant"])
    kept = echos.groupby("patient_id", as_index=False).tail(1).copy()
    kept["is_reference"] = False
    followup = tables["followup"].copy()
    counts = kept.groupby("patient_id").size()
    followup["n_echos"] = followup["patient_id"].map(counts).fillna(0).astype(int)
    return tables | {"echos": kept.reset_index(drop=True), "followup": followup}


def _one_encounter(tables: _Tables, rng: np.random.Generator, quoted_priors_mean: float = 0.9) -> _Tables:
    """Keep one encounter, plus the earlier studies that encounter quotes.

    A gentler and more faithful defect than keeping exactly one examination. The
    supplied extract averages 1.69 examinations per patient who has any, because a
    clinical note routinely quotes prior studies alongside the current one -- "the
    mean gradient is 25 mmHg, compared with 18 mmHg previously".

    What is destroyed is therefore not the *number* of measurements but their
    **order and their dates**. The quoted priors carry no date of their own, so they
    all collapse onto the service year of the note that mentions them: a patient can
    have three gradients and no trajectory. Modelling this as a single examination,
    as an earlier version did, understated what the extract contains and overstated
    how cleanly it fails.

    ``quoted_priors_mean`` is the mean number of earlier studies a note repeats,
    chosen so that the simulated rung reproduces the 1.69 measured in the extract.
    """
    echos = tables["echos"].sort_values(["patient_id", "days_from_implant"])
    kept: list[pd.DataFrame] = []
    for _, group in echos.groupby("patient_id", sort=False):
        index = rng.integers(0, len(group))
        encounter = group.iloc[index]
        earlier = group.iloc[:index]
        quoted = min(int(rng.poisson(quoted_priors_mean)), len(earlier))
        block = pd.concat([earlier.tail(quoted), group.iloc[[index]]]).copy()
        # Everything the note mentions is attributed to the note's own service year.
        block["days_from_implant"] = int(encounter["days_from_implant"])
        block["is_reference"] = False
        kept.append(block)

    echos = pd.concat(kept).reset_index(drop=True) if kept else echos.iloc[:0]
    followup = tables["followup"].copy()
    counts = echos.groupby("patient_id").size()
    followup["n_echos"] = followup["patient_id"].map(counts).fillna(0).astype(int)
    return tables | {"echos": echos, "followup": followup}


def _no_mortality(tables: _Tables, rng: np.random.Generator) -> _Tables:
    """Remove every death.

    The supplied extract contains no mortality data of any kind: no death table, no
    date of death, no linkage. The competing risk is therefore entirely unobserved,
    and this is the single most consequential absence in it -- more damaging than
    the missing age, and far easier to overlook, because nothing in the data
    announces it. A cumulative incidence computed where death is invisible is not
    comparable with one computed where it is known, and a model fitted without it
    will mistake patients who died for patients who were fine.
    """
    events = tables["events"]
    events = events[events["event_type"] != "death"].reset_index(drop=True)
    followup = tables["followup"].copy()
    followup["censoring_reason"] = followup["censoring_reason"].replace("death", "administrative")
    return tables | {"events": events, "followup": followup}


def _extraction_yield(tables: _Tables, rng: np.random.Generator, retained: float = 0.521) -> _Tables:
    """Retain haemodynamic data for only the fraction of patients abstraction yields.

    The retained fraction is **measured, not assumed**: mapping the supplied extract
    into this schema yields post-operative prosthetic examinations for 61 of its 117
    patients, 52.1%. A stricter figure exists for a different question -- only 32 of
    117 receive a label assessable against the endpoint criteria, 27% -- but the
    quantity this rung models is what reaches the analyst, which is the examinations.

    Events established by reintervention survive, because operative reports exist
    even where echocardiographic values do not. That is exactly the ground-truth
    hierarchy the protocol relies on, and it is why the real cohort still carries 14
    events with no usable haemodynamics behind most of them.
    """
    ids = tables["patients"]["patient_id"].to_numpy()
    keep = set(rng.choice(ids, size=int(round(retained * len(ids))), replace=False))

    echos = tables["echos"]
    echos = echos[echos["patient_id"].isin(keep)].reset_index(drop=True)

    events = tables["events"]
    events = events[(events["ascertainment"] != "echo") | (events["patient_id"].isin(keep))].reset_index(drop=True)

    followup = tables["followup"].copy()
    counts = echos.groupby("patient_id").size()
    followup["n_echos"] = followup["patient_id"].map(counts).fillna(0).astype(int)
    return tables | {"echos": echos, "events": events, "followup": followup}


def _drop_implant_detail(tables: _Tables, rng: np.random.Generator) -> _Tables:
    """Remove the device identity and the native valve morphology.

    Mirrors the supplied extract, which has no implant registry: valve model and
    label size exist only inside operative-report free text and did not survive the
    consolidation, and bicuspid morphology is nowhere recorded in structured form.
    Both are covariates the durability literature treats as central.
    """
    patients = tables["patients"].copy()
    patients["valve_model"] = pd.NA
    patients["valve_size_mm"] = np.nan
    patients["bicuspid"] = pd.NA
    return tables | {"patients": patients}


_DEFECTS: Final[dict[str, Callable[[_Tables, np.random.Generator], _Tables]]] = {
    "drop_age": _drop_age,
    "round_to_year": _round_to_year,
    "single_echo": _single_echo,
    "extraction_yield": _extraction_yield,
    "drop_implant_detail": _drop_implant_detail,
    "one_encounter": _one_encounter,
    "no_mortality": _no_mortality,
}

PRESETS: Final[dict[str, tuple[str, ...]]] = {
    "ideal": (),
    "no_age": ("drop_age",),
    "year_resolution": ("drop_age", "round_to_year"),
    "single_echo": ("drop_age", "round_to_year", "single_echo"),
    "as_supplied": (
        "drop_age", "round_to_year", "one_encounter", "extraction_yield",
        "drop_implant_detail", "no_mortality",
    ),
}
"""The rungs, in order. Cumulative: each contains every defect above it.

These five are *simulations* of data poverty. The ladder has a sixth rung that is
not simulated at all -- the supplied extract itself, mapped into this schema by
``cohort.to_schema``. Comparing the fifth rung with the sixth answers a question
the simulation cannot answer about itself: whether our model of how poor the data
are was accurate. See ``cohort.ladder``.
"""

PRESET_DESCRIPTIONS: Final[dict[str, str]] = {
    "ideal": "The data the protocol asks a site to supply: dated serial echocardiography with demographics.",
    "no_age": "Age at implant redacted, as in the supplied notes.",
    "year_resolution": "All timing collapsed to the calendar year by date shifting.",
    "single_echo": "One examination per patient and no reference study, so VARC-3 rise criteria cannot be applied.",
    "as_supplied": "Simulating the supplied extract: one encounter per patient, examinations for "
                   "only the 52% abstraction reaches, no device identity, and no mortality at all.",
}


def apply_preset(tables: _Tables, preset: str, *, seed: int = 20260917) -> _Tables:
    """Return a degraded copy of ``tables``.

    Args:
        tables: A cohort as returned by :func:`synthetic.generator.build_cohort`.
        preset: One of the keys of :data:`PRESETS`.
        seed: Seed for the defects that make random choices, so that a rung is
            reproducible independently of the cohort it was applied to.

    Returns:
        A new mapping; the input frames are not modified.

    Raises:
        KeyError: If ``preset`` is not a known rung.
    """
    if preset not in PRESETS:
        raise KeyError(f"Unknown preset {preset!r}; expected one of {tuple(PRESETS)}.")
    rng = np.random.default_rng(seed)
    out = dict(tables)
    for defect in PRESETS[preset]:
        out = _DEFECTS[defect](out, rng)
    return out
