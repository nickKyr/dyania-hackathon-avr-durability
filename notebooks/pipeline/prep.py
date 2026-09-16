import re
import numpy as np
import pandas as pd

CONFIG = dict(
    drop_exact_duplicates=True,
    last_valid_year=2026,
    lab_lookback_years=2,
    med_modes=("Outpatient",),
    reference_window_years=1,
    reference_prefers_gradient=True,
    fill_from_rules=True,
    ppm_excludes_echo_events=False,
    use_written_dates=True,
    event_year_rule="midpoint",
    require_eoa_or_dvi_confirmation=False,
    hvd_without_reference=False,
    censor_at_last_echo=True,
    horizons=(2, 5),
    fixed_landmarks=(0, 1, 3, 5),
)

LLM = "notes-llm"
VALVE_PROCEDURES = {"SAVR", "TAVR", "redo SAVR", "valve-in-valve TAVR"}
OPERATION_NOTE_TYPES = {"Operative Report", "Procedures", "Discharge Summary"}
SIGNED_RANK = {"Signed": 0, "Addendum": 0, "Unsigned": 1, "Deleted": 2}
MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}

ANALYTES = {
    "creatinine": (["Creatinine", "Creatinine (POCT)", "Creatinine, Blood", "CREATEXT"], "mg/dL"),
    "egfr": (["eGFR-All Other Races", "GFR Estimated", "GFR Estimated (POCT)", "eGFR (POCT)"], "mL/min/1.73m2"),
    "calcium_total": (["Calcium", "Calcium, Total"], "mg/dL"),
    "calcium_ionized": (["Calcium Ionized, Whole Blood", "Calcium Ionized, pH corrected", "Ionized Calcium"], "mmol/L"),
    "phosphorus": (["Phosphorus"], "mg/dL"),
    "alkaline_phosphatase": (["Alkaline Phosphatase"], "U/L"),
    "albumin": (["Albumin"], "g/dL"),
    "hemoglobin": (["Hemoglobin", "Hemoglobin Total, Whole Blood", "Hemoglobin, Whole Blood", "Total Hemoglobin (POCT)"], "g/dL"),
    "platelets": (["Platelet Count"], "10^3/uL"),
    "inr": (["PT INR", "INR", "INR (POCT)"], ""),
    "hba1c": (["Hemoglobin A1C"], "%"),
    "ldl": (["LDL Cholesterol", "LDL Cholesterol, Calculated"], "mg/dL"),
    "nt_probnp": (["NT Pro BNP", "ProBNP"], "pg/mL"),
    "lvef_lab": (["LV Ejection Fraction"], "%"),
}
COMPONENT_TO_ANALYTE = {c: a for a, (names, _) in ANALYTES.items() for c in names}

MED_CLASSES = {
    "vka": dict(pharm=r"COUMARIN", name=r"warfarin"),
    "doac": dict(pharm=r"FACTOR XA|THROMBIN INHIBITOR", name=r"apixaban|rivaroxaban|edoxaban|dabigatran"),
    "antiplatelet": dict(pharm=r"PLATELET AGGREGATION", name=r"aspirin|clopidogrel|ticagrelor|prasugrel"),
    "statin": dict(pharm=r"STATIN", name=r"statin\b|atorvastatin|rosuvastatin|simvastatin|pravastatin"),
    "raas_inhibitor": dict(pharm=r"ACE INHIBITOR|ANGIOTENSIN RECEPT", name=r"pril\b|sartan"),
    "loop_diuretic": dict(pharm=r"LOOP DIURETIC", name=r"furosemide|torsemide|bumetanide"),
    "sglt2_inhibitor": dict(pharm=r"SGLT2", name=r"gliflozin"),
    "calcium_or_vitamin_d": dict(pharm=r"CALCIUM REPLACEMENT|VITAMIN D", name=r"calcitriol|ergocalciferol|cholecalciferol"),
}
NOTE_THERAPY_PATTERNS = {
    "vka": r"warfarin|coumadin",
    "doac": r"apixaban|eliquis|rivaroxaban|xarelto|edoxaban|dabigatran|pradaxa",
    "antiplatelet": r"aspirin|\basa\b|clopidogrel|plavix|ticagrelor|brilinta|prasugrel",
    "statin": r"statin|lipitor|crestor|zocor|pravachol",
}

AR_GRADES = {"none": 0.0, "trace": 0.5, "trivial": 0.5, "mild": 1.0, "mild-moderate": 1.5, "moderate": 2.0, "moderate-severe": 2.5, "severe": 3.0}
NON_STRUCTURAL_CATEGORIES = {"endocarditis", "thrombosis/leaflet thickening", "paravalvular leak", "patient-prosthesis mismatch"}
NON_STRUCTURAL_REASON = r"endocardit|infect|thromb|paravalv|perivalv|leak|mismatch"
VALVE_TYPES = [
    ("sutureless", r"perceval"),
    ("stentless", r"freestyle|homograft"),
    ("balloon-expandable transcatheter", r"sapien"),
    ("self-expanding transcatheter", r"evolut|corevalve|navitor|portico|acurate"),
    ("bovine pericardial", r"pericardial|perimount|magna|trifecta|inspiris|carpentier|konect|mitroflow|avalus"),
    ("porcine", r"porcine|epic|biocor|mosaic|hancock"),
]


def is_llm(method):
    return method.fillna("").str.startswith(LLM)


def year_from_text(text):
    if not isinstance(text, str):
        return None
    years = re.findall(r"(?<!\d)((?:19|20)\d{2})(?!\d)", text)
    return int(years[-1]) if years else None


