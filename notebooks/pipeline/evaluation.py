import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline import landmarks, ml, viz

MODEL_FILES = {
    "calendar": "calendar schedule",
    "time_only": "valve age only",
    "cox": "Cox, risk factors",
    "baseline": "regression baseline",
    "primary": "gradient boosting",
    "primary_unconstrained": "gradient boosting, no constraints",
    "baseline_recalibrated": "regression baseline, recalibrated",
    "primary_recalibrated": "gradient boosting, recalibrated",
}
REQUIRED_MODELS = ["calendar", "time_only", "cox", "baseline", "primary", "primary_unconstrained"]
MODEL_COLORS = {
    "calendar schedule": viz.AXIS,
    "valve age only": viz.MUTED,
    "Cox, risk factors": viz.SERIES[2],
    "regression baseline": viz.SERIES[0],
    "gradient boosting": viz.SERIES[1],
    "gradient boosting, no constraints": "#e87ba4",
    "regression baseline, recalibrated": "#4a3aa7",
    "gradient boosting, recalibrated": "#eda100",
}


def color(name):
    return MODEL_COLORS.get(name, viz.INK_SECONDARY)


def missing_inputs(run_dir, real_dir):
    need = [Path(run_dir) / "model_input.pkl"] + [Path(run_dir) / "models" / f"{f}.pkl" for f in REQUIRED_MODELS]
    need += [Path(real_dir) / f"{n}.parquet" for n in ["implants", "echo_timeline", "events", "follow_up", "covariates"]]
    return [p for p in need if not p.exists()]


def load_run(run_dir):
    run_dir = Path(run_dir)
    bundle = pickle.loads((run_dir / "model_input.pkl").read_bytes())
    models = {}
    for stem, name in MODEL_FILES.items():
        f = run_dir / "models" / f"{stem}.pkl"
        if f.exists():
            models[name] = pickle.loads(f.read_bytes())
    return bundle, models


def score_real(bundle, real_dir):
    tables = landmarks.from_preprocessing(Path(real_dir))
    lm, outcomes = landmarks.build_landmark_table(tables, bundle["labels"])
    Xr, mr = ml.feature_matrix(lm)
    Xr = Xr.reindex(columns=bundle["X"].columns)
    return Xr.reset_index(drop=True), mr.reset_index(drop=True), outcomes


def predict_all(models, X, horizons):
    out = {}
    for name, model in models.items():
        cif = model.predict_cif(X)
        out[name] = pd.DataFrame({h: cif[f"svd_{h}y"].to_numpy(float) for h in horizons if f"svd_{h}y" in cif})
    return out


def _arrays(meta):
    return meta.time_to_end.to_numpy(float), meta.status.to_numpy()


def point_metrics(p, time, status, h, G=None):
    G = G or ml.censoring_survival(time, status)
    obs = ml.aalen_johansen(time, status, h)
    brier = ml.cr_brier(p, time, status, h, G)
    null = ml.cr_brier(np.full(len(p), obs), time, status, h, G)
    return dict(auc=ml.cr_auc(p, time, status, h, G), brier=brier, brier_null=null,
                scaled_brier=1 - brier / null if null > 0 else np.nan, mean_predicted=float(np.mean(p)), observed=obs,
                oe_ratio=obs / float(np.mean(p)) if np.mean(p) > 0 else np.nan)


def performance(preds, meta):
    t, s = _arrays(meta)
    G = ml.censoring_survival(t, s)
    rows = {(name, h): point_metrics(cif[h].to_numpy(), t, s, h, G) for name, cif in preds.items() for h in cif}
    return pd.DataFrame(rows).T.rename_axis(["model", "horizon"])


def bootstrap(preds, meta, n_boot=300, seed=0, metrics=("auc", "scaled_brier")):
    rng = np.random.default_rng(seed)
    t, s = _arrays(meta)
    pid = meta.patient_id.to_numpy()
    patients = np.unique(pid)
    rows_of = {p: np.flatnonzero(pid == p) for p in patients}
    draws = []
    for b in range(n_boot):
        idx = np.concatenate([rows_of[p] for p in rng.choice(patients, len(patients), replace=True)])
        tb, sb = t[idx], s[idx]
        G = ml.censoring_survival(tb, sb)
        for name, cif in preds.items():
            for h in cif:
                m = point_metrics(cif[h].to_numpy()[idx], tb, sb, h, G)
                draws.append(dict(boot=b, model=name, horizon=h, **{k: m[k] for k in metrics}))
    draws = pd.DataFrame(draws)
    lo = draws.groupby(["model", "horizon"])[list(metrics)].quantile(0.025)
    hi = draws.groupby(["model", "horizon"])[list(metrics)].quantile(0.975)
    return lo.add_suffix("_lo").join(hi.add_suffix("_hi"))


