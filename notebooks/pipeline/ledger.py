import hashlib
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
LEDGER_DIR = ROOT / "results"
LEDGER_FILE = LEDGER_DIR / "runs.jsonl"
LEDGER_MD = LEDGER_DIR / "LEDGER.md"
CONFIG_NAME = "run_config.json"
HEADLINE_MODELS = ["regression baseline", "gradient boosting", "Cox, risk factors", "valve age only"]


def clean(value):
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [clean(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return None if not np.isfinite(value) else round(float(value), 6)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, Path):
        return str(value)
    if value is None or isinstance(value, (str, int, bool)):
        return value
    return str(value)


def read_run_config(run_dir):
    path = Path(run_dir) / CONFIG_NAME
    return json.loads(path.read_text()) if path.exists() else {}


def update_run_config(run_dir, section, values):
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    config = read_run_config(run_dir)
    config[section] = clean(values)
    config["updated"] = datetime.now().isoformat(timespec="seconds")
    (run_dir / CONFIG_NAME).write_text(json.dumps(config, indent=2, sort_keys=True))
    return config


def git_state():
    def run(*args):
        try:
            return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, timeout=5).stdout.strip()
        except Exception:
            return ""
    return dict(commit=run("rev-parse", "--short", "HEAD"), branch=run("rev-parse", "--abbrev-ref", "HEAD"),
                uncommitted_changes=bool(run("status", "--porcelain", "--untracked-files=no")))


def config_hash(config):
    stable = {k: v for k, v in config.items() if k != "updated"}
    return hashlib.sha1(json.dumps(stable, sort_keys=True).encode()).hexdigest()[:10]


def record(run, run_dir, perf, ci, meta, note=None):
    config = read_run_config(run_dir)
    table = perf.join(ci, how="left")
    metrics = {}
    for (model, h), r in table.iterrows():
        metrics.setdefault(model, {})[str(h)] = clean({k: r[k] for k in r.index})
    horizons = sorted({h for _, h in table.index})
    stamp = datetime.now().isoformat(timespec="seconds")
    entry = dict(
        id=f"{stamp}_{run}",
        timestamp=stamp,
        run=run,
        note=note if note is not None else os.environ.get("AVR_NOTE", ""),
        git=git_state(),
        config_hash=config_hash(config),
        config=config,
        real_extract=clean(dict(
            rows=len(meta), valves=meta.patient_id.nunique(),
            valves_with_event=meta.patient_id[meta.status.eq("svd")].nunique(),
            deaths=int(meta.status.eq("death").sum()),
            observed={str(h): table.xs(h, level="horizon")["observed"].iloc[0] for h in horizons},
        )),
        metrics=metrics,
    )
    LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    with LEDGER_FILE.open("a") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")
    write_markdown()
    return entry


def entries():
    if not LEDGER_FILE.exists():
        return []
    return [json.loads(line) for line in LEDGER_FILE.read_text().splitlines() if line.strip()]


def table(horizon=5):
    rows = []
    for e in entries():
        c = e.get("config", {})
        data, match, sel, train = c.get("data", {}), c.get("matching", {}), c.get("selection", {}), c.get("training", {})
        base = dict(
            time=e["timestamp"][:16].replace("T", " "), run=e["run"], commit=e["git"].get("commit", ""),
            dirty=e["git"].get("uncommitted_changes", False), config=e.get("config_hash", ""), note=e.get("note", ""),
            patients=data.get("n_patients"), like_real=data.get("train_like_real"),
            follow_up=match.get("follow_up_window") if data.get("train_like_real") else "",
            selection=sel.get("enabled"), dropped_blocks=",".join(sel.get("drop_blocks", []) or []),
            n_features=len(data.get("features_used", []) or []), train_events=data.get("train_events"),
            tuned=train.get("best_params"), real_events=e["real_extract"].get("valves_with_event"),
            observed=e["real_extract"].get("observed", {}).get(str(horizon)),
        )
        for model, by_h in e["metrics"].items():
            m = by_h.get(str(horizon), {})
            rows.append({**base, "model": model, "auc": m.get("auc"), "auc_lo": m.get("auc_lo"), "auc_hi": m.get("auc_hi"),
                         "c_index": m.get("c_index"), "scaled_brier": m.get("scaled_brier"), "mean_predicted": m.get("mean_predicted")})
    return pd.DataFrame(rows)


def _fmt(v, pct=False, digits=2):
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return ""
    return f"{v:.1%}" if pct else f"{v:.{digits}f}"


def write_markdown(horizon=5):
    t = table(horizon)
    lines = [
        "# Run ledger",
        "",
        f"One line per evaluation of a trained run on the real extract, written by `notebooks/05_results.ipynb` (`notebooks/pipeline/ledger.py`). "
        f"Metrics are at {horizon} years: competing-risk AUC with its 95% bootstrap interval, and mean predicted risk against the observed (Aalen-Johansen) risk. "
        "All training data are synthetic; the real extract is only scored. Full settings and every metric for every horizon are in `runs.jsonl`.",
        "",
    ]
    if t.empty:
        LEDGER_MD.write_text("\n".join(lines + ["No runs recorded yet.", ""]))
        return
    head = ["time", "run", "commit", "config", "note", "training data", "features", "real events", "observed"]
    head += [f"{m} AUC" for m in HEADLINE_MODELS] + [f"{m} predicted" for m in HEADLINE_MODELS[:2]]
    lines += ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for (time, run), g in t.groupby(["time", "run"], sort=False):
        r0 = g.iloc[0]
        by = g.set_index("model")
        training = f"{r0.patients or ''} patients" + (f", like real ({r0.follow_up})" if r0.like_real else ", ideal")
        feats = f"{r0.n_features}" + (" selected" if r0.selection else " all") + (f", minus {r0.dropped_blocks}" if r0.dropped_blocks else "")
        commit = f"{r0.commit}{'+' if r0.dirty else ''}"
        cells = [time, run, commit, r0.config, r0.note or "", training, feats, str(r0.real_events), _fmt(r0.observed, pct=True)]
        for m in HEADLINE_MODELS:
            cells.append(f"{_fmt(by.loc[m, 'auc'])} ({_fmt(by.loc[m, 'auc_lo'])}-{_fmt(by.loc[m, 'auc_hi'])})" if m in by.index else "")
        for m in HEADLINE_MODELS[:2]:
            cells.append(_fmt(by.loc[m, "mean_predicted"], pct=True) if m in by.index else "")
        lines.append("| " + " | ".join(str(c) for c in cells) + " |")
    lines += ["", "A `+` after the commit means the run used uncommitted code.", ""]
    LEDGER_MD.write_text("\n".join(lines))
