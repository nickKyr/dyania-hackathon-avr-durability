import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.decomposition import PCA
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

F = lambda block, direction, prior, why: dict(block=block, direction=direction, prior=prior, why=why)
FEATURES = {
    "landmark_years": F("time", 1, True, "years since implant at the landmark; SVD hazard rises with valve age"),
    "age_at_implant": F("patient", -1, True, "younger patients degenerate valves faster; the strongest surgical predictor"),
    "male": F("patient", 0, False, "direction conflicting across cohorts"),
    "bsa_m2": F("patient", 0, False, "body size; needed to index EOA"),
    "diabetes": F("patient", 1, True, "dysmetabolic calcification, HR 1.33"),
    "ckd": F("patient", 1, True, "calcium-phosphate disturbance, early SVD"),
    "smoking": F("patient", 1, True, "HR 2.28 to 2.58"),
    "bicuspid": F("patient", 1, False, "native morphology, younger patients"),
    "tavr": F("valve", 0, True, "SAVR vs TAVR is the comparison of interest"),
    "valve_sapien_3": F("valve", 0, False, "valve family"),
    "valve_evolut": F("valve", 0, False, "valve family"),
    "valve_trifecta": F("valve", 0, False, "valve family with known early failures"),
    "valve_perimount": F("valve", 0, False, "valve family"),
    "valve_epic": F("valve", 0, False, "valve family (porcine)"),
    "valve_magna": F("valve", 0, False, "valve family"),
    "valve_inspiris": F("valve", 0, False, "valve family"),
    "valve_size_mm": F("valve", -1, True, "small valves fail earlier, HR 0.82 per mm"),
    "eoa_index_implant": F("valve", -1, False, "indexed EOA at implant"),
    "ppm_grade": F("valve", 1, True, "patient-prosthesis mismatch, HR 1.79 to 1.95"),
    "ref_mg": F("reference echo", 1, True, "early residual gradient, sHR 1.05 per mmHg"),
    "ref_peak": F("reference echo", 1, False, "redundant with the mean gradient"),
    "ref_dvi": F("reference echo", -1, False, "early obstruction index"),
    "ref_eoa": F("reference echo", -1, False, "early valve area"),
    "ref_ar": F("reference echo", 1, False, "residual regurgitation, HR 1.87"),
    "ref_lvef": F("reference echo", 0, False, "ventricular function"),
    "ref_missing": F("reference echo", 0, False, "no reference echo: change-based criteria unusable"),
    "last_mg": F("latest echo", 1, False, "current gradient"),
    "last_peak": F("latest echo", 1, False, "redundant with the mean gradient"),
    "last_dvi": F("latest echo", -1, False, "current obstruction index"),
    "last_eoa": F("latest echo", -1, False, "current valve area"),
    "last_ar": F("latest echo", 1, False, "current regurgitation"),
    "last_lvef": F("latest echo", 0, False, "low flow hides stenosis"),
    "delta_mg": F("trajectory", 1, True, "gradient change from reference, the VARC-3 criterion itself"),
    "delta_dvi": F("trajectory", -1, False, "VARC-3 confirmation criterion"),
    "delta_eoa": F("trajectory", -1, False, "VARC-3 confirmation criterion"),
    "delta_ar": F("trajectory", 1, False, "regurgitant pathway"),
    "max_mg": F("trajectory", 1, False, "highest gradient so far"),
    "mg_slope": F("trajectory", 1, False, "speed of deterioration over the last two echoes"),
    "n_echo": F("surveillance", 0, False, "number of echoes so far"),
    "n_echo_recent": F("surveillance", 0, False, "dense recent surveillance signals clinical concern"),
    "years_since_last_echo": F("surveillance", 0, False, "how stale the echo features are"),
}
BLOCKS = list(dict.fromkeys(v["block"] for v in FEATURES.values()))
OUTCOME_CLASSES = {1.0: "SVD", 0.0: "no SVD", 2.0: "died first"}

SELECTION_CONFIG = dict(
    enabled=False,
    drop_missing=True, max_missing=0.6,
    drop_constant=True, max_mode_share=0.98,
    drop_correlated=True, max_corr=0.95,
    stability=True, n_boot=40, l1_c=0.05, min_freq=0.6,
    keep_priors=True,
    horizon=5,
    seed=0,
)
RISK_TIERS = [(0.05, "low", "guideline schedule"), (0.15, "moderate", "echo every 2 years"), (1.01, "high", "echo every year")]


def feature_matrix(landmark):
    cols = [c for c in FEATURES if c in landmark]
    meta_cols = ["patient_id", "landmark_id", "landmark_years", "implant_year", "time_to_end", "status", "source", "time_resolution"]
    meta = landmark[meta_cols + [c for c in landmark if c.startswith(("svd_", "death_")) and c.endswith("y")]].copy()
    return landmark[cols].astype(float), meta


