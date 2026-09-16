# Notes file

`data/notes_deidentified.xlsx`, 215 notes, 11 columns, 117 patients.

## Columns

| Column | Non-null | Distinct | Comment |
|---|---|---|---|
| Profile Key | 100% | 117 | patient id, different column name from the other files |
| Note Type | 100% | 1 | always `Generic`, carries no information |
| Type | 100% | 4 | the real note type |
| Service | 61% | 6 | |
| Signed Status | 100% | 4 | `Signed` 177, `Addendum` 21, `Deleted` 13, `Unsigned` 4 |
| Authoring Provider Type | 97% | 6 | |
| Authoring Provider Specialty | 24% | 10 | |
| Notes | 100% | 215 | free text, 1.2k to 25k characters |
| Service Date / Creation Date / Last Edited Date | 100% | 19 | year only; identical for 98% of notes |

## Note types

| Type | Count | Patients | Median length (chars) |
|---|---|---|---|
| Operative Report | 112 | 100 | 3,200 |
| Progress Notes | 83 | 83 | 9,200 |
| Procedures | 15 | 15 | 3,400 |
| Discharge Summary | 5 | 5 | 11,100 |

Patients have 1 to 4 notes (36 with one, 65 with two, 15 with three, 1 with four). No note text is duplicated, even after stripping redaction tokens.

Thirteen notes are marked `Deleted` (9 operative reports, 4 progress notes) and four `Unsigned`. No patient depends solely on a deleted note, but deleted operative reports should be excluded or at least flagged, since a deleted report may have been replaced by an addendum.

## Operative reports

Service years run 2006 to 2022. Keyword classification of the 112 reports:

| Category | Reports | Patients |
|---|---|---|
| Transcatheter AVR terms (TAVR, TAVI, Sapien, Evolut, CoreValve) | 45 | 41 |
| Surgical AVR wording without transcatheter terms | 49 | 43 |
| Neither keyword set (mostly minimally invasive AVR, CABG-only or re-exploration on manual reading of the procedure line) | 18 | |
| Concomitant CABG | 21 | 17 |
| Concomitant mitral procedure | 7 | 5 |
| Transcatheter valve-in-valve into a failed surgical bioprosthesis | 7 | 6 |
| Explicit redo sternotomy or reoperation | fewer than 10 | |

A `REOPERATION:` template field exists in only 2 reports. Beware that "reoperat" also matches "preoperative", which inflates naive keyword counts to almost every report.

Valve models named in operative reports (reports / patients): Sapien 30 / 29, Trifecta 29 / 25, Epic 22 / 20, other St. Jude 9 / 8, Evolut or CoreValve 8 / 7, Perimount 5 / 5, Magna 3 / 3, Inspiris 2 / 2. No Medtronic surgical valves, no Perceval, no Mitroflow, no homografts, no mechanical valves and no Ross procedures were found. A valve size in millimetres appears in 71 reports, and size and model sit on the same line in 47, so implant type, model and size are extractable for roughly half the surgical cohort by regex and for most of it with an LLM pass.

Every report has a parsable procedure heading, but the heading label varies (`OPERATION`, `OPERATIONS`, `OPERATIVE PROCEDURE`, `SURGERY/PROCEDURE`, `DESCRIPTION OF PROCEDURE`). Cross-clamp and bypass times are recorded in only 2 reports. Implant lot or serial numbers appear in 4.

## Echo values inside note text

Progress notes and discharge summaries embed echo report conclusions. 42 notes contain a `CONCLUSIONS` block (56 blocks in total). The prosthetic-valve sentence is highly regular:

> The peak gradient is N mmHg, the mean gradient is N mmHg and the dimensionless valve index is 0.NN.

and valve area follows the form "AV area is N.NN cm² (N.NN cm²/m²) by continuity". Regex extraction on the 103 non-operative notes yields:

| Parameter | Matches | Notes | Patients |
|---|---|---|---|
| Mean gradient (mmHg) | 135 | 51 | 51 |
| Peak gradient | 127 | 50 | 50 |
| Dimensionless valve index | 114 | 47 | 47 |
| LVEF (%) | 246 | 76 | 75 |
| Aortic valve area (cm²) | 27 | 18 | 18 |
| Paravalvular leak mention | 21 | 13 | 12 |
| Regurgitation grade | 8 | 7 | 7 |
| Peak velocity (m/s) | 4 | 3 | 3 |

Mean gradients found range from 1 to 57 mmHg with a median of 11. Some gradients are native-valve pre-operative values, some are prosthetic follow-up values; the surrounding sentence (native stenosis wording versus "prosthetic aortic valve") is needed to tell them apart.

Two constraints limit their use: the echo date inside the note is redacted to `[DATE]`, so timing relative to implant is known only to the note's service year; and most patients have a single echo-bearing note, so serial trajectories exist for only a handful.

## Event signals

- 17 notes across 16 patients contain failed-bioprosthesis, degenerated-prosthesis, structural-valve-deterioration or valve-in-valve language (10 progress notes, 7 operative reports).
- 6 patients have an operative report for transcatheter valve-in-valve into a previous surgical bioprosthesis. These are confirmed SVD-driven re-interventions, but the original implant is not in the dataset.
- Endocarditis is mentioned for 9 patients, valve thrombosis or leaflet thickening for 1, patient-prosthesis mismatch for 17.

## Redaction and leakage

Token counts across all notes: `[DATE]` 2,378, `[NAME]` 2,293, `[LOCATION]` 999, `[AGE]` 382, `[FACILITY]` 310, `[ID]` 258, `[PHONE]` 200, `[ADDRESS]` 187, `[ZIP]` 183, `[TIME]` 118, `[URL]` 54, `[UNIT]` 36.

- Age is redacted in 194 of 215 notes, so age at implant is not recoverable. Sex words appear in 144 notes. BMI or BSA appear in 56 notes.
- 42 notes retain month/year partial dates (in `MM/YYYY` form) that escaped redaction. 81 notes contain bare four-digit years, mostly legitimate references such as "in 2015" but also one implausible `2083`.
- 7 notes mention a calendar year later than the note's own service year, so the shift applied to structured dates does not always match years left in text.
- 13 operative reports have their surgery date field redacted entirely; the rest rely on the year in `Service Date`.
- 12 notes contain six-digit or longer numeric strings that look like URL or identifier fragments.
- Progress notes contain template filler (`No date`, `Comment`, smoking-history blocks) that should be stripped before any text modelling.
