# Candidate Failure Criteria

Published criteria under consideration for the primary endpoint, and how each maps onto what
the prototype extract can actually support. The final column is a team decision and is
deliberately left open until the clinical lead signs off.

| criterion | definition | timing | how it maps to our data | team decision (fill in) |
|---|---|---|---|---|
| VARC-3 stage 2 HVD (moderate) | mean gradient rise >= 10 mmHg from reference echo resulting in >= 20 mmHg, with EOA fall >= 0.3 cm2 or >= 25 % and/or DVI fall >= 0.1 or >= 20 %; or new / one-grade worse intraprosthetic AR that is at least moderate | reference echo 30 days to 3 months after implant | needs serial echo; single-echo fallback: mean gradient >= 20 mmHg | — |
| VARC-3 stage 3 HVD (severe) | rise >= 20 mmHg resulting in >= 30 mmHg, with EOA fall >= 0.6 cm2 or >= 50 % and/or DVI fall >= 0.2 or >= 40 %; or severe AR | as above | single-echo fallback: mean gradient >= 30 mmHg or DVI < 0.25 | — |
| VARC-3 bioprosthetic valve failure stage 2 | reintervention (valve-in-valve TAVR or redo SAVR) for valve deterioration | any time | operative report or history mention of valve-in-valve / redo | — |
| EAPCI/ESC/EACTS 2017 moderate SVD | mean gradient 20-40 mmHg or rise 10-20 mmHg, or moderate AR | from baseline | — | — |
| EAPCI/ESC/EACTS 2017 severe SVD | mean gradient >= 40 mmHg or rise >= 20 mmHg, or severe AR | from baseline | — | — |
| Exclusions (non-structural) | endocarditis, valve thrombosis, isolated paravalvular leak, isolated patient-prosthesis mismatch | — | flagged separately in events | — |

## Why a single-echo fallback is listed

VARC-3 stage 2/3 haemodynamic valve deterioration is defined as a **rise** from a reference
echo taken 30 days to 3 months after implant. The prototype extract does not contain serial
echoes (see `data_plan.md`, section 3), so the rise cannot be computed. The fallback applies
the absolute-threshold arm of the same definition to a single measurement. This is weaker and
must be declared as such wherever a label built this way is used.
