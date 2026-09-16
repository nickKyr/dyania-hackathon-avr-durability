# CLAUDE.md

Team submission repo for the Dyania Health Docathon / Hackathon (Athens, 15-18 Sep 2026, with Onassis Hospital, NVIDIA coaching).

## Challenge

Design a study (ML, statistical model, or any approach) proposing a protocol to **predict aortic valve durability in patients with a bioprosthetic aortic valve replacement** (structural valve deterioration, SVD, after SAVR / TAVR). Team is physicians + engineers.

## Deadlines

- **Final commit: 17:00, Thursday 17 September 2026.** Anything pushed later is not assessed. Repos are locked at 17:00.
- Presentation the same evening (20:15-21:15): about 5 min pitch plus 2 min panel Q&A.
- Awards Friday 18 Sep, Onassis Hospital.
- Mentor office hours Wed 16 Sep: technical 14:00-19:00 (Niki Altani, elpiniki@dyaniahealth.com), clinical 17:00-18:00 (Myrto Bakatsia, myrto@dyaniahealth.com).

## Scoring

Final score = 40% case study (this repo) + 20% Docathon (physician-only sprint vs Synapsis AI) + 40% judges (live pitch).

Repo rubric (`evaluation/scoring_rubric.md`, 1-5 per criterion):

| Criterion | Weight |
|---|---|
| Clinical validity | 25% |
| ML approach | 25% |
| Study design quality | 20% |
| GitHub & documentation | 15% |
| Presentation | 15% |

Every choice in the docs should be justified against the clinical context. Vague answers score low.

## Deliverables

| File | Content |
|---|---|
| `README.md` | Approach, problem framing, key design decisions, team info |
| `protocol/study_protocol.md` | Main deliverable: objectives, cohort, endpoints, statistical plan, ethics & privacy |
| `model/approach.md` | Model choice, features, validation, outputs, clinical integration, limitations |
| `data/data_plan.md` | Data sources, availability assumptions, preprocessing, labels, governance |
| `presentation/slides.pdf` | 7-10 slides. `presentation/slides.md` is the outline to follow |
| `notebooks/` | Proof of concept. Optional but scored positively |

Every `> *Fill in:*` block is a placeholder and must be replaced. No section may be left empty. The README's structure section says `ml/approach.md`, but the real folder is `model/`, so keep using `model/` and fix the README.

## Git workflow

- Work on branch `team/dyanooumenoi`. Remote `origin` is the fork `nickKyr/dyania-hackathon-avr-durability`.
- Submit by opening a PR to `dyaniahealth/dyania-hackathon-avr-durability` `main`, titled `Team submission: dyanooumenoi`. Do not merge it.

## Provided data

Three de-identified EHR extracts in `data/` (Epic/Caboodle style, one sheet named "Query result" each). Dates are shifted and reduced to the **year only**.

- `labs_deidentified.xlsx`: 43,550 rows, 17 patients. Lab component names, LOINC code and name, Result Date, flag / is abnormal, string and numeric value, unit, reference range.
- `medications_deidentified.xlsx`: 5,807 rows, 17 patients. Generic name, therapeutic and pharmaceutical class, dose, route, start / end / discontinued year, RxNorm codes, associated diagnoses (JSON with ICD-10).
- `notes_deidentified.xlsx`: 215 notes, 117 patients (`Profile Key`). Note types include Operative Report, services include Cardiac Surgery. Free text with `[DATE]` / `[ID]` redactions.

There is no structured echo table. Echo parameters (mean gradient, EOA, regurgitation, PPM) have to be extracted from note text.

## Data rules

- **Never commit patient data.** `*.xlsx` is gitignored. The repo may be public.
- Do not paste raw note text, patient-level rows, or identifiers into docs, notebook outputs, or slides. Only aggregate results.
- Clear notebook outputs that show row-level data before committing.

## Environment

The team uses uv (`pyproject.toml`, `uv.lock`). Add packages with `uv add <pkg>`, run from the repo root. Data build scripts live in `scripts/` (01 rules extraction, 02 merge LLM JSON, 03 raw tables, 04 single sheet); analysis notebooks live in `notebooks/` (01 raw overview, 02 preprocessing, then training and evaluation) with shared plot style in `notebooks/viz.py`.
