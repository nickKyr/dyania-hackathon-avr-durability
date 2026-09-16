"""Reading the team's consolidated extract, with its traps handled once.

`all_data_one_sheet.xlsx` is a long-format consolidation of the three supplied
workbooks: one row per fact, 55,049 rows over 117 patients, keyed by
``patient`` / ``year`` / ``source`` / ``category`` / ``item`` / ``value``. It is a
good shape for an extract -- provenance travels with every value, and a new field
costs a row rather than a column -- but three properties of it will silently
corrupt any analysis that reads it naively. Each is handled here, once, so that no
notebook has to remember it.

**Duplicated rows.** 28,198 of the 55,049 rows are marked ``duplicate_row = "yes"``:
join fan-out in the original export, not repeated measurements. They are dropped by
default. A count taken before dropping them overstates the laboratory data by 2.3x
and the medications by 2.7x.

**Two extraction methods over the same notes.** 105 notes carry echocardiographic
rows from *both* a regex pass and a language-model pass, with different structure,
so the same measurement appears twice in different shapes. The language-model pass
is the better of the two and is preferred; see :func:`echo_exams`. The regex rows
are not discarded, because comparing the two is itself a result -- see
:func:`method_comparison`.

**Verbatim note text.** The ``evidence`` column carries some 787,000 characters of
note text. It is dropped by default: it is needed to verify an extraction by eye,
and for nothing else, and anything that leaves this machine must not contain it.

Nothing in this module writes to the repository. The workbook itself lives with the
source data, resolved through :mod:`data_paths`.
"""

from __future__ import annotations

import re
from typing import Final

import pandas as pd

from data_paths import ALL_DATA, derived_file

__all__ = [
    "load_long",
    "echo_exams",
    "method_comparison",
    "profile",
    "LLM_METHOD_PREFIX",
    "REGEX_METHOD_PREFIX",
]

LLM_METHOD_PREFIX: Final[str] = "notes-llm"
REGEX_METHOD_PREFIX: Final[str] = "notes-regex"

_ECHO_CATEGORY: Final[re.Pattern[str]] = re.compile(
    r"^echo study\s*(?P<number>\d+)?\s*\((?P<valve>[^,]*),\s*(?P<timing>[^)]*)\)"
)
_MONTH_YEAR: Final[re.Pattern[str]] = re.compile(r"\b(?P<month>0?[1-9]|1[0-2])[/-](?P<year>(?:19|20)\d{2})\b")
_BARE_YEAR: Final[re.Pattern[str]] = re.compile(r"\b(?P<year>(?:19|20)\d{2})\b")
_PRIOR: Final[re.Pattern[str]] = re.compile(r"prior|previous|comparison|referenced|earlier", re.IGNORECASE)


def load_long(*, drop_duplicates: bool = True, drop_evidence: bool = True) -> pd.DataFrame:
    """Load the consolidated extract.

    Args:
        drop_duplicates: Drop the rows the export marked as join fan-out. Leave this
            on unless you are specifically auditing the duplication.
        drop_evidence: Drop the column carrying verbatim note text. Turn it off only
            for interactive verification on the machine holding the data, and never
            for anything that is written out.

    Returns:
        The long table, with ``patient`` as a plain string column.

    Raises:
        FileNotFoundError: If the workbook is not in the derived data directory.
    """
    frame = pd.read_excel(derived_file(ALL_DATA))
    if drop_duplicates:
        frame = frame[frame["duplicate_row"].isna()].copy()
    if drop_evidence and "evidence" in frame:
        frame = frame.drop(columns=["evidence"])
    return frame.reset_index(drop=True)


def _parse_echo_category(category: str) -> dict[str, object]:
    """Split ``echo study 2 (prosthetic valve, post-operative)`` into its parts."""
    match = _ECHO_CATEGORY.match(category)
    if not match:
        return {"study_number": pd.NA, "valve_context": pd.NA, "timing": pd.NA}
    valve = (match.group("valve") or "").replace("valve", "").strip() or pd.NA
    timing = (match.group("timing") or "").strip() or pd.NA
    number = match.group("number")
    return {
        "study_number": int(number) if number else pd.NA,
        "valve_context": valve,
        "timing": timing,
    }


