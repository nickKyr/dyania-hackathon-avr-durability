import re
import json
import pandas as pd

from _inputs import require_extracts

DATA = "data"
OUT = "data/structured_extraction.xlsx"
SNIP = 140

MODELS = [
    ("Sapien 3 Ultra", r"s3 ultra|sapien 3 ultra|sapien ultra", "Edwards", "TAVR"),
    ("Sapien 3", r"sapien 3|sapien s3|sapien3|edwards s3|\bs3\b", "Edwards", "TAVR"),
    ("Sapien XT", r"sapien xt", "Edwards", "TAVR"),
    ("Sapien (unspecified)", r"sapien", "Edwards", "TAVR"),
    ("Sapien 3 Ultra (inferred, name redacted)", r"\[NAME\] ultra valve|\[NAME\] ultra", "Edwards", "TAVR"),
    ("Evolut FX", r"evolut fx", "Medtronic", "TAVR"),
    ("Evolut Pro", r"evolut pro|corevalue pro|corevalve pro", "Medtronic", "TAVR"),
    ("Evolut R", r"evolut r\b", "Medtronic", "TAVR"),
    ("Evolut (unspecified)", r"evolut|corevalve|corevalue", "Medtronic", "TAVR"),
    ("Navitor / Portico", r"navitor|portico", "Abbott", "TAVR"),
    ("Acurate", r"acurate", "Boston Scientific", "TAVR"),
    ("Trifecta", r"trifecta", "Abbott / St. Jude", "SAVR"),
    ("Biocor", r"biocor", "Abbott / St. Jude", "SAVR"),
    ("Epic", r"\bepic\b(?! care)", "Abbott / St. Jude", "SAVR"),
    ("Magna Ease", r"magna ease", "Edwards", "SAVR"),
    ("Magna", r"\bmagna\b", "Edwards", "SAVR"),
    ("Inspiris Resilia", r"inspiris|resilia", "Edwards", "SAVR"),
    ("Perimount", r"perimount|peri-mount", "Edwards", "SAVR"),
    ("Konect", r"konect", "Edwards", "SAVR"),
    ("Carpentier-Edwards pericardial", r"carpentier[- ]edwards|\bCE\b\s*#?\s*\d{2}|\(CE #\d{2}\)|\d{2}\s*(?:mm\s*)?CE\b|\bCE (?:valve|pericardial|bovine)", "Edwards", "SAVR"),
    ("Edwards (unspecified)", r"edwards (?:valve|bioprosthesis|pericardial)", "Edwards", "SAVR"),
    ("Mitroflow", r"mitroflow", "Sorin / LivaNova", "SAVR"),
    ("Perceval", r"perceval", "Sorin / LivaNova", "SAVR"),
    ("Hancock", r"hancock", "Medtronic", "SAVR"),
    ("Mosaic", r"mosaic", "Medtronic", "SAVR"),
    ("Avalus", r"avalus", "Medtronic", "SAVR"),
    ("Freestyle", r"freestyle", "Medtronic", "SAVR"),
    ("St. Jude (unspecified)", r"st\.? ?jude", "Abbott / St. Jude", "SAVR"),
    ("Pericardial (unspecified)", r"pericardial (?:tissue )?valve|bovine pericardial", "unknown", "SAVR"),
    ("Porcine (unspecified)", r"porcine", "unknown", "SAVR"),
]
TAVR_RE = r"transcatheter|\bTAVR\b|\bTAVI\b|transfemoral (?:implantation|aortic)|aortic valve insertion|sapien|evolut|corevalve|corevalue|navitor|portico|acurate"
SAVR_RE = r"aortic valve replacement|\bAVR\b|replacement of (?:the )?aortic valve|replaced (?:the )?aortic valve|aortic valve (?:was )?replaced|tissue implant type:|prosthesis was (?:seated|sutured|secured)"
OPEN_RE = r"sternotomy|thoracotomy|cardiopulmonary bypass|cardioplegia|aortotomy|cross.?clamp"
SIZE_RE = r"(?:#\s?|size\s*#?\s*|implant size:\s*|\bR)?(1[79]|2[0-9]|3[0-4])\s?-?\s?mm\b|#\s?(1[79]|2[0-9]|3[0-4])\b|size\s*#?\s*(1[79]|2[0-9]|3[0-4])\b|implant size:\s*(1[79]|2[0-9]|3[0-4])\b"
CONCOMITANT = {
    "CABG": r"\bCABG\b|coronary artery bypass|bypass grafting",
    "mitral": r"mitral valve (?:repair|replacement|annuloplasty)|\bMVR\b|\bMVr\b|\bMV repair",
    "tricuspid": r"tricuspid valve (?:repair|replacement|annuloplasty)|\bTVR\b|\bTV repair",
    "root_or_ascending": r"bentall|root replacement|root enlargement|ascending aort\w+ (?:replacement|graft)|hemiarch|arch replacement",
    "maze_or_LAA": r"\bmaze\b|appendage (?:ligation|clip|occlusion|exclusion)",
    "myectomy": r"myectomy",
}
ACCESS = {
    "transfemoral": r"transfemoral|\bTF\b|femoral (?:artery )?access|common femoral",
    "subclavian_or_axillary": r"subclavian|axillary",
    "transapical": r"transapical",
    "transaortic": r"transaortic|direct aortic",
    "transcarotid": r"transcarotid",
}
PROSTH_CTX = r"prosthetic|prosthesis|bioprosth|across the (?:surgical )?AVR|post[- ]?TAVR|post[- ]?AVR|s/p (?:transcatheter )?aortic valve replacement|s/p tavr|s/p avr|post tavr|post[- ]?op(?:erative)? echo|tavr|\bavr\b|trifecta|sapien|\bS3\b|evolut|magna|epic|perimount|\(CE #\d+\)|#\d{2}\)"
NATIVE_CTX = r"caused by (?:calcified|calcification|thickened|bicuspid)|native|aortic valve stenosis caused|calcified valve|severe (?:calcific )?aortic (?:valve )?stenosis|critical aortic stenosis|calcific aortic stenosis|heavily calcified|by planimetry|pre-?op(?:erative)? echo|bicuspid|tricuspid aortic valve\."
EVENTS = {
    "valve_in_valve": r"valve[- ]in[- ]valve|\bViV\b",
    "prosthetic_failure_language": r"prosthetic (?:aortic )?valve (?:failure|dysfunction|stenosis|degeneration)|bioprosthe\w+ (?:aortic )?(?:valve )?(?:failure|dysfunction|stenosis|degeneration)|failed (?:bio)?prosth|degenerat\w* (?:bio)?prosth|structural valve deterioration|\bSVD\b|prosthetic valve dysfunction|prosthetic thickening|prosthetic aortic valve failure",
    "redo_or_reintervention": r"redo (?:aortic valve replacement|avr|bioprosthetic avr)|redo (?:aortic )?(?:valve|root) (?:replacement|surgery)|re-?replacement of (?:the )?aortic|aortic valve re-?replacement|explant(?:ation)? of (?:the )?(?:aortic )?(?:valve|prosthesis|bioprosth)|(?:aortic )?(?:valve|prosthesis) (?:was )?explanted|redo sternotomy[^.\n]{0,40}(?:bio)?bentall",
    "redo_sternotomy_any": r"redo sternotomy|re-?do sternotomy",
    "endocarditis": r"endocarditis",
    "thrombosis_or_HALT": r"valve thrombosis|leaflet thickening|\bHALT\b|hypoattenuat",
    "paravalvular_leak": r"paravalvular|perivalvular|\bPVL\b",
    "patient_prosthesis_mismatch": r"prosthesis[- ]patient mismatch|patient[- ]prosthesis mismatch|\bPPM\b",
}
ECHO_PATTERNS = [
    ("mean_gradient", "mmHg", r"mean\s+(?:pressure\s+)?gradient(?:\s+is|\s+of|\s*[:=])?\s*(\d{1,3}(?:\.\d)?)\s*mm\s*hg"),
    ("mean_gradient", "mmHg", r"mean\s+(?:pressure\s+)?gradient(?:\s+is|\s+of|\s*[:=])?\s*(\d{1,3}(?:\.\d)?)(?!\s*mm\s*hg)(?=\s*(?:mmhg|mm hg|,|\.|and|with|;|\)))"),
    ("peak_gradient", "mmHg", r"peak\s+(?:pressure\s+)?gradient(?:\s+is|\s+of|\s*[:=])?\s*(\d{1,3}(?:\.\d)?)\s*(?:mm\s*hg)?"),
    ("peak_and_mean_gradient", "mmHg", r"(?:pk|peak)\s*/\s*(?:mn|mean)\s*(?:av\s+)?gradients?\s*(?:of\s*)?(\d{1,3})\s*/\s*(\d{1,3})\s*mm\s*hg"),
    ("peak_and_mean_gradient", "mmHg", r"gradient\s+pk\s*/\s*m\s*(\d{1,3})\s*/\s*(\d{1,3})\s*mm\s*hg"),
    ("peak_and_mean_gradient", "mmHg", r"peak\s*/\s*mean\s+(?:av\s+)?gradients?\s*(\d{1,3})\s*/\s*(\d{1,3})"),
    ("dvi", "", r"dimensionless (?:valve )?index(?:\s+is|\s+of|\s*[:=])?\s*(0?\.\d{1,2})"),
    ("dvi", "", r"\b(?:DVI|DI)\s*[:=]?\s*(0?\.\d{1,2})"),
    ("aortic_valve_area", "cm2", r"(?:AV area|AVA|aortic valve area|valve area|effective orifice area|EOA)(?:\s+is|\s+of|\s*[:=])?\s*(\d\.\d{1,2})\s*cm"),
    ("aortic_valve_area_indexed", "cm2/m2", r"\((\d\.\d{1,2})\s*cm²?\s*/\s*m²?\)"),
    ("peak_velocity", "m/s", r"(?:peak velocity|Vmax|V max|peak aortic velocity)(?:\s+is|\s+of|\s*[:=])?\s*(\d\.\d{1,2})\s*m/s"),
    ("peak_velocity", "cm/s", r"peak velocity\s*=\s*(\d{2,3}(?:\.\d)?)\s*cm/s"),
    ("lvef", "%", r"(?:LVEF|ejection fraction|\bEF\b)\s*(?:is|of|was|=|:)?\s*(?:approximately|about|estimated at)?\s*(\d{2})\s*(?:±\s*\d+\s*)?%"),
    ("lvef", "%", r"(?:LVEF|\bEF\b)\s*(?:is|of|was|=|:)\s*(\d{2})\b(?!\s*%)"),
]
AR_GRADE = r"(no|trace|trivial|mild|mild to moderate|moderate|moderately severe|moderate to severe|severe)\s*(?:\(\d\+\)\s*)?(?:aortic (?:valve )?(?:regurgitation|insufficiency)|\bAI\b|\bAR\b)"
AR_GRADE_ALT = r"(\d)\s*\+\s*(?:AI|AR)\b"
LAB_ANALYTES = {
    "creatinine": ["Creatinine", "Creatinine (POCT)", "Creatinine, Blood"],
    "egfr": ["eGFR-All Other Races", "Estimated Glomerular Filtration Rate", "GFR Estimated (POCT)", "eGFR (POCT)", "GFR Estimated"],
    "hemoglobin": ["Hemoglobin", "Hemoglobin, Whole Blood"],
    "platelets": ["Platelet Count"],
    "inr": ["PT INR", "INR", "INR (POCT)"],
    "nt_probnp": ["NT Pro BNP", "ProBNP"],
    "troponin_t": ["Troponin T"],
    "calcium": ["Calcium", "Calcium, Total"],
    "phosphorus": ["Phosphorus"],
    "ldl": ["LDL Cholesterol, Calculated", "LDL Cholesterol"],
    "albumin": ["Albumin"],
    "lvef": ["LV Ejection Fraction"],
}
MED_CLASSES = {
    "warfarin": r"warfarin",
    "doac": r"apixaban|rivaroxaban|dabigatran|edoxaban",
    "aspirin": r"^aspirin",
    "p2y12": r"clopidogrel|ticagrelor|prasugrel",
    "statin": r"statin",
    "loop_diuretic": r"furosemide|torsemide|bumetanide",
    "mra": r"spironolactone|eplerenone",
    "raas_inhibitor": r"pril$|pril/|sartan",
    "beta_blocker": r"olol\b|carvedilol|labetalol|bisoprolol",
    "sglt2": r"gliflozin",
    "insulin": r"insulin",
    "oral_antidiabetic": r"metformin|glipizide|glimepiride|sitagliptin|semaglutide|liraglutide",
    "amiodarone": r"amiodarone",
    "surgery_marker": r"protamine|tranexamic|aminocaproic|propofol|sevoflurane|isoflurane|desflurane|cardioplegia",
}


