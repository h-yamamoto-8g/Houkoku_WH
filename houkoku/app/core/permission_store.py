"""Department x sample permission mapping and data splitting.

Uses ``valid_sample_set_code`` (VSSET_xxxx) as the stable matching key
between CSV data and department permission config.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from app.core.config_store import Department


# ---------- Data Models ----------


@dataclass
class DepartmentSummary:
    """Summary of data destined for a single department."""

    dept_id: str
    dept_name: str
    folder_name: str
    sample_count: int
    sample_codes: list[str]


# ---------- Public API ----------


def split_by_department(
    df: pd.DataFrame,
    departments: list[Department],
    report_id: str,
) -> dict[str, pd.DataFrame]:
    """Split a filtered DataFrame by department permissions.

    For each department, keeps only rows whose ``valid_sample_set_code``
    is in that department's ``allowed_samples[report_id]``.

    Args:
        df: DataFrame already filtered by report + job.
        departments: List of Department configs.
        report_id: Current report ID for permission lookup.

    Returns:
        Dict mapping dept_id -> filtered DataFrame.
    """
    result: dict[str, pd.DataFrame] = {}

    for dept in departments:
        allowed = dept.allowed_samples.get(report_id, [])
        if not allowed:
            result[dept.dept_id] = df.iloc[0:0].copy()  # empty with same columns
            continue

        mask = df["valid_sample_set_code"].isin(allowed)
        result[dept.dept_id] = df[mask].copy()

    return result


def filter_trend_data(
    df: pd.DataFrame,
    department: Department,
    report_id: str,
) -> pd.DataFrame:
    """Extract trend data for a department (for graph use).

    Filters by:
      1. valid_sample_set_code in department's allowed_samples
      2. test_status == "U"

    Args:
        df: Full source DataFrame (all jobs).
        department: Department config.
        report_id: Current report ID for permission lookup.

    Returns:
        Filtered DataFrame for trend/graph use.
    """
    allowed = department.allowed_samples.get(report_id, [])
    if not allowed:
        return df.iloc[0:0].copy()

    mask = df["valid_sample_set_code"].isin(allowed)
    if "test_status" in df.columns:
        mask = mask & (df["test_status"] == "U")

    return df[mask].copy()


def compute_department_summary(
    df: pd.DataFrame,
    departments: list[Department],
    report_id: str,
) -> list[DepartmentSummary]:
    """Compute per-department sample counts for the preview panel.

    Args:
        df: DataFrame already filtered by report + job.
        departments: List of Department configs.
        report_id: Current report ID.

    Returns:
        List of DepartmentSummary, one per department.
    """
    split = split_by_department(df, departments, report_id)
    summaries: list[DepartmentSummary] = []

    for dept in departments:
        dept_df = split.get(dept.dept_id, pd.DataFrame())
        if dept_df.empty:
            codes: list[str] = []
        else:
            codes = sorted(dept_df["valid_sample_set_code"].unique().tolist())

        summaries.append(
            DepartmentSummary(
                dept_id=dept.dept_id,
                dept_name=dept.dept_name,
                folder_name=dept.folder_name,
                sample_count=len(codes),
                sample_codes=codes,
            )
        )

    return summaries
