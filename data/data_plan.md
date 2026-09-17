# Data Plan

This document covers what a real deployment would use, what we had for this prototype, and how we
bridged the gap. Every figure about the supplied extract is measured by code in this repository, and
none of them is a patient-level value.

---

## 1. Data Sources — Real Deployment

A site that wants to run the model has to supply four tables:
- one row per implant
- one row per echocardiogram
- one row per event
- one row per patient's follow-up

They are defined column by column in
[`notebooks/synthetic/schema.py`](../notebooks/synthetic/schema.py). The sources below are where
those rows come from in a hospital.

| Source | Data Type | Access Pathway | Variables Used |
|---|---|---|---|
| Operative and procedure reports | free text | EHR note export, abstracted on site by rules plus language-model agents that record the sentence behind each field | implant date, SAVR or TAVR, valve model and label size, valve-in-valve, native valve morphology |
| Echocardiography reports | structured measurements where the echo system stores them, otherwise free text | echo reporting system (DICOM SR) or note abstraction | mean and peak gradient, DVI, effective orifice area, intraprosthetic and paravalvular regurgitation, LVEF, exam date |
| Clinical notes and problem list | free text and coded diagnoses | EHR | diabetes, chronic kidney disease or dialysis, smoking, atrial fibrillation, body size |
| Medications | structured orders | EHR medication table | anticoagulation, which protects against the thrombotic failure mode |
| Laboratory results | structured | EHR lab table | creatinine and eGFR, calcium, phosphate |
| Reinterventions | procedure codes and operative notes | EHR procedures, cardiac surgery and cath lab registries | valve-in-valve TAVR, redo SAVR, balloon valvuloplasty, and the reason for each |
| Vital status | date of death | hospital registry or national death index | death date. Without it the competing risk of death cannot be modelled |
| Demographics | structured | EHR | age at implant, sex |

The two inputs that matter most are **dated serial echocardiograms** and **age at implant**. The
prototype extract has almost neither (section 3).

---

## 2. Data Sources — Prototype / Hackathon

| Dataset | Size Used | Why Selected | Limitations as Proxy |
|---|---|---|---|
| Notes extract (`notes_deidentified.xlsx`) | 215 notes from 117 patients: operative reports, progress notes, procedure notes, discharge summaries | the only source that names the valve and quotes echo values, and the kind of data a real system would read | dates cut to the year; age redacted in 194 of 215 notes; one or two notes per patient |
| Labs extract (`labs_deidentified.xlsx`) | 43,550 rows (19,002 after removing exact duplicates), 17 patients | renal and calcium markers are published risk factors | covers only 17 patients, and they have no operative report; mostly admission bloodwork |
| Medications extract (`medications_deidentified.xlsx`) | 5,807 rows (2,157 unique), 17 patients | anticoagulation exposure | same 17 patients; mostly inpatient orders |
| Agent-based extraction from each note (`data/llm_json/`) | one structured record per note, with the sentence each field came from | turns free text into fields, the extraction step a deployment needs | not yet reviewed note by note by a clinician |
| Synthetic cohort (`notebooks/synthetic/`) | 6,000 patients per draw, five draws for the main results (the reshaped check draws its 6,000 from a pool of 18,000) | the extract cannot train or test a model (10 events, no deaths, no ages); the generator supplies patients whose outcome is known | built from published effect sizes, so it confirms the method rather than the clinical effects |

After preprocessing, the extract gives:
- **129 valve episodes in 116 patients** (77 SAVR, 52 TAVR)
- **204 echocardiograms**
- 117 valves with a known implant year
- **51 valve episodes followed long enough to be scored**, giving 301 prediction rows

---

## 3. Availability Assumptions

| Assumption | In the prototype extract | Risk if it fails |
|---|---|---|
| Serial dated echocardiograms per patient | **Fails.** 1.62 examinations per patient on average; only 16.2% have more than one gradient; 4 valves have a usable change from their reference study | High: gradient change and trajectory features stay mostly empty |
| Exact dates | **Fails.** Years only | High: time is known to the nearest year |
| Age at implant | **Fails.** Redacted everywhere | High: the strongest published predictor is unavailable |
| Deaths recorded | **Fails.** No death data of any kind | High: the competing risk cannot be observed |
| A reference echo 30 to 90 days after implant, as VARC-3 requires | Partly. 33 valves have a reference study with a gradient, taken within a year of implant | Medium |
| Valve model and size coded | Holds. Model known for 95% of valves and size for 96% | Low |
| Risk factors recorded when absent | **Fails.** They are written mostly when present: diabetes is "yes" for 29 of the 35 patients whose notes state it | Medium: a blank is not a "no" |

A site that meets the first four assumptions is the kind of site the protocol targets. The
degradation ladder (section 5) measures what each failed assumption costs.

