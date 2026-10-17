"""The big tables in the middle: gear, kits and rentals. Click a row to edit it on the right.

Every list leads with a tick on every row (the standard's 4.3 and 4.17): a click opens a row, its tick (or ⌘-click,
or Space) ticks it, Shift-click ticks a range, ⌘A ticks every row showing, and the heading's tick ticks them all
or none. What's ticked is what Delete, a drag or the selection bar acts on (chosen_ids()).

Every column sorts; the grip column, at a gear row's trailing edge, is your own order (drag a row by its grip to
change it). Gear is divided
by department, group or company (or not at all), each divider with its totals; click one to fold it. Gear
that goes with a piece is listed under it, one step in (the standard's G.11): the piece's chevron opens and
closes it (remembered), its figures are it with all of that, and its tick ticks it all. A search opens the
piece whose gear it finds. Right-click the column titles to choose the columns.
"""

from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QItemSelectionModel,
    QPoint,
    QPointF,
    QRect,
    QRectF,
    QSize,
    Qt,
    QTimer,
    QVariantAnimation,
    Signal,
)
from PySide6.QtGui import QColor, QFontMetricsF, QKeySequence, QPainter, QPen, QPixmap, QRegion
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFrame,
    QHeaderView,
    QMenu,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QToolTip,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
)

from bodega.core import dates, earnings, money, pricing, search
from bodega.core.model import RENTAL_WORDS, Business, Item
from bodega.core.store import Library
from bodega.ui.components import access, photos
from bodega.ui.components.widgets import TickMenu, vbox
from bodega.ui.style import theme, tokens
from bodega.ui.window.lift import Lift


def words_inset(view: QTreeWidget) -> int:
    """How far a cell's words sit inside the cell: its padding, then the style's own margin before the words."""
    opt = QStyleOptionViewItem()
    opt.initFrom(view.viewport())
    opt.rect = QRect(0, 0, tokens.SEARCH_W, tokens.TABLE_ROW_H)
    opt.features |= QStyleOptionViewItem.ViewItemFeature.HasDisplay
    opt.text = "x"
    style = view.style()
    text = style.subElementRect(QStyle.SubElement.SE_ItemViewItemText, opt, view)
    return text.left() + style.pixelMetric(QStyle.PixelMetric.PM_FocusFrameHMargin, None, view) + 1


ID = Qt.ItemDataRole.UserRole
SORT = Qt.ItemDataRole.UserRole + 1
HAY = Qt.ItemDataRole.UserRole + 2
HEAD = Qt.ItemDataRole.UserRole + 3  # a divider row: its place in the list
ATTACHED = Qt.ItemDataRole.UserRole + 4  # attached gear: only shown when searching
DEP = Qt.ItemDataRole.UserRole + 5  # a divider's department
GRP = Qt.ItemDataRole.UserRole + 6  # a group divider's group (None on a department divider)
DOT = Qt.ItemDataRole.UserRole + 12  # a status cell: its dot's color (the word stays in the text color)

RIGHT = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
CENTER = Qt.AlignmentFlag.AlignCenter


TICK = 0  # every list's first column: its ticks
SHIFT, CMD = Qt.KeyboardModifier.ShiftModifier, Qt.KeyboardModifier.ControlModifier  # (⌘ on a Mac)


def paint_tick(painter: QPainter, rect, state: str) -> None:
    """A tick box (G.10.3's `check`), centred in `rect`: "off", "on" or "some" (a dash: some rows ticked)."""
    size = tokens.INDICATOR
    box = QRectF(rect.center().x() - size / 2 + 0.5, rect.center().y() - size / 2 + 0.5, size - 1, size - 1)
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    if state == "off":
        painter.setPen(QPen(theme.qcolor(tokens.BORDER_CHECK), 1))
        painter.setBrush(theme.qcolor(tokens.CARD))
        painter.drawRoundedRect(box, tokens.RADIUS_XS, tokens.RADIUS_XS)
    else:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(theme.qcolor(tokens.ACCENT_FILL))
        painter.drawRoundedRect(box, tokens.RADIUS_XS, tokens.RADIUS_XS)
        pen = QPen(theme.qcolor(tokens.ON_ACCENT), tokens.CHECK_STROKE)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        c, u = box.center(), size / 16
        if state == "some":
            painter.drawLine(QPointF(c.x() - 4 * u, c.y()), QPointF(c.x() + 4 * u, c.y()))
        else:
            painter.drawPolyline(
                [
                    QPointF(c.x() - 4 * u, c.y()),
                    QPointF(c.x() - 1.5 * u, c.y() + 2.5 * u),
                    QPointF(c.x() + 4 * u, c.y() - 3 * u),
                ]
            )
    painter.restore()


class TickHeader(QHeaderView):
    """The headings, led by the tick column's box: ticked when every row showing is, a dash when some are. A click
    on it ticks every row showing, or none (it never sorts)."""

    def __init__(self, table: Table):
        super().__init__(Qt.Orientation.Horizontal, table)
        self.table = table

    def _plus(self) -> int:
        """The heading that holds the + for choosing columns (the last one showing), or -1 on a list without."""
        if not getattr(self.table, "chooses_columns", False):
            return -1
        for v in range(self.count() - 1, -1, -1):
            if not self.isSectionHidden(self.logicalIndex(v)):
                return self.logicalIndex(v)
        return -1

    def paintSection(self, painter, rect, logical) -> None:
        painter.save()
        super().paintSection(painter, rect, logical)
        painter.restore()
        if logical == TICK and self.table.has_rows():
            paint_tick(painter, rect, self.table.tick_state())
        elif logical == self._plus():  # the standard's 4.3: + at the end of the headings chooses the columns
            size = tokens.ICON_SM
            pix = theme.icon("plus", theme.MUTED, size).pixmap(QSize(size, size), self.devicePixelRatioF())
            painter.drawPixmap(QPointF(rect.center().x() - size / 2 + 0.5, rect.center().y() - size / 2), pix)

    def _special(self, e) -> int:
        at = self.logicalIndexAt(e.position().toPoint())
        return at if at in (TICK, self._plus()) else -1

    def mousePressEvent(self, e) -> None:
        at = self._special(e)
        if at < 0:
            super().mousePressEvent(e)
            return
        if e.button() == Qt.MouseButton.LeftButton:
            if at == TICK:
                self.table.tick_every(self.table.tick_state() != "on")
            else:
                pos = e.position().toPoint()
                QTimer.singleShot(0, self.table, lambda: self.table._column_menu(pos))  # once the click is over
        e.accept()

    def mouseReleaseEvent(self, e) -> None:
        if self._special(e) >= 0:
            e.accept()
            return
        super().mouseReleaseEvent(e)


class Row(QTreeWidgetItem):
    """Sorts by the hidden sort key of the clicked column (numbers as numbers, words as words)."""

    def __lt__(self, other):
        tree = self.treeWidget()
        col = tree.sortColumn() if tree else 0
        ha, hb = self.data(0, HEAD), other.data(0, HEAD)
        if ha is not None and hb is not None:  # dividers keep their order whichever way you sort
            descending = tree is not None and tree.header().sortIndicatorOrder() == Qt.SortOrder.DescendingOrder
            return ha > hb if descending else ha < hb
        a, b = self.data(col, SORT), other.data(col, SORT)
        if a is None or b is None:
            return (self.text(col) or "").casefold() < (other.text(col) or "").casefold()
        if isinstance(a, str) or isinstance(b, str):
            return str(a).casefold() < str(b).casefold()
        return a < b


