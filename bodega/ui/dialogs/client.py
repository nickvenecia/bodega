"""A saved renter: who you rent to. Filled in once, then picked on every rental after that. A new one is made in a
sheet; one you have is edited in place, on the Renters page (panels/renter.py embeds this same form there, with
Cancel and Save Changes under it)."""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtWidgets import QDialog, QLabel, QLineEdit, QPushButton, QWidget

from bodega.core.model import Client
from bodega.ui.components import sheet
from bodega.ui.components.address import AddressFields
from bodega.ui.components.widgets import (
    Embeddable,
    Guarded,
    ReturnMovesOn,
    Section,
    TextBox,
    hbox,
    primary_button,
    sized,
    vbox,
)
from bodega.ui.style.tokens import DIALOG_W_WIDE, SPACE_2, SPACE_3, SPACE_4, SPACE_5, TEXT_BOX_H


class ClientDialog(Guarded, Embeddable, QDialog):
    """Add or edit a renter. After Save, `.client` holds the result; `.deleted` if Delete was chosen."""

    def __init__(self, client: Client | None, can_delete: bool, parent: QWidget | None = None):
        super().__init__(parent)
        sheet.prepare(self)  # shown over its window (components/sheet.py)
        self.editing = client is not None
        self.client = replace(client) if client else Client()
        self.deleted = False
        title_text = "Edit Renter" if self.editing else "New Renter"
        self.setWindowTitle(title_text)
        self.setMinimumWidth(DIALOG_W_WIDE)
        lay = vbox(self, SPACE_5, SPACE_3)
        self.title_label = title = QLabel(title_text)
        title.setObjectName("DialogTitle")
        lay.addWidget(title)
        c = self.client
        row = hbox(spacing=SPACE_2)
        self.name = self._line(row, "Name", c.name, "Who signs the agreement")
        self.company = self._line(row, "Company", c.company, "Production company (optional)")
        lay.addLayout(row)
        row = hbox(spacing=SPACE_2)
        self.email = self._line(row, "Email", c.email, "Where the agreement goes")
        self.phone = self._line(row, "Phone", c.phone, "")
        lay.addLayout(row)
        self.address = AddressFields(c)
        lay.addWidget(self.address)
        sec = Section("Notes")
        self.notes = TextBox("ID checked, insurance on file until…", TEXT_BOX_H)
        self.notes.set_text(c.notes)
        self.notes.setToolTip("Just for you: never printed")
        sec.add(self.notes)
        lay.addWidget(sec)
        lay.addStretch(1)
        buttons = hbox(spacing=SPACE_2)
        buttons.setContentsMargins(0, SPACE_4 - SPACE_3, 0, 0)
        if self.editing and can_delete:
            delete = QPushButton("Delete Renter")  # (at once, with Undo: nothing more to ask)
            delete.setObjectName("Danger")
            delete.clicked.connect(self._delete)
            buttons.addWidget(delete)
        buttons.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        self.save = primary_button("Save")
        self.save.setDefault(True)
        self.save.clicked.connect(self._save)
        ReturnMovesOn(self, self.save)
        buttons.addWidget(cancel)
        buttons.addWidget(self.save)
        lay.addLayout(buttons)
        for f in (self.name, self.company, self.email, self.phone):
            f.textChanged.connect(self._check)
        for box in (self.address, self.notes):
            box.edited.connect(self._check)
        self.settled()
        self._check()

    def embed(self) -> None:
        """In the Renters page's panel: no title of its own (the panel's is), Cancel and Save Changes stay."""
        super().embed()
        self.setMinimumWidth(0)  # (the panel's width)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.save.setText("Save Changes")

    def form_values(self) -> object:
        return self._draft()

    def _line(self, row, label: str, value: str, placeholder: str) -> QLineEdit:
        sec = Section(label)
        f = sized(QLineEdit(value), "name")  # (a name, an email or a phone: the standard's C-90)
        f.setPlaceholderText(placeholder)
        sec.add(f)
        row.addWidget(sec, 1)
        return f

    def _check(self, *_a) -> None:
        named = bool(self.name.text().strip() or self.company.text().strip())
        self.save.setEnabled(named and (not self.editing or self.unsaved()))

    def _draft(self) -> Client:
        c = replace(
            self.client,
            name=self.name.text().strip(),
            company=self.company.text().strip(),
            email=self.email.text().strip(),
            phone=self.phone.text().strip(),
            notes=self.notes.text().strip(),
        )
        self.address.put_in(c)
        return c

    def _save(self) -> None:
        self.client = self._draft()
        self.accept()

    def _delete(self) -> None:
        """Deleted at once (the window says so, with Undo: the standard's 4.19). Rentals keep their own copy."""
        self.deleted = True
        self.accept()
