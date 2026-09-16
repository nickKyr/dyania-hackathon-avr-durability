"""Mapping the supplied extract into the same schema as the synthetic cohort.

This is the join between the two halves of the study. The synthetic cohort
describes what the protocol asks a site to supply; the extract is what a site
actually supplied. Expressing both in one schema is what makes them comparable,
and comparability is the whole point: the real cohort becomes the **last rung of
the degradation ladder**, so that the ladder ends not with a simulation of poor
data but with the poor data itself.

Nothing is imputed. Where the extract cannot supply a column it is left null, and
the schema permits that deliberately -- see :mod:`synthetic.schema`. The gap
between a populated synthetic column and a null real one is a measurement, not a
defect to be papered over.

**Three things the extract cannot supply at all**, each of which changes what any
analysis of it can claim:

*Age at implant.* Redacted in every note, and not recoverable by joining the three
workbooks.

*A reference examination.* VARC-3 defines haemodynamic deterioration as a **rise**
from an examination taken 30 days to 3 months after implant. No such examination
can be identified here, and exam dates were destroyed by de-identification, so
the rise criteria cannot be evaluated. Only reintervention -- documented in an
operative report -- survives as an event this mapping will assert.

*Death.* The extract contains no mortality data whatsoever. The competing risk is
therefore entirely unobserved, which means a cumulative incidence computed on this
cohort is not comparable with one computed where death is known. It is the single
most consequential absence in the extract and the easiest to overlook, because
nothing in the data announces it.
"""

from __future__ import annotations

import re
from typing import Final

import numpy as np
import pandas as pd

from synthetic.schema import TABLES, validate_all

from .load import echo_exams, load_long

__all__ = ["to_schema", "implausible_values", "REAL_COHORT_NOTE"]

DAYS_PER_YEAR: Final[float] = 365.25

REAL_COHORT_NOTE: Final[str] = (
    "Supplied extract mapped into the study schema. Age, reference examinations and "
    "mortality are absent; events are limited to documented reintervention."
)

_HEIGHT_CM = re.compile(r"(?:Ht|Height)[^0-9]{0,12}(?P<cm>\d{2,3}(?:\.\d+)?)\s*cm", re.IGNORECASE)
_HEIGHT_M = re.compile(r"\((?P<m>[12]\.\d{2})\s*m\)", re.IGNORECASE)
_WEIGHT_KG = re.compile(r"(?:Wt|Weight)[^0-9]{0,18}?(?P<kg>\d{2,3}(?:\.\d+)?)\s*kg", re.IGNORECASE)
_WEIGHT_KG_PAREN = re.compile(r"\((?P<kg>\d{2,3}(?:\.\d+)?)\s*kg\)", re.IGNORECASE)


def _body_surface_area(text: str) -> float:
    """Return body surface area in m^2 by the Mosteller formula, or NaN.

    Mosteller is used rather than DuBois because it needs only height and weight,
    which is all the free text reliably carries.
    """
    height = _HEIGHT_CM.search(text)
    centimetres = float(height.group("cm")) if height else None
    if centimetres is None:
        metres = _HEIGHT_M.search(text)
        centimetres = float(metres.group("m")) * 100 if metres else None

    weight = _WEIGHT_KG.search(text) or _WEIGHT_KG_PAREN.search(text)
    kilograms = float(weight.group("kg")) if weight else None

    if centimetres is None or kilograms is None:
        return float("nan")
    if not (120 <= centimetres <= 210 and 30 <= kilograms <= 250):
        return float("nan")
    return float(np.sqrt(centimetres * kilograms / 3600.0))


def _first_by_year(frame: pd.DataFrame, column: str = "item") -> pd.Series:
    """Return, per patient, the value from the earliest year it appears in."""
    ordered = frame.sort_values(["patient", "year"])
    return ordered.groupby("patient")[column].first()


