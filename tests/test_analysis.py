import subprocess
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.analyze_code_status import load_qualtrics_workbook, prepare_survey, run_analysis


FIXTURE = Path(__file__).parent / "fixtures" / "synthetic_qualtrics_export.xlsx"


def test_workbook_loading_and_derived_columns():
    raw = load_qualtrics_workbook(FIXTURE)
    prepared = prepare_survey(raw)

    assert len(prepared.data) == 6
    assert prepared.pgy_col == "I am a:"
    assert set(prepared.data["PGY_cat"].astype(str)) == {"PGY1", "PGY2", "PGY3/4"}
    assert len(prepared.ordinal_cols) >= 6
    assert len(prepared.rank_cols) == 5
    assert len(prepared.multiselect_cols) >= 4
    assert len(prepared.free_text_cols) == 2
    assert not any("In your own words" in c for c in prepared.ordinal_cols)


def test_run_analysis_writes_expected_outputs(tmp_path):
    prepared = run_analysis(FIXTURE, tmp_path)

    assert prepared.free_text_cols
    assert (tmp_path / "tables" / "analysis_summary.csv").exists()
    assert (tmp_path / "tables" / "cmh_results_by_item.csv").exists()
    assert (tmp_path / "tables" / "tableone.xlsx").exists()
    assert (tmp_path / "figures" / "key_figure_single_answer.png").exists()
    assert (tmp_path / "figures" / "key_figure_single_answer_with_legends.png").exists()
    assert list((tmp_path / "figures").glob("heatmap_*.png"))

    summary = pd.read_csv(tmp_path / "tables" / "analysis_summary.csv")
    assert int(summary.loc[summary["metric"] == "analyzed_responses", "value"].iloc[0]) == 6
    assert int(summary.loc[summary["metric"] == "free_text_items_excluded", "value"].iloc[0]) == 2


def test_cli_smoke(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_code_status.py",
            "--input",
            str(FIXTURE),
            "--output-dir",
            str(tmp_path),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    assert "Analyzed responses: 6" in result.stdout
    assert (tmp_path / "tables" / "cmh_results_by_item.csv").exists()
