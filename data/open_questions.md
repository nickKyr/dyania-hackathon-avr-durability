# Open Questions — Data and Label Construction

Decisions that change what the labels mean, listed with the person who owns the decision.
Nothing here is settled.

| topic | question | decision owner |
|---|---|---|
| Failure definition | Adopt VARC-3 stage 2/3 HVD plus BVF stage 2 as primary? Single-echo fallback thresholds when no baseline echo exists? | team |
| Native vs prosthetic gradients | The valve_context rule uses the surrounding sentence. Please spot-check 20 rows in echo_values where valve_context is ambiguous or unknown. | clinician |
| Valve name redaction | In some TAVR reports the device name was replaced by [NAME]; model is then inferred from S3 / Ultra / Evolut tokens or left blank. Accept inference? | team |
| Deleted operative reports | 9 operative reports are marked Deleted. They are kept in implants with signed_status but excluded from the patient-level index operation. Confirm. | team |
| Group B implant year | For the 17 lab/med patients the implant year comes from anaesthetic or protamine orders. Some patients have several such years; the earliest is used. Confirm or override per patient. | clinician |
| Two operations per patient | 10 patients have two operative reports and one has three; the first AVR-type report is used as the index operation and later ones appear in implants. Should a later valve-in-valve count as the outcome for the first implant? | team |
| Age and sex | Age is redacted everywhere; sex is inferred from pronouns. Use sex_hint or drop it? | team |
| Where the private data live | The extraction scripts resolve data as `data/` **inside** the repository, protected only by `.gitignore`; `notebooks/data_paths.py` resolves it **outside** and refuses any path inside the repository. Both work, but only one can be the convention, and until it is settled each half of the pipeline looks for the files somewhere the other half does not put them. Two data files have already been found sitting in the repository root during this event, and the fork is public. | team |
| LLM pass | Rows with extraction_confidence = low or valve_context = ambiguous could be sent to Claude with a question-and-justification prompt in the Synapsis style. Run it? | user |
