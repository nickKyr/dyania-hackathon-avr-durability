# Dyania Health Hackathon 2026 — Team Submission Repository

**Challenge:** Build a study — using machine learning, a statistical model, or whatever approach you prefer — proposing a protocol to predict aortic valve durability in patients with a bioprosthetic aortic valve replacement.
**Event:** September 15–17, 2026 (3 days)
**Team:** `dyanooumenoi`
**Members:** *(names and roles — to be completed by the team)*

---

## Problem Statement

A bioprosthetic aortic valve wears out, and the published rates are not small: at ten years
NOTION reports moderate-or-severe structural valve deterioration in **20.8%** of surgical and
**15.4%** of transcatheter recipients, with all-cause mortality of **62.7%** in the same cohort.
Every figure we use is held with its primary citation in
[`notebooks/synthetic/parameters.py`](notebooks/synthetic/parameters.py).

Two consequences shape everything in this repository. First, **death competes with
deterioration**: in a cohort where most patients die before ten years, an estimator that ignores
the competing risk overstates how many valves fail. Second, **deterioration is only ever seen at
an echocardiogram**, so the time recorded is the time of the examination that detected it, not
the time it began. Measured on the synthetic cohort, the gap between a patient's last clean
examination and the one that detected stage-2 deterioration has a median of **1.1 years** and a
maximum of **4.2**. A patient with sparse surveillance is therefore not a low-risk patient; they
are an unobserved one.

The gap this work addresses is the surveillance schedule itself: guidelines set echocardiographic
follow-up by the calendar, identically for every patient, while the risk of deterioration is not
distributed identically at all.

## Our Approach

The work is built as three layers, kept deliberately separate because they answer different
questions and are evaluated differently.

| Layer | What it does | Status in this repository |
|---|---|---|
| 1. Data processing | de-duplication, analyte and unit normalisation, whitelisted numeric parsing, alignment to the note's service year | [`scripts/`](scripts/), [`notebooks/01`](notebooks/01_raw_data_overview.ipynb), [`notebooks/02`](notebooks/02_preprocessing.ipynb) — measurements in [`data/data_plan.md`](data/data_plan.md) |
| 2. Chart abstraction | note text → structured fields with an evidence span; predicts *what the chart says* | rule-based and language-model passes in [`scripts/`](scripts/), reconciled in [`notebooks/02`](notebooks/02_preprocessing.ipynb) |
| 3. Risk model | time from implant to deterioration, with death as a competing risk; predicts *what happens to the patient* | labels and features in [`notebooks/03`](notebooks/03_data_preparation.ipynb), models in [`notebooks/04`](notebooks/04_model_training.ipynb), scoring on the extract in [`notebooks/05`](notebooks/05_results.ipynb), code in [`notebooks/pipeline/`](notebooks/pipeline/) |

**No model is fitted on the supplied extract, and that is a finding rather than a shortfall.**
Mapped into the study schema, the extract has an examination for 83.8% of patients, averages
1.62 examinations each, has more than one gradient for only 16.2%, carries **no mortality data at
all**, and records 8.55 affected patients per 100. Nine of those ten valve episodes are documented
reinterventions; only one is a stage-2 deterioration seen on echo, because haemodynamic staging
needs a reference examination the extract rarely contains. Those figures are printed, alongside
the synthetic rungs they are compared against, in
[`data/synthetic/results.md`](data/synthetic/results.md). Endpoint **rows** are not the same
quantity as affected patients or affected valves, and this repository reports all three; the four
counts and the frame each belongs to are reconciled in
[`data/endpoint_criteria.md`](data/endpoint_criteria.md).

Simulating that same poverty on a cohort whose truth we know puts a number on what it costs:
extract-quality surveillance loses **34% of the patients who deteriorate and 42% of the endpoint
rows** they would have generated. Losing follow-up rarely erases a patient entirely; it erases the
later stages of their course, which is exactly what a durability model learns from.