def snip(text, start, end, w=SNIP):
    s = text[max(0, start - w): min(len(text), end + w)]
    return re.sub(r"\s+", " ", s).strip()


def find_models(text):
    found = []
    lower = text.lower()
    for name, pat, mfr, kind in MODELS:
        m = re.search(pat, lower, re.I)
        if m:
            found.append((name, mfr, kind, m.start(), m.end()))
    seen, out = set(), []
    for f in sorted(found, key=lambda f: f[3]):
        family = f[0].split(" (")[0].split(" ")[0]
        if family in seen and "unspecified" in f[0]:
            continue
        seen.add(family)
        out.append(f)
    return out


def find_sizes(text):
    sizes = []
    for m in re.finditer(SIZE_RE, text, re.I):
        v = next(g for g in m.groups() if g)
        sizes.append((int(v), m.start(), m.end()))
    return sizes


def size_near(pos, sizes, window=160):
    near = [s for s in sizes if abs(s[1] - pos) <= window]
    if not near:
        return None
    return min(near, key=lambda s: abs(s[1] - pos))[0]


def classify_approach(text):
    line = procedure_line(text)
    if line:
        if re.search(TAVR_RE, line, re.I):
            return "TAVR", "transcatheter terms in the procedure line"
        if re.search(SAVR_RE, line, re.I) or re.search(r"replacement of (?:the )?aortic valve|aortic valve replacement|\bAVR\b", line, re.I):
            return "SAVR", "surgical AVR wording in the procedure line"
    tavr = bool(re.search(TAVR_RE, text, re.I))
    savr_words = bool(re.search(SAVR_RE, text, re.I))
    open_words = bool(re.search(OPEN_RE, text, re.I))
    if tavr and not open_words:
        return "TAVR", "transcatheter terms, no open-surgery terms"
    if tavr and open_words:
        return "TAVR", "transcatheter terms present alongside open-surgery terms (check: hybrid or ViV after prior surgery)"
    if savr_words and open_words:
        return "SAVR", "surgical AVR wording with open-surgery terms"
    if savr_words:
        return "SAVR", "surgical AVR wording only"
    if open_words:
        return "other cardiac surgery", "open-surgery terms without AVR wording"
    return "unclear", "no approach keywords"


