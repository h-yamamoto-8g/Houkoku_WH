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
class AppConfig:
    """Top-level application configuration."""

    version: str = "1.0"
    sharepoint_paths: dict[str, str] = field(default_factory=dict)
    report_definitions: list[ReportDefinition] = field(default_factory=list)
    departments: list[Department] = field(default_factory=list)


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
    return AppConfig(
        version=raw.get("version", "1.0"),
        sharepoint_paths=raw.get("sharepoint_paths", {}),
        report_definitions=[
            _report_def_from_dict(r) for r in raw.get("report_definitions", [])
        ],
        departments=[_department_from_dict(d) for d in raw.get("departments", [])],
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
    )
