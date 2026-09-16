# Data overview

Three Excel workbooks, each with one sheet named `Query result`, exported from an Epic Caboodle style warehouse and de-identified. Dates are shifted and truncated to the calendar year.

| File | Rows | Columns | Patients | Patient id column |
|---|---|---|---|---|
| `labs_deidentified.xlsx` | 43,550 | 16 | 17 | `Patient` |
| `medications_deidentified.xlsx` | 5,807 | 23 | 17 | `Patient` |
| `notes_deidentified.xlsx` | 215 | 11 | 117 | `Profile Key` |

Pseudonyms are `Patient_001` to `Patient_117`. Labs and medications cover exactly the same 17 patients (101 to 117). Notes cover all 117.

## Two sub-cohorts

| Group | Patients | Notes | Labs / meds |
|---|---|---|---|
| A: `Patient_001` to `Patient_100` | 100 | 112 operative reports, 15 procedure notes, 71 progress notes | none |
| B: `Patient_101` to `Patient_117` | 17 | exactly one note each: 12 progress notes, 5 discharge summaries; no operative reports | all rows |

Group A is the surgical cohort: every patient has at least one operative report (89 have one, 10 have two, 1 has three). Group B is the "deep" cohort with structured longitudinal data, but their index operation is not documented as an operative report. In 14 of the 17 group B notes the patient is described as status post aortic valve replacement; one note is a pre-operative assessment for severe aortic stenosis.

## Time coverage

| Source | Year range | Notes |
|---|---|---|
| Labs | 2004 to 2027 | 71% of rows fall in 2009 to 2013; 28 rows in 2027 (one patient, shift artefact) |
| Medications | 2001 to 2027 | peaks in 2010, 2011, 2013, 2015, 2023; 1 row in 2027 |
| Notes | 2006 to 2026 | operative reports 2006 to 2022; TAVR reports 2014 to 2022 |

Per-patient depth in group B is uneven. For labs, 6 of 17 patients have data from a single calendar year, 5 from two years and 6 from six or more years. For medications, 7 patients are single-year, 3 two-year, 1 three-year and 6 span seven or more years. The single-year patients are index-admission dumps: their labs, medications and their one discharge summary or progress note all sit in the same year, and anaesthetic or protamine orders in that year mark the operation.

For group A, 74 of the 100 patients have all their notes in a single year. Follow-up beyond the surgery year exists for 41 patients, with a spread of 1 to 15 years but only one or two later notes each.

## What does not exist

- No demographics table. Age is redacted as `[AGE]` in the notes (382 occurrences). Sex is only inferable from pronouns.
- No encounter, diagnosis, procedure or echo table. Diagnoses appear only as ICD-10 JSON on 24 unique medication rows.
- No implant registry. Valve model and size are only in operative-report free text.
- No exact dates. Time-to-event resolution is one year at best, and shifted.
