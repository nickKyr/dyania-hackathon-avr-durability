import json
import pathlib
import re
import pandas as pd

from _inputs import require, require_extracts, require_glob

DATA = pathlib.Path("data")
OUT_DIR = DATA / "raw_tables"
OUT_XLSX = DATA / "raw_tables.xlsx"
JSON_DIR = DATA / "llm_json"
LLM = "notes-llm (claude-sonnet, 16 Sep 2026)"
RGX = "notes-regex (scripts/01_extract_rules.py)"


def add_duplicate_flags(df, ignore):
    cols = [c for c in df.columns if c not in ignore]
    key = pd.util.hash_pandas_object(df[cols], index=False)
    sizes = key.map(key.value_counts())
    first = ~key.duplicated()
    return df.assign(dup_group_size=sizes.values, is_exact_duplicate=(~first).values)


def parse_number(s):
    v = pd.to_numeric(s, errors="coerce")
    censored = s.astype(str).str.match(r"^\s*[<>]=?\s*[\d.]")
    direction = s.astype(str).str.extract(r"^\s*([<>]=?)")[0].where(censored)
    v2 = pd.to_numeric(s.astype(str).str.replace(r"^\s*[<>]=?\s*", "", regex=True).str.replace(",", ""), errors="coerce").where(censored)
    return v.fillna(v2), censored.fillna(False), direction


def load_notes_meta():
    n = pd.read_excel(DATA / "notes_deidentified.xlsx")
    n["note_id"] = ["N%03d" % i for i in range(1, len(n) + 1)]
    meta = pd.DataFrame(dict(
        note_id=n.note_id, patient=n["Profile Key"], note_type=n.Type, service=n.Service, signed_status=n["Signed Status"],
        author_type=n["Authoring Provider Type"], author_specialty=n["Authoring Provider Specialty"], service_year=n["Service Date"],
        creation_year=n["Creation Date"], last_edited_year=n["Last Edited Date"], n_characters=n.Notes.str.len(),
        n_words=n.Notes.str.split().str.len(), n_date_tokens=n.Notes.str.count(r"\[DATE\]"), n_name_tokens=n.Notes.str.count(r"\[NAME\]"),
        n_age_tokens=n.Notes.str.count(r"\[AGE\]"), source_file="notes_deidentified.xlsx", source_row=range(1, len(n) + 1),
    ))
    dates = [dict(note_id=r.note_id, patient=r["Profile Key"], date_string=d, method="regex") for _, r in n.iterrows() for d in sorted(set(re.findall(r"\b\d{1,2}/(?:19|20)\d{2}\b|\b(?:19|20)\d{2}\b", r.Notes)))]
    return meta, pd.DataFrame(dates)


