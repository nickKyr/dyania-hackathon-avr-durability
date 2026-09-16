"""Frozen table schema for the synthetic AVR durability cohort.

This module is the **contract between the three workstreams**. The data workstream
produces frames that satisfy it, the model workstream consumes them, and the
extraction workstream scores its output against them. Changing a column here
changes work for other people, so treat the definitions as frozen for the
duration of the study unless the team agrees otherwise.

Two design decisions are load-bearing and are documented here rather than in a
commit message, because reviewers of the protocol will ask about both.

**The schema is derived from the endpoint and the model, not from the shape of
the supplied extract.** The synthetic cohort is a *superset* of what the
prototype extract contains; the extract is a sparse, degraded case of it. Had the
schema been narrowed to the columns the extract happens to provide, the landmark
model could not be expressed at all and the degradation experiment would have no
upper rung to measure against.

**Every row of every table carries two governance columns.** ``source`` records
whether a row is a real observation, a value reconstructed from published
aggregate data, or a simulated one; ``time_resolution`` records whether its
timing is known to the day, only to the calendar year, or not at all. They exist
so that a frame can never be separated from its own provenance: a reader holding
one CSV, with no access to this repository, can still tell that nothing in it
came from a patient.

Times in every table other than :data:`PATIENTS` are expressed as
``days_from_implant``, so the implant is always the time origin and cohorts
generated at different calendar epochs remain directly comparable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import pandas as pd
from pandas.api import types as pdt

__all__ = [
    "SOURCES",
    "TIME_RESOLUTIONS",
    "GOVERNANCE_COLUMNS",
    "TABLES",
    "TABLE_NAMES",
    "Column",
    "Table",
    "SchemaError",
    "validate",
    "validate_all",
    "describe",
]


class SchemaError(ValueError):
    """Raised when a frame does not satisfy the schema.

    The message lists every violation found, not just the first, so that a
    generator can be corrected in one pass rather than one error at a time.
    """


SOURCES: Final[tuple[str, ...]] = ("real", "reconstructed", "simulated")
"""Provenance of a row.

``real``
    An observation of an actual patient.
``reconstructed``
    Derived from published aggregate data, for example event times recovered
    from a published survival curve. Not a patient observation, but anchored to
    one.
``simulated``
    Drawn from the generative model in :mod:`synthetic.generator`. Every row this
    package produces is ``simulated``.
"""

TIME_RESOLUTIONS: Final[tuple[str, ...]] = ("day", "year", "unknown")
"""How precisely the timing of a row is known.

``day``
    Exact to the day.
``year``
    Known only to the calendar year. This is the ceiling the prototype extract
    imposes, and the ``year_resolution`` rung of the degradation ladder.
``unknown``
    No usable timing.
