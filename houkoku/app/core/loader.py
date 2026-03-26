"""CSV loading, validation, and filtering.

Reads the normalized bunseki.csv (51 columns) and provides
filter/query functions for report generation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd


# ---------- CSV Loading ----------


def load_source_csv(path: Path) -> pd.DataFrame:
    """Load source CSV with encoding detection (utf-8 -> cp932 fallback).

    Args:
        path: Path to CSV file.

    Returns:
        DataFrame with all columns.

    Raises:
        FileNotFoundError: If CSV does not exist.
        ValueError: If CSV cannot be parsed.
    """
    if not path.exists():
        raise FileNotFoundError(f"元データCSVが見つかりません: {path}")

    for encoding in ("utf-8", "cp932", "shift_jis"):
        try:
            df = pd.read_csv(path, encoding=encoding, dtype=str, keep_default_na=False)
            _fix_garbled_unit_names(df)
            return df
        except UnicodeDecodeError:
            continue

    raise ValueError(f"CSVのエンコーディングを検出できません: {path}")


# ---------- Garbled text repair ----------

# ETL段階でCP932→UTF-8変換時に壊れた単位名の修復マッピング
# test_unit_code をキーに正しい test_unit_name を復元する
_UNIT_NAME_FIX: dict[str, str] = {
    "GC": "°C",
    "ug/L": "μg/L",
}


def _fix_garbled_unit_names(df: pd.DataFrame) -> None:
    """Repair garbled test_unit_name values using test_unit_code mapping."""
    if "test_unit_name" not in df.columns or "test_unit_code" not in df.columns:
        return
    for code, correct_name in _UNIT_NAME_FIX.items():
        mask = df["test_unit_code"] == code
        df.loc[mask, "test_unit_name"] = correct_name


# ---------- Validation ----------


REQUIRED_COLUMNS = [
    "sample_job_number",
    "request_protocol",
    "valid_sample_set_code",
    "sample_code",
    "sample_name",
]


def validate_csv_columns(df: pd.DataFrame, required: Optional[list[str]] = None) -> list[str]:
    """Check that required columns exist in the DataFrame.

    Args:
        df: Source DataFrame.
        required: Column names to check. Defaults to REQUIRED_COLUMNS.

    Returns:
        List of missing column names (empty if all present).
    """
    if required is None:
        required = REQUIRED_COLUMNS
    return [col for col in required if col not in df.columns]


# ---------- Filtering ----------


def filter_by_report(df: pd.DataFrame, search_filters: dict[str, list[str]]) -> pd.DataFrame:
    """Filter DataFrame by report search filters.

    Uses the ``request_protocol`` column to match protocol names
    defined in the report's search_filters.

    Args:
        df: Source DataFrame.
        search_filters: e.g. {"protocol_name": ["水質分析プロトコルA"]}

    Returns:
        Filtered DataFrame.
    """
    protocol_names = search_filters.get("protocol_name", [])
    if not protocol_names:
        return df

    if "request_protocol" not in df.columns:
        return pd.DataFrame(columns=df.columns)

    mask = df["request_protocol"].isin(protocol_names)
    return df[mask].copy()


def get_unique_job_numbers(df: pd.DataFrame) -> list[str]:
    """Extract unique job numbers from a (pre-filtered) DataFrame.

    Args:
        df: DataFrame (typically already filtered by report).

    Returns:
        Sorted list of unique job numbers (descending for newest first).
    """
    if "sample_job_number" not in df.columns:
        return []
    jobs = df["sample_job_number"].dropna().unique().tolist()
    return sorted(jobs, reverse=True)


def filter_by_job(df: pd.DataFrame, job_number: str) -> pd.DataFrame:
    """Filter DataFrame by a specific job number.

    Args:
        df: Source DataFrame.
        job_number: Value to match in sample_job_number column.

    Returns:
        Filtered DataFrame.
    """
    if "sample_job_number" not in df.columns:
        return pd.DataFrame(columns=df.columns)
    return df[df["sample_job_number"] == job_number].copy()
