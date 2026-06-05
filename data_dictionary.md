# Data Dictionary

This dictionary documents the restricted Qualtrics source export, derived analysis variables, and aggregate outputs for the code-status exploration survey analysis. It does not include respondent-level data.

Machine-readable CSV: [data_dictionary.csv](data_dictionary.csv)

## Source Data Boundary

The source workbook is a restricted Qualtrics export expected at `data/private/resident_code_status_survey.xlsx`. It contains respondent metadata, timestamps, and two free-text response items. These fields are documented for reproducibility but must not be committed or published.

## Key Variable Families

- Qualtrics metadata: start/end dates, recorded date, response ID, distribution channel, language, progress, completion status, and duration.
- Survey items: code-status exploration frequency by ICU admission context, perceived ideal frequency, time pressure, confidence, patient/surrogate understanding, perceived expectation to explore, provisional code-status use, training beliefs, ranked conversation topics, prior training, intervention preferences, and PGY category.
- Restricted free text: open-ended challenges and requested skills.
- Derived analysis variables: `PGY_cat`, ordered Likert items, ordered rank items, multi-select indicator columns, TableOne inputs, CMH trend-test outputs, and generated aggregate figures/tables.

## Review Flags

Rows marked `needs_review` have definitions inferred from the current survey export or analysis script and should be checked against the final survey instrument before reuse.
