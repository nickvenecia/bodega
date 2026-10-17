"""Settings (⌘,): one window with a glass sidebar of sections, like the Mac's System Settings.

    General             Appearance; updates
    Profiles            your profiles (name, logo, pricing, terms), edited right here
    AI                  provider, key (in the keychain), model
    Account             sign in or out
    Keyboard Shortcuts  every key, read from the menus
    Your Data           the folder, Back Up

Everything is edited inside its section, so Settings never opens a window on top of itself. Things that aren't
settings (Send Feedback, About) have their own windows.
"""

from __future__ import annotations

import os

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QDialog, QLabel, QLineEdit, QPushButton, QStackedWidget, QWidget

from bodega import version_label
from bodega.core import backups, dates, errors, settings
from bodega.core.paths import data_dir
from bodega.core.store import Library
from bodega.services import account
from bodega.ui.components import access, sheet
from bodega.ui.components.glass import GlassRoot
from bodega.ui.components.panels import LeftPanel
from bodega.ui.components.rows import Group
from bodega.ui.components.widgets import (
    AccentPicker,
    FitScroll,
    SearchField,
    Segmented,
    Toast,
    combo,
    hbox,
    set_combo,
    sized,
    vbox,
)
from bodega.ui.style import theme, tokens

LOOKS = [("system", "Match System"), ("light", "Light"), ("dark", "Dark")]
FINDS = {  # what each section holds, for Settings' search (with its name)
    "general": "look appearance light dark accent color text size larger bigger zoom updates check automatically",
    "profiles": "profile business name logo email phone address pricing day rate percent tax week weekend deposit "
    "numbers prefix next number paper terms agreement note currency",
    "ai": "ai assistant provider key model anthropic openai gemini claude",
    "account": "account sign in sign out email password",
    "shortcuts": "keyboard shortcuts keys single letters voice speech",
    "data": "data folder backup back up restore safety copies renters details log import export spreadsheet csv "
    "google sheets",
}
PANES = [
    ("account", "Account", "key"),  # first, as the standard's account card (shown once accounts exist)
    ("general", "General", "cog"),
    ("profiles", "Profiles", "user"),
    ("ai", "AI", "assistant"),
    ("shortcuts", "Keyboard Shortcuts", "keyboard"),
    ("data", "Your Data", "box"),
]


