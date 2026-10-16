"""The big tables in the middle: gear, kits and rentals. Click a row to edit it on the right.

Every column sorts; the grip column is your own order (drag a row by its grip to change it). Gear is divided
by department, group or company (or not at all), each divider with its totals; click one to fold it. Gear
that goes with a piece isn't listed under it: the piece shows "+3" and the inspector lists them. Searching
finds them too. Right-click the column titles to choose the columns.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QPoint, QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QKeySequence, QPainter, QPen, QPixmap, QRegion
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
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
from bodega.core.model import Business, Item
from bodega.core.store import Library
from bodega.ui.components import photos
from bodega.ui.style import theme, tokens
from bodega.ui.window.lift import Lift

ID = Qt.ItemDataRole.UserRole
SORT = Qt.ItemDataRole.UserRole + 1
HAY = Qt.ItemDataRole.UserRole + 2
HEAD = Qt.ItemDataRole.UserRole + 3  # a divider row: its place in the list
ATTACHED = Qt.ItemDataRole.UserRole + 4  # attached gear: only shown when searching
DEP = Qt.ItemDataRole.UserRole + 5  # a divider's department
GRP = Qt.ItemDataRole.UserRole + 6  # a group divider's group (None on a department divider)

RIGHT = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
CENTER = Qt.AlignmentFlag.AlignCenter


class Row(QTreeWidgetItem):
    """Sorts by the hidden sort key of the clicked column (numbers as numbers, words as words)."""

    def __lt__(self, other):
        tree = self.treeWidget()
        col = tree.sortColumn() if tree else 0
        ha, hb = self.data(0, HEAD), other.data(0, HEAD)
        if ha is not None and hb is not None:  # dividers keep their order whichever way you sort
            descending = (
                tree is not None and tree.header().sortIndicatorOrder() == Qt.SortOrder.DescendingOrder
            )
            return ha > hb if descending else ha < hb
        a, b = self.data(col, SORT), other.data(col, SORT)
        if a is None or b is None:
            return (self.text(col) or "").casefold() < (other.text(col) or "").casefold()
        if isinstance(a, str) or isinstance(b, str):
            return str(a).casefold() < str(b).casefold()
        return a < b


class Table(QTreeWidget):
    picked = Signal(str)
    menu_wanted = Signal(str, QPoint)
    delete_wanted = Signal(list)  # Delete / Backspace on the selected rows
    cleared = Signal()  # a click on empty space: nothing picked

    COLUMNS: list[tuple[str, int, object]] = []  # (title, width or 0 = stretch, alignment)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Table")
        self.setColumnCount(len(self.COLUMNS))
        self.setHeaderLabels([c[0] for c in self.COLUMNS])
        self.setRootIsDecorated(False)
        self.setUniformRowHeights(True)
        self.setAlternatingRowColors(False)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
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
        for i, (_t, w, align) in enumerate(self.COLUMNS):
            if w:
                h.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
                self.setColumnWidth(i, w)
            else:
                h.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
            if align is not None:
                self.headerItem().setTextAlignment(i, align)
        self.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self.setItemDelegate(RowPainter(self))
        self.setMouseTracking(True)
        self.currentItemChanged.connect(self._current)
        self._quiet = False

    # ------------------------------------------------------------------ sliding with the inspector
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

    # ------------------------------------------------------------------ narrow
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
            self.setCurrentItem(found)
            self.scrollToItem(found, QAbstractItemView.ScrollHint.PositionAtCenter)
        else:
            self.clearSelection()
        self._quiet = False

    def mousePressEvent(self, e):
        if self.itemAt(e.position().toPoint()) is None:
            self.cleared.emit()
            return
        super().mousePressEvent(e)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape and getattr(self, "_lift", None) is not None:
            self.end_lift(drop=False)  # put it back
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

    def select_showing(self) -> None:
        """Cmd+A: everything you can see (never the dividers, never hidden rows)."""
        if self.selectionMode() != QAbstractItemView.SelectionMode.ExtendedSelection:
            return
        self.clearSelection()
        for r in self.showing_rows():
            r.setSelected(True)

    def chosen_ids(self) -> list[str]:
        """The selected rows you can see, top to bottom (or the current row)."""
        ids = [r.data(0, ID) for r in self.showing_rows() if r.isSelected()]
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
        col = self.sortColumn()
        order = self.header().sortIndicatorOrder()
        self._quiet = True
        self.setSortingEnabled(False)
        self.clear()
        return keep, col, order

    def _fill_end(self, keep: str, col: int, order) -> None:
        self.setSortingEnabled(True)
        self.sortItems(max(0, col), order)
        self._quiet = False
        if keep:
            self.select_id(keep)


def _tone(it: Item, out: int) -> tuple[str, str]:
    """The status column: what it says and its color."""
    if it.status == "repair":
        return "Repair", tokens.WARN  # amber, like the In Repair chip everywhere else
    if it.status == "retired":
        return "Retired", tokens.MUTED
    if out >= it.qty:
        return "Out", tokens.WARN
    if out:
        return f"{it.qty - out} of {it.qty} In", tokens.WARN
    return "In", tokens.MUTED


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
        """Paint the row's shape; True for a divider."""
        row0 = index.siblingAtColumn(0)
        divider = row0.data(HEAD) is not None
        hover = bool(option.state & QStyle.StateFlag.State_MouseOver)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        if divider:
            self.row_shape(
                painter, option, index, theme.qcolor(tokens.DIVIDER_HOVER if hover else tokens.DIVIDER)
            )
        elif selected:
            self.row_shape(painter, option, index, theme.qcolor(tokens.CARD_SELECTED))
        elif hover:
            self.row_shape(painter, option, index, theme.qcolor(tokens.ROW_HOVER))
        return divider

    @staticmethod
    def plain(option) -> QStyleOptionViewItem:
        """The cell without hover or selection (its row shape is already drawn)."""
        opt = QStyleOptionViewItem(option)
        opt.state &= ~(
            QStyle.StateFlag.State_MouseOver
            | QStyle.StateFlag.State_Selected
            | QStyle.StateFlag.State_HasFocus
        )
        return opt

    def paint(self, painter, option, index):
        self.backdrop(painter, option, index)
        super().paint(painter, self.plain(option), index)

    def helpEvent(self, event, view, option, index):
        """A cell's own tooltip, or else, when the cell cuts its words short, the whole of them."""
        if (
            event.type() != QEvent.Type.ToolTip
            or not index.isValid()
            or index.data(Qt.ItemDataRole.ToolTipRole)
        ):
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
        if index.column() == GEAR_COL["name"] and getattr(view, "thumbs", False):
            room -= tokens.TABLE_THUMB + tokens.SPACE_2
        return text if text and option.fontMetrics.horizontalAdvance(text) > room else ""