The pipeline is therefore trained on a **literature-calibrated synthetic cohort**, and the same
descriptive measures are computed on every rung of a **degradation ladder**: the same patients
with their data progressively stripped, ending in the real extract itself. That converts "the
data were poor" into a ranked, quantified statement of which defect costs how much. The models are
then scored, never trained, on the extract: over five synthetic draws the regression baseline
reaches a 5-year AUC of 0.71 ± 0.02 on its 51 valve episodes, no better than valve age alone with
only 10 events, and its mean predicted risk (15.9%) falls inside the observed 7.7% to 27.6%
([`model/approach.md`](model/approach.md) §4).

## Key Design Decisions

| Decision | Rationale |
|---|---|
| **Competing-risk cumulative incidence (Aalen–Johansen), never Kaplan–Meier** | At a mortality of 62.7% by ten years, one minus Kaplan–Meier answers a question about a population in which nobody dies. NOTION used the same estimator, so our comparison with it is like for like. Implemented in [`notebooks/synthetic/calibration.py`](notebooks/synthetic/calibration.py). |
| **Events are recorded when *detected*, not when they begin** | The generator emits both ends of the censoring interval (`interval_start_days`, `days_from_implant`). A generator that emitted latent onset times would produce a dataset on which any model looks better than it could ever be in clinic. Enforced by `test_the_censoring_interval_brackets_the_event`. |
| **A mechanistic generator, not a learned one (no CTGAN/synthpop)** | A generative model learns the joint distribution of data you already hold. What is needed here is structure the extract does **not** hold: a trajectory cannot be learned from a dataset containing one trajectory. |
| **One tolerance rule, fixed before any cohort was generated** | Bands are 2 percentage points or a quarter of the published value, whichever is larger, applied uniformly. A per-anchor tolerance chosen by hand is not a standard, it is a description of the result. Enforced by `test_every_anchor_uses_the_stated_tolerance_rule`. |
| **Calibration is not correctness, so correctness is tested separately** | Nine parameters were fitted against the anchors, which is close to saturated. Correctness is established by injecting known hazard ratios and recovering them with an independently implemented Cox fit, one per failure mode: the 95% interval covered the injected value in **70 of 75 fits (93.3%)**, mean log bias **−0.0030** ([`notebooks/synthetic/validation.py`](notebooks/synthetic/validation.py)). The injected effects are themselves cross-checked against published predictor estimates in [`docs/research/svd_literature.md`](docs/research/svd_literature.md) §3.6 — agreements and disagreements alike. |
| **No gradient change from values that share a note** | Most patients with more than one prosthetic mean gradient have every value inside a single note with the examination dates redacted, so the values have no recoverable order. A change is computed only against a genuine reference examination in its own note, which exists for 4 of the 51 modelled valve episodes; any other derived trajectory would be fabricated. |
| **The last rung of the ladder is the extract itself, not a simulation of it** | The panel is not asked to take the simulation on trust: where the simulated bottom rung and the real one agree, the intermediate rungs can be believed. Today they do not fully agree: the simulated rung reaches an examination for 52.1% of patients against 83.8% in the extract, and records more endpoint rows (15.17 against 8.55 per 100), so the simulation of the extract is itself still too pessimistic about surveillance. |
| **One route for real and synthetic data** | The synthetic cohort is converted into the tables `02_preprocessing.ipynb` writes for the extract, so both go through identical label, feature and model code. On every ladder rung the conversion reproduces the generator's own tables row for row. |
| **Train on data that look like the target** | Trained on the ideal cohort, the boosted model ranked the real valves worse than chance. The synthetic cohort is therefore reshaped to the extract's measured gaps before training (`TRAIN_LIKE_REAL`): case mix, which risk factors the notes record, gradient levels and when echoes happen. |

## What Runs Today

```bash
uv sync
uv run python -m pytest notebooks/synthetic/tests -q     # 54 tests on the synthetic cohort
uv run python -m pytest notebooks/pipeline/tests -q      # 15 tests on labels, features and matching
uv run python scripts/05_report_synthetic.py             # regenerates data/synthetic/results.md
uv run python scripts/06_model_stability.py              # regenerates model/stability.md
uv run python scripts/07_sample_size.py                  # regenerates protocol/sample_size.md
uv run python scripts/08_decision_curve.py               # regenerates model/decision_curve.md
uv run python scripts/01_extract_rules.py                # needs the extract; then 03
uv run jupyter lab                                        # notebooks 01 to 05, in order
uv run python scripts/09_real_extract_rung.py            # needs notebook 02's tables; then rerun 05
```

