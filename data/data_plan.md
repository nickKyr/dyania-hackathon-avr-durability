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

The specification is not prose: it is [`notebooks/synthetic/schema.py`](../notebooks/synthetic/schema.py).
The four tables defined there, and their columns, are exactly what a site must supply for the
protocol to run, and every rung of the degradation ladder is validated against them. A site that
can populate these four tables can run this study; a site that cannot is measurably worse off,
and the ladder in [`synthetic/results.md`](synthetic/results.md) says by how much.

| Source | Data Type | Access pathway (assumed) | Variables used — the `schema.py` table it fills |
|---|---|---|---|
| Implant registry / operative record | one row per implant | institutional registry export, or the operative report through the abstraction pipeline when no registry exists | `patients`: `implant_year`, `approach`, `valve_model`, `valve_size_mm`, `eoa_cm2` |
| Demographics | one row per patient | EHR demographics table | `patients`: `age_at_implant`, `sex`, `bsa_m2` — and from these `eoa_index_cm2_m2` and `ppm_grade` at the VARC-3 cut-offs |
| Structured echocardiography | one row per examination, **dated** | the echo laboratory's own reporting database, not the note | `echos`: `days_from_implant`, `is_reference`, `mean_gradient_mmhg`, `peak_gradient_mmhg`, `dvi`, `eoa_cm2`, `ar_grade`, `lvef_pct` |
| Procedures | reinterventions with their stated indication | EHR procedure table | `events`: `event_type = bvf_reintervention`, with the indication needed to separate structural from endocarditis- or paravalvular-leak-driven reintervention |
| Vital status | date and cause of death | hospital registry or national death index | `events`: `event_type = death` — without it the competing risk is unobserved and cumulative incidence is not comparable across cohorts |
| Comorbidity | diagnoses at implant | EHR problem list / diagnosis table | `patients`: `diabetes`, `ckd`, `smoking`, `bicuspid` |
| Encounter record | last contact and censoring reason | EHR encounter table | `followup`: `last_contact_days`, `n_echos`, `censoring_reason` |

The access pathways are deployment assumptions and are labelled as such; the **variables** are
not assumptions, they are the frozen interface the code already validates against. Two of these
sources are wholly absent from the prototype extract — demographics and vital status — and their
cost is quantified rather than asserted: the `no_age` rung of the ladder measures the first, and
the absence of the second is why the real rung reports no competing risk at all.

---

## 2. Data Sources — Prototype / Hackathon

The organisers supplied a de-identified extract from an Epic/Caboodle-style warehouse: three
workbooks, one sheet each, dates shifted and truncated to the calendar year.

| Dataset | Size Used | Why Selected | Limitations as Proxy |
|---|---|---|---|
| Clinical notes | 215 notes, 117 patients | the only source of valve model, size, procedure type and echo haemodynamics | free text; exam dates redacted; 1–4 notes per patient |
| Laboratory results | 43,550 rows → 19,002 after de-duplication, 17 patients | renal function, haemoglobin, NT-proBNP, calcium/phosphate | 56% exact duplicates from export join fan-out; only ~half the rows are laboratory data, the remainder are blood gases, respiratory-therapy fields and device interrogation |
| Medications | 5,807 rows → 2,157 after de-duplication, 17 patients | antithrombotic and heart-failure exposure; procedure-year anchor | 63% exact duplicates; 64% of the de-duplicated rows are inpatient orders from the index admission (86% before de-duplication), so it is a medication administration record rather than a drug history |

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
| Follow-up extends beyond the implant year | Partly. Only **41 of 100** cohort-A patients have any note in a year later than their operative report; 57 have every note in a single calendar year. | High — heavy administrative censoring |

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
21 of the 117 have more than one gradient value but only 4 have gradients in more than one
year, so almost nobody has a trajectory; age is redacted throughout; and timing is known only
to the calendar year. The three things the landmark model
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
   symptoms once deterioration has begun, and informative dropout. The dropout hazard rises at
   latent onset, not merely with age: a dropout process driven only by measured covariates would
   be non-informative given those covariates, an analysis adjusting for them would be unbiased,
   and the protocol's concern about loss to follow-up would be a concern about nothing.
4. **Haemodynamics at each visit** — drifting gently before onset, accelerating after it, with
   proportional measurement error representing inter-observer and beat-to-beat variability.
5. **Observed events** — established by applying the VARC-3 criteria to each examination against
   that patient's own reference examination.

Each event carries both ends of its censoring interval: `interval_start_days`, the last
examination at which the event had not yet occurred, and `days_from_implant`, the examination that
detected it. On this cohort those intervals have a median width of 1.0 years and a maximum of 4.25
years, so a deterioration recorded at an examination may have begun four years earlier. Supplying
only the right endpoint, as most extracts do, silently converts an interval-censored outcome into
an exactly observed one.

