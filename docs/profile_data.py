import re
import pandas as pd

pd.set_option("display.width", 200)
pd.set_option("display.max_rows", 200)

DATA = "data"


def section(title):
    print(f"\n=== {title} ===")


def load():
    labs = pd.read_excel(f"{DATA}/labs_deidentified.xlsx")
    meds = pd.read_excel(f"{DATA}/medications_deidentified.xlsx")
    notes = pd.read_excel(f"{DATA}/notes_deidentified.xlsx")
    return labs, meds, notes


def profile_labs(labs):
    section("labs: shape, nulls, duplicates")
    print("rows, cols:", labs.shape, "patients:", labs.Patient.nunique())
    print(labs.isna().mean().round(2).to_dict())
    dedup = labs.drop(columns=["Row"]).drop_duplicates()
    print("exact duplicates:", len(labs) - len(dedup), "unique rows:", len(dedup))
    print("years:", dedup["Result Date"].value_counts().sort_index().to_dict())
    print("Lab Type:", dedup["Lab Type"].value_counts(dropna=False).to_dict())
    print("LOINC coverage (raw):", round(labs["Loinc Code"].notna().mean(), 3))
    print("Flag x Is Abnormal:")
    print(pd.crosstab(labs.Flag.fillna("NA"), labs["Is Abnormal"].fillna(-1)))
    section("labs: content mix of unique rows")
    name = dedup["Lab Component Name"]
    categories = {
        "respiratory therapy": r"transcription|resp|breath|cough|PEP|nebul|MDI|DPI|SVN|mask|mouthpiece|O2 |oxygen|LPM|adverse|mobility|mental status|therapy|Med Name|Med Route|Pre |Post |ALF|inline|inhala",
        "blood gas / whole blood": r"arterial|venous|whole blood|lactate|base excess|oxyhemoglobin|carboxy|methemo|temperature",
        "device / ECG": r"lead|implant|generator|ICD|PM-|pacing|sensing|impedance|shock|battery|model|serial|device|episode|tachy|brady|arrhyth|QRS|QT |PR interval|RR interval",
        "blood bank": r"ABO|Rh|antibody screen|crossmatch|type|screen|product|unit",
        "pathology / micro": r"specimen|culture|gram|organism|PCR|RNA|stain|sensitiv|report",
    }
    assigned = pd.Series("other", index=dedup.index)
    for key, pattern in categories.items():
        hit = name.str.contains(pattern, case=False, regex=True) & (assigned == "other")
        assigned[hit] = key
    print(assigned.value_counts().to_dict())
    section("labs: units and naming")
    print("distinct units:", dedup.Unit.nunique(), "rows without unit:", dedup.Unit.isna().sum())
    multi_unit = dedup.dropna(subset=["Unit"]).groupby("Lab Component Name")["Unit"].nunique()
    print("components with >1 unit:", multi_unit[multi_unit > 1].index.tolist())
    multi_loinc = dedup.dropna(subset=["Loinc Code"]).groupby("Lab Component Name")["Loinc Code"].nunique()
    print("components with >1 LOINC:", multi_loinc[multi_loinc > 1].index.tolist())
    creat = dedup[dedup["Lab Component Name"] == "Creatinine"]
    print("creatinine unit by year:")
    print(pd.crosstab(creat["Result Date"], creat.Unit))
    section("labs: values")
    text_only = dedup[dedup["Numeric Value"].isna() & dedup["String Value"].notna()]["String Value"]
    print("string-only rows:", len(text_only), "censored (<, >):", text_only.str.match(r"^\s*[<>]=?\s*\d").sum(), "unparsed numbers:", text_only.str.match(r"^\s*-?\d+(\.\d+)?\s*$").sum())
    section("labs: key analytes (unique rows / patients)")
    for analyte in ["Creatinine", "Hemoglobin", "Platelet Count", "PT INR", "Troponin T", "NT Pro BNP", "Calcium", "Phosphorus", "LDL Cholesterol, Calculated", "CRP", "LV Ejection Fraction"]:
        sub = dedup[dedup["Lab Component Name"] == analyte]
        print(f"{analyte}: rows={len(sub)} patients={sub.Patient.nunique()}")
    print("years per patient (labs):", dedup.groupby("Patient")["Result Date"].nunique().value_counts().sort_index().to_dict())
    section("labs: de-identification observations")
    text = dedup["String Value"].fillna("")
    print("angle tokens:", pd.Series(re.findall(r"<[A-Z_]+>", "\n".join(text))).value_counts().to_dict())
    full_dates = text.str.contains(r"\b\d{1,2}/\d{1,2}/\d{4}\b", regex=True)
    print("rows with full mm/dd/yyyy dates:", full_dates.sum(), "in components:", dedup[full_dates]["Lab Component Name"].value_counts().to_dict())
    print("serial-number rows:", dedup[name.str.contains("Serial", case=False)]["String Value"].notna().sum())


