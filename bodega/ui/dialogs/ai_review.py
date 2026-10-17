"""Review what the AI suggests: every change listed, ticked to apply, nothing applied until you say so. A page in
place of the one beside the sidebar (the standard's 4.9: a table is too much for a dialog), its title, Cancel and
Apply across its top as a page's are."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHeaderView,
    QPushButton,
    QSizePolicy,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
)

from bodega.services.ai.tasks import Change, Result
from bodega.ui.components import sheet
from bodega.ui.components.widgets import ElidedLabel, hbox, hint, primary_button, vbox
from bodega.ui.style import theme, tokens
from bodega.ui.window.tables import ID, TICK, RowPainter

MAX_PROBLEMS_SHOWN = 4
SUGGESTED, FROM = 4, 5  # (columns: the tick, Piece, What, Now, Suggested, From)


class ReviewDialog(QDialog):
    SHEET_KIND = "page"  # (components/sheet.py: in place of the page beside the sidebar)
    SHEET_OUTSIDE = False  # (a click beside it never drops what your AI suggested)

    def __init__(self, title: str, result: Result, names: dict[str, str], parent: QWidget | None = None):
        super().__init__(parent)
        sheet.prepare(self)  # shown over its window (components/sheet.py)
        self.result = result
        self.setWindowTitle(title)
        self.resize(tokens.REVIEW_W, tokens.PAGE_DIALOG_MIN_H)  # (where it can't be a page, a window this size)
        outer = vbox(self, 0, 0)
        bar = QFrame()  # a page's top: its title, then Cancel and Apply
        bar.setObjectName("Toolbar")
        bar.setFixedHeight(tokens.TOOLBAR_H)
        top = hbox(bar, (tokens.PAGE_INSET, 0, tokens.PAGE_INSET, 0), tokens.SPACE_2)
        t = ElidedLabel(title)
        t.setObjectName("PageTitle")
        t.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        top.addWidget(t)
        top.addStretch(1)
        outer.addWidget(bar)
        lay = vbox(margins=(tokens.PAGE_INSET, 0, tokens.PAGE_INSET, tokens.SPACE_5), spacing=tokens.SPACE_3)
        outer.addLayout(lay, 1)
        n = len(result.changes)
        unsure = sum(1 for c in result.changes if c.unsure)
        guess = (
            f" The {unsure} your AI wasn't sure of are left unticked."
            if unsure > 1
            else (" The one your AI wasn't sure of is left unticked." if unsure else "")
        )
        above = hbox(spacing=tokens.SPACE_2)  # what's suggested, and ticking them all or none, above the list
        above.addWidget(
            hint(
                f"{n} suggestion{'s' if n != 1 else ''}. Untick any you don't want.{guess}"
                if n
                else "No changes to suggest."
            ),
            1,
        )
        every = QPushButton("Select All")
        every.setObjectName("Ghost")
        every.clicked.connect(lambda: self._tick_all(True))
        none = QPushButton("Select None")
        none.setObjectName("Ghost")
        none.clicked.connect(lambda: self._tick_all(False))
        above.addWidget(every)
        above.addWidget(none)
        lay.addLayout(above)

        self.list = QTreeWidget()
        self.list.setObjectName("Table")  # rows like the main table's
        self.list.setItemDelegate(RowPainter(self.list))
        self.list.setHeaderLabels(["", "Piece", "What", "Now", "Suggested", "From"])
        self.list.setRootIsDecorated(False)
        self.list.setUniformRowHeights(True)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # ticked is chosen, as in every list (G.10.3): a click on a row, or Space, ticks or unticks it
        self.list.setSelectionMode(QTreeWidget.SelectionMode.MultiSelection)
        self.rows: list[tuple[QTreeWidgetItem, Change]] = []
        for n_row, c in enumerate(result.changes):
            source = f"{c.why} · Not Sure" if c.unsure else c.why  # (the standard's 14.8: a guess says so)
            row = QTreeWidgetItem(["", names.get(c.item_id, "?"), c.label, c.old or "—", c.new, source])
            row.setData(TICK, ID, str(n_row))  # (a record row: it has a tick)
            if c.unsure:
                row.setForeground(FROM, theme.qcolor(tokens.WARN))
            row.setSizeHint(0, QSize(0, tokens.TABLE_ROW_H))
            for col in range(1, FROM + 1):
                row.setToolTip(col, theme.plain_tip(row.text(col)))
            self.list.addTopLevelItem(row)
            row.setSelected(not c.unsure)
            self.rows.append((row, c))
        head = self.list.header()
        head.setStretchLastSection(False)
        for col, w in enumerate((tokens.TICK_W, *tokens.REVIEW_COL_W)):
            if w:
                self.list.setColumnWidth(col, w)
        head.setSectionResizeMode(SUGGESTED, QHeaderView.ResizeMode.Stretch)  # Suggested takes the room
        self.list.itemSelectionChanged.connect(self._count)
        lay.addWidget(self.list, 1)

        if result.problems:
            shown = result.problems[:MAX_PROBLEMS_SHOWN]
            more = len(result.problems) - len(shown)
            lay.addWidget(hint("\n".join(shown) + (f"\n…and {more} more." if more > 0 else "")))

        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        self.go = primary_button()
        self.go.setDefault(True)
        self.go.clicked.connect(self.accept)
        top.addWidget(cancel)
        top.addWidget(self.go)
        self.list.setFocus()
        self._count()

    def chosen(self) -> list[Change]:
        return [c for row, c in self.rows if row.isSelected()]

    def _tick_all(self, on: bool) -> None:
        for row, _c in self.rows:
            row.setSelected(on)

    def _count(self) -> None:
        n = len(self.chosen())
        self.go.setText(f"Apply {n} Change{'s' if n != 1 else ''}" if n else "Apply")
        self.go.setEnabled(n > 0)
