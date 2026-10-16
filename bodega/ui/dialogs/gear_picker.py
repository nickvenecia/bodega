"""The Add Gear window: search your gear (and packages), tick what you want, Add.

Used to attach gear to a piece, to fill a package and to put gear on a rental. Main gear shows how much
is attached to it, since that comes along too.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QPushButton, QWidget

from bodega.core import money, pricing, search, words
from bodega.core.model import Business
from bodega.core.store import Library
from bodega.ui.components.widgets import SearchField, hbox, hint, primary_button, vbox
from bodega.ui.style import theme, tokens

KIND = Qt.ItemDataRole.UserRole
REF = Qt.ItemDataRole.UserRole + 1
HAY = Qt.ItemDataRole.UserRole + 2


class GearPicker(QDialog):
    """`.picked` after Add: a list of ("item" | "package", id)."""

    def __init__(
        self,
        lib: Library,
        b: Business | None,
        title: str,
        action: str = "Add",
        packages: bool = False,
        exclude: set[str] | None = None,
        main_only: bool = True,
        note: str = "",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.lib = lib
        self.picked: list[tuple[str, str]] = []
        self.setWindowTitle(title)
        self.resize(*tokens.PICKER_SIZE)
        lay = vbox(self, tokens.SPACE_5, tokens.SPACE_3)
        t = QLabel(title)
        t.setObjectName("DialogTitle")
        lay.addWidget(t)
        if note:
            lay.addWidget(hint(note))
        self.search = SearchField()  # (Esc: its words first, then the picker closes)
        self.search.setPlaceholderText("Search")
        self.search.setClearButtonEnabled(True)
        self.search.addAction(theme.icon("search", theme.FAINT), QLineEdit.ActionPosition.LeadingPosition)
        lay.addWidget(self.search)
        self.list = QListWidget()
        self.list.setObjectName("Picker")
        self.list.setUniformItemSizes(False)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.setTextElideMode(Qt.TextElideMode.ElideRight)  # names: cut at the end
        lay.addWidget(self.list, 1)
        row = hbox(spacing=tokens.SPACE_2)
        self.count = QLabel()
        self.count.setObjectName("Muted")
        row.addWidget(self.count, 1)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        self.go = primary_button(action)
        self.go.setDefault(True)
        self.go.clicked.connect(self._done)
        row.addWidget(cancel)
        row.addWidget(self.go)
        lay.addLayout(row)

        cur = (b.currency if b else "$") or "$"
        exclude = exclude or set()
        if packages and lib.packages:
            self._heading("Kits")
            for p in sorted(lib.packages.values(), key=lambda p: p.name.casefold()):
                rate = money.fmt_short(pricing.package_rate(lib, p, b), cur)
                n = sum(u for _i, u, _d in pricing.package_gear(lib, p))
                self._row(
                    "package",
                    p.id,
                    p.name or "Untitled Kit",
                    f"{rate} a day  ·  {words.count(n, 'piece')}",
                    p.name,
                )
        last = None
        for it in lib.ordered_items():
            if it.id in exclude or it.is_retired():
                continue
            attached = bool(it.parent and it.parent in lib.items)
            if main_only and attached:
                continue
            dep = it.group or "No Group"
            if dep != last:
                self._heading(dep)
                last = dep
            bits = []
            kids = len(pricing.with_attached(lib, it, 1)) - 1
            if it.qty > 1:
                bits.append(f"×{it.qty}")
            if it.rentable:
                bits.append(f"{money.fmt_short(pricing.item_rate(lib, it, b), cur)} a day")
            if kids and main_only:
                bits.append(f"+{kids} attached")
            if attached:
                bits.append(f"on {lib.items[it.parent].name}")
            if it.in_repair():
                bits.append("in repair")
            hay = " ".join((it.name, it.brand, it.group, " ".join(it.serials)))
            self._row("item", it.id, it.name or "Untitled Piece", "  ·  ".join(bits), hay)
        self.search.textChanged.connect(self._filter)
        self.list.itemChanged.connect(lambda _i: self._count())
        self.list.itemActivated.connect(self._toggle)
        self._count()
        self.search.setFocus()

    def _heading(self, text: str) -> None:
        it = QListWidgetItem(text)
        it.setFlags(Qt.ItemFlag.NoItemFlags)
        it.setFont(theme.font(tokens.TEXT_SM, tokens.WEIGHT_SEMIBOLD))  # like every section label
        it.setForeground(theme.qcolor(tokens.MUTED))
        it.setData(KIND, "")
        self.list.addItem(it)

    def _row(self, kind: str, ref: str, name: str, meta: str, hay: str) -> None:
        it = QListWidgetItem(f"{name}    {meta}" if meta else name)
        it.setToolTip(name)
        it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsSelectable)
        it.setCheckState(Qt.CheckState.Unchecked)
        it.setData(KIND, kind)
        it.setData(REF, ref)
        it.setData(HAY, search.folded(hay))
        self.list.addItem(it)

    def _toggle(self, it: QListWidgetItem) -> None:
        if it.data(KIND):
            on = it.checkState() == Qt.CheckState.Checked
            it.setCheckState(Qt.CheckState.Unchecked if on else Qt.CheckState.Checked)

    def _filter(self, text: str) -> None:
        words = search.words(text)
        heading = None
        heading_has = False
        for i in range(self.list.count()):
            it = self.list.item(i)
            if not it.data(KIND):
                if heading is not None:
                    heading.setHidden(not heading_has)
                heading, heading_has = it, False
                continue
            hay = it.data(HAY) or ""
            show = all(w in hay for w in words)
            it.setHidden(not show)
            heading_has = heading_has or show
        if heading is not None:
            heading.setHidden(not heading_has)

    def _checked(self) -> list[tuple[str, str]]:
        out = []
        for i in range(self.list.count()):
            it = self.list.item(i)
            if it.data(KIND) and it.checkState() == Qt.CheckState.Checked:
                out.append((it.data(KIND), it.data(REF)))
        return out

    def _count(self) -> None:
        n = len(self._checked())
        self.count.setText(f"{n:,} selected" if n else "")
        self.go.setEnabled(n > 0)

    def _done(self) -> None:
        self.picked = self._checked()
        self.accept()
