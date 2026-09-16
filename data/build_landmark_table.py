"""
Build a landmark table for predictive modelling of bioprosthetic aortic
valve failure (structural valve deterioration, SVD) from the workbook
`structured_extraction.xlsx`.

Design
------
Every row of the landmark table is one patient at one landmark time t
(measured in whole years since implant -- the workbook is de-identified
and only calendar years survive, so the clock is integer-valued).

  * Landmarks: fixed points at t = 1, 3, 5 years after the reference echo
    (which, at year granularity, coincides with the implant year), plus one
    landmark at every follow-up prosthetic echo. Duplicates on (patient, t)
    are collapsed. A patient contributes a row only if they are alive and
    SVD-free at t and still under observation after t.
  * Outcome: time from t to the first of {SVD, non-valve death, censoring}
    and which one it was. The workbook contains NO death information
    (checked programmatically), so the competing-death arm is wired in but
    never fires here; when a vital-status feed arrives, populate
    `death_year` in `build_outcomes()` and everything downstream works.
  * The discrete-time person-period table expands each landmark row into
    one row per patient-landmark-year with a three-way status
    (0 = nothing yet, 1 = SVD event, 2 = competing death) -- the form a
    discrete-time / ML hazard model consumes directly.

SVD definition (from the workbook's own `failure_criteria` sheet,
VARC-3 / EAPCI-flavoured, each component kept as a separate column so the
team can toggle them):

  * hemodynamic stage >= 2: mean gradient >= 20 mmHg with a rise >= 10 from
    the reference echo (single-echo fallback: >= 20 with no reference), or
    stage 3: mean gradient >= 30 mmHg or DVI < 0.25;
  * intraprosthetic AR at least moderate and (when a reference grade
    exists) worse than reference; AR flagged as paravalvular is excluded
    (non-structural per the exclusions row);
  * reintervention (redo SAVR / valve-in-valve / balloon valvuloplasty)
    whose stated reason is structural -- endocarditis- or paravalvular-
    leak-driven reinterventions are treated as non-structural and censor
    the patient at that year;
  * explicit prosthetic-failure language ("failure stated" statements and
    non-negated `prosthetic_failure_language` events) -- optional, ON by
    default, column kept separate.

Leakage rules
-------------
  * Every feature merged into a landmark row uses only records with
    year <= landmark calendar year (echo, labs, meds, comorbidity
    statements alike).
  * Event-definition columns never enter the feature blocks.
  * The train/validation/test split is temporal by implant year and by
    patient (each patient has one implant year, so no patient straddles
    splits).

Outputs (written next to the script, then delivered):
  landmark_table.csv       one row per patient x landmark
  person_period_table.csv  one row per patient x landmark x follow-up year
  landmark_build_report.txt sanity counts and leakage checks
"""

from __future__ import annotations

import re
import numpy as np
import pandas as pd

XLSX = "data/structured_extraction.xlsx"
FIXED_LANDMARKS = [1, 3, 5]
MAX_HORIZON = 5          # person-period expansion horizon (years)
HORIZONS = [2, 5]        # label horizons requested
USE_FAILURE_LANGUAGE = True   # include "failure stated" text as an event component
TRAIN_MAX_IMPLANT_YEAR = 2016  # temporal split; chosen below to give ~60/20/20
VALID_MAX_IMPLANT_YEAR = 2019

AR_ORDINAL = {
    "none": 0.0, "no": 0.0, "trace": 0.5, "trivial": 0.5,
    "mild": 1.0, "mild-moderate": 1.5, "moderate": 2.0,
    "moderate-severe": 2.5, "severe": 3.0,
}

VALVE_FAMILY_PATTERNS = [
    (r"sapien", "Sapien (balloon-expandable TAVR)"),
    (r"evolut|corevalve", "Evolut/CoreValve (self-expanding TAVR)"),
    (r"trifecta", "Trifecta"),
    (r"inspiris|resilia", "Inspiris/Resilia"),
    (r"magna|perimount|carpentier|edwards pericardial|pericardial", "Edwards pericardial (CE/Magna/Perimount)"),
    (r"mosaic|hancock|epic|porcine", "Porcine"),
    (r"freestyle|homograft|allograft", "Stentless/homograft"),
    (r"mitroflow|crown|avalus|dokimos|solo|perceval|intuity", "Other stented bovine"),
]


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def valve_family(model: str | float) -> str:
    if not isinstance(model, str) or not model.strip():
        return "unknown"
    m = model.lower()
    for pat, fam in VALVE_FAMILY_PATTERNS:
        if re.search(pat, m):
            return fam
    return "other/unspecified"


