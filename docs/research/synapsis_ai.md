# Dyania Health and Synapsis AI: what the judges build, and what it implies for us

Research note for team dyanooumenoi, Dyania Health AVR durability hackathon, Athens, 15 to 18 September 2026.
All web sources were accessed on 16 September 2026 unless stated otherwise. Where a claim could not be confirmed from a primary source it is marked "unverified" or "secondhand".

## 1. Takeaways for our team

1. Dyania's entire product is question answering over messy longitudinal EHR data, mostly free text, with an auditable justification for every answer. The Cleveland Clinic J Card Fail paper shows their working method: 32 inclusion/exclusion criteria were decomposed into 77 explicit questions across 9 categories; each answer carries one of four labels (accept, reject, borderline, missing information); and every conclusion points to the note passage that supports it. Frame our label definitions, feature extraction and cohort criteria the same way. Explicit, decomposed, per criterion, with a justification trail.

2. They separate "structured only", "structured plus LLM output" and "LLM output only" criteria (10, 18 and 4 of 32 in the ATTR-CM study). Our data plan should do the same: state for each variable (mean gradient, EOA, regurgitation grade, PPM, valve type and size, implant year) whether it comes from a structured field, from note text, or from a combination, and how the note-derived ones are validated.

3. Their evaluation vocabulary is accuracy against physician ground truth, positive predictive value after human review, negative predictive value on a random sample of rejects, and time to result. They report per-question accuracy (96.2% on 7,700 questions) and per-patient range (86% to 100%). If we validate extraction of echo parameters from notes, report it in these terms and include a human-review step.

4. Human in the loop is not optional in their worldview. In every published study the physician team reviewed the AI's matches before any patient was contacted, and Schlosser repeatedly says care decisions stay between clinician and patient. Our protocol should show where a clinician confirms model output before it changes surveillance scheduling.

5. Data never leaves the hospital in their deployments (on-premise, behind the firewall, two GPUs for a 1,476-patient run). A protocol that assumes on-premise inference and federated or site-local training will read as realistic to this panel. Cloud-first designs that ship notes to an API will not.

6. They are patent holders on temporal reasoning over timestamped records: most recent record first, walk backwards until the criterion resolves, compare values across records to detect trends. Time-aware handling of serial echo measurements (gradient trajectory, not a single value) is exactly the kind of reasoning they think matters and will recognise.

7. They care about who gets found. Both Cleveland Clinic studies stress that AI screening surfaced more Black patients and more patients without a specialist connection than routine screening. A short equity or access section in the protocol (who gets missed by current echo follow-up, how the model changes that) fits their language.

8. The Docathon component (20% of score) is physicians answering the same kind of questions the model answers, scored against Synapsis AI's benchmark (95.7% in 2024; the best physician scored 80.9%). The questions are medically nuanced and derived from real notes. Our clinicians should expect assertion-style questions (was X present, absent, historical, uncertain) rather than open summarisation.

9. On the pitch: their own communication style is numbers plus a workflow story (screened N, found M, verified K, time T, compared with baseline B). The Cleveland Clinic pilots are always narrated as "AI found 30 in one week vs 14 in 90 days with routine screening". A comparable before/after framing for SVD surveillance (how many late detections, how many unnecessary echos) will land.

10. They have said in public that success depends on "how the data has been organized", especially across acquired hospitals needing normalisation, and that they prefer raw free text over pre-processed data. Naming data-quality problems we actually found in the provided extracts (year-only dates, redactions, no echo table, note duplication) and stating how we handle them is consistent with how they talk.

11. Vocabulary that matches theirs: chart review, abstraction, eligibility criteria, justification, longitudinal record, cross-data reasoning, temporal sensitivity, physician-driven, de-identified. Avoid saying the model "summarises"; Schlosser has explicitly positioned Synapsis as "very specifically not summarization".

12. Things not to overclaim in front of this panel: they know the gap between a PoC on 17 patients' labs and 215 notes and a deployable system. Be explicit about sample size, what is simulated, and what is a design rather than a result.

## 2. The product

### What Synapsis AI is

Dyania Health's website describes Synapsis AI as software that automates the reading of EMRs and lets a user "think of a question, any clinical question" and receive answers, with physicians able to "interrogate patient data with complex clinical questions about patients over time". Claims on the product page: ">95% accuracy compared to highly trained human beings doing the same task" and ">15,000x faster than a human reader". The home page phrases it as reading and interpreting an EMR in 0.5 seconds against a 30 minute human baseline, with about 95% accuracy.
Sources: https://dyaniahealth.com/synapsis-ai/ and https://dyaniahealth.com/ (accessed 2026-09-16).

