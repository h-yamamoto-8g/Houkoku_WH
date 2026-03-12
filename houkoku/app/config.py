"""Path management and application settings.

Two configurable root paths:
  - 課内データパス (DATA_PATH): 報告ツール自体のデータ (config.json, reports/)
  - 課外データパス (SOURCE_APP_DATA_PATH): Bunseki_ccc の app_data
    → SOURCE_CSV_PATH = {課外データパス}/_common/data/lab_aid/normalized/bunseki.csv

Resolution chain:
  1. ~/.houkoku/settings.json -> saved path
  2. SharePoint default (platform-dependent)
  3. Development fallback
  4. None (forces setup dialog)
"""

from __future__ import annotations

import json
import platform
from pathlib import Path
from typing import Optional

# ---------- Bootstrap: user-local settings (not on SharePoint) ----------

LOCAL_SETTINGS_DIR: Path = Path.home() / ".houkoku"
LOCAL_SETTINGS_PATH: Path = LOCAL_SETTINGS_DIR / "settings.json"

# Bunseki_ccc の正規化CSVの相対パス
_SOURCE_CSV_RELATIVE = Path("_common") / "data" / "lab_aid" / "normalized" / "bunseki.csv"


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


# ---------- 課内データパス (DATA_PATH) ----------

def load_data_path() -> Optional[Path]:
    """Load saved 課内データパス from local settings.json."""
    return _load_path_setting("app_data_path")


def save_data_path(path: Path) -> None:
    """Persist 課内データパス to local settings.json."""
    _save_path_setting("app_data_path", path)


# ---------- 課外データパス (SOURCE_APP_DATA_PATH) ----------

def load_source_app_data_path() -> Optional[Path]:
    """Load saved 課外データパス from local settings.json."""
    return _load_path_setting("source_app_data_path")


def save_source_app_data_path(path: Path) -> None:
    """Persist 課外データパス to local settings.json."""
    _save_path_setting("source_app_data_path", path)


# ---------- Resolution ----------

def _resolve_data_path() -> Optional[Path]:
    """Resolve 課内データパス: settings.json -> SharePoint default -> dev fallback -> None."""
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


def _resolve_source_app_data_path() -> Optional[Path]:
    """Resolve 課外データパス: settings.json -> SharePoint default -> dev fallback -> None."""
    saved = load_source_app_data_path()
    if saved is not None:
        return saved

    if platform.system() == "Windows":
        sp = (
            Path.home()
            / "トクヤマグループ"
            / "環境分析課 - ドキュメント"
            / "app_data"
        )
        if sp.exists():
            return sp

    # Development fallback: look for app_data in project root or parent
    for ancestor in (
        Path(__file__).resolve().parent.parent,       # houkoku/
        Path(__file__).resolve().parent.parent.parent, # Houkoku_WH/
    ):
        dev_path = ancestor / "app_data"
        if dev_path.exists():
            return dev_path

    return None


def _derive_source_csv_path() -> Optional[Path]:
    """Derive SOURCE_CSV_PATH from 課外データパス + relative path."""
    if SOURCE_APP_DATA_PATH is None:
        return None
    candidate = SOURCE_APP_DATA_PATH / _SOURCE_CSV_RELATIVE
    if candidate.exists():
        return candidate
    return None


def _derive_reports_path() -> Optional[Path]:
    """Derive REPORTS_PATH from 課内データパス."""
    if DATA_PATH is None:
        return None
    return DATA_PATH / "reports"


def _config_dir_path() -> Optional[Path]:
    """Shared config directory (課内データパス/config)."""
    if DATA_PATH is None:
        return None
    return DATA_PATH / "config"


# ---------- Module-level path variables ----------

DATA_PATH: Optional[Path] = _resolve_data_path()
SOURCE_APP_DATA_PATH: Optional[Path] = _resolve_source_app_data_path()
SOURCE_CSV_PATH: Optional[Path] = _derive_source_csv_path()
REPORTS_PATH: Optional[Path] = _derive_reports_path()
CONFIG_DIR_PATH: Optional[Path] = _config_dir_path()


def paths_valid() -> bool:
    """Check if both root paths are configured and source CSV exists."""
    return (
        DATA_PATH is not None
        and DATA_PATH.exists()
        and SOURCE_APP_DATA_PATH is not None
        and SOURCE_APP_DATA_PATH.exists()
        and SOURCE_CSV_PATH is not None
        and SOURCE_CSV_PATH.exists()
    )


def reload_paths(
    new_data_path: Optional[Path] = None,
    new_source_app_data_path: Optional[Path] = None,
) -> None:
    """Re-resolve all derived paths. Called after SetupRootDialog or settings change."""
    global DATA_PATH, SOURCE_APP_DATA_PATH, SOURCE_CSV_PATH, REPORTS_PATH, CONFIG_DIR_PATH

    if new_data_path is not None:
        DATA_PATH = new_data_path
    else:
        DATA_PATH = _resolve_data_path()

    if new_source_app_data_path is not None:
        SOURCE_APP_DATA_PATH = new_source_app_data_path
    else:
        SOURCE_APP_DATA_PATH = _resolve_source_app_data_path()

    SOURCE_CSV_PATH = _derive_source_csv_path()
    REPORTS_PATH = _derive_reports_path()
    CONFIG_DIR_PATH = _config_dir_path()