class ListCard(QFrame):
    """A page's list in its card (the standard's G.10.1, C-55): the surface, its corners at radius-lg, and the list
    inset 4 8 inside it, so the headings sit in the card's rounded top and no row shows in its corners."""

    def __init__(self, table: Table, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("ListCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.table = table
        x, y = tokens.LIST_CARD_INSET
        vbox(self, (x, y, x, y), 0).addWidget(table)


class Table(QTreeWidget):
    picked = Signal(str)
    menu_wanted = Signal(str, QPoint)
    delete_wanted = Signal(list)  # Delete / Backspace on the selected rows
    cleared = Signal()  # a click on empty space: nothing picked

    COLUMNS: list[tuple[str, int, object]] = []  # (title, width or 0 = stretch, alignment); the first, the ticks
    NAME_COL = 1  # the column that holds the names (the first after the ticks)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setHeader(TickHeader(self))
        self.setObjectName("Table")
        self.setColumnCount(len(self.COLUMNS))
        self.setHeaderLabels([c[0] for c in self.COLUMNS])
        self.setRootIsDecorated(False)
        self.setUniformRowHeights(True)
        self.setAlternatingRowColors(False)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)  # the ticks (selectionCommand)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSortingEnabled(True)
        self.setIndentation(tokens.ROW_INDENT)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setFrameShape(QTreeWidget.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._menu)
        h = self.header()
        h.setStretchLastSection(False)
        h.setSectionsMovable(False)
        h.setHighlightSections(False)
        h.setMinimumSectionSize(min(w for _t, w, _a in self.COLUMNS if w))  # (else the style's own, wider)
        for i, (_t, w, align) in enumerate(self.COLUMNS):
            if w:
                h.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
                self.setColumnWidth(i, w)
            else:
                h.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
            if align is not None:
                self.headerItem().setTextAlignment(i, align)
        h.setSectionResizeMode(TICK, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(TICK, tokens.TICK_W)
        self.headerItem().setToolTip(TICK, "Tick every row shown, or none")
        self.sortByColumn(self.NAME_COL, Qt.SortOrder.AscendingOrder)
        self.setItemDelegate(RowPainter(self))
        self.setMouseTracking(True)
        self.currentItemChanged.connect(self._current)
        self.itemSelectionChanged.connect(self.ticks_changed)
        self.ticks_changed.connect(self.header().viewport().update)  # (the heading's box follows)
        self._quiet = False

    # Sliding with the inspector
    # Redrawing every row on every step of the inspector's slide is too slow, so while it slides the table
    # is two still pictures (before and after) split after the wide column: the columns to the right
    # move with the edge, the names are covered or uncovered. The real table comes back when it stops.
    sliding = False
    _slide = None

    def _shot(self) -> QPixmap:
        vp = self.viewport()
        dpr = vp.devicePixelRatioF()
        pix = QPixmap(max(1, round(vp.width() * dpr)), max(1, round(vp.height() * dpr)))
        pix.setDevicePixelRatio(dpr)
        pix.fill(Qt.GlobalColor.transparent)
        vp.render(pix, QPoint(), QRegion(), QWidget.RenderFlag.DrawChildren)
        return pix

    def _seam(self) -> int:
        """Where the wide column ends (everything right of it keeps its width)."""
        h = self.header()
        for c in range(h.count()):
            if not h.isSectionHidden(c) and h.sectionResizeMode(c) == QHeaderView.ResizeMode.Stretch:
                return h.sectionViewportPosition(c) + h.sectionSize(c)
        return self.viewport().width()

    def freeze(self, to_end, to_start) -> None:
        """Take the before and after pictures (`to_end` / `to_start` resize the table), then show them."""
        before, seam_before, w_before = self._shot(), self._seam(), self.viewport().width()
        to_end()
        after, seam_after, w_after = self._shot(), self._seam(), self.viewport().width()
        self.sliding = True  # columns stay as they'll end up
        to_start()
        wide = (before, seam_before) if w_before >= w_after else (after, seam_after)
        self._slide = (wide[0], wide[1], after, seam_after, w_after - seam_after)
        self.viewport().update()

    def thaw(self) -> None:
        self._slide = None
        self.sliding = False
        self.slide_done()
        self.viewport().update()

    def slide_done(self) -> None:
        """The slide is over: settle anything held still while it ran."""
        self._step_aside()

    # Narrow
    STEP_ASIDE: tuple[int, ...] = ()  # columns that make way, in turn, so the wide one keeps WIDE_MIN
    WIDE_MIN = tokens.NAME_MIN

    def _step_aside(self) -> None:
        if not self.STEP_ASIDE:
            return
        room = self.viewport().width() - self.WIDE_MIN
        needed = sum(w for _t, w, _a in self.COLUMNS if w)
        for col in self.STEP_ASIDE:
            hide = needed > room
            if hide:
                needed -= self.COLUMNS[col][1]
            self.setColumnHidden(col, hide)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if not self.sliding:
            self._step_aside()

    def paintEvent(self, e):
        if self._slide is None:
            return super().paintEvent(e)
        left, left_seam, right, right_seam, right_w = self._slide
        vp = self.viewport()
        h = vp.height()
        cut = vp.width() - right_w
        p = QPainter(vp)
        lw = max(0, min(cut, left_seam))
        if lw:
            d = left.devicePixelRatio()
            p.drawPixmap(QRectF(0, 0, lw, h), left, QRectF(0, 0, lw * d, h * d))
        if right_w > 0:
            d = right.devicePixelRatio()
            p.drawPixmap(QRectF(cut, 0, right_w, h), right, QRectF(right_seam * d, 0, right_w * d, h * d))
        p.end()

    def _current(self, cur, _prev) -> None:
        if cur is not None and cur.data(0, ID):
            self._anchor = cur.data(0, ID)
        if cur is not None and not self._quiet and cur.data(0, ID):
            self.picked.emit(cur.data(0, ID))

    def _menu(self, pos) -> None:
        it = self.itemAt(pos)
        if it is not None and it.data(0, ID):
            self.menu_wanted.emit(it.data(0, ID), self.viewport().mapToGlobal(pos))

    def make(self, obj_id: str, cells: list[tuple[str, object]], parent=None) -> Row:
        row = Row(parent or self)
        row.setData(0, ID, obj_id)
        figures = theme.font(tokens.TEXT_MD, tabular=True)  # money and quantities line up digit for digit
        for i, (text, key) in enumerate(cells):
            row.setText(i, text)
            row.setData(i, SORT, key)
            align = self.COLUMNS[i][2]
            if align is not None:
                row.setTextAlignment(i, align)
            if isinstance(key, (int, float)) and not isinstance(key, bool):
                row.setFont(i, figures)
        row.setSizeHint(0, QSize(0, tokens.TABLE_ROW_H))
        return row

    def select_id(self, obj_id: str) -> None:
        self._quiet = True
        found = None
        it = self.invisibleRootItem()
        stack = [it.child(i) for i in range(it.childCount())]
        while stack:
            r = stack.pop()
            if r.data(0, ID) == obj_id:
                found = r
                break
            stack.extend(r.child(i) for i in range(r.childCount()))
        if found is not None:
            p = found.parent()
            while p is not None:
                p.setExpanded(True)
                p = p.parent()
            self.setCurrentItem(found, 0, QItemSelectionModel.SelectionFlag.NoUpdate)  # open, never ticked
            self.scrollToItem(found, QAbstractItemView.ScrollHint.PositionAtCenter)
        self._quiet = False

    # Ticks: what's ticked is the table's selection; the row that's open is its current row (never ticked by
    # opening it). A plain click or an arrow key moves the current row; a tick, ⌘-click or Space ticks.
    ticks_changed = Signal()

    def has_rows(self) -> bool:
        return next(iter(self.listed_rows()), None) is not None

    def ticked_ids(self) -> list[str]:
        return [r.data(0, ID) for r in self.listed_rows() if r.isSelected()]

    def tick_state(self) -> str:
        """The heading's box: "on" (every row listed is ticked), "some" or "off"."""
        rows = list(self.listed_rows())
        n = sum(1 for r in rows if r.isSelected())
        return "on" if rows and n == len(rows) else "some" if n else "off"

    @staticmethod
    def family(row) -> list:
        """A record row and the rows under it (the gear that goes with a piece), not hidden by a search."""
        return [row] + [row.child(i) for i in range(row.childCount()) if not row.child(i).isHidden()]

    def family_state(self, row) -> str:
        """A row's tick: "on" or "off"; a row with rows under it is "on" when they're all ticked, "some" (a
        dash) when some are."""
        rows = self.family(row)
        n = sum(1 for r in rows if r.isSelected())
        return "on" if n == len(rows) else "some" if n else "off"

    def tick_family(self, row) -> None:
        """A row's tick: ticks it and every row under it, or (when they all are) none of them."""
        on = self.family_state(row) != "on"
        self.blockSignals(True)  # (one change, said once)
        for r in self.family(row):
            r.setSelected(on)
        self.blockSignals(False)
        self.ticks_changed.emit()
        self.viewport().update()

    def tick_every(self, on: bool) -> None:
        if on:
            self.select_showing()
        else:
            self.clearSelection()

    def selectionCommand(self, index, event=None):
        """A plain click, an arrow key or the code moving the current row never ticks it (the standard's G.10.11:
        a click opens a row, its tick selects it); ⌘-click and Space tick or untick one, Shift-click ticks a run."""
        flags = QItemSelectionModel.SelectionFlag
        if event is None:
            return flags.NoUpdate
        kind = event.type()
        if kind == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Space and not event.modifiers() & ~Qt.KeyboardModifier.KeypadModifier:
                return flags.Toggle | flags.Rows  # (the row under the cursor)
            return super().selectionCommand(index, event) if event.modifiers() & SHIFT else flags.NoUpdate
        if kind in (
            QEvent.Type.MouseButtonPress,
            QEvent.Type.MouseButtonDblClick,
            QEvent.Type.MouseButtonRelease,
            QEvent.Type.MouseMove,
        ):
            mods = event.modifiers()
            return super().selectionCommand(index, event) if mods & CMD and not mods & SHIFT else flags.NoUpdate
        return super().selectionCommand(index, event)

    _anchor = ""  # the row last ticked or opened: where a Shift-click's run starts

    def mousePressEvent(self, e):
        pos = e.position().toPoint()
        row = self.itemAt(pos)
        if row is None:
            self.cleared.emit()
            return
        left = e.button() == Qt.MouseButton.LeftButton
        if left and row.data(0, ID) and e.modifiers() & SHIFT:
            self._tick_run(row)  # every row showing from the last one ticked or opened to this one
            e.accept()
            return
        if left and row.data(0, ID) and self.columnAt(pos.x()) == TICK:
            self.tick_family(row)  # its tick: ticked or not (and what's under it), the row that's open stays open
            self._anchor = row.data(0, ID)
            e.accept()
            return
        if left and row.data(0, ID) and e.modifiers() & CMD:
            self._anchor = row.data(0, ID)
        super().mousePressEvent(e)

    def _tick_run(self, row) -> None:
        showing = list(self.listed_rows())
        start = next((r for r in showing if r.data(0, ID) == self._anchor), None) or self.currentItem()
        if start not in showing or row not in showing:
            row.setSelected(True)
        else:
            a, b = sorted((showing.index(start), showing.index(row)))
            for r in showing[a : b + 1]:
                r.setSelected(True)
        self._anchor = row.data(0, ID)

    MOVES = {
        Qt.Key.Key_Up: QAbstractItemView.CursorAction.MoveUp,
        Qt.Key.Key_Down: QAbstractItemView.CursorAction.MoveDown,
        Qt.Key.Key_Home: QAbstractItemView.CursorAction.MoveHome,
        Qt.Key.Key_End: QAbstractItemView.CursorAction.MoveEnd,
        Qt.Key.Key_PageUp: QAbstractItemView.CursorAction.MovePageUp,
        Qt.Key.Key_PageDown: QAbstractItemView.CursorAction.MovePageDown,
    }

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape and getattr(self, "_lift", None) is not None:
            self.end_lift(drop=False)  # put it back
            return
        if e.key() in self.MOVES and not e.modifiers() & ~Qt.KeyboardModifier.KeypadModifier:
            to = self.moveCursor(self.MOVES[e.key()], e.modifiers())  # the next row opens; the ticks stay
            if to.isValid():
                self.selectionModel().setCurrentIndex(to, QItemSelectionModel.SelectionFlag.NoUpdate)
                self.scrollTo(to)
            return
        if e.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            ids = self.chosen_ids()
            if ids:
                self.delete_wanted.emit(ids)
            return
        if e.matches(QKeySequence.StandardKey.SelectAll):
            self.select_showing()
            return
        super().keyPressEvent(e)

    def keyboardSearch(self, typed: str) -> None:
        """Letters never pick a row by its name here (the standard's 6.1): they're the single-key commands (N, E,
        D, A), and / goes to the search."""

    def record_rows(self):
        """Every row that is a record (not a divider), folded away or not, top to bottom."""

        def walk(row):
            for i in range(row.childCount()):
                r = row.child(i)
                if r.data(0, ID):
                    yield r
                yield from walk(r)

        yield from walk(self.invisibleRootItem())

    def showing_rows(self):
        """Rows you can see: not hidden, not inside a folded divider."""

        def walk(row):
            for i in range(row.childCount()):
                r = row.child(i)
                if r.isHidden():
                    continue
                if r.data(0, ID):
                    yield r
                if r.isExpanded():
                    yield from walk(r)

        yield from walk(self.invisibleRootItem())

    def listed_rows(self):
        """The rows ticks count over: those showing, and the gear under a piece that's closed (ticking the piece
        ticked them). Not hidden ones, nor those inside a folded divider."""

        def walk(row, under_record: bool):
            for i in range(row.childCount()):
                r = row.child(i)
                if r.isHidden():
                    continue
                if r.data(0, ID):
                    yield r
                if r.isExpanded() or (r.data(0, ID) and not under_record):
                    yield from walk(r, bool(r.data(0, ID)))

        yield from walk(self.invisibleRootItem(), False)

    def select_showing(self) -> None:
        """Cmd+A: everything listed (never the dividers, never hidden rows)."""
        if self.selectionMode() != QAbstractItemView.SelectionMode.ExtendedSelection:
            return
        self.blockSignals(True)
        self.clearSelection()
        for r in self.listed_rows():
            r.setSelected(True)
        self.blockSignals(False)
        self.ticks_changed.emit()
        self.viewport().update()

    def chosen_ids(self) -> list[str]:
        """The ticked rows listed, top to bottom (or, with none ticked, the row that's open)."""
        ids = [r.data(0, ID) for r in self.listed_rows() if r.isSelected()]
        if not ids and self.current_id():
            ids = [self.current_id()]
        return ids

    def current_id(self) -> str:
        it = self.currentItem()
        return it.data(0, ID) if it is not None else ""

    def filter(self, text: str) -> int:
        """Hide rows that don't match every word. Returns how many top rows show."""
        words = search.words(text)

        def walk(row) -> bool:
            kids = any([walk(row.child(i)) for i in range(row.childCount())])
            me = all(w in (row.data(0, HAY) or "") for w in words)
            row.setHidden(not (me or kids))
            if words and kids:
                row.setExpanded(True)
            return me or kids

        root = self.invisibleRootItem()
        return sum(1 for i in range(root.childCount()) if walk(root.child(i)))

    def _fill_start(self) -> tuple[str, int, Qt.SortOrder]:
        keep = self.current_id()
        self._kept_ticks = {r.data(0, ID) for r in self.selectedItems() if r.data(0, ID)}  # (a refill keeps them)
        col = self.sortColumn()
        order = self.header().sortIndicatorOrder()
        self._quiet = True
        self.setSortingEnabled(False)
        self.blockSignals(True)  # (the ticks don't change: the rows are made again)
        self.clear()
        self.blockSignals(False)
        return keep, col, order

    def _fill_end(self, keep: str, col: int, order) -> None:
        self.setSortingEnabled(True)
        self.sortItems(max(0, col), order)
        kept = getattr(self, "_kept_ticks", set())
        if kept:
            self.blockSignals(True)
            for r in self.record_rows():
                if r.data(0, ID) in kept:
                    r.setSelected(True)
            self.blockSignals(False)
        self._quiet = False
        if keep:
            self.select_id(keep)
        if kept:
            self.ticks_changed.emit()  # (a ticked row that's gone is gone from the count)


def status_of(it: Item, out: int) -> tuple[str, str]:
    """A piece's status, as the gear list and the piece's own head say it: its word and its color."""
    if it.in_repair():
        return "Repair", tokens.WARN  # amber, like the In Repair chip everywhere else
    if it.is_retired():
        return "Retired", tokens.MUTED
    if out >= it.qty:
        return "Out", tokens.WARN
    if out:
        return f"{it.qty - out} of {it.qty} In", tokens.WARN
    return "In", tokens.MUTED


def family_status(it: Item, kids: list[Item], out: dict) -> tuple[str, str, str]:
    """A closed piece's status (G.11): the most pressing among it and the gear that goes with it, with how many
    when it isn't the piece's own ("1 in Repair", "2 Out"), and who (for its tooltip)."""

    def rank(x: Item) -> int:
        return 2 if x.in_repair() else 1 if not x.is_retired() and out.get(x.id, 0) else 0

    everyone = [it, *kids]
    worst = max(rank(x) for x in everyone)
    them = [x for x in everyone if rank(x) == worst]
    if worst == 0 or them == [it]:
        return (*status_of(it, out.get(it.id, 0)), "")
    word = "in Repair" if worst == 2 else "Out"
    who = "\n".join(f"{x.name}: {status_of(x, out.get(x.id, 0))[0]}" for x in them)
    return f"{len(them)} {word}", tokens.WARN, who


class RowPainter(QStyledItemDelegate):
    """Every table row's highlight, drawn once across the whole row as one rounded shape (hover, selected,
    and the dividers' accent band, a step brighter under the mouse), the way iOS lists do it.
    The stylesheet leaves cells clear so nothing paints over it."""

    def row_shape(self, painter, option, index, fill: QColor) -> None:
        view = self.parent()
        left, right = option.rect.left(), option.rect.right()
        if view is not None:
            head = view.header()
            for v in range(head.count()):  # the first column showing starts the row
                c = head.logicalIndex(v)
                if not head.isSectionHidden(c):
                    left = head.sectionViewportPosition(c)
                    break
            right = view.viewport().width()
        i = tokens.ROW_INSET
        r = QRectF(left + 1, option.rect.top() + i, right - left - 2, option.rect.height() - 2 * i)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setClipRect(option.rect)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(fill)
        painter.drawRoundedRect(r, tokens.ROW_R, tokens.ROW_R)
        painter.restore()

    def backdrop(self, painter, option, index) -> bool:
        """Paint the row's shape (G.10.3: ticked in the accent's soft tint, the row that's open in fill-2, hovered
        in row-hover); True for a divider."""
        row0 = index.siblingAtColumn(0)
        divider = row0.data(HEAD) is not None
        hover = bool(option.state & QStyle.StateFlag.State_MouseOver)
        ticked = bool(option.state & QStyle.StateFlag.State_Selected)
        view = self.parent()
        cur = view.currentIndex() if view is not None else None
        current = cur is not None and cur.isValid() and cur.row() == index.row() and cur.parent() == index.parent()
        if divider:
            self.row_shape(painter, option, index, theme.qcolor(tokens.DIVIDER_HOVER if hover else tokens.DIVIDER))
        elif ticked:
            self.row_shape(painter, option, index, theme.qcolor(tokens.CARD_SELECTED))
        elif current:
            self.row_shape(painter, option, index, theme.qcolor(tokens.FILL_2))
        elif hover:
            self.row_shape(painter, option, index, theme.qcolor(tokens.ROW_HOVER))
        return divider

    def tick(self, painter, option, index) -> None:
        """A record row's tick box (a divider has none); a piece with gear under it shows a dash while only some
        of them are ticked."""
        row0 = index.siblingAtColumn(0)
        if not row0.data(ID):
            return
        view = self.parent()
        item = view.itemFromIndex(row0) if isinstance(view, Table) else None
        if item is not None and item.childCount():
            state = view.family_state(item)
        else:
            state = "on" if option.state & QStyle.StateFlag.State_Selected else "off"
        paint_tick(painter, option.rect, state)

    @staticmethod
    def plain(option) -> QStyleOptionViewItem:
        """The cell without hover or selection (its row shape is already drawn)."""
        opt = QStyleOptionViewItem(option)
        opt.state &= ~(
            QStyle.StateFlag.State_MouseOver | QStyle.StateFlag.State_Selected | QStyle.StateFlag.State_HasFocus
        )
        return opt

    def paint(self, painter, option, index):
        self.backdrop(painter, option, index)
        if index.column() == TICK:
            self.tick(painter, option, index)
            return
        option = self.plain(option)
        if not self.dotted(painter, option, index):
            super().paint(painter, option, index)

    def dotted(self, painter, option, index) -> bool:
        """A status: a small dot in its color, then the word in the text color (the color is never the only
        sign). The cell itself (its hairline) is drawn whole. False if the cell isn't a status."""
        color = index.data(DOT)
        if not color:
            return False
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        words, opt.text = opt.text, ""
        w = opt.widget
        style = w.style() if w else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, w)  # the cell, without its words
        rect = style.subElementRect(QStyle.SubElement.SE_ItemViewItemText, opt, w)
        d = tokens.STATUS_DOT
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(theme.qcolor(color))
        painter.drawEllipse(QRectF(rect.left() + tokens.SPACE_1, rect.center().y() - d / 2 + 1, d, d))
        painter.setPen(theme.qcolor(tokens.TEXT))
        text = rect.adjusted(tokens.SPACE_1 + d + tokens.SPACE_2, 0, 0, 0)
        painter.drawText(text, int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
                         opt.fontMetrics.elidedText(words, Qt.TextElideMode.ElideRight, text.width()))  # fmt: skip
        painter.restore()
        return True

    def helpEvent(self, event, view, option, index):
        """A cell's own tooltip, or else, when the cell cuts its words short, the whole of them."""
        if event.type() != QEvent.Type.ToolTip or not index.isValid() or index.data(Qt.ItemDataRole.ToolTipRole):
            return super().helpEvent(event, view, option, index)
        text = self.cut_short(view, option, index)
        if text:
            QToolTip.showText(event.globalPos(), theme.plain_tip(text), view)
        else:
            QToolTip.hideText()
        return True

    @staticmethod
    def cut_short(view, option, index) -> str:
        """The cell's whole text if it doesn't fit (so it's shown cut short), else ''."""
        text = str(index.data(Qt.ItemDataRole.DisplayRole) or "")
        room = view.visualRect(index).width() - 2 * tokens.SPACE_2  # the cell's padding
        if index.column() == GEAR_COL["name"] and isinstance(view, GearTable):
            row0 = index.siblingAtColumn(0)
            room -= view.name_shift(row0)
            if view.thumbs:
                room -= tokens.TABLE_THUMB + tokens.SPACE_2
            if row0.data(SUMMARY):
                small = QFontMetricsF(theme.font(tokens.TEXT_SM))
                room -= tokens.SPACE_2 + small.horizontalAdvance(row0.data(SUMMARY))
        return text if text and option.fontMetrics.horizontalAdvance(text) > room else ""


class _GearPainter(RowPainter):
    """…plus the divider's chevron, the grip you drag a row by, a piece's photo before its name, and (G.11) the
    chevron of a piece with gear under it, which turns as it opens, its name in Semibold with how many go with it
    after it, and that gear under it, one step in."""

    _inset = -1  # where a cell's words start inside it (the style's, worked out once)

    def paint(self, painter, option, index):
        row0 = index.siblingAtColumn(0)
        divider = self.backdrop(painter, option, index)
        if index.column() == TICK:
            if divider:
                self._chevron(painter, option.rect, bool(row0.data(OPEN)))
            else:
                self.tick(painter, option, index)  # (with its state: ticked or not)
            return
        option = self.plain(option)
        if index.column() == GEAR_COL["grip"]:
            if row0.data(ID) and not divider and row0.data(CHILD) is None:  # (gear never leaves its piece)
                self._grip(painter, option.rect)
            return
        view = self.parent()
        if index.column() == GEAR_COL["name"] and not divider and isinstance(view, GearTable):
            option = QStyleOptionViewItem(option)
            option.rect = option.rect.adjusted(view.name_shift(row0), 0, 0, 0)
            item = view.itemFromIndex(row0)
            if item is not None and view.opens(item):
                self._disclosure(painter, self.disclosure_box(view, option.rect), view.angle(item))
            if view.thumbs:
                option = self._thumb(painter, option, row0.data(PHOTO) or "")
            if row0.data(SUMMARY) and self._named(painter, option, index, row0.data(SUMMARY)):
                return
        if not self.dotted(painter, option, index):
            QStyledItemDelegate.paint(self, painter, option, index)

    def disclosure_box(self, view, cell) -> QRectF:
        """Where a piece's chevron goes: DISCLOSURE_GAP before what follows it (its photo, or its words)."""
        if self._inset < 0:
            type(self)._inset = words_inset(view)
        start = cell.left() + (tokens.SPACE_1 if view.thumbs else self._inset)
        size = tokens.DISCLOSURE
        right = start - tokens.DISCLOSURE_GAP
        return QRectF(right - size, cell.center().y() - size / 2 + 0.5, size, size)

    @staticmethod
    def _disclosure(painter, box: QRectF, angle: float) -> None:
        """chevron-right, turned `angle` degrees (0: closed, pointing to the trailing side; 90: open, down)."""
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(theme.qcolor(tokens.MUTED), tokens.LINE_STROKE)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.translate(box.center())
        painter.rotate(angle)
        r = box.width() / 2
        painter.drawPolyline([QPointF(-r / 4, -r / 2), QPointF(r / 4, 0), QPointF(-r / 4, r / 2)])
        painter.restore()

    def _named(self, painter, option, index, summary: str) -> bool:
        """A piece with gear under it: its name (Semibold), then SPACE_2 on, how many go with it, muted. The name
        gives way first. False if there's no room for the summary at all (the plain cell is drawn instead)."""
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        name, opt.text = opt.text, ""
        w = opt.widget
        style = w.style() if w else QApplication.style()
        margin = style.pixelMetric(QStyle.PixelMetric.PM_FocusFrameHMargin, None, w) + 1  # (as the style's words)
        rect = style.subElementRect(QStyle.SubElement.SE_ItemViewItemText, opt, w).adjusted(margin, 0, -margin, 0)
        small = theme.font(tokens.TEXT_SM)
        sw = QFontMetricsF(small).horizontalAdvance(summary)
        room = rect.width() - tokens.SPACE_2 - sw
        if room < opt.fontMetrics.horizontalAdvance("…") * 4:
            return False
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, w)  # the cell, without its words
        shown = opt.fontMetrics.elidedText(name, Qt.TextElideMode.ElideRight, int(room))
        nw = opt.fontMetrics.horizontalAdvance(shown)
        middle = int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        painter.save()
        painter.setFont(opt.font)
        painter.setPen(theme.qcolor(tokens.TEXT))
        painter.drawText(QRectF(rect.left(), rect.top(), nw + 1, rect.height()), middle, shown)
        painter.setFont(small)
        painter.setPen(theme.qcolor(tokens.MUTED))
        painter.drawText(QRectF(rect.left() + nw + tokens.SPACE_2, rect.top(), sw + 1, rect.height()), middle, summary)
        painter.restore()
        return True

    @staticmethod
    def _thumb(painter, option, name: str) -> QStyleOptionViewItem:
        """The piece's photo before its name (an empty square keeps names lined up when it has none).
        Returns the cell with its text moved over."""
        size = tokens.TABLE_THUMB
        r = option.rect
        box = QRectF(r.left() + tokens.SPACE_1, r.top() + (r.height() - size) / 2, size, size)
        pix = photos.thumbnail(name, size, painter.device().devicePixelRatioF()) if name else None
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if pix is not None:
            painter.drawPixmap(box.topLeft(), pix)
        else:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(theme.qcolor(tokens.CHIP))
            painter.drawRoundedRect(box, tokens.RADIUS_SM, tokens.RADIUS_SM)
        painter.restore()
        opt = QStyleOptionViewItem(option)
        opt.rect = r.adjusted(size + tokens.SPACE_2, 0, 0, 0)
        return opt

    @staticmethod
    def _chevron(painter, rect, open_: bool) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(theme.qcolor(tokens.DIVIDER_TEXT), tokens.LINE_STROKE)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        c = QPointF(rect.center())
        r = tokens.CHEVRON / 2
        if open_:
            pts = [
                QPointF(c.x() - r, c.y() - r / 2),
                QPointF(c.x(), c.y() + r / 2),
                QPointF(c.x() + r, c.y() - r / 2),
            ]
        else:
            pts = [
                QPointF(c.x() - r / 2, c.y() - r),
                QPointF(c.x() + r / 2, c.y()),
                QPointF(c.x() - r / 2, c.y() + r),
            ]
        painter.drawPolyline(pts)
        painter.restore()

    @staticmethod
    def _grip(painter, rect) -> None:
        theme.draw_grip(painter, rect)


