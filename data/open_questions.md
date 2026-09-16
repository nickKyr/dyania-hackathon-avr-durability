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
| Where the private data live | Settled on 16 Sep: the extraction scripts and notebooks read the extract from `data/` inside the working tree, and `.gitignore` blocks every spreadsheet, CSV, parquet, pickle and derived table there. The earlier outside-the-repository loader was removed. Anyone adding a data path must keep it under an ignored pattern, since the fork is public. | team |
| LLM pass | Rows with extraction_confidence = low or valve_context = ambiguous could be sent to Claude with a question-and-justification prompt in the Synapsis style. Run it? | user |
