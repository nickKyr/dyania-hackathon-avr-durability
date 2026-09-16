# Methods literature for building the AVR durability study from messy de-identified EHR extracts

Compiled 16 Sep 2026 for the hackathon team. Every problem number below refers to the ranked list in `docs/data_quality_issues.md`. Citation keys in square brackets point to the reference list at the end. Every reference was checked against Europe PMC or the publisher page unless it is tagged "unverified"; numbers quoted in the text come from abstracts or full texts that were opened during this review.

## Part 1. Recommended pipeline for our data

The data has two disjoint sub-cohorts, echo values only in note text, year-only shifted dates, no demographics, and a handful of true events. Nothing in the literature makes that data good, but there is a well-documented recipe for each piece.

### Step 0. Data quality audit before anything else (problems 6, 7, 8, 9, 11 to 15, 17 to 23)

Frame the audit with the Kahn harmonised terminology: conformance (value, relational, computational), completeness, and plausibility (uniqueness, atemporal, temporal), each in verification mode (against the data's own rules) or validation mode (against external knowledge) [Kahn 2016]. The OHDSI Data Quality Dashboard operationalises the same categories as named checks; the ones we can copy directly are `isPrimaryKey` (duplicate rows), `plausibleValueLow` / `plausibleValueHigh`, `plausibleUnitConceptIds`, `plausibleAfterBirth`, `plausibleBeforeDeath` and `plausibleStartBeforeEnd` [Blacketer 2021; OHDSI DQD docs]. Concretely:

- Duplicates (6): exact-row de-duplication first, then key-based de-duplication on (patient, date, analyte, value, unit). Report the before and after counts as a uniqueness-plausibility metric. No peer-reviewed paper on Epic Caboodle/Clarity duplicate rows was found; the mechanism (joins across normalised Clarity tables and repeated nightly loads) is practitioner knowledge, so we document it as such.
- Mixed labs file (7): classify rows into lab result, device interrogation, ECG, blood bank, pathology, transcription using `Lab Type`, LOINC and the component name. Parr et al. show a supervised classifier can assign LOINC codes from name, unit and value distribution with 85 to 96 percent accuracy, which is the same task at scale [Parr 2018].
- Analyte and unit harmonisation (11, 12): map every component name to one LOINC group, then normalise unit strings to UCUM and convert to one reference unit per group. Hauser published the conversion table between inter-convertible LOINC codes [Hauser 2018]; Zayed et al. released open-source R functions that standardised 96 percent of 164 million results and cut 2,019 unit strings to 381 UCUM units [Zayed 2026].
- Censored values (14): keep the numeric bound and a censoring flag. Do not substitute a constant; substitution biases estimates and the bias does not vanish with sample size [Lubin 2004]. For eGFR reported as ">60", treat the variable as ordinal (the "coarsened category" case discussed by Sun et al.) [Sun 2026].
- Abnormal flags (13): a missing flag is not "normal". Recompute against parsed reference ranges and treat unparseable ranges as missing.
- Deleted and unsigned notes (15): exclude deleted operative reports from the primary analysis and flag them; keep an audit table. Conformance rule, not a judgement call.
- Redaction vocabularies (8, 9): rewrite `<PERSON>` and `<DATE_TIME>` to `[NAME]` and `[DATE]` so one token set exists. Berg et al. found that pseudonym-style placeholders have low impact on downstream NLP, whereas deleting whole sentences has high impact, so keep the tokens in place rather than stripping them [Berg 2020]. Sweep for residual `mm/dd/yyyy`, `mm/yyyy` and serial-number patterns using the i2b2 2014 PHI categories (NAME, PROFESSION, LOCATION, AGE, DATE, CONTACT, ID) as the checklist [Stubbs & Uzuner 2015].

### Step 1. Extract echo values and prosthesis details from text (problem 2)

Two passes, then reconcile.

1. Rule-based pass. Our prosthetic-valve sentence is regular ("The peak gradient is N mmHg, the mean gradient is N mmHg and the dimensionless valve index is 0.NN"). That is exactly the situation in which regex systems reach precision above 97 percent: EchoInfer extracted 80 elements from 15,116 reports with precision 94.1 percent and recall 92.2 percent overall, and 98.1 percent precision and 94.4 percent recall for the aortic mean gradient specifically [Nath 2016]. The VA system reached precision 0.97 to 0.98 on echo reports and 0.97 to 1.0 for LVEF [Patterson 2017; Garvin 2012]. Build it in medspaCy so that the sectionizer (CONCLUSIONS block, procedure heading variants) and the ConText component come for free [Eyre 2021; Denny 2009; Harkema 2009]. Bowles et al. ran exactly this stack over 14.5 million VA echo documents and used dedicated rules to separate prosthetic from native valves [Bowles 2025].
2. LLM pass. Zero-shot prompting of a 9B to 70B open model with a JSON schema gives F1 around 0.96 for LVEF and regurgitation grades but is weak on the rare abnormal class (aortic stenosis F1 0.48 in EchoLLM, driven by 89 percent normal reports) [Chi 2025]. Llama-3-70B and Qwen2-72B with chain-of-thought reached 99 percent accuracy on valve disease severity and 99.9 to 100 percent on prosthetic valve presence, but small models fell to 54 to 86 percent on severity [Mahmoudi 2025]. Majority voting across five small open models lifted accuracy to 96.8 percent and let the team quantify disagreement as an uncertainty signal [MacKay 2025]. For numeric fields, HeartDX-LM (a fine-tuned Llama2-13b) hit 98.5 percent on continuous values in-house but only 72.4 percent on MIMIC-III continuous values, so external-format shift is the main risk [Shankar 2025].
3. Reconcile: accept when regex and LLM agree; route disagreements and regex misses to a human review queue. This is the LLM-assisted adjudication pattern in which human review is spent only on flagged cases [Marti-Castellote 2025; Schuemie 2025].
4. Validate on 50 to 100 notes dual-annotated by two team members with a third adjudicating, which is the annotation protocol EchoLLM used [Chi 2025]. Report precision, recall and F1 per field, and exact-match rate for numbers.

For prosthesis type, model and size from operative reports: the closest published analogues are rule-based extraction of implant common data elements from arthroplasty operative notes, validated across centres [Sagheb 2021; Han 2022], and GPT-based extraction from TAVR records where the valve brand was the worst-performing field (accuracy 0.657) while procedure timings and rare intra-operative events reached 1.00 [Brigiari 2026]. GPT-4 on renal operative notes showed the same pattern: categorical fields 89 to 94 percent, heterogeneously documented numbers as low as 26 percent [Hsueh 2024]. Expect brand and size to need a curated lexicon (Sapien, Evolut, CoreValve, Trifecta, Epic, Perimount, Magna, Inspiris, and the size regex `\b(1[79]|2[13579])\s?mm\b`) plus LLM fallback, and expect to hand-check them.

### Step 2. Decide which gradient belongs to which valve (problem 2, native versus prosthetic)

Assertion and temporality classification is a solved problem for negation and hypothetical status and a moderately solved one for historical status [Harkema 2009; Uzuner 2011]. Our specific ambiguity (pre-operative native gradient versus post-operative prosthetic gradient) is a target-plus-context decision, so:

- Use the sectionizer to know whether a measurement sits in a pre-operative echo summary, an operative report, or a follow-up CONCLUSIONS block.
- Use ConText-style rules with custom triggers: "prosthetic aortic valve", "bioprosthesis", "Sapien", "valve-in-valve" mark prosthetic; "native", "aortic stenosis", "calcified trileaflet" mark native; "pre-operative", "prior to surgery", "at baseline" mark historical relative to the implant. Bowles et al. show this works for the native-versus-prosthetic distinction at scale [Bowles 2025].
- If an LLM is used for this classification, fine-tuning or in-context examples matter: a LoRA-tuned LLaMA2-7B got micro F1 0.89 on the i2b2 2010 assertion set, but the same recipes dropped to 0.74 on an out-of-domain clinical corpus [Ji 2024]; a fine-tuned assertion model reached 0.962 accuracy versus 0.901 for GPT-4o [Kocaman 2025, preprint].
- Cross-check with the note's service year against the operative report year: an echo in a note dated before the operation year cannot be prosthetic.

### Step 3. Handle year-only, shifted dates (problems 3, 4)

Year-only dates make every implant-to-echo interval interval-censored: an echo in service year Y after an implant in year X occurred somewhere in (Y - X - 1, Y - X + 1) years. The methods are standard:

- Non-parametric maximum likelihood (Turnbull) and semi-parametric proportional-hazards or proportional-odds regression for interval-censored data are implemented in `icenReg` [Anderson-Bergman 2017]. Støvring and Kristiansen show a parametric survival analysis on register data that had exactly our problem (times known only to a coarse interval, plus truncation) [Støvring 2011].
- Do not midpoint-impute and run Kaplan-Meier; treat the year as the coarsest unit and use a discrete-time (person-year) hazard model if the interval-censored fit is unstable with 41 patients.
- Report actual (cumulative incidence) rather than actuarial (Kaplan-Meier) freedom from SVD, because Kaplan-Meier overstates valve failure risk in an elderly population that dies of other causes [Grunkemeier 1994; Kaempchen 2003; Grunkemeier 2007; Fine & Gray 1999].
- Explain the date shift as MIMIC does: a per-patient shift preserves within-patient intervals but not calendar alignment across patients, and the `anchor_year_group` idea (a 3-year bin for the true period) is the honest way to talk about calendar time [Johnson 2023]. Hripcsak's Shift-and-Truncate shows why edges of a shifted data set (our 2027 rows) leak and why they should be truncated [Hripcsak 2016]. Rows dated 2027 and in-text years later than the service year are inconsistencies between two shifting processes; flag them, do not repair them.

### Step 4. Define the outcome computably (problem 3, rare events)

Use a published definition rather than free-text keywords alone. VARC-3 stages haemodynamic SVD: stage 2 is a mean gradient rise of 10 mmHg or more to at least 20 mmHg with an EOA fall of 0.3 cm2 or 25 percent or more; stage 3 is a rise of 20 mmHg or more to at least 30 mmHg with an EOA fall of 0.6 cm2 or 50 percent or more [Généreux 2021; Pibarot 2022]. The 2024 ASE guideline gives cross-sectional thresholds when no baseline exists: significant prosthetic aortic stenosis at mean gradient 35 mmHg or more, DVI below 0.25, acceleration time over 100 ms; and it defines SVD as a mean-gradient increase of 20 mmHg or more to 30 mmHg or more with a paired DVI fall of 0.2 or 40 percent [Zoghbi 2024]. Earlier European and VIVID definitions are the same family [Capodanno 2017; Dvir 2018].

Build a computable phenotype in the eMERGE / PheKB sense (explicit rules over structured and NLP-derived variables, validated by chart review with PPV reported) [Newton 2013; Kirby 2016]. Suggested tiers: (a) confirmed re-intervention for failed bioprosthesis (the 6 valve-in-valve operative reports); (b) VARC-3 stage 2 or 3 by extracted gradients when a baseline exists; (c) ASE cross-sectional criteria when only one echo exists; (d) text mention of SVD or failed bioprosthesis with ConText confirming it is present, current and about the patient. No published EHR computable phenotype for SVD was found in PheKB or the literature, so this would be a contribution.

With roughly 16 events, use Firth's penalised likelihood for any logistic model and report it as such [Heinze & Schemper 2002; Puhr 2017]. Prefer descriptive cumulative incidence and case series over regression.

### Step 5. Labels: NLP silver standard plus physician adjudication (problem 3, 5)

Generate silver labels from the pipeline, then adjudicate a stratified sample. PheNorm shows phenotyping can be trained on silver labels without gold labels at all [Yu 2018]. LLM-based adjudication of structured patient profiles achieved sensitivity 78 to 98 percent and specificity 48 to 98 percent across ten diseases [Schuemie 2025]; for heart failure hospitalisation, an NLP adjudicator agreed with the clinical events committee on 83 percent of events and reached 91 percent when the 16 percent uncertain cases were sent to humans, cutting workload by 84 percent [Marti-Castellote 2025]. Local Llama 3.3 70B matched cardiologist inter-reviewer agreement for the same task [Aggarwal 2026], and a zero-shot LLM workflow found cardiovascular events in a 1,426-patient TAVR cohort with AUC 0.84 to 0.93 [Ibrahim 2026]. So: LLM proposes, a clinician on the team adjudicates the uncertain and positive cases, and we report PPV on the adjudicated set.

### Step 6. Proof of concept on public or synthetic data (problem 1)

Because no patient has labs, medications and an operative report, demonstrate the full pipeline on a proxy. ECHO-NOTE2NUM provides the raw text of 43,472 MIMIC-III echo reports with adjudicated severity labels for aortic stenosis and regurgitation, so it is the best public stand-in for our CONCLUSIONS blocks [Kwak 2024; Sci Data 2025]. Synthea's `heart/` modules include `savreplace`, `tavr`, `avrr`, `savrepair` and `cabg`, so it can generate structured SAVR/TAVR trajectories under Apache 2.0 with no access delay, though it produces no free text and no gradients [Walonoski 2018; Synthea repo]. Access to any PhysioNet credentialed set takes a CITI course, a DUA and a reviewed application, usually days to two weeks, which is outside the hackathon window unless someone already holds credentials.

## Part 2. Detailed findings

### 2.1 Extracting echo measurements and prosthesis details from text

Rule-based systems remain the reference for measurement-value pairs in echo reports because the language is formulaic.

- EchoInfer [Nath 2016] used regular expressions over structured, semi-structured and free-text sections of 15,116 reports (1,684 patients). Overall precision 94.06 percent, recall 92.21 percent, F1 93.12 percent across 80 elements on a 50-report set; on 400 physician-reviewed reports, aortic mean gradient precision 98.05 percent and recall 94.40 percent, LVEF precision 97.40 percent and recall 94.90 percent. Failures came from non-standard reporting.
- The VA system [Patterson 2017] used dictionary lookup, rules and patterns with a disambiguation step for measurement terms, reaching F 0.872, 0.844 and 0.877 on clinic notes, echo reports and radiology reports respectively, with precision 0.936 to 0.982. Its portability study across Weill Cornell, Mayo and Northwestern found high precision and recall for four concepts (aortic regurgitation, LA size, mitral and tricuspid regurgitation) and moderate to poor results for the remaining 23, varying by site [Adekkanattu 2019]. Expect the same when a regex built on one template meets another hospital's template.
- CUIMANDREef [Garvin 2012] is the canonical UIMA regex system for LVEF in VA echo reports, built for heart-failure quality measures.
- cTAKES [Savova 2010] and MedTagger (Mayo; details unverified here) are the general-purpose clinical NLP frameworks in this lineage. For a two-day build, medspaCy [Eyre 2021] is the pragmatic choice: it packages sentence splitting, a rule-based target matcher, a sectionizer descended from SecTag [Denny 2009], and a ConText implementation.
- Stress echo report interpretation with NLP [Zheng 2022] and EF/strain extraction from imaging reports [Brown 2026] are further examples of rule and hybrid systems on cardiology text (numbers not extracted here).
- Bowles et al. [2025] is the most relevant large-scale valve NLP paper: medspaCy plus ConText over 14,453,591 VA echo documents to find bicuspid aortic valve, precision 0.925, sensitivity 0.939, F1 0.932, with explicit rules distinguishing prosthetic from native valves.

LLM-based extraction has reached parity on categorical fields and is competitive on numbers when the report format is familiar.

- EchoLLM [Chi 2025]: 14 open-source models, zero-shot, JSON output, 507 institutional reports, dual annotation with adjudication. Gemma2-9b-instruct best at F1 0.965 overall; LVEF F1 0.967; aortic regurgitation F1 0.990; aortic stenosis abnormal-only F1 0.479, attributed to class imbalance.
- Mahmoudi et al. [2025] (Mayo): five open models on 1,000 reports; Llama3.0-70B and Qwen2.0-72B with chain-of-thought at 99.1 and 98.9 percent accuracy for valve disease severity and 100 and 99.9 percent for prosthetic valve presence; small models 54.1 to 85.9 percent on severity but above 96 percent on prosthetic valve detection; chain-of-thought raised per-report time from 2 to 25 seconds to 67 to 154 seconds; errors mainly from irrelevant text influencing output.
- MacKay et al. [2025]: 7,106 intra-operative TOE reports, five 7B to 13B open models (Llama2, Llama3, Mistral, Gemma, Gemma2), consensus voting; majority-vote accuracy 96.8 percent pre-surgical and 94.8 percent post-surgical for LVEF, RV function and TR categories.
- Van der Loo et al. [2025]: 1,000 TTE and 1,000 angiography reports, GPT-4o versus local open models, prompt engineering versus fine-tuning. TTE LV function accuracy 1.0, regurgitation grades 0.97 to 0.993, with human annotators at 0.993 to 1.0; the paper is explicit about class imbalance and ambiguous labels as the limiting factors.
- HeartDX-LM [Shankar 2025]: Llama2-70b generated format variants of 3,000 real TTE reports; Llama2-13b was fine-tuned to extract 18 fields including AV peak velocity, mean gradient, AVA by continuity and AVA index. Internal accuracy 98.7 percent (continuous 98.5), MIMIC-IV 91.3 percent (continuous 97.8), MIMIC-III 86.9 percent (continuous 72.4), pre-2016 in-house reports 87.1 percent. No prosthetic, PVL or DVI fields.
- Xie et al. [2026]: BioclinicalBERT and BART fine-tuned as extractive QA on 3,286 echo and 1,884 cath reports; echo accuracy 95.7 percent, F1 0.98; performance plateaued at about 1,000 training reports; weakest categories included prosthetic mitral valve.
- General LLM extraction background: InstructGPT few-shot clinical IE [Agrawal 2022]; task-specific prompts lifting GPT-3.5/4 NER on i2b2 2010 concepts [Hu 2024].

Operative notes. No paper was found that extracts prosthetic valve model and size from cardiac surgery operative reports specifically. Closest evidence:

- Rule-based extraction of implant and procedure common data elements from knee and hip arthroplasty operative notes, with multicentre validation [Sagheb 2021; Han 2022].
- GPT-based extraction from 108 TAVR patient records: accuracy from 0.657 (valve brand) to 1.00 (sex, Barthel index, procedure timings, several intra-operative complications); sensitivity 1.00 for rare intra-operative neurological events; specificity above 0.90 for most fields; Bland-Altman agreement good for vital signs [Brigiari 2026].
- GPT-4 on 1,498 renal surgery operative notes: laterality 94.4 percent, procedure 92.5, approach 89.4, estimated blood loss 77.1, ischaemia time 25.6; errors concentrated in heterogeneously documented variables [Hsueh 2024].

Implication for us: type (SAVR versus TAVR) and concomitant procedures are categorical and will extract well; model and size need a lexicon and a review pass.

### 2.2 Assertion status and temporality

- NegEx [Chapman 2001]: trigger terms, pseudo-triggers, termination terms, regex scope.
- ConText [Harkema 2009]: extends NegEx to negated, hypothetical, historical and experiencer. Good on negation and hypothetical; moderate on historical and experiencer.
- i2b2 2010 [Uzuner 2011]: assertion classes present, absent, possible, conditional, hypothetical, not associated with the patient; 21 systems submitted; corpus available via n2c2.
- i2b2 2012 [Sun 2013]: events, TIMEX and temporal relations in discharge summaries; rule-based systems dominated the top ten, best system hybrid; durations hardest.
- Section detection: SecTag [Denny 2009] recall 99.0 and precision 95.6 percent; medspaCy's sectionizer is its descendant [Eyre 2021].
- LLM assertion: LLaMA2-7B with LoRA and ChatGPT-3.5 on i2b2 2010 reached micro F1 0.89 (negated 0.98, hypothetical 0.96) but 0.74 on a private sleep-medicine corpus, with ConText at 0.72 and BERT at 0.84 on selected classes [Ji 2024]. A fine-tuned assertion model scored 0.962 accuracy against GPT-4o at 0.901, with the largest gap on hypothetical (+23.4 points) [Kocaman 2025, preprint].

For our native-versus-prosthetic problem the recommended combination is section plus sentence-level ConText with custom modifier lexicons, verified by an LLM only on the ambiguous residue.

### 2.3 De-identified text, redaction tokens and coarse dates

- MIMIC-III and MIMIC-IV shift dates per patient into 2100 to 2200, preserving within-patient intervals; MIMIC-IV adds `anchor_year_group` in 3-year bins so that calendar period can be approximated [Johnson 2016; Johnson 2023]. MIMIC-IV-Note replaces PHI with three underscores [PhysioNet MIMIC-IV-Note].
- The i2b2 2014 corpus replaced PHI with realistic surrogates and shifted dates; PHI categories are NAME, PROFESSION, LOCATION, AGE, DATE, CONTACT, ID; best de-identification system F 0.964 [Stubbs & Uzuner 2015; Stubbs, Kotfila & Uzuner 2015].
- Shift and Truncate [Hripcsak 2016] proves that shifting alone leaks at the edges of the data window and that truncation is needed to guarantee no temporal information finer than the chosen granularity. Our 2027 rows are that edge effect.
- Downstream impact [Berg 2020]: pseudonymisation has low impact on downstream NER, sentence removal high impact, and low-precision de-identification is harmful. Our bracket tokens are placeholders, so we keep them and normalise them.
- Interval censoring: `icenReg` for NPMLE and semi-parametric regression with imputation utilities [Anderson-Bergman 2017]; parametric approach for anonymised register data with truncated and interval-censored times [Støvring 2011]. Competing risks for valve durability: actual versus actuarial [Grunkemeier 1994; Kaempchen 2003; Grunkemeier 2007], Fine-Gray subdistribution hazards [Fine & Gray 1999].

### 2.4 EHR data quality frameworks

- Harmonised terminology [Kahn 2016] and the earlier review that found completeness, correctness, concordance, plausibility and currency to be the dimensions actually assessed [Weiskopf & Weng 2013]; a 2023 systematic review of tools exists [Lewis et al., JAMIA 2023;30(10):1730, PMID 37390812, not opened].
- OHDSI DQD [Blacketer 2021]: Kahn categories as ~20 check types; in the EHDEN experience it was most effective for conformance and less so for completeness and plausibility. Check names above.
- PCORnet data curation runs quarterly characterisation queries and publishes the query package [PCORnet Data Curation GitHub; Qualls et al. 2018 unverified].
- LOINC mapping [Parr 2018]; unit conversions between LOINC codes [Hauser 2018, code on GitHub]; UCUM standardisation and LOINC-group harmonisation functions [Zayed 2026]. A 2022 JAMIA paper on harmonising units and values (ocac054) appeared in search but was not opened (unverified).
- Censored lab values [Lubin 2004; Sun 2026]; Helsel's book "Nondetects and Data Analysis" (Wiley 2005) is the standard text (not opened, unverified).
- Epic Caboodle versus Clarity: only vendor and institutional documentation was found (Vanderbilt VCLIC "Epic Data Resources" page describes Caboodle as a nightly-refreshed warehouse and Clarity as the record-level source). No peer-reviewed work on duplicate rows in research extracts.

### 2.5 Small-cohort, rare-event design and phenotyping

- eMERGE validation lessons [Newton 2013]; PheKB workflow and portability [Kirby 2016]; PhEMA portability case study with PPV 90 percent or more at four sites [Pacheco et al. 2018, JAMIA 25(11):1540, authors unverified].
- Silver-standard phenotyping [Yu 2018].
- LLM adjudication [Schuemie 2025; Marti-Castellote 2025; Aggarwal 2026; Ibrahim 2026]; LLM extraction in TAVR observational research [Brigiari 2026].
- SVD definitions [Capodanno 2017; Dvir 2018; Généreux 2021; Pibarot 2022; Zoghbi 2009; Zoghbi 2024]. A single-centre 5-year valve-in-valve registry illustrates the registry-based SVD cohort design our 6 ViV patients resemble [Schamroth Pravda 2021].
- Rare events: Firth penalisation [Firth 1993, not opened; Heinze & Schemper 2002; Puhr 2017].
- No EHR computable phenotype for bioprosthetic SVD was found on PheKB or in PubMed.

### 2.6 Public and synthetic data for a proof of concept

| Resource | What it has for us | Licence and access | Time to access |
|---|---|---|---|
| MIMIC-IV v3.1 [Johnson 2023] | Structured labs, meds, ICD, procedures; date-shifted like ours | PhysioNet Credentialed Health Data License 1.5.0; CITI course, DUA, credentialing | Days to 2 weeks |
| MIMIC-IV-Note v2.2 | 331,794 discharge summaries, 2.32 million radiology reports; no echo reports; PHI as `___` | Same | Same |
| MIMIC-IV-ECHO v0.1 | 7,243 studies, 4,579 patients, DICOM only; measurements and reports promised later | Same | Same |
| ECHO-NOTE2NUM [Kwak 2024; Sci Data 2025] | 43,472 MIMIC-III echo report texts with 19 severity variables incl. aortic stenosis and regurgitation; raw text included | Same | Same |
| MIMIC-III NOTEEVENTS [Johnson 2016] | Echo category notes (source of the above) | Same | Same |
| eICU [Pollard 2018] | ICU structured data, no useful cardiology text | Same | Same |
| EchoNet-Dynamic [Ouyang 2020] | 10,030 echo videos with EF; no text | Stanford AIMI research use agreement, non-commercial | Registration, typically quick (not verified) |
| UK Biobank [Sudlow 2015] | HES procedure codes, cardiac MRI; no echo reports | Fee-based; MTA | Average 15 weeks; applications paused until late 2026 per UKB site |
| n2c2 / i2b2 corpora | 2010 assertion, 2012 temporal, 2014 de-id | Per-user DUA via DBMI portal | Uncertain; site says new process "coming soon" |
| Synthea [Walonoski 2018] | `heart/savreplace`, `tavr`, `avrr`, `savrepair`, `cabg`, CHF modules; structured FHIR/CSV; no free text, no gradients | Apache 2.0 | Immediate |

For a hackathon proof of concept the realistic path is Synthea for structured trajectories plus LLM-generated synthetic notes seeded from those trajectories (the report-variant generation trick in Shankar 2025), with ECHO-NOTE2NUM as the benchmark if anyone on the team already has PhysioNet credentials. Note PhysioNet's responsible-use terms restrict sending credentialed data to third-party LLM APIs; check the current policy before any cloud model call.

## Part 3. References

Tag: [V] metadata verified via Europe PMC or publisher page during this review; [V-abstract] abstract also read; [U] unverified or not opened.

- Adekkanattu P, Jiang G, Luo Y, et al. Evaluating the portability of an NLP system for processing echocardiograms: a retrospective, multi-site observational study. AMIA Annu Symp Proc 2019;2019:190-199. PMID 32308812. arXiv 1905.01961. [V]
- Aggarwal R, Oseran AS, Manrai AK, et al. Performance of local large language models for adjudicating heart failure hospitalizations. Circulation 2026;153(22):1785-1787. DOI 10.1161/CIRCULATIONAHA.126.079166. [V]
- Agrawal M, Hegselmann S, Lang H, Kim Y, Sontag D. Large language models are few-shot clinical information extractors. Proc EMNLP 2022:1998-2022. https://aclanthology.org/2022.emnlp-main.130/ [V]
- Anderson-Bergman C. icenReg: regression models for interval censored data in R. J Stat Softw 2017;81(12):1-23. DOI 10.18637/jss.v081.i12. [V]
- Berg H, Henriksson A, Dalianis H. The impact of de-identification on downstream named entity recognition in clinical text. Proc LOUHI 2020. https://aclanthology.org/2020.louhi-1.1/ [V]
- Blacketer C, Defalco FJ, Ryan PB, Rijnbeek PR. Increasing trust in real-world evidence through evaluation of observational data quality. J Am Med Inform Assoc 2021;28(10):2251-2257. DOI 10.1093/jamia/ocab132. [V] DQD check descriptions: https://ohdsi.github.io/DataQualityDashboard/articles/CheckTypeDescriptions.html [V]
- Bowles et al. Detecting bicuspid aortic valve from echocardiographic reports using natural language processing: a Veterans Affairs study. JACC Adv 2025. DOI 10.1016/j.jacadv.2025.102463. PMC12869887. [V]
- Brigiari G, Dotto R, Cernetti C, Gregori D, Lorenzoni G. From theory to practice: GPT-supported data extraction in observational studies on transcatheter aortic valve replacement. JACC Adv 2026:102871. DOI 10.1016/j.jacadv.2026.102871. PMID 42275684. [V-abstract]
- Brown SA, et al. Leveraging natural language processing artificial intelligence for automated data extraction of ejection fraction and strain from cardiovascular imaging reports. Am Heart J Plus 2026;67:100799. DOI 10.1016/j.ahjo.2026.100799. [V, content not read]
- Capodanno D, Petronio AS, Prendergast B, et al. Standardized definitions of structural deterioration and valve failure in assessing long-term durability of transcatheter and surgical aortic bioprosthetic valves: EAPCI consensus statement endorsed by ESC and EACTS. Eur Heart J 2017;38(45):3382-3390. DOI 10.1093/eurheartj/ehx303. [V]
- Chapman WW, Bridewell W, Hanbury P, Cooper GF, Buchanan BG. A simple algorithm for identifying negated findings and diseases in discharge summaries. J Biomed Inform 2001;34(5):301-310. DOI 10.1006/jbin.2001.1029. [V]
- Chi J, Rouphail Y, Hillis E, et al. EchoLLM: extracting echocardiogram entities with light-weight, open-source large language models. JAMIA Open 2025;8(4):ooaf092. DOI 10.1093/jamiaopen/ooaf092. [V, full text read]
- Denny JC, Spickard A, Johnson KB, Peterson NB, Peterson JF, Miller RA. Evaluation of a method to identify and categorize section headers in clinical documents. J Am Med Inform Assoc 2009;16(6):806-815. DOI 10.1197/jamia.M3037. [V]
- Dvir D, et al. (VIVID). Standardized definition of structural valve degeneration for surgical and transcatheter bioprosthetic aortic valves. Circulation 2018;137(4):388-399. DOI 10.1161/CIRCULATIONAHA.117.030729. PMID 29358344. [V, pages unverified]
- Eyre H, Chapman AB, Peterson KS, et al. Launching into clinical space with medspaCy: a new clinical text processing toolkit in Python. AMIA Annu Symp Proc 2021. arXiv 2106.07799. https://github.com/medspacy/medspacy [V]
- Fine JP, Gray RJ. A proportional hazards model for the subdistribution of a competing risk. J Am Stat Assoc 1999;94(446):496-509. DOI 10.1080/01621459.1999.10474144. [U, standard reference, not opened]
- Firth D. Bias reduction of maximum likelihood estimates. Biometrika 1993;80(1):27-38. DOI 10.1093/biomet/80.1.27. [U, standard reference, not opened]
- Garvin JH, DuVall SL, South BR, et al. Automated extraction of ejection fraction for quality measurement using regular expressions in UIMA for heart failure. J Am Med Inform Assoc 2012;19(5):859-866. DOI 10.1136/amiajnl-2011-000535. [V]
- Généreux P, et al. Valve Academic Research Consortium 3: updated endpoint definitions for aortic valve clinical research. J Am Coll Cardiol 2021;77(21):2717-2746. DOI 10.1016/j.jacc.2021.02.038. [V DOI, pages unverified]
- Grunkemeier GL, Jamieson WR, Miller DC, Starr A. Actuarial versus actual risk of porcine structural valve deterioration. J Thorac Cardiovasc Surg 1994;108(4):709-718. DOI 10.1016/S0022-5223(94)70298-5. PMID 7934107. [V]
- Grunkemeier GL, Jin R, Eijkemans MJ, Takkenberg JJ. Actual and actuarial probabilities of competing risks: apples and lemons. Ann Thorac Surg 2007;83(5):1586-1592. DOI 10.1016/j.athoracsur.2006.11.044. [V]
- Han P, Fu S, Kolis J, et al. Multicenter validation of natural language processing algorithms for the detection of common data elements in operative notes for total hip arthroplasty. JMIR Med Inform 2022;10:e38155. DOI 10.2196/38155. [V]
- Harkema H, Dowling JN, Thornblade T, Chapman WW. ConText: an algorithm for determining negation, experiencer, and temporal status from clinical reports. J Biomed Inform 2009;42(5):839-851. DOI 10.1016/j.jbi.2009.05.002. [V]
- Hauser RG, Quine DB, Ryder A, Campbell S. Unit conversions between LOINC codes. J Am Med Inform Assoc 2018;25(2):192-196. DOI 10.1093/jamia/ocx056. Code: https://github.com/hauserrg/LOINC_Unit_Conversions [V]
- Heinze G, Schemper M. A solution to the problem of separation in logistic regression. Stat Med 2002;21(16):2409-2419. DOI 10.1002/sim.1047. [V]
- Hripcsak G, Mirhaji P, Low AF, Malin BA. Preserving temporal relations in clinical data while maintaining privacy. J Am Med Inform Assoc 2016;23(6):1040-1045. DOI 10.1093/jamia/ocw001. [V-abstract]
- Hsueh JY, Nethala D, Singh S, et al. Exploring the feasibility of GPT-4 as a data extraction tool for renal surgery operative notes. Urol Pract 2024;11(5):782-789. DOI 10.1097/UPJ.0000000000000599. [V]
- Hu Y, Chen Q, Du J, et al. Improving large language models for clinical named entity recognition via prompt engineering. J Am Med Inform Assoc 2024;31(9):1812-1820. DOI 10.1093/jamia/ocad259. [V]
- Ibrahim O, Farina J, Pereyra Pietri M, et al. Diagnostic accuracy of electronic medical record retrieval methods and a large language model for identifying cardiovascular events: a multisite retrospective validation study. BMJ Open 2026;16(8):e116133. DOI 10.1136/bmjopen-2025-116133. [V-abstract]
- Ji Y, Yu Z, Wang Y. Assertion detection in clinical natural language processing using large language models. Proc IEEE ICHI 2024. DOI 10.1109/ICHI61247.2024.00039. PMC11908446. [V, full text read]
- Johnson AEW, Pollard TJ, Shen L, et al. MIMIC-III, a freely accessible critical care database. Sci Data 2016;3:160035. DOI 10.1038/sdata.2016.35. [V]
- Johnson AEW, Bulgarelli L, Shen L, et al. MIMIC-IV, a freely accessible electronic health record dataset. Sci Data 2023;10:1. DOI 10.1038/s41597-022-01899-x. [V] PhysioNet pages for MIMIC-IV, MIMIC-IV-Note v2.2 and MIMIC-IV-ECHO v0.1 read directly.
- Kaempchen S, Guenther T, Toschke M, Grunkemeier GL, Wottke M, Lange R. Assessing the benefit of biological valve prostheses: cumulative incidence (actual) vs. Kaplan-Meier (actuarial) analysis. Eur J Cardiothorac Surg 2003;23(5):710-713. DOI 10.1016/S1010-7940(03)00081-2. [V]
- Kahn MG, Callahan TJ, Barnard J, et al. A harmonized data quality assessment terminology and framework for the secondary use of electronic health record data. EGEMS 2016;4(1):1244. DOI 10.13063/2327-9214.1244. [V]
- Kirby JC, Speltz P, Rasmussen LV, et al. PheKB: a catalog and workflow for creating electronic phenotype algorithms for transportability. J Am Med Inform Assoc 2016;23(6):1046-1052. DOI 10.1093/jamia/ocv202. [V]
- Kocaman V, Gul Y, Kaya MA, Haq HU, Butgul M, Celik C, Talby D. Beyond negation detection: comprehensive assertion detection models for clinical NLP. arXiv 2503.17425, 2025. [V, preprint]
- Kwak GH, Moukheiber D, Moukheiber M, et al. EchoNotes Structured Database derived from MIMIC-III (ECHO-NOTE2NUM) v1.0.0. PhysioNet 2024. DOI 10.13026/xhrz-ht59. Companion paper: Large open access database of echocardiogram reports in intensive care unit patients. Sci Data 2025. DOI 10.1038/s41597-025-04849-5. [V PhysioNet page; Sci Data authors not checked]
- Lubin JH, Colt JS, Camann D, et al. Epidemiologic evaluation of measurement data in the presence of detection limits. Environ Health Perspect 2004;112(17):1691-1696. DOI 10.1289/ehp.7199. [V]
- MacKay EJ, et al. Automated structured data extraction from intraoperative echocardiography reports using large language models. Br J Anaesth 2025;134(5):1308-1317. DOI 10.1016/j.bja.2025.01.028. [V, full text read]
- Mahmoudi E, Vahdati S, Chao CJ, et al. A comparative analysis of privacy-preserving large language models for automated echocardiography report analysis. J Am Med Inform Assoc 2025;32(7):1120-1129. DOI 10.1093/jamia/ocaf056. [V-abstract]
- Marti-Castellote PM, Reeder C, Claggett B, et al. Natural language processing to adjudicate heart failure hospitalizations in global clinical trials. Circ Heart Fail 2025;18(1):e012514. DOI 10.1161/CIRCHEARTFAILURE.124.012514. [V-abstract]
- Nath C, Albaghdadi MS, Jonnalagadda SR. A natural language processing tool for large-scale data extraction from echocardiography reports. PLoS One 2016;11(4):e0153749. DOI 10.1371/journal.pone.0153749. [V, full text read]
- Newton KM, Peissig PL, Kho AN, et al. Validation of electronic medical record-based phenotyping algorithms: results and lessons learned from the eMERGE network. J Am Med Inform Assoc 2013;20(e1):e147-e154. DOI 10.1136/amiajnl-2012-000896. [V]
- Ouyang D, He B, Ghorbani A, et al. Video-based AI for beat-to-beat assessment of cardiac function. Nature 2020;580:252-256. DOI 10.1038/s41586-020-2145-8. Dataset: https://echonet.github.io/dynamic/ [V DOI; pages unverified]
- Pacheco JA, et al. A case study evaluating the portability of an executable computable phenotype algorithm across multiple institutions and electronic health record environments. J Am Med Inform Assoc 2018;25(11):1540-1546. https://academic.oup.com/jamia/article/25/11/1540/5075388 [U, authors and DOI not verified]
- Parr SK, Shotwell MS, Jeffery AD, Lasko TA, Matheny ME. Automated mapping of laboratory tests to LOINC codes using noisy labels in a national electronic health record system database. J Am Med Inform Assoc 2018;25(10):1292-1300. DOI 10.1093/jamia/ocy110. [V]
- Patterson OV, Freiberg MS, Skanderson M, Fodeh SJ, Brandt CA, DuVall SL. Unlocking echocardiogram measurements for heart disease research through natural language processing. BMC Cardiovasc Disord 2017;17(1):151. DOI 10.1186/s12872-017-0580-8. [V-abstract]
- Pibarot P, Herrmann HC, Wu C, et al. Standardized definitions for bioprosthetic valve dysfunction following aortic or mitral valve replacement: JACC state-of-the-art review. J Am Coll Cardiol 2022;80(5):545-561. DOI 10.1016/j.jacc.2022.06.002. [V]
- Pollard TJ, Johnson AEW, Raffa JD, Celi LA, Mark RG, Badawi O. The eICU Collaborative Research Database. Sci Data 2018;5:180178. DOI 10.1038/sdata.2018.178. [V]
- Puhr R, Heinze G, Nold M, Lusa L, Geroldinger A. Firth's logistic regression with rare events: accurate effect estimates and predictions? Stat Med 2017;36(14):2302-2317. DOI 10.1002/sim.7273. [V]
- Sagheb E, Ramazanian T, Tafti AP, et al. Use of natural language processing algorithms to identify common data elements in operative notes for knee arthroplasty. J Arthroplasty 2021;36(3):922-926. DOI 10.1016/j.arth.2020.09.029. [V]
- Savova GK, Masanz JJ, Ogren PV, et al. Mayo clinical Text Analysis and Knowledge Extraction System (cTAKES): architecture, component evaluation and applications. J Am Med Inform Assoc 2010;17(5):507-513. DOI 10.1136/jamia.2009.001560. [V]
- Schamroth Pravda N, Kornowski R, Levi A, et al. 5 year outcomes of patients with aortic structural valve deterioration treated with transcatheter valve in valve: a single center prospective registry. Front Cardiovasc Med 2021;8:713341. DOI 10.3389/fcvm.2021.713341. [V]
- Schuemie MJ, Ostropolets A, Zhuk A, et al. Standardized patient profile review using large language models for case adjudication in observational research. NPJ Digit Med 2025;8(1):18. DOI 10.1038/s41746-025-01433-4. [V-abstract]
- Shankar SV, Dhingra LS, Aminorroaya A, et al. Automated transformation of unstructured cardiovascular diagnostic reports into structured datasets using sequentially deployed large language models. Eur Heart J Digit Health 2025;6:783-796. DOI 10.1093/ehjdh/ztaf030. [V, full text read via PMC12282380]
- Støvring H, Kristiansen IS. Simple parametric survival analysis with anonymized register data: a cohort study with truncated and interval censored event and censoring times. BMC Res Notes 2011;4:308. DOI 10.1186/1756-0500-4-308. [V]
- Stubbs A, Uzuner Ö. Annotating longitudinal clinical narratives for de-identification: the 2014 i2b2/UTHealth corpus. J Biomed Inform 2015;58 Suppl:S20-S29. DOI 10.1016/j.jbi.2015.07.020. [V]
- Stubbs A, Kotfila C, Uzuner Ö. Automated systems for the de-identification of longitudinal clinical narratives: overview of 2014 i2b2/UTHealth shared task Track 1. J Biomed Inform 2015;58 Suppl:S11-S19. DOI 10.1016/j.jbi.2015.06.007. [V]
- Sudlow C, Gallacher J, Allen N, et al. UK Biobank: an open access resource for identifying the causes of a wide range of complex diseases of middle and old age. PLoS Med 2015;12(3):e1001779. DOI 10.1371/journal.pmed.1001779. [V] Access timing from UK Biobank community FAQ pages (about 15 weeks average).
- Sun S, Mas VR, Archer KJ. Penalized cumulative probability model for a continuous outcome subject to detection limits. Stat Med 2026;45(20-22):e70723. DOI 10.1002/sim.70723. [V, content from abstract snippet only]
- Sun W, Rumshisky A, Uzuner Ö. Evaluating temporal relations in clinical text: 2012 i2b2 Challenge. J Am Med Inform Assoc 2013;20(5):806-813. DOI 10.1136/amiajnl-2013-001628. [V]
- Synthea. Walonoski J, Kramer M, Nichols J, et al. Synthea: an approach, method, and software mechanism for generating synthetic patients and the synthetic electronic health care record. J Am Med Inform Assoc 2018;25(3):230-238. DOI 10.1093/jamia/ocx079. [V] Repository https://github.com/synthetichealth/synthea (Apache 2.0; `src/main/resources/modules/heart/` contains `savreplace`, `tavr`, `avrr`, `savrepair`, `cabg` folders; module contents not inspected).
- Uzuner Ö, South BR, Shen S, DuVall SL. 2010 i2b2/VA challenge on concepts, assertions, and relations in clinical text. J Am Med Inform Assoc 2011;18(5):552-556. DOI 10.1136/amiajnl-2011-000203. [V]
- van der Loo W, van der Valk V, van den Broek T, Atsma D, Staring M, Scherptong R. Large language models for structured cardiovascular data extraction: a foundation for scalable research and clinical applications. Eur Heart J Digit Health 2025/2026;7(2):ztaf127. DOI 10.1093/ehjdh/ztaf127. [V, full text read]
- Weiskopf NG, Weng C. Methods and dimensions of electronic health record data quality assessment: enabling reuse for clinical research. J Am Med Inform Assoc 2013;20(1):144-151. DOI 10.1136/amiajnl-2011-000681. [V]
- Xie F, Lee MS, Chen W, Phan DQ. Converting unstructured cardiac catheterization and echocardiography reports into structured data using transformer-based language models. JAMIA Open 2026;9(2):ooag036. DOI 10.1093/jamiaopen/ooag036. [V-abstract]
- Yu S, Ma Y, Gronsbell J, et al. Enabling phenotypic big data with PheNorm. J Am Med Inform Assoc 2018;25(1):54-60. DOI 10.1093/jamia/ocx111. [V]
- Zayed AM, Sarikakis I, Delvaux N. Automated standardization and harmonization of laboratory units in large-scale clinical data using open-source R functions. Int J Med Inform 2026;205:106131. DOI 10.1016/j.ijmedinf.2025.106131. [V-abstract]
- Zheng C, Sun BC, Wu YL, et al. Automated interpretation of stress echocardiography reports using natural language processing. Eur Heart J Digit Health 2022;3(4):626-637. DOI 10.1093/ehjdh/ztac047. [V, content not read]
- Zoghbi WA, Chambers JB, Dumesnil JG, et al. Recommendations for evaluation of prosthetic valves with echocardiography and Doppler ultrasound. J Am Soc Echocardiogr 2009;22(9):975-1014. DOI 10.1016/j.echo.2009.07.013. [V]
- Zoghbi WA, Jone PN, Chamsi-Pasha MA, et al. Guidelines for the evaluation of prosthetic valve function with cardiovascular imaging: a report from the ASE developed in collaboration with SCMR and SCCT. J Am Soc Echocardiogr 2024;37(1):2-63. DOI 10.1016/j.echo.2023.10.004. [V] Thresholds quoted via Graham F, Dobbin S, Sooriyakanthan M, Tsang W. Struct Heart 2025;9(4):100372. DOI 10.1016/j.shj.2024.100372. [V]

Not found despite targeted searches: a peer-reviewed NLP paper on cardiac-surgery operative reports for valve model and size; a published EHR computable phenotype for bioprosthetic SVD; peer-reviewed work on duplicate rows in Epic Caboodle/Clarity research extracts. Med-PaLM was not pursued because no extraction benchmark relevant to echo or operative text was found for it.
