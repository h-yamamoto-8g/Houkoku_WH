# CLAUDE.md

> Auto-loaded by Claude Code CLI.
> Read this file and `docs/設計書.md` before starting any implementation.

---

## Project Overview

Desktop tool (Python + PySide6) for distributing environmental analysis reports to multiple departments.
Reads CSV from SharePoint-synced folders, splits data by department-level sample permissions, and outputs filtered CSV + metadata JSON to each department's SharePoint folder.
Excel Online templates (Power Query) render the reports. Power Automate sends email notifications triggered by JSON file creation.

Reference implementation: https://github.com/h-yamamoto-8g/Bunseki_ccc

Detailed design: `docs/設計書.md`

---

## Tech Stack

| Item | Value |
|------|-------|
| Language | Python |
| UI Framework | PySide6 |
| Data Processing | pandas |
| Config | JSON (config.json) |
| Distribution | PyInstaller (one-file exe) |
| Report Display | Excel Online + Power Query |
| Notification | Power Automate (JSON trigger) |
| Package Manager | pip + requirements.txt |

Use well-known, pure-Python libraries. No external API calls — all file I/O via SharePoint sync folders.

---

## Directory Structure

Follow the same layered architecture as Bunseki_ccc:

```
houkoku/
├── main.py                     # Entry point (splash → module load → login → main window)
├── houkoku.spec                # PyInstaller spec
├── requirements.txt
│
├── app/
│   ├── __init__.py
│   ├── config.py               # Path management, settings, constants
│   │
│   ├── core/                   # Data access layer (no UI dependency)
│   │   ├── __init__.py
│   │   ├── loader.py           # CSV read, parse, filter
│   │   └── permission_store.py # Department × sample permission mapping
│   │
│   ├── services/               # Business logic (depends on core/ only)
│   │   ├── __init__.py
│   │   ├── data_update_service.py  # Startup data refresh
│   │   ├── report_service.py       # CSV split, conditions JSON, export
│   │   └── notification_service.py # notification JSON creation
│   │
│   └── ui/                     # Presentation layer (depends on services/ only)
│       ├── __init__.py
│       ├── generated/          # Qt Designer auto-generated code (DO NOT EDIT)
│       │   ├── resources_rc.py
│       │   ├── ui_mainwindow.py
│       │   └── ui_settingswindow.py
│       ├── pages/              # Page implementations (wrapper pattern)
│       │   ├── main_window.py      # Wraps ui_mainwindow, connects signals
│       │   └── settings/
│       │       └── page.py         # Wraps ui_settingswindow
│       ├── dialogs/            # Modal dialogs
│       │   ├── loading_dialog.py   # Loading overlay (QThread progress)
│       │   ├── logon_dialog.py
│       │   └── setup_root_dialog.py
│       ├── widgets/            # Reusable UI components
│       │   └── ...
│       └── styles/             # QSS stylesheet definitions
│           └── __init__.py
│
├── resources/
│   ├── assets/
│   │   ├── splash.png
│   │   └── app-logo.ico
│   └── ui/                     # Qt Designer .ui files (source of generated/)
│       ├── mainwindow.ui
│       └── settingswindow.ui
│
└── docs/
    ├── 設計書.md
    └── CLAUDE.md (this file)
```

### Layer Dependency Rules

```
core/       → External libs only (pandas, json, pathlib)
services/   → core/ only. NEVER import from ui/
ui/         → services/ only. NEVER import from core/ directly
config.py   → Standalone. Imported by all layers for path constants
```

---

## Coding Conventions

### Naming

```
Classes:     PascalCase          e.g. ReportService
Functions:   snake_case          e.g. split_csv_by_department
Constants:   UPPER_SNAKE_CASE    e.g. SOURCE_CSV_PATH
Files:       snake_case.py       e.g. report_service.py
Private:     underscore prefix   e.g. _validate_config()
```

### Python Style

- **Type hints required**: all function args and return types
- **Docstrings required**: Google-style for all public functions/classes
- **Exception handling**: never swallow exceptions; log then notify UI
- **No magic numbers**: extract to constants or config
- Formatter: black (line length: 100)
- Linter: flake8
- Target: Python 3.10+ (match Bunseki_ccc environment)

