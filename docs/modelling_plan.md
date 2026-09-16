# Modelling plan

> **Superseded.** This is the plan written before the model was built, kept as a record. It names files that were never created (`notebooks/03_modelling.ipynb`, `data/landmark.parquet`, `scripts/05_synthetic_landmark.py`) and choices that changed: the horizons are now 2, 5 and 8 years, the primary endpoint is VARC-3 stage 2 or worse, and the models use the feature list in `ml.FIXED_FEATURES`. What was built is described in [`../model/approach.md`](../model/approach.md).

Written 16 Sep 2026. Two sessions are working on this in parallel: one finishes the preprocessing steps in `notebooks/02_preprocessing.ipynb`, the other builds `notebooks/03_modelling.ipynb`. The interface between them is one file, `data/landmark.parquet`, whose columns are fixed below. Anything else in either notebook can change without telling the other side.

## The task

At each landmark time t after the reference echo, given everything known about the patient up to t, estimate the probability of structural valve deterioration within the next 2 and 5 years, with death from other causes as a competing event.

This is a dynamic, competing-risks, time-to-event problem. Supervised. The training unit is a patient at a landmark, not a patient.

## Event definition (from the clinician, 16 Sep)

Two sources, which agree on the thresholds. The 2017 EAPCI/ESC/EACTS consensus gives two tiers; VARC-3 (2021) gives stages 2 and 3 with the same numbers plus a percentage form. Both are measured against the baseline echo performed 1 to 3 months after the procedure.

Tier 1, possible or subclinical SVD (consensus) and VARC-3 stage 2 moderate HVD. Any of:
- mean gradient rise of more than 10 mmHg (VARC-3: resulting in at least 20 mmHg) with EOA fall of more than 0.3 cm2, or 25 percent, and/or DVI fall of more than 0.08 (VARC-3: 0.1 or 20 percent);
- new intraprosthetic regurgitation of at least mild, or a rise of at least one grade, with the result at most moderate (VARC-3: resulting in at least moderate);
- change in leaflet morphology (thickening, calcification, flail, pannus) or mobility (reduced, avulsed) compared with baseline. This criterion is consensus only.

Tier 2, clinically relevant SVD (consensus) and VARC-3 stage 3 severe HVD. Either:
- mean gradient rise of more than 20 mmHg (VARC-3: resulting in at least 30 mmHg) with EOA fall of more than 0.6 cm2, or 50 percent, and/or DVI fall of more than 0.15 (VARC-3: 0.2 or 40 percent);
- new or at least one grade worse intraprosthetic regurgitation resulting in moderate-to-severe or severe (VARC-3: two grades, resulting in severe).

Plus reintervention for valve deterioration (VARC-3 bioprosthetic valve failure stage 2), which counts as tier 2 regardless of echo.

Primary outcome for the model: tier 2. Secondary: tier 1 or worse. Both are encoded in the contract through `event_tier`. Endocarditis, thrombosis, isolated paravalvular leak and isolated patient-prosthesis mismatch are non-structural and do not count; they are logged in `event_basis` so a sensitivity analysis can include them.

When no baseline echo exists, the consensus rise-based criteria cannot be applied; the fallback is the VARC-3 absolute level (mean gradient at least 20 or 30 mmHg) and `event_basis` records that the label is absolute, not change-based.

## The contract: `data/landmark.parquet`

One row per patient per landmark. Column names are fixed. A column may be all-missing on the real extract (age, death) but it must exist.

Keys

| column | type | meaning |
|---|---|---|
| patient | str | pseudonym |
| landmark_year | int | the year of the landmark |
| landmark_type | str | `echo` (a prosthetic echo happened this year) or `fixed` (1, 3 or 5 years after reference) |
| implant_year | int | year of the index implant |
| t_since_implant | float | landmark_year minus implant_year |
| split | str | `train` or `test`, assigned by implant year cut-off |

Outcome, measured from the landmark

| column | type | meaning |
|---|---|---|
| time_to_event | float | years from landmark to first of: SVD event, death, end of follow-up |
| event_type | int | 0 censored, 1 structural deterioration (tier 2), 2 death from other causes |
| event_tier | int | 0 none, 1 possible or subclinical SVD, 2 clinically relevant SVD; tier 1 rows keep event_type 0 for the primary analysis |
| event_basis | str | `reintervention`, `gradient_change`, `gradient_absolute`, `regurgitation`, `morphology`, `adjudicated`, `provisional`, `non_structural_excluded`, or empty |
| status_2y | int | 0, 1, 2 as above, evaluated at 2 years |
| status_5y | int | same at 5 years |

