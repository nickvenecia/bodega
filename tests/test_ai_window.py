"""The AI, account and feedback windows, end to end (a pretend provider, no internet)."""

from __future__ import annotations

import json

import pytest
from PySide6.QtWidgets import QLabel

from bodega.core import sample, web
from bodega.core.store import Library
from bodega.services import account, feedback
from bodega.services.ai import providers
from bodega.services.ai.providers import Setup
from tests.test_ai import FakeKeyring, FakeResponse, anthropic_reply


@pytest.fixture
def keychain(monkeypatch):
    from bodega.services import secrets

    fake = FakeKeyring()
    monkeypatch.setattr(secrets, "_keyring", lambda: fake)
    return fake


@pytest.fixture
def win(qapp, data_folder, keychain):
    from bodega.ui.window.main_window import MainWindow

    w = MainWindow(sample.fill(Library(data_folder).load()))
    w.show()
    yield w
    w.close()


def _wait(worker):
    from PySide6.QtWidgets import QApplication

    worker.wait(5000)
    QApplication.processEvents()
    QApplication.processEvents()


def test_tidy_names_end_to_end(win, monkeypatch):
    from bodega.ui.dialogs import ai_review

    providers.save_key("anthropic", "sk-test")
    Setup("anthropic", "test-model").to_settings(win.lib.settings)
    win.go("grp:Lenses")
    lens = next(i for i in win.lib.items.values() if i.group == "Lenses")
    answer = [{"n": 0, "name": lens.name + " (Tidy)", "brand": lens.brand, "series": "Cine"}]
    monkeypatch.setattr(
        web,
        "open_no_redirect",
        lambda req, timeout, **_k: FakeResponse(json.dumps(anthropic_reply(json.dumps(answer))).encode()),
    )
    picked = {}

    def approve(self):
        picked["n"] = len(self.chosen())
        return ai_review.ReviewDialog.DialogCode.Accepted

    monkeypatch.setattr(ai_review.ReviewDialog, "exec", approve)
    win.open_ai_assistant()
    assert win.assistant.job_buttons["names"].isEnabled()
    assert "Lenses" in win.assistant.scope.text()
    win.ai_job("names", [lens])
    _wait(win.assistant.worker)
    assert picked["n"] >= 1
    assert win.lib.items[lens.id].name.endswith("(Tidy)") and win.lib.items[lens.id].series == "Cine"
    assert list((win.lib.root / "backups").glob("Bodega * before-ai.zip"))


def test_jobs_need_setup_first(win, monkeypatch):
    asked = []
    monkeypatch.setattr(win, "open_settings", lambda pane="general", **_k: asked.append(pane))
    win.ai_job("names")
    assert asked == ["ai"]  # opened Settings › AI instead of running
    assert win.assistant.worker is None


def test_assistant_is_the_right_panel(win):
    win.toggle_assistant()
    assert win.assistant_showing() and win.dock.opened
    win.go("kits")  # it stays while you move around
    assert win.assistant_showing()
    piece = next(iter(win.lib.items))
    win.open("gear", piece)  # a piece takes the panel
    assert win.inspector.currentWidget() is win.items and not win.assistant_showing()
    win.toggle_assistant()  # and the chat comes back
    assert win.assistant_showing()
    win.toggle_assistant()
    assert not win.dock.opened


def test_ai_setup_saves_to_keychain_not_settings(win, keychain):
    from bodega.ui.dialogs.ai_setup import AISetupDialog

    d = AISetupDialog(win.lib, win)
    d.provider.setCurrentIndex(d.provider.findData("kimi"))
    d.key.setText("sk-kimi-abc")
    d.model.setEditText("kimi-model")
    d._save()
    assert providers.key_for("kimi") == "sk-kimi-abc"
    assert win.lib.settings["ai"] == {"provider": "kimi", "model": "kimi-model", "base_url": ""}
    assert "sk-kimi-abc" not in (win.lib.root / "settings.json").read_text(encoding="utf-8")