---

## 4. Preprocessing and Data Quality

The pipeline has two stages:
1. `scripts/01` and `scripts/03` extract the raw tables.
2. [`notebooks/02_preprocessing.ipynb`](../notebooks/02_preprocessing.ipynb) cleans and combines
   them, using the rules in [`notebooks/pipeline/prep.py`](../notebooks/pipeline/prep.py).

### Data Cleaning
- **Duplicates.** 56% of lab rows and 63% of medication rows are exact copies of another row. They
  are collapsed, and the number of copies is kept.
- **Lab names and units.** The same test appears under several names and unit spellings. Fourteen
  analytes, including creatinine, eGFR, calcium, phosphorus, haemoglobin and HbA1c, are each mapped
  to one name and one unit. Results written as limits (">60") are kept as limits.
- **Impossible dates.** The date shift pushed some rows into 2027, so years after 2026 are dropped.
- **Free-text notes.** Every note is read twice.
  - **Rules:** regular expressions pick out valve names, sizes, echo values and event keywords.
  - **Language-model agents:** an orchestrator agent split the notes among sub-agents. Each sub-agent
    read its notes one at a time and filled the same fixed set of fields (operation, valve, echo
    values with their timing, signs of failure), quoting the sentence behind each value. The result
    is one structured record per note, in `data/llm_json/`.

  The two readings are then reconciled field by field. A value is kept only when it refers to the
  prosthetic aortic valve rather than a native or different valve, and paravalvular regurgitation is
  kept separate from intraprosthetic regurgitation.

### Missing Data Strategy
Share of the 204 echocardiograms that record each measurement:

| mean gradient | intraprosthetic regurgitation | LVEF | DVI | orifice area |
|---|---|---|---|---|
| 50% | 62% | 44% | 35% | 4% |

Nothing is imputed at this stage.
- **Missing reference study.** Recorded as a feature of its own (`ref_missing`).
- **Unmentioned risk factors.** Recorded as "not stated", never as "no".
- **Patients with no echocardiogram.** Kept, not dropped: dropping them would favour closely watched
  patients.
- **Blanks at modelling time.** How each model handles them is described in
  [`model/approach.md`](../model/approach.md) §3.

### Temporal Alignment
- **Time origin.** The implant year is year 0, and every echo is placed by its year relative to it.
- **Reference study.** The first post-operative echo within one year of implant. If there are
  several, the one with a mean gradient is preferred.
- **Values from one note.** Several gradients quoted in the same note, with the dates redacted, have
  no recoverable order, so they are never turned into a change or a slope.
- **What each prediction may use.** At each landmark (6 months, 1 year, then yearly) only studies
  dated at or before the landmark are used. A test corrupts every later study, rebuilds the features
  and checks that nothing changes (`notebooks/pipeline/tests/test_pipeline.py`).

### Label / Ground Truth Construction
- **Echo rule.** Each echo is compared with the valve's own reference study using the VARC-3
  criteria.
  - **Stage 2:** a mean gradient rise of at least 10 mmHg to at least 20 mmHg, or regurgitation that
    is at least moderate and worse than before.
  - **Stage 3:** a rise of at least 20 mmHg to at least 30 mmHg, or severe regurgitation.
- **Reintervention.** A valve-in-valve TAVR, a redo SAVR or a balloon valvuloplasty of the
  prosthesis counts when the reason is structural failure.
- **Exclusions.** Candidate events whose stated reason is endocarditis, thrombosis or a paravalvular
  leak are marked non-structural and not counted.
- **Prevalence.** Of 18 candidate events, 8 are non-structural. The remaining **10 affected valve
  episodes** are 9 reinterventions and 1 stage-2 deterioration seen on echo: 8.55 affected patients
  per 100.
- **Label quality.** The rule-based and agent readings are compared field by field, and
  doubtful cases are listed for clinician review. That review is not yet complete, so no event is
  marked as adjudicated.
- **Relaxed rule on the extract.** VARC-3 also requires a fall in orifice area or DVI for stage 2.
  The extract rarely records those values, so the corroboration is not enforced there. This is a
  stated limitation.
- **Count reconciliation.** The different event counts quoted in this repository are placed side by
  side in [`endpoint_criteria.md`](endpoint_criteria.md).

---

## 5. Synthetic or Proxy Data (if applicable)

### Why a generator
With 10 events, no deaths and no ages, the extract can neither train nor test a durability model.
We therefore wrote a generator of synthetic patients whose truth is known
([`notebooks/synthetic/`](../notebooks/synthetic/)). It is not a learned generator such as CTGAN,
which would only copy the extract's gaps. It simulates the course of the disease step by step:

1. **Patient and implant.** Age, sex, body size, SAVR or TAVR, valve model and size. From these, the
   orifice area and patient–prosthesis mismatch.
