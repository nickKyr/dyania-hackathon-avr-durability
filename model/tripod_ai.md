# TRIPOD+AI reporting checklist

TRIPOD+AI (Collins GS, Moons KGM, Dhiman P, et al. *BMJ* 2024;385:e078378) is the reporting
standard for clinical prediction models developed with regression or machine learning. It is the
standard this study's reporting is written against, and this page is the map: for each of its 27
items, where the answer is in this repository and how complete it is.

Two things make the mapping unusual, and both are stated here rather than buried:

1. **This is a protocol with an executed pipeline, not a completed prediction-model study.** No
   model is fitted on patient data. Items about development and evaluation are answered against a
   literature-calibrated **synthetic** cohort, and the checklist says so every time.
2. **TRIPOD+AI item 5a explicitly requires that synthetic data be justified and its generation
   documented.** That is the one place where our unusual design is exactly what the standard asks
   for, and [`../data/data_plan.md`](../data/data_plan.md) §5 plus
   [`../data/synthetic/README.md`](../data/synthetic/README.md) are the answer.

**Status vocabulary.** *Reported* — answered in the repository. *Partial* — answered, with a
stated limitation. *Planned* — specified in the protocol for the real study, not executed here.
*Not done* — neither answered nor specified; an honest gap. *N/A* — does not apply to this design.

