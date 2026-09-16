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
the time it began. Measured on our own cohort, the gap between a patient's last clean
examination and the one that detected stage-2 deterioration has a median of **1.0 years** and a
maximum of **4.3**. A patient with sparse surveillance is therefore not a low-risk patient; they
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
| 2. Chart abstraction | note text → structured fields with an evidence span; predicts *what the chart says* | rule-based and language-model passes, compared against each other in [`notebooks/cohort/load.py`](notebooks/cohort/load.py) |
| 3. Risk model | time from implant to deterioration, with death as a competing risk; predicts *what happens to the patient* | cohort and degradation ladder complete and reproducible; the fitting scripts are in [`model/`](model/) with no results committed yet |

**No model is fitted on the supplied extract, and that is a finding rather than a shortfall.**
Mapped into the study schema, the extract reaches an examination for 52.1% of patients, averages
1.69 examinations each, carries **no mortality data at all**, and yields 12.0 events per 100
patients — all of them documented reinterventions, because haemodynamic staging needs a reference
examination the extract does not contain. Those figures are printed, alongside the synthetic
rungs they are compared against, by `python -m cohort` into
[`data/synthetic/results.md`](data/synthetic/results.md).

The pipeline is therefore exercised on a **literature-calibrated synthetic cohort**, and the same
unchanged pipeline is run across a **degradation ladder** — the same patients with their data
progressively stripped, ending in the real extract itself. That converts "the data were poor"
into a ranked, quantified statement of which defect costs how much.

## Key Design Decisions

| Decision | Rationale |
|---|---|
| **Competing-risk cumulative incidence (Aalen–Johansen), never Kaplan–Meier** | At a mortality of 62.7% by ten years, one minus Kaplan–Meier answers a question about a population in which nobody dies. NOTION used the same estimator, so our comparison with it is like for like. Implemented in [`synthetic/calibration.py`](notebooks/synthetic/calibration.py). |
| **Events are recorded when *detected*, not when they begin** | The generator emits both ends of the censoring interval (`interval_start_days`, `days_from_implant`). A generator that emitted latent onset times would produce a dataset on which any model looks better than it could ever be in clinic. Enforced by `test_the_censoring_interval_brackets_the_event`. |
| **A mechanistic generator, not a learned one (no CTGAN/synthpop)** | A generative model learns the joint distribution of data you already hold. What is needed here is structure the extract does **not** hold: a trajectory cannot be learned from a dataset containing one trajectory. |
| **One tolerance rule, fixed before any cohort was generated** | Bands are 2 percentage points or a quarter of the published value, whichever is larger, applied uniformly. A per-anchor tolerance chosen by hand is not a standard, it is a description of the result. Enforced by `test_every_anchor_uses_the_stated_tolerance_rule`. |
| **Calibration is not correctness, so correctness is tested separately** | Nine parameters were fitted against the anchors, which is close to saturated. Correctness is established by injecting known hazard ratios and recovering them with an independently implemented Cox fit: the 95% interval covered the injected value in **20 of 21 fits**, mean log bias **+0.0005** ([`synthetic/validation.py`](notebooks/synthetic/validation.py)). The injected effects are themselves cross-checked against published predictor estimates in [`docs/research/svd_literature.md`](docs/research/svd_literature.md) §3.6 — agreements and disagreements alike. |
| **No gradient change, slope or "first versus latest" from the supplied extract** | Most patients with more than one prosthetic mean gradient have every value inside a single note with the examination dates redacted, so the values have no recoverable order. A derived trajectory there would be fabricated. |
| **The last rung of the ladder is the extract itself, not a simulation of it** | The panel is not asked to take the simulation on trust: where the simulated bottom rung and the real one agree, the intermediate rungs can be believed. Enforced by `test_the_simulated_bottom_rung_reproduces_the_real_one`. |

## What Runs Today

```bash
uv sync
uv run pytest                     # 58 tests
cd notebooks && uv run python -m cohort > ../data/synthetic/results.md
```

`python -m cohort` regenerates [`data/synthetic/results.md`](data/synthetic/results.md) — the
calibration table against the published anchors, and the degradation ladder. Every figure in it
is reproduced exactly from a fixed seed; only the generation date on the first line changes.
Its synthetic rungs need nothing but this repository; the final `as_received` rung reads the
consolidated extract and therefore requires `AVR_DATA_DIR` to point at the private data
(see [`.env.example`](.env.example)).