# the gear table's columns: key, title, width (0 = takes the rest), alignment
GEAR_COLUMNS = [
    ("tick", "", tokens.TICK_W, None),
    ("name", "Name", 0, None),
    ("with", "Goes With", tokens.COL_W["with"], None),  # the piece it's attached to
    ("brand", "Company", tokens.COL_W["company"], None),
    ("series", "Series", tokens.COL_W["series"], None),
    ("group", "Group", tokens.COL_W["group"], None),
    ("qty", "Qty", tokens.COL_W["qty"], CENTER),
    ("status", "Status", tokens.COL_W["status"], None),
    ("paid", "Paid", tokens.COL_W["paid"], RIGHT),
    ("value", "With Tax", tokens.COL_W["with_tax"], RIGHT),
    ("day", "Day Rate", tokens.COL_W["day"], RIGHT),
    ("earned", "Earned", tokens.COL_W["earned"], RIGHT),  # rental income so far (core/earnings.py)
    ("grip", "", tokens.GRIP_W, None),  # your order: drag a row by it (always last, at the trailing edge)
]
GEAR_COL = {key: n for n, (key, *_rest) in enumerate(GEAR_COLUMNS)}
HIDDEN_AT_FIRST = ["series", "paid", "earned"]
# on a narrow window these columns step aside first (Name always keeps NAME_MIN)
GIVE_WAY = ["earned", "series", "paid", "with", "status", "brand", "group", "qty", "day"]
DIVIDES = [  # how the gear table is divided
    ("group", "By Group", ""),
    ("brand", "By Company", ""),
    ("none", "No Dividers", ""),
]
OPEN = Qt.ItemDataRole.UserRole + 7  # a divider is open
KIND = Qt.ItemDataRole.UserRole + 8  # what a divider divides by
WHERE = Qt.ItemDataRole.UserRole + 9  # a gear row's (group, company)
WITH = Qt.ItemDataRole.UserRole + 10  # the name of the piece this one goes with
PHOTO = Qt.ItemDataRole.UserRole + 11  # a gear row's photo (its file name)
CHILD = Qt.ItemDataRole.UserRole + 13  # gear under a piece (it goes with it): that piece's id
SUMMARY = Qt.ItemDataRole.UserRole + 14  # a piece with gear under it: the words after its name ("2 Attached")
STATUSES = Qt.ItemDataRole.UserRole + 15  # …and its status open (its own) and closed (the most pressing of all)


