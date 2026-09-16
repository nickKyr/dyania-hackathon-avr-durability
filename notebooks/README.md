# Notebooks

The analysis, in order. Notebooks 01 and 02 read `data/raw_tables/`, so build those first with the scripts in `../scripts/` (see its README); notebooks 03 to 05 read what 02 writes to `data/processed/`.

| Notebook | Purpose | Status |
|---|---|---|
| `01_raw_data_overview.ipynb` | What the three extracts contain: coverage, time span, completeness, duplicates, content | done |
| `02_preprocessing.ipynb` | Cohort, deduplication, lab mapping, one record per valve, echo timeline, events, follow-up, medications, covariates, landmark dataset, sensitivity | done (logic in `pipeline/prep.py`) |
| `03_data_preparation.ipynb` | Labels (SVD, competing death, censoring), landmark table, feature catalogue, feature exploration (distributions by outcome, class profile, correlation, PCA), fixed clinical feature list (automatic selection switchable), temporal split, person-period rows | done (logic in `pipeline/landmarks.py`, `pipeline/ml.py`) |
| `04_model_training.ipynb` | Comparators (calendar schedule, valve age only, Cox on risk factors), discrete-time competing-risks regression baseline, gradient-boosted primary model with grouped CV tuning, learning curve, first test check, SHAP, one worked prediction | done (logic in `pipeline/ml.py`) |
| `05_results.ipynb` | Every trained model scored on the real extract: competing-risk AUC with bootstrap intervals, Uno-style C-index, scaled Brier score, calibration in the large and by risk group, decision curve, risk tiers, subgroups, and the run ledger in `../results/` | done (logic in `pipeline/evaluation.py`, `pipeline/ledger.py`) |
| outside the notebooks | The degradation ladder, the repeated-cohort model comparison, the sample size and the synthetic decision curve, by `../scripts/05` to `08` | done |

Shared code lives in `pipeline/`: `viz.py` (plot style), `prep.py` (preprocessing), `landmarks.py` (labels, landmarks, data conversion), `matching.py` (reshaping the synthetic cohort to the extract), `ml.py` (features, selection, models, metrics), `evaluation.py` (scoring on the extract) and `ledger.py` (the run ledger). Real and synthetic data take the same route: the real extract through `02_preprocessing.ipynb`, the team synthetic cohort through `pipeline.landmarks.synthetic_to_preprocessing`, then both through `pipeline.landmarks.from_preprocessing` into notebooks 03 to 05. Notebook 03 trains, by default, on the synthetic cohort reshaped to look like the real extract (`TRAIN_LIKE_REAL`); settings are in its first cell. `pipeline/prep.py` holds the preprocessing `CONFIG`; processed tables are written to `data/processed/` (gitignored). Figures are written to `figures/`, prefixed with the notebook number.

## Packages

`synthetic/` is the team's literature-calibrated synthetic cohort and degradation ladder (tests in `synthetic/tests`, run with `uv run python -m pytest synthetic/tests -q`). Notebook 03 converts it into the format `02_preprocessing.ipynb` writes, so real and synthetic data follow the same route from there on. `pipeline/` holds our shared code: label construction, landmark features, the conversion between the two data shapes and the matching rules, with its own tests in `pipeline/tests` (`uv run python -m pytest pipeline/tests -q`).

## Running

```bash
uv sync
uv run jupyter lab
```

To build the synthetic cohort without opening a notebook, from this directory:

```bash
uv run python -m synthetic --preset ideal --out ../data/synthetic/ideal
```

`--ladder` writes every rung instead of one, `--n-patients` sets the cohort size and
`--no-calibration` skips the calibration table. Full options and the presets are in
[`../data/synthetic/README.md`](../data/synthetic/README.md).

Only aggregate outputs (counts, shares, distributions) may be committed. Clear any cell that shows patient rows or note text.
