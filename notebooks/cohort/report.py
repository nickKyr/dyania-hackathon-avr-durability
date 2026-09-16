"""Generate the committed results document.

Everything this project claims about the synthetic cohort is reproducible by
running code, which is the right standard but the wrong assumption about how a
document gets read. A reviewer with ten minutes does not clone a repository and
run a package; they read what is in front of them. This module writes the two
tables that carry the argument into a Markdown file that is committed, so the
evidence is legible without execution and still regenerated from the code rather
than maintained by hand.

Run it from the ``notebooks`` directory::

    python -m cohort > ../data/synthetic/results.md

The output contains counts and published comparisons only. No patient-level value,
no note text and no identifier appears in it, so it is safe to commit and to paste
into a slide.
"""

from __future__ import annotations

from datetime import date

from synthetic import calibration_across_seeds, coverage_test, generate
from synthetic.parameters import ABSOLUTE_TOLERANCE, ANCHORS, RELATIVE_TOLERANCE

from .ladder import RUNG_DESCRIPTIONS, RUNGS, availability

__all__ = ["markdown_report"]


def _percent(value: float) -> str:
    return f"{100 * value:.1f}%"


def _calibration_section() -> str:
    """Render the calibration of the synthetic cohort against published evidence."""
    report = calibration_across_seeds()
    targeted = report[report["targeted"]]
    rest = report[~report["targeted"]]

    lines = [
        "## Calibration against published evidence",
        "",
        "Cumulative incidence by the Aalen–Johansen estimator, under a competing risk of death —",
        "not one minus Kaplan–Meier, which would answer a question about a population in which",
        "nobody dies. NOTION used the same estimator, so the comparison is like for like.",
        "",
        "Each band is the same rule applied to every anchor, fixed before any cohort was generated:",
        f"**{_percent(ABSOLUTE_TOLERANCE)} absolute, or {_percent(RELATIVE_TOLERANCE)} of the published value, whichever is larger.**",
        "Figures are the mean and standard deviation over eight seeds, because at 1,800 patients the",
        "Monte Carlo error of a 20% incidence is about one percentage point — the size of the",
        "differences being judged.",
        "",
        "| quantity | group | horizon | published | cohort | inside band |",
        "|---|---|---|---|---|---|",
    ]
    for label, block in (("targeted", targeted), ("not targeted", rest)):
        lines.append(f"| **{label}** | | | | | |")
        for _, row in block.iterrows():
            lines.append(
                f"| {row['quantity'].replace('_', ' ')} | {row['subgroup']} | "
                f"{row['horizon_years']:g} y | {_percent(row['published'])} | "
                f"{_percent(row['cohort_mean'])} ± {100 * row['cohort_sd']:.1f} | "
                f"{row['seeds_within_band']} of {row['seeds']} |"
            )
    lines += ["", "Sources:", ""]
    for source in dict.fromkeys(a.source for a in ANCHORS):
        lines.append(f"- {source}")
    return "\n".join(lines)


def _ladder_section(n_patients: int) -> str:
    """Render what an analyst can see at each rung of the degradation ladder."""
    table = availability(n_patients=n_patients)
    lines = [
        "## The degradation ladder",
        "",
        "The same cohort, its data progressively removed. The patients, their biology and their",
        "events are identical on every rung; only what an analyst can see of them changes, so one",
        "unchanged pipeline run across the rungs measures exactly one thing — what each defect",
        "costs.",
        "",
        "**The last rung is not simulated.** It is the supplied extract, mapped into the same",
        "schema. Every rung above it is synthetic and reproducible without access to any private",
        f"data; all rungs are shown here at n = {n_patients} so that they are comparable with it.",
        "",
        "| rung | simulated | any examination | exams per patient | more than one gradient | events per 100 | death observed |",
        "|---|---|---|---|---|---|---|",
    ]
    for _, row in table.iterrows():
        lines.append(
            f"| `{row['rung']}` | {'yes' if row['simulated'] else '**no**'} | {row['any_echo_pct']:.1f}% | "
            f"{row['echos_per_patient']:.2f} | {row['serial_gradient_pct']:.1f}% | "
            f"{row['events_per_100']:.1f} | {'yes' if row['death_observed'] else '**no**'} |"
        )
    lines += ["", "What each rung removes:", ""]
    for rung in RUNGS:
        lines.append(f"- `{rung}` — {RUNG_DESCRIPTIONS[rung]}")

    simulated = table[table["rung"] == "as_supplied"].iloc[0]
    received = table[table["rung"] == "as_received"].iloc[0]
    lines += [
        "",
        "### What the last two rows are for",
        "",
        "`as_supplied` is our model of how poor the extract is; `as_received` is the extract. Where",
        "they agree, the simulation is trustworthy and the intermediate rungs can be believed. Where",
        "they differ, the difference names something the model of the data did not capture.",
        "",
        (
            f"They agree on the reach of abstraction ({simulated['any_echo_pct']:.1f}% against "
            f"{received['any_echo_pct']:.1f}%), on examinations per patient "
            f"({simulated['echos_per_patient']:.2f} against {received['echos_per_patient']:.2f}), "
            "and on the total absence of mortality data."
        ),
        "",
        (
            f"They disagree on events: **{simulated['events_per_100']:.1f} per 100 patients in "
            f"the simulation against {received['events_per_100']:.1f} in the extract**."
        ),
        "",
        "That gap is not a calibration failure and was deliberately left uncorrected. It is the",
        "measured cost of incomplete ascertainment: "
        # Derived rather than described, because the size of the gap moves whenever the
        # cohort is recalibrated and a word like "half" quietly stops being true.
        f"**{_missing_share(simulated, received):.0%} of the deteriorations** a properly followed",
        "cohort would show are invisible here, in patients who were never imaged again. It is the",
        "clearest single argument in this repository for building the abstraction pipeline the",
        "protocol proposes.",
    ]
    return "\n".join(lines)