class GearTable(Table):
    divider_menu = Signal(str, QPoint)  # the group a divider stands for, where
    dropped = Signal(list, str)  # gear ids, the group they were dropped into
    branded = Signal(list, str)  # gear ids dropped onto a company divider
    reordered = Signal(list, str, bool)  # gear ids, the row they were dropped on, after it?
    columns_changed = Signal(list)  # the column keys you hid
    order_changed = Signal(list)  # the column keys in the order you put them (after the grip and Name)
    folds_changed = Signal()  # a divider folded or opened, by a click or the keyboard (kept in settings)

    COLUMNS = [(title, w, align) for _k, title, w, align in GEAR_COLUMNS]
    NAME_COL = GEAR_COL["name"]
    thumbs = False  # some piece has a photo: every name makes room for one
    earned: dict | None = None

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setRootIsDecorated(False)
        self.setIndentation(0)
        h = self.headerItem()
        h.setToolTip(GEAR_COL["grip"], "Choose Columns")
        h.setToolTip(GEAR_COL["with"], "The piece it's attached to")
        with_it = "a piece with gear under it counts that gear too"
        h.setToolTip(GEAR_COL["paid"], f"What it cost, before tax ({with_it})")
        h.setToolTip(GEAR_COL["value"], f"Replacement value: paid plus sales tax ({with_it})")
        h.setToolTip(GEAR_COL["day"], f"A day of all of them ({with_it})")
        h.setToolTip(
            GEAR_COL["earned"],
            f"An estimate: each rental's gear total, shared out by each piece's day rate ({with_it})",
        )
        self.header().setSectionResizeMode(GEAR_COL["grip"], QHeaderView.ResizeMode.Fixed)
        self.header().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.header().customContextMenuRequested.connect(self._column_menu)
        self.header().setSectionsMovable(True)  # drag a column's title to put it elsewhere
        self.header().setFirstSectionMovable(False)  # (the ticks stay first and Name after them; the grip, last)
        self.header().sectionMoved.connect(self._column_moved)
        self._moving = False
        self.folded: set[str] = set()  # dividers you folded
        self.open_pieces: set[str] = set()  # pieces you opened to show the gear under them (settings "gear_open")
        self.families = False  # some piece in the list has gear under it (every name then makes room for a chevron)
        self.shown: list[str] = []  # the pieces the search and filters left, top to bottom (show_only)
        self._turns: dict[str, QVariantAnimation] = {}  # chevrons turning
        self.setExpandsOnDoubleClick(False)  # (a piece opens by its chevron or the keyboard; a click opens it)
        self.itemExpanded.connect(self._show_status)
        self.itemCollapsed.connect(self._show_status)
        self.hidden_cols: set[str] = set(HIDDEN_AT_FIRST)
        self._squeezed: set[str] = set()  # stepped aside because the window is narrow
        self.any_with = False  # some piece is attached to another (else Goes With stays away)
        self._dragging = False
        self._queued: list = []
        self.divide = "group"
        self.itemClicked.connect(self._divider_clicked)
        self.stocks: dict[str, pricing.Stock] = {}  # item id -> it and what's attached, totalled
        self.group = ""  # showing one group only
        self.setItemDelegate(_GearPainter(self))
        self.setMouseTracking(True)
        # pick several (Shift/Cmd-click) to move them together; drag by the grip to reorder, or onto a divider
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setDragEnabled(False)  # dragging starts from the grip only, live (window/lift.py)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self._press = None  # (where, row) a grip was pressed, until it moves far enough to lift
        self._lift: Lift | None = None
        self._fill_later = None  # a refill asked for mid-drag, run when the row lands
        self.setDefaultDropAction(Qt.DropAction.CopyAction)
        self.setDropIndicatorShown(True)
        self.sortByColumn(GEAR_COL["grip"], Qt.SortOrder.AscendingOrder)  # your order, at first

    # Columns
    FIXED = ("tick", "name")  # always first, in this order
    LAST = "grip"  # always last

    def column_order(self) -> list[str]:
        h = self.header()
        keys = [k for k, _t, _w, _a in GEAR_COLUMNS]
        mine = [keys[h.logicalIndex(v)] for v in range(h.count())]
        return [k for k in mine if k not in self.FIXED and k != self.LAST]

    def _grip_last(self) -> None:
        h = self.header()
        at = h.visualIndex(GEAR_COL[self.LAST])
        if at != h.count() - 1:
            self._moving = True
            h.moveSection(at, h.count() - 1)
            self._moving = False

    def set_column_order(self, order: list[str]) -> None:
        """Put the columns in this order (keys it doesn't know are skipped; columns it doesn't name stay after)."""
        h = self.header()
        self._moving = True
        at = len(self.FIXED)
        for key in order:
            if key in GEAR_COL and key not in self.FIXED and key != self.LAST:
                h.moveSection(h.visualIndex(GEAR_COL[key]), at)
                at += 1
        self._moving = False
        self._grip_last()

    def _column_moved(self, logical: int, old: int, new: int) -> None:
        if self._moving:
            return
        h = self.header()
        if logical in (GEAR_COL["name"], GEAR_COL[self.LAST]) or new < len(self.FIXED):  # Name stays first:
            self._moving = True  # put it back (and the grip stays last)
            h.moveSection(new, old)
            self._moving = False
            return
        self._grip_last()  # (a column dropped past the grip)
        self.order_changed.emit(self.column_order())

    def _step_column(self, key: str, step: int) -> None:
        """Move Left / Move Right: past the next column that shows."""
        h = self.header()
        v = h.visualIndex(GEAR_COL[key])
        to = v + step
        while len(self.FIXED) <= to < h.count() and h.isSectionHidden(h.logicalIndex(to)):
            to += step
        if len(self.FIXED) <= to < h.count():
            h.moveSection(v, to)

    chooses_columns = True  # (its headings end in a +: TickHeader)

    def _column_menu(self, pos) -> None:
        """The columns: each ticked or not (the menu stays open while several change), Reset Columns at the end;
        on a column's own heading, Move Left and Move Right first. The same from the headings' + or a right-click."""
        m = TickMenu(self)
        h = self.header()
        keys = [k for k, _t, _w, _a in GEAR_COLUMNS]
        logical = h.logicalIndexAt(pos)
        here = keys[logical] if 0 <= logical < len(keys) else ""
        mine = m.addAction(
            "Sort by Your Order", lambda: self.sortByColumn(GEAR_COL["grip"], Qt.SortOrder.AscendingOrder)
        )
        mine.setCheckable(True)
        mine.setChecked(self.your_order())
        m.addSeparator()
        if here and here not in self.FIXED and here != self.LAST:
            v = h.visualIndex(logical)
            shown = [x for x in range(len(self.FIXED), h.count()) if not h.isSectionHidden(h.logicalIndex(x))]
            left = m.addAction("Move Left", lambda: self._step_column(here, -1))
            left.setEnabled(bool(shown) and v > shown[0])
            right = m.addAction("Move Right", lambda: self._step_column(here, 1))
            right.setEnabled(bool(shown) and v < shown[-1])
            m.addSeparator()
        for key, title, _w, _a in GEAR_COLUMNS:
            if key in (*self.FIXED, self.LAST):
                continue
            a = m.addAction(title)
            a.setCheckable(True)
            a.setChecked(key not in self.hidden_cols)
            a.toggled.connect(lambda on, k=key: self._toggle_column(k, on))
        m.addSeparator()
        m.addAction("Reset Columns", self.reset_columns)
        m.exec(self.header().mapToGlobal(pos))

    def reset_columns(self) -> None:
        """The columns as they are at first: Bodega's own choice and order."""
        self.hidden_cols = set(HIDDEN_AT_FIRST)
        self.set_column_order([k for k, _t, _w, _a in GEAR_COLUMNS])
        self._apply_columns()
        self.columns_changed.emit(sorted(self.hidden_cols))
        self.order_changed.emit(self.column_order())

    def _toggle_column(self, key: str, on: bool) -> None:
        (self.hidden_cols.discard if on else self.hidden_cols.add)(key)
        self._apply_columns()
        self.columns_changed.emit(sorted(self.hidden_cols))

    def _apply_columns(self) -> None:
        auto = set()
        if self.divide == "group" or self.group:
            auto.add("group")
        if self.divide == "brand":
            auto.add("brand")
        if not self.any_with:  # nothing's attached to anything: no empty column
            auto.add("with")
        off = self.hidden_cols | auto
        # make room for Name: the least needed columns step aside on a narrow window
        room = self.viewport().width() - tokens.NAME_MIN
        widths = {k: w for k, _t, w, _a in GEAR_COLUMNS}
        needed = sum(widths[k] for k in GEAR_COL if k != "name" and k not in off)
        self._squeezed = set()
        for k in GIVE_WAY:
            if needed <= room:
                break
            if k not in off:
                self._squeezed.add(k)
                needed -= widths[k]
        for key, n in GEAR_COL.items():
            self.setColumnHidden(n, key in off or key in self._squeezed)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if not self.sliding:
            self._apply_columns()

    def slide_done(self) -> None:
        self._apply_columns()

    # A piece and the gear that goes with it (the standard's G.11): one row that opens in place
    def name_shift(self, row) -> int:
        """How far a row's name moves in (`row` is the row, or one of its cells): room for a chevron once any piece
        has gear under it, and a step more for that gear."""
        lead = tokens.DISCLOSURE + tokens.DISCLOSURE_GAP if self.families else 0
        under = row.data(0, CHILD) if isinstance(row, QTreeWidgetItem) else row.siblingAtColumn(0).data(CHILD)
        return lead + (tokens.ROW_INDENT if under is not None else 0)

    @staticmethod
    def opens(row) -> bool:
        """A piece with gear under it showing (a search can hide all of it)."""
        return bool(row.data(0, ID)) and any(not row.child(i).isHidden() for i in range(row.childCount()))

    def angle(self, row) -> float:
        """Its chevron: 0 closed, 90 open, or on its way."""
        turning = self._turns.get(row.data(0, ID))
        if turning is not None:
            return float(turning.currentValue())
        return 90.0 if row.isExpanded() else 0.0

    def _turn(self, row, opening: bool) -> None:
        piece = row.data(0, ID)
        start = self.angle(row)
        old = self._turns.pop(piece, None)
        if old is not None:
            old.stop()
        ms = access.duration(tokens.TURN_MS)  # Reduce Motion: it just points the other way
        if not ms:
            return
        a = QVariantAnimation(self, startValue=start, endValue=90.0 if opening else 0.0, duration=ms)
        a.setEasingCurve(QEasingCurve.Type.OutCubic)
        a.valueChanged.connect(self.viewport().update)
        a.finished.connect(lambda: self._turns.pop(piece, None) if self._turns.get(piece) is a else None)
        self._turns[piece] = a
        a.start()

    def open_piece(self, row, opening: bool, every: bool = False) -> None:
        """Open or close a piece to show the gear under it (remembered, as a divider's fold is); ⌥ does it to every
        piece. Closing it over the row that's open opens the piece instead (the Finder does the same)."""
        rows = [r for r in self.record_rows() if self.opens(r)] if every else [row]
        for r in rows:
            if r.isExpanded() == opening:
                continue
            (self.open_pieces.add if opening else self.open_pieces.discard)(r.data(0, ID))
            self._turn(r, opening)
            cur = self.currentItem()
            if not opening and cur is not None and cur.parent() is r:
                self.setCurrentItem(r, 0, QItemSelectionModel.SelectionFlag.NoUpdate)
            r.setExpanded(opening)
        self.folds_changed.emit()

    def _show_status(self, row) -> None:
        """A piece open shows its own status; closed, the most pressing of it and what's under it. A screen reader
        hears which it is, and how many go with it."""
        both = row.data(0, STATUSES)
        if not both:
            return
        state = "open" if row.isExpanded() else "closed"
        row.setData(GEAR_COL["name"], Qt.ItemDataRole.AccessibleDescriptionRole, f"{row.data(0, SUMMARY)}, {state}")
        text, color, tip = both[0] if row.isExpanded() else both[1]
        col = GEAR_COL["status"]
        if row.text(col) != text:
            row.setText(col, text)
        row.setData(col, DOT, color)
        row.setToolTip(col, theme.plain_tip(tip) if tip else "")

    def _on_chevron(self, row, pos) -> bool:
        """The press is on a piece's chevron (or the room before its name that holds it)."""
        if row is None or not self.opens(row) or self.columnAt(pos.x()) != GEAR_COL["name"]:
            return False
        h = self.header()
        left = h.sectionViewportPosition(GEAR_COL["name"])
        return pos.x() < left + self.name_shift(row) + (tokens.SPACE_1 if self.thumbs else tokens.SPACE_2)

    # Dragging
    def selected_ids(self) -> list[str]:
        return self.chosen_ids()

    def _describe(self, row) -> tuple:
        """For the Lift: what a row is."""
        if row.data(0, HEAD) is not None:
            return ("divider", row.data(0, GRP) or "", row.data(0, KIND) or "group")
        if row.data(0, CHILD) is not None:
            return ("child", row.data(0, CHILD))  # (it stands for its piece: it moves with it)
        return ("item", row.data(0, ID))

    def _visible_rows(self) -> list:
        """Every row you can see, dividers too, top to bottom."""
        out = []

        def walk(parent):
            for i in range(parent.childCount()):
                r = parent.child(i)
                if r.isHidden():
                    continue
                out.append(r)
                if r.childCount() and r.isExpanded():
                    walk(r)

        walk(self.invisibleRootItem())
        return out

    def _on_grip(self, pos) -> object:
        row = self.itemAt(pos)
        if (
            row is not None
            and row.data(0, ID)
            and row.data(0, CHILD) is None  # (gear under a piece moves with it, never on its own)
            and self.columnAt(pos.x()) == GEAR_COL["grip"]
        ):
            return row
        return None

    def mousePressEvent(self, e):
        pos = e.position().toPoint()
        piece = self.itemAt(pos)
        if e.button() == Qt.MouseButton.LeftButton and self._on_chevron(piece, pos):
            every = bool(e.modifiers() & Qt.KeyboardModifier.AltModifier)  # ⌥: every piece, as the Finder does
            self.open_piece(piece, not piece.isExpanded(), every)
            e.accept()
            return
        row = self._on_grip(pos)
        if e.button() == Qt.MouseButton.LeftButton and row is not None and not e.modifiers():
            self._press = (e.position().toPoint(), row)  # (the ticked rows go with it if it's one of them)
            e.accept()
            return
        super().mousePressEvent(e)

    def start_lift(self, row, y: float) -> Lift:
        """Lift the pressed row (and the others selected with it) to drag it into place; the Lift follows the
        pointer until end_lift()."""
        if not self.your_order():  # dragging means your own order: switch to it first
            self.sortByColumn(GEAR_COL["grip"], Qt.SortOrder.AscendingOrder)
            y = self.visualItemRect(row).center().y()
        ids = [i for i in self.ticked_ids() if i]
        if row.data(0, ID) not in ids:  # a row that isn't ticked moves alone
            ids = [row.data(0, ID)]
        self._lift = Lift(self, self._visible_rows(), ids, row, y, self._describe)
        self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
        return self._lift

    def end_lift(self, drop: bool = True) -> None:
        lift, self._lift = self._lift, None
        if lift is None:
            return
        lift.stop()
        later, self._fill_later = self._fill_later, None
        if later is not None:  # the list changed while it was lifted
            QTimer.singleShot(0, self, lambda: self.fill(*later))
        self.viewport().setCursor(Qt.CursorShape.ArrowCursor)
        self.viewport().update()
        got = lift.result() if drop else None
        if got is None:
            return
        ids = lift.ids
        if got[0] in ("before", "after"):
            QTimer.singleShot(0, self, lambda: self.reordered.emit(ids, got[1], got[0] == "after"))
        elif got[2] == "brand":
            QTimer.singleShot(0, self, lambda: self.branded.emit(ids, got[1]))
        else:
            QTimer.singleShot(0, self, lambda: self.dropped.emit(ids, got[1]))

    def mouseReleaseEvent(self, e):
        if self._lift is not None:
            self.end_lift(drop=True)
            self._press = None
            return
        if self._press is not None:  # a click on the grip, not a drag: pick the row
            row = self._press[1]
            self._press = None
            self.setCurrentItem(row)
            return
        super().mouseReleaseEvent(e)

    def paintEvent(self, e):
        if self._lift is not None:
            self._lift.paint()
            return
        super().paintEvent(e)

    def mouseMoveEvent(self, e):
        pos = e.position().toPoint()
        if self._lift is not None:
            if self._over_sidebar(e.globalPosition().toPoint()):  # onto the sidebar: drop it on a group there
                ids = self._lift.ids
                self.end_lift(drop=False)
                for r in self.item_rows():
                    r.setSelected(r.data(0, ID) in ids)
                self._press = None
                self.startDrag(Qt.DropAction.CopyAction)
                return
            self._lift.move_to(pos.y())
            return
        if self._press is not None and e.buttons() & Qt.MouseButton.LeftButton:
            if (pos - self._press[0]).manhattanLength() >= QApplication.startDragDistance():
                self.start_lift(self._press[1], self._press[0].y())
                self._lift.move_to(pos.y())
            return
        if not e.buttons():
            on_grip = self._on_grip(e.position().toPoint()) is not None
            shape = Qt.CursorShape.OpenHandCursor if on_grip else Qt.CursorShape.ArrowCursor
            if self.viewport().cursor().shape() != shape:
                self.viewport().setCursor(shape)
        super().mouseMoveEvent(e)

    @staticmethod
    def _over_sidebar(global_pos) -> bool:
        """The pointer is over the list of places on the left (not just a little left of the grip, which sits
        at the table's very edge: drifting there while dragging mustn't drop the row)."""
        from bodega.ui.components.panels import LeftPanel

        w = QApplication.widgetAt(global_pos)
        while w is not None:
            if isinstance(w, LeftPanel):
                return True
            w = w.parentWidget()
        return False

    def target_at(self, pos):
        """What a drop here means: ("row", row) next to a piece, or ("divider", row) into a divider."""
        row = self.itemAt(pos)
        if row is None:
            return None
        if row.data(0, HEAD) is not None:
            return "divider", row
        if row.data(0, CHILD) is not None and row.parent() is not None:
            return "row", row.parent()  # next to gear under a piece: next to the piece
        if row.data(0, ID):
            return "row", row
        return None

    def dragEnterEvent(self, e):
        if e.source() is self:
            e.acceptProposedAction()
        else:
            e.ignore()

    def dragMoveEvent(self, e):
        super().dragMoveEvent(e)  # keeps the line showing where it lands
        if e.source() is self and self.target_at(e.position().toPoint()) is not None:
            e.acceptProposedAction()
        else:
            e.ignore()

    def startDrag(self, actions):
        """A drag runs its own loop; the table must not be refilled until it's over (refilling mid-drag
        left the Mac's table blank). Moves asked for during the drag wait here and run right after."""
        self._dragging = True
        try:
            super().startDrag(actions)
        finally:
            self._dragging = False
            self.setState(QAbstractItemView.State.NoState)
            queued, self._queued = self._queued, []
            for fn in queued:
                fn()
            self.viewport().update()

    def after_drag(self, fn) -> None:
        """Run `fn` now, or as soon as the drag in progress ends."""
        if getattr(self, "_dragging", False):
            self._queued.append(fn)
        else:
            fn()

    def dropEvent(self, e):
        target = self.target_at(e.position().toPoint())
        after = self.dropIndicatorPosition() == QAbstractItemView.DropIndicatorPosition.BelowItem
        ids = self.selected_ids()
        e.setDropAction(Qt.DropAction.IgnoreAction)  # we move them ourselves; the table refills
        e.accept()
        if target is None or not ids:
            return
        kind, row = target
        if kind == "row":
            anchor = row.data(0, ID)
            if anchor not in ids:
                self.after_drag(lambda: self.reordered.emit(ids, anchor, after))
            return
        what, grp = row.data(0, KIND), row.data(0, GRP) or ""
        if what == "brand":
            self.after_drag(lambda: self.branded.emit(ids, grp))
        else:
            self.after_drag(lambda: self.dropped.emit(ids, grp))

    def _menu(self, pos) -> None:
        row = self.itemAt(pos)
        if row is not None and row.data(0, HEAD) is not None:
            if row.data(0, KIND) == "group" and row.data(0, GRP):
                self.divider_menu.emit(row.data(0, GRP), self.viewport().mapToGlobal(pos))
            return
        super()._menu(pos)

    def _divider_clicked(self, row, _col) -> None:
        """A click opens or folds a divider; ⌥-click does it to every divider (as the Finder does)."""
        if row.data(0, HEAD + 10) is None:
            return
        opening = not row.isExpanded()
        every = bool(QApplication.keyboardModifiers() & Qt.KeyboardModifier.AltModifier)
        for d in self._dividers() if every else [row]:
            self._fold(d, opening)
        self.folds_changed.emit()

    def _dividers(self) -> list:
        root = self.invisibleRootItem()
        return [root.child(i) for i in range(root.childCount()) if root.child(i).data(0, HEAD + 10) is not None]

    def _fold(self, row, opening: bool) -> None:
        row.setExpanded(opening)
        row.setData(0, OPEN, opening)
        (self.folded.discard if opening else self.folded.add)(row.data(0, HEAD + 10))

    def keyPressEvent(self, e):
        """On a divider, → opens it and ← folds it (remembered, as a click is); Space or Return does either. On a
        piece with gear under it, → opens it, ← closes it and Return does either; Space ticks it and what's under
        it. On gear under a piece, ← goes up to the piece (G.11)."""
        row = self.currentItem()
        k = e.key()
        plain = not e.modifiers() & ~Qt.KeyboardModifier.KeypadModifier
        if row is not None and plain and row.data(0, ID):
            if self.opens(row):
                if k in (Qt.Key.Key_Right, Qt.Key.Key_Left) and row.isExpanded() != (k == Qt.Key.Key_Right):
                    self.open_piece(row, k == Qt.Key.Key_Right)
                    return
                if k in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    self.open_piece(row, not row.isExpanded())
                    return
                if k == Qt.Key.Key_Space:
                    self.tick_family(row)
                    return
            if k == Qt.Key.Key_Left and row.data(0, CHILD) is not None and row.parent() is not None:
                self.setCurrentItem(row.parent(), 0, QItemSelectionModel.SelectionFlag.NoUpdate)
                self.scrollToItem(row.parent())
                return
            if k in (Qt.Key.Key_Right, Qt.Key.Key_Left):
                return  # (nothing to open or close: the list never scrolls sideways)
        if row is not None and row.data(0, HEAD + 10) is not None and plain:
            if k in (Qt.Key.Key_Right, Qt.Key.Key_Left) and row.isExpanded() != (k == Qt.Key.Key_Right):
                self._fold(row, k == Qt.Key.Key_Right)
                self.folds_changed.emit()
                return
            if k in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self._fold(row, not row.isExpanded())
                self.folds_changed.emit()
                return
        super().keyPressEvent(e)

    def your_order(self) -> bool:
        return self.sortColumn() == GEAR_COL["grip"]

    # Filling
    def fill(self, lib: Library, b: Business | None, group: str = "", divide: str = "") -> None:
        if self._lift is not None:  # never rebuild the rows under a row being dragged: after it lands
            self._fill_later = (lib, b, group, divide)
            return
        self.thumbs = any(it.photo for it in lib.items.values())  # once one has a photo, every row has room
        # worked out only while the Earned column shows (the piece's panel works out its own otherwise)
        self.earned = earnings.earnings(lib) if "earned" not in self.hidden_cols else None
        self.group = group
        self.divide = divide or ("brand" if group else "group")
        keep, col, order = self._fill_start()
        cur = (b.currency if b else "$") or "$"
        out = pricing.units_out(lib)
        self.stocks = {}
        ordered = lib.ordered_items()
        position = {it.id: n for n, it in enumerate(ordered)}
        items = [i for i in ordered if not group or i.group == group]
        kind = self.divide
        # gear that goes with a piece goes under it, one level (G.11): under the piece it ultimately lives with
        listed = {i.id for i in items}
        under: dict[str, list[Item]] = {}
        for i in items:
            root = pricing.root_of(lib, i)
            if root.id != i.id and root.id in listed:
                under.setdefault(root.id, []).append(i)
        top_of = {kid.id: piece for piece, kids in under.items() for kid in kids}
        self.families = bool(under)
        # Goes With, only where being under its piece doesn't say it: gear on gear that goes with a piece, or a piece
        # listed without the one it goes with
        self.any_with = any(i.parent in lib.items and top_of.get(i.id) != i.parent for i in items)

        def key_of(i: Item):
            i = lib.items.get(top_of.get(i.id, ""), i)  # (gear under a piece is under its divider)
            return i.group if kind == "group" else (i.brand if kind == "brand" else None)

        keys: list = []
        for i in items:
            if key_of(i) not in keys:
                keys.append(key_of(i))
        if kind == "brand":
            keys.sort(key=lambda k: (not k, (k or "").casefold()))
        elif kind == "group":
            keys.sort(key=lambda k: (not k,))  # your order, no group last
        use_dividers = kind != "none" and (len(keys) > 1 or not group)
        dividers: dict = {}
        for n, key in enumerate(keys if use_dividers else []):
            d = Row(self)
            name = key or ("No Group" if kind == "group" else "No Company")
            d.setData(0, HEAD, n)
            d.setData(0, KIND, kind)
            d.setData(0, HEAD + 10, f"{group}/{kind}/{key}")
            d.setData(0, GRP, key or "")
            d.setText(GEAR_COL["name"], name)
            d.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsDropEnabled)
            d.setSizeHint(0, QSize(0, tokens.TABLE_ROW_H))
            # a group row: its name in Callout Semibold, muted; its subtotals as a body row's figures (G.10.8)
            f = theme.font(tokens.TEXT_MD, tokens.WEIGHT_SEMIBOLD, tabular=True)
            big = theme.font(tokens.TEXT_SM, tokens.WEIGHT_SEMIBOLD)
            for c, (_k, _t, _w, align) in enumerate(GEAR_COLUMNS):
                d.setFont(c, big if c == GEAR_COL["name"] else f)
                d.setForeground(c, theme.qcolor(tokens.MUTED if c == GEAR_COL["name"] else tokens.DIVIDER_TEXT))
                if align is not None:
                    d.setTextAlignment(c, align)
            dividers[key] = d
        totals = {key: pricing.Stock() for key in dividers}
        rows: dict[str, Row] = {}
        for it in sorted(items, key=lambda i: i.id in top_of):  # (each piece before the gear under it)
            st = pricing.stock(lib, it, b, attached=False)  # each row is that piece alone (the totals add them)
            self.stocks[it.id] = st
            on = lib.items.get(it.parent) if it.parent else None
            home = rows[top_of[it.id]] if it.id in top_of else dividers.get(key_of(it), self)
            row = self._row(it, st, cur, out, home, on.name if on else "", position[it.id])
            rows[it.id] = row
            if it.id in top_of:
                row.setData(0, CHILD, top_of[it.id])
            elif it.id in under:
                self._family(row, it, under[it.id], lib, b, cur, out)
            if key_of(it) in totals:
                totals[key_of(it)].add(st)
        for key, d in dividers.items():
            t = totals[key]
            d.setText(GEAR_COL["qty"], f"{t.pieces:,}")
            d.setText(GEAR_COL["paid"], money.fmt_short(money.whole(t.paid), cur) if t.paid else "")
            d.setText(GEAR_COL["value"], money.fmt_short(money.whole(t.value), cur) if t.value else "")
            d.setText(GEAR_COL["day"], money.fmt_short(t.day, cur) if t.day else "")
            d.setExpanded(d.data(0, HEAD + 10) not in self.folded)
            d.setData(0, OPEN, d.isExpanded())
        self._apply_columns()
        self._fill_end(keep, col, order)
        self.filter("")

    def _row(self, it: Item, st, cur: str, out: dict, parent, on: str, pos: int) -> Row:
        status, color = status_of(it, out.get(it.id, 0))
        e = self.earned.get(it.id) if self.earned is not None else None
        made = e.amount if e is not None else money.ZERO
        day = st.day if it.rentable else None
        row = self.make(
            it.id,
            [
                ("", pos),  # its tick
                (it.name or "Untitled Piece", it.name.casefold()),
                (on, (on or "~").casefold()),
                (it.brand, (it.brand or "~").casefold()),
                (it.series, (it.series or "~").casefold()),
                (it.group, (it.group or "~").casefold()),
                (str(it.qty), it.qty),
                (status, status),
                (money.fmt_short(money.whole(st.paid), cur) if st.paid else "", money.in_cents(st.paid)),
                (money.fmt_short(money.whole(st.value), cur) if st.value else "", money.in_cents(st.value)),
                (
                    money.fmt_short(day, cur) if day else ("—" if not it.rentable else ""),
                    money.in_cents(day or 0),
                ),
                (money.fmt_short(made, cur) if made else "", money.in_cents(made)),
                ("", pos),  # its grip: your order
            ],
            parent,
        )
        row.setData(GEAR_COL["status"], DOT, color)
        for k in ("with", "brand", "series"):
            row.setForeground(GEAR_COL[k], theme.qcolor(tokens.MUTED))
        if on:
            row.setData(0, WITH, on)
            row.setToolTip(GEAR_COL["name"], theme.plain_tip(f"{it.name}\nGoes with {on}"))
        row.setData(0, WHERE, (it.group, it.brand))
        row.setData(0, PHOTO, it.photo)
        row.setData(0, HAY, search.gear_hay(it, on))
        return row

    def _family(self, row: Row, it: Item, kids: list[Item], lib: Library, b: Business | None, cur: str, out) -> None:
        """A piece with gear under it (G.11): its name in Semibold and how many go with it; its figures are it with
        all of them (what a rental line of it costs); closed, its status is the most pressing among them."""
        n = len(kids)
        words = f"{n} Attached"
        row.setData(0, SUMMARY, words)
        row.setFont(GEAR_COL["name"], theme.font(tokens.TEXT_MD, tokens.WEIGHT_SEMIBOLD))
        alone = self.stocks[it.id]
        everything = pricing.stock(lib, it, b)  # the piece and all that goes with it
        made = alone_made = money.ZERO
        if self.earned is not None:
            alone_made = self.earned[it.id].amount if it.id in self.earned else money.ZERO
            made = sum((self.earned[x.id].amount for x in (it, *kids) if x.id in self.earned), money.ZERO)
        day, own_day = (everything.day, alone.day) if it.rentable else (None, None)
        figures = (
            ("paid", money.whole(everything.paid), money.whole(alone.paid)),
            ("value", money.whole(everything.value), money.whole(alone.value)),
            ("day", day, own_day),
            ("earned", made, alone_made),
        )
        for key, total, own in figures:
            if total is None:
                continue
            col = GEAR_COL[key]
            row.setText(col, money.fmt_short(total, cur) if total else "")
            row.setData(col, SORT, money.in_cents(total))
            if total != own:
                row.setToolTip(col, f"With what goes with it ({money.fmt_short(own or money.ZERO, cur)} on its own)")
        own_status = (*status_of(it, out.get(it.id, 0)), "")
        row.setData(0, STATUSES, (own_status, family_status(it, kids, out)))
        self._show_status(row)

    def item_rows(self):
        """Every gear row (not the dividers), and the gear under each piece after it."""

        def walk(row):
            for i in range(row.childCount()):
                r = row.child(i)
                if r.data(0, HEAD) is None:
                    yield r
                yield from walk(r)

        yield from walk(self.invisibleRootItem())

    def show_only(self, text: str, keep=None) -> list[str]:
        """Hide rows that don't match every word of `text` (and `keep(item_id)`, when given). A piece whose gear
        matches shows too, opened to show it (G.11); clearing the search closes what you hadn't opened. Returns the
        ids of the rows that match, top to bottom (those under a closed piece too)."""
        words = search.words(text)
        narrowed = bool(words) or keep is not None

        def matches(row) -> bool:
            ok = all(w in (row.data(0, HAY) or "") for w in words)
            return ok and (keep is None or keep(row.data(0, ID)))

        cur = self.currentItem()
        shown: list[str] = []
        for row in self.item_rows():
            if row.data(0, CHILD) is not None:
                continue  # (with its piece)
            me = matches(row)
            kids = [row.child(i) for i in range(row.childCount())]
            found = [k for k in kids if matches(k)]
            for k in kids:
                k.setHidden(k not in found)
            row.setHidden(not (me or found))
            if me:
                shown.append(row.data(0, ID))
            shown.extend(k.data(0, ID) for k in found)
            if kids:
                want = row.data(0, ID) in self.open_pieces or (narrowed and bool(found))
                want = want or (cur is not None and cur.parent() is row and not cur.isHidden())
                if row.isExpanded() != want:
                    row.setExpanded(want)
        self.shown = shown
        root = self.invisibleRootItem()
        for i in range(root.childCount()):
            d = root.child(i)
            if d.data(0, HEAD) is not None:
                any_shown = any(not d.child(k).isHidden() for k in range(d.childCount()))
                d.setHidden(not any_shown)
                if words and any_shown and not d.isExpanded():
                    d.setExpanded(True)
                    d.setData(0, OPEN, True)
        return shown

    def filter(self, text: str) -> int:
        return len(self.show_only(text))


