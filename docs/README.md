# Data investigation

Findings from a first pass over the three de-identified EHR extracts in `data/` (16 Sep 2026). All numbers are aggregates; no patient-level rows or note text are reproduced here. Re-run `uv run python scripts/00_profile_extracts.py` from the repo root to regenerate every figure quoted.

| Document | What it covers |
|---|---|
| [data_overview.md](data_overview.md) | What the three files are, how patients link across them, time coverage |
| [labs.md](labs.md) | Labs file: content mix, duplicates, coding, units, usable analytes |
| [medications.md](medications.md) | Medications file: inpatient bias, duplicates, coding, usable signals |
| [notes.md](notes.md) | Notes file: note types, sub-cohorts, valve models, echo values in text, redaction |
| [data_quality_issues.md](data_quality_issues.md) | Consolidated problem list, ranked by impact |
| [recommendations.md](recommendations.md) | What the data can and cannot support, and the preprocessing plan |
| `../scripts/01_extract_rules.py`, `02_merge_llm_extraction.py` | Build `data/structured_extraction.xlsx` (gitignored): rule-based extraction, then the Claude Sonnet note-by-note pass merged in with per-study echo rows, quoted evidence and comparison sheets |
| `../scripts/03_build_raw_tables.py` | Builds the raw, conclusion-free tables the preprocessing pipeline starts from: `data/raw_tables/*.parquet` plus `data/raw_tables.xlsx` (both gitignored). One table per grain, shared keys, no derived fields |
| [docathon_briefing.md](docathon_briefing.md) | Briefing for the clinical members before the physician-only Docathon sprint: the four-label scheme, the six reading traps, a per-question checklist and worked examples |
| [research/synapsis_ai.md](research/synapsis_ai.md) | How Synapsis AI works (sourced), Dyania's method and events, framing advice for the judges |
| [research/svd_literature.md](research/svd_literature.md) | VARC-3 and consensus SVD definitions with thresholds (§2), risk factors and published effect sizes (§3), a cross-check of the cohort generator's injected hazard ratios against those estimates (§3.6), trial outcomes, existing models, statistical methods, cohort sizing |
| [research/ehr_extraction_methods.md](research/ehr_extraction_methods.md) | Cited methods for each data problem: echo and operative note extraction, assertion, year-only dates, data quality, proxy datasets |

## Headline findings

1. **Two disjoint sub-cohorts.** Patients 001 to 100 have operative reports and follow-up notes but no labs or medications. Patients 101 to 117 have labs and medications but only one note each and no operative report. There is no patient with the full picture.
2. **More than half of the structured rows are exact duplicates.** Labs: 56% duplicate rows (43,550 raw, 19,002 unique). Medications: 63% duplicate rows (5,807 raw, 2,157 unique).
3. **The "labs" file is a mixed bag.** Only about 6% of raw rows (9% after de-duplication) carry a lab type. The rest include respiratory-therapy session notes chopped into 30-character lines, pacemaker and defibrillator interrogation values, ECG intervals, blood bank, pathology specimen descriptions and device implant records. Conventional chemistry and haematology are roughly half of the unique rows.
4. **There is no structured echo data anywhere.** The only echo-derived structured value is LV ejection fraction (77 unique rows). Gradients, valve area, dimensionless index and regurgitation grade exist only inside note text, in a consistent sentence pattern that regex can extract.
5. **Follow-up is thin.** 59 of the 100 operative-report patients have every note in the same calendar year as surgery. Only 41 have any note in a later year. Serial echo trajectories per patient are mostly unavailable.
6. **Dates are year-only and shifted, with artefacts.** Both structured files contain rows dated 2027. Seven notes mention a year later than their own service year. Age is redacted everywhere, so there are no demographics at all.
7. **De-identification is incomplete and inconsistent.** Labs use `<PERSON>` and `<DATE_TIME>` tokens while notes use `[NAME]` and `[DATE]`. The labs file keeps full month/day/year dates in device implant and blood-bank expiry fields, and device serial numbers. Notes keep month/year partial dates in 42 places.
8. **Events are rare but present.** Six operative reports describe transcatheter valve-in-valve implantation into a failed surgical bioprosthesis. Seventeen notes across 16 patients use failed-bioprosthesis or structural-deterioration language. One medication row carries the ICD-10 code for prosthetic aortic valve failure.
