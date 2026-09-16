# Modeling Brief — Work Assignment for the Model Layer

**Owner of this work:** the team member taking the model layer.
**Author:** study design / integration.
**Status:** proposal. It follows the study spine the team agreed on; disagree before you start, not after.
**Hard deadline:** Thursday 17 September, 17:00. Nothing new gets built after Thursday noon.

---

## 0. Summary in one paragraph

No model is trained on the real packet. The extract yields 32 usable labels out of 117 patients,
5 of them failures, and exactly one patient has echo values in more than one year — a survival
model fitted on that is noise with a confidence interval around it. Your job is therefore to
build the **censoring-aware pipeline the study protocol specifies, executed end to end on a
literature-calibrated synthetic cohort**, and to write the modelling sections of
[`approach.md`](approach.md) so that the design, not the performance, is what the panel scores.
The real packet contributes counts and an extraction-yield figure, produced by someone else.

**You do not build the synthetic cohort.** It is supplied to you by the data workstream against a
frozen schema (section 4). Code against that interface from the start; a stub cohort is available
before the calibrated one, so nothing about your pipeline needs to wait for it.

---

## 1. Where the model layer sits

The project has three layers. Only the third is yours.

| Layer | What it is | Machine learning? | Owner |
|---|---|---|---|
| 1. Data processing | de-duplication, analyte/unit normalisation, whitelisted numeric parsing, temporal alignment to the note's service year | no — deterministic code | done, see [`../data/data_plan.md`](../data/data_plan.md) §4 |
| 2. Chart abstraction | note text → structured fields + evidence span + one of four label statuses; scored with precision/recall/F1, numeric agreement, Cohen's kappa | yes, but it predicts *what the chart says* | extraction owner |
| 3. Risk model | time from implant to structural valve deterioration, with death as a competing risk | yes, predicts *what happens to the patient* | **you** |

Keep the vocabulary of layers 2 and 3 separate in everything you write. The panel comes from a
chart-abstraction company; conflating the two reads as imprecision.

---

## 2. What the prototype data will and will not support

Every number below is measured on the extract and documented in
[`../data/data_plan.md`](../data/data_plan.md).

| Constraint | Measurement | Consequence for modelling |
|---|---|---|
| Labels | 32 of 117 patients labelled: 5 accept, 15 reject, 12 borderline; 85 missing information | ~5 events. Below any sample size that supports estimation |
| Serial echo | 143 mean-gradient mentions across 54–59 patients, **1 patient** with values in more than one note or year | no gradient change, no slope, no landmark updating |
| Exam dates | 119 of 143 mentions sit next to a redacted `[DATE]` | time resolution is one year at best; values within a note have no recoverable order |
| Age at implant | redacted in 194 of 215 notes, no demographics table | the strongest published predictor is unavailable |
| Cohort split | patients 001–100 have operative reports and no structured data; 101–117 have structured data and no operative report | no feature vector spans both groups |
| Follow-up | 74 of 100 cohort-A patients have all notes in a single year | heavy administrative censoring |

**Conclusion, and it is not negotiable:** the real packet is evidence of a data-access problem,
not a training set. Present it as the reason the protocol is designed the way it is.

---

## 3. Frozen rules

1. **No ΔMG, no gradient slope, no "first versus latest" from the real packet.** 34 patients have
   more than one prosthetic mean gradient, and 33 of them have every value inside the same note
   with the exam dates redacted. `latest − first` on those columns is a fabricated trajectory.
2. **No imputation across cohorts A and B.** It would invent the linkage the extract lacks.
3. **Labels are rule-based proposals awaiting clinician adjudication**, never ground truth. Use
   the four statuses (`accept` / `reject` / `borderline` / `missing information`) as they are.
4. **Death is a competing risk.** Report cumulative incidence (Aalen–Johansen), not Kaplan–Meier;
   KM overestimates deterioration when patients die first.