def outcome_class(meta, h):
    y = meta[f"svd_{h}y"].copy()
    y[meta[f"death_{h}y"] == 1] = 2.0
    return y.map(OUTCOME_CLASSES)


def summarize(X, meta, h):
    per_patient = meta.groupby("patient_id").size()
    return pd.Series({
        "landmark rows": len(X),
        "patients": meta.patient_id.nunique(),
        "features": X.shape[1],
        "rows with any missing feature": int(X.isna().any(axis=1).sum()),
        "rows per patient (median / max)": f"{per_patient.median():.0f} / {per_patient.max()}",
        f"rows with SVD within {h} years": int(meta[f"svd_{h}y"].eq(1).sum()),
        f"rows dying first within {h} years": int(meta[f"death_{h}y"].eq(1).sum()),
        f"rows censored before {h} years": int(meta[f"svd_{h}y"].isna().sum()),
        "source": ", ".join(meta.source.dropna().unique()),
        "time resolution": ", ".join(meta.time_resolution.dropna().unique()),
    }, name="value").to_frame()


def feature_profile(X, meta, h):
    y = outcome_class(meta, h)
    known = y.notna()
    z = (X - X.mean()) / X.std(ddof=0).replace(0, np.nan)
    means = z[known].groupby(y[known]).mean().T
    lab = meta[f"svd_{h}y"]
    ok = lab.notna()
    auc = {}
    for c in X:
        m = ok & X[c].notna()
        if m.sum() > 20 and lab[m].nunique() == 2 and X.loc[m, c].nunique() > 1:
            auc[c] = roc_auc_score(lab[m], X.loc[m, c])
    means["univariable AUC"] = pd.Series(auc)
    means["missing"] = X.isna().mean()
    means["block"] = [FEATURES[c]["block"] for c in means.index]
    return means


def pca_view(X, seed=0):
    usable = X.loc[:, X.notna().any()]
    Z = make_pipeline(SimpleImputer(strategy="median"), StandardScaler()).fit_transform(usable)
    pca = PCA(n_components=min(10, usable.shape[1]), random_state=seed).fit(Z)
    return pca.transform(Z)[:, :2], pca.explained_variance_ratio_


def expand_discrete(X, meta, horizon):
    t = meta.time_to_end.to_numpy(float)
    status = meta.status.to_numpy()
    event = status != "censored"
    n_int = np.where(event & (t <= horizon), np.ceil(t), np.floor(np.minimum(t, horizon))).astype(int)
    n_int = np.maximum(n_int, 0)
    rep = np.repeat(np.arange(len(X)), n_int)
    k = np.concatenate([np.arange(1, m + 1) for m in n_int]) if n_int.sum() else np.array([], int)
    last = event[rep] & (k == np.ceil(t[rep])) & (t[rep] <= horizon)
    target = np.where(last & (status[rep] == "svd"), 1, np.where(last & (status[rep] == "death"), 2, 0))
    Xe = X.iloc[rep].reset_index(drop=True).assign(interval=k)
    return Xe, target, meta.patient_id.to_numpy()[rep]


