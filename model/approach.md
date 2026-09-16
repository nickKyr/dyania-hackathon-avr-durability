# Model Approach

> **Status.** Every section describes code that runs in this checkout: the real extract through
> [`../notebooks/02_preprocessing.ipynb`](../notebooks/02_preprocessing.ipynb), labels, landmarks and
> features in [`../notebooks/03_data_preparation.ipynb`](../notebooks/03_data_preparation.ipynb), and
> models in [`../notebooks/04_model_training.ipynb`](../notebooks/04_model_training.ipynb), scoring of
> the real extract in [`../notebooks/05_results.ipynb`](../notebooks/05_results.ipynb), with the
> shared code in [`../notebooks/pipeline/`](../notebooks/pipeline/). Every evaluation on the real
> extract is recorded, with its full settings, in [`../results/LEDGER.md`](../results/LEDGER.md). Performance numbers come from
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
([`notebooks/synthetic/calibration.py`](../notebooks/synthetic/calibration.py)).

**The event is not observed when it happens; it is observed when someone images the patient.**
An event is recorded at the examination that *detects* it, and both ends of the censoring interval
travel with it (`interval_start_days`, `days_from_implant`). On the synthetic cohort (ideal rung,
1,800 patients, seed 20260917) the interval between a patient's last clean examination and the one
that detected stage-2 deterioration has a median of 1.1 years and a maximum of 4.2, so a
deterioration recorded at one examination may have begun four years earlier. `test_the_censoring_interval_brackets_the_event` holds the
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
from records dated at or before the landmark, and the outcome measured from it. The first
landmark, at six months, falls after the VARC-3 reference examination (30 days to 3 months after
implant), so a reference study can exist at every landmark.

---

## 2. Chosen Model(s)

All models answer one question: from a landmark, what is the cumulative incidence of SVD at 2, 5
and 8 years, with death as a competing event. Two years is the shortest interval the risk tiers
schedule (§5); five and eight years are where the published series report durability (PARTNER 3
at 5 and 7 years, the UK TAVI registry at a median of 7.8;
[`../data/synthetic/results.md`](../data/synthetic/results.md)). Code in
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

**Why gradient boosting and not deep learning.** The protocol's cohort is sized at 3,580 patients
with about 565 deteriorations ([`../protocol/sample_size.md`](../protocol/sample_size.md)); trees
with native missing-value handling and monotone constraints are the strongest option at that scale
and stay explainable with SHAP.

---

## 3. Feature Engineering

The catalogue (`FEATURES` in `ml.py`) lists 42 features in seven blocks, each with the direction
the literature expects and whether it is a clinical prior:

- **time:** years since implant at the landmark
- **patient:** age at implant, sex, BSA, diabetes, CKD, smoking, bicuspid anatomy, anticoagulation
- **valve:** SAVR or TAVR, valve family, label size, indexed EOA at implant, mismatch grade
- **reference echo:** mean and peak gradient, DVI, EOA, regurgitation, LVEF, and a flag when it is missing
- **latest echo:** the same measurements at the most recent study before the landmark
- **trajectory:** change from reference in gradient, DVI, EOA and regurgitation, highest gradient so far, gradient slope over the last two studies
- **surveillance:** number of echoes, echoes in the last two years, years since the last one

Eleven are clinical priors (valve age, age, diabetes, CKD, smoking, anticoagulation, SAVR vs TAVR,
size, mismatch, reference gradient, gradient change). The regression baseline and the Cox
comparator use only the priors among the features in use, which under the default fixed list below
are five: valve age, SAVR vs TAVR, size, reference gradient and gradient change. A change is computed only against a genuine reference examination, never from values that
share one note.

**The primary and baseline models use a fixed clinical feature list by default**
(`ml.FIXED_FEATURES`): years since implant, SAVR or TAVR, label size, Trifecta, the reference
mean gradient and a flag when it is missing, the latest mean gradient, and the change between the
two. These are the valve-level predictors the SVD literature names and the ones the extract
actually records. Age, diabetes, CKD, smoking and anticoagulation are left out although the
literature ranks them highly: the extract never records age or anticoagulation, and it records the
other three mainly when they are present, so a model trained on them would learn the note-writing
habit rather than the risk. The Trifecta flag is there because of the FDA 2023 safety communication
(cited in [`../notebooks/synthetic/parameters.py`](../notebooks/synthetic/parameters.py)) and the
published excess of early leaflet tears and explants against the Perimount
([`../docs/research/svd_literature.md`](../docs/research/svd_literature.md) §3.3). The surveillance block is never used, because the number
and timing of echoes reflect how worried the clinician was, not how the valve is doing.

