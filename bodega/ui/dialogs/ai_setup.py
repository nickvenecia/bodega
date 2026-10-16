"""Settings › AI: pick a provider, paste your key (it goes in the keychain), pick a model from its live list. Grouped
rows (the standard's §4.12, G.12), and every change is kept as it's made: there's no Save.

The key checks itself (the standard's §14.10): pasted, or typed and left to rest, or on leaving the field, it's kept
in the keychain (unless it plainly can't be right, which is said without sending anything) and tried once against
the provider's list of models; a ✓ or ! sits beside it and the line under the rows says what came back ("Key works ·
12 models"). There's no Test button. The models show by the names the provider gives them, the list is kept for the
day and a ↻ asks again.
"""

from __future__ import annotations

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QComboBox, QLineEdit, QWidget

from bodega.core import dates, errors, settings, words
from bodega.core.store import Library
from bodega.services import secrets
from bodega.services.ai import providers, usage
from bodega.services.ai.providers import PROVIDERS, Setup
from bodega.ui.components.rows import Group
from bodega.ui.components.widgets import (
    COUNT_TYPED,
    IconLabel,
    circle_button,
    combo,
    hbox,
    hint,
    only,
    sized,
    status_line,
    vbox,
)
from bodega.ui.components.worker import Worker
from bodega.ui.dialogs.update import open_url
from bodega.ui.style import tokens
from bodega.ui.style.tokens import SPACE_2, SPACE_3

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


class AISettings(QWidget):
    """Settings' AI section. `changed` once something is kept (the window shows the Assistant ready, or not)."""

    changed = Signal()

    def __init__(self, lib: Library, parent: QWidget | None = None):
        super().__init__(parent)
        self.lib = lib
        self._worker: Worker | None = None
        self._loading = True
        start = Setup.from_settings(lib.settings)
        lay = vbox(self, 0, tokens.GROUP_GAP)

        g = Group("Provider")
        self.provider = sized(
            combo([(p.key, p.label, "") for p in PROVIDERS.values()], start.provider or "anthropic"), "popup"
        )
        g.control("Provider", self.provider)
        self.provider.currentIndexChanged.connect(lambda _i: self._provider_changed())
        self.address = sized(QLineEdit(start.base_url), "name")
        self.address.setPlaceholderText("https://…/v1")
        self.address.setToolTip("Or http://localhost:11434/v1 for a model on this computer")
        g.control("Address", self.address)
        self.address_row = self.address.parentWidget()
        self.address.editingFinished.connect(self._apply)
        self.get_key = g.action("Get a Key ↗", lambda: open_url(self._p().keys_page))
        lay.addWidget(g)

        g = Group("API Key")
        box = QWidget()
        row = hbox(box, 0, SPACE_2)
        self.key = sized(QLineEdit(), "name")
        self.key.setEchoMode(QLineEdit.EchoMode.Password)  # always hidden: a key is pasted, not remembered
        self.key.setAccessibleName("API Key")
        row.addWidget(self.key)
        self.key_mark = IconLabel("", "GOOD", tokens.ICON)  # ✓ or ! once it's been tried
        row.addWidget(self.key_mark)
        g.control("Key", box)
        self.forget = g.action("Remove Key", self._remove_key, danger=True)
        lay.addWidget(g)
        self._key_rest = QTimer(self, singleShot=True, interval=tokens.KEY_CHECK_MS, timeout=self._check_key)
        self.key.textEdited.connect(lambda _t: self._key_rest.start())  # pasted, or typed and left to rest
        self.key.editingFinished.connect(self._check_now)

        g = Group("Model")
        box = QWidget()
        row = hbox(box, 0, SPACE_2)
        self.model = sized(QComboBox(), "name")
        self.model.setEditable(True)  # a model the list doesn't show can be typed
        self.model.lineEdit().setPlaceholderText("Pick one, or type a model's name")
        self.model.setAccessibleName("Model")
        if start.model:
            self.model.addItem(start.model, start.model)
        row.addWidget(self.model)
        self.load = circle_button("retry", "Ask for the List Again")
        self.load.clicked.connect(self._load_models)
        row.addWidget(self.load)
        g.control("Model", box)
        self.model.activated.connect(lambda _i: self._apply())
        self.model.lineEdit().editingFinished.connect(self._apply)
        lay.addWidget(g)

        g = Group("Daily Limit", "A warning at 80% of it, and no more questions that day at 100%.")
        self.limit = sized(only(QLineEdit(str(settings.value(lib.settings, "ai_daily_limit"))), COUNT_TYPED), "short")
        self.limit.setPlaceholderText("None")
        self.limit.setToolTip("Questions to your AI a day; blank or 0: no limit")
        g.control("Questions a Day", self.limit)
        self.limit.editingFinished.connect(self._apply)
        self.usage = g.value("Asked", usage.METER.summary())  # what's been asked, today and this month
        lay.addWidget(g)

        notes = QWidget()
        nl = vbox(notes, (tokens.GROUP_INSET, 0, tokens.GROUP_INSET, 0), SPACE_3)
        self.status = status_line()
        nl.addWidget(self.status)
        for words_ in (SENT, BILLED):  # what goes out and what it costs: footnotes, under the rows
            nl.addWidget(hint(words_))
        lay.addWidget(notes)
        self._provider_changed(first=True)
        self._models_for_today()
        self._loading = False

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
        self.address_row.setVisible(p.key == "custom")
        self.get_key.setText(f"Get a Key from {p.label} ↗")
        self.get_key.parentWidget().setVisible(bool(p.keys_page))
        self.key.clear()
        self.key.setPlaceholderText(
            "Saved in your keychain"
            if saved
            else ("Paste your key (if it needs one)" if not p.needs_key else "Paste your key")
        )
        self.forget.parentWidget().setVisible(saved)
        self.key_mark.set_icon("")
        if not first:
            self.model.clear()
            self.status.setText("")
            self._apply()  # (the provider is kept as it's picked)
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
        """Keep the key in the keychain, then try it once against the provider's list of models (which fills the
        Model list too). One that plainly can't be right is said, and neither kept nor sent."""
        key = self._typed_key()
        if key is None:
            return
        problem = providers.key_problem(self._p().key, key)
        if problem:  # said without sending anything
            self.key_mark.set_tone("WARN")
            self.key_mark.set_icon("alert")
            self.status.setText(problem)
            return
        try:
            providers.save_key(self._p().key, key)
        except OSError as e:
            self.status.setText(errors.plain(e, "save the key"))
            return
        self.forget.parentWidget().setVisible(True)
        self.changed.emit()
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

    def _apply(self) -> None:
        """Keep what's picked as it's picked: the provider, its address, the model and the daily limit (the key is
        kept as it's checked). An address that can't be used is said, and the one before stays."""
        if self._loading:
            return
        if self._p().key == "custom" and self.address.text().strip():
            try:
                providers.check_address(self.address.text())
            except OSError as e:
                self.status.setText(errors.plain(e, "use that address"))
                return
        self._setup().to_settings(self.lib.settings)
        typed = self.limit.text().strip()
        self.lib.settings["ai_daily_limit"] = int(typed) if typed.isdigit() else 0
        usage.METER.set_limit(self.lib.settings["ai_daily_limit"])  # from the next question on
        self.usage.set_full_text(usage.METER.summary())
        self.lib.save_settings()
        self.changed.emit()
