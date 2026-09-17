# Model Approach

This document covers how the prediction task is framed, which models we built and why, what they
learn from, how they were tested, what they return, and where they fail. The code is in
[`notebooks/pipeline/`](../notebooks/pipeline/); the notebooks are 03 (labels and features),
04 (training) and 05 (scoring on the real extract). Every evaluation on the extract is recorded
with its settings in [`results/LEDGER.md`](../results/LEDGER.md).

---

## 1. Problem Formulation

**The question** (the study's problem statement, *Dynamic Prediction of Bioprosthetic Aortic Valve
Failure to Guide Personalised Surveillance*). Among adults who are alive and free of valve failure
following bioprosthetic aortic valve replacement, can clinical information available at each
postoperative visit predict the risk of bioprosthetic valve failure over the next five years, with
risk estimates updated at every subsequent visit? The models answer it at 5 years, and also report
2 and 8 years.

**Framing: a competing-risks time-to-event model, re-evaluated at each visit (landmark design).**
Four properties of the clinical setting force this framing.

1. **Follow-up is right-censored.** Many patients are followed for a few years and then lost. A
   yes/no label at a fixed horizon would throw these patients away, or count them as event-free
   when nobody knows. A time-to-event model uses the years each patient was actually observed.

2. **Death competes with valve failure.**
   - Bioprosthesis recipients are old: in NOTION, 62.7% of the transcatheter arm had died by
     10 years, against 15.4% to 20.8% with moderate or severe deterioration.
   - A patient who dies with a working valve can never fail later.
   - Treating death as ordinary censoring (one minus Kaplan–Meier) would overstate failure risk.
   - Every risk here is therefore a cumulative incidence with death as a competing event
     (Aalen–Johansen form).

3. **Failure is seen only when someone looks.** Deterioration is recorded at the echocardiogram
   that detects it, not when it begins.
   - In the synthetic cohort (ideal rung, 1,800 patients, seed 20260917), the gap between the last
     normal study and the one that detected stage-2 deterioration has a median of 1.1 years and a
     maximum of 4.2.
   - Time is also coarse: the supplied extract has years only.
   - A discrete-time model, which estimates risk per follow-up year, fits this resolution.

4. **The clinical decision recurs.** The decision the model supports, when to image this patient
   next, is taken again at every visit. So the model is asked again at every visit, the
   **landmark** design:
   - landmarks at 6 months, 1 year, then every year up to 10 years;
   - one row per valve per landmark it reaches while event-free and observed;
   - features use only records dated at or before the landmark, and the outcome is counted from it.

**Why these landmarks and horizons.**
- **First landmark at 6 months.** It falls after the VARC-3 reference echocardiogram (30 days to
  3 months after implant), so a reference study can exist at every landmark. With year-only dates,
  it is the closest usable point to the "first post-operative visit" our clinical question starts
  from.
- **The 2-year horizon** is the shortest interval the risk tiers schedule.
- **The 5- and 8-year horizons** are where the published series report durability: PARTNER 3 at 5
  and 7 years, the UK TAVI registry at a median of 7.8 years.

**Endpoint** (implemented as `stage2_or_worse`, switchable to `stage3_or_bvf`):
- VARC-3 haemodynamic valve deterioration stage 2 or worse, against the patient's own reference
  study;
- or a reintervention for structural failure.

Endocarditis, thrombosis and isolated paravalvular leak are not counted.

---

## 2. Chosen Model(s)

All models answer the same question and are scored the same way.

