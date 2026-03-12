"""Path management and application settings.

Resolution chain for each path:
  1. ~/.houkoku/settings.json -> individual path settings
  2. SharePoint default (platform-dependent)
  3. Development fallback
  4. None (forces setup dialog)

Paths managed:
  - DATA_PATH: Root data folder (config.json location)
  - SOURCE_CSV_PATH: 元データCSVファイルパス (individually configurable)
  - REPORTS_PATH: 報告データ出力先 (individually configurable)
"""

from __future__ import annotations

import json
import platform
from pathlib import Path
from typing import Optional

# ---------- Bootstrap: user-local settings (not on SharePoint) ----------

LOCAL_SETTINGS_DIR: Path = Path.home() / ".houkoku"
LOCAL_SETTINGS_PATH: Path = LOCAL_SETTINGS_DIR / "settings.json"


def _load_settings() -> dict:
    """Load local settings.json as dict."""
    if not LOCAL_SETTINGS_PATH.exists():
        return {}
    try:
        return json.loads(LOCAL_SETTINGS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_settings(data: dict) -> None:
    """Persist dict to local settings.json."""
    LOCAL_SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    LOCAL_SETTINGS_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _load_path_setting(key: str) -> Optional[Path]:
    """Load a path from settings.json by key. Returns None if missing or invalid."""
    raw = _load_settings().get(key)
    if raw:
        p = Path(raw)
        if p.exists():
            return p
    return None


def _save_path_setting(key: str, path: Path) -> None:
    """Save a path to settings.json by key."""
    data = _load_settings()
    data[key] = str(path)
    _save_settings(data)


# ---------- DATA_PATH (config root) ----------

def load_data_path() -> Optional[Path]:
    """Load saved data path from local settings.json."""
    return _load_path_setting("app_data_path")


def save_data_path(path: Path) -> None:
    """Persist data path to local settings.json."""
    _save_path_setting("app_data_path", path)


# ---------- SOURCE_CSV_PATH (元データCSVパス) ----------

def load_source_csv_setting() -> Optional[Path]:
    """Load saved source CSV path from local settings.json."""
    return _load_path_setting("source_csv_path")


def save_source_csv_setting(path: Path) -> None:
    """Persist source CSV path to local settings.json."""
    _save_path_setting("source_csv_path", path)


# ---------- REPORTS_PATH (報告データ出力先) ----------

def load_reports_path_setting() -> Optional[Path]:
    """Load saved reports output path from local settings.json."""
    return _load_path_setting("reports_path")


def save_reports_path_setting(path: Path) -> None:
    """Persist reports output path to local settings.json."""
    _save_path_setting("reports_path", path)


# ---------- Source app_data path (元データ取得先) ----------

def load_source_app_data_path() -> Optional[Path]:
    """Load saved source app_data path from local settings.json."""
    return _load_path_setting("source_app_data_path")


def save_source_app_data_path(path: Path) -> None:
    """Persist source app_data path to local settings.json."""
    _save_path_setting("source_app_data_path", path)


# ---------- Resolution ----------

def _resolve_data_path() -> Optional[Path]:
    """Resolve DATA_PATH: settings.json -> SharePoint default -> dev fallback -> None."""
    saved = load_data_path()
    if saved is not None:
        return saved

    if platform.system() == "Windows":
        sp = (
            Path.home()
            / "トクヤマグループ"
            / "環境分析課 - ドキュメント"
            / "報告ツール"
        )
        if sp.exists():
            return sp

    # Development fallback: look for houkoku_data in project root or parent
    for ancestor in (
        Path(__file__).resolve().parent.parent,       # houkoku/
        Path(__file__).resolve().parent.parent.parent, # Houkoku_WH/
    ):
        dev_path = ancestor / "houkoku_data"
        if dev_path.exists():
            return dev_path

    return None


def _resolve_source_csv_path() -> Optional[Path]:
    """Resolve SOURCE_CSV_PATH: explicit setting -> DATA_PATH/source/analysis_data.csv."""
    saved = load_source_csv_setting()
    if saved is not None:
        return saved
    if DATA_PATH is not None:
        candidate = DATA_PATH / "source" / "analysis_data.csv"
        if candidate.exists():
            return candidate
    return None


def _resolve_reports_path() -> Optional[Path]:
    """Resolve REPORTS_PATH: explicit setting -> DATA_PATH/reports."""
    saved = load_reports_path_setting()
    if saved is not None:
        return saved
    if DATA_PATH is not None:
        candidate = DATA_PATH / "reports"
        if candidate.exists():
            return candidate
    return None


def _config_dir_path() -> Optional[Path]:
    """Shared config directory on SharePoint (lazy)."""
    if DATA_PATH is None:
        return None
    return DATA_PATH / "config"


# ---------- Module-level path variables ----------

DATA_PATH: Optional[Path] = _resolve_data_path()
SOURCE_APP_DATA_PATH: Optional[Path] = load_source_app_data_path()
SOURCE_CSV_PATH: Optional[Path] = _resolve_source_csv_path()
REPORTS_PATH: Optional[Path] = _resolve_reports_path()
CONFIG_DIR_PATH: Optional[Path] = _config_dir_path()


def paths_valid() -> bool:
    """Check if both source CSV and reports paths are configured and valid."""
    return (
        SOURCE_CSV_PATH is not None
        and SOURCE_CSV_PATH.exists()
        and REPORTS_PATH is not None
        and REPORTS_PATH.exists()
    )


def reload_paths(
    new_data_path: Optional[Path] = None,
    new_source_csv_path: Optional[Path] = None,
    new_reports_path: Optional[Path] = None,
) -> None:
    """Re-resolve all derived paths. Called after SetupRootDialog or settings change."""
    global DATA_PATH, SOURCE_CSV_PATH, REPORTS_PATH, CONFIG_DIR_PATH

    if new_data_path is not None:
        DATA_PATH = new_data_path
    else:
        DATA_PATH = _resolve_data_path()

    if new_source_csv_path is not None:
        SOURCE_CSV_PATH = new_source_csv_path
    else:
        SOURCE_CSV_PATH = _resolve_source_csv_path()

    if new_reports_path is not None:
        REPORTS_PATH = new_reports_path
    else:
        REPORTS_PATH = _resolve_reports_path()

    CONFIG_DIR_PATH = _config_dir_path()
