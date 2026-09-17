# Dyania Health Hackathon 2026 — Team Submission Repository

**Challenge:** Build a study — using machine learning, a statistical model, or whatever approach you prefer — proposing a protocol to predict aortic valve durability in patients with a bioprosthetic aortic valve replacement.
**Event:** September 15–17, 2026 (3 days)
**Team size:** 2–3 ML engineers
**Team:** `dyanooumenoi`
**Members:** `[Name — Role]`, `[Name — Role]`, `[Name — Role]`

**Study:** *Dynamic Prediction of Bioprosthetic Aortic Valve Failure to Guide Personalised Surveillance*

---

## Problem Statement

Among adults who are alive and free of valve failure following bioprosthetic aortic valve
replacement, can clinical information available at each postoperative visit predict the risk of
bioprosthetic valve failure over the next five years, with risk estimates updated at every
subsequent visit?

**Why this matters.**
- **Failure is common.** At ten years, NOTION reports moderate or severe structural valve
  deterioration in 20.8% of surgical and 15.4% of transcatheter recipients.
- **Many patients die first.** All-cause mortality in the same trial was 62.7%, so every risk has to
  account for death.
- **Surveillance ignores individual risk.** Guidelines schedule echocardiograms by the calendar, the
  same for every patient, although the risk of deterioration is not the same.
- **Deterioration is found late.** It is seen only when someone images the valve, often long after
  it began: in our synthetic cohort, up to 4.2 years later.
- **Who pays for late detection.** A patient with sparse follow-up is not a low-risk patient, but an
  unobserved one, and late identification means a reintervention in an older, frailer patient.

## Our Approach

**Data.** A deployment would use:
- operative reports
- serial echocardiograms
- clinical notes
- medications and laboratory results
- reintervention and death records

The hospital extract we were given has 215 notes from 117 patients, with dates cut to the year, age
redacted, no death records and 1.62 echocardiograms per patient. We extract structured fields from
the notes with rules and with language-model agents: an orchestrator splits the notes among
sub-agents, which quote the sentence behind every value
([`data/data_plan.md`](data/data_plan.md)).

**Synthetic cohort.** The extract has only 10 failure events and cannot train or test a model. We
therefore built a synthetic cohort from published evidence ([`notebooks/synthetic/`](notebooks/synthetic/)):
- it follows how valves actually fail, in three modes;
- death is a competing event;
- failure is recorded only at the echocardiogram that detects it;
- it is calibrated against published trials;
- it is checked by recovering known effects.

**Model.** A competing-risks, discrete-time model is re-evaluated at every follow-up visit (a
landmark design: 6 months, 1 year, then yearly).
- **Output:** the risk of structural valve failure at 2, 5 and 8 years.
- **Primary model:** gradient boosting with monotone clinical constraints.
- **Baseline:** a transparent regression model on the published risk factors.
- **Comparators:** valve age alone, the guideline calendar, and a Cox model.

([`model/approach.md`](model/approach.md))

**Clinically actionable.** The 5-year risk sets a surveillance tier:

| 5-year risk | tier | next echocardiogram |
|---|---|---|
| under 5% | low | guideline schedule |
| 5% to 15% | moderate | every 2 years |
| 15% or more | high | every year |

The decision curve shows that acting on the model beats both scanning everyone and changing nothing
from 5% risk upward. The tiered schedule needs 517 fewer examinations per 1,000 patient-years than an
annual echocardiogram for everyone ([`model/decision_curve.md`](model/decision_curve.md)).

**The study.** [`protocol/study_protocol.md`](protocol/study_protocol.md) specifies:
- the population and the VARC-3 endpoint;
- ground-truth adjudication;
- 3,580 patients ([`protocol/sample_size.md`](protocol/sample_size.md));
- external validation;
- ethics and privacy.

**What we found.** Main results come from full-quality synthetic data, with separate training,
validation and test sets, over five independent draws of 6,000 patients
([`model/approach.md`](model/approach.md) §4).

| 5-year AUC | all visits | first postoperative visit | 5 years or later |
|---|---|---|---|
| regression baseline | 0.76 | 0.61 | 0.74 |
| gradient boosting (primary) | 0.76 (0.83 at 2 years) | 0.60 | 0.73 |
| valve age only | 0.73 | 0.50 | 0.48 |

- **The question can be answered, modestly, from the first visit.** Information available at the
  first postoperative visit separates patients (AUC about 0.60, where valve age gives 0.50), and
  the predicted risk there is well calibrated (about 6% against 6.6% observed).
- **Prediction improves at later visits** as serial echocardiograms accumulate.
- **The clinician's factors matter.** Aligning the features with the team clinician's list raised the
  5-year AUC from 0.73–0.74 to 0.77–0.78, and at the first visit from about 0.55 to 0.62–0.64
  (single cohort).
- **Real extract, scored, never trained on.** 51 valve episodes, 10 events. The same models reach a
  5-year AUC of 0.72 (regression) and 0.69 (gradient boosting), no better than valve age alone
  (0.72) with this few events.
- **What limits the result.** The extract lacks ages, dated serial echocardiograms and death records.
  That gap is what the protocol is designed to close.

## Key Design Decisions

