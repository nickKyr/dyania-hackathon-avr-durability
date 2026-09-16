# Docathon briefing for the clinical members of the team

The Docathon is **20% of our final score** and it is the one component the engineers cannot
help with on the day: it is a physician-only sprint in which our clinicians take the role
Synapsis AI normally plays, answering precise questions about real clinical notes, scored
against the model's benchmark. This briefing is what we know about the format and how to
read for it. Nothing here is medical instruction — every reader of this page knows more
cardiology than the person who wrote it. What it offers is the *reading discipline* the
format rewards, which is not the same discipline that clinical practice rewards.

Every example below is **invented for this briefing**. No text from the supplied extract
appears here, and none may be added to this page.

---

## 1. What the task is

Dyania's product answers one clinical question at a time over a patient's whole longitudinal
record, and returns, per question, one of four labels with a justification that points at the
passage supporting it:

| label | meaning |
|---|---|
| **accept** | the record states that the criterion is met |
| **reject** | the record states that the criterion is not met |
| **borderline** | the record addresses the criterion but the answer sits on the boundary, or the evidence conflicts |
| **missing information** | the record does not address the criterion at all |

In their published Cleveland Clinic work, 32 trial eligibility criteria were decomposed into
77 questions in 9 categories and answered this way across 1,476 patients. The Docathon puts a
physician in that seat. Expect **assertion-style questions** — was this present, absent,
historical, planned, uncertain, or not mentioned — rather than "summarise this note".

**The distinction that decides most questions:** *reject* and *missing information* are not the
same answer. "Echocardiography showed no paravalvular leak" is a reject. Silence about
paravalvular leak is missing information. In ordinary clinical reasoning both lead to the same
action; here they are different answers and only one of them is right.

## 2. What the score realistically is

The benchmark quoted for the model is ~95.7% (the melanoma abstract). At Dyania's 2024
Docathon, held in Athens in February 2025 with medical students, residents, rural physicians
and pharmacists competing, **the winner scored 80.9%**, second 80.0%, third 79.1%.

So the human ceiling in this format is about 80%, and the spread between competitors will not
come from medical knowledge — everyone in the room has it — but from disciplined reading of
what the note actually says. Losing points happens in a predictable way: the clinician answers
the question the patient poses instead of the question the note answers.

## 3. The six traps, in the order they cost points

**1. Clinical plausibility.** The single biggest source of error. If a note describes a
78-year-old with a bioprosthetic valve and a mean gradient of 45 mmHg, it is almost certain
that the patient has structural deterioration — and if the note does not say so, the answer is
still *missing information*. **Answer from the text, never from what must be true.**

**2. Negation and its scope.** "No evidence of endocarditis or abscess" negates both. "Chest
pain without radiation, with dyspnoea" negates only the radiation. Read to the end of the
sentence before deciding what was ruled out, and check whether the negation belongs to the
finding or to a symptom of it.

**3. Timing.** Questions frequently carry a window: *at the time of the index operation*,
*within six months*, *since the implant*. A true statement in the wrong window is a wrong
answer. Two specific patterns: a history section describes what was true years ago, and a plan
section describes what has not happened yet. "Scheduled for valve-in-valve TAVR" is not a
reintervention; it is a plan.

**4. Assertion status other than present or absent.** "Cannot exclude", "suspected",
"possible", "raises the question of" are hedges, and in this scheme they are usually
*borderline*, not *accept*. "Resolved" and "status post" are historical, not current.

**5. Attribution.** Whose finding is it, and which valve is it? Family history is not patient
history. In an aortic valve report a gradient may belong to the mitral valve, to the native
valve before the operation, or to the prosthesis. Copy-forward text reproduces last month's
assessment verbatim inside today's note, so a finding can appear "today" while belonging to an
earlier encounter — check whether the paragraph has its own date.