def parse_year(val) -> float:
    """Pull a plausible 4-digit year out of a free-text date field."""
    if pd.isna(val):
        return np.nan
    m = re.search(r"(19[89]\d|20[0-3]\d)", str(val))
    return float(m.group(1)) if m else np.nan


def parse_bsa(text) -> float:
    """Du Bois BSA from 'Ht 162.6 cm ... Wt 112.5 kg ...' strings.
    Uses an explicit BSA if the note states one."""
    if not isinstance(text, str):
        return np.nan
    m = re.search(r"BSA[^\d]{0,10}([\d.]+)", text, re.I)
    if m:
        try:
            v = float(m.group(1))
            if 1.0 < v < 3.5:
                return v
        except ValueError:
            pass
    ht = re.search(r"([\d.]+)\s*cm", text)
    if not ht:
        m2 = re.search(r"\(?([\d.]+)\s*m\)?", text)
        ht_cm = float(m2.group(1)) * 100 if m2 and float(m2.group(1)) < 2.5 else np.nan
    else:
        ht_cm = float(ht.group(1))
    wt = re.search(r"([\d.]+)\s*kg", text)
    wt_kg = float(wt.group(1)) if wt else np.nan
    if np.isnan(ht_cm) or np.isnan(wt_kg):
        return np.nan
    return 0.007184 * (ht_cm ** 0.725) * (wt_kg ** 0.425)


def yes(val) -> bool:
    return isinstance(val, str) and val.strip().lower().startswith("yes")


# --------------------------------------------------------------------------
# 1. load
# --------------------------------------------------------------------------

def load(xlsx=XLSX) -> dict[str, pd.DataFrame]:
    xl = pd.ExcelFile(xlsx)
    return {s: xl.parse(s) for s in [
        "patients", "patients_llm_view", "implants", "llm_echo_studies",
        "llm_reinterventions", "llm_status_statements", "llm_clinical_context",
        "labs_by_year", "meds_by_year", "events", "diagnoses",
    ]}


# --------------------------------------------------------------------------
# 2. per-patient spine: implant year, censoring, implant-fixed block
# --------------------------------------------------------------------------

def build_spine(d: dict) -> pd.DataFrame:
    p = d["patients"].copy()
    pv = d["patients_llm_view"].copy()
    imp = d["implants"]

    spine = p[[
        "patient", "implant_year", "implant_approach", "valve_model",
        "valve_size_mm", "native_valve_morphology", "concomitant_procedures",
        "sex", "first_note_year", "last_note_year",
    ]].copy()

    # fall back to LLM extraction where the regex pipeline came up empty
    pv_small = pv.set_index("patient")
    spine = spine.set_index("patient")
    spine["implant_year"] = spine["implant_year"].fillna(pv_small["llm_index_year"])
    spine["valve_size_mm"] = spine["valve_size_mm"].fillna(pv_small["llm_valve_size_mm"])
    spine["valve_model"] = spine["valve_model"].fillna(pv_small["llm_valve_model"])
    spine["sex"] = spine["sex"].fillna(pv_small["llm_sex"].where(
        pv_small["llm_sex"].isin(["male", "female"])))
    spine = spine.reset_index()

    # native morphology also lives in the implants sheet
    morph = (imp.dropna(subset=["native_valve_morphology"])
                .groupby("patient")["native_valve_morphology"].first())
    spine["native_valve_morphology"] = (
        spine["native_valve_morphology"].fillna(spine["patient"].map(morph)))

    spine["valve_family"] = spine["valve_model"].map(valve_family)
    spine["concomitant_cabg"] = (
        spine["concomitant_procedures"].fillna("").str.contains("CABG", case=False))
    # age is redacted throughout this extract ([AGE]); keep the column so the
    # schema is ready when a linked age feed arrives
    spine["age_at_implant"] = np.nan

    # BSA: earliest height/weight note per patient (body size is quasi-stable;
    # flagged with its source year so the team can drop late measurements)
    cc = d["llm_clinical_context"]
    bsa = cc.assign(bsa=cc["height_weight_bsa_bmi"].map(parse_bsa)).dropna(subset=["bsa"])
    bsa = bsa.sort_values("service_year").groupby("patient").first()
    spine["bsa"] = spine["patient"].map(bsa["bsa"])
    spine["bsa_source_year"] = spine["patient"].map(bsa["service_year"])

    spine = spine.dropna(subset=["implant_year"])
    spine["implant_year"] = spine["implant_year"].astype(int)
    return spine


