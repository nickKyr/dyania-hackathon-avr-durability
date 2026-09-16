# Model Approach

> **Ownership and status.** Sections 2 to 5 are the model workstream's to write
> ([`modeling_brief.md`](modeling_brief.md) §6) and are left for its owner: the fitting code in
> this folder has not been run outside that workstream, so nothing is asserted here about how it
> behaves. Sections 1, 6 and 7 are written from the parts of the pipeline that have been executed
> and verified in this checkout — the study schema, the cohort generator, the calibration and the
> degradation ladder. No performance number appears anywhere in this document, because none has
> been produced and committed.

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
imaged. That is a landmark design. Its implementation lives in
[`../data/build_landmark_table.py`](../data/build_landmark_table.py) and belongs to the model
workstream.

---

## 2. Chosen Model(s)

> **Owner: the model workstream** ([`modeling_brief.md`](modeling_brief.md) §6). The fitting code
> is [`fit_svd_models.py`](fit_svd_models.py) and the tables it consumes are built by
> [`../data/build_landmark_table.py`](../data/build_landmark_table.py). Neither has been run
> outside that workstream and no results are committed, so this section is left to its owner
> rather than described second-hand.

One boundary is worth recording here because it constrains what may be claimed anywhere in this
repository: `lifelines`, `scikit-survival` and `shap` are **not** dependencies of this project.
Fine–Gray models, penalised Cox, gradient-boosted survival analysis, random survival forests,
DeepHit and SHAP attribution are named as candidates in
[`modeling_brief.md`](modeling_brief.md) and are not implemented.

---

## 3. Feature Engineering

> **Owner: the model workstream.** The feature blocks are defined in
> [`fit_svd_models.py`](fit_svd_models.py) and derived in
> [`../data/build_landmark_table.py`](../data/build_landmark_table.py).

Two constraints come from the data workstream and hold regardless of which features are chosen.

**No gradient change, slope or "first versus latest" may be derived from the supplied extract.**
Most patients with more than one prosthetic mean gradient have every value inside a single note
with the examination dates redacted, so those values have no recoverable order. A change computed
against a genuine reference examination is a different quantity and is legitimate; a change
computed from the minimum and maximum inside one note is a fabricated trajectory.

**No imputation across the two sub-cohorts.** A patient in this extract either has an operative
report or has structured laboratory and medication data, never both. Imputing across the two
invents the linkage the extract lacks, and any feature that exists for only one of them encodes
cohort membership rather than biology.

---

## 4. Validation Strategy

> **Owner: the model workstream.**

Two requirements come from the study design and are not the model owner's to trade away:

- **Patient-level splits only.** No patient may contribute rows to more than one of training,
  validation and test, because one patient contributes many landmark rows.
- **No feature may be dated after its landmark.** This has to be asserted mechanically rather
  than reasoned about, since the landmark table is built by iterating over examinations.

Everything else — the cross-validation scheme, the temporal split, the metrics actually computed,
and the uncertainty intervals — belongs to this section's owner.

**External validation:** none. No second site or registry is available.

---

## 5. Expected Model Outputs

> **Owner: the model workstream.**

What the clinical product is intended to return is described in
[`modeling_brief.md`](modeling_brief.md): a cumulative incidence at fixed horizons, a risk tier,
the leading contributing features, and a recommended next surveillance interval. Risk tiering and
feature attribution are **not implemented**, and the thresholds that would define a tier have not
been chosen — see section 6.

---

## 6. Clinical Integration

**Not yet decided — owner: the team, with the clinical lead.** The intended shape is a risk
estimate refreshed at each echocardiogram, used to bring the next study forward or push it back.
Three things are missing before that can be written down honestly: the decision threshold, the
action attached to each tier, and evidence that reallocating surveillance capacity this way helps.
None of them exists in code today, and writing them as though they did would be the one thing this
repository has consistently refused to do.

---

## 7. Limitations and Failure Modes

**The supplied extract cannot support estimation, and this is measured rather than asserted.**
Mapped into the study schema, it reaches an examination for 52.1% of patients, averages 1.69
examinations each, contains **no mortality data at all**, and yields 12.0 events per 100 patients,
all of them documented reinterventions — because haemodynamic staging needs a reference
examination the extract does not contain. Every figure is regenerated by `python -m cohort` into
[`../data/synthetic/results.md`](../data/synthetic/results.md).

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
independently implemented Cox fit: 20 of 21 confidence intervals covered the injected value, with
a mean log bias of +0.0005. Two anchors are missed and neither was tuned away — severe
deterioration after transcatheter implant reproduces the UK TAVI registry rather than NOTION, and
severe deterioration after surgical implant lands at the level of NOTION's *bioprosthetic valve
failure* rather than its *severe deterioration*. The second miss says something the protocol
depends on: thresholds applied mechanically do not separate two categories that a trial
adjudication panel separates.

**The simulation of the extract and the extract itself disagree on one figure, and it was left
uncorrected.** The simulated bottom rung produces 20.5 events per 100 patients against 12.0 in the
extract. That gap is the measured cost of incomplete ascertainment: 41% of the deteriorations a
properly followed cohort would show are invisible here, in patients who were never imaged
again.

**Where the model would break in deployment.** A valve model with no history in the training data
inherits the behaviour of its family, or nothing at all. Inter-observer and beat-to-beat
variability in gradient measurement is real and is modelled as proportional error, but a site with
a systematically different measurement convention would shift every prediction. And because the
outcome is interval-censored at examinations, a patient who is not imaged cannot generate an
event: the model will report a low risk for the patient nobody has looked at, which is exactly the
patient who most needs looking at. Any deployment must surface the surveillance gap next to the
risk, not instead of it.
