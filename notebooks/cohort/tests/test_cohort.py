"""Tests for the real-data half of the ladder.

Every test here needs the private extract, which is not in the repository and
never will be. They skip cleanly when it is absent, so that a reviewer with no
access to the data can still run the rest of the suite and reproduce every
synthetic rung.

Most of these assert **absences**. That is deliberate: the failure mode this
mapping has to be protected against is not a crash but a quiet invention -- an age
imputed, a death assumed, a gradient clipped into plausibility. Each of those would
make the real cohort look better than it is, and the ladder's whole value is that
its bottom rung is honest about what was missing.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import pytest

from synthetic import TABLE_NAMES, validate_all

try:
    from cohort.ladder import RUNGS, availability
    from cohort.to_schema import implausible_values, to_schema

    _TABLES = to_schema()
except (FileNotFoundError, ImportError) as error:  # pragma: no cover - depends on the machine
    pytest.skip(f"private extract unavailable: {error}", allow_module_level=True)


@pytest.fixture(scope="module")
def real() -> dict[str, pd.DataFrame]:
    return _TABLES


# --- The contract: the real cohort must satisfy the same schema as the synthetic one.


def test_the_real_cohort_satisfies_the_study_schema(real):
    validate_all(real)


def test_it_has_every_table(real):
    assert set(real) == set(TABLE_NAMES)


@pytest.mark.parametrize("table", sorted(TABLE_NAMES))
def test_every_row_declares_real_provenance_at_year_resolution(real, table):
    assert (real[table]["source"] == "real").all()
    assert (real[table]["time_resolution"] == "year").all()


def test_real_patients_cannot_be_mistaken_for_synthetic_ones(real):
    assert not real["patients"]["patient_id"].str.startswith("SYN-").any()


# --- Absences, which must survive the mapping rather than being filled in.


def test_age_is_absent_for_every_patient(real):
    """Redacted in the source. An imputed age would be the single most damaging
    invention here, because age is the strongest published predictor."""
    assert real["patients"]["age_at_implant"].isna().all()


def test_no_death_is_asserted(real):
    """The extract carries no mortality data at all. Asserting a death, or treating
    an absence of notes as survival, would make the competing risk look observed."""
    assert not (real["events"]["event_type"] == "death").any()
    assert not (real["followup"]["censoring_reason"] == "death").any()


def test_events_are_limited_to_documented_reintervention(real):
    """Haemodynamic staging needs a reference examination the extract lacks, so no
    deterioration stage may be asserted from it without clinician adjudication."""
    assert set(real["events"]["event_type"]) <= {"bvf_reintervention"}
    assert (real["events"]["ascertainment"] == "reintervention").all()


def test_no_examination_claims_to_be_a_varc3_reference(real):
    """The 30-to-90-day window cannot be verified: exam dates were destroyed."""
    assert not real["echos"]["is_reference"].any()


def test_implausible_measurements_are_discarded_rather_than_clipped(real):
    """Clipping an out-of-range value to the boundary turns a detectable extraction
    error into a plausible number. They are nulled, and counted."""
    counts = implausible_values()
    assert isinstance(counts, dict)
    for field, limit in (("eoa_cm2", 3.5), ("mean_gradient_mmhg", 120.0)):
        values = real["echos"][field].dropna()
        assert values.empty or values.max() <= limit
        assert not (values == limit).any() or field not in counts


def test_every_examination_reports_something(real):
    measured = ["mean_gradient_mmhg", "peak_gradient_mmhg", "dvi", "eoa_cm2", "ar_grade", "lvef_pct"]
    assert not real["echos"][measured].isna().all(axis=1).any()


def test_events_and_examinations_reference_known_patients(real):
    known = set(real["patients"]["patient_id"])
    for table in ("echos", "events", "followup"):
        assert set(real[table]["patient_id"]) <= known


# --- The ladder, and the comparison that justifies including the real rung.


def test_the_ladder_ends_with_the_real_cohort():
    assert RUNGS[-1] == "as_received"
    assert len(RUNGS) == 6


def test_the_simulated_bottom_rung_reproduces_the_real_one():
    """The point of the last rung is to check the second-to-last one.

    Data availability in the simulation of the extract should resemble the extract.
    The tolerance is loose because the two cohorts are not the same people; what
    would be a failure is a qualitative mismatch, such as the simulation retaining
    examinations for twice as many patients.
    """
    table = availability(n_patients=117).set_index("rung")
    simulated, received = table.loc["as_supplied"], table.loc["as_received"]
    assert abs(simulated["any_echo_pct"] - received["any_echo_pct"]) < 10
    assert abs(simulated["echos_per_patient"] - received["echos_per_patient"]) < 0.5
    # Written out rather than chained: `a == b is False` means `(a == b) and (b is
    # False)`, and a numpy boolean is never the `False` singleton.
    assert not simulated["death_observed"]
    assert not received["death_observed"]
    assert simulated["age_known_pct"] == 0.0
    assert received["age_known_pct"] == 0.0


def test_data_availability_falls_monotonically_down_the_ladder():
    """Each rung must be at least as impoverished as the one above it, or the ladder
    is not a ladder and a difference in model performance between two rungs cannot
    be attributed to the defect that separates them."""
    table = availability(n_patients=117)
    for column in ("age_known_pct", "device_known_pct", "any_echo_pct", "day_resolution_pct"):
        values = table[column].tolist()
        assert values == sorted(values, reverse=True), f"{column} is not monotone: {values}"


# --- The committed report is the one artefact a stranger reads ------------------


def test_the_committed_report_carries_no_identifier_or_note_text():
    """``results.md`` is committed to a repository that may be public.

    Its own header promises that no patient-level value, note text or identifier
    appears in it, and that promise is the reason it can be committed at all. Every
    figure in it is produced by aggregation, so the promise should hold by
    construction -- but "by construction" is exactly the kind of guarantee that
    stops holding the first time someone adds a table of examples to the report
    generator. This asserts it against the file itself.
    """
    report = Path(__file__).resolve().parents[3] / "data" / "synthetic" / "results.md"
    assert report.exists(), report
    text = report.read_text()

    real_ids = set(_TABLES["patients"]["patient_id"].astype(str))
    leaked = sorted(i for i in real_ids if i in text)
    assert not leaked, f"identifiers from the extract appear in the committed report: {leaked[:5]}"

    for token in ("[DATE]", "[NAME]", "[AGE]", "[ID]", "[LOCATION]", "[FACILITY]"):
        assert token not in text, f"redaction token {token} implies note text was pasted in"

    assert not re.search(r"\bPatient_\d+\b", text), "a patient identifier pattern appears in the report"
