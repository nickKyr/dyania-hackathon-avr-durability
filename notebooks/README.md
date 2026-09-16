# Notebooks

The analysis, in order. Each notebook reads `data/raw_tables/`, so build those first with the scripts in `../scripts/` (see its README).

| Notebook | Purpose | Status |
|---|---|---|
| `01_raw_data_overview.ipynb` | What the three extracts contain: coverage, time span, completeness, duplicates, content | done |
| `02_preprocessing.ipynb` | Deduplication, lab mapping, one implant per patient, echo timeline, event adjudication, covariates, landmark dataset | skeleton |
| `03_model_training.ipynb` | Cox / Fine-Gray baseline and competing-risks boosted model | planned |
| `04_evaluation.ipynb` | Discrimination, calibration, decision curve, SHAP | planned |

`viz.py` holds the shared plot style. Figures are written to `figures/`, prefixed with the notebook number.

## Packages

Two importable packages sit alongside the notebooks. Neither is a notebook, and both are
covered by tests in their own `tests/` directory (`python -m pytest synthetic/tests cohort/tests -q`).

| Package | Purpose |
|---|---|
| `synthetic/` | The literature-calibrated synthetic cohort and the degradation ladder. Needs no data: every rung is reproducible on a machine with no access to the extract |
| `cohort/` | Reads the consolidated extract built by `../scripts/`, and maps it into the same schema as the synthetic cohort so the two are comparable |

```bash
python -m synthetic --preset ideal      # cohort plus its calibration table
python -m cohort > ../data/synthetic/results.md   # the committed results document
```

`synthetic/schema.py` is the contract both sides satisfy; see
[`../data/synthetic/README.md`](../data/synthetic/README.md) for the tables and
[`../data/data_plan.md`](../data/data_plan.md) section 5 for the method.

## Running

```bash
uv sync
uv run jupyter lab
```

Only aggregate outputs (counts, shares, distributions) may be committed. Clear any cell that shows patient rows or note text.