def month_from_text(text):
    if not isinstance(text, str):
        return None
    m = re.match(r"\s*(\d{1,2})/(?:\d{1,2}/)?(?:19|20)\d{2}", text)
    if m and 1 <= int(m.group(1)) <= 12:
        return int(m.group(1))
    m = re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b", text.lower())
    return MONTHS[m.group(1)] if m else None


def valve_type(model):
    if not isinstance(model, str):
        return None
    for label, pattern in VALVE_TYPES:
        if re.search(pattern, model, re.I):
            return label
    return None


def model_level(model):
    if not isinstance(model, str) or not model:
        return "unknown"
    if "inferred" in model:
        return "inferred"
    if "unspecified" in model or model.strip().lower() in {"carpentier-edwards", "st. jude", "edwards"}:
        return "family"
    return "exact"


def most_specific(names):
    names = [n for n in names if isinstance(n, str) and n]
    if not names:
        return None
    rank = {"exact": 0, "inferred": 1, "family": 2, "unknown": 3}
    return min(names, key=lambda n: (rank[model_level(n)], -len(n.split()), -len(n)))


def approach_family(procedure):
    if not isinstance(procedure, str):
        return None
    if "TAVR" in procedure:
        return "TAVR"
    if "SAVR" in procedure:
        return "SAVR"
    return None


def first_valid(values):
    for v in values:
        if v is not None and not (isinstance(v, float) and np.isnan(v)) and v is not pd.NA:
            return v
    return None


def build_cohort(raw):
    notes, ops, status = raw["notes"], raw["note_operations"], raw["note_prosthesis_status"]
    op_report = set(notes.loc[notes.note_type == "Operative Report", "patient"])
    op_llm = set(ops.loc[is_llm(ops.method) & ops.aortic_valve_intervention.isin(VALVE_PROCEDURES), "patient"])
    has_valve = set(status.loc[status.has_prosthetic_aortic_valve.eq("yes"), "patient"])
    p = raw["patients"][["patient", "in_labs_file", "first_note_year", "last_note_year"]].copy()
    p["group"] = np.where(p.in_labs_file, "structured history, one note", "operative notes, no structured data")
    p["has_operative_report"] = p.patient.isin(op_report)
    p["prosthesis_evidence"] = p.patient.isin(op_report | op_llm | has_valve)
    p["included"] = p.prosthesis_evidence
    p["exclusion_reason"] = np.where(p.included, "", "no evidence of an aortic valve prosthesis in any note")
    return p.drop(columns="in_labs_file")


def dedupe(df, config=CONFIG):
    if not config["drop_exact_duplicates"]:
        return df.assign(n_copies=1)
    return df[~df.is_exact_duplicate].assign(n_copies=lambda d: d.dup_group_size.astype(int))


def clean_labs(labs, config=CONFIG):
    mapped = labs["Lab Component Name"].map(COMPONENT_TO_ANALYTE)
    other = labs[mapped.isna()].copy()
    res = labs[mapped.notna()].assign(analyte=mapped[mapped.notna()])
    res = res[res["Result Date"] <= config["last_valid_year"]]
    clean = pd.DataFrame({
        "patient": res.Patient,
        "year": res["Result Date"].astype(int),
        "analyte": res.analyte,
        "component": res["Lab Component Name"],
        "value": res.value_num,
        "unit": res.analyte.map(lambda a: ANALYTES[a][1]),
        "is_censored": res.is_censored.astype(bool),
        "censor_direction": res.censor_direction,
        "n_copies": res.n_copies,
    }).dropna(subset=["value"])
    return clean.reset_index(drop=True), other


def _operation_notes(raw, cohort):
    notes = raw["notes"][["note_id", "note_type", "signed_status"]]
    ops = raw["note_operations"].merge(notes, on="note_id")
    ops = ops[ops.patient.isin(cohort.loc[cohort.included, "patient"]) & ops.note_type.isin(OPERATION_NOTE_TYPES)]
    llm = ops[is_llm(ops.method)].set_index("note_id")
    rules = ops[~is_llm(ops.method)].set_index("note_id")
    rows, conflicts = [], []
    for nid in sorted(set(llm.index) | set(rules.index)):
        m = llm.loc[nid] if nid in llm.index else None
        r = rules.loc[nid] if nid in rules.index else None
        m_proc = m.aortic_valve_intervention if m is not None and m.aortic_valve_intervention in VALVE_PROCEDURES else None
        r_proc = r.aortic_valve_intervention if r is not None and r.aortic_valve_intervention in {"SAVR", "TAVR"} else None
        procedure = m_proc or r_proc
        if procedure is None:
            continue
        base = m if m is not None else r
        if m_proc and r_proc and approach_family(m_proc) != approach_family(r_proc):
            conflicts.append(dict(patient=base.patient, note_id=nid, field="approach", model=m_proc, rules=r_proc, kept=m_proc))
        m_size = m.valve_size_mm if m is not None else None
        r_size = r.valve_size_mm if r is not None else None
        if pd.notna(m_size) and pd.notna(r_size) and m_size != r_size:
            conflicts.append(dict(patient=base.patient, note_id=nid, field="valve size", model=m_size, rules=r_size, kept=m_size))
        models = [m.valve_model_normalised if m is not None else None, r.valve_model_normalised if r is not None else None]
        rows.append(dict(
            patient=base.patient, note_id=nid, year=int(base.service_year), note_type=base.note_type, signed_status=base.signed_status,
            procedure=procedure, valve_model=most_specific(models), valve_size_mm=first_valid([m_size, r_size]),
            manufacturer=first_valid([m.manufacturer if m is not None else None, r.manufacturer if r is not None else None]),
            tavr_access=m.tavr_access if m is not None else None,
            native_valve_morphology=first_valid([m.native_valve_morphology if m is not None else None, r.native_valve_morphology if r is not None else None]),
            concomitant_procedures="; ".join(str(x) for x in [m.concomitant_procedures if m is not None else None, r.concomitant_procedures if r is not None else None] if isinstance(x, str) and x),
            name_redacted=bool(r.valve_name_redacted) if r is not None and pd.notna(r.valve_name_redacted) else False,
        ))
    return pd.DataFrame(rows), conflicts


