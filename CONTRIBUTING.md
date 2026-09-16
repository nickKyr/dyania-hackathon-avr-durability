# Working in this repository

Setup and submission mechanics, kept out of `README.md` so that the README stays the document a
reader of the *study* needs. Nothing here is specific to our team except the branch and the fork.

## Environment

The project uses [uv](https://docs.astral.sh/uv/). After cloning, and after every `git pull`:

```bash
uv sync
```

Add a dependency with `uv add <package>` rather than installing into the machine's Python, and
commit both `pyproject.toml` and `uv.lock` so everyone resolves the same versions.

## The data

The three supplied extracts are patient data. They are **never** committed: `.gitignore` blocks
every spreadsheet, CSV, parquet, pickle and derived table under `data/`, and the fork is public.
Copy them into `data/` before running `scripts/01`–`04`; the scripts say so if they are missing.
Notebook outputs must contain aggregates only — no row-level values, no note text, no identifiers.

## Branch and submission

We work on `team/dyanooumenoi`. Push to the fork, then open one pull request to
`dyaniahealth/dyania-hackathon-avr-durability` `main`, titled `Team submission: dyanooumenoi`.
**Do not merge it.** Only the last commit pushed before the deadline is assessed.

## Reproducing the evidence

| Command | Regenerates |
|---|---|
| `uv run python -m pytest notebooks/synthetic/tests -q` | the synthetic cohort's 54 tests |
| `uv run python -m pytest notebooks/pipeline/tests -q` | 15 tests on labels, landmark features, the round trip and matching |
| `uv run python scripts/05_report_synthetic.py` | `data/synthetic/results.md` |
| `uv run python scripts/06_model_stability.py` | `model/stability.md` |
| `uv run python scripts/07_sample_size.py` | `protocol/sample_size.md` |
| `uv run python scripts/08_decision_curve.py` | `model/decision_curve.md` |

`scripts/09_real_extract_rung.py` is the one exception: it needs the private extract, and it
measures the foot of the degradation ladder with the same code the synthetic rungs use, so that the
comparison between them is a comparison. Run it after notebook 02, then rerun 05.

Rerun the relevant one after changing the generator, the features or the models, and commit the
regenerated document with the change. A published number that no longer matches the code is worse
than no number at all.

---

## The organisers' instructions, for reference

## Getting Started

> ⚠️ **Do not upload real patient data or clinical notes to this repository.** Any data you use must be de-identified, synthetic, or otherwise cleared for public sharing — this repo (and your fork) may be publicly visible.

### 1. Fork this repository

Go to **[https://github.com/dyaniahealth/dyania-hackathon-avr-durability](https://github.com/dyaniahealth/dyania-hackathon-avr-durability)** and click **Fork** (top-right) to create a copy under your own GitHub account.

### 2. Clone your fork

```bash
git clone https://github.com/<your-username>/dyania-hackathon-avr-durability.git
cd dyania-hackathon-avr-durability
```

### 3. Create your team branch

Branch names must follow this format: `team/<your-team-name>` (lowercase, hyphens for spaces).

```bash
git checkout -b team/your-team-name
```

Examples: `team/panathinea`, `team/valve-guardians`, `team/svd-sentinels`

### 4. Work on your branch

Edit the template files inside `protocol/`, `model/`, `data/`, and `presentation/`. Every `> *Fill in:*` block is a placeholder — replace it with your team's content.

```bash
# Stage and commit as you go
git add .
git commit -m "your message"
```

### 5. Submit — open a Pull Request before the deadline

Push your branch to your fork and open a Pull Request to the original repository:

```bash
git push origin team/your-team-name
```

Then go to your fork on GitHub and click **"Compare & pull request"**.
Set the base repository to `dyania-health/dyania-hackathon-avr-durability` and the base branch to `main`.
Title your PR: `Team submission: <your-team-name>`

> **Deadline: September 17, 2026 — before the presentation session.**
> Only the last commit pushed before the deadline will be evaluated.
> Make sure your PR is open — **do not** merge it.

## uv package manager

1. Install uv on macOS/Linux:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

now you should be able to see the version of uv:
```bash
uv --version
```

2. Go to repository and then, initialize the project with uv:
```bash
uv init
```

3. After git pull, synchronize environment:
```bash
uv sync
```

4. Add dependencies in .venv instead of installing them on the machine, i.e. for pandas:
```bash
uv add pandas
```

5. For removing an unnecessary package from venv, i.e. removing pandas:
```bash
uv remove pandas
```
