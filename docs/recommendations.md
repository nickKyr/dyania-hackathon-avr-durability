# Recommendations

## What the provided data can support

- A **feasibility demonstration** of an extraction pipeline: implant approach, valve model and size from operative reports; prosthetic gradients, DVI, AVA, LVEF and regurgitation from follow-up notes; operation year from anaesthetic orders; renal, haematological and antithrombotic covariates from labs and medications.
- A **label-definition exercise**: the six valve-in-valve operative reports and the notes with failed-bioprosthesis language show what a VARC-3 style adjudication would consume, and how rare the event is.
- **Descriptive statistics** on the surgical cohort: mix of transcatheter vs surgical implants, model distribution, size distribution, share with any follow-up echo.

## What it cannot support

- Training or validating a survival model. There are about 100 implanted patients, a handful of confirmed events, no exact dates, and serial echo for very few patients.
- Age, sex or body-size adjusted analysis. Demographics are absent.
- Any claim about inter-site generalisation. One institution, one export.

The protocol and model documents should say this plainly and position the notebook as a proof of pipeline, not a proof of performance. The scoring rubric rewards honest, well-justified design over inflated results.

## Preprocessing plan

1. **De-duplicate** both structured files on all columns except `Row`. Report the before and after row counts.
2. **Harmonise patient ids**: rename `Profile Key` to `Patient`, keep `Patient_001` to `Patient_117`.
3. **Split the labs file** into (a) laboratory results, (b) blood gases, (c) respiratory therapy, (d) device interrogation, (e) other. Do this by a whitelist on `Lab Component Name` plus `Lab Type`, not by LOINC alone.
4. **Map analytes** to a small canonical dictionary (creatinine, eGFR, haemoglobin, platelets, INR, NT-proBNP, troponin T, calcium, phosphorus, LDL, albumin, LVEF). Merge the name variants and the LOINC variants. Normalise unit strings to lower case with whitespace removed before comparison. Drop the race-stratified eGFR duplicates in favour of one series.
5. **Parse values**: coalesce `Numeric Value` with a numeric parse of `String Value`; keep censored values (`>60`, `<0.01`) as a separate limit-of-detection flag; treat null `Flag` as "not flagged", never as "normal".
6. **Medications**: after de-duplication, derive per patient-year flags for warfarin, DOAC, aspirin, P2Y12, statin, loop diuretic, RAAS inhibitor, SGLT2 inhibitor; derive operation years from anaesthetic, protamine, tranexamic and aminocaproic rows; ignore `Dose`, `End Date` and `Discontinued Date` for now.
7. **Notes**: exclude `Deleted`; keep `Addendum`; strip both redaction vocabularies; segment operative reports on their heading variants; classify implant approach (transcatheter vs surgical) and extract model and size; extract echo parameters with the sentence patterns documented in `notes.md`, and tag each as native or prosthetic from context.
8. **Timeline**: treat every event at year resolution; compute follow-up as note year minus operation year; drop rows dated after 2026.
9. **Governance**: keep the venv and every `.xlsx` out of git (already ignored); never print row-level output in notebooks; note in the data plan that the received extract still contains full dates and device serial numbers and should be re-processed by the data owner before any wider use.

## Data plan for a real study

The data plan should ask for what is missing here: a demographics table (age at implant, sex, BSA), a structured echo measurements table with exam dates, an implant registry entry (approach, model, size, date), a procedures table for re-interventions, a diagnosis table for endocarditis and thrombosis, and consistent date shifting across all sources with a single redaction vocabulary. Each of these maps directly to a gap documented in `data_quality_issues.md`.
