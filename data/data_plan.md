# Data Plan

> **Instructions:** Describe the data your system would use in a real deployment, what you used for this prototype, and how you handle the gap between the two. Be honest about availability assumptions.

**Status of this document.** Sections 2, 3, 4 and 6 are written from measurements on the
prototype extract and are evidence-backed. Sections 1 and 5 depend on study-design decisions
the team has not taken yet and are marked accordingly. Companion documents:
[`data_dictionary.md`](data_dictionary.md) (field provenance),
[`endpoint_criteria.md`](endpoint_criteria.md) (candidate failure definitions),
[`open_questions.md`](open_questions.md) (decisions and their owners).

---

## 1. Data Sources — Real Deployment

> **DECISION NEEDED** — blocked on the study-design decision in [`open_questions.md`](open_questions.md).
> *Fill in: What data sources would your system ingest in a production clinical environment? For each, describe what it contains, how it would be accessed, and any integration dependencies.*

| Source | Data Type | Access Pathway | Variables Used |
|---|---|---|---|
| | | | |

---

## 2. Data Sources — Prototype / Hackathon

The organisers supplied a de-identified extract from an Epic/Caboodle-style warehouse: three
workbooks, one sheet each, dates shifted and truncated to the calendar year.

| Dataset | Size Used | Why Selected | Limitations as Proxy |
|---|---|---|---|
| Clinical notes | 215 notes, 117 patients | the only source of valve model, size, procedure type and echo haemodynamics | free text; exam dates redacted; 1–4 notes per patient |
| Laboratory results | 43,550 rows → 19,002 after de-duplication, 17 patients | renal function, haemoglobin, NT-proBNP, calcium/phosphate | 56% exact duplicates from export join fan-out; only ~half the rows are laboratory data, the remainder are blood gases, respiratory-therapy fields and device interrogation |
| Medications | 5,807 rows → 2,157 after de-duplication, 17 patients | antithrombotic and heart-failure exposure; procedure-year anchor | 63% exact duplicates; 86% inpatient orders from the index admission, so it is a medication administration record rather than a drug history |

**The extract contains two sub-cohorts that do not overlap.**

| Group | Patients | Notes | Labs / meds |
|---|---|---|---|
| A | `Patient_001`–`Patient_100` | 112 operative reports, 15 procedure notes, 71 progress notes | none |
| B | `Patient_101`–`Patient_117` | exactly one note each, no operative report | all rows |

Patients with surgical documentation have no structured data, and patients with structured data
have no documented index operation. Any analysis must state which group it uses.

---

## 3. Availability Assumptions

Assumptions are listed with what the prototype extract actually shows, because three of them
fail on this data.

| Assumption | Status in the prototype extract | Risk |
|---|---|---|
| Serial follow-up echoes are available per patient | **Fails.** 143 mean-gradient mentions across 54–59 patients, but only **one patient** has values in more than one note or year. | High — removes gradient change and gradient slope as features |
| Echo measurements can be dated | **Fails.** 119 of 143 mean-gradient mentions sit beside a redacted `[DATE]` token. The exam was dated; de-identification removed it. Values can be attributed only to the note's service year. | High — time-to-event resolution is one year at best |
| Age at implant is available | **Fails.** Redacted in 194 of 215 notes; no demographics table exists and the value cannot be recovered by joining the three files. | High — the strongest published predictor of structural valve deterioration is unavailable |
| Valve manufacturer and model are consistently coded | Partly. No implant registry exists; model and size are recoverable from operative-report text for most of cohort A, and in some transcatheter reports the device name itself was redacted. | Medium |
| Echo parameters live in a structured echo table | **Fails.** No echo table exists; all values are embedded in note text under 26 different section headings. | Medium — handled by the abstraction pipeline |
| Follow-up extends beyond the implant year | Partly. 74 of 100 cohort-A patients have all notes in a single year; 41 have any later note. | High — heavy administrative censoring |

