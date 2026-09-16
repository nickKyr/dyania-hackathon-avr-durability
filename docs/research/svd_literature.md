# Bioprosthetic aortic valve durability: literature review for the study protocol

Compiled 16 September 2026 for the Dyania hackathon case study (predicting structural valve deterioration, SVD, after bioprosthetic SAVR or TAVR). Sources were located through PubMed, Europe PMC, publisher sites and web search. Where a full text could not be opened, the entry says so and the numbers come from the abstract or from a secondary source that is named. Nothing below is cited from memory alone without being marked as such.

Abbreviations: AR aortic regurgitation; BE balloon-expandable; BVD bioprosthetic valve dysfunction; BVF bioprosthetic valve failure; DVI Doppler velocity index; EOA effective orifice area; HALT hypoattenuated leaflet thickening; HVD hemodynamic valve deterioration; MG mean transprosthetic gradient; PPM prosthesis-patient mismatch; SE self-expanding; ViV valve-in-valve.

## 1. What this means for our protocol (one page)

**Endpoint we should adopt.** Use the VARC-3 (2021) classification [3], because it is the definition every trial and registry since 2021 uses (NOTION 10-year [9], PARTNER 2 and 3 [11, 13], CoreValve pooled analyses [14, 15], Bern registry [22], EORP registry [21], the nine-centre real-world TAVI cohort [20]). Concretely:

- Primary endpoint: time to VARC-3 stage 2 or 3 hemodynamic valve deterioration (moderate or severe HVD). Stage 2 is an increase in MG of 10 mmHg or more from the reference echo that results in MG of 20 mmHg or more, with an EOA fall of 0.3 cm2 or 25 percent or more and/or a DVI fall of 0.1 or 20 percent or more, or new or one-grade-worse intraprosthetic AR that is at least moderate. Stage 3 is an increase of 20 mmHg or more resulting in MG of 30 mmHg or more, with EOA fall of 0.6 cm2 or 50 percent or more and/or DVI fall of 0.2 or 40 percent or more, or new or two-grade-worse severe AR. Exact wording is in section 2.3. Because DVI is often missing in routine reports, NOTION used a "modified haemodynamic" VARC-3 definition without the DVI term [9]; we should pre-specify the same fallback.
- Secondary endpoints: (a) VARC-3 BVF (stage 1 clinically expressive BVD or irreversible stage 3 HVD; stage 2 reintervention; stage 3 valve-related death), (b) the continuous MG trajectory from serial echo, (c) stage 3 HVD alone as a sensitivity endpoint.
- Reference echo: the first echo 30 days to 3 months after implant (VARC-3). Salaun used a median of 4.1 months [27]; Palmerini showed the residual gradient at discharge or within 3 months predicts later SVD [23], so the reference gradient is also a predictor.
- Exclusions from SVD: endocarditis, valve thrombosis (reversible with anticoagulation), isolated PPM, isolated paravalvular leak. These are non-structural dysfunction under VARC-3 and should be coded separately, not ignored.

