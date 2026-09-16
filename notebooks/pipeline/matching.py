import numpy as np
import pandas as pd

from pipeline import landmarks

ECHO_FIELDS = ["mean_gradient_mmhg", "peak_gradient_mmhg", "dvi", "aortic_valve_area_cm2", "ar_intraprosthetic", "lvef_percent"]
COVARIATE_FIELDS = {"sex": "sex", "bsa_m2": "bsa_m2", "diabetes": "diabetes", "chronic_kidney_disease_or_dialysis": "ckd", "smoking": "smoking"}
IMPLANT_FIELDS = {"valve_model": "valve_model", "valve_size_mm": "valve_size_mm", "native_valve_morphology": "bicuspid"}

MATCH_CONFIG = dict(
    year_resolution=True,
    hide_age=True,
    hide_implant_eoa=True,
    hide_deaths=True,
    match_echo_counts=True,
    match_echo_fields=True,
    match_covariates=True,
    events="reintervention_only",
    match_follow_up=True,
    seed=0,
)


def reference_profile(real_prepared):
    imp = real_prepared["implants"]
    imp = imp[imp.implant_year.notna()]
    echo = real_prepared["echo_timeline"]
    echo = echo[echo.episode_id.isin(imp.episode_id)]
    counts = echo.groupby("episode_id").size().reindex(imp.episode_id).fillna(0).astype(int)
    fu = real_prepared["follow_up"]
    fu = fu[fu.episode_id.isin(imp.episode_id)]
    span = (fu.end_year - fu.implant_year).astype(float)
    tables = landmarks.from_preprocessing({**real_prepared, "source": "real", "time_resolution": "year"})
    presence = tables["patients"].notna().mean()
    return dict(
        echo_counts=counts.value_counts(normalize=True).sort_index(),
        reference_share=float(echo.groupby("episode_id").is_reference.any().mean()),
        echo_fields=echo[ECHO_FIELDS].notna().mean(),
        covariates={k: float(presence[v]) for k, v in {**COVARIATE_FIELDS, **IMPLANT_FIELDS}.items()},
        event_free_span=span[fu.status.ne("svd")].round().astype(int).value_counts(normalize=True).sort_index(),
        event_share=float(fu.status.eq("svd").mean()),
    )


def _mask(values, keep_share, rng):
    return values.where(rng.random(len(values)) < keep_share)