def _patients(long: pd.DataFrame) -> pd.DataFrame:
    """Build the patient table from whatever the extract can support."""
    notes = long[long["source"] == "notes"]

    operation = notes[
        (notes["category"] == "operation described in this note")
        & (notes["item"].isin(("SAVR", "TAVR")))
    ]
    history = notes[
        (notes["category"] == "prosthetic valve in history") & (notes["item"].isin(("SAVR", "TAVR")))
    ]
    # An operative report outranks a history mention: the report describes the
    # operation, the mention describes someone's recollection of it.
    approach = _first_by_year(operation).reindex(sorted(set(long["patient"])))
    approach = approach.fillna(_first_by_year(history))

    implant_year = operation.groupby("patient")["year"].min()
    implant_year = implant_year.reindex(approach.index).fillna(
        notes.groupby("patient")["year"].min().reindex(approach.index)
    )

    context = notes[notes["category"] == "clinical context"]
    sex = context[context["item"] == "sex"].groupby("patient")["value"].first()
    sex = sex.where(sex.isin(("male", "female")))

    body = context[context["item"] == "height / weight / BSA / BMI"]
    bsa = body.assign(bsa=body["value"].astype(str).map(_body_surface_area)).groupby("patient")["bsa"].median()

    comorbidity = notes[notes["category"] == "comorbidity"]
    def flag(name: str) -> pd.Series:
        """True where documented; null where not, because absence of documentation is not absence of disease."""
        present = set(comorbidity.loc[comorbidity["item"] == name, "patient"])
        return pd.Series({p: (True if p in present else pd.NA) for p in approach.index}, dtype="object")

    echo = echo_exams(method="llm")
    indexed = echo[echo["item"] == "aortic_valve_area_indexed_cm2_m2"]
    eoa_index = pd.to_numeric(indexed["value"], errors="coerce").groupby(indexed["patient"]).min()
    eoa_index = eoa_index.reindex(approach.index).where(lambda s: s.between(0.2, 2.5))

    ppm = pd.Series(pd.NA, index=approach.index, dtype="object")
    ppm[eoa_index.notna()] = np.where(
        eoa_index[eoa_index.notna()] <= 0.65, "severe",
        np.where(eoa_index[eoa_index.notna()] <= 0.85, "moderate", "none"),
    )

    return pd.DataFrame(
        {
            "patient_id": approach.index,
            "implant_year": implant_year.astype("Int64").reindex(approach.index),
            "age_at_implant": np.nan,
            "sex": sex.reindex(approach.index),
            "bsa_m2": bsa.reindex(approach.index).round(3),
            "approach": approach.values,
            "valve_model": pd.NA,
            "valve_size_mm": np.nan,
            "eoa_cm2": np.nan,
            "eoa_index_cm2_m2": eoa_index.round(3),
            "ppm_grade": ppm,
            "diabetes": flag("diabetes"),
            "ckd": flag("chronic_kidney_disease_or_dialysis"),
            "smoking": flag("smoking"),
            "bicuspid": pd.NA,
            "source": "real",
            "time_resolution": "year",
        }
    ).reset_index(drop=True)