def procedure_line(text):
    m = re.search(r"(?:OPERATIONS?|OPERATIVE PROCEDURE|SURGERY/PROCEDURE|PROCEDURE\(S\)|PROCEDURES?)(?:\s+PERFORMED)?\s*:\s*(.{0,220})", text, re.I | re.S)
    if not m:
        return ""
    return re.sub(r"\s+", " ", m.group(1)).strip()[:200]


def valve_context(text, pos, window=260):
    before = text[max(0, pos - window): pos]
    line_start = text.rfind("\n- ", max(0, pos - 600), pos)
    bullet = text[line_start: pos] if line_start >= 0 else before
    scope = bullet if (line_start >= 0 and len(bullet) < 700) else before[-220:]
    prosth = re.search(PROSTH_CTX, scope, re.I)
    native = re.search(NATIVE_CTX, scope, re.I)
    if prosth and not native:
        return "prosthetic"
    if native and not prosth:
        return "native"
    if prosth and native:
        return "ambiguous"
    return "unknown"


def extract_echo(note_id, patient, year, note_type, text):
    rows = []
    for param, unit, pat in ECHO_PATTERNS:
        for m in re.finditer(pat, text, re.I):
            ctx = valve_context(text, m.start()) if param != "lvef" else "n/a"
            if param == "peak_and_mean_gradient":
                for p, g in (("peak_gradient", 1), ("mean_gradient", 2)):
                    rows.append(dict(note_id=note_id, patient=patient, note_year=year, note_type=note_type, parameter=p, value=float(m.group(g)), unit=unit, valve_context=ctx, method="regex", snippet=snip(text, m.start(), m.end())))
            else:
                v = float(m.group(1))
                if param == "lvef" and not 5 <= v <= 85:
                    continue
                if param == "dvi" and not 0.05 <= v <= 1.0:
                    continue
                if param in ("mean_gradient", "peak_gradient") and v > 150:
                    continue
                rows.append(dict(note_id=note_id, patient=patient, note_year=year, note_type=note_type, parameter=param, value=v, unit=unit, valve_context=ctx, method="regex", snippet=snip(text, m.start(), m.end())))
    for m in re.finditer(AR_GRADE, text, re.I):
        rows.append(dict(note_id=note_id, patient=patient, note_year=year, note_type=note_type, parameter="aortic_regurgitation_grade", value=m.group(1).lower(), unit="grade", valve_context=valve_context(text, m.start()), method="regex", snippet=snip(text, m.start(), m.end())))
    for m in re.finditer(AR_GRADE_ALT, text):
        rows.append(dict(note_id=note_id, patient=patient, note_year=year, note_type=note_type, parameter="aortic_regurgitation_grade", value=m.group(1) + "+", unit="grade", valve_context=valve_context(text, m.start()), method="regex", snippet=snip(text, m.start(), m.end())))
    out = pd.DataFrame(rows)
    if len(out):
        out = out.drop_duplicates(subset=["note_id", "parameter", "value", "snippet"])
    return out


def extract_events(note_id, patient, year, note_type, text):
    rows = []
    for name, pat in EVENTS.items():
        for m in re.finditer(pat, text, re.I):
            window = text[max(0, m.start() - 60): m.end() + 40]
            negated = bool(re.search(r"valve in valve:\s*no|no evidence of|without|negative for|denies|rule out|r/o|not consistent", window, re.I))
            rows.append(dict(note_id=note_id, patient=patient, note_year=year, note_type=note_type, event_type=name, negated=negated, method="regex", snippet=snip(text, m.start(), m.end())))
    return pd.DataFrame(rows)


