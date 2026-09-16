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
    follow_up_window="all",
    late_event_capture=0.25,
    window_min_years=1,
    echo_counts_by_span=True,
    case_mix=True,
    sample_size=None,
    informative_missingness=True,
    gradient_scale=True,
    echo_timing="real",
    seed=0,
)
YEAR_BUCKETS = [0, 2013, 2016, 2019, 2022]
FLAG_FIELDS = {"diabetes": ("yes", "no"), "chronic_kidney_disease_or_dialysis": ("yes", "no"), "smoking": ("current", "never")}
SPAN_BUCKETS = [0, 1, 3, 6]


def _era(years):
    return np.searchsorted(YEAR_BUCKETS, np.asarray(years, float), side="right") - 1


def _family_of(models):
    fam = models.map(landmarks._family)
    known = {f for f, _ in landmarks.FAMILY_PATTERNS}
    return fam.where(fam.isin(known), "other").fillna("unknown")


def _flag_profile(cov, col, positive):
    v = cov[col].astype(object)
    stated = v.isin(["yes", "no"]) if col != "smoking" else v.isin(["current", "former", "never"])
    return dict(presence=float(stated.mean()), positive=float((v[stated] == positive).mean()) if stated.any() else 0.0)


def _echo_positions(imp, echo, fu):
    iy = imp.set_index("episode_id").implant_year
    end = fu.set_index("episode_id").end_year
    e = echo[~echo.is_reference.astype(bool)]
    e = e.assign(after=e.study_year - e.episode_id.map(iy), end=e.episode_id.map(end))
    e = e[(e.end - e.episode_id.map(iy)) >= 1]
    pos = np.select([e.study_year > e.end, e.study_year == e.end, e.after <= 0], ["after", "end", "implant"], "middle")
    counts = pd.Series(pos).value_counts()
    counts = counts.drop("after", errors="ignore")
    return (counts / counts.sum()).reindex(["end", "implant", "middle"]).fillna(0)


def _gradient_medians(imp, echo):
    ap = echo.episode_id.map(imp.set_index("episode_id").approach)
    return echo.groupby([ap, echo.is_reference.astype(bool)])[["mean_gradient_mmhg", "peak_gradient_mmhg"]].median()


def reference_profile(real_prepared):
    imp = real_prepared["implants"]
    imp = imp[imp.implant_year.notna()]
    echo = real_prepared["echo_timeline"]
    echo = echo[echo.episode_id.isin(imp.episode_id)]
    cov = real_prepared["covariates"]
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
        echo_counts_by_span={b: d.value_counts(normalize=True).sort_index() for b, d in counts.groupby(_bucket(span.to_numpy(float)))},
        approach_by_era=pd.crosstab(_era(imp.implant_year), imp.approach, normalize=True),
        sex=imp.patient.map(cov.set_index("patient").sex).value_counts(normalize=True),
        family=_family_of(imp.valve_model).value_counts(normalize=True),
        flags={col: _flag_profile(cov, col, pos) for col, (pos, _) in FLAG_FIELDS.items()},
        gradients=_gradient_medians(imp, echo),
        echo_positions=_echo_positions(imp, echo, fu),
        covariate_columns=list(cov.columns),
    )


def _bucket(span):
    return np.searchsorted(SPAN_BUCKETS, np.asarray(span, float), side="right") - 1


def _draw(dist, n, rng, low=None):
    d = dist[dist.index >= low] if low is not None else dist
    return rng.choice(d.index.to_numpy(), size=n, p=(d / d.sum()).to_numpy())


