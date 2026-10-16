"""Review what the AI suggests: every change listed, ticked to apply, nothing applied until you say so."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QDialog, QHeaderView, QLabel, QPushButton, QTreeWidget, QTreeWidgetItem, QWidget

from bodega.services.ai.tasks import Change, Result
from bodega.ui.components.widgets import button_row, hint, primary_button, vbox
from bodega.ui.style import theme, tokens
from bodega.ui.window.tables import RowPainter

MAX_PROBLEMS_SHOWN = 4


class ReviewDialog(QDialog):
    def __init__(self, title: str, result: Result, names: dict[str, str], parent: QWidget | None = None):
        super().__init__(parent)
        self.result = result
        self.setWindowTitle(title)
        self.setMinimumWidth(tokens.DIALOG_W_XWIDE)
        self.resize(tokens.REVIEW_W, tokens.PAGE_DIALOG_MIN_H)
        lay = vbox(self, tokens.SPACE_5, tokens.SPACE_3)
        t = QLabel(title)
        t.setObjectName("DialogTitle")
        lay.addWidget(t)
        n = len(result.changes)
        lay.addWidget(
            hint(
                f"{n} suggestion{'s' if n != 1 else ''}. Untick any you don't want."
                if n
                else "No changes to suggest."
            )
        )

        self.list = QTreeWidget()
        self.list.setObjectName("Table")  # rows like the main table's
        self.list.setItemDelegate(RowPainter(self.list))
        self.list.setHeaderLabels(["Piece", "What", "Now", "Suggested", "From"])
        self.list.setRootIsDecorated(False)
        self.list.setUniformRowHeights(True)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.setSelectionMode(QTreeWidget.SelectionMode.NoSelection)
        self.rows: list[tuple[QTreeWidgetItem, Change]] = []
        for c in result.changes:
            row = QTreeWidgetItem([names.get(c.item_id, "?"), c.label, c.old or "—", c.new, c.why])
            row.setCheckState(0, Qt.CheckState.Checked)
            row.setSizeHint(0, QSize(0, tokens.TABLE_ROW_H))
            for col in range(5):
                row.setToolTip(col, theme.plain_tip(row.text(col)))
            self.list.addTopLevelItem(row)
            self.rows.append((row, c))
        head = self.list.header()
        head.setStretchLastSection(False)
        for col, w in enumerate(tokens.REVIEW_COL_W):
            if w:
                self.list.setColumnWidth(col, w)
        head.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # Suggested takes the room
        self.list.itemChanged.connect(lambda *_a: self._count())
        lay.addWidget(self.list, 1)

        if result.problems:
            shown = result.problems[:MAX_PROBLEMS_SHOWN]
            more = len(result.problems) - len(shown)
            lay.addWidget(hint("\n".join(shown) + (f"\n…and {more} more." if more > 0 else "")))

        buttons = button_row()
        every = QPushButton("Select All")
        every.clicked.connect(lambda: self._tick_all(True))
        none = QPushButton("Select None")
        none.clicked.connect(lambda: self._tick_all(False))
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        self.go = primary_button()
        self.go.setDefault(True)
        self.go.clicked.connect(self.accept)
        buttons.insertWidget(0, every)
        buttons.insertWidget(1, none)
        buttons.addWidget(cancel)
        buttons.addWidget(self.go)
        lay.addLayout(buttons)
        self._count()

    def chosen(self) -> list[Change]:
        return [c for row, c in self.rows if row.checkState(0) == Qt.CheckState.Checked]

    def _tick_all(self, on: bool) -> None:
        state = Qt.CheckState.Checked if on else Qt.CheckState.Unchecked
        for row, _c in self.rows:
            row.setCheckState(0, state)

    def _count(self) -> None:
        n = len(self.chosen())
        self.go.setText(f"Apply {n} Change{'s' if n != 1 else ''}" if n else "Apply")
        self.go.setEnabled(n > 0)
