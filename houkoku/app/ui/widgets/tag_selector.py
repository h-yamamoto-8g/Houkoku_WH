"""Tag-style multi-select widget for JOB numbers."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLayout,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class _FlowLayout(QLayout):
    """Simple flow layout that wraps items to the next line."""

    def __init__(self, parent=None, spacing=6):
        super().__init__(parent)
        self._items = []
        self._spacing = spacing

    def addItem(self, item):  # noqa: N802
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):  # noqa: N802
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):  # noqa: N802
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def sizeHint(self):  # noqa: N802
        return self.minimumSize()

    def minimumSize(self):  # noqa: N802
        from PySide6.QtCore import QSize

        return QSize(0, self._do_layout(self.geometry(), dry_run=True))

    def setGeometry(self, rect):  # noqa: N802
        super().setGeometry(rect)
        self._do_layout(rect, dry_run=False)

    def hasHeightForWidth(self):  # noqa: N802
        return True

    def heightForWidth(self, width):  # noqa: N802
        from PySide6.QtCore import QRect

        return self._do_layout(QRect(0, 0, width, 0), dry_run=True)

    def _do_layout(self, rect, dry_run=False):
        x = rect.x()
        y = rect.y()
        line_height = 0

        for item in self._items:
            size = item.sizeHint()
            if x + size.width() > rect.right() and line_height > 0:
                x = rect.x()
                y += line_height + self._spacing
                line_height = 0
            if not dry_run:
                from PySide6.QtCore import QRect as QR

                item.setGeometry(QR(x, y, size.width(), size.height()))
            x += size.width() + self._spacing
            line_height = max(line_height, size.height())

        return y + line_height - rect.y()


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
                "TagButton { background: #2196F3; border-radius: 4px; }"
                "QLabel { color: white; font-weight: bold; }"
            )
        else:
            self.setStyleSheet(
                "TagButton { background: #E0E0E0; border-radius: 4px; }"
                "QLabel { color: #333; }"
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
        self._scroll.setWidgetResizable(True)
        self._scroll.setMaximumHeight(80)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._container = QWidget()
        self._flow = _FlowLayout(self._container, spacing=6)
        self._container.setLayout(self._flow)
        self._scroll.setWidget(self._container)

        layout.addWidget(self._scroll)

    def set_items(self, items: list[str]) -> None:
        """Replace all tags with new items."""
        # Clear existing
        for tag in self._tags:
            self._flow.removeWidget(tag)
            tag.deleteLater()
        self._tags.clear()

        # Add new
        for text in items:
            tag = TagButton(text, self._container)
            tag.clicked.connect(self.selection_changed.emit)
            self._tags.append(tag)
            self._flow.addWidget(tag)

        self._container.updateGeometry()

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
