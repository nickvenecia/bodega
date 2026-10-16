"""The gear inspector: the piece you picked, changed in place.

Always there: name, company and series, department and group, how many, status, and value and rate (with the
tax math a gear sheet does). Added only when a piece needs them (+ Add): Link (with Check Price), Serial
Numbers, Works With and Notes; a stand doesn't need serial numbers. Duplicate and Delete live under ⋯, and
Rent This is the button along the bottom.

Works With: gear that goes with a piece (the FX6's cage, the 80c's fresnel) isn't listed in the table; it's
here, each one click away, and goes wherever its piece goes, onto kits, rentals and agreements.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPoint, QPointF, QRectF, QSize, QStringListModel, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QPainter, QPainterPath
from PySide6.QtWidgets import (
    QApplication,
    QCompleter,
    QFileDialog,
    QFrame,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QToolButton,
    QWidget,
)

from bodega.core import dates, earnings, errors, figures, maintenance, money, prices, pricing, web
from bodega.core.log import get_logger
from bodega.core.model import ITEM_STATUSES, Item, LogEntry
from bodega.core.store import Library
from bodega.ui.components import photos
from bodega.ui.components.figures import FigureStrip
from bodega.ui.components.widgets import (
    Card,
    ElidedLabel,
    FlowLayout,
    MoneyField,
    Section,
    TextBox,
    TitleEdit,
    ToggleRow,
    add_chip,
    by_keyboard,
    combo,
    date_field,
    from_qdate,
    hbox,
    hint,
    icon_button,
    picker,
    qty_field,
    repolish,
    rows_done,
    set_combo,
    status_line,
    suggestions,
    to_qdate,
    vbox,
)
from bodega.ui.components.worker import Background, Worker
from bodega.ui.panels.base import DetailsBase
from bodega.ui.style import theme, tokens

log = get_logger(__name__)

PASTE_INSTEAD = "In your browser, right-click the photo, choose Copy Image, then paste it here."
STATUS_LABELS = {"ready": "Ready", "repair": "In Repair", "retired": "Retired"}
NEW = "\x00new"  # the "New Department…" / "New Group…" row
EXTRAS = [
    ("works", "Works With"),
    ("link", "Link"),
    ("serials", "Serial Numbers"),
    ("notes", "Notes"),
    ("care", "Maintenance"),
]
LOG_KINDS = [
    ("service", "Service", "Cleaning, a check-up: resets the reminder"),
    ("repair", "Repair", ""),
    ("note", "Note", ""),
]


class Block(Card):
    """A titled part of the gear inspector. Added parts (Link, Serial Numbers…) have an × to take them off
    again while they're empty."""

    removed = Signal(str)

    def __init__(self, key: str, title: str, removable: bool, parent: QWidget | None = None):
        super().__init__(title, parent)
        self.key = key
        self.x = icon_button("x", f"Take {title} off this piece")
        self.x.clicked.connect(lambda: self.removed.emit(self.key))
        self.x.setVisible(removable)
        self.head.addWidget(self.x)
        self.body = self.lay


class PhotoBox(QFrame):
    """The piece's photo in its head, beside its name (the standard's 4.5): the whole picture, rounded, on a soft
    tint. It is itself the control that changes it: press it for Replace, From Link, Paste, Remove."""

    pressed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("PhotoBox")
        self.setFixedSize(tokens.PHOTO_HEAD, tokens.PHOTO_HEAD)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Change the Photo")
        self.setAccessibleName("Photo")
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.name = ""
        self.menu: QMenu | None = None

    def show_photo(self, name: str) -> None:
        self.name = name
        self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self.rect().contains(e.position().toPoint()):
            QTimer.singleShot(0, self, self.pressed.emit)  # once the click is over
        super().mouseReleaseEvent(e)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.pressed.emit()
            return
        super().keyPressEvent(e)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect())
        clip = QPainterPath()
        clip.addRoundedRect(r, tokens.RADIUS_LG, tokens.RADIUS_LG)
        p.fillPath(clip, theme.qcolor(tokens.FILL))
        pix = photos.fitted(self.name, self.width(), self.height(), self.devicePixelRatioF())
        if pix is not None and not pix.isNull():
            w, h = pix.width() / pix.devicePixelRatio(), pix.height() / pix.devicePixelRatio()
            p.setClipPath(clip)
            p.drawPixmap(QPointF((r.width() - w) / 2, (r.height() - h) / 2), pix)
        p.end()


