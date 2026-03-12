"""Path management and application settings.

Two configurable root paths:
  - 課内データパス (INTERNAL_PATH): Bunseki_ccc の app_data
    → SOURCE_CSV_PATH = {課内}/_common/data/lab_aid/normalized/bunseki.csv
  - 課外データパス (EXTERNAL_PATH): 報告書の出力先
    → REPORTS_PATH = {課外}/報告書
    → CONFIG_DIR_PATH = {課外}/config

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


# ---------- 課内データパス (INTERNAL_PATH) ----------
# Bunseki_ccc の app_data (bunseki.csv, config 等)

def load_internal_path() -> Optional[Path]:
    """Load saved 課内データパス from local settings.json."""
    return _load_path_setting("internal_data_path")


def save_internal_path(path: Path) -> None:
    """Persist 課内データパス to local settings.json."""
    _save_path_setting("internal_data_path", path)


# ---------- 課外データパス (EXTERNAL_PATH) ----------
# 報告書出力先 ({外部パス}/報告書/{部署名}/...)

def load_external_path() -> Optional[Path]:
    """Load saved 課外データパス from local settings.json."""
    return _load_path_setting("external_data_path")


def save_external_path(path: Path) -> None:
    """Persist 課外データパス to local settings.json."""
    _save_path_setting("external_data_path", path)


# ---------- Resolution ----------

def _resolve_internal_path() -> Optional[Path]:
    """Resolve 課内データパス: settings.json -> SharePoint default -> dev fallback -> None."""
    saved = load_internal_path()
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


def _resolve_external_path() -> Optional[Path]:
    """Resolve 課外データパス: settings.json -> SharePoint default -> dev fallback -> None."""
    saved = load_external_path()
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


def _derive_source_csv_path() -> Optional[Path]:
    """Derive SOURCE_CSV_PATH from 課内データパス + relative path."""
    if INTERNAL_PATH is None:
        return None
    candidate = INTERNAL_PATH / _SOURCE_CSV_RELATIVE
    if candidate.exists():
        return candidate
    return None


def _derive_reports_path() -> Optional[Path]:
    """Derive REPORTS_PATH from 課外データパス/報告書."""
    if EXTERNAL_PATH is None:
        return None
    return EXTERNAL_PATH / "報告書"


def _derive_config_dir_path() -> Optional[Path]:
    """Config directory (課外データパス/config)."""
    if EXTERNAL_PATH is None:
        return None
    return EXTERNAL_PATH / "config"


# ---------- Module-level path variables ----------

INTERNAL_PATH: Optional[Path] = _resolve_internal_path()
EXTERNAL_PATH: Optional[Path] = _resolve_external_path()
SOURCE_CSV_PATH: Optional[Path] = _derive_source_csv_path()
REPORTS_PATH: Optional[Path] = _derive_reports_path()
CONFIG_DIR_PATH: Optional[Path] = _derive_config_dir_path()

# Legacy aliases (used by config_store, report_service, etc.)
DATA_PATH = INTERNAL_PATH


def paths_valid() -> bool:
    """Check if both root paths are configured and source CSV exists."""
    return (
        INTERNAL_PATH is not None
        and INTERNAL_PATH.exists()
        and EXTERNAL_PATH is not None
        and EXTERNAL_PATH.exists()
        and SOURCE_CSV_PATH is not None
        and SOURCE_CSV_PATH.exists()
    )


def reload_paths(
    new_internal_path: Optional[Path] = None,
    new_external_path: Optional[Path] = None,
) -> None:
    """Re-resolve all derived paths. Called after SetupRootDialog or settings change."""
    global INTERNAL_PATH, EXTERNAL_PATH, SOURCE_CSV_PATH, REPORTS_PATH, CONFIG_DIR_PATH, DATA_PATH

    if new_internal_path is not None:
        INTERNAL_PATH = new_internal_path
    else:
        INTERNAL_PATH = _resolve_internal_path()

    if new_external_path is not None:
        EXTERNAL_PATH = new_external_path
    else:
        EXTERNAL_PATH = _resolve_external_path()

    DATA_PATH = INTERNAL_PATH
    SOURCE_CSV_PATH = _derive_source_csv_path()
    REPORTS_PATH = _derive_reports_path()
    CONFIG_DIR_PATH = _derive_config_dir_path()
