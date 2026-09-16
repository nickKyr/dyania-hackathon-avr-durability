# Labs file

`data/labs_deidentified.xlsx`, 43,550 rows, 16 columns, 17 patients.

## Columns

| Column | Non-null | Distinct | Comment |
|---|---|---|---|
| Row | 100% | 43,550 | export index, not sorted |
| Patient | 100% | 17 | |
| Lab Component Name | 100% | 703 | primary label for the row |
| Lab Component Base Name | 73% | 528 | internal short code |
| Lab Component Common Name | 100% | 735 | mostly upper-cased copy of the name |
| Lab Abbreviation | 1% | 18 | |
| Lab Type | 6% | 4 | `Lab Standard`, `Lab Anatomic Pathology`, `External Blood Bank`, `Lab Microbiology`; populated only from 2021 onward |
| Loinc Code / Loinc Name | 32% | 179 / 192 | |
| Result Date | 100% | 24 | year only, 2004 to 2027 |
| Flag | 16% | 6 | `Low`, `High`, `Abnormal`, `Low Panic`, `Actionable`, `(NONE)` |
| Is Abnormal | 16% | 2 | 1 on 6,798 rows, 0 on only 3 rows |
| String Value | 95% | 3,394 | |
| Numeric Value | 62% | 2,031 | |
| Unit | 54% | 76 | |
| Reference Values | 44% | 329 | free-text patterns |

## Duplicates

24,548 of 43,550 rows (56%) are exact duplicates of another row once the `Row` index is dropped. After de-duplication 19,002 rows remain. Some rows repeat more than 100 times, and one repeats 826 times. Duplication is heaviest in respiratory-therapy fields (`Med Route`, `Med Name 1`, `Work of Breathing`), body temperature and device interrogation counters. It looks like a join fan-out in the export rather than repeated measurements, so exact de-duplication is safe.

## Content mix

The file is not a lab table. A keyword classification of the 19,002 unique rows by component name gives:

| Content | Unique rows | Example components |
|---|---|---|
| Blood gases and whole-blood analysers | ~5,000 | `pH, Arterial`, `pO2, Arterial`, `Lactate`, `Sodium, Whole Blood`, `Calcium Ionized, Whole Blood` |
| Respiratory therapy sessions | ~2,500 | `Transcription`, `Pre Resp Rate`, `Work of Breathing (Pre)`, `Cough Type`, `PEP Reps`, `Adverse Effects Y/N`, `Med Name 1` |
| Pacemaker / ICD interrogation, implant records, ECG intervals | ~1,700 | `Lead Impedance (RV)`, `Implantable Pulse Generator Model`, `Implant Date`, `Serial Number`, `ICD-Shocks Aborted`, `QT Interval` |
| Blood bank | ~200 | `ABO/RH(D)`, `Antibody Screen`, type-and-screen expiry |
| Pathology and microbiology | ~150 | `Specimen Description`, `Culture Report` |
| Everything else: chemistry, haematology, coagulation, urinalysis, lipids, LVEF, misc | ~9,400 | `Creatinine`, `Hemoglobin`, `Platelet Count`, `PT INR`, `LV Ejection Fraction` |

`Transcription` rows are the largest single component (8,677 raw, 1,355 unique). They are respiratory-therapy narrative and electronic-signature lines split into fragments of about 30 characters, not echo, cath or radiology reports. No gradient, valve or prosthesis terms occur in them.

The device rows (four patients) describe pacemakers and CRT defibrillators, not heart valves. `Model`, `Serial Number` and `Implant Date` refer to those devices.

## Coding and naming

- LOINC is present on 32% of raw rows. Coverage is 40 to 50% in most years, near zero in 2024 to 2026.
- 15 component names map to two different LOINC codes each (for example `Glucose`, `Magnesium`, `Phosphorus`, `pH, Arterial`). 14 LOINC codes map to more than one component name (for example creatinine, glucose and haemoglobin each appear under two or three names).
- The same analyte is split across names: creatinine appears as `Creatinine`, `Creatinine (POCT)`, `Creatinine, Blood`; haemoglobin as `Hemoglobin`, `Hemoglobin Total, Whole Blood`, `Hemoglobin, Whole Blood`; eGFR as five variants including race-stratified ones.
- Naming style changes over time. A legacy source (2005 to about 2021) uses `MG/DL`, `K/uL`, `pG`; the newer source (2021 onward, where `Lab Type` is populated) uses `mg/dL`, `k/uL`, `pg`. Creatinine switches unit spelling completely in 2022.

