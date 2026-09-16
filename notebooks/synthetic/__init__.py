"""Synthetic cohort for the AVR durability study.

The package produces a literature-calibrated cohort of bioprosthetic aortic valve
recipients with serial echocardiography, dated events and a competing risk of
death. **Nothing it produces is a patient.** Every row carries ``source =
"simulated"``, and every figure, table or slide derived from it must say so.

Why a synthetic cohort exists in this study at all: the supplied extract yields 32
assessable labels from 117 patients, 5 of them failures, and exactly one patient
has echocardiographic values in more than one year. A survival model fitted on
that is noise with a confidence interval around it. The cohort here lets the
protocol's pipeline be executed and evaluated end to end and honestly, and it lets
the cost of each data defect be measured rather than asserted.

Typical use::

    from synthetic import generate
    tables = generate(preset="ideal", seed=20260917, n_patients=1800)
    tables["patients"], tables["echos"], tables["events"], tables["followup"]

and for the degradation ladder::

    from synthetic import PRESETS
    ladder = {name: generate(preset=name) for name in PRESETS}
"""

from __future__ import annotations

from dataclasses import replace

import pandas as pd

from .calibration import (
    calibration_across_seeds,
    calibration_report,
    cumulative_incidence,
    endpoint_times,
    solve_scales,
)
from .degrade import PRESET_DESCRIPTIONS, PRESETS, apply_preset
from .generator import VARC3_STAGE2, VARC3_STAGE3, build_cohort
from .parameters import ANCHORS, DEFAULT, Parameters
from .validation import CoxFit, coverage_test, fit_cox, recovery_test
from .schema import TABLE_NAMES, TABLES, SchemaError, describe, validate, validate_all

__all__ = [
    "generate",
    "PRESETS",
    "PRESET_DESCRIPTIONS",
    "ANCHORS",
    "DEFAULT",
    "Parameters",
    "TABLES",
    "TABLE_NAMES",
    "SchemaError",
    "VARC3_STAGE2",
    "VARC3_STAGE3",
    "build_cohort",
    "apply_preset",
    "calibration_across_seeds",
    "calibration_report",
    "cumulative_incidence",
    "endpoint_times",
    "solve_scales",
    "coverage_test",
    "recovery_test",
    "fit_cox",
    "validate",
    "validate_all",
    "describe",
]

__version__ = "0.1.0"


def generate(
    preset: str = "ideal",
    *,
    seed: int = 20260917,
    n_patients: int | None = None,
    params: Parameters | None = None,
    validate_output: bool = True,
) -> dict[str, pd.DataFrame]:
    """Generate a synthetic cohort, optionally degraded to one rung of the ladder.

    The cohort is a deterministic function of ``preset``, ``seed``, ``n_patients``
    and ``params``: the same arguments always produce the same tables.

    Args:
        preset: Rung of the degradation ladder; see :data:`PRESETS`. ``"ideal"``
            applies no degradation.
        seed: Seed of the random generator.
        n_patients: Cohort size. Defaults to the protocol's sample size of 1,800.
        params: Parameter set. Defaults to the calibrated
            :data:`synthetic.parameters.DEFAULT`.
        validate_output: Check the result against the schema before returning.
            Leave this on unless profiling; it is what stops a malformed cohort
            from reaching another workstream.

    Returns:
        Mapping with keys ``patients``, ``echos``, ``events`` and ``followup``.

    Raises:
        KeyError: If ``preset`` is not a known rung.
        SchemaError: If the generated cohort violates the schema.
    """
    if preset not in PRESETS:
        raise KeyError(f"Unknown preset {preset!r}; expected one of {tuple(PRESETS)}.")

    settings = params if params is not None else DEFAULT
    if n_patients is not None:
        settings = replace(settings, cohort=replace(settings.cohort, n_patients=n_patients))

    tables = build_cohort(settings, seed=seed)
    if preset != "ideal":
        tables = apply_preset(tables, preset, seed=seed)
    if validate_output:
        validate_all(tables)
    return tables
