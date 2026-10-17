"""A renter on the right of the Renters page (the standard's N-18: every kind of record edits in place on its own
page): the renter's form (dialogs/client.py, the same one a new renter fills in a sheet), with Cancel and Save
Changes under it, then the renter's rentals, newest first (each opens its rental).

Renters are saved only on purpose: nothing typed here is kept until Save Changes, and opening something else
while it's unsaved asks first (Guarded). Saved, the rentals not out the door yet follow (store.save_client)."""

from __future__ import annotations

from dataclasses import replace

import shiboken6
from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QLabel, QPushButton, QWidget

from bodega.core import dates
from bodega.core.model import RENTAL_WORDS, Client
from bodega.core.store import Library
from bodega.ui.components.widgets import Card, vbox
from bodega.ui.dialogs.client import ClientDialog
from bodega.ui.panels.base import DetailsBase
from bodega.ui.style import tokens


class RenterPanel(DetailsBase):
    KEY = "renter"
    TITLE = "Renter"

    saved = Signal(object)  # the renter as you saved it (a Client)
    delete_wanted = Signal(str)  # its id
    open_rental = Signal(str)  # a rental's id, from the renter's list

    def __init__(self, lib: Library, parent: QWidget | None = None):
        super().__init__(parent)
        self.lib = lib
        self.c: Client | None = None
        self.editor: ClientDialog | None = None
        self.capsule.hide()
        self.header_buttons.remove(self.capsule)  # (Delete Renter sits with its form; there's nothing to print)
        self.editor_box = QWidget()
        vbox(self.editor_box, 0, 0)
        self.form_lay.insertWidget(0, self.editor_box)
        self.rentals_card = Card("Rentals")
        self.rentals_box = QWidget()
        self.rentals_lay = vbox(self.rentals_box, 0, tokens.SPACE_1)
        self.rentals_card.add(self.rentals_box)
        self.form_lay.addWidget(self.rentals_card)

    def current_id(self) -> str:
        return self.c.id if self.c is not None else ""

    def may_leave(self) -> bool:
        """Before something else shows here: typing not saved asks Discard Changes / Keep Editing."""
        return self.editor is None or not self.isVisible() or self.editor.may_leave()

    def load(self, c: Client) -> None:
        self.c = c
        old = self.editor
        if old is not None:
            old.hide()  # (hidden first: the field you typed in mustn't keep the focus as it goes)
            old.deleteLater()
        d = ClientDialog(replace(c), True)
        d.embed()
        d.accepted.connect(self._done)
        d.rejected.connect(lambda: self.c is not None and self.load(self.c))  # Cancel: back to as it's saved
        self.editor = d
        self.editor_box.layout().addWidget(d)
        d.show()
        self._show_rentals()
        self.show_form()

    def _done(self) -> None:
        d = self.editor
        if d is None or self.c is None:
            return
        if d.deleted:
            self.delete_wanted.emit(self.c.id)
        else:
            self.saved.emit(d.client)

    def _show_rentals(self) -> None:
        """The renter's rentals, newest first: each says its number, dates and where it stands."""
        while self.rentals_lay.count():
            w = self.rentals_lay.takeAt(0).widget()
            if w is not None:
                w.hide()
                w.deleteLater()
        mine = [r for r in self.lib.rentals.values() if self.c is not None and r.client.id == self.c.id]
        mine.sort(key=lambda r: r.pickup or r.created, reverse=True)
        for r in mine:
            when = dates.span(dates.parse(r.pickup), dates.parse(r.return_date))
            b = QPushButton(" · ".join(x for x in (r.number or "Quote", when, RENTAL_WORDS.get(r.status, "")) if x))
            b.setObjectName("LineRow")
            b.setToolTip("Open this rental")
            b.clicked.connect(lambda _c=False, rid=r.id: self._later(rid))
            self.rentals_lay.addWidget(b)
        if not mine:
            none = QLabel("No rentals yet.")
            none.setObjectName("Muted")
            self.rentals_lay.addWidget(none)
        self.rentals_card.title.setText(f"Rentals · {len(mine)}" if mine else "Rentals")

    def _later(self, rental_id: str) -> None:
        """The rental opens once the click is over (the list it's in is rebuilt as it does)."""
        QTimer.singleShot(0, self, lambda: shiboken6.isValid(self) and self.open_rental.emit(rental_id))
