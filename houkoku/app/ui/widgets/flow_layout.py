"""Flow layout that arranges widgets horizontally with wrapping.

Based on the Qt FlowLayout example, adapted for PySide6.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import QLayout, QLayoutItem, QSizePolicy, QWidget


class FlowLayout(QLayout):
    """Layout that arranges child widgets left-to-right, wrapping to next row."""

    def __init__(self, parent: QWidget | None = None, h_spacing: int = 6, v_spacing: int = 6) -> None:
        super().__init__(parent)
        self._h_spacing = h_spacing
        self._v_spacing = v_spacing
        self._items: list[QLayoutItem] = []

    def addItem(self, item: QLayoutItem) -> None:
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int) -> QLayoutItem | None:
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int) -> QLayoutItem | None:
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientation:
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        size += QSize(m.left() + m.right(), m.top() + m.bottom())
        return size

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        m = self.contentsMargins()
        effective = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x = effective.x()
        y = effective.y()
        row_height = 0

        for item in self._items:
            wid = item.widget()
            if wid is None:
                continue
            item_size = item.sizeHint()
            next_x = x + item_size.width() + self._h_spacing
            if next_x - self._h_spacing > effective.right() and row_height > 0:
                x = effective.x()
                y = y + row_height + self._v_spacing
                next_x = x + item_size.width() + self._h_spacing
                row_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item_size))

            x = next_x
            row_height = max(row_height, item_size.height())

        return y + row_height - rect.y() + m.bottom()