In a production deployment the first three assumptions would hold: a hospital's own echo
database carries exam dates and serial studies, and the demographics table carries age. The
prototype's limitations are artefacts of the de-identified extract, not of the clinical setting —
this distinction is load-bearing for the protocol and is stated explicitly in the study design.

---

## 4. Preprocessing and Data Quality

### Data Cleaning

- **De-duplication first.** Laboratory and medication rows contain 56% and 63% exact duplicates
  respectively, caused by a join fan-out in the export (one row repeats 826 times). Any count
  taken before de-duplication is inflated roughly two-fold.
- **Analyte normalisation.** The laboratory file uses 703 component names and 76 distinct unit
  strings for a much smaller set of analytes: creatinine appears under three names, haemoglobin
  under three, eGFR under five including race-stratified variants. Two export eras use different
  unit spellings (`MG/DL` vs `mg/dL`, `K/uL` vs `k/uL`). LOINC is present on only 32% of rows and
  is not one-to-one with component names. Normalisation therefore runs on a curated component
  map, not on names or LOINC alone.
- **Numeric parsing is whitelisted.** Date-times and identifiers occur inside the numeric value
  column, so parsing is restricted to an explicit list of analytes. Censored results stored as
  strings (`>60`, `<0.01`) are parsed to the limit and flagged.
- **Flags are not normality.** The abnormal flag is populated only when a result was flagged;
  a null means no flag was attached, not a normal result.
- **Free-text echo values** are abstracted as described below rather than parsed from a table.

### Missing Data Strategy

Missingness in this extract is structural rather than random: a patient either has an operative
report or has structured data. Prototype policy is to report availability per feature and per
sub-cohort, and to carry explicit missingness indicators rather than impute across the two
groups. Imputation across sub-cohorts would invent the very linkage the extract lacks.

### Temporal Alignment

Year resolution is the hard ceiling. Every extracted value is attributed to the **service year
of the note that carries it** and never to an exam date. Within a single note, multiple
measurements frequently appear — 33 of the 34 patients with more than one prosthetic mean
gradient have all of those values inside one note, quoting a current study alongside a previous
one. Because the exam dates are redacted, those values have **no recoverable order**. They are
therefore reported as a range within the note, and no change, delta or slope is computed from
them. A derived "first versus latest gradient" on this extract would be a fabricated trajectory.

### Label / Ground Truth Construction

Labels are proposed by rule from the abstracted values and carry one of four statuses —
`accept`, `reject`, `borderline`, `missing information` — following the candidate criteria in
[`endpoint_criteria.md`](endpoint_criteria.md). Every proposed label points back to the text
that supports it. The rule-based pass is a **proposal for clinician adjudication, not a
ground truth**.

Current yield on the prototype extract, all 117 patients:

| Status | Patients | Basis |
|---|---|---|
| accept | 5 | reintervention for a failed bioprosthesis |
| reject | 15 | prosthetic echo present, no deterioration criteria met |
| borderline | 12 | haemodynamic criteria met without a baseline, or failure language, or a competing non-structural cause |
| missing information | 85 | 69 with no prosthetic echo value at all, 16 with a baseline-year echo only |

**32 of 117 patients (27%) receive an assessable label**, and cohort B contributes none of the
accepts. Event counts at this scale are illustrative of the pipeline, never an incidence
estimate. Label quality is assessed by clinician review of a held-out sample frozen before the
extraction rules were tuned, reported as per-question agreement, positive predictive value after
review, and negative predictive value on a random sample of rejections.

---

## 5. Synthetic Data

### Why a synthetic cohort is necessary here

The prototype extract cannot support the analysis the protocol specifies, and no amount of
cleaning changes that. It yields 32 assessable labels from 117 patients, 5 of them failures;
exactly one patient has echocardiographic values in more than one year; age is redacted
throughout; and timing is known only to the calendar year. The three things the landmark model
consumes — serial dated gradients, exact event times, and age at implant — are precisely the
three the extract lacks.

A synthetic cohort is therefore not a substitute for data we failed to obtain. It is the only
way to execute the specified pipeline end to end and report what it does, while keeping every
number that touches a patient descriptive.

