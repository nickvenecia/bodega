"""The date field (the standard's G.22): a text field with the date in the accent's words and a calendar glyph.

Click it, or press ↓, and the month opens under it: ← → a day, ↑ ↓ a week, Page Up and Page Down a month, Return
or Space chooses, Esc closes. Typing works too ("10/16", "Oct 16", "today": core/dates.typed) and counts as soon
as it reads as a date. It has QDateEdit's few calls the panels use: date(), setDate(), dateChanged,
setMinimumDate(), minimumDate().
"""

from __future__ import annotations

from PySide6.QtCore import QDate, QEvent, QPoint, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QKeyEvent, QPainter, QPen
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QLineEdit, QWidget

from bodega.core import dates
from bodega.ui.style import theme, tokens

DATE_FORMATS = ("ddd, MMM d, yyyy", "MMM d, yyyy", "M/d/yy")  # the longest that fits is shown
EARLIEST = QDate(1900, 1, 1)


def _qdate(d) -> QDate:
    return QDate(d.year, d.month, d.day)


def _pydate(q: QDate):
    from datetime import date

    return date(q.year(), q.month(), q.day())


class MonthGrid(QWidget):
    """The days of one month in seven columns, Sunday first. Painted: the chosen day an accent circle, today in
    the accent's words, days before the earliest allowed faded."""

    chosen = Signal(QDate)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.month = QDate.currentDate().addDays(1 - QDate.currentDate().day())  # the 1st of the month shown
        self.picked = QDate.currentDate()
        self.cursor = QDate.currentDate()  # where the keys are (ringed once it leaves the chosen day)
        self.earliest = EARLIEST
        self._hover: QDate | None = None
        self.setMouseTracking(True)
        self.setFixedSize(self.sizeHint())

    def sizeHint(self) -> QSize:
        w = 7 * tokens.DAY_CELL_W
        h = tokens.DAY_LETTERS_H + tokens.SPACE_1 + 6 * tokens.DAY_CELL_H + 5 * tokens.SPACE_0_5
        return QSize(w, h)

    def show_month(self, any_day: QDate) -> None:
        self.month = any_day.addDays(1 - any_day.day())
        self.update()

    def _first_cell(self) -> QDate:
        """The Sunday on or before the 1st (Qt counts Monday as 1, Sunday as 7)."""
        return self.month.addDays(-(self.month.dayOfWeek() % 7))

    def _cell(self, n: int) -> QRectF:
        row, col = divmod(n, 7)
        top = tokens.DAY_LETTERS_H + tokens.SPACE_1 + row * (tokens.DAY_CELL_H + tokens.SPACE_0_5)
        return QRectF(col * tokens.DAY_CELL_W, top, tokens.DAY_CELL_W, tokens.DAY_CELL_H)

    def day_at(self, pos) -> QDate | None:
        first = self._first_cell()
        for n in range(42):
            d = first.addDays(n)
            if d.month() == self.month.month() and self._cell(n).contains(pos):
                return d
        return None

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        letters = theme.font(tokens.TEXT_SUBHEAD, tokens.WEIGHT_SEMIBOLD)
        p.setFont(letters)
        p.setPen(theme.qcolor(tokens.MUTED))
        for col, name in enumerate(dates.CAL_WEEKDAYS):
            box = QRectF(col * tokens.DAY_CELL_W, 0, tokens.DAY_CELL_W, tokens.DAY_LETTERS_H)
            p.drawText(box, int(Qt.AlignmentFlag.AlignCenter), name[0])
        today, first = QDate.currentDate(), self._first_cell()
        plain = theme.font(tokens.TEXT_TITLE3, tabular=True)
        bold = theme.font(tokens.TEXT_TITLE3, tokens.WEIGHT_SEMIBOLD, tabular=True)
        r = tokens.CONTROL_H / 2
        for n in range(42):
            d = first.addDays(n)
            if d.month() != self.month.month():
                continue
            cell = self._cell(n)
            c = cell.center()
            circle = QRectF(c.x() - r, c.y() - r, 2 * r, 2 * r)
            off = d < self.earliest
            p.setPen(Qt.PenStyle.NoPen)
            if d == self.picked:
                p.setBrush(theme.qcolor(tokens.ACCENT_FILL))
                p.drawEllipse(circle)
            elif d == self._hover and not off:
                p.setBrush(theme.qcolor(tokens.FILL_2))
                p.drawEllipse(circle)
            if d == self.cursor and d != self.picked:  # the keys are here
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(theme.qcolor(tokens.ACCENT), tokens.FOCUS_RING))
                p.drawEllipse(circle)
            p.setFont(bold if d in (self.picked, today) else plain)
            if d == self.picked:
                p.setPen(theme.qcolor(tokens.ON_ACCENT))
            elif off:
                p.setPen(theme.qcolor(tokens.TEXT_OFF))
            elif d == today:
                p.setPen(theme.qcolor(tokens.ACCENT_TEXT))
            else:
                p.setPen(theme.qcolor(tokens.TEXT))
            p.drawText(circle, int(Qt.AlignmentFlag.AlignCenter), str(d.day()))
        p.end()

    def mouseMoveEvent(self, e):
        d = self.day_at(e.position())
        if d != self._hover:
            self._hover = d
            self.update()

    def leaveEvent(self, _e):
        self._hover = None
        self.update()

    def mouseReleaseEvent(self, e):
        d = self.day_at(e.position())
        if d is not None and d >= self.earliest and e.button() == Qt.MouseButton.LeftButton:
            self.chosen.emit(d)