def _merge_operation_group(g):
    g = g.assign(rank=g.signed_status.map(SIGNED_RANK).fillna(1)).sort_values(["rank", "note_type"])
    best = g.iloc[0]
    procedures = g.procedure.tolist()
    procedure = next((p for p in procedures if p in {"redo SAVR", "valve-in-valve TAVR"}), best.procedure)
    return dict(
        patient=best.patient, implant_year=best.year, implant_year_low=best.year, implant_year_high=best.year, implant_year_source="operation note",
        procedure=procedure, valve_model=most_specific(g.valve_model.tolist()), valve_size_mm=first_valid(g.valve_size_mm.tolist()),
        manufacturer=first_valid(g.manufacturer.tolist()), tavr_access=first_valid(g.tavr_access.tolist()),
        native_valve_morphology=first_valid(g.native_valve_morphology.tolist()),
        concomitant_cabg=bool(g.concomitant_procedures.str.contains(r"cabg|coronary|bypass graft", case=False).any()),
        name_redacted=bool(g.name_redacted.any()), source_notes=", ".join(g.note_id), n_duplicate_notes=len(g) - 1,
    )


def _peak_inpatient_year(meds, patient, upper):
    m = meds[(meds.Patient == patient) & (meds.Mode == "Inpatient") & (meds["Start Date"] <= upper)]
    if m.empty:
        return None
    return int(m.groupby("Start Date").size().idxmax())


def build_implants(raw, cohort, meds, config=CONFIG):
    op_notes, conflicts = _operation_notes(raw, cohort)
    episodes = [_merge_operation_group(g) for _, g in op_notes.groupby(["patient", "year"])] if len(op_notes) else []
    episodes = pd.DataFrame(episodes)
    status = raw["note_prosthesis_status"]
    status = status[is_llm(status.method) & status.has_prosthetic_aortic_valve.eq("yes")].copy()
    status["written_year"] = status.implant_date_as_written.map(year_from_text)
    reint = raw["reinterventions"].copy()
    reint["written_year"] = reint.date_as_written.map(year_from_text) if config["use_written_dates"] else None
    out = []
    for p in cohort.loc[cohort.included, "patient"]:
        e = episodes[episodes.patient == p].sort_values("implant_year").to_dict("records") if len(episodes) else []
        s = status[status.patient == p].sort_values("service_year")
        r = reint[reint.patient == p].sort_values("service_year")
        if not e:
            first_reint_year = r.service_year.min() if len(r) else None
            written = s.written_year.dropna()
            written = written[written != first_reint_year] if first_reint_year is not None else written
            note_year = int(s.service_year.max()) if len(s) else int(cohort.loc[cohort.patient == p, "last_note_year"].iloc[0])
            year, source = (int(written.iloc[0]), "date written in note") if len(written) else (None, None)
            if year is None:
                peak = _peak_inpatient_year(meds, p, note_year)
                if peak is not None and peak != first_reint_year:
                    year, source = peak, "peak inpatient medication year"
            proc = first_valid([a for a in s.approach if a in {"SAVR", "TAVR"}])
            e = [dict(
                patient=p, implant_year=year, implant_year_low=year, implant_year_high=year if year is not None else note_year,
                implant_year_source=source or "unknown (before last note)", procedure=proc,
                valve_model=most_specific(s[s.approach == proc].valve_model_normalised.tolist()) if proc else None,
                valve_size_mm=first_valid(s[s.approach == proc].valve_size_mm.tolist()) if proc else None,
                manufacturer=None, tavr_access=None, native_valve_morphology=None, concomitant_cabg=False, name_redacted=False,
                source_notes=", ".join(s.note_id), n_duplicate_notes=0,
            )]
            if len(r) and set(s.note_id) & set(r.note_id):
                conflicts.append(dict(patient=p, note_id=", ".join(sorted(set(s.note_id) & set(r.note_id))), field="index valve",
                                      model=proc, rules=None, kept=proc, detail="valve described in a note that also reports a reintervention; it may be the new valve"))
        for _, ri in r.iterrows():
            if ri.type not in {"redo SAVR", "valve-in-valve TAVR"}:
                continue
            prior_years = [x["implant_year"] for x in e if x["implant_year"] is not None]
            index_year = min(prior_years) if prior_years else None
            year = ri.written_year if pd.notna(ri.written_year) else None
            match = [x for x in e[1:] if approach_family(x["procedure"]) == approach_family(ri.type) and (year is None or x["implant_year"] is None or abs(x["implant_year"] - year) <= 1)]
            if match:
                continue
            low = index_year + 1 if index_year is not None else None
            high = int(ri.service_year)
            later = s[(s.service_year >= ri.service_year) & (s.approach == approach_family(ri.type))]
            e.append(dict(
                patient=p, implant_year=int(year) if year is not None else None, implant_year_low=int(year) if year is not None else low,
                implant_year_high=int(year) if year is not None else high,
                implant_year_source="date written in note" if year is not None else "unknown (between index and note)",
                procedure=ri.type, valve_model=most_specific(later.valve_model_normalised.tolist()),
                valve_size_mm=first_valid(later.valve_size_mm.tolist()), manufacturer=None, tavr_access=None, native_valve_morphology=None,
                concomitant_cabg=False, name_redacted=False, source_notes=ri.note_id, n_duplicate_notes=0,
            ))
        e = e[:1] + sorted(e[1:], key=lambda x: x["implant_year_high"] if x["implant_year"] is None else x["implant_year"])
        for i, x in enumerate(e, start=1):
            x["episode"] = i
            x["kind"] = "index" if i == 1 else "reintervention valve"
            nxt = e[i] if i < len(e) else None
            x["next_procedure"] = nxt["procedure"] if nxt else None
            x["next_procedure_year_low"] = nxt["implant_year_low"] if nxt else None
            x["next_procedure_year_high"] = nxt["implant_year_high"] if nxt else None
            if x["kind"] == "index" and len(s):
                limit = x["next_procedure_year_high"] if nxt else 9999
                same = s[(s.approach == approach_family(x["procedure"])) & (s.service_year < limit)]
                x["valve_model"] = most_specific([x["valve_model"]] + same.valve_model_normalised.tolist())
                x["valve_size_mm"] = first_valid([x["valve_size_mm"]] + same.valve_size_mm.tolist())
        out.extend(e)
    implants = pd.DataFrame(out)
    implants["approach"] = implants.procedure.map(approach_family)
    implants["model_level"] = implants.valve_model.map(model_level)
    implants["valve_type"] = implants.valve_model.map(valve_type)
    implants["episode_id"] = implants.patient + "-V" + implants.episode.astype(str)
    cols = ["episode_id", "patient", "episode", "kind", "procedure", "approach", "implant_year", "implant_year_low", "implant_year_high", "implant_year_source",
            "valve_model", "model_level", "valve_type", "manufacturer", "valve_size_mm", "tavr_access", "native_valve_morphology", "concomitant_cabg",
            "name_redacted", "next_procedure", "next_procedure_year_low", "next_procedure_year_high", "source_notes", "n_duplicate_notes"]
    for c in ["implant_year", "implant_year_low", "implant_year_high", "next_procedure_year_low", "next_procedure_year_high"]:
        implants[c] = implants[c].astype("Int64")
    return implants[cols], pd.DataFrame(conflicts)