class KitTable(Table):
    COLUMNS = [
        ("", tokens.TICK_W, None),
        ("Name", 0, None),
        ("Pieces", tokens.COL_W["pieces"], CENTER),
        ("Day Rate", tokens.COL_W["rate"], RIGHT),
        ("Week", tokens.COL_W["rate"], RIGHT),
        ("Value", tokens.COL_W["value"], RIGHT),
    ]
    STEP_ASIDE = (5, 4)  # Value, then Week

    def fill(self, lib: Library, b: Business | None) -> None:
        keep, col, order = self._fill_start()
        cur = (b.currency if b else "$") or "$"
        wd = b.week_days if b else 7
        for p in lib.packages.values():
            pieces = sum(u for _i, u, _d in pricing.package_gear(lib, p))
            rate = pricing.package_rate(lib, p, b)
            value = pricing.package_value(lib, p, b)
            row = self.make(
                p.id,
                [
                    ("", None),  # its tick
                    (p.name or "Untitled Kit", p.name.casefold()),
                    (str(pieces), pieces),
                    (money.fmt_short(rate, cur), money.in_cents(rate)),
                    (money.fmt_short(rate * wd, cur), money.in_cents(rate * wd)),
                    (money.fmt_short(money.whole(value), cur), money.in_cents(value)),
                ],
            )
            row.setData(0, HAY, search.kit_hay(p))
        self._fill_end(keep, col, order)