Step 5 is what makes the cohort honest. An event is recorded at the examination that *detects*
it, never at the latent onset, so the outcome is interval-censored exactly as it is in a real
surveillance cohort. A generator emitting latent onset times would produce a dataset on which any
model looks better than it could ever be in clinic.

Every parameter, with its published source or an explicit ASSUMPTION marker, is in
`notebooks/synthetic/parameters.py`. Every row of every table carries `source = "simulated"` and
a `time_resolution` field, so a reader holding one CSV with no access to this repository can
still tell that nothing in it came from a patient.

### Calibration, and what is honestly claimed

*The tables in this section are reproduced, with the ladder, in
[`synthetic/results.md`](synthetic/results.md), generated on 16 September and committed so that
the evidence can be read without running anything.*


**Every published figure below was verified against its primary publication**, not taken from a
secondary summary. That check changed two things. It confirmed that NOTION estimated its rates
with the Aalen–Johansen method under a competing risk of death — the same estimator used here, so
the comparison is like for like rather than an assumption. And it returned the age hazard ratio to
the published 0.91 (95% CI 0.89–0.94): an earlier version used 0.95 on the reasoning that 0.91
extrapolated across a 50-to-95 age span implies an incredible seventy-fold hazard range, but 0.95
lies outside the published interval, and citing a meta-analysis while using a value it excludes is
not a position worth defending. A sensitivity analysis across 0.91–0.97, re-solving the
deterioration scales at each value, moves no anchor by more than 0.43 percentage points, so
nothing rests on it. The re-solving is the analysis: changing the hazard ratio while holding
the scales fixed de-calibrates the cohort rather than testing it, and moves the surgical anchor
by 7.1 points.

**What was fitted.** Nine parameters: three scales solved by bisection — two for deterioration
against the NOTION moderate-or-severe figures, one for competing mortality against NOTION's
all-cause death — and six shape parameters selected from small grids.

| quantity | subgroup | horizon | published | cohort, mean ± sd over 8 seeds | seeds inside band |
|---|---|---|---|---|---|
| **targeted** | | | | | |
| moderate or severe SVD | SAVR | 10 y | 20.8% | 20.1% ± 2.0 | 8 of 8 |
| moderate or severe SVD | TAVR | 10 y | 15.4% | 15.2% ± 1.3 | 8 of 8 |
| all-cause death | TAVR | 10 y | 62.7% | 62.6% ± 1.2 | 8 of 8 |
| **out of sample** | | | | | |
| severe SVD | SAVR | 10 y | 10.0% | 12.6% ± 2.0 | 4 of 8 |
| severe SVD | TAVR | 10 y | 1.5% | 9.2% ± 0.7 | **0 of 8** |
| bioprosthetic valve failure | all | 5 y | 3.6% | 3.6% ± 0.2 | 8 of 8 |
| bioprosthetic valve failure | all | 7 y | 7.2% | 6.6% ± 0.6 | 8 of 8 |
| severe SVD | TAVR | 7.8 y | 5.9% | 5.9% ± 0.6 | 8 of 8 |
| **post-hoc holdout** | | | | | |
| bioprosthetic valve failure | TAVR | 10 y | 9.7% | 9.2% ± 0.7 | 8 of 8 |
| bioprosthetic valve failure | SAVR | 10 y | 13.8% | 12.6% ± 2.0 | 7 of 8 |

Bands come from one rule, fixed before any cohort was generated and applied uniformly: **two
percentage points, or a quarter of the published value, whichever is larger**. A per-anchor
tolerance chosen by hand is not a standard, it is a description of the result. When the earlier
hand-picked bands were replaced by this rule the cohort fell from six anchors inside to three,
which is what exposed the deficiency the two-component onset model then fixed.

Results are means and standard deviations across eight seeds rather than one cohort. At 1,800
patients the Monte Carlo standard error of a 20% incidence is about one percentage point, which is
the size of the differences being judged.

> The table above is transcribed for readability from
> [`synthetic/results.md`](synthetic/results.md), generated on 16 September — if the two ever
> disagree, that file is right and this one is stale. The grouping into
> *targeted*, *out of sample* and *post-hoc holdout* is an argument made here and is not
> carried by the generated table, which separates targeted anchors from the rest only.

**The two post-hoc rows are the closest this calibration comes to a holdout.** NOTION's
bioprosthetic-valve-failure figures were found while verifying the other anchors, after every
parameter had been fixed. They were not used to choose anything, and the cohort reproduces both:
9.2% against 9.7% in the transcatheter arm and 12.6% against 13.8% in the surgical arm.