def _studies(raw):
    e = raw["echo_measurements"]
    e = e[is_llm(e.method)]
    keys = ["note_id", "patient", "service_year", "study_index"]
    meta = e.groupby(keys, as_index=False).agg(date_as_written=("date_as_written", "first"), timing=("timing", "first"), valve_assessed=("valve_assessed", "first"))
    num = e[e.value_num.notna()].pivot_table(index=keys, columns="parameter", values="value_num", aggfunc="first").reset_index()
    txt = e[e.value_text.notna() & (e.parameter != "study_recorded")].pivot_table(index=keys, columns="parameter", values="value_text", aggfunc="first").reset_index()
    s = meta.merge(num, on=keys, how="left").merge(txt, on=keys, how="left")
    for c in ["mean_gradient_mmhg", "peak_gradient_mmhg", "dvi", "aortic_valve_area_cm2", "aortic_valve_area_indexed_cm2_m2", "peak_velocity_m_s", "lvef_percent", "aortic_regurgitation_grade", "regurgitation_location"]:
        if c not in s:
            s[c] = np.nan
    return s


RULE_FILL_PARAMETERS = ["mean_gradient_mmhg", "peak_gradient_mmhg", "dvi", "aortic_valve_area_cm2"]
HEMODYNAMIC = ["mean_gradient_mmhg", "peak_gradient_mmhg", "dvi", "aortic_valve_area_cm2", "ar_intraprosthetic"]


def _fill_from_rules(s, raw):
    e = raw["echo_measurements"]
    rules = e[~is_llm(e.method) & e.valve_assessed.eq("prosthetic") & e.parameter.isin(RULE_FILL_PARAMETERS) & e.value_num.notna()]
    rules = rules.groupby(["note_id", "parameter"]).value_num.apply(lambda v: set(v.round(2)))
    s = s.copy()
    s["values_from_rules"] = ""
    for param in RULE_FILL_PARAMETERS:
        for nid, g in s.groupby("note_id"):
            found = rules.get((nid, param))
            if not found:
                continue
            unused = found - set(g[param].dropna().round(2))
            missing = g.index[g[param].isna()]
            if len(unused) == 1 and len(missing) == 1:
                s.loc[missing[0], param] = next(iter(unused))
                s.loc[missing[0], "values_from_rules"] = (s.loc[missing[0], "values_from_rules"] + " " + param).strip()
    return s


def _assign_episode(study, eps, reint_notes):
    if eps.empty:
        return None
    later = eps[eps.episode > 1]
    target = later[later.source_notes.str.contains(study.note_id, regex=False)] if study.note_id in reint_notes else later.iloc[0:0]
    if len(target):
        t = target.iloc[0]
        before = pd.notna(t.implant_year) and study.study_year < t.implant_year
        if study.timing == "pre-operative" or before:
            return eps[eps.episode < t.episode].iloc[-1].episode_id
        return t.episode_id
    known = eps[eps.implant_year_low.fillna(-1) <= study.study_year]
    if study.timing == "pre-operative":
        known = known[known.implant_year_low.fillna(-1) < study.study_year]
    return known.iloc[-1].episode_id if len(known) else eps.iloc[0].episode_id