class ItemPanel(DetailsBase):
    TITLE = "Gear"
    KEY = "gear"
    GROUPS: dict[str, tuple[str, bool]] = {}

    changed = Signal(object)  # Item: save and redraw
    structure_changed = Signal()  # what goes with it, or its category, changed: the list needs rebuilding
    open_item = Signal(str)
    attach_wanted = Signal(str)  # pick gear that goes with this piece
    detach_wanted = Signal(str)  # gear that went with a piece becomes its own
    delete_wanted = Signal(str)
    duplicate_wanted = Signal(str)
    rent_wanted = Signal(str)
    open_rental = Signal(str)
    toast_wanted = Signal(str, str)  # a short message for the window to show, and its tone (MainWindow.toast)
    ai_wanted = Signal(str)  # Update with AI (this piece)

    def __init__(self, lib: Library, parent: QWidget | None = None):
        super().__init__(parent)
        self.lib = lib
        self.it: Item | None = None
        self.serial_fields: list[QLineEdit] = []
        self.blocks: dict[str, Block] = {}
        lay = self.form_lay
        lay.setSpacing(tokens.SPACE_3)

        self.menu_action("copy", "Duplicate", lambda: self.it and self.duplicate_wanted.emit(self.it.id))
        self.menu_action("assistant", "Update with AI…", lambda: self.it and self.ai_wanted.emit(self.it.id))
        self.menu_action("", "-", None)
        self.menu_action("trash", "Delete", lambda: self.it and self.delete_wanted.emit(self.it.id))
        self.rent = self.footer_button("Rent This", "receipt")
        self.rent.clicked.connect(lambda: self.it and self.rent_wanted.emit(self.it.id))

        # the head (the standard's 4.5): the photo beside the name, a quiet status line, a line of detail
        self.where = QPushButton()  # "● Out · Northwind Media · back Oct 25": click it to open that rental
        self.where.setObjectName("StatusLine")
        self.where.setIconSize(QSize(tokens.STATUS_DOT, tokens.STATUS_DOT))  # the list's own dot
        self.where.clicked.connect(lambda: self._where_id and self.open_rental.emit(self._where_id))
        self._where_id = ""
        self.detail = hint("")  # "Sony · Body"

        # its photo (once it has one; until then "+ Photo" sits with the other parts you can add)
        self.photo = PhotoBox()
        pm = QMenu(self.photo)
        pm.addAction(theme.menu_icon("image"), "Replace…", self.choose_photo)
        self.act_photo_link = pm.addAction(theme.menu_icon("link"), "From Link", self.photo_from_link)
        self.act_photo_paste = pm.addAction(theme.menu_icon("clipboard"), "Paste", self.paste_photo)
        pm.aboutToShow.connect(self._paste_state)
        pm.addSeparator()
        pm.addAction(theme.menu_icon("trash"), "Remove Photo", self.remove_photo)
        self.photo.menu = pm
        self.photo.pressed.connect(
            lambda: pm.popup(self.photo.mapToGlobal(QPoint(0, self.photo.height() + tokens.MENU_GAP)))
        )
        self.photo.hide()
        self._photo_job: Worker | None = None
        self._all_earned: dict | None = None  # what every piece has earned, from the list (None: this one's, here)
        self._one_earned: tuple[str, object] | None = None  # (piece, what it earned), until the next refresh
        self.setAcceptDrops(True)  # drop a picture anywhere on the panel (a file, or one out of a browser)

        # what it is
        self.name = TitleEdit()
        self.name.setPlaceholderText("Name")
        head = QWidget()
        outer = vbox(head, (0, 0, 0, tokens.HEAD_BELOW - lay.spacing()), tokens.STRIP_ABOVE)
        hl = hbox(spacing=tokens.SPACE_3)
        hl.addWidget(self.photo, 0, Qt.AlignmentFlag.AlignTop)
        col = vbox(spacing=tokens.SPACE_0_5)
        for w in (self.name, self.where, self.detail):
            col.addWidget(w)
        col.addStretch(1)
        hl.addLayout(col, 1)
        outer.addLayout(hl)
        self.strip = FigureStrip()  # its day rate, what it has earned, how much of its cost that is
        outer.addWidget(self.strip)
        lay.addWidget(head)
        b = self._block("details", "Details", removable=False)
        row = hbox(spacing=tokens.SPACE_2)
        sec = Section("Company")
        self.brand = QLineEdit()
        self.brand_list = QStringListModel(self)
        self.brand.setCompleter(self._completer(self.brand_list))
        sec.add(self.brand)
        row.addWidget(sec, 1)
        sec = Section("Series")
        self.series = QLineEdit()
        self.series_list = QStringListModel(self)
        self.series.setCompleter(self._completer(self.series_list))
        sec.add(self.series)
        row.addWidget(sec, 1)
        b.add(row)
        sec = Section("Group")
        self.group = picker("None", "Group")
        sec.add(self.group)
        b.add(sec)
        row = hbox(spacing=tokens.SPACE_2)
        sec = Section("How Many")
        self.qty = qty_field()
        sec.add(self.qty)
        row.addWidget(sec)
        sec = Section("Status")
        self.status = combo([(k, STATUS_LABELS[k], "") for k in ITEM_STATUSES], "ready")
        self.status.setItemData(1, "Not available to rent until it's back", Qt.ItemDataRole.ToolTipRole)
        self.status.setItemData(2, "Sold, lost or broken for good: left off the inventory", Qt.ItemDataRole.ToolTipRole)
        sec.add(self.status)
        row.addWidget(sec, 1)
        b.add(row)

        # value and rate
        b = self._block("value", "Value & Rate", removable=False)
        row = hbox(spacing=tokens.SPACE_2)
        sec = Section("Paid Each")
        self.value = MoneyField()
        self.value.setPlaceholderText("$0.00")
        sec.add(self.value)
        row.addWidget(sec, 1)
        sec = Section("Day Rate Each")
        self.rate = MoneyField()
        self.rate.setToolTip("Blank: worked out from the value, at your profile's rate")
        sec.add(self.rate)
        row.addWidget(sec, 1)
        b.add(row)
        self.sums = QWidget()
        sl = vbox(self.sums, 0, tokens.SPACE_1)
        self.sum_rows: dict[str, tuple[QLabel, QLabel]] = {}
        for key in ("tax", "each", "total"):  # (its day rate and earnings are in the head's strip)
            r = QWidget()
            rl = hbox(r, 0, tokens.SPACE_2)
            k = QLabel()
            k.setObjectName("SumLabel")
            v = QLabel()
            v.setObjectName("SumValue")
            rl.addWidget(k, 1)
            rl.addWidget(v)
            sl.addWidget(r)
            self.sum_rows[key] = (k, v)
        b.add(self.sums)
        self.rentable = ToggleRow("For Rent", True)
        self.rentable.setToolTip("Off for gear you keep for yourself: it's left off rentals and the rate card")
        b.add(self.rentable)

        # the parts you add
        b = self._block("works", "Works With")
        self.kids_box = QWidget()
        self.kids_lay = vbox(self.kids_box, 0, 0)  # rows, with hairlines between
        b.add(self.kids_box)
        arow = hbox()
        self.attach = add_chip("Add Gear…")
        self.attach.setToolTip("Gear that goes with this piece: a cage, a handle, a fresnel")
        arow.addWidget(self.attach)
        arow.addStretch(1)
        b.add(arow)

        b = self._block("link", "Link")
        lrow = hbox(spacing=tokens.SPACE_1)
        self.link = QLineEdit()
        self.link.setPlaceholderText("https://")
        self.check_price = icon_button("retry", "Check Price: read the price on this page")
        self.open_link = icon_button("reveal", "Open in your browser")
        lrow.addWidget(self.link, 1)
        lrow.addWidget(self.check_price)
        lrow.addWidget(self.open_link)
        b.add(lrow)
        # under the link only while there's something to say: Checking…, then the price found, or what went wrong
        # (which stays beside the link until you close it, check again or open another piece: the standard's 5.5)
        self.price_row = QWidget()
        prow = hbox(self.price_row, spacing=tokens.SPACE_2)
        self.price_found = status_line(hinted=False)
        self.price_found.setObjectName("Meta")
        self.price_found.setWordWrap(True)
        self.use_price = QPushButton("Use It")
        self.use_price.setObjectName("LinkBtn")
        self.use_price.setCursor(Qt.CursorShape.PointingHandCursor)
        self.use_price.setToolTip("Put this price in Paid Each")
        self.use_price.hide()
        self.price_close = icon_button("x", "Close")
        self.price_close.clicked.connect(lambda: self._show_price())
        self.price_close.hide()
        prow.addWidget(self.price_found, 1)
        prow.addWidget(self.use_price)
        prow.addWidget(self.price_close)
        self.price_row.setMinimumHeight(tokens.CONTROL_H)  # as tall with Use It as without: no jump
        self.price_row.hide()
        b.add(self.price_row)
        self._found_price = ""
        self._price_thread: PriceCheck | None = None

        b = self._block("serials", "Serial Numbers")
        self.serial_box = QWidget()
        self.serial_lay = vbox(self.serial_box, 0, tokens.SPACE_1)
        b.add(self.serial_box)

        b = self._block("notes", "Notes")
        self.notes = TextBox("Firmware, what's in the case, quirks…", tokens.TEXT_BOX_TALL)
        b.add(self.notes)

        # maintenance: how often it's serviced, when it's next due, and its log
        b = self._block("care", "Maintenance")
        sec = Section("Service")
        self.every = combo([(str(d), label, "") for d, label in maintenance.EVERY], "0")
        self.every.currentIndexChanged.connect(lambda _i: self._every_picked())
        sec.add(self.every)
        b.add(sec)
        self.due = QLabel()
        self.due.setObjectName("Due")
        b.add(self.due)
        self.log_box = QWidget()
        self.log_lay = vbox(self.log_box, 0, tokens.SPACE_1)
        b.add(self.log_box)
        row = hbox(spacing=tokens.SPACE_2)
        self.log_kind = combo(LOG_KINDS, "service")
        self.log_date = date_field()
        row.addWidget(self.log_kind, 1)
        row.addWidget(self.log_date, 1)
        b.add(row)
        row = hbox(spacing=tokens.SPACE_2)
        self.log_text = QLineEdit()
        self.log_text.setPlaceholderText("What was done")
        self.log_text.returnPressed.connect(self._log_add)
        self.log_cost = MoneyField()
        self.log_cost.setPlaceholderText("Cost")
        self.log_cost.setFixedWidth(tokens.LOG_COST_W)
        self.log_add = QPushButton("Add")
        self.log_add.clicked.connect(self._log_add)
        row.addWidget(self.log_text, 1)
        row.addWidget(self.log_cost)
        row.addWidget(self.log_add)
        b.add(row)

        self.adders = QWidget()
        arow = FlowLayout(self.adders)
        self.add_buttons: dict[str, QPushButton] = {}
        self.add_photo = add_chip("Photo")
        am = QMenu(self.add_photo)
        am.addAction(theme.menu_icon("image"), "Choose File…", self.choose_photo)
        self.act_add_photo_link = am.addAction(theme.menu_icon("link"), "From Link", self.photo_from_link)
        self.act_add_photo_paste = am.addAction(theme.menu_icon("clipboard"), "Paste", self.paste_photo)
        am.aboutToShow.connect(self._paste_state)
        self.add_photo.setMenu(am)
        arow.addWidget(self.add_photo)
        for key, title in EXTRAS:
            btn = add_chip(title)
            btn.clicked.connect(lambda _c=False, k=key: self._add_part(k))
            arow.addWidget(btn)
            self.add_buttons[key] = btn
        lay.addWidget(self.adders)

        self._connect()
        self.form.hide()

    def _block(self, key: str, title: str, removable: bool = True) -> Block:
        b = Block(key, title, removable)
        b.removed.connect(self._remove_part)
        self.blocks[key] = b
        self.form_lay.addWidget(b)
        return b

    @staticmethod
    def _completer(model: QStringListModel) -> QCompleter:
        c = QCompleter()
        c.setModel(model)
        c.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        c.setFilterMode(Qt.MatchFlag.MatchContains)
        return suggestions(c)

    # Wiring
    def _connect(self) -> None:
        self.name.textEdited.connect(lambda t: self._set("name", t))
        self.brand.textEdited.connect(lambda t: self._set("brand", t.strip()))
        self.brand.editingFinished.connect(self._brand_done)
        self.series.textEdited.connect(lambda t: self._set("series", t.strip()))
        self.group.activated.connect(lambda _i: self._group_picked())
        self.qty.valueChanged.connect(self._qty_changed)
        self.status.currentIndexChanged.connect(lambda _i: self._set("status", self.status.currentData(), True))
        self.attach.clicked.connect(lambda: self.it and self.attach_wanted.emit(self.it.id))
        self.value.textEdited.connect(lambda t: self._set("value", t.replace("$", "").replace(",", "").strip()))
        self.rate.textEdited.connect(lambda t: self._set("day_rate", t.replace("$", "").replace(",", "").strip()))
        self.rentable.toggled.connect(lambda on: self._set("rentable", on, True))
        self.link.textEdited.connect(lambda t: (self._set("link", t.strip()), self._parts(), self._link_state()))
        self.link.textEdited.connect(lambda _t: self._price_thread is None and self._show_price())  # (it was another)
        self.open_link.clicked.connect(self._open_link)
        self.check_price.clicked.connect(self._check_price)
        self.use_price.clicked.connect(self._use_price)
        self.notes.edited.connect(lambda: (self._set("notes", self.notes.text()), self._parts()))

    def _set(self, key: str, value, structural: bool = False) -> None:
        if self._loading or self.it is None:
            return
        setattr(self.it, key, value)
        self._hints()
        self.changed.emit(self.it)
        if structural:
            self.structure_changed.emit()

    def _brand_done(self) -> None:
        if self.it is not None:
            self.series_list.setStringList(self.lib.series_of(self.it.brand))

    def _group_picked(self) -> None:
        """A group picked from the list (or a new one named)."""
        it = self.it
        if self._loading or it is None:
            return
        value = self.group.currentData()
        if value == NEW:
            from bodega.ui.dialogs.common import ask_name

            value = ask_name(self, "New Group", "Add", placeholder="Lights, Media, Pelican Cases…",
                             known=self.lib.groups())  # fmt: skip
            if value is None:
                self._fill_groups()
                return
        if value == it.group:
            return
        self.lib.put_in_group([it.id], value)
        self._fill_groups()
        self._hints()
        self.changed.emit(it)
        self.structure_changed.emit()

    def _qty_changed(self, n: int) -> None:
        if self._loading or self.it is None:
            return
        self.it.qty = n
        self._build_serials()
        self._hints()
        self.changed.emit(self.it)
        self.structure_changed.emit()

    # The parts you add
    def _has(self, key: str) -> bool:
        """Whether a part has anything in it."""
        it = self.it
        if it is None:
            return False
        return {
            "link": bool(it.link.strip()),
            "serials": bool(it.serial_list()),
            "works": bool(it.parent) or bool(pricing.children(self.lib, it.id)),
            "notes": bool(it.notes.strip()),
            "care": bool(it.log) or it.service_days > 0,
        }.get(key, False)

    def _parts(self) -> None:
        """Show the parts this piece has (or you added), and offer the rest under + Add."""
        it = self.it
        if it is None:
            return
        missing = 0
        for key, _title in EXTRAS:
            shown = self._has(key) or key in it.extras
            self.blocks[key].setVisible(shown)
            self.blocks[key].x.setVisible(shown and not self._has(key))
            self.add_buttons[key].setVisible(not shown)
            missing += not shown
        self.add_photo.setVisible(not it.photo)
        self.adders.setVisible(missing > 0 or not it.photo)

    def _add_part(self, key: str) -> None:
        it = self.it
        if it is None:
            return
        if key not in it.extras:
            it.extras.append(key)
        if key == "serials":
            self._build_serials()
        self._parts()
        focus = {
            "link": self.link,
            "notes": self.notes,
            "serials": self.serial_fields[0] if self.serial_fields else None,
        }
        w = focus.get(key)
        if w is not None:
            w.setFocus()
        if key == "works" and not self._has("works"):
            self.attach_wanted.emit(it.id)
        self.changed.emit(it)

    def _remove_part(self, key: str) -> None:
        it = self.it
        if it is None or self._has(key):
            return
        it.extras = [x for x in it.extras if x != key]
        self._build_serials()
        self._parts()
        self.changed.emit(it)

    # Link + price
    def _open_link(self) -> None:
        url = web.web_link(self.link.text())
        if url:  # only web pages open: never file://, smb:// or an app's own links
            QDesktopServices.openUrl(QUrl(url))
        elif self.link.text().strip():
            self.toast_wanted.emit("Only web links (https://…) open from here.", "problem")

    def _link_state(self) -> None:
        """Check Price works once there's a link, one check at a time."""
        has_link, free = bool(self.link.text().strip()), self._price_thread is None
        self.check_price.setEnabled(has_link and free)
        self.check_price.setToolTip(
            "Check Price: read the price on this page"
            if has_link and free
            else "Checking…"
            if has_link
            else "Add a link first"
        )

    def _show_price(self, text: str = "", use: bool = False, problem: bool = False) -> None:
        self.price_found.setText(text)
        self.price_found.setObjectName("Warn" if problem else "Meta")
        repolish(self.price_found)
        self.use_price.setVisible(use)
        self.price_close.setVisible(problem)
        self.price_row.setVisible(bool(text))

    def _check_price(self) -> None:
        if self.it is None or not self.it.link.strip() or self._price_thread is not None:
            return
        self._show_price(f"Checking {web.site_name(self.it.link) or 'the page'}…")
        t = PriceCheck(self.it.id, self.it.link, self)
        t.done.connect(self._price_done)
        t.finished.connect(self._price_checked)
        t.finished.connect(t.deleteLater)  # a finished check doesn't stay under the panel
        self._price_thread = t
        self._link_state()
        t.start()

    def _price_checked(self) -> None:
        self._price_thread = None
        self._link_state()

    def _price_done(self, item_id: str, price: str, store: str, error: str) -> None:
        if self.it is None or self.it.id != item_id:
            return
        if error or not price:
            self._show_price(error or "No price on that page.", problem=True)
            return
        b = self.b()
        cur = (b.currency if b else "$") or "$"
        self._found_price = price
        found = f"{store}: {money.fmt(money.parse(price), cur)}"
        if money.parse(price) == money.parse(self.it.value):
            self._show_price(found + " · same as yours")
        else:
            self._show_price(found, use=True)

    def _use_price(self) -> None:
        if self.it is None or not self._found_price:
            return
        self.value.set_value(self._found_price)
        self._set("value", self._found_price)
        self._show_price(self.price_found.text() + " · same as yours")

    # Maintenance
    def _show_care(self) -> None:
        it = self.it
        if it is None:
            return
        set_combo(self.every, str(it.service_days) if self.every.findData(str(it.service_days)) >= 0 else "0")
        d = maintenance.due(it)
        self.due.setText(maintenance.say(d) if d else "")
        self.due.setVisible(d is not None)
        self.due.setProperty("tone", {"overdue": "late", "soon": "out"}.get(d.state, "") if d else "")
        repolish(self.due)
        while self.log_lay.count():
            w = self.log_lay.takeAt(0).widget()
            if w is not None:
                w.deleteLater()
        cur = (self.b().currency or "$") if self.b() else "$"
        kinds = {k: label for k, label, _t in LOG_KINDS}
        for n in range(len(it.log) - 1, -1, -1):  # newest first
            e = it.log[n]
            parts = [
                dates.fmt(dates.parse(e.date)) if dates.parse(e.date) else "",
                kinds.get(e.kind, ""),
                e.text,
            ]
            if money.parse(e.cost):
                parts.append(money.fmt(money.parse(e.cost), cur))
            row = QWidget()
            rl = hbox(row, 0, tokens.SPACE_2)
            text = ElidedLabel(" · ".join(p for p in parts if p))
            rl.addWidget(text, 1)
            x = icon_button("x", "Remove this line")
            x.clicked.connect(lambda _c=False, i=n: self._log_remove(i))
            rl.addWidget(x)
            self.log_lay.addWidget(row)
        self.log_box.setVisible(bool(it.log))
        self.log_date.setDate(to_qdate(""))

    def _every_picked(self) -> None:
        if self._loading or self.it is None:
            return
        self.it.service_days = int(self.every.currentData() or 0)
        self._show_care()
        self._parts()
        self.changed.emit(self.it)

    def _log_add(self) -> None:
        it = self.it
        text = self.log_text.text().strip()
        if it is None or not (text or self.log_kind.currentData() == "service"):
            return
        it.log.append(
            LogEntry(from_qdate(self.log_date.date()), self.log_kind.currentData(), text, self.log_cost.value())
        )
        it.log.sort(key=lambda e: e.date)
        self.log_text.clear()
        self.log_cost.set_value("")
        self._show_care()
        self._parts()
        self.changed.emit(it)

    def _log_remove(self, n: int) -> None:
        it = self.it
        if it is None or not 0 <= n < len(it.log):
            return
        del it.log[n]
        self._show_care()
        self._parts()
        self.changed.emit(it)

    # Photo
    def _show_photo(self) -> None:
        it = self.it
        name = it.photo if it is not None and photos.path_of(it.photo) else ""
        self.photo.show_photo(name)
        self.photo.setVisible(bool(name))
        has_link = it is not None and bool(web.web_link(it.link))
        for a in (self.act_photo_link, self.act_add_photo_link):
            a.setEnabled(has_link)
            a.setText("From Link" if has_link else "From Link (add a link first)")

    def _use_photo(self, name: str) -> None:
        if self.it is None:
            return
        self.it.photo = name
        self._show_photo()
        self._parts()
        self.changed.emit(self.it)

    def choose_photo(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose a Photo", "", "Pictures (*.jpg *.jpeg *.png *.webp *.heic *.gif)"
        )
        if path:
            self._photo_file(Path(path))

    def _photo_file(self, path: Path) -> None:
        try:
            self._use_photo(photos.keep_file(path))
        except ValueError as e:  # not a picture, too big: said plainly by photos
            self.toast_wanted.emit(str(e), "problem")
        except OSError as e:
            self.toast_wanted.emit(errors.plain(e, "use that photo"), "error")

    def photo_from_link(self) -> None:
        if self.it is not None and web.web_link(self.it.link):
            self._photo_from_web(self.it.link, photos.from_link, "Getting the photo from the link…")

    def _photo_from_web(self, link: str, get, message: str) -> None:
        """Fetch a photo in the background: get(link) -> its name in the photos folder."""
        if self.it is None or (self._photo_job and self._photo_job.isRunning()):
            return
        item_id = self.it.id

        def job(_progress, _cancel) -> str:
            try:
                return get(link)
            except web.Refused as e:  # the store lets only browsers in: the browser can hand it over
                raise OSError(f"{e} {PASTE_INSTEAD}") from e

        self.toast_wanted.emit(message, "")
        w = Worker(job, self)
        w.done.connect(lambda name: self._photo_came(item_id, name))
        w.failed.connect(lambda e: self.toast_wanted.emit(e, "problem"))
        w.finished.connect(lambda: self._job_done(w))
        self._photo_job = w
        w.start()

    def _job_done(self, w: Worker) -> None:
        """A finished photo job goes (its thread with it), so nothing piles up as photos come in."""
        if self._photo_job is w:
            self._photo_job = None
        w.deleteLater()

    def _photo_came(self, item_id: str, name: str) -> None:
        if self.it is not None and self.it.id == item_id:
            self._use_photo(name)
        else:  # you moved on: it still goes on the piece it was for
            it = self.lib.items.get(item_id)
            if it is not None:
                it.photo = name
                self.changed.emit(it)

    def remove_photo(self) -> None:
        self._use_photo("")

    def paste_photo(self) -> bool:
        """Paste (⌘V): a picture you copied (Copy Image in a browser, a picture file) becomes the photo.
        False when there's no picture to paste."""
        return self._take_picture(QApplication.clipboard().mimeData(), links=False)

    def _paste_state(self) -> None:
        can = self.it is not None and photos.has_picture(QApplication.clipboard().mimeData(), links=False)
        for a in (self.act_photo_paste, self.act_add_photo_paste):
            a.setEnabled(can)
            a.setText("Paste" if can else "Paste (copy a picture first)")

    def _take_picture(self, mime, links: bool) -> bool:
        """A picture pasted or dropped: a picture file, the picture itself, or (`links`) a web link to it."""
        if self.it is None or mime is None:
            return False
        path = photos.picture_file(mime)
        if path is not None:
            self._photo_file(path)
            return True
        img = photos.picture_image(mime)
        if img is not None:
            try:
                self._use_photo(photos.keep_image(img))
            except ValueError as e:
                self.toast_wanted.emit(str(e), "problem")
            except OSError as e:
                self.toast_wanted.emit(errors.plain(e, "use that photo"), "error")
            return True
        link = photos.picture_link(mime) if links else ""
        if link:
            self._photo_from_web(link, photos.from_any_link, "Getting the photo…")
            return True
        return False

    def dragEnterEvent(self, e):
        if self.it is not None and photos.has_picture(e.mimeData()):
            e.acceptProposedAction()
        else:
            e.ignore()

    def dropEvent(self, e):
        if self._take_picture(e.mimeData(), links=True):
            e.acceptProposedAction()

    # Loading
    def b(self):
        return self.lib.pricing()

    def load(self, it: Item) -> None:
        self._loading = True
        self.it = it
        self.show_form()
        self.name.setText(it.name)
        self.name.setCursorPosition(0)
        self.brand_list.setStringList(self.lib.brands())
        self.series_list.setStringList(self.lib.series_of(it.brand))
        self.brand.setText(it.brand)
        self.series.setText(it.series)
        self._fill_groups()
        self.qty.setValue(it.qty)
        set_combo(self.status, it.status)
        cur = (self.b().currency or "$") if self.b() else "$"
        self.value.currency = self.rate.currency = cur
        self.value.set_value(it.value)
        self.rate.set_value(it.day_rate)
        self.rentable.setChecked(it.rentable)
        self.link.setText(it.link)
        self.link.setCursorPosition(0)
        self.notes.set_text(it.notes)
        self._show_price()
        self._link_state()
        self._build_serials()
        self._show_works()
        self._show_photo()
        self._show_care()
        self._parts()
        self._hints()
        self._loading = False

    def _fill_groups(self) -> None:
        c, it = self.group, self.it
        if it is None:
            return
        c.blockSignals(True)
        c.clear()
        for g in self.lib.groups():
            c.addItem(g, g)
        c.insertSeparator(c.count())
        c.addItem("None", "")
        c.insertSeparator(c.count())
        c.addItem("New Group…", NEW)
        c.setCurrentIndex(max(0, c.findData(it.group)))
        c.blockSignals(False)

    def _build_serials(self) -> None:
        """A field per unit, made only while Serial Numbers is shown (a big quantity would mean thousands)."""
        it = self.it
        if it is None:
            return
        if not (self._has("serials") or "serials" in it.extras):
            while self.serial_fields:
                self.serial_fields.pop().setParent(None)
            return
        while len(it.serials) < it.qty:
            it.serials.append("")
        while self.serial_fields and len(self.serial_fields) > it.qty:
            self.serial_fields.pop().setParent(None)
        while len(self.serial_fields) < it.qty:
            f = QLineEdit()
            n = len(self.serial_fields)
            f.textEdited.connect(lambda t, n=n: self._serial(n, t))
            self.serial_lay.addWidget(f)
            self.serial_fields.append(f)
        for n, f in enumerate(self.serial_fields):
            f.setPlaceholderText(f"Unit {n + 1}" if it.qty > 1 else "Serial number")
            if f.text() != it.serials[n]:
                f.setText(it.serials[n])

    def _serial(self, n: int, text: str) -> None:
        if self.it is None:
            return
        while len(self.it.serials) <= n:
            self.it.serials.append("")
        self.it.serials[n] = text
        self.changed.emit(self.it)
        self._parts()

    def _show_works(self) -> None:
        """Works With: what goes with this piece, or the piece it goes with."""
        it = self.it
        if it is None:
            return
        while self.kids_lay.count():
            w = self.kids_lay.takeAt(0).widget()
            if w is not None:
                w.setParent(None)
        p = self.lib.items.get(it.parent)
        if p is not None:
            self.kids_lay.addWidget(self._link_row(p, "Goes with", parent_row=True))
        for kid in pricing.children(self.lib, it.id):
            self.kids_lay.addWidget(self._link_row(kid, ""))
        rows_done(self.kids_lay)
        self.kids_box.setVisible(self.kids_lay.count() > 0)
        self.attach.setVisible(p is None)

    def _link_row(self, other: Item, lead: str, parent_row: bool = False) -> QWidget:
        box = KidRow(other.id)
        box.clicked.connect(lambda k: self.later(lambda: self.open_item.emit(k)))
        box.setToolTip("Open it")
        lay = hbox(
            box, (tokens.SPACE_3, tokens.SPACE_2, tokens.SPACE_2, tokens.SPACE_2), tokens.SPACE_2
        )  # as a rental's lines
        if lead:
            t = QLabel(lead)
            t.setObjectName("Meta")
            lay.addWidget(t)
        name = ElidedLabel(other.name + (f"  ×{other.qty}" if other.qty > 1 else ""))
        name.setObjectName("ItemTitle")
        lay.addWidget(name, 1)
        b = self.b()
        if other.value.strip() and not parent_row:
            v = QLabel(
                money.fmt_short(
                    money.whole(pricing.replacement(other, b) * other.qty), (b.currency if b else "$") or "$"
                )
            )
            v.setObjectName("ItemAmount")
            lay.addWidget(v)
        more = icon_button("more", "Open or remove")
        more.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        m = QMenu(more)
        m.addAction(theme.menu_icon("edit"), "Open", lambda k=other.id: self.later(lambda: self.open_item.emit(k)))
        loose = self.it.id if parent_row else other.id  # the one that stops going with the other
        m.addAction(
            theme.menu_icon("unlink"),
            "Doesn't Go With It",
            lambda k=loose: self.later(lambda: self.detach_wanted.emit(k)),
        )
        more.setMenu(m)
        lay.addWidget(more)
        return box

    def refresh_attached(self) -> None:
        if self.it is not None:
            self._loading = True
            self._show_works()
            self._parts()
            self._hints()
            self._loading = False

    def _where(self) -> None:
        """The head's quiet lines: the status as a dot and words (where it is, and until when, when it's out or
        booked: click to open that rental), then its company and group."""
        from bodega.ui.window.tables import status_of

        it = self.it
        found = None
        for r, _units, a, z in pricing.rentals_with(self.lib, it):
            if r.holds_gear():
                found = (r, a, z)
                break
        if found is None:
            word, color = status_of(it, pricing.units_out(self.lib).get(it.id, 0))
            text, tip, self._where_id = word, "", ""
        else:
            r, a, z = found
            who = r.client.company or r.client.name or r.number
            if r.is_out():
                text = f"Out · {who}" + (f" · back {dates.fmt_short(z)}" if z else "")
                color = tokens.BAD if pricing.late(r) else tokens.WARN
            else:
                text, color = f"Booked · {who} · {dates.span(a, z)}", tokens.INFO
            tip, self._where_id = f"Open {r.number}", r.id
        self.where.setText(text)
        self.where.setIcon(theme.dot(color))
        self.where.setToolTip(theme.plain_tip(tip) if tip else "")
        self.where.setProperty("link", bool(self._where_id))
        self.where.setCursor(Qt.CursorShape.PointingHandCursor if self._where_id else Qt.CursorShape.ArrowCursor)
        repolish(self.where)
        self.detail.setText(" · ".join(x for x in (it.brand, it.group) if x))
        self.detail.setVisible(bool(it.brand or it.group))
        self.rent.setEnabled(it.can_rent())
        self.rent.setToolTip(  # off, it says why
            "" if self.rent.isEnabled() else "Retired: it can't go on a rental" if it.is_retired() else "Not for rent"
        )

    @property
    def earned(self) -> dict | None:
        return self._all_earned

    @earned.setter
    def earned(self, every: dict | None) -> None:
        """Each refresh sets it (the list's sums, or None), and what was worked out here goes with it."""
        self._all_earned, self._one_earned = every, None

    def _earned(self, item_id: str):
        """What this piece has earned: from the list's sums when it has them; else only its own rentals are added
        up (a fraction of the work at a rental house's size), once until the next refresh."""
        if self._all_earned is not None:
            return self._all_earned.get(item_id)
        if self._one_earned is None or self._one_earned[0] != item_id:
            self._one_earned = (item_id, earnings.earnings(self.lib, only=item_id).get(item_id))
        return self._one_earned[1]

    def _sums(self, b, cur: str) -> None:
        """A gear sheet's math: tax, each with tax, the total for all of them; the head's strip has the day rate and
        what it has earned."""
        it = self.it
        paid = max(money.ZERO, money.parse(it.value))
        each = pricing.replacement(it, b)
        tax_pct = b.value_tax if b else "0"
        rows = {
            "tax": (
                f"Tax {money.fmt_rate(tax_pct)}",
                money.fmt(each - paid, cur),
                bool(paid) and each != paid,
            ),
            "each": ("Each with Tax", money.fmt(each, cur), bool(paid)),
            "total": (f"All {it.qty} with Tax", money.fmt(each * it.qty, cur), bool(paid) and it.qty > 1),
        }
        for key, (label, value, show) in rows.items():
            k, v = self.sum_rows[key]
            k.setText(label)
            v.setText(value)
            k.parentWidget().setVisible(show)
        self.sums.setVisible(any(show for _l, _v, show in rows.values()))
        self.strip.show_for(figures.piece(self.lib, it, b, self._earned(it.id)))

    def _hints(self) -> None:
        it, b = self.it, self.b()
        if it is None:
            return
        self._where()
        cur = (b.currency if b else "$") or "$"
        auto = pricing.auto_day_rate(it, b)
        self.rate.setPlaceholderText(f"{money.fmt_short(auto, cur)} (auto)")
        self._sums(b, cur)


