# Data quality issues

Ranked by impact on the AVR durability study. Severity: **blocker** means the study design must work around it; **major** means it needs a preprocessing step; **minor** means a cleanup rule.

| # | Severity | Issue | Where | Evidence |
|---|---|---|---|---|
| 1 | blocker | Structured data and operative reports cover disjoint patients. No patient has labs, medications and an operative report. | all | 17 lab/med patients have one note each and no operative report; 100 operative-report patients have no labs or meds |
| 2 | blocker | No structured echo table. Gradients, EOA, DVI and regurgitation exist only in note text. | notes, labs | only `LV Ejection Fraction` (77 unique rows) is structured |
| 3 | blocker | Follow-up too short and too sparse for time-to-event modelling. | notes | 59 of 100 surgical patients have all notes in the operation year; median later notes per patient is one |
| 4 | blocker | Year-only, shifted dates, with artefacts. Implant-to-echo intervals resolve to whole years at best. | all | rows dated 2027 in labs and meds; 7 notes cite years after their own service year; `[DATE]` inside notes |
| 5 | blocker | No demographics. Age redacted everywhere, no sex column, no height or weight table. | all | `[AGE]` in 194 notes; BSA only in 56 notes |
| 6 | major | Exact duplicate rows. | labs, meds | labs 56% duplicates, meds 63%; single rows repeated up to 826 times |
| 7 | major | Labs file mixes lab results with respiratory-therapy notes, device interrogation, ECG intervals, blood bank, pathology and implant records. | labs | `Lab Type` populated on 6% of rows; `Transcription` is the largest component |
| 8 | major | De-identification leaks. Full dates in device implant and blood-bank expiry fields, device serial numbers, signer credentials, month/year dates in notes. | labs, notes | 80 lab rows with mm/dd/yyyy; 67 serial-number rows; 42 notes with mm/yyyy |
| 9 | major | Two redaction vocabularies (`<PERSON>` / `<DATE_TIME>` in labs vs `[NAME]` / `[DATE]` in notes). | labs, notes | token counts in the per-file docs |
| 10 | major | Medications are mostly inpatient administration records from the index admission. Outpatient history is thin and durations are meaningless at year resolution. | meds | 86% inpatient; 2,358 auto-discontinued at discharge |
| 11 | major | Same analyte under multiple component names and LOINC codes; LOINC on only 32% of rows. | labs | creatinine 4 names, eGFR 5, haemoglobin 3; 15 names with two LOINC codes |
| 12 | major | Unit strings differ by case and spelling across two source eras; MPV mislabelled as `%`. | labs | 76 unit strings; `MG/DL` before 2022, `mg/dL` after |
| 13 | major | Flags are only present when abnormal; a null flag is not "normal". | labs | `Is Abnormal` = 0 on 3 rows only |
| 14 | major | Censored values stored as strings (`>60`, `<0.01`) and 88 plain numbers never parsed. | labs | 112 censored rows |
| 15 | major | 13 deleted and 4 unsigned notes, including 9 deleted operative reports. | notes | `Signed Status` |
| 16 | major | `Rx Norm Codes` is a JSON concept set with a median of 14 codes per row, not a single identifier. | meds | up to 150 codes in one cell |
| 17 | minor | `Note Type` is constant (`Generic`); `Service` missing on 39% of notes; authoring specialty missing on 76%. | notes | |
| 18 | minor | Patient id column named `Patient` in two files and `Profile Key` in the third. | all | |
| 19 | minor | `Date Shift Days` column exists but is empty; `Row` index unsorted. | meds, labs | |
| 20 | minor | Reference ranges are free text in at least 15 patterns. | labs | |
| 21 | minor | Non-drug items (contrast, test strips, containers) and nursing instructions inside the medication list. | meds | |
| 22 | minor | Operative-report headings vary (`OPERATION`, `OPERATIONS`, `OPERATIVE PROCEDURE`, `SURGERY/PROCEDURE`). | notes | |
| 23 | minor | Progress-note template filler (`No date`, empty section headers, social-history blocks). | notes | |
| 24 | major | Some notes contain unredacted names or ages in headers or assessment lines despite the redaction tokens elsewhere. | notes | flagged by the LLM extraction pass on 16 Sep; not reproduced anywhere in the repo |
| 25 | major | The same operation appears as two or three separate notes: a Deleted draft plus a Signed version, or a cardiologist's procedure note plus the surgeon's operative report. Counting notes over-counts operations. | notes | at least 8 pairs identified by the LLM pass |
| 26 | major | Device names were redacted as `[NAME]` in operative reports but often survive in a later clinic letter for the same patient; the valve model must be reconciled across a patient's notes. | notes | 25 operative reports with a redacted device name |
| 27 | major | Follow-up notes carry forward old pre-operative echo text, so a "severe stenosis" sentence in a late note can describe the native valve years earlier. Echo timing must be read from context, not from the note year. | notes | flagged by the LLM pass |
| 28 | minor | The same valve is named inconsistently across a patient's notes (Trifecta in the operative report, "CE" in a progress note; Sapien, S3 and S3 Ultra for one implant). | notes | |
| 29 | minor | Years written inside note text sometimes disagree with the shifted structured year by one year for the same event. | notes | |