| Model | Role | Justification |
|---|---|---|
| Discrete-time competing-risks gradient boosting | **Primary** | Captures non-linear effects and thresholds, handles missing echo values natively, and is constrained so that risk can never fall as a stenosis marker worsens. It is built for the data the protocol asks sites to supply. |
| Discrete-time competing-risks regression | Clinical baseline | The same two-hazard structure with logistic regression on the published risk factors. It is transparent, and its odds ratios can be checked against the literature. |
| Cause-specific Cox on published risk factors (`lifelines`) | Comparator | The model clinicians know, with hazard ratios and standard errors clustered by patient. It treats death as censoring, so its absolute risk runs high; it is used for ranking. |
| Valve age only | Comparator | Gradient boosting with time since implant as its only input. Risk rises with valve age, so any useful model has to beat this. |
| Guideline calendar schedule | Comparator | Current practice. Valves under and over 5 years old each get the training incidence of their group. |
| Gradient boosting without constraints, and recalibrated versions of both main models | Checks | They show what the monotone constraints and a calibration step add. |

**How the two main models work.** Each landmark row is expanded into one row per follow-up year, up
to 8 years. Each year row is marked as "valve failed this year", "patient died this year" or
"nothing". Two classifiers of the same kind are then trained:
- one for the yearly chance of failure, given the valve is still working and the patient alive;
- one for the yearly chance of death.

Their yearly chances are chained into the cumulative incidence at 2, 5 and 8 years. This is the
discrete-time form of the cause-specific Cox model for tied yearly event times.
- **Death stays a competing event.** A patient who dies stops contributing to later years.
- **Censored follow-up still counts.** A partly observed final year enters with a fractional
  weight.
- **Few deaths.** If the training data hold fewer than 5 deaths, the death model is skipped and its
  hazard is taken as zero.

**Why gradient boosting as primary, and not deep learning.**
- **Scale.** The protocol's cohort is sized at 3,580 patients with about 565 deteriorations
  ([`protocol/sample_size.md`](../protocol/sample_size.md)). At that scale, tree ensembles on
  tabular data are the strongest practical option.
- **Missing values.** They handle missing measurements without imputation.
- **Clinical sense.** They take monotone constraints (a higher gradient or a larger rise in it never
  lowers risk).
- **Explanation.** SHAP explains each prediction.

Sequence and deep survival models (for example DeepHit) need more events than a single-centre
registry provides. **Planned extension:** a joint longitudinal model of the gradient.

**Tuning.** A small grid is searched:
- learning rate 0.03 or 0.1
- 7, 15 or 31 leaves
- a minimum of 20 or 80 rows per leaf

Each setting is scored by the 5-year competing-risk AUC in 3-fold cross-validation grouped by
patient, with early stopping inside each fit. In the committed run the best setting was learning
rate 0.03, 7 leaves and 20 rows per leaf.

---

## 3. Feature Engineering

### Input Variables

| Group | Variables |
|---|---|
| Time | years since implant at the landmark |
| Patient | age at implant, sex, body surface area, diabetes, chronic kidney disease, smoking, bicuspid native valve, anticoagulation |
| Valve | SAVR or TAVR, valve family (Sapien 3, Evolut, Trifecta, Perimount, Epic, Magna, Inspiris), label size, indexed orifice area at implant, patient–prosthesis mismatch grade |
| Echo | mean and peak gradient, DVI, effective orifice area, intraprosthetic regurgitation grade, LVEF |
| Surveillance | number of echoes, echoes in the last two years, years since the last echo |

In total, the feature catalogue (`ml.FEATURES`) holds **42 features**. For each one it records the
direction the literature expects, and whether it is a **clinical prior**, a predictor established
well enough to keep whatever the data say. There are 11 priors:
- years since implant
- age
- diabetes
- chronic kidney disease
- smoking
- anticoagulation
- SAVR or TAVR
- size
- mismatch grade
- reference gradient
- gradient change

### Engineered Features

