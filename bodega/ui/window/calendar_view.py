"""The rentals calendar, two ways:

Month     a month as a wall calendar: each rental a bar across the days it's out (several stack, "+2 more"
          when a day is full), colored by where it stands (quote, booked, out, late)
Timeline  weeks across, one row per rental: the way to see what overlaps

‹ Today › move through months (or a screenful of weeks on the timeline). A rental whose lines have their
own dates shows one bar per stretch. Click a bar to open the rental.
"""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QPainter, QPen
from PySide6.QtWidgets import QLabel, QPushButton, QStackedWidget, QToolButton, QToolTip, QWidget

from bodega.core import dates, pricing
from bodega.core.model import Rental
from bodega.core.store import Library
from bodega.ui.style import theme, tokens

NAME_W = tokens.CAL_NAME_W
HEAD_H = tokens.CAL_HEAD_H
BAR_TONES = {  # fill, edge, text: token names, read when drawing (light and dark differ)
    "quote": ("CARD_HOVER", "BORDER_STRONG", "MUTED"),
    "booked": ("ACCENT_TINT", "ACCENT_EDGE", "TEXT"),
    "out": ("WARN_TINT", "WARN", "TEXT"),
    "late": ("BAD", "BAD", "ON_ACCENT"),
    "returned": ("CARD", "BORDER", "FAINT"),
}


def week_start(d: date) -> date:
    return dates.plus(d, -((d.weekday() + 1) % 7))


def merge(spans: list[tuple[date, date]]) -> list[tuple[date, date]]:
    """Overlapping or touching stretches drawn as one bar."""
    out: list[tuple[date, date]] = []
    for a, z in sorted(spans):
        if out and a <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], z))
        else:
            out.append((a, z))
    return out