### How it is generated

The generator is `notebooks/synthetic/`, run as `python -m synthetic`. It is a **mechanistic**
model, not a learned one, and the distinction matters: a generative model such as CTGAN or
synthpop learns the joint distribution of the data you already hold, whereas what is needed here
is structure the extract does **not** hold. A trajectory cannot be learned from a dataset
containing one trajectory.

The cohort is built as a causal chain, in this order:

1. **Covariates at implant** — age, sex, body surface area, approach, valve model and label size,
   and from those the effective orifice area and the patient–prosthesis mismatch grade at the
   VARC-3 indexed cut-offs.
2. **Latent times** — a Weibull time to the *onset* of deterioration with log-linear covariate
   effects, and an independent Weibull time to death. Onset is a biological event that nobody
   observes.
3. **A surveillance process** — guideline echocardiographic visits, extra studies triggered by
   symptoms once deterioration has begun, and informative dropout.
4. **Haemodynamics at each visit** — drifting gently before onset, accelerating after it, with
   proportional measurement error representing inter-observer and beat-to-beat variability.
5. **Observed events** — established by applying the VARC-3 criteria to each examination against
   that patient's own reference examination.

Step 5 is what makes the cohort honest. An event is recorded at the examination that *detects*
it, never at the latent onset, so the outcome is interval-censored exactly as it is in a real
surveillance cohort. A generator emitting latent onset times would produce a dataset on which any
model looks better than it could ever be in clinic.

Every parameter, with its published source or an explicit ASSUMPTION marker, is in
`notebooks/synthetic/parameters.py`. Every row of every table carries `source = "simulated"` and
a `time_resolution` field, so a reader holding one CSV with no access to this repository can
still tell that nothing in it came from a patient.

### Calibration, and what is honestly claimed

Six parameters were chosen against published evidence: two Weibull scales solved by bisection
against the NOTION ten-year moderate-or-severe figures, and four shape parameters selected from a
small grid. Those six reproduce **six of seven** published quantities, across three independent
sources, two endpoints and four time horizons.

| quantity | subgroup | horizon | published | cohort | within band |
|---|---|---|---|---|---|
| moderate or severe SVD | SAVR | 10 y | 20.8% | 19.8% | yes (targeted) |
| moderate or severe SVD | TAVR | 10 y | 15.4% | 14.5% | yes (targeted) |
| severe SVD | SAVR | 10 y | 10.0% | 10.3% | yes |
| severe SVD | TAVR | 10 y | 1.5% | 7.4% | **no** |
| bioprosthetic valve failure | all | 5 y | 3.6% | 1.5% | yes |
| bioprosthetic valve failure | all | 7 y | 7.2% | 4.3% | yes |
| severe SVD | TAVR | 7.8 y | 5.9% | 5.4% | yes |

Sources: NOTION ten-year echocardiographic follow-up; PARTNER 3 at five and seven years; UK TAVI
registry at a median of 7.8 years. Incidence is reported as an Aalen–Johansen cumulative
incidence function, never as one minus Kaplan–Meier, because death is a competing risk and
Kaplan–Meier would answer a question about a population in which nobody dies.

**The one miss is reported rather than removed, because the published anchors contradict each
other.** NOTION's own figures imply that 48% of deteriorated surgical valves become severe within
ten years but only 10% of transcatheter ones — a five-fold difference in progression conditional
on deterioration, between two arms of one trial. The UK TAVI registry meanwhile reports severe
deterioration in 5.9% of transcatheter patients at a *shorter* horizon, roughly four times the
NOTION figure. No single cohort can satisfy both. This one sides with the registry, matching it
closely and missing NOTION. The alternative — a separate progression process fitted per arm —
would reproduce both numbers by fitting the sampling noise of a few dozen patients.

### Internal validation