The company positions the task as chart review that is "very specifically not summarization", answering specific questions to find "clinical signals" that inform care, trial eligibility and registry definitions. This wording comes from a MobiHealthNews Q&A with Schlosser; the page returned HTTP 403 to us so the quote is taken from search-engine snippets of the article and is secondhand. Source: https://www.mobihealthnews.com/news/qa-ai-platform-targets-clinical-chart-insights-beyond-llm-limits (accessed 2026-09-16, snippet only).

### Data types

Structured data (ICD-10 codes, labs, medications) and unstructured notes (physician notes, pathology, imaging reports). The Cleveland Clinic ATTR-CM study states roughly 80% of EHR data used was unstructured. Sources: https://consultqd.clevelandclinic.org/ai-can-unlock-ehr-data-to-determine-trial-eligibility ; https://dyaniahealth.com/synapsis-ai/ (accessed 2026-09-16).

### Output format and assertion status

The J Card Fail study (Cleveland Clinic, March 2026) describes per-criterion outputs of four labels: accept, reject, borderline, missing information. Patients were then grouped as complete match (all criteria met, no exclusions), partial match (all met, 1 or 2 missing) or borderline match (all met except 1 or 2 borderline). Investigators reviewed all complete, partial and borderline matches. Justifications "were judged 100% interpretable without further chart review". Source: https://consultqd.clevelandclinic.org/ai-can-unlock-ehr-data-to-determine-trial-eligibility (accessed 2026-09-16); PubMed record https://pubmed.ncbi.nlm.nih.gov/41785956/ (DOI 10.1016/j.cardfail.2026.01.010, fetched via NCBI E-utilities 2026-09-16).

The word "assertion status" does not appear in any public Dyania material we found. The closest public description is Schlosser's 2023 MedCity piece: named entity recognition "will not tell you what the clinical note is saying about prednisone (e.g., whether it was started, stopped, resumed, or whether and why the dosage was increased or decreased)". Source: https://medcitynews.com/2023/10/how-ai-can-fix-the-broken-clinical-trial-process/ (accessed 2026-09-16). So the concept is central, the term is ours.

### Deployment and compliance

"We install our software behind the healthcare system firewall in a closed-off environment, and patient data never leaves the healthcare system." One-time deployment, ongoing maintenance by Dyania, access by VPN or the hospital's access management. Small enough for on-premise or private cloud; the home page comparison scenario cites 2 GPUs. Listed as HIPAA, HITRUST and GDPR compliant. "Synapsis AI seamlessly integrates with any EMR database structure" (marketing claim, unverified). Sources: https://dyaniahealth.com/synapsis-ai/ ; https://dyaniahealth.com/ ; https://dyaniahealth.com/healthcare-systems/ (accessed 2026-09-16). Dr Martyn (Cleveland Clinic): "No data ever exited the Cleveland Clinic firewall when we were using this technology." Source: Consult QD, above.

### Workflow

Dyania's in-house clinical team analyses study protocols and prepares the system for deployment ("protocol assessment, criteria deconstruction, protocol design, and accuracy review of results before delivery"). Customers get daily pre-screening reports and can query specific clinical questions through an app ("Patient Finder"). Named use cases: trial pre-screening, registry population and reporting, observational studies, "evidence-guided care pathways" (patients misaligned with guidelines), and finding undiagnosed conditions. Sources: https://dyaniahealth.com/ ; https://dyaniahealth.com/healthcare-systems/ ; https://dyaniahealth.com/press-release/fierce-innovation-awards-winner/ (accessed 2026-09-16).

### Specialties

Oncology, cardiology, autoimmune conditions "and more" (website). Published work covers melanoma, polycythemia vera, and transthyretin amyloid cardiomyopathy (ATTR-CM). Cleveland Clinic pilots also covered neurology (movement disorders, neurodegenerative conditions). A closed job advert for part-time MD/PharmD annotators in Athens listed neurology residency as preferred. A HealthX Ventures piece describes an unnamed health system where Dyania found 488 patients with severe aortic stenosis not referred for valve replacement, around 85 of whom became eligible for intervention; we could not find any primary source for this and it is unverified beyond the investor blog. Sources: https://dyaniahealth.com/synapsis-ai/ ; https://newsroom.clevelandclinic.org/2025/08/27/cleveland-clinic-accelerates-clinical-trial-recruitment-with-roll-out-of-dyania-healths-artificial-intelligence-platform-across-health-system ; https://careers.saasventurecapital.com/companies/dyania-health/jobs/46637744-part-time-clinical-data-annotator-md-or-pharmd ; https://www.healthxventures.com/insights/buried-in-the-medical-record-how-dyanias-ai-reads-between-the-lines (all accessed 2026-09-16).