# --------------------------------------------------------------------------
# 3. echo long table (prosthetic studies, one row per patient-year)
# --------------------------------------------------------------------------

def build_echo(d: dict, spine: pd.DataFrame) -> pd.DataFrame:
    es = d["llm_echo_studies"].copy()
    es = es[es["valve_assessed"] == "prosthetic"].copy()

    # best-guess calendar year of the study: an explicit year in the free-text
    # date beats the note's service year
    es["echo_year"] = es["date_as_written"].map(parse_year).fillna(es["service_year"])
    es["ar_num"] = es["aortic_regurgitation_grade"].map(AR_ORDINAL)
    # paravalvular AR must not drive the (structural) event definition
    es["ar_intra_num"] = es["ar_num"].where(es["regurgitation_location"] != "paravalvular")

    grp = es.groupby(["patient", "echo_year"])
    echo = grp.agg(
        mean_gradient=("mean_gradient_mmhg", "max"),   # worst-in-year
        dvi=("dvi", "median"),   # median: robust to one mis-extracted study
        ava=("aortic_valve_area_cm2", "min"),
        ar_grade=("ar_num", "max"),
        ar_intra=("ar_intra_num", "max"),
        lvef=("lvef_percent", "mean"),
        n_studies=("note_id", "size"),
    ).reset_index()

    echo = echo.merge(spine[["patient", "implant_year"]], on="patient")
    echo = echo[echo["echo_year"] >= echo["implant_year"]]
    echo["t"] = (echo["echo_year"] - echo["implant_year"]).astype(int)
    return echo.sort_values(["patient", "echo_year"]).reset_index(drop=True)


def reference_echo(echo: pd.DataFrame) -> pd.DataFrame:
    """First prosthetic echo within 1 year of implant = reference (VARC-3's
    30d-3m window is unresolvable at year granularity). A later first echo is
    still used but flagged."""
    first = echo.groupby("patient").first().reset_index()
    ref = first.rename(columns={
        "mean_gradient": "ref_mean_gradient", "dvi": "ref_dvi",
        "ava": "ref_ava", "ar_intra": "ref_ar_intra", "echo_year": "ref_echo_year",
    })[["patient", "ref_echo_year", "ref_mean_gradient", "ref_dvi", "ref_ava", "ref_ar_intra"]]
    ref["ref_echo_late"] = (ref["ref_echo_year"].notna()
                            & (first.set_index("patient").loc[ref["patient"], "t"].values > 1))
    return ref


# --------------------------------------------------------------------------
# 4. event and censoring times
# --------------------------------------------------------------------------

NONSTRUCTURAL_PAT = re.compile(r"endocarditis|paravalvular", re.I)


