"""The full degradation ladder: five simulated rungs and one that is not simulated.

The synthetic package can descend from the data the protocol asks for to a
simulation of the data we were given. It cannot tell us whether that simulation is
any good, because it has nothing to check itself against. This module supplies the
missing rung: the supplied extract itself, mapped into the same schema, sitting at
the bottom of the same ladder.

Two things follow, and the second is the one worth putting on a slide.

**The ladder now ends in reality.** A panel reading "our last rung simulates how
poor the data are" is being asked to take the simulation on trust. A panel reading
"our last rung *is* the data" is not.

**The step from the fifth rung to the sixth is itself a measurement.** If the
simulated rung and the real one show the same data availability, the simulation of
poverty was accurate and every conclusion drawn from the intermediate rungs is
better supported. Where they differ, the difference names something about the real
extract the model of it did not capture -- which is worth knowing before anyone
generalises from the ladder.

The dependency runs one way only. :mod:`synthetic` never imports this package, so
it remains runnable on a machine with no access to the private extract; a reviewer
can reproduce every synthetic rung without the data we are not allowed to share.
"""

from __future__ import annotations

from typing import Final

import pandas as pd

from synthetic import PRESET_DESCRIPTIONS, PRESETS, generate

from .to_schema import to_schema

__all__ = ["RUNGS", "RUNG_DESCRIPTIONS", "full_ladder", "availability"]

REAL_RUNG: Final[str] = "as_received"

RUNGS: Final[tuple[str, ...]] = tuple(PRESETS) + (REAL_RUNG,)

RUNG_DESCRIPTIONS: Final[dict[str, str]] = PRESET_DESCRIPTIONS | {
    REAL_RUNG: "Not simulated: the supplied extract itself, mapped into the same schema.",
}


def full_ladder(*, n_patients: int | None = None, seed: int = 20260917) -> dict[str, dict[str, pd.DataFrame]]:
    """Build every rung of the ladder, including the real one.

    Args:
        n_patients: Size of each synthetic rung. The real rung is whatever size the
            extract is, and is not resampled to match: pretending the extract is
            larger than its 117 patients would defeat the purpose of including it.
        seed: Seed for the synthetic rungs.

    Returns:
        Mapping of rung name to that rung's four tables, in ladder order.

    Raises:
        FileNotFoundError: If the extract is not available. Every synthetic rung can
            be built without it; only the last rung needs it.
    """
    rungs = {name: generate(name, seed=seed, n_patients=n_patients) for name in PRESETS}
    rungs[REAL_RUNG] = to_schema()
    return rungs


def _availability(tables: dict[str, pd.DataFrame]) -> dict[str, object]:
    """Measure what an analyst can actually see in one cohort."""
    patients, echos, events = tables["patients"], tables["echos"], tables["events"]
    n = len(patients)
    with_echo = echos["patient_id"].nunique()
    per_patient = echos.groupby("patient_id").size()
    gradients = echos[echos["mean_gradient_mmhg"].notna()]
    serial = gradients.groupby("patient_id").size().gt(1).sum()

    return {
        "patients": n,
        "age_known_pct": round(100 * patients["age_at_implant"].notna().mean(), 1),
        "device_known_pct": round(100 * patients["valve_model"].notna().mean(), 1),
        "any_echo_pct": round(100 * with_echo / n, 1) if n else 0.0,
        "echos_per_patient": round(float(per_patient.mean()), 2) if len(per_patient) else 0.0,
        "reference_echo_pct": round(100 * echos["is_reference"].sum() / n, 1) if n else 0.0,
        "serial_gradient_pct": round(100 * serial / n, 1) if n else 0.0,
        "day_resolution_pct": round(100 * echos["time_resolution"].eq("day").mean(), 1) if len(echos) else 0.0,
        "events_per_100": round(100 * len(events[events["event_type"] != "death"]) / n, 1) if n else 0.0,
        "death_observed": bool((events["event_type"] == "death").any()),
    }


def availability(*, n_patients: int | None = None, seed: int = 20260917) -> pd.DataFrame:
    """Report, per rung, what an analyst can see.

    This is the table the degradation ladder rests on. Every column is a property of
    the *data*, not of a model, so it can be read before any model exists and it
    explains what the model results on each rung are going to mean.

    The last two rows are the ones to read together: ``as_supplied`` is our
    simulation of the extract's poverty and ``as_received`` is the extract.

    Returns:
        One row per rung, in ladder order.
    """
    rungs = full_ladder(n_patients=n_patients, seed=seed)
    rows = []
    for name in RUNGS:
        rows.append({"rung": name, "simulated": name != REAL_RUNG} | _availability(rungs[name]))
    return pd.DataFrame(rows)