def build_echo_timeline(raw, implants, config=CONFIG):
    s = _studies(raw)
    s = s[s.valve_assessed.eq("prosthetic") & s.patient.isin(implants.patient)].copy()
    s = _fill_from_rules(s, raw) if config.get("fill_from_rules", False) else s.assign(values_from_rules="")
    written = s.date_as_written.map(year_from_text)
    s["study_year"] = np.where(config["use_written_dates"] & written.notna() & (written <= s.service_year), written, s.service_year).astype(int)
    s["study_month"] = s.date_as_written.map(month_from_text)
    reint_notes = set(raw["reinterventions"].note_id)
    s["episode_id"] = [_assign_episode(r, implants[implants.patient == r.patient].sort_values("episode"), reint_notes) for r in s.itertuples()]
    rules = raw["echo_measurements"]
    rules = rules[~is_llm(rules.method) & (rules.parameter == "mean_gradient_mmhg")].groupby("note_id").value_num.apply(set)
    s["mean_gradient_confirmed_by_rules"] = [pd.notna(v) and v in rules.get(n, set()) for n, v in zip(s.note_id, s.mean_gradient_mmhg)]
    grade = s.aortic_regurgitation_grade.str.lower().str.strip().map(AR_GRADES)
    pvl = s.regurgitation_location.str.lower().eq("paravalvular")
    s["ar_intraprosthetic"] = grade.where(~pvl)
    s["ar_paravalvular"] = grade.where(pvl)
    s["timing_rank"] = s.timing.map({"pre-operative": 0, "post-operative": 1}).fillna(1)
    s = s.sort_values(["patient", "study_year", "timing_rank", "study_month", "service_year", "note_id", "study_index"], na_position="last")
    numbers = ["mean_gradient_mmhg", "peak_gradient_mmhg", "dvi", "aortic_valve_area_cm2"]
    s["duplicate_of_earlier_study"] = s.duplicated(subset=["episode_id", "study_year"] + numbers) & s[numbers].notna().any(axis=1)
    s = s[~s.duplicate_of_earlier_study].copy()
    s["study_id"] = s.note_id + "-S" + s.study_index.astype(int).astype(str)
    imp = implants.set_index("episode_id")
    s["implant_year"] = s.episode_id.map(imp.implant_year)
    s["years_since_implant"] = s.study_year - s.implant_year
    s["is_reference"] = False
    for eid, g in s.groupby("episode_id"):
        post = g[g.timing.ne("pre-operative")]
        iy = imp.loc[eid, "implant_year"]
        if pd.notna(iy):
            post = post[(post.study_year >= iy) & (post.study_year <= iy + config["reference_window_years"])]
        else:
            post = post.iloc[0:0]
        if len(post) and config.get("reference_prefers_gradient", False):
            has_mg = post.mean_gradient_mmhg.notna()
            has_any = post[HEMODYNAMIC].notna().any(axis=1)
            post = post[has_mg] if has_mg.any() else post[has_any] if has_any.any() else post
        if len(post):
            s.loc[post.index[0], "is_reference"] = True
    ref_year = s[s.is_reference].set_index("episode_id").study_year
    s["years_since_reference"] = s.study_year - s.episode_id.map(ref_year)
    s["sequence"] = s.groupby("episode_id").cumcount() + 1
    cols = ["study_id", "episode_id", "patient", "note_id", "study_year", "study_month", "timing", "sequence", "is_reference", "implant_year", "years_since_implant", "years_since_reference",
            "mean_gradient_mmhg", "peak_gradient_mmhg", "peak_velocity_m_s", "dvi", "aortic_valve_area_cm2", "aortic_valve_area_indexed_cm2_m2", "lvef_percent",
            "ar_intraprosthetic", "ar_paravalvular", "mean_gradient_confirmed_by_rules", "values_from_rules"]
    return s[cols].reset_index(drop=True)


def _hvd_stage(study, ref, config):
    mg, ar = study.mean_gradient_mmhg, study.ar_intraprosthetic
    if ref is None:
        if not config["hvd_without_reference"]:
            return 0, None
        stage = 3 if (pd.notna(mg) and mg >= 40) or ar == 3 else 2 if (pd.notna(mg) and mg >= 30) or (pd.notna(ar) and ar >= 2) else 0
        return stage, "absolute threshold, no reference echo"
    dmg = mg - ref.mean_gradient_mmhg if pd.notna(mg) and pd.notna(ref.mean_gradient_mmhg) else np.nan
    dar = ar - (ref.ar_intraprosthetic if pd.notna(ref.ar_intraprosthetic) else 0) if pd.notna(ar) else np.nan
    eoa_drop = pd.notna(study.aortic_valve_area_cm2) and pd.notna(ref.aortic_valve_area_cm2) and (ref.aortic_valve_area_cm2 - study.aortic_valve_area_cm2 >= min(0.3, 0.25 * ref.aortic_valve_area_cm2))
    dvi_drop = pd.notna(study.dvi) and pd.notna(ref.dvi) and (ref.dvi - study.dvi >= min(0.1, 0.2 * ref.dvi))
    confirmed = eoa_drop or dvi_drop
    gradient_ok = confirmed or not config["require_eoa_or_dvi_confirmation"]
    if (pd.notna(dmg) and dmg >= 20 and mg >= 30 and gradient_ok) or (pd.notna(dar) and dar >= 2 and ar >= 3):
        return 3, "confirmed by EOA or DVI" if confirmed else "gradient or regurgitation only"
    if (pd.notna(dmg) and dmg >= 10 and mg >= 20 and gradient_ok) or (pd.notna(dar) and dar >= 1 and ar >= 2):
        return 2, "confirmed by EOA or DVI" if confirmed else "gradient or regurgitation only"
    return 0, None


def event_year(low, high, config=CONFIG):
    if pd.isna(low) or pd.isna(high):
        return high
    if config["event_year_rule"] == "upper":
        return high
    return int(np.ceil((low + high) / 2))


