"""Tests for the label, feature and matching code in ``pipeline``.

``synthetic/tests`` covers the cohort generator; this module covers what happens
to a cohort afterwards. The distinction matters because these are the functions
that also run on the private extract, where nothing can be checked by eye: a
defect here is invisible in the output and changes every number downstream.

Each test protects one promise made in the written deliverables:

* no feature may be derived from a record dated after its landmark
  (``protocol/study_protocol.md`` section 5),
* the synthetic cohort and the extract go through one route, and the conversion
  between the two reproduces the generator's own tables (``README.md``),
* a patient's follow-up ends once, at the first of event, death and last
  contact (``model/approach.md`` section 2),
* matching to the extract hides mortality, because the extract has none
  (``data/data_plan.md`` section 8).

The cohorts here are small and fixed-seed, so the suite runs in seconds::

    uv run python -m pytest notebooks/pipeline/tests -q
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from pipeline import landmarks, matching
from synthetic import generate

SEED = 20260917
N_PATIENTS = 300

OUTCOME_COLUMNS = {
    "time_to_end",
    "status",
    "svd_2y",
    "svd_5y",
    "svd_8y",
    "death_2y",
    "death_5y",
    "death_8y",
}


@pytest.fixture(scope="module")
def cohort():
    """A small ideal-rung cohort: serial echoes, dated events, deaths observed."""
    return generate(preset="ideal", seed=SEED, n_patients=N_PATIENTS)


@pytest.fixture(scope="module")
def prepared(cohort):
    """The same cohort in the shape ``02_preprocessing.ipynb`` writes for the extract."""
    return landmarks.synthetic_to_preprocessing(cohort)


# --------------------------------------------------------------------------- #
# No look-ahead                                                               #
# --------------------------------------------------------------------------- #


def _poison_echoes_after(cohort, landmark_years):
    """Return the cohort with every post-landmark echo value replaced by nonsense.

    Only the measurements are changed, never the timing: the examination still
    happens when it happened, so follow-up, censoring and event times are
    untouched and the only thing that can move a feature is the value itself.
    """
    tables = {name: frame.copy() for name, frame in cohort.items()}
    echos = tables["echos"]
    after = echos.days_from_implant > landmark_years * landmarks.DAYS_PER_YEAR
    echos.loc[after, "mean_gradient_mmhg"] = 999.0
    echos.loc[after, "peak_gradient_mmhg"] = 999.0
    echos.loc[after, "dvi"] = 0.01
    echos.loc[after, "eoa_cm2"] = 0.01
    echos.loc[after, "ar_grade"] = "severe"
    echos.loc[after, "lvef_pct"] = 5.0
    return tables, int(after.sum())


@pytest.mark.parametrize("landmark", [1.0, 3.0, 5.0])
def test_features_ignore_every_record_dated_after_the_landmark(cohort, landmark):
    """Poisoning the future must not move a single feature at the landmark.

    This is the mechanical form of the protocol's no-look-ahead rule. It is
    written behaviourally rather than by reading the filter, because the filter
    is one comparison in one function and the rule has to survive every future
    edit to the twenty features built around it.
    """
    config = dict(landmarks.LABEL_CONFIG, landmarks_years=(landmark,))
    clean, _ = landmarks.build_landmark_table(cohort, config)
    poisoned_tables, poisoned_rows = _poison_echoes_after(cohort, landmark)
    poisoned, _ = landmarks.build_landmark_table(poisoned_tables, config)

    assert poisoned_rows > 0, "nothing was poisoned, so the test proves nothing"
    features = [c for c in clean.columns if c not in OUTCOME_COLUMNS]
    pd.testing.assert_frame_equal(
        clean[features].sort_values("landmark_id").reset_index(drop=True),
        poisoned[features].sort_values("landmark_id").reset_index(drop=True),
    )


def test_poisoning_the_past_does_move_the_features(cohort):
    """The mirror image: the test above must be able to fail.

    A feature builder that silently returned constants would pass the
    look-ahead test. This one fails unless pre-landmark records are actually
    read.
    """
    landmark = 5.0
    config = dict(landmarks.LABEL_CONFIG, landmarks_years=(landmark,))
    clean, _ = landmarks.build_landmark_table(cohort, config)
    tables = {name: frame.copy() for name, frame in cohort.items()}
    before = tables["echos"].days_from_implant <= landmark * landmarks.DAYS_PER_YEAR
    tables["echos"].loc[before, "mean_gradient_mmhg"] = 999.0
    poisoned, _ = landmarks.build_landmark_table(tables, config)

    assert before.sum() > 0
    assert not clean.last_mg.equals(poisoned.last_mg)


def test_a_landmark_row_exists_only_for_a_patient_still_at_risk(cohort):
    """Landmark analysis conditions on survival to the landmark, event-free."""
    lm, outcomes = landmarks.build_landmark_table(cohort)
    end_years = outcomes.set_index("patient_id").end_years
    assert (lm.landmark_years < lm.patient_id.map(end_years)).all()
    assert (lm.time_to_end > 0).all()


# --------------------------------------------------------------------------- #
# Labels and censoring                                                        #
# --------------------------------------------------------------------------- #


def test_follow_up_ends_once_at_the_first_of_event_death_and_last_contact(cohort):
    outcomes = landmarks.build_outcomes(cohort)
    assert outcomes.patient_id.is_unique
    assert set(outcomes.status) <= {"svd", "death", "censored"}
    assert (outcomes.end_days >= 0).all()

    svd, death = outcomes.status.eq("svd"), outcomes.status.eq("death")
    assert outcomes.loc[svd, "endpoint_days"].notna().all()
    assert (outcomes.loc[svd, "end_days"] == outcomes.loc[svd, "endpoint_days"]).all()
    assert outcomes.loc[death, "death_days"].notna().all()
    assert (outcomes.loc[death, "end_days"] == outcomes.loc[death, "death_days"]).all()

    # Whatever the status, the end is the earliest of the three candidate times.
    earliest = np.minimum(
        np.minimum(outcomes.endpoint_days.fillna(np.inf), outcomes.death_days.fillna(np.inf)),
        outcomes.last_contact_days.astype(float),
    )
    assert (outcomes.end_days <= earliest + 1e-9).all()


def test_the_endpoint_is_the_first_qualifying_event_not_the_worst(cohort):
    """VARC-3 stage 3 usually follows stage 2 in the same valve; time to the
    endpoint is time to the first of them, or the deterioration would be dated
    to whenever the patient happened to be imaged again."""
    outcomes = landmarks.build_outcomes(cohort).set_index("patient_id")
    endpoints = landmarks.ENDPOINTS[landmarks.LABEL_CONFIG["endpoint"]]
    events = cohort["events"]
    first = (
        events[events.event_type.isin(endpoints)]
        .sort_values("days_from_implant")
        .groupby("patient_id")
        .days_from_implant.first()
    )
    observed = outcomes.loc[outcomes.status.eq("svd"), "endpoint_observed_days"]
    assert (observed == first.reindex(observed.index)).all()


def test_a_horizon_label_is_missing_only_when_follow_up_stops_before_the_horizon(cohort):
    lm, _ = landmarks.build_landmark_table(cohort)
    for horizon in landmarks.LABEL_CONFIG["horizons"]:
        label = lm[f"svd_{horizon}y"]
        censored_early = lm.status.eq("censored") & (lm.time_to_end < horizon)
        assert label.isna().equals(censored_early)
        assert (label[lm.status.eq("svd") & (lm.time_to_end <= horizon)] == 1.0).all()
        assert (label[lm.status.eq("death")] == 0.0).all()


def test_death_is_a_competing_event_and_never_a_censoring_time(cohort):
    """A patient who dies is not at risk afterwards, and is not counted as an
    SVD case at any horizon: the two indicator columns are mutually exclusive."""
    lm, _ = landmarks.build_landmark_table(cohort)
    for horizon in landmarks.LABEL_CONFIG["horizons"]:
        both = lm[f"svd_{horizon}y"].fillna(0) + lm[f"death_{horizon}y"].fillna(0)
        assert (both <= 1.0).all()


# --------------------------------------------------------------------------- #
# One route for real and synthetic data                                       #
# --------------------------------------------------------------------------- #


def test_the_round_trip_reproduces_the_generators_own_tables(cohort, prepared):
    """``synthetic -> preprocessing tables -> schema`` must be the identity.

    The claim in the README is that both data sources reach the model through
    the same code. That is only true if the conversion into the preprocessing
    shape and back loses nothing, so the round trip is checked row by row
    rather than in aggregate.
    """
    back = landmarks.from_preprocessing(prepared)

    assert list(back["patients"].patient_id) == list(cohort["patients"].patient_id)
    assert len(back["echos"]) == len(cohort["echos"])

    original_echo = cohort["echos"].set_index("echo_id").sort_index()
    returned_echo = back["echos"].set_index("echo_id").sort_index()
    for column in ["days_from_implant", "mean_gradient_mmhg", "dvi", "eoa_cm2", "lvef_pct"]:
        pd.testing.assert_series_equal(
            returned_echo[column].astype(float),
            original_echo[column].astype(float),
            check_names=False,
        )
    assert (returned_echo.ar_grade == original_echo.ar_grade).all()

    key = ["patient_id", "event_type"]
    original = cohort["events"]
    returned = back["events"]

    structural = ["patient_id", "event_type", "days_from_implant", "interval_start_days"]
    pd.testing.assert_frame_equal(
        returned[returned.event_type.ne("death")].sort_values(key)[structural].reset_index(drop=True),
        original[original.event_type.ne("death")].sort_values(key)[structural].reset_index(drop=True),
        check_dtype=False,
    )


def test_a_death_after_loss_to_follow_up_does_not_survive_the_round_trip(cohort, prepared):
    """And it must not, because no site would ever record it.

    The generator knows every death, including the ones that happen after a
    patient stops attending. The preprocessing tables hold what an abstractor
    could find in a chart, so a death dated after the last contact is invisible
    there and the patient is censored instead. This is the one place where the
    round trip is deliberately lossy, and the loss has to be exactly this and
    nothing else: a death *within* follow-up that went missing would silently
    remove a competing event and inflate every cumulative incidence.
    """
    back = landmarks.from_preprocessing(prepared)
    deaths = cohort["events"]
    deaths = deaths[deaths.event_type.eq("death")].groupby("patient_id").days_from_implant.min()
    last_contact = cohort["followup"].set_index("patient_id").last_contact_days

    observable = deaths[deaths <= last_contact.reindex(deaths.index)]
    returned = back["events"]
    returned = returned[returned.event_type.eq("death")].set_index("patient_id").days_from_implant

    assert set(returned.index) == set(observable.index)
    assert (returned.sort_index().to_numpy() == observable.sort_index().to_numpy()).all()

    dropped = deaths.index.difference(returned.index)
    assert len(dropped) > 0, "no death was dropped, so the test proves nothing"
    assert (deaths[dropped] > last_contact.reindex(dropped)).all()
    assert cohort["followup"].set_index("patient_id").censoring_reason[dropped].eq("dropout").all()


def test_the_round_trip_preserves_the_labels_the_model_is_fitted_on(cohort, prepared):
    """The round trip could preserve every row and still move a label, because
    labels are derived. This checks the derived objects, not the inputs."""
    direct = landmarks.build_outcomes(cohort).set_index("patient_id")
    round_tripped = landmarks.build_outcomes(landmarks.from_preprocessing(prepared)).set_index("patient_id")
    assert (direct.status == round_tripped.status.reindex(direct.index)).all()
    pd.testing.assert_series_equal(
        direct.end_days.astype(float),
        round_tripped.end_days.reindex(direct.index).astype(float),
        check_names=False,
    )


# --------------------------------------------------------------------------- #
# Matching the cohort to the extract                                          #
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def matched(prepared):
    """A cohort reshaped to its own profile.

    The profile normally comes from the private extract. Here it is measured on
    the cohort itself, which is the only version a reviewer without the extract
    can run: it exercises every masking rule, and leaves what each rule is
    matching *to* out of scope.
    """
    profile = matching.reference_profile(prepared)
    return matching.match_to_reference(prepared, profile)


def test_matching_leaves_no_death_anywhere(matched):
    """The extract contains no mortality data of any kind, so a cohort matched
    to it must not smuggle one in through a status, an event row or a label."""
    assert not matched["follow_up"].status.eq("death").any()

    tables = landmarks.from_preprocessing(matched)
    assert not tables["events"].event_type.eq("death").any()
    assert not tables["followup"].censoring_reason.eq("death").any()

    lm, outcomes = landmarks.build_landmark_table(tables)
    assert not outcomes.status.eq("death").any()
    for horizon in landmarks.LABEL_CONFIG["horizons"]:
        assert not lm[f"death_{horizon}y"].eq(1.0).any()


def test_matching_hides_age_and_collapses_time_to_the_year(matched):
    tables = landmarks.from_preprocessing(matched)
    assert tables["patients"].age_at_implant.isna().all()
    assert matched["time_resolution"] == "year"
    assert "days_from_implant" not in matched["echo_timeline"]

    # Year resolution means every echo lands on a whole year from implant once
    # converted back: the day of the examination is not recoverable.
    years = tables["echos"].days_from_implant / landmarks.DAYS_PER_YEAR
    assert np.allclose(years, years.round(), atol=1 / landmarks.DAYS_PER_YEAR)


def test_matching_only_ever_removes_information(prepared, matched):
    """Every matching rule masks, drops or censors. None of them may invent a
    patient, an examination or an event that the cohort did not have."""
    assert len(matched["implants"]) == len(prepared["implants"])
    assert len(matched["echo_timeline"]) <= len(prepared["echo_timeline"])
    assert len(matched["events"]) <= len(prepared["events"])
    assert set(matched["echo_timeline"].study_id) <= set(prepared["echo_timeline"].study_id)
    assert set(matched["events"].event_id) <= set(prepared["events"].event_id)

    svd_before = prepared["follow_up"].status.eq("svd").sum()
    svd_after = matched["follow_up"].status.eq("svd").sum()
    assert svd_after <= svd_before