Fixed at implant

| column | type |
|---|---|
| approach | str: SAVR, TAVR |
| valve_family | str: sapien, evolut, trifecta, epic, biocor, perimount, magna, inspiris, other, unknown |
| valve_model_level | str: exact, family, inferred, unknown |
| valve_size_mm | float |
| native_bicuspid | int 0/1, missing allowed |
| concomitant_cabg | int 0/1 |
| sex | str: male, female, missing |
| age_at_implant | float, all missing on this extract |
| bsa | float, mostly missing |
| bmi | float, mostly missing |
| smoking | str: current, former, never, missing |
| ppm | int 0/1: patient-prosthesis mismatch stated in a note or indexed EOA at or below 0.85 cm2/m2 at the reference echo |

Reference echo (first prosthetic echo in the implant year or the year after)

| column | type |
|---|---|
| ref_mean_gradient | float |
| ref_dvi | float |
| ref_ava | float |
| ref_ar_grade | int 0 to 4 |
| ref_missing | int 0/1 |

Time-varying, from rows dated at or before the landmark year

| column | type |
|---|---|
| last_mean_gradient | float |
| last_peak_gradient | float |
| last_dvi | float |
| last_ava | float |
| last_ar_grade | int 0 to 4 |
| last_lvef | float |
| last_leaflet_abnormal | int 0/1: thickening, calcification, flail, pannus, reduced mobility described at the latest study |
| lvh | int 0/1: left ventricular hypertrophy described at the latest study |
| delta_mg_from_ref | float |
| delta_dvi_from_ref | float |
| delta_ava_from_ref | float |
| delta_ar_grade_from_ref | int |
| mg_slope | float, mmHg per year over the last two studies |
| n_echo_so_far | int |
| years_since_last_echo | float |
| last_creatinine | float |
| last_egfr | float |
| last_hemoglobin | float |
| last_calcium | float |
| last_phosphate | float |
| anticoagulant | int 0/1 |
| antiplatelet | int 0/1 |
| statin | int 0/1 |
| loop_diuretic | int 0/1 |
| raas_inhibitor | int 0/1 |
| sglt2 | int 0/1 |
| diabetes | int 0/1 |
| ckd | int 0/1 |
| atrial_fibrillation | int 0/1 |
| hypertension | int 0/1 |
| coronary_disease | int 0/1 |
| heart_failure | int 0/1 |
| endocarditis_history | int 0/1 |

Two producers write this file with the same columns: step 9 of the preprocessing notebook (real extract) and `scripts/05_synthetic_landmark.py` (synthetic cohort). A `source` column says which.

## Why a synthetic cohort

The real extract yields about 24 patients with prosthetic echoes in more than one year, a dozen reinterventions and no deaths. That proves the pipeline runs; it cannot train anything. The synthetic generator produces about 2,000 implants with 4 to 8 years of follow-up, event rates from the literature review (moderate or severe SVD near 2 percent at 1 year, 11 percent at 5, 26 percent at 10 for TAVR; 6.6 percent clinically relevant SVD at 10 years for SAVR), death as a competing event at the rate of a cohort in its late seventies, and covariate effects in the published direction (younger age, smaller valve, higher reference gradient, renal disease, diabetes raise the hazard; anticoagulation lowers it). Every effect size is a named constant at the top of the script so the panel can see what was assumed. The clinician supplied a published table of predictors (references 54 to 56 in the source review; the review itself is to be cited once the team has the title). The generator uses these values:

| predictor | effect | as used |
|---|---|---|
| age, per year | HR 0.97 | hazard falls 3 percent per year of age at implant |
| smoking | HR 2.58 | current smoker |
| BMI, per unit | HR 1.84 | applied per unit above 25, capped |
| diabetes | significant, size not given | HR 1.5 assumed |
| dyslipidaemia | OR 3.9 | HR 2.0 assumed, since an odds ratio overstates a hazard ratio |
| renal insufficiency | HR 1.1 | per stage of CKD |
| persistent LV hypertrophy | HR 2.38 | LVH at the reference echo |
| prosthesis size, per mm | HR 0.82 | larger valve, lower hazard |
| patient-prosthesis mismatch | HR 1.79 | |
| anticoagulation | protective in most registries | HR 0.7 assumed |
| TAVR vs SAVR | trial data, see literature review | equal at 5 years, SAVR higher after 8 |