The first six need no private data: everything they report is generated from a fixed seed and can
be reproduced on any clone. Each one writes the date and the commit it ran against into the
document it produces, so a number that has drifted away from the code is visible rather than
silent.

- `02_preprocessing.ipynb` turns the extract into valves, echo timelines, events and follow-up.
- `03_data_preparation.ipynb` builds labels, landmarks and features for the synthetic cohort
  (reshaped to look like the extract by default) and explores them.
- `04_model_training.ipynb` trains the comparators, the regression baseline and the boosted model,
  and checks them on later synthetic valves.
- `05_results.ipynb` scores every trained model on the real extract, with bootstrap intervals,
  calibration, decision curves and subgroups, and records the run in
  [`results/LEDGER.md`](results/LEDGER.md).

Every synthetic number is labelled synthetic. The real extract is scored and never trained on.

No patient-level value, note text or identifier appears in this repository, in any figure, or in
any committed notebook output. The source extracts sit in `data/`, and `.gitignore` blocks every
spreadsheet, CSV, parquet, pickle and derived table there.

---

## Repository Structure

```
.
├── README.md                        # This file — team overview and key decisions
├── CONTRIBUTING.md                  # Setup, data handling, how to regenerate the evidence
├── protocol/
│   ├── study_protocol.md            # Full study design (main deliverable)
│   └── sample_size.md               # Generated: how large the real study has to be
├── model/
│   ├── approach.md                  # Modelling methodology and validation strategy
│   ├── stability.md                 # Generated: which model differences survive re-drawing the cohort
│   ├── decision_curve.md            # Generated: at which thresholds acting on the model pays, and what it costs
│   ├── tripod_ai.md                 # TRIPOD+AI reporting checklist, item by item, gaps included
│   └── modeling_brief.md            # Internal work assignment for the model layer
├── results/                         # Run ledger: every evaluation on the extract, with its settings
├── data/
│   ├── data_plan.md                 # Data sources, preprocessing, availability
│   ├── data_dictionary.md           # Field provenance
│   ├── endpoint_criteria.md         # Candidate failure definitions
│   ├── open_questions.md            # Decisions still open, with their owners
│   └── synthetic/                   # Generated results and a schema sample
├── docs/                            # Per-source data review and research notes
├── scripts/                         # 01, 03 extracts → tables; 05–08 regenerate evidence; 09 measures the extract rung
├── notebooks/
│   ├── 01_raw_data_overview.ipynb   # What the three extracts contain
│   ├── 02_preprocessing.ipynb       # Cleaning and abstraction
│   ├── 03_data_preparation.ipynb    # Labels, landmarks, features, selection
│   ├── 04_model_training.ipynb      # Comparators, baseline, boosted model
│   ├── 05_results.ipynb             # Scoring on the real extract, run ledger
│   ├── figures/                     # Aggregate figures written by the notebooks
│   ├── pipeline/                    # Shared code: prep, landmarks, matching, ml, evaluation, ledger, viz (+ tests)
│   └── synthetic/                   # Cohort generator, calibration, degradation ladder
├── presentation/
│   ├── slides.md                    # Deck content and the spoken script; slides.pdf still to be built
│   └── figures/                     # Diagram used on slide 3
└── evaluation/
    └── scoring_rubric.md            # Organisers' rubric
```

---

## Submission Checklist

- [x] `README.md` — team overview, problem framing, key design decisions *(team members still to be listed)*
- [x] `protocol/study_protocol.md` — complete study protocol *(open decisions are named with their owner)*
- [x] `model/approach.md` — modelling methodology
- [x] `data/data_plan.md` — data plan
- [ ] `presentation/slides.pdf` — slide deck *(content and script written in `presentation/slides.md`; PDF not built)*
- [x] `notebooks/` — proof-of-concept, five notebooks end to end

Setup, data-handling rules and the submission mechanics are in
[`CONTRIBUTING.md`](CONTRIBUTING.md).
