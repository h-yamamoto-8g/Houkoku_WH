"""Confirmation dialog before sending notifications.

Shows department list, sample counts, and message preview.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.core.permission_store import DepartmentSummary


class SendConfirmDialog(QDialog):
    """Shows a summary and asks for confirmation before sending."""

    def __init__(
        self,
        summaries: list[DepartmentSummary],
        message: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("送信確認")
        self.setMinimumWidth(450)
        self._setup_ui(summaries, message)

    def _setup_ui(
        self,
        summaries: list[DepartmentSummary],
        message: str,
    ) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        layout.addWidget(QLabel("以下の部署に報告を送信します。よろしいですか？"))

        # Department table
        tbl = QTableWidget()
        tbl.setColumnCount(2)
        tbl.setHorizontalHeaderLabels(["部署名", "サンプル数"])
        tbl.setRowCount(len(summaries))
        tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        for i, s in enumerate(summaries):
            tbl.setItem(i, 0, QTableWidgetItem(s.dept_name))
            tbl.setItem(i, 1, QTableWidgetItem(str(s.sample_count)))

        tbl.resizeColumnsToContents()
        tbl.setMaximumHeight(min(200, 30 + 30 * len(summaries)))
        layout.addWidget(tbl)

        # Message preview
        if message:
            layout.addWidget(QLabel("メッセージ:"))
            msg_lbl = QLabel(message)
            msg_lbl.setWordWrap(True)
            msg_lbl.setStyleSheet(
                "background-color: #ffffff; padding: 8px; "
                "border: 1px solid #e0e0e0; border-radius: 4px;"
            )
            layout.addWidget(msg_lbl)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("送信")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("キャンセル")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
