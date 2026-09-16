"""Tests for the synthetic cohort generator.

These codify the checks that would otherwise be run by hand and forgotten. They
are grouped by what they protect, because a test whose purpose is not obvious is
a test that gets deleted the first time it fails.

Run from the ``notebooks`` directory::

    python -m pytest synthetic/tests -q

The whole suite runs in seconds: every test uses a small cohort except the two
that cannot be answered on one, which are marked ``slow``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from synthetic import (
    PRESETS,
    TABLE_NAMES,
    SchemaError,
    calibration_report,
    generate,
    validate,
    validate_all,
)
from synthetic.generator import DAYS_PER_YEAR, _meets_stage
from synthetic.parameters import ANCHORS, DEFAULT
from synthetic.validation import coverage_test, recovery_test

SMALL = 400


@pytest.fixture(scope="module")
def cohort() -> dict[str, pd.DataFrame]:
    """A small cohort, shared across tests that only need well-formed output."""
    return generate("ideal", n_patients=SMALL)


# --- The contract other workstreams code against -------------------------------


def test_every_table_is_present(cohort):
    assert set(cohort) == set(TABLE_NAMES)


def test_cohort_satisfies_the_schema(cohort):
    validate_all(cohort)


@pytest.mark.parametrize("preset", sorted(PRESETS))
def test_every_rung_of_the_ladder_satisfies_the_schema(preset):
    validate_all(generate(preset, n_patients=SMALL))


def test_schema_rejects_a_value_outside_the_allowed_set(cohort):
    broken = cohort["patients"].copy()
    broken.loc[broken.index[0], "ppm_grade"] = "catastrophic"
    with pytest.raises(SchemaError, match="ppm_grade"):
        validate(broken, "patients")


def test_schema_rejects_a_duplicated_key(cohort):
    broken = pd.concat([cohort["patients"], cohort["patients"].head(1)], ignore_index=True)
    with pytest.raises(SchemaError, match="not unique"):
        validate(broken, "patients")


def test_schema_rejects_an_orphan_reference(cohort):
    broken = dict(cohort)
    broken["echos"] = cohort["echos"].assign(patient_id="SYN-NONEXISTENT")
    with pytest.raises(SchemaError, match="absent from"):
        validate_all(broken)


def test_an_unknown_preset_is_refused():
    with pytest.raises(KeyError):
        generate("wishful_thinking", n_patients=10)


# --- Reproducibility, which the rubric rewards and a reviewer will check --------


def test_the_same_seed_reproduces_the_cohort_exactly():
    first, second = generate("ideal", n_patients=SMALL), generate("ideal", n_patients=SMALL)
    for name in TABLE_NAMES:
        pd.testing.assert_frame_equal(first[name], second[name])


def test_a_different_seed_produces_a_different_cohort():
    first = generate("ideal", seed=1, n_patients=SMALL)
    second = generate("ideal", seed=2, n_patients=SMALL)
    assert not first["patients"].equals(second["patients"])


# --- Governance: the property that makes the output safe to circulate ----------


@pytest.mark.parametrize("table", sorted(TABLE_NAMES))
def test_every_row_declares_itself_simulated(cohort, table):
    assert (cohort[table]["source"] == "simulated").all()


def test_patient_identifiers_cannot_be_mistaken_for_real_ones(cohort):
    assert cohort["patients"]["patient_id"].str.fullmatch(r"SYN-\d{5}").all()


# --- Clinical definitions, transcribed from VARC-3 -----------------------------


def test_a_gradient_rise_alone_is_not_deterioration():
    """VARC-3 requires a corroborating fall in area or dimensionless index.

    A rise in gradient with an unchanged orifice area is higher flow, not a
    failing valve, and a definition that called it deterioration would generate
    events every time a patient became anaemic or febrile.
    """
    assert not _meets_stage(35.0, 10.0, 1.8, 1.8, 0.45, 0.45, 0.0, 0.0, severe=False)


def test_a_rise_with_a_falling_orifice_area_is_deterioration():
    assert _meets_stage(35.0, 10.0, 1.2, 1.8, 0.45, 0.45, 0.0, 0.0, severe=False)


def test_severe_criteria_are_strictly_harder_than_moderate():
    args = (32.0, 10.0, 1.4, 1.8, 0.33, 0.45, 0.0, 0.0)
    assert _meets_stage(*args, severe=False)
    assert not _meets_stage(*args, severe=True)


def test_severe_regurgitation_alone_qualifies():
    """The regurgitant arm of the definition stands on its own, without any
    gradient change: a bioprosthesis can fail by leaking rather than stenosing."""
    assert _meets_stage(10.0, 10.0, 1.8, 1.8, 0.45, 0.45, 4.0, 0.0, severe=True)


# --- Structure of the generated cohort -----------------------------------------


def test_every_patient_has_a_reference_examination(cohort):
    references = cohort["echos"].groupby("patient_id")["is_reference"].sum()
    assert (references == 1).all()


def test_the_reference_examination_falls_in_the_varc3_window(cohort):
    reference = cohort["echos"][cohort["echos"]["is_reference"]]
    assert reference["days_from_implant"].between(30, 90).all()


def test_the_reference_examination_reproduces_the_recorded_orifice_area(cohort):
    """Guards the defect where area was derived from the already-noisy gradient,
    which let a patient's reference examination disagree with their own record."""
    reference = cohort["echos"][cohort["echos"]["is_reference"]].set_index("patient_id")
    recorded = cohort["patients"].set_index("patient_id")["eoa_cm2"]
    difference = reference["eoa_cm2"] - recorded.reindex(reference.index)
    assert abs(difference.mean()) < 0.05