| Feature | Derivation | Clinical Rationale |
|---|---|---|
| `ref_mg`, `ref_dvi`, `ref_eoa`, `ref_ar` | values at the reference study, the first post-operative echo | VARC-3 defines deterioration as change from the patient's own baseline, not as an absolute level |
| `ref_missing` | 1 when there is no reference study | without a baseline, change cannot be measured, and the absence itself says something about follow-up |
| `last_mg`, `last_dvi`, `last_ar`, `last_lvef` | most recent value at or before the landmark | the current state of the valve |
| `delta_mg`, `delta_dvi`, `delta_eoa`, `delta_ar` | latest minus reference | the VARC-3 criteria are written in these terms: a gradient rise, a fall in area or DVI, worsening regurgitation |
| `max_mg`, `mg_slope` | highest gradient so far; change per year over the last two studies | speed of deterioration |
| `valve_trifecta` and other family flags | from the valve model name in the operative report | valve durability differs by design; the Trifecta has an FDA 2023 safety communication (cited in `notebooks/synthetic/parameters.py`) and published excess leaflet tears and explants against the Perimount ([`docs/research/svd_literature.md`](../docs/research/svd_literature.md) §3.3) |
| `ppm_grade`, `eoa_index_implant` | orifice area at implant indexed to body surface area, graded at the VARC-3 cut-offs | patient–prosthesis mismatch raises the gradient without the valve failing, and is itself a risk factor |

**The feature list depends on the data** (`SELECTION["mode"] = "fixed"`, chosen in notebook 03).

| Setting | List | Features |
|---|---|---|
| **Main setup: full-quality synthetic data** | `ml.FIXED_FEATURES` (21) | years since implant, SAVR or TAVR, label size, Trifecta, mismatch grade, age, sex, body surface area, smoking, diabetes, chronic kidney disease, anticoagulation, reference mean gradient and its missing flag, latest mean gradient, change in mean gradient, latest DVI and its change, latest regurgitation grade and its change, latest LVEF |
| **Real-extract check: data reshaped to look like the extract** | `ml.SPARSE_FEATURES` (8) | years since implant, SAVR or TAVR, label size, Trifecta, reference mean gradient and its missing flag, latest mean gradient, change in mean gradient |

The regression baseline and the Cox model use the clinical priors in the list:
- **Main setup:** all 11.
- **Real-extract check:** 5 (years since implant, SAVR or TAVR, size, reference gradient, gradient
  change).

**Where the main list comes from.** The team clinician listed the factors that matter for
structural valve deterioration. Every item the feature catalogue can build is in the main list:

| Clinician's item | Feature |
|---|---|
| rise in mean gradient (more than 10 or 20 mmHg) | `delta_mg`, `last_mg`, `ref_mg` |
| fall in DVI | `delta_dvi`, `last_dvi` |
| new or worsening intraprosthetic regurgitation | `delta_ar`, `last_ar` |
| patient–prosthesis mismatch | `ppm_grade` |
| ejection fraction | `last_lvef` |
| age, sex, smoking, diabetes, renal insufficiency | `age_at_implant`, `male`, `smoking`, `diabetes`, `ckd` |
| body mass index | `bsa_m2`, the closest body-size measure the data carry |
| prosthesis size, surgical or transcatheter, years since implant | `valve_size_mm`, `tavr`, `landmark_years` |
| anticoagulants | `anticoagulation` |

**Not yet covered.**
- **Patient history:** hypertension, dyslipidaemia, amyloidosis, hyperparathyroidism.
- **Echo:** changes in leaflet morphology.
- **Laboratory values:** HbA1c, lipids, renal markers, calcium, phosphate, PTH, vitamin D, blood
  count, coagulation.
- **Medications:** statins, beta blockers, anti-inflammatories, SGLT2 inhibitors.

**Why.**
- **Training.** The generator does not simulate these items, so a model trained on the synthetic
  cohort could not learn their effect.
- **The extract.** Labs and medications exist only for 17 patients, none of whom has an operative
  report.

The protocol asks sites to supply these items, and they are the first extension of the list.

**The clinician's factors help when they are recorded.** Clinician-aligned list against the earlier
8-feature list, same cohort and split, 5-year AUC:

| data | model | 8 features | clinician-aligned list |
|---|---|---|---|
| full-quality synthetic, all visits | gradient boosting | 0.74 | 0.77 |
| full-quality synthetic, all visits | regression baseline | 0.73 | 0.78 |
| full-quality synthetic, first visit | gradient boosting | 0.54 | 0.62 |
| full-quality synthetic, first visit | regression baseline | 0.55 | 0.64 |
| real extract, trained on reshaped data (mean of 5 draws) | gradient boosting | 0.64 ± 0.05 | 0.54 ± 0.10 |
| real extract, trained on reshaped data (mean of 5 draws) | regression baseline | 0.71 ± 0.02 | 0.70 ± 0.03 |

The full-quality rows come from a single cohort (seed 20260917, 6,000 patients).

**Why the list depends on the data.**
- **Full-quality data.** The patient factors and serial echo values carry real signal. They matter
  most at the first visit, where valve age cannot separate patients.
- **The extract.** It rarely records them:
  - age is never recorded;
  - echo values are sparse;
  - risk factors are written mainly when present.

  Trained on reshaped data that include them, the boosted model learned patterns that do not hold in
  the notes, and fell to near chance on the real valves. The same list trained on full-quality data
  does not have this problem (§4).

**Other rules.**
- **The surveillance block is never used.** How often a valve was imaged reflects how worried the
  clinician was, not how the valve is doing. With it included, the boosted model learned the
  synthetic surveillance pattern and ranked real valves worse than chance.
- **Empty features are dropped.** Features that are entirely empty in a training set are dropped
  automatically; age, for example, in the reshaped data.
- **Automatic selection is available but not the default** (`SELECTION["mode"] = "auto"`). It
  combines filters for missingness, near-constant columns and correlation with stability selection
  over 40 bootstrap halves. It is not the default because it chose different features on different
  synthetic draws, and a fixed list is one a clinician can check.

### Handling Missing Data
- **Gradient boosting** handles blanks natively: at each split, missing values go to whichever side
  fits better.
- **Regression model** fills blanks with the training median and adds a missing-value indicator.
- **No value is carried forward** beyond the most recent study at or before the landmark.
- **Informative missingness is modelled explicitly.**
  - `ref_missing` flags the absence of a baseline study.
  - In the synthetic cohort, patients whose valve is failing are more likely to drop out, so the
    models are trained and tested with that bias present.
- **Surveillance gap: shown, not modelled.** A long gap without an echo is not used as a feature,
  for the reason above. It is shown next to every prediction instead (§6).

---

## 4. Validation Strategy

**Design.** As the organisers recommended, the main results come entirely from synthetic data, with
separate training, validation and test sets. The real extract is a secondary check.

- **Main setup: full-quality synthetic data** (notebooks 03 and 04, `TRAIN_LIKE_REAL = False`, the
  default). The generator's `ideal` cohort has dated serial echocardiograms, age and deaths. Each
  draw has 6,000 patients.
- **Train / test split.** Temporal: valves implanted up to 2018 train, later valves test. No patient
  appears on both sides.
- **Why 2018.** It is where case mix turns: 88% of the extract's implants from 2019 on are TAVR. The
  test set therefore asks whether a model trained mostly on surgical valves carries over to the
  transcatheter era.
- **Validation.** Only inside the training set:
  - hyperparameters are tuned by 3-fold cross-validation grouped by patient;
  - recalibration uses out-of-fold predictions from a further 3-fold split;
  - the learning curve is measured on a held-out quarter of the training patients.
- **Repeated draws.** A single synthetic draw is not trusted.
  - The main setup is run on 5 independent cohorts (`AVR_SEED`), and results are reported as the
    mean and spread.
  - `scripts/06_model_stability.py` reruns a simpler version of the pipeline on 8 more cohorts
    ([`stability.md`](stability.md)).
- **Results by visit.** Metrics are also reported for the first postoperative visit (6 months)
  separately from later visits. The problem statement starts at the first visit, and there valve age
  cannot help.