| Decision | Rationale |
|---|---|
| **Competing-risk cumulative incidence, never Kaplan–Meier** | Most bioprosthesis recipients die with a working valve (62.7% mortality at 10 years in NOTION). One minus Kaplan–Meier would describe a population in which nobody dies and overstate failure. |
| **Landmark design: re-predict at every visit** | The decision the model supports, when to image next, recurs at every visit, and new echocardiograms change the risk. Each prediction uses only what was known at that visit. |
| **Events dated when detected, and the interval kept** | Deterioration begins between examinations. Recording the detecting study, not the hidden onset, keeps the synthetic data as imperfect as a real surveillance cohort; otherwise any model would look better than it could be in clinic. |
| **VARC-3 as ground truth, against the patient's own reference echo** | The consensus definition is a change from the post-operative baseline, with a corroborating fall in orifice area or DVI. Reinterventions for structural failure count; endocarditis, thrombosis and paravalvular leak do not. |
| **A mechanistic, literature-calibrated synthetic cohort** | The extract has one or two notes per patient, so a trajectory cannot be learned from it. The generator is built from published effect sizes, lands inside a fixed tolerance for 8 of 10 published anchors, and recovers injected effects in 70 of 75 tests. |
| **One code path for real and synthetic data** | The synthetic cohort is converted into the same tables the extract preprocessing writes, so both go through identical label, feature and model code. |
| **Monotone constraints and a short clinical feature list** | Risk should never fall as a stenosis marker worsens. On the synthetic data reshaped to look like the extract, removing the constraints cost the boosted model 0.14 of AUC at 5 years; on full-quality synthetic data the unconstrained model scores slightly higher (5-year AUC 0.75 against 0.73), so the constraints are kept for clinical sense and for sparse data, at a small cost. The feature list follows the published risk factors and the team clinician's list. Surveillance counts are excluded, because how often a valve is imaged reflects concern, not the valve. |
| **Synthetic train, validation and test; the real extract as a check** | As the organisers recommended, the main results are trained, validated and tested on synthetic data, split by implant year and grouped by patient, and repeated over independent draws. The real extract is scored and never trained on, with intervals that resample valves, not rows. |

---

## Getting Started

> ⚠️ **Do not upload real patient data or clinical notes to this repository.** Any data you use must be de-identified, synthetic, or otherwise cleared for public sharing — this repo (and your fork) may be publicly visible.

```bash
uv sync
uv run pytest -q                                   # 69 tests: synthetic cohort and pipeline
uv run python scripts/05_report_synthetic.py       # regenerates data/synthetic/results.md
uv run python scripts/06_model_stability.py        # regenerates model/stability.md
uv run python scripts/07_sample_size.py            # regenerates protocol/sample_size.md
uv run python scripts/08_decision_curve.py         # regenerates model/decision_curve.md
uv run jupyter lab                                 # notebooks 01 to 05, in order
```

- **No private data needed:** the tests and scripts 05 to 08. Each stamps its document with the
  commit it ran against.
- **Private data needed:** notebooks 01, 02 and 05, and scripts 01, 03 and 09
  ([`scripts/README.md`](scripts/README.md), [`notebooks/README.md`](notebooks/README.md)).
- **Setup, data handling and submission:** [`CONTRIBUTING.md`](CONTRIBUTING.md).

No patient-level value, note text or identifier appears in this repository, in any figure, or in
any committed notebook output.

---

## Repository Structure

```
.
├── README.md                        # This file — team overview and key decisions
├── CONTRIBUTING.md                  # Setup, data handling, submission
├── protocol/
│   ├── study_protocol.md            # Full study design (main deliverable)
│   └── sample_size.md               # Generated: how large the study has to be
├── model/
│   ├── approach.md                  # Model methodology and validation strategy
│   ├── stability.md                 # Generated: model comparison over 8 synthetic cohorts
│   ├── decision_curve.md            # Generated: net benefit and surveillance workload
│   ├── tripod_ai.md                 # TRIPOD+AI reporting checklist
│   └── modeling_brief.md            # Original work assignment, kept as a record
├── data/
│   ├── data_plan.md                 # Data sources, preprocessing, availability
│   ├── data_dictionary.md           # Field provenance
│   ├── endpoint_criteria.md         # Failure definitions and event counts
│   ├── open_questions.md            # Open decisions and their owners
│   └── synthetic/                   # Generated calibration and ladder results, schema sample
├── docs/                            # Review of the supplied data, and research notes
├── scripts/                         # 01, 03 extracts to tables; 05–08 regenerate evidence; 09 measures the extract
├── notebooks/
│   ├── 01_raw_data_overview.ipynb   # What the three extracts contain
│   ├── 02_preprocessing.ipynb       # Cleaning, valves, echo timeline, events
│   ├── 03_data_preparation.ipynb    # Labels, landmarks, features
│   ├── 04_model_training.ipynb      # Comparators, baseline, primary model
│   ├── 05_results.ipynb             # Scoring on the real extract
│   ├── figures/                     # Aggregate figures
│   ├── pipeline/                    # Shared code and its tests
│   └── synthetic/                   # Synthetic cohort generator and its tests
├── results/                         # Run ledger: every evaluation with its settings
├── presentation/
│   ├── slides.md                    # Deck content and script
│   └── figures/                     # System and model diagrams
└── evaluation/
    └── scoring_rubric.md            # Organisers' rubric
```

---

## Submission Checklist

- [x] `README.md` — team overview, problem framing, key design decisions *(team members still to be listed)*
- [x] `protocol/study_protocol.md` — complete study protocol
- [x] `model/approach.md` — model methodology
- [x] `data/data_plan.md` — data plan
- [ ] `presentation/slides.pdf` — slide deck
- [x] `notebooks/` — proof-of-concept implementation, five notebooks end to end