def echo_exams(*, method: str = "llm") -> pd.DataFrame:
    """Return echocardiographic measurements one row per exam and parameter.

    The category string of the extract encodes three things at once -- which study
    within the note, whether the valve is native or prosthetic, and whether the
    study preceded or followed the operation. They are split into columns here,
    because leaving them fused means every downstream filter is a string match.

    Args:
        method: ``"llm"`` for the language-model pass, ``"regex"`` for the regex
            pass, or ``"both"`` to keep them side by side with the method labelled.
            The two overlap on 105 notes, so ``"both"`` double-counts by
            construction and is only for comparison.

    Returns:
        One row per measurement, with ``study_number``, ``valve_context``,
        ``timing``, a parsed ``study_date`` where one survived redaction, and
        ``is_prior_study`` marking a study quoted for comparison rather than
        performed now.

    Raises:
        ValueError: If ``method`` is not one of the three accepted values.
    """
    if method not in {"llm", "regex", "both"}:
        raise ValueError(f"method must be 'llm', 'regex' or 'both', not {method!r}")

    frame = load_long()
    echo = frame[frame["category"].str.startswith("echo study", na=False)].copy()

    prefixes = {"llm": (LLM_METHOD_PREFIX,), "regex": (REGEX_METHOD_PREFIX,), "both": (LLM_METHOD_PREFIX, REGEX_METHOD_PREFIX)}[method]
    echo = echo[echo["method"].str.startswith(prefixes, na=False)].copy()

    parsed = pd.DataFrame([_parse_echo_category(c) for c in echo["category"]], index=echo.index)
    echo = pd.concat([echo, parsed], axis=1)

    detail = echo["detail"].fillna("")
    echo["is_prior_study"] = detail.str.contains(_PRIOR)

    # Some month/year dates escaped de-identification. They are the only timing
    # information finer than the note's service year that this extract contains.
    month_year = detail.str.extract(_MONTH_YEAR)
    bare_year = detail.str.extract(_BARE_YEAR)
    echo["study_month"] = pd.to_numeric(month_year["month"], errors="coerce")
    echo["study_year"] = pd.to_numeric(month_year["year"].fillna(bare_year["year"]), errors="coerce")
    echo["study_date_known"] = echo["study_year"].notna()

    columns = [
        "patient", "note_id", "note_type", "year", "study_number", "valve_context",
        "timing", "item", "value", "unit", "is_prior_study", "study_month",
        "study_year", "study_date_known", "detail", "method",
    ]
    return echo[columns].reset_index(drop=True)


def method_comparison() -> pd.DataFrame:
    """Compare what the regex pass and the language-model pass each recovered.

    Both ran over the same notes, so this is a like-for-like comparison of two
    abstraction methods on identical input -- the closest thing to an evaluation
    available without a gold standard. It cannot say which is *right*; it says
    which recovers more structure.

    Returns:
        One row per parameter, with the notes, patients and values each method
        produced.
    """
    frame = load_long()
    echo = frame[frame["category"].str.startswith("echo study", na=False)]
    rows = []
    for label, prefix in (("regex", REGEX_METHOD_PREFIX), ("llm", LLM_METHOD_PREFIX)):
        subset = echo[echo["method"].str.startswith(prefix, na=False)]
        grouped = subset.groupby("item").agg(
            values=("value", "size"), notes=("note_id", "nunique"), patients=("patient", "nunique")
        )
        rows.append(grouped.add_prefix(f"{label}_"))
    return pd.concat(rows, axis=1).fillna(0).astype(int).reset_index()


def profile() -> str:
    """Return an aggregate description of the extract, safe to paste into a document.

    Counts and distributions only: no patient identifiers, no values, no note text.
    """
    raw = pd.read_excel(derived_file(ALL_DATA))
    clean = load_long()
    echo = echo_exams(method="llm")
    post = echo[(echo["valve_context"] == "prosthetic") & (echo["timing"] == "post-operative")]
    gradients = post[post["item"] == "mean_gradient_mmhg"]
    per_patient = gradients.groupby("patient").agg(values=("value", "size"), years=("year", "nunique"))

    lines = [
        "Consolidated extract",
        f"  rows                     {len(raw):,} raw, {len(clean):,} after dropping join fan-out",
        f"  patients                 {clean['patient'].nunique()}",
        f"  sources                  " + ", ".join(f"{k} {v:,}" for k, v in clean["source"].value_counts().items()),
        f"  extraction methods       " + ", ".join(f"{k.split(' (')[0]} {v:,}" for k, v in clean["method"].value_counts().items()),
        "",
        "Echocardiography, language-model pass",
        f"  measurements             {len(echo):,} over {echo['patient'].nunique()} patients",
        f"  post-operative prosthetic mean gradients: {len(gradients)} over {gradients['patient'].nunique()} patients",
        f"  patients with more than one value        : {(per_patient['values'] > 1).sum()}",
        f"  patients with values in more than one year: {(per_patient['years'] > 1).sum()}",
        f"  measurements with a surviving date       : {int(echo['study_date_known'].sum())} of {len(echo)}",
        f"  measurements marked as a quoted prior    : {int(echo['is_prior_study'].sum())}",
    ]
    return "\n".join(lines)