- **Real-extract check** (notebook 05). The real hospital extract is scored, never trained on.
  - **Training data.** Models for this check are trained on synthetic data reshaped to look like the
    extract (`TRAIN_LIKE_REAL = True`, [`data_plan.md`](../data/data_plan.md) §5), with the short
    feature list.
  - **Intervals.** 500 bootstrap resamples drawn **by valve**, because landmark rows from the same
    valve are correlated.
  - **Other sites.** Validation at other sites is specified in the protocol.

**Metrics.**
- **Competing-risk time-dependent AUC** at 2, 5 and 8 years, with inverse probability of censoring
  weights. Cases have failure by the horizon. Controls are event-free past the horizon, or died
  first.
- **Scaled Brier score** against a model that gives everyone the observed incidence.
- **Calibration:** mean predicted against observed (Aalen–Johansen), overall and by risk third.
- **Decision curve:** net benefit against scanning everyone and against changing nothing
  ([`decision_curve.md`](decision_curve.md)).
- **Sensitivity, specificity, PPV and NPV** at the tier cut-offs.

### Main results: full-quality synthetic data (not patients)

**Five independent draws, 6,000 patients each.**
- **Split per draw:** about 22,400 training rows and 14,700 test rows.
- **Events:** about 510 patients with failure in training and 360 in test.
- **Deaths:** recorded.
- **Features:** the 21-feature list.

Competing-risk AUC, mean ± standard deviation across draws:

| model | 2 years | 5 years | 8 years | mean predicted 5-year risk |
|---|---|---|---|---|
| regression baseline | 0.807 ± 0.011 | **0.761 ± 0.012** | **0.763 ± 0.013** | 18.4% |
| gradient boosting (primary) | **0.830 ± 0.009** | 0.756 ± 0.010 | 0.761 ± 0.008 | 18.5% |
| gradient boosting, no constraints | 0.833 ± 0.005 | 0.757 ± 0.010 | 0.760 ± 0.010 | 18.3% |
| Cox, risk factors | 0.807 ± 0.012 | 0.755 ± 0.012 | 0.743 ± 0.012 | 21.9% |
| valve age only | 0.788 ± 0.014 | 0.730 ± 0.013 | 0.705 ± 0.005 | 18.2% |
| calendar schedule | 0.694 ± 0.013 | 0.665 ± 0.010 | 0.579 ± 0.004 | 18.4% |

The observed 5-year incidence in the test sets is 14.7% on average.

- **Every risk model beats valve age alone** at every horizon, by 0.02 to 0.06, with a spread across
  draws of about 0.01.
- **The primary model leads at 2 years.** At 5 and 8 years it is level with the regression
  baseline.
- **Monotone constraints make no difference to discrimination on full-quality data.** They are kept
  for clinical sense and for sparse data.
- **Calibration.** The models over-predict the pooled 5-year risk by about a quarter: 18% predicted
  against 15% observed. Training-cohort recalibration brings the primary model to 17.3%.

**By visit.** 5-year AUC, mean of the five draws:

| visit | test rows | failures by 5 years | observed | valve age only | Cox | regression baseline | gradient boosting |
|---|---|---|---|---|---|---|---|
| **first visit (6 months)** | 2,332 | 135 | 6.6% | 0.50 | 0.60 ± 0.03 | **0.61 ± 0.03** | 0.60 ± 0.03 |
| 1 to 4 years | 7,498 | 854 | 12.1% | 0.61 | 0.66 | **0.67** | **0.67** |
| 5 years or later | 5,306 | 799 | 34.5% | 0.48 | 0.69 | **0.74** | 0.73 |

**This answers the problem statement.**
- **At the first postoperative visit,** information available by then separates patients modestly:
  AUC about 0.60, where valve age alone gives 0.50. The predicted risk is well calibrated there, for
  example 6.3% (regression) and 5.8% (gradient boosting) against 6.6% observed.
- **Discrimination improves at later visits** as serial echocardiograms accumulate, reaching about
  0.74 from 5 years on. At those visits valve age alone is no better than chance, because the
  valves are all old.