def load_llm():
    docs = [json.loads(f.read_text()) for f in sorted(JSON_DIR.glob("N*.json"))]
    ops, status, echo, stmts, reint, ctx, notes_extra, dates = [], [], [], [], [], [], [], []
    for d in docs:
        nid, pat, yr = d["note_id"], d["patient"], d.get("service_year")
        base = dict(note_id=nid, patient=pat, service_year=yr, method=LLM)
        o = d.get("operation_in_this_note") or {}
        ops.append(dict(base, is_operative_report=d.get("is_operative_report"), aortic_valve_intervention=o.get("aortic_valve_intervention"), valve_model_as_written=o.get("valve_model_as_written"), valve_model_normalised=o.get("valve_model_normalised"), manufacturer=o.get("manufacturer"), valve_size_mm=o.get("valve_size_mm"), tavr_access=o.get("tavr_access"), concomitant_procedures="; ".join(o.get("concomitant_procedures") or []), native_valve_morphology=o.get("native_valve_morphology"), prior_cardiac_surgery_mentioned=o.get("prior_cardiac_surgery_mentioned"), cross_clamp_minutes=o.get("cross_clamp_minutes"), bypass_minutes=o.get("bypass_minutes"), procedure_text=o.get("procedure_summary"), evidence=o.get("evidence")))
        ps = d.get("prosthetic_aortic_valve_status") or {}
        status.append(dict(base, has_prosthetic_aortic_valve=ps.get("patient_has_prosthetic_aortic_valve_at_time_of_note"), approach=ps.get("approach_of_existing_valve"), valve_model_as_written=ps.get("existing_valve_model_as_written"), valve_model_normalised=ps.get("existing_valve_model_normalised"), valve_size_mm=ps.get("existing_valve_size_mm"), implant_date_as_written=ps.get("implant_date_as_written"), evidence=ps.get("evidence")))
        for i, e in enumerate(d.get("echo_studies") or [], start=1):
            common = dict(base, study_index=i, study_label=e.get("study_label"), date_as_written=e.get("date_as_written"), timing=e.get("timing_relative_to_aortic_valve_intervention"), valve_assessed=e.get("valve_assessed"), evidence=e.get("evidence"))
            echo.append(dict(common, parameter="study_recorded", value_num=None, value_text=e.get("study_label") or "echo study mentioned", unit=None))
            for param, unit in [("lvef_percent", "%"), ("peak_gradient_mmhg", "mmHg"), ("mean_gradient_mmhg", "mmHg"), ("dvi", ""), ("aortic_valve_area_cm2", "cm2"), ("aortic_valve_area_indexed_cm2_m2", "cm2/m2"), ("peak_velocity_m_s", "m/s")]:
                if e.get(param) is not None:
                    echo.append(dict(common, parameter=param, value_num=e.get(param), value_text=None, unit=unit))
            for param in ["aortic_regurgitation_grade", "regurgitation_location", "aortic_stenosis_severity_as_written", "leaflet_or_prosthesis_description", "lvot_velocity_or_vti", "other_valves_and_ventricle"]:
                if e.get(param):
                    echo.append(dict(common, parameter=param, value_num=None, value_text=e.get(param), unit=None))
        for s in d.get("prosthesis_status_statements") or []:
            stmts.append(dict(base, statement=s.get("statement"), category=s.get("category"), date_as_written=s.get("date_as_written")))
        for r in d.get("reinterventions_on_aortic_valve") or []:
            reint.append(dict(base, type=r.get("type"), date_as_written=r.get("date_as_written"), reason_as_written=r.get("reason_as_written"), device_as_written=r.get("device_as_written"), evidence=r.get("evidence")))
        c = d.get("clinical_context") or {}
        ctx.append(dict(base, sex_as_written=c.get("sex_as_written"), age_as_written=c.get("age_as_written"), height_weight_bsa_bmi_as_written=c.get("height_weight_bsa_bmi_as_written"), nyha_or_symptoms=c.get("nyha_or_symptoms"), **{f"comorbidity_{k}": v for k, v in (c.get("comorbidities") or {}).items()}, antithrombotic_therapy_as_written=c.get("antithrombotic_therapy_as_written"), statin_as_written=c.get("statin_as_written")))
        notes_extra.append(dict(base, extraction_notes=d.get("extraction_notes")))
        for ds in d.get("dates_in_text") or []:
            dates.append(dict(note_id=nid, patient=pat, date_string=ds, method=LLM))
    return dict(ops=pd.DataFrame(ops), status=pd.DataFrame(status), echo=pd.DataFrame(echo), stmts=pd.DataFrame(stmts), reint=pd.DataFrame(reint), ctx=pd.DataFrame(ctx), extra=pd.DataFrame(notes_extra), dates=pd.DataFrame(dates))