5. **Patient-level splits only.** Never split rows of the same patient across train and test.
6. **No real-data rows, snippets or per-patient outputs in the repo** — aggregate counts only.
   The private files live outside the repository; load them through
   [`../notebooks/data_paths.py`](../notebooks/data_paths.py).
7. **Every synthetic number is labelled synthetic** in the notebook, the figure caption, the
   document and the slide. A reviewer who thinks for one second that a metric came from patients
   is a lost submission.

---

## 4. Your input — the synthetic cohort (built by the data workstream, not by you)

**Ownership:** the generator belongs to the data workstream. This section is the **specification of
what you receive**, so you can code against it before it exists. It is documented here in full
because your modelling choices depend on how the cohort was generated — a model is only as
defensible as the data-generating process it was demonstrated on.

The cohort is produced with a fixed seed and matches published durability evidence. It exists so
the pipeline can be executed and evaluated honestly; it is not a claim about any patient.

**Interface — frozen, code against this:**

```python
from synthetic import generate
tables = generate(preset="ideal", seed=20260917, n_patients=1800)
# dict[str, pandas.DataFrame] with keys: patients, echos, events, followup
```

Equivalently, read the CSVs at `data/synthetic/<preset>/{patients,echos,events,followup}.csv`.
Every row of every table carries two governance columns that you must never drop:
`source` (always `simulated` here) and `time_resolution` (`day` / `year` / `unknown`).

**Target scale:** ~1,800 implants, ~190 deterioration events over 10 years — the figures the
sample size calculation in the protocol arrives at (Riley et al. 2019, `pmsampsize`).

**Data-generating process:**

1. **Baseline covariates** with plausible marginals: age, sex, body surface area, SAVR vs TAVR,
   valve model and label size, effective orifice area indexed to BSA (and the patient–prosthesis
   mismatch flag derived from it at the VARC-3 cut-offs ≤0.85 moderate, ≤0.65 severe), diabetes,
   chronic kidney disease, smoking, bicuspid anatomy.
2. **Latent time to structural deterioration** from a Weibull with shape > 1, so the hazard
   accelerates with time in the valve, and a log-linear covariate effect using published hazard
   ratios: age 0.91 per year (older is protective), BSA 1.77, PPM 1.95, smoking 2.28.
3. **Competing death** from a separate Weibull, independent of the SVD latent time given
   covariates, calibrated to an elderly surgical/transcatheter cohort.
4. **Serial mean gradient** from a linear mixed model — random intercept and slope per patient,
   with the slope increasing after the latent onset. This is what makes a landmark model
   meaningful, and it is exactly the structure the real extract does not have.
5. **Visit process** at the guideline times (reference echo 1–3 months, then 5 and 10 years,
   annually thereafter) with jitter, plus **informative dropout** so that a missed visit carries
   signal.
6. **Interval censoring:** an event becomes observable at the first echo whose values meet the
   endpoint criteria, not at the latent onset. Administrative censoring at 10 years.

**Calibration targets** (state the source next to each in the notebook):

| Quantity | Literature anchor |
|---|---|
| severe SVD at 10 y | NOTION: 1.5% transcatheter vs 10.0% surgical |
| moderate/severe SVD at 10 y | NOTION: 15.4% vs 20.8% |
| bioprosthetic valve failure at 5 / 7 y | PARTNER 3: 3.3–3.8% / 6.9–7.5% |
| severe SVD, registry | UK TAVI: 5.9% at median 7.8 y |
| all-cause death at 10 y | NOTION: ~63% in an 79-year-old cohort |

**Acceptance criterion:** the generator's cumulative incidence at 5, 8 and 10 years falls inside
a band you state explicitly around those anchors, and the notebook prints the comparison as a
table. If it does not, the generator is wrong — not the literature.

---

## 5. Deliverable 1 — the pipeline

One notebook, `notebooks/03_model_training.ipynb` (merge evaluation into it if time is short),
running end to end on the synthetic cohort.

**Formulation.** Time from implant to SVD-attributable VARC-3 stage ≥2 hemodynamic valve
deterioration or bioprosthetic valve failure stage 2–3, with death as a competing risk, events
interval-censored at echo visits, horizons of 5 and 8 years.