"""


@dataclass(frozen=True, slots=True)
class Column:
    """One column of a table, with the constraints :func:`validate` enforces."""

    name: str
    kind: str
    """One of ``"int"``, ``"float"``, ``"bool"`` or ``"str"``."""
    description: str
    nullable: bool = False
    allowed: tuple[str, ...] | None = None
    """Permitted values, for categorical string columns."""
    minimum: float | None = None
    maximum: float | None = None

    def __post_init__(self) -> None:
        if self.kind not in {"int", "float", "bool", "str"}:
            raise ValueError(f"{self.name}: unsupported kind {self.kind!r}")


@dataclass(frozen=True, slots=True)
class Table:
    """One table of the cohort."""

    name: str
    grain: str
    """What exactly one row represents. Ambiguity here is how duplicate rows and
    silent join fan-out enter a dataset."""
    key: tuple[str, ...]
    """Columns that are unique together. Enforced by :func:`validate`."""
    columns: tuple[Column, ...]

    @property
    def column_names(self) -> tuple[str, ...]:
        """Names of every column, in declaration order."""
        return tuple(column.name for column in self.columns)

    def column(self, name: str) -> Column:
        """Return the named column.

        Raises:
            KeyError: If the table has no such column.
        """
        for column in self.columns:
            if column.name == name:
                return column
        raise KeyError(f"{self.name} has no column {name!r}")


GOVERNANCE_COLUMNS: Final[tuple[Column, ...]] = (
    Column(
        "source",
        "str",
        "Provenance of the row; always 'simulated' for rows this package produces.",
        allowed=SOURCES,
    ),
    Column(
        "time_resolution",
        "str",
        "Precision of the row's timing: day, year or unknown.",
        allowed=TIME_RESOLUTIONS,
    ),
)


def _table(name: str, grain: str, key: tuple[str, ...], columns: tuple[Column, ...]) -> Table:
    """Build a table, appending the governance columns every table must carry."""
    return Table(name=name, grain=grain, key=key, columns=columns + GOVERNANCE_COLUMNS)


PATIENTS: Final[Table] = _table(
    "patients",
    grain="one row per implanted patient",
    key=("patient_id",),
    columns=(
        Column("patient_id", "str", "Synthetic identifier, stable for a given seed."),
        Column("implant_year", "int", "Calendar year of the index implant.", minimum=1990, maximum=2040),
        # Everything below is nullable, and that is the point of the schema rather
        # than a weakness in it. This table describes the cohort the protocol asks a
        # site to supply; a real extract is a SPARSE CASE of it. The supplied extract
        # has no demographics table, no implant registry and no echo table, so it can
        # populate only some of these columns -- and the gap between what the schema
        # asks for and what an extract delivers is precisely the quantity the
        # degradation ladder measures. Forbidding nulls here would have forced the
        # real data into a different shape and made the comparison impossible.
        #
        # A synthetic cohort at the `ideal` rung populates all of them, and a test
        # asserts it does.
        Column(
            "age_at_implant",
            "float",
            "Age in years at the index implant. Absent from the supplied extract, "
            "where it is redacted as a token in 194 of 215 notes.",
            nullable=True,
            minimum=18.0,
            maximum=105.0,
        ),
        Column(
            "sex",
            "str",
            "Recorded sex. In the supplied extract this is inferred from pronouns, "
            "so it is a weak field there and absent for patients whose notes use none.",
            nullable=True,
            allowed=("female", "male"),
        ),
        Column("bsa_m2", "float", "Body surface area in m^2.", nullable=True, minimum=1.0, maximum=3.0),
        Column("approach", "str", "Index procedure type.", nullable=True, allowed=("SAVR", "TAVR")),
        Column("valve_model", "str", "Commercial model of the implanted bioprosthesis.", nullable=True),
        Column("valve_size_mm", "int", "Label size in mm.", nullable=True, minimum=17, maximum=34),
        Column(
            "eoa_cm2",
            "float",
            "Effective orifice area at the reference echo, cm^2.",
            nullable=True, minimum=0.3, maximum=3.5,
        ),
        Column(
            "eoa_index_cm2_m2",
            "float",
            "Effective orifice area indexed to body surface area, cm^2/m^2. The "
            "quantity patient-prosthesis mismatch is defined on.",
            nullable=True,
            minimum=0.2,
            maximum=2.5,
        ),
        Column(
            "ppm_grade",
            "str",
            "Patient-prosthesis mismatch at the VARC-3 cut-offs: moderate at an indexed "
            "EOA of 0.85 or below, severe at 0.65 or below.",
            nullable=True,
            allowed=("none", "moderate", "severe"),
        ),
        # A comorbidity absent from a note is UNKNOWN, not absent. Recording it as
        # False would turn missing documentation into a negative finding, which is
        # how chart review manufactures spurious associations.
        Column("diabetes", "bool", "Diabetes mellitus at implant.", nullable=True),
        Column("ckd", "bool", "Chronic kidney disease at implant.", nullable=True),
        Column("smoking", "bool", "Current or recent smoking at implant.", nullable=True),
        Column("bicuspid", "bool", "Bicuspid native aortic valve.", nullable=True),
        Column(
            "anticoagulation",
            "bool",
            "Oral anticoagulant at implant, usually for atrial fibrillation rather "
            "than for the valve. It protects against the pannus and thrombosis "
            "failure mode and against no other, so it is one of the covariates that "
            "tells the modes apart. The supplied extract can populate this column "
            "from its medication table, which is why it is worth asking for.",
            nullable=True,
        ),
    ),
)

ECHOS: Final[Table] = _table(
    "echos",
    grain="one row per echocardiographic examination",
    key=("echo_id",),
    columns=(
        Column("patient_id", "str", "Foreign key to patients."),
        Column("echo_id", "str", "Unique examination identifier."),
        Column(
            "days_from_implant",
            "int",
            "Days between the index implant and this examination.",
            minimum=0,
            maximum=20_000,
        ),
        Column(
            "is_reference",
            "bool",
            "True for the reference examination performed 30 days to 3 months after "
            "implant, against which VARC-3 haemodynamic deterioration is defined. "
            "Without it, only the absolute-threshold arm of the definition is usable.",
        ),
        Column("mean_gradient_mmhg", "float", "Mean transprosthetic gradient.", nullable=True, minimum=0.0, maximum=120.0),
        Column("peak_gradient_mmhg", "float", "Peak transprosthetic gradient.", nullable=True, minimum=0.0, maximum=200.0),
        Column("dvi", "float", "Dimensionless valve index.", nullable=True, minimum=0.05, maximum=1.2),
        Column("eoa_cm2", "float", "Effective orifice area by continuity, cm^2.", nullable=True, minimum=0.1, maximum=3.5),
        Column(
            "ar_grade",
            "str",
            "Intraprosthetic aortic regurgitation grade.",
            nullable=True,
            allowed=("none", "trace", "mild", "moderate", "severe"),
        ),
        Column("lvef_pct", "float", "Left ventricular ejection fraction, percent.", nullable=True, minimum=10.0, maximum=80.0),
    ),
)

EVENTS: Final[Table] = _table(
    "events",
    grain="one row per adjudicated event; a patient may contribute several",
    key=("patient_id", "event_type"),
    columns=(
        Column("patient_id", "str", "Foreign key to patients."),
        Column(
            "event_type",
            "str",
            "svd_stage2 and svd_stage3 are VARC-3 haemodynamic valve deterioration; "
            "bvf_reintervention is bioprosthetic valve failure treated by valve-in-valve "
            "or redo surgery; death is the competing risk.",
            allowed=("svd_stage2", "svd_stage3", "bvf_reintervention", "death"),
        ),
        Column(
            "failure_mode",
            "str",
            "Which failure mode the valve reached first before this event: calcific "
            "stenosis, leaflet tear, or pannus and thrombosis. Null on deaths. "
            "This is the EARLIEST-ONSET mode, not a causal attribution of which "
            "criterion fired: a valve that has both calcified and torn contributes "
            "both signatures to the echo, and the VARC-3 rule is applied to the "
            "combination. It is ground truth available only in simulation, and the "
            "protocol names mode-specific prediction as an extension.",
            nullable=True,
            allowed=("calcific", "tear", "pannus"),
        ),
        Column(
            "days_from_implant",
            "int",
            "Days between implant and the event as it becomes OBSERVABLE, not the "
            "latent onset. A deterioration is observed at the examination that detects "
            "it, which is what makes the outcome interval-censored.",
            minimum=0,
            maximum=20_000,
        ),
        Column(
            "interval_start_days",
            "int",
            "Day of the last observation at which the event had NOT yet occurred, so "
            "the event lies in the half-open interval (interval_start_days, "
            "days_from_implant]. For an echocardiographic event this is the previous "
            "examination, which may be years earlier; for a reintervention or a death "
            "it equals days_from_implant, because those are observed exactly. Supplied "
            "so that an interval-censored analysis is possible: an analysis using only "
            "the right endpoint treats a deterioration found after a three-year gap as "
            "though it happened on the day it was found.",
            minimum=0,
            maximum=20_000,
        ),
        Column(
            "ascertainment",
            "str",
            "How the event was established. The ground-truth hierarchy of the protocol: "
            "explant and reintervention outrank echocardiographic criteria.",
            allowed=("echo", "reintervention", "explant", "registry"),
        ),
    ),
)

FOLLOWUP: Final[Table] = _table(
    "followup",
    grain="one row per patient, summarising observation time",
    key=("patient_id",),
    columns=(
        Column("patient_id", "str", "Foreign key to patients."),
        Column(
            "last_contact_days",
            "int",
            "Days from implant to the end of observation, whether by event, loss to "
            "follow-up or administrative censoring at the study horizon.",
            minimum=0,
            maximum=20_000,
        ),
        Column("n_echos", "int", "Number of examinations recorded for the patient.", minimum=0, maximum=200),
        Column(
            "censoring_reason",
            "str",
            "Why observation ended. 'dropout' is informative by construction: patients "
            "who stop attending are not a random sample of those at risk.",
            allowed=("event", "death", "dropout", "administrative"),
        ),
    ),
)

TABLES: Final[dict[str, Table]] = {
    table.name: table for table in (PATIENTS, ECHOS, EVENTS, FOLLOWUP)
}
TABLE_NAMES: Final[tuple[str, ...]] = tuple(TABLES)


_MEASUREMENTS: Final[frozenset[str]] = frozenset(
    {"mean_gradient_mmhg", "peak_gradient_mmhg", "dvi", "eoa_cm2", "ar_grade", "lvef_pct"}
)
"""Parameters an examination may report. At least one must be present per row."""


def _kind_matches(series: pd.Series, kind: str) -> bool:
    """Return whether a series is compatible with a declared column kind.

    Compatibility is deliberately looser than equality: a column read back from
    CSV arrives with a different but equivalent dtype, and a nullable integer
    column that happens to contain missing values arrives as float. Refusing
    those would make the schema unusable on its own round-tripped output.
    """
    if kind == "int":
        return pdt.is_integer_dtype(series) or (
            pdt.is_float_dtype(series) and series.dropna().mod(1).eq(0).all()
        )
    if kind == "float":
        return pdt.is_numeric_dtype(series) and not pdt.is_bool_dtype(series)
    if kind == "bool":
        return pdt.is_bool_dtype(series) or set(series.dropna().unique()) <= {0, 1}
    return pdt.is_object_dtype(series) or isinstance(series.dtype, pd.CategoricalDtype) or pdt.is_string_dtype(series)


def validate(frame: pd.DataFrame, table: str) -> None:
    """Check a frame against the schema of ``table``.

    Every violation is collected and reported together, because a generator that
    is wrong is usually wrong in several columns at once.

    Args:
        frame: The frame to check.
        table: Name of the table, one of :data:`TABLE_NAMES`.

    Raises:
        KeyError: If ``table`` is not a known table.
        SchemaError: If the frame violates the schema in any way.
    """
    if table not in TABLES:
        raise KeyError(f"Unknown table {table!r}; expected one of {TABLE_NAMES}.")
    spec = TABLES[table]
    problems: list[str] = []

    expected = set(spec.column_names)
    present = set(frame.columns)
    if missing := sorted(expected - present):
        problems.append(f"missing columns: {missing}")
    if extra := sorted(present - expected):
        problems.append(f"unexpected columns: {extra}")

    for column in spec.columns:
        if column.name not in present:
            continue
        series = frame[column.name]

        if not column.nullable and series.isna().any():
            problems.append(f"{column.name}: {int(series.isna().sum())} missing values, column is not nullable")

        if not _kind_matches(series, column.kind):
            problems.append(f"{column.name}: dtype {series.dtype} is not compatible with kind {column.kind!r}")

        values = series.dropna()
        if column.allowed is not None and (
            unexpected := sorted(set(values.unique()) - set(column.allowed))
        ):
            problems.append(f"{column.name}: values outside the allowed set {list(column.allowed)}: {unexpected}")
        if column.minimum is not None and pdt.is_numeric_dtype(values) and (values < column.minimum).any():
            problems.append(f"{column.name}: {int((values < column.minimum).sum())} values below the minimum {column.minimum}")
        if column.maximum is not None and pdt.is_numeric_dtype(values) and (values > column.maximum).any():
            problems.append(f"{column.name}: {int((values > column.maximum).sum())} values above the maximum {column.maximum}")

    if table == "echos" and set(_MEASUREMENTS) <= present:
        empty = frame[list(_MEASUREMENTS)].isna().all(axis=1).sum()
        if empty:
            problems.append(
                f"{int(empty)} examinations report none of {sorted(_MEASUREMENTS)}. "
                "An examination from which nothing was measured is not an examination; "
                "it is a row that will silently inflate any count of follow-up imaging."
            )

    if set(spec.key) <= present:
        duplicated = int(frame.duplicated(subset=list(spec.key)).sum())
        if duplicated:
            problems.append(
                f"key {list(spec.key)} is not unique: {duplicated} duplicate rows. "
                f"The grain of this table is {spec.grain}."
            )

    if problems:
        listed = "\n  - ".join(problems)
        raise SchemaError(f"Table {table!r} does not satisfy the schema:\n  - {listed}")


def validate_all(tables: dict[str, pd.DataFrame]) -> None:
    """Validate a complete cohort and the referential integrity between its tables.

    Args:
        tables: Mapping of table name to frame; must contain every table in
            :data:`TABLE_NAMES`.

    Raises:
        SchemaError: If any table is invalid, a table is absent, or a child table
            references a patient that does not exist.
    """
    if absent := sorted(set(TABLE_NAMES) - set(tables)):
        raise SchemaError(f"Cohort is incomplete; missing tables: {absent}")

    for name in TABLE_NAMES:
        validate(tables[name], name)

    known = set(tables["patients"]["patient_id"])
    for name in ("echos", "events", "followup"):
        referenced = set(tables[name]["patient_id"])
        if orphans := referenced - known:
            raise SchemaError(
                f"Table {name!r} references {len(orphans)} patient_id values absent from 'patients'."
            )


def describe(table: str) -> str:
    """Return a Markdown table documenting ``table``, for use in the data plan.

    Generating the documentation from the schema keeps the two from drifting
    apart, which is the usual fate of a hand-written data dictionary.

    Raises:
        KeyError: If ``table`` is not a known table.
    """
    if table not in TABLES:
        raise KeyError(f"Unknown table {table!r}; expected one of {TABLE_NAMES}.")
    spec = TABLES[table]
    lines = [
        f"### `{spec.name}`",
        "",
        f"*Grain:* {spec.grain}. *Key:* {', '.join(f'`{k}`' for k in spec.key)}.",
        "",
        "| column | type | constraints | description |",
        "|---|---|---|---|",
    ]
    for column in spec.columns:
        constraints: list[str] = []
        if column.allowed is not None:
            constraints.append(" / ".join(f"`{value}`" for value in column.allowed))
        if column.minimum is not None or column.maximum is not None:
            constraints.append(f"{column.minimum} to {column.maximum}")
        if column.nullable:
            constraints.append("nullable")
        lines.append(
            f"| `{column.name}` | {column.kind} | {'; '.join(constraints) or '—'} | {column.description} |"
        )
    return "\n".join(lines)