Automatic selection remains available (`SELECTION["mode"] = "auto"`), and notebook 03 always shows
what it would have chosen. It uses four filters on training rows only: missing on more than 60% of
rows, near-constant, Spearman correlation above 0.95 (the prior wins), and stability selection (an
L1-penalised hazard model on 40 random halves of the training patients, kept if chosen in 60% of
fits). It was not made the default because it picked different features on different synthetic
draws (body surface area in one, bicuspid anatomy in another). Fixing the list did not change
discrimination on the real extract (regression baseline 0.72 ± 0.03 either way over five draws, measured before the three-mode
generator),
and a fixed list is the one a clinician can check. Features that are entirely empty in a training
set are dropped automatically.

---

## 4. Validation Strategy

- **Temporal split:** valves implanted up to 2018 train, later valves test. A patient's rows never
  cross the split. The year is where case mix turns: in the extract 88% of implants from 2019 on are
  TAVR, so the test set asks whether a model trained mostly on surgical valves transfers to the
  transcatheter era. The protocol's primary patient-level partition (protocol §5) is not run here.
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
  reintervention-only events and extract-like follow-up. 6,000 valves are drawn from a generated
  pool of 18,000. Four further steps close the gaps a
  statistical comparison of the two datasets found:
  - **Case mix.** A cohort three times the needed size is drawn and resampled (raking weights) to
    the extract's approach by implant era (TAVR is 88% of its implants from 2019 on), its sex ratio
    and its valve families.
  - **Informative missingness.** In the notes a risk factor is mostly written down when it is
    present (diabetes is "yes" in 83% of the patients where it is stated, CKD in 93%). The cohort
    keeps a "yes" more often than a "no" so that both the stated rate and the share of "yes"
    match. A covariate the extract does not record at all, such as anticoagulation, is hidden.
  - **Gradient level.** Mean and peak gradients are rescaled by approach and by reference or later
    study to the extract's medians (surgical reference gradient 7 mmHg in the extract, 11 in the
    raw cohort).
  - **Echo timing.** Kept follow-up studies are placed where the extract has them, mostly in the
    last year the valve is seen (84% in the extract, 17% before this step, 59% after it).

  How alike the two datasets are is measured, not asserted: a classifier is trained to tell
  extract rows from cohort rows (`matching.distinguishability`, cross-validated by patient). Its
  AUC on the clinical features fell from 0.85 to 0.80 with these steps (0.5 would mean the two
  cannot be told apart). The remaining difference is mostly deliberate. Most real events belong to
  valves with long follow-up, a pattern of how the notes were written that a model should not
  learn, so it is not copied.
- **Repeated on the real extract.** Each configuration evaluated on the extract is trained on five
  independently drawn cohorts (`AVR_SEED`), and the mean and spread are quoted, not one draw. With
  10 events one synthetic draw moved the boosted model's AUC anywhere from 0.47 to 0.76 before the
  three-mode generator, and from 0.56 to 0.69 after it.
- **Repeated, not single-shot.** `scripts/06_model_stability.py` reruns the whole pipeline on eight
  independently drawn cohorts and reports the spread, because a ranking read off one draw is a
  description of the seed. Its output is [`stability.md`](stability.md), and it is the file to
  quote AUCs from.
- **Decision curve.** `scripts/08_decision_curve.py` reports net benefit at every candidate
  threshold against scanning everyone and against changing nothing, with death competing; its
  output is [`decision_curve.md`](decision_curve.md). On the real extract, notebook 05 adds
  calibration by risk group, an Uno-style C-index and the same decision curve.
- **External check:** the real extract, prepared by notebook 02, is scored by every trained model.

**Results on the synthetic cohort (not patients).** Trained and tested on the cohort matched to the
extract (ledger run `final`), valve age carries most of the signal: AUC 0.86, 0.78 and 0.88 at 2, 5
and 8 years for the valve-age-only model, 0.86, 0.79 and 0.83 for the regression baseline and the
Cox comparator, 0.85, 0.77 and 0.79 for the constrained boosted model, and 0.70, 0.62 and 0.45 for
the calendar schedule. **Every one of those numbers is a single cohort**, and
[`stability.md`](stability.md) measures what that is worth: redrawing the cohort moves an AUC by a
standard deviation of about 0.027, so differences of that size between two of the models above are
not evidence of anything. On the ideal rung, where the comparison can be repeated eight times and
paired within cohorts, every risk model does beat scheduling by valve age at every horizon — but
that is a claim about the ideal rung, and the matched-cohort ranking here has not been repeated.
The ideal-rung numbers themselves are in [`stability.md`](stability.md) and supersede the earlier
single-run figures that used to be quoted here.

