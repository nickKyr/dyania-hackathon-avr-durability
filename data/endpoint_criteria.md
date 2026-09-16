# Candidate Failure Criteria

Published criteria under consideration for the primary endpoint, and how each maps onto what
the prototype extract can actually support. The final column records the decision and, where one
has been taken, the code that enforces it. Where the supplied extract is handled differently, the
row says what `notebooks/pipeline/prep.py` applies to it.

| criterion | definition | timing | how it maps to our data | decision, as implemented |
|---|---|---|---|---|
| VARC-3 stage 2 HVD (moderate) | mean gradient rise >= 10 mmHg from reference echo resulting in >= 20 mmHg, with EOA fall >= 0.3 cm2 or >= 25 % and/or DVI fall >= 0.1 or >= 20 %; or new / one-grade worse intraprosthetic AR that is at least moderate | reference echo 30 days to 3 months after implant | needs serial echo; single-echo fallback: mean gradient >= 20 mmHg | **Adopted, primary.** Transcribed verbatim in `synthetic/generator.py::VARC3_STAGE2` and applied examination by examination by `_meets_stage(severe=False)`; emitted as `svd_stage2`. The reference window is `VisitParameters.reference_min_days=30` / `reference_max_days=90`. |
| VARC-3 stage 3 HVD (severe) | rise >= 20 mmHg resulting in >= 30 mmHg, with EOA fall >= 0.6 cm2 or >= 50 % and/or DVI fall >= 0.2 or >= 40 %; or severe AR | as above | single-echo fallback: mean gradient >= 30 mmHg or DVI < 0.25 | **Adopted, reported separately.** `VARC3_STAGE3`, `_meets_stage(severe=True)`, emitted as `svd_stage3`. `test_severe_criteria_are_strictly_harder_than_moderate` and `test_every_severe_event_has_a_moderate_one` hold it to the stage-2 definition. |
| VARC-3 bioprosthetic valve failure stage 2 | reintervention (valve-in-valve TAVR or redo SAVR) for valve deterioration | any time | operative report or history mention of valve-in-valve / redo | **Adopted.** Emitted as `bvf_reintervention`. On the supplied extract it accounts for nine of the ten affected valve episodes, because haemodynamic staging needs a reference examination the extract rarely contains; the tenth is a stage-2 deterioration labelled under the relaxed extract rule (`require_eoa_or_dvi_confirmation=False`). Operative records survive where echo values do not (`test_the_as_supplied_rung_keeps_reinterventions_when_it_drops_echoes`). |
| EAPCI/ESC/EACTS 2017 moderate SVD | mean gradient 20-40 mmHg or rise 10-20 mmHg, or moderate AR | from baseline | — | **Not implemented.** Kept as a sensitivity definition only; no code applies it. |
| EAPCI/ESC/EACTS 2017 severe SVD | mean gradient >= 40 mmHg or rise >= 20 mmHg, or severe AR | from baseline | — | **Not implemented.** As above. |
| Subclinical / clinically relevant SVD (two-tier echo definition) | subclinical: MG rise > 10 mmHg with EOA fall > 0.3 cm2 and/or DVI fall > 0.08; or new at-least-mild intraprosthetic AR up to moderate; or a morphological change in the leaflets. Clinically relevant: MG rise > 20 mmHg with EOA fall > 0.6 cm2 and/or DVI fall > 0.15; or AR worsening to moderate-to-severe or severe | against the post-intervention baseline | the subclinical tier has no absolute gradient floor, so it is far more sensitive than VARC-3 stage 2; the morphological criterion needs leaflet imaging, which no extract here contains | **Not implemented.** Recorded because incidence figures quoted from series that used it (subclinical 30.1% vs clinically relevant 6.6% in the same patients) are not comparable with VARC-3 figures. Transcribed in full in [`../docs/research/svd_literature.md`](../docs/research/svd_literature.md) §2.5. |
| Single-echo fallback | absolute-threshold arm of the VARC-3 definition applied to one examination with no reference | any | the only arm the extract can support for most patients | **Open — owner: the clinical lead.** A fallback is unavoidable on this extract, but its thresholds have not been ratified. The extract pipeline currently applies no single-echo fallback (`hvd_without_reference=False`); labels built with one are strictly weaker than the criteria above and must be declared as such wherever they are used. |
| Exclusions (non-structural) | endocarditis, valve thrombosis, isolated paravalvular leak, isolated patient-prosthesis mismatch | — | flagged separately in events | **Adopted as a study rule.** Regurgitation identified as paravalvular is excluded from the regurgitation arm, and a reintervention driven by endocarditis or paravalvular leak **censors** the patient rather than counting as an event. On the supplied extract, candidate events with endocarditis, thrombosis or paravalvular evidence are marked non-structural and not counted: 8 of the 18 candidate rows. |

