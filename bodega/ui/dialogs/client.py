"""A saved renter: who you rent to. Filled in once, then picked on every rental after that."""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtWidgets import QDialog, QLabel, QLineEdit, QPushButton, QWidget

from bodega.core.model import Client
from bodega.ui.components.widgets import Guarded, ReturnMovesOn, Section, TextBox, hbox, primary_button, vbox
from bodega.ui.style.tokens import DIALOG_W_WIDE, SPACE_2, SPACE_3, SPACE_4, SPACE_5, TEXT_BOX_H


class ClientDialog(Guarded, QDialog):
    """Add or edit a renter. After Save, `.client` holds the result; `.deleted` if Delete was chosen."""

    def __init__(self, client: Client | None, can_delete: bool, parent: QWidget | None = None):
        super().__init__(parent)
        self.editing = client is not None
        self.client = replace(client) if client else Client()
        self.deleted = False
        title_text = "Edit Renter" if self.editing else "New Renter"
        self.setWindowTitle(title_text)
        self.setMinimumWidth(DIALOG_W_WIDE)
        lay = vbox(self, SPACE_5, SPACE_3)
        title = QLabel(title_text)
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
        sec = Section("Address")
        self.address = TextBox("Street\nCity, State ZIP")
        self.address.set_text(c.address)
        sec.add(self.address)
        lay.addWidget(sec)
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

    def form_values(self) -> object:
        return self._draft()

    def _line(self, row, label: str, value: str, placeholder: str) -> QLineEdit:
        sec = Section(label)
        f = QLineEdit(value)
        f.setPlaceholderText(placeholder)
        sec.add(f)
        row.addWidget(sec, 1)
        return f

    def _check(self, *_a) -> None:
        named = bool(self.name.text().strip() or self.company.text().strip())
        self.save.setEnabled(named and (not self.editing or self.unsaved()))

    def _draft(self) -> Client:
        return replace(
            self.client,
            name=self.name.text().strip(),
            company=self.company.text().strip(),
            email=self.email.text().strip(),
            phone=self.phone.text().strip(),
            address=self.address.text().strip(),
            notes=self.notes.text().strip(),
        )

    def _save(self) -> None:
        self.client = self._draft()
        self.accept()

    def _delete(self) -> None:
        """Deleted at once (the window says so, with Undo: the standard's 4.19). Rentals keep their own copy."""
        self.deleted = True
        self.accept()