---

## config.py Pattern (Critical)

Follow the Bunseki_ccc pattern for path management:

```python
# Bootstrap: user-local settings (not on SharePoint)
LOCAL_SETTINGS_DIR = Path.home() / ".houkoku"
LOCAL_SETTINGS_PATH = LOCAL_SETTINGS_DIR / "settings.json"

# Resolution chain:
#   1. ~/.houkoku/settings.json -> app_data_path
#   2. SharePoint default: ~/トクヤマグループ/環境分析課 - ドキュメント/報告ツール
#   3. Fallback (forces setup dialog)
```

### DATA_PATH Lazy Evaluation (Mandatory)

**Never cache DATA_PATH at module level in stores.**

```python
# BAD: fixed at import time, reload_paths() won't update this
from app.config import DATA_PATH
REPORTS_DIR = DATA_PATH / "reports"

# GOOD: reads latest DATA_PATH on each call
import app.config as _cfg
def _reports_dir():
    return _cfg.DATA_PATH / "reports"
```

### Derived Paths

```python
DATA_PATH                                      # Root (SharePoint sync folder)
├── source/analysis_data.csv                   # Source CSV (input)
├── reports/                                   # Output root
│   ├── {dept_folder}/                         # Per-department
│   │   ├── latest/report_data.csv             # Filtered data
│   │   ├── latest/report_conditions.json      # Report metadata
│   │   ├── report_template.xlsx               # Excel Online template
│   │   ├── history/{date}_{job}/              # Archive
│   │   └── notifications/notification_{ts}.json  # PA trigger
│   └── ...
└── config/                                    # Shared config backup
```

---

## Data Update at Startup

Follow the Bunseki_ccc `data_update_service.py` pattern:

```
App launch
  ├── Show splash (PyInstaller Splash for frozen, QSplashScreen for dev)
  ├── Delayed import of heavy modules during splash (_load_app_modules pattern)
  │   └── processEvents() between imports to keep splash responsive
  ├── Load config.py, resolve DATA_PATH
  ├── If DATA_PATH missing → show SetupRootDialog
  ├── Run data update (QThread worker)
  │   ├── Check source CSV exists and is readable
  │   ├── Validate CSV structure (expected columns present)
  │   └── Emit signal to update UI with last-modified timestamp
  └── Show main window
```

Key points:
- Use `QThread` + Signal/Slot for background work (same as Bunseki_ccc `_DataUpdateWorker`)
- `ENABLED` flag to disable update during development
- `CREATE_NO_WINDOW` flag (0x08000000) if calling subprocess on Windows
- Delayed import pattern: heavy modules (pandas, etc.) are imported inside `_load_app_modules()` during splash, then injected into `globals()`

---

## EXE Build

### Spec File Template

```python
# houkoku.spec
a = Analysis(
    ["main.py"],
    datas=[("resources/assets/splash.png", "resources/assets")],
    hiddenimports=[
        "PySide6.QtSvg",
        "PySide6.QtSvgWidgets",
        "openpyxl",
    ],
    excludes=[
        "matplotlib",
        "matplotlib.backends.backend_tk",
        "matplotlib.backends.backend_tkagg",
        "PyQt5",
        "PyQt6",
    ],
)

pyz = PYZ(a.pure, a.zipped_data)

splash = Splash(
    "resources/assets/splash.png",
    binaries=a.binaries,
    datas=a.datas,
    text_pos=None,
)

exe = EXE(
    pyz, splash, splash.binaries,
    a.scripts, a.binaries, a.zipfiles, a.datas, [],
    name="Houkoku",
    console=False,
    icon="resources/assets/app-logo.ico",
    upx=True,
)
```

### Build & Deploy

```bash
pip install pyinstaller
pyinstaller houkoku.spec
# -> dist/Houkoku.exe
# Copy to SharePoint distribution folder
```

### OneDrive Sync Considerations

- `--onefile` may trigger repeated sync / antivirus scans
- If issues occur, switch to `--onedir` + launcher.bat:
  ```bat
  @echo off
  start "" "%~dp0dist\Houkoku\Houkoku.exe"
  ```

---

## Implementation Workflow (Mandatory)

