# Medications file

`data/medications_deidentified.xlsx`, 5,807 rows, 23 columns, the same 17 patients as the labs.

## Columns

| Column | Non-null | Distinct | Comment |
|---|---|---|---|
| Patient | 100% | 17 | |
| Proper Name | 100% | 593 | brand or formulation name with strength |
| Simple Generic Name | 98% | 313 | best key for grouping |
| Medication Therapeutic / Pharmaceutical Class / Subclass | 98% | 35 / 181 / 221 | |
| Medication Strength, Form, Expected Route | 92 to 97% | | |
| Start Date | 100% | 23 | year only, 2001 to 2027 |
| Administration Date | 86% | 16 | populated only for inpatient rows, always equal to Start Date |
| End Date | 96% | 22 | |
| Discontinued Date | 81% | 21 | |
| Mode | 100% | 2 | `Inpatient` 86%, `Outpatient` 14% |
| Frequency | 96% | 83 | free text (`DAILY`, `2 TIMES DAILY 9AM/5PM`, `ONCE - WARFARIN`) |
| Route | 86% | 24 | |
| Dose / Dose Unit | 89% | 84 / 26 | |
| Discontinued Reason | 50% | 14 | |
| Rx Norm Codes | 96% | 518 | JSON array, median 14 codes per row, up to 150 |
| Prescribing Provider Specialty | 26% | 18 | |
| Associated Diagnoses | 0.5% | 18 | JSON with ICD-10 |
| Date Shift Days | 0% | 0 | entirely empty |

## Duplicates

3,650 of 5,807 rows (63%) are exact duplicates. 2,157 unique rows remain. The multiplicity goes up to 61 copies of one row. As with labs, this looks like join fan-out.

## Inpatient bias

86% of raw rows and 64% of unique rows are inpatient orders. 2,358 raw rows were discontinued with "Auto DC at discharge" and 338 with "Auto DC with change in level of care". The file is mostly the medication administration record of the index admission, not a longitudinal outpatient medication history. Perioperative agents dominate the top generics: metoprolol, furosemide, insulin lispro, docusate, oxycodone, potassium chloride, heparin, lidocaine, fentanyl.

End and discontinued years equal the start year for 77% and 90% of unique rows respectively. At year resolution, durations and adherence cannot be derived.

## Coding

- `Rx Norm Codes` is a concept set (every related RxNorm identifier for the product family), not a single code. It cannot be used as a join key without choosing one code per row.
- 51 unique rows have no generic name. They are infusions and nursing instructions (`NITROPRUSSIDE IV INFUSION`, `HEPARIN NOMOGRAM - INSTRUCTIONS FOR NURSE`, `OR IRRIGATION BUILDER`).
- Non-drug items are mixed in: radiology contrast, echo contrast (perflutren), glucose test strips, lancets, pen needles, empty containers.
- The same generic appears under many proper names (warfarin 10 variants, furosemide 8, potassium chloride 8).
- `Associated Diagnoses` is populated on 24 unique rows only. Codes seen include I35.0 (aortic stenosis), Z95.2 (presence of prosthetic heart valve), I50.32/I50.33 (diastolic heart failure), M31.6 (giant cell aortitis) and T82.01XA (breakdown of heart valve prosthesis). The T82.01XA row is the only structured prosthetic-failure signal in the whole dataset and belongs to one patient.

## Usable signals

- Operation year: anaesthetic, protamine, tranexamic acid or aminocaproic acid orders identify a surgery or procedure year for all 17 patients. Several patients have two or three such years, consistent with re-interventions or other procedures.
- Antithrombotic therapy: aspirin in 16 patients, statins in 16, warfarin in 6, apixaban in 2, dabigatran in 1, clopidogrel in 3. Warfarin use after a bioprosthesis is a documented SVD-related covariate, and here it can only be flagged as present or absent per year.
- Heart-failure and renal therapy: loop diuretics in 17 patients, RAAS inhibitors in 13, SGLT2 inhibitors in 3.
- Diabetes: insulin or oral agents in all 17 patients, but mostly inpatient sliding-scale insulin, so it is not a reliable diabetes flag.

## Artefacts

- One row dated 2027.
- `Date Shift Days` is present as a column but empty, which confirms the shift was applied upstream and cannot be reversed or checked.
- Prescribing specialty is missing on 74% of rows; where present it is mostly Thoracic Surgery, Cardiology and Anaesthesiology.