The modelling notebook runs on the synthetic file today and on the real file when preprocessing is done, with no code change. Results on synthetic data are reported as a test of the method, never as a finding.

## Models

1. Clinical baseline: cause-specific Cox on the landmark rows with the published predictors from the clinician's table (age, smoking, BMI, diabetes, dyslipidaemia, renal insufficiency, LVH, prosthesis size, PPM) plus reference mean gradient and landmark time. On the real extract several of these are missing for everyone (age, BMI, smoking), so the fitted baseline uses what exists and the protocol states the intended list. Fine-Gray on the same for the subdistribution view. Package: lifelines or scikit-survival.
2. Primary: discrete-time competing-risks gradient boosting. Expand each landmark row into yearly intervals up to the horizon, train a multiclass boosted classifier (no event, SVD, death) on the features, chain the interval probabilities into cumulative incidence at 2 and 5 years. Package: lightgbm with monotone constraints on gradient, delta and slope. This keeps death as a competing event, which scikit-survival's boosting does not.
3. Trivial comparators: the fixed calendar schedule (everyone flagged at 5 and 10 years) and time since implant alone. Both must be beaten for the model to be worth anything.
4. Deferred: joint longitudinal-survival model of the gradient trajectory. Named in the protocol as the planned extension, not built.

## Feature handling in the modelling notebook

Selection is by rule, fitted inside the training split, no statistical screening:

- drop any column with more than 60 percent missing in train;
- drop peak gradient (duplicates mean gradient) and keep mean;
- missing indicator plus median fill, fitted on train, for the rest;
- valve family as a categorical, native to lightgbm;
- the Cox baseline uses its fixed six predictors and nothing else.

Importance is read afterwards with SHAP on the boosted model, not used to choose features.

## Evaluation

- Time-dependent AUC at landmark plus 2 and plus 5 years, inverse probability of censoring weighted, death treated as competing (timeROC logic; implement with scikit-survival's cumulative_dynamic_auc on cause-specific labels or the Blanche estimator by hand).
- Brier score at the same horizons against the Aalen-Johansen baseline.
- Calibration: predicted versus observed cumulative incidence by risk decile at each horizon, with slope and intercept.
- Decision curve for the one action, shortening the echo interval, across threshold probabilities 5 to 40 percent.
- Temporal validation: train on implants up to a cut-off year, test after. On synthetic data the cut-off is arbitrary; on real data it will be about 2017.
- Report the same table for baseline, primary and the two trivial comparators.

## Outputs of one inference

For a patient at a landmark: cumulative incidence of SVD at 2 and 5 years, risk tier (low, moderate, high) with thresholds taken from the decision curve, the three largest SHAP contributions in words, and the recommended next echo interval (12 months if high, 24 if moderate, guideline schedule if low). A clinician confirms before any schedule changes. The notebook prints one example.

## Notebook cell plan for `03_modelling.ipynb`

1. Load `landmark.parquet`, print source, rows, patients, events by horizon.
2. Split by implant year; print event counts per split.
3. Feature preparation (rules above), fitted on train.
4. Trivial comparators.
5. Cox and Fine-Gray baseline with hazard ratios table.
6. Discrete-time expansion and lightgbm competing-risks model.
7. Predictions at 2 and 5 years for every test row.
8. Evaluation table and calibration plots.
9. Decision curve and risk tiers.
10. SHAP summary and one worked patient example.
11. Same run on the real landmark file when available, reported as pipeline proof only.

## Division of work

Preprocessing session: steps 4, 5, 6 and 9 of `02_preprocessing.ipynb` first, since they are the path to the real landmark file; steps 1, 2, 3, 7, 8 after. Writes `data/landmark.parquet` with `source = "extract"`.

Modelling session: `scripts/05_synthetic_landmark.py` first, so `03_modelling.ipynb` has data on day one; then cells 1 to 10 against the synthetic file; cell 11 when the real file exists.

Neither side adds or renames a column in the contract without editing this file first.

## Open points for the team

- Cut-off year for the temporal split on real data.
- Risk-tier thresholds: taken from the decision curve, or fixed a priori at 5 and 15 percent 2-year risk.
- Whether reinterventions for endocarditis are excluded (VARC-3 says non-structural) or kept as a sensitivity analysis.