**What drives the risk.** SHAP ranking for the primary model, committed run:
1. years since implant
2. TAVR
3. age (younger means higher risk)
4. body surface area
5. change in mean gradient
6. Trifecta
7. reference gradient
8. LVEF
9. smoking

The Cox hazard ratios on the same run:
- **per year since implant:** 1.17
- **per year of age:** 0.971
- **smoking:** 1.39
- **TAVR:** 1.34
- **per mismatch grade:** 1.19
- **per mmHg of gradient change:** 1.20
- **not clearly different from 1:** diabetes, kidney disease and anticoagulation

These are the effects the generator was built with, so they confirm that the pipeline recovers them.
They are not new clinical findings.

**More patients would not help at this scale.** On the learning curve, the primary model's 5-year
AUC stays between 0.71 and 0.72 from 10% to 100% of the training patients. The limit is the
information available per patient, not the number of patients.

**The committed run** (seed 20260917, notebooks 03 and 04), 5-year AUC:

| model | all visits | first visit |
|---|---|---|
| regression baseline | 0.78 | 0.64 |
| gradient boosting | 0.77 | 0.62 |
| valve age only | 0.73 | 0.50 |

**The same models on the real extract.** Scored in notebook 05, five draws. The full-quality models
transfer to the extract at least as well as the models trained on reshaped data:

| model | 5-year AUC | mean predicted |
|---|---|---|
| regression baseline | 0.72 ± 0.01 | 10.1% |
| gradient boosting | 0.69 ± 0.03 | 14.1% |
| valve age only | 0.72 ± 0.00 | 18.2% |

The observed rate on the extract is 16.6%.

### Other synthetic results

**A simpler setup, repeated over 8 cohorts** ([`stability.md`](stability.md); fixed hyperparameters and its own feature set). Mean 5-year AUC:

| model | 5-year AUC |
|---|---|
| regression baseline | 0.752 |
| gradient boosting, no constraints | 0.745 |
| Cox | 0.744 |
| gradient boosting | 0.733 |
| valve age only | 0.723 |
| calendar schedule | 0.663 |

- **Noise between draws.** Redrawing the cohort moves an AUC by a standard deviation of about 0.027,
  so smaller differences between two models are not evidence.
- **Against valve age.** Measured within the same cohort, every risk model beats valve age alone at
  every horizon, but by only 0.01 to 0.05.
- **Calibration.** The models over-predict five-year risk by up to 57%.

**Reshaped data, 8-feature list** (ledger run `final`, the models behind the real-extract check). AUC on its synthetic test set at 2, 5 and 8 years:

| model | 2 years | 5 years | 8 years |
|---|---|---|---|
| valve age only | 0.86 | 0.78 | 0.88 |
| regression baseline | 0.86 | 0.79 | 0.83 |
| Cox | 0.86 | 0.79 | 0.83 |
| gradient boosting | 0.85 | 0.77 | 0.79 |
| calendar schedule | 0.70 | 0.62 | 0.45 |

- **Monotone constraints matter.** Without them, gradient boosting drops to 0.62 at 5 years.
- **Calibration.** The models predict 7.6% to 10.2% five-year risk against 7.2% observed.

**Most of the signal is valve age.** SHAP ranks years since implant far above everything else for
the primary model, followed by Trifecta, TAVR and the gradients.

### Real-extract check

Models trained on reshaped synthetic data with the 8-feature list. The real extract gives 51 valve episodes, 301 landmark rows, 10 episodes with failure and no deaths
recorded. Mean 5-year AUC over five synthetic training draws:

| Model | 5-year AUC (mean ± SD) | Mean predicted 5-year risk |
|---|---|---|
| Regression baseline | 0.71 ± 0.02 | 15.9% |
| Cox on risk factors | 0.71 ± 0.00 | 10.6% |
| Valve age only | 0.71 ± 0.00 | 10.9% |
| Gradient boosting (primary) | 0.64 ± 0.05 | 11.1% |

