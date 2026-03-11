"""Loading overlay and worker thread.

Shows a semi-transparent overlay with a message while a background
operation runs in a QThread.
"""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class WorkerThread(QThread):
    """Generic worker thread for background operations."""

    finished = Signal(object)
    error = Signal(str)

    def __init__(self, func: Callable, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._func = func
        self._result = None

    def run(self) -> None:
        try:
            self._result = self._func()
            self.finished.emit(self._result)
        except Exception as e:
            self.error.emit(str(e))


class LoadingOverlay(QWidget):
    """Semi-transparent overlay shown during long operations."""

    def __init__(self, parent: QWidget, message: str = "処理中...") -> None:
        super().__init__(parent)
        self.setStyleSheet(
            "background-color: rgba(245, 247, 250, 200);"
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._lbl = QLabel(message)
        self._lbl.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #555555; "
            "background: transparent;"
        )
        self._lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._lbl)

        self.hide()

    def set_message(self, message: str) -> None:
        self._lbl.setText(message)

    def show_overlay(self) -> None:
        if self.parent():
            self.setGeometry(self.parent().rect())
        self.show()
        self.raise_()

    def hide_overlay(self) -> None:
        self.hide()
