# Notebooks

The analysis, in order. Each notebook reads `data/raw_tables/`, so build those first with the scripts in `../scripts/` (see its README).

| Notebook | Purpose | Status |
|---|---|---|
| `01_raw_data_overview.ipynb` | What the three extracts contain: coverage, time span, completeness, duplicates, content | done |
| `02_preprocessing.ipynb` | Deduplication, lab mapping, one implant per patient, echo timeline, event adjudication, covariates, landmark dataset | skeleton |
| `03_model_training.ipynb` | Cox / Fine-Gray baseline and competing-risks boosted model | planned |
| `04_evaluation.ipynb` | Discrimination, calibration, decision curve, SHAP | planned |

`viz.py` holds the shared plot style. Figures are written to `figures/`, prefixed with the notebook number.

## Running

```bash
uv sync
uv run jupyter lab
```

Only aggregate outputs (counts, shares, distributions) may be committed. Clear any cell that shows patient rows or note text.