def test_question_is_answered_as_plain_text(win, monkeypatch):
    providers.save_key("anthropic", "sk-test")
    Setup("anthropic", "test-model").to_settings(win.lib.settings)
    monkeypatch.setattr(
        web,
        "open_no_redirect",
        lambda req, timeout, **_k: FakeResponse(json.dumps(anthropic_reply("<b>Two</b> lenses")).encode()),
    )
    win.open_ai_assistant()
    win.assistant.question.setText("how many lenses?")
    win.assistant._ask()
    _wait(win.assistant.worker)
    shown = win.assistant.log.toPlainText()
    assert "<b>Two</b> lenses" in shown  # shown as typed, not as bold


def test_sign_in_says_accounts_arent_on_yet(win):
    from bodega.ui.dialogs.account import SignInDialog

    d = SignInDialog(win)
    d.email.setText("me@example.com")
    d.password.setText("hunter2")
    d._sign_in()
    assert "aren't switched on" in d.error.text() and d.password.text() == ""
    assert account.current() is None


def test_feedback_waits_in_the_outbox(win, data_folder):
    from bodega.ui.dialogs.feedback import FeedbackDialog

    d = FeedbackDialog(win)
    d.message.set_text("Love it. Could kits have photos?")
    d._send()
    waiting = feedback.waiting()
    assert len(waiting) == 1 and not d.sent_now
    saved = json.loads(waiting[0].read_text(encoding="utf-8"))
    assert saved["message"].startswith("Love it") and saved["details"]["bodega"]


def test_settings_sections_edit_in_place(win, keychain):
    from bodega.ui.dialogs.settings import PANES, SettingsDialog

    d = SettingsDialog(win.lib, win, "ai")
    assert d.current_pane() == "ai" and d.windowTitle() == "AI"
    for key, _label, _icon in PANES:
        d.show_pane(key)
    d.show_pane("ai")
    # AI saves right in its section, no second window
    e = d.ai_editor
    e.provider.setCurrentIndex(e.provider.findData("kimi"))
    e.key.setText("sk-kimi-abc")
    e.model.setEditText("kimi-model")
    e._save()
    assert providers.key_for("kimi") == "sk-kimi-abc" and e.status.text() == "Saved." and e.isVisibleTo(d)
    # a profile, edited in place
    p = d.profile_editor
    p.name.setText("Renamed Rentals")
    p._save()
    assert win.business().name == "Renamed Rentals"
    assert d.profile_editor is not p  # rebuilt with the saved one
    # adding a profile
    d._add_profile()
    d.profile_editor.name.setText("Second Shop")
    d.profile_editor._save()
    assert len(win.lib.businesses) == 2 and win.business().name == "Second Shop"
    d.close()


def test_every_right_panel_fits_a_small_window(win):
    win._restored = True
    win.resize(1100, 700)
    win.open_ai_assistant()
    widths = {win.inspector.widget(i).width() for i in range(win.inspector.count())}
    assert widths == {win.dock.target}  # the assistant shrinks with the others: its ✕ stays inside the glass


def test_a_big_job_says_how_many_questions_first(win, monkeypatch):
    from bodega.ui.dialogs import common
    from bodega.ui.style import tokens

    providers.save_key("anthropic", "sk-test")
    Setup("anthropic", "test-model").to_settings(win.lib.settings)
    asked = []
    monkeypatch.setattr(tokens, "AI_ASK_ABOVE", 1)
    monkeypatch.setattr(common, "confirm", lambda _w, title, *a, **k: asked.append(title) or False)
    sent = []
    monkeypatch.setattr(web, "open_no_redirect", lambda req, timeout, **_k: sent.append(req))
    win.open_ai_assistant()
    win.ai_job("names", list(win.lib.items.values()))
    assert len(asked) == 1 and asked[0].startswith("Ask Your AI Up to")
    assert not sent and not win.assistant.running()  # Cancel: nothing asked, nothing billed


def test_a_model_the_provider_dropped_is_kept_and_said(qapp, data_folder, monkeypatch):
    from bodega.core.store import Library
    from bodega.ui.dialogs.ai_setup import AISetupDialog

    d = AISetupDialog(Library(data_folder).load())
    d.model.setCurrentText("retired-model-1")
    monkeypatch.setattr(
        d, "_run", lambda _job, done, _msg, _failed=None: done([("model-a", "Model A"), ("model-b", "Model B")])
    )
    d._load_models()
    assert d.model.currentText() == "retired-model-1"  # never swapped for another without asking
    assert "isn't offered" in d.status.text()
    d.deleteLater()