STATUS_COLORS = {  # token names, read when filling (light and dark differ)
    "quote": "MUTED",
    "booked": "INFO",
    "out": "WARN",
    "late": "BAD",
    "returned": "GOOD",
    "cancelled": "MUTED",
}


class RentalTable(Table):
    COLUMNS = [
        ("", tokens.TICK_W, None),
        ("Rental", tokens.COL_W["rental"], None),
        ("Renter", 0, None),
        ("Production", tokens.COL_W["production"], None),
        ("Dates", tokens.COL_W["dates"], None),
        ("Status", tokens.COL_W["rental_status"], None),
        ("Total", tokens.COL_W["total"], RIGHT),
    ]
    STEP_ASIDE = (3, 6, 5)  # Production, then Total (the open rental's panel shows it), then Status
    WIDE_MIN = tokens.RENTER_MIN
    DATES = 4

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.sortByColumn(self.DATES, Qt.SortOrder.DescendingOrder)  # newest dates first

    def fill(self, lib: Library, which: str) -> None:
        keep, col, order = self._fill_start()
        for r in lib.rentals.values():
            if which == "out" and not r.is_out():
                continue
            if which == "upcoming" and not pricing.coming_up(r):  # the same rule as the sidebar's count
                continue
            b = lib.businesses.get(r.business_id)
            cur = (b.currency if b else "$") or "$"
            t = pricing.totals(lib, r, b)
            a, z = pricing.span_of(r)
            tone = "late" if pricing.late(r) else r.status
            who = r.client.company or r.client.name
            row = self.make(
                r.id,
                [
                    ("", None),  # its tick
                    (r.number, r.number),
                    (who or "No renter yet", who.casefold() or "~"),
                    (r.project, r.project.casefold()),
                    (dates.span(a, z), dates.iso(a) if a else ""),
                    ("Late" if tone == "late" else RENTAL_WORDS[r.status], tone),
                    (money.fmt(t.total, cur), money.in_cents(t.total)),
                ],
            )
            row.setData(5, DOT, getattr(tokens, STATUS_COLORS[tone]))  # (its status)
            row.setData(0, HAY, search.rental_hay(r))
        self._fill_end(keep, col, order)