class MonthPopover(QFrame):
    """The month, under its field, as a menu opens (one at a time, gone with a click outside or Esc)."""

    chosen = Signal(QDate)

    def __init__(self, field: QWidget):
        super().__init__(field, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowFlag(Qt.WindowType.NoDropShadowWindowHint, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.field = field
        from bodega.ui.components.widgets import circle_button, hbox, vbox

        outer = vbox(self, 0, 0)
        card = QFrame()
        card.setObjectName("DatePop")
        outer.addWidget(card)
        pad = tokens.SPACE_2_5
        lay = vbox(card, (pad, pad, pad, tokens.SPACE_2), tokens.SPACE_2)
        head = hbox(spacing=tokens.SPACE_1)
        head.setContentsMargins(tokens.SPACE_2, tokens.SPACE_0_5, tokens.SPACE_0_5, 0)
        self.title = QLabel()
        self.title.setObjectName("DatePopTitle")
        self.prev = circle_button("chevron-left", "Earlier Month (Page Up)", theme.ACCENT)
        self.next = circle_button("chevron-right", "Later Month (Page Down)", theme.ACCENT)
        for b in (self.prev, self.next):
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        head.addWidget(self.title, 1)
        head.addWidget(self.prev)
        head.addWidget(self.next)
        lay.addLayout(head)
        self.grid = MonthGrid()
        lay.addWidget(self.grid)
        self.prev.clicked.connect(lambda: self._months(-1))
        self.next.clicked.connect(lambda: self._months(1))
        self.grid.chosen.connect(self._choose)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName("Choose a Date")

    def open_at(self, picked: QDate, earliest: QDate) -> None:
        g = self.grid
        g.picked = g.cursor = picked
        g.earliest = earliest
        self._show_month(picked)
        self.adjustSize()
        below = self.field.mapToGlobal(QPoint(0, self.field.height() + tokens.MENU_GAP))
        screen = self.field.screen().availableGeometry()
        x = min(max(below.x(), screen.left()), screen.right() - self.width())
        y = below.y()
        if y + self.height() > screen.bottom():  # no room below: above it
            y = self.field.mapToGlobal(QPoint(0, 0)).y() - tokens.MENU_GAP - self.height()
        self.move(x, y)
        self.show()
        self.setFocus()

    def _show_month(self, day: QDate) -> None:
        self.grid.show_month(day)
        self.title.setText(f"{dates.MONTH_NAMES[day.month() - 1]} {day.year()}")

    def _months(self, n: int) -> None:
        g = self.grid
        g.cursor = g.cursor.addMonths(n)
        self._show_month(g.cursor)

    def _move(self, days: int) -> None:
        g = self.grid
        to = g.cursor.addDays(days)
        if to < g.earliest:
            return
        g.cursor = to
        if to.month() != g.month.month() or to.year() != g.month.year():
            self._show_month(to)
        g.update()
        self.setAccessibleDescription(dates.fmt(_pydate(to)))

    def _choose(self, d: QDate) -> None:
        self.chosen.emit(d)
        self.close()

    def keyPressEvent(self, e):
        k, g = e.key(), self.grid
        steps = {Qt.Key.Key_Left: -1, Qt.Key.Key_Right: 1, Qt.Key.Key_Up: -7, Qt.Key.Key_Down: 7}
        if k in steps:
            self._move(steps[k])
        elif k in (Qt.Key.Key_PageUp, Qt.Key.Key_PageDown):
            self._months(-1 if k == Qt.Key.Key_PageUp else 1)
        elif k in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            if g.cursor >= g.earliest:
                self._choose(g.cursor)
        elif k == Qt.Key.Key_Escape:
            self.close()
        elif e.text().strip():  # typing: the month goes and the field takes it, from scratch
            field = self.field
            self.close()
            field.setFocus()
            field.selectAll()
            QApplication.sendEvent(field, QKeyEvent(e.type(), e.key(), e.modifiers(), e.text()))
        else:
            super().keyPressEvent(e)


class DateField(QLineEdit):
    """Every date: "Sat, Oct 10, 2026", or shorter ("Oct 10, 2026", "10/10/26") when its box is narrow, never cut
    off. Typed or picked from the month."""

    dateChanged = Signal(QDate)
    WIDEST = QDate(2026, 9, 30)  # "Wed, Sep 30, 2026": as wide as dates get, so the format holds as dates change

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        from PySide6.QtCore import QLocale

        self.setProperty("date", True)
        self.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        self._date = QDate.currentDate()
        self._min = EARLIEST
        self._fmt = DATE_FORMATS[0]
        self._pop: MonthPopover | None = None
        self.glyph = self.addAction(theme.icon("calendar", theme.ACCENT), QLineEdit.ActionPosition.TrailingPosition)
        self.glyph.setToolTip("Choose a Date (↓)")
        self.glyph.triggered.connect(lambda: QTimer.singleShot(0, self, self.open_month))
        self.textEdited.connect(self._typed)
        self.editingFinished.connect(self._show)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._show()

    # QDateEdit's calls
    def date(self) -> QDate:
        return QDate(self._date)

    def setDate(self, d: QDate) -> None:
        d = max(d, self._min)
        changed = d != self._date
        self._date = QDate(d)
        self._show()
        if changed:
            self.dateChanged.emit(QDate(d))

    def minimumDate(self) -> QDate:
        return QDate(self._min)

    def setMinimumDate(self, d: QDate) -> None:
        self._min = QDate(d)
        if self._date < d:
            self.setDate(d)

    # typing
    def _typed(self, text: str) -> None:
        """A date counts as soon as it reads as one (and isn't before the earliest allowed)."""
        got = dates.typed(text, _pydate(self._date))
        if got is None:
            return
        q = _qdate(got)
        if q >= self._min and q != self._date:
            self._date = q
            self.dateChanged.emit(QDate(q))

    def _show(self) -> None:
        """The date in words, as long as its box allows."""
        self.setText(self.locale().toString(self._date, self._fmt))
        self.setCursorPosition(0)

    # the month
    def open_month(self) -> None:
        if not self.isEnabled() or (self._pop is not None and self._pop.isVisible()):
            return
        self._pop = MonthPopover(self)
        self._pop.chosen.connect(self._picked)
        self._pop.destroyed.connect(lambda _o=None: setattr(self, "_pop", None))
        self._pop.open_at(self._date, self._min)

    def _picked(self, d: QDate) -> None:
        self.setDate(d)
        self.setFocus()

    def mousePressEvent(self, e):
        self._typing = self.hasFocus()  # a click in a field you're typing in places the cursor
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        super().mouseReleaseEvent(e)
        if e.button() == Qt.MouseButton.LeftButton and not getattr(self, "_typing", False):
            QTimer.singleShot(0, self, self.open_month)  # the first click opens the month, once it's over

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Down and not e.modifiers():
            self.open_month()
            return
        super().keyPressEvent(e)

    def focusInEvent(self, e):
        super().focusInEvent(e)
        self.setCursor(Qt.CursorShape.IBeamCursor)

    def focusOutEvent(self, e):
        super().focusOutEvent(e)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    # never cut off
    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.fit()

    def showEvent(self, e):
        super().showEvent(e)
        self.fit()

    def changeEvent(self, e):  # the stylesheet's font arrives after the first resize
        super().changeEvent(e)
        if e.type() in (QEvent.Type.FontChange, QEvent.Type.StyleChange):
            self.fit()

    def fit(self) -> None:
        room = self.width() - tokens.DATE_GLYPH_ROOM - tokens.SPACE_3
        fm = self.fontMetrics()
        fits = [f for f in DATE_FORMATS if fm.horizontalAdvance(self.locale().toString(self.WIDEST, f)) <= room]
        fmt = fits[0] if fits else DATE_FORMATS[-1]
        if fmt != self._fmt:
            self._fmt = fmt
            if not self.hasFocus():
                self._show()