def cohort_summary(meta, outcomes, X, horizons):
    event_valves = meta.patient_id[meta.status.eq("svd")].nunique()
    per = meta.groupby("patient_id").size()
    t, s = _arrays(meta)
    out = {
        "valves with a known implant year": len(outcomes),
        "valves scored (followed beyond the first landmark)": meta.patient_id.nunique(),
        "landmark rows scored": len(meta),
        "landmark rows per valve (median / max)": f"{per.median():.0f} / {per.max()}",
        "valves with a structural event": event_valves,
        "valves with a recorded death": meta.patient_id[meta.status.eq("death")].nunique(),
        "TAVR / SAVR / unknown approach (valves)": "{} / {} / {}".format(*_approach_counts(meta, X)),
        "follow-up after landmark, median (years)": f"{np.median(t):.1f}",
    }
    for h in horizons:
        out[f"observed SVD within {h} years (Aalen-Johansen, rows)"] = f"{ml.aalen_johansen(t, s, h):.1%}"
        out[f"rows censored before {h} years"] = int(((s == "censored") & (t < h)).sum())
    return pd.Series(out, name="real extract").to_frame()


def _approach_counts(meta, X):
    first = pd.DataFrame({"pid": meta.patient_id, "tavr": X["tavr"] if "tavr" in X else np.nan}).groupby("pid").tavr.first()
    return int(first.eq(1).sum()), int(first.eq(0).sum()), int(first.isna().sum())


def calibration_groups(p, meta, h, n_groups=3):
    p = np.asarray(p, float)
    t, s = _arrays(meta)
    ranks = pd.Series(p).rank(method="first")
    groups = pd.qcut(ranks, n_groups, labels=False)
    rows = []
    for g in range(n_groups):
        m = (groups == g).to_numpy()
        rows.append(dict(group=g + 1, rows=int(m.sum()), valves=meta.patient_id[m].nunique(),
                         valves_with_event=meta.patient_id[m & (s == "svd") & (t <= h)].nunique(),
                         predicted_low=p[m].min(), predicted_high=p[m].max(),
                         mean_predicted=p[m].mean(), observed=ml.aalen_johansen(t[m], s[m], h)))
    return pd.DataFrame(rows).set_index("group")


def net_benefit(p, meta, h, thresholds):
    p = np.asarray(p, float)
    t, s = _arrays(meta)
    rows = []
    for th in thresholds:
        pos = p >= th
        odds = th / (1 - th)
        cif_pos = ml.aalen_johansen(t[pos], s[pos], h) if pos.any() else 0.0
        share = pos.mean()
        rows.append(dict(threshold=th, net_benefit=share * cif_pos - share * (1 - cif_pos) * odds, flagged=share))
    return pd.DataFrame(rows).set_index("threshold")


def treat_all(meta, h, thresholds):
    t, s = _arrays(meta)
    cif = ml.aalen_johansen(t, s, h)
    return pd.Series([cif - (1 - cif) * th / (1 - th) for th in thresholds], index=thresholds)


def tier_labels(p):
    return pd.Series([ml.risk_tier(v)[0] for v in np.asarray(p, float)])


def tier_table(p, meta, h):
    t, s = _arrays(meta)
    tiers = tier_labels(p).to_numpy()
    rows = []
    for _, name, action in ml.RISK_TIERS:
        m = tiers == name
        rows.append(dict(tier=name, action=action, rows=int(m.sum()), share=m.mean(), valves=meta.patient_id[m].nunique(),
                         valves_with_event=meta.patient_id[m & (s == "svd") & (t <= h)].nunique(),
                         mean_predicted=np.asarray(p)[m].mean() if m.any() else np.nan,
                         observed=ml.aalen_johansen(t[m], s[m], h) if m.any() else np.nan))
    return pd.DataFrame(rows).set_index("tier")


def threshold_metrics(p, meta, h, cut):
    t, s = _arrays(meta)
    G = ml.censoring_survival(t, s)
    case, control, w = ml._ipcw(t, s, h, G)
    pos = np.asarray(p, float) >= cut
    tp, fn = (w * (case & pos)).sum(), (w * (case & ~pos)).sum()
    fp, tn = (w * (control & pos)).sum(), (w * (control & ~pos)).sum()
    div = lambda a, b: a / b if b > 0 else np.nan
    return dict(cutoff=cut, flagged=pos.mean(), sensitivity=div(tp, tp + fn), specificity=div(tn, tn + fp),
                ppv=div(tp, tp + fp), npv=div(tn, tn + fn), accuracy=div(tp + tn, tp + tn + fp + fn),
                accuracy_flag_nobody=div(tn + fp, tp + tn + fp + fn))


def subgroup_table(preds, meta, h, groups, min_events=3):
    t, s = _arrays(meta)
    rows = []
    for gname, mask in groups.items():
        m = np.asarray(mask, bool)
        n_ev = meta.patient_id[m & (s == "svd") & (t <= h)].nunique()
        n_ctrl = int((m & (t > h)).sum())
        row = dict(subgroup=gname, rows=int(m.sum()), valves=meta.patient_id[m].nunique(), valves_with_event=n_ev,
                   rows_event_free_past_horizon=n_ctrl, observed=ml.aalen_johansen(t[m], s[m], h) if m.any() else np.nan)
        ok = n_ev >= min_events and n_ctrl >= min_events
        Gm = ml.censoring_survival(t[m], s[m]) if m.any() else None
        for name, cif in preds.items():
            row[name] = ml.cr_auc(cif[h].to_numpy()[m], t[m], s[m], h, Gm) if ok else np.nan
        rows.append(row)
    return pd.DataFrame(rows).set_index("subgroup")