class _GearPainter(RowPainter):
    """…plus the divider's chevron, the grip you drag a row by, and "with Sony FX6" after linked gear."""

    def paint(self, painter, option, index):
        row0 = index.siblingAtColumn(0)
        divider = self.backdrop(painter, option, index)
        option = self.plain(option)
        if index.column() == 0:
            if divider:
                self._chevron(painter, option.rect, bool(row0.data(OPEN)))
            elif row0.data(ID):
                self._grip(painter, option.rect)
            return
        with_ = row0.data(WITH)
        if index.column() == GEAR_COL["name"] and not divider and getattr(self.parent(), "thumbs", False):
            option = self._thumb(painter, option, row0.data(PHOTO) or "")
        if with_ and index.column() == GEAR_COL["name"]:
            self._name_with(painter, option, index, with_)
            return
        QStyledItemDelegate.paint(self, painter, option, index)

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

    def _name_with(self, painter, option, index, parent_name: str) -> None:
        """A piece that goes with another: its name, then "with Sony FX6" in grey."""
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        name, opt.text = opt.text, ""
        w = opt.widget
        style = w.style() if w else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, w)
        # where Qt puts a cell's text, so these names line up with the others
        rect = style.subElementRect(QStyle.SubElement.SE_ItemViewItemText, opt, w)
        margin = style.pixelMetric(QStyle.PixelMetric.PM_FocusFrameHMargin, None, w) + 1
        rect = rect.adjusted(margin, 0, -margin, 0)
        fm = opt.fontMetrics
        suffix = f"  with {parent_name}"
        room = rect.width()
        if fm.horizontalAdvance(name + suffix) > room:
            keep = max(room // 2, room - fm.horizontalAdvance(suffix))
            name = fm.elidedText(name, Qt.TextElideMode.ElideRight, keep)
        name_w = fm.horizontalAdvance(name)
        suffix = fm.elidedText(suffix, Qt.TextElideMode.ElideRight, max(0, room - name_w))
        painter.save()
        align = int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        painter.setPen(theme.qcolor(tokens.TEXT))
        painter.drawText(rect, align, name)
        painter.setPen(theme.qcolor(tokens.MUTED))
        painter.drawText(rect.adjusted(name_w, 0, 0, 0), align, suffix)
        painter.restore()

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
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(theme.qcolor(tokens.FAINT))
        c = QPointF(rect.center())
        gap = tokens.GRIP_GAP
        for dx in (-gap / 2, gap / 2):
            for dy in (-gap, 0, gap):
                painter.drawEllipse(QPointF(c.x() + dx, c.y() + dy), tokens.GRIP_DOT, tokens.GRIP_DOT)
        painter.restore()


# the gear table's columns: key, title, width (0 = takes the rest), alignment
GEAR_COLUMNS = [
    ("grip", "", tokens.GRIP_W, None),
    ("name", "Name", 0, None),
    ("kids", "", tokens.COL_W["kids"], None),
    ("brand", "Company", tokens.COL_W["company"], None),
    ("series", "Series", tokens.COL_W["series"], None),
    ("group", "Group", tokens.COL_W["group"], None),
    ("qty", "Qty", tokens.COL_W["qty"], CENTER),
    ("status", "Status", tokens.COL_W["status"], None),
    ("paid", "Paid", tokens.COL_W["paid"], RIGHT),
    ("value", "With Tax", tokens.COL_W["with_tax"], RIGHT),
    ("day", "Day Rate", tokens.COL_W["day"], RIGHT),
    ("earned", "Earned", tokens.COL_W["earned"], RIGHT),  # rental income so far (core/earnings.py)
]
GEAR_COL = {key: n for n, (key, *_rest) in enumerate(GEAR_COLUMNS)}
HIDDEN_AT_FIRST = ["series", "paid", "earned"]
# on a narrow window these columns step aside first (Name always keeps NAME_MIN)
GIVE_WAY = ["earned", "series", "paid", "status", "brand", "group", "kids", "qty", "day"]
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


class GearTable(Table):
    divider_menu = Signal(str, QPoint)  # the group a divider stands for, where
    dropped = Signal(list, str)  # gear ids, the group they were dropped into
    branded = Signal(list, str)  # gear ids dropped onto a company divider
    reordered = Signal(list, str, bool)  # gear ids, the row they were dropped on, after it?
    columns_changed = Signal(list)  # the column keys you hid
    folds_changed = Signal()  # a divider folded or opened, by a click or the keyboard (kept in settings)

    COLUMNS = [(title, w, align) for _k, title, w, align in GEAR_COLUMNS]

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setRootIsDecorated(False)
        self.setIndentation(0)
        h = self.headerItem()
        h.setToolTip(GEAR_COL["grip"], "Your order")
        h.setToolTip(GEAR_COL["kids"], "Gear that goes with it")
        h.setToolTip(GEAR_COL["paid"], "What it cost, before tax (what goes with it included)")
        h.setToolTip(GEAR_COL["value"], "Replacement value: paid plus sales tax")
        h.setToolTip(
            GEAR_COL["earned"], "An estimate: each rental's gear total, shared out by each piece's day rate"
        )
        self.header().setSectionResizeMode(GEAR_COL["grip"], QHeaderView.ResizeMode.Fixed)
        self.header().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.header().customContextMenuRequested.connect(self._column_menu)
        self.folded: set[str] = set()  # dividers you folded
        self.opened: set[str] = set()  # kept for older settings files
        self.hidden_cols: set[str] = set(HIDDEN_AT_FIRST)
        self._squeezed: set[str] = set()  # stepped aside because the window is narrow
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

    # ------------------------------------------------------------------ columns
    def _column_menu(self, pos) -> None:
        m = QMenu(self)
        for key, title, _w, _a in GEAR_COLUMNS:
            if key in ("grip", "name"):
                continue
            a = m.addAction(title or "Goes With (+3)")
            a.setCheckable(True)
            a.setChecked(key not in self.hidden_cols)
            a.toggled.connect(lambda on, k=key: self._toggle_column(k, on))
        m.exec(self.header().mapToGlobal(pos))

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

    # ------------------------------------------------------------------ dragging
    def selected_ids(self) -> list[str]:
        return self.chosen_ids()

    def _describe(self, row) -> tuple:
        """For the Lift: what a row is."""
        if row.data(0, HEAD) is not None:
            return ("divider", row.data(0, GRP) or "", row.data(0, KIND) or "group")
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
        if row is not None and row.data(0, ID) and self.columnAt(pos.x()) == GEAR_COL["grip"]:
            return row
        return None

    def mousePressEvent(self, e):
        row = self._on_grip(e.position().toPoint())
        if e.button() == Qt.MouseButton.LeftButton and row is not None and not e.modifiers():
            if not row.isSelected():
                self.clearSelection()
                row.setSelected(True)
            self._press = (e.position().toPoint(), row)
            e.accept()
            return
        super().mousePressEvent(e)

    def start_lift(self, row, y: float) -> None:
        """Lift the pressed row (and the others selected with it) to drag it into place."""
        if not self.your_order():  # dragging means your own order: switch to it first
            self.sortByColumn(GEAR_COL["grip"], Qt.SortOrder.AscendingOrder)
            y = self.visualItemRect(row).center().y()
        ids = [i for i in self.chosen_ids() if i] or [row.data(0, ID)]
        if row.data(0, ID) not in ids:
            ids = [row.data(0, ID)]
        self._lift = Lift(self, self._visible_rows(), ids, row, y, self._describe)
        self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)

    def end_lift(self, drop: bool = True) -> None:
        lift, self._lift = self._lift, None
        if lift is None:
            return
        lift.stop()
        later, self._fill_later = self._fill_later, None
        if later is not None:  # the list changed while it was lifted
            QTimer.singleShot(0, lambda: self.fill(*later))
        self.viewport().setCursor(Qt.CursorShape.ArrowCursor)
        self.viewport().update()
        got = lift.result() if drop else None
        if got is None:
            return
        ids = lift.ids
        if got[0] in ("before", "after"):
            QTimer.singleShot(0, lambda: self.reordered.emit(ids, got[1], got[0] == "after"))
        elif got[2] == "brand":
            QTimer.singleShot(0, lambda: self.branded.emit(ids, got[1]))
        else:
            QTimer.singleShot(0, lambda: self.dropped.emit(ids, got[1]))

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
            row = self.itemAt(e.position().toPoint())
            on_grip = (
                row is not None
                and row.data(0, ID)
                and self.columnAt(int(e.position().x())) == GEAR_COL["grip"]
            )
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
        return [
            root.child(i) for i in range(root.childCount()) if root.child(i).data(0, HEAD + 10) is not None
        ]

    def _fold(self, row, opening: bool) -> None:
        row.setExpanded(opening)
        row.setData(0, OPEN, opening)
        (self.folded.discard if opening else self.folded.add)(row.data(0, HEAD + 10))

    def keyPressEvent(self, e):
        """On a divider, → opens it and ← folds it (remembered, as a click is); Space or Return does either."""
        row = self.currentItem()
        k = e.key()
        if (
            row is not None
            and row.data(0, HEAD + 10) is not None
            and not e.modifiers() & ~Qt.KeyboardModifier.KeypadModifier
        ):
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

    # ------------------------------------------------------------------ filling
    def fill(self, lib: Library, b: Business | None, group: str = "", divide: str = "") -> None:
        if self._lift is not None:  # never rebuild the rows under a row being dragged: after it lands
            self._fill_later = (lib, b, group, divide)
            return
        self.thumbs = any(it.photo for it in lib.items.values())  # once one has a photo, every row has room
        self.earned = earnings.earnings(lib)
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

        def key_of(i: Item):
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
                d.setForeground(
                    c, theme.qcolor(tokens.MUTED if c == GEAR_COL["name"] else tokens.DIVIDER_TEXT)
                )
                if align is not None:
                    d.setTextAlignment(c, align)
            dividers[key] = d
        totals = {key: pricing.Stock() for key in dividers}
        for it in items:
            st = pricing.stock(lib, it, b, attached=False)  # each row is that piece alone
            self.stocks[it.id] = st
            kids = len(pricing.children(lib, it.id))
            on = lib.items.get(it.parent) if it.parent else None
            self._row(
                it, st, kids, cur, out, dividers.get(key_of(it), self), on.name if on else "", position[it.id]
            )
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

    def _row(self, it: Item, st, kids: int, cur: str, out: dict, parent, on: str, pos: int) -> Row:
        status, color = _tone(it, out.get(it.id, 0))
        e = self.earned.get(it.id)
        made = e.amount if e is not None else money.ZERO
        day = st.day if it.rentable else None
        row = self.make(
            it.id,
            [
                ("", pos),
                (it.name or "New item", it.name.casefold()),
                (f"+{kids}" if kids else "", kids),
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
            ],
            parent,
        )
        row.setForeground(GEAR_COL["status"], theme.qcolor(color))
        row.setForeground(GEAR_COL["kids"], theme.qcolor(tokens.MUTED))  # a count, not a button
        for k in ("brand", "series"):
            row.setForeground(GEAR_COL[k], theme.qcolor(tokens.MUTED))
        if kids:
            row.setToolTip(GEAR_COL["kids"], f"{kids} go with it")
        if on:
            row.setData(0, WITH, on)
            row.setToolTip(GEAR_COL["name"], theme.plain_tip(f"{it.name}\nGoes with {on}"))
        row.setData(0, WHERE, (it.group, it.brand))
        row.setData(0, PHOTO, it.photo)
        hay = (it.name, it.brand, it.series, it.group, it.notes, " ".join(it.serials), on)
        row.setData(0, HAY, search.folded(" ".join(hay)))
        return row

    def item_rows(self):
        """Every gear row (not the dividers)."""
        root = self.invisibleRootItem()
        for i in range(root.childCount()):
            top = root.child(i)
            if top.data(0, HEAD) is None:
                yield top
            else:
                for k in range(top.childCount()):
                    yield top.child(k)

    def show_only(self, text: str, keep=None) -> list[str]:
        """Hide rows that don't match every word of `text` (and `keep(item_id)`, when given).
        Gear that goes with a piece shows only when searching. Returns the ids of the rows left showing."""
        words = search.words(text)
        shown: list[str] = []
        for row in self.item_rows():
            ok = all(w in (row.data(0, HAY) or "") for w in words)
            if ok and keep is not None:
                ok = keep(row.data(0, ID))
            row.setHidden(not ok)
            if ok:
                shown.append(row.data(0, ID))
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
        ("Name", 0, None),
        ("Pieces", tokens.COL_W["pieces"], CENTER),
        ("Day Rate", tokens.COL_W["rate"], RIGHT),
        ("Week", tokens.COL_W["rate"], RIGHT),
        ("Value", tokens.COL_W["value"], RIGHT),
    ]
    STEP_ASIDE = (4, 3)  # Value, then Week

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
                    (p.name or "New kit", p.name.casefold()),
                    (str(pieces), pieces),
                    (money.fmt_short(rate, cur), money.in_cents(rate)),
                    (money.fmt_short(rate * wd, cur), money.in_cents(rate * wd)),
                    (money.fmt_short(money.whole(value), cur), money.in_cents(value)),
                ],
            )
            row.setData(0, HAY, search.folded(p.name + " " + p.notes))
        self._fill_end(keep, col, order)