def test_a_pasted_key_checks_itself_and_models_show_by_name(qapp, data_folder, keychain, monkeypatch):
    from bodega.services.ai import providers as prov
    from bodega.ui.dialogs.ai_setup import AISetupDialog

    lib = Library(data_folder).load()
    d = AISetupDialog(lib)
    asked = []
    monkeypatch.setattr(prov, "named_models", lambda setup, key=None: asked.append(key) or [("claude-x", "Claude X")])
    d.key.setText("sk-oops")  # (Anthropic's keys start sk-ant-)
    d._check_key()
    assert not asked and "start with sk-ant-" in d.status.text()  # said without sending it
    d.key.setText("sk-ant-good")
    d._check_key()
    _wait(d._worker)
    assert asked == ["sk-ant-good"] and d.status.text() == "Key works · 1 model"
    assert d.model.itemText(0) == "Claude X" and d._setup().model == "claude-x"  # the name shown, the id used
    assert lib.settings["ai_models"]["models"] == [["claude-x", "Claude X"]]  # kept for the day
    d.deleteLater()


def _answers(monkeypatch, text: str) -> None:
    monkeypatch.setattr(
        web,
        "open_no_redirect",
        lambda req, timeout, **_k: FakeResponse(json.dumps(anthropic_reply(text)).encode()),
    )


def test_cancel_in_review_changes_nothing(win, monkeypatch):
    from bodega.ui.dialogs import ai_review

    providers.save_key("anthropic", "sk-test")
    Setup("anthropic", "test-model").to_settings(win.lib.settings)
    lens = next(i for i in win.lib.items.values() if i.group == "Lenses")
    before = lens.name
    _answers(monkeypatch, json.dumps([{"n": 0, "name": before + " (Tidy)", "brand": lens.brand, "series": "Cine"}]))
    monkeypatch.setattr(ai_review.ReviewDialog, "exec", lambda self: ai_review.ReviewDialog.DialogCode.Rejected)
    win.go("grp:Lenses")
    win.open_ai_assistant()
    win.ai_job("names", [lens])
    _wait(win.assistant.worker)
    assert win.lib.items[lens.id].name == before  # Cancel: nothing changed
    assert not list((win.lib.root / "backups").glob("Bodega * before-ai.zip"))  # (and nothing to undo)


def _asked_for_a_change(win, monkeypatch):
    providers.save_key("anthropic", "sk-test")
    Setup("anthropic", "test-model").to_settings(win.lib.settings)
    win.open_ai_assistant()
    _answers(
        monkeypatch,
        json.dumps({"reply": "Moved it.", "changes": [{"n": 0, "field": "group", "value": "Cases"}]}),
    )
    win.assistant.question.setText("put the first piece in a group called Cases")
    win.assistant._ask()
    _wait(win.assistant.worker)
    return win.assistant


def test_a_change_asked_for_in_the_chat_waits_in_a_card(win, monkeypatch):
    a = _asked_for_a_change(win, monkeypatch)
    assert a.card.isVisibleTo(a) and a.card.go.text() == "Change 1 Piece"
    from bodega.ui.components.widgets import widgets_of

    piece, what = widgets_of(a.card.rows)[0].findChildren(QLabel)
    assert what.text() == "Group: Body → Cases" and piece.text()
    assert not a.question.isEnabled() and not a.ask_btn.isEnabled()  # one thing at a time
    assert not any(i.group == "Cases" for i in win.lib.items.values())  # nothing yet
    a.card.go.click()
    assert any(i.group == "Cases" for i in win.lib.items.values())
    assert "Changed 1 thing" in a.log.toPlainText() and a.question.isEnabled()  # said in the chat
    assert list((win.lib.root / "backups").glob("Bodega * before-ai.zip"))


def test_declining_a_change_in_the_chat_changes_nothing(win, monkeypatch):
    a = _asked_for_a_change(win, monkeypatch)
    a.card.decline.click()
    assert not a.card.foot.isVisibleTo(a) and a.card.outcome.text() == "Declined. Nothing changed."  # it says so
    assert not any(i.group == "Cases" for i in win.lib.items.values())