def build_outcomes(d: dict, spine: pd.DataFrame, echo: pd.DataFrame,
                   ref: pd.DataFrame) -> pd.DataFrame:
    # ---- component 1: echo-based hemodynamic SVD -------------------------
    e = echo.merge(ref, on="patient", how="left")
    is_ref_row = e["echo_year"] == e["ref_echo_year"]
    rise = e["mean_gradient"] - e["ref_mean_gradient"]

    stage2_grad = np.where(
        e["ref_mean_gradient"].notna() & ~is_ref_row,
        (e["mean_gradient"] >= 20) & (rise >= 10),
        (e["mean_gradient"] >= 20) & ~is_ref_row,   # single-echo fallback
    )
    # DVI-only severe criterion must be corroborated by a non-normal gradient
    # (a low DVI next to a 5-10 mmHg mean gradient is internally inconsistent
    # and, in this workbook, an extraction artifact)
    dvi_severe = (e["dvi"] < 0.25) & (e["mean_gradient"].isna() | (e["mean_gradient"] >= 20))
    stage3 = (e["mean_gradient"] >= 30) | dvi_severe
    stage3 &= ~is_ref_row.values
    ar_worse = np.where(
        e["ref_ar_intra"].notna(),
        (e["ar_intra"] >= 2) & (e["ar_intra"] > e["ref_ar_intra"]),
        e["ar_intra"] >= 2,
    ) & ~is_ref_row.values
    e["hemo_svd"] = stage2_grad | stage3.fillna(False).values | ar_worse
    hemo_year = (e[e["hemo_svd"]].groupby("patient")["echo_year"].min()
                 .rename("svd_echo_year"))

    # ---- component 2: reintervention -------------------------------------
    ri = d["llm_reinterventions"].copy()
    ri["ri_year"] = ri["date_as_written"].map(parse_year).fillna(ri["service_year"])
    ri["structural"] = ~ri["reason_as_written"].fillna("").str.contains(NONSTRUCTURAL_PAT)
    ri_struct = (ri[ri["structural"]].groupby("patient")["ri_year"].min()
                 .rename("svd_reint_year"))
    ri_nonstruct = (ri[~ri["structural"]].groupby("patient")["ri_year"].min()
                    .rename("nonstructural_reint_year"))

    # regex pipeline's reintervention_year as backup
    ri_regex = d["patients"].set_index("patient")["reintervention_year"].rename("svd_reint_regex")

    # ---- component 3: explicit failure language --------------------------
    ss = d["llm_status_statements"]
    fail_stmt = (ss[ss["category"].isin(["failure stated", "stenosis/degeneration"])]
                 .groupby("patient")["service_year"].min().rename("svd_language_year"))
    ev = d["events"]
    fail_ev = (ev[(ev["event_type"] == "prosthetic_failure_language") & (~ev["negated"])]
               .groupby("patient")["note_year"].min())
    fail_year = pd.concat([fail_stmt, fail_ev], axis=1).min(axis=1).rename("svd_language_year")

    # ---- combine ----------------------------------------------------------
    out = spine[["patient", "implant_year", "last_note_year"]].copy().set_index("patient")
    out = (out.join(hemo_year).join(ri_struct).join(ri_nonstruct)
              .join(ri_regex).join(fail_year))
    # regex reintervention year is a backup ONLY for patients the LLM sheet
    # missed entirely -- otherwise it would resurrect reinterventions the LLM
    # classified as non-structural (e.g. endocarditis-driven redo)
    no_llm_ri = ~out.index.isin(ri["patient"])
    out.loc[no_llm_ri, "svd_reint_year"] = (
        out.loc[no_llm_ri, "svd_reint_year"].fillna(out.loc[no_llm_ri, "svd_reint_regex"]))

    # failure language in the year of (or after) a non-structural
    # reintervention describes that non-structural failure -- suppress it
    lang_is_nonstruct = out["svd_language_year"] >= out["nonstructural_reint_year"]
    out.loc[lang_is_nonstruct.fillna(False), "svd_language_year"] = np.nan

    parts = ["svd_echo_year", "svd_reint_year"]
    if USE_FAILURE_LANGUAGE:
        parts.append("svd_language_year")
    out["svd_year"] = out[parts].min(axis=1)
    # an event can only happen after implant
    out.loc[out["svd_year"] < out["implant_year"], "svd_year"] = np.nan

    # no death data exists in this extract (verified by text search);
    # populate this column when a vital-status linkage arrives
    out["death_year"] = np.nan

    # censoring = end of observation, or a non-structural reintervention
    # (valve replaced for endocarditis / PVL -> original prosthesis no longer
    # at risk of SVD)
    out["censor_year"] = out[["last_note_year", "nonstructural_reint_year"]].min(axis=1)

    out["exit_year"] = out[["svd_year", "death_year", "censor_year"]].min(axis=1)
    out["exit_status"] = np.select(
        [out["exit_year"].eq(out["svd_year"]), out["exit_year"].eq(out["death_year"])],
        ["event", "death"], default="censored")
    return out.reset_index()