The aortic stenosis anecdote is the only public Dyania work we found in structural heart disease, which suggests the AVR durability challenge is a new area for them, drawn from the Onassis Hospital partnership named in our CLAUDE.md, rather than an existing product line.

### Customers

Cleveland Clinic is confirmed as both customer and investor. The Cleveland Clinic newsroom release of 27 August 2025 states: "Cleveland Clinic has invested in Dyania Health and may benefit financially from the sale of this technology", and describes enterprise-wide rollout across the research enterprise after pilots that began in early 2024 in oncology, cardiology and neurology. The March 2026 release repeats the disclosure and says the system was embedded in the EMR across 25 hospitals and 250 outpatient centres in Ohio, Florida and Nevada. Other customers are described only as unnamed "large US healthcare systems" and "academic medical centers". Sources: https://newsroom.clevelandclinic.org/2025/08/27/cleveland-clinic-accelerates-clinical-trial-recruitment-with-roll-out-of-dyania-healths-artificial-intelligence-platform-across-health-system ; https://newsroom.clevelandclinic.org/2026/03/03/ai-driven-chart-review-accurately-identifies-potential-rare-disease-trial-participants-in-new-study ; https://medcitynews.com/2025/08/cleveland-clinic-ai-healthcare-clinical-research/ (accessed 2026-09-16).

### Funding

- Seed, 19 September 2022: $5.3M led by Innospark Ventures, with Outsiders Fund, Wild Basin, Big Pi Ventures, Tau Ventures, Genesis Ventures and TLife Investments. Source: https://www.prnewswire.com/news-releases/dyania-health-inc-raises-5-3m-seed-to-advance-their-proprietary-and-physician-built-natural-language-processing-technology-to-drive-better-outcomes-in-clinical-research-301627579.html (accessed 2026-09-16).
- Series A, October 2024: $10M led by HealthX Ventures with Tech Square Ventures and Cleveland Clinic Ventures plus existing investors. Sources: https://dyaniahealth.com/press-release/dyania-series-a/ ; https://hitconsultant.net/2024/10/24/dyania-health-secures-10m-for-ai-powered-chart-review/ (accessed 2026-09-16).
- Total raised "around $23 million" per MobiHealthNews snippet (secondhand, unverified; the two disclosed rounds sum to $15.3M, so there may be undisclosed money).

Founding year is inconsistent across sources: 2019 (seed press release, Cleveland Clinic coverage, MedCity) versus 2020 (Series A release, HIT Consultant). Offices in Jersey City, NJ and Athens, Greece (about page). A Greek entity "Dyania Health P.C." is registered in Athens (D&B listing).

### Awards

Fierce Healthcare Innovation Award 2025, AI Solutions category (announced 19 November 2025); Fierce Healthcare DEI Award 2025; Schlosser named in Inc.'s Female Founders list 2025. Source: https://dyaniahealth.com/news/ (accessed 2026-09-16).

## 3. Technical details available publicly

### Architecture and training claims (company statements)

The product page describes three phases:
- "AI Medical Degree": pre-training on a medical knowledge library "containing over 120 billion characters".
- "AI Residency": fine-tuning on "over 25,000 annotated cases, that's over 15,000 physician hours".
- "Synapsis AI": a "physician-driven reasoning engine" post-training. Elsewhere described as "a medically pre-adapted LLM with a physician-driven algorithmic reasoning engine" with "temporal sensitivity" (job advert).
The page also says "any remaining hallucinations are identified and corrected by our experienced physicians before results are delivered", which means the marketed accuracy figure includes a human QA step.
Sources: https://dyaniahealth.com/synapsis-ai/ ; job advert above (accessed 2026-09-16).

Schlosser in interviews: the physician team writes "questions, answers, and justifications for the exact or similar tasks that the model would have to complete" (MindSea podcast). "We call it AI residency and for a disease area there were 10,000 samples ... in oncology we did 10,000 samples, in cardiology 10,000 samples" and "we hired Greek doctors who had already completed their specialty" (Outliers podcast, Greek, machine-extracted quote). The HealthX blog states a proprietary dataset of about 9 million de-identified longitudinal EMRs and that over a third of staff are physicians (investor blog, unverified). Sources: https://mindsea.com/blog/moving-digital-health-eirini-schlosser/ ; https://outliers.gr/episodes/eirini-schlosser-dyania-health-the-greek-startup-which-is-transforming-medicine ; https://www.healthxventures.com/insights/buried-in-the-medical-record-how-dyanias-ai-reads-between-the-lines (accessed 2026-09-16).

The base model family, parameter count, and whether the LLM is trained from scratch or adapted from an open model are not disclosed anywhere we found.

### Patents (the most concrete public description of the method)