def load_regex():
    x = pd.ExcelFile(DATA / "structured_extraction.xlsx")
    imp = x.parse("implants")
    ops = imp[imp.note_type == "Operative Report"]
    ops = pd.DataFrame(dict(note_id=ops.note_id, patient=ops.patient, service_year=ops.implant_year, method=RGX, is_operative_report=True, aortic_valve_intervention=ops.approach, valve_model_as_written=ops.model_snippet, valve_model_normalised=ops.valve_model, manufacturer=ops.manufacturer, valve_size_mm=ops.valve_size_mm, tavr_access=ops.tavr_access, concomitant_procedures=ops.concomitant_procedures, native_valve_morphology=ops.native_valve_morphology, prior_cardiac_surgery_mentioned=ops.redo_sternotomy.map({True: "yes", False: "not stated"}), cross_clamp_minutes=None, bypass_minutes=None, procedure_text=ops.procedure_line, evidence=ops.model_snippet, valve_in_valve_flag=ops.valve_in_valve, valve_name_redacted=ops.valve_name_redacted, structured_implant_block=ops.structured_implant_block, extraction_confidence=ops.extraction_confidence))
    fm = imp[imp.note_type == "follow-up mention"]
    status = pd.DataFrame(dict(note_id=fm.note_id, patient=fm.patient, service_year=fm.mention_year, method=RGX, has_prosthetic_aortic_valve="yes", approach=fm.approach, valve_model_as_written=fm.model_snippet, valve_model_normalised=fm.valve_model, valve_size_mm=fm.valve_size_mm, implant_date_as_written=fm.implant_date_mention, evidence=fm.procedure_line))
    ev = x.parse("echo_values")
    echo = pd.DataFrame(dict(note_id=ev.note_id, patient=ev.patient, service_year=ev.note_year, method=RGX, study_index=None, study_label=None, date_as_written=None, timing=None, valve_assessed=ev.valve_context.replace({"n/a": None, "unknown": "unclear"}), evidence=ev.snippet, parameter=ev.parameter.replace({"mean_gradient": "mean_gradient_mmhg", "peak_gradient": "peak_gradient_mmhg", "aortic_valve_area": "aortic_valve_area_cm2", "aortic_valve_area_indexed": "aortic_valve_area_indexed_cm2_m2", "lvef": "lvef_percent", "peak_velocity": "peak_velocity_m_s"}), value_num=pd.to_numeric(ev.value, errors="coerce"), value_text=ev.value.where(pd.to_numeric(ev.value, errors="coerce").isna()), unit=ev.unit))
    events = x.parse("events").rename(columns={"note_year": "service_year"}).assign(method=RGX)
    return ops, status, echo, events


def load_labs():
    L = pd.read_excel(DATA / "labs_deidentified.xlsx")
    L = L.rename(columns={"Row": "source_row"}).assign(source_file="labs_deidentified.xlsx", lab_row_id=["L%05d" % i for i in range(1, len(L) + 1)])
    L = add_duplicate_flags(L, ignore=["source_row", "lab_row_id", "source_file"])
    v, censored, direction = parse_number(L["String Value"].where(L["Numeric Value"].isna(), L["Numeric Value"]))
    L["value_num"] = L["Numeric Value"].fillna(v)
    L["is_censored"] = censored.values
    L["censor_direction"] = direction.values
    L["unit_normalised_lower"] = L["Unit"].astype(str).str.lower().str.replace(r"\s+", "", regex=True).where(L["Unit"].notna())
    ref = L["Reference Values"].astype(str).str.extract(r"Low:\s*([\d.]+)\s*High:\s*([\d.]+)")
    L["ref_low_parsed"] = pd.to_numeric(ref[0], errors="coerce")
    L["ref_high_parsed"] = pd.to_numeric(ref[1], errors="coerce")
    return L


def load_meds():
    M = pd.read_excel(DATA / "medications_deidentified.xlsx")
    M = M.assign(source_file="medications_deidentified.xlsx", source_row=range(1, len(M) + 1), med_row_id=["M%05d" % i for i in range(1, len(M) + 1)])
    M = add_duplicate_flags(M, ignore=["source_row", "med_row_id", "source_file"])
    dx, rx = [], []
    for _, r in M.iterrows():
        if isinstance(r["Associated Diagnoses"], str):
            for d in json.loads(r["Associated Diagnoses"]):
                for c in d.get("icd10s", []):
                    dx.append(dict(med_row_id=r.med_row_id, patient=r.Patient, start_year=r["Start Date"], caboodle_key=d.get("caboodle_key"), diagnosis_name=d.get("name"), icd10_code=c.get("code"), icd10_name=c.get("name")))
        if isinstance(r["Rx Norm Codes"], str):
            for code in json.loads(r["Rx Norm Codes"]):
                rx.append(dict(med_row_id=r.med_row_id, patient=r.Patient, rxnorm_code=code))
    return M, pd.DataFrame(dx), pd.DataFrame(rx)