class KidRow(QFrame):
    """Gear that goes with this piece (or the piece it goes with): click to open it."""

    clicked = Signal(str)

    def __init__(self, item_id: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.item_id = item_id
        self.setObjectName("ItemBox")
        self.setProperty("open", False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)  # Tab reaches it; Return or Space opens it

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.item_id)
        super().mousePressEvent(e)

    def keyPressEvent(self, e):
        if not by_keyboard(self, lambda: self.clicked.emit(self.item_id), e):
            super().keyPressEvent(e)


class PriceCheck(Background):
    """Reads the price from a link without freezing the window."""

    done = Signal(str, str, str, str)  # item id, price, store, error
    SAYS = ("done",)

    def __init__(self, item_id: str, url: str, parent=None):
        super().__init__(parent)
        self.item_id, self.url = item_id, url

    def run(self) -> None:
        try:
            got = prices.fetch(self.url)
        except web.Refused:
            site = web.site_name(self.url) or "That store"
            self.done.emit(self.item_id, "", "", f"{site} won't let Bodega read its price. Open the link instead.")
            return
        except OSError as e:
            self.done.emit(self.item_id, "", "", errors.plain(e, "check the price"))
            return
        except Exception:  # never leave the button stuck on "Checking…"
            log.warning("price check failed", exc_info=True)
            self.done.emit(self.item_id, "", "", "Couldn't read that page.")
            return
        if got is None:
            self.done.emit(self.item_id, "", web.site_name(self.url), "No price on that page.")
        else:
            self.done.emit(self.item_id, str(got.price), got.store, "")
