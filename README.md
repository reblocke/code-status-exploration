# code-status-exploration

[![DOI](https://img.shields.io/badge/ATS%202026-10.1093%2Fajrccm%2Faamag162.1058-blue)](https://doi.org/10.1093/ajrccm/aamag162.1058)
[![License: MIT](https://img.shields.io/badge/Code%20license-MIT-green.svg)](LICENSE)
[![Docs: CC BY 4.0](https://img.shields.io/badge/Docs%20license-CC%20BY%204.0-lightgrey.svg)](LICENSE-DOCS.md)

Survey analysis, poster materials, and reproducible public code for the ATS 2026 abstract **"C56-19 Beyond Verification: Exploring Resident Attitudes and Behaviors in Code-Status Discussions."**

## Citation And Links

- Abstract DOI: [10.1093/ajrccm/aamag162.1058](https://doi.org/10.1093/ajrccm/aamag162.1058)
- OUP record: [AJRCCM 2026 Supplement abstract](https://academic.oup.com/ajrccm/article/212/Supplement_1/aamag162.1058/8680759)
- Journal record: *American Journal of Respiratory and Critical Care Medicine*, 2026;212(Supplement_1)
- Public poster: [poster/code-status-exploration-ats-2026-poster.pdf](poster/code-status-exploration-ats-2026-poster.pdf)
- Machine-readable index: [llms.txt](llms.txt)
- Data dictionary: [data_dictionary.md](data_dictionary.md) and [data_dictionary.csv](data_dictionary.csv)

## Project Summary

This project analyzes an anonymous resident survey about code-status discussions during ICU admission. The analysis distinguishes **code-status verification** - confirming and documenting previously established goals of care - from **code-status exploration** - shared decision-making to help a patient or surrogate make a new or revised decision in light of the clinical situation.

The repository is intended to support review and reuse of the analysis approach without exposing raw survey responses. The raw Qualtrics export remains restricted because it includes response metadata and free-text resident responses.

## Authors

- Colton W. Long, MD - Department of Internal Medicine, University of Utah
- Gabrielle A. Langmann, MD - Supportive and Palliative Care Program, Division of General Internal Medicine, University of Utah
- Eliote L. Hirshberg, MD MSc - Department of Pulmonary and Critical Care Medicine, Intermountain Medical Center
- Brian W. Locke, MD MSc - Department of Pulmonary and Critical Care Medicine, Intermountain Medical Center; ORCID [0000-0002-3588-5238](https://orcid.org/0000-0002-3588-5238)

Funding and conflicts of interest were not reported in the public repository materials at the time of this readiness pass. Update this section if a final disclosure statement is supplied.

## Data Access And Privacy

The source Qualtrics workbook is not public. It should be stored locally at:

```text
data/private/resident_code_status_survey.xlsx
```

Do not commit raw survey exports, response identifiers, timestamps, free-text responses, profiling reports, local analysis outputs, or editable poster drafts. Public materials in this repository are limited to code, documentation, a sanitized poster PDF, synthetic test fixtures, and aggregate outputs generated from synthetic data.

## Repository Contents

| Path | Purpose |
| --- | --- |
| `scripts/analyze_code_status.py` | Repo-root runnable Python analysis script derived from the original notebook workflow. |
| `ats_abstract_tables.ipynb` | Optional stripped notebook wrapper for interactive use. |
| `tests/fixtures/synthetic_qualtrics_export.xlsx` | No-respondent synthetic workbook for smoke tests. |
| `tests/test_analysis.py` | Tests for workbook loading, derived variables, free-text exclusion, and output creation. |
| `poster/` | Sanitized, flattened public ATS poster PDF. |
| `data_dictionary.*` | Machine-readable and human-readable schema documentation. |
| `llms.txt` | Machine-readable project index and future-agent cautions. |

## Reproducing The Analysis

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Run the analysis with a local restricted workbook:

```bash
python scripts/analyze_code_status.py \
  --input data/private/resident_code_status_survey.xlsx \
  --output-dir outputs/analysis
```

Run the synthetic no-respondent smoke test:

```bash
python scripts/analyze_code_status.py \
  --input tests/fixtures/synthetic_qualtrics_export.xlsx \
  --output-dir /tmp/code-status-smoke
```

Expected generated outputs include:

- `tables/cmh_results_by_item.csv`
- `tables/tableone.xlsx` when `tableone` is available
- `figures/key_figure_single_answer.png`
- `figures/key_figure_single_answer_with_legends.png`
- `figures/heatmap_*.png`

Generated outputs belong under ignored `outputs/` paths and should not be committed unless they are deliberately curated, aggregate, and privacy-reviewed.

## Dependencies

| Runtime | Purpose |
| --- | --- |
| Python 3.11+ | Analysis and test runtime. |
| `pandas`, `numpy`, `scipy`, `statsmodels` | Survey cleaning, ordinal summaries, and CMH-style trend tests. |
| `matplotlib` | Figures. |
| `openpyxl` | Excel input/output. |
| `tableone` | Optional descriptive table export. |
| `pytest`, `PyYAML` | Development checks. |

The historical Conda environment is preserved in `environment.yml`, but the canonical lightweight install path for this public-ready repository is `requirements.txt`.

## Citation

Please cite the ATS abstract and repository metadata in [CITATION.cff](CITATION.cff). BibTeX for the abstract:

```bibtex
@article{long2026code_status_exploration,
  title = {C56-19 Beyond Verification: Exploring Resident Attitudes and Behaviors in Code-Status Discussions},
  author = {Long, Colton W. and Langmann, Gabrielle A. and Hirshberg, Eliote L. and Locke, Brian W.},
  journal = {American Journal of Respiratory and Critical Care Medicine},
  volume = {212},
  issue = {Supplement_1},
  year = {2026},
  doi = {10.1093/ajrccm/aamag162.1058}
}
```

## License

Code is released under the [MIT License](LICENSE). Author-owned documentation and the sanitized poster PDF are released under [CC BY 4.0](LICENSE-DOCS.md). Restricted survey exports, free-text responses, respondent metadata, and third-party or publisher material are excluded from these licenses.

## Contact

For repository questions, open a GitHub issue after public release or contact Brian W. Locke through the profile linked from this repository.