- **Observed risk.** The observed 5-year incidence is 16.6%, with a bootstrap 95% interval of 7.7%
  to 27.6%.
- **The committed run** (`final`): regression baseline 0.72 (0.55 to 0.89), gradient boosting 0.67
  (0.46 to 0.89).
- **No ranking is established.** With 10 events, every interval is about 0.3 wide and no model is
  shown to rank better than valve age alone.
- **Calibration.** The regression baseline's average risk falls inside the observed interval without
  any fitting to real outcomes. The other models predict too little.
- **The primary model.** Gradient boosting stays primary because it is designed for protocol-quality
  data. On the extract, which lacks those data, the regression baseline did better, and both are
  reported.
- **Against the full-quality models.** The main-setup models, trained without any reshaping, score
  the same extract at 0.72 (regression) and 0.69 (gradient boosting). Reshaping the training data
  therefore does not improve transfer once the surveillance features are excluded. It remains a
  check of how a model built only for the extract's gaps behaves.

**What changed these numbers.** Each change below was checked over five draws:
- **Reshaping the training cohort** raised the boosted model's mean AUC on the extract from 0.63 to
  0.68, and its mean predicted risk from 7.3% to 10.9%.
- **The three-mode failure process** in the generator left AUC unchanged, halved the boosted model's
  spread, and brought the baseline's mean risk from 13.7% to 15.9%.

**At the first visit the models do not separate patients.** On real landmarks under 2 years
(91 rows, 3 events), the 5-year AUC is about 0.5 or lower for every model. At the first visit every
valve has the same age, so the ranking has to come from patient and valve information, and the
extract has little of it.

**Local recalibration was tested and not adopted.**
- **The test.** Every predicted risk was shifted by one constant, learned on four fifths of the real
  valves and applied to the fifth.
- **The result.** The average moved to 16.5%, but the baseline's individual risks got slightly worse,
  and the learned shift varied widely between folds.
- **Why.** Ten events cannot fix a calibration intercept.

---

## 5. Expected Model Outputs

**Output format.** One model inference, for a valve at a follow-up visit, returns:
- cumulative incidence of structural failure at 2, 5 and 8 years, with death as a competing event;
- a risk tier from the 5-year risk: **low** (under 5%), **moderate** (5% to 15%) or **high** (15% or
  more);
- the echo interval attached to the tier: the guideline schedule, an echo every 2 years, or an echo
  every year;
- the three features that moved the risk most, from SHAP values of the primary model;
- in deployment, the time since the last echocardiogram and the list of missing inputs, shown
  beside the risk. The notebook prototype returns the first four items.

**Example.** From notebook 04, a test valve 1 year after implant:
- **Risk:** 1.7% within 2 years, 15.0% within 5 years, 33.8% within 8 years.
- **Tier:** moderate, so an echo every 2 years.
- **Main reasons given:** the valve's short time since implant lowers the risk; a transcatheter valve
  raises it.

**On the full-quality synthetic test set** (committed run), the tiers split the rows as follows:

| tier | share of test rows | mean 5-year risk |
|---|---|---|
| low | 18% | 3.3% |
| moderate | 43% | 9.4% |
| high | 39% | 34.3% |

In the decision-curve analysis ([`decision_curve.md`](decision_curve.md)), the high tier holds 33%
of patient-years and 60% of the deteriorations.

**How the output is consumed.** It is read by the clinician or the echo scheduling service at each
follow-up visit, as decision support. The tier cut-offs are provisional; choosing them is a clinical
decision (§6).

---

## 6. Clinical Integration

**Where it sits.** Echo surveillance scheduling, at each follow-up visit of a patient with a
bioprosthetic aortic valve.

**What triggers an inference.** A new echocardiogram report or a follow-up visit. The site's
abstraction step turns the report into fields, and the model recomputes the risk with the new
values and the valve's greater age.