**Models.**

| Model | Role | Why |
|---|---|---|
| cause-specific Cox + Fine–Gray | baseline | interpretable, standard in the valve literature, handles the competing risk directly |
| penalized Cox (CoxNet) | baseline under small n | shrinkage is the honest answer to few events per parameter |
| gradient-boosted survival (scikit-survival GBSA) or Random Survival Forest | primary | non-linear interactions across valve model, size, PPM and gradient trajectory |
| landmark competing-risk model at fixed landmarks | primary, dynamic | lets each new echo update risk — this is the clinical product |

DeepHit and joint models are named in [`approach.md`](approach.md) as planned extensions and are
**not** implemented.

**Metrics.** Uno's IPCW C-index (Harrell's C is biased under this much censoring), time-dependent
cumulative/dynamic AUC at 5 and 8 years, IPCW Brier and integrated Brier score, calibration
against Aalen–Johansen at the fixed horizons, and a decision curve for the surveillance decision.

**Comparators**, because a model that does not beat the current practice is not worth deploying:
the guideline calendar schedule, time since implant alone, and a Cox model using only the
published risk factors.

**Outputs of one inference:** probability of SVD at 5 and 8 years, a Low/Moderate/High tier, the
top three contributing features, and a recommended next echo interval.

**Two figures, and they must be slide-ready** (dark and light legible, labelled *synthetic*):

1. calibration plus cumulative incidence against Aalen–Johansen;
2. the decision curve, or the reallocation of surveillance intervals — how many echoes move
   earlier and how many move later at a fixed capacity.

### The degradation ladder — a joint deliverable, and the one original result in the submission

The data workstream supplies the **same cohort six times**. Five are the same patients with their
data progressively stripped; the sixth is not simulated at all. You run **the unchanged pipeline**
on each and report the primary metric per rung:

| rung | what is removed | the question it answers |
|---|---|---|
| `ideal` | nothing | what the design achieves when the data are what the protocol asks for |
| `no_age` | age at implant | what the strongest published predictor is worth |
| `year_resolution` | exact dates, collapsed to calendar year | what date-shifting to the year costs |
| `single_echo` | all follow-up examinations but one | what serial surveillance is worth |
| `as_supplied` | our simulation of the extract: one encounter with its quoted priors, examinations for only the 52% abstraction reaches, no device identity, **no mortality** | what our extract supports, as modelled |
| `as_received` | **nothing — this *is* the supplied extract**, mapped into the same schema | what our extract supports, in fact |

Get them all, real rung included, in one call:

```python
from cohort.ladder import full_ladder, availability
rungs = full_ladder()            # dict of six, in ladder order
print(availability())            # what an analyst can see in each, before any model
```

This converts "the data were poor" into a **ranked, quantified list of which defect costs most**,
which is the argument a hospital needs in order to justify supplying dated serial echoes. And
because the last rung is the extract itself rather than a simulation of it, the panel is not being
asked to take the simulation on trust.

**Three things to expect on the real rung, so they do not surprise you mid-run.** It has 117
patients, not 1,800. It carries **no deaths at all** — the extract contains no mortality data, so
the competing risk is unobserved and a cumulative incidence computed there is not comparable with
one computed where death is known; say so wherever you report it. And its only events are 14
documented reinterventions, because haemodynamic staging needs a reference examination the extract
does not contain. Expect the metric to be uninformative on that rung. **That is the finding, not a
failure** — and it is the strongest argument in the submission for building the abstraction
pipeline the protocol proposes.

Budget for it: one loop over six cohorts, the same function you already wrote. Do not restructure
the pipeline for it — if it is not a loop, the rungs are wrong and that is the data workstream's bug.

---|---|---|
| `ideal` | nothing | what the design achieves when the data are what the protocol asks for |
| `no_age` | age at implant | what the strongest published predictor is worth |
| `year_resolution` | exact dates, collapsed to calendar year | what date-shifting to the year costs |
| `single_echo` | all follow-up echoes but one | what serial surveillance is worth |
| `as_supplied` | all of the above together | what our actual extract supports |

