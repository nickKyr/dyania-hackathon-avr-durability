# Synthetic Cohort

**Nothing in this directory is a patient.** Every row of every table carries
`source = "simulated"`. The cohort is produced by `notebooks/synthetic/`, is a deterministic
function of its seed, and is regenerated rather than stored: only the 60-patient sample in
[`sample/`](sample) is committed, so that a reader can inspect the schema without running code.

Full rationale, calibration results and limitations are in
[`../data_plan.md`](../data_plan.md), section 5.

## Generating it

From the `notebooks/` directory:

```bash
python -m synthetic --preset ideal --out ../data/synthetic/ideal
```

```bash
python -m synthetic --ladder --out ../data/synthetic
```

```bash
python -m synthetic --preset ideal --sample 60 --out ../data/synthetic/sample
```

The first prints the calibration table against the published anchors. Generated cohorts are
ignored by git; the committed sample is the single exception, declared in `.gitignore`.

## Using it

```python
from synthetic import generate

tables = generate(preset="ideal", seed=20260917, n_patients=1800)
patients, echos, events, followup = (tables[k] for k in ("patients", "echos", "events", "followup"))
```

Every rung of the degradation ladder is reached the same way, changing only `preset`:

```python
from synthetic import PRESETS

ladder = {name: generate(preset=name) for name in PRESETS}
```

## The tables

| table | grain | key |
|---|---|---|
| `patients` | one row per implanted patient | `patient_id` |
| `echos` | one row per echocardiographic examination | `echo_id` |
| `events` | one row per adjudicated event | `patient_id`, `event_type` |
| `followup` | one row per patient, summarising observation time | `patient_id` |

Times outside `patients` are `days_from_implant`, so the implant is always the time origin.
The full field documentation is generated from the schema itself, which keeps the two from
drifting apart:

```python
from synthetic import describe, TABLE_NAMES

print("\n\n".join(describe(name) for name in TABLE_NAMES))
```

## The two governance columns

Every table carries them, and no consumer should drop them.

| column | values | meaning |
|---|---|---|
| `source` | `real` / `reconstructed` / `simulated` | provenance of the row |
| `time_resolution` | `day` / `year` / `unknown` | how precisely its timing is known |

They exist so that a frame can never be separated from its own provenance. A reader holding one
CSV, with no access to this repository, can still tell that nothing in it came from a patient.

## Module map

| module | responsibility |
|---|---|
| `schema.py` | the frozen contract between workstreams, and `validate` / `validate_all` |
| `parameters.py` | every parameter with its published source, and the calibration anchors |
| `generator.py` | the generative model, and the VARC-3 criteria as code |
| `calibration.py` | Aalen–Johansen incidence, the scale solver, the calibration report |
| `degrade.py` | the degradation ladder |
| `validation.py` | the recovery test, with an independent Cox implementation |
| `cli.py` | `python -m synthetic` |