STATUS_WORDS = {
    "quote": "Quote",
    "booked": "Booked",
    "out": "Out",
    "returned": "Returned",
    "cancelled": "Cancelled",
}
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
        ("Rental", tokens.COL_W["rental"], None),
        ("Renter", 0, None),
        ("Production", tokens.COL_W["production"], None),
        ("Dates", tokens.COL_W["dates"], None),
        ("Status", tokens.COL_W["rental_status"], None),
        ("Total", tokens.COL_W["total"], RIGHT),
    ]
    STEP_ASIDE = (2, 5, 4)  # Production, then Total (the open rental's panel shows it), then Status
    WIDE_MIN = tokens.RENTER_MIN

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.sortByColumn(3, Qt.SortOrder.DescendingOrder)  # newest dates first

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
                    (r.number, r.number),
                    (who or "No renter yet", who.casefold() or "~"),
                    (r.project, r.project.casefold()),
                    (dates.span(a, z), dates.iso(a) if a else ""),
                    ("Late" if tone == "late" else STATUS_WORDS[r.status], tone),
                    (money.fmt(t.total, cur), money.in_cents(t.total)),
                ],
            )
            row.setForeground(4, theme.qcolor(getattr(tokens, STATUS_COLORS[tone])))
            row.setData(
                0, HAY, search.folded(" ".join((r.number, r.client.name, r.client.company, r.project)))
            )
        self._fill_end(keep, col, order)


def menu(parent: QWidget, items: list[tuple[str, str, object]]) -> QMenu:
    m = QMenu(parent)
    for icon, text, slot in items:
        if text == "-":
            m.addSeparator()
        else:
            m.addAction(theme.menu_icon(icon), text, slot)
    return m
