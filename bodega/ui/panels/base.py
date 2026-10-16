"""What the details panels (gear, kit, rental) share on top of components.panels.SidePanel: an empty state,
fold-away groups (kits and rentals), and remembering which groups are open."""

from __future__ import annotations

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QLabel, QPushButton, QWidget

from bodega.ui.components.panels import SidePanel
from bodega.ui.components.widgets import Disclosure, hbox, primary_button, vbox
from bodega.ui.style import theme, tokens


class DetailsBase(SidePanel):
    """A piece, kit or rental on the right: the SidePanel frame (with ⋯), plus an empty state, a form of
    fold-away groups, and remembering which groups are open."""

    groups_changed = Signal(str, dict)  # panel key, {"group": open?}

    KEY = ""
    TITLE = ""
    GROUPS: dict[str, tuple[str, bool]] = {}

    def __init__(self, parent: QWidget | None = None):
        super().__init__(self.TITLE, more=True, parent=parent)
        self._loading = False
        self.more.setToolTip("Duplicate, delete")
        self.header_buttons: list[QWidget] = [self.more]
        self.more.hide()

        self.empty = QWidget()
        el = vbox(self.empty, (0, tokens.SPACE_5, 0, 0), tokens.SPACE_3)
        self.empty_title = QLabel()
        self.empty_title.setObjectName("EmptyTitle")
        self.empty_title.setWordWrap(True)
        self.empty_text = QLabel()
        self.empty_text.setObjectName("EmptyText")
        self.empty_text.setWordWrap(True)
        self.empty_btn = primary_button()
        self.empty_btn2 = QPushButton()
        row = hbox()
        row.addWidget(self.empty_btn)
        row.addWidget(self.empty_btn2)
        row.addStretch(1)
        el.addWidget(self.empty_title)
        el.addWidget(self.empty_text)
        el.addLayout(row)
        self.lay.addWidget(self.empty)
        self._actions = (None, None)
        self.empty_btn.clicked.connect(lambda: self._actions[0] and self._actions[0]())
        self.empty_btn2.clicked.connect(lambda: self._actions[1] and self._actions[1]())

        self.form = QWidget()
        self.form_lay = vbox(self.form, 0, tokens.SPACE_3)
        self.lay.addWidget(self.form)
        self.groups: dict[str, Disclosure] = {}
        for key, (title, is_open) in self.GROUPS.items():
            d = Disclosure(title, is_open, first=not self.groups)
            d.toggled.connect(lambda _on: self.groups_changed.emit(self.KEY, self.open_groups()))
            self.groups[key] = d
            self.form_lay.addWidget(d)
        self.lay.addStretch(1)

    def show_empty(self, title: str, text: str, action: str, slot, action2: str = "", slot2=None) -> None:
        self.form.hide()
        self.empty.show()
        self.empty_title.setText(title)
        self.empty_text.setText(text)
        self.empty_btn.setText(action)
        self.empty_btn2.setText(action2)
        self.empty_btn2.setVisible(bool(action2))
        self._actions = (slot, slot2)
        for b in self.header_buttons:
            b.hide()
        self.footer.hide()

    def show_form(self) -> None:
        self.empty.hide()
        self.form.show()
        for b in self.header_buttons:
            b.show()
        self.footer.setVisible(self.footer_lay.count() > 0)

    def menu_action(self, icon: str, text: str, slot):
        """A command under the header's ⋯ (Duplicate, Delete…). Returns its QAction (None for "-")."""
        if text == "-":
            self.more_menu.addSeparator()
            return None
        return self.more_menu.addAction(theme.menu_icon(icon), text, lambda: self.later(slot))

    def header_button(self, text: str, primary: bool = False) -> QPushButton:
        """A button in the panel's header (Agreement…, Rent This), shown only while something is open."""
        b = primary_button(text) if primary else QPushButton(text)
        self.header.actions.addWidget(b)
        self.header_buttons.append(b)
        b.hide()
        return b

    def open_groups(self) -> dict[str, bool]:
        return {k: d.is_open() for k, d in self.groups.items()}

    def set_open_groups(self, state: dict) -> None:
        for k, d in self.groups.items():
            if isinstance(state.get(k), bool):
                d.set_open(state[k])

    def later(self, fn) -> None:
        QTimer.singleShot(0, self, fn)