def profile_meds(meds):
    section("meds: shape, nulls, duplicates")
    print("rows, cols:", meds.shape, "patients:", meds.Patient.nunique())
    print(meds.isna().mean().round(2).to_dict())
    dedup = meds.drop_duplicates()
    print("exact duplicates:", len(meds) - len(dedup), "unique rows:", len(dedup))
    print("Mode (raw):", meds.Mode.value_counts().to_dict(), "Mode (unique):", dedup.Mode.value_counts().to_dict())
    print("years:", dedup["Start Date"].value_counts().sort_index().to_dict())
    print("years per patient (meds):", dedup.groupby("Patient")["Start Date"].nunique().value_counts().sort_index().to_dict())
    print("discontinued reasons:", meds["Discontinued Reason"].value_counts().head(5).to_dict())
    print("end==start share:", round((dedup["End Date"] == dedup["Start Date"]).mean(), 2))
    section("meds: coding")
    print("rows with Associated Diagnoses:", dedup["Associated Diagnoses"].notna().sum())
    codes = pd.Series(re.findall(r'"code": "([A-Z0-9.]+)"', "\n".join(dedup["Associated Diagnoses"].dropna())))
    print("ICD-10 codes seen:", codes.value_counts().to_dict())
    print("rows without generic name:", dedup["Simple Generic Name"].isna().sum())
    section("meds: valve-relevant classes (patients)")
    generic = dedup["Simple Generic Name"].fillna("").str.lower()
    classes = {
        "aspirin": r"^aspirin", "P2Y12": r"clopidogrel|ticagrelor|prasugrel", "warfarin": r"warfarin", "DOAC": r"apixaban|rivaroxaban|dabigatran|edoxaban",
        "statin": r"statin", "loop diuretic": r"furosemide|torsemide|bumetanide", "RAAS": r"pril$|sartan", "SGLT2": r"gliflozin",
    }
    for key, pattern in classes.items():
        hit = generic.str.contains(pattern, regex=True) & ~generic.str.contains("nystatin")
        print(f"{key}: patients={dedup[hit].Patient.nunique()}")
    surgery = dedup["Medication Therapeutic Class"].eq("ANESTHETICS") | generic.str.contains("protamine|tranexamic|aminocaproic", regex=True)
    print("patients with an anaesthetic/protamine year (surgery marker):", dedup[surgery].Patient.nunique())