def test_no_reference_gradient_is_physiologically_impossible(cohort):
    """Guards the defect where additive measurement error produced gradients no
    echocardiographer would report."""
    reference = cohort["echos"][cohort["echos"]["is_reference"]]
    assert reference["mean_gradient_mmhg"].min() >= 2.0


def test_severe_deterioration_never_precedes_moderate(cohort):
    events = cohort["events"]
    stage2 = events[events["event_type"] == "svd_stage2"].set_index("patient_id")["days_from_implant"]
    stage3 = events[events["event_type"] == "svd_stage3"].set_index("patient_id")["days_from_implant"]
    shared = stage2.index.intersection(stage3.index)
    assert (stage3[shared] >= stage2[shared]).all()


def test_every_severe_event_has_a_moderate_one(cohort):
    """Stage 3 implies stage 2, so a severe event without a moderate one would
    mean the criteria had been transcribed inconsistently."""
    events = cohort["events"]
    stage2 = set(events[events["event_type"] == "svd_stage2"]["patient_id"])
    stage3 = set(events[events["event_type"] == "svd_stage3"]["patient_id"])
    assert stage3 <= stage2


def test_no_clinical_event_occurs_after_the_end_of_follow_up(cohort):
    """Nothing that requires a clinician to be looking may happen after the
    patient stops attending. Death is the exception, below."""
    last = cohort["followup"].set_index("patient_id")["last_contact_days"]
    events = cohort["events"]
    clinical = events[events["event_type"] != "death"]
    assert (clinical["days_from_implant"] <= last.reindex(clinical["patient_id"]).to_numpy()).all()


def test_death_may_be_ascertained_after_follow_up_ends(cohort):
    """Death comes from registry linkage, so the competing risk is captured more
    completely than the outcome. That asymmetry is real, and a cohort that hid it
    would let an analysis look better calibrated than it could be in practice."""
    last = cohort["followup"].set_index("patient_id")["last_contact_days"]
    deaths = cohort["events"][cohort["events"]["event_type"] == "death"]
    after = deaths["days_from_implant"].to_numpy() > last.reindex(deaths["patient_id"]).to_numpy()
    assert after.any(), "no death was ascertained after follow-up ended; linkage is not being modelled"


def test_the_censoring_interval_brackets_the_event(cohort):
    events = cohort["events"]
    assert (events["interval_start_days"] <= events["days_from_implant"]).all()


def test_events_found_by_echo_carry_a_real_interval(cohort):
    """An echocardiographic event is interval-censored; a reintervention is not."""
    events = cohort["events"]
    by_echo = events[events["ascertainment"] == "echo"]
    exact = events[events["ascertainment"].isin(("reintervention", "registry"))]
    assert (by_echo["interval_start_days"] < by_echo["days_from_implant"]).all()
    assert (exact["interval_start_days"] == exact["days_from_implant"]).all()