def extract_implant(note_id, patient, year, note_type, signed, text):
    approach, reason = classify_approach(text)
    models = find_models(text)
    sizes = find_sizes(text)
    primary = None
    for f in models:
        if approach == "TAVR" and f[2] == "TAVR":
            primary = f
            break
        if approach == "SAVR" and f[2] == "SAVR":
            primary = f
            break
    if primary is None and models:
        primary = models[0]
    size = size_near(primary[3], sizes) if primary else (sizes[0][0] if sizes else None)
    viv = bool(re.search(r"valve[- ]in[- ]valve", text, re.I)) and not re.search(r"valve in valve:\s*no", text, re.I)
    struct_block = bool(re.search(r"Valve Type Used:|Tissue Implant Type:|Implant Size:", text))
    name_redacted_valve = bool(re.search(r"\d{2}\s?-?\s?mm \[NAME\]|\[NAME\] (?:aortic )?valve|\[NAME\] S3", text))
    concomitant = [k for k, p in CONCOMITANT.items() if re.search(p, text, re.I)]
    access = [k for k, p in ACCESS.items() if re.search(p, text, re.I)] if approach == "TAVR" else []
    redo = bool(re.search(r"\bredo\b|re-do|re-?operative|prior sternotomy|previous sternotomy", text, re.I))
    native = re.search(r"(bicuspid|tricuspid|unicuspid)\s+aortic valve|type of native valve:\s*(\w+)", text, re.I)
    conf = "high" if (primary and size and approach in ("TAVR", "SAVR")) else ("medium" if approach in ("TAVR", "SAVR") else "low")
    return dict(
        note_id=note_id, patient=patient, note_type=note_type, implant_year=year, signed_status=signed,
        approach=approach, approach_reason=reason,
        valve_model=primary[0] if primary else None, manufacturer=primary[1] if primary else None,
        all_models_mentioned="; ".join(f[0] for f in models),
        valve_size_mm=size, all_sizes_mentioned="; ".join(str(s[0]) for s in sizes),
        valve_in_valve=viv, structured_implant_block=struct_block, valve_name_redacted=name_redacted_valve,
        tavr_access="; ".join(access), concomitant_procedures="; ".join(concomitant), redo_sternotomy=redo,
        native_valve_morphology=(native.group(1) or native.group(2)).lower() if native else None,
        procedure_line=procedure_line(text), extraction_confidence=conf, method="regex",
        model_snippet=snip(text, primary[3], primary[4], 80) if primary else "",
    )


def implant_from_followup(note_id, patient, year, text):
    m = re.search(r"(s/p|status post|underwent|history of|prior|previous|s/p surgery:|day of surgery)\s*[^.]{0,80}?(transcatheter aortic valve replacement|\bTAVR\b|\bTAVI\b|aortic valve replacement|\bAVR\b|bioprosthetic AVR)", text, re.I)
    if not m:
        return None
    approach = "TAVR" if re.search(r"transcatheter|TAVR|TAVI", m.group(2), re.I) else "SAVR"
    models = find_models(text)
    sizes = find_sizes(text)
    primary = next((f for f in models if f[2] == approach), models[0] if models else None)
    size = size_near(primary[3], sizes, 200) if primary else None
    partial = re.search(r"(?:on|in)\s+(\d{1,2}/(?:19|20)\d{2}|(?:19|20)\d{2})\b", text[m.start(): m.end() + 80])
    return dict(note_id=note_id, patient=patient, note_type="follow-up mention", implant_year=None, signed_status=None,
                approach=approach, approach_reason="history mention in follow-up note",
                valve_model=primary[0] if primary else None, manufacturer=primary[1] if primary else None,
                all_models_mentioned="; ".join(f[0] for f in models), valve_size_mm=size, all_sizes_mentioned="; ".join(str(s[0]) for s in sizes),
                valve_in_valve=bool(re.search(r"valve[- ]in[- ]valve", text, re.I)), structured_implant_block=False, valve_name_redacted=bool(re.search(r"\[NAME\] (?:aortic )?valve|\[NAME\] S3", text)),
                tavr_access="", concomitant_procedures="", redo_sternotomy=False, native_valve_morphology=None,
                procedure_line=snip(text, m.start(), m.end(), 60), extraction_confidence="medium" if primary else "low", method="regex",
                model_snippet=snip(text, primary[3], primary[4], 80) if primary else "", implant_date_mention=partial.group(1) if partial else None, mention_year=year)


def summarise_labs(labs):
    labs = labs.drop(columns=["Row"]).drop_duplicates()
    labs["value"] = pd.to_numeric(labs["Numeric Value"], errors="coerce")
    labs.loc[labs["value"].isna(), "value"] = pd.to_numeric(labs["String Value"], errors="coerce")
    censored = labs["String Value"].astype(str).str.match(r"^\s*[<>]=?\s*\d")
    labs["censored"] = censored
    labs.loc[censored, "value"] = pd.to_numeric(labs.loc[censored, "String Value"].astype(str).str.replace(r"[<>=\s]", "", regex=True), errors="coerce")
    long, wide = [], []
    for analyte, names in LAB_ANALYTES.items():
        sub = labs[labs["Lab Component Name"].isin(names) & labs["value"].notna()]
        for (p, y), g in sub.groupby(["Patient", "Result Date"]):
            long.append(dict(patient=p, analyte=analyte, year=int(y), n=len(g), mean=round(g.value.mean(), 2), min=g.value.min(), max=g.value.max(), any_censored=bool(g.censored.any()), units="; ".join(sorted(g.Unit.dropna().astype(str).unique()))))
        for p, g in sub.groupby("Patient"):
            g = g.sort_values("Result Date")
            wide.append(dict(patient=p, analyte=analyte, n=len(g), first_year=int(g["Result Date"].iloc[0]), last_year=int(g["Result Date"].iloc[-1]), first_year_mean=round(g[g["Result Date"] == g["Result Date"].iloc[0]].value.mean(), 2), last_year_mean=round(g[g["Result Date"] == g["Result Date"].iloc[-1]].value.mean(), 2), overall_min=g.value.min(), overall_max=g.value.max(), source="structured: labs file", component_names="; ".join(sorted(g["Lab Component Name"].unique()))))
    return pd.DataFrame(long), pd.DataFrame(wide)


