"""AI setup: pick a provider, paste your key (it goes in the keychain), pick a model from its live list."""

from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QDialog, QLabel, QLineEdit, QPushButton, QWidget

from bodega.core import errors
from bodega.core.store import Library
from bodega.services import secrets
from bodega.services.ai import providers
from bodega.services.ai.providers import PROVIDERS, Setup
from bodega.ui.components.widgets import (
    Embeddable,
    Section,
    button_row,
    combo,
    hbox,
    hint,
    primary_button,
    set_combo,
    status_line,
    vbox,
)
from bodega.ui.components.worker import Worker
from bodega.ui.dialogs.update import open_url
from bodega.ui.style.tokens import DIALOG_W_WIDE, SPACE_2, SPACE_3, SPACE_5

SENT = (
    "Bodega uses your own AI account; its key is kept in this computer's keychain. When you use AI, it sends "
    "the gear you ask about (up to 600 pieces at a time): each piece's name, company, series, group, quantity, "
    "status, what you paid and what goes with what, and the words of any page it reads. Renters and rentals are "
    "never sent."
)
BILLED = (
    "Your provider bills you for every question and keeps what's sent under its own terms (some free plans use "
    "it to train their AI). Set a spending limit in your account there. The AI only suggests: nothing changes "
    "until you approve it, and it can be wrong."
)


class AISetupDialog(Embeddable, QDialog):
    def __init__(self, lib: Library, parent: QWidget | None = None):
        super().__init__(parent)
        self.lib = lib
        self.setWindowTitle("AI")
        self.setMinimumWidth(DIALOG_W_WIDE)
        self._worker: Worker | None = None
        start = Setup.from_settings(lib.settings)
        lay = vbox(self, SPACE_5, SPACE_3)
        self.title_label = QLabel("AI")
        self.title_label.setObjectName("DialogTitle")
        lay.addWidget(self.title_label)
        lay.addWidget(hint(SENT))
        lay.addWidget(hint(BILLED))

        sec = Section("Provider")
        row = hbox(spacing=SPACE_2)
        self.provider = combo(
            [(p.key, p.label, "") for p in PROVIDERS.values()], start.provider or "anthropic"
        )
        self.provider.currentIndexChanged.connect(lambda _i: self._provider_changed())
        row.addWidget(self.provider, 1)
        self.get_key = QPushButton("Get Key ↗")
        self.get_key.setObjectName("LinkBtn")
        self.get_key.clicked.connect(lambda: open_url(self._p().keys_page))
        row.addWidget(self.get_key)
        sec.add(row)
        lay.addWidget(sec)

        self.address_sec = Section("Address")
        self.address = QLineEdit(start.base_url)
        self.address.setPlaceholderText(
            "https://…/v1   (or http://localhost:11434/v1 for a model on this computer)"
        )
        self.address_sec.add(self.address)
        lay.addWidget(self.address_sec)

        sec = Section("API Key")
        row = hbox(spacing=SPACE_2)
        self.key = QLineEdit()
        self.key.setEchoMode(QLineEdit.EchoMode.Password)
        row.addWidget(self.key, 1)
        self.forget = QPushButton("Remove")
        self.forget.clicked.connect(self._remove_key)
        row.addWidget(self.forget)
        sec.add(row)
        lay.addWidget(sec)

        sec = Section("Model")
        row = hbox(spacing=SPACE_2)
        self.model = QComboBox()
        self.model.setEditable(True)  # a model the list doesn't show can be typed
        self.model.lineEdit().setPlaceholderText("Load the list, or type a model name")
        if start.model:
            self.model.addItem(start.model)
        row.addWidget(self.model, 1)
        self.load = QPushButton("Load Models")
        self.load.clicked.connect(self._load_models)
        row.addWidget(self.load)
        sec.add(row)
        lay.addWidget(sec)

        self.status = status_line()
        lay.addWidget(self.status)

        buttons = button_row()
        self.test = QPushButton("Test")
        self.test.clicked.connect(self._test)
        self.cancel_btn = cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        save = primary_button("Save")
        save.setDefault(True)
        save.clicked.connect(self._save)
        buttons.insertWidget(0, self.test)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        lay.addLayout(buttons)
        self._provider_changed(first=True)

    # ------------------------------------------------------------------ what's picked
    def _p(self) -> providers.Provider:
        return PROVIDERS[self.provider.currentData()]

    def _setup(self) -> Setup:
        return Setup(self._p().key, self.model.currentText().strip(), self.address.text().strip())

    def _typed_key(self) -> str | None:
        """The key in the box, or None to use the saved one."""
        return self.key.text().strip() or None

    def _provider_changed(self, first: bool = False) -> None:
        p = self._p()
        saved = bool(providers.key_for(p.key))
        self.address_sec.setVisible(p.key == "custom")
        self.get_key.setVisible(bool(p.keys_page))
        self.key.clear()
        self.key.setPlaceholderText(
            "Saved in your keychain"
            if saved
            else ("Paste your key (if it needs one)" if not p.needs_key else "Paste your key")
        )
        self.forget.setVisible(saved)
        if not first:
            self.model.clear()
            self.status.setText("")
        if not secrets.available():
            self.status.setText("This computer has no keychain, so Bodega can't keep a key safely.")

    # ------------------------------------------------------------------ actions
    def _run(self, job, done, busy: str) -> None:
        if self._worker is not None and self._worker.isRunning():
            return
        self.status.setText(busy)
        for b in (self.load, self.test):
            b.setEnabled(False)
        w = Worker(job, self)
        w.done.connect(done)
        w.failed.connect(self.status.setText)
        w.finished.connect(lambda: [b.setEnabled(True) for b in (self.load, self.test)])
        self._worker = w
        w.start()

    def _load_models(self) -> None:
        setup, key = self._setup(), self._typed_key()

        def shown(models: list[str]) -> None:
            current = self.model.currentText().strip()
            self.model.clear()
            self.model.addItems(models)
            if current in models:
                set_combo(self.model, current)
                self.model.setCurrentText(current)
            elif current and models:  # kept, never swapped silently for another (and billed differently)
                self.model.setCurrentText(current)
                self.status.setText(f"{current} isn't offered for this key any more. Pick another.")
                return
            self.status.setText(f"{len(models)} models." if models else "No models came back for this key.")

        self._run(lambda _p, _c: providers.list_models(setup, key=key), shown, "Asking for the list…")

    def _test(self) -> None:
        setup, key = self._setup(), self._typed_key()  # a typed key is tried without being saved
        self._run(
            lambda _p, _c: providers.ask(setup, "Reply with the single word OK.", "Are you there?", key=key),
            lambda _answer: self.status.setText("It works: the model answered."),
            "Asking it something small…",
        )

    def _remove_key(self) -> None:
        providers.save_key(self._p().key, "")
        self._provider_changed()
        self.status.setText("Key removed from your keychain.")

    def _save(self) -> None:
        key = self._typed_key()
        try:
            if self._p().key == "custom":
                providers.check_address(self.address.text())  # first: nothing is saved for a bad address
            if key:
                providers.save_key(self._p().key, key)
        except OSError as e:
            self.status.setText(errors.plain(e, "save the key"))
            return
        self._setup().to_settings(self.lib.settings)
        self.lib.save_settings()
        if self.embedded:
            self._provider_changed(first=True)
            self.status.setText("Saved.")
        self.accept()