## Units

76 distinct unit strings; 19,848 raw rows (5,217 unique rows) have none. Problems found:

| Component | Units seen | Comment |
|---|---|---|
| Creatinine | `MG/DL`, `mg/dL` | same unit, case differs, era-dependent |
| WBC, Platelet Count, Abs counts | `K/uL`, `k/uL` | same unit |
| MCH | `pG`, `pg` | same unit |
| MCHC | `%`, `g/dL` | same unit numerically, different label |
| MPV | `%`, `fL` | `%` is wrong for MPV; legacy mis-mapping |
| RBC | `M/uL`, `m/uL` | same unit |
| eGFR | `mL/min/1.73m2`, `mL/min/1.73 m2`, `mL/min per 1.73 m2`, `mL/min/1.73m²` | four spellings |
| pCO2 / pO2 | `mm Hg`, `mmHg` | same unit |
| Osmolality | `mOs/kg`, `mOsm/kg` | typo |
| `.` , blank, `comment:`, `yes/no` | | placeholder units |

## Values

- 16,416 rows have no numeric value. 14,159 of those have a string value (respiratory text, signatures, device labels). 2,257 have neither.
- 112 rows are censored results stored only as strings (`>60` for eGFR, `<0.01` for troponin, `>=100,000 CFU/ml`). 88 rows hold a plain number in the string field that was never parsed into the numeric field.
- `Flag` and `Is Abnormal` are only populated when a result is flagged. A null does not mean normal; it means no flag was attached (and many components such as blood gases and device values never get flags).
- `Reference Values` is free text in at least 15 patterns (`Low: x High: y`, `Normal: <x`, `Low: NEGAT`, `Normal: R#`). Lower and upper bounds need a parser.
- Date-time and person fields inside `Numeric Value` occur (for example notification times stored as 154600.0), so numeric parsing must be restricted to a whitelist of components.

## Analytes relevant to valve durability

Counts are unique rows after de-duplication.

| Analyte | Patients | Unique rows | Comment |
|---|---|---|---|
| Creatinine | 17 | 285 | plus 15 point-of-care rows and one `Creatinine, Blood` |
| eGFR | 17 | ~80 per variant | five name variants, two race-stratified per draw |
| Hemoglobin | 17 | 240 | plus whole-blood variants |
| Platelet Count | 17 | 291 | |
| PT INR | 17 | 66 | plus 7 `INR` rows |
| Troponin T | 16 | 44 | mostly peri-operative |
| NT-proBNP | 10 | 35 | 11 patients if the `ProBNP` and point-of-care BNP variants are merged |
| Calcium (total) | 17 | 189 | plus 64 `Calcium, Total` |
| LDL cholesterol | 14 | 18 | 15 with the direct LDL variant |
| Phosphorus | 4 | 25 | |
| CRP | 1 | 1 | |
| HbA1c, PTH, LDH, haptoglobin, lipoprotein(a) | 0 | 0 | absent |

Calcium-phosphate product, a plausible SVD risk marker, is computable for only four patients. Serial creatinine exists for the six long-span patients only.

## De-identification observations

- Tokens are `<PERSON>` (326 rows), `<DATE_TIME>` (156), `<LOCATION>` (49), `<PHONE_NUMBER>` (8), `<URL>` (2). This is a different redaction pipeline from the notes.
- 80 rows keep full month/day/year dates in `String Value`: device `Implant Date` (46), type-and-screen expiry (28), ICD counter reset dates, product expiry and one culture report. These are unshifted-looking dates and contradict the year-only policy.
- Device serial numbers are present in clear text on 67 rows. Implanting physician fields are populated on 13 rows.
- 108 rows contain "Electronically Signed By" text with credentials.
