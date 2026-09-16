import re

import numpy as np
import pandas as pd

DAYS_PER_YEAR = 365.25
ENDPOINTS = {
    "stage2_or_worse": ("svd_stage2", "svd_stage3", "bvf_reintervention"),
    "stage3_or_bvf": ("svd_stage3", "bvf_reintervention"),
}
AR_ORDINAL = {"none": 0.0, "trace": 0.5, "mild": 1.0, "mild-moderate": 1.5, "moderate": 2.0, "moderate-severe": 2.5, "severe": 3.0}
PPM_ORDINAL = {"none": 0.0, "moderate": 1.0, "severe": 2.0}
VALVE_FAMILIES = ["Sapien 3", "Evolut", "Trifecta", "Perimount", "Epic", "Magna", "Inspiris"]
ECHO_VALUES = {"mean_gradient_mmhg": "mg", "peak_gradient_mmhg": "peak", "dvi": "dvi", "eoa_cm2": "eoa", "ar": "ar", "lvef_pct": "lvef"}

LABEL_CONFIG = dict(
    endpoint="stage2_or_worse",
    event_time="observed",
    censor_at_last_echo=True,
    landmarks_years=(0.5, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10),
    horizons=(2, 5, 8),
    recent_window_years=2.0,
)


def build_outcomes(tables, config=LABEL_CONFIG):
    p = tables["patients"][["patient_id", "implant_year"]].copy()
    ev = tables["events"]
    fu = tables["followup"].set_index("patient_id")
    echo_last = tables["echos"].groupby("patient_id").days_from_implant.max()
    endpoint = ev[ev.event_type.isin(ENDPOINTS[config["endpoint"]])].sort_values("days_from_implant").groupby("patient_id").first()
    death = ev[ev.event_type.eq("death")].groupby("patient_id").days_from_implant.min()
    p["endpoint_observed_days"] = p.patient_id.map(endpoint.days_from_implant)
    p["endpoint_interval_start_days"] = p.patient_id.map(endpoint.interval_start_days)
    p["endpoint_type"] = p.patient_id.map(endpoint.event_type)
    p["endpoint_ascertainment"] = p.patient_id.map(endpoint.ascertainment)
    if config["event_time"] == "midpoint":
        p["endpoint_days"] = (p.endpoint_interval_start_days + p.endpoint_observed_days) / 2
    else:
        p["endpoint_days"] = p.endpoint_observed_days
    p["death_days"] = p.patient_id.map(death)
    p["last_contact_days"] = p.patient_id.map(fu.last_contact_days)
    p["last_echo_days"] = p.patient_id.map(echo_last)
    inf = np.inf
    e, d, c = p.endpoint_days.fillna(inf), p.death_days.fillna(inf), p.last_contact_days.astype(float)
    end = np.minimum(np.minimum(e, d), c)
    status = np.where(e <= np.minimum(d, c), "svd", np.where(d <= c, "death", "censored"))
    if config["censor_at_last_echo"]:
        cut = (status == "censored") & p.last_echo_days.notna()
        end = np.where(cut, np.minimum(end, p.last_echo_days), end)
    p["end_days"] = end
    p["status"] = status
    p["end_years"] = p.end_days / DAYS_PER_YEAR
    return p


def _echo_frame(echos):
    e = echos.copy()
    e["ar"] = e.ar_grade.map(AR_ORDINAL)
    e["years"] = e.days_from_implant / DAYS_PER_YEAR
    return e.sort_values(["patient_id", "days_from_implant"])


def _echo_features_at(e, s, recent):
    seen = e[e.years <= s]
    if seen.empty:
        return pd.DataFrame()
    g = seen.groupby("patient_id")
    last = g.tail(1).set_index("patient_id")
    out = pd.DataFrame(index=last.index)
    for col, short in ECHO_VALUES.items():
        out[f"last_{short}"] = g[col].last()
    ref = seen[seen.is_reference].groupby("patient_id").first()
    for col, short in ECHO_VALUES.items():
        out[f"ref_{short}"] = ref[col].reindex(out.index)
    out["ref_missing"] = out.ref_mg.isna().astype(float) if "ref_mg" in out else 1.0
    for short in ["mg", "dvi", "eoa", "ar"]:
        out[f"delta_{short}"] = out[f"last_{short}"] - out[f"ref_{short}"]
    out["max_mg"] = g.mean_gradient_mmhg.max()
    tail2 = seen.dropna(subset=["mean_gradient_mmhg"]).groupby("patient_id").tail(2)
    first, second = tail2.groupby("patient_id").first(), tail2.groupby("patient_id").last()
    dt = second.years - first.years
    out["mg_slope"] = ((second.mean_gradient_mmhg - first.mean_gradient_mmhg) / dt).where(dt >= 0.25).reindex(out.index)
    out["n_echo"] = g.size()
    out["n_echo_recent"] = seen[seen.years > s - recent].groupby("patient_id").size().reindex(out.index).fillna(0)
    out["years_since_last_echo"] = s - last.years
    return out