def _echos(long: pd.DataFrame, implant_year: pd.Series) -> pd.DataFrame:
    """Build the examination table, one row per distinct study the abstraction found."""
    echo = echo_exams(method="llm")
    echo = echo[(echo["valve_context"] == "prosthetic") & (echo["timing"] == "post-operative")].copy()
    echo["value"] = pd.to_numeric(echo["value"], errors="coerce")

    wanted = {
        "mean_gradient_mmhg": "mean_gradient_mmhg",
        "peak_gradient_mmhg": "peak_gradient_mmhg",
        "dvi": "dvi",
        "aortic_valve_area_cm2": "eoa_cm2",
        "lvef_percent": "lvef_pct",
    }
    numeric = echo[echo["item"].isin(wanted)].copy()
    numeric["field"] = numeric["item"].map(wanted)
    keys = ["patient", "note_id", "study_number", "year"]
    wide = numeric.pivot_table(index=keys, columns="field", values="value", aggfunc="median").reset_index()

    grades = echo[echo["item"] == "aortic_regurgitation_grade"].copy()
    extracted = grades["value"].astype(str).str.lower().str.extract(
        r"\b(none|trace|trivial|mild|moderate|severe)\b"
    )[0]
    grades["ar_grade"] = extracted.where(extracted != "trivial", "trace")
    wide = wide.merge(grades.groupby(keys)["ar_grade"].first().reset_index(), on=keys, how="left")

    for field in ("mean_gradient_mmhg", "peak_gradient_mmhg", "dvi", "eoa_cm2", "lvef_pct"):
        if field not in wide:
            wide[field] = np.nan
    if "ar_grade" not in wide:
        wide["ar_grade"] = pd.Series(pd.NA, index=wide.index, dtype="object")
    wide["ar_grade"] = wide["ar_grade"].astype("object")

    # Values outside physiological range are dropped, not clipped, and counted. An
    # abstraction that returns an aortic valve area above 3.5 cm2 has misread
    # something -- most often a different measurement on the same line -- and
    # clipping it to the boundary would convert a detectable error into a plausible
    # number. The count belongs in the extraction-quality report, not in silence.
    wide, dropped = _drop_implausible(wide)
    if dropped:
        _IMPLAUSIBLE.update(dropped)

    wide["implant_year"] = wide["patient"].map(implant_year)
    wide = wide[wide["implant_year"].notna()]
    elapsed = (wide["year"] - wide["implant_year"]).clip(lower=0)
    wide["days_from_implant"] = (elapsed * DAYS_PER_YEAR).round().astype(int)

    measured = ["mean_gradient_mmhg", "peak_gradient_mmhg", "dvi", "eoa_cm2", "lvef_pct", "ar_grade"]
    wide = wide[~wide[measured].isna().all(axis=1)]
    wide = wide.sort_values(["patient", "days_from_implant", "study_number"])
    wide["echo_id"] = [
        f"{p}-E{i + 1:02d}" for p, i in zip(wide["patient"], wide.groupby("patient").cumcount())
    ]

    # No examination here can be a VARC-3 reference study: the 30-to-90-day window
    # cannot be checked because exam dates were destroyed by de-identification.
    wide["is_reference"] = False
    return pd.DataFrame(
        {
            "patient_id": wide["patient"].values,
            "echo_id": wide["echo_id"].values,
            "days_from_implant": wide["days_from_implant"].values,
            "is_reference": wide["is_reference"].values,
            "mean_gradient_mmhg": wide["mean_gradient_mmhg"].values,
            "peak_gradient_mmhg": wide["peak_gradient_mmhg"].values,
            "dvi": wide["dvi"].values,
            "eoa_cm2": wide["eoa_cm2"].values,
            "ar_grade": wide["ar_grade"].values,
            "lvef_pct": wide["lvef_pct"].values,
            "source": "real",
            "time_resolution": "year",
        }
    ).reset_index(drop=True)


_IMPLAUSIBLE: Final[dict[str, int]] = {}
"""Count of measurements discarded for falling outside physiological range, by field.

Populated by :func:`to_schema` and reported by :func:`implausible_values`.
"""

_RANGES: Final[dict[str, tuple[float, float]]] = {
    "mean_gradient_mmhg": (0.0, 120.0),
    "peak_gradient_mmhg": (0.0, 200.0),
    "dvi": (0.05, 1.2),
    "eoa_cm2": (0.1, 3.5),
    "lvef_pct": (10.0, 80.0),
}