def profile_notes(notes):
    section("notes: shape and types")
    print("rows, cols:", notes.shape, "patients:", notes["Profile Key"].nunique())
    print("Type:", notes.Type.value_counts().to_dict())
    print("patients per type:", notes.groupby("Type")["Profile Key"].nunique().to_dict())
    print("Signed Status:", notes["Signed Status"].value_counts().to_dict())
    print("notes per patient:", notes["Profile Key"].value_counts().value_counts().sort_index().to_dict())
    group = notes["Profile Key"].str.slice(8).astype(int).apply(lambda i: "001-100" if i <= 100 else "101-117")
    print(pd.crosstab(group, notes.Type))
    section("notes: follow-up")
    op_year = notes[notes.Type == "Operative Report"].groupby("Profile Key")["Service Date"].min()
    last_year = notes.groupby("Profile Key")["Service Date"].max()
    follow_up = (last_year - op_year).dropna()
    print("years from first operative report to last note:", follow_up.value_counts().sort_index().to_dict())
    section("notes: operative report content")
    op = notes[notes.Type == "Operative Report"].Notes
    patterns = {
        "transcatheter terms": r"transcatheter|\bTAVR\b|\bTAVI\b|sapien|evolut|corevalve",
        "surgical AVR wording": r"aortic valve replacement|\bAVR\b",
        "valve-in-valve": r"valve.in.valve",
        "CABG": r"\bCABG\b|coronary artery bypass",
        "mitral": r"mitral valve|\bMVR\b",
        "size in mm": r"\b(?:19|2[0-9]|3[01])\s?-?\s?mm\b",
    }
    for key, pattern in patterns.items():
        print(f"{key}: reports={op.str.contains(pattern, case=False, regex=True).sum()}")
    models = {"Sapien": r"sapien", "Trifecta": r"trifecta", "Epic": r"\bepic\b", "St Jude other": r"st\.? ?jude", "Evolut/CoreValve": r"evolut|corevalve", "Perimount": r"perimount", "Magna": r"magna", "Inspiris": r"inspiris", "Mosaic/Hancock/Avalus": r"mosaic|hancock|avalus", "Perceval": r"perceval", "mechanical": r"mechanical (?:valve|prosthesis)|on-x"}
    print("valve models:", {k: int(op.str.contains(p, case=False, regex=True).sum()) for k, p in models.items()})
    section("notes: echo values in non-operative notes")
    fu = notes[notes.Type != "Operative Report"]
    echo = {
        "mean gradient mmHg": r"(?i)mean\s+(?:pressure\s+)?gradient[^0-9\n]{0,40}(\d{1,3}(?:\.\d)?)\s*mm\s*hg",
        "peak gradient": r"(?i)peak\s+(?:pressure\s+)?gradient[^0-9\n]{0,40}(\d{1,3})",
        "DVI": r"(?i)(?:DVI|dimensionless)[^0-9\n]{0,30}(0\.\d{1,2})",
        "AVA cm2": r"(?i)(?:AVA|EOA|valve area|orifice area)[^0-9\n]{0,40}(\d\.\d{1,2})\s*cm",
        "LVEF %": r"(?i)(?:LVEF|ejection fraction|\bEF\b)[^0-9\n]{0,25}(\d{2})\s*%?",
        "paravalvular": r"(?i)(paravalvular)",
    }
    for key, pattern in echo.items():
        found = fu.Notes.str.extractall(pattern)
        idx = found.index.get_level_values(0).unique()
        print(f"{key}: matches={len(found)} notes={len(idx)} patients={fu.loc[idx, 'Profile Key'].nunique()}")
    events = notes.Notes.str.contains(r"(?i)valve.in.valve|failed (?:bio)?prosth|degenerat\w* (?:bio)?prosth|prosthetic (?:aortic )?valve (?:failure|stenosis|degeneration|dysfunction)|structural valve deterioration|bioprosthetic valve (?:failure|degeneration|dysfunction)", regex=True)
    print("SVD-type language: notes=", events.sum(), "patients=", notes[events]["Profile Key"].nunique())
    section("notes: redaction")
    joined = "\n".join(notes.Notes)
    print("bracket tokens:", pd.Series(re.findall(r"\[[A-Z_ ]+\]", joined)).value_counts().to_dict())
    print("notes with mm/yyyy partial dates:", notes.Notes.str.contains(r"\b\d{1,2}/(?:19|20)\d{2}\b", regex=True).sum())
    later = sum(any(int(y) > row["Service Date"] for y in re.findall(r"\b((?:19|20)\d{2})\b", row.Notes)) for _, row in notes.iterrows())
    print("notes citing a year after their service year:", later)


if __name__ == "__main__":
    labs, meds, notes = load()
    lab_patients, med_patients, note_patients = set(labs.Patient), set(meds.Patient), set(notes["Profile Key"])
    section("patient overlap")
    print("labs == meds:", lab_patients == med_patients, "| labs subset of notes:", lab_patients <= note_patients, "| notes only:", len(note_patients - lab_patients))
    profile_labs(labs)
    profile_meds(meds)
    profile_notes(notes)