RECOVERY_SEEDS: tuple[int, ...] = (20260917, 1, 2)
"""Seeds of the recovery test quoted in the report.

Three seeds over seven covariates give 21 fits, which is the smallest number that
says anything about coverage while keeping the report runnable in about a minute.
"""


def _recovery_sentence() -> str:
    """Report the recovery test by running it, not by quoting a remembered figure.

    The number this produces is the document's central claim of *correctness*, as
    opposed to plausibility, so it is the last number that should be maintained by
    hand in a file whose header says it is generated. Computing it costs about a
    minute and means the claim cannot outlive the code it describes.
    """
    result = coverage_test(seeds=RECOVERY_SEEDS)
    overall = result[result["covariate"] == "ALL"].iloc[0]
    return (
        f"the 95% interval covered the injected value in "
        f"**{int(overall['seeds_covering'])} of {int(overall['seeds'])} fits**, against a nominal "
        f"95%, with a mean log bias of **{overall['mean_log_bias']:+.4f}**."
    )


def _missing_share(simulated: dict[str, object], received: dict[str, object]) -> float:
    """Fraction of the simulation's events that the extract never records.

    Both rungs describe the same population at the same size, so the shortfall
    between them is what abstraction and surveillance together fail to reach.
    """
    expected = float(simulated["events_per_100"])
    return 0.0 if expected <= 0 else (expected - float(received["events_per_100"])) / expected


def markdown_report(*, n_patients: int = 117, seed: int = 20260917) -> str:
    """Return the full results document.

    Args:
        n_patients: Size of the synthetic rungs. Defaults to the size of the real
            extract so that every rung is directly comparable with it.
        seed: Seed of the synthetic cohorts.

    Returns:
        Markdown, containing aggregate counts and published comparisons only.

    Raises:
        FileNotFoundError: If the supplied extract is unavailable; the real rung
            cannot be built without it.
    """
    full = generate("ideal", seed=seed)
    counts = ", ".join(f"{len(v):,} {k}" for k, v in full.items())
    return "\n\n".join(
        [
            "# Synthetic Cohort — Results",
            (
                "> Generated by `python -m cohort` on "
                f"{date.today().isoformat()}. Do not edit by hand.\n>\n"
                "> Every figure is an aggregate. No patient-level value, note text or identifier "
                "appears here."
            ),
            (
                f"At its full protocol size the synthetic cohort is {counts}, from seed {seed}. "
                "The tables below are the two claims this workstream makes: that the cohort lands "
                "where published series land, and that the cost of each data defect can be measured "
                "rather than asserted."
            ),
            _calibration_section(),
            _ladder_section(n_patients),
            (
                "## What calibration does and does not prove\n\n"
                "Nine parameters were fitted against these anchors, which is close to saturated, so "
                "agreement is **not** independent evidence that the cohort is correct. It establishes "
                "that the cohort is *plausible* — that a pipeline exercised on it runs at realistic "
                "event rates. Correctness is established separately, by injecting known hazard ratios "
                "into the generator and recovering them with an independently implemented Cox model: "
                f"{_recovery_sentence()}\n\n"
                "Two anchors are missed and neither is tuned away. Severe deterioration after "
                "transcatheter implant is reported by NOTION as 1.5% — about two events among 145 "
                "randomised patients — against 5.9% in the UK TAVI registry at a *shorter* horizon; "
                "this cohort reproduces the registry and misses the trial. Severe deterioration after "
                "surgical implant comes out at the level of NOTION's *bioprosthetic valve failure* "
                "rather than its *severe deterioration*, which says that thresholds applied "
                "mechanically do not separate two categories a trial adjudication panel separates. "
                "That gap is what the protocol's ground-truth hierarchy exists to close."
            ),
        ]
    )