```
1. Before: Read docs/設計書.md and this CLAUDE.md
2. Before: Review existing code structure before adding/changing
3. During: Implement one feature at a time, one layer at a time (core → service → ui)
4. After:  Run the app and verify behavior manually
5. After:  Confirm config.json round-trip (load → edit → save → reload)
```

---

## Common Mistakes (Do NOT Do These)

```
NG: Hardcode SharePoint paths
    → Use _resolve_data_path() from config.py

NG: Cache DATA_PATH at module level in stores
    → Use lazy function pattern: def _path(): return _cfg.DATA_PATH / ...

NG: File I/O on main thread
    → Use QThread + Signal/Slot. Never block the UI event loop.

NG: Write logic directly in UI files (generated/ or pages/)
    → Go through services/ → core/. UI only handles display and signal connections.

NG: Edit auto-generated files in ui/generated/
    → Edit .ui files in Qt Designer, then regenerate. Wrap in pages/ with wrapper pattern.

NG: Use absolute paths in config.json for SharePoint folders
    → Store relative paths from DATA_PATH

NG: Overwrite notification.json (Power Automate won't re-trigger)
    → Use timestamped filenames: notification_{YYYYMMDD_HHMMSS}.json

NG: Output CSV without BOM
    → Use UTF-8 BOM (utf-8-sig) for Excel compatibility

NG: Assume SharePoint sync is instant
    → Add retry logic with file existence checks after write

NG: Import PySide6 before restoring builtins.__import__
    → PySide6 patches builtins.__import__ (conflicts with six). Restore immediately after import.
```

---

## Key Data Structures

### config.json (App Settings)

```json
{
  "version": "1.0",
  "sharepoint_paths": { "source_dir": "...", "reports_dir": "..." },
  "report_definitions": [
    { "report_id": "RPT-001", "report_name": "...", "search_filters": { "protocol_name": ["..."] } }
  ],
  "departments": [
    { "dept_id": "DEPT-A", "dept_name": "...", "folder_name": "...",
      "allowed_samples": { "RPT-001": ["SAMPLE-001", "SAMPLE-002"] } }
  ]
}
```

### notification JSON (Power Automate Trigger)

```json
{
  "report_id": "RPT-001", "job_number": "JOB-2026-0042",
  "sent_at": "2026-03-11T14:00:00", "sent_by": "担当者名",
  "dept_id": "DEPT-A", "message": "...", "report_link": "https://..."
}
```

---

## PySide6 Rules

Match Bunseki_ccc conventions:

- Separate UI from business logic (`ui/generated/` → `ui/pages/` wrapper → `services/` → `core/`)
- No service/logic code in `ui/`
- Signal/slot connections in `__init__` or `_connect_signals()`
- Heavy operations (file I/O, CSV processing) must run in `QThread` — never block UI
- Widget sizing via layout managers, no hardcoded pixel sizes
- Use `QSS` for styling (defined in `ui/styles/`)

### Wrapper Pattern

```python
# ui/pages/main_window.py
from app.ui.generated.ui_mainwindow import Ui_MainWindow

class MainWindow(QMainWindow):
    def __init__(self, services: dict) -> None:
        super().__init__()
        self._ui = Ui_MainWindow()
        self._ui.setupUi(self)
        self._report_svc = services["report"]
        self._connect_signals()

    def _connect_signals(self) -> None:
        self._ui.btn_send.clicked.connect(self._on_send)
```

### QThread Worker Pattern

```python
class _ExportWorker(QThread):
    finished = Signal()
    error = Signal(str)

    def __init__(self, func, parent=None):
        super().__init__(parent)
        self._func = func

    def run(self):
        try:
            self._func()
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))
```

---

## Design Guidelines

- White-based theme (#f5f7fa background), text color #333333
- No primary/saturated accent colors
- Light rounded corners, adequate spacing
- Don't stretch content full-width unnecessarily
- Show LoadingOverlay during file operations (match Bunseki_ccc pattern)
- Confirmation dialog before send (list departments and sample counts)
- Settings screen: tabbed layout (report management / department permissions / path config)
- Japanese UI text throughout
- Watch for font garbling in Japanese text (use Yu Gothic on Windows, Hiragino Sans on macOS)
- Native-feeling UI