Nine fitted parameters against ten anchors is still close to saturated, so agreement is **not**
proof that the cohort is correct — it establishes that the cohort is plausible, landing where
published series land so that a pipeline exercised on it runs at realistic event rates. The
evidence of correctness is the recovery test below, which no amount of curve-fitting can pass.

### The two anchors the cohort misses, and why they are not tuned away

**Severe deterioration after transcatheter implant.** NOTION reports 1.5%; the cohort gives 9.2%.
That figure is 1.5% of 145 randomised patients — **about two events** — and it contradicts the UK
TAVI registry, which reports severe deterioration in 13 of 221 patients (5.9%) at a *shorter*
median follow-up of 7.8 years. NOTION's own arms are mutually inconsistent too: its figures imply
that 48% of deteriorated surgical valves become severe within ten years but only 10% of
transcatheter ones, a five-fold difference in progression conditional on deterioration between two
arms of one trial. This cohort sides with the registry, reproducing it exactly at 5.9%. Fitting a separate progression process per arm would reproduce both numbers by fitting the
sampling noise of a few dozen patients.

**Severe deterioration after surgical implant.** NOTION reports 10.0%; the cohort gives 12.6% —
which sits at NOTION's *bioprosthetic valve failure* figure of 13.8%, an anchor the cohort does
hit, rather than at its severe-deterioration figure. The pattern is informative rather than random: this cohort's stage-3 threshold
behaves like NOTION's adjudicated valve failure rather than its adjudicated severe deterioration,
so the two categories that a trial adjudication panel separates are not separated here. That is a
limitation of applying published echocardiographic thresholds mechanically, without the clinical
adjudication a trial applies, and it is exactly the gap the ground-truth hierarchy in the protocol
exists to close.

### Two processes, not one

Onset is a mixture. About 9% of valves follow a **rapidly progressive phenotype** — early onset
and roughly four and a half times the usual rate of gradient rise — covering early structural
problems, severe mismatch that was never going to be tolerated, and accelerated calcification.
The remainder follow the slow calcific process that dominates late, with a Weibull shape of 2.0
so that its hazard clearly accelerates with time in the valve.

This is not a device for hitting a number. A single Weibull forced an impossible compromise: to
produce any failures by five years its shape had to be dragged down towards 1, flattening the
very acceleration that characterises late deterioration, and even then the five- and seven-year
failure anchors were missed by a factor of three. Splitting the process lets each component keep
its own shape and reproduces both ends of the time course, which is also the clinically truthful
description — bioprosthetic failure is genuinely not one mechanism.

### Internal validation

Calibration shows the cohort resembles the literature; it does not show the code is correct, and
with nine fitted parameters it cannot. That is established by a **recovery test**: hazard ratios
are injected into the generator, a Cox model is fitted to the output, and the estimates are
compared with what went in. The Cox model is implemented directly against the Breslow partial
likelihood rather than taken from the library the modelling workstream uses, so that a shared
misunderstanding cannot pass unnoticed in both places.

The model is **stratified** by phenotype and approach. The two phenotypes are generated with
different Weibull shapes, so they are not proportional to one another and no coefficient could
express the difference between them; forcing one biases every other estimate, which is exactly
what happened when the mixture was first introduced and recovery collapsed from eight covariates
in eight to one in eight. Stratifying restored it.

- **Latent hazard.** Over three seeds and seven covariates, the 95% interval covered the injected
  value in **20 of 21 fits (95.2%)**, against a nominal 95%, with a mean log bias of **+0.0005** —
  no detectable systematic error. Coverage is the right criterion rather than a clean sweep: a
  95% interval is supposed to miss about one time in twenty, and treating any miss as failure
  would invite tuning until it passes.
- **Observed events.** The same effects estimated from what an analyst actually sees — detections
  at scheduled examinations, with death competing and patients dropping out — are **attenuated**:
  the median attenuation of the log hazard ratio is **0.66** over the same 21 fits, ranging from
  0.15 to 0.91 across individual covariates and seeds. This is not a defect. It
  quantifies how much sparse guideline-interval surveillance biases effect estimates toward the
  null, and it applies to any real study built the same way, which is why it is restated in the
  limitations.

### Automated tests

`notebooks/synthetic/tests/` holds 54 tests covering the schema contract, reproducibility,
governance, the VARC-3 criteria, the structure of the generated cohort, the two follow-up clocks,
what each rung of the ladder removes, the convergence of the parameter solvers, and the claims
made in this document. They run in a minute or two:

```bash
uv run python -m pytest notebooks/synthetic/tests -q
```