def select_features(X, meta, config=SELECTION_CONFIG):
    c = config
    rep = pd.DataFrame({"block": [FEATURES[f]["block"] for f in X], "prior": [FEATURES[f]["prior"] for f in X]}, index=X.columns)
    rep["missing"] = X.isna().mean()
    rep["mode_share"] = X.apply(lambda s: s.value_counts(normalize=True).iloc[0] if s.notna().any() else 1.0)
    rep["flag"] = ""
    if c["drop_missing"]:
        rep.loc[rep.missing > c["max_missing"], "flag"] = "too much missing"
    if c["drop_constant"]:
        rep.loc[(rep.flag == "") & (rep.mode_share > c["max_mode_share"]), "flag"] = "almost constant"
    if c["drop_correlated"]:
        keep = rep.index[rep.flag == ""].tolist()
        corr = X[keep].corr(method="spearman").abs()
        for i, a in enumerate(keep):
            if rep.loc[a, "flag"]:
                continue
            for b in keep[i + 1:]:
                if not rep.loc[b, "flag"] and corr.loc[a, b] > c["max_corr"]:
                    loser, winner = (a, b) if rep.loc[b, "prior"] and not rep.loc[a, "prior"] else (b, a)
                    rep.loc[loser, "flag"] = f"correlated with {winner} (rho {corr.loc[a, b]:.2f})"
                    if loser == a:
                        break
    rep["stability"] = np.nan
    if c["stability"]:
        keep = rep.index[rep.flag == ""].tolist()
        Xe, target, groups = expand_discrete(X[keep], meta, c["horizon"])
        y = (target == 1).astype(int)
        rng = np.random.default_rng(c["seed"])
        patients = np.unique(groups)
        counts, fits = pd.Series(0.0, index=keep), 0
        model = make_pipeline(SimpleImputer(strategy="median", keep_empty_features=True), StandardScaler(),
                              LogisticRegression(l1_ratio=1.0, C=c["l1_c"], solver="liblinear", max_iter=500))
        for _ in range(c["n_boot"]):
            m = np.isin(groups, rng.choice(patients, len(patients) // 2, replace=False))
            if y[m].sum() < 5:
                continue
            fit = clone(model).fit(Xe.loc[m, keep + ["interval"]], y[m])
            counts += (np.abs(fit[-1].coef_[0][: len(keep)]) > 1e-8).astype(float)
            fits += 1
        rep.loc[keep, "stability"] = counts / max(fits, 1)
        rep.loc[(rep.flag == "") & (rep.stability < c["min_freq"]), "flag"] = "unstable in bootstrap"
    hard = rep.flag.str.startswith(("too much", "almost"))
    rep["would_keep"] = (rep.flag == "") | (c["keep_priors"] & rep.prior & ~hard)
    rep["used"] = rep.would_keep if c["enabled"] else True
    kept_label = np.where(rep.flag == "", "kept", "kept as clinical prior (" + rep.flag + ")")
    if c["enabled"]:
        rep["decision"] = np.where(rep.would_keep, kept_label, "dropped: " + rep.flag)
    else:
        rep["decision"] = np.where(rep.would_keep, "used; selection would keep", "used; selection would drop: " + rep.flag)
    return rep.drop(columns="mode_share")


def _logit(C=1.0):
    return make_pipeline(SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True), StandardScaler(), LogisticRegression(C=C, max_iter=3000))


def _gbm(monotone, **params):
    base = dict(learning_rate=0.05, max_iter=1000, max_leaf_nodes=15, min_samples_leaf=40, l2_regularization=1.0,
                early_stopping=True, validation_fraction=0.15, n_iter_no_change=25, random_state=0)
    base.update(params)
    return HistGradientBoostingClassifier(monotonic_cst=monotone, **base)


class DiscreteTimeCompetingRisks:
    def __init__(self, features, kind="gbm", horizon=8, monotone=True, **params):
        self.features, self.kind, self.horizon, self.monotone, self.params = list(features), kind, horizon, monotone, params

    def _estimator(self, cause):
        if self.kind == "logit":
            return _logit(**self.params)
        mono = [FEATURES.get(f, {}).get("direction", 0) if (cause == "svd" and self.monotone) else 0 for f in self.features] + [0]
        return _gbm(mono, **self.params)

    def _design(self, Xe):
        D = Xe[self.features + ["interval"]].copy()
        if self.kind == "logit":
            for k in range(2, self.horizon + 1):
                D[f"interval_{k}"] = (D.interval == k).astype(float)
            D = D.drop(columns="interval")
        return D

    def fit(self, X, meta):
        self.requested_ = list(self.features)
        self.features = [f for f in self.requested_ if X[f].nunique() > 1]
        self.dropped_ = [f for f in self.requested_ if f not in self.features]
        Xe, target, _ = expand_discrete(X[self.features], meta, self.horizon)
        D = self._design(Xe)
        self.svd_ = self._estimator("svd").fit(D, (target == 1).astype(int))
        self.death_ = self._estimator("death").fit(D, (target == 2).astype(int)) if (target == 2).sum() >= 5 else None
        self.n_rows_, self.n_events_ = len(D), dict(svd=int((target == 1).sum()), death=int((target == 2).sum()))
        return self

    def hazards(self, X):
        n = len(X)
        hs, hd = np.zeros((n, self.horizon)), np.zeros((n, self.horizon))
        for k in range(1, self.horizon + 1):
            D = self._design(X[self.features].reset_index(drop=True).assign(interval=k))
            hs[:, k - 1] = self.svd_.predict_proba(D)[:, 1]
            if self.death_ is not None:
                hd[:, k - 1] = self.death_.predict_proba(D)[:, 1]
        return hs, hd

    def predict_cif(self, X):
        hs, hd = self.hazards(X)
        surv = np.ones(len(X))
        cif_s, cif_d = np.zeros_like(hs), np.zeros_like(hd)
        rs, rd = np.zeros(len(X)), np.zeros(len(X))
        for k in range(self.horizon):
            rs, rd = rs + surv * hs[:, k], rd + surv * hd[:, k]
            cif_s[:, k], cif_d[:, k] = rs, rd
            surv = surv * np.clip(1 - hs[:, k] - hd[:, k], 0, 1)
        cols = [f"svd_{k}y" for k in range(1, self.horizon + 1)] + [f"death_{k}y" for k in range(1, self.horizon + 1)]
        return pd.DataFrame(np.hstack([cif_s, cif_d]), columns=cols, index=X.index)


def censoring_survival(time, status):
    t = np.asarray(time, float)
    cens = np.asarray(status) == "censored"
    grid = np.unique(t[cens])
    surv, s = [], 1.0
    for u in grid:
        at_risk = (t >= u).sum()
        s *= 1 - ((t == u) & cens).sum() / at_risk if at_risk else 1
        surv.append(s)
    surv = np.array(surv)

    def G(x, left=False):
        x = np.atleast_1d(np.asarray(x, float))
        if not len(surv):
            return np.ones(len(x))
        idx = np.searchsorted(grid, x, side="left" if left else "right") - 1
        return np.where(idx >= 0, surv[np.clip(idx, 0, None)], 1.0)
    return G


def _ipcw(time, status, h, G):
    t, s = np.asarray(time, float), np.asarray(status)
    case = (s == "svd") & (t <= h)
    dead = (s == "death") & (t <= h)
    control = (t > h) | dead
    w = np.zeros(len(t))
    w[case | dead] = 1 / np.maximum(G(t[case | dead], left=True), 1e-3)
    w[t > h] = 1 / max(float(G([h])[0]), 1e-3)
    return case, control, w


def cr_auc(pred, time, status, h, G=None):
    G = G or censoring_survival(time, status)
    case, control, w = _ipcw(time, status, h, G)
    p = np.asarray(pred, float)
    pc, wc = p[control], w[control]
    o = np.argsort(pc)
    pc, wc = pc[o], wc[o]
    cum = np.concatenate([[0], np.cumsum(wc)])
    lo, hi = np.searchsorted(pc, p[case], "left"), np.searchsorted(pc, p[case], "right")
    denom = w[case].sum() * wc.sum()
    return float((w[case] * (cum[lo] + 0.5 * (cum[hi] - cum[lo]))).sum() / denom) if denom > 0 else np.nan


def cr_brier(pred, time, status, h, G=None):
    G = G or censoring_survival(time, status)
    case, control, w = _ipcw(time, status, h, G)
    use = case | control
    return float((w[use] * (case[use].astype(float) - np.asarray(pred, float)[use]) ** 2).sum() / len(case))


def aalen_johansen(time, status, h):
    t, s = np.asarray(time, float), np.asarray(status)
    surv, cif = 1.0, 0.0
    for u in np.unique(t[(t <= h) & (s != "censored")]):
        n = (t >= u).sum()
        ds, dd = ((t == u) & (s == "svd")).sum(), ((t == u) & (s == "death")).sum()
        cif += surv * ds / n
        surv *= 1 - (ds + dd) / n
    return cif


def risk_tier(p):
    for cut, name, action in RISK_TIERS:
        if p < cut:
            return name, action
    return RISK_TIERS[-1][1], RISK_TIERS[-1][2]


class CalendarSchedule:
    def __init__(self, horizon=8, threshold_years=5):
        self.horizon, self.threshold_years = horizon, threshold_years

    def fit(self, X, meta):
        grp = (X.landmark_years >= self.threshold_years).to_numpy()
        self.cif_ = {g: {h: aalen_johansen(meta.time_to_end[grp == g], meta.status[grp == g], h) for h in range(1, self.horizon + 1)} for g in (False, True)}
        return self

    def predict_cif(self, X):
        grp = (X.landmark_years >= self.threshold_years).to_numpy()
        return pd.DataFrame({f"svd_{h}y": np.where(grp, self.cif_[True][h], self.cif_[False][h]) for h in range(1, self.horizon + 1)}, index=X.index)


class CoxRiskFactors:
    def __init__(self, features, horizon=8, penalizer=0.05):
        self.features, self.horizon, self.penalizer = list(features), horizon, penalizer

    def fit(self, X, meta):
        from lifelines import CoxPHFitter
        usable = X[self.features]
        self.used_ = [f for f in self.features if usable[f].nunique() > 1]
        self.median_ = usable[self.used_].median()
        d = usable[self.used_].fillna(self.median_).assign(T=meta.time_to_end.to_numpy(), E=meta.status.eq("svd").astype(int).to_numpy(), cluster=meta.patient_id.to_numpy())
        self.model_ = CoxPHFitter(penalizer=self.penalizer).fit(d, duration_col="T", event_col="E", cluster_col="cluster")
        return self

    def predict_cif(self, X):
        sf = self.model_.predict_survival_function(X[self.used_].fillna(self.median_), times=list(range(1, self.horizon + 1)))
        return pd.DataFrame((1 - sf.T).to_numpy(), columns=[f"svd_{h}y" for h in range(1, self.horizon + 1)], index=X.index)