2. **Hidden timing.** A time to structural failure for each of three competing modes (calcific
   stenosis, leaflet tear, pannus or thrombosis), each with its own risk factors, plus a time to
   death.
3. **Surveillance.** Guideline echo visits, extra studies once symptoms begin, and dropout that
   becomes more likely once the valve starts to fail.
4. **Echo readings.** Stable before failure begins, then changing the way that failure mode changes
   them, with measurement noise.
5. **Recorded events.** VARC-3 is applied at each study against the patient's own reference, so an
   event is recorded when a study detects it, not when it began.

### Evidence that it is realistic
- **Calibration.** The cumulative incidence (Aalen–Johansen, with death as a competing risk) falls
  inside a fixed tolerance for 8 of 10 published anchors. For example, at 10 years against NOTION:
  - moderate or severe SVD after SAVR: 21.1%, published 20.8%
  - moderate or severe SVD after TAVR: 14.7%, published 15.4%
  - all-cause death: 62.8%, published 62.7%

  The two misses are reported, not tuned away.
- **Correctness.** Known hazard ratios were injected into the generator and recovered by an
  independent Cox fit: 70 of 75 intervals covered the true value (93.3%).
- **Tests.** 54 automated tests cover the generator.
- **Sources.** Every parameter and its source is listed in `parameters.py`, and the tables are
  regenerated in [`synthetic/results.md`](synthetic/results.md).

### The degradation ladder
The same patients are produced five times, with information progressively removed:
- `ideal`
- `no_age`
- `year_resolution`
- `single_echo`
- `as_supplied`

The real extract is the sixth rung.
- **Cost of poor surveillance.** Between `ideal` and `as_supplied`, extract-quality surveillance loses
  34% of the patients who deteriorate and 42% of the endpoint rows.
- **Check against the real rung.** Measured with the same code, the real extract is examined more
  often than our simulation of it: 83.8% of patients have an examination, against 52.1% in
  `as_supplied`. That rung is therefore still too pessimistic about surveillance.

### Which synthetic data the models learn from
- **Main setup: the full-quality cohort** (`ideal`). The models are trained, validated and tested on
  it, as the organisers recommended.
- **Secondary check: a reshaped cohort.** To test how a model built for the extract's gaps behaves,
  the cohort can also be reshaped to resemble the extract (`notebooks/pipeline/matching.py`,
  `AVR_LIKE_REAL=1`).

**Why reshaping was added.** An early model trained on the full-quality cohort, with the
surveillance features included, ranked the real valves worse than chance. Once those features were
removed, full-quality models transferred as well as reshaped ones: 5-year AUC 0.72 against 0.71 for
the regression baseline ([`model/approach.md`](../model/approach.md) §4).

The reshaping changes the cohort as follows:
- year-only dates
- no age and no recorded deaths
- the extract's case mix
- risk factors missing the way the notes miss them
- the extract's gradient levels, echo counts and echo timing
- reinterventions as the only events

After reshaping, a classifier trying to tell real rows from synthetic rows reaches an AUC of 0.80 on
the clinical features, down from 0.85 before (0.5 would mean the two cannot be told apart).

### Limitations
- **No new effects.** The generator returns the effects it was built with, so a model trained on it
  cannot discover new clinical effects.
- **Failure-mode shares.** The split between the three failure modes is an assumption.
- **No deaths in reshaped data.** The reshaped training data contain no deaths, so those runs never
  exercise the competing-risk part of the models.

### Replacement in a real study
In a real study the generator is replaced by the site's four tables, and the code path stays the
same: synthetic and real data already go through the same conversion
(`landmarks.from_preprocessing`), and every row carries `source` and `time_resolution` columns.

---

## 6. Data Governance and Privacy

- **Prototype data.** The organisers supplied the three extracts, de-identified, for use at this event
  only. They stay on team machines under `data/`.
  - `.gitignore` blocks every spreadsheet, CSV, parquet and pickle file there.
  - A scan of the full repository history confirmed that none was ever committed.
- **What is published.** Only aggregates: counts, rates, metrics and group-level figures. No note
  text, identifier or patient row appears in any document, figure or notebook output.
- **Re-identification risk.** The supplied de-identification is incomplete: the labs keep some full
  dates and device serial numbers, and some notes keep a month and year. None of those fields is
  extracted or displayed.
- **Language model.** The note-by-note reading ran on the supplied de-identified text. In a
  deployment it would run inside the hospital network, so notes never leave the site.
- **Production.**
  - Each site runs the study under a data use agreement and ethics approval.
  - Training and inference stay on site; only aggregate monitoring statistics are shared, and access
    is logged.
  - Synthetic rows carry `source = simulated`, so they cannot be mistaken for patient data.