def _baseline_features(patients):
    p = patients.set_index("patient_id")
    b = pd.DataFrame(index=p.index)
    b["age_at_implant"] = p.age_at_implant
    b["male"] = p.sex.map({"male": 1.0, "female": 0.0})
    b["bsa_m2"] = p.bsa_m2
    b["tavr"] = p.approach.map({"TAVR": 1.0, "SAVR": 0.0})
    for fam in VALVE_FAMILIES:
        b[f"valve_{fam.lower().replace(' ', '_')}"] = p.valve_model.eq(fam).astype(float).where(p.valve_model.notna())
    b["valve_size_mm"] = p.valve_size_mm.astype(float)
    b["eoa_index_implant"] = p.eoa_index_cm2_m2
    b["ppm_grade"] = p.ppm_grade.map(PPM_ORDINAL)
    for c in ["diabetes", "ckd", "smoking", "bicuspid", "anticoagulation"]:
        b[c] = p[c].map({True: 1.0, False: 0.0})
    return b


def build_landmark_table(tables, config=LABEL_CONFIG):
    outcomes = build_outcomes(tables, config).set_index("patient_id")
    echos = _echo_frame(tables["echos"])
    base = _baseline_features(tables["patients"])
    source = tables["patients"].set_index("patient_id").source
    resolution = tables["echos"].groupby("patient_id").time_resolution.first()
    frames = []
    for s in config["landmarks_years"]:
        risk = outcomes[outcomes.end_years > s]
        if risk.empty:
            continue
        f = pd.DataFrame(index=risk.index)
        f["landmark_years"] = float(s)
        f = f.join(_echo_features_at(echos[echos.patient_id.isin(risk.index)], s, config["recent_window_years"]), how="left")
        f["n_echo"] = f["n_echo"].fillna(0) if "n_echo" in f else 0.0
        f = f.join(base, how="left")
        t = risk.end_years - s
        f["time_to_end"] = t
        f["status"] = risk.status
        for h in config["horizons"]:
            f[f"svd_{h}y"] = np.where((risk.status == "svd") & (t <= h), 1.0, np.where((t >= h) | (risk.status == "death"), 0.0, np.nan))
            f[f"death_{h}y"] = np.where((risk.status == "death") & (t <= h), 1.0, np.where((t >= h) | (risk.status == "svd"), 0.0, np.nan))
        f["implant_year"] = risk.implant_year
        frames.append(f.reset_index())
    lm = pd.concat(frames, ignore_index=True)
    lm["source"] = lm.patient_id.map(source)
    lm["time_resolution"] = lm.patient_id.map(resolution).fillna("unknown")
    lm["landmark_id"] = lm.patient_id + "@" + lm.landmark_years.map("{:g}".format)
    return lm, outcomes.reset_index()


FAMILY_PATTERNS = [("Sapien 3", r"sapien"), ("Evolut", r"evolut|corevalve"), ("Trifecta", r"trifecta"),
                   ("Perimount", r"perimount|carpentier"), ("Magna", r"magna"), ("Inspiris", r"inspiris"), ("Epic", r"\bepic\b")]
AR_LABELS = [(0.25, "none"), (0.75, "trace"), (1.25, "mild"), (1.75, "mild-moderate"), (2.25, "moderate"), (2.75, "moderate-severe"), (9.0, "severe")]
EVENT_TYPES = {"HVD stage 2": "svd_stage2", "HVD stage 3": "svd_stage3"}


def _family(model):
    if not isinstance(model, str):
        return None
    for family, pattern in FAMILY_PATTERNS:
        if re.search(pattern, model, re.IGNORECASE):
            return family
    return model


def _ar_label(v):
    if pd.isna(v):
        return None
    return next(label for cut, label in AR_LABELS if v < cut)


def _yesno(v):
    return {"yes": True, "no": False}.get(v)


