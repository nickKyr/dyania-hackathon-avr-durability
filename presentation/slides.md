# Presentation: content and spoken script

> **What this file is.** The deck is built from ten HTML slides in [`slides/`](slides/), one file
> per slide on a 1920x1080 canvas. This file is the companion: what is on each slide, what is said
> over it, and where every figure comes from. It is written to be read aloud.
>
> **Rebuild the PDF** with the script in this folder. Nothing is exported by hand:
>
> ```
> python3 presentation/render_deck.py presentation/slides.pdf presentation/slides/*.html
> ```
>
> Each slide file also carries the spoken script in its `<aside>`, which the renderer hides. The
> two are kept in step: edit the slide, then update this file.

**The one sentence, if only one survives:** a bioprosthetic valve is watched by the calendar but it
does not fail by the calendar, and the patient nobody has imaged is not the patient at low risk.

---

## Timing, honestly

The ten slides are marked to 6:00 and the spoken script is about 997 words, which is closer to
seven minutes at a normal pace. The slot is five minutes. **Rehearse with a timer and cut before
the night, not during it.** The cheapest cuts, in order:

1. Slide 6, the longest script at about 139 words. The table can be pointed at rather than read.
2. Slide 3, about 126 words. Drop the sentence about how the calendar works and start at the 40%.
3. Slide 8, about 109 words. The list of what the model is not can go to questions.

Slides 2, 4, 7 and 9 carry the argument and the results. Cut those last.

---

## Slide 1: Title (0:15)

**On the slide.** The study title, team `dyanooumenoi` with the four members and their roles, the
hackathon and the date.

**Said.** "We were asked for a protocol to predict aortic valve durability. We brought three
things: a protocol, a pipeline that runs end to end, and a measurement of what the supplied data
can actually support. The third one is where our original work sits."

**If asked what the model predicts.** Among adults alive and free of valve failure after
bioprosthetic aortic valve replacement, the risk of bioprosthetic valve failure over the next five
years, with the estimate updated at every visit. Two phrases carry the design: *alive and free of
valve failure* is the landmark condition, and *updated at every visit* is what makes it dynamic.

---

## Slide 2: Structural Valve Deterioration (0:45)

**On the slide.** What deterioration is and that neither remedy is free of harm. Ten-year NOTION
outcomes: 20.8% of surgical valves deteriorated, 15.4% transcatheter, 62.7% died before any of it.
Then *How late they are found: 3 to 9 months past the window*, a four-row table contrasting the
ideal window against where patients are actually found, on NYHA class, presentation, left
ventricle and procedural urgency.

**Said.** "Structural valve deterioration is permanent leaflet change, and the only remedy is
another procedure, neither route of it clean. At ten years, one in five surgical valves and one in
seven transcatheter, and most of these patients die first, so death competes with deterioration.
Now look at how late we find them. The ideal moment to act is while the patient is still
asymptomatic, the ventricle is still normal and the repair can be planned. Where we actually find
them is class three or four, in decompensated heart failure, with a ventricle that will not
recover, operating inside forty-eight hours. Three to nine months past the window."

**Sources.** NOTION: Thyregod HGH et al., Eur Heart J 2024;45:1116-1124. The window and the state
at detection are a clinical synthesis of published reviews and case series, **not a cohort
measurement**, and the slide says so.

**If asked for a cohort measurement that supports the same point.** In 672 consecutive surgical
patients, deterioration was visible on echo in 30.1% while only 6.6% had reached the clinically
relevant threshold, and 83% of those went to reintervention (Rodriguez-Gabella T et al., J Am Coll
Cardiol 2018;71:1401-1412).

**If asked whose 62.7% that is.** The transcatheter arm. The surgical arm was 64.0%. NOTION
randomised 280 low-risk patients, mean age 79.

---

## Slide 3: Surveillance today (0:45)

**On the slide.** Deterioration is only ever seen at an echo. *How it works today:* SAVR first echo
at 1 year, TAVR often at 6 months, then annually for both, whatever the patient's risk. *Where it
breaks:* 40% of timely surveillance echos are never performed. *What late costs:* elective redo AVR
2.5% operative mortality against 4.6 to 17% urgent or emergent. Then the cost of delay in one line.

**Said.** "Here is how it works today. After surgery the first echo is at a year, after a
transcatheter valve often at six months, then annually for both, and the interval is the same
whatever the patient's risk. And here is where it breaks: those timely studies are simply not
performed in about forty per cent of patients. The cost of finding it late is the difference
between a planned operation and an emergency. Elective redo aortic valve replacement carries two
and a half per cent operative mortality. The same operation, urgent or emergent, carries four point
six to seventeen. And the cost of that delay is a fifty per cent higher long-term risk of death,
and about thirty-six thousand dollars more per patient over three years."

