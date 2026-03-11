"""Setup dialog for selecting the data folder path.

Shown on first launch or when DATA_PATH is not found.
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
    QPushButton,
    QVBoxLayout,
)

import app.config as _cfg


class SetupRootDialog(QDialog):
    """Dialog for setting the data folder path."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("データフォルダ設定")
        self.setMinimumWidth(500)
        self._selected_path: str = ""
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        layout.addWidget(
            QLabel(
                "水質報告ツールのデータフォルダを指定してください。\n"
                "SharePoint同期フォルダ内の「報告ツール」フォルダを選択します。"
            )
        )

        row = QHBoxLayout()
        self._txt_path = QLineEdit()
        self._txt_path.setPlaceholderText("フォルダパスを選択...")

        # Pre-fill if we have a saved path
        if _cfg.DATA_PATH is not None:
            self._txt_path.setText(str(_cfg.DATA_PATH))
            self._selected_path = str(_cfg.DATA_PATH)

        row.addWidget(self._txt_path)

        self._btn_browse = QPushButton("参照...")
        self._btn_browse.setFixedWidth(80)
        row.addWidget(self._btn_browse)
        layout.addLayout(row)

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        layout.addWidget(self._buttons)

    def _connect_signals(self) -> None:
        self._btn_browse.clicked.connect(self._on_browse)
        self._txt_path.textChanged.connect(self._on_text_changed)
        self._buttons.accepted.connect(self._on_ok)
        self._buttons.rejected.connect(self.reject)

    def _on_browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "データフォルダを選択", str(Path.home())
        )
        if folder:
            self._txt_path.setText(folder)

    def _on_text_changed(self, text: str) -> None:
        self._selected_path = text

    def _on_ok(self) -> None:
        if not self._selected_path:
            return

        path = Path(self._selected_path)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)

        _cfg.save_data_path(path)
        _cfg.reload_paths(path)
        self.accept()

    def selected_path(self) -> Path:
        return Path(self._selected_path)
