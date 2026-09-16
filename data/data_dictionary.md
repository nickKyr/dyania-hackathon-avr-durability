# Data Dictionary — Note Abstraction

Every variable the prototype produces from the hackathon extract, with **where it comes from**.
`source_type` is the important column: it states whether a field is read from a structured
field, abstracted from note text, or derived from other fields. Note-derived fields are the
ones that require validation against clinician review.

This file describes **schema only**. No patient-level values, note text or counts per patient
are stored in this repository.

## Field provenance

| sheet | field | source_type | definition | method |
|---|---|---|---|---|
| patients | cohort_group | derived | A = Patient_001-100 (operative reports), B = Patient_101-117 (labs and meds) | structured |
| patients | implant_approach | note-derived | TAVR if transcatheter terms or TAVR device names; SAVR if aortic valve replacement wording with open-surgery terms; from the first signed operative report, else from a history mention | regex, rule |
| patients | valve_model / manufacturer | note-derived | first model name matching the approach in the index operative report; valve_name_redacted flags reports where the de-identifier replaced the device name with [NAME] | regex lexicon |
| patients | valve_size_mm | note-derived | size in mm nearest the model mention (#21, 21 mm, size 26, Implant Size: 25) | regex |
| patients | implant_year | hybrid | operative report service year; for group B the earliest year with anaesthetic or protamine orders in the medications file | structured + rule |
| patients | follow_up_years | derived | last note year minus implant year; year resolution only | arithmetic |
| patients | prosthetic_mean_gradient_* | note-derived | mean gradient values whose surrounding sentence refers to a prosthesis, S/P AVR or TAVR, restricted to notes in or after the implant year | regex + context rule |
| patients | prosthetic_dvi_latest | note-derived | dimensionless valve index in prosthetic context | regex + context rule |
| patients | prosthetic_ar_grade_latest | note-derived | regurgitation grade word (no, trace, mild, moderate, severe) in prosthetic context | regex + context rule |
| patients | native_mean_gradient_preop_max | note-derived | highest mean gradient in native-valve context (pre-operative stenosis severity) | regex + context rule |
| patients | event_* | note-derived | keyword events with a simple negation check (valve in valve: No, no evidence of); years listed | regex + negation rule |
| patients | svd_label | derived proposal | accept = reintervention for failed bioprosthesis; borderline = haemodynamic thresholds or failure language; reject = prosthetic echo without criteria; missing = no prosthetic echo. Thresholds from VARC-3 / 2024 ASE, without the baseline comparison VARC-3 requires. To be adjudicated by clinicians | rule |
| patients | *_last_year_mean | structured | mean of the analyte in the last year it was measured (labs file, de-duplicated) | aggregation |
| patients | sex_hint | note-derived, weak | pronoun majority across notes; no structured sex field exists | regex |
| patients | age_available | structured | always False: age is redacted as [AGE] in every note and no demographics table exists | constant |
| implants | one row per operative report or history mention | note-derived | approach, model, size, valve-in-valve, TAVR access, concomitant procedures, redo, native morphology, procedure line, confidence | regex |
| echo_values | one row per extracted value | note-derived | parameter, value, unit, valve_context (prosthetic / native / ambiguous / unknown), snippet for verification | regex |
| events | one row per keyword hit | note-derived | event_type, negated flag, snippet | regex |
| labs_by_year / labs_summary | canonical analytes | structured | component-name variants merged; censored values (>60, <0.01) parsed to the limit and flagged; units listed, not converted | aggregation |
| meds_by_year / meds_summary | medication classes | structured | class flags by patient-year and mode; surgery_marker = anaesthetics, protamine, antifibrinolytics | aggregation |
| diagnoses | ICD-10 from medications | structured | the only coded diagnoses in the extract (24 rows) | JSON parse |

## Source-type summary

| source_type | fields |
|---|---|
| note-derived | 11 |
| structured | 5 |
| derived | 2 |
| hybrid | 1 |
| derived proposal | 1 |
| note-derived, weak | 1 |

## Extraction tables

| Table | Grain | Evidence kept |
|---|---|---|
| `implants` | one row per operative report or per implant mention in a later note | procedure line, model snippet |
| `echo_values` | one row per extracted measurement | surrounding text snippet, valve context |
| `events` | one row per keyword hit | snippet, negation flag |
| `notes` | one row per note | note metadata only |
| `labs_*`, `meds_*`, `diagnoses` | patient-year aggregates | structured source |

Tables carrying text snippets are held **outside this repository** together with the source
data; only schema and aggregate counts are committed here.
