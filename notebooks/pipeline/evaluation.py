import pickle
import subprocess
from datetime import datetime
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
LOG_COLUMNS = ["timestamp", "commit", "run", "label", "preset", "source", "selection_enabled", "split_year", "seed", "endpoint",
               "model", "horizon", "rows", "valves", "events", "observed", "mean_predicted", "oe_ratio",
               "auc", "auc_lo", "auc_hi", "c_index", "c_index_lo", "c_index_hi", "brier", "brier_null", "scaled_brier", "scaled_brier_lo", "scaled_brier_hi"]


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


def ipcw_weights(time, status, h, G):
    t, s = np.asarray(time, float), np.asarray(status)
    case = (s == "svd") & (t <= h)
    dead = (s == "death") & (t <= h)
    control = (t > h) | dead
    w = np.zeros(len(t))
    w[case | dead] = 1 / np.maximum(G(t[case | dead], left=True), 1e-3)
    w[t > h] = 1 / max(float(G([h])[0]), 1e-3)
    return case, control, w


def uno_c(pred, time, status, tau, G=None):
    t, s = np.asarray(time, float), np.asarray(status)
    p = np.asarray(pred, float)
    G = G or ml.censoring_survival(t, s)
    cases = np.flatnonzero((s == "svd") & (t <= tau))
    if not len(cases):
        return np.nan
    gl = np.maximum(G(t, left=True), 1e-3)
    num = den = 0.0
    for i in cases:
        later = (t > t[i]) | ((t == t[i]) & (s == "censored"))
        died = (s == "death") & (t <= t[i])
        w = np.where(later, 1 / gl[i] ** 2, 0.0) + np.where(died, 1 / (gl[i] * gl), 0.0)
        conc = (p[i] > p).astype(float) + 0.5 * (p[i] == p)
        num += (w * conc).sum()
        den += w.sum()
    return float(num / den) if den > 0 else np.nan


def point_metrics(p, time, status, h, G=None):
    G = G or ml.censoring_survival(time, status)
    obs = ml.aalen_johansen(time, status, h)
    brier = ml.cr_brier(p, time, status, h, G)
    null = ml.cr_brier(np.full(len(p), obs), time, status, h, G)
    return dict(auc=ml.cr_auc(p, time, status, h, G), c_index=uno_c(p, time, status, h, G), brier=brier, brier_null=null,
                scaled_brier=1 - brier / null if null > 0 else np.nan, mean_predicted=float(np.mean(p)), observed=obs,
                oe_ratio=obs / float(np.mean(p)) if np.mean(p) > 0 else np.nan)


def performance(preds, meta):
    t, s = _arrays(meta)
    G = ml.censoring_survival(t, s)
    rows = {(name, h): point_metrics(cif[h].to_numpy(), t, s, h, G) for name, cif in preds.items() for h in cif}
    return pd.DataFrame(rows).T.rename_axis(["model", "horizon"])


def bootstrap(preds, meta, n_boot=300, seed=0, metrics=("auc", "c_index", "scaled_brier")):
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
    for cut, name, action in ml.RISK_TIERS:
        m = tiers == name
        rows.append(dict(tier=name, action=action, rows=int(m.sum()), share=m.mean(), valves=meta.patient_id[m].nunique(),
                         valves_with_event=meta.patient_id[m & (s == "svd") & (t <= h)].nunique(),
                         mean_predicted=np.asarray(p)[m].mean() if m.any() else np.nan,
                         observed=ml.aalen_johansen(t[m], s[m], h) if m.any() else np.nan))
    return pd.DataFrame(rows).set_index("tier")


def threshold_metrics(p, meta, h, cut):
    t, s = _arrays(meta)
    G = ml.censoring_survival(t, s)
    case, control, w = ipcw_weights(t, s, h, G)
    pos = np.asarray(p, float) >= cut
    tp, fn = (w * (case & pos)).sum(), (w * (case & ~pos)).sum()
    fp, tn = (w * (control & pos)).sum(), (w * (control & ~pos)).sum()
    div = lambda a, b: a / b if b > 0 else np.nan
    return dict(cutoff=cut, flagged=pos.mean(), sensitivity=div(tp, tp + fn), specificity=div(tn, tn + fp),
                ppv=div(tp, tp + fp), npv=div(tn, tn + fn), accuracy=div(tp + tn, tp + tn + fp + fn),
                accuracy_flag_nobody=div(tn + fp, tp + tn + fp + fn))


def subgroup_table(preds, meta, X, h, groups, min_events=3):
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


def git_commit(root):
    try:
        return subprocess.run(["git", "-C", str(root), "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        return ""


def log_rows(run, bundle, perf, ci, meta, root):
    stamp = datetime.now().isoformat(timespec="seconds")
    events = meta.patient_id[meta.status.eq("svd")].nunique()
    table = perf.join(ci, how="left").reset_index()
    base = dict(timestamp=stamp, commit=git_commit(root), run=run, label=bundle.get("label"), preset=bundle.get("preset"),
                source=bundle.get("source"), selection_enabled=bool(bundle.get("selection", {}).get("enabled", False)),
                split_year=bundle.get("split_year"), seed=bundle.get("seed"), endpoint=bundle.get("labels", {}).get("endpoint"),
                rows=len(meta), valves=meta.patient_id.nunique(), events=events)
    rows = [{**base, **r} for r in table.to_dict("records")]
    return pd.DataFrame(rows).reindex(columns=LOG_COLUMNS)


def append_log(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        old = pd.read_csv(path)
        rows = pd.concat([old, rows], ignore_index=True)
    rows.reindex(columns=list(dict.fromkeys(LOG_COLUMNS + list(rows.columns)))).to_csv(path, index=False)
    return rows


def compare_runs(processed, real_dir, horizon=5):
    rows = []
    for run_dir in sorted(Path(processed, "runs").glob("*")):
        if missing_inputs(run_dir, real_dir):
            continue
        try:
            bundle, models = load_run(run_dir)
            Xr, mr, _ = score_real(bundle, real_dir)
            perf = performance(predict_all(models, Xr, [horizon]), mr)
        except Exception as err:
            rows.append(dict(run=run_dir.name, model="(failed)", note=str(err)[:80]))
            continue
        stamp = datetime.fromtimestamp((run_dir / "models" / "primary.pkl").stat().st_mtime).isoformat(timespec="minutes")
        for (name, h), r in perf.iterrows():
            rows.append(dict(run=run_dir.name, trained=stamp, label=bundle.get("label"),
                             selection_enabled=bool(bundle.get("selection", {}).get("enabled", False)),
                             model=name, auc=r.auc, c_index=r.c_index, scaled_brier=r.scaled_brier, oe_ratio=r.oe_ratio))
    return pd.DataFrame(rows)
