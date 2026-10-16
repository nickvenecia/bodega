"""Step 2 for a rental: who it's for, when, the gear (and fees), money, and the agreement's terms.

Every line can have its own dates: the FX6 package Sunday to Sunday and the FX3 package Monday to
Wednesday, on the same rental and the same agreement. Each line is billed for its own days. Gear that's
already promised for those dates, in repair, or more than you own is flagged under the line.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QFrame, QLabel, QLineEdit, QMenu, QPushButton, QToolButton, QWidget

from bodega.core import dates, money, pricing
from bodega.core.model import RENTAL_STATUSES, Client, Rental, RentalLine
from bodega.core.store import Library, terms_for
from bodega.ui.components.widgets import (
    WHOLE_TYPED,
    ElidedLabel,
    IconLabel,
    MoneyField,
    Section,
    TextBox,
    ToggleRow,
    add_chip,
    combo,
    date_field,
    from_qdate,
    hbox,
    hint,
    icon_button,
    only,
    percent_field,
    picker,
    qty_field,
    repolish,
    set_combo,
    to_qdate,
    vbox,
)
from bodega.ui.panels.base import DetailsBase
from bodega.ui.style import theme, tokens

STATUS_LABELS = {
    "quote": "Quote",
    "booked": "Booked",
    "out": "Out",
    "returned": "Returned",
    "cancelled": "Cancelled",
}
STATUS_TIPS = {
    "quote": "Not held yet: the gear can still go to someone else",
    "booked": "The gear is held for these dates",
    "out": "Picked up: shows as Out on the gear",
    "returned": "Everything's back",
    "cancelled": "Kept for your records; holds nothing",
}
NEW_CLIENT = "__new__"
ADD_BUSINESS = "__add__"


def _billed(d: pricing.Days) -> str:
    """ "Billed 3 of 7 days" — short, the reason is on the agreement."""
    if d.billed == d.out:
        return f"{d.out} day{'s' if d.out != 1 else ''}"
    return f"Billed {d.billed} of {d.out} days"


def _index(lines: list[RentalLine], line: RentalLine) -> int:
    """Where this very line is (two lines can be equal, so never compare them)."""
    return next((i for i, x in enumerate(lines) if x is line), -1)


HOLDS = ("booked", "out")  # statuses that hold their gear: picking one over a shortage asks first


class _Head(QFrame):
    clicked = Signal()

    def mousePressEvent(self, e):
        from PySide6.QtCore import Qt

        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(e)


class LineEditor(QFrame):
    """One line: a header (what, how much, ⋯) that folds its fields away. One open at a time."""

    changed = Signal()
    open_wanted = Signal(object)
    remove_wanted = Signal(object)
    move_wanted = Signal(object, int)
    gear_wanted = Signal(str)

    def __init__(self, panel: RentalPanel, line: RentalLine, parent: QWidget | None = None):
        super().__init__(parent)
        self.panel = panel
        self.line = line
        self.setObjectName("ItemBox")
        lay = vbox(self, 0, 0)
        self.head = _Head()
        from PySide6.QtCore import Qt

        self.head.setCursor(Qt.CursorShape.PointingHandCursor)
        hl = hbox(self.head, (tokens.SPACE_3, tokens.SPACE_2, tokens.SPACE_2, tokens.SPACE_2), tokens.SPACE_2)
        self.chevron = IconLabel("chevron-right")
        self.title = ElidedLabel()
        self.title.setObjectName("ItemTitle")
        self.amount = QLabel()
        self.amount.setObjectName("ItemAmount")
        self.flag = IconLabel("alert", "BAD")
        self.flag.hide()
        self.cal = IconLabel("calendar", "MUTED")
        self.cal.setToolTip("Has its own dates")
        self.cal.hide()
        self.more = icon_button("more", "Move or remove")
        self.more.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        m = QMenu(self.more)
        if line.kind == "item":
            m.addAction(theme.menu_icon("edit"), "Open Gear", lambda: self._later(self.gear_wanted, line.ref))
        self.act_up = m.addAction(
            theme.menu_icon("arrow-up"), "Move Up", lambda: self._later(self.move_wanted, self, -1)
        )
        self.act_down = m.addAction(
            theme.menu_icon("arrow-down"), "Move Down", lambda: self._later(self.move_wanted, self, 1)
        )
        m.addSeparator()
        m.addAction(theme.menu_icon("trash"), "Remove", lambda: self._later(self.remove_wanted, self))
        self.more.setMenu(m)
        for w in (self.chevron,):
            hl.addWidget(w)
        hl.addWidget(self.title, 1)
        hl.addWidget(self.cal)
        hl.addWidget(self.flag)
        hl.addWidget(self.amount)
        hl.addWidget(self.more)
        lay.addWidget(self.head)
        self.head.clicked.connect(lambda: self.open_wanted.emit(self))

        self.body = QWidget()
        bl = vbox(self.body, (tokens.SPACE_3, 0, tokens.SPACE_3, tokens.SPACE_3), tokens.SPACE_2)
        if line.kind == "fee":
            self.desc = QLineEdit(line.name)
            self.desc.setPlaceholderText("Delivery, tech day, cleaning…")
            self.desc.setAccessibleName("Fee")
            bl.addWidget(self.desc)
            self.desc.textEdited.connect(lambda t: self._set("name", t))
        row = hbox(spacing=tokens.SPACE_2)
        self.qty = qty_field(line.qty)
        times = QLabel("×")
        times.setObjectName("Muted")
        self.rate = MoneyField()
        self.rate.set_value(line.rate)
        self.rate.setFixedWidth(tokens.NUM_FIELD_W)
        self.qty.setAccessibleName("How Many")
        self.rate.setAccessibleName("Day Rate" if line.kind != "fee" else "Amount")
        per = QLabel("a day" if line.kind != "fee" else "each, once")
        per.setObjectName("Muted")
        row.addWidget(self.qty)
        row.addWidget(times)
        row.addWidget(self.rate)
        row.addWidget(per)
        row.addStretch(1)
        bl.addLayout(row)
        self.meta = hint("")
        self.meta.hide()  # what comes along is listed on the agreement, not here
        bl.addWidget(self.meta)
        if line.kind != "fee":
            self.own = ToggleRow("Its Own Dates", panel.r.own_dates(line) if panel.r else False)
            self.own.setToolTip("Goes out on different days than the rest of the rental")
            bl.addWidget(self.own)
            self.dates_box = QWidget()
            dl = hbox(self.dates_box, 0, tokens.SPACE_2)
            s1 = Section("Pickup")
            self.pick = date_field()
            s1.add(self.pick)
            s2 = Section("Return")
            self.ret = date_field()
            s2.add(self.ret)
            dl.addWidget(s1, 1)
            dl.addWidget(s2, 1)
            bl.addWidget(self.dates_box)
            self.days = hint("")
            bl.addWidget(self.days)
            self.own.toggled.connect(self._own_toggled)
            self.pick.dateChanged.connect(lambda q: self._date("pickup", from_qdate(q)))
            self.ret.dateChanged.connect(lambda q: self._date("return_date", from_qdate(q)))
            self.pick.dateChanged.connect(self.ret.setMinimumDate)  # it can't come back before it goes out
        self.warn = QLabel()
        self.warn.setObjectName("Bad")
        self.warn.setWordWrap(True)
        self.warn.hide()
        bl.addWidget(self.warn)
        lay.addWidget(self.body)
        self.qty.valueChanged.connect(lambda v: self._set("qty", v))
        self.rate.textEdited.connect(lambda t: self._set("rate", t.replace("$", "").replace(",", "").strip()))
        self.set_open(False)
        self.refresh()

    def _later(self, signal, *args) -> None:
        QTimer.singleShot(0, self, lambda: signal.emit(*args))

    def set_open(self, on: bool) -> None:
        self.body.setVisible(on)
        self.chevron.set_icon("chevron" if on else "chevron-right")
        self.setProperty("open", on)
        repolish(self)

    def is_open(self) -> bool:
        return self.body.isVisibleTo(self)

    def set_position(self, i: int, n: int) -> None:
        self.act_up.setEnabled(i > 0)
        self.act_down.setEnabled(i < n - 1)

    def _set(self, key: str, value) -> None:
        setattr(self.line, key, value)
        self.changed.emit()

    def _own_toggled(self, on: bool) -> None:
        r = self.panel.r
        if r is None:
            return
        if on:
            self.line.pickup = r.pickup
            self.line.return_date = r.return_date
            # nudge it a day so it really is different (they'll set the dates they want)
            if not r.own_dates(self.line):
                d = dates.parse(r.pickup)
                if d:
                    self.line.pickup = dates.iso(dates.plus(d, 1))
                    if (dates.parse(self.line.return_date) or d) <= dates.plus(d, 1):
                        self.line.return_date = dates.iso(dates.plus(d, 2))
        else:
            self.line.pickup = self.line.return_date = ""
        self.changed.emit()

    def _date(self, key: str, iso: str) -> None:
        if self.panel._loading:
            return
        setattr(self.line, key, iso)
        if key == "pickup" and (dates.parse(self.line.return_date) or dates.parse(iso)) < dates.parse(iso):
            self.line.return_date = iso
        self.changed.emit()

    def refresh(self) -> None:
        """Show the line's current numbers (called after any change to the rental)."""
        p = self.panel
        r, b, lib = p.r, p.b(), p.lib
        if r is None:
            return
        line = self.line
        cur = (b.currency if b else "$") or "$"
        name = pricing.line_name(lib, line) or ("New fee" if line.kind == "fee" else "")
        q = f"{line.qty} × " if line.qty > 1 else ""
        self.title.set_full_text(q + name)
        t = p.totals
        idx = _index(r.lines, line)
        amt = t.line_amounts[idx] if t and 0 <= idx < len(t.line_amounts) else money.ZERO
        self.amount.setText(money.fmt(amt, cur))
        if line.kind == "fee":
            self.rate.setPlaceholderText("Amount")
            self.meta.hide()
        else:
            auto = pricing.line_unit(lib, RentalLine(line.kind, line.ref, line.qty), b)
            self.rate.setPlaceholderText(money.fmt_short(auto, cur))
            self.rate.setToolTip("Leave blank for the automatic rate")
            gear = pricing.line_gear(lib, line)
            if line.kind == "package":
                n = sum(u for _i, u, _d in gear)
                self.meta.setText(f"Package: {n} pieces, serials and all, go on the agreement.")
            else:
                kids = [f"{k.name}" + (f" ×{u}" if u > 1 else "") for k, u, d in gear if d]
                self.meta.setText(("With " + ", ".join(kids)) if kids else "")

            own = r.own_dates(line)
            self.cal.setVisible(own)
            self.own.blockSignals(True)
            self.own.setChecked(own)
            self.own.blockSignals(False)
            self.dates_box.setVisible(own)
            if own:
                for f, iso in ((self.pick, line.pickup), (self.ret, line.return_date or line.pickup)):
                    f.blockSignals(True)
                    f.setDate(to_qdate(iso))
                    f.blockSignals(False)
            d = t.line_days[idx] if t and 0 <= idx < len(t.line_days) else None
            self.days.setText(_billed(d) if d else "")
            self.days.setVisible(own)
        shorts = [s for s in p.shorts if s.item.id in {it.id for it, _u, _d in pricing.line_gear(lib, line)}]
        if shorts:
            msg = "; ".join(
                f"{s.item.name}: {s.why.lower() if s.free == 0 and s.why in ('In repair', 'Retired') else f'{s.free} free, needs {s.needed} ({s.why})'}"
                for s in shorts
            )
            self.warn.setText(msg)
        self.warn.setVisible(bool(shorts))
        self.flag.setVisible(bool(shorts))
        self.flag.setToolTip(self.warn.text())


