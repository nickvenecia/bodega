"""The AI helpers in the window: the assistant, its jobs, the Review window and applying what you approve.

A part of MainWindow (see main_window.py); it uses the window's widgets and the library."""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtWidgets import QDialog

from bodega.core import words
from bodega.core.model import Item
from bodega.services.ai import tasks
from bodega.services.ai.providers import Setup
from bodega.ui.components.worker import Worker
from bodega.ui.dialogs.ai_review import ReviewDialog
from bodega.ui.panels.assistant import JOBS, AssistantPanel
from bodega.ui.style import tokens
from bodega.ui.window.common import kind_of

RUNS = {
    "links": tasks.update_from_links,
    "find": tasks.find_links,
    "names": tasks.tidy_names,
    "groups": tasks.organize_groups,  # also takes your groups (added when it starts)
}


class AIMixin:
    assistant: AssistantPanel

    def _build_assistant(self) -> AssistantPanel:
        """The assistant panel (made once, with the window; it shares the right-hand glass with the details)."""
        a = AssistantPanel()
        a.job_wanted.connect(lambda key: self.ai_job(key))
        a.setup_wanted.connect(self.open_ai_setup)
        a.close_wanted.connect(self.close_assistant)
        a.changes_found.connect(lambda result: self._ai_review("Suggested Changes", result, in_chat=True))
        a.apply_wanted.connect(lambda changes: self._ai_apply(changes, in_chat=True))
        a.name_of = lambda item_id: self.lib.items[item_id].name if item_id in self.lib.items else "A piece"
        a.ask_job = self._ai_question
        return a

    def ai_setup(self) -> Setup:
        return Setup.from_settings(self.lib.settings)

    def open_ai_setup(self) -> None:
        self.open_settings("ai")

    def assistant_showing(self) -> bool:
        return self.inspector.currentWidget() is self.assistant and self.dock.opened

    def toggle_assistant(self) -> None:
        if self.assistant_showing():
            self.close_assistant()
        else:
            self.open_ai_assistant()

    def close_assistant(self) -> None:
        self.dock.set_open(False)

    def open_ai_assistant(self, job: str = "", items: list[Item] | None = None) -> None:
        self.flush()
        self._drop_fresh()
        self._ai_state()
        self.inspector.setCurrentWidget(self.assistant)
        self.dock.set_open(True)
        if job:
            self.ai_job(job, items)
        else:
            self.assistant.question.setFocus()

    def _ai_question(self):
        """What a question needs, gathered now on the window's thread: (question) -> answer, to run later."""
        setup = self.ai_setup()
        items = [replace(it) for it in self.lib.ordered_items()]
        lookup = {it.id: it for it in items}
        groups = self.lib.groups()
        return lambda q: tasks.chat(setup, q, items, lookup, groups)

    def _ai_scope(self) -> tuple[list[Item], str]:
        """The gear the jobs work on: what's in view (a group, or all gear)."""
        group = self._grp() if kind_of(self.view_key) == "gear" else ""
        items = [it for it in self.lib.ordered_items() if not group or it.group == group]
        n = len(items)
        return items, f"On {group or 'All Gear'}: {n} piece{'s' if n != 1 else ''}."

    def _ai_state(self) -> None:
        setup = self.ai_setup()
        self.assistant.show_setup(setup, self._ai_scope()[1], self._model_name(setup))

    def _model_name(self, setup: Setup) -> str:
        """The model's name as the provider's list gave it (kept by AI Settings), or "" (never its id)."""
        kept = self.lib.settings.get("ai_models")
        if not isinstance(kept, dict) or kept.get("provider") != setup.provider:
            return ""
        for row in kept.get("models", []):
            if isinstance(row, list) and len(row) == 2 and row[0] == setup.model and row[1] != row[0]:
                return str(row[1])
        return ""

    def ai_job(self, key: str, items: list[Item] | None = None) -> None:
        setup = self.ai_setup()
        if not setup.ready() and key != "links":  # links' prices work without an AI; the rest need one
            self.open_ai_setup()
            setup = self.ai_setup()
            if not setup.ready():
                return
        if not self.assistant_showing():
            self.open_ai_assistant()
        if self.assistant.running():
            return
        self.flush()
        chosen = items if items is not None else self._ai_scope()[0]
        if not self._may_ask(key, chosen, setup):
            return
        copies = [replace(it) for it in chosen]  # the job reads its own copies while you keep working
        run = RUNS[key]
        title = dict((k, label) for k, label, _t in JOBS)[key]
        use = setup if setup.ready() else None
        if key == "groups":
            groups = self.lib.groups()
            w = Worker(lambda progress, cancel: run(use, copies, groups, progress, cancel), self)
        else:
            w = Worker(lambda progress, cancel: run(use, copies, progress, cancel), self)
        w.done.connect(lambda result: self._ai_review(title, result))
        w.failed.connect(lambda e: self.assistant.say("Bodega", e, "problem"))
        self.assistant.start(w, f"{title}…")

    def _may_ask(self, key: str, chosen: list[Item], setup) -> bool:
        """A job that may ask your AI more than a few questions says how many first (each one is billed)."""
        from bodega.ui.dialogs.common import confirm

        n = tasks.calls_for(key, chosen, setup.ready())
        if n < tokens.AI_ASK_ABOVE:
            return True
        who = setup.p.label if setup.p else "Your provider"
        return confirm(
            self,
            f"Ask Your AI Up to {n:,} Times?",
            f"{who} bills your account for each question. To cap what any job can cost, set a spending limit "
            f"in your account there.",
            "Ask",
            danger=False,
        )

    def ai_this_piece(self, item_id: str) -> None:
        """⋯ › Update with AI on a piece: its link if it has one, else find one."""
        it = self.lib.items.get(item_id)
        if it is not None:
            self.open_ai_assistant("links" if it.link.strip() else "find", [it])

    def _ai_review(self, title: str, result: tasks.Result, in_chat: bool = False) -> None:
        if not result.changes:
            msg = result.problems[0] if result.problems else "Everything already looks right."
            self.assistant.say("Bodega", f"{title}: {msg}")
            return
        names = {it.id: it.name for it in self.lib.items.values()}
        d = ReviewDialog(title, result, names, self)
        if d.exec() != QDialog.DialogCode.Accepted:
            if in_chat:
                self.assistant.nothing_changed()
            return
        self._ai_apply(d.chosen(), in_chat)

    def _ai_apply(self, changes: list, in_chat: bool = False) -> None:
        """Make the changes you said yes to (a safety copy first), and say so: in the chat, if they were asked
        for there, else as a toast."""
        self.flush()
        n = tasks.apply(self.lib, changes)
        if self.items.it is not None:
            self.items.load(self.items.it)
        self.refresh()
        if in_chat:
            self.assistant.changes_made(n)  # said on its card, in the conversation
        else:
            self.toast(f"Changed {words.count(n, 'thing')}. A safety copy of how things were is kept.", "done")