**Sources, and their limits.** The 40% is Circulation 2026, doi:10.1161/CIRCULATIONAHA.126.081405,
**a native aortic stenosis cohort**, quoted as the nearest published measure of whether the same
echo service delivers timely studies. Redo AVR mortality is from published surgical series. **The
cost and death-risk figures are United States estimates whose primary citations are still being
attached.** All three caveats are on the slide.

**Do not claim** that the patients who miss follow-up are the sicker ones. The published position
runs both ways: symptomatic patients get more echo, while those who stop attending may be the well
ones. The safe form of the claim is that a patient with sparse follow-up is not a low-risk patient
but an unobserved one, and it is stated as the condition on slide 4.

**If asked about inter-observer variability.** Gradients vary between readers and laboratories,
which is why the protocol measures change from the patient's own reference study rather than an
absolute level, and why external validation is scoped as a separate study.

**The rest of the economic case, if pressed.** About 22,127 dollars of the total is excess inpatient
cost, a late-presenting patient has about five times more heart failure admissions, severe
complications add 34,000 to 42,000 dollars per acute episode, and survivors carry a 24% higher risk
of a disabling stroke. Same caveat: United States estimates, citations pending.

---

## Slide 4: Hypothesis (0:35)

**On the slide.** Two proportion bars. The first is where the visits go, split low 45%, moderate
22%, high 33%, with the interval each tier receives underneath. The second is where the failures
are, split 22%, 18%, 60%. Then the mismatch in one line, and the workload: 1,000 to 483 echos per
1,000 patient-years.

**Said.** "So here is the hypothesis. Durability risk is not uniform, and it is knowable from what
the hospital already records. Estimate it at every visit. Now look at the two bars. The top bar is
where the visits go, the bottom bar is where the failures are, and they do not line up. A third of
the visits carry three fifths of the failures. That mismatch is the opportunity. Point the same
examinations at it and the workload falls from a thousand echoes per thousand patient-years to four
hundred and eighty-three."

**Define the unit unprompted.** A visit is one decision about when to image next, so the bands are
visits and not patients, and the same patient moves up a band as the valve ages.

**Why this is not circular.** If failures were spread evenly, a third of the visits would carry a
third of them. They carry three fifths.

**The evidence that the bands are real.** The observed five-year risk inside them is 7.6%, 12.9% and
28.1%, nearly fourfold from bottom to top. It is in the footnote.

**What the comparison is against.** The thousand is an annual study for every bioprosthesis, which
is what slide 3 describes as current practice. Against the sparser ACC/AHA calendar the risk-guided
schedule is 332 examinations **more**, not fewer. Which comparator is honest depends on what a given
clinic does today, so show both and claim neither as a saving.

**The condition.** The model has to see the surveillance gap as well, or it will read an unobserved
patient as a low-risk one.

**Source.** [`../model/decision_curve.md`](../model/decision_curve.md), synthetic cohort, tiers
assigned by the gradient boosting model.

---

## Slide 5: Study design (0:35)

**On the slide.** Three columns. *Population:* adults with a bioprosthetic aortic valve, SAVR or
TAVR, alive and failure-free at the reference echo 30 to 90 days after implant; risk re-estimated at
every visit out to 10 years; exclusions. *Endpoints, VARC-3:* stage 2 or worse deterioration against
the patient's own reference echo, or reintervention for structural failure, within 5 years; death is
a competing event. *What is not deterioration:* endocarditis, thrombosis and paravalvular leak
censor rather than count, 8 of 18 candidate events in the extract; mismatch is a risk factor, not an
event.

**Said.** "The endpoint is not ours, it is VARC-3, because an endpoint that does not match the
literature compares with nothing. The clock starts at the reference echo, thirty to ninety days
after implant, and the risk is re-estimated at every visit out to ten years. And what we refuse to
count matters as much: endocarditis, thrombosis and paravalvular leak all look like deterioration
and are none of it. They censor rather than count, and on this extract that removed eight of
eighteen candidate events."

**Keep the mismatch distinction straight**, because a cardiologist will test it. Patient-prosthesis
mismatch is not one of the eight. The valve was small from day one, so it never deteriorated.

**If asked about adjudication.** The code proposes, two blinded cardiologists decide, a third
settles disagreements, and kappa is reported. Say plainly that this is planned in the protocol and
that **nothing in the supplied extract has been adjudicated yet**.

**Source.** Definitions from VARC-3: Genereux P et al., Eur Heart J 2021;42:1825-1857.

---

## Slide 6: Data sources (0:40)

