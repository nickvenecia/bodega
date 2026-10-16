"""The Import window: look over a spreadsheet before any of it goes into Bodega, and choose what comes in.

Bodega starts empty for everyone. A sheet only ever goes into the copy on this computer, and only after
Import is clicked. Here you can:
- fix which column is which (Bodega guesses from the header words),
- leave out whole departments, or single pieces,
- choose whether gear that says what it's for gets attached to it,
- choose whether your profile takes the sheet's day-rate percent and tax (off when you have a profile:
  it would replace yours),
- see what the sheet left blank and was filled in (a quantity of 1, for rent, a company guessed from the
  name), and turn the company guess off,
- choose whether gear you already have takes the sheet's links (only where it has none),
- skip what's already in Bodega (so importing the same sheet twice doesn't double it).
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QListWidget, QListWidgetItem, QPushButton, QWidget

from bodega.core import importer, money, words
from bodega.core.model import Item
from bodega.ui.components.widgets import (
    Disclosure,
    FitScroll,
    Section,
    ToggleRow,
    combo,
    hbox,
    set_combo,
    vbox,
)
from bodega.ui.style import theme, tokens

NONE = "__none__"
REF = Qt.ItemDataRole.UserRole


class ImportDialog(QDialog):
    """After Import: `.items` (what to add, parents tidied), `.pricing` ((rate %, tax %) or None) and
    `.fill_links` (gear you have takes the sheet's links where it has none)."""

    def __init__(
        self,
        path: Path,
        rows: list[list],
        have: set[tuple[str, str]],
        parent: QWidget | None = None,
        has_profile: bool = False,
    ):
        super().__init__(parent)
        self.fill_links = False
        self.path = path
        self.rows = rows
        self.have = have  # (name, department) already in Bodega, casefolded
        self.layout_guess = importer.detect(rows)
        self.got = importer.Imported()
        self.items: list[Item] = []
        self.pricing: tuple[str, str] | None = None
        self._unticked: set[tuple[str, str, str]] = set()  # pieces left out by hand (survive a re-read)
        self.dep_toggles: dict[str, ToggleRow] = {}

        self.setWindowTitle(f"Import {path.name}")
        self.resize(*tokens.IMPORT_SIZE)
        outer = vbox(self, (0, tokens.SPACE_5, 0, tokens.SPACE_5), tokens.SPACE_3)
        head = vbox(spacing=tokens.SPACE_2)
        head.setContentsMargins(tokens.SPACE_5, 0, tokens.SPACE_5, 0)
        t = QLabel(f"Import {path.name}")
        t.setObjectName("DialogTitle")
        head.addWidget(t)
        outer.addLayout(head)

        body = QWidget()
        lay = vbox(body, (tokens.SPACE_5, 0, tokens.SPACE_5 - tokens.SCROLL_GUTTER, 0), tokens.SPACE_3)

        # which column is which
        self.columns = Disclosure("Columns", is_open=False, first=True)
        self.col_pickers: dict[str, object] = {}
        choices = [(NONE, "Not in This Sheet", "")] + [
            (str(i), label, "") for i, label in enumerate(self.layout_guess.labels)
        ]
        grid = None
        for n, (key, label) in enumerate(importer.FIELDS):
            if n % 2 == 0:
                grid = hbox(spacing=tokens.SPACE_2)
                self.columns.add(grid)
            sec = Section(label)
            c = combo(choices, str(self.layout_guess.cols[key]) if key in self.layout_guess.cols else NONE)
            c.currentIndexChanged.connect(lambda _i: self.reread())
            sec.add(c)
            grid.addWidget(sec, 1)
            self.col_pickers[key] = c
        if len(importer.FIELDS) % 2:
            grid.addStretch(1)
        lay.addWidget(self.columns)

        # options
        self.options = Disclosure("Options", is_open=True)
        self.attach = ToggleRow("Attach Gear Made for Other Gear", True)
        self.attach.setToolTip('"Tilta Cage for Sony FX6" goes with the FX6')
        self.attach.toggled.connect(lambda _on: self.reread())
        self.options.add(self.attach)
        self.tidy = ToggleRow("Tidy Up Group Names", True)
        self.tidy.setToolTip("SD Cards becomes Media, 1000c becomes Lights")
        self.tidy.toggled.connect(lambda _on: self.reread())
        self.options.add(self.tidy)
        self.use_pricing = ToggleRow(
            "Use the Sheet's Pricing", not has_profile
        )  # never replaces yours unasked
        self.use_pricing.setToolTip(
            "Your profile's day-rate percent and tax become the sheet's"
            if has_profile
            else "Your profile starts with the sheet's day-rate percent and tax"
        )
        self.use_pricing.toggled.connect(lambda _on: self._summary())
        self.options.add(self.use_pricing)
        self.guess = ToggleRow("Fill In the Company From the Name", True)
        self.guess.setToolTip('"Aputure STORM 80c" gets Aputure')
        self.guess.toggled.connect(lambda _on: self.reread())
        self.options.add(self.guess)
        known_links = {
            (i.name.casefold(), i.department.casefold())
            for i in importer.parse_rows(rows, self.layout_guess, guess_brands=False).items
            if i.link
        } & have
        self.links = ToggleRow(
            f"Add the Sheet's Links to {len(known_links)} Piece{'s' if len(known_links) != 1 else ''} You Have",
            True,
        )
        self.links.setToolTip("Only where a piece has no link yet")
        self.links.setVisible(bool(known_links))
        self.options.add(self.links)
        # what a blank means, when the sheet leaves some blank (shown only then): today's defaults, chosen
        self.blank_rent = ToggleRow("A Blank Rent? Means For Rent", True)
        self.blank_rent.setToolTip("Off: gear the sheet doesn't say about stays off rentals")
        self.blank_rent.toggled.connect(lambda _on: self.reread())
        self.options.add(self.blank_rent)
        self.blank_qty = ToggleRow("Bring In Pieces With No Quantity, as 1", True)
        self.blank_qty.setToolTip("Off: rows with no quantity are left out")
        self.blank_qty.toggled.connect(lambda _on: self.reread())
        self.options.add(self.blank_qty)
        self.total_note = QLabel()  # the sheet's own total, checked against what was read
        self.total_note.setObjectName("Hint")
        self.total_note.setWordWrap(True)
        self.options.add(self.total_note)
        self.filled = QLabel()  # what the sheet left blank, filled in
        self.filled.setObjectName("Hint")
        self.filled.setWordWrap(True)
        self.options.add(self.filled)
        self.skip_have = ToggleRow("Skip What's Already in Bodega", True)
        self.skip_have.setToolTip("Same name in the same department")
        self.skip_have.toggled.connect(lambda _on: self.fill())
        self.skip_have.setVisible(bool(have))
        self.options.add(self.skip_have)
        lay.addWidget(self.options)

        # departments
        self.deps = Disclosure("Departments", is_open=True)
        self.deps_box = QWidget()
        self.deps_lay = vbox(self.deps_box, 0, 0)
        self.deps.add(self.deps_box)
        lay.addWidget(self.deps)

        # the pieces
        sec = Section("Gear")
        self.list = QListWidget()
        self.list.setObjectName("Picker")
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.setTextElideMode(Qt.TextElideMode.ElideRight)  # names: cut at the end
        self.list.setMinimumHeight(tokens.IMPORT_LIST_H)
        self.list.itemChanged.connect(self._ticked)
        sec.add(self.list)
        row = hbox(spacing=tokens.SPACE_2)
        all_on = QPushButton("Select All")
        all_on.setObjectName("Ghost")
        all_on.clicked.connect(lambda: self._tick_all(True))
        all_off = QPushButton("Untick All")
        all_off.setObjectName("Ghost")
        all_off.clicked.connect(lambda: self._tick_all(False))
        row.addWidget(all_on)
        row.addWidget(all_off)
        row.addStretch(1)
        sec.add(row)
        lay.addWidget(sec)
        lay.addStretch(1)

        scroll = FitScroll()
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        buttons = hbox(spacing=tokens.SPACE_2)
        buttons.setContentsMargins(tokens.SPACE_5, tokens.SPACE_4, tokens.SPACE_5, 0)
        self.count = QLabel()
        self.count.setObjectName("Muted")
        buttons.addWidget(self.count, 1)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        self.go = QPushButton("Import")
        self.go.setObjectName("Primary")
        self.go.setDefault(True)
        self.go.clicked.connect(self._done)
        buttons.addWidget(cancel)
        buttons.addWidget(self.go)
        outer.addLayout(buttons)
        self.reread()

    # ------------------------------------------------------------------ reading
    def _layout(self) -> importer.Layout:
        cols = {}
        for key, c in self.col_pickers.items():
            v = c.currentData()
            if v and v != NONE:
                cols[key] = int(v)
        return importer.Layout(self.layout_guess.head, cols, self.layout_guess.labels)

    def reread(self) -> None:
        """Read the sheet again with the columns and options as they are now."""
        layout = self._layout()
        self.got = importer.parse_rows(
            self.rows,
            layout,
            guess_brands=self.guess.isChecked(),
            blank_rent=self.blank_rent.isChecked(),
            no_qty="one" if self.blank_qty.isChecked() else "skip",
        )
        if self.attach.isChecked():
            self.got.attached = importer.attach_guesses(self.got.items)
        if self.tidy.isChecked():
            from bodega.core import tidy

            by_id = {i.id: i for i in self.got.items}
            for item_id, group in tidy.suggest(by_id).items():
                by_id[item_id].group = group
        bits = [f"{money.fmt_rate(self.got.rate_pct)} of value a day"] if self.got.rate_pct else []
        if self.got.value_tax:
            bits.append(f"{money.fmt_rate(self.got.value_tax)} tax")
        self.use_pricing.setText(
            "Use the Sheet's Pricing: " + ", ".join(bits) if bits else "Use the Sheet's Pricing"
        )
        self.use_pricing.setVisible(bool(bits))
        self._has_pricing = bool(bits)
        g = self.got
        said = [
            f"{n:,} with {what}" for n, what in (
                (g.assumed_qty, "no quantity count as 1"),
                (g.skipped_qty, "no quantity are left out"),
                (g.assumed_rent, f"no Rent? are {'for rent' if self.blank_rent.isChecked() else 'not for rent'}"),
                (g.guessed_brand, "no company got one from the name"),
            ) if n
        ]  # fmt: skip
        check = importer.total_check(g)
        self.total_note.setText(check)
        self.total_note.setVisible(bool(check))
        self.blank_rent.setVisible(bool(g.assumed_rent))
        self.blank_qty.setVisible(bool(g.assumed_qty or g.skipped_qty))
        self.filled.setText("Filled in for you: " + "; ".join(said) + "." if said else "")
        self.filled.setVisible(bool(said))
        names = [label for key, label in importer.FIELDS if key in layout.cols]
        self.columns.set_summary(
            " · ".join(names[:5]) + (" …" if len(names) > 5 else "") if names else "Pick the Name column"
        )
        self._fill_departments()
        self.fill()

    def _fill_departments(self) -> None:
        counts: dict[str, int] = {}
        for it in self.got.items:
            counts[it.department or "No Department"] = (
                counts.get(it.department or "No Department", 0) + it.qty
            )
        was = {d: t.isChecked() for d, t in self.dep_toggles.items()}
        for t in self.dep_toggles.values():
            t.setParent(None)
            t.deleteLater()
        self.dep_toggles = {}
        for dep, n in counts.items():
            t = ToggleRow(f"{dep}  ·  {n:,} piece{'s' if n != 1 else ''}", was.get(dep, True))
            t.toggled.connect(lambda _on: self.fill())
            self.deps_lay.addWidget(t)
            self.dep_toggles[dep] = t
        self.deps.setVisible(bool(counts))
        self.deps.set_summary(f"{len(counts)} found")

    def _key(self, it: Item) -> tuple[str, str, str]:
        return (it.department, it.group, it.name)

    def _shown(self) -> list[Item]:
        out = []
        for it in self.got.items:
            t = self.dep_toggles.get(it.department or "No Department")
            if t is not None and not t.isChecked():
                continue
            if self.skip_have.isChecked() and (it.name.casefold(), it.department.casefold()) in self.have:
                continue
            out.append(it)
        return out

    def fill(self) -> None:
        by_id = {i.id: i for i in self.got.items}
        self.list.blockSignals(True)
        self.list.clear()
        for it in self._shown():
            bits = [f"{it.qty} ×" if it.qty > 1 else "", it.name]
            text = "  ".join(b for b in bits if b)
            meta = " · ".join(x for x in (it.department, it.group) if x)
            if it.value:
                meta += f"  ·  {money.fmt(money.parse(it.value))}"
            parent = by_id.get(it.parent)
            if parent is not None:
                text = "    ↳ " + text
                meta += f"  ·  on {parent.name}"
            row = QListWidgetItem(f"{text}      {meta}")
            row.setToolTip(theme.plain_tip(f"{it.name}\n{meta}"))
            row.setFlags(
                Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsSelectable
            )
            row.setCheckState(
                Qt.CheckState.Unchecked if self._key(it) in self._unticked else Qt.CheckState.Checked
            )
            row.setData(REF, it.id)
            self.list.addItem(row)
        self.list.blockSignals(False)
        self._summary()

    def _ticked(self, row: QListWidgetItem) -> None:
        it = next((i for i in self.got.items if i.id == row.data(REF)), None)
        if it is not None:
            if row.checkState() == Qt.CheckState.Checked:
                self._unticked.discard(self._key(it))
            else:
                self._unticked.add(self._key(it))
        self._summary()

    def _tick_all(self, on: bool) -> None:
        for it in self._shown():
            if on:
                self._unticked.discard(self._key(it))
            else:
                self._unticked.add(self._key(it))
        self.fill()

    def chosen(self) -> list[Item]:
        keep = [it for it in self._shown() if self._key(it) not in self._unticked]
        return keep

    def _summary(self) -> None:
        keep = self.chosen()
        pieces = sum(i.qty for i in keep)
        attached = sum(1 for i in keep if i.parent)
        found = len(self.got.items)
        if not found:
            self.count.setText("No gear found. Check which column is the Name under Columns.")
        else:
            self.count.setText(
                f"{len(keep):,} of {words.count(found, 'item')}, {words.count(pieces, 'piece')}"
                + (f", {attached} attached to other gear" if attached else "")
            )
        self.go.setText(f"Import {len(keep)} Item{'s' if len(keep) != 1 else ''}" if keep else "Import")
        self.go.setEnabled(bool(keep))

    def _done(self) -> None:
        self.items = self.chosen()
        self.fill_links = not self.links.isHidden() and self.links.isChecked()
        if self._has_pricing and self.use_pricing.isChecked():
            self.pricing = (self.got.rate_pct, self.got.value_tax)
        self.accept()

    def pick_column(self, field: str, column: int | None) -> None:
        """For tests: point a field at a column (None: not in this sheet)."""
        set_combo(self.col_pickers[field], NONE if column is None else str(column))
        self.reread()