Item wording is abbreviated; the authoritative text is the
[TRIPOD+AI checklist](https://www.tripod-statement.org/tripod-ai).

## Title and abstract

| Item | What it asks | Where it is answered | Status |
|---|---|---|---|
| 1 | Identify the study as developing or evaluating a prediction model, the target population and the outcome | [`../README.md`](../README.md); [`../protocol/study_protocol.md`](../protocol/study_protocol.md) §1 | Reported |
| 2 | Abstract per the TRIPOD+AI for Abstracts checklist | README, *Problem Statement* and *Our Approach* | Partial — the README opening serves as the abstract; it is not structured to the abstracts checklist |

## Introduction

| Item | What it asks | Where it is answered | Status |
|---|---|---|---|
| 3a | Healthcare context, rationale, references to existing models | Protocol §1; [`../docs/research/svd_literature.md`](../docs/research/svd_literature.md) §3–4, which reviews the existing durability models and why none is usable here | Reported |
| 3b | Target population, intended purpose in the care pathway, intended users | Protocol §2; [`approach.md`](approach.md) §6 — decision support that moves the next echocardiogram earlier or later, used by the cardiologist reviewing the study | Reported |
| 3c | Known health inequalities between sociodemographic groups | Protocol §6, *Algorithmic Fairness* — including the inequality specific to this endpoint: a group imaged less often appears lower-risk and is then imaged even less | Partial — the structural inequality is named and its mechanism given; population-level inequality figures for this endpoint are not cited |
| 4 | Study objectives, development or validation or both | Protocol §1 | Reported |

## Methods — data

| Item | What it asks | Where it is answered | Status |
|---|---|---|---|
| 5a | Data sources, rationale, representativeness — **including why any synthetic data were used and how they were created** | [`../data/data_plan.md`](../data/data_plan.md) §1–2 (real deployment and prototype), §5 (why synthetic, how calibrated, what it is not); [`../data/synthetic/README.md`](../data/synthetic/README.md); generator code in [`../notebooks/synthetic/`](../notebooks/synthetic/) with 54 tests | Reported |
| 5b | Dates of participant data, accrual and follow-up | `data_plan.md` §3 — dates in the extract are shifted and reduced to the year, which is itself a finding and is costed on the `year_resolution` rung of the ladder | Partial — true accrual dates are unrecoverable by design of the de-identification |
| 6a | Study setting, number and location of centres | Protocol §2; the prototype extract is a single centre | Partial — the multi-centre setting is specified for the real study, not demonstrated |
| 6b | Eligibility criteria | Protocol §2, inclusion and exclusion | Reported |
| 6c | Treatments received and how they were handled | `approach.md` §3 — anticoagulation enters as a feature; [`../docs/medications.md`](../docs/medications.md) explains why the medication file is an index-admission record and not a drug history | Partial |
| 7 | Data pre-processing and quality checking, and whether it was similar across sociodemographic groups | `data_plan.md` §4; [`../docs/data_quality_issues.md`](../docs/data_quality_issues.md); notebooks 01 and 02 | Partial — pre-processing is documented in full, but it **cannot** be checked across sociodemographic groups: age is redacted and sex is inferable only from pronouns |

## Methods — outcome, predictors, sample size

| Item | What it asks | Where it is answered | Status |
|---|---|---|---|
| 8a | Outcome definition, time horizon, how and when assessed | Protocol §3; [`../data/endpoint_criteria.md`](../data/endpoint_criteria.md), which transcribes every candidate definition and records which was adopted | Reported |
| 8b | Qualifications of outcome assessors where assessment is subjective | Protocol §3, *Outcome Adjudication* — two independent cardiologists, third for disagreements, Cohen's kappa reported | Planned |
| 8c | Blinding of outcome assessment | Protocol §3, *Outcome Adjudication* — adjudicators are blinded to the prediction, the risk tier and each other | Planned |
| 9a | Choice of initial predictors and any pre-selection | `approach.md` §3; effect sizes and their sources in `svd_literature.md` §3, including where our injected effects disagree with the literature | Reported |
| 9b | Definition of all predictors, how and when measured | [`../data/data_dictionary.md`](../data/data_dictionary.md); `approach.md` §3 | Reported |
| 9c | Qualifications of predictor assessors where measurement is subjective | `data_plan.md` §4 — echocardiographic values are read by the performing laboratory and abstracted from note text by a rule-based and a language-model pass, reconciled with an evidence span | Partial — the abstraction layer's accuracy against a physician gold standard has not been measured; it needs clinician time and is named as owed |
| 10 | How the study size was arrived at | Protocol §5, *Sample Size*; [`../protocol/sample_size.md`](../protocol/sample_size.md), generated by `scripts/07_sample_size.py` — three criteria, not one | Reported |
| 11 | How missing data were handled | Protocol §5, *Missing Data* — three mechanisms separated, no outcome imputed, tipping-point analysis for MNAR | Reported |

## Methods — analysis

| Item | What it asks | Where it is answered | Status |
|---|---|---|---|
| 12a | How the data were used, partitioning | Protocol §5, *Train / Validation / Test Split* — patient-level partition, temporal split by implant era; `approach.md` §4 | Reported |
| 12b | How predictors were handled (functional form, rescaling) | `approach.md` §3 | Reported |
| 12c | Model type, rationale, model-building steps, hyperparameter tuning, internal validation | `approach.md` §2 and §4; code in [`../notebooks/pipeline/ml.py`](../notebooks/pipeline/ml.py) | Reported |
| 12d | Heterogeneity across clusters (hospitals, countries) | Protocol §5, *External Validation* | Planned — the prototype has one centre, so there is no cluster structure to quantify |
| 12e | Measures and plots used to evaluate performance, and their rationale | Protocol §5, *Evaluation Metrics*; `approach.md` §4; [`stability.md`](stability.md); [`decision_curve.md`](decision_curve.md) | Reported |
| 12f | Model updating such as recalibration | Protocol §6, *Post-Deployment Monitoring* — recalibration before retraining, with the triggers that fire it | Planned — recalibration at a deploying site is specified and waits for at least 100 local events; recalibration on the training cohort is implemented (`ml.RecalibratedModel`, notebook 04) and changes little |
| 12g | How predictions were calculated at evaluation | Code: `pipeline/ml.py`, driven by `scripts/06` and `scripts/08`; every generated document carries the commit it was produced from | Reported |
| 13 | Class imbalance methods, and any subsequent recalibration | Protocol §5 — resampling and class weighting are **rejected**, with the reason: both distort the calibration the clinical use depends on | Reported |
| 14 | Approaches used to address model fairness | Protocol §6, *Algorithmic Fairness*; subgroup analyses in §5 | Partial — by approach and valve family only; age, sex and ethnicity cannot be audited on this extract and no fairness claim is made |
| 15 | Model output, and the rationale for any classification threshold | `approach.md` §5; [`decision_curve.md`](decision_curve.md) for the threshold analysis and the workload each tier implies | Reported — with the thresholds explicitly provisional until recalibration |
| 16 | Differences between development and evaluation data | `data_plan.md` §5 and [`../data/synthetic/results.md`](../data/synthetic/results.md) — the degradation ladder *is* this item, measured rung by rung rather than described | Reported |
| 17 | Ethics approval and consent | Protocol §6, *IRB / Ethics Review* | Planned — for the real study; the prototype uses a de-identified extract supplied by the organisers |

## Open science

| Item | What it asks | Where it is answered | Status |
|---|---|---|---|
| 18a | Funding and the role of funders | — | Not done — one line for the team: a hackathon submission with no external funding still has to say so |
| 18b | Conflicts of interest | — | Not done — as above |
| 18c | Where the protocol can be accessed | [`../protocol/study_protocol.md`](../protocol/study_protocol.md), in this public repository | Reported |
| 18d | Registration information | — | Not done — the study is not registered; the real study would be, and the protocol should say where |
| 18e | Availability of the study data | `data_plan.md` §6, *Data Governance and Privacy*. The patient extract cannot be shared and is excluded by `.gitignore`; the synthetic cohort is fully reproducible from a fixed seed and a sample is committed in [`../data/synthetic/sample/`](../data/synthetic/sample/) | Reported |
| 18f | Availability of the analytical code | This repository, with `pyproject.toml` and `uv.lock` pinning every dependency, run commands in [`../CONTRIBUTING.md`](../CONTRIBUTING.md), and a commit stamp in every generated document | Reported |

## Patient and public involvement

| Item | What it asks | Where it is answered | Status |
|---|---|---|---|
| 19 | Patient and public involvement, or a statement of none | — | **No involvement.** Stating it is the requirement, and it is stated here. For the real study it is a genuine gap: the trade-off this model asks patients to accept — fewer examinations for some, more for others — is one patients should be consulted on |

## Results

| Item | What it asks | Where it is answered | Status |
|---|---|---|---|
| 20a | Flow of participants, numbers with and without the outcome, follow-up | `data/synthetic/results.md` for the synthetic cohort; [`../data/endpoint_criteria.md`](../data/endpoint_criteria.md) for the extract, where the four event counts are reconciled | Reported |
| 20b | Characteristics, key dates, predictors, sample size, events | `data/synthetic/results.md`; notebook 03 figures | Partial — demographics are absent from the extract, so its characteristics table is unavoidably thin |
| 20c | Comparison of predictor distributions between development and evaluation data | `matching.compare_profiles` and the ladder tables in `results.md` | Reported |
| 21 | Number of participants and events in each analysis | `results.md`; [`stability.md`](stability.md); `endpoint_criteria.md` | Reported |
| 22 | Full model, sufficient for prediction in new individuals | Code plus fixed seeds reproduce every model fitted on the unreshaped cohort exactly; the models reshaped to the extract (`TRAIN_LIKE_REAL`) also need the extract's profile, which is private | Partial — no serialised model object is committed, deliberately: a model fitted on synthetic data must not be portable enough to be mistaken for a clinical tool |
| 23a | Performance with confidence intervals, including key subgroups | `approach.md` §4, including the patient-level bootstrap interval for the extract; [`stability.md`](stability.md) reports mean ± SD and the range across cohorts, with the finding that a single-seed comparison in this repository is noise | Reported |
| 23b | Heterogeneity in performance across clusters | — | N/A — one centre |
| 24 | Results of any model updating | — | Not done at a site — the training-cohort recalibrated models are reported beside the originals in notebook 05, and a local recalibration on the extract was tested and not adopted, because ten events cannot fix an intercept (`approach.md` §4). Miscalibration differs by setting: on the synthetic cohort the models over-predict five-year risk by up to 57% ([`stability.md`](stability.md)); on the extract the regression baseline predicts 15.9% on average against 16.6% observed |

## Discussion

| Item | What it asks | Where it is answered | Status |
|---|---|---|---|
| 25 | Overall interpretation, including fairness, against the objectives and previous studies | README, *Our Approach* and *Key Design Decisions*; `approach.md` §7 | Reported |
| 26 | Limitations and their effect on bias, uncertainty and generalisability | `approach.md` §7; `data_plan.md` §3–5; the caveats section of every generated document | Reported |
| 27a | How poor-quality or unavailable input data should be handled at implementation | Protocol §5, *Missing Data*, final paragraph — the model scores the patient with the indicator set and displays the surveillance gap, rather than refusing to score the patient nobody imaged | Reported |
| 27b | Whether users interact with the input data, and what expertise is required | `approach.md` §6; protocol §6, *Post-Deployment Monitoring* — every changed interval is a clinician's decision | Reported |
| 27c | Next steps for future research, applicability and generalisability | Protocol §5, *External Validation*; [`../data/open_questions.md`](../data/open_questions.md) | Reported |

## What the checklist shows

Counting the 52 rows: 31 are reported, 10 are partial with the limitation stated, 5 are specified
for the real study and not executed here, 5 are honest gaps, and one does not apply. The five gaps
are worth listing on their own, because a checklist that hides its failures is worth nothing:

1. **Funding, conflicts and registration** (18a, 18b, 18d) — three sentences the team owes.
2. **Model updating** (24) — recalibration at a deploying site is the single most consequential
   open item in the modelling work, and it is specified rather than done.
3. **Patient and public involvement** (19) — none, on a design that changes how often patients are
   examined.

Two items are answered better than a typical submission answers them, and both come from the same
decision. Because the pipeline runs on a synthetic cohort whose truth is known, item 16 —
differences between development and evaluation data — is *measured* rung by rung instead of
described, and item 5a's requirement to justify and document synthetic data is met with a
calibrated generator, its parameters, its citations and its tests.