class SettingsDialog(QDialog):
    SHEET_KIND = "window"  # (the standard's window over the app)

    def __init__(
        self,
        lib: Library,
        window,
        pane: str = "general",
        profile: str | None = None,
        add_profile: bool = False,
        for_rental: bool = False,
        parent: QWidget | None = None,
    ):
        super().__init__(parent or window)
        sheet.prepare(self)  # shown over its window (components/sheet.py)
        self.lib = lib
        self.win = window
        self.setWindowTitle("Settings")
        self.resize(*tokens.SETTINGS_SIZE)
        self.setMinimumSize(*tokens.SETTINGS_MIN)
        self._profile_id = profile
        self._for_rental = for_rental
        self._adding = add_profile or not lib.businesses

        outer = vbox(self, 0, 0)
        root = GlassRoot()
        outer.addWidget(root)
        gap = tokens.GLASS_GAP
        body = hbox(root, gap, gap)
        self.side = side = LeftPanel(tokens.SETTINGS_SIDE_W)
        root.float(side)
        self.find = SearchField()  # narrows the sections: "logo" leaves Profiles
        self.find.setPlaceholderText("Search")
        self.find.setAccessibleName("Search Settings")
        self.find.addAction(theme.icon("search", theme.FAINT), QLineEdit.ActionPosition.LeadingPosition)
        self.find.textChanged.connect(self._find)
        self.find.returnPressed.connect(self._found)
        side.lay.addWidget(self.find)
        for key, label, icon in PANES:
            side.add_row(key, label, icon, foldable=False).clicked.connect(self.show_pane)
        side.lay.addStretch(1)
        self.rows = side.rows
        body.addWidget(side)

        self.stack = QStackedWidget()
        body.addWidget(self.stack, 1)
        # its own messages, over its sections: Settings sits on top of the window, so the window's can't be reached
        self.toaster = Toast(self, lambda: self.stack.geometry())
        self.panes: dict[str, QWidget] = {}
        for key, label, _icon in PANES:
            page = QWidget()
            lay = vbox(page, (tokens.SPACE_4, tokens.SPACE_4, tokens.SPACE_4, 0), tokens.SPACE_3)
            title = QLabel(label)
            title.setObjectName("PageTitle")
            lay.addWidget(title)
            holder = QWidget()
            vbox(holder, 0, 0)
            lay.addWidget(holder, 1)
            self.stack.addWidget(page)
            self.panes[key] = holder
        self._build_general()
        self._build_profiles()
        self._build_ai()
        self._build_account()
        self._build_shortcuts()
        self._build_data()
        # Account shows once there's an account service to sign in to (until then nothing could sign in)
        self._account_shown = account.service().connected or account.current() is not None
        self.rows["account"].setVisible(self._account_shown)
        shown = pane in self.panes and not self.rows[pane].isHidden()
        self.show_pane(pane if shown else "general")

    # Moving around
    def _then(self, run) -> None:
        """Settings closes first, then `run` opens its own window (one window at a time)."""
        if self._profile_may_go():
            self.accept()
            QTimer.singleShot(0, self.win, run)

    def _find(self, text: str) -> None:
        """Only the sections that hold what's typed (by their names and what's in them)."""
        from bodega.core import search

        wanted = search.words(text)
        for key, label, _icon in PANES:
            if key == "account" and not self._account_shown:
                continue
            hay = search.folded(f"{label} {FINDS.get(key, '')}")
            self.rows[key].setVisible(search.matches(hay, wanted))

    def _found(self) -> None:
        """Return in the search: the first section left."""
        first = next((k for k, _l, _i in PANES if not self.rows[k].isHidden()), None)
        if first is not None:
            self.show_pane(first)
            self.rows[first].setFocus()

    def showEvent(self, e):
        super().showEvent(e)
        row = self.rows.get(self.current_pane())
        if row is not None:  # the keyboard starts on the section shown, never on an invisible scroll area
            row.setFocus()

    def show_pane(self, key: str) -> None:
        self.side.select(key)
        self.stack.setCurrentIndex([k for k, _l, _i in PANES].index(key))
        self.setWindowTitle(dict((k, label) for k, label, _i in PANES)[key])

    def current_pane(self) -> str:
        return PANES[self.stack.currentIndex()][0]

    def _fill(self, key: str, w: QWidget, scroll: bool = True) -> None:
        """Put `w` in a section (replacing what was there)."""
        holder = self.panes[key]
        lay = holder.layout()
        while lay.count():
            old = lay.takeAt(0).widget()
            if old is not None:
                # hidden first, while it's whole, so the focus leaves it now: a form thrown away while it shows
                # with the focus in it (on a Mac, the field you typed in) crashes Bodega as it goes
                old.hide()
                old.deleteLater()
        inner = w
        if scroll:
            area = FitScroll()
            area.setWidget(w)
            w = area
        lay.addWidget(w)
        inner.show()  # (an embedded dialog starts hidden)

    @staticmethod
    def _column() -> tuple[QWidget, object]:
        w = QWidget()
        lay = vbox(w, (0, 0, tokens.SPACE_3, tokens.SPACE_4), tokens.GROUP_GAP)  # (groups of rows: G.12)
        return w, lay

    # General
    def _build_general(self) -> None:
        w, lay = self._column()
        look = Group()  # (its first row says what it is)
        self.look = look.control("Appearance", Segmented(LOOKS))
        self.look.set_value(settings.value(self.lib.settings, "appearance"))
        self.look.changed.connect(self.win.set_look)
        self.accent = look.control("Accent Color", AccentPicker(settings.value(self.lib.settings, "accent")))
        self.accent.picked.connect(self.win.set_accent)
        lay.addWidget(look)
        size = Group("Text Size", "The whole window grows with it: words, rows and buttons.")
        system = round(access.system_text_scale() * 100)
        choices = [("0", f"Match System ({system}%)", "")] + [(str(n), f"{n}%", "") for n in access.TEXT_SIZES]
        self.text_size = size.control(
            "Text Size", sized(combo(choices, str(settings.value(self.lib.settings, "text_size"))), "popup")
        )
        self.text_size.currentIndexChanged.connect(lambda _i: self._text_size())
        self.restart = size.action("Restart Bodega to Use It", self._restart)
        self._text_size(save=False)
        lay.addWidget(size)
        upd = Group("Updates")
        self.auto = upd.switch("Check for Updates Automatically", settings.value(self.lib.settings, "auto_update"))
        self.auto.toggled.connect(self._auto)
        upd.value("Version", version_label())
        upd.action("Check for Updates…", lambda: self._then(self.win.check_updates))
        lay.addWidget(upd)
        lay.addStretch(1)
        self._fill("general", w)

    def _restart(self) -> None:
        from bodega.app import restart

        self._then(restart)

    def _text_size(self, save: bool = True) -> None:
        """Kept as it's picked; it shows from the next time Bodega opens (Restart offers that now)."""
        chosen = int(self.text_size.currentData() or 0)
        if save:
            self.lib.settings["text_size"] = chosen
            self.lib.save_settings()
        now = float(os.environ.get("QT_SCALE_FACTOR") or 1)
        self.restart.parentWidget().setVisible(abs(access.text_scale(chosen) - now) > 0.01)

    def _auto(self, on: bool) -> None:
        self.lib.settings["auto_update"] = on
        self.lib.save_settings()

    # Profiles
    def _build_profiles(self) -> None:
        from bodega.ui.dialogs.profile import ProfileDialog

        lib = self.lib
        w = QWidget()
        lay = vbox(w, 0, tokens.SPACE_2)
        if lib.businesses:
            row = hbox(spacing=tokens.SPACE_2)
            pick = self._profile_id if self._profile_id in lib.businesses else None
            if pick is None and not self._adding:
                b = self.win.business()
                pick = b.id if b is not None else None
            choices = [(b.id, b.name or "Unnamed Profile", "") for b in lib.businesses.values()]
            if self._adding:
                choices.append(("", "New Profile", ""))
            self._showing = "" if self._adding else (pick or "")
            self.profile_pick = combo(choices, self._showing)
            self.profile_pick.activated.connect(lambda _i: self._pick_profile())
            row.addWidget(self.profile_pick, 1)
            add = QPushButton("Add Profile")
            add.setEnabled(not self._adding)
            add.clicked.connect(self._add_profile)
            row.addWidget(add)
            row.setContentsMargins(0, 0, tokens.SPACE_3, 0)
            lay.addLayout(row)
        else:
            self.profile_pick = None
            pick = None
        current, start, can_delete = self.win.profile_start(None if self._adding else pick)
        d = ProfileDialog(
            start,
            can_delete,
            w,
            new=current is None,
            next_for=lambda prefix: lib.number_after(prefix, dates.today().year),
        )
        d.embed()
        d.layout().setContentsMargins(0, tokens.SPACE_2, 0, tokens.SPACE_4)
        d.side_margin(0)
        d.save.setText("Add Profile" if current is None else "Save Changes")
        d.accepted.connect(lambda: self._profile_done(d, current))
        lay.addWidget(d, 1)
        d.show()
        self.profile_editor = d
        self._fill("profiles", w, scroll=False)

    def _profile_may_go(self) -> bool:
        """Changes typed into the profile form are asked about before it's swapped or closed."""
        d = getattr(self, "profile_editor", None)
        return d is None or d.may_leave()

    def reject(self) -> None:
        """Esc: words in the search go first (one layer at a time), then Settings closes."""
        if self.find.text():
            self.find.clear()
            return
        if self._profile_may_go():
            super().reject()

    def _pick_profile(self) -> None:
        key = self.profile_pick.currentData()
        if key == self._showing:
            return
        if not self._profile_may_go():
            set_combo(self.profile_pick, self._showing)
            return
        self._adding = not key
        self._profile_id = key or None
        self._build_profiles()

    def _add_profile(self) -> None:
        if not self._profile_may_go():
            return
        self._adding = True
        self._profile_id = None
        self._build_profiles()

    def _profile_done(self, d, current) -> None:
        saved = self.win.profile_saved(d, current, self._for_rental)
        self._for_rental = False
        self._adding = False
        self._profile_id = saved or None
        self._build_profiles()
        if saved:
            self.toaster.show_message("Profile saved.", "done")
        else:  # deleted at once, with Undo here (the standard's 4.19)
            name = current.name if current is not None and current.name else "the profile"
            self.toaster.show_message(f"Deleted {name}.", "done", action=("Undo", self._undo_delete))

    def _undo_delete(self) -> None:
        self.win.undo()
        self._profile_id = None
        self._build_profiles()

    # AI
    def _build_ai(self) -> None:
        from bodega.ui.dialogs.ai_setup import AISettings

        d = AISettings(self.lib)
        d.layout().setContentsMargins(0, 0, tokens.SPACE_3, tokens.SPACE_4)
        d.layout().addStretch(1)  # packed at the top, like the other sections
        d.changed.connect(self.win._ai_state)  # (kept as it's changed: there's no Save)
        self.ai_editor = d
        self._fill("ai", d)

    # Account
    def _build_account(self) -> None:
        from bodega.ui.dialogs.account import SignInDialog

        who = account.current()
        if "account" in self.rows:  # its row reads who's signed in, the way the standard's account card does
            self.rows["account"].set_label((who.name or who.email) if who else "Sign In")
        if who is not None:
            w, lay = self._column()
            card = Group()
            if who.name:
                card.value("Name", who.name)
            card.value("Signed In As", who.email)
            card.action("Sign Out", self._sign_out)
            lay.addWidget(card)
            lay.addStretch(1)
            self._fill("account", w)
            return
        d = SignInDialog()
        d.embed()
        d.word.hide()
        d.layout().setContentsMargins(0, 0, tokens.SPACE_3, tokens.SPACE_4)
        d.layout().addStretch(1)
        d.accepted.connect(self._signed_in)
        self._fill("account", d)

    def _signed_in(self) -> None:
        self._build_account()
        self.win.sidebar.show_who()

    def _sign_out(self) -> None:
        try:
            account.sign_out()
        except OSError as e:
            self.win.toast(errors.plain(e, "sign out"), "error")
        self._build_account()
        self.win.sidebar.show_who()

    # Shortcuts
    def _build_shortcuts(self) -> None:
        from bodega.ui.dialogs.shortcuts import ShortcutsList

        top = Group("Single Keys", "N, E, D, /, ? and A work alone, outside text fields.")
        self.single = top.switch("Use Single-Key Shortcuts", settings.value(self.lib.settings, "single_keys"))
        self.single.setToolTip("Turn them off if you type by voice")
        self.single.toggled.connect(self._single_keys)
        self._fill("shortcuts", ShortcutsList(self.win.menuBar(), self.win.single_acts, top))

    def _single_keys(self, on: bool) -> None:
        self.lib.settings["single_keys"] = on
        self.lib.save_settings()
        self.win.use_single_keys(on)

    # Your Data
    def _build_data(self) -> None:
        w, lay = self._column()
        where = Group("Saved on This Computer")
        where.value("Folder", str(data_dir()), middle=True)
        where.action("Show Folder", self.win.open_data_folder)
        where.action("Back Up…", lambda: self._then(self.win.back_up))
        restore = where.action("Restore…", lambda: self._then(self.win.restore))
        restore.setToolTip("Put a backup or a safety copy back in place of everything")
        lay.addWidget(where)
        safety = Group("Safety Copies", "Restore… starts with them.")
        safety.value("Each Day You Open Bodega", f"The last {backups.DAILY_KEPT}")
        safety.value("Before an Import, Tidy Up, AI Changes or a Restore", f"The last {backups.CHANGES_KEPT}")
        lay.addWidget(safety)
        come_in = Group("Import")  # (data comes in where data lives: §4.12)
        come_in.action("Import Spreadsheet…", lambda: self._then(self.win.import_sheet))
        come_in.action("Import from Google Sheets…", lambda: self._then(self.win.import_google))
        lay.addWidget(come_in)
        out = Group("Export")
        out.action("Export Gear as CSV…", lambda: self._then(self.win.export_csv))
        out.action("Export Kits as CSV…", lambda: self._then(self.win.export_kits_csv))
        out.action("Export Rentals as CSV…", lambda: self._then(self.win.export_rentals_csv))
        lay.addWidget(out)
        private = Group("Renters' Details", "Turn on FileVault (Mac) or BitLocker (Windows) to keep them safe.")
        private.value("Kept", "On this computer, and in every backup")
        lay.addWidget(private)
        lay.addStretch(1)
        self._fill("data", w)
