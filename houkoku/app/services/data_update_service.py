"""Startup data validation service.

Checks that the source CSV exists, is readable, and has expected columns.
Follows the Bunseki_ccc data_update_service pattern with ENABLED flag.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import app.config as _cfg
from app.core.loader import load_source_csv, validate_csv_columns


# Set to False during development to skip validation
ENABLED: bool = True


@dataclass
class UpdateResult:
    """Result of startup data validation."""

    success: bool
    message: str
    csv_modified: Optional[datetime] = None
    row_count: int = 0
    warnings: list[str] = None

    def __post_init__(self) -> None:
        if self.warnings is None:
            self.warnings = []


def run_validation() -> UpdateResult:
    """Run startup data validation checks.

    Returns:
        UpdateResult with status and diagnostics.
    """
    if not ENABLED:
        return UpdateResult(success=True, message="データ検証はスキップされました（開発モード）。")

    csv_path = _cfg.SOURCE_CSV_PATH
    if csv_path is None:
        return UpdateResult(
            success=False,
            message="データフォルダが設定されていません。",
        )

    if not csv_path.exists():
        return UpdateResult(
            success=False,
            message=f"元データCSVが見つかりません: {csv_path}",
        )

    warnings: list[str] = []

    # Check file modification time
    try:
        mtime = os.path.getmtime(csv_path)
        csv_modified = datetime.fromtimestamp(mtime)
    except OSError:
        csv_modified = None
        warnings.append("CSVの更新日時を取得できませんでした。")

    # Try loading and validating
    try:
        df = load_source_csv(csv_path)
    except (FileNotFoundError, ValueError) as e:
        return UpdateResult(success=False, message=str(e), warnings=warnings)

    missing = validate_csv_columns(df)
    if missing:
        warnings.append(f"不足している列: {', '.join(missing)}")

    row_count = len(df)
    if row_count == 0:
        warnings.append("CSVにデータ行がありません。")

    return UpdateResult(
        success=True,
        message=f"データ読み込み完了: {row_count:,}行",
        csv_modified=csv_modified,
        row_count=row_count,
        warnings=warnings,
    )