def _drop_implausible(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Null out measurements outside physiological range, returning the counts."""
    dropped: dict[str, int] = {}
    for field, (low, high) in _RANGES.items():
        if field not in frame:
            continue
        values = pd.to_numeric(frame[field], errors="coerce")
        outside = values.notna() & ~values.between(low, high)
        if int(outside.sum()):
            dropped[field] = int(outside.sum())
        frame[field] = values.where(~outside)
    return frame, dropped


def implausible_values() -> dict[str, int]:
    """Return how many measurements the last mapping discarded as out of range."""
    return dict(_IMPLAUSIBLE)


def _events(long: pd.DataFrame, implant_year: pd.Series) -> pd.DataFrame:
    """Build the event table.

    Only documented reintervention is asserted. Haemodynamic staging needs a
    reference examination the extract does not contain, and mortality is absent
    from it entirely, so neither deterioration stages nor the competing risk can be
    established without clinician adjudication.
    """
    notes = long[long["source"] == "notes"]
    reintervention = notes[notes["category"] == "reintervention on aortic valve"]

    rows = []
    for patient, group in reintervention.groupby("patient"):
        start = implant_year.get(patient)
        if pd.isna(start):
            continue
        year = int(group["year"].min())
        days = int(round(max(year - int(start), 0) * DAYS_PER_YEAR))
        rows.append(
            {
                "patient_id": patient,
                "event_type": "bvf_reintervention",
                "days_from_implant": days,
                "interval_start_days": days,
                "ascertainment": "reintervention",
            }
        )
    frame = pd.DataFrame(rows, columns=["patient_id", "event_type", "days_from_implant", "interval_start_days", "ascertainment"])
    return frame.assign(source="real", time_resolution="year")


def _followup(long: pd.DataFrame, implant_year: pd.Series, echos: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    """Build the follow-up table from the span of documentation, at year resolution."""
    notes = long[long["source"] == "notes"]
    last_year = notes.groupby("patient")["year"].max()
    counts = echos.groupby("patient_id").size()
    with_event = set(events["patient_id"])

    rows = []
    for patient, start in implant_year.items():
        if pd.isna(start):
            continue
        elapsed = max(int(last_year.get(patient, start)) - int(start), 0)
        rows.append(
            {
                "patient_id": patient,
                "last_contact_days": int(round(elapsed * DAYS_PER_YEAR)),
                "n_echos": int(counts.get(patient, 0)),
                # Never "death": the extract contains no mortality data, so a patient
                # whose documentation simply stops is administratively censored as far
                # as anything here can tell.
                "censoring_reason": "event" if patient in with_event else "administrative",
            }
        )
    return pd.DataFrame(rows).assign(source="real", time_resolution="year")


def to_schema(*, validate: bool = True) -> dict[str, pd.DataFrame]:
    """Map the supplied extract into the study schema.

    Args:
        validate: Check the result against :func:`synthetic.schema.validate_all`
            before returning. Leave it on; it is what guarantees the real and
            synthetic cohorts are actually comparable rather than merely similar.

    Returns:
        Mapping with keys ``patients``, ``echos``, ``events`` and ``followup``,
        every row carrying ``source = "real"`` and ``time_resolution = "year"``.

    Raises:
        SchemaError: If the mapping produces a frame the schema rejects.
        FileNotFoundError: If the extract is not in the derived data directory.
    """
    long = load_long()
    patients = _patients(long)
    implant_year = patients.set_index("patient_id")["implant_year"]

    echos = _echos(long, implant_year)
    events = _events(long, implant_year)
    followup = _followup(long, implant_year, echos, events)

    known = set(patients["patient_id"])
    tables = {
        "patients": patients,
        "echos": echos[echos["patient_id"].isin(known)].reset_index(drop=True),
        "events": events[events["patient_id"].isin(known)].reset_index(drop=True),
        "followup": followup[followup["patient_id"].isin(known)].reset_index(drop=True),
    }
    for name, frame in tables.items():
        tables[name] = frame.reindex(columns=list(TABLES[name].column_names))
    if validate:
        validate_all(tables)
    return tables