This converts "the data were poor" into a **ranked, quantified list of which defect costs most**,
which is the argument a hospital needs in order to justify supplying dated serial echoes. Budget
for it: one loop over five directories, the same function you already wrote. Do not restructure the
pipeline for it — if it is not a loop, the presets are wrong and that is the data workstream's bug.

---

## 6. Deliverable 2 — the modelling sections of `approach.md`

Sections 1–7 of [`approach.md`](approach.md) are yours. Vague answers score low; each choice needs
a justification tied to the clinical setting. Section 7 (limitations) is the one that wins points
here: sparse follow-up, inter-observer echo variability, new valve models with no history, and
the verification bias created by the fact that patients are echoed because someone was worried.

---

## 7. Out of scope — do not start these

- Any model fitted on the 32 real labels, illustrative or otherwise.
- External validation experiments.
- DeepHit, joint models, anything that needs tuning time we do not have.
- A third notebook. Two is the cap.
- **The synthetic generator itself.** It belongs to the data workstream (section 4). If it blocks
  you, say so in the group rather than writing a second one — two generators means two different
  cohorts and no comparable numbers.

---

## 8. Environment and conventions

The repository uses **uv**. After pulling, run `uv sync`. Add packages with `uv add`, never pip,
and commit `pyproject.toml` together with `uv.lock`.

```bash
uv add lifelines scikit-survival shap matplotlib pandas numpy jupyter
```

A scratch install confirmed the stack resolves (lifelines 0.30.3, scikit-survival 0.28.0,
shap 0.52.0) and that a Cox/RSF/GBSA pipeline with Uno's C, time-dependent AUC and IBS runs in
seconds at this scale. Work on the shared branch `team/dyanooumenoi`, stage explicitly, never
force-push, and keep every file in the repository in English.

---

## 9. Definition of done

- [ ] The notebook consumes the supplied cohort through the section 4 interface, with no local
      copy of the generator and no hand-edited data.
- [ ] The notebook runs top to bottom on a clean checkout after `uv sync`.
- [ ] The degradation ladder is reported for all six rungs, the real one included, as a single
      table or figure.
- [ ] Uno's C, time-dependent AUC, IBS and calibration are reported for the primary model and for
      all three comparators.
- [ ] The two figures are exported as files and handed over for the deck.
- [ ] Sections 1–7 of `approach.md` are written, with no placeholder text left.
- [ ] Every synthetic result is labelled as synthetic in the notebook, the figure and the document.

---

## 10. Traps

- The `prosthetic_mean_gradient_first` / `_latest` / `_max` columns in the extraction workbook
  look like a trajectory and are not one. Treat them as a min and a max within one note, order
  unknown.
- The laboratory abnormal flag is populated only when a result was flagged; a null is not "normal".
- Laboratory and medication rows contain 56% and 63% exact duplicates from an export join
  fan-out. Any count taken before de-duplication is roughly doubled.
- The medications file is an administration record from the index admission, not a drug history.
- Kaplan–Meier on this endpoint overstates deterioration; use cumulative incidence.

---

## 11. Questions that block you, and who answers them

| Question | Owner |
|---|---|
| Primary endpoint: VARC-3 stage 2/3 HVD plus BVF stage 2, and which single-echo fallback | team, with the clinical lead |
| Whether a later valve-in-valve counts as the outcome of the first implant | team |
| Whether inferred sex (from pronouns) is used as a covariate or dropped | team |
| The band the generator must fall inside to be called "calibrated" against the literature anchors | data workstream, stated explicitly |
| Anything about the cohort's generating process that changes your modelling choices | data workstream |

The full list lives in [`../data/open_questions.md`](../data/open_questions.md) and the candidate
endpoint definitions in [`../data/endpoint_criteria.md`](../data/endpoint_criteria.md). Read both
before you write section 1 of `approach.md`.
