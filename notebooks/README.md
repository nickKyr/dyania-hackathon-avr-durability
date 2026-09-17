# Notebooks — Proof-of-Concept Implementation

The proof of concept runs in five notebooks, from the raw hospital extracts to results on the real
data. The shared code is in `pipeline/` and the synthetic cohort generator in `synthetic/`. Every
output shown in these notebooks is an aggregate: no note text, identifier or patient row.

## Notebooks, in order

| Notebook | What it does | Main outputs |
|---|---|---|
| [`01_raw_data_overview.ipynb`](01_raw_data_overview.ipynb) | What the three supplied extracts contain: patient coverage, time span, duplicates, column completeness, lab, medication and note content | figures `01_*` |
| [`02_preprocessing.ipynb`](02_preprocessing.ipynb) | Turns the raw tables into one record per valve, an echocardiogram timeline, events labelled with the VARC-3 rules, follow-up and covariates | the prepared real tables in `data/processed/` (gitignored); figures `02_*` |
| [`03_data_preparation.ipynb`](03_data_preparation.ipynb) | Loads the synthetic cohort (full-quality by default; reshaped to look like the real extract with `AVR_LIKE_REAL=1`), builds the outcomes, the landmark rows and the features, explores them, applies the feature list for that data and splits by implant year | `data/processed/runs/<run>/model_input.pkl`; figures `03_*` |
| [`04_model_training.ipynb`](04_model_training.ipynb) | Trains the comparators (calendar schedule, valve age only, Cox), the regression baseline and the gradient-boosted primary model, tunes it, adds recalibrated versions, checks them on the synthetic test set (overall and by visit, including the first postoperative visit), and explains the primary model with SHAP | trained models in `data/processed/runs/<run>/models/`; figures `04_*` |
| [`05_results.ipynb`](05_results.ipynb) | Scores the models of one run (default `final`, trained on reshaped data) on the real extract: competing-risk AUC with bootstrap intervals, scaled Brier score, calibration, decision curve, risk tiers, subgroups, and a written interpretation. Records the run in the ledger | [`../results/LEDGER.md`](../results/LEDGER.md); figures `05_*` |

The step-by-step method, the models and the results are described in
[`../model/approach.md`](../model/approach.md); the data and preprocessing in
[`../data/data_plan.md`](../data/data_plan.md).

## Shared code

| Package | Module | Contents |
|---|---|---|
| `pipeline/` | `prep.py` | preprocessing rules and settings (`CONFIG`) for notebook 02 |
| | `landmarks.py` | outcomes, landmark rows and features; the conversion that puts real and synthetic data into the same tables |
| | `matching.py` | reshaping the synthetic cohort to look like the real extract, and the check of how similar they are |
| | `ml.py` | the feature catalogue and fixed feature list, feature selection, the discrete-time competing-risks models, metrics |
| | `evaluation.py` | scoring on the real extract: metrics, bootstrap, calibration, decision curve, tiers, subgroups |
| | `ledger.py` | the run ledger in `results/` |
| | `viz.py` | plot style and figure saving |
| | `tests/` | 15 tests on labels, features, the data conversion and matching |
| `synthetic/` | | the literature-calibrated cohort generator, its calibration, the degradation ladder and 54 tests; see [`../data/synthetic/README.md`](../data/synthetic/README.md) |

Real and synthetic data take the same route. The real extract comes out of notebook 02. The
synthetic cohort is converted by `landmarks.synthetic_to_preprocessing` into the same tables. From
`landmarks.from_preprocessing` on, both go through identical code.

## Running

From the repository root, once:

```bash
uv sync
```

Then run the notebooks in order (01 to 05), in Jupyter:

```bash
uv run jupyter lab
```

or from the command line, from this folder:

```bash
for n in 01_raw_data_overview 02_preprocessing 03_data_preparation 04_model_training 05_results; do
  uv run jupyter nbconvert --to notebook --execute --inplace $n.ipynb
done
```

- **Private data.** Notebooks 01, 02 and 05 need it. Copy the three supplied extracts into `data/`
  and build the raw tables first (`scripts/01_extract_rules.py`, then
  `scripts/03_build_raw_tables.py`; see [`../scripts/README.md`](../scripts/README.md)).
- **Synthetic data only.** Notebooks 03 and 04 run on the full-quality synthetic cohort alone by
  default: this is the main setup. With `AVR_LIKE_REAL=1` they reshape the cohort to look like the
  real extract, and then also need the prepared real tables.
- **Which run notebook 05 scores.** Notebook 05 scores the run named by `AVR_RUN`. By default this is
  `final`, trained on reshaped data; `AVR_RUN=main` scores the main-setup models instead.

**Settings.** The first cell of each notebook holds its settings: data source, preset, seed,
labels, matching and feature selection in 03; the tuning grid in 04; horizons and bootstrap size
in 05. These environment variables override the defaults:

| Variable | Effect |
|---|---|
| `AVR_RUN` | name of the run folder under `data/processed/runs/` (default `main` in 03 and 04, `final` in 05) |
| `AVR_LIKE_REAL=1` | train on the synthetic cohort reshaped to look like the real extract, with the short feature list |
| `AVR_SEED` | seed of the synthetic cohort |
| `AVR_MATCH=v1` | the earlier, simpler reshaping of the synthetic cohort |
| `AVR_NOTE` | a short description stored with the run in the ledger |
| `AVR_WRITE_LOG=0` | evaluate in notebook 05 without adding a ledger entry |
| `AVR_REAL_DIR` | where the prepared real tables are (default `data/processed`) |
| `AVR_FIG_DIR` | where figures are written (default `figures/`) |

To build the synthetic cohort without a notebook, from this folder:

```bash
uv run python -m synthetic --preset ideal --out ../data/synthetic/ideal
```

`--ladder` writes every rung, `--n-patients` sets the cohort size, and `--no-calibration` skips the
calibration table.

## Tests

```bash
uv run pytest -q                              # all 69 tests, from the repository root
uv run python -m pytest pipeline/tests -q     # 15 tests, from this folder
uv run python -m pytest synthetic/tests -q    # 54 tests, from this folder
```

## Environment

Python 3.12 or later, managed with [uv](https://docs.astral.sh/uv/). Dependencies are pinned in
`../pyproject.toml` and `../uv.lock`:
- pandas, numpy and pyarrow
- scikit-learn: the gradient-boosted and logistic models
- lifelines: the Cox model
- shap
- matplotlib
- scipy
- openpyxl
- jupyter, nbconvert and nbformat

Development tools are pytest and ruff.

Figures are written to `figures/`, prefixed with the notebook number. Only aggregate outputs may be
committed: clear any cell that shows patient rows or note text before committing.