def build_events(raw, implants, echo_timeline, adjudication_csv=None, config=CONFIG):
    rows = []
    for eid, g in echo_timeline.groupby("episode_id"):
        g = g.sort_values("sequence")
        refs = g[g.is_reference]
        ref = refs.iloc[0] if len(refs) else None
        after = g[g.study_year > ref.study_year] if ref is not None else g
        last_clear = ref.study_year if ref is not None else None
        for st in after.itertuples():
            stage, basis = _hvd_stage(st, ref, config)
            if stage:
                rows.append(dict(episode_id=eid, patient=st.patient, source="echo", event_type=f"HVD stage {stage}", note_id=st.note_id,
                                 year_low=last_clear, year_high=st.study_year, detail=basis, reason_as_written=None))
                break
            last_clear = st.study_year
    imp = implants.set_index("episode_id")
    for x in implants[implants.episode > 1].itertuples():
        prev = implants[(implants.patient == x.patient) & (implants.episode == x.episode - 1)].iloc[0]
        ri = raw["reinterventions"]
        ri = ri[(ri.patient == x.patient) & ri.note_id.isin(x.source_notes.split(", "))]
        rows.append(dict(episode_id=prev.episode_id, patient=x.patient, source="reintervention", event_type=f"reintervention: {x.procedure}", note_id=x.source_notes,
                         year_low=x.implant_year_low, year_high=x.implant_year_high, detail="BVF stage 2",
                         reason_as_written="; ".join(ri.reason_as_written.dropna()) or None))
    for ri in raw["reinterventions"][~raw["reinterventions"].type.isin(["redo SAVR", "valve-in-valve TAVR"])].itertuples():
        eps = implants[implants.patient == ri.patient].sort_values("episode")
        if eps.empty:
            continue
        cur = eps.iloc[-1]
        y = year_from_text(ri.date_as_written)
        low = y if y else (cur.implant_year + 1 if pd.notna(cur.implant_year) else None)
        rows.append(dict(episode_id=cur.episode_id, patient=ri.patient, source="reintervention", event_type=f"reintervention: {ri.type}", note_id=ri.note_id,
                         year_low=low, year_high=y or ri.service_year, detail="BVF stage 2", reason_as_written=ri.reason_as_written))
    ev = pd.DataFrame(rows)
    ev["year_low"] = ev.year_low.astype("Int64")
    ev["year_high"] = ev.year_high.astype("Int64")
    ev["event_year"] = [event_year(lo, hi, config) for lo, hi in zip(ev.year_low, ev.year_high)]
    stm = raw["prosthesis_statements"]
    nonstruct = stm[stm.category.isin(NON_STRUCTURAL_CATEGORIES)]
    kw = raw["events_regex"]
    kw = kw[~kw.negated & kw.event_type.str.contains("endocard|thromb", case=False, na=False)]
    endo = raw["clinical_context"]
    endo = endo.loc[endo.comorbidity_endocarditis_history.eq("yes"), ["patient", "service_year"]]
    provisional = []
    for x in ev.itertuples():
        start = imp.loc[x.episode_id, "implant_year_low"]
        start = -1 if pd.isna(start) else start
        high = 9999 if pd.isna(x.year_high) else x.year_high
        causes = set(nonstruct[(nonstruct.patient == x.patient) & (nonstruct.service_year >= start) & (nonstruct.service_year <= high)].category)
        if x.source == "echo" and not config.get("ppm_excludes_echo_events", True):
            causes.discard("patient-prosthesis mismatch")
        in_window = lambda d: d[(d.patient == x.patient) & (d.service_year >= start) & (d.service_year <= high)]
        if len(in_window(endo)) or len(in_window(kw)):
            causes.add("endocarditis or thrombosis mentioned")
        if isinstance(x.reason_as_written, str) and re.search(NON_STRUCTURAL_REASON, x.reason_as_written, re.I):
            causes.add("reason as written")
        provisional.append("; ".join(sorted(causes)))
    ev["non_structural_evidence"] = provisional
    ev["is_structural"] = ev.non_structural_evidence.eq("")
    ev["varc3_category"] = np.where(ev.is_structural, ev.detail, "non-structural (provisional)")
    ev["adjudicated"] = False
    ev["event_id"] = ev.episode_id + "-" + ev.groupby("episode_id").cumcount().add(1).astype(str).radd("E")
    if adjudication_csv is not None and adjudication_csv.exists():
        adj = pd.read_csv(adjudication_csv).set_index("event_id")
        hit = ev.event_id.isin(adj.index)
        ev.loc[hit, "is_structural"] = ev.loc[hit, "event_id"].map(adj.is_structural.astype(str).str.upper().str.startswith("Y"))
        ev.loc[hit, "varc3_category"] = ev.loc[hit, "event_id"].map(adj.varc3_category)
        ev.loc[hit, "adjudicated"] = True
    cols = ["event_id", "episode_id", "patient", "source", "event_type", "year_low", "year_high", "event_year", "is_structural", "varc3_category",
            "non_structural_evidence", "adjudicated", "reason_as_written", "note_id", "detail"]
    return ev[cols].sort_values(["patient", "episode_id", "event_year"]).reset_index(drop=True)


def last_contact(raw, labs, meds, config=CONFIG):
    years = pd.concat([
        raw["notes"][["patient", "service_year"]].rename(columns={"service_year": "year"}),
        labs[["Patient", "Result Date"]].set_axis(["patient", "year"], axis=1),
        meds[["Patient", "Start Date"]].set_axis(["patient", "year"], axis=1),
    ])
    years = years[years.year <= config["last_valid_year"]]
    return years.groupby("patient").year.max()


