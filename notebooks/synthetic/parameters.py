"""Parameters of the generative model, each carrying its published source.

Every number a synthetic cohort depends on lives here rather than inside the
generator, for two reasons. A reviewer can audit the entire evidence base of the
cohort by reading one file. And the degradation ladder can vary a parameter set
without touching generator code, which keeps its rungs genuinely comparable.

Where a value is an assumption rather than a published estimate it is marked
ASSUMPTION, with the reasoning. Distinguishing the two is the difference between
a calibrated cohort and an invented one.

A note on what calibration means here. Two parameters -- the Weibull scales of
the deterioration hazard, one per approach -- are **solved numerically** so that
the cohort reproduces the NOTION 10-year moderate-or-severe deterioration
figures. Every other anchor in :data:`ANCHORS` is then an **out-of-sample check**:
it was never targeted, and if the cohort reproduces it, that is evidence the
generating process is shaped correctly rather than merely fitted at one point.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Final

__all__ = [
    "Anchor",
    "ANCHORS",
    "CohortParameters",
    "HazardParameters",
    "EchoParameters",
    "VisitParameters",
    "Parameters",
    "DEFAULT",
]


ABSOLUTE_TOLERANCE: Final[float] = 0.02
RELATIVE_TOLERANCE: Final[float] = 0.25


@dataclass(frozen=True, slots=True)
class Anchor:
    """A published quantity the synthetic cohort is compared against."""

    quantity: str
    subgroup: str
    horizon_years: float
    value: float
    """Cumulative incidence as a proportion."""
    source: str
    targeted: bool = False
    """True if a parameter was solved to match this anchor; False makes it an
    out-of-sample check."""

    @property
    def tolerance(self) -> float:
        """Half-width of the band inside which the cohort is called calibrated.

        Computed from one rule applied uniformly to every anchor, stated before any
        cohort was generated: **two percentage points, or a quarter of the published
        value, whichever is larger**.

        A per-anchor tolerance chosen by hand is not a standard, it is a description
        of the result. The absolute floor keeps small published proportions from
        demanding an impossible precision; the relative term keeps large ones from
        being trivially satisfied. Anchors this cohort fails under this rule are
        reported as failures.
        """
        return max(ABSOLUTE_TOLERANCE, RELATIVE_TOLERANCE * self.value)


ANCHORS: Final[tuple[Anchor, ...]] = (
    # Every figure below was verified against the primary publication in September
    # 2026, not taken from a secondary summary. NOTION estimated its rates with the
    # Aalen-Johansen method under a competing risk of death, which is the estimator
    # used here, so the comparison is like for like.

    # --- Targeted: parameters were solved against these three rows. ---
    Anchor(
        "moderate_or_severe_svd", "SAVR", 10.0, 0.208,
        "NOTION 10-year outcomes, Eur Heart J 2024;45:1116 (n=280; 135 SAVR)", targeted=True,
    ),
    Anchor(
        "moderate_or_severe_svd", "TAVR", 10.0, 0.154,
        "NOTION 10-year outcomes, Eur Heart J 2024;45:1116 (n=280; 145 TAVI)", targeted=True,
    ),
    Anchor(
        "all_cause_death", "TAVR", 10.0, 0.627,
        "NOTION 10-year all-cause mortality, transcatheter arm (mean age ~79)", targeted=True,
    ),

    # --- Out-of-sample: never targeted, never used to select a parameter. ---
    Anchor(
        "severe_svd", "SAVR", 10.0, 0.100,
        "NOTION, severe structural valve deterioration at 10 years",
    ),
    Anchor(
        "severe_svd", "TAVR", 10.0, 0.015,
        "NOTION, severe SVD at 10 years (1.5% of 145 patients is about 2 events)",
    ),
    Anchor(
        "bioprosthetic_valve_failure", "all", 5.0, 0.036,
        "PARTNER 3 at 5 years: 3.3% transcatheter, 3.8% surgical",
    ),
    Anchor(
        "bioprosthetic_valve_failure", "all", 7.0, 0.072,
        "PARTNER 3 at 7 years: 6.9% transcatheter, 7.5% surgical",
    ),
    Anchor(
        "severe_svd", "TAVR", 7.8, 0.059,
        "UK TAVI registry, severe SVD in 13 of 221 at a median of 7.8 years "
        "(a crude proportion, not a competing-risk estimate)",
    ),
    # These two were found in the NOTION paper AFTER every parameter had been
    # fixed, while verifying the figures above. They were not used to choose
    # anything, and they are the closest this calibration comes to a holdout.
    Anchor(
        "bioprosthetic_valve_failure", "TAVR", 10.0, 0.097,
        "NOTION, bioprosthetic valve failure at 10 years (found post hoc)",
    ),
    Anchor(
        "bioprosthetic_valve_failure", "SAVR", 10.0, 0.138,
        "NOTION, bioprosthetic valve failure at 10 years (found post hoc)",
    ),
)
"""Published anchors the cohort is checked against.