# --------------------------------------------------------------------------
# 5. clinical block (year-indexed lookups, all filtered to <= landmark year)
# --------------------------------------------------------------------------

def latest_at(df, patient, year_col, year, value_col):
    sub = df[(df["patient"] == patient) & (df[year_col] <= year)]
    if sub.empty:
        return np.nan, np.nan
    row = sub.loc[sub[year_col].idxmax()]
    return row[value_col], row[year_col]


LVH_POS = re.compile(r"LVH|hypertroph", re.I)
LVH_NEG = re.compile(r"\b(?:no|without|resolved)\b[^.;|]{0,25}(?:LVH|hypertroph)", re.I)


def build_clinical_lookup(d: dict):
    lb = d["labs_by_year"]
    labs = {a: lb[lb["analyte"] == a][["patient", "year", "mean"]]
            for a in ["creatinine", "egfr", "calcium", "phosphorus", "lvef"]}

    mb = d["meds_by_year"]
    ac = mb[mb["medication_class"].isin(["warfarin", "doac"])][
        ["patient", "year", "medication_class"]]
    dm_meds = mb[mb["medication_class"].isin(["insulin", "oral_antidiabetic", "sglt2"])][
        ["patient", "year"]]

    cc = d["llm_clinical_context"]
    def comorb_years(col):
        sub = cc[cc[col].map(yes)]
        return sub.groupby("patient")["service_year"].min()
    dm_first = comorb_years("comorbidity_diabetes")
    af_first = comorb_years("comorbidity_atrial_fibrillation")
    endo_first = comorb_years("comorbidity_endocarditis_history")

    ev = d["events"]
    endo_ev = (ev[(ev["event_type"] == "endocarditis") & (~ev["negated"])]
               .groupby("patient")["note_year"].min())
    endo_first = pd.concat([endo_first, endo_ev], axis=1).min(axis=1)

    amio = mb[mb["medication_class"] == "amiodarone"].groupby("patient")["year"].min()

    # dyslipidemia: stated comorbidity, corroborated by statin prescriptions
    hld_first = comorb_years("comorbidity_hyperlipidemia")
    statin_first = (mb[mb["medication_class"] == "statin"]
                    .groupby("patient")["year"].min())
    hld_first = pd.concat([hld_first, statin_first], axis=1).min(axis=1)

    # renal insufficiency as a STATED diagnosis (covers cohort A, which has
    # no lab feed; the creatinine/egfr columns cover cohort B)
    ckd_first = comorb_years("comorbidity_chronic_kidney_disease_or_dialysis")

    # smoking status: latest informative value (current/former/never)
    smoke = cc[cc["comorbidity_smoking"].isin(["current", "former", "never"])][
        ["patient", "service_year", "comorbidity_smoking"]]

    # BMI: stated explicitly in the height/weight note text; time-varying
    bmi = cc.assign(bmi=cc["height_weight_bsa_bmi"].astype(str)
                    .str.extract(r"BMI\s*([\d.]+)")[0].astype(float))
    bmi = bmi.dropna(subset=["bmi"])[["patient", "service_year", "bmi"]]
    bmi = bmi[(bmi["bmi"] > 10) & (bmi["bmi"] < 80)]

    # LVH: positive mention in echo ventricle free-text, negations excluded.
    # Year granularity supports presence, not the formal "persistent LVH
    # despite AVR" definition (which needs serial wall measurements).
    es = d["llm_echo_studies"]
    txt = es["other_valves_and_ventricle"].astype(str)
    lvh_pos = txt.str.contains(LVH_POS) & ~txt.str.contains(LVH_NEG)
    lvh_year = es.loc[lvh_pos, "date_as_written"].map(parse_year).fillna(
        es.loc[lvh_pos, "service_year"])
    lvh_first = (pd.DataFrame({"patient": es.loc[lvh_pos, "patient"],
                               "year": lvh_year})
                 .groupby("patient")["year"].min())

    return dict(labs=labs, ac=ac, dm_meds=dm_meds, dm_first=dm_first,
                af_first=af_first, endo_first=endo_first, amio_first=amio,
                hld_first=hld_first, ckd_first=ckd_first,
                smoke=smoke, bmi=bmi, lvh_first=lvh_first)


