"""The page window's options (the standard's C-53 and C-61), beside the pages in grouped rows: Paper, Letterhead and a
Note for every page, and on a list (the inventory, the rate card) its Columns (tick each, drag to order) and Filters
(a card each: the column, then a value or a From and a To; Remove Filter in red; Add Filter under them). Every
change redraws the pages at once (`changed`), and is kept as your last choice for that kind of page; Use as This
Profile's Default keeps it for a page you haven't set yet. What the options mean is core/pageopts.py's."""

from __future__ import annotations

from PySide6.QtCore import QRect, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QStyledItemDelegate,
    QWidget,
)

from bodega.core import pageopts
from bodega.core.model import Item
from bodega.ui.components.rows import Group
from bodega.ui.components.widgets import FitScroll, combo, sized, vbox
from bodega.ui.style import theme, tokens

LISTS = ("inventory", "ratecard")  # the pages that are lists: they have columns and filters


class _GripRow(QStyledItemDelegate):
    """A column's row: its tick and name, and the grip it's dragged by at the trailing edge."""

    def paint(self, painter, option, index) -> None:
        super().paint(painter, option, index)
        r = option.rect
        theme.draw_grip(
            painter, QRect(r.right() - tokens.GROUP_INSET - tokens.GRIP_W, r.top(), tokens.GRIP_W, r.height())
        )


