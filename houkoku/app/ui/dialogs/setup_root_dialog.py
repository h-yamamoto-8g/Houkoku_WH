"""Setup dialog for selecting data paths.

Shown on first launch or when required paths are not configured.
Allows separate configuration of:
  - 元データCSVパス (source CSV file)
  - 報告データ出力先 (report output folder)
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

import app.config as _cfg


class SetupRootDialog(QDialog):
    """Dialog for setting the source CSV and reports output paths."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("データパス設定")
        self.setMinimumWidth(550)
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        layout.addWidget(
            QLabel(
                "水質報告ツールのデータパスを設定してください。\n"
                "元データCSVファイルと報告データの出力先フォルダを指定します。"
            )
        )

        # --- 元データCSVパス ---
        layout.addWidget(QLabel("元データCSVファイル:"))
        row_csv = QHBoxLayout()
        self._txt_source_csv = QLineEdit()
        self._txt_source_csv.setPlaceholderText("CSVファイルを選択...")
        if _cfg.SOURCE_CSV_PATH is not None:
            self._txt_source_csv.setText(str(_cfg.SOURCE_CSV_PATH))
        row_csv.addWidget(self._txt_source_csv)

        self._btn_browse_csv = QPushButton("参照...")
        self._btn_browse_csv.setFixedWidth(80)
        row_csv.addWidget(self._btn_browse_csv)
        layout.addLayout(row_csv)

        # --- 報告データ出力先 ---
        layout.addWidget(QLabel("報告データ出力先フォルダ:"))
        row_reports = QHBoxLayout()
        self._txt_reports = QLineEdit()
        self._txt_reports.setPlaceholderText("出力先フォルダを選択...")
        if _cfg.REPORTS_PATH is not None:
            self._txt_reports.setText(str(_cfg.REPORTS_PATH))
        row_reports.addWidget(self._txt_reports)

        self._btn_browse_reports = QPushButton("参照...")
        self._btn_browse_reports.setFixedWidth(80)
        row_reports.addWidget(self._btn_browse_reports)
        layout.addLayout(row_reports)

        # --- Buttons ---
        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        layout.addWidget(self._buttons)

    def _connect_signals(self) -> None:
        self._btn_browse_csv.clicked.connect(self._on_browse_csv)
        self._btn_browse_reports.clicked.connect(self._on_browse_reports)
        self._buttons.accepted.connect(self._on_ok)
        self._buttons.rejected.connect(self.reject)

    def _on_browse_csv(self) -> None:
        start_dir = str(Path.home())
        if self._txt_source_csv.text():
            p = Path(self._txt_source_csv.text())
            if p.parent.exists():
                start_dir = str(p.parent)

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "元データCSVファイルを選択",
            start_dir,
            "CSVファイル (*.csv);;すべてのファイル (*)",
        )
        if file_path:
            self._txt_source_csv.setText(file_path)

    def _on_browse_reports(self) -> None:
        start_dir = str(Path.home())
        if self._txt_reports.text():
            p = Path(self._txt_reports.text())
            if p.exists():
                start_dir = str(p)

        folder = QFileDialog.getExistingDirectory(
            self, "報告データ出力先フォルダを選択", start_dir
        )
        if folder:
            self._txt_reports.setText(folder)

    def _on_ok(self) -> None:
        csv_text = self._txt_source_csv.text().strip()
        reports_text = self._txt_reports.text().strip()

        if not csv_text or not reports_text:
            QMessageBox.warning(
                self, "入力エラー", "両方のパスを入力してください。"
            )
            return

        csv_path = Path(csv_text)
        reports_path = Path(reports_text)

        if not csv_path.exists():
            QMessageBox.warning(
                self,
                "パスエラー",
                f"元データCSVファイルが見つかりません:\n{csv_path}",
            )
            return

        if not reports_path.exists():
            reports_path.mkdir(parents=True, exist_ok=True)

        # Save paths
        _cfg.save_source_csv_setting(csv_path)
        _cfg.save_reports_path_setting(reports_path)

        # Also set DATA_PATH to reports parent if not already set
        if _cfg.DATA_PATH is None:
            data_path = reports_path.parent
            _cfg.save_data_path(data_path)
            _cfg.reload_paths(
                new_data_path=data_path,
                new_source_csv_path=csv_path,
                new_reports_path=reports_path,
            )
        else:
            _cfg.reload_paths(
                new_source_csv_path=csv_path,
                new_reports_path=reports_path,
            )

        self.accept()
