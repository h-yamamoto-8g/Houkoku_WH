"""Tag-style multi-select widget for JOB numbers."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLayout,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class TagButton(QFrame):
    """A single clickable tag."""

    clicked = Signal()

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self._text = text
        self._selected = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)

        from PySide6.QtWidgets import QLabel

        self._label = QLabel(text)
        layout.addWidget(self._label)

        self._update_style()

    @property
    def text(self) -> str:
        return self._text

    @property
    def selected(self) -> bool:
        return self._selected

    @selected.setter
    def selected(self, value: bool):
        self._selected = value
        self._update_style()

    def _update_style(self):
        if self._selected:
            self.setStyleSheet(
                "TagButton { background: #C8E6C9; border: 1px solid #A5D6A7; border-radius: 4px; }"
                "QLabel { background: transparent; color: #388E3C; font-weight: bold; }"
            )
        else:
            self.setStyleSheet(
                "TagButton { background: transparent; border: 1px solid #BDBDBD; border-radius: 4px; }"
                "QLabel { background: transparent; color: #555; }"
            )

    def mousePressEvent(self, event):  # noqa: N802
        self._selected = not self._selected
        self._update_style()
        self.clicked.emit()


class TagSelector(QWidget):
    """Widget showing tags in a flow layout with multi-select support."""

    selection_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tags: list[TagButton] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(False)
        self._scroll.setFixedHeight(40)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: 1px solid #BDBDBD; border-radius: 6px; }"
        )
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._hbox = QHBoxLayout(self._container)
        self._hbox.setContentsMargins(4, 0, 4, 0)
        self._hbox.setSpacing(6)
        self._hbox.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self._hbox.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
        self._container.setLayout(self._hbox)
        self._scroll.setWidget(self._container)

        layout.addWidget(self._scroll)

    def set_items(self, items: list[str]) -> None:
        """Replace all tags with new items."""
        # Clear existing
        for tag in self._tags:
            self._hbox.removeWidget(tag)
            tag.deleteLater()
        self._tags.clear()

        # Add new
        for text in items:
            tag = TagButton(text, self._container)
            tag.clicked.connect(self.selection_changed.emit)
            self._tags.append(tag)
            self._hbox.addWidget(tag)

        self._container.adjustSize()

    def clear(self) -> None:
        self.set_items([])

    def selected_items(self) -> list[str]:
        return [t.text for t in self._tags if t.selected]

    def select_all(self) -> None:
        for t in self._tags:
            t.selected = True
        self.selection_changed.emit()

    def deselect_all(self) -> None:
        for t in self._tags:
            t.selected = False
        self.selection_changed.emit()