Calibration shows the cohort resembles the literature; it does not show the code is correct. That
is established by a **recovery test**: hazard ratios are injected into the generator, a Cox model
is fitted to the output, and the estimates are compared with what went in. The Cox model is
implemented directly against the Breslow partial likelihood rather than taken from the library
the modelling workstream uses, so that a shared misunderstanding cannot pass unnoticed in both
places.

- **Latent hazard:** all **8 of 8** injected hazard ratios are recovered inside their 95%
  confidence intervals. This validates the generator and the analysis path together.
- **Observed events:** the same effects estimated from what an analyst actually sees — detections
  at scheduled examinations, with death competing and patients dropping out — are **attenuated**,
  with a median attenuation of the log hazard ratio of 0.96 and the weakest effects attenuating
  most (diabetes 0.76, chronic kidney disease 0.82). This is not a defect. It quantifies how much
  sparse guideline-interval surveillance biases effect estimates toward the null, and it applies
  to any real study built the same way, which is why it is restated in the limitations.

### The degradation ladder

The same cohort is emitted five times, each rung removing one property of the data while leaving
the patients, their biology and their events untouched. The truth is identical on every rung;
only what an analyst can see of it changes. One unchanged modelling pipeline run across the rungs
therefore measures exactly one thing: what each defect costs.

| rung | defect added | mirrors |
|---|---|---|
| `ideal` | none | the data the protocol asks a site to supply |
| `no_age` | age at implant removed | `[AGE]` redacted in 194 of 215 notes |
| `year_resolution` | all timing collapsed to the calendar year | date shifting and truncation in the extract |
| `single_echo` | one examination per patient, no reference study | one patient in the extract has values in more than one year |
| `as_supplied` | haemodynamics kept for only 27% of patients | the measured yield of chart abstraction: 32 of 117 |

The rungs are cumulative. This converts a statement no panel can act on — "the data were poor" —
into a ranked, quantified account of which defect costs most, which is the argument a site needs
before it will fund dated, serial, linkable echocardiography.

### Limitations

- **A synthetic cohort cannot validate a model, only exercise it.** Every performance figure
  computed on it measures the pipeline, not clinical accuracy, and is labelled synthetic wherever
  it appears.
- **The covariate structure is an assumption.** Interactions the literature has not reported
  cannot be present, so a model that would have found them will look no worse for missing them.
- **Effect sizes are injected, so they are recoverable by construction.** The recovery test proves
  the code is correct; it says nothing about whether those effect sizes are right.
- **Calibration rests on trial populations** that are narrower than the real-world cohort the
  protocol describes, and on anchors that disagree with one another.

### How synthetic data is replaced in the real study

The synthetic cohort is scaffolding with a defined removal point. On execution, each rung is
replaced by the corresponding real quantity: the site's echocardiography database supplies dated
serial examinations, its demographics table supplies age, and its operative and catheterisation
records supply reinterventions. The generator then keeps exactly one role — as the simulation
against which the analysis code is tested before it touches patient data, which is how it should
be used in any case.

---

## 6. Data Governance and Privacy

- **The extract never enters this repository.** The source workbooks live outside the working
  tree and are resolved at runtime through `notebooks/data_paths.py`, which reads `AVR_DATA_DIR`
  and refuses any path inside the repository. `.gitignore` additionally blocks spreadsheet,
  CSV, parquet and pickle files.
- **Derived tables are treated as source data.** Abstraction output retains verbatim note
  snippets as evidence for each extracted value, so those tables are held with the source data
  outside the repository. Only schema and aggregate counts are committed.
- **What appears in this repository, the slides and any figure** is aggregate only: counts,
  distributions and per-field availability. No note text, no patient-level values, no
  pseudonymous identifiers tied to values.
- **Inference stays local.** Any language-model step in the abstraction pipeline runs on the
  machine holding the data; note text is not sent to an external API. This mirrors the
  on-premise deployment assumed in the protocol.
- **Quality and identifiability observations** made while reviewing the extract were reported
  directly to the organisers rather than documented here.
- In a production deployment the equivalent controls are a data use agreement with the
  operating site, inference behind the institutional firewall, and access through the hospital's
  own identity management.
