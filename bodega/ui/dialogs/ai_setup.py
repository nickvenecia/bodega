"""AI setup: pick a provider, paste your key (it goes in the keychain), pick a model from its live list.

The key checks itself (the standard's §14.10): pasted, or typed and left to rest, or on leaving the field, it's tried
once against the provider's list of models; a ✓ or ! sits beside it and the line under the form says what came
back ("Key works · 12 models"). A key that plainly can't be right is said without sending anything. There's no Test
button. The models show by the names the provider gives them, the list is kept for the day and a ↻ asks again.
"""

from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QComboBox, QDialog, QLabel, QLineEdit, QPushButton, QWidget

from bodega.core import dates, errors, settings, words
from bodega.core.store import Library
from bodega.services import secrets
from bodega.services.ai import providers, usage
from bodega.services.ai.providers import PROVIDERS, Setup
from bodega.ui.components import sheet
from bodega.ui.components.widgets import (
    COUNT_TYPED,
    Embeddable,
    IconLabel,
    Section,
    button_row,
    circle_button,
    combo,
    hbox,
    hint,
    only,
    primary_button,
    sized,
    status_line,
    vbox,
)
from bodega.ui.components.worker import Worker
from bodega.ui.dialogs.update import open_url
from bodega.ui.style import tokens
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
        sheet.prepare(self)  # shown over its window (components/sheet.py)
        self.lib = lib
        self.setWindowTitle("AI")
        self.setMinimumWidth(DIALOG_W_WIDE)
        self._worker: Worker | None = None
        start = Setup.from_settings(lib.settings)
        lay = vbox(self, SPACE_5, SPACE_3)
        self.title_label = QLabel("AI")
        self.title_label.setObjectName("DialogTitle")
        lay.addWidget(self.title_label)

        sec = Section("Provider")
        row = hbox(spacing=SPACE_2)
        self.provider = combo([(p.key, p.label, "") for p in PROVIDERS.values()], start.provider or "anthropic")
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
        self.address.setPlaceholderText("https://…/v1   (or http://localhost:11434/v1 for a model on this computer)")
        self.address_sec.add(self.address)
        lay.addWidget(self.address_sec)

        sec = Section("API Key")
        row = hbox(spacing=SPACE_2)
        self.key = QLineEdit()
        self.key.setEchoMode(QLineEdit.EchoMode.Password)  # always hidden: a key is pasted, not remembered
        row.addWidget(self.key, 1)
        self.key_mark = IconLabel("", "GOOD", tokens.ICON)  # ✓ or ! once it's been tried
        row.addWidget(self.key_mark)
        sec.add(row)
        lay.addWidget(sec)
        self._key_rest = QTimer(self, singleShot=True, interval=tokens.KEY_CHECK_MS, timeout=self._check_key)
        self.key.textEdited.connect(lambda _t: self._key_rest.start())  # pasted, or typed and left to rest
        self.key.editingFinished.connect(self._check_now)

        sec = Section("Model")
        row = hbox(spacing=SPACE_2)
        self.model = QComboBox()
        self.model.setEditable(True)  # a model the list doesn't show can be typed
        self.model.lineEdit().setPlaceholderText("Pick one, or type a model's name")
        if start.model:
            self.model.addItem(start.model, start.model)
        row.addWidget(self.model, 1)
        self.load = circle_button("retry", "Ask for the List Again")
        self.load.clicked.connect(self._load_models)
        row.addWidget(self.load)
        sec.add(row)
        lay.addWidget(sec)

        sec = Section("Daily Limit")  # the standard's quota: a warning at 80%, a stop at 100%
        row = hbox(spacing=SPACE_2)
        self.limit = sized(only(QLineEdit(str(settings.value(lib.settings, "ai_daily_limit"))), COUNT_TYPED), "short")
        self.limit.setPlaceholderText("None")
        self.limit.setToolTip("Questions to your AI a day; blank or 0: no limit")
        self.limit.setAccessibleName("Daily Limit, Questions")
        row.addWidget(self.limit)
        row.addWidget(hint("questions a day"))
        row.addStretch(1)
        sec.add(row)
        self.usage = hint(usage.METER.summary())  # what's been asked, today and this month
        sec.add(self.usage)
        lay.addWidget(sec)

        self.forget = QPushButton("Remove Key")  # a red row at the form's foot
        self.forget.setObjectName("Danger")
        self.forget.clicked.connect(self._remove_key)
        lay.addWidget(self.forget)

        self.status = status_line()
        lay.addWidget(self.status)
        for words_ in (SENT, BILLED):  # what goes out and what it costs: footnotes, under the form
            note = hint(words_)
            note.setWordWrap(True)
            lay.addWidget(note)

        buttons = button_row()
        self.cancel_btn = cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        save = primary_button("Save")
        save.setDefault(True)
        save.clicked.connect(self._save)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        lay.addLayout(buttons)
        self._provider_changed(first=True)
        self._models_for_today()

    # What's picked
    def _p(self) -> providers.Provider:
        return PROVIDERS[self.provider.currentData()]

    def _model_id(self) -> str:
        """The picked model's id (the list shows names), or what was typed."""
        typed = self.model.currentText().strip()
        i = self.model.currentIndex()
        if i >= 0 and self.model.itemText(i) == typed and self.model.itemData(i):
            return str(self.model.itemData(i))
        return typed

    def _setup(self) -> Setup:
        return Setup(self._p().key, self._model_id(), self.address.text().strip())

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
        self.key_mark.set_icon("")
        if not first:
            self.model.clear()
            self.status.setText("")
            self._models_for_today()
        if not secrets.available():
            self.status.setText("This computer has no keychain, so Bodega can't keep a key safely.")

    # Actions
    def _run(self, job, done, busy: str, failed=None) -> None:
        if self._worker is not None and self._worker.isRunning():
            return
        self.status.setText(busy)
        self.load.setEnabled(False)
        w = Worker(job, self)
        w.done.connect(done)
        w.failed.connect(failed or self.status.setText)
        w.finished.connect(lambda: self.load.setEnabled(True))
        self._worker = w
        w.start()

    def _check_now(self) -> None:
        if self._key_rest.isActive():
            self._key_rest.stop()
            self._check_key()

    def _check_key(self) -> None:
        """Try the key once against the provider's list of models (which fills the Model list too)."""
        key = self._typed_key()
        if key is None:
            return
        problem = providers.key_problem(self._p().key, key)
        if problem:  # said without sending anything
            self.key_mark.set_tone("WARN")
            self.key_mark.set_icon("alert")
            self.status.setText(problem)
            return
        self._load_models(checking=True)

    def _models_for_today(self) -> None:
        """The list from today, kept; else, with a key saved, asked for now (in the background)."""
        kept = settings.value(self.lib.settings, "ai_models")
        p = self._p()
        if isinstance(kept, dict) and kept.get("provider") == p.key and kept.get("day") == dates.iso(dates.today()):
            rows = [tuple(r) for r in kept.get("models", []) if isinstance(r, list) and len(r) == 2]
            self._show_models([(str(a), str(b)) for a, b in rows], quiet=True)
        elif providers.key_for(p.key) or not p.needs_key:
            self._load_models(quiet=True)

    def _show_models(self, models: list[tuple[str, str]], quiet: bool = False) -> bool:
        """Fill the list by name; the model you had stays picked, and is never swapped for another without asking."""
        current = self._model_id()
        self.model.clear()
        for mid, name in models:
            self.model.addItem(name, mid)
        ids = [mid for mid, _name in models]
        if current in ids:
            self.model.setCurrentIndex(ids.index(current))
            return True
        if current:
            self.model.setEditText(current)
            if models and not quiet:  # kept, never swapped silently for another (and billed differently)
                self.status.setText(f"{current} isn't offered for this key any more. Pick another.")
                return False
        return True

    def _load_models(self, checking: bool = False, quiet: bool = False) -> None:
        setup, key, p = self._setup(), self._typed_key(), self._p()

        def shown(models) -> None:
            pairs = [(m, m) if isinstance(m, str) else (str(m[0]), str(m[1])) for m in models]
            self.lib.settings["ai_models"] = {
                "provider": p.key,
                "day": dates.iso(dates.today()),
                "models": [list(x) for x in pairs],
            }
            if checking or key:
                self.key_mark.set_tone("GOOD")
                self.key_mark.set_icon("check")
            kept = self._show_models(pairs)
            if kept:
                n = len(pairs)
                self.status.setText(
                    (f"Key works · {words.count(n, 'model')}" if checking or key else words.count(n, "model"))
                    if n
                    else "No models came back for this key."
                )

        def failed(message: str) -> None:
            if checking or key:
                self.key_mark.set_tone("WARN")
                self.key_mark.set_icon("alert")
            self.status.setText(message)

        self._run(
            lambda _p, _c: providers.named_models(setup, key=key),
            shown,
            "Trying the key…" if checking else ("" if quiet else "Asking for the list…"),
            failed,
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
        typed = self.limit.text().strip()
        self.lib.settings["ai_daily_limit"] = int(typed) if typed.isdigit() else 0
        usage.METER.set_limit(self.lib.settings["ai_daily_limit"])  # from the next question on
        self.usage.setText(usage.METER.summary())
        self.lib.save_settings()
        if self.embedded:
            self._provider_changed(first=True)
            self.status.setText("Saved.")
        self.accept()