## Why a single-echo fallback is listed

VARC-3 stage 2/3 haemodynamic valve deterioration is defined as a **rise** from a reference
echo taken 30 days to 3 months after implant. The prototype extract does not contain serial
echoes (see `data_plan.md`, section 3), so the rise cannot be computed. The fallback applies
the absolute-threshold arm of the same definition to a single measurement. This is weaker and
must be declared as such wherever a label built this way is used.

## Where the published definitions live

Every definition considered here — EAPCI/ESC/EACTS 2017, the VIVID staging, VARC-3, the Heart
Valve Collaboratory position and the two-tier subclinical definition — is transcribed with its
primary citation in [`../docs/research/svd_literature.md`](../docs/research/svd_literature.md)
section 2, and the published predictor effect sizes in section 3.

## What the criteria do not settle

Three questions remain open and are listed in [`open_questions.md`](open_questions.md) with
their owners: whether a later valve-in-valve counts as the outcome of the first implant, how an
ambiguous native-versus-prosthetic gradient is resolved, and whether inferred sex is used as a
covariate. None of them is encoded in code, and none should be until the clinical lead signs off.

## How many events the supplied extract contains: 5, 10 or 18

Several event counts appear across this repository, and each is correct inside its own frame.
They differ because they count different objects (patients, valve episodes or endpoint rows)
under different inclusion rules. Quoted without that frame, two of them read as a contradiction,
so this table is the single place where they are placed side by side. **No figure in this
repository should be quoted without its denominator.**

| count | what it counts | denominator | inclusion rule | produced by | published in |
|---|---|---|---|---|---|
| **5** | patients whose rule-based label is `accept` | 32 assessable labels among 117 patients | patient-level `svd_label`: a documented reintervention for a failed bioprosthesis. Haemodynamic thresholds alone give `borderline`, not `accept` | the labelling rule described in [`data_dictionary.md`](data_dictionary.md) | [`../model/modeling_brief.md`](../model/modeling_brief.md), [`data_plan.md`](data_plan.md) §4 |
| **10** | valve episodes whose follow-up ends in an SVD event | 51 modelled valve episodes | first **structural** event per episode, whatever its source (haemodynamic stage or reintervention); a patient with two valves contributes two episodes | `prep.build_follow_up`, which reads `events[events.is_structural]` and takes the earliest per episode | [`../model/approach.md`](../model/approach.md) §4 |
| **10** | structural endpoint **rows** | 117 patients, reported as 8.55 per 100 | every structural row is kept: one episode could contribute a haemodynamic-stage row *and* a reintervention row | `prep.build_events`, structural subset | [`../README.md`](../README.md), [`../model/approach.md`](../model/approach.md) §7, [`synthetic/results.md`](synthetic/results.md) |
| **18** | all candidate event rows before the structural filter | 117 patients | adds the rows whose `non_structural_evidence` is non-empty: endocarditis, valve thrombosis or a paravalvular reason, which the study rules exclude rather than count | `prep.build_events` before `is_structural` is applied | printed by [`../notebooks/02_preprocessing.ipynb`](../notebooks/02_preprocessing.ipynb) |

Read downwards, each row relaxes exactly one restriction of the row above it:

1. **5 → 10** changes the unit from the patient to the valve episode and widens the rule from
   reintervention-only to any structural event. It also drops the requirement that the patient be
   assessable at all: the 5 is counted among the 32 patients who receive a usable label, the 10
   among the 51 episodes the model pipeline builds.
2. **10 episodes → 10 rows** changes the unit from the affected episode to the endpoint row. One
   valve that deteriorates and is then reintervened is *one* affected episode and *two* rows. On
   the current extract no episode has two structural rows, so the two counts coincide, but they
   remain different quantities: the degradation ladder in
   [`synthetic/results.md`](synthetic/results.md) shows them differing by roughly a factor of two
   on every synthetic rung.
3. **10 → 18** adds back the provisionally non-structural events. Endocarditis, thrombosis and
   isolated paravalvular leak are excluded from the endpoint by the exclusion row of the table
   above. The eight rows that separate 18 from 10 (five with endocarditis or thrombosis evidence,
   three with a paravalvular reason) are exactly what that exclusion removes, and they are the rows
   most in need of clinician adjudication, because the evidence flag is set by keyword rather than
   by review.

**Which figure to quote.** When the subject is *what the extract can label*, quote the pair
"32 assessable labels from 117 patients, 5 of them failures". When the subject is *what the
model was given*, quote "51 valve episodes, 10 with an SVD event, no deaths recorded". The rate of
8.55 per 100 belongs where the extract is compared against the synthetic ladder, which counts the
same way. All of these are measured on the private extract and are therefore not reproducible from
a clone of this repository; every figure derived from the synthetic cohort is.