class RentalPanel(DetailsBase):
    TITLE = "Rental"
    KEY = "rentals"
    GROUPS = {
        "who": ("From && Renter", True),
        "rental": ("Rental", True),
        "gear": ("Gear", True),
        "money": ("Money", True),
        "agreement": ("Agreement", False),
        "history": ("History", False),
    }

    changed = Signal(object)  # Rental
    status_changed = Signal(object)
    business_wanted = Signal(str)  # "edit" or "add"
    client_wanted = Signal(str)  # "edit" or "new"
    add_wanted = Signal(str)  # rental id
    open_item = Signal(str)
    defaults_saved = Signal(object)  # Business
    delete_wanted = Signal(str)
    duplicate_wanted = Signal(str)
    calendar_wanted = Signal(str)  # its pickup and return in your calendar app
    check_wanted = Signal(str, bool)  # rental id, back in (else out)
    saldo_wanted = Signal(str)  # send it to Saldo as an invoice
    sheet_wanted = Signal(str)

    def __init__(self, lib: Library, parent: QWidget | None = None):
        super().__init__(parent)
        self.lib = lib
        self.r: Rental | None = None
        # (rental, "booked" or "out") -> may it hold gear that's short? (the window asks; None: never asked)
        self.may_hold: Callable[[Rental, str], bool] | None = None
        self.editors: list[LineEditor] = []
        self.totals: pricing.Totals | None = None
        self.shorts: list[pricing.Short] = []
        g = self.groups
        self.check = self.footer_button("Check Out…", "check", primary=False)
        self.check.clicked.connect(
            lambda: self.r and self.check_wanted.emit(self.r.id, self.r.status == "out")
        )
        self.sheet = self.footer_button("Agreement…", "receipt")
        self.menu_action("copy", "Duplicate", lambda: self.r and self.duplicate_wanted.emit(self.r.id))
        self.menu_action(
            "calendar", "Add to Calendar", lambda: self.r and self.calendar_wanted.emit(self.r.id)
        )
        self.menu_action("check", "Check Out…", lambda: self.r and self.check_wanted.emit(self.r.id, False))
        self.menu_action("check", "Check In…", lambda: self.r and self.check_wanted.emit(self.r.id, True))
        self.menu_action("receipt", "Send to Saldo…", lambda: self.r and self.saldo_wanted.emit(self.r.id))
        self.menu_action("", "-", None)
        self.delete_act = self.menu_action(
            "trash", "Delete Rental…", lambda: self.r and self.delete_wanted.emit(self.r.id)
        )  # a booked one: Mark as Cancelled… (it's never deleted)
        self.sheet.clicked.connect(lambda: self.r and self.sheet_wanted.emit(self.r.id))

        # who
        sec = Section("From")
        row = hbox(spacing=tokens.SPACE_2)
        self.business = picker()
        self.edit_business = QPushButton("Edit…")
        self.edit_business.setToolTip("Your name, logo, pricing and standard terms")
        row.addWidget(self.business, 1)
        row.addWidget(self.edit_business)
        sec.add(row)
        g["who"].add(sec)
        sec = Section("Renter")
        row = hbox(spacing=tokens.SPACE_2)
        self.client = picker("Choose a Renter")
        self.edit_client = QPushButton("Edit…")
        row.addWidget(self.client, 1)
        row.addWidget(self.edit_client)
        sec.add(row)
        g["who"].add(sec)

        # rental
        row = hbox(spacing=tokens.SPACE_2)
        sec = Section("Status")
        self.status = combo([(k, STATUS_LABELS[k], STATUS_TIPS[k]) for k in RENTAL_STATUSES], "quote")
        sec.add(self.status)
        row.addWidget(sec, 1)
        sec = Section("Rental No.")
        self.number = QLineEdit()
        sec.add(self.number)
        row.addWidget(sec, 1)
        g["rental"].add(row)
        self.number_clash = QLabel()
        self.number_clash.setObjectName("Warn")
        self.number_clash.setWordWrap(True)
        self.number_clash.hide()
        g["rental"].add(self.number_clash)
        sec = Section("Production")
        self.project = QLineEdit()
        self.project.setPlaceholderText("Project name (optional)")
        sec.add(self.project)
        g["rental"].add(sec)
        row = hbox(spacing=tokens.SPACE_2)
        sec = Section("Pickup")
        self.pickup = date_field()
        sec.add(self.pickup)
        row.addWidget(sec, 1)
        sec = Section("Return")
        self.ret = date_field()
        sec.add(self.ret)
        row.addWidget(sec, 1)
        g["rental"].add(row)
        self.weekend = ToggleRow("Weekend Counts as 1 Day", True)
        self.weekend.setToolTip("Pick up Friday, return Monday: billed as one day")
        g["rental"].add(self.weekend)
        row = hbox(spacing=tokens.SPACE_2)
        sec = Section("Billed Days")
        self.billed = only(QLineEdit(), WHOLE_TYPED)
        self.billed.setFixedWidth(tokens.NUM_FIELD_W)
        self.billed.setToolTip("Leave blank and Bodega works it out")
        sec.add(self.billed)
        row.addWidget(sec)
        self.days_hint = hint("")
        row.addWidget(self.days_hint, 1)
        g["rental"].add(row)

        # gear
        self.lines_box = QWidget()
        self.lines_lay = vbox(self.lines_box, 0, tokens.SPACE_2)
        g["gear"].add(self.lines_box)
        arow = hbox(spacing=tokens.SPACE_2)
        self.add = add_chip("Add Gear")
        self.add.setToolTip("Kits and gear")
        self.add_fee = add_chip("Add Fee")
        self.add_fee.setToolTip("A flat charge: delivery, a tech, cleaning")
        arow.addWidget(self.add)
        arow.addWidget(self.add_fee)
        arow.addStretch(1)
        g["gear"].add(arow)
        self.short_hint = QLabel()
        self.short_hint.setObjectName("Bad")
        self.short_hint.setWordWrap(True)
        self.short_hint.hide()
        g["gear"].add(self.short_hint)

        # money
        row = hbox(spacing=tokens.SPACE_2)
        sec = Section("Discount %")
        self.discount = percent_field(placeholder="None")
        sec.add(self.discount)
        row.addWidget(sec, 1)
        sec = Section("Sales Tax %")
        self.tax = percent_field(placeholder="None")
        sec.add(self.tax)
        row.addWidget(sec, 1)
        g["money"].add(row)
        sec = Section("Security Deposit")
        drow = hbox(spacing=tokens.SPACE_2)
        self.deposit = MoneyField()
        self.deposit.setPlaceholderText("None")
        self.deposit.setToolTip("Refundable: on the agreement, not in the total")
        self.suggest = QPushButton("Suggest")
        self.suggest.setObjectName("Ghost")
        drow.addWidget(self.deposit, 1)
        drow.addWidget(self.suggest)
        sec.add(drow)
        g["money"].add(sec)
        self.sums = QWidget()
        sl = vbox(self.sums, (0, tokens.SPACE_1, 0, 0), tokens.SPACE_1)
        self.sum_rows: dict[str, tuple[QLabel, QLabel]] = {}
        for key in ("per_day", "gear", "fees", "discount", "tax", "total", "deposit", "value"):
            r = hbox(spacing=tokens.SPACE_2)
            k = QLabel()
            k.setObjectName("SumLabel")
            v = QLabel()
            v.setObjectName("Sum" if key == "total" else "SumValue")
            r.addWidget(k, 1)
            r.addWidget(v)
            sl.addLayout(r)
            self.sum_rows[key] = (k, v)
        g["money"].add(self.sums)

        # agreement
        self.serials = ToggleRow("Show Serial Numbers", True)
        self.checks = ToggleRow("Out && In Check Boxes".replace("&&", "&"), True)
        self.checks.setToolTip("Boxes beside every piece, for checking it out and back in")
        g["agreement"].add(self.serials)
        g["agreement"].add(self.checks)
        sec = Section("Terms")
        self.terms = TextBox("", tokens.TEXT_BOX_TERMS)
        self.terms.setToolTip("One clause per paragraph: its first words, up to a period, print bold")
        sec.add(self.terms)
        g["agreement"].add(sec)
        sec = Section("Closing Note")
        self.note = QLineEdit()
        sec.add(self.note)
        g["agreement"].add(sec)
        row = hbox()
        self.reset_terms = QPushButton("Use Profile Terms")
        self.reset_terms.setObjectName("Ghost")
        self.save_terms = QPushButton("Make These the Defaults")
        self.save_terms.setObjectName("Ghost")
        self.save_terms.setToolTip("New rentals will start with these terms and note")
        row.addWidget(self.reset_terms)
        row.addWidget(self.save_terms)
        row.addStretch(1)
        g["agreement"].add(row)
        self.history = QLabel()  # what happened to it, newest first
        self.history.setObjectName("Muted")
        self.history.setWordWrap(True)
        g["history"].add(self.history)

        self._connect()
        self.form.hide()

    # ------------------------------------------------------------------ wiring
    def _connect(self) -> None:
        def text(field):
            return lambda t: self._edit(field, t)

        self.business.activated.connect(self._business_picked)
        self.edit_business.clicked.connect(lambda: self.business_wanted.emit("edit"))
        self.client.activated.connect(self._client_picked)
        self.edit_client.clicked.connect(lambda: self.client_wanted.emit("edit"))
        self.status.currentIndexChanged.connect(self._status_picked)
        self.number.textEdited.connect(self._number_typed)
        self.project.textEdited.connect(text("project"))
        self.pickup.dateChanged.connect(self._pickup_changed)
        self.ret.dateChanged.connect(lambda q: self._edit("return_date", from_qdate(q)))
        self.pickup.dateChanged.connect(self.ret.setMinimumDate)  # it can't come back before it goes out
        self.weekend.toggled.connect(lambda on: self._edit("weekend_deal", on))
        self.billed.textEdited.connect(text("billed_days"))
        self.add.clicked.connect(lambda: self.r and self.add_wanted.emit(self.r.id))
        self.add_fee.clicked.connect(self._add_fee)
        self.discount.textEdited.connect(text("discount"))
        self.tax.textEdited.connect(text("tax_rate"))
        self.deposit.textEdited.connect(text("deposit"))
        self.suggest.clicked.connect(self._suggest)
        self.serials.toggled.connect(lambda on: self._edit("show_serials", on))
        self.checks.toggled.connect(lambda on: self._edit("show_checks", on))
        self.terms.edited.connect(lambda: self._edit("terms", self.terms.text()))
        self.note.textEdited.connect(text("note"))
        self.reset_terms.clicked.connect(self._reset_terms)
        self.save_terms.clicked.connect(self._save_terms)

    def b(self):
        if self.r is not None and self.r.business_id in self.lib.businesses:
            return self.lib.businesses[self.r.business_id]
        return next(iter(self.lib.businesses.values()), None)

    def current_business(self):
        return self.b()

    def _edit(self, key: str, value) -> None:
        if self._loading or self.r is None:
            return
        setattr(self.r, key, value)
        self.recalc()
        self.changed.emit(self.r)

    def _number_typed(self, t: str) -> None:
        if self.r is not None:
            self.r.auto_number = False
        self._edit("number", t)
        self._show_clash()

    def _show_delete(self) -> None:
        r = self.r
        if r is None:
            return
        self.delete_act.setText("Delete Rental…" if r.deletable() else "Mark as Cancelled…")
        self.delete_act.setVisible(r.deletable() or r.status != "cancelled")

    def show_history(self) -> None:
        """Its history, newest first (it's written as it's saved)."""
        r = self.r
        if r is None:
            return
        lines = [f"{dates.fmt_moment(e.at)} · {e.what}" for e in reversed(r.history) if e.what]
        self.history.setText("\n".join(lines) or "Nothing yet.")
        last = r.history[-1] if r.history else None
        self.groups["history"].set_summary(last.what if last else "")

    def _show_clash(self) -> None:
        """A number another rental already has is said under the field (it's still yours to keep)."""
        other = self.lib.number_taken(self.r.number, skip=self.r.id) if self.r is not None else None
        if other is None:
            self.number_clash.hide()
            return
        who = f"{other.client.name}'s rental" if other.client.name.strip() else "Another rental"
        when = dates.fmt(dates.parse(other.pickup))
        self.number_clash.setText(f"{who}{' from ' + when if when else ''} already has this number.")
        self.number_clash.show()

    def _pickup_changed(self, q) -> None:
        if self._loading or self.r is None:
            return
        iso = from_qdate(q)
        old = dates.parse(self.r.pickup)
        new = dates.parse(iso)
        ret = dates.parse(self.r.return_date)
        # moving the pickup keeps the same length of rental
        if old and new and ret:
            self.r.return_date = dates.iso(dates.plus(new, max(0, (ret - old).days)))
            self._loading = True
            self.ret.setDate(to_qdate(self.r.return_date))
            self._loading = False
        self.r.pickup = iso
        self.recalc()
        self.changed.emit(self.r)

    def _show_check(self) -> None:
        """Check Out… while it's booked, Check In… while it's out; otherwise it steps aside."""
        r = self.r
        on = r is not None and r.status in ("booked", "out")
        self.check.setVisible(on)
        if on:
            self.check.setText("Check In…" if r.status == "out" else "Check Out…")

    def _status_picked(self, _i: int) -> None:
        if self._loading or self.r is None:
            return
        new = self.status.currentData()
        if new in HOLDS and new != self.r.status and pricing.shortages(self.lib, self.r) and self.may_hold:
            set_combo(self.status, self.r.status)  # asked once the pick is over (it may be said no to)
            r = self.r
            QTimer.singleShot(0, self, lambda: self._ask_to_hold(r, new))
            return
        self._apply_status(new)

    def _ask_to_hold(self, r: Rental, status: str) -> None:
        if self.r is r and self.may_hold(r, status):
            set_combo(self.status, status)
            self._apply_status(status)

    def _apply_status(self, status: str) -> None:
        self.r.status = status
        self._show_check()
        self._show_delete()
        if self.r.status != "quote":
            self.r.auto_number = False
        self.recalc()
        self.changed.emit(self.r)
        self.status_changed.emit(self.r)

    def set_status(self, status: str) -> None:
        """Set its status as given (already asked about, if it needed asking)."""
        set_combo(self.status, status)
        if self.r is not None and not self._loading:
            self._apply_status(status)

    def _business_picked(self, _i: int) -> None:
        if self.r is None:
            return
        key = self.business.currentData()
        if key == ADD_BUSINESS:
            self.refresh_businesses()
            self.business_wanted.emit("add")
            return
        if key and key != self.r.business_id:
            self.r.business_id = key
            if self.lib.renumber(self.r):
                self.number.setText(self.r.number)
                self._show_clash()
            self.recalc()
            self.changed.emit(self.r)

    def _client_picked(self, _i: int) -> None:
        if self.r is None:
            return
        key = self.client.currentData()
        if key == NEW_CLIENT:
            self.refresh_clients()
            self.client_wanted.emit("new")
            return
        c = self.lib.clients.get(key)
        if c is not None:
            self.use_client(c)

    def use_client(self, c: Client) -> None:
        if self.r is None:
            return
        self.r.client = replace(c)
        self.refresh_clients()
        self.recalc()
        self.changed.emit(self.r)

    def _add_fee(self) -> None:
        if self.r is None:
            return
        line = RentalLine("fee", "", 1, "", "")
        self.r.lines.append(line)
        self.build_lines(open_line=line)
        self.changed.emit(self.r)

    def _suggest(self) -> None:
        if self.r is None:
            return
        b = self.b()
        amt = pricing.suggested_deposit(self.lib, self.r, b)
        self.deposit.set_value(f"{amt:f}".split(".")[0])
        self._edit("deposit", self.deposit.value())

    def _reset_terms(self) -> None:
        b = self.b()
        if self.r is None or b is None:
            return
        self.terms.set_text(terms_for(b))
        self.note.setText(b.note)
        self.r.terms, self.r.note = self.terms.text(), b.note
        self.recalc()
        self.changed.emit(self.r)

    def _save_terms(self) -> None:
        b = self.b()
        if self.r is None or b is None:
            return
        who = b.name.strip()
        b.terms = self.r.terms.replace(who, "{owner}") if who else self.r.terms
        b.note = self.r.note
        self.defaults_saved.emit(b)
        self.recalc()

    # ------------------------------------------------------------------ loading
    def load(self, r: Rental) -> None:
        self._loading = True
        self.r = r
        self.show_form()
        self.refresh_businesses()
        self.refresh_clients()
        set_combo(self.status, r.status)
        self._show_check()
        self.number.setText(r.number)
        self._show_clash()
        self._show_delete()
        self.project.setText(r.project)
        self.pickup.setDate(to_qdate(r.pickup))
        self.ret.setDate(to_qdate(r.return_date or r.pickup))
        self.weekend.setChecked(r.weekend_deal)
        self.billed.setText(r.billed_days)
        self.discount.setText(r.discount)
        self.tax.setText(r.tax_rate)
        self.deposit.set_value(r.deposit)
        self.serials.setChecked(r.show_serials)
        self.checks.setChecked(r.show_checks)
        self.terms.set_text(r.terms)
        self.note.setText(r.note)
        self._loading = False
        self.build_lines()

    def refresh_businesses(self) -> None:
        c = self.business
        c.blockSignals(True)
        c.clear()
        for b in self.lib.businesses.values():
            c.addItem(b.name or "Your profile", b.id)
        c.insertSeparator(c.count())
        c.addItem("Add a Profile…", ADD_BUSINESS)
        if self.r is not None:
            c.setCurrentIndex(max(0, c.findData(self.r.business_id)))
        c.blockSignals(False)

    def refresh_clients(self) -> None:
        c = self.client
        c.blockSignals(True)
        c.clear()
        for cl in sorted(self.lib.clients.values(), key=lambda x: (x.company or x.name).casefold()):
            label = cl.name + (f" · {cl.company}" if cl.company and cl.company != cl.name else "")
            c.addItem(label or "Renter", cl.id)
        if self.r is not None and not self.r.client.is_blank() and self.r.client.id not in self.lib.clients:
            c.insertItem(0, self.r.client.name or self.r.client.company, self.r.client.id)
        if c.count():
            c.insertSeparator(c.count())
        c.addItem("New Renter…", NEW_CLIENT)
        idx = c.findData(self.r.client.id) if self.r is not None and not self.r.client.is_blank() else -1
        c.setCurrentIndex(idx)
        c.blockSignals(False)
        self.edit_client.setVisible(idx >= 0)

    def build_lines(self, open_line: RentalLine | None = None) -> None:
        was_open = next((e.line for e in self.editors if e.is_open()), None)
        for e in self.editors:
            e.setParent(None)
            e.deleteLater()
        self.editors = []
        while self.lines_lay.count():
            w = self.lines_lay.takeAt(0).widget()
            if w is not None:
                w.setParent(None)
        if self.r is None:
            return
        self._compute()
        if not self.r.lines:
            self.lines_lay.addWidget(hint("Nothing on it yet."))
        for line in self.r.lines:
            e = LineEditor(self, line)
            e.changed.connect(self._line_changed)
            e.open_wanted.connect(self._open_editor)
            e.remove_wanted.connect(self._remove_line)
            e.move_wanted.connect(self._move_line)
            e.gear_wanted.connect(self.open_item.emit)
            self.lines_lay.addWidget(e)
            self.editors.append(e)
        for i, e in enumerate(self.editors):
            e.set_position(i, len(self.editors))
            if e.line is (open_line or was_open):
                e.set_open(True)
        self.recalc()

    def _open_editor(self, ed: LineEditor) -> None:
        on = not ed.is_open()
        for e in self.editors:
            e.set_open(e is ed and on)

    def _line_changed(self) -> None:
        self.recalc()
        if self.r is not None:
            self.changed.emit(self.r)

    def _remove_line(self, ed: LineEditor) -> None:
        i = _index(self.r.lines, ed.line) if self.r is not None else -1
        if i >= 0:
            del self.r.lines[i]
            self.build_lines()
            self.changed.emit(self.r)

    def _move_line(self, ed: LineEditor, step: int) -> None:
        i = _index(self.r.lines, ed.line) if self.r is not None else -1
        if i < 0:
            return
        j = i + step
        if 0 <= j < len(self.r.lines):
            self.r.lines[i], self.r.lines[j] = self.r.lines[j], self.r.lines[i]
            self.build_lines(open_line=ed.line)
            self.changed.emit(self.r)

    # ------------------------------------------------------------------ numbers
    def _compute(self) -> None:
        if self.r is None:
            return
        self.totals = pricing.totals(self.lib, self.r, self.b())
        self.shorts = pricing.shortages(self.lib, self.r)

    def recalc(self) -> None:
        """Every number in the panel, after any change."""
        r, b = self.r, self.b()
        if r is None:
            return
        self._compute()
        t = self.totals
        cur = (b.currency if b else "$") or "$"
        for e in self.editors:
            e.refresh()
        auto = pricing.days_for(
            dates.parse(r.pickup), dates.parse(r.return_date), b, r.weekend_deal, pricing.week_days(r, b)
        )
        self.billed.setPlaceholderText(str(auto.billed))
        self.days_hint.setText(_billed(t.days))
        self.weekend.setVisible(True)
        if self.shorts:
            n = len(self.shorts)
            self.short_hint.setText(
                f"{n} piece{'s are' if n != 1 else ' is'} not free on these dates. Open the flagged lines to see why."
            )
        self.short_hint.setVisible(bool(self.shorts) and r.status in ("quote", "booked", "out"))
        rows = {
            "per_day": ("Gear per Day", money.fmt(t.per_day, cur), False),
            "gear": (
                f"Rental, {len(pricing.periods(r))} Periods"
                if t.mixed
                else f"Rental, {t.days.billed} Day{'s' if t.days.billed != 1 else ''}",
                money.fmt(t.gear, cur),
                True,
            ),
            "fees": ("Fees", money.fmt(t.fees, cur), bool(t.fees)),
            "discount": ("Discount", money.fmt(-t.discount, cur), bool(t.discount)),
            "tax": ("Sales Tax", money.fmt(t.tax, cur), bool(t.tax)),
            "total": ("Total", money.fmt(t.total, cur), True),
            "deposit": ("Deposit (Refundable)", money.fmt(t.deposit, cur), bool(t.deposit)),
            "value": ("Replacement Value", money.fmt(t.value, cur), False),
        }
        for key, (label, val, show) in rows.items():
            k, v = self.sum_rows[key]
            k.setText(label)
            v.setText(val)
            k.setVisible(show)
            v.setVisible(show)
        self.suggest.setToolTip(
            f"{money.fmt_rate(pricing.deposit_pct(b))} of the replacement value"
            + (" (your profile)" if b and b.deposit_pct.strip() else "")
        )
        g = self.groups
        g["who"].set_summary(r.client.company or r.client.name or "No renter yet")
        g["rental"].set_summary(f"{STATUS_LABELS[r.status]} · {dates.span(*pricing.span_of(r))}")
        n = len([ln for ln in r.lines if ln.kind != "fee"])
        g["gear"].set_summary(f"{n} line{'s' if n != 1 else ''}" + (" · check dates" if self.shorts else ""))
        g["money"].set_summary(money.fmt(t.total, cur))
        g["agreement"].set_summary(
            "Custom terms" if b and r.terms.strip() != terms_for(b).strip() else "Profile terms"
        )
        self.show_history()
        self.reset_terms.setVisible(bool(b) and r.terms.strip() != terms_for(b).strip())