They are not decoration. Writing them found two defects that had survived review: mismatch grade
was computed on an unrounded indexed area while the rounded value was published, so a borderline
patient's grade contradicted the number printed beside it; and a reintervention could be recorded
after a patient had been lost to follow-up, giving the cohort ascertainment nobody had.

### The degradation ladder, and why its last rung is not simulated

The same cohort is emitted five times, each rung removing one property of the data
while leaving the patients, their biology and their events untouched. The truth is
identical on every rung; only what an analyst can see of it changes. One unchanged
modelling pipeline run across the rungs therefore measures exactly one thing: what each
defect costs.

**A sixth rung is the supplied extract itself**, prepared by `notebooks/02_preprocessing.ipynb`
and brought into the same pipeline by `notebooks/pipeline/landmarks.py`. That is what makes the ladder an argument rather than an
assertion: a panel reading "our last rung simulates how poor the data are" is being asked
to take the simulation on trust; a panel reading "our last rung *is* the data" is not.

| rung | defect added | simulated? |
|---|---|---|
| `ideal` | none — the data the protocol asks a site to supply | yes |
| `no_age` | age at implant removed | yes |
| `year_resolution` | all timing collapsed to the calendar year | yes |
| `single_echo` | one examination per patient, no reference study | yes |
| `as_supplied` | one encounter with its quoted priors, examinations for only the 52% abstraction reaches, no device identity, **no mortality** | yes |
| `as_received` | nothing added — this *is* the supplied extract | **no** |

The synthetic rungs are cumulative. Every one of them can be reproduced by a reviewer with
no access to the private extract, because `synthetic` never imports `cohort`; only the last
rung needs the data.

### What the comparison found

Building the real rung immediately exposed four ways in which our model of the data's
poverty had been wrong. Three were corrected; the fourth is a finding and was left alone.

| property | simulated rung, before | corrected | the extract |
|---|---|---|---|
| patients with any examination | 27% | 52% | 52% |
| examinations per patient | 1.00 | 1.59 | 1.69 |
| patients with more than one gradient | 0% | 22% | 18% |
| **mortality observed** | **yes** | **no** | **no** |
| events per 100 patients | 20.5 | 20.5 | **12.0** |

The *before* column is a record of what the earlier model of the extract produced, kept because
the four corrections are the point of the section. It was measured before the cohort was last
recalibrated, so it is not directly comparable with the column beside it: the two event rates
coinciding at 20.5 is arithmetic coincidence, not a finding. The *corrected* and *the extract*
columns come from the same generated record ([`synthetic/results.md`](synthetic/results.md)) and are comparable.

The mortality correction matters most. The extract contains **no death data of any kind** —
no table, no date, no linkage — so the competing risk is entirely unobserved. That is the
single most consequential absence in it and the easiest to overlook, because nothing in the
data announces it: a patient whose notes simply stop looks identical to a patient who is
well. A cumulative incidence computed where death is invisible is not comparable with one
computed where it is known, and our simulation had been quietly retaining deaths the real
data could never supply.

The examination-count correction matters for a subtler reason. Modelling the extract as
*one examination per patient* was too harsh: a clinical note routinely quotes prior studies
alongside the current one, so patients do have several gradients. What the extract destroys
is not the number of measurements but their **order and their dates** — the quoted priors
carry no date of their own. A patient can have three gradients and no trajectory.

**The event-rate gap is not corrected, because it is a result.** The extract documents 12
events per 100 patients where a comparable cohort under proper follow-up shows about 25.
Roughly half the events are invisible: they are echocardiographic deteriorations that were
never adjudicated, in patients who were never imaged again. This is the cost of incomplete
ascertainment, measured rather than asserted, and it is the clearest single argument in this
document for why the abstraction pipeline the protocol proposes is worth building.

### Real and synthetic are kept apart

The two cohorts share a schema; they are never concatenated into one table. Merging them
would be indefensible on three counts. It would add nothing — 32 assessable labels against
1,800 synthetic patients is 0.3% of a training set. It would destroy the one claim this
submission rests on, because no number in it could then be attributed cleanly: the answer to
"which of these came from patients?" would be "they are mixed", which is the worst available
answer. And the real rows carry verbatim note text, which must not travel with anything
else.

Kept apart, each does the job it can do. The synthetic cohort is where the pipeline is
exercised, because it is the only cohort that has serial dated examinations, known event
times and age. The real cohort is where the pipeline's *inputs* are measured, and it anchors
the bottom of the ladder in something nobody has to take on trust.

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

- **The extract is never committed.** The source workbooks and every table derived from them sit
  in `data/` and are blocked by `.gitignore` (spreadsheet, CSV, parquet, pickle and JSON files,
  `data/raw_tables/`, `data/llm_json/` and `data/processed/`). Notebooks print aggregate counts
  only.
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