**Results on the real extract (51 valve episodes, 301 landmark rows, 10 episodes with an SVD
event, no deaths recorded** — the unit is the valve episode; the other event counts in this
repository are placed against it in
[`../data/endpoint_criteria.md`](../data/endpoint_criteria.md)**).** Trained on the ideal cohort,
the boosted model ranked the real valves worse than chance (5-year AUC 0.29, in an early run
made before the ledger existed), because it had never seen the inputs the extract lacks. Trained on the matched cohort with the fixed feature list, the
mean 5-year AUC over five synthetic draws (± standard deviation) is:

| Model | 5-year AUC | Mean predicted 5-year risk |
|---|---|---|
| Regression baseline | 0.71 ± 0.02 | 15.9% |
| Cox on risk factors | 0.71 ± 0.00 | 10.6% |
| Valve age only | 0.71 ± 0.00 | 10.9% |
| Gradient boosting (constrained) | 0.64 ± 0.05 | 11.1% |

The committed notebooks show one of these draws (ledger run `final`): regression baseline 0.72
(0.55 to 0.89) with a mean predicted risk of 17.3%, boosted model 0.67 (0.46 to 0.89) at 12.8%.
The observed 5-year incidence is 16.6%, with a patient-bootstrap 95% interval of 7.7% to 27.6%.
Each single draw carries a bootstrap interval roughly 0.3 wide (for example 0.55 to 0.89 for the
regression baseline), so with 10 events no model is shown to rank better than valve age alone.
The regression baseline's average risk falls inside the observed interval without any fitting to
real outcomes. The boosted model is less stable than the baseline across draws and never better on
average. It remains the pre-specified primary model of §2, but on the extract the regression
baseline is the stronger of the two, and it is the one this repository presents.

Two changes moved these numbers, and both were checked over five draws rather than one. Reshaping
the cohort (the steps above) raised the boosted model's mean AUC from 0.63 to 0.68 and its mean
predicted risk from 7.3% to 10.9%. The three-mode failure process in the generator left AUC
unchanged, halved the boosted model's spread (0.12 to 0.05), and brought the baseline's risk from
13.7% to 15.9%.

**Local recalibration was tested and not adopted.** Shifting every predicted risk by one constant
on the logit scale, learned on four fifths of the real patients and applied to the fifth, brings
the average to 16.5% but made the baseline's individual risks slightly worse (scaled Brier score
lower in four of five draws), and the learned shift varied from −0.13 to +0.47 between folds. Ten
events cannot fix a calibration intercept. The protocol therefore recalibrates at each site only
once it has enough local events (§6).

---

## 5. Expected Model Outputs

For a valve at a follow-up visit the model returns the cumulative incidence of SVD at 2, 5 and 8
years, a risk tier from the 5-year risk (low under 5%, moderate 5 to 15%, high 15% or more), the
echo interval attached to the tier (guideline schedule, every two years, every year), and the three
features that moved the risk most, from SHAP values of the boosted SVD hazard. Notebook 04 prints
one worked example. The tier thresholds remain provisional, but no longer for want of an analysis:
[`decision_curve.md`](decision_curve.md) reports the net benefit at every candidate threshold and
what each of the two boundaries above would buy. They should be fixed only after recalibration
at the deploying site, because a decision curve is read off absolute risk.

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
the action attached to each tier, and a model recalibrated on the deploying site's own outcomes,
since the curve is read off absolute risk and ten real events cannot pin the risk level down (§4).
Recalibration waits until a site has at least 100 events of its own, the minimum Collins et al.
(Stat Med 2016) found for a reliable external calibration estimate
([`../docs/research/svd_literature.md`](../docs/research/svd_literature.md) [79]).

---

## 7. Limitations and Failure Modes

The reporting of this work is mapped against TRIPOD+AI item by item in
[`tripod_ai.md`](tripod_ai.md), including the five items it does not satisfy. The limitations
below are the substantive ones.


**The supplied extract cannot support estimation, and this is measured rather than asserted.**
Mapped into the study schema, it has an examination for 83.8% of patients, averages 1.62
examinations each, has more than one gradient for 16.2%, contains **no mortality data at all**, and
records 8.55 affected patients per 100. Nine of the ten affected valve episodes are documented
reinterventions and one is a stage-2 deterioration seen on echo, because haemodynamic staging needs
a reference examination the extract rarely contains. The recorded figures are in
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
