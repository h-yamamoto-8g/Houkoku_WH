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
    from app.ui.dialogs.loading_dialog import LoadingOverlay, WorkerThread
    from app.services.report_service import ReportService
    from app.services.data_update_service import run_validation
    from app.core.config_store import load_config
    import app.config as _cfg

    app.processEvents()

    # --- Apply stylesheet ---
    app.setStyleSheet(APP_STYLESHEET)

    # --- Resolve paths: show setup dialog if source CSV or reports path is invalid ---
    if not _cfg.paths_valid():
        if splash:
            splash.close()
        _close_pyinstaller_splash()

        dlg = SetupRootDialog()
        if dlg.exec() != SetupRootDialog.DialogCode.Accepted:
            sys.exit(0)

    # --- Initialize services ---
    report_svc = ReportService()

    # Load config (creates default if missing)
    try:
        config = load_config()
    except FileNotFoundError:
        config = None

    report_svc.set_config(config)

    # --- Create main window (show immediately with loading overlay) ---
    services = {"report": report_svc}
    window = MainWindow(services)

    # Close splash screens before showing main window
    if splash:
        splash.close()
    _close_pyinstaller_splash()

    window.show()

    # --- Load CSV data with loading overlay ---
    overlay = LoadingOverlay(window.centralWidget(), "データを読み込み中...")
    overlay.show_overlay()
    app.processEvents()

    def _do_load() -> object:
        """Run validation and load CSV in background thread."""
        validation = run_validation()
        report_svc.load_data()
        return validation

    def _on_load_done(result: object) -> None:
        """Handle successful data load."""
        overlay.hide_overlay()
        if config:
            window.set_config(config)

        # Show validation warnings
        if hasattr(result, "warnings") and result.warnings:
            window._ui.lbl_status.setText(
                f"データ: {result.message} | 警告: {', '.join(result.warnings)}"
            )
        elif hasattr(result, "success") and result.success:
            window._ui.lbl_status.setText(result.message)
        else:
            window._ui.lbl_status.setText("データの読み込みが完了しました。")

    def _on_load_error(msg: str) -> None:
        """Handle data load failure — prompt user to reconfigure."""
        overlay.hide_overlay()
        QMessageBox.warning(
            window,
            "データ読み込みエラー",
            f"CSVデータの読み込みに問題があります:\n{msg}\n\n"
            "設定画面から正しい元データCSVファイルを選択してください。",
        )
        dlg = SetupRootDialog(window)
        if dlg.exec() == SetupRootDialog.DialogCode.Accepted:
            # Retry loading with new paths
            overlay.set_message("データを読み込み中...")
            overlay.show_overlay()
            worker = WorkerThread(_do_load, window)
            worker.finished.connect(_on_load_done)
            worker.error.connect(_on_load_error)
            # Keep reference to prevent GC
            window._startup_worker = worker
            worker.start()
        else:
            window._ui.lbl_status.setText("データが読み込まれていません。設定を確認してください。")

    worker = WorkerThread(_do_load, window)
    worker.finished.connect(_on_load_done)
    worker.error.connect(_on_load_error)
    # Keep reference to prevent GC
    window._startup_worker = worker
    worker.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