def summarise_meds(meds):
    meds = meds.drop_duplicates()
    generic = meds["Simple Generic Name"].fillna(meds["Proper Name"]).str.lower()
    rows = []
    for cls, pat in MED_CLASSES.items():
        hit = generic.str.contains(pat, regex=True) & ~generic.str.contains("nystatin")
        if cls == "surgery_marker":
            hit = hit | meds["Medication Therapeutic Class"].eq("ANESTHETICS")
        for (p, y, mode), g in meds[hit].groupby(["Patient", "Start Date", "Mode"]):
            rows.append(dict(patient=p, year=int(y), medication_class=cls, mode=mode, n_orders=len(g), drugs="; ".join(sorted(g["Simple Generic Name"].fillna(g["Proper Name"]).unique()))[:200], source="structured: medications file"))
    long = pd.DataFrame(rows)
    per_patient = []
    for p, g in long.groupby("patient"):
        d = dict(patient=p)
        for cls in MED_CLASSES:
            yrs = sorted(g[g.medication_class == cls].year.unique())
            d[f"{cls}_years"] = ", ".join(map(str, yrs))
            d[f"{cls}_ever"] = bool(yrs)
        out_yrs = sorted(g[(g.medication_class == "surgery_marker")].year.unique())
        d["surgery_marker_years"] = ", ".join(map(str, out_yrs))
        d["inferred_index_operation_year"] = min(out_yrs) if out_yrs else None
        per_patient.append(d)
    dx = meds[meds["Associated Diagnoses"].notna()].copy()
    dx_rows = []
    for _, r in dx.iterrows():
        for d in json.loads(r["Associated Diagnoses"]):
            for c in d.get("icd10s", []):
                dx_rows.append(dict(patient=r.Patient, year=int(r["Start Date"]), icd10=c["code"], icd10_name=c["name"], diagnosis_name=d["name"], linked_drug=r["Simple Generic Name"], source="structured: medications file, Associated Diagnoses"))
    return long, pd.DataFrame(per_patient), pd.DataFrame(dx_rows).drop_duplicates()


def model_level(name):
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return "unknown"
    if "inferred" in name:
        return "inferred from surviving tokens (name redacted)"
    if "unspecified" in name:
        return "family only"
    return "exact model"


def valve_type_hint(op):
    text = " ".join(str(v) for v in [op.get("all_models_mentioned"), op.get("procedure_line"), op.get("model_snippet")] if v)
    hints = []
    for k, pat in {"bovine pericardial": r"bovine|pericardial|perimount|magna|trifecta|inspiris|carpentier|sapien|konect", "porcine": r"porcine|epic|biocor|mosaic|hancock|evolut|corevalve", "balloon-expandable THV": r"sapien", "self-expanding THV": r"evolut|corevalve|navitor|portico|acurate", "stentless": r"freestyle|homograft", "sutureless": r"perceval"}.items():
        if re.search(pat, text, re.I):
            hints.append(k)
    return "; ".join(hints)


def svd_label(row):
    def val(k):
        v = row.get(k)
        return None if v is None or (isinstance(v, float) and pd.isna(v)) else v
    if row.get("event_valve_in_valve") or row.get("event_redo_or_reintervention"):
        if row.get("event_endocarditis"):
            return "borderline: reintervention but endocarditis documented (VARC-3 non-structural exclusion, adjudicate)", "reintervention with possible non-structural cause"
        return "accept: reintervention for failed bioprosthesis", "reintervention (VARC-3 BVF stage 2)"
    mg, mg_year, dvi = val("prosthetic_mean_gradient_max"), val("prosthetic_mean_gradient_max_year"), val("prosthetic_dvi_latest")
    ar = str(val("prosthetic_ar_grade_latest") or "")
    later = mg is not None and mg_year is not None and val("implant_year") is not None and mg_year > val("implant_year")
    if mg is not None and not later and not re.search(r"severe|moderate", ar) and not row.get("event_prosthetic_failure_language"):
        return "missing information: prosthetic echo only in the implant year (baseline), no later follow-up echo", "baseline only"
    if (mg is not None and mg >= 30 and later) or re.search(r"severe", ar):
        return "borderline: severe haemodynamic criteria met (needs baseline comparison)", "candidate VARC-3 stage 3 HVD"
    if (mg is not None and mg >= 20 and later) or (dvi is not None and dvi < 0.25) or re.search(r"moderate", ar) or row.get("event_prosthetic_failure_language"):
        return "borderline: moderate haemodynamic criteria or failure language", "candidate VARC-3 stage 2 HVD"
    if mg is not None:
        return "reject: prosthetic echo present without deterioration criteria", "no HVD on available echo"
    return "missing information: no prosthetic echo values found", "not assessable"


