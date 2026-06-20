#!/usr/bin/env python3
"""Path-safe analysis workflow for the code-status exploration survey."""

from __future__ import annotations

import argparse
import math
import re
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pandas.api.types import CategoricalDtype
from scipy.stats import chi2
from statsmodels.stats.multitest import multipletests


PGY_LEVELS = ["PGY1", "PGY2", "PGY3/4"]
METADATA_LABELS = {
    "start date",
    "end date",
    "response type",
    "progress",
    "duration (in seconds)",
    "finished",
    "recorded date",
    "response id",
    "distribution channel",
    "user language",
}
FREE_TEXT_HINTS = ("in your own words", "free-text", "free text", "_text")
MULTISELECT_HINTS = ("select all", "select as many", "as many as you want")
RANK_HINTS = ("prioritize from 1", "highest priority", "lowest priority")

LIKERT_TEMPLATES = {
    "FREQ5": ["Never", "Rarely", "Sometimes", "Often", "Always"],
    "FREQ4": ["Never", "Rarely", "Sometimes", "Often"],
    "AGREE5": ["Strongly disagree", "Disagree", "Neutral", "Agree", "Strongly agree"],
    "CONF5": [
        "None",
        "Slightly confident",
        "Somewhat confident",
        "Very confident",
        "Extremely confident",
    ],
    "CONF4": ["None", "Slightly confident", "Somewhat confident", "Very confident"],
}

LIKERT_CANON = {
    "never": "Never",
    "rarely": "Rarely",
    "sometimes": "Sometimes",
    "often": "Often",
    "always": "Always",
    "strongly disagree": "Strongly disagree",
    "disagree": "Disagree",
    "neither agree nor disagree": "Neutral",
    "neutral": "Neutral",
    "agree": "Agree",
    "strongly agree": "Strongly agree",
    "none": "None",
    "no confidence": "None",
    "not confident": "None",
    "not at all confident": "None",
    "slightly confident": "Slightly confident",
    "somewhat confident": "Somewhat confident",
    "very confident": "Very confident",
    "extremely confident": "Extremely confident",
}


@dataclass
class PreparedSurvey:
    data: pd.DataFrame
    pgy_col: str
    free_text_cols: list[str]
    ordinal_cols: list[str]
    multiselect_cols: list[str]
    rank_cols: list[str]


