"""Entry point for 水質報告ツール.

Startup flow:
  1. Splash screen (QSplashScreen in dev, PyInstaller Splash in frozen)
  2. Delayed import of heavy modules during splash
  3. Resolve DATA_PATH -> show SetupRootDialog if missing
  4. Load CSV in QThread
  5. Show main window
"""

from __future__ import annotations

import sys
import os


def _is_frozen() -> bool:
    """Check if running as PyInstaller bundle."""
    return getattr(sys, "frozen", False)


def _close_pyinstaller_splash() -> None:
    """Close PyInstaller splash screen if present."""
    if _is_frozen():
        try:
            import pyi_splash  # type: ignore
            pyi_splash.close()
        except ImportError:
            pass


def main() -> None:
    """Application entry point."""
    # --- Early setup ---
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    # Import pandas before PySide6 to avoid shibokensupport/six conflict.
    # PySide6's import hooks interfere with dateutil's use of six.moves.
    import pandas  # noqa: F401

    from PySide6.QtWidgets import QApplication, QSplashScreen, QMessageBox
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QPixmap

    app = QApplication(sys.argv)

    # --- Splash screen (dev mode) ---
    splash = None
    if not _is_frozen():
        splash_path = os.path.join(
            os.path.dirname(__file__), "resources", "assets", "splash.png"
        )
        if os.path.exists(splash_path):
            pixmap = QPixmap(splash_path)
            splash = QSplashScreen(pixmap)
            splash.show()
        else:
            # No splash image — just proceed
            pass

    app.processEvents()

    # --- Delayed imports (heavy modules) ---
    if splash:
        splash.showMessage(
            "モジュールを読み込み中...",
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
        )
    app.processEvents()

    app.processEvents()

    from app.ui.styles import APP_STYLESHEET
    from app.ui.pages.main_window import MainWindow
    from app.ui.dialogs.setup_root_dialog import SetupRootDialog
    from app.ui.dialogs.loading_dialog import WorkerThread
    from app.services.report_service import ReportService
    from app.services.data_update_service import run_validation
    from app.core.config_store import load_config
    import app.config as _cfg

    app.processEvents()

    # --- Apply stylesheet ---
    app.setStyleSheet(APP_STYLESHEET)

    # --- Resolve DATA_PATH ---
    if _cfg.DATA_PATH is None:
        if splash:
            splash.close()
        _close_pyinstaller_splash()

        dlg = SetupRootDialog()
        if dlg.exec() != SetupRootDialog.DialogCode.Accepted:
            sys.exit(0)

    # --- Data validation (startup check) ---
    if splash:
        splash.showMessage(
            "データを検証中...",
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
        )
    app.processEvents()

    result = run_validation()

    # --- Initialize services ---
    report_svc = ReportService()

    # Load config (creates default if missing)
    try:
        config = load_config()
    except FileNotFoundError:
        config = None

    report_svc.set_config(config)

    # --- Load CSV data ---
    if splash:
        splash.showMessage(
            "CSVデータを読み込み中...",
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
        )
    app.processEvents()

    try:
        report_svc.load_data()
    except (FileNotFoundError, ValueError) as e:
        if splash:
            splash.close()
        _close_pyinstaller_splash()
        QMessageBox.warning(
            None,
            "データ読み込み警告",
            f"CSVデータの読み込みに問題があります:\n{e}\n\n"
            "設定画面からデータフォルダを確認してください。",
        )

    # --- Create main window ---
    services = {"report": report_svc}
    window = MainWindow(services)

    if config:
        window.set_config(config)

    # Show validation warnings
    if result.warnings:
        window._ui.lbl_status.setText(
            f"データ: {result.message} | 警告: {', '.join(result.warnings)}"
        )
    elif result.success:
        window._ui.lbl_status.setText(result.message)

    # --- Show main window ---
    if splash:
        splash.close()
    _close_pyinstaller_splash()

    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