**On the slide.** Six sources with what we take from each and how realistic it is in deployment.
How we read the notes: rules plus language-model agents, fixed fields, each with the sentence it
came from. Then the supplied extract measured against that schema: 117 patients with dates in years,
1.62 echos each, 16% with more than one gradient, 0 deaths recorded, 10 events in 51 episodes. Then
the design decision.

**Said.** "Six data sources, and all six are already collected today. Two are harder than they look
in deployment: echo values sit as structured fields on the machine but often reach the record only
as report text, and vital status needs a registry link. We read the notes with rules plus
language-model agents that fill fixed fields and quote the sentence behind every value. Now the
extract we were given, measured against that schema. One patient in six has more than one gradient.
No deaths at all. Ten events in fifty-one scored episodes. So the extract cannot train or test a
model on its own, and that is why the models are trained, validated and tested on a synthetic cohort
built from published evidence, with the real extract scored only as a check."

**Make the last point a design decision, not an apology.** Training on the extract would fit noise.
Scoring it untouched is the stronger claim.

**The ten events** are nine reinterventions and one stage-2 deterioration seen on echo.

---

## Slide 7: Validation (0:40)

**On the slide.** How we validate: full-quality synthetic cohort of 6,000 patients; temporal split
at 2018 grouped by patient, where 88% of later implants are TAVR; tuning and recalibration inside
the training set only; competing-risk time-dependent AUC at 2, 5 and 8 years calibrated against
Aalen-Johansen; comparators. Then 5-year AUC as the mean of five draws: gradient boosting 0.76 over
all visits and 0.60 at the first visit, regression baseline 0.76 and 0.61, valve age alone 0.73 and
0.50. Then 0.60 at the first visit against 0.50 for valve age, and 6% predicted against 6.6%
observed.

**Said.** "We train, validate and test on full-quality synthetic data, six thousand patients, split
temporally at 2018 because that is where case mix turns. Metrics are competing-risk and calibrated
against Aalen-Johansen. Over all visits the model reaches an AUC of 0.76 against 0.73 for valve age
alone. The number that answers our question is the first visit: 0.60, where valve age alone gives
0.50, and the predicted risk there is about 6% against 6.6% observed. So from the very first
postoperative visit the question can be answered, modestly, and it improves as serial echoes
accumulate."

**Why train on synthetic data at all.** The extract gives 51 valve episodes and 10 events. Training
on it would fit noise.

**Source.** [`../model/approach.md`](../model/approach.md) section 4. Synthetic data, not patients.

---

## Slide 8: Model (0:35)

**On the slide.** A competing-risks survival model re-run at every visit, chained into risk at 2, 5
and 8 years. Three columns. *Why this model:* survival rather than a fixed-horizon classifier, not a
sequence model, gradient boosting primary with logistic regression as the baseline. *How we chose
the features:* clinical input first with all 42 the data can supply, automatic screening built and
rejected, the clinician-aligned 21 tested and fixed. *From risk to action:* the tier table, under
5% guideline, 5% to 15% every two years, 15% or more every year.

**Said.** "The model is a competing-risks survival model, re-run at every visit: the chance of
failure in each follow-up year, chained into risk at two, five and eight years. Survival rather than
a classifier at five years, because most patients are followed for less and a yes-or-no label would
throw them away. Not a sequence model, because most patients have one or two echoes. On features:
our clinician named them, we built all forty-two the data can supply, and the clinician-aligned list
of twenty-one won over repeated draws. And the output is not a score. It is a risk, a next echo
date, and the three factors that moved it."

**The evidence that the clinical list earns its place.** On full-quality data it lifts the
first-visit 5-year AUC from 0.54 to 0.62 for the boosted model and 0.55 to 0.64 for the baseline,
one cohort. That is the visit where valve age alone cannot separate anyone.

**Two things not on the slide.** Where the direction is known, the boosted model is constrained so a
worse value can never lower the risk. And a high-risk tier prompts review by the heart valve team;
the model sets the next echo date and never decides on reintervention.

**Why scan frequency was dropped.** How often a valve was imaged reflects how worried the clinician
was, not how the valve is doing. With it in, the boosted model learned the surveillance pattern and
ranked real valves worse than chance.

**Why the tiers are provisional.** A decision curve is read off absolute risk, and absolute risk
needs local recalibration first.

---

## Slide 9: Results (0:40)

**On the slide.** Competing-risk AUC on full-quality synthetic data over five draws at 2, 5 and 8
years: gradient boosting 0.83, 0.76, 0.76; regression baseline 0.81, 0.76, 0.76; valve age alone
0.79, 0.73, 0.71; guideline calendar 0.69, 0.67, 0.58. Every risk model beats valve age at every
horizon by 0.02 to 0.06, with a spread across draws of about 0.01. Predicted against observed
5-year risk, 18% against 15%. The SHAP ranking. Then the real extract, scored only: 0.72 regression,
0.69 boosting, 0.72 valve age against 16.6% observed.