Two US patents, both assigned to Dyania Health Inc, inventors Weiqi Sun, Renae (Eirini) Schlosser, George Sakkis, Jason Cannavale, both filed 27 June 2025:
- US 12,554,726 B1, "Natural language framework for contextual entity identification", granted 17 February 2026.
- US 12,566,769 B1, "Systems and methods for conserving token use with a language model for contextual entity selection", granted 3 March 2026.
Source: https://dyaniahealth.com/patents/ ; https://patents.google.com/patent/US12554726B1/en ; https://patents.google.com/patent/US12566769B1/en (accessed 2026-09-16).

What the claims describe (from the Google Patents text):
- Records are stored with timestamps and sorted in reverse chronological order. The system takes the most recent relevant record first, forms a natural-language question from the criterion, runs the LLM on that record plus the question, and only walks back to earlier records if the criterion is still unresolved. This conserves tokens and prioritises recent data.
- Criteria are converted into question sets; answers from multiple records are combined to decide whether the criterion is satisfied, including partial satisfaction (entities associated with the subset of unsatisfied criteria).
- Notes are scored for relevance to the query and only the filtered notes go into the context.
- For structured data the LLM can generate executable code to identify matching records.
- Registry use case: flag time-sensitive criteria, detect record updates, re-evaluate and update a registry.
- Hallucination mitigation via intermediate confidence scores (patent text summary; details not verified in the claims).
Neither patent discusses de-identification or deduplication.

### Peer-reviewed and conference evidence

1. Martyn T, Hanna M, Nissen SE, Patolia H, Rajendran J, Sun W, Schlosser E, Cannavale J, Bakogiannis K, Tang WHW, Vest AR, Tasopoulou O, Karathanasopoulou A, Cho L, Svensson LG, Mavi V, Gerds A, Kapadia S, Jehi L, Sarraju A. "Automating Chart Review Using an Artificial Intelligence-Enabled System for Assessing Transthyretin Amyloid Cardiomyopathy Trial Eligibility." J Card Fail, online 3 March 2026, DOI 10.1016/j.cardfail.2026.01.010, PMID 41785956. Dyania authors: Sun, Schlosser, Cannavale, Bakogiannis, Tasopoulou, Karathanasopoulou, Mavi. Disclosure: Dr Martyn receives consulting fees from Dyania Health among others. Numbers: 1,476 patients pre-filtered by amyloid-related diagnosis codes, processed in 6 days on 2 GPUs; 32 criteria to 77 questions in 9 categories; primary outcome 96.2% accuracy on 7,700 questions in 100 random patients versus physician review, per-patient 86% to 100%; 46 matches of which 43 appropriate after human review (93.4%); 198 of 200 sampled rejections correct (99% NPV); 30 recruitable patients in 7 days versus 14 by routine screening over 90 days; 29 of 30 not previously identified; 36.6% Black patients among AI-identified versus 7.1% routine. Sources: PubMed E-utilities record (2026-09-16); https://consultqd.clevelandclinic.org/ai-can-unlock-ehr-data-to-determine-trial-eligibility ; Cleveland Clinic newsroom 2026-03-03 (accessed 2026-09-16).

2. Preceding abstract: Martyn T, Hanna MA, Patolia H, et al. "Evaluating a medically trained artificial intelligence and natural language processing-enabled, large-language model in screening for transthyretin cardiac amyloidosis clinical trials." JACC 2025, ACC.25 "CardioHacks" session, 31 March 2025. DOI 10.1016/S0735-1097(25)03021-9. Page returned 403; citation from search results only. Source: https://www.jacc.org/doi/full/10.1016/S0735-1097(25)03021-9 (accessed 2026-09-16, not fetched).

3. Braley S, Kennedy LB, Isaacs J, et al. "Analysis of a large language model-based system versus manual review in clinical data abstraction and deduction from real-world medical records of patients with melanoma for clinical trial eligibility assessment." J Clin Oncol 2025;43(16_suppl):1571 (ASCO 2025). Two cohorts of 25 EMRs with 23 and 22 eligibility questions each, 1,125 questions answered by each nurse and by the LLM; ground truth by physician consensus review. Synapsis 95.73% accuracy in 2.5 minutes; melanoma-specialised nurse 95.11% in 427 minutes; oncology research nurse 88.09% in 540 minutes. Abstract page returned 403; numbers from search snippets and Cleveland Clinic press release. Source: https://ascopubs.org/doi/abs/10.1200/JCO.2025.43.16_suppl.1571 (accessed 2026-09-16, not fetched); https://www.asco.org/abstracts-presentations/252631 (403).

