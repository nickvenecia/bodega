"""Settings, your account, feedback, updates, and light or dark.

A part of MainWindow (see main_window.py); it uses the window's widgets and the library."""

from __future__ import annotations

import time

from bodega import __version__
from bodega.core import update
from bodega.ui.style import theme


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
                "Thanks! Sent."
                if d.sent_now
                else "Thanks! It's saved and goes out once sending is switched on."
            )

    def _auto_check_updates(self) -> None:
        if not self.lib.settings.get("auto_update", True) or update.install_kind() == "source":
            return
        last = float(self.lib.settings.get("last_update_check", 0) or 0)
        if time.time() - last < update.CHECK_EVERY_S:
            return
        self.check_updates(quiet=True)

    def check_updates(self, quiet: bool = False) -> None:
        from bodega.ui.dialogs.update import CheckThread

        self._check = CheckThread(self)
        self._check.found.connect(lambda rel: self._found_release(rel, quiet))
        self._check.failed.connect(
            lambda _m: (
                None if quiet else self.toast("Couldn't reach GitHub. Check your internet and try again.")
            )
        )
        self._check.start()

    def _found_release(self, rel: update.Release, quiet: bool) -> None:
        self.lib.settings["last_update_check"] = time.time()
        if rel.newer:
            self._release = rel
            self.sidebar.btn_update.setText(f"Update to {rel.version}")
            self.sidebar.btn_update.show()
            if not quiet:
                self.show_update()
        elif not quiet:
            self.toast(f"You have the newest Bodega ({__version__}).")

    def show_update(self) -> None:
        if self._release is None:
            return
        from bodega.ui.dialogs.update import UpdateDialog, restart_into

        d = UpdateDialog(self._release, parent=self)
        if d.exec() == UpdateDialog.DialogCode.Accepted and d.plan is not None:
            self.shutdown()
            restart_into(d.plan)

    def set_look(self, appearance: str) -> None:
        """Light, Dark, or Match the System."""
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