def clinical_features(clin, patient, year):
    f = {}
    for a, df in clin["labs"].items():
        v, _ = latest_at(df, patient, "year", year, "mean")
        f[f"{a}_lab_latest" if a == "lvef" else f"{a}_latest"] = v
    ca, ph = f.get("calcium_latest"), f.get("phosphorus_latest")
    f["ca_phos_product"] = ca * ph if pd.notna(ca) and pd.notna(ph) else np.nan

    ac = clin["ac"]
    sub = ac[(ac["patient"] == patient) & (ac["year"] <= year)]
    if sub.empty:
        f["anticoagulant_status"] = "none/unknown"
    else:
        f["anticoagulant_status"] = sub.loc[sub["year"].idxmax(), "medication_class"]

    dm_med = clin["dm_meds"]
    dm_med_hit = ((dm_med["patient"] == patient) & (dm_med["year"] <= year)).any()
    dm_stated = clin["dm_first"].get(patient, np.inf) <= year
    f["diabetes"] = bool(dm_med_hit or dm_stated)

    af_stated = clin["af_first"].get(patient, np.inf) <= year
    amio_hit = clin["amio_first"].get(patient, np.inf) <= year
    f["atrial_fibrillation"] = bool(af_stated or amio_hit)
    f["endocarditis_history"] = bool(clin["endo_first"].get(patient, np.inf) <= year)

    f["hyperlipidemia"] = bool(clin["hld_first"].get(patient, np.inf) <= year)
    f["ckd_stated"] = bool(clin["ckd_first"].get(patient, np.inf) <= year)
    f["lvh_so_far"] = bool(clin["lvh_first"].get(patient, np.inf) <= year)
    f["smoking_status"], _ = latest_at(clin["smoke"], patient, "service_year",
                                       year, "comorbidity_smoking")
    if pd.isna(f["smoking_status"]):
        f["smoking_status"] = "unknown"
    f["bmi_latest"], _ = latest_at(clin["bmi"], patient, "service_year",
                                   year, "bmi")
    return f


# --------------------------------------------------------------------------
# 6. landmark rows
# --------------------------------------------------------------------------