4. Gerds AT, et al. "Using a medically trained LLM-based end-to-end system in automating patient eligibility screening across a health system for a phase 3 study evaluating the safety of givinostat in patients with polycythemia vera." Blood 2025;146(Suppl 1):4340 (ASH 2025, 7 December 2025). Funnel: 4.7M active EMRs, 28,200 with oncology diagnosis in prior 3 years, 904 with PV, 22 eligible identified in one week (50 before trial closure), 100% PPV after research staff verification; 7 inclusion and 20 exclusion criteria; traditional method 9 pre-screened, 4 enrolled, 3 treated in 12 months. Limitations noted by ASCO Post: single institution, no sensitivity/specificity, post hoc verification. Sources: https://ashpublications.org/blood/article/146/Supplement%201/4340/550506/Using-a-medically-trained-LLM-based-end-to-end (403, citation from search) ; https://consultqd.clevelandclinic.org/ai-screening-platform-accelerates-trial-recruitment-in-polycythemia-vera ; https://ascopost.com/issues/may-10-2026/llm-tool-significantly-reduces-participant-screening-burdens-improves-enrollment-for-phase-iii-trial-in-polycythemia-vera/ (accessed 2026-09-16).

5. Mavi V, Jaroria S, Sun W. "Self-Evaluating LLMs for Multi-Step Tasks: Stepwise Confidence Estimation for Failure Detection." arXiv 2511.07364, 10 November 2025; also a NeurIPS 2025 workshop paper (OpenReview id AWL1j8u2PH). Not medical: it compares holistic versus stepwise self-evaluation for failure detection in multi-step reasoning, reporting up to 15% relative AUC-ROC improvement for stepwise scoring. Relevant because it shows the AI team's interest in per-step confidence and failure detection, which matches the patents' "intermediate confidence scores". Source: https://arxiv.org/abs/2511.07364 ; https://openreview.net/pdf?id=AWL1j8u2PH (accessed 2026-09-16).

6. Older papers listed on Dyania's publications page are Weiqi Sun's pre-Dyania NLP work (NAACL 2022 "Compositional Task-Oriented Parsing as Abstractive Question Answering"; WWW 2022 "Unfreeze with Care: Space-Efficient Fine-Tuning of Semantic Parsing Models"). Source: https://dyaniahealth.com/research/academic-publications/ (accessed 2026-09-16).

The PubMed search for "Dyania Health" affiliation returned only PMID 41785956 as a Dyania-authored paper; other hits were false positives. No medRxiv or arXiv preprints with a Dyania affiliation were found beyond item 5 (arXiv API query for "Dyania" returned nothing; the paper does not carry the affiliation in metadata).

### The "95%" figure: where it comes from

The marketed "~95%" or ">95%" is a company claim on the website. The closest primary numbers are 95.73% (melanoma, JCO 2025 abstract, 1,125 questions) and 96.2% (ATTR-CM, J Card Fail 2026, 7,700 questions), both versus physician ground truth, both in Cleveland Clinic settings, both after Dyania physicians had prepared the criteria. The Docathon page uses 95.7%, which matches the melanoma abstract. In the Outliers podcast Schlosser said "we are over 90%". Sources as above.

## 4. Events

### Docathon 2024 (held February 2025, Athens)

Dyania's page describes a "docathon" as a hackathon where "instead of coding, participants stepped into the role of a clinical expert, using the same process that powers Synapsis AI to handle complex, medically-nuanced questions". Participants (recent and current medical students, resident and rural doctors, pharmacy students and pharmacists) crafted "realistic medical cases from clinical notes" and answered "precise medical questions derived from those notes". Scores were compared with "Synapsis AI (with an accuracy rate of over 95.7%)". First place went to a gastroenterologist at 80.9% (iPad), second 80%, third 79.1% (gift cards). Source: https://dyaniahealth.com/docathon/dyania-docathon-2024/ ; LinkedIn recap https://www.linkedin.com/posts/dyaniahealth_dyania-dyaniahealth-docathon-activity-7300994151691522049-Vl26 (accessed 2026-09-16).

Implication: the Docathon score in our final grade is relative to the model. The physicians' realistic ceiling is about 80%, so the spread between teams will come from careful reading of negation, timing and missing information, not from medical knowledge alone.

### LifeHack Athens, Panathenea 2026 (27 to 29 May 2026)

