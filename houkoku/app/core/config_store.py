"""config.json read/write for shared application configuration.

config.json lives in DATA_PATH/config/ (SharePoint-synced).
Stores report definitions and department permission mappings.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

import app.config as _cfg


# ---------- Data Models ----------


@dataclass
class ReportDefinition:
    """A single report type with its search filters."""

    report_id: str = ""
    report_name: str = ""
    search_filters: dict[str, list[str]] = field(default_factory=dict)
    description: str = ""


@dataclass
class Department:
    """A department with per-report sample permissions."""

    dept_id: str = ""
    dept_name: str = ""
    folder_name: str = ""
    allowed_samples: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class ColumnSetting:
    """A single column display configuration."""

    column_key: str = ""
    display_name: str = ""
    visible: bool = True


# Default column settings — matches bunseki.csv column order (all 51 columns visible)
DEFAULT_COLUMN_SETTINGS: list[ColumnSetting] = [
    ColumnSetting("sample_request_number", "依頼番号"),
    ColumnSetting("sample_sampling_date", "採取日"),
    ColumnSetting("sample_sampling_date_sample", "採取日（サンプル）"),
    ColumnSetting("sample_measurement_date", "測定日"),
    ColumnSetting("sample_job_number", "JOB番号"),
    ColumnSetting("sample_job_branch_number", "JOB枝番"),
    ColumnSetting("sample_protocol_name", "プロトコル名（サンプル）"),
    ColumnSetting("sample_code", "サンプルコード"),
    ColumnSetting("sample_name", "サンプル名"),
    ColumnSetting("sample_material_or_facility_name", "物質/施設名"),
    ColumnSetting("holder_code", "保持者コード"),
    ColumnSetting("holder_name", "保持者名"),
    ColumnSetting("test_code", "テストコード"),
    ColumnSetting("test_name", "テスト名"),
    ColumnSetting("test_raw_data", "生データ"),
    ColumnSetting("test_reported_data", "報告データ"),
    ColumnSetting("test_unit_code", "単位コード"),
    ColumnSetting("test_unit_name", "単位"),
    ColumnSetting("test_upper_limit_spec_1", "上限規格1"),
    ColumnSetting("test_upper_limit_spec_2", "上限規格2"),
    ColumnSetting("test_upper_limit_spec_3", "上限規格3"),
    ColumnSetting("test_upper_limit_spec_4", "上限規格4"),
    ColumnSetting("test_lower_limit_spec_1", "下限規格1"),
    ColumnSetting("test_lower_limit_spec_2", "下限規格2"),
    ColumnSetting("test_lower_limit_spec_3", "下限規格3"),
    ColumnSetting("test_lower_limit_spec_4", "下限規格4"),
    ColumnSetting("test_upper_quantitation_limit", "定量上限"),
    ColumnSetting("test_lower_quantitation_limit", "定量下限"),
    ColumnSetting("sample_requester", "依頼者"),
    ColumnSetting("sample_approver", "承認者"),
    ColumnSetting("sample_approver_name", "承認者名"),
    ColumnSetting("sample_overall_judge", "総合判定"),
    ColumnSetting("sample_overall_judge_name", "総合判定名"),
    ColumnSetting("sample_status", "サンプルステータス"),
    ColumnSetting("test_status", "テストステータス"),
    ColumnSetting("test_grade_code", "グレードコード"),
    ColumnSetting("sample_out_of_spec_flag", "規格外フラグ"),
    ColumnSetting("test_judgment", "テスト判定"),
    ColumnSetting("test_hidden_flag", "非表示フラグ"),
    ColumnSetting("test_report_value_flag", "報告値フラグ"),
    ColumnSetting("valid_sample_set_code", "サンプルセットコード"),
    ColumnSetting("valid_sample_display_name", "サンプル表示名"),
    ColumnSetting("valid_holder_set_code", "保持者セットコード"),
    ColumnSetting("valid_holder_display_name", "保持者表示名"),
    ColumnSetting("valid_test_set_code", "テストセットコード"),
    ColumnSetting("valid_test_display_name", "テスト表示名"),
    ColumnSetting("holder_group_code", "保持者グループコード"),
    ColumnSetting("trend_enabled", "トレンド有効"),
    ColumnSetting("test_domain_code", "テストドメインコード"),
    ColumnSetting("request_protocol_name", "依頼プロトコル名"),
    ColumnSetting("request_protocol_code", "依頼プロトコルコード"),
]


@dataclass
class AppConfig:
    """Top-level application configuration."""

    version: str = "1.0"
    sharepoint_paths: dict[str, str] = field(default_factory=dict)
    report_definitions: list[ReportDefinition] = field(default_factory=list)
    departments: list[Department] = field(default_factory=list)
    column_settings: list[ColumnSetting] = field(default_factory=list)


# ---------- Serialization helpers ----------


def _config_path() -> Path:
    """Resolve config.json path (lazy, reads latest DATA_PATH)."""
    config_dir = _cfg.CONFIG_DIR_PATH
    if config_dir is None:
        raise FileNotFoundError("DATA_PATH が設定されていません。設定画面からデータフォルダを指定してください。")
    return config_dir / "config.json"


def _report_def_from_dict(d: dict) -> ReportDefinition:
    return ReportDefinition(
        report_id=d.get("report_id", ""),
        report_name=d.get("report_name", ""),
        search_filters=d.get("search_filters", {}),
        description=d.get("description", ""),
    )


def _department_from_dict(d: dict) -> Department:
    return Department(
        dept_id=d.get("dept_id", ""),
        dept_name=d.get("dept_name", ""),
        folder_name=d.get("folder_name", ""),
        allowed_samples=d.get("allowed_samples", {}),
    )


def _column_setting_from_dict(d: dict) -> ColumnSetting:
    return ColumnSetting(
        column_key=d.get("column_key", ""),
        display_name=d.get("display_name", ""),
        visible=d.get("visible", True),
    )


# ---------- Public API ----------


def load_config() -> AppConfig:
    """Load config.json from shared config directory.

    Returns:
        Parsed AppConfig. Creates default if file doesn't exist.
    """
    path = _config_path()
    if not path.exists():
        cfg = create_default_config()
        save_config(cfg)
        return cfg

    raw = json.loads(path.read_text(encoding="utf-8"))
    column_settings = [
        _column_setting_from_dict(c) for c in raw.get("column_settings", [])
    ]
    # If no column_settings saved yet, use defaults
    if not column_settings:
        column_settings = [ColumnSetting(c.column_key, c.display_name, c.visible) for c in DEFAULT_COLUMN_SETTINGS]
    return AppConfig(
        version=raw.get("version", "1.0"),
        sharepoint_paths=raw.get("sharepoint_paths", {}),
        report_definitions=[
            _report_def_from_dict(r) for r in raw.get("report_definitions", [])
        ],
        departments=[_department_from_dict(d) for d in raw.get("departments", [])],
        column_settings=column_settings,
    )


def save_config(config: AppConfig) -> None:
    """Persist config to config.json (ensure_ascii=False, indent=2)."""
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "version": config.version,
        "sharepoint_paths": config.sharepoint_paths,
        "report_definitions": [asdict(r) for r in config.report_definitions],
        "departments": [asdict(d) for d in config.departments],
        "column_settings": [asdict(c) for c in config.column_settings],
    }
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def validate_config(config: AppConfig) -> list[str]:
    """Validate config and return list of warning messages."""
    warnings: list[str] = []

    if not config.report_definitions:
        warnings.append("報告書定義が空です。設定画面から報告書を追加してください。")

    if not config.departments:
        warnings.append("部署定義が空です。設定画面から部署を追加してください。")

    report_ids = {r.report_id for r in config.report_definitions}
    for dept in config.departments:
        for rid in dept.allowed_samples:
            if rid not in report_ids:
                warnings.append(
                    f"部署「{dept.dept_name}」の権限に存在しない報告書ID「{rid}」が指定されています。"
                )

    return warnings


def create_default_config() -> AppConfig:
    """Create a minimal default config."""
    return AppConfig(
        version="1.0",
        sharepoint_paths={
            "source_dir": "",
            "reports_dir": "",
        },
        report_definitions=[],
        departments=[],
        column_settings=[
            ColumnSetting(c.column_key, c.display_name, c.visible)
            for c in DEFAULT_COLUMN_SETTINGS
        ],
    )
