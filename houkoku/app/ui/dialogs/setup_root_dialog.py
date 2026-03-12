"""Setup dialog for selecting data paths.

Shown on first launch or when required paths are not configured.
Two folder paths:
  - 課内データパス: Bunseki_ccc の app_data (bunseki.csv の取得元)
  - 課外データパス: 報告書の出力先 ({外部パス}/報告書/水質/{部署名}/...)
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
    """Dialog for setting 課内データパス and 課外データパス."""

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
                "課内データパス（元データ取得元）と課外データパス（報告書出力先）を指定します。"
            )
        )

        # --- 課内データパス ---
        layout.addWidget(QLabel("課内データパス（Bunseki app_data）:"))
        row_internal = QHBoxLayout()
        self._txt_internal = QLineEdit()
        self._txt_internal.setPlaceholderText("フォルダを選択...")
        if _cfg.INTERNAL_PATH is not None:
            self._txt_internal.setText(str(_cfg.INTERNAL_PATH))
        row_internal.addWidget(self._txt_internal)

        self._btn_browse_internal = QPushButton("参照...")
        self._btn_browse_internal.setFixedWidth(80)
        row_internal.addWidget(self._btn_browse_internal)
        layout.addLayout(row_internal)

        # CSV derived path info
        self._lbl_csv_info = QLabel()
        self._lbl_csv_info.setStyleSheet("color: gray; font-size: 11px;")
        self._update_csv_info()
        layout.addWidget(self._lbl_csv_info)

        # --- 課外データパス ---
        layout.addWidget(QLabel("課外データパス（報告書出力先）:"))
        row_external = QHBoxLayout()
        self._txt_external = QLineEdit()
        self._txt_external.setPlaceholderText("フォルダを選択...")
        if _cfg.EXTERNAL_PATH is not None:
            self._txt_external.setText(str(_cfg.EXTERNAL_PATH))
        row_external.addWidget(self._txt_external)

        self._btn_browse_external = QPushButton("参照...")
        self._btn_browse_external.setFixedWidth(80)
        row_external.addWidget(self._btn_browse_external)
        layout.addLayout(row_external)

        # Reports derived path info
        self._lbl_reports_info = QLabel()
        self._lbl_reports_info.setStyleSheet("color: gray; font-size: 11px;")
        self._update_reports_info()
        layout.addWidget(self._lbl_reports_info)

        # --- Buttons ---
        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        layout.addWidget(self._buttons)

    def _connect_signals(self) -> None:
        self._btn_browse_internal.clicked.connect(self._on_browse_internal)
        self._btn_browse_external.clicked.connect(self._on_browse_external)
        self._txt_internal.textChanged.connect(lambda _: self._update_csv_info())
        self._txt_external.textChanged.connect(lambda _: self._update_reports_info())
        self._buttons.accepted.connect(self._on_ok)
        self._buttons.rejected.connect(self.reject)

    def _update_csv_info(self) -> None:
        text = self._txt_internal.text().strip()
        if text:
            csv_path = Path(text) / _cfg._SOURCE_CSV_RELATIVE
            self._lbl_csv_info.setText(f"  → 元データCSV: {csv_path}")
        else:
            self._lbl_csv_info.setText("  → 元データCSV: (課内データパスを設定してください)")

    def _update_reports_info(self) -> None:
        text = self._txt_external.text().strip()
        if text:
            reports_path = Path(text) / "報告書" / "水質"
            self._lbl_reports_info.setText(f"  → 報告書出力先: {reports_path}")
        else:
            self._lbl_reports_info.setText("  → 報告書出力先: (課外データパスを設定してください)")

    def _on_browse_internal(self) -> None:
        start_dir = str(Path.home())
        if self._txt_internal.text():
            p = Path(self._txt_internal.text())
            if p.exists():
                start_dir = str(p)

        folder = QFileDialog.getExistingDirectory(
            self, "課内データパスを選択", start_dir
        )
        if folder:
            self._txt_internal.setText(folder)

    def _on_browse_external(self) -> None:
        start_dir = str(Path.home())
        if self._txt_external.text():
            p = Path(self._txt_external.text())
            if p.exists():
                start_dir = str(p)

        folder = QFileDialog.getExistingDirectory(
            self, "課外データパスを選択", start_dir
        )
        if folder:
            self._txt_external.setText(folder)

    def _on_ok(self) -> None:
        internal_text = self._txt_internal.text().strip()
        external_text = self._txt_external.text().strip()

        if not internal_text or not external_text:
            QMessageBox.warning(
                self, "入力エラー", "両方のパスを入力してください。"
            )
            return

        internal_path = Path(internal_text)
        external_path = Path(external_text)

        # 課内データパス: must exist (Bunseki app_data)
        if not internal_path.exists():
            QMessageBox.warning(
                self,
                "パスエラー",
                f"課内データパスが見つかりません:\n{internal_path}",
            )
            return

        # Check CSV exists under 課内データパス
        csv_path = internal_path / _cfg._SOURCE_CSV_RELATIVE
        if not csv_path.exists():
            QMessageBox.warning(
                self,
                "パスエラー",
                f"元データCSVが見つかりません:\n{csv_path}\n\n"
                "課内データパスが正しいか確認してください。",
            )
            return

        # 課外データパス: create if not exists
        if not external_path.exists():
            external_path.mkdir(parents=True, exist_ok=True)

        # Save paths
        _cfg.save_internal_path(internal_path)
        _cfg.save_external_path(external_path)
        _cfg.reload_paths(
            new_internal_path=internal_path,
            new_external_path=external_path,
        )

        self.accept()