class RentalCalendar(QWidget):
    picked = Signal(str)
    span_changed = Signal()  # it shows more or fewer weeks (the window was resized)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.start = week_start(dates.today())
        self.days = tokens.CAL_WEEKS_AHEAD * 7
        self.rows: list[tuple[Rental, list[tuple[date, date]]]] = []
        self._bars: list[tuple[QRectF, Rental, date, date]] = []
        self.lib: Library | None = None

    def resizeEvent(self, e):
        """As many whole weeks as fit, so every day shown is a day you can read."""
        super().resizeEvent(e)
        fit = int((self.width() - NAME_W) // (tokens.DAY_W_MIN * 7))
        days = max(2, min(tokens.CAL_WEEKS_AHEAD, fit)) * 7
        if days != self.days:
            self.days = days
            self.fill(self.lib)
            self.span_changed.emit()

    def fill(self, lib: Library | None) -> None:
        self.lib = lib
        end = dates.plus(self.start, self.days - 1)
        self.rows = rental_spans(lib, self.start, end) if lib is not None else []
        rows = self.rows
        self.setMinimumHeight(HEAD_H + max(1, len(rows)) * tokens.CAL_ROW_H + tokens.SPACE_4)
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(NAME_W + self.days * tokens.DAY_W, HEAD_H + len(self.rows) * tokens.CAL_ROW_H)

    def _day_w(self) -> float:
        return max(float(tokens.DAY_W_MIN), (self.width() - NAME_W) / self.days)

    def _x(self, d: date) -> float:
        return NAME_W + (d - self.start).days * self._day_w()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        f = p.font()
        f.setPixelSize(tokens.TEXT_SM)
        p.setFont(f)
        dw = self._day_w()
        today = dates.today()
        # weekends and today, behind everything
        for n in range(self.days):
            d = dates.plus(self.start, n)
            x = NAME_W + n * dw
            if d.weekday() >= 5:
                p.fillRect(QRectF(x, HEAD_H, dw, self.height() - HEAD_H), theme.qcolor(tokens.PANEL))
            if d == today:
                p.fillRect(QRectF(x, 0, dw, self.height()), theme.qcolor(tokens.ACCENT_TINT))
        # the header: months and day numbers
        p.setPen(theme.qcolor(tokens.FAINT))
        for n in range(self.days):
            d = dates.plus(self.start, n)
            x = NAME_W + n * dw
            if n == 0 or d.day == 1:
                p.setPen(theme.qcolor(tokens.MUTED))
                p.drawText(
                    QRectF(x + tokens.SPACE_1 / 2, tokens.SPACE_1, dw * 6, HEAD_H / 2 - tokens.SPACE_1),
                    int(Qt.AlignmentFlag.AlignLeft),
                    dates.MONTHS[d.month - 1],
                )
            p.setPen(theme.qcolor(tokens.TEXT if d == today else tokens.FAINT))
            p.drawText(
                QRectF(x, HEAD_H / 2, dw, HEAD_H / 2 - tokens.SPACE_1),
                int(Qt.AlignmentFlag.AlignCenter),
                str(d.day),
            )
        p.setPen(QPen(theme.qcolor(tokens.BORDER), 1))
        p.drawLine(0, HEAD_H, self.width(), HEAD_H)
        # one row per rental
        self._bars = []
        for i, (r, spans) in enumerate(self.rows):
            y = HEAD_H + i * tokens.CAL_ROW_H
            p.setPen(theme.qcolor(tokens.TEXT))
            who = r.client.company or r.client.name or r.project or "No renter yet"
            p.drawText(QRectF(tokens.SPACE_3, y, NAME_W - tokens.SPACE_4, tokens.CAL_ROW_H / 2 + 4),
                       int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom), who)  # fmt: skip
            p.setPen(theme.qcolor(tokens.FAINT))
            p.drawText(QRectF(tokens.SPACE_3, y + tokens.CAL_ROW_H / 2 + 2, NAME_W - tokens.SPACE_4, tokens.CAL_ROW_H / 2),
                       int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop), r.number)  # fmt: skip
            tone = "late" if pricing.late(r) else r.status
            fill, edge, ink = (getattr(tokens, k) for k in BAR_TONES.get(tone, BAR_TONES["quote"]))
            for a, z in spans:
                x1 = max(float(NAME_W), self._x(a))
                x2 = min(float(self.width()), self._x(max(z, dates.plus(a, 1))))
                inset = tokens.CAL_BAR_INSET
                rect = QRectF(
                    x1 + 1, y + inset, max(float(tokens.SPACE_2), x2 - x1 - 2), tokens.CAL_ROW_H - 2 * inset
                )
                p.setBrush(theme.qcolor(fill))
                p.setPen(QPen(theme.qcolor(edge), 1))
                p.drawRoundedRect(rect, tokens.RADIUS_SM, tokens.RADIUS_SM)
                p.setPen(theme.qcolor(ink))
                p.drawText(rect.adjusted(tokens.SPACE_2, 0, -tokens.SPACE_1, 0),
                           int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
                           p.fontMetrics().elidedText(dates.span(a, z), Qt.TextElideMode.ElideRight, int(rect.width() - tokens.SPACE_3)))  # fmt: skip
                self._bars.append((rect, r, a, z))
            p.setPen(QPen(theme.qcolor(tokens.BORDER), 1))
            p.drawLine(0, int(y + tokens.CAL_ROW_H), self.width(), int(y + tokens.CAL_ROW_H))
        if not self.rows:
            p.setPen(theme.qcolor(tokens.FAINT))
            p.drawText(QRectF(0, HEAD_H, self.width(), tokens.CAL_ROW_H * 2), int(Qt.AlignmentFlag.AlignCenter),
                       "Nothing booked in these weeks.")  # fmt: skip
        p.end()

    def _bar_at(self, pos):
        for rect, r, a, z in self._bars:
            if rect.contains(pos):
                return r, a, z
        return None

    def mouseMoveEvent(self, e):
        hit = self._bar_at(e.position())
        self.setCursor(Qt.CursorShape.PointingHandCursor if hit else Qt.CursorShape.ArrowCursor)
        if hit:
            r, a, z = hit
            who = r.client.company or r.client.name or ""
            QToolTip.showText(e.globalPosition().toPoint(), f"{r.number} {who}\n{dates.span(a, z)}", self)
        else:
            QToolTip.hideText()

    def mousePressEvent(self, e):
        hit = self._bar_at(e.position())
        if hit and e.button() == Qt.MouseButton.LeftButton:
            self.picked.emit(hit[0].id)