**Said.** "Across horizons the primary model leads at two years, 0.83 against 0.79 for valve age,
and is level with the regression baseline at five and eight. Every risk model beats valve age at
every horizon, and the spread across draws is about 0.01, so those gaps are real. What drives it:
time since implant first, then whether the valve was transcatheter, then age, and younger means
higher risk. Calibration is the weak point, eighteen per cent predicted against fifteen observed.
And on the real extract, which no model ever trained on, 0.72, 0.69 and 0.72: ten events cannot
separate them, and we say so."

**Why calibration and not ranking is the defect.** A tier boundary is read off absolute risk, so
over-prediction moves patients into the wrong tier even when the ranking is right. Local
recalibration was tested on the extract and not adopted: ten events cannot fix a calibration
intercept.

**Why younger age raises risk.** A younger patient's valve is exposed to more years of calcium
turnover and the patient lives long enough to reach failure, the same pattern the surgical series
report for implants under 60.

**Source.** [`../model/approach.md`](../model/approach.md) section 4. Real extract: 51 valve
episodes, 301 landmark rows, 10 events.

---

## Slide 10: Next steps (0:30)

**On the slide.** Three columns. *What it enables:* fewer scans than yearly screening, focused on
the patients who fail, and earlier attention for the high-risk ones. *What validation needs:* 3,580
patients followed five years with about 565 failures, complete data, labels confirmed by two blinded
cardiologists. *Given three months:* one hospital's full cohort linked to death records, extraction
checked against a cardiologist's reading, the clinician's remaining factors, and fine-tuning against
more models. Then the deployment sentence.

**Said.** "What it enables is fewer scans than screening everyone yearly, pointed at the patients
who actually fail, and earlier attention for the high-risk ones. Real validation needs more data,
three and a half thousand patients followed five years, complete data with dated echoes, age and
death records, and labels confirmed by two blinded cardiologists. Given three months we would take
one hospital's full cohort linked to death records, check the extraction against a cardiologist's
reading, and add the clinician's remaining factors. And it deploys inside the hospital: no patient
data leaves the site, and it runs on standard hardware."

**The readiness answer, and give it before you are asked.** This is not ready to deploy. Nothing
here should touch a patient before a site has its own hundred local events and has recalibrated on
them.

**Source.** Sample size from [`../protocol/sample_size.md`](../protocol/sample_size.md).

---

## Panel questions to drill

| Likely question | The short answer |
|---|---|
| "Your results are on simulated data, why should we believe them?" | We do not ask you to. The real extract is scored and never trained on, and we report that no model beats valve age alone on it. The synthetic cohort is calibrated to published anchors and the generator is validated by injecting known hazard ratios and recovering them with an independent fit. |
| "You have ten events. What can you conclude?" | Very little about performance: every interval is about 0.3 wide. What ten events support is a measurement of what the data lack, which is the finding we report. |
| "Why not just follow the guideline?" | We keep it as the comparator. Below 5% predicted risk the decision curve says to do exactly that. The claim is narrower: from 5% upward a risk-guided schedule beats both scanning everyone and changing nothing. |
| "Why a mechanistic generator rather than CTGAN?" | A generative model learns the distribution you already hold. We needed structure the extract does not contain: you cannot learn a trajectory from a dataset with one trajectory per patient. |
| "Are the risks calibrated?" | Not yet for a site. On full-quality synthetic data we predict 18% against 15% observed. It is a calibration problem, not a ranking problem, and recalibration at each site updates the baseline risk without touching the coefficients. |
| "Where does the LLM fit, and do notes leave the hospital?" | The LLM abstracts notes into fixed fields with the sentence behind every value, on-premises. Notes never leave the site. |
| "What about fairness?" | No fairness claim can be made from this extract: age is redacted, sex is inferable only from pronouns, ethnicity is absent. The fairness risk specific to this endpoint is structural, because a group imaged less often looks lower-risk, so the surveillance gap is displayed beside every prediction. |

---

## Build notes

- Ten slides, one idea each. The numbers live on the slide, the sentences in the mouth.
- Every figure quoting the synthetic cohort says so on the slide itself, not only in the script.
- Three figures on slide 3 are marked as pending their primary citations. Attach them or drop them
  before the deck is shown outside the team.
- The deck is dark throughout except slides 4 and 10, which are light. That is deliberate: the
  hypothesis and the close are the two turns in the argument.
- Layout is uniform across the nine content slides: 128px top margin, 200px bottom, 36px between
  blocks, 60px headings, 26px body, footnotes 24px at 1400px wide. Slide 6 uses a 24px gap because
  it carries a seven-row table.