def match_to_reference(prepared, profile, config=MATCH_CONFIG):
    c = config
    rng = np.random.default_rng(c["seed"])
    out = {k: (v.copy() if isinstance(v, pd.DataFrame) else v) for k, v in prepared.items()}
    imp, echo, ev, fu, cov = (out[k] for k in ["implants", "echo_timeline", "events", "follow_up", "covariates"])
    iy = imp.set_index("episode_id").implant_year
    if c["hide_age"]:
        cov["age_at_implant"] = np.nan
    if c["hide_implant_eoa"]:
        imp["eoa_cm2_implant"] = np.nan
        imp["eoa_index_implant"] = np.nan
    if c["match_covariates"]:
        for col in COVARIATE_FIELDS:
            share = profile["covariates"][col]
            if col in cov:
                blank = rng.random(len(cov)) >= share
                cov[col] = cov[col].astype(object)
                cov.loc[blank, col] = "not stated" if col in ("diabetes", "chronic_kidney_disease_or_dialysis", "smoking") else np.nan
        for col in IMPLANT_FIELDS:
            if col in imp:
                imp[col] = _mask(imp[col], profile["covariates"][col], rng)
    if c["match_echo_counts"]:
        k = rng.choice(profile["echo_counts"].index.to_numpy(), size=len(imp), p=profile["echo_counts"].to_numpy())
        want = pd.Series(k, index=imp.episode_id.to_numpy())
        keep = []
        for eid, g in echo.groupby("episode_id"):
            n = int(want.get(eid, 0))
            if n == 0:
                continue
            ref = g[g.is_reference]
            chosen = []
            if len(ref) and rng.random() < profile["reference_share"]:
                chosen.append(ref.index[0])
            rest = g.index.difference(chosen)
            extra = min(n - len(chosen), len(rest))
            if extra > 0:
                chosen += list(rng.choice(rest, extra, replace=False))
            keep += chosen
        echo = echo.loc[sorted(keep)].copy()
    if c["match_echo_fields"]:
        for col in ECHO_FIELDS:
            if col in echo:
                echo[col] = _mask(echo[col], float(profile["echo_fields"][col]), rng)
    echo["is_reference"] = echo.is_reference & echo.mean_gradient_mmhg.notna()
    if c["events"] == "reintervention_only":
        ev = ev[ev.source.eq("reintervention")].copy()
    elif c["events"] == "observable":
        detected = set(zip(echo.episode_id, echo.days_from_implant if "days_from_implant" in echo else echo.study_year))
        key = ev.days_high if "days_high" in ev else ev.year_high
        ev = ev[ev.source.eq("reintervention") | [(e, d) in detected for e, d in zip(ev.episode_id, key)]].copy()
    has_event = fu.episode_id.isin(ev.episode_id).to_numpy()
    if c["hide_deaths"]:
        dead = fu.status.eq("death").to_numpy()
        fu.loc[dead, "status"] = "censored"
    fu.loc[~has_event & fu.status.eq("svd").to_numpy(), "status"] = "censored"
    fu.loc[has_event, "status"] = "svd"
    if c["match_follow_up"]:
        span = rng.choice(profile["event_free_span"].index.to_numpy(), size=len(fu), p=profile["event_free_span"].to_numpy())
        base = fu.implant_year.to_numpy(float)
        censored = fu.status.eq("censored").to_numpy()
        new_end = np.minimum(fu.end_year.to_numpy(float), base + span)
        fu.loc[censored, "end_year"] = new_end[censored]
        fu.loc[censored, "last_contact_year"] = new_end[censored]
        if "end_days" in fu:
            cut = (new_end - base + 1) * landmarks.DAYS_PER_YEAR
            fu.loc[censored, "end_days"] = np.minimum(fu.end_days.to_numpy(float), cut)[censored]
            fu.loc[censored, "contact_days"] = np.minimum(fu.contact_days.to_numpy(float), cut)[censored]
        visible_until = fu.set_index("episode_id").end_year
        yr = echo.study_year
        echo = echo[(yr <= echo.episode_id.map(visible_until)).to_numpy()].copy()
    if c["year_resolution"]:
        echo = echo.drop(columns=[x for x in ["days_from_implant"] if x in echo])
        ev = ev.drop(columns=[x for x in ["days_low", "days_high"] if x in ev])
        fu = fu.drop(columns=[x for x in ["end_days", "contact_days"] if x in fu])
        out["time_resolution"] = "year"
    out.update(implants=imp, echo_timeline=echo, events=ev, follow_up=fu, covariates=cov)
    return out


def compare_profiles(prepared, profile):
    ref = reference_profile(prepared) if isinstance(prepared, dict) else prepared
    rows = {
        "valves with any echo": (1 - profile["echo_counts"].get(0, 0), 1 - ref["echo_counts"].get(0, 0)),
        "valves with 3 or more echoes": (profile["echo_counts"][profile["echo_counts"].index >= 3].sum(), ref["echo_counts"][ref["echo_counts"].index >= 3].sum()),
        "valves with an event": (profile["event_share"], ref["event_share"]),
        "event-free valves followed under 1 year": (profile["event_free_span"].get(0, 0), ref["event_free_span"].get(0, 0)),
    }
    rows.update({f"echo {k} present": (profile["echo_fields"][k], ref["echo_fields"][k]) for k in ECHO_FIELDS})
    rows.update({f"{k} present": (profile["covariates"][k], ref["covariates"][k]) for k in profile["covariates"]})
    return pd.DataFrame(rows, index=["real extract", "training cohort"]).T
