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

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QStackedWidget, QWidget

from bodega import __version__
from bodega.core import backups, dates, errors
from bodega.core.paths import data_dir
from bodega.core.store import Library
from bodega.services import account
from bodega.ui.components.glass import GlassRoot
from bodega.ui.components.panels import LeftPanel
from bodega.ui.components.widgets import (
    AccentPicker,
    ElidedLabel,
    FitScroll,
    Section,
    Segmented,
    ToggleRow,
    combo,
    hbox,
    hint,
    set_combo,
    vbox,
)
from bodega.ui.style import tokens

LOOKS = [("system", "Match System"), ("light", "Light"), ("dark", "Dark")]
PANES = [
    ("general", "General", "cog"),
    ("profiles", "Profiles", "user"),
    ("ai", "AI", "assistant"),
    ("account", "Account", "key"),
    ("shortcuts", "Keyboard Shortcuts", "keyboard"),
    ("data", "Your Data", "box"),
]


class SettingsDialog(QDialog):
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
        for key, label, icon in PANES:
            side.add_row(key, label, icon, foldable=False).clicked.connect(self.show_pane)
        side.lay.addStretch(1)
        self.rows = side.rows
        body.addWidget(side)

        self.stack = QStackedWidget()
        body.addWidget(self.stack, 1)
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
        self.rows["account"].setVisible(account.service().connected or account.current() is not None)
        shown = pane in self.panes and not self.rows[pane].isHidden()
        self.show_pane(pane if shown else "general")

    # ------------------------------------------------------------------ moving around
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
        lay = vbox(w, (0, 0, tokens.SPACE_3, tokens.SPACE_4), tokens.SPACE_3)
        return w, lay

    def _row(self, text: str, *buttons: QPushButton) -> object:
        row = hbox(spacing=tokens.SPACE_2)
        label = ElidedLabel(text)
        label.setObjectName("Muted")
        row.addWidget(label, 1)
        for b in buttons:
            row.addWidget(b)
        return row

    # ------------------------------------------------------------------ General
    def _build_general(self) -> None:
        w, lay = self._column()
        look = Section("Appearance")
        self.look = Segmented(LOOKS)
        self.look.set_value(str(self.lib.settings.get("appearance", "system")))
        self.look.changed.connect(self.win.set_look)
        look.add(self.look)
        lay.addWidget(look)
        accent = Section("Accent Color")
        self.accent = AccentPicker(str(self.lib.settings.get("accent", "")))
        self.accent.picked.connect(self.win.set_accent)
        accent.add(self.accent)
        lay.addWidget(accent)
        upd = Section("Updates")
        self.auto = ToggleRow(
            "Check for Updates Automatically", bool(self.lib.settings.get("auto_update", True))
        )
        self.auto.toggled.connect(self._auto)
        upd.add(self.auto)
        version = ElidedLabel(f"Version {__version__}")
        version.setObjectName("Muted")
        upd.add(version)  # checking now is a command: the profile menu and Bodega › Check for Updates…
        lay.addWidget(upd)
        lay.addStretch(1)
        self._fill("general", w)

    def _auto(self, on: bool) -> None:
        self.lib.settings["auto_update"] = on
        self.lib.save_settings()

    # ------------------------------------------------------------------ Profiles
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
            add = QPushButton("Add a Profile")
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
        self.win.toast("Profile deleted." if not saved else "Profile saved.", "done")

    # ------------------------------------------------------------------ AI
    def _build_ai(self) -> None:
        from bodega.ui.dialogs.ai_setup import AISetupDialog

        d = AISetupDialog(self.lib)
        d.embed()
        d.layout().setContentsMargins(0, 0, tokens.SPACE_3, tokens.SPACE_4)
        d.layout().addStretch(1)  # packed at the top, like the other sections
        d.accepted.connect(self.win._ai_state)
        self.ai_editor = d
        self._fill("ai", d)

    # ------------------------------------------------------------------ Account
    def _build_account(self) -> None:
        from bodega.ui.dialogs.account import SignInDialog

        who = account.current()
        if who is not None:
            w, lay = self._column()
            out = QPushButton("Sign Out")
            out.clicked.connect(self._sign_out)
            lay.addLayout(self._row(f"Signed in as {who.email}", out))
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
            self.win.toast(errors.plain(e, "sign out"), "problem")
        self._build_account()
        self.win.sidebar.show_who()

    # ------------------------------------------------------------------ Shortcuts
    def _build_shortcuts(self) -> None:
        from bodega.ui.dialogs.shortcuts import ShortcutsList

        self._fill("shortcuts", ShortcutsList(self.win.menuBar()))

    # ------------------------------------------------------------------ Your Data
    def _build_data(self) -> None:
        w, lay = self._column()
        where = Section("Saved On This Computer")
        path = ElidedLabel(str(data_dir()), mode=Qt.TextElideMode.ElideMiddle)
        path.setObjectName("Muted")
        path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        where.add(path)
        show = QPushButton("Show Folder")
        show.clicked.connect(self.win.open_data_folder)
        back = QPushButton("Back Up…")
        back.clicked.connect(self.win.back_up)
        restore = QPushButton("Restore…")
        restore.setToolTip("Put a backup or a safety copy back in place of everything")
        restore.clicked.connect(self.win.restore)
        row = hbox(spacing=tokens.SPACE_2)
        row.addWidget(show)
        row.addWidget(back)
        row.addWidget(restore)
        row.addStretch(1)
        where.add(row)
        lay.addWidget(where)
        safety = Section("Safety Copies")
        safety.add(
            hint(
                f"Bodega keeps a copy of your gear, kits, rentals, renters and profiles each day you open it "
                f"(the last {backups.DAILY_KEPT} days) and before a big change: an import, Tidy Up Groups, an "
                f"AI's changes or a restore (the last {backups.CHANGES_KEPT}). Restore… starts with them."
            )
        )
        lay.addWidget(safety)
        private = Section("Renters' Details")
        private.add(
            hint(
                "Your renters' names, emails, phones and addresses are kept on this computer as plain files, and "
                "every backup holds them too. Turn on FileVault (Mac) or BitLocker (Windows) so a lost computer "
                "doesn't give them away, and keep backups somewhere private."
            )
        )
        lay.addWidget(private)
        lay.addStretch(1)
        self._fill("data", w)