def _window_all(c, profile, rng, echo, ev, fu):
    base = fu.implant_year.to_numpy(float)
    limit = base + _draw(profile["event_free_span"], len(fu), rng, c["window_min_years"])
    limit_of = pd.Series(limit, index=fu.episode_id.to_numpy())
    late = pd.Series(rng.random(len(fu)) < c["late_event_capture"], index=fu.episode_id.to_numpy())
    keep = (ev.year_high.to_numpy(float) <= ev.episode_id.map(limit_of).to_numpy(float)) | ev.episode_id.map(late).to_numpy(bool)
    ev = ev[keep].copy()
    event_year = ev.groupby("episode_id").year_high.min().reindex(fu.episode_id).to_numpy(float)
    has_event = ~np.isnan(event_year)
    if c["hide_deaths"]:
        fu.loc[fu.status.eq("death").to_numpy(), "status"] = "censored"
    fu.loc[~has_event & fu.status.eq("svd").to_numpy(), "status"] = "censored"
    fu.loc[has_event, "status"] = "svd"
    old_end = fu.end_year.to_numpy(float)
    new_end = np.where(has_event, np.maximum(np.nan_to_num(event_year), np.minimum(old_end, limit)), np.minimum(old_end, limit))
    fu["end_year"] = new_end
    fu["last_contact_year"] = np.minimum(fu.last_contact_year.to_numpy(float), new_end)
    if "end_days" in fu:
        cut = (new_end - base + 1) * landmarks.DAYS_PER_YEAR
        fu["end_days"] = np.minimum(fu.end_days.to_numpy(float), cut)
        fu["contact_days"] = np.minimum(fu.contact_days.to_numpy(float), cut)
        if "days_high" in ev:
            ev_end = ev.days_high.groupby(ev.episode_id).min().reindex(fu.episode_id).to_numpy(float)
            fu["end_days"] = np.where(has_event, np.maximum(fu.end_days.to_numpy(float), ev_end), fu.end_days.to_numpy(float))
            fu["contact_days"] = np.where(has_event, np.maximum(fu.contact_days.to_numpy(float), ev_end), fu.contact_days.to_numpy(float))
    visible_until = fu.set_index("episode_id").end_year
    echo = echo[(echo.study_year <= echo.episode_id.map(visible_until)).to_numpy()].copy()
    return echo, ev, fu


def _mask(values, keep_share, rng):
    return values.where(rng.random(len(values)) < keep_share)


def _event_free_window(c, profile, rng, echo, ev, fu):
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
    return echo, ev, fu


def _rake(pool, targets, iterations=25):
    w = np.ones(len(pool))
    for _ in range(iterations):
        for col, target in targets.items():
            cur = pd.Series(w).groupby(pool[col].to_numpy()).sum()
            cur = cur / cur.sum()
            ratio = (target.reindex(cur.index).fillna(0) / cur.replace(0, np.nan)).fillna(0)
            w = w * pool[col].map(ratio).to_numpy(float)
    return w / w.sum()


def resample_case_mix(prepared, profile, n, rng):
    imp, cov = prepared["implants"], prepared["covariates"]
    pool = pd.DataFrame(dict(
        episode_id=imp.episode_id.to_numpy(),
        cell=[f"{e}|{a}" for e, a in zip(_era(imp.implant_year), imp.approach)],
        sex=imp.patient.map(cov.set_index("patient").sex).fillna("unknown").to_numpy(),
        family=_family_of(imp.valve_model).to_numpy(),
    ))
    cells = profile["approach_by_era"].stack()
    cells.index = [f"{e}|{a}" for e, a in cells.index]
    targets = dict(cell=cells, sex=profile["sex"], family=profile["family"].drop("unknown", errors="ignore") / profile["family"].drop("unknown", errors="ignore").sum())
    w = _rake(pool, targets)
    n = min(n, int((w > 0).sum()))
    chosen = set(rng.choice(pool.episode_id.to_numpy(), size=n, replace=False, p=w))
    patients = set(imp.patient[imp.episode_id.isin(chosen)])
    out = dict(prepared)
    for name, key in [("implants", "episode_id"), ("echo_timeline", "episode_id"), ("events", "episode_id"), ("follow_up", "episode_id")]:
        out[name] = prepared[name][prepared[name][key].isin(chosen)].copy()
    out["covariates"] = prepared["covariates"][prepared["covariates"].patient.isin(patients)].copy()
    return out


def _mask_flags(cov, profile, rng):
    for col, (pos, _) in FLAG_FIELDS.items():
        if col not in cov:
            continue
        v = cov[col].astype(object)
        target = profile["flags"][col]
        s = float((v == pos).mean())
        p, q = target["presence"], target["positive"]
        k_pos = min(1.0, p * q / s) if s > 0 else 0.0
        k_neg = min(1.0, p * (1 - q) / (1 - s)) if s < 1 else 0.0
        keep = np.where(v == pos, rng.random(len(v)) < k_pos, rng.random(len(v)) < k_neg)
        cov[col] = v.where(keep, "not stated")
    return cov


def _scale_gradients(imp, echo, profile):
    real = profile["gradients"]
    pool = _gradient_medians(imp, echo)
    ap = echo.episode_id.map(imp.set_index("episode_id").approach)
    ref = echo.is_reference.astype(bool)
    for col in ["mean_gradient_mmhg", "peak_gradient_mmhg"]:
        factor = (real[col] / pool[col]).reindex(pool.index).fillna(1.0)
        f = [factor.get((a, r), 1.0) for a, r in zip(ap, ref)]
        echo[col] = (echo[col] * np.asarray(f, float)).round(1)
    return echo


