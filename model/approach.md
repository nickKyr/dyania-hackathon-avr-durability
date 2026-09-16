# Model Approach

> **Status.** Every section describes code that runs in this checkout: the real extract through
> [`../notebooks/02_preprocessing.ipynb`](../notebooks/02_preprocessing.ipynb), labels, landmarks and
> features in [`../notebooks/03_data_preparation.ipynb`](../notebooks/03_data_preparation.ipynb), and
> models in [`../notebooks/04_model_training.ipynb`](../notebooks/04_model_training.ipynb), with the
> shared code in [`../notebooks/pipeline/`](../notebooks/pipeline/). Performance numbers come from
> the synthetic cohort and are labelled as such; the real extract is scored, never trained on.

---

## 1. Problem Formulation

The task is **time from implant to the first structural failure of the prosthesis, with death as a
competing risk and the event interval-censored at echocardiographic examinations**. Three
properties of the clinical setting force that framing, and each is enforced in code that runs in
this repository.

**Death is not a nuisance, it is a competing risk.** In the population that receives a
bioprosthesis, all-cause mortality by ten years is around 63% against a moderate-or-severe
deterioration incidence around 15–21% (anchors with their primary citations in
[`notebooks/synthetic/parameters.py`](../notebooks/synthetic/parameters.py)). Most patients die
with a working valve. An estimator that treats death as censoring answers a question about a
population in which nobody dies, so every incidence reported in this work is an Aalen–Johansen
cumulative incidence function under the competing risk
([`synthetic/calibration.py`](../notebooks/synthetic/calibration.py)).

**The event is not observed when it happens; it is observed when someone images the patient.**
An event is recorded at the examination that *detects* it, and both ends of the censoring interval
travel with it (`interval_start_days`, `days_from_implant`). On the reference cohort the interval
between a patient's last clean examination and the one that detected stage-2 deterioration has a
median of 1.0 years and a maximum of 4.25 — so a deterioration recorded at one examination may
have begun four years earlier. `test_the_censoring_interval_brackets_the_event` holds the
property; a generator emitting latent onset times would instead produce a dataset on which any
model looks better than it could be in clinic.

**Time is coarse, so event times are tied.** In the supplied extract every date is reduced to the
calendar year. A model formulated in continuous time has nothing to work with; a discrete-time
hazard formulation, in which risk is estimated per follow-up year and chained into a cumulative
incidence, is the form this resolution permits.

**Risk has to be re-estimated at each new examination, not once at implant**, because the clinical
decision the model serves — when to image this patient next — recurs every time the patient is
imaged. That is a landmark design, implemented in
[`../notebooks/pipeline/landmarks.py`](../notebooks/pipeline/landmarks.py): a row per valve at 0.5,
1, 2 … 10 years after implant while the valve is event-free and observed, features taken only
from records dated at or before the landmark, and the outcome measured from it.

---

## 2. Chosen Model(s)

All models answer one question: from a landmark, what is the cumulative incidence of SVD at 2, 5
and 8 years, with death as a competing event. Code in
[`../notebooks/pipeline/ml.py`](../notebooks/pipeline/ml.py), trained in notebook 04.

| Model | Role | Why |
|---|---|---|
| Guideline calendar schedule | comparator | Current practice: valves under and over five years, each given the training incidence of its group |
| Valve age only | comparator | Boosted model on time since implant alone; any useful model must beat it |
| Cause-specific Cox on published risk factors (`lifelines`) | comparator, hazard ratios | The model clinicians read; robust errors clustered by patient because a patient contributes several landmark rows. It ignores death, so its absolute risk is an overestimate |
| Discrete-time competing-risks regression | clinical baseline | Two logistic hazards (SVD, death) per follow-up year on the clinical priors, chained into a cumulative incidence (Aalen–Johansen form). At yearly resolution this is Cox's model for tied times |
| Discrete-time competing-risks gradient boosting | primary | The same two-hazard structure with `HistGradientBoostingClassifier`: native missing values, non-linear effects, and monotone constraints so risk cannot fall as a stenosis marker rises |

Death is never treated as censoring: the SVD and death hazards are fitted separately and combined,
so a patient who dies first counts as not having SVD. Fine–Gray, random survival forests and
DeepHit are not implemented; the joint longitudinal model of the gradient is the planned extension.

**Why gradient boosting and not deep learning.** A protocol-sized cohort has 100 to 200 events;
trees with native missing-value handling and monotone constraints are the strongest option at that
scale and stay explainable with SHAP.

---

## 3. Feature Engineering

The catalogue (`FEATURES` in `ml.py`) lists 41 features in seven blocks, each with the direction
the literature expects and whether it is a clinical prior:

- **time:** years since implant at the landmark
- **patient:** age at implant, sex, BSA, diabetes, CKD, smoking, bicuspid anatomy
- **valve:** SAVR or TAVR, valve family, label size, indexed EOA at implant, mismatch grade
- **reference echo:** mean and peak gradient, DVI, EOA, regurgitation, LVEF, and a flag when it is missing
- **latest echo:** the same measurements at the most recent study before the landmark
- **trajectory:** change from reference in gradient, DVI, EOA and regurgitation, highest gradient so far, gradient slope over the last two studies
- **surveillance:** number of echoes, echoes in the last two years, years since the last one

Ten are clinical priors (valve age, age, diabetes, CKD, smoking, SAVR vs TAVR, size, mismatch,
reference gradient, gradient change); the regression baseline and the Cox comparator use only
these. A change is computed only against a genuine reference examination, never from values that
share one note.

**Feature selection is switchable and off by default.** Four filters run on training rows only:
missing on more than 60% of rows, near-constant, Spearman correlation above 0.95 (the prior wins),
and stability selection (an L1-penalised hazard model on 40 random halves of the training
patients, kept if chosen in 60% of fits). With selection off every feature is used and the report
shows what each filter would drop. Features that are entirely empty in a training set are dropped
automatically.

---

## 4. Validation Strategy

- **Temporal split:** valves implanted up to 2018 train, later valves test. A patient's rows never
  cross the split.
- **Tuning:** a small grid (learning rate, leaves, leaf size) scored by 3-fold cross-validation
  grouped by patient, with early stopping inside each fit.
- **Metrics:** competing-risk time-dependent AUC and Brier score at 2, 5 and 8 years with inverse
  probability of censoring weights (cases: SVD by the horizon; controls: event-free at the horizon
  or dead first), mean predicted risk against the Aalen–Johansen incidence, a learning curve, and a
  patient-level bootstrap interval for the real extract.
- **Training data like the target data.** The model must work on the extract, so by default the
  synthetic cohort is reshaped to look like it (`TRAIN_LIKE_REAL`,
  [`../notebooks/pipeline/matching.py`](../notebooks/pipeline/matching.py)): year-only dates, no
  age, no recorded deaths, echo counts and missing fields at the rates measured in the extract,
  reintervention-only events and extract-like follow-up.
- **Repeated, not single-shot.** `scripts/06_model_stability.py` reruns the whole pipeline on eight
  independently drawn cohorts and reports the spread, because a ranking read off one draw is a
  description of the seed. Its output is [`stability.md`](stability.md), and it is the file to
  quote AUCs from.
- **Decision curve.** `scripts/08_decision_curve.py` reports net benefit at every candidate
  threshold against scanning everyone and against changing nothing, with death competing; its
  output is [`decision_curve.md`](decision_curve.md). Calibration curves and Uno's C are still
  planned and not yet run.
- **External check:** the real extract, prepared by notebook 02, is scored by every trained model.

**Results on the synthetic cohort (not patients).** Trained and tested on the cohort matched to the
extract, valve age carries most of the signal: AUC 0.81, 0.78 and 0.88 at 2, 5 and 8 years for the
valve-age-only model, 0.80, 0.78 and 0.84 for the regression baseline and the Cox comparator,
0.78, 0.72 and 0.79 for the constrained boosted model, and 0.68, 0.62 and 0.44 for the calendar
schedule. **Every one of those numbers is a single cohort**, and
[`stability.md`](stability.md) measures what that is worth: redrawing the cohort moves an AUC by a
standard deviation of about 0.023, so differences of that size between two of the models above are
not evidence of anything. On the ideal rung, where the comparison can be repeated eight times and
paired within cohorts, every risk model does beat scheduling by valve age at every horizon — but
that is a claim about the ideal rung, and the matched-cohort ranking here has not been repeated.
The ideal-rung numbers themselves are in [`stability.md`](stability.md) and supersede the earlier
single-run figures that used to be quoted here.

**Results on the real extract (51 valves, 8 events, no deaths recorded** — the unit here is the
valve episode, and the other event counts quoted in this repository are placed against it in
[`../data/endpoint_criteria.md`](../data/endpoint_criteria.md)**).** Trained on the ideal
cohort, the boosted model ranked the real valves worse than chance (5-year AUC 0.29), because it had
never seen the inputs the extract lacks. Trained on the matched cohort, the regression baseline
reaches 0.78 (95% interval 0.60 to 0.95), the Cox comparator 0.75, valve age alone 0.74, the
unconstrained boosted model 0.71 and the constrained one 0.57 (0.30 to 0.82). With 8 events the
intervals overlap and no ranking is established, and every model predicts far more SVD than the
observed 12.6% at 5 years, so recalibration on real outcomes comes before any clinical use.

---

## 5. Expected Model Outputs