def rental_spans(lib: Library, start: date, end: date) -> list[tuple[Rental, list[tuple[date, date]]]]:
    """Each rental (not cancelled) with its stretches of dates that touch start..end."""
    rows = []
    for r in lib.rentals.values():
        if r.status == "cancelled":
            continue
        spans = []
        for a, z in pricing.periods(r):
            if a is None:
                continue
            z = z or a
            if z >= start and a <= end:
                spans.append((a, z))
        if spans:
            rows.append((r, merge(spans)))
    rows.sort(key=lambda x: (min(a for a, _z in x[1]), x[0].number))
    return rows


def tone_of(r: Rental) -> str:
    return "late" if pricing.late(r) else r.status


class MonthCalendar(QWidget):
    """A month as a wall calendar, rentals as bars across their days."""

    picked = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setMouseTracking(True)
        t = dates.today()
        self.year, self.month = t.year, t.month
        self.rows: list[tuple[Rental, list[tuple[date, date]]]] = []
        self._bars: list[tuple[QRectF, Rental, date, date]] = []
        self.lib: Library | None = None
        self.setMinimumHeight(tokens.MONTH_HEAD_H + 5 * tokens.MONTH_CELL_MIN_H)

    # ------------------------------------------------------------------ the month
    def first_day(self) -> date:
        return week_start(date(self.year, self.month, 1))

    def weeks(self) -> int:
        last = dates.plus(date(self.year + self.month // 12, self.month % 12 + 1, 1), -1)
        return ((last - self.first_day()).days // 7) + 1

    def step(self, n: int) -> None:
        m = self.year * 12 + (self.month - 1) + n
        self.year, self.month = m // 12, m % 12 + 1
        self.fill(self.lib)

    def today(self) -> None:
        t = dates.today()
        self.year, self.month = t.year, t.month
        self.fill(self.lib)

    def title(self) -> str:
        return f"{dates.MONTH_NAMES[self.month - 1]} {self.year}"

    def fill(self, lib: Library | None) -> None:
        self.lib = lib
        start = self.first_day()
        end = dates.plus(start, self.weeks() * 7 - 1)
        self.rows = rental_spans(lib, start, end) if lib is not None else []
        self.update()

    # ------------------------------------------------------------------ drawing
    def _cell(self) -> tuple[float, float]:
        return self.width() / 7, (self.height() - tokens.MONTH_HEAD_H) / self.weeks()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setFont(theme.font(tokens.TEXT_SM, tokens.WEIGHT_MEDIUM))
        cw, ch = self._cell()
        head = tokens.MONTH_HEAD_H
        start, today = self.first_day(), dates.today()
        weeks = self.weeks()
        # weekday names
        p.setPen(theme.qcolor(tokens.FAINT))
        for c, name in enumerate(dates.CAL_WEEKDAYS):
            p.drawText(QRectF(c * cw, 0, cw, head), int(Qt.AlignmentFlag.AlignCenter), name)
        # the squares
        grid = QPen(theme.qcolor(tokens.BORDER), 1)
        for w in range(weeks):
            for c in range(7):
                d = dates.plus(start, w * 7 + c)
                cell = QRectF(c * cw, head + w * ch, cw, ch)
                if c in (0, 6):  # the weekend, a touch quieter
                    p.fillRect(cell, theme.qcolor(tokens.BLOCK))
                p.setPen(grid)
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawRect(cell)
                num = QRectF(
                    cell.left() + tokens.SPACE_1,
                    cell.top() + tokens.SPACE_1,
                    tokens.MONTH_DAY_H - 4,
                    tokens.MONTH_DAY_H - 4,
                )
                if d == today:
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(theme.qcolor(tokens.ACCENT))
                    p.drawEllipse(num)
                    p.setPen(theme.qcolor(tokens.ON_ACCENT))
                else:
                    p.setPen(theme.qcolor(tokens.TEXT if d.month == self.month else tokens.FAINT))
                p.drawText(num, int(Qt.AlignmentFlag.AlignCenter), str(d.day))
        # the rentals, week by week, each in the first lane free across its days
        self._bars = []
        lanes_fit = max(
            0, int((ch - tokens.MONTH_DAY_H - tokens.SPACE_1) // (tokens.MONTH_BAR_H + tokens.MONTH_BAR_GAP))
        )
        for w in range(weeks):
            w0, w1 = dates.plus(start, w * 7), dates.plus(start, w * 7 + 6)
            pieces = []
            for r, spans in self.rows:
                for a, z in spans:
                    if z < w0 or a > w1:
                        continue
                    pieces.append((max(a, w0), min(z, w1), r, a, z))
            pieces.sort(key=lambda x: (x[0], -(x[1] - x[0]).days))
            lanes: list[date] = []  # the last day taken in each lane
            hidden = [0] * 7
            for a, z, r, ra, rz in pieces:
                lane = next((i for i, last in enumerate(lanes) if last < a), len(lanes))
                if lane == len(lanes):
                    lanes.append(z)
                else:
                    lanes[lane] = z
                c0, c1 = (a - w0).days, (z - w0).days
                if lane >= lanes_fit:
                    for c in range(c0, c1 + 1):
                        hidden[c] += 1
                    continue
                y = head + w * ch + tokens.MONTH_DAY_H + lane * (tokens.MONTH_BAR_H + tokens.MONTH_BAR_GAP)
                left = c0 * cw + (tokens.SPACE_1 if a == ra else 0)
                right = (c1 + 1) * cw - (tokens.SPACE_1 if z == rz else 0)
                rect = QRectF(left, y, right - left, tokens.MONTH_BAR_H)
                fill, edge, ink = (getattr(tokens, k) for k in BAR_TONES.get(tone_of(r), BAR_TONES["quote"]))
                p.setBrush(theme.qcolor(fill))
                p.setPen(QPen(theme.qcolor(edge), 1))
                p.drawRoundedRect(rect, tokens.RADIUS_SM, tokens.RADIUS_SM)
                p.setPen(theme.qcolor(ink))
                who = r.client.company or r.client.name or r.project or r.number
                p.drawText(
                    rect.adjusted(tokens.SPACE_2, 0, -tokens.SPACE_1, 0),
                    int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
                    p.fontMetrics().elidedText(
                        who, Qt.TextElideMode.ElideRight, int(rect.width() - tokens.SPACE_3)
                    ),
                )
                self._bars.append((rect, r, ra, rz))
            p.setPen(theme.qcolor(tokens.MUTED))
            for c, n in enumerate(hidden):
                if n:
                    cell = QRectF(
                        c * cw,
                        head + (w + 1) * ch - tokens.MONTH_BAR_H - tokens.SPACE_1,
                        cw,
                        tokens.MONTH_BAR_H,
                    )
                    p.drawText(
                        cell.adjusted(tokens.SPACE_2, 0, 0, 0),
                        int(Qt.AlignmentFlag.AlignVCenter),
                        f"+{n} more",
                    )
        p.end()

    def _bar_at(self, pos):
        for rect, r, a, z in self._bars:
            if rect.contains(pos):
                return r, a, z
        return None

    def mouseMoveEvent(self, e):
        hit = self._bar_at(e.position())
        self.setCursor(Qt.CursorShape.PointingHandCursor if hit else Qt.CursorShape.ArrowCursor)
        if hit:
            r, a, z = hit
            who = r.client.company or r.client.name or ""
            QToolTip.showText(
                e.globalPosition().toPoint(), theme.plain_tip(f"{r.number} {who}\n{dates.span(a, z)}"), self
            )
        else:
            QToolTip.hideText()

    def mousePressEvent(self, e):
        hit = self._bar_at(e.position())
        if hit and e.button() == Qt.MouseButton.LeftButton:
            self.picked.emit(hit[0].id)


class CalendarPage(QWidget):
    """The Calendar place: Month or Timeline, with ‹ Today › to move through time."""

    picked = Signal(str)
    mode_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        from bodega.ui.components.widgets import FitScroll, Segmented, hbox, vbox

        super().__init__(parent)
        lay = vbox(self, (tokens.SPACE_4, 0, tokens.SPACE_4, tokens.SPACE_3), tokens.SPACE_3)
        bar = hbox(spacing=tokens.SPACE_2)
        self.title = QLabel()
        self.title.setObjectName("CalTitle")
        bar.addWidget(self.title)
        bar.addStretch(1)
        self.prev = QToolButton()
        self.prev.setObjectName("Circle")
        self.prev.setIcon(theme.icon("chevron-left", theme.MUTED))
        self.prev.setToolTip("Earlier")
        self.prev.clicked.connect(lambda: self._step(-1))
        self.today_btn = QPushButton("Today")
        self.today_btn.clicked.connect(self._today)
        self.next = QToolButton()
        self.next.setObjectName("Circle")
        self.next.setIcon(theme.icon("chevron-right", theme.MUTED))
        self.next.setToolTip("Later")
        self.next.clicked.connect(lambda: self._step(1))
        self.mode = Segmented([("month", "Month"), ("timeline", "Timeline")], compact=True)
        self.mode.changed.connect(self.set_mode)
        for w in (self.prev, self.today_btn, self.next):
            bar.addWidget(w)
        bar.addSpacing(tokens.SPACE_2)
        bar.addWidget(self.mode)
        lay.addLayout(bar)
        self.stack = QStackedWidget()
        self.month = MonthCalendar()
        self.timeline = RentalCalendar()
        scroll = FitScroll()
        scroll.setWidget(self.timeline)
        self.stack.addWidget(self.month)
        self.stack.addWidget(scroll)
        lay.addWidget(self.stack, 1)
        self.month.picked.connect(self.picked.emit)
        self.timeline.picked.connect(self.picked.emit)
        self.timeline.span_changed.connect(self._show_title)
        self.lib: Library | None = None
        self.set_mode("month", quiet=True)

    def set_mode(self, mode: str, quiet: bool = False) -> None:
        mode = mode if mode in ("month", "timeline") else "month"
        self.mode.set_value(mode)
        self.stack.setCurrentIndex(0 if mode == "month" else 1)
        self._show_title()
        if not quiet:
            self.mode_changed.emit(mode)

    def is_month(self) -> bool:
        return self.stack.currentIndex() == 0

    def fill(self, lib: Library) -> None:
        self.lib = lib
        self.month.fill(lib)
        self.timeline.fill(lib)
        self._show_title()

    def _step(self, n: int) -> None:
        if self.is_month():
            self.month.step(n)
        else:
            self.timeline.start = dates.plus(self.timeline.start, n * self.timeline.days)
            self.timeline.fill(self.lib)
        self._show_title()

    def _today(self) -> None:
        self.month.today()
        self.timeline.start = week_start(dates.today())
        self.timeline.fill(self.lib)
        self._show_title()

    def _show_title(self) -> None:
        if self.is_month():
            self.title.setText(self.month.title())
        else:
            a = self.timeline.start
            self.title.setText(dates.span(a, dates.plus(a, self.timeline.days - 1)))