36-hour life sciences hackathon at Athens LifeTech Park, Spata, run by Athens LifeTech Park with Endeavor Greece and Longevity Hacks; 60 participants, 13 teams, 22 mentors. Three tracks: Metabolic Health and Obesity (Pfizer CDI Thessaloniki), Drug Discovery (ALTP), and "Synapsis AI Docathon for liver diseases" (Dyania). The Dyania track brief: "Use ML to solve for a clinical problem in metabolic disease and test your abilities in our Docathon against our Synapsis AI." Physicians competed against Synapsis AI on 28 May for an iPad and a paid internship. Microsoft for Startups supplied Azure credits and GPU access. Dyania's prize: iPad plus one-month paid internship per team member. Winning Dyania-track team: "Dyania Challengers", "early-stage MASH detection from unstructured clinical data". A UNIC Athens press item names a first-prize team ("Designing Hepatic Patients Triage", members Vasileios Kassos, Leonidas Salikiriakis, Panagiotis Xhovalin Qazimi, Petros Moschovakos, and Dr Maria-Myrto Bakatsia) that received a three-month internship at Dyania's New Jersey headquarters and an investor pitch. Whether "Dyania Challengers" and this team are the same is not stated; the two accounts may describe the same team under different names. Judging criteria for that event were not published. Sources: https://luma.com/rquttffe ; https://www.rc.uoi.gr/index.php/nea-anakoinoseis/genika-nea/9540-lifehack-athens-may-27-28 ; https://www.panathenea.org/panathnea-2026/side-events1/longevity-hackathon/ ; https://www.unic.ac.cy/unic-athens-md-student-wins-first-prize-at-lifehack-athens-hackathon-2026/ (accessed 2026-09-16).

What the winning projects had in common with Dyania's own work: extracting a diagnosis signal (MASH, hepatic triage) from unstructured clinical text, a clinical decision output, mixed MD plus bioinformatics teams. That is the same shape as our task (extract echo and operative details from notes, predict a clinically actionable risk).

### This event (15 to 18 September 2026)

Public template repo: https://github.com/dyaniahealth/dyania-hackathon-avr-durability (fork indexed at https://github.com/claco/dyania-hackathon-avr-durability). Scoring per the repo rubric: clinical validity 25%, ML approach 25%, study design 20%, GitHub and documentation 15%, presentation 15%; overall 40% repo, 20% Docathon, 40% live pitch (from our CLAUDE.md, which reflects the organiser brief). No public announcement of the Onassis Hospital or NVIDIA involvement was found online; those come from the organiser brief only.

## 5. Public statements on data quality, de-identification, deduplication, trial recruitment