The two NOTION moderate-or-severe rows are targeted by the scale solver. The rest
are checks. Tolerances follow the single rule in :attr:`Anchor.tolerance`, stated before any
cohort existed and applied uniformly. They are wider than a trial's confidence
interval on purpose: the synthetic cohort's age mix is deliberately *not*
NOTION's, because a real-world cohort spans a far wider age range than a
randomised trial of intermediate-risk patients. A cohort matching NOTION exactly
would be a cohort that had been forced to.
"""


@dataclass(frozen=True, slots=True)
class CohortParameters:
    """Composition of the cohort at implant."""

    n_patients: int = 1800
    """Protocol sample size: ~1,800 implants for ~190 events (Riley et al. 2019)."""

    savr_fraction: float = 0.55
    """ASSUMPTION. Contemporary mixed practice.

    The prototype extract is more surgical than this: 73 of its 117 patients had a
    surgical implant against 43 transcatheter, about 63/37. That is a property of
    how the notes were sampled -- operative reports from a cardiac surgery service
    -- rather than of the practice being modelled, so the cohort is not matched to
    it. The fraction matters mainly because the two arms differ in age by a decade,
    and the calibration is checked separately within each arm."""

    # Age. TAVR recipients are substantially older than SAVR recipients; the gap
    # is the single largest structural difference between the two populations and
    # drives most of the apparent durability difference in observational series.
    age_mean_savr: float = 68.0
    age_sd_savr: float = 9.5
    age_mean_tavr: float = 79.5
    age_sd_tavr: float = 7.0
    """ASSUMPTION, shaped to contemporary registry practice; the TAVR mean matches
    the NOTION cohort age of about 79."""
    age_min: float = 50.0
    age_max: float = 95.0

    female_fraction: float = 0.45
    """ASSUMPTION, consistent with reported AVR series."""

    bsa_mean_male: float = 1.98
    bsa_sd_male: float = 0.18
    bsa_mean_female: float = 1.72
    bsa_sd_female: float = 0.16
    """ASSUMPTION. Body surface area matters only through the indexed effective
    orifice area, which is what patient-prosthesis mismatch is defined on."""

    anticoagulation_prevalence: float = 0.28
    """ASSUMPTION. The share of recipients on an oral anticoagulant, usually for
    atrial fibrillation rather than for the valve itself. It protects against the
    pannus and thrombosis mode and against nothing else, which is what makes it a
    covariate that separates one failure mode from the others rather than another
    reading of overall frailty."""

    diabetes_prevalence: float = 0.30
    ckd_prevalence: float = 0.20
    smoking_prevalence: float = 0.15
    bicuspid_prevalence_savr: float = 0.22
    bicuspid_prevalence_tavr: float = 0.06
    """ASSUMPTION, taken from the literature rather than from the extract, whose
    native morphology is mostly unrecorded: the abstraction adjudicates bicuspid
    anatomy in 10 of its 117 patients and tricuspid in 8, leaving 99 unknown, and 18
    patients have the word bicuspid or unicuspid somewhere in a note. Bicuspid
    anatomy is commoner in the younger surgical population, which is the direction
    these two values express."""

    implant_year_first: int = 2010
    implant_year_last: int = 2024

    savr_models: tuple[tuple[str, float], ...] = (
        ("Trifecta", 0.34), ("Perimount", 0.30), ("Epic", 0.14),
        ("Magna", 0.12), ("Inspiris", 0.10),
    )
    tavr_models: tuple[tuple[str, float], ...] = (
        ("Sapien 3", 0.72), ("Evolut", 0.28),
    )
    """Model mix follows the prototype extract, where Trifecta and Perimount
    dominated the surgical valves and Sapien the transcatheter ones."""


@dataclass(frozen=True, slots=True)
class HazardParameters:
    """Latent deterioration and competing-death hazards.

    Deterioration is modelled as **three competing failure modes**, each with its
    own Weibull hazard, its own covariates and its own echo signature. A valve may
    reach any of them, and the earliest one it reaches is what a clinician sees.

    ==============  ====================================  ===========================
    mode            echo signature                        driven by
    ==============  ====================================  ===========================
    calcific        gradient up, EOA down, DVI down       age, PPM, BSA, smoking,
                                                          diabetes, renal disease
    tear            regurgitation up, gradient flat       valve size, TAVR, bicuspid
    pannus          gradient up, EOA down, early          no anticoagulation, small
                                                          valve, SAVR
    ==============  ====================================  ===========================

    Why three rather than one: with a single latent onset driving every
    observable, the gradient, the area, the regurgitation grade, the ejection
    fraction and even the visit schedule were all noisy readings of the same
    hidden variable. Anything could be dropped without loss, so no analysis run on
    the cohort could attribute performance to a data channel -- which is the one
    question the degradation ladder exists to answer.

    Only the calcific mode keeps an accelerating shape. Calcification is
    cumulative, so its hazard rises with time in the valve; a tear is a mechanical
    event and pannus an ingrowth, and neither needs years of deposition first.
    """

    # ------------------------------------------------------------------
    # Process 1: calcific stenosis. The dominant late process.
    # ------------------------------------------------------------------

    svd_shape: float = 2.0
    """Shape of the late calcific process, comfortably above 1 so that its hazard
    accelerates with time in the valve. This is the defining feature of structural
    valve deterioration: leaflet calcification is cumulative, and a constant-hazard
    model is the wrong shape for it."""

    # ------------------------------------------------------------------
    # Process 2: leaflet tear or prolapse. The regurgitant failure mode.
    # ------------------------------------------------------------------

    tear_shape: float = 1.15
    """Close to a constant hazard. A tear is a mechanical failure of a leaflet
    under cyclic load; unlike calcification it does not need years of mineral
    deposition to become possible, so its hazard is nearly flat rather than
    accelerating."""

    tear_scale_years: float = 120.0
    """ASSUMPTION. This is where the cohort's *early* failure comes from, and it is
    set deliberately rather than left at a round number. Shortened from 150 once it
    was measured that early failure has to come from somewhere: see
    :attr:`pannus_scale_years` for the alternative that was tried and rejected.

    Why this process rather than the other flat-hazard one. Both can supply
    failures inside five years, but a tear announces itself -- regurgitation climbs
    while the gradient *falls* -- and it answers to covariates the data actually
    carry, including valve family. Pannus obstructs exactly as calcification does
    and answers to almost nothing. Measured on the model: moving early mass from
    pannus to tear was worth 0.023 of five-year AUC and 0.049 of precision at a 10%
    alert budget. A synthetic cohort whose early failures are unattributable
    teaches a model nothing and measures nothing.

    The realised shares, reported by
    :func:`synthetic.validation.failure_mode_shares`, are 62 / 32 / 6 of
    moderate-or-worse deterioration and 47 / 46 / 7 of severe deterioration,
    calcific / tear / pannus -- not the 70 / 20 / 10 originally intended.

    That drift is a real tension and worth stating plainly rather than hiding.
    PARTNER 3 reports 3.6% bioprosthetic valve failure at five years while NOTION
    reports 20.8% moderate-or-severe deterioration at ten, and an accelerating
    calcific process with a shape of 2 cannot produce both: whatever fails inside
    five years must come from a process whose hazard is already meaningful at year
    two. The shares are an assumption, the anchors are published data, so the
    anchors win. The honest way to recover the balance is not to retune these two
    numbers but to give the calcific process its own early, identifiable component
    -- accelerated calcification in renal failure and hyperparathyroidism is well
    described -- which is recorded as the next extension rather than done here.

    What the cohort does preserve is the clinically meaningful gradient: calcific
    degeneration dominates *moderate* deterioration and arrives late (median 7.1
    years), while tear is a third of deterioration but nearly half of outright
    failure and arrives early (median 5.0 years)."""

    hr_tear_by_family: tuple[tuple[str, float], ...] = (("Trifecta", 3.20),)
    hr_calcific_by_family: tuple[tuple[str, float], ...] = (("Trifecta", 1.60),)
    """Device-specific durability, entered on the mode the device actually fails by.

    Families not listed here carry 1.0. Only the Trifecta is listed, because it is
    the only family in this cohort with a regulatory signal behind it: the FDA
    issued a safety communication in 2023 on early structural deterioration
    peaking at three to four years, Abbott withdrew the valve from US sale in July
    2023, and a surgical series reports reoperation of 16.9% at eight years against
    3.8% for the Perimount.

    Most of the weight goes on the tear mode rather than on calcification, because
    the reported mechanism is commissural leaflet tear in an externally mounted
    pericardial design, not accelerated mineralisation. Entering it this way is the
    point of having named modes at all: a device effect that acts through one
    mechanism produces a different echo signature from one that acts through
    another, and a model that reads only the gradient will miss it.

    ASSUMPTION on the magnitude, and a deliberately conservative one. Taken at face
    value the reoperation series implies an overall hazard ratio near 4.8; the
    values here are set below that because the evidence is contested -- a
    propensity-matched series from the Cleveland Clinic (2,298 Trifecta against
    Perimount) reported 100% freedom from structural deterioration at five years.
    The realised overall effect is reported by
    :func:`synthetic.calibration.incidence_by_family`, and it is the quantity to
    quote, not these two multipliers.

    The haemodynamic table in the generator is deliberately NOT changed to match.
    The Trifecta has the largest effective orifice area of any surgical valve here,
    which is correct and is the clinically interesting part: best gradients at
    implant, worst durability afterwards. A cohort that encodes only the first half
    teaches a model the opposite of the truth."""

    hr_tear_per_mm: float = 1.10
    hr_tear_tavr: float = 1.30
    hr_tear_bicuspid: float = 1.35
    """ASSUMPTIONS in the direction the literature reports, and **deliberately a
    different covariate set from the calcific process**.

    Tearing is mechanical, not metabolic: it is not driven by diabetes, renal
    disease or smoking, and it does not carry the strong inverse age effect that
    calcification does. Larger leaflets carry more load per unit thickness,
    transcatheter leaflets are thinner and crimped before deployment, and a
    bicuspid annulus deploys the frame elliptically.

    That the two processes answer to different covariates is the point of
    separating them. While one latent process drove every observable, the patient
    covariates, the valve covariates and every echo channel were noisy copies of
    one hidden variable: a model could drop any of them and lose nothing."""

    # ------------------------------------------------------------------
    # Process 3: pannus or valve thrombosis. The early obstructive mode.
    # ------------------------------------------------------------------

    pannus_shape: float = 1.10
    pannus_scale_years: float = 420.0
    """ASSUMPTION. Fibrous pannus ingrowth and leaflet thrombosis both obstruct
    without calcifying, and both appear earlier than calcific degeneration. They
    are modelled as one process because their echo signature and their management
    are the same; what separates them from calcification clinically is that they
    respond to anticoagulation.

    **This value was shortened to 200 and then put back, and the reason is worth
    keeping.** At 200 the mode reached 23% of severe deterioration and the cohort
    hit the early bioprosthetic-failure anchors comfortably -- but five-year AUC
    fell by 0.023 and precision at a 10% alert budget by 0.049, the largest single
    loss of any change made to this generator. Pannus is the least identifiable
    mode by construction: its hazard is nearly flat, so its timing is close to
    random; it answers to three weak covariates; and its echo signature -- gradient
    up, area down -- is the same as calcification's, so a model cannot even tell
    the two apart after the fact. Filling the early window with it buys the anchor
    and pays for it in unattributable noise. The early mass belongs on
    :attr:`tear_scale_years`, which is identifiable, and that is where it now sits.

    That this mode is hard to predict is not a flaw in the simulation. Pannus and
    subclinical thrombosis are genuinely poorly predicted in clinic, which is
    precisely why anticoagulation is the covariate worth having: it is the one
    handle there is."""

    hr_pannus_no_anticoagulation: float = 1.43
    """The reciprocal of the protective HR 0.70 that registries report for
    anticoagulation. Entered on the exposed side, since the generator draws
    anticoagulation as a covariate rather than treating its absence as baseline."""

    hr_pannus_per_mm: float = 0.88
    hr_pannus_savr: float = 1.50
    """ASSUMPTIONS. A smaller orifice is obstructed by less tissue, and pannus is
    predominantly reported around a sewing ring, so it is more a surgical than a
    transcatheter phenomenon."""

    pannus_progression_multiplier: float = 4.5
    """Once obstruction begins it progresses faster than calcification. This is the
    ``early_progression_multiplier`` of the previous single-mixture model, which
    grouped tear, pannus and accelerated calcification into one unexplained
    "rapidly progressive phenotype". That grouping was recorded there as a
    simplification; naming the three processes and giving each its own covariates
    and its own echo signature is the de-simplification."""

    svd_scale_savr_years: float = 38.009765625
    svd_scale_tavr_years: float = 16.177734375
    """SOLVED by bisection, not assumed: the values reproducing the two targeted
    NOTION moderate-or-severe anchors. Re-derive with::

        solve_scales(DEFAULT, n_solve=12_000)   # -> (38.0098, 16.1777)

    at seed 20260917, which is the call these two numbers came from, and with the
    mortality scale below already solved -- the competing risk governs how many
    patients remain at risk, so the order is not arbitrary. The cohort size is part
    of the reproduction rather than an incidental detail: the objective is evaluated
    on a freshly drawn cohort at every candidate scale, so a different ``n_solve``
    lands a little differently, within the Monte Carlo noise of the search.

    The scales differ far more than the durability of the two valve types does. That
    is expected and is not a claim about devices: a scale describes the hazard of a
    patient at the centring age of 75, and the two arms' real age distributions sit
    on either side of it, so the covariate model absorbs most of the arm difference
    before the scale is reached."""

    # Hazard ratios for the deterioration hazard, applied log-linearly. Covariates
    # are centred (see the *_centre fields) so that the scales above describe a
    # patient at the centring point rather than an impossible patient at zero.
    hr_age_per_year: float = 0.91
    """Per additional year of age at implant: **HR 0.91 (95% CI 0.89-0.94)**.

    Younger age is the strongest published predictor of deterioration. Verified
    against the source meta-analysis rather than taken from a secondary summary.

    An earlier version of this file used 0.95, on the reasoning that 0.91 applied
    linearly across this cohort's age span of 50 to 95 implies a seventy-fold
    difference in hazard between the youngest and the oldest patient, which is not
    a credible extrapolation of an estimate made near the middle of that range.
    That reasoning still holds, but 0.95 lies **outside the published confidence
    interval**, and citing a meta-analysis while using a value it excludes is not a
    position worth defending. The published point estimate is used, and the
    extrapolation is recorded in the limitations instead.

    A sensitivity analysis across 0.91, 0.93, 0.95 and 0.97, **re-solving the
    deterioration scales at each value**, moved no calibration anchor by more than
    0.43 percentage points, so nothing rests on the choice.

    The re-solving is the analysis, not a detail of it. Changing this hazard ratio
    while holding the scales fixed does not test the cohort's sensitivity to it; it
    de-calibrates the cohort, because the scales were solved *against* this value.
    Done that way the surgical anchor moves 7.1 percentage points, which measures
    the arithmetic rather than anything about the model. What the scales absorb is
    visible in their own movement: the surgical scale runs 32.7, 28.4, 24.8, 21.6
    years across those four values while its anchor stays at 20.8%.
    """
    hr_bsa_per_m2: float = 1.77
    hr_ppm_moderate: float = 1.95
    hr_ppm_severe: float = 2.60
    """Patient-prosthesis mismatch, VARC-3 grades. The moderate hazard ratio is
    the published figure; the severe value is an ASSUMPTION extrapolating it."""
    hr_smoking: float = 2.28
    hr_diabetes: float = 1.25
    hr_ckd: float = 1.45
    """Diabetes and chronic kidney disease accelerate leaflet calcification;
    both hazard ratios are ASSUMPTIONS in the direction the literature reports."""

    age_centre: float = 75.0
    bsa_centre: float = 1.85
    valve_size_centre_mm: float = 23.0
    """Centring point for label size, the commonest size in the cohort. The tear
    and pannus modes both take size as a covariate, in opposite directions, so the
    scale of each has to describe a real valve rather than a 0 mm one."""

    death_shape: float = 1.45
    death_scale_years_at_centre: float = 14.638671875
    hr_death_per_year_age: float = 1.085
    hr_death_ckd: float = 1.70
    hr_death_diabetes: float = 1.30
    """Competing mortality. The scale is SOLVED by
    :func:`synthetic.calibration.solve_death_scale` against NOTION's 62.7%
    all-cause mortality at ten years, on the transcatheter arm only, whose mean age
    of 79.5 matches the trial's 79; the surgical arm here is deliberately a decade
    younger, as it is in practice but not in a randomised trial of one population.

    Death is a COMPETING RISK, not censoring: a patient who dies can never
    deteriorate. Its rate governs how many patients remain at risk, so a cohort
    that dies too fast understates every cumulative incidence and one that dies too
    slowly overstates them."""


@dataclass(frozen=True, slots=True)
class EchoParameters:
    """Haemodynamics and their trajectory.

    The mean gradient of a patient without deterioration drifts gently upward;
    after the latent onset of deterioration it accelerates. This two-phase
    trajectory is precisely the structure the prototype extract cannot show -- 4 of
    its 117 patients have gradients in more than one year -- and it is what makes a
    landmark model meaningful.
    """

    gradient_reference_at_eoa: float = 10.0
    gradient_eoa_reference_cm2: float = 1.75
    gradient_eoa_exponent: float = 1.7
    """Gradient rises steeply as effective orifice area falls. The exponent sits
    below the theoretical 2 because flow is not held constant across patients."""
    gradient_lognormal_sd: float = 0.16

    drift_mmhg_per_year: float = 0.25
    drift_sd_mmhg_per_year: float = 0.15
    """ASSUMPTION. Gentle pre-onset drift with a per-patient random slope."""

    progression_mmhg_per_year_mean: float = 2.6
    progression_lognormal_sd: float = 0.65
    progression_quadratic_coefficient: float = 0.08
    """ASSUMPTION. Mean, dispersion and curvature of the post-onset rise in mean
    gradient. The mean rate is lognormal so that a minority of patients
    deteriorate rapidly -- the clinically important tail. Deterioration also
    compounds, a stiffer leaflet calcifying faster, which is what the quadratic
    term expresses; that term additionally governs how quickly a moderately
    deteriorated valve becomes severe, and therefore the ratio between the two
    stages that the literature reports."""

    measurement_cv_gradient: float = 0.10
    measurement_cv_eoa: float = 0.12
    measurement_cv_dvi: float = 0.10
    """Inter-observer and beat-to-beat variability, as coefficients of variation.

    Present because a surveillance model that ignores measurement error will
    declare deterioration on noise, and the protocol has to confront that.

    The error is **proportional, not additive**. An additive error of a fixed
    number of mmHg is indefensible at the low end: a large supra-annular valve
    with a true mean gradient of 3 mmHg would be measured at 1 mmHg or less, which
    no echocardiographer reports, and it would make the VARC-3 criterion of a
    10 mmHg rise from an artificially low reference far too easy to satisfy.
    Echocardiographic measurement error is empirically proportional.

    Each quantity is measured with its own independent error, rather than area and
    dimensionless index being derived from the already-noisy gradient. Deriving
    them would count the same measurement error twice and would let the reference
    examination disagree with the patient's own recorded orifice area."""

    peak_to_mean_low: float = 1.75
    peak_to_mean_high: float = 2.25

    dvi_reference: float = 0.45
    dvi_sd: float = 0.05

    lvef_mean: float = 58.0
    lvef_sd: float = 7.0
    lvef_decline_after_onset_per_year: float = 1.2

    ar_progression_after_tear_per_year: float = 2.50
    """Rate at which regurgitation gains grades once a leaflet has torn, per year.

    Fast, because this is the tear mode's defining signature: a torn leaflet does
    not hold. At this rate a valve starting from trace regurgitation reaches severe
    in about eighteen months, which is still conservative -- a leaflet that tears
    outright can produce severe regurgitation in weeks.

    The first value tried here was 0.75, which needed more than four years to move
    a valve from trace to severe and made the tear mode almost incapable of
    producing a *failure* inside the five-year window that PARTNER 3 reports. The
    cohort missed the five- and seven-year bioprosthetic-failure anchors by more
    than half as a result. Raising it is the clinically truthful correction, not a
    device for hitting the anchor: the anchor was missed *because* the rate was
    wrong."""

    ar_progression_after_calcific_per_year: float = 0.06
    """The same probability under calcific degeneration, which is far lower.

    A calcifying leaflet retracts a little and can leak a little, but it fails by
    obstructing. Keeping this small is what makes regurgitation an **independent
    channel** rather than a second reading of the gradient: under the previous
    single-onset model every deteriorating valve became regurgitant at the same
    rate whatever its mode, so the regurgitation grade carried no information the
    gradient did not already carry."""

    tear_gradient_change_mmhg_per_year: float = -0.4
    """Mean gradient after a tear, in mmHg per year.

    Negative, and this is the point of the mode. A torn leaflet obstructs less,
    not more, so the VARC-3 gradient arm never fires and the event is established
    through the regurgitation arm alone. A model reading only the gradient is
    blind to this failure mode, which is exactly the clinical situation the
    protocol argues surveillance must cover."""