class PageOptionsPanel(FitScroll):
    changed = Signal()  # an option changed: the pages redraw
    default_wanted = Signal()  # Use as This Profile's Default

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("PageOptions")
        self.setFixedWidth(tokens.PAGE_OPTIONS_W)
        self.kind = ""
        self.opts = pageopts.PageOptions()
        self.items: list[Item] = []
        self._building = False
        self.body = QWidget()
        self.lay = vbox(self.body, tokens.SPACE_4, tokens.GROUP_GAP)
        self.setWidget(self.body)

    def show_for(self, kind: str, opts: pageopts.PageOptions, items: list[Item]) -> None:
        """The options for this kind of page, as they are now; `items` the gear its filters can pick from."""
        self.kind, self.opts, self.items = kind, opts, items
        self._build()

    # Building
    def _build(self) -> None:
        self._building = True
        while self.lay.count():
            w = self.lay.takeAt(0).widget()
            if w is not None:
                w.hide()  # (hidden first: a part thrown away while its window stays open)
                w.deleteLater()
        o = self.opts
        page = Group("Page")
        self.paper = page.control(
            "Paper", sized(combo([(k, v[0], "") for k, v in pageopts.PAPERS.items()], o.paper), "popup")
        )
        self.paper.currentIndexChanged.connect(lambda _i: self._set(paper=self.paper.currentData()))
        self.letterhead = page.switch("Your Logo and Contact", o.letterhead)
        self.letterhead.setToolTip("Off for paper that has your letterhead printed on it")
        self.letterhead.toggled.connect(lambda on: self._set(letterhead=on))
        self.note = QLineEdit(o.note)
        self.note.setFixedWidth(tokens.PAGE_OPTIONS_FIELD_W)  # (its width on this narrow surface)
        page.control("Note", self.note)
        self.note.setPlaceholderText("Optional")
        self.note.setMaxLength(pageopts.NOTE_MAX)
        self.note.textEdited.connect(lambda t: self._set(note=t))
        self.lay.addWidget(page)
        if self.kind in LISTS:
            self._build_columns()
            self._build_filters()
        mine = Group()
        mine.action("Use as This Profile's Default", self.default_wanted.emit)
        self.lay.addWidget(mine)
        self.lay.addStretch(1)
        self._building = False

    def _build_columns(self) -> None:
        known, _shown = pageopts.COLUMNS[self.kind]
        shown = pageopts.columns(self.kind, self.opts)
        g = Group("Columns", "Tick the ones to print; drag to put them in order.")
        self.cols = QListWidget()
        self.cols.setObjectName("ColumnList")
        self.cols.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)  # (drag to order, by the grip)
        self.cols.setItemDelegate(_GripRow(self.cols))
        self.cols.setFrameShape(QListWidget.Shape.NoFrame)
        self.cols.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        for key in [*shown, *(k for k in known if k not in shown)]:
            row = QListWidgetItem(known[key][0])
            row.setData(Qt.ItemDataRole.UserRole, key)
            flags = row.flags() | Qt.ItemFlag.ItemIsDragEnabled
            if key != pageopts.NAME_COLUMN:  # (what each row is: always printed)
                flags |= Qt.ItemFlag.ItemIsUserCheckable
            row.setFlags(flags & ~Qt.ItemFlag.ItemIsDropEnabled)
            row.setCheckState(Qt.CheckState.Checked if key in shown else Qt.CheckState.Unchecked)
            self.cols.addItem(row)
        self.cols.setFixedHeight(tokens.ROW_H * self.cols.count())
        self.cols.itemChanged.connect(lambda _r: self._columns_changed())
        self.cols.model().rowsMoved.connect(lambda *_a: self._columns_changed())
        g.card.add(self.cols)  # (a list in a card is its content, edge to edge)
        self.lay.addWidget(g)

    def _build_filters(self) -> None:
        for n, f in enumerate(self.opts.filters):
            g = Group("Filter" if n == 0 else "")
            col = sized(combo([(k, v[0], "") for k, v in pageopts.FILTERS.items()], f.col), "popup")
            g.control("Column", col)
            col.currentIndexChanged.connect(lambda _i, n=n, col=col: self._filter_col(n, col.currentData()))
            if f.is_range:
                lo = sized(QLineEdit(f.lo), "short")
                lo.setPlaceholderText("Any")
                g.control("From", lo)
                hi = sized(QLineEdit(f.hi), "short")
                hi.setPlaceholderText("Any")
                g.control("To", hi)
                lo.textEdited.connect(lambda t, n=n: self._filter(n, lo=t))
                hi.textEdited.connect(lambda t, n=n: self._filter(n, hi=t))
            else:
                values = pageopts.values(self.items, f.col)
                pick = sized(combo([("", "Any", ""), *((v, v, "") for v in values)], f.lo), "popup")
                g.control("Is", pick)
                pick.currentIndexChanged.connect(
                    lambda _i, n=n, pick=pick: self._filter(n, lo=pick.currentData() or "")
                )
            g.action("Remove Filter", lambda n=n: self._remove_filter(n), danger=True)
            self.lay.addWidget(g)
        add = Group("Filter" if not self.opts.filters else "")
        add.action("Add Filter", self._add_filter)
        self.lay.addWidget(add)

    # Changes
    def _set(self, **changes) -> None:
        if self._building:
            return
        for k, v in changes.items():
            setattr(self.opts, k, v)
        self.changed.emit()

    def _columns_changed(self) -> None:
        if self._building:
            return
        picked = []
        for i in range(self.cols.count()):
            row = self.cols.item(i)
            if row.data(Qt.ItemDataRole.UserRole) == pageopts.NAME_COLUMN or row.checkState() == Qt.CheckState.Checked:
                picked.append(row.data(Qt.ItemDataRole.UserRole))
        self._set(columns=picked)

    def _filter(self, n: int, **changes) -> None:
        if self._building or n >= len(self.opts.filters):
            return
        for k, v in changes.items():
            setattr(self.opts.filters[n], k, v)
        self.changed.emit()

    def _filter_col(self, n: int, col: str) -> None:
        """Another column: what it keeps starts over (a group's name means nothing to a price)."""
        if self._building:
            return
        self.opts.filters[n] = pageopts.Filter(col)
        self.changed.emit()
        self._rebuild_soon()

    def _add_filter(self) -> None:
        self.opts.filters.append(pageopts.Filter())
        self.changed.emit()
        self._rebuild_soon()

    def _remove_filter(self, n: int) -> None:
        if n < len(self.opts.filters):
            del self.opts.filters[n]
        self.changed.emit()
        self._rebuild_soon()

    def _rebuild_soon(self) -> None:
        """The rows change once the click that asked is over (a row is never thrown away inside its own click)."""
        from PySide6.QtCore import QTimer

        QTimer.singleShot(0, self, self._build)