def synthetic_to_preprocessing(tables):
    p = tables["patients"].copy()
    ids = p.patient_id
    implants = pd.DataFrame(dict(
        episode_id=ids, patient=ids, episode=1, kind="index", procedure=p.approach, approach=p.approach,
        implant_year=p.implant_year, valve_model=p.valve_model, valve_size_mm=p.valve_size_mm.astype(float),
        native_valve_morphology=p.bicuspid.map({True: "bicuspid", False: "tricuspid"}),
        eoa_cm2_implant=p.eoa_cm2, eoa_index_implant=p.eoa_index_cm2_m2,
    ))
    iy = p.set_index("patient_id").implant_year
    e = tables["echos"]
    echo = pd.DataFrame(dict(
        study_id=e.echo_id, episode_id=e.patient_id, patient=e.patient_id, days_from_implant=e.days_from_implant,
        study_year=(e.patient_id.map(iy) + e.days_from_implant // DAYS_PER_YEAR).astype(int), is_reference=e.is_reference.astype(bool),
        mean_gradient_mmhg=e.mean_gradient_mmhg, peak_gradient_mmhg=e.peak_gradient_mmhg, dvi=e.dvi,
        aortic_valve_area_cm2=e.eoa_cm2, aortic_valve_area_indexed_cm2_m2=np.nan,
        ar_intraprosthetic=e.ar_grade.map(AR_ORDINAL), lvef_percent=e.lvef_pct,
    ))
    ev = tables["events"]
    svd = ev[ev.event_type.ne("death")]
    name = {"svd_stage2": "HVD stage 2", "svd_stage3": "HVD stage 3", "bvf_reintervention": "reintervention: valve replacement"}
    to_year = lambda pid, d: (pid.map(iy) + d // DAYS_PER_YEAR).astype(int)
    events = pd.DataFrame(dict(
        event_id=svd.patient_id + "-" + svd.event_type, episode_id=svd.patient_id, patient=svd.patient_id,
        source=np.where(svd.ascertainment.eq("echo"), "echo", "reintervention"), event_type=svd.event_type.map(name),
        days_low=svd.interval_start_days, days_high=svd.days_from_implant,
        year_low=to_year(svd.patient_id, svd.interval_start_days), year_high=to_year(svd.patient_id, svd.days_from_implant),
        is_structural=True, adjudicated=True,
    ))
    events["event_year"] = events.year_high
    death = ev[ev.event_type.eq("death")].groupby("patient_id").days_from_implant.min()
    fu = tables["followup"].set_index("patient_id")
    has_svd = fu.index.isin(svd.patient_id)
    death_days = fu.index.map(death).to_numpy(float)
    died_in_view = np.nan_to_num(death_days, nan=np.inf) <= fu.last_contact_days.to_numpy(float)
    status = np.where(died_in_view, "death", np.where(has_svd, "svd", "censored"))
    end_days = np.where(status == "death", death_days, fu.last_contact_days.to_numpy(float))
    follow_up = pd.DataFrame(dict(
        episode_id=fu.index, patient=fu.index, implant_year=fu.index.map(iy), status=status,
        end_days=end_days, contact_days=fu.last_contact_days.to_numpy(float),
        end_year=(fu.index.map(iy) + end_days // DAYS_PER_YEAR).astype(int),
        last_contact_year=(fu.index.map(iy) + fu.last_contact_days // DAYS_PER_YEAR).astype(int),
    ))
    yes = lambda s: s.map({True: "yes", False: "no"}).fillna("not stated")
    covariates = pd.DataFrame(dict(
        patient=ids, group="simulated", sex=p.sex, bsa_m2=p.bsa_m2, age_at_implant=p.age_at_implant,
        diabetes=yes(p.diabetes), chronic_kidney_disease_or_dialysis=yes(p.ckd),
        smoking=p.smoking.map({True: "current", False: "never"}).fillna("not stated"),
        anticoagulation=yes(p.anticoagulation),
    ))
    resolution = tables["echos"].time_resolution.iloc[0] if len(tables["echos"]) else "unknown"
    return dict(implants=implants, echo_timeline=echo, events=events, follow_up=follow_up, covariates=covariates,
                source="simulated", time_resolution=resolution)


def from_preprocessing(prepared):
    if not isinstance(prepared, dict):
        read = lambda n: pd.read_parquet(prepared / f"{n}.parquet")
        prepared = {n: read(n) for n in ["implants", "echo_timeline", "events", "follow_up", "covariates"]}
        prepared.update(source="real", time_resolution="year")
    implants, echo, events, follow_up, cov = (prepared[n] for n in ["implants", "echo_timeline", "events", "follow_up", "covariates"])
    imp = implants[implants.implant_year.notna()].copy()
    imp["iy"] = imp.implant_year.astype(int)
    cov = cov.set_index("patient")
    get = lambda col: imp.patient.map(cov[col]) if col in cov else pd.Series(np.nan, index=imp.index)
    ref = echo[echo.is_reference].set_index("episode_id")
    eoa = imp.eoa_cm2_implant if "eoa_cm2_implant" in imp else imp.episode_id.map(ref.aortic_valve_area_cm2)
    bsa = pd.to_numeric(get("bsa_m2"), errors="coerce")
    eoa_i = imp.eoa_index_implant if "eoa_index_implant" in imp else imp.episode_id.map(ref.aortic_valve_area_indexed_cm2_m2).astype(float).fillna(eoa / bsa)
    patients = pd.DataFrame(dict(
        patient_id=imp.episode_id, implant_year=imp.iy, age_at_implant=pd.to_numeric(get("age_at_implant"), errors="coerce"),
        sex=get("sex"), bsa_m2=bsa, approach=imp.approach, valve_model=imp.valve_model.map(_family),
        valve_size_mm=imp.valve_size_mm, eoa_cm2=eoa, eoa_index_cm2_m2=eoa_i,
        ppm_grade=np.select([eoa_i <= 0.65, eoa_i <= 0.85, eoa_i.notna()], ["severe", "moderate", "none"], None),
        diabetes=get("diabetes").map(_yesno), ckd=get("chronic_kidney_disease_or_dialysis").map(_yesno),
        smoking=get("smoking").map({"current": True, "former": False, "never": False}),
        anticoagulation=get("anticoagulation").map(_yesno),
        bicuspid=imp.native_valve_morphology.map({"bicuspid": True, "unicuspid": True, "tricuspid": False}),
    ))
    iy = patients.set_index("patient_id").implant_year
    years_to_days = lambda years: np.round(np.clip(np.asarray(years, float), 0, None) * DAYS_PER_YEAR)
    e = echo[echo.episode_id.isin(iy.index)].copy()
    days = e.days_from_implant.to_numpy(float) if "days_from_implant" in e else years_to_days(e.study_year - e.episode_id.map(iy))
    echos = pd.DataFrame(dict(
        patient_id=e.episode_id, echo_id=e.study_id, days_from_implant=days.astype(int), is_reference=e.is_reference.astype(bool),
        mean_gradient_mmhg=e.mean_gradient_mmhg, peak_gradient_mmhg=e.peak_gradient_mmhg, dvi=e.dvi,
        eoa_cm2=e.aortic_valve_area_cm2, ar_grade=e.ar_intraprosthetic.map(_ar_label), lvef_pct=e.lvef_percent,
    ))
    ev = events[events.is_structural.astype(bool) & events.episode_id.isin(iy.index)].copy()
    ev["schema_type"] = ev.event_type.map(lambda t: EVENT_TYPES.get(t, "bvf_reintervention"))
    base = ev.episode_id.map(iy).astype(float)
    hi = ev.days_high.to_numpy(float) if "days_high" in ev else years_to_days(ev.year_high.astype(float) - base)
    lo = ev.days_low.to_numpy(float) if "days_low" in ev else years_to_days(ev.year_low.astype(float).fillna(base) - base)
    ev["hi"], ev["lo"] = hi, np.minimum(lo, hi)
    ev = ev.sort_values("hi").groupby(["episode_id", "schema_type"], as_index=False).first()
    fu = follow_up[follow_up.episode_id.isin(iy.index)].set_index("episode_id")
    base_fu = fu.index.map(iy).to_numpy(float)
    end_days = fu.end_days.to_numpy(float) if "end_days" in fu else years_to_days(fu.end_year.astype(float).to_numpy() - base_fu)
    contact_days = fu.contact_days.to_numpy(float) if "contact_days" in fu else years_to_days(fu.last_contact_year.astype(float).to_numpy() - base_fu)
    is_svd, is_death = fu.status.eq("svd").to_numpy(), fu.status.eq("death").to_numpy()
    replaced = fu.end_reason.eq("non-structural reintervention").to_numpy() if "end_reason" in fu else np.zeros(len(fu), bool)
    last_contact = np.where(is_svd, np.maximum(contact_days, end_days), np.where(is_death | replaced, end_days, np.maximum(contact_days, end_days)))
    deaths = pd.DataFrame(dict(patient_id=fu.index[is_death], event_type="death", days_from_implant=end_days[is_death],
                               interval_start_days=end_days[is_death], ascertainment="registry"))
    events_out = pd.concat([pd.DataFrame(dict(
        patient_id=ev.episode_id, event_type=ev.schema_type, days_from_implant=ev.hi, interval_start_days=ev.lo,
        ascertainment=np.where(ev.source.eq("echo"), "echo", "reintervention"),
    )), deaths], ignore_index=True)
    events_out[["days_from_implant", "interval_start_days"]] = events_out[["days_from_implant", "interval_start_days"]].round().astype(int)
    followup = pd.DataFrame(dict(
        patient_id=fu.index, last_contact_days=np.round(last_contact).astype(int),
        n_echos=fu.index.map(echos.groupby("patient_id").size()).fillna(0).astype(int),
        censoring_reason=np.select([is_death, is_svd], ["death", "event"], "administrative"),
    ))
    tables = dict(patients=patients.reset_index(drop=True), echos=echos.reset_index(drop=True), events=events_out, followup=followup.reset_index(drop=True))
    for t in tables.values():
        t["source"] = prepared["source"]
        t["time_resolution"] = prepared["time_resolution"]
    return tables