def main():
    require_extracts(DATA)
    require(
        DATA / "structured_extraction.xlsx",
        hint="Run scripts/01_extract_rules.py first.",
    )
    require_glob(
        JSON_DIR,
        "N*.json",
        hint=(
            "This directory holds one JSON file per note from the language-model pass over\n"
            "notes_deidentified.xlsx. It is not produced by these scripts: ask whoever ran the\n"
            "pass for a copy. See scripts/README.md."
        ),
    )
    OUT_DIR.mkdir(exist_ok=True)
    notes, dates_rgx = load_notes_meta()
    llm = load_llm()
    ops_rgx, status_rgx, echo_rgx, events_rgx = load_regex()
    labs, meds = load_labs(), load_meds()
    meds, diagnoses, rxnorm = meds
    lab_pts, med_pts = set(labs.Patient), set(meds.Patient)
    patients = notes.groupby("patient").agg(n_notes=("note_id", "size"), first_note_year=("service_year", "min"), last_note_year=("service_year", "max")).reset_index()
    patients["in_labs_file"] = patients.patient.isin(lab_pts)
    patients["in_medications_file"] = patients.patient.isin(med_pts)
    patients["n_lab_rows"] = patients.patient.map(labs.Patient.value_counts()).fillna(0).astype(int)
    patients["n_medication_rows"] = patients.patient.map(meds.Patient.value_counts()).fillna(0).astype(int)
    tables = {
        "patients": patients,
        "notes": notes,
        "note_operations": pd.concat([llm["ops"], ops_rgx], ignore_index=True),
        "note_prosthesis_status": pd.concat([llm["status"], status_rgx], ignore_index=True),
        "echo_measurements": pd.concat([llm["echo"], echo_rgx], ignore_index=True),
        "prosthesis_statements": llm["stmts"],
        "reinterventions": llm["reint"],
        "events_regex": events_rgx,
        "clinical_context": llm["ctx"],
        "dates_in_text": pd.concat([llm["dates"], dates_rgx], ignore_index=True).drop_duplicates(),
        "extraction_notes": llm["extra"],
        "labs_raw": labs,
        "meds_raw": meds,
        "diagnoses": diagnoses,
        "rxnorm_codes": rxnorm,
    }
    readme = pd.DataFrame([
        ("patients", "patient", "one row per pseudonym; which source files cover the patient and how many rows each has", ""),
        ("notes", "note_id", "note metadata; the text itself stays in notes_deidentified.xlsx and is joined by note_id", "notes_deidentified.xlsx row order"),
        ("note_operations", "note_id, method", "what the note says about an operation it documents; two readings per operative report: regex and LLM", "method distinguishes readings"),
        ("note_prosthesis_status", "note_id, method", "whether a prosthetic aortic valve exists at the time of the note, with model, size and implant date as written", ""),
        ("echo_measurements", "note_id, method, study_index, parameter", "long format: one row per measurement; LLM rows are grouped into studies with timing and valve_assessed; regex rows have no study grouping", "value_num or value_text, unit, evidence"),
        ("prosthesis_statements", "note_id, row", "quoted sentences about prosthesis function with a category", "LLM only"),
        ("reinterventions", "note_id, row", "aortic valve reinterventions with type, date and reason as written", "LLM only"),
        ("events_regex", "note_id, row", "keyword hits for failure, valve-in-valve, redo, endocarditis, thrombosis, leak, mismatch, with negation flag", "regex only"),
        ("clinical_context", "note_id", "sex, age token, body size, symptoms, comorbidities and therapy as written", "LLM only"),
        ("dates_in_text", "note_id, date_string", "partial or full dates that survived redaction", "both methods"),
        ("extraction_notes", "note_id", "the LLM extractor's remarks on ambiguities and contradictions", ""),
        ("labs_raw", "lab_row_id", "all 43,550 rows unchanged, plus duplicate flags, a parsed numeric value, censoring flag and direction, lower-cased unit, parsed reference range", "no rows dropped"),
        ("meds_raw", "med_row_id", "all 5,807 rows unchanged, plus duplicate flags", "no rows dropped"),
        ("diagnoses", "med_row_id, icd10_code", "Associated Diagnoses JSON exploded", ""),
        ("rxnorm_codes", "med_row_id, rxnorm_code", "Rx Norm Codes JSON exploded", ""),
    ], columns=["table", "key", "contents", "notes"])
    with pd.ExcelWriter(OUT_XLSX, engine="openpyxl") as xw:
        readme.to_excel(xw, sheet_name="README", index=False)
        for name, df in tables.items():
            df.to_excel(xw, sheet_name=name, index=False)
            df.to_parquet(OUT_DIR / f"{name}.parquet", index=False)
        for ws in xw.book.worksheets:
            ws.freeze_panes = "B2"
    for name, df in tables.items():
        print(f"{name}: {df.shape[0]} rows x {df.shape[1]} cols")


if __name__ == "__main__":
    main()