For a valve at a follow-up visit the model returns the cumulative incidence of SVD at 2, 5 and 8
years, a risk tier from the 5-year risk (low under 5%, moderate 5 to 15%, high 15% or more), the
echo interval attached to the tier (guideline schedule, every two years, every year), and the three
features that moved the risk most, from SHAP values of the boosted SVD hazard. Notebook 04 prints
one worked example. The tier thresholds remain provisional, but no longer for want of an analysis:
[`decision_curve.md`](decision_curve.md) reports the net benefit at every candidate threshold and
what each of the two boundaries above would buy. They should be fixed only after recalibration,
because a decision curve is read off absolute risk and these models over-predict it.

---

## 6. Clinical Integration

**The shape is settled; the operating point is the clinical lead's to choose.** A risk estimate is
refreshed at each echocardiogram and used to bring the next study forward or push it back.
Notebook 04 implements provisional tiers (5-year risk under 5%, 5 to 15%, 15% or more) mapped to
the guideline schedule, an echo every two years and an echo every year.

The decision curve in [`decision_curve.md`](decision_curve.md) supplies what was missing on the
analysis side: the range of thresholds over which acting on the model beats both scanning everyone
and changing nothing, what each candidate boundary buys in deteriorations caught per hundred
patients, and what the tiered schedule costs in examinations per 1,000 patient-years against each
of the two guideline calendars — the number a service line is actually planned in, and the one
figure a claim about reallocating surveillance cannot be made without. Two things are still outstanding and neither is a computation — clinical agreement on
the action attached to each tier, and a recalibrated model, since the curve is read off absolute
risk and these models over-predict it by about half.

---

## 7. Limitations and Failure Modes

**The supplied extract cannot support estimation, and this is measured rather than asserted.**
Mapped into the study schema, it reaches an examination for 52.1% of patients, averages 1.69
examinations each, contains **no mortality data at all**, and records 12.0 endpoint rows per 100
patients, all of them documented reinterventions — because haemodynamic staging needs a reference
examination the extract does not contain. The recorded figures are in
[`../data/synthetic/results.md`](../data/synthetic/results.md); notebook 02 reproduces the event
count from the notes.

**The competing risk is unobserved on the real rung.** With no vital status in the extract, a
cumulative incidence computed there is not comparable with one computed where death is known, and
must be labelled wherever it appears.

**Verification bias is built into the problem and is not corrected.** Patients are imaged because
someone was worried. The synthetic cohort reproduces this deliberately — symptom-triggered
examinations once deterioration has begun — so the bias is present in any evaluation run on it
rather than assumed away. Nothing in the pipeline adjusts for it.

**Loss to follow-up is informative by construction, and that is the point.** The dropout hazard
rises at latent onset, a state nobody observes, so patients who stop attending are sicker than
those who remain *even after adjustment for every measured covariate*. An analysis that assumes
censoring is non-informative will therefore be optimistic, and the cohort is built so that this
can be demonstrated rather than debated.

**Calibration of the synthetic cohort is not evidence that it is correct.** Nine parameters were
fitted against the published anchors, which is close to saturated. Correctness is established
separately, by injecting known hazard ratios into the generator and recovering them with an
independently implemented Cox fit, one per failure mode: 70 of 75 confidence intervals covered the
injected value (93.3% against a nominal 95%), with a mean log bias of −0.0030. Two anchors are missed and neither was tuned away — severe
deterioration after transcatheter implant reproduces the UK TAVI registry rather than NOTION, and
severe deterioration after surgical implant lands at the level of NOTION's *bioprosthetic valve
failure* rather than its *severe deterioration*. The second miss says something the protocol
depends on: thresholds applied mechanically do not separate two categories that a trial
adjudication panel separates.

**The cost of incomplete ascertainment is measured inside the ladder, not across the gap to the
extract.** Comparing a simulated rung with the extract confounds how poor the data are with
whether the two datasets count endpoints the same way — and they do not, since a valve that
reaches stage 2, then stage 3, then reintervention is one patient and three rows. Measured between
the top of the ladder and the extract-like rung, where the patients and their failure times are
identical and only the surveillance differs, extract-quality ascertainment loses **34% of affected
patients and 42% of endpoint rows**. The extract's own figure sits between the two synthetic ones
and cannot be placed more precisely until it is recomputed under the same definition.

**Where the model would break in deployment.** A valve model with no history in the training data
inherits the behaviour of its family, or nothing at all. Inter-observer and beat-to-beat
variability in gradient measurement is real and is modelled as proportional error, but a site with
a systematically different measurement convention would shift every prediction. And because the
outcome is interval-censored at examinations, a patient who is not imaged cannot generate an
event: the model will report a low risk for the patient nobody has looked at, which is exactly the
patient who most needs looking at. Any deployment must surface the surveillance gap next to the
risk, not instead of it.