def build_landmarks(spine, echo, ref, outcomes, clin) -> pd.DataFrame:
    out_idx = outcomes.set_index("patient")
    ref_idx = ref.set_index("patient")
    rows = []

    for _, sp in spine.iterrows():
        pid, iy = sp["patient"], sp["implant_year"]
        if pid not in out_idx.index:
            continue
        oc = out_idx.loc[pid]
        pe = echo[echo["patient"] == pid]
        rf = ref_idx.loc[pid] if pid in ref_idx.index else None

        # candidate landmarks: fixed 1/3/5y + every follow-up prosthetic echo
        # (the reference echo itself is t=0, not a landmark)
        cand = set(FIXED_LANDMARKS)
        follow_ts = pe.loc[pe["echo_year"] != (rf["ref_echo_year"] if rf is not None else -1), "t"]
        cand |= {int(t) for t in follow_ts if t >= 1}

        for t in sorted(cand):
            ly = iy + t                                   # landmark calendar year
            exit_year, status = oc["exit_year"], oc["exit_status"]
            if pd.isna(exit_year) or exit_year <= ly:      # must be at risk past t
                continue

            r = {
                "patient": pid, "landmark_t": t, "landmark_year": ly,
                "landmark_source": "echo" if t in set(follow_ts.astype(int)) else "fixed",
                # ---- implant-fixed block ----
                "approach": sp["implant_approach"],
                "valve_family": sp["valve_family"],
                "valve_size_mm": sp["valve_size_mm"],
                "age_at_implant": sp["age_at_implant"],
                "sex": sp["sex"], "bsa": sp["bsa"],
                "native_morphology": sp["native_valve_morphology"],
                "concomitant_cabg": sp["concomitant_cabg"],
                "implant_year": iy,
            }
            if rf is not None:
                r["ref_mean_gradient"] = rf["ref_mean_gradient"]
                r["ref_dvi"] = rf["ref_dvi"]
                iEOA = (rf["ref_ava"] / sp["bsa"]
                        if pd.notna(rf["ref_ava"]) and pd.notna(sp["bsa"]) else np.nan)
            else:
                r["ref_mean_gradient"] = r["ref_dvi"] = iEOA = np.nan
            r["indexed_eoa"] = iEOA
            r["ppm_moderate_or_worse"] = bool(iEOA < 0.85) if pd.notna(iEOA) else np.nan
            r["ppm_severe"] = bool(iEOA < 0.65) if pd.notna(iEOA) else np.nan

            # ---- time-varying echo block (echoes strictly up to t) ----
            hist = pe[pe["echo_year"] <= ly]
            r["n_echoes_so_far"] = len(hist)
            r["time_since_implant"] = t
            if len(hist):
                def last_nonnull(col):
                    s = hist[col].dropna()
                    return s.iloc[-1] if len(s) else np.nan
                # "latest" = most recent recorded value up to t (values are
                # sparse at year granularity, so carry the last non-missing
                # measurement forward rather than blanking on a partial echo)
                r["mg_latest"] = last_nonnull("mean_gradient")
                r["dvi_latest"] = last_nonnull("dvi")
                r["ava_latest"] = last_nonnull("ava")
                r["ar_grade_latest"] = last_nonnull("ar_grade")
                r["lvef_latest"] = last_nonnull("lvef")
                r["years_since_last_echo"] = ly - hist["echo_year"].iloc[-1]
                r["mg_change_from_ref"] = (r["mg_latest"] - r["ref_mean_gradient"]
                                           if pd.notna(r["ref_mean_gradient"]) else np.nan)
                r["dvi_change_from_ref"] = (r["dvi_latest"] - r["ref_dvi"]
                                            if pd.notna(r["ref_dvi"]) else np.nan)
                mg_hist = hist.dropna(subset=["mean_gradient"])
                if len(mg_hist) >= 2:
                    a, b = mg_hist.iloc[-2], mg_hist.iloc[-1]
                    dt = max(b["echo_year"] - a["echo_year"], 1)
                    r["mg_slope_last_two"] = (b["mean_gradient"] - a["mean_gradient"]) / dt
                else:
                    r["mg_slope_last_two"] = np.nan
            else:
                for c in ["mg_latest", "dvi_latest", "ava_latest", "ar_grade_latest",
                          "lvef_latest", "years_since_last_echo", "mg_change_from_ref",
                          "dvi_change_from_ref", "mg_slope_last_two"]:
                    r[c] = np.nan

            # ---- clinical block ----
            r.update(clinical_features(clin, pid, ly))
            # LVEF: structured lab feed (cohort B) backs up the echo notes
            if pd.isna(r["lvef_latest"]):
                r["lvef_latest"] = r["lvef_lab_latest"]

            # ---- outcomes from t ----
            tte = exit_year - ly                      # whole years, >= 1 here
            r["time_to_exit_years"] = tte
            r["exit_status"] = status
            for h in HORIZONS:
                if tte <= h:
                    r[f"label_{h}y"] = {"event": "event", "death": "competing_death",
                                        "censored": "censored_early"}[status]
                else:
                    r[f"label_{h}y"] = "event_free"
            rows.append(r)

    lm = pd.DataFrame(rows).drop_duplicates(subset=["patient", "landmark_t"])
    return lm.sort_values(["patient", "landmark_t"]).reset_index(drop=True)


# --------------------------------------------------------------------------
# 7. discrete-time person-period expansion + temporal split
# --------------------------------------------------------------------------

def expand_person_period(lm: pd.DataFrame) -> pd.DataFrame:
    rows = []
    status_code = {"event": 1, "death": 2}
    for _, r in lm.iterrows():
        n_years = int(min(np.ceil(r["time_to_exit_years"]), MAX_HORIZON))
        for k in range(1, n_years + 1):
            pr = r.to_dict()
            pr["interval_k"] = k                       # (t+k-1, t+k] after landmark
            last = k == n_years
            terminal = r["time_to_exit_years"] <= MAX_HORIZON
            pr["status_3way"] = status_code.get(r["exit_status"], 0) if (last and terminal) else 0
            pr["censored_in_interval"] = bool(last and terminal
                                              and r["exit_status"] == "censored")
            rows.append(pr)
    return pd.DataFrame(rows)


