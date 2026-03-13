"""Loading overlay and worker thread.

Shows a semi-transparent overlay with a spinner animation and message
while a background operation runs in a QThread.
Follows the Bunseki_ccc loading screen pattern.
"""

from __future__ import annotations

import math
from typing import Callable, Optional

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPen
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


class _SpinnerWidget(QWidget):
    """Animated circular spinner with fading dots."""

    _DOT_COUNT = 12
    _DOT_RADIUS = 4
    _CIRCLE_RADIUS = 24

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._angle_offset = 0
        self.setFixedSize(
            self._CIRCLE_RADIUS * 2 + self._DOT_RADIUS * 2 + 4,
            self._CIRCLE_RADIUS * 2 + self._DOT_RADIUS * 2 + 4,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._timer = QTimer(self)
        self._timer.setInterval(80)
        self._timer.timeout.connect(self._step)

    def start(self) -> None:
        self._angle_offset = 0
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def _step(self) -> None:
        self._angle_offset = (self._angle_offset + 1) % self._DOT_COUNT
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = self.width() / 2
        cy = self.height() / 2

        for i in range(self._DOT_COUNT):
            angle = 2 * math.pi * i / self._DOT_COUNT - math.pi / 2
            x = cx + self._CIRCLE_RADIUS * math.cos(angle)
            y = cy + self._CIRCLE_RADIUS * math.sin(angle)

            # Fade: the dot closest to _angle_offset is most opaque
            distance = (i - self._angle_offset) % self._DOT_COUNT
            opacity = max(0.15, 1.0 - distance / self._DOT_COUNT)

            color = QColor(74, 144, 217)  # #4a90d9
            color.setAlphaF(opacity)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawEllipse(
                int(x - self._DOT_RADIUS),
                int(y - self._DOT_RADIUS),
                self._DOT_RADIUS * 2,
                self._DOT_RADIUS * 2,
            )

        painter.end()


class LoadingOverlay(QWidget):
    """Semi-transparent overlay with spinner, shown during long operations."""

    def __init__(self, parent: QWidget, message: str = "処理中...") -> None:
        super().__init__(parent)
        self.setStyleSheet("background-color: rgba(245, 247, 250, 220);")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

        # Outer layout fills the entire overlay and centres the card
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addStretch(1)

        # Card: rounded white box with spinner + message
        card = QWidget(self)
        card.setFixedSize(220, 140)
        card.setStyleSheet(
            "background: #ffffff; border-radius: 12px;"
            "border: 1px solid #e0e0e0;"
        )
        card_layout = QVBoxLayout(card)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.setSpacing(14)

        # Spinner
        self._spinner = _SpinnerWidget(card)
        card_layout.addWidget(self._spinner, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Message
        self._lbl = QLabel(message)
        self._lbl.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #555555; "
            "background: transparent; border: none;"
        )
        self._lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self._lbl)

        outer.addWidget(card, alignment=Qt.AlignmentFlag.AlignHCenter)
        outer.addStretch(1)

        # Delayed-show timer: only display overlay if operation takes > threshold
        self._delay_timer = QTimer(self)
        self._delay_timer.setSingleShot(True)
        self._delay_timer.timeout.connect(self._do_show)
        self._pending = False

        self.hide()

    def set_message(self, message: str) -> None:
        """Update the overlay message text."""
        self._lbl.setText(message)

    def show_overlay(self) -> None:
        """Show the overlay immediately and start the spinner."""
        self._delay_timer.stop()
        self._pending = False
        self._do_show()

    def show_overlay_delayed(self, delay_ms: int = 500) -> None:
        """Show the overlay only if not cancelled within delay_ms.

        Call hide_overlay() before the timer fires to skip showing entirely.
        Useful for operations that may finish quickly (<500ms).
        """
        self._pending = True
        self._delay_timer.start(delay_ms)

    def hide_overlay(self) -> None:
        """Hide the overlay and stop the spinner. Cancels pending delayed show."""
        self._delay_timer.stop()
        self._pending = False
        self._spinner.stop()
        self.hide()

    def _do_show(self) -> None:
        """Internal: actually show the overlay."""
        self._pending = False
        p = self.parent()
        if p:
            # For QMainWindow, cover the centralWidget area (not the frame)
            from PySide6.QtWidgets import QMainWindow

            if isinstance(p, QMainWindow) and p.centralWidget():
                target = p.centralWidget()
                # Map centralWidget geometry to MainWindow coordinates
                pos = target.mapTo(p, target.rect().topLeft())
                self.setGeometry(
                    pos.x(), pos.y(), target.width(), target.height()
                )
            else:
                self.setGeometry(p.rect())
        self._spinner.start()
        self.show()
        self.raise_()