def _place_echoes(g, n, end_year, profile, rng):
    chosen = []
    ref = g[g.is_reference]
    if len(ref) and rng.random() < profile["reference_share"]:
        chosen.append(ref.index[0])
    positions = profile["echo_positions"]
    rest = g.drop(index=chosen).sort_values("study_year")
    for _ in range(n - len(chosen)):
        if rest.empty:
            break
        where = rng.choice(positions.index.to_numpy(), p=positions.to_numpy())
        if where == "end":
            pick = rest.index[-1]
        elif where == "implant":
            pick = rest.index[0]
        else:
            pick = rng.choice(rest.index.to_numpy())
        chosen.append(pick)
        rest = rest.drop(index=pick)
        if where == "end":
            g.loc[pick, "study_year"] = end_year
    return chosen


def match_to_reference(prepared, profile, config=MATCH_CONFIG):
    c = {**MATCH_CONFIG, **config}
    rng = np.random.default_rng(c["seed"])
    if c["case_mix"]:
        size = c["sample_size"] or len(prepared["implants"]) // 3
        prepared = resample_case_mix(prepared, profile, size, rng)
    out = {k: (v.copy() if isinstance(v, pd.DataFrame) else v) for k, v in prepared.items()}
    imp, echo, ev, fu, cov = (out[k] for k in ["implants", "echo_timeline", "events", "follow_up", "covariates"])
    if c["gradient_scale"]:
        echo = _scale_gradients(imp, echo, profile)
    if c["hide_age"]:
        cov["age_at_implant"] = np.nan
    if c["hide_implant_eoa"]:
        imp["eoa_cm2_implant"] = np.nan
        imp["eoa_index_implant"] = np.nan
    if c["match_covariates"]:
        if c["informative_missingness"]:
            cov = _mask_flags(cov, profile, rng)
        for col in cov.columns.difference(profile.get("covariate_columns", cov.columns)):
            cov[col] = "not stated"
        for col in COVARIATE_FIELDS:
            share = profile["covariates"][col]
            if c["informative_missingness"] and col in FLAG_FIELDS:
                continue
            if col in cov:
                blank = rng.random(len(cov)) >= share
                cov[col] = cov[col].astype(object)
                cov.loc[blank, col] = "not stated" if col in ("diabetes", "chronic_kidney_disease_or_dialysis", "smoking") else np.nan
        for col in IMPLANT_FIELDS:
            if col in imp:
                imp[col] = _mask(imp[col], profile["covariates"][col], rng)
    window_all = c["match_follow_up"] and c["follow_up_window"] == "all"
    if window_all:
        if c["events"] == "reintervention_only":
            ev = ev[ev.source.eq("reintervention")].copy()
        echo, ev, fu = _window_all(c, profile, rng, echo, ev, fu)
    if c["match_echo_counts"]:
        k = rng.choice(profile["echo_counts"].index.to_numpy(), size=len(imp), p=profile["echo_counts"].to_numpy())
        want = pd.Series(k, index=imp.episode_id.to_numpy())
        if c["echo_counts_by_span"]:
            span = fu.end_year.to_numpy(float) - fu.implant_year.to_numpy(float)
            buckets = _bucket(span)
            k = np.zeros(len(fu), int)
            for b in np.unique(buckets):
                m = buckets == b
                dist = profile["echo_counts_by_span"].get(b, profile["echo_counts"])
                k[m] = rng.choice(dist.index.to_numpy(), size=m.sum(), p=dist.to_numpy())
            want = pd.Series(k, index=fu.episode_id.to_numpy())
        keep = []
        end_of = fu.set_index("episode_id").end_year
        placed = []
        for eid, g in echo.groupby("episode_id"):
            n = int(want.get(eid, 0))
            if n == 0:
                continue
            if c["echo_timing"] == "real":
                g = g.copy()
                picks = _place_echoes(g, n, end_of.get(eid, g.study_year.max()), profile, rng)
                placed.append(g.loc[picks])
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
        echo = pd.concat(placed).sort_index() if c["echo_timing"] == "real" and placed else echo.loc[sorted(keep)].copy()
    if c["match_echo_fields"]:
        for col in ECHO_FIELDS:
            if col in echo:
                echo[col] = _mask(echo[col], float(profile["echo_fields"][col]), rng)
    echo["is_reference"] = echo.is_reference & echo.mean_gradient_mmhg.notna()
    if not window_all and c["events"] == "reintervention_only":
        ev = ev[ev.source.eq("reintervention")].copy()
    elif not window_all and c["events"] == "observable":
        detected = set(zip(echo.episode_id, echo.days_from_implant if "days_from_implant" in echo else echo.study_year))
        key = ev.days_high if "days_high" in ev else ev.year_high
        ev = ev[ev.source.eq("reintervention") | [(e, d) in detected for e, d in zip(ev.episode_id, key)]].copy()
    if not window_all:
        echo, ev, fu = _event_free_window(c, profile, rng, echo, ev, fu)
    if c["year_resolution"]:
        echo = echo.drop(columns=[x for x in ["days_from_implant"] if x in echo])
        ev = ev.drop(columns=[x for x in ["days_low", "days_high"] if x in ev])
        fu = fu.drop(columns=[x for x in ["end_days", "contact_days"] if x in fu])
        out["time_resolution"] = "year"
    out.update(implants=imp, echo_timeline=echo, events=ev, follow_up=fu, covariates=cov)
    return out