def fix_mojibake(value: object) -> object:
    """Normalize common Qualtrics/Excel encoding artifacts."""
    if not isinstance(value, str):
        return value
    replacements = {
        "‚Äô": "'",
        "‚Äú": '"',
        "‚Äù": '"',
        "â€“": "-",
        "â€”": "-",
        "Â": "",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    return re.sub(r"\s+", " ", value).strip()


def load_qualtrics_workbook(path: Path) -> pd.DataFrame:
    """Read the Qualtrics export using question text as column labels."""
    df = pd.read_excel(path, header=1, dtype="object")
    if not df.empty and df.iloc[0].astype(str).str.contains("ImportId", na=False).any():
        df = df.iloc[1:].reset_index(drop=True)
    df.columns = [str(fix_mojibake(c)) for c in df.columns]
    if hasattr(df, "map"):
        return df.map(fix_mojibake)
    return df.applymap(fix_mojibake)


def normalize_pgy(value: object) -> str:
    if not isinstance(value, str):
        return "Other"
    normalized = value.strip().lower()
    if any(token in normalized for token in ("pgy1", "pgy 1", "pgy-1", "intern")):
        return "PGY1"
    if any(token in normalized for token in ("pgy2", "pgy 2", "pgy-2")):
        return "PGY2"
    if any(
        token in normalized
        for token in ("pgy3/4", "pgy3", "pgy 3", "pgy-3", "pgy4", "pgy 4", "pgy-4")
    ):
        return "PGY3/4"
    return "Other"


def find_pgy_col(columns: Iterable[str]) -> str:
    candidates = [c for c in columns if "i am a" in c.lower() or "[qid29]" in c.lower()]
    if not candidates:
        raise ValueError("Could not find PGY column; expected an 'I am a:' survey item.")
    return candidates[0]


def is_metadata_col(name: str) -> bool:
    return name.strip().lower() in METADATA_LABELS


def is_free_text_col(name: str, series: pd.Series) -> bool:
    normalized = name.lower()
    if any(hint in normalized for hint in FREE_TEXT_HINTS):
        return True
    non_missing = series.dropna().astype(str)
    if non_missing.empty:
        return False
    long_values = non_missing.str.len().median() > 40
    mostly_unique = non_missing.nunique(dropna=True) / max(len(non_missing), 1) > 0.75
    return bool(long_values and mostly_unique)


def header_says_multiselect(name: str) -> bool:
    return any(hint in name.lower() for hint in MULTISELECT_HINTS)


def header_says_rank(name: str) -> bool:
    return any(hint in name.lower() for hint in RANK_HINTS)


def coerce_likert(series: pd.Series) -> pd.Series | None:
    values = series.where(series.notna(), np.nan).astype(str).str.strip()
    values = values.replace({"nan": np.nan, "None": np.nan, "": np.nan})
    mapped = values.str.lower().map(LIKERT_CANON).fillna(values)
    observed = set(mapped.dropna().unique().tolist())
    best_order: list[str] | None = None
    best_score = 0
    for order in LIKERT_TEMPLATES.values():
        score = len(observed.intersection(order))
        if score > best_score or (score == best_score and best_order and len(order) < len(best_order)):
            best_order = order
            best_score = score
    if best_order is None or best_score == 0:
        return None
    dtype = CategoricalDtype(categories=best_order, ordered=True)
    return mapped.where(mapped.isin(best_order), np.nan).astype(dtype)


def coerce_rank(series: pd.Series) -> pd.Series | None:
    values = series.where(series.notna(), np.nan).astype(str).str.extract(r"([1-4])", expand=False)
    if values.notna().sum() == 0:
        return None
    dtype = CategoricalDtype(categories=["1", "2", "3", "4"], ordered=True)
    return values.astype(dtype)


def split_multiselect(value: object) -> list[str]:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return []
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return []
    delimiter = ";" if ";" in text else ","
    return [part.strip() for part in text.split(delimiter) if part.strip()]


def expand_multiselect_column(df: pd.DataFrame, col: str) -> list[str]:
    options = sorted({option for value in df[col] for option in split_multiselect(value)})
    new_cols: list[str] = []
    for option in options:
        safe_option = re.sub(r"\s+", " ", option).strip()
        new_name = f"{col} - {safe_option}"
        selected = df[col].map(lambda value, opt=option: opt in split_multiselect(value))
        dtype = CategoricalDtype(categories=["Not selected", "Selected"], ordered=False)
        df[new_name] = np.where(selected, "Selected", "Not selected").astype("object")
        df[new_name] = df[new_name].astype(dtype)
        new_cols.append(new_name)
    return new_cols


def prepare_survey(df: pd.DataFrame) -> PreparedSurvey:
    pgy_col = find_pgy_col(df.columns)
    df = df.copy()
    df["PGY_cat"] = df[pgy_col].map(normalize_pgy).astype(
        CategoricalDtype(categories=PGY_LEVELS, ordered=True)
    )
    df = df[df["PGY_cat"].isin(PGY_LEVELS)].copy()

    free_text_cols: list[str] = []
    ordinal_cols: list[str] = []
    multiselect_cols: list[str] = []
    rank_cols: list[str] = []

    for col in list(df.columns):
        if col in {"PGY_cat", pgy_col} or is_metadata_col(col):
            continue
        if header_says_multiselect(col):
            multiselect_cols.extend(expand_multiselect_column(df, col))
            continue
        if is_free_text_col(col, df[col]):
            free_text_cols.append(col)
            continue
        if header_says_rank(col):
            coerced_rank = coerce_rank(df[col])
            if coerced_rank is not None:
                df[col] = coerced_rank
                rank_cols.append(col)
            continue
        coerced = coerce_likert(df[col])
        if coerced is not None:
            df[col] = coerced
            ordinal_cols.append(col)

    return PreparedSurvey(
        data=df,
        pgy_col=pgy_col,
        free_text_cols=free_text_cols,
        ordinal_cols=ordinal_cols,
        multiselect_cols=multiselect_cols,
        rank_cols=rank_cols,
    )


def percent_matrix(series: pd.Series, group: pd.Series, row_order: list[str] | None = None):
    counts = pd.crosstab(series, group, dropna=False).reindex(columns=PGY_LEVELS, fill_value=0)
    if row_order is not None:
        counts = counts.reindex(row_order, fill_value=0)
    percent = counts.div(counts.sum(axis=0).replace(0, np.nan), axis=1).mul(100)
    return percent.fillna(0), counts.fillna(0)


def save_heatmap(series: pd.Series, group: pd.Series, title: str, path: Path) -> None:
    order = list(series.cat.categories) if isinstance(series.dtype, CategoricalDtype) else None
    percent, counts = percent_matrix(series, group, row_order=order)
    height = max(2.4, 1.4 + 0.34 * max(1, percent.shape[0]))
    fig, ax = plt.subplots(figsize=(8.8, height))
    image = ax.imshow(percent.values, aspect="auto", vmin=0, vmax=100, cmap="Blues")
    ax.set_xticks(np.arange(len(percent.columns)))
    ax.set_xticklabels(percent.columns)
    ax.set_yticks(np.arange(len(percent.index)))
    ax.set_yticklabels(percent.index)
    ax.set_title(textwrap.fill(title, width=78), fontsize=10)
    for i in range(percent.shape[0]):
        for j in range(percent.shape[1]):
            ax.text(j, i, f"{percent.iloc[i, j]:.0f}%\n(n={int(counts.iloc[i, j])})",
                    ha="center", va="center", fontsize=7)
    fig.colorbar(image, ax=ax, label="Column percent")
    fig.tight_layout()
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def cmh_linear_by_linear(series: pd.Series, group: pd.Series) -> float | None:
    if not isinstance(series.dtype, CategoricalDtype) or not series.dtype.ordered:
        return None
    tab = (
        pd.crosstab(series, group, dropna=False)
        .reindex(index=list(series.cat.categories), columns=PGY_LEVELS, fill_value=0)
        .values
    )
    tab = tab[tab.sum(axis=1) > 0][:, tab.sum(axis=0) > 0]
    n = tab.sum()
    if n == 0 or tab.shape[0] < 2 or tab.shape[1] < 2:
        return None
    rows, cols = tab.shape
    row_scores = np.arange(1, rows + 1, dtype=float)
    col_scores = np.arange(1, cols + 1, dtype=float)
    row_totals = tab.sum(axis=1)
    col_totals = tab.sum(axis=0)
    row_mean = (row_scores * row_totals).sum() / n
    col_mean = (col_scores * col_totals).sum() / n
    numerator = (((row_scores[:, None] - row_mean) * (col_scores[None, :] - col_mean)) * tab).sum()
    row_var = (((row_scores - row_mean) ** 2) * row_totals).sum()
    col_var = (((col_scores - col_mean) ** 2) * col_totals).sum()
    if row_var <= 0 or col_var <= 0:
        return None
    statistic = (n * (numerator ** 2)) / (row_var * col_var)
    return float(chi2.sf(statistic, df=1))


def build_cmh_results(prepared: PreparedSurvey) -> pd.DataFrame:
    rows = []
    for col in [*prepared.ordinal_cols, *prepared.rank_cols]:
        p_value = cmh_linear_by_linear(prepared.data[col], prepared.data["PGY_cat"])
        rows.append(
            {
                "Item": col,
                "N": int(prepared.data[[col, "PGY_cat"]].dropna().shape[0]),
                "Levels": int(prepared.data[col].nunique(dropna=True)),
                "p": p_value,
            }
        )
    results = pd.DataFrame(rows)
    if not results.empty:
        mask = results["p"].notna()
        if mask.any():
            results.loc[mask, "q_BH"] = multipletests(results.loc[mask, "p"], method="fdr_bh")[1]
        results["p_fmt"] = results["p"].apply(lambda x: f"{x:.3g}" if pd.notna(x) else "NA")
        results["q_fmt"] = results["q_BH"].apply(lambda x: f"{x:.3g}" if pd.notna(x) else "NA")
    return results


def write_tableone(prepared: PreparedSurvey, path: Path) -> None:
    cols = [*prepared.ordinal_cols, *prepared.rank_cols, *prepared.multiselect_cols, "PGY_cat"]
    table_df = prepared.data[cols].copy()
    try:
        from tableone import TableOne

        table = TableOne(
            data=table_df,
            columns=[c for c in cols if c != "PGY_cat"],
            groupby="PGY_cat",
            categorical=[c for c in cols if c != "PGY_cat"],
            pval=True,
            overall=True,
            missing=False,
        )
        table.to_excel(path)
    except Exception:
        summaries = []
        for col in [c for c in cols if c != "PGY_cat"]:
            counts = pd.crosstab(table_df[col], table_df["PGY_cat"]).reindex(columns=PGY_LEVELS, fill_value=0)
            summaries.append(counts.assign(item=col).reset_index(names="level"))
        fallback = pd.concat(summaries, ignore_index=True) if summaries else pd.DataFrame()
        fallback.to_excel(path, index=False)


def save_single_answer_plot(
    prepared: PreparedSurvey,
    path: Path,
    *,
    with_legends: bool = False,
) -> None:
    cols = prepared.ordinal_cols
    if not cols:
        return
    labels = [re.sub(r"\s+", " ", c).strip() for c in cols]
    fig_height = max(3.5, 0.55 * len(cols))
    fig, axes = plt.subplots(len(cols), 1, figsize=(10, fig_height), sharex=True)
    if len(cols) == 1:
        axes = [axes]
    palette = plt.get_cmap("viridis")
    for ax, col, label in zip(axes, cols, labels):
        order = list(prepared.data[col].cat.categories)
        counts = prepared.data[col].value_counts(normalize=True).reindex(order, fill_value=0).mul(100)
        left = 0.0
        handles = []
        for idx, (level, pct) in enumerate(counts.items()):
            color = palette((idx + 1) / (len(order) + 1))
            ax.barh([0], [pct], left=left, color=color, edgecolor="white", height=0.62)
            if pct >= 9:
                ax.text(left + pct / 2, 0, f"{pct:.0f}%", ha="center", va="center", fontsize=8)
            handles.append(plt.Rectangle((0, 0), 1, 1, color=color, label=level))
            left += pct
        ax.set_yticks([0])
        ax.set_yticklabels([textwrap.fill(label, width=70)], fontsize=8)
        ax.set_xlim(0, 100)
        ax.grid(axis="x", color="#dddddd", linewidth=0.5)
        if with_legends:
            ax.legend(handles=handles, loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=7)
    axes[-1].set_xlabel("Percent of analyzed responses")
    fig.tight_layout()
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def run_analysis(input_path: Path, output_dir: Path) -> PreparedSurvey:
    tables_dir = output_dir / "tables"
    figures_dir = output_dir / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    raw_df = load_qualtrics_workbook(input_path)
    prepared = prepare_survey(raw_df)

    summary = pd.DataFrame(
        [
            {"metric": "analyzed_responses", "value": int(len(prepared.data))},
            {"metric": "ordinal_items", "value": int(len(prepared.ordinal_cols))},
            {"metric": "rank_items", "value": int(len(prepared.rank_cols))},
            {"metric": "multiselect_indicators", "value": int(len(prepared.multiselect_cols))},
            {"metric": "free_text_items_excluded", "value": int(len(prepared.free_text_cols))},
        ]
    )
    summary.to_csv(tables_dir / "analysis_summary.csv", index=False)

    cmh = build_cmh_results(prepared)
    cmh.to_csv(tables_dir / "cmh_results_by_item.csv", index=False)
    write_tableone(prepared, tables_dir / "tableone.xlsx")

    for col in [*prepared.ordinal_cols, *prepared.rank_cols, *prepared.multiselect_cols]:
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", col).strip("_")[:120]
        save_heatmap(prepared.data[col], prepared.data["PGY_cat"], col, figures_dir / f"heatmap_{safe}.png")

    save_single_answer_plot(prepared, figures_dir / "key_figure_single_answer.png")
    save_single_answer_plot(
        prepared,
        figures_dir / "key_figure_single_answer_with_legends.png",
        with_legends=True,
    )
    return prepared


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Local Qualtrics workbook.")
    parser.add_argument("--output-dir", required=True, type=Path, help="Output directory for generated files.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.input.exists():
        raise SystemExit(f"Missing restricted input workbook: {args.input}")
    prepared = run_analysis(args.input, args.output_dir)
    print(f"Analyzed responses: {len(prepared.data)}")
    print(f"Excluded free-text items: {len(prepared.free_text_cols)}")
    print(f"Wrote outputs under: {args.output_dir}")


if __name__ == "__main__":
    main()