def build_follow_up(implants, events, echo_timeline, contact, config=CONFIG):
    rows = []
    structural = events[events.is_structural]
    ref = echo_timeline[echo_timeline.is_reference].set_index("episode_id").study_year
    last_echo = echo_timeline.groupby("episode_id").study_year.max()
    for x in implants.itertuples():
        ev = structural[structural.episode_id == x.episode_id].sort_values("event_year")
        end_contact = contact.get(x.patient)
        nxt = x.next_procedure_year_high if pd.notna(x.next_procedure_year_high) else None
        nxt_low = x.next_procedure_year_low if pd.notna(x.next_procedure_year_low) else None
        if len(ev):
            end, status, reason = int(ev.iloc[0].event_year), "svd", ev.iloc[0].event_type
        elif nxt is not None:
            end, status, reason = int(event_year(nxt_low, nxt, config)), "censored", "non-structural reintervention"
        elif config["censor_at_last_echo"] and x.episode_id in last_echo.index:
            end, status, reason = int(last_echo[x.episode_id]), "censored", "last echo"
        else:
            end, status, reason = int(end_contact) if end_contact is not None else None, "censored", "last contact"
        start = ref.get(x.episode_id)
        rows.append(dict(episode_id=x.episode_id, patient=x.patient, implant_year=x.implant_year, reference_year=start, end_year=end, status=status, end_reason=reason,
                         last_contact_year=end_contact, follow_up_years=(end - start) if start is not None and end is not None else None, vital_status="not available"))
    f = pd.DataFrame(rows)
    for c in ["implant_year", "reference_year", "end_year", "last_contact_year", "follow_up_years"]:
        f[c] = f[c].astype("Int64")
    return f


def build_med_exposure(meds, raw, config=CONFIG):
    m = meds[meds.Mode.isin(config["med_modes"])]
    rows = []
    for cls, pat in MED_CLASSES.items():
        hit = m["Medication Pharmaceutical Class"].str.contains(pat["pharm"], case=False, na=False) | m["Simple Generic Name"].str.contains(pat["name"], case=False, na=False)
        rows.append(m.loc[hit, ["Patient", "Start Date"]].set_axis(["patient", "year"], axis=1).assign(drug_class=cls, source="medication file"))
    c = raw["clinical_context"]
    text = c.antithrombotic_therapy_as_written.fillna("") + " " + c.statin_as_written.fillna("")
    for cls, pat in NOTE_THERAPY_PATTERNS.items():
        hit = text.str.contains(pat, case=False)
        rows.append(c.loc[hit, ["patient", "service_year"]].set_axis(["patient", "year"], axis=1).assign(drug_class=cls, source="note text"))
    long = pd.concat(rows).drop_duplicates()
    long = long[long.year <= config["last_valid_year"]]
    return long.reset_index(drop=True)


def parse_body_size(text):
    if not isinstance(text, str):
        return None, None
    h = None
    m = re.search(r"(\d{3}(?:\.\d)?)\s*cm", text)
    if m:
        h = float(m.group(1))
    else:
        m = re.search(r"\b([12]\.\d{1,3})\s*m\b", text)
        if m:
            h = float(m.group(1)) * 100
        else:
            m = re.search(r"(\d)'\s*(\d{1,2}(?:\.\d)?)?", text)
            if m:
                h = (int(m.group(1)) * 12 + float(m.group(2) or 0)) * 2.54
    w = None
    m = re.search(r"(\d{2,3}(?:\.\d+)?)\s*kg", text)
    if m:
        w = float(m.group(1))
    else:
        m = re.search(r"(\d{2,3}(?:\.\d+)?)\s*lbs?\b", text)
        if m:
            w = float(m.group(1)) * 0.4536
    if h is not None and not 130 <= h <= 215:
        h = None
    if w is not None and not 30 <= w <= 250:
        w = None
    return h, w


def build_covariates(raw, cohort):
    c = raw["clinical_context"]
    body = c.height_weight_bsa_bmi_as_written.map(parse_body_size)
    c = c.assign(height_cm=[b[0] for b in body], weight_kg=[b[1] for b in body])
    rows = []
    comorb = [k for k in c.columns if k.startswith("comorbidity_")]
    for p, g in c.groupby("patient"):
        sex = g.sex_as_written[g.sex_as_written.isin(["male", "female"])]
        row = dict(patient=p, sex=sex.mode().iloc[0] if len(sex) else None, height_cm=g.height_cm.median(), weight_kg=g.weight_kg.median())
        for k in comorb:
            v = g[k]
            order = ["current", "former", "never"] if k == "comorbidity_smoking" else ["yes", "no"]
            row[k.replace("comorbidity_", "")] = next((o for o in order if v.eq(o).any()), "not stated")
        rows.append(row)
    cov = pd.DataFrame(rows)
    cov["bsa_m2"] = np.sqrt(cov.height_cm * cov.weight_kg / 3600)
    cov["bmi"] = cov.weight_kg / (cov.height_cm / 100) ** 2
    cov["age_at_implant"] = np.nan
    cov = cohort[cohort.included][["patient", "group"]].merge(cov, on="patient", how="left")
    return cov


def _slope(g):
    g = g.dropna(subset=["mean_gradient_mmhg"])
    if len(g) < 2:
        return np.nan
    a, b = g.iloc[-2], g.iloc[-1]
    dt = b.study_year - a.study_year
    return (b.mean_gradient_mmhg - a.mean_gradient_mmhg) / dt if dt > 0 else np.nan