- On free text: "we work on free text, so we prefer that the data be in its raw form" (Schlosser, MindSea podcast). "On average, each note is 3,000 to 5,000 characters, so we're not talking about just one or two lines" (Outliers podcast, translated). Sources above.
- On data organisation: success depends on "how the data has been organized" more than on the EHR vendor, particularly in systems with acquired hospitals needing normalisation (Schlosser, HCI Innovation Group, August 2025). Source: https://www.hcinnovationgroup.com/clinical-it/learning-health-systems-research/article/55313949/how-cleveland-clinic-is-speeding-up-clinical-trial-recruitment (accessed 2026-09-16).
- On granularity of criteria: "medication A, but not medication B, and definitely not within the last six months" (Dr Lara Jehi, Cleveland Clinic, same source). This is the temporal and negation reasoning they consider the hard part.
- On NER versus understanding: entity recognition finds "prednisone" but "will not tell you what the clinical note is saying about prednisone (e.g., whether it was started, stopped, resumed, or whether and why the dosage was increased or decreased)" (Schlosser, MedCity News, October 2023). Source above.
- On de-identification: the 2022 seed release says the technology "de-identifies and derives clinically accurate meaning from unstructured and structured EMR-based patient data" and quotes John Chelico MD (then CMIO, CommonSpirit) on an environment that "unlocks and de-identifies unstructured patient data". Schlosser: "we do not have access to the identities of the patients, nor do we want that. We reserve that for a conversation for the physician to have with their own patient" (MindSea). In the 2023 MedCity piece she says AI tools should "review de-identified and raw medical data to find patients who are eligible". The current deployment model (on-premise, data never leaves) means de-identification is less central than in 2022.
- On deduplication and copy-forward: no public Dyania statement found. Unverified whether the pipeline dedups notes. The patents' relevance scoring and "most recent record first" approach would reduce redundant context but is not described as deduplication.
- On trial recruitment: "Fifty-five percent of all interventional trials terminated each year are terminated due to lack of patient enrollment" (MedCity 2023); "86% of studies are delayed ... about 30 to 40% are often terminated" (MindSea); manual review costs "$100 an hour and up to 30 minutes per chart" (MedCity). Cleveland Clinic: "We were only meeting 51% of our enrollment goals across our clinical trials portfolio" (Jehi, HCI Innovation Group).
- On human oversight: "The conversation about treatment options, trial participation options, and other care plan decisions should still always [be] between the clinician and the patient" (MedCity 2023). "Validation by the clinical team remained an essential component of the workflow to ensure safety and accuracy" (Cleveland Clinic 2026 release via Medical Xpress, https://medicalxpress.com/news/2026-03-ai-driven-accurately-potential-rare.html , accessed 2026-09-16).
- On generic LLMs: "currently there's no AI in the world that can effectively reason in the same way a human would" (MindSea); off-the-shelf foundation models cannot reason across a longitudinal record (HealthX blog paraphrase); "Long before large language models became mainstream, Dyania was quietly in R&D, building and annotating a massive dataset" (MedCity, August 2025).

## 6. Team

### Leadership (from https://dyaniahealth.com/about-us/ and https://theorg.com/org/dyania-health , accessed 2026-09-16)

- Eirini Schlosser, MSc, Founder and CEO. Former Morgan Stanley M&A, MIT ML certification, London Business School master's. Appears as "Renae Schlosser" on the patents. Sole listed author at MedCity News.
- Jason Cannavale, MSc, CTO. 20+ years at Flatiron Health and Rackspace; MSc Information and Cybersecurity, UC Berkeley. Patent co-inventor; co-author on the J Card Fail paper.
- Weiqi Sun, PhD, Chief AI Officer. Princeton, Bloomberg AI, Amazon Alexa AI; leads Synapsis training strategy. Lead inventor on both patents; author on J Card Fail and arXiv papers.
- George Sakkis, patent co-inventor; title not listed on the site (unverified role).
- Daniel Kadin, General Counsel, registered patent attorney.
- Zacharoula Economou, Chief of Staff (The Org).
- Katerina (Aikaterini) Karathanasopoulou, PharmD, Director of Clinical Innovations. University of Athens; Doctors Without Borders. Co-author J Card Fail.
- Olga Tasopoulou, MD, Director of Product Strategy. Internal medicine and gastroenterology, IBD research at Humanitas. Co-author J Card Fail.
- Cassandra Kosmidou, Clinical Innovations Director (The Org).
- Konstantinos Bakogiannis, Dyania Health, co-author J Card Fail; role not public.
- Shubh Jaroria, NLP Applied Scientist (MS, University at Buffalo). Vaibhav Mavi, Senior NLP Applied Scientist (MS, NYU; co-author of "Multi-hop Question Answering", FnTIR 2024). Both authors on arXiv 2511.07364; Mavi is on the J Card Fail paper.
- Advisors: Dimitrios Iliopoulos PhD MBA (co-founder per Tracxn, senior scientific advisor), Allan J. Pantuck MD (UCLA, senior medical advisor / director), Athanasios Papatsoris (Senior Medical Director, The Org), Petros Grivas (Senior Oncology Advisor, The Org), John Chelico MD (EMR integration advisor, ex Northwell CIO), Bill Theofilou.

### Hackathon contacts

- Niki Altani, technical office hours, elpiniki@dyaniahealth.com (from our CLAUDE.md). A LinkedIn profile for Elpiniki Altani lists Dyania Health as employer, Athens, education at the Technological Educational Institute of Crete (2014 to 2019), React/Redux course certificates, and activity promoting Dyania's Docathons and Forward Deployed Engineering and backend engineering roles. Title not shown. Probable match to the technical mentor; treat as an engineer rather than a clinician. Source: https://gr.linkedin.com/in/elpiniki-altani-778103164 (accessed 2026-09-16; identity match is inferred from the email local part, unverified).
- Myrto Bakatsia, clinical office hours, myrto@dyaniahealth.com (CLAUDE.md). A Dr Maria-Myrto Bakatsia, MD, was on the first-prize team at LifeHack Athens 2026 that received a Dyania internship (UNIC page above). Whether she now works at Dyania is inferred from the email domain, unverified. If correct, she recently went through the very format we are in, as a participant.
- Panagiota Kypraiou, Dyania Health, appears in search results tied to the Docathon; profile not accessible (LinkedIn 999). Unverified role.

## 7. Gaps and unverified items

- Base model, size, and training corpus composition: not public.
- Any published inter-annotator agreement or annotation guideline: not public.
- Deduplication or copy-forward handling: no public statement.
- Cleveland Clinic Ventures investment amount: not disclosed.
- "Around $23M total raised": secondhand.
- 488 aortic stenosis patients anecdote: investor blog only.
- Docathon judging beyond accuracy versus Synapsis: not published.
- LifeHack Athens Dyania-track judging criteria: not published.
- Onassis Hospital and NVIDIA roles in this event: organiser brief only, nothing online.
- Pages that blocked fetching (403 or 999): Fierce Healthcare (two articles), MobiHealthNews (two articles), JACC abstract, ASCO/JCO abstract, ASH/Blood abstract, ScienceDirect, LinkedIn company page. Numbers from those are taken from Cleveland Clinic Consult QD, Cleveland Clinic newsroom, ASCO Post, HIT Consultant, HLTH and search snippets.

## 8. Source list (all accessed 2026-09-16)

Company
- https://dyaniahealth.com/
- https://dyaniahealth.com/synapsis-ai/
- https://dyaniahealth.com/healthcare-systems/
- https://dyaniahealth.com/about-us/
- https://dyaniahealth.com/news/
- https://dyaniahealth.com/patents/
- https://dyaniahealth.com/research/academic-publications/
- https://dyaniahealth.com/docathon/dyania-docathon-2024/
- https://dyaniahealth.com/press-release/dyania-series-a/
- https://dyaniahealth.com/press-release/cleveland-clinic-dyania-health/
- https://dyaniahealth.com/press-release/fierce-innovation-awards-winner/
- https://careers.saasventurecapital.com/companies/dyania-health/jobs/46637744-part-time-clinical-data-annotator-md-or-pharmd

Patents
- https://patents.google.com/patent/US12554726B1/en
- https://patents.google.com/patent/US12566769B1/en

Publications
- https://pubmed.ncbi.nlm.nih.gov/41785956/ (J Card Fail 2026, DOI 10.1016/j.cardfail.2026.01.010)
- https://www.jacc.org/doi/full/10.1016/S0735-1097(25)03021-9 (ACC.25 abstract)
- https://ascopubs.org/doi/abs/10.1200/JCO.2025.43.16_suppl.1571 (ASCO 2025 abstract 1571)
- https://ashpublications.org/blood/article/146/Supplement%201/4340/550506/Using-a-medically-trained-LLM-based-end-to-end (ASH 2025 abstract 4340)
- https://arxiv.org/abs/2511.07364 and https://openreview.net/pdf?id=AWL1j8u2PH
- https://consultqd.clevelandclinic.org/ai-can-unlock-ehr-data-to-determine-trial-eligibility
- https://consultqd.clevelandclinic.org/ai-screening-platform-accelerates-trial-recruitment-in-polycythemia-vera
- https://ascopost.com/issues/may-10-2026/llm-tool-significantly-reduces-participant-screening-burdens-improves-enrollment-for-phase-iii-trial-in-polycythemia-vera/

Cleveland Clinic and press
- https://newsroom.clevelandclinic.org/2025/08/27/cleveland-clinic-accelerates-clinical-trial-recruitment-with-roll-out-of-dyania-healths-artificial-intelligence-platform-across-health-system
- https://newsroom.clevelandclinic.org/2026/03/03/ai-driven-chart-review-accurately-identifies-potential-rare-disease-trial-participants-in-new-study
- https://medicalxpress.com/news/2026-03-ai-driven-accurately-potential-rare.html
- https://medcitynews.com/2025/08/cleveland-clinic-ai-healthcare-clinical-research/
- https://www.hcinnovationgroup.com/clinical-it/learning-health-systems-research/article/55313949/how-cleveland-clinic-is-speeding-up-clinical-trial-recruitment
- https://hlth.com/insights/news/cleveland-clinic-dyania-health-partner-for-research-studies-2025-09-01
- https://hitconsultant.net/2025/08/27/cleveland-clinic-and-dyania-health-partner-to-accelerate-clinical-trial-recruitment-with-ai/
- https://hitconsultant.net/2024/10/24/dyania-health-secures-10m-for-ai-powered-chart-review/
- https://www.prnewswire.com/news-releases/dyania-health-inc-raises-5-3m-seed-to-advance-their-proprietary-and-physician-built-natural-language-processing-technology-to-drive-better-outcomes-in-clinical-research-301627579.html
- https://www.mobihealthnews.com/news/qa-ai-platform-targets-clinical-chart-insights-beyond-llm-limits (blocked, snippets only)
- https://www.healthxventures.com/insights/buried-in-the-medical-record-how-dyanias-ai-reads-between-the-lines

Interviews and opinion
- https://medcitynews.com/2023/10/how-ai-can-fix-the-broken-clinical-trial-process/
- https://mindsea.com/blog/moving-digital-health-eirini-schlosser/
- https://outliers.gr/episodes/eirini-schlosser-dyania-health-the-greek-startup-which-is-transforming-medicine
- https://hellenic.org/eirini-schlosser/

Events and people
- https://luma.com/rquttffe
- https://www.rc.uoi.gr/index.php/nea-anakoinoseis/genika-nea/9540-lifehack-athens-may-27-28
- https://www.panathenea.org/panathnea-2026/side-events1/longevity-hackathon/
- https://www.unic.ac.cy/unic-athens-md-student-wins-first-prize-at-lifehack-athens-hackathon-2026/
- https://www.linkedin.com/posts/dyaniahealth_dyania-dyaniahealth-docathon-activity-7300994151691522049-Vl26
- https://gr.linkedin.com/in/elpiniki-altani-778103164
- https://theorg.com/org/dyania-health
- https://github.com/dyaniahealth/dyania-hackathon-avr-durability