**6. Thresholds and units.** Where a question names a numeric criterion, apply it literally:
mean gradient ≥ 20 mmHg means 19 mmHg is a reject, not a borderline. Watch peak versus mean
gradient, cm² versus indexed cm²/m², and percentages against absolute changes.

## 4. A checklist to run per question

Spend the first pass locating, the second deciding. For each question:

1. **What exactly is being asked?** Rewrite it in your head as a yes/no proposition.
2. **Does the note address it at all?** If not → *missing information*. Do not go looking for
   it in your clinical knowledge.
3. **Where is the sentence that addresses it?** That sentence — not the impression, not the
   diagnosis list — is the evidence.
4. **Is it negated?** Read the full clause.
5. **Is it in the asked-for window, and is it this patient's, this valve's, and current?**
6. **Is it hedged?** Hedged and boundary values → *borderline*.
7. **Could you point at the passage and have a colleague agree without reading the rest of the
   chart?** That is the standard Dyania holds their own justifications to; it is a good test
   of an answer.

## 5. Worked examples

All invented. The point of each is the gap between the clinical reading and the textual one.

| what the note says | question | answer | why |
|---|---|---|---|
| "Status post bioprosthetic AVR 2019. No prosthetic dysfunction on the most recent study." | Does the patient have structural valve deterioration? | reject | Addressed and denied. |
| "Bioprosthetic AVR 2019. Echo: mean gradient 38 mmHg, DVI 0.22." | Does the patient have structural valve deterioration? | missing information (or borderline if the question names the thresholds) | The numbers meet the usual criteria, but the note does not assert deterioration. If the question is phrased numerically, answer the numbers; if it asks what the note concludes, the note concludes nothing. |
| "Echo pending; clinical suspicion of prosthetic stenosis." | Is prosthetic stenosis present? | borderline | Suspicion is a hedge, not a finding. |
| "Family history of aortic valve replacement." | Has the patient had an AVR? | missing information | Wrong subject. |
| "Redo AVR discussed with the patient; will proceed if symptoms progress." | Has a reintervention occurred? | reject or missing information depending on the wording of the question | A plan is not an event. |
| "Endocarditis 2021, treated, resolved." | Active endocarditis at this encounter? | reject | Explicitly historical and resolved. |
| "Mean gradient across the prosthesis 19 mmHg." | Is the mean gradient ≥ 20 mmHg? | reject | Literal threshold. |
| "Moderate aortic regurgitation, paravalvular." | Is there intraprosthetic aortic regurgitation? | reject | The location makes it a different finding — and in our own study, a paravalvular leak is an exclusion rather than an endpoint. |

## 6. Practicalities

- **Budget the time.** If the questions are timed as a block, a first pass answering the
  unambiguous ones protects the score; the hedged ones are where the minutes go.
- **Do not leave blanks.** Every question has a defensible answer under this scheme, and
  *missing information* is an answer, not an abstention.
- **Be consistent.** If two questions ask about the same finding in different windows, decide
  the finding once and then apply each window to it.
- **Work note-first, not memory-first.** In the patents Dyania's own system reads the most
  recent relevant record first and walks backwards only until the criterion resolves. That is
  a good human strategy too: start at the record most likely to settle the question.

## 7. Why this is the same discipline as the rest of our submission

Our label rule for the supplied extract emits exactly these four values — `accept`, `reject`,
`borderline`, `missing information` (see [`../data/data_dictionary.md`](../data/data_dictionary.md)),
and 85 of 117 patients land in *missing information* precisely because the notes do not address
the endpoint. The same four categories are how the protocol treats the difference between a
valve that is documented as sound and a valve nobody has imaged
([`../protocol/study_protocol.md`](../protocol/study_protocol.md), section 4). The Docathon and
the repository are the same reading problem at two scales, and saying so in the pitch is worth
more than either on its own.

Sources for the format and the scores: [`research/synapsis_ai.md`](research/synapsis_ai.md),
sections 1 and 2.
