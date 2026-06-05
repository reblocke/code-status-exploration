# AGENTS

## Repository Rules

- This repository is being prepared for public release. Treat respondent-level survey exports, timestamps, response identifiers, and free-text responses as restricted even when the survey was anonymous.
- Do not commit files under `data/` or `Data/`, Qualtrics exports, generated profiling reports, notebook output blobs, local plot folders, or editable PPTX/DOCX drafts.
- Keep the public scholarly framing limited to the ATS 2026 abstract DOI `10.1093/ajrccm/aamag162.1058` unless a later manuscript or publication record is supplied.
- Use concise original summaries and links. Do not mirror publisher abstract text.

## Analysis Workflow

- Canonical command:
  `python scripts/analyze_code_status.py --input data/private/resident_code_status_survey.xlsx --output-dir outputs/analysis`
- Synthetic smoke command:
  `python scripts/analyze_code_status.py --input tests/fixtures/synthetic_qualtrics_export.xlsx --output-dir /tmp/code-status-smoke`
- Generated figures and tables belong under ignored `outputs/` paths.
- Keep `ats_abstract_tables.ipynb` stripped of outputs. Prefer updating shared logic in `scripts/analyze_code_status.py`.

## Required Checks

- Validate `CITATION.cff` with `cffconvert` or a YAML parse.
- Run `python -m pytest`.
- Run the synthetic smoke command.
- Run `git diff --check`.
- Search for raw survey artifacts, hard-coded local paths, notebook output blobs, and overclaimed publication metadata before public release.
