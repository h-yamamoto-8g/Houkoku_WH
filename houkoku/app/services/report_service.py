"""Report generation service.

Orchestrates CSV loading, filtering, splitting, and export.
Depends on core/ only.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

import app.config as _cfg
from app.core import loader, permission_store, file_utils
from app.core.config_store import AppConfig, Department, ReportDefinition


class ReportService:
    """Manages report data lifecycle: load -> filter -> preview -> export."""

    def __init__(self) -> None:
        self._df: Optional[pd.DataFrame] = None
        self._config: Optional[AppConfig] = None
        # Cache for report-filtered DataFrame to avoid redundant filtering
        self._report_cache_key: Optional[str] = None
        self._report_cache_df: Optional[pd.DataFrame] = None

    # ---------- Data Loading ----------

    def load_data(self) -> None:
        """Load source CSV from DATA_PATH.

        Raises:
            FileNotFoundError: If CSV path is not configured or missing.
            ValueError: If CSV has missing required columns.
        """
        csv_path = _cfg.SOURCE_CSV_PATH
        if csv_path is None:
            raise FileNotFoundError("データフォルダが設定されていません。")

        df = loader.load_source_csv(csv_path)
        missing = loader.validate_csv_columns(df)
        if missing:
            self._df = None
            raise ValueError(f"CSVに必須列が不足しています: {', '.join(missing)}")
        self._df = df
        self.invalidate_report_cache()

    @property
    def is_loaded(self) -> bool:
        return self._df is not None

    def set_config(self, config: AppConfig) -> None:
        self._config = config

    # ---------- Query ----------

    def get_report_definitions(self) -> list[ReportDefinition]:
        """Return report definitions from current config."""
        if self._config is None:
            return []
        return self._config.report_definitions

    def get_departments(self) -> list[Department]:
        """Return department list from current config."""
        if self._config is None:
            return []
        return self._config.departments

    def _get_report_filtered(self, report: ReportDefinition) -> pd.DataFrame:
        """Return report-filtered DataFrame, using cache if available."""
        if self._df is None:
            return pd.DataFrame()

        cache_key = report.report_id
        if self._report_cache_key == cache_key and self._report_cache_df is not None:
            return self._report_cache_df

        filtered = loader.filter_by_report(self._df, report.search_filters)
        self._report_cache_key = cache_key
        self._report_cache_df = filtered
        return filtered

    def invalidate_report_cache(self) -> None:
        """Clear the report filter cache (call when source data changes)."""
        self._report_cache_key = None
        self._report_cache_df = None

    def get_job_numbers(self, report: ReportDefinition) -> list[str]:
        """Get unique job numbers for a report definition.

        Args:
            report: Report definition with search_filters.

        Returns:
            Sorted list of job numbers (newest first).
        """
        filtered = self._get_report_filtered(report)
        return loader.get_unique_job_numbers(filtered)

    def preview_report(
        self, report: ReportDefinition, job_number: str
    ) -> pd.DataFrame:
        """Get filtered data for preview display.

        Args:
            report: Report definition.
            job_number: Selected job number.

        Returns:
            Filtered DataFrame.
        """
        filtered = self._get_report_filtered(report)
        return loader.filter_by_job(filtered, job_number)

    def preview_job(
        self, report: ReportDefinition, job_number: str
    ) -> tuple[pd.DataFrame, list[permission_store.DepartmentSummary]]:
        """Compute preview data and department summaries in one pass.

        Args:
            report: Report definition.
            job_number: Selected job number.

        Returns:
            Tuple of (filtered DataFrame, list of DepartmentSummary).
        """
        data = self.preview_report(report, job_number)
        summaries: list[permission_store.DepartmentSummary] = []
        if self._config is not None:
            summaries = permission_store.compute_department_summary(
                data, self._config.departments, report.report_id
            )
        return data, summaries

    def preview_departments(
        self, report: ReportDefinition, job_number: str
    ) -> list[permission_store.DepartmentSummary]:
        """Compute department distribution preview.

        Args:
            report: Report definition.
            job_number: Selected job number.

        Returns:
            List of DepartmentSummary for the preview panel.
        """
        if self._config is None:
            return []
        data = self.preview_report(report, job_number)
        return permission_store.compute_department_summary(
            data, self._config.departments, report.report_id
        )

    # ---------- Export ----------

    def export_report(
        self,
        report: ReportDefinition,
        job_number: str,
        selected_dept_ids: list[str],
        created_by: str = "",
    ) -> dict[str, Path]:
        """Export filtered CSV + conditions JSON to department folders.

        Uses history mode B: latest/ + history/{date}_{job}/

        Args:
            report: Report definition.
            job_number: Selected job number.
            selected_dept_ids: List of dept_ids to export to.
            created_by: User name for report_conditions.

        Returns:
            Dict mapping dept_id -> path to exported report_data.csv.

        Raises:
            FileNotFoundError: If REPORTS_PATH is not configured.
        """
        reports_dir = _cfg.REPORTS_PATH
        if reports_dir is None:
            raise FileNotFoundError("出力先フォルダが設定されていません。")
        if self._config is None:
            raise ValueError("設定が読み込まれていません。")

        data = self.preview_report(report, job_number)
        split = permission_store.split_by_department(
            data, self._config.departments, report.report_id
        )

        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        timestamp = now.isoformat(timespec="seconds")

        exported: dict[str, Path] = {}

        for dept in self._config.departments:
            if dept.dept_id not in selected_dept_ids:
                continue

            dept_df = split.get(dept.dept_id, pd.DataFrame())
            dept_dir = reports_dir / dept.folder_name

            # --- latest/ ---
            latest_dir = dept_dir / "latest"
            latest_dir.mkdir(parents=True, exist_ok=True)

            csv_path = latest_dir / "report_data.csv"
            csv_bytes = dept_df.to_csv(index=False).encode("utf-8-sig")
            file_utils.safe_write_bytes_with_retry(csv_path, csv_bytes)

            conditions = {
                "report_id": report.report_id,
                "report_name": report.report_name,
                "job_number": job_number,
                "protocol_name": ", ".join(
                    report.search_filters.get("protocol_name", [])
                ),
                "created_at": timestamp,
                "created_by": created_by,
                "dept_id": dept.dept_id,
                "dept_name": dept.dept_name,
                "sample_count": len(
                    dept_df["valid_sample_set_code"].unique() if not dept_df.empty else []
                ),
            }
            cond_json = json.dumps(conditions, ensure_ascii=False, indent=2)
            file_utils.safe_write_with_retry(
                latest_dir / "report_conditions.json", cond_json
            )

            # --- history/{date}_{job}/ ---
            history_dir = dept_dir / "history" / f"{date_str}_{job_number}"
            history_dir.mkdir(parents=True, exist_ok=True)
            file_utils.safe_write_bytes_with_retry(
                history_dir / "report_data.csv", csv_bytes
            )
            file_utils.safe_write_with_retry(
                history_dir / "report_conditions.json", cond_json
            )

            exported[dept.dept_id] = csv_path

        return exported