@dataclass(frozen=True, slots=True)
class VisitParameters:
    """The surveillance process, and how patients leave it.

    Guideline echocardiographic surveillance of a bioprosthesis is sparse:
    a reference study soon after implant, then a long gap, then annual imaging.
    Sparsity is not a defect of the simulation -- it is the clinical reality the
    protocol proposes to improve on.
    """

    reference_min_days: int = 30
    reference_max_days: int = 90
    """VARC-3 defines haemodynamic deterioration against a reference echo taken
    30 days to 3 months after implant."""

    routine_years: tuple[float, ...] = (1.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0)
    """Guideline schedule: an early study, then imaging at five years and annually
    thereafter."""
    jitter_days: int = 60

    symptom_echo_probability_per_year: float = 0.35
    """Once deterioration has begun, symptoms bring patients in between scheduled
    studies. This creates verification bias -- patients are imaged BECAUSE someone
    was worried -- which the protocol must account for and which a simulation that
    omitted it would hide."""

    dropout_rate_per_year: float = 0.035
    dropout_hr_per_year_age: float = 1.04
    dropout_hr_after_onset: float = 1.8
    """Loss to follow-up, rising with age and again once deterioration has begun.

    The dependence on **latent onset** is what makes this censoring genuinely
    informative, and it is deliberate. A dropout hazard that depended only on age
    would be non-informative given the covariates, because age is measured: an
    analysis adjusting for age would be unbiased and the protocol's concern about
    loss to follow-up would be a concern about nothing. Here the hazard rises with
    a state nobody observes, so patients who stop attending are sicker than those
    who remain **even after adjustment**, which is the situation real surveillance
    cohorts are in and the one the analysis has to survive.

    The direction is the conservative one: frailty and transfer of care remove
    deteriorating patients from view, so naive estimates understate deterioration."""

    horizon_years: float = 10.0
    """Administrative censoring horizon."""

    reintervention_probability: float = 0.55
    reintervention_delay_days_mean: float = 150.0
    """ASSUMPTION. Not every severely deteriorated valve is reoperated: some
    patients are too frail, some decline. The delay is the interval between
    detection and treatment."""


@dataclass(frozen=True, slots=True)
class Parameters:
    """The complete parameter set of one cohort."""

    cohort: CohortParameters = field(default_factory=CohortParameters)
    hazard: HazardParameters = field(default_factory=HazardParameters)
    echo: EchoParameters = field(default_factory=EchoParameters)
    visit: VisitParameters = field(default_factory=VisitParameters)

    def with_scales(self, savr_years: float, tavr_years: float) -> "Parameters":
        """Return a copy with the deterioration scales replaced by solved values."""
        return replace(
            self,
            hazard=replace(
                self.hazard,
                svd_scale_savr_years=savr_years,
                svd_scale_tavr_years=tavr_years,
            ),
        )


DEFAULT: Final[Parameters] = Parameters()