**Features with evidence** (details and effect sizes in section 3):
- Age at implant (strongest surgical predictor; Perimount explant for SVD at 20 years 15 percent overall vs 46 percent under age 60 [32]; freedom from SVD-reoperation at 20 years 38 percent under 60 vs 60 percent at 60 to 70 [33]).
- Valve model and generation (Mitroflow 12A/LX [35], first-generation Trifecta [37, 38], SAPIEN XT vs SAPIEN 3 [11], intra-annular vs supra-annular THV [21], BE vs SE in real-world TAVI [20]).
- Valve size, PPM and the early post-implant gradient (Flameng [31], Sénage [35], Johnston [32], Salaun [27], Del Trigo [42], O'Hair [14], Palmerini [23], EORP small-device HR 4.8 [21]).
- Renal insufficiency and dialysis, diabetes, active smoking, higher BMI (Salaun [27], Rodriguez-Gabella [26], Long meta-analysis [24], Del Trigo [42]).
- Dysmetabolic and calcium-phosphate markers: Lp-PLA2, PCSK9, insulin resistance, calcium-phosphorus product, CT leaflet calcification [28, 29, 30].
- Sex: conflicting (female sex for late HVD after SAVR [27]; male sex HR 2.17 in one TAVR cohort summarised in [6]). Keep as a candidate, do not pre-assume direction.
- Antithrombotic therapy: absence of oral anticoagulation at discharge predicts HVD after TAVR in several registries [24, 42, 43, 44], and anticoagulation reduces HALT and reduced leaflet motion (GALILEO-4D [47]); but in the Bern registry OAC was associated with more HVD [22] and in SAVR warfarin use was associated with late HVD [27]. Treat OAC as confounded by indication (atrial fibrillation, prior thrombosis) and handle it as a time-varying exposure with an active-comparator or landmark design to avoid immortal time bias [72].
- Residual AR at discharge and post-procedural PVL (Bern HR 1.87 [22]; EORP HR 3.64 [21]); THV underexpansion (sHR 4.9 [52]).
- HALT: early HALT was not associated with later SVD in the one study with 6-year follow-up [48], so treat CT leaflet findings as exploratory unless we have serial CT.

**Realistic cohort size.** Published SVD cohorts that produced stable multivariable estimates had 560 to 2,400 patients with 40 to 430 events (Flameng 564/40 [31], Sénage 561/103 [36], Rodriguez-Gabella 672 with 6.6 percent clinically relevant SVD [26], Salaun 1,387/428 HVD [27], Del Trigo 1,521/68 [42], Alaour 2,403 [22], O'Hair 4,762 [14]). Randomised trials at 5 to 10 years each had well under 100 SVD events (NOTION: 280 patients [9]). Using Riley's criteria [60] with a conservative anticipated Cox-Snell R2 of 15 percent of its maximum, an event rate of 1 to 3 per 100 patient-years and 4 to 6 years mean echo follow-up, a 15-parameter model needs roughly 1,000 to 2,400 patients and 100 to 190 events; a 25-parameter model needs 1,700 to 4,000 patients (our own calculation from the published formulas, section 5.3; must be re-run with pmsampsize once pilot rates are known). Our provided extracts (100 surgical operative notes, 17 patients with labs and medications, 6 valve-in-valve reports, no echo table) cannot support model development; they can support a proof of an extraction pipeline and an honest feasibility statement. The protocol should therefore specify a multicentre retrospective cohort of at least about 2,000 implants with a minimum of 3 years of serial echo, or a registry linkage (STS/ACC TVT, NICOR UK TAVI, EORP), and a fully external validation cohort sized per Riley 2022 [61] (target roughly 200 events for a precise calibration slope).

**Comparators.** (1) A Fine-Gray or cause-specific Cox model with the six or so established predictors (age, valve model class, valve size or indexed EOA, reference MG, renal function, diabetes) as the clinical baseline; (2) the same with the Puvimanasinghe-style age-only Weibull hazard [53] as the minimal benchmark; (3) the ML model (gradient boosted survival or a joint longitudinal-survival model using serial gradients). No published, externally validated SVD risk score exists to compare against (section 4), which is itself a selling point.

**Metrics.** Time-dependent AUC and Brier score at 3, 5 and 8 years using inverse probability of censoring weighting with death as a competing risk (Blanche [67], timeROC); calibration plots of predicted vs observed cumulative incidence at fixed horizons, with calibration slope and intercept (Wolbers [63]); Uno's C for discrimination; decision-curve net benefit for the practical decision (intensified echo surveillance). Report cumulative incidence with death as a competing event, never one minus Kaplan-Meier [62, 65]. Treat event times as interval-censored between the last normal and first abnormal echo (Turnbull or illness-death model, as in Sénage 2019 [36], Flameng [31]). Follow TRIPOD+AI [74].

## 2. Definitions

### 2.1 EAPCI/ESC/EACTS consensus 2017 (Capodanno et al.)

Source: Capodanno D, Petronio AS, Prendergast B, et al. Eur Heart J 2017;38:3382-3390, doi:10.1093/eurheartj/ehx303 [1]. Full text opened.

- SVD is intrinsic permanent change of the prosthesis (leaflet fibrosis, calcification, tear, flail, strut fracture) with morphological and/or hemodynamic dysfunction. Morphological SVD: leaflet integrity abnormality (tear or flail causing intra-frame regurgitation), leaflet structure abnormality (thickening or calcification), leaflet function abnormality (impaired mobility), strut or frame abnormality (fracture).
- Moderate hemodynamic SVD: MG 20 mmHg or more and below 40 mmHg; or MG change from baseline of 10 mmHg or more and below 20 mmHg; or moderate intra-prosthetic AR new or worsening by more than 1 grade out of 4 from baseline.
- Severe hemodynamic SVD: MG 40 mmHg or more; or MG change from baseline of 20 mmHg or more; or severe intra-prosthetic AR new or worsening by more than 2 grades out of 4 from baseline.
- BVF (any of): (1) BVD at autopsy or valve-related death; (2) aortic valve reintervention (ViV TAVI, paravalvular leak closure or redo SAVR); (3) severe hemodynamic SVD.
- Echo schedule: baseline before discharge or within 30 days, at 1 year, then annually.

### 2.2 VIVID staged definition 2018 (Dvir et al.)

Source: Dvir D, Bourguignon T, Otto CM, et al. Circulation 2018;137:388-399, doi:10.1161/CIRCULATIONAHA.117.030729 [2]. Publisher page returned HTTP 403; the abstract was read via Europe PMC and the staging table via the open-access review in Structural Heart 2023 [7], which reproduces it.

- Stage 1: morphological leaflet abnormality without hemodynamic change.
- Stage 2S (moderate stenosis): MG 20 to 40 mmHg, or MG increase of 10 to 20 mmHg from baseline with concomitant decrease in EOA and DVI.
- Stage 2R (moderate regurgitation): intraprosthetic AR of 2+ or more out of 4, new or worsened; paravalvular leak does not count.
- Stage 2RS: moderate stenosis and regurgitation together.
- Stage 3 (severe): MG 40 mmHg or more, or MG increase of 20 mmHg or more from baseline with concomitant EOA and DVI decrease, or severe AR (more than 2+ out of 4) new or worsened.
- Excluded: endocarditis, thrombosis, isolated PPM without deterioration, isolated paravalvular leak, frame distortion without abnormal leaflet function. Stages describe the valve, not the patient.

### 2.3 VARC-3 2021 (Généreux et al.)

Source: VARC-3 Writing Committee, Généreux P, Piazza N, Alu MC, et al. Eur Heart J 2021;42:1825-1857, doi:10.1093/eurheartj/ehaa799, and J Am Coll Cardiol 2021;77:2717-2746, doi:10.1016/j.jacc.2021.02.038 [3]. The EHJ page opened but was truncated before the BVD tables; the exact HVD wording below is quoted from the methods of an open-access 2026 registry paper that applied VARC-3 verbatim [45] and matches the ARTEMIS and ACASA protocols found on ClinicalTrials.gov.

BVD is an umbrella with four categories: SVD (permanent intrinsic change), non-structural valve dysfunction (PPM, paravalvular regurgitation, malposition, pannus), valve thrombosis, endocarditis.

HVD stages (compared with the post-procedural reference echo, ideally 30 days to 3 months):

- Stage 1 (morphological): leaflet thickening, calcification, HALT with or without reduced leaflet motion, without significant hemodynamic change (MG below 20 mmHg and AR less than moderate).
- Stage 2 (moderate): "an increase in mean transvalvular gradient of 10 mmHg or more resulting in mean gradient of 20 mmHg or more with a concomitant decrease in EOA of 0.3 cm2 or more or 25 percent or more and/or decrease in Doppler velocity index of 0.1 or more or 20 percent or more compared with the post-procedural echo, or new occurrence or increase of 1 grade or more of intraprosthetic AR resulting in moderate or greater AR."
- Stage 3 (severe): "an increase in mean transvalvular gradient of 20 mmHg or more resulting in a mean gradient of 30 mmHg or more with a concomitant decrease in EOA of 0.6 cm2 or more or 50 percent or more and/or decrease in Doppler velocity index of 0.2 or more or 40 percent or more, or new occurrence, or increase of 2 grades or more, of intraprosthetic AR resulting in severe AR."

Note the change from 2017: severe HVD now starts at MG 30 mmHg (not 40) provided the increase is 20 mmHg or more, and the gradient criteria require concomitant EOA or DVI decline so that a rise in gradient from higher flow is not misclassified.

BVF stages (VARC-3): Stage 1, any BVD with clinically expressive criteria (new or worsening symptoms, LV dilation, hypertrophy or dysfunction, pulmonary hypertension) or irreversible stage 3 HVD; Stage 2, aortic valve reintervention; Stage 3, valve-related death. Confirmed in the JAHA 2025 review [6] and applied in NOTION [9].

### 2.4 Heart Valve Collaboratory 2022 and later updates

Pibarot P, Herrmann HC, Wu C, et al. J Am Coll Cardiol 2022;80:545-561, doi:10.1016/j.jacc.2022.06.002 [4] (abstract read) argues that reintervention-based definitions underestimate structural BVF and that single high-gradient echo definitions overestimate it; structural BVD should require imaging confirmation of permanent leaflet change plus hemodynamic deterioration. The companion paper on bioprosthetic hemodynamics is Herrmann HC et al. J Am Coll Cardiol 2022;80:527-544, doi:10.1016/j.jacc.2022.06.001 [5]. Searches for a 2024 or 2025 VARC-4 or new consensus on SVD definitions found none; the 2025 JAHA review [6] states that VARC-3 "is likely the most robust definition of SVD and this is thus the one that should be applied in future studies". A 2024 paper reporting that current hemodynamic SVD definitions lack consistency (PMC11247222) could not be opened (reCAPTCHA) and is not cited further.

Older definitions worth knowing because registries used them: VARC-2 (2012) defined prosthetic stenosis as MG 20 mmHg or more with EOA below 0.9 to 1.1 cm2 and DVI below 0.35 [6]; Rodriguez-Gabella 2018 [26] used "subclinical SVD" (MG rise above 10 mmHg plus EOA fall above 0.3 cm2 and/or new mild or moderate AR) and "clinically relevant SVD" (MG rise above 20 mmHg plus EOA fall above 0.6 cm2 and/or new moderate to severe AR); Del Trigo [42] and the TVT registry [51] used a 10 mmHg rise alone.

## 3. Epidemiology and risk factors

### 3.1 Randomised trials, TAVR vs SAVR

- NOTION (Thyregod et al., Eur Heart J 2024;45:1116-1124, doi:10.1093/eurheartj/ehae043) [9]: 280 low-risk patients (145 CoreValve TAVI, 135 SAVR), mean age 79, STS 3.0. At 10 years: all-cause mortality 62.7 vs 64.0 percent; severe SVD (VARC-3, modified hemodynamic definition without DVI) 1.5 vs 10.0 percent (HR 0.2, 95 percent CI 0.04 to 0.7, p=0.02); moderate or severe SVD 15.4 vs 20.8 percent (HR 0.7, p=0.3); BVF 9.7 vs 13.8 percent (HR 0.7, 0.4 to 1.5, p=0.4). Echo available in 82 of 101 survivors. At 8 years (Jørgensen et al., Eur Heart J 2021;42:2912-2919, doi:10.1093/eurheartj/ehab375) [10] SVD was 13.9 vs 28.3 percent (p=0.0017) and BVF 8.7 vs 10.5 percent.
- PARTNER 2A and SAPIEN 3 registry (Pibarot et al., J Am Coll Cardiol 2020;76:1830-1843, doi:10.1016/j.jacc.2020.08.049) [11]: intermediate risk, 5-year exposure-adjusted rates per 100 patient-years: SVD 1.61 (SAPIEN XT) vs 0.63 (SAVR); SVD-related BVF 0.58 vs 0.12; all-cause BVF 0.81 vs 0.27 (all p at or below 0.01). SAPIEN 3 vs SAVR SVD 0.68 vs 0.60 (p=0.71) after propensity matching.
- PARTNER 3 (Mack et al., N Engl J Med 2023;389:1949-1960, doi:10.1056/NEJMoa2307447) [12]: low risk, 5-year BVF 3.3 percent TAVR vs 3.8 percent SAVR. Seven-year durability (Ternacle et al., JAMA Cardiol 2026, doi:10.1001/jamacardio.2026.2299) [13]: 948 implanted (495 TAVR, 453 SAVR), echo in 80 percent of survivors; BVF 6.9 vs 7.5 percent (HR 0.91); SVD-related BVF 3.9 vs 5.3 percent (HR 0.72); stage 2 or 3 HVD 7.3 vs 7.6 percent (HR 0.96); reintervention 6.0 vs 5.5 percent.
- CoreValve US Pivotal plus SURTAVI (O'Hair et al., JAMA Cardiol 2023;8:111-119, doi:10.1001/jamacardio.2022.4627) [14]: RCT pool 2,099 (1,128 TAVI, 971 SAVR) plus 2,663 non-randomised TAVI, mean age 82. SVD defined as MG increase of 10 mmHg or more to a final MG of 20 mmHg or more, or new moderate or severe intraprosthetic AR. Five-year cumulative incidence with death as competing risk 2.57 percent TAVI vs 4.38 percent SAVR; difference larger in annuli 23 mm or smaller (1.39 vs 5.86 percent). SVD was associated with all-cause mortality HR 2.03 (1.46 to 2.82), cardiovascular mortality HR 1.86 and heart failure or valve hospitalisation HR 2.17. Companion 5-year BVD analysis (Yakubov et al., J Am Coll Cardiol 2025;85, doi:10.1016/j.jacc.2025.02.009) [15]: BVD 9.7 percent TAVR vs 15.3 percent surgery (subdistribution HR 0.57, 0.45 to 0.73); BVD associated with all-cause mortality HR 1.49 and cardiovascular mortality HR 1.76.
- Evolut Low Risk 5 years (Forrest et al., J Am Coll Cardiol 2025, doi:10.1016/j.jacc.2025.03.004) [16]: 1,414 patients, mean age 74; reintervention 3.3 percent TAVR vs 2.5 percent surgery; the abstract reports "excellent" durability without stage-specific SVD rates.
- UK TAVI trial (Toff et al., JAMA 2022, PMID 35579641): 913 patients, 1-year mortality outcome only; no 5-year SVD publication was found in this search.

### 3.2 Registries and long-term TAVR series

- Long and Liu meta-analysis (J Interv Cardiol 2020, doi:10.1155/2020/4075792) [24]: 12 studies, 10,031 TAVR patients, EAPCI definition; pooled SVD 4.93 percent at 1 year and 8.97 percent at 5 years or more; severe SVD 1.75 percent long term. Predictors: valve diameter below 26 mm HR 3.57 (1.47 to 8.69); OAC at discharge OR 0.48 (0.38 to 0.61); renal dysfunction OR 1.42 (1.03 to 1.96).
- Nine-centre real-world TAVI cohort (Silva, Alperi et al., Eur Heart J Cardiovasc Imaging 2025;26:1018-1028, doi:10.1093/ehjci/jeaf083) [20]: 2,040 patients 2007 to 2020, VARC-3; 8-year SVD 13.3 percent (9.8 to 18), BVF 11.5 percent; after IPTW, SVD 5.25 percent BE vs 1.19 percent SE (HR 10.25) and BVF 6.41 vs 3.2 percent (HR 2.1) at median 4 years.
- EORP ESC Valve Durability TAVI registry (Giannini et al., EuroIntervention 2025, doi:10.4244/EIJ-D-24-00662) [21]: 597 patients, median echo follow-up 6.1 years; moderate or severe SVD 9.5 percent crude; cumulative incidence 2.4 percent at 6 years, 13.2 percent at 8 years, 33.2 percent at 10 years (the 10-year figure rests on 3.9 percent of patients). Predictors: intra-annular design HR 38.4 (10.8 to 136), small device size HR 4.82 (2.42 to 9.60), moderate or severe post-procedural PVL HR 3.64 (1.59 to 8.32).
- Bern registry (Alaour et al., JACC Cardiovasc Interv 2025, doi:10.1016/j.jcin.2024.09.039) [22]: 2,403 patients, VARC-3 moderate or severe HVD cumulative incidence 2.2 percent at 1 year, 10.8 percent at 5 years, 25.6 percent at 10 years (wide CI 17.5 to 36.5). Predictors: aortic valve complex calcium volume HR 1.81, residual AR at discharge HR 1.87, oral anticoagulants HR 1.78 (1.00 to 3.15). HVD raised reintervention 4.8-fold, not mortality.
- Italian CoreValve/Evolut cohort (Palmerini et al., EuroIntervention 2026, doi:10.4244/EIJ-D-25-00575) [23]: 1,291 patients, median 59 months; SVD 3.6 percent; early residual gradient (discharge or within 3 months) sHR 1.05 per mmHg; SVD raised all-cause mortality HR 2.12 and cardiac mortality sHR 5.78; 54 percent of SVD progressed to BVF.
- UK TAVI registry (Blackman et al., J Am Coll Cardiol 2019;73:537-545, PMID 30732706) [17]: 241 patients with paired echo, median 5.8 years; moderate SVD 8.7 percent, severe 0.4 percent. Follow-up (Ali et al., Catheter Cardiovasc Interv 2023, doi:10.1002/ccd.30627) [18]: 221 patients, median 7 years, severe SVD 5.9 percent overall, 11.9 percent BE vs 3.5 percent SE, 28.6 percent in small BE valves.
- Vancouver 10-year (Sathananthan et al., Catheter Cardiovasc Interv 2021, doi:10.1002/ccd.29124) [19]: 235 early-generation BE recipients, mortality 91.6 percent at 10 years; SVD or BVF 0.4, 1.7, 4.7 and 6.5 percent at 4, 6, 8 and 10 years.
- STS/ACC TVT registry (Am Heart J 2018, PMID 29224637) [51]: 10,099 TAVRs with paired echo; HVD (10 mmHg rise) 2.1 percent at 0 to 30 days and 2.5 percent at 30 days to 1 year; predictors male sex, BMI, severe lung disease, ViV, 23 mm valve.
- Del Trigo et al. (J Am Coll Cardiol 2016;67:644-655, doi:10.1016/j.jacc.2015.10.097) [42]: 1,521 TAVR, mean follow-up 20 months; MG rose 0.30 mmHg per year; HVD (10 mmHg rise) 4.5 percent; predictors absence of anticoagulation at discharge, ViV, 23 mm valve, higher BMI.
- Rheude et al. (EuroIntervention 2020, doi:10.4244/EIJ-D-19-00710) [43]: 691 BE TAVI; moderate or greater hemodynamic SVD at 12 months 10.3 percent; 20 mm valve, ViV and OAC status independently associated; valve thrombosis 0.87 percent.
- Trimaille et al. (JACC Cardiovasc Interv 2025, doi:10.1016/j.jcin.2025.08.020) [44]: 1,912 TAVR; early HVD within 3 months in 3.6 percent, predicted by smaller annulus, ViV (OR 3.86) and no anticoagulation (OR 2.44); early HVD predicted later stage 2 or 3 HVD (sHR 7.40) and BVF (sHR 2.70).
- Angellotti et al. (JACC Cardiovasc Interv 2025, doi:10.1016/j.jcin.2025.10.005) [52]: 1,043 SAPIEN 3 patients; underexpansion of 20 percent or more sHR 4.88 for 5-year HVD.

### 3.3 Surgical series and valve models

- Perimount, Cleveland Clinic (Johnston et al., Ann Thorac Surg 2015;99:1239-1247, doi:10.1016/j.athoracsur.2014.10.070) [32]: 12,569 implants, 81,706 patient-years, 27,386 echo records; explant for SVD 1.9 percent at 10 years and 15 percent at 20 years overall, 5.6 and 46 percent under age 60; younger age and higher gradient at implantation were the risks.
- Perimount, Tours (Bourguignon et al., Ann Thorac Surg 2015;99:831-837, doi:10.1016/j.athoracsur.2014.09.030) [33]: 2,659 patients, 18,404 valve-years; freedom from SVD reoperation at 15 and 20 years 70.8 and 38.1 percent (age 60 or under), 82.7 and 59.6 percent (60 to 70), 98.1 percent at 15 years (over 70); expected valve durability 19.7 years. In the under-60 subgroup (Bourguignon et al., Ann Thorac Surg 2015, 373 patients) [34] freedom from SVD at 20 years was 37.2 percent (search result; full text not opened; DOI not retrieved).
- Real-world SAVR, Quebec (Rodriguez-Gabella et al., J Am Coll Cardiol 2018;71:1401-1412, doi:10.1016/j.jacc.2018.01.059) [26]: 672 consecutive patients 2002 to 2004, 10-year echo in 87 percent of survivors; clinically relevant SVD 6.6 percent, subclinical SVD 30.1 percent; BMI and a specific bioprosthesis independently predicted clinically relevant SVD; 83 percent of those were reintervened.
- HVD after SAVR (Salaun et al., Circulation 2018;138:971-985, doi:10.1161/CIRCULATIONAHA.118.035150) [27]: 1,387 patients, baseline echo at median 4.1 months; HVD (10 mmHg rise or AR worsening by at least one class) in 30.9 percent; within 5 years predicted by diabetes, active smoking, renal insufficiency, baseline MG 15 mmHg or more, baseline AR at least mild, stented vs stentless; after 5 years by female sex, warfarin use and valve type (pericardial vs porcine); HVD carried 2.2-fold adjusted mortality.
- Dysmetabolic markers (Salaun et al., J Am Coll Cardiol 2018;72:241-251, doi:10.1016/j.jacc.2018.04.064) [28]: 137 patients; HVD in 13.1 percent over 3 years predicted by CT leaflet calcification, HOMA index 2.7 or more, Lp-PLA2 activity and PCSK9 305 ng/mL or more; HVD HR 5.12 for death or reintervention. CT leaflet calcium density 58 AU/cm2 or more: HR 2.23 for death or reintervention (Zhang et al., J Am Coll Cardiol 2020;76:1737-1748, doi:10.1016/j.jacc.2020.08.034) [29]. Calcium-phosphorus product OR 1.11 per unit and PPM OR 3.67 for CT calcification (Mahjoub et al., Heart 2015;101:472-477, doi:10.1136/heartjnl-2014-306445) [30].
- PPM (Flameng et al., Circulation 2010;121:2123-2129, doi:10.1161/CIRCULATIONAHA.109.901272) [31]: 564 patients, SVD 7 percent; PPM (indexed EOA below 0.85 cm2/m2) and label size 21 or smaller independent predictors; stenosis-type SVD appears after 2 to 3 years with PPM, regurgitation-type SVD after 9 years without.
- Mitroflow 12A/LX (Sénage et al., Circulation 2014;130:2012-2020, doi:10.1161/CIRCULATIONAHA.114.010400) [35]: 617 patients, early SVD 1.66 percent per patient-year, mean delay 3.8 years; 5-year SVD-free survival 91.6 percent overall, 79.8 percent for 19 mm; SVD HR 7.7 for mortality. Re-analysis with interval censoring (Sénage et al., J Thorac Cardiovasc Surg 2019, doi:10.1016/j.jtcvs.2018.08.086) [36]: 561 patients, 103 SVD; cumulative incidence 15.2 percent at 4 years and 31.0 percent at 7 years; risk factors female sex, dyslipidaemia, COPD, PPM.
- Trifecta (Yongue et al., Ann Thorac Surg 2021;111:1198-1205, doi:10.1016/j.athoracsur.2020.07.040) [37]: 2,298 propensity-matched pairs vs Perimount; lower early gradient (11 vs 15 mmHg at 1 year) but faster gradient rise, more AR and lower 5-year freedom from explant. Werner et al. (Interact Cardiovasc Thorac Surg 2021, doi:10.1093/icvts/ivaa236) [38]: 347 patients, SVD 7.2 percent, freedom from SVD 92.5 percent at 5 and 65.5 percent at 7 years. Suzuki et al. (Asian Cardiovasc Thorac Ann 2022, doi:10.1177/02184923221100994) [39]: 270 patients, 5-year freedom from redo for SVD 89.4 percent Trifecta vs 100 percent Magna Ease, HR 20.8.
- Hancock II porcine (Toronto series, David et al., J Thorac Cardiovasc Surg 2003, PMID 12878940; Une et al., Eur J Cardiothorac Surg 2010, PMID 20194029) [40]: actual freedom from SVD at 18 years 86.4 percent overall and 98.2 percent over age 70; 20-year freedom from SVD 73 percent in AVR patients aged 65 or more vs 39 percent under 65 (figures from search summaries; full texts not opened).
- Epic porcine (J Artif Organs 2023, doi:10.1007/s10047-023-01401-3) [41]: freedom from reintervention for SVD at 10 years 99.4 percent (abstract via search; small single-centre series).
- Mechanisms review (Kostyunin et al., J Am Heart Assoc 2020;9:e018506, doi:10.1161/JAHA.120.018506) [50]: early SVD associated with young age, end-stage renal disease, diabetes, hyperparathyroidism, smoking, PPM; immune response now considered a major pathway.
- Narrative review of predictors (Rodriguez-Gabella et al., J Am Coll Cardiol 2017;70:1013-1028, doi:10.1016/j.jacc.2017.07.715) [25]: publisher page returned 403; cited for the predictor list only as summarised by later reviews.

### 3.4 Subclinical leaflet thrombosis and anticoagulation

- PARTNER 3 CT substudy (Makkar et al., J Am Coll Cardiol 2020;75:3003-3015, doi:10.1016/j.jacc.2020.04.043) [46]: 435 patients; HALT 10 percent at 30 days, 24 percent at 1 year; TAVR vs SAVR 13 vs 5 percent at 30 days, 28 vs 20 percent at 1 year; persistent HALT associated with higher MG (17.8 vs 12.7 mmHg).
- GALILEO-4D (De Backer et al., N Engl J Med 2020;382:130-139, doi:10.1056/NEJMoa1911426) [47]: rivaroxaban 10 mg plus aspirin vs clopidogrel plus aspirin; grade 3 or higher reduced leaflet motion 2.1 vs 10.9 percent; leaflet thickening 12.4 vs 32.4 percent. The main GALILEO trial stopped early for harm, so this is not a treatment recommendation.
- Meta-analysis of 53 studies, 25,258 TAVR (Roule et al., Arch Cardiovasc Dis 2023, doi:10.1016/j.acvd.2023.10.003) [49]: leaflet thrombosis 16.4 percent by CT, 1.1 percent by echo; OAC protective RR 0.51; intra-annular valves higher risk; no mortality association, small stroke signal.
- Long-term HALT (Iwata et al., Catheter Cardiovasc Interv 2025, doi:10.1002/ccd.31435) [48]: 448 SAPIEN patients, HALT 15.2 percent within 30 days; no difference in SVD at median 5.1 years (14.7 vs 17.9 percent, HR 0.89).
- VKA vs DOAC (Trimaille et al., Struct Heart 2026, doi:10.1016/j.shj.2025.100786) [45]: 132 matched pairs, no difference in stage 2 or 3 HVD (sHR 0.89).
- Direction of the anticoagulation effect is not consistent: protective in Del Trigo [42], Long [24], Trimaille [44] and GALILEO-4D [47]; associated with more HVD in Bern [22] and with late HVD after SAVR in Salaun [27], where it is plausibly a marker of atrial fibrillation and comorbidity. The protocol should model OAC as a time-varying exposure and report both cause-specific and subdistribution hazards.

### 3.5 Summary table of predictors with published effect sizes

| Predictor | Effect | Source |
|---|---|---|
| Age under 60 at SAVR | Explant for SVD 46 vs 15 percent at 20 years | Johnston 2015 [32] |
| Age 60 or under vs 60 to 70 vs over 70 | Freedom from SVD reoperation at 20 years 38 vs 60 vs about 98 percent (15 years) | Bourguignon 2015 [33] |
| Small valve (19 mm Mitroflow) | 5-year SVD-free 79.8 vs 91.6 percent | Sénage 2014 [35] |
| Valve diameter below 26 mm (TAVR) | HR 3.57 | Long 2020 [24] |
| 20 mm or 23 mm THV, ViV | Independent predictors of HVD | Del Trigo 2016 [42], Rheude 2020 [43] |
| Small device size (TAVR) | HR 4.82 | Giannini 2025 [21] |
| Intra-annular THV design | HR 38.4 | Giannini 2025 [21] |
| BE vs SE valve | SVD HR 10.25 at 4 years | Silva 2025 [20] |
| SAPIEN XT vs SAVR | SVD 1.61 vs 0.63 per 100 patient-years | Pibarot 2020 [11] |
| PPM (iEOA below 0.85) | Independent predictor, early stenosis-type SVD | Flameng 2010 [31] |
| Severe PPM | HR 1.85 after SAVR; 1.70 after TAVR (ns) | as tabulated in Trimaille 2025 [6] |
| Baseline post-op MG 15 mmHg or more | HR 1.30 | Salaun 2018 [27] |
| Early residual MG | sHR 1.05 per mmHg | Palmerini 2026 [23] |
| Residual AR at discharge | HR 1.87 | Alaour 2025 [22] |
| Post-procedural moderate or severe PVL | HR 3.64 | Giannini 2025 [21] |
| THV underexpansion 20 percent or more | sHR 4.88 | Angellotti 2025 [52] |
| Renal dysfunction | OR 1.42 | Long 2020 [24] |
| Chronic kidney disease | HR 1.10 | tabulated in [6] |
| Diabetes | HR 1.33 | tabulated in [6] |
| Active smoking | HR 2.58 | tabulated in [6] |
| BMI | HR 1.08 per unit | tabulated in [6] |
| No anticoagulation at discharge | HR 3.35; OR 2.44 | tabulated in [6]; Trimaille 2025 [44] |
| Lp-PLA2, PCSK9 above 305, HOMA 2.7 or more | HR 1.15 per 0.1, 4.36, 3.30 | Salaun 2018 JACC [28] |
| Calcium-phosphorus product | OR 1.11 per unit for CT calcification | Mahjoub 2015 [30] |
| CT leaflet calcium density 58 AU/cm2 or more | HR 2.23 death or reintervention | Zhang 2020 [29] |
| Female sex | Late HVD after SAVR; risk factor in Mitroflow cohort | Salaun 2018 [27], Sénage 2019 [36] |
| Male sex | HR 2.17 in one TAVR cohort | tabulated in [6] |
| Early HALT | No association with SVD at 5 years | Iwata 2025 [48] |

## 4. Existing prediction models

The searches (PubMed via web search, Europe PMC title and abstract queries for "structural valve deterioration", "bioprosthetic valve failure", "hemodynamic valve deterioration" combined with "prediction model", "risk score", "nomogram", "machine learning", "deep learning") found no published, validated multivariable risk score or machine learning model whose target is SVD, HVD or BVF after aortic bioprosthesis. What exists:

- Microsimulation from meta-analysis (Puvimanasinghe et al., Circulation 2001;103:1535-1541, doi:10.1161/01.CIR.103.11.1535) [53]: 9 reports, 5,837 patients, 31,874 patient-years of stented porcine valves; SVD modelled with an age-dependent Weibull hazard; a 65-year-old man had 28 percent lifetime reoperation risk. This is a population model, not an individual predictor, and it predates current valves.
- Predictor studies with multivariable Cox or Fine-Gray models but no derived score or reported discrimination: Salaun 2018 [27], Flameng 2010 [31], Sénage 2019 [36], Del Trigo 2016 [42], O'Hair 2023 [14], Alaour 2025 [22], Giannini 2025 [21], Palmerini 2026 [23], Trimaille 2025 [44]. None reports a C-index for the SVD model.
- Machine learning adjacent to the question: prediction of the post-TAVR transvalvular gradient waveform from pre-procedural echo with deep learning (Song et al., J Thorac Cardiovasc Surg 2025, PMID 40320003) [54]; prediction of subclinical leaflet thrombosis at 6 months after SE TAVI with LASSO, random forest and XGBoost on 118 patients (AUC 0.84 to 0.89, Brier 0.04 to 0.16; Moscarelli et al., JTCVS Struct Endovasc 2025, doi:10.1016/j.xjse.2025.100064) [55] and XGBoost on 128 patients (AUC 0.91, Brier 0.09; Moscarelli et al., Interdiscip CardioVasc Thorac Surg 2026, doi:10.1093/icvts/ivag144) [56]; prediction of HALT from pre-procedural CT (Venkatesh et al., JTCVS Struct Endovasc 2025, PMID 42306643) [57]. These are small, single-centre, cross-validated only, and their outcome is thrombosis, not SVD.
- Models of the hemodynamic trajectory from serial echo: the Erasmus group modelled serial aortic gradient and AR jointly with death and reoperation in allograft recipients (Andrinopoulou et al., Ann Thorac Surg 2012;93:1765-1772, doi:10.1016/j.athoracsur.2012.02.049 [69]; Stat Med 2014;33:3167-3178, doi:10.1002/sim.6158 [70]; Stat Methods Med Res 2017;26:1787-1801, doi:10.1177/0962280215588340 [71]), using B-spline subject-specific gradient curves and Bayesian joint models to give dynamically updated risk. Johnston 2015 [32] used time-varying covariable analysis of 27,386 echo records to model gradient change. Del Trigo [42] reported a mean annualised gradient change of 0.30 mmHg per year with SD 5.0, which is the noise level a trajectory model must beat.
- Mortality models after TAVR (for example ML AUC 0.70 vs EuroSCORE II) are not relevant to durability and are not cited.

Implication: there is no external benchmark C-index for SVD. The protocol should pre-specify a clinical Cox or Fine-Gray baseline built from the established predictors and compare the ML model to it, and should present any C-index above about 0.70 with calibration as a meaningful result given the noise in echo gradients.

## 5. Statistical methodology

### 5.1 Competing risk of death

Death before SVD is frequent (NOTION 63 percent dead at 10 years [9]; Vancouver 92 percent [19]; Johnston 76 percent probability of death before explant [32]). One minus Kaplan-Meier overstates SVD risk: in a mitral bioprosthesis series 15-year freedom from reoperation was 55 percent by Kaplan-Meier and 83 percent by cumulative incidence (Kaempchen, Grunkemeier et al., Eur J Cardiothorac Surg 2003;23:710-713, doi:10.1016/S1010-7940(03)00081-2) [65]; see also Grunkemeier et al., Ann Thorac Surg 2007;83:1586-1592 [66]. Use the cumulative incidence function and report both cause-specific hazards (aetiology) and Fine-Gray subdistribution hazards (absolute risk prediction) (Austin, Lee, Fine, Circulation 2016;133:601-609, doi:10.1161/CIRCULATIONAHA.115.017719 [62]; Fine and Gray, J Am Stat Assoc 1999;94:496-509 [64]). For prediction, calibration and discrimination must be adapted to competing risks (Wolbers et al., Epidemiology 2009;20:555-561, doi:10.1097/EDE.0b013e3181a39056) [63]. Recent SVD papers already do this: O'Hair [14], Yakubov [15], Palmerini [23], Trimaille [44, 45], Angellotti [52] all report subdistribution hazards.

### 5.2 Interval censoring

SVD is detected at discrete echo visits, so the event time lies between the last normal and the first abnormal echo. Sénage 2019 [36] showed that ignoring this underestimates cumulative SVD and used an illness-death model for interval-censored data; Flameng [31] used the non-parametric Turnbull estimator (Turnbull, J R Stat Soc B 1976;38:290-295) [73]. Midpoint imputation is a common shortcut but biases hazards when visit intervals are long and irregular, which is exactly the situation in EHR data. Yang, Rizopoulos, Newcomb and Erler (Biom J 2026, doi:10.1002/bimj.70108) [68] give model-based and IPCW versions of time-dependent AUC, Brier score and predictive cross-entropy for interval-censored outcomes with competing risks and time-varying covariates, built on a joint model. This is the closest methodological template for our problem.

### 5.3 Sample size and events per variable

Riley et al. (Stat Med 2019;38:1276-1296, doi:10.1002/sim.7992) [60] replace the 10 events-per-variable rule with three criteria: global shrinkage factor 0.9 or more, absolute difference of 0.05 or less between apparent and adjusted Nagelkerke R2, and precise estimation of the overall risk at the horizon of interest; worked examples required 4.8 to 23 events per parameter. Implemented in pmsampsize (R, Stata, Python). External validation of a time-to-event model has its own criteria targeting the confidence interval of the calibration slope and time-dependent measures (Riley, Collins, Ensor et al., Stat Med 2022;41:1280-1295, doi:10.1002/sim.9275) [61]. A cardiothoracic primer is in Eur J Cardiothorac Surg 2025;67:ezaf142 (PMC12106283) [77].

Our illustrative calculation using the first two Riley criteria for time-to-event outcomes, with anticipated Cox-Snell R2 set at 15 percent of its maximum (Riley's conservative default) and iterated to convergence (script in the scratchpad; verify with pmsampsize):

| Parameters | SVD rate per 100 patient-years | Mean echo follow-up (years) | Minimum n | Events | Events per parameter |
|---|---|---|---|---|---|
| 15 | 1.0 | 4 | 2,415 | 97 | 6.4 |
| 15 | 2.0 | 4 | 1,578 | 127 | 8.4 |
| 15 | 2.0 | 6 | 1,224 | 147 | 9.8 |
| 15 | 3.0 | 6 | 1,045 | 189 | 12.5 |
| 25 | 2.0 | 4 | 2,629 | 211 | 8.4 |
| 25 | 3.0 | 6 | 1,742 | 314 | 12.5 |

A rate of 1 to 2 per 100 patient-years corresponds to the moderate or severe SVD incidence seen in modern TAVR and SAVR cohorts at 5 to 8 years [11, 20, 22]; 3 per 100 corresponds to the 10 mmHg-rise HVD definition in SAVR (Salaun 30.9 percent over up to 10 years [27]) or to high-risk valves. Note that every predictor category and every spline knot counts as a parameter, and that ML models with data-driven interactions need substantially more.

### 5.4 Discrimination, calibration and validation

- Time-dependent AUC with IPCW under competing risks (Blanche, Dartigues, Jacqmin-Gadda, Stat Med 2013;32:5381-5397, doi:10.1002/sim.5958; timeROC package) [67]; Uno's C-statistic for censored data (Uno et al., Stat Med 2011;30:1105-1117) [78]; Brier score and index of prediction accuracy with IPCW.
- Calibration at fixed horizons (3, 5, 8 years): predicted vs observed cumulative incidence in risk groups and smoothed curves, calibration slope and intercept (Van Calster et al., BMC Med 2019;17:230) [75]. Calibration is where ML survival models typically fail.
- Internal validation by bootstrap or repeated cross-validation with all model-building steps inside the loop; external validation in a geographically or temporally separate cohort sized per Riley 2022 [61]; report per TRIPOD+AI (Collins et al., BMJ 2024;385:e078378) [74].

### 5.5 Immortal time and informative censoring

- Immortal time bias arises when exposure is defined by something that happens after time zero (for example "on anticoagulation during follow-up", "had a follow-up echo", "survived to 1 year") (Lévesque, Hanley, Kezouh, Suissa, BMJ 2010;340:b5087) [72]. Fix time zero at implantation (or at the reference echo, applied uniformly), treat later exposures as time-varying, or use landmark analysis.
- Informative censoring: patients who are sicker or who have symptoms get more echo; patients who die are censored by a competing event; patients lost to follow-up may be the well ones. Requiring a follow-up echo for inclusion (as Blackman [17] and Ali [18] did) selects survivors and understates events. Report the number at risk with echo at each horizon (NOTION 81 percent of survivors, PARTNER 3 80 percent), use competing-risk estimators, and consider IPCW for dependent censoring with the joint model as the principled alternative.

### 5.6 Joint models for serial echo plus time-to-event

Joint models couple a mixed-effects model for the longitudinal marker (MG, EOA, DVI, AR grade) with a survival submodel for SVD, death and reintervention, and yield dynamically updated individual predictions as new echoes arrive (Andrinopoulou et al. 2012, 2014, 2017 [69, 70, 71]; software JM and JMbayes2, Rizopoulos, J Stat Softw 2010;35(9):1-33 [79]). They handle irregular visit timing, measurement error in gradients and informative dropout, and they fit the clinical question "given this patient's gradient trajectory to date, what is the 3-year risk of stage 2 or 3 HVD" better than a baseline-only model. Landmarking (van Houwelingen, Scand J Stat 2007;34:70-85) is the simpler alternative.

## 6. Cohort size and follow-up needed to see meaningful effects

Annual incidence and cumulative event rates from the sources above:

- Modern TAVR (VARC-3 moderate or severe): 1-year 2.2 percent, 5-year 10.8 percent, 10-year about 26 percent (Bern [22]); 8-year 13.3 percent SVD and 11.5 percent BVF (nine centres [20]); 6-year 2.4 percent, 8-year 13.2 percent (EORP [21]); pooled meta-analysis 4.9 percent at 1 year and 9.0 percent at 5 years or more, severe 1.75 percent (EAPCI definition [24]). SVD-related BVF at 5 years is 0.7 to 3.4 percent across trials (table in [6]).
- Modern SAVR: 5-year SVD 0.60 to 0.63 per 100 patient-years (PARTNER 2 [11]); 10-year clinically relevant SVD 6.6 percent and subclinical 30.1 percent (Quebec [26]); 10-year severe SVD 10.0 percent and moderate or severe 20.8 percent in NOTION [9]; explant for SVD 1.9 percent at 10 and 15 percent at 20 years (Perimount, mean age 71 [32]).
- Young patients and poor valves: 46 percent explant for SVD at 20 years under age 60 [32]; Mitroflow 1.66 percent per patient-year early SVD, 31 percent at 7 years with interval censoring [36]; Trifecta 35 percent SVD at 7 years [38].
- HVD by 10 mmHg rise only: 30.9 percent overall after SAVR [27]; 4.5 percent over 20 months after TAVR [42]; 10.3 percent at 12 months with BE TAVI [43].

What the published cohorts needed: to show a valve-type effect at 5 years, PARTNER 2 needed about 1,665 patients [11] and the CoreValve pool 2,099 randomised plus 2,663 registry patients [14]; NOTION with 280 patients detected a difference in severe SVD only at 8 to 10 years [9, 10]. Single-centre series of 240 to 600 patients produced descriptive incidence with wide intervals [17, 18, 19, 21]. Multivariable predictor models used 560 to 2,400 patients with 40 to 430 events [22, 27, 31, 36, 42]. For a prediction model with about 15 parameters, the Riley-based estimates above (1,000 to 2,400 patients, 100 to 190 events, at least 4 to 6 years of serial echo) match the size of the cohorts that actually produced stable predictor effects, so they are a realistic target for the protocol. Because most SVD occurs after year 5 in SAVR and after year 4 to 5 in TAVR, a study with under 4 years median echo follow-up will mostly capture early HVD (thrombosis, PPM, ViV), which is a different phenotype from late calcific SVD; the protocol should say which one it is predicting, or stratify the analysis by early (under 5 years) and late HVD as Salaun did [27].

## 7. Reference list

Definitions
1. Capodanno D, Petronio AS, Prendergast B, Eltchaninoff H, Vahanian A, Modine T, Lancellotti P, Sondergaard L, Ludman PF, Tamburino C, Piazza N, Hancock J, Mehilli J, Byrne RA, Baumbach A, Kappetein AP, Windecker S, Bax J, Haude M. Standardized definitions of structural deterioration and valve failure in assessing long-term durability of transcatheter and surgical aortic bioprosthetic valves: EAPCI consensus endorsed by ESC and EACTS. Eur Heart J 2017;38:3382-3390. doi:10.1093/eurheartj/ehx303. Full text opened.
2. Dvir D, Bourguignon T, Otto CM, Hahn RT, Rosenhek R, Webb JG, et al., VIVID Investigators. Standardized definition of structural valve degeneration for surgical and transcatheter bioprosthetic aortic valves. Circulation 2018;137:388-399. doi:10.1161/CIRCULATIONAHA.117.030729. Abstract only; staging via [7].
3. VARC-3 Writing Committee, Généreux P, Piazza N, Alu MC, Nazif T, Hahn RT, Pibarot P, et al. Valve Academic Research Consortium 3: updated endpoint definitions for aortic valve clinical research. Eur Heart J 2021;42:1825-1857, doi:10.1093/eurheartj/ehaa799; J Am Coll Cardiol 2021;77:2717-2746, doi:10.1016/j.jacc.2021.02.038. Full text truncated; HVD wording verified via [45].
4. Pibarot P, Herrmann HC, Wu C, Hahn RT, Otto CM, Abbas AE, et al. Standardized definitions for bioprosthetic valve dysfunction following aortic or mitral valve replacement: JACC state-of-the-art review. J Am Coll Cardiol 2022;80:545-561. doi:10.1016/j.jacc.2022.06.002. Abstract.
5. Herrmann HC, Pibarot P, Wu C, Hahn RT, Tang GHL, Abbas AE, et al. Bioprosthetic aortic valve hemodynamics: definitions, outcomes, and evidence gaps. J Am Coll Cardiol 2022;80:527-544. doi:10.1016/j.jacc.2022.06.001. Abstract.
6. Trimaille A, et al. Transcatheter aortic valve durability: focus on structural valve deterioration. J Am Heart Assoc 2025;14:e041505. doi:10.1161/JAHA.125.041505. Full text opened (Europe PMC XML).
7. Structural valve deterioration in transcatheter aortic bioprostheses: diagnosis, pathogenesis, and treatment. Struct Heart 2023 (PMC10236800; PII S2474-8706(22)01981-9). Full text opened via Europe PMC; author list not captured.

Trials and registries
9. Thyregod HGH, Jørgensen TH, Ihlemann N, Steinbrüchel DA, Nissen H, Kjeldsen BJ, et al. Transcatheter or surgical aortic valve implantation: 10-year outcomes of the NOTION trial. Eur Heart J 2024;45:1116-1124. doi:10.1093/eurheartj/ehae043. Full text opened.
10. Jørgensen TH, Thyregod HGH, Ihlemann N, Nissen H, Petursson P, Kjeldsen BJ, et al. Eight-year outcomes for patients with aortic valve stenosis at low surgical risk randomized to TAVI vs SAVR. Eur Heart J 2021;42:2912-2919. doi:10.1093/eurheartj/ehab375. Abstract.
11. Pibarot P, Ternacle J, Jaber WA, Salaun E, Dahou A, Asch FM, et al. Structural deterioration of transcatheter versus surgical aortic valve bioprostheses in the PARTNER-2 trial. J Am Coll Cardiol 2020;76:1830-1843. doi:10.1016/j.jacc.2020.08.049. Abstract.
12. Mack MJ, Leon MB, Thourani VH, et al., PARTNER 3 Investigators. Transcatheter aortic-valve replacement in low-risk patients at five years. N Engl J Med 2023;389:1949-1960. doi:10.1056/NEJMoa2307447. Numbers from search summary.
13. Ternacle J, et al., PARTNER 3 Investigators. Seven-year valve durability with transcatheter or surgical aortic valve replacement: an ad hoc analysis of the PARTNER 3 randomized clinical trial. JAMA Cardiol 2026, published online 24 June 2026. doi:10.1001/jamacardio.2026.2299. Full text opened (PMC13294825).
14. O'Hair D, Yakubov SJ, Grubb KJ, Oh JK, Ito S, Deeb GM, et al. Structural valve deterioration after self-expanding transcatheter or surgical aortic valve implantation in patients at intermediate or high risk. JAMA Cardiol 2023;8:111-119. doi:10.1001/jamacardio.2022.4627. Abstract.
15. Yakubov SJ, Van Mieghem NM, Oh JK, Ito S, Grubb KJ, O'Hair D, et al. Impact of transcatheter or surgical aortic valve performance on 5-year outcomes in patients at intermediate or greater risk. J Am Coll Cardiol 2025;85(13). doi:10.1016/j.jacc.2025.02.009. Abstract.
16. Forrest JK, Yakubov SJ, Deeb GM, Gada H, Mumtaz MA, Ramlawi B, et al. 5-year outcomes after transcatheter or surgical aortic valve replacement in low-risk patients with aortic stenosis. J Am Coll Cardiol 2025. doi:10.1016/j.jacc.2025.03.004. Abstract.
17. Blackman DJ, Saraf S, MacCarthy PA, et al. Long-term durability of transcatheter aortic valve prostheses. J Am Coll Cardiol 2019;73:537-545. PMID 30732706. Search summary.
18. Ali N, Hildick-Smith D, Parker J, Malkin CJ, Cunnington MS, Gurung S, et al. Long-term durability of self-expanding and balloon-expandable transcatheter aortic valve prostheses: UK TAVI registry. Catheter Cardiovasc Interv 2023. doi:10.1002/ccd.30627. Abstract.
19. Sathananthan J, Lauck S, Polderman J, Yu M, Stephenson A, et al. Ten year follow-up of high-risk patients treated during the early experience with TAVR. Catheter Cardiovasc Interv 2021. doi:10.1002/ccd.29124. Abstract.
20. Silva I, Alperi A, Muñoz A, Cheema A, Nombela L, Veiga-Fernandez G, et al. Incidence and impact of structural valve deterioration following TAVI: a multicenter real-world study. Eur Heart J Cardiovasc Imaging 2025;26:1018-1028. doi:10.1093/ehjci/jeaf083. Abstract.
21. Giannini C, et al. Long-term structural valve deterioration after TAVI: insights from the EORP ESC Valve Durability TAVI Registry. EuroIntervention 2025. doi:10.4244/EIJ-D-24-00662. Publisher page opened.
22. Alaour B, Tomii D, Nakase M, Heg D, Stortecky S, Lanz J, et al. Hemodynamic valve deterioration after TAVR: incidence, predictors, and clinical outcomes. JACC Cardiovasc Interv 2025. doi:10.1016/j.jcin.2024.09.039. Abstract.
23. Palmerini T, Saia F, Bruno AG, Adamo M, Chizzola G, Massussi M, et al. Predictors of long-term structural valve deterioration and failure after TAVI. EuroIntervention 2026. doi:10.4244/EIJ-D-25-00575. Abstract and publisher page.
24. Long YX, Liu ZZ. Incidence and predictors of structural valve deterioration after TAVR: a systematic review and meta-analysis. J Interv Cardiol 2020;2020:4075792. doi:10.1155/2020/4075792. Full text opened.
25. Rodriguez-Gabella T, Voisine P, Puri R, Pibarot P, Rodés-Cabau J. Aortic bioprosthetic valve durability: incidence, mechanisms, predictors, and management of surgical and transcatheter valve degeneration. J Am Coll Cardiol 2017;70:1013-1028. doi:10.1016/j.jacc.2017.07.715. Not opened (403).
26. Rodriguez-Gabella T, Voisine P, Dagenais F, Mohammadi S, Perron J, Dumont E, et al. Long-term outcomes following surgical aortic bioprosthesis implantation. J Am Coll Cardiol 2018;71:1401-1412. doi:10.1016/j.jacc.2018.01.059. Abstract.
27. Salaun E, Mahjoub H, Girerd N, Dagenais F, Voisine P, Mohammadi S, et al. Rate, timing, correlates, and outcomes of hemodynamic valve deterioration after bioprosthetic surgical aortic valve replacement. Circulation 2018;138:971-985. doi:10.1161/CIRCULATIONAHA.118.035150. Abstract.
28. Salaun E, Mahjoub H, Dahou A, Mathieu P, Larose É, Després JP, et al. Hemodynamic deterioration of surgically implanted bioprosthetic aortic valves. J Am Coll Cardiol 2018;72:241-251. doi:10.1016/j.jacc.2018.04.064. Abstract.
29. Zhang B, Salaun E, Côté N, Wu Y, Mahjoub H, Mathieu P, et al. Association of bioprosthetic aortic valve leaflet calcification on hemodynamic and clinical outcomes. J Am Coll Cardiol 2020;76:1737-1748. doi:10.1016/j.jacc.2020.08.034. Abstract.
30. Mahjoub H, Mathieu P, Larose E, Dahou A, Sénéchal M, Dumesnil JG, Després JP, Pibarot P. Determinants of aortic bioprosthetic valve calcification assessed by multidetector CT. Heart 2015;101:472-477. doi:10.1136/heartjnl-2014-306445. Abstract.
31. Flameng W, Herregods MC, Vercalsteren M, Herijgers P, Bogaerts K, Meuris B. Prosthesis-patient mismatch predicts structural valve degeneration in bioprosthetic heart valves. Circulation 2010;121:2123-2129. doi:10.1161/CIRCULATIONAHA.109.901272. Abstract.
32. Johnston DR, Soltesz EG, Vakil N, Rajeswaran J, Roselli EE, Sabik JF, et al. Long-term durability of bioprosthetic aortic valves: implications from 12,569 implants. Ann Thorac Surg 2015;99:1239-1247. doi:10.1016/j.athoracsur.2014.10.070. Abstract.
33. Bourguignon T, Bouquiaux-Stablo AL, Candolfi P, Mirza A, Loardi C, May MA, et al. Very long-term outcomes of the Carpentier-Edwards Perimount valve in aortic position. Ann Thorac Surg 2015;99:831-837. doi:10.1016/j.athoracsur.2014.09.030. Abstract.
34. Bourguignon T, et al. Very long-term outcomes of the Carpentier-Edwards Perimount aortic valve in patients aged 60 or younger. Ann Thorac Surg 2015. DOI not retrieved; figures from search summary.
35. Sénage T, Le Tourneau T, Foucher Y, Pattier S, Cueff C, Michel M, et al. Early structural valve deterioration of Mitroflow aortic bioprosthesis: mode, incidence, and impact on outcome in a large cohort of patients. Circulation 2014;130:2012-2020. doi:10.1161/CIRCULATIONAHA.114.010400. Abstract.
36. Sénage T, Gillaizeau F, Le Tourneau T, Marie B, Roussel JC, Foucher Y. Structural valve deterioration of bioprosthetic aortic valves: an underestimated complication. J Thorac Cardiovasc Surg 2019. doi:10.1016/j.jtcvs.2018.08.086. Abstract.
37. Yongue C, Lopez DC, Soltesz EG, Roselli EE, Bakaeen FG, Gillinov AM, et al. Durability and performance of 2298 Trifecta aortic valve prostheses: a propensity-matched analysis. Ann Thorac Surg 2021;111:1198-1205. doi:10.1016/j.athoracsur.2020.07.040. Abstract.
38. Werner P, Gritsch J, Scherzer S, Gross C, Russo M, Coti I, et al. Structural valve deterioration after aortic valve replacement with the Trifecta valve. Interact Cardiovasc Thorac Surg 2021;32:39-46. doi:10.1093/icvts/ivaa236. Abstract.
39. Suzuki R, Ito T, Suzuki M, Ohori S, Takayanagi R, Miura S. Trifecta versus Perimount Magna Ease aortic valves: failure mechanisms. Asian Cardiovasc Thorac Ann 2022. doi:10.1177/02184923221100994. Search summary.
40. David TE, et al. Long-term durability of the Hancock II porcine bioprosthesis. J Thorac Cardiovasc Surg 2003 (PMID 12878940); Une D, et al. The fate of Hancock II porcine valve recipients 25 years after implant. Eur J Cardiothorac Surg 2010 (PMID 20194029). Search summaries only.
41. Long-term valve performance of St Jude Medical Epic porcine bioprosthesis in aortic position. J Artif Organs 2023. doi:10.1007/s10047-023-01401-3. Search summary.
42. Del Trigo M, Muñoz-Garcia AJ, Wijeysundera HC, Nombela-Franco L, Cheema AN, Gutierrez E, et al. Incidence, timing, and predictors of valve hemodynamic deterioration after TAVR: multicenter registry. J Am Coll Cardiol 2016;67:644-655. doi:10.1016/j.jacc.2015.10.097. Abstract.
43. Rheude T, Pellegrini C, Cassese S, Wiebe J, Wagner S, Trenkwalder T, et al. Predictors of haemodynamic structural valve deterioration following TAVI with latest-generation balloon-expandable valves. EuroIntervention 2020. doi:10.4244/EIJ-D-19-00710. Abstract.
44. Trimaille A, Cepas-Guillen P, Del Portillo JH, Paradis JM, Dumont E, Poulin A, et al. Impact of early hemodynamic valve deterioration on long-term outcomes following TAVR. JACC Cardiovasc Interv 2025. doi:10.1016/j.jcin.2025.08.020. Abstract.
45. Trimaille A, Vidal-Cales P, Giuliani C, Hernando Del Portillo J, Paradis JM, Mohammadi S, et al. Impact of anticoagulant class on long-term bioprosthesis durability following TAVR. Struct Heart 2026. doi:10.1016/j.shj.2025.100786. Full text opened (PMC12810551); source of the verbatim VARC-3 HVD wording.
46. Makkar RR, Blanke P, Leipsic J, Thourani V, Chakravarty T, Brown D, et al. Subclinical leaflet thrombosis in transcatheter and surgical bioprosthetic valves: PARTNER 3 cardiac CT substudy. J Am Coll Cardiol 2020;75:3003-3015. doi:10.1016/j.jacc.2020.04.043. Abstract.
47. De Backer O, Dangas GD, Jilaihawi H, Leipsic JA, Terkelsen CJ, Makkar R, et al., GALILEO-4D Investigators. Reduced leaflet motion after transcatheter aortic-valve replacement. N Engl J Med 2020;382:130-139. doi:10.1056/NEJMoa1911426. Abstract.
48. Iwata J, Hayashida K, Arita R, Moriizumi T, Kajino A, Sakata S, et al. Long-term impact of early subclinical leaflet thrombosis after TAVI. Catheter Cardiovasc Interv 2025. doi:10.1002/ccd.31435. Abstract.
49. Roule V, Guedeney P, Silvain J, Beygui F, Zeitouni M, Sorrentino S, et al. Bioprosthetic leaflet thrombosis and reduced leaflet motion after TAVR: systematic review and meta-analysis. Arch Cardiovasc Dis 2023. doi:10.1016/j.acvd.2023.10.003. Abstract.
50. Kostyunin AE, Yuzhalin AE, Rezvova MA, Ovcharenko EA, Glushkova TV, Kutikhin AG. Degeneration of bioprosthetic heart valves: update 2020. J Am Heart Assoc 2020;9:e018506. doi:10.1161/JAHA.120.018506. Search summary.
51. Valve hemodynamic deterioration and cardiovascular outcomes in TAVR: a report from the STS/ACC TVT Registry. Am Heart J 2018 (PMID 29224637). Search summary; author list not captured.
52. Angellotti D, Elamin N, Ferro C, Tomii D, Lanz J, Stortecky S, et al. Real-time fluoroscopic assessment of underexpansion predicts hemodynamic valve deterioration following TAVR with balloon-expandable device. JACC Cardiovasc Interv 2025. doi:10.1016/j.jcin.2025.10.005. Abstract.

Prediction models
53. Puvimanasinghe JP, Steyerberg EW, Takkenberg JJ, Eijkemans MJ, van Herwerden LA, Bogers AJ, Habbema JD. Prognosis after aortic valve replacement with a bioprosthesis: predictions based on meta-analysis and microsimulation. Circulation 2001;103:1535-1541. doi:10.1161/01.CIR.103.11.1535. Abstract.
54. Song W, et al. Machine learning methods to predict transvalvular gradient waveform post-TAVR using preprocedural echocardiogram. J Thorac Cardiovasc Surg 2025. PMID 40320003. Title and abstract only.
55. Moscarelli M, Athanasiou T, Casula R, Pernice V, Zaccone G, Zlahoda-Huzior A, et al. Predicting subclinical leaflet thrombosis in self-expandable prosthesis: a multimodal machine learning analysis. JTCVS Struct Endovasc 2025. doi:10.1016/j.xjse.2025.100064. Abstract.
56. Moscarelli M, Athanasiou T, Casula R, Pernice V, Salardino M, Zaccone G, et al. Interpretable machine learning using accumulated local effects to characterise predictors of subclinical leaflet thrombosis after self-expanding TAVI. Interdiscip CardioVasc Thorac Surg 2026. doi:10.1093/icvts/ivag144. Abstract.
57. Venkatesh A, et al. A novel computational method to predict hypoattenuated leaflet thickening post-TAVR using preprocedural CT. JTCVS Struct Endovasc 2025. PMID 42306643. Title only.

Methods
60. Riley RD, Snell KIE, Ensor J, Burke DL, Harrell FE Jr, Moons KGM, Collins GS. Minimum sample size for developing a multivariable prediction model: PART II, binary and time-to-event outcomes. Stat Med 2019;38:1276-1296. doi:10.1002/sim.7992. Abstract opened.
61. Riley RD, Collins GS, Ensor J, et al. Minimum sample size calculations for external validation of a clinical prediction model with a time-to-event outcome. Stat Med 2022;41:1280-1295. doi:10.1002/sim.9275. Search summary.
62. Austin PC, Lee DS, Fine JP. Introduction to the analysis of survival data in the presence of competing risks. Circulation 2016;133:601-609. doi:10.1161/CIRCULATIONAHA.115.017719.
63. Wolbers M, Koller MT, Witteman JCM, Steyerberg EW. Prognostic models with competing risks: methods and application to coronary risk prediction. Epidemiology 2009;20:555-561. doi:10.1097/EDE.0b013e3181a39056.
64. Fine JP, Gray RJ. A proportional hazards model for the subdistribution of a competing risk. J Am Stat Assoc 1999;94:496-509. Cited from memory (standard reference).
65. Kaempchen S, Guenther T, Toschke M, Grunkemeier GL, Wottke M, Lange R. Assessing the benefit of biological valve prostheses: cumulative incidence (actual) vs Kaplan-Meier (actuarial) analysis. Eur J Cardiothorac Surg 2003;23:710-713. doi:10.1016/S1010-7940(03)00081-2. Abstract.
66. Grunkemeier GL, Jin R, Eijkemans MJ, Takkenberg JJ. Actual and actuarial probabilities of competing risks: apples and lemons. Ann Thorac Surg 2007;83:1586-1592. PII S0003-4975(06)02289-2. Title located; text not opened.
67. Blanche P, Dartigues JF, Jacqmin-Gadda H. Estimating and comparing time-dependent areas under ROC curves for censored event times with competing risks. Stat Med 2013;32:5381-5397. doi:10.1002/sim.5958.
68. Yang Z, Rizopoulos D, Newcomb LF, Erler NS. Time-dependent predictive accuracy metrics in the context of interval censoring and competing risks. Biom J 2026. doi:10.1002/bimj.70108. Abstract.
69. Andrinopoulou ER, Rizopoulos D, Jin R, Bogers AJ, Lesaffre E, Takkenberg JJ. An introduction to mixed models and joint modeling: analysis of valve function over time. Ann Thorac Surg 2012;93:1765-1772. doi:10.1016/j.athoracsur.2012.02.049. Abstract.
70. Andrinopoulou ER, Rizopoulos D, Takkenberg JJ, Lesaffre E. Joint modeling of two longitudinal outcomes and competing risk data. Stat Med 2014;33:3167-3178. doi:10.1002/sim.6158. Abstract.
71. Andrinopoulou ER, Rizopoulos D, Takkenberg JJ, Lesaffre E. Combined dynamic predictions using joint models of two longitudinal outcomes and competing risk data. Stat Methods Med Res 2017;26:1787-1801. doi:10.1177/0962280215588340.
72. Lévesque LE, Hanley JA, Kezouh A, Suissa S. Problem of immortal time bias in cohort studies: example using statins for preventing progression of diabetes. BMJ 2010;340:b5087.
73. Turnbull BW. The empirical distribution function with arbitrarily grouped, censored and truncated data. J R Stat Soc B 1976;38:290-295. Cited from memory (standard reference).
74. Collins GS, Moons KGM, Dhiman P, et al. TRIPOD+AI statement. BMJ 2024;385:e078378. Cited from memory (standard reference).
75. Van Calster B, McLernon DJ, van Smeden M, Wynants L, Steyerberg EW. Calibration: the Achilles heel of predictive analytics. BMC Med 2019;17:230. Cited from memory (standard reference).
76. Vahanian A, Beyersdorf F, Praz F, et al. 2021 ESC/EACTS Guidelines for the management of valvular heart disease. Eur Heart J 2022;43:561-632. doi:10.1093/eurheartj/ehab395. Cited from memory; echo surveillance recommendations not verified in this search.
77. Statistical primer: sample size considerations for developing and validating clinical prediction models. Eur J Cardiothorac Surg 2025;67:ezaf142 (PMC12106283). Search summary; authors not captured.
78. Uno H, Cai T, Pencina MJ, D'Agostino RB, Wei LJ. On the C-statistics for evaluating overall adequacy of risk prediction procedures with censored survival data. Stat Med 2011;30:1105-1117. Cited from memory (standard reference).
79. Rizopoulos D. JM: an R package for the joint modelling of longitudinal and time-to-event data. J Stat Softw 2010;35(9):1-33. Cited from memory (standard reference).

Sources that could not be opened: JACC publisher pages (403), AHA Circulation full texts (403), PubMed abstract pages (cookie wall; Europe PMC used instead), PMC pages for PMC11247222 and PMC9681687 (reCAPTCHA), ScienceDirect and Wiley full texts (403). Where this affected a number, the entry above says "abstract" or "search summary".
