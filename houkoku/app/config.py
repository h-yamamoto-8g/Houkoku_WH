"""Path management and application settings.

Resolution chain:
  1. ~/.houkoku/settings.json -> app_data_path
  2. SharePoint default path (platform-dependent)
  3. Fallback (forces setup dialog)
"""

from __future__ import annotations

import json
import platform
from pathlib import Path
from typing import Optional

# ---------- Bootstrap: user-local settings (not on SharePoint) ----------

LOCAL_SETTINGS_DIR: Path = Path.home() / ".houkoku"
LOCAL_SETTINGS_PATH: Path = LOCAL_SETTINGS_DIR / "settings.json"


def load_data_path() -> Optional[Path]:
    """Load saved data path from local settings.json."""
    if not LOCAL_SETTINGS_PATH.exists():
        return None
    try:
        data = json.loads(LOCAL_SETTINGS_PATH.read_text(encoding="utf-8"))
        raw = data.get("app_data_path")
        if raw:
            p = Path(raw)
            if p.exists():
                return p
    except (json.JSONDecodeError, OSError):
        pass
    return None


def save_data_path(path: Path) -> None:
    """Persist data path to local settings.json."""
    LOCAL_SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    data: dict = {}
    if LOCAL_SETTINGS_PATH.exists():
        try:
            data = json.loads(LOCAL_SETTINGS_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    data["app_data_path"] = str(path)
    LOCAL_SETTINGS_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ---------- Source app_data path (元データ取得先) ----------

def load_source_app_data_path() -> Optional[Path]:
    """Load saved source app_data path from local settings.json."""
    if not LOCAL_SETTINGS_PATH.exists():
        return None
    try:
        data = json.loads(LOCAL_SETTINGS_PATH.read_text(encoding="utf-8"))
        raw = data.get("source_app_data_path")
        if raw:
            p = Path(raw)
            if p.exists():
                return p
    except (json.JSONDecodeError, OSError):
        pass
    return None


def save_source_app_data_path(path: Path) -> None:
    """Persist source app_data path to local settings.json."""
    LOCAL_SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    data: dict = {}
    if LOCAL_SETTINGS_PATH.exists():
        try:
            data = json.loads(LOCAL_SETTINGS_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    data["source_app_data_path"] = str(path)
    LOCAL_SETTINGS_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _resolve_data_path() -> Optional[Path]:
    """Resolve DATA_PATH: settings.json -> SharePoint default -> None."""
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


# ---------- Module-level path variables ----------

DATA_PATH: Optional[Path] = _resolve_data_path()
SOURCE_APP_DATA_PATH: Optional[Path] = load_source_app_data_path()


def _source_csv_path() -> Optional[Path]:
    """Current source CSV path (lazy)."""
    if DATA_PATH is None:
        return None
    return DATA_PATH / "source" / "analysis_data.csv"


def _reports_path() -> Optional[Path]:
    """Current reports output root (lazy)."""
    if DATA_PATH is None:
        return None
    return DATA_PATH / "reports"


def _config_dir_path() -> Optional[Path]:
    """Shared config directory on SharePoint (lazy)."""
    if DATA_PATH is None:
        return None
    return DATA_PATH / "config"


# Convenience properties (call these instead of caching DATA_PATH-derived paths)
SOURCE_CSV_PATH: Optional[Path] = _source_csv_path()
REPORTS_PATH: Optional[Path] = _reports_path()
CONFIG_DIR_PATH: Optional[Path] = _config_dir_path()


def reload_paths(new_data_path: Optional[Path] = None) -> None:
    """Re-resolve all derived paths. Called after SetupRootDialog."""
    global DATA_PATH, SOURCE_CSV_PATH, REPORTS_PATH, CONFIG_DIR_PATH

    if new_data_path is not None:
        DATA_PATH = new_data_path
    else:
        DATA_PATH = _resolve_data_path()

    SOURCE_CSV_PATH = _source_csv_path()
    REPORTS_PATH = _reports_path()
    CONFIG_DIR_PATH = _config_dir_path()
