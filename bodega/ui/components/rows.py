"""Grouped rows (the standard's §4.12 and G.12): Settings' rounded cards of rows, each group with a small name above
its card and at most one short note below. A row is ROW_H tall: its label on the left, and on the right one of

- a value (read only, in secondary words): value()
- a control (a switch, a pop-up hugging its value, a segmented control, a field of its kind's width): control(), switch()
- an action on the group's thing (its words in the accent across the row; red for one that removes): action()

Hairlines run between rows from where the label starts to the card's trailing edge, none after the last. No leading
icons (a group has them on every row or none: Bodega's have none)."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPen
from PySide6.QtWidgets import QComboBox, QFrame, QLabel, QLineEdit, QPushButton, QSizePolicy, QWidget

from bodega.ui.components.widgets import ElidedLabel, ToggleRow, hbox, vbox
from bodega.ui.style import theme, tokens

QWIDGETSIZE_MAX = (1 << 24) - 1  # (Qt's "no maximum")


class _Card(QFrame):
    """The group's card: its rows stacked, a hairline under each but the last."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("GroupCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.lay = vbox(self, 0, 0)
        self.rows: list[QWidget] = []  # (its own list: a layout is never asked for its items)

    def add(self, row: QWidget) -> None:
        self.rows.append(row)
        self.lay.addWidget(row)

    def paintEvent(self, e):
        super().paintEvent(e)
        shown = [r for r in self.rows if not r.isHidden()]
        p = QPainter(self)
        pen = QPen(theme.qcolor(tokens.BORDER))
        pen.setWidth(tokens.HAIRLINE)
        p.setPen(pen)
        for r in shown[:-1]:
            y = r.geometry().bottom()
            p.drawLine(tokens.GROUP_INSET, y, self.width(), y)
        p.end()


class Group(QWidget):
    """A group of rows: `name` above its card (none: no name), `note` below it (one short line, if any)."""

    def __init__(self, name: str = "", note: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        lay = vbox(self, 0, 0)
        self.name = QLabel(name)
        self.name.setObjectName("GroupName")
        self.name.setVisible(bool(name))
        self.name.setContentsMargins(tokens.GROUP_INSET, 0, tokens.GROUP_INSET, tokens.SPACE_2)
        lay.addWidget(self.name)
        self.card = _Card()
        lay.addWidget(self.card)
        self.note = QLabel(note)
        self.note.setObjectName("GroupNote")
        self.note.setWordWrap(True)
        self.note.setVisible(bool(note))
        self.note.setContentsMargins(tokens.GROUP_INSET, tokens.SPACE_2, tokens.GROUP_INSET, 0)
        lay.addWidget(self.note)

    def _row(self, label: str = "") -> tuple[QWidget, object]:
        row = QWidget()
        row.setObjectName("GroupRow")
        row.setFixedHeight(tokens.ROW_H)
        lay = hbox(row, (tokens.GROUP_INSET, 0, tokens.GROUP_INSET, 0), tokens.SPACE_4)
        if label:
            words = QLabel(label)
            words.setObjectName("RowLabel")
            lay.addWidget(words)
        self.card.add(row)
        return row, lay

    def value(self, label: str, text: str, middle: bool = False) -> ElidedLabel:
        """A value, read only (`middle`: cut in the middle when it's long, as a file's path is)."""
        _row, lay = self._row(label)
        mode = Qt.TextElideMode.ElideMiddle if middle else Qt.TextElideMode.ElideRight
        v = ElidedLabel(text, mode=mode)
        v.setObjectName("RowValue")
        v.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        v.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(v, 1)
        return v

    def control(self, label: str, w: QWidget) -> QWidget:
        """A control at the row's trailing edge, at its own size: a pop-up hugs its value, a text field is its kind's
        width (widgets.sized: a name's or a rate's, so fields of a kind line up down the rows)."""
        _row, lay = self._row(label)
        lay.addStretch(1)
        lay.addWidget(w)
        for f in (w, *w.findChildren(QWidget)):
            if isinstance(f, (QLineEdit, QComboBox)) and f.maximumWidth() < QWIDGETSIZE_MAX:
                f.setMinimumWidth(f.maximumWidth())
        w.setAccessibleName(w.accessibleName() or label)
        return w

    def switch(self, label: str, on: bool) -> ToggleRow:
        """An on/off setting: the whole row is the switch."""
        _row, lay = self._row()
        t = ToggleRow(label, on)
        lay.addWidget(t)
        return t

    def action(self, text: str, run: Callable[[], None], danger: bool = False) -> QPushButton:
        """An action on the group's thing ("Sign Out", "Back Up…"): its words in the accent across the row, red
        for one that removes."""
        _row, lay = self._row()
        b = QPushButton(text)
        b.setObjectName("RowAction")
        b.setProperty("danger", danger)
        b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        b.clicked.connect(lambda _c=False: run())
        lay.setContentsMargins(0, 0, 0, 0)  # (the button is the whole row: its words keep the inset)
        lay.addWidget(b)
        return b