def distinguishability(X_synthetic, X_real, groups_synthetic, groups_real, columns=None, n_synthetic=3000, seed=0):
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import GroupKFold, cross_val_predict
    rng = np.random.default_rng(seed)
    pick = rng.choice(len(X_synthetic), min(n_synthetic, len(X_synthetic)), replace=False)
    X = pd.concat([X_synthetic.iloc[pick], X_real], ignore_index=True)
    cols = [col for col in (columns or X.columns) if X[col].dropna().nunique() >= 3]
    if not cols:
        return np.nan
    y = np.r_[np.zeros(len(pick)), np.ones(len(X_real))]
    g = np.r_[np.asarray(groups_synthetic)[pick], np.asarray(groups_real)]
    clf = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.05, max_leaf_nodes=15, random_state=seed)
    p = cross_val_predict(clf, X[cols], y, cv=GroupKFold(5), groups=g, method="predict_proba")[:, 1]
    return float(roc_auc_score(y, p))


def compare_profiles(prepared, profile):
    ref = reference_profile(prepared) if isinstance(prepared, dict) else prepared
    rows = {
        "valves with any echo": (1 - profile["echo_counts"].get(0, 0), 1 - ref["echo_counts"].get(0, 0)),
        "valves with 3 or more echoes": (profile["echo_counts"][profile["echo_counts"].index >= 3].sum(), ref["echo_counts"][ref["echo_counts"].index >= 3].sum()),
        "valves with an event": (profile["event_share"], ref["event_share"]),
        "event-free valves followed under 1 year": (profile["event_free_span"].get(0, 0), ref["event_free_span"].get(0, 0)),
    }
    rows.update({
        "TAVR share": (profile["approach_by_era"].get("TAVR", pd.Series(dtype=float)).sum(), ref["approach_by_era"].get("TAVR", pd.Series(dtype=float)).sum()),
        "TAVR share among implants from 2019": (_share_late_tavr(profile), _share_late_tavr(ref)),
        "male (where known)": (profile["sex"].get("male", 0) / profile["sex"].reindex(["male", "female"]).sum(), ref["sex"].get("male", 0) / ref["sex"].reindex(["male", "female"]).sum()),
        "Evolut valves": (profile["family"].get("Evolut", 0), ref["family"].get("Evolut", 0)),
        "Trifecta valves": (profile["family"].get("Trifecta", 0), ref["family"].get("Trifecta", 0)),
        "non-reference echoes in the last year seen": (profile["echo_positions"].get("end", 0), ref["echo_positions"].get("end", 0)),
    })
    rows.update({f"{k} stated": (profile["flags"][k]["presence"], ref["flags"][k]["presence"]) for k in FLAG_FIELDS})
    rows.update({f"{k}: positive when stated": (profile["flags"][k]["positive"], ref["flags"][k]["positive"]) for k in FLAG_FIELDS})
    rows.update({f"echo {k} present": (profile["echo_fields"][k], ref["echo_fields"][k]) for k in ECHO_FIELDS})
    rows.update({f"{k} present": (profile["covariates"][k], ref["covariates"][k]) for k in profile["covariates"]})
    table = pd.DataFrame(rows, index=["real extract", "training cohort"]).T
    grad = pd.DataFrame({"real extract": profile["gradients"]["mean_gradient_mmhg"], "training cohort": ref["gradients"]["mean_gradient_mmhg"]})
    grad.index = [f"median mean gradient, {a}, {'reference' if r else 'later'} echo (mmHg)" for a, r in grad.index]
    return table, grad


def _share_late_tavr(p):
    t = p["approach_by_era"]
    late = t.loc[t.index >= 3]
    return float(late.get("TAVR", pd.Series(dtype=float)).sum() / late.values.sum()) if late.values.sum() else np.nan