The risk-model layer lives in [`data/build_landmark_table.py`](data/build_landmark_table.py) and
[`model/fit_svd_models.py`](model/fit_svd_models.py). It consumes the abstraction workbook built
by `scripts/01`–`02`, and no results from it are committed yet; see
[`model/approach.md`](model/approach.md).

No patient-level value, note text or identifier appears in this repository, in any figure, or in
any committed notebook output. The source extracts are resolved outside the working tree through
[`notebooks/data_paths.py`](notebooks/data_paths.py), which refuses any path inside it; the
intermediate tables written by the scripts above are gitignored.

---

## Getting Started

> ⚠️ **Do not upload real patient data or clinical notes to this repository.** Any data you use must be de-identified, synthetic, or otherwise cleared for public sharing — this repo (and your fork) may be publicly visible.

### 1. Fork this repository

Go to **[https://github.com/dyaniahealth/dyania-hackathon-avr-durability](https://github.com/dyaniahealth/dyania-hackathon-avr-durability)** and click **Fork** (top-right) to create a copy under your own GitHub account.

### 2. Clone your fork

```bash
git clone https://github.com/<your-username>/dyania-hackathon-avr-durability.git
cd dyania-hackathon-avr-durability
```

### 3. Create your team branch

Branch names must follow this format: `team/<your-team-name>` (lowercase, hyphens for spaces).

```bash
git checkout -b team/your-team-name
```

Examples: `team/panathinea`, `team/valve-guardians`, `team/svd-sentinels`

### 4. Work on your branch

Edit the template files inside `protocol/`, `model/`, `data/`, and `presentation/`. Every `> *Fill in:*` block is a placeholder — replace it with your team's content.

```bash
# Stage and commit as you go
git add .
git commit -m "your message"
```

### 5. Submit — open a Pull Request before the deadline

Push your branch to your fork and open a Pull Request to the original repository:

```bash
git push origin team/your-team-name
```

Then go to your fork on GitHub and click **"Compare & pull request"**.
Set the base repository to `dyania-health/dyania-hackathon-avr-durability` and the base branch to `main`.
Title your PR: `Team submission: <your-team-name>`

> **Deadline: September 17, 2026 — before the presentation session.**
> Only the last commit pushed before the deadline will be evaluated.
> Make sure your PR is open — **do not** merge it.

---

## Repository Structure

```
.
├── README.md                        # This file — team overview and key decisions
├── protocol/
│   └── study_protocol.md            # Full study design (main deliverable)
├── model/
│   ├── approach.md                  # Modelling methodology and validation strategy
│   ├── modeling_brief.md            # Internal work assignment for the model layer
│   └── fit_svd_models.py            # Risk models fitted on the landmark table
├── data/
│   ├── data_plan.md                 # Data sources, preprocessing, availability
│   ├── data_dictionary.md           # Field provenance
│   ├── endpoint_criteria.md         # Candidate failure definitions
│   ├── open_questions.md            # Decisions still open, with their owners
│   ├── build_landmark_table.py      # Landmark and person-period tables
│   └── synthetic/                   # Generated results and a schema sample
├── docs/                            # Per-source data review (labs, meds, notes, quality)
├── scripts/                         # 01–04: extracts → structured tables
├── notebooks/
│   ├── 01_raw_data_overview.ipynb   # What the three extracts contain
│   ├── 02_preprocessing.ipynb       # Cleaning and abstraction
│   ├── synthetic/                   # Cohort generator, calibration, degradation ladder
│   └── cohort/                      # The real extract mapped into the study schema
├── presentation/
│   └── slides.md                    # Outline only — slides.pdf not yet written
└── evaluation/
    └── scoring_rubric.md            # Organisers' rubric
```

---

## Submission Checklist

- [ ] `README.md` — team overview, problem framing, key design decisions
- [ ] `protocol/study_protocol.md` — complete study protocol
- [ ] `model/approach.md` — modelling methodology
- [ ] `data/data_plan.md` — data plan
- [ ] `presentation/slides.pdf` — slide deck
- [ ] `notebooks/` — proof-of-concept (optional, evaluated positively if present)


## uv package manager

1. Install uv on macOS/Linux:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

now you should be able to see the version of uv:
```bash
uv --version
```

2. Go to repository and then, initialize the project with uv:
```bash
uv init
```

3. After git pull, synchronize environment:
```bash
uv sync
```

4. Add dependencies in .venv instead of installing them on the machine, i.e. for pandas:
```bash
uv add pandas
```

5. For removing an unnecessary package from venv, i.e. removing pandas:
```bash
uv remove pandas
```

6. Run python script:
```
uv run -m data.build_landmark_table
```