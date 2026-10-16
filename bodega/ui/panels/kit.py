"""Step 2 for a package: its name, the gear in it (attached gear comes along), and its price.

The price starts from what the gear would cost piece by piece. Take a percent off (the usual way, 15% to
start), set your own day rate, or charge what it adds up to. The numbers under it say what that comes to.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QLabel, QMenu, QToolButton, QWidget

from bodega.core import money, pricing
from bodega.core.model import Package
from bodega.core.store import Library
from bodega.ui.components.widgets import (
    ElidedLabel,
    MoneyField,
    Section,
    TextBox,
    TitleEdit,
    add_chip,
    combo,
    hbox,
    hint,
    icon_button,
    percent_field,
    qty_field,
    rows_done,
    set_combo,
    vbox,
)
from bodega.ui.panels.base import DetailsBase
from bodega.ui.style import theme, tokens

PRICINGS = [
    ("discount", "Gear Discount", "A percent off what the gear costs piece by piece"),
    ("fixed", "Own Day Rate", "Your own price for the whole kit"),
    ("sum", "Gear Total", "What the gear adds up to, no discount"),
]


class PackagePanel(DetailsBase):
    TITLE = "Kit"
    KEY = "packages"
    GROUPS = {
        "package": ("About", True),
        "gear": ("Gear", True),
        "price": ("Price", True),
    }

    changed = Signal(object)  # Package
    add_wanted = Signal(str)  # package id
    open_item = Signal(str)
    delete_wanted = Signal(str)
    duplicate_wanted = Signal(str)
    sheet_wanted = Signal(str)

    def __init__(self, lib: Library, parent: QWidget | None = None):
        super().__init__(parent)
        self.lib = lib
        self.pkg: Package | None = None
        g = self.groups
        self.sheet = self.footer_button("Kit Sheet…", "receipt")
        self.menu_action("copy", "Duplicate", lambda: self.pkg and self.duplicate_wanted.emit(self.pkg.id))
        self.menu_action("", "-", None)
        self.menu_action("trash", "Delete Kit…", lambda: self.pkg and self.delete_wanted.emit(self.pkg.id))
        self.sheet.clicked.connect(lambda: self.pkg and self.sheet_wanted.emit(self.pkg.id))
        self.name = TitleEdit()  # the kit's name as its title, like a piece of gear's
        self.name.setPlaceholderText("FX6 Run && Gun, Interview Kit…".replace("&&", "&"))
        self.form_lay.insertWidget(0, self.name)
        self.notes = TextBox("What it's good for. Prints on the kit sheet.", tokens.TEXT_BOX_H)
        g["package"].add(self.notes)

        self.lines_box = QWidget()
        self.lines_lay = vbox(self.lines_box, 0, 0)  # rows, with hairlines between
        g["gear"].add(self.lines_box)
        arow = hbox()
        self.add = add_chip("Add Gear…")
        arow.addWidget(self.add)
        arow.addStretch(1)
        g["gear"].add(arow)

        sec = Section("Priced By")
        self.pricing = combo(PRICINGS, "discount")
        sec.add(self.pricing)
        g["price"].add(sec)
        self.disc_sec = Section("Discount %")
        self.discount = percent_field(placeholder="15")
        self.disc_sec.add(self.discount)
        self.fixed_sec = Section("Day Rate")
        self.fixed = MoneyField()
        self.fixed_sec.add(self.fixed)
        row = hbox(spacing=tokens.SPACE_2)
        row.addWidget(self.disc_sec, 1)
        row.addWidget(self.fixed_sec, 1)
        g["price"].add(row)
        self.sums = QWidget()
        sl = vbox(self.sums, 0, tokens.SPACE_1)
        self.sum_rows = {}
        for key, label in (
            ("rate", "Day Rate"),
            ("week", "Week"),
            ("alone", "Without the Kit"),
            ("value", "Value"),
        ):
            r = hbox(spacing=tokens.SPACE_2)
            k = QLabel(label)
            k.setObjectName("SumLabel")
            v = QLabel()
            v.setObjectName("Sum" if key == "rate" else "SumValue")
            r.addWidget(k, 1)
            r.addWidget(v)
            sl.addLayout(r)
            self.sum_rows[key] = v
        g["price"].add(self.sums)
        self.price_hint = hint("")  # what renters save with the kit
        g["price"].add(self.price_hint)

        self.name.textEdited.connect(lambda t: self._set("name", t))
        self.notes.edited.connect(lambda: self._set("notes", self.notes.text()))
        self.add.clicked.connect(lambda: self.pkg and self.add_wanted.emit(self.pkg.id))
        self.pricing.currentIndexChanged.connect(lambda _i: self._set("pricing", self.pricing.currentData()))
        self.discount.textEdited.connect(lambda t: self._set("discount", t))
        self.fixed.textEdited.connect(lambda t: self._set("day_rate", t.replace("$", "").replace(",", "").strip()))
        self.form.hide()

    def b(self):
        return self.lib.pricing()

    def _set(self, key: str, value) -> None:
        if self._loading or self.pkg is None:
            return
        setattr(self.pkg, key, value)
        self._sums()
        self.changed.emit(self.pkg)

    def load(self, pkg: Package) -> None:
        self._loading = True
        self.pkg = pkg
        self.show_form()
        self.name.setText(pkg.name)
        self.notes.set_text(pkg.notes)
        set_combo(self.pricing, pkg.pricing)
        self.discount.setText(pkg.discount)
        self.fixed.set_value(pkg.day_rate)
        self.build_lines()
        self._sums()
        self._loading = False

    def build_lines(self) -> None:
        while self.lines_lay.count():
            w = self.lines_lay.takeAt(0).widget()
            if w is not None:
                w.setParent(None)
        if self.pkg is None:
            return
        if not self.pkg.lines:
            self.lines_lay.addWidget(hint("No gear yet."))
        for n, line in enumerate(self.pkg.lines):
            it = self.lib.items.get(line.item_id)
            if it is None:
                continue
            self.lines_lay.addWidget(self._line_row(n, it, line))
        rows_done(self.lines_lay)
        self._sums()

    def _line_row(self, n: int, it, line) -> QWidget:
        box = QFrame()
        box.setObjectName("ItemBox")
        lay = vbox(box, (tokens.SPACE_3, tokens.SPACE_2, tokens.SPACE_2, tokens.SPACE_2), tokens.SPACE_1)
        top = hbox(spacing=tokens.SPACE_2)
        name = ElidedLabel(it.name)
        name.setObjectName("ItemTitle")
        top.addWidget(name, 1)
        qty = qty_field(line.qty)
        qty.setToolTip(f"You have {it.qty}")
        qty.setAccessibleName(f"How many {it.name}")
        qty.valueChanged.connect(lambda v, line=line: self._qty(line, v))
        top.addWidget(qty)
        more = icon_button("more", "Open or remove")
        more.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        m = QMenu(more)
        m.addAction(theme.menu_icon("edit"), "Open Gear", lambda i=it.id: self.later(lambda: self.open_item.emit(i)))
        m.addSeparator()
        m.addAction(theme.menu_icon("trash"), "Remove", lambda n=n: self.later(lambda: self._remove(n)))
        more.setMenu(m)
        top.addWidget(more)
        lay.addLayout(top)
        kids = pricing.with_attached(self.lib, it, line.qty)[1:]
        if kids:
            meta = ElidedLabel("With " + ", ".join(k.name for k, _u, _d in kids))
            meta.setObjectName("RowMeta")
            lay.addWidget(meta)
        if line.qty > it.qty:
            warn = QLabel(f"You only have {it.qty}.")
            warn.setObjectName("Warn")
            lay.addWidget(warn)
        return box

    def _qty(self, line, v: int) -> None:
        line.qty = v
        self._sums()
        if self.pkg is not None:
            self.changed.emit(self.pkg)

    def _remove(self, n: int) -> None:
        if self.pkg is not None and 0 <= n < len(self.pkg.lines):
            del self.pkg.lines[n]
            self.build_lines()
            self.changed.emit(self.pkg)

    def _sums(self) -> None:
        p, b = self.pkg, self.b()
        if p is None:
            return
        cur = (b.currency if b else "$") or "$"
        wd = b.week_days if b else 7
        self.disc_sec.setVisible(p.pricing == "discount")
        self.fixed_sec.setVisible(p.pricing == "fixed")
        alone = pricing.package_sum(self.lib, p, b)
        rate = pricing.package_rate(self.lib, p, b)
        self.fixed.setPlaceholderText(money.fmt_short(alone, cur))
        self.sum_rows["alone"].setText(f"{money.fmt_short(alone, cur)} a day")
        self.sum_rows["rate"].setText(f"{money.fmt_short(rate, cur)} a day")
        self.sum_rows["week"].setText(money.fmt_short(rate * wd, cur))
        self.sum_rows["value"].setText(money.fmt_short(money.whole(pricing.package_value(self.lib, p, b)), cur))
        save = alone - rate
        if save > 0 and alone:
            pct = money.whole(save / alone * 100)
            self.price_hint.setText(
                f"Renters save {money.fmt_short(save, cur)} a day ({pct}%) over renting it piece by piece."
            )
        elif rate > alone:
            self.price_hint.setText("That's more than the gear costs piece by piece.")
        else:
            self.price_hint.setText("")
        pieces = sum(u for _i, u, _d in pricing.package_gear(self.lib, p))
        self.groups["gear"].set_summary(f"{pieces} piece{'s' if pieces != 1 else ''}")
        self.groups["price"].set_summary(f"{money.fmt_short(rate, cur)} a day")