**What a flag prompts.**
- **High (15% or more):** a yearly echo and a review by the heart valve team.
- **Moderate (5% to 15%):** an echo every 2 years.
- **Low (under 5%):** the guideline schedule.

The model brings the next study forward or leaves it where it is. It does not decide on
reintervention, which stays with the heart team.

**What the analysis says about the cut-offs.** The decision curve shows where acting on the model
helps:
- From 5% risk upward, a risk-guided schedule beats both scanning everyone and changing nothing
  ([`decision_curve.md`](decision_curve.md)).
- Below 5%, scanning everyone is the better policy.

**What the schedule costs.** The tiered schedule needs 483 examinations per 1,000 patient-years:
- 332 more than the ACC/AHA calendar;
- 517 fewer than the ESC/EACTS annual echo.

**Two things are still owed before clinical use.**
1. Clinical agreement on the action attached to each tier.
2. Recalibration of the risk level at each site, once the site has at least 100 events of its own.
   That is the minimum Collins et al. (Stat Med 2016) found for a reliable external calibration
   estimate ([`svd_literature.md`](../docs/research/svd_literature.md) [79]).

**Safeguards specified for deployment.** These are not yet built into the prototype.
- **The surveillance gap is shown beside every risk.** A low risk for a patient nobody has imaged
  recently must not read as reassurance.
- **Missing inputs are listed.** Each prediction lists which of its inputs were missing.

---

## 7. Limitations and Failure Modes

- **The first visit is where the model is weakest.**
  - **Full-quality synthetic data.** The first-visit 5-year AUC is about 0.60, against 0.76 over all
    visits. The separation has to come from baseline factors alone; the gain at later visits comes
    mostly from the gradient trajectory.
  - **The real extract.** Predictions at landmarks under 2 years do not separate patients (AUC about
    0.5). The real-extract check with reshaped training uses the short list, which lacks the patient
    risk factors.
  - **What would help most.** A site that records age, risk factors and a dated reference
    echocardiogram gets the most out of the first visit.
- **Valve age dominates.** Over all landmarks, the models rank patients only slightly better than
  valve age alone, on synthetic data and on the extract.
- **The real test is small.** Ten events in 51 valve episodes cannot establish a ranking between
  models, and every AUC interval is about 0.3 wide.
- **The competing risk is untested on real data.**
  - The extract records no deaths, so the death part of the models is never checked against real
    patients.
  - The reshaped training data also contain no deaths, so in those runs the death hazard is zero.
- **The extract's labels are weaker than the protocol's.**
  - Nine of the ten real events are reinterventions.
  - The one echo-detected event was labelled with the VARC-3 corroboration (fall in orifice area or
    DVI) switched off, and with a reference window of one year rather than 30 to 90 days.
  - No event has been clinician-adjudicated yet.
- **Synthetic training has a ceiling.** The generator returns the effects it was built with, so the
  synthetic results confirm the method, not the clinical effects. Its simulation of the extract is
  still more pessimistic about surveillance than the real extract.
- **Calibration depends on the setting.** On the synthetic cohort the models over-predict five-year
  risk by up to 57%; on the extract most of them under-predict. The absolute risk has to be
  recalibrated at each site before the tiers are used.
- **Deployment risks.**
  - **New valve models.** A model with no history in the training data inherits the average of its
    approach, or nothing.
  - **Measurement differences.** A laboratory that measures gradients systematically higher shifts
    every prediction; inter-observer and beat-to-beat variability are only partly modelled, as
    proportional noise.
  - **Patients who are not imaged.** Because failure is only seen at an echo, a patient who is not
    imaged cannot generate an event. The model will show a low risk for exactly the patient who most
    needs a scan, which is why the surveillance gap is displayed next to the risk.
- **How clinicians are told.** In deployment, each output carries the time since the last echo and
  the list of missing inputs, and the tiers are labelled provisional until a site has recalibrated
  them.