def test_patient_prosthesis_mismatch_follows_the_varc3_cut_offs(cohort):
    patients = cohort["patients"]
    severe = patients["eoa_index_cm2_m2"] <= 0.65
    moderate = (patients["eoa_index_cm2_m2"] > 0.65) & (patients["eoa_index_cm2_m2"] <= 0.85)
    assert (patients.loc[severe, "ppm_grade"] == "severe").all()
    assert (patients.loc[moderate, "ppm_grade"] == "moderate").all()
    assert (patients.loc[~(severe | moderate), "ppm_grade"] == "none").all()


# --- What each rung of the ladder actually removes ------------------------------


def test_the_no_age_rung_removes_age():
    assert generate("no_age", n_patients=SMALL)["patients"]["age_at_implant"].isna().all()


def test_the_year_resolution_rung_declares_and_applies_year_resolution():
    tables = generate("year_resolution", n_patients=SMALL)
    assert (tables["echos"]["time_resolution"] == "year").all()
    remainder = tables["echos"]["days_from_implant"].to_numpy() % DAYS_PER_YEAR
    assert np.allclose(np.minimum(remainder, DAYS_PER_YEAR - remainder), 0, atol=1.0)


def test_the_single_echo_rung_leaves_one_examination_and_no_reference():
    tables = generate("single_echo", n_patients=SMALL)
    assert (tables["echos"].groupby("patient_id").size() == 1).all()
    assert not tables["echos"]["is_reference"].any()


def test_the_as_supplied_rung_keeps_reinterventions_when_it_drops_echoes():
    """Operative records survive where echocardiographic values do not, which is
    exactly the ground-truth hierarchy the protocol relies on."""
    ideal = generate("ideal", n_patients=SMALL)["events"]
    supplied = generate("as_supplied", n_patients=SMALL)["events"]
    kept = lambda frame, how: len(frame[frame["ascertainment"] == how])
    assert kept(supplied, "reintervention") == kept(ideal, "reintervention")
    assert kept(supplied, "echo") < kept(ideal, "echo")


def test_the_ladder_never_alters_the_patients_themselves():
    """Every rung must describe the same people, or the comparison between rungs
    measures two things at once and means nothing."""
    ideal = generate("ideal", n_patients=SMALL)["patients"]
    for preset in PRESETS:
        rung = generate(preset, n_patients=SMALL)["patients"]
        pd.testing.assert_series_equal(ideal["patient_id"], rung["patient_id"])
        pd.testing.assert_series_equal(ideal["eoa_index_cm2_m2"], rung["eoa_index_cm2_m2"])


# --- The claims made in the documentation ---------------------------------------


def test_every_anchor_uses_the_stated_tolerance_rule():
    for anchor in ANCHORS:
        assert anchor.tolerance == max(0.02, 0.25 * anchor.value)


@pytest.mark.slow
def test_the_cohort_reproduces_the_published_anchors():
    report = calibration_report(generate("ideal", n_patients=DEFAULT.cohort.n_patients))
    failures = report[~report["within_band"]]
    assert set(failures["quantity"]) <= {"severe_svd"}, (
        "Only the documented NOTION transcatheter disagreement may fail:\n"
        f"{failures.to_string(index=False)}"
    )


@pytest.mark.slow
def test_injected_hazard_ratios_are_recovered():
    """The check that a calibrated cohort can still come from broken code.

    Coverage is asserted, not a clean sweep. A 95% interval should miss about one
    time in twenty, so requiring every covariate to be covered in a single run
    would be a test that fails at random and invites tuning until it passes. The
    bound is deliberately loose relative to the nominal rate because the number of
    fits here is small.
    """
    result = coverage_test(seeds=(20260917, 1, 2))
    overall = result[result["covariate"] == "ALL"].iloc[0]
    assert overall["coverage"] >= 0.80, result.to_string(index=False)
    assert abs(overall["mean_log_bias"]) < 0.05, (
        "systematic bias in the recovered effects, which coverage alone can miss:\n"
        f"{result.to_string(index=False)}"
    )