def test_review_from_the_chat_picks_in_the_review_window(win, monkeypatch):
    from bodega.ui.dialogs import ai_review

    a = _asked_for_a_change(win, monkeypatch)
    reviewed = []

    def approve(self):
        reviewed.append([c.new for c in self.chosen()])
        return ai_review.ReviewDialog.DialogCode.Accepted

    monkeypatch.setattr(ai_review.ReviewDialog, "exec", approve)
    a.card.review.click()
    assert reviewed == [["Cases"]] and any(i.group == "Cases" for i in win.lib.items.values())
    assert "Changed 1 thing" in a.log.toPlainText()


def test_the_assistant_header_clears_the_chat_and_offers_settings(win, monkeypatch):
    providers.save_key("anthropic", "sk-test")
    Setup("anthropic", "test-model").to_settings(win.lib.settings)
    _answers(monkeypatch, "Plenty.")
    win.open_ai_assistant()
    a = win.assistant
    a.examples[0].click()  # an example question fills the box, ready to send
    assert a.question.text() == a.examples[0].text() and win.focusWidget() is a.question
    a._ask()
    _wait(a.worker)
    assert not a.log.isHidden() and "Plenty." in a.log.toPlainText()
    a.clear_btn.click()
    assert a.log.isHidden() and not a.hello.isHidden() and a.log.toPlainText() == ""
    opened = []
    a.setup_wanted.disconnect()  # (the window's own opens Settings, which would wait for a click)
    a.setup_wanted.connect(lambda: opened.append(True))
    settings = next(x for x in a.more_menu.actions() if x.text() == "AI Settings…")
    settings.trigger()
    assert opened == [True]


def test_the_message_field_sends_on_return_and_starts_a_line_on_shift_return(win, monkeypatch):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    providers.save_key("anthropic", "sk-test")
    Setup("anthropic", "test-model").to_settings(win.lib.settings)
    _answers(monkeypatch, "Four lenses.")
    win.open_ai_assistant()
    a = win.assistant
    a.question.setText("how many")
    QTest.keyClick(a.question, Qt.Key.Key_Return, Qt.KeyboardModifier.ShiftModifier)
    QTest.keyClicks(a.question, "lenses?")
    assert a.question.text() == "how many\nlenses?" and a.worker is None  # a new line, nothing sent
    QTest.keyClick(a.question, Qt.Key.Key_Return)
    _wait(a.worker)
    assert "Four lenses." in a.chat.text() and a.question.text() == ""


def test_a_message_can_be_copied_edited_and_asked_again(win, monkeypatch):
    from PySide6.QtGui import QGuiApplication

    from bodega.ui.panels.assistant import Message

    providers.save_key("anthropic", "sk-test")
    Setup("anthropic", "test-model").to_settings(win.lib.settings)
    _answers(monkeypatch, "Plenty.")
    win.open_ai_assistant()
    a = win.assistant
    a.question.setText("what's it worth?")
    a._ask()
    _wait(a.worker)
    mine, answer = [m for m in a.chat.parts if isinstance(m, Message)]
    assert mine.kind == "mine" and answer.kind == "answer" and len(answer.actions) == 1  # Copy only, on answers
    answer.copy.click()
    assert QGuiApplication.clipboard().text() == "Plenty."
    mine.edit.click()
    assert a.question.text() == "what's it worth?"  # the words go back in the field
    a.question.setText("")
    mine.again.click()  # Ask Again
    _wait(a.worker)
    assert a.chat.text().count("Plenty.") == 2


def test_esc_leaves_the_assistant_open_while_a_change_waits(win, monkeypatch):
    a = _asked_for_a_change(win, monkeypatch)
    win.escape()
    assert win.assistant_showing() and a.pending is not None
    assert a.question.placeholderText() == "Accept or Decline Above"
    a.card.decline.click()
    win.escape()
    assert not win.dock.opened


def test_the_assistant_names_its_model_as_the_provider_does(win):
    providers.save_key("anthropic", "sk-ant-test")
    Setup("anthropic", "claude-x").to_settings(win.lib.settings)
    win.lib.settings["ai_models"] = {"provider": "anthropic", "day": "2026-10-16", "models": [["claude-x", "Claude X"]]}
    win.open_ai_assistant()
    assert win.assistant.model_line.text() == "Claude X" and win.assistant.model_line.isVisibleTo(win.assistant)
    win.lib.settings["ai_models"] = {}
    win._ai_state()
    assert not win.assistant.model_line.isVisibleTo(win.assistant)  # no name known: never the id
