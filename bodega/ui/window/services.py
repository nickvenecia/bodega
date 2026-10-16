"""Settings, your account, feedback, updates, and light or dark.

A part of MainWindow (see main_window.py); it uses the window's widgets and the library."""

from __future__ import annotations

import time

from bodega import __version__
from bodega.core import settings, update
from bodega.ui.style import theme, tokens


class ServicesMixin:
    def open_settings(self, pane: str = "general", **kw) -> None:
        """Settings, at a section: general, profiles, ai, account, shortcuts, data."""
        from bodega.ui.dialogs.settings import SettingsDialog

        self.flush()
        SettingsDialog(self.lib, self, pane, **kw).exec()
        self.lib.save_settings()
        self._ai_state()
        self.sidebar.show_who()

    def use_business(self, b_id: str) -> None:
        """Work as another of your profiles (new rentals use it; its pricing shows on gear)."""
        if b_id in self.lib.businesses:
            self.lib.settings["business"] = b_id
            self.lib.save_settings()
            if self.items.it is not None:
                self.items.load(self.items.it)
            self.refresh()
            self.sidebar.show_who()

    def open_account(self) -> None:
        """Sign in or out, in Settings › Account."""
        self.open_settings("account")

    def open_feedback(self) -> None:
        from bodega.ui.dialogs.feedback import FeedbackDialog

        d = FeedbackDialog(self)
        if d.exec():
            self.toast(
                "Feedback sent."
                if d.sent_now
                else "Feedback saved. It goes out once sending is switched on.",
                "done",
            )

    def _auto_check_updates(self) -> None:
        if not settings.value(self.lib.settings, "auto_update") or update.install_kind() == "source":
            return
        self.check_updates(quiet=True)  # every time Bodega opens

    def check_updates(self, quiet: bool = False) -> None:
        """One check at a time: asking again while one runs only makes that one speak up when it's done."""
        from bodega.ui.dialogs.update import CheckThread

        running = getattr(self, "_update_check", None)
        if running is not None:
            running.quiet = running.quiet and quiet
            return
        check = CheckThread(self)
        check.quiet = quiet
        check.found.connect(lambda rel: self._found_release(rel, check.quiet))
        check.failed.connect(lambda m: None if check.quiet else self.toast(m, "problem"))
        check.finished.connect(lambda: setattr(self, "_update_check", None))
        check.finished.connect(check.deleteLater)  # a finished check doesn't stay under the window
        self._update_check = check
        check.start()

    def _found_release(self, rel: update.Release, quiet: bool) -> None:
        self.lib.settings["last_update_check"] = time.time()
        if rel.newer:
            self._release = rel
            self.sidebar.btn_update.setText(f"Update to {rel.version}")
            self.sidebar.btn_update.show()
            if quiet:
                self._offer_update()  # found on its own: say so right away (Later closes it, like any window)
            else:
                self.show_update()
        elif not quiet:
            self.toast(f"You have the newest Bodega ({__version__}).", "done")

    def _offer_update(self) -> None:
        """Show the update window once Bodega is free: never on top of another window or an open menu."""
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication

        busy = QApplication.activeModalWidget() is not None or QApplication.activePopupWidget() is not None
        if busy or not self.isVisible():
            QTimer.singleShot(tokens.UPDATE_WAIT_MS, self._offer_update)
            return
        self.show_update()

    def show_update(self) -> None:
        if self._release is None:
            return
        from bodega.ui.dialogs.update import UpdateDialog, restart_into

        d = UpdateDialog(self._release, parent=self)
        if d.exec() == UpdateDialog.DialogCode.Accepted and d.plan is not None:
            if not self.may_quit():
                return
            self.shutdown()
            restart_into(d.plan)

    def set_look(self, appearance: str) -> None:
        """Light, Dark, or Match System."""
        from PySide6.QtWidgets import QApplication

        from bodega.app import set_appearance

        self.lib.settings["appearance"] = appearance
        set_appearance(QApplication.instance(), appearance)

    def set_accent(self, key: str) -> None:
        """The accent color ("" or Bodega's own blue: the default)."""
        from PySide6.QtWidgets import QApplication

        from bodega.app import set_appearance
        from bodega.ui.style import tokens

        key = "" if key == tokens.APP_ACCENT or key not in tokens.ACCENTS else key
        self.lib.settings["accent"] = key
        self.lib.save_settings()
        app = QApplication.instance()
        set_appearance(app, getattr(app, "_appearance", "system"), key)

    def look_changed(self) -> None:
        """The colors changed: redraw what holds its own."""
        from PySide6.QtWidgets import QApplication

        current = getattr(QApplication.instance(), "_appearance", "system")
        for k, a in getattr(self, "look_actions", {}).items():
            a.setChecked(k == current)
        self.sidebar.word.setText(theme.wordmark())
        self.sidebar.recolor()
        self.assistant.recolor()
        if self.titlebar is not None:
            self.titlebar.word.setText(theme.wordmark())
        self.refresh()
        self.calendar.update()
        self.redraw()