def main():
    require_extracts()
    notes = pd.read_excel(f"{DATA}/notes_deidentified.xlsx")
    labs = pd.read_excel(f"{DATA}/labs_deidentified.xlsx")
    meds = pd.read_excel(f"{DATA}/medications_deidentified.xlsx")
    notes = notes.rename(columns={"Profile Key": "patient"})
    notes["note_id"] = ["N%03d" % i for i in range(1, len(notes) + 1)]

    implants, followup_mentions, echo_frames, event_frames, note_rows = [], [], [], [], []
    for _, n in notes.iterrows():
        text = n.Notes
        year = int(n["Service Date"])
        echo = extract_echo(n.note_id, n.patient, year, n.Type, text)
        events = extract_events(n.note_id, n.patient, year, n.Type, text)
        echo_frames.append(echo)
        event_frames.append(events)
        if n.Type == "Operative Report":
            implants.append(extract_implant(n.note_id, n.patient, year, n.Type, n["Signed Status"], text))
        else:
            fm = implant_from_followup(n.note_id, n.patient, year, text)
            if fm:
                followup_mentions.append(fm)
        note_rows.append(dict(
            note_id=n.note_id, patient=n.patient, note_type=n.Type, service=n.Service, year=year, signed_status=n["Signed Status"],
            author_type=n["Authoring Provider Type"], author_specialty=n["Authoring Provider Specialty"], characters=len(text),
            exclude_recommended=n["Signed Status"] == "Deleted",
            mentions_tavr=bool(re.search(TAVR_RE, text, re.I)), mentions_surgical_avr=bool(re.search(SAVR_RE, text, re.I)),
            models_mentioned="; ".join(f[0] for f in find_models(text)),
            has_echo_conclusions_block=bool(re.search(r"CONCLUSIONS|Echocardiogram:|ECHO\b", text)),
            n_echo_values=len(echo), n_prosthetic_echo_values=int((echo.valve_context == "prosthetic").sum()) if len(echo) else 0,
            n_native_echo_values=int((echo.valve_context == "native").sum()) if len(echo) else 0,
            event_types="; ".join(sorted(events[~events.negated].event_type.unique())) if len(events) else "",
            partial_dates_in_text="; ".join(sorted(set(re.findall(r"\b\d{1,2}/(?:19|20)\d{2}\b", text)))),
            years_in_text="; ".join(sorted(set(re.findall(r"\b(?:19|20)\d{2}\b", text)))),
            age_redacted="[AGE]" in text, sex=("female" if re.search(r"\b(?:she|her|female|woman)\b", text, re.I) else "male" if re.search(r"\b(?:he|his|male|man)\b", text, re.I) else ""),
        ))

    notes_df = pd.DataFrame(note_rows)
    implants_df = pd.DataFrame(implants + followup_mentions)
    echo_df = pd.concat([e for e in echo_frames if len(e)], ignore_index=True)
    events_df = pd.concat([e for e in event_frames if len(e)], ignore_index=True)
    labs_long, labs_wide = summarise_labs(labs)
    meds_long, meds_pt, dx_df = summarise_meds(meds)

    rows = []
    for p, g in notes_df.groupby("patient"):
        op = implants_df[(implants_df.patient == p) & (implants_df.note_type == "Operative Report") & (implants_df.signed_status != "Deleted")].sort_values("implant_year")
        op_any = implants_df[(implants_df.patient == p) & (implants_df.note_type == "Operative Report")].sort_values("implant_year")
        fm = implants_df[(implants_df.patient == p) & (implants_df.note_type == "follow-up mention")]
        src = op if len(op) else (op_any if len(op_any) else fm)
        first = src.iloc[0] if len(src) else None
        avr_ops = src[src.approach.isin(["TAVR", "SAVR"])] if len(src) else src
        index_op = avr_ops.iloc[0] if len(avr_ops) else first
        mp = meds_pt[meds_pt.patient == p]
        implant_year = index_op.implant_year if index_op is not None and not pd.isna(index_op.implant_year) else (mp.inferred_index_operation_year.iloc[0] if len(mp) else None)
        implant_year_source = "operative report year" if index_op is not None and not pd.isna(index_op.implant_year) else ("anaesthetic / protamine order year (medications file)" if len(mp) and mp.inferred_index_operation_year.iloc[0] else "not available")
        pe = echo_df[(echo_df.patient == p) & (echo_df.valve_context == "prosthetic")]
        pe_after = pe[pe.note_year >= implant_year] if implant_year else pe
        mg = pe_after[pe_after.parameter == "mean_gradient"].sort_values("note_year")
        dvi = pe_after[pe_after.parameter == "dvi"].sort_values("note_year")
        ar = pe_after[pe_after.parameter == "aortic_regurgitation_grade"].sort_values("note_year")
        ef = echo_df[(echo_df.patient == p) & (echo_df.parameter == "lvef")].sort_values("note_year")
        ev = events_df[(events_df.patient == p) & (~events_df.negated)]
        last_year = int(g.year.max())
        r = dict(
            patient=p, cohort_group="A: operative report, no labs/meds" if p not in set(labs.Patient) else "B: labs and meds, no operative report",
            n_notes=len(g), note_types="; ".join(sorted(g.note_type.unique())), first_note_year=int(g.year.min()), last_note_year=last_year,
            n_deleted_notes=int(g.exclude_recommended.sum()), has_labs_and_meds=p in set(labs.Patient),
            implant_approach=index_op.approach if index_op is not None else None,
            implant_approach_source=("operative report " + index_op.note_id) if index_op is not None and index_op.note_type == "Operative Report" else (("history mention in " + index_op.note_id) if index_op is not None else None),
            valve_model=index_op.valve_model if index_op is not None else None, manufacturer=index_op.manufacturer if index_op is not None else None,
            valve_size_mm=index_op.valve_size_mm if index_op is not None else None, valve_name_redacted=bool(index_op.valve_name_redacted) if index_op is not None else None,
            valve_model_level=model_level(index_op.valve_model) if index_op is not None else "unknown",
            all_models_mentioned=index_op.all_models_mentioned if index_op is not None else None,
            valve_type_hint=valve_type_hint(index_op) if index_op is not None else None,
            implant_year=implant_year, implant_year_source=implant_year_source,
            concomitant_procedures=index_op.concomitant_procedures if index_op is not None else None, tavr_access=index_op.tavr_access if index_op is not None else None,
            native_valve_morphology=index_op.native_valve_morphology if index_op is not None else None,
            n_operative_reports=len(op_any), n_avr_operations=len(avr_ops) if len(src) else 0,
            follow_up_years=(last_year - implant_year) if implant_year else None, has_later_year_note=bool(implant_year and last_year > implant_year),
            n_prosthetic_echo_values=len(pe_after), prosthetic_echo_years="; ".join(map(str, sorted(pe_after.note_year.unique()))),
            prosthetic_mean_gradient_latest=mg.value.iloc[-1] if len(mg) else None, prosthetic_mean_gradient_latest_year=int(mg.note_year.iloc[-1]) if len(mg) else None,
            prosthetic_mean_gradient_first=mg.value.iloc[0] if len(mg) else None, prosthetic_mean_gradient_max=mg.value.max() if len(mg) else None,
            prosthetic_mean_gradient_max_year=int(mg.sort_values("value").note_year.iloc[-1]) if len(mg) else None,
            reintervention_year=(lambda s: int(s.min()) if len(s) else None)(ev[ev.event_type.isin(["valve_in_valve", "redo_or_reintervention"]) & (ev.note_year >= (implant_year or 0))].note_year),
            prosthetic_dvi_latest=dvi.value.iloc[-1] if len(dvi) else None, prosthetic_ar_grade_latest=ar.value.iloc[-1] if len(ar) else None,
            lvef_latest=ef.value.iloc[-1] if len(ef) else None, lvef_latest_year=int(ef.note_year.iloc[-1]) if len(ef) else None,
            native_mean_gradient_preop_max=echo_df[(echo_df.patient == p) & (echo_df.valve_context == "native") & (echo_df.parameter == "mean_gradient")].value.max(),
        )
        for e in EVENTS:
            sub = ev[ev.event_type == e]
            r[f"event_{e}_n_mentions"] = int(len(sub))
            r[f"event_{e}_years"] = "; ".join(map(str, sorted(sub.note_year.unique())))
            r[f"event_{e}_statements"] = " || ".join(sub.snippet.head(3))
        if len(mp):
            r["warfarin_ever"] = bool(mp.warfarin_ever.iloc[0]); r["doac_ever"] = bool(mp.doac_ever.iloc[0]); r["aspirin_ever"] = bool(mp.aspirin_ever.iloc[0]); r["statin_ever"] = bool(mp.statin_ever.iloc[0])
        lw = labs_wide[labs_wide.patient == p]
        for a in ["creatinine", "egfr", "hemoglobin", "nt_probnp", "calcium", "phosphorus"]:
            s = lw[lw.analyte == a]
            r[f"{a}_last_year_mean"] = s.last_year_mean.iloc[0] if len(s) else None
        r["time_to_reintervention_years"] = (r["reintervention_year"] - implant_year) if (r.get("reintervention_year") and implant_year) else None
        r["sex"] = g.sex.mode().iloc[0] if g.sex.replace("", pd.NA).dropna().size else ""
        r["age_available"] = False
        r["prosthetic_mean_gradients_by_year"] = "; ".join(f"{int(y)}: {v:g}" for y, v in zip(mg.note_year, mg.value))
        r["prosthetic_dvi_by_year"] = "; ".join(f"{int(y)}: {v:g}" for y, v in zip(dvi.note_year, dvi.value))
        r["prosthetic_ar_grade_by_year"] = "; ".join(f"{int(y)}: {v}" for y, v in zip(ar.note_year, ar.value))
        r["lvef_by_year"] = "; ".join(f"{int(y)}: {v:g}" for y, v in zip(ef.note_year, ef.value))
        rows.append(r)
    patients_df = pd.DataFrame(rows)
    label_rows = []
    for _, r in patients_df.iterrows():
        d = r.to_dict()
        d["event_valve_in_valve"] = d["event_valve_in_valve_n_mentions"] > 0
        d["event_redo_or_reintervention"] = d["event_redo_or_reintervention_n_mentions"] > 0
        d["event_endocarditis"] = d["event_endocarditis_n_mentions"] > 0
        d["event_prosthetic_failure_language"] = d["event_prosthetic_failure_language_n_mentions"] > 0
        lab, basis = svd_label(d)
        label_rows.append(dict(patient=r.patient, proposed_label=lab, basis=basis, method="rule-based proposal on regex-extracted values; illustrative only, the model should learn from the raw fields", mean_gradient_max=r.prosthetic_mean_gradient_max, mean_gradient_max_year=r.prosthetic_mean_gradient_max_year, dvi_latest=r.prosthetic_dvi_latest, ar_grade_latest=r.prosthetic_ar_grade_latest, reintervention_year=r.reintervention_year))
    label_proposal_df = pd.DataFrame(label_rows)

    dictionary = pd.DataFrame([
        ("patients", "cohort_group", "derived", "A = Patient_001-100 (operative reports), B = Patient_101-117 (labs and meds)", "structured"),
        ("patients", "implant_approach", "note-derived", "TAVR if transcatheter terms or TAVR device names; SAVR if aortic valve replacement wording with open-surgery terms; from the first signed operative report, else from a history mention", "regex, rule"),
        ("patients", "valve_model / manufacturer", "note-derived", "first model name matching the approach in the index operative report; valve_name_redacted flags reports where the de-identifier replaced the device name with [NAME]", "regex lexicon"),
        ("patients", "valve_size_mm", "note-derived", "size in mm nearest the model mention (#21, 21 mm, size 26, Implant Size: 25)", "regex"),
        ("patients", "implant_year", "hybrid", "operative report service year; for group B the earliest year with anaesthetic or protamine orders in the medications file", "structured + rule"),
        ("patients", "follow_up_years", "derived", "last note year minus implant year; year resolution only", "arithmetic"),
        ("patients", "prosthetic_mean_gradient_*", "note-derived", "mean gradient values whose surrounding sentence refers to a prosthesis, S/P AVR or TAVR, restricted to notes in or after the implant year", "regex + context rule"),
        ("patients", "prosthetic_dvi_latest", "note-derived", "dimensionless valve index in prosthetic context", "regex + context rule"),
        ("patients", "prosthetic_ar_grade_latest", "note-derived", "regurgitation grade word (no, trace, mild, moderate, severe) in prosthetic context", "regex + context rule"),
        ("patients", "native_mean_gradient_preop_max", "note-derived", "highest mean gradient in native-valve context (pre-operative stenosis severity)", "regex + context rule"),
        ("patients", "event_*_n_mentions / _years / _statements", "note-derived", "keyword events with a simple negation check; count, years and the first quoted statements are kept rather than a yes/no flag", "regex + negation rule"),
        ("patients", "*_by_year", "note-derived", "every prosthetic gradient, DVI, regurgitation grade and LVEF value with its note year, so a model can use the trajectory", "regex + context rule"),
        ("label_proposal", "proposed_label", "derived proposal", "illustrative rule: accept = reintervention for failed bioprosthesis; borderline = haemodynamic thresholds or failure language; reject = prosthetic echo without criteria; missing = no prosthetic echo. Kept in its own sheet so the patient table holds only raw fields", "rule"),
        ("patients", "*_last_year_mean", "structured", "mean of the analyte in the last year it was measured (labs file, de-duplicated)", "aggregation"),
        ("patients", "sex", "note-derived", "pronoun majority across the patient's notes; no structured sex field exists", "regex"),
        ("patients", "valve_model_level", "derived", "exact model / family only / inferred from surviving tokens (name redacted) / unknown", "rule"),
        ("patients", "valve_type_hint", "derived", "tissue and design class implied by the model name (bovine pericardial, porcine, balloon-expandable, self-expanding)", "lexicon"),
        ("patients", "age_available", "structured", "always False: age is redacted as [AGE] in every note and no demographics table exists", "constant"),
        ("implants", "one row per operative report or history mention", "note-derived", "approach, model, size, valve-in-valve, TAVR access, concomitant procedures, redo, native morphology, procedure line, confidence", "regex"),
        ("echo_values", "one row per extracted value", "note-derived", "parameter, value, unit, valve_context (prosthetic / native / ambiguous / unknown), snippet for verification", "regex"),
        ("events", "one row per keyword hit", "note-derived", "event_type, negated flag, snippet", "regex"),
        ("labs_by_year / labs_summary", "canonical analytes", "structured", "component-name variants merged; censored values (>60, <0.01) parsed to the limit and flagged; units listed, not converted", "aggregation"),
        ("meds_by_year / meds_summary", "medication classes", "structured", "class flags by patient-year and mode; surgery_marker = anaesthetics, protamine, antifibrinolytics", "aggregation"),
        ("diagnoses", "ICD-10 from medications", "structured", "the only coded diagnoses in the extract (24 rows)", "JSON parse"),
    ], columns=["sheet", "field", "source_type", "definition", "method"])

    criteria = pd.DataFrame([
        ("VARC-3 stage 2 HVD (moderate)", "mean gradient rise >= 10 mmHg from reference echo resulting in >= 20 mmHg, with EOA fall >= 0.3 cm2 or >= 25 % and/or DVI fall >= 0.1 or >= 20 %; or new / one-grade worse intraprosthetic AR that is at least moderate", "reference echo 30 days to 3 months after implant", "needs serial echo; single-echo fallback: mean gradient >= 20 mmHg", ""),
        ("VARC-3 stage 3 HVD (severe)", "rise >= 20 mmHg resulting in >= 30 mmHg, with EOA fall >= 0.6 cm2 or >= 50 % and/or DVI fall >= 0.2 or >= 40 %; or severe AR", "as above", "single-echo fallback: mean gradient >= 30 mmHg or DVI < 0.25", ""),
        ("VARC-3 bioprosthetic valve failure stage 2", "reintervention (valve-in-valve TAVR or redo SAVR) for valve deterioration", "any time", "operative report or history mention of valve-in-valve / redo", ""),
        ("EAPCI/ESC/EACTS 2017 moderate SVD", "mean gradient 20-40 mmHg or rise 10-20 mmHg, or moderate AR", "from baseline", "", ""),
        ("EAPCI/ESC/EACTS 2017 severe SVD", "mean gradient >= 40 mmHg or rise >= 20 mmHg, or severe AR", "from baseline", "", ""),
        ("Exclusions (non-structural)", "endocarditis, valve thrombosis, isolated paravalvular leak, isolated patient-prosthesis mismatch", "", "flagged separately in events", ""),
    ], columns=["criterion", "definition", "timing", "how it maps to our data", "team decision (fill in)"])

    questions = pd.DataFrame([
        ("Failure definition", "Adopt VARC-3 stage 2/3 HVD plus BVF stage 2 as primary? Single-echo fallback thresholds when no baseline echo exists?", "team"),
        ("Native vs prosthetic gradients", "The valve_context rule uses the surrounding sentence. Please spot-check 20 rows in echo_values where valve_context is ambiguous or unknown.", "clinician"),
        ("Valve name redaction", "Decided 16 Sep: keep inferred and family-level models; valve_model_level records the certainty. Ask Dyania whether an un-redacted device field can be provided.", "decided"),
        ("Deleted operative reports", "9 operative reports are marked Deleted. They are kept in implants with signed_status but excluded from the patient-level index operation. Confirm.", "team"),
        ("Group B implant year", "For the 17 lab/med patients the implant year comes from anaesthetic or protamine orders. Some patients have several such years; the earliest is used. Confirm or override per patient.", "clinician"),
        ("Two operations per patient", "10 patients have two operative reports and one has three; the first AVR-type report is used as the index operation and later ones appear in implants. Should a later valve-in-valve count as the outcome for the first implant?", "team"),
        ("Age and sex", "Decided 16 Sep: keep pronoun-derived sex as the sex column. Age remains unavailable; request birth year from Dyania.", "decided"),
        ("LLM pass", "Rows with extraction_confidence = low or valve_context = ambiguous could be sent to Claude with a question-and-justification prompt in the Synapsis style. Run it?", "user"),
    ], columns=["topic", "question", "decision owner"])

    with pd.ExcelWriter(OUT, engine="openpyxl") as xw:
        patients_df.to_excel(xw, sheet_name="patients", index=False)
        label_proposal_df.to_excel(xw, sheet_name="label_proposal", index=False)
        implants_df.to_excel(xw, sheet_name="implants", index=False)
        echo_df.sort_values(["patient", "note_year", "parameter"]).to_excel(xw, sheet_name="echo_values", index=False)
        events_df.sort_values(["patient", "note_year"]).to_excel(xw, sheet_name="events", index=False)
        notes_df.to_excel(xw, sheet_name="notes", index=False)
        labs_wide.to_excel(xw, sheet_name="labs_summary", index=False)
        labs_long.to_excel(xw, sheet_name="labs_by_year", index=False)
        meds_pt.to_excel(xw, sheet_name="meds_summary", index=False)
        meds_long.to_excel(xw, sheet_name="meds_by_year", index=False)
        dx_df.to_excel(xw, sheet_name="diagnoses", index=False)
        criteria.to_excel(xw, sheet_name="failure_criteria", index=False)
        dictionary.to_excel(xw, sheet_name="data_dictionary", index=False)
        questions.to_excel(xw, sheet_name="open_questions", index=False)
        for ws in xw.book.worksheets:
            ws.freeze_panes = "B2"
            for col in ws.columns:
                width = min(60, max(10, max(len(str(c.value)) if c.value is not None else 0 for c in col[:200]) + 2))
                ws.column_dimensions[col[0].column_letter].width = width

    print("patients", patients_df.shape, "implants", implants_df.shape, "echo_values", echo_df.shape, "events", events_df.shape)
    print("approach:", patients_df.implant_approach.value_counts(dropna=False).to_dict())
    print("valve model:", patients_df.valve_model.value_counts(dropna=False).to_dict())
    print("size known:", patients_df.valve_size_mm.notna().sum(), "implant year known:", patients_df.implant_year.notna().sum())
    print("prosthetic echo patients:", (patients_df.n_prosthetic_echo_values > 0).sum())
    print("label_proposal:", label_proposal_df.proposed_label.value_counts().to_dict())
    print("echo valve_context:", echo_df.valve_context.value_counts().to_dict())
    print("implant confidence:", implants_df.extraction_confidence.value_counts().to_dict())
    print("follow_up_years:", patients_df.follow_up_years.value_counts().sort_index().to_dict())


if __name__ == "__main__":
    main()