def add_split(df: pd.DataFrame) -> pd.DataFrame:
    df["split"] = np.select(
        [df["implant_year"] <= TRAIN_MAX_IMPLANT_YEAR,
         df["implant_year"] <= VALID_MAX_IMPLANT_YEAR],
        ["train", "valid"], default="test")
    return df


# --------------------------------------------------------------------------
# 8. checks + main
# --------------------------------------------------------------------------

def leakage_checks(lm, pp):
    msgs = []
    assert (lm["landmark_year"] == lm["implant_year"] + lm["landmark_t"]).all()
    # no feature computed after the landmark
    ok = lm["years_since_last_echo"].dropna() >= 0
    assert ok.all(), "echo feature dated after landmark"
    # each patient in exactly one split
    n_splits = lm.groupby("patient")["split"].nunique()
    assert (n_splits == 1).all(), "patient straddles splits"
    # at-risk condition: exit strictly after landmark
    assert (lm["time_to_exit_years"] > 0).all()
    # person-period: at most one terminal row per landmark
    term = pp[pp["status_3way"] > 0].groupby(["patient", "landmark_t"]).size()
    assert (term <= 1).all()
    msgs.append("all leakage/consistency assertions passed")
    return msgs


def main():
    d = load()
    spine = build_spine(d)
    echo = build_echo(d, spine)
    ref = reference_echo(echo)
    outcomes = build_outcomes(d, spine, echo, ref)
    clin = build_clinical_lookup(d)

    lm = build_landmarks(spine, echo, ref, outcomes, clin)
    lm = add_split(lm)
    pp = expand_person_period(lm)

    lm.to_csv("data/landmark_table.csv", index=False)
    pp.to_csv("data/person_period_table.csv", index=False)

    with open("data/landmark_build_report.txt", "w") as f:
        def w(*a): print(*a, file=f)
        w("LANDMARK TABLE BUILD REPORT")
        w("=" * 60)
        w(f"patients in workbook          : {len(d['patients'])}")
        w(f"patients with implant year    : {len(spine)}")
        w(f"patients contributing rows    : {lm['patient'].nunique()}")
        w(f"landmark rows                 : {len(lm)}")
        w(f"person-period rows            : {len(pp)}")
        w()
        w("SVD component years (patients with each):")
        oc = outcomes
        for c in ["svd_echo_year", "svd_reint_year", "svd_language_year", "svd_year"]:
            w(f"  {c:22s}: {oc[c].notna().sum()}")
        w(f"  non-structural reint (censor): {oc['nonstructural_reint_year'].notna().sum()}")
        w(f"  death (no data in extract)   : {oc['death_year'].notna().sum()}")
        w()
        w("exit status at end of follow-up (all patients):")
        w(oc["exit_status"].value_counts().to_string())
        w()
        w("landmark rows by t:")
        w(lm["landmark_t"].value_counts().sort_index().to_string())
        w()
        w("labels at horizons (landmark rows):")
        for h in HORIZONS:
            w(f"  {h}y: {lm[f'label_{h}y'].value_counts().to_dict()}")
        w()
        w("person-period 3-way status: "
          f"{pp['status_3way'].value_counts().to_dict()} "
          f"(0=nothing yet, 1=SVD, 2=competing death)")
        w()
        w("temporal split (patients / landmark rows / events within 5y):")
        for s in ["train", "valid", "test"]:
            sub = lm[lm["split"] == s]
            w(f"  {s:5s}: {sub['patient'].nunique():3d} patients, "
              f"{len(sub):4d} rows, "
              f"{(sub['label_5y'] == 'event').sum():3d} event rows, "
              f"implant years {sub['implant_year'].min()}-{sub['implant_year'].max()}")
        w()
        for m in leakage_checks(lm, pp):
            w(m)
        w()
        w("feature completeness (landmark rows, % non-missing):")
        feat_cols = [c for c in lm.columns if c not in
                     ["patient", "landmark_t", "landmark_year", "landmark_source",
                      "implant_year", "time_to_exit_years", "exit_status",
                      "label_2y", "label_5y", "split"]]
        comp = (lm[feat_cols].notna().mean() * 100).round(0).astype(int)
        w(comp.to_string())

    # print(open("landmark_build_report.txt").read())


if __name__ == "__main__":
    main()