class RenterTable(Table):
    """The Renters page (N-18): everyone you rent to, with how many rentals and the last one's dates."""

    COLUMNS = [
        ("", tokens.TICK_W, None),
        ("Name", 0, None),
        ("Company", tokens.COL_W["company"], None),
        ("Email", tokens.COL_W["email"], None),
        ("Phone", tokens.COL_W["phone"], None),
        ("Rentals", tokens.COL_W["rentals"], CENTER),
        ("Last Rental", tokens.COL_W["last"], None),
    ]
    STEP_ASIDE = (4, 3, 6)  # Phone, then Email, then the last rental's dates
    WIDE_MIN = tokens.RENTER_MIN

    def fill(self, lib: Library) -> None:
        keep, col, order = self._fill_start()
        theirs: dict[str, list] = {}
        for r in lib.rentals.values():
            theirs.setdefault(r.client.id, []).append(r)
        for c in lib.clients.values():
            mine = theirs.get(c.id, [])
            last = max((dates.parse(r.pickup) for r in mine if dates.parse(r.pickup)), default=None)
            name = c.name or c.company or "Unnamed Renter"
            row = self.make(
                c.id,
                [
                    ("", None),  # its tick
                    (name, name.casefold()),
                    (c.company if c.name else "", c.company.casefold()),
                    (c.email, c.email.casefold()),
                    (c.phone, c.phone),
                    (str(len(mine)), len(mine)),
                    (dates.fmt(last) if last else "", dates.iso(last) if last else ""),
                ],
            )
            row.setData(0, HAY, search.renter_hay(c))
        self._fill_end(keep, col, order)


def menu(parent: QWidget, items: list[tuple[str, str, object]]) -> QMenu:
    m = QMenu(parent)
    for icon, text, slot in items:
        if text == "-":
            m.addSeparator()
        else:
            m.addAction(theme.menu_icon(icon), text, slot)
    return m