def build_landmark(implants, echo_timeline, follow_up, lab_clean, med_exposure, covariates, config=CONFIG):
    rows = []
    fu = follow_up.set_index("episode_id")
    imp = implants.set_index("episode_id")
    cov = covariates.set_index("patient")
    look = config["lab_lookback_years"]
    labs_by_patient = dict(tuple(lab_clean.groupby("patient")))
    meds_by_patient = dict(tuple(med_exposure.groupby("patient")))
    empty_labs, empty_meds = lab_clean.iloc[0:0], med_exposure.iloc[0:0]
    for eid, g in echo_timeline.groupby("episode_id"):
        g = g.sort_values("sequence")
        if not g.is_reference.any():
            continue
        f = fu.loc[eid]
        ref = g[g.is_reference].iloc[0]
        r0 = int(ref.study_year)
        end = f.end_year
        if pd.isna(end):
            continue
        marks = {r0 + s: f"fixed +{s}y" for s in config["fixed_landmarks"]}
        for y in g.study_year[g.study_year > r0]:
            marks.setdefault(int(y), "echo")
        for L, kind in sorted(marks.items()):
            if L >= end:
                continue
            seen = g[g.study_year <= L]
            last = seen.iloc[-1]
            recent = seen[seen.study_year > L - 2]
            row = dict(
                episode_id=eid, patient=ref.patient, landmark_year=L, landmark_type=kind, years_since_reference=L - r0,
                years_since_implant=L - imp.loc[eid, "implant_year"] if pd.notna(imp.loc[eid, "implant_year"]) else np.nan,
                split_year=imp.loc[eid, "implant_year"],
                mean_gradient_latest=first_valid(seen.mean_gradient_mmhg[::-1].tolist()),
                mean_gradient_reference=ref.mean_gradient_mmhg,
                peak_gradient_latest=first_valid(seen.peak_gradient_mmhg[::-1].tolist()),
                dvi_latest=first_valid(seen.dvi[::-1].tolist()), dvi_reference=ref.dvi,
                eoa_latest=first_valid(seen.aortic_valve_area_cm2[::-1].tolist()), eoa_reference=ref.aortic_valve_area_cm2,
                eoa_indexed_latest=first_valid(seen.aortic_valve_area_indexed_cm2_m2[::-1].tolist()),
                ar_intraprosthetic_latest=first_valid(seen.ar_intraprosthetic[::-1].tolist()),
                ar_paravalvular_latest=first_valid(seen.ar_paravalvular[::-1].tolist()),
                lvef_latest=first_valid(seen.lvef_percent[::-1].tolist()),
                mean_gradient_slope=_slope(seen), n_echo=len(seen), n_echo_last_2y=len(recent),
                years_since_last_echo=L - int(last.study_year),
            )
            row["mean_gradient_change"] = row["mean_gradient_latest"] - ref.mean_gradient_mmhg if row["mean_gradient_latest"] is not None and pd.notna(ref.mean_gradient_mmhg) else np.nan
            for k in ["procedure", "approach", "valve_type", "model_level", "valve_size_mm", "native_valve_morphology", "concomitant_cabg", "kind"]:
                row[k if k != "kind" else "episode_kind"] = imp.loc[eid, k]
            if ref.patient in cov.index:
                for k, v in cov.loc[ref.patient].items():
                    row[k] = v
            pl = labs_by_patient.get(ref.patient, empty_labs)
            labs = pl[(pl.year <= L) & (pl.year > L - look)]
            for a in ANALYTES:
                v = labs[labs.analyte == a].sort_values("year").value
                row[f"lab_{a}"] = v.iloc[-1] if len(v) else np.nan
            pm = meds_by_patient.get(ref.patient, empty_meds)
            meds = pm[(pm.year <= L) & (pm.year > L - look)]
            for cls in MED_CLASSES:
                row[f"med_{cls}"] = cls in set(meds.drug_class)
            t = int(end) - L
            row["time_to_end"] = t
            row["status"] = f.status
            for h in config["horizons"]:
                row[f"svd_within_{h}y"] = 1 if f.status == "svd" and t <= h else (0 if t >= h or f.status == "death" else np.nan)
                row[f"death_within_{h}y"] = 1 if f.status == "death" and t <= h else (0 if t >= h or f.status == "svd" else np.nan)
            rows.append(row)
    return pd.DataFrame(rows)


def coverage_report(cohort, implants, echo_timeline, events, follow_up, landmark, conflicts, config=CONFIG):
    lines = {
        "patients in extract": len(cohort),
        "patients included": int(cohort.included.sum()),
        "valve episodes": len(implants),
        "episodes with known implant year": int(implants.implant_year.notna().sum()),
        "prosthetic echo studies": len(echo_timeline),
        "episodes with a reference echo": int(echo_timeline.groupby("episode_id").is_reference.any().sum()),
        "episodes with a follow-up echo after the reference": int((echo_timeline.years_since_reference > 0).groupby(echo_timeline.episode_id).any().sum()),
        "candidate events": len(events),
        "structural events (provisional unless adjudicated)": int(events.is_structural.sum()),
        "episodes ending in SVD": int(follow_up.status.eq("svd").sum()),
        "landmark rows": len(landmark),
        "landmark episodes": landmark.episode_id.nunique() if len(landmark) else 0,
        "rules vs model conflicts logged": len(conflicts),
        "deaths (competing risk)": "not in extract",
    }
    for h in config["horizons"]:
        col = f"svd_within_{h}y"
        if len(landmark) and col in landmark:
            lines[f"landmark rows with {h}-year outcome known"] = int(landmark[col].notna().sum())
            lines[f"landmark rows with SVD within {h} years"] = int(landmark[col].eq(1).sum())
    return pd.Series(lines, name="value").to_frame()
