"""The menu bar (Mac) and the ⋯ menu: every command with its shortcut.

A part of MainWindow (see main_window.py); it uses the window's widgets and the library."""

from __future__ import annotations

import sys

from PySide6.QtCore import QPoint, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QApplication, QLineEdit, QMenu, QPlainTextEdit, QTextEdit, QToolButton

from bodega import version_label
from bodega.core import settings
from bodega.core.fileutil import reveal
from bodega.core.paths import data_dir, log_dir
from bodega.ui.components.widgets import menu_item
from bodega.ui.dialogs.common import about
from bodega.ui.style import theme, tokens
from bodega.ui.window.common import PLACES, kind_of

# Single keys (the standard's 6.1): a letter alone, for the commands people use most. They work only outside text
# fields (a field takes its letters first) with nothing open over the window (a menu or a dialog is its own
# window), never with ⌘, Ctrl or ⌥ held; Shift doesn't change them. On by default; Settings › Keyboard Shortcuts
# turns them off (speech typing sets letters off too). The Keyboard Shortcuts list reads this table.
SINGLE_KEYS = (  # (key, what it does, the window's method)
    ("N", "New", "new_here"),
    ("E", "Edit", "edit_open"),
    ("D", "Delete", "delete_selected"),
    ("/", "Search This Page", "_focus_search"),
    ("?", "Keyboard Shortcuts", "show_shortcuts"),
    ("A", "Assistant", "open_assistant"),
)


# Commands more than one menu offers (the standard's D-04: one registry): the File menu, the sidebar's + and the
# toolbar's + list them from here, and Search Everything reads them from the menus.
COMMANDS = {  # id -> (title, menu icon, the window's method and what it's given)
    "new_gear": ("New Gear", "box", ("new", "gear")),
    "new_kit": ("New Kit", "case", ("new", "packages")),
    "new_rental": ("New Rental", "receipt", ("new", "rentals")),
    "new_group": ("New Group…", "folder", ("new_group",)),
    "import_sheet": ("Import Spreadsheet…", "table", ("import_sheet",)),
    "import_google": ("Import from Google Sheets…", "link", ("import_google",)),
}
INVENTORY_PLUS = ("new_gear", "new_group", "new_kit", None, "import_sheet", "import_google")  # the + beside Inventory
GEAR_PLUS = ("new_gear", "new_group", None, "import_sheet", "import_google")  # the toolbar's + on gear pages


class MenusMixin:
    def run_command(self, cid: str) -> None:
        """A command from COMMANDS, whichever menu it was picked in."""
        method, *given = COMMANDS[cid][2]
        getattr(self, method)(*given)

    def _command_menu(self, parent, ids) -> QMenu:
        """A menu of COMMANDS (None: a divider), with their icons."""
        m = QMenu(parent)
        for cid in ids:
            if cid is None:
                m.addSeparator()
            else:
                m.addAction(
                    theme.menu_icon(COMMANDS[cid][1]), COMMANDS[cid][0], lambda _c=False, c=cid: self.run_command(c)
                )
        return m

    def _menus(self) -> None:
        """Every command, with its shortcut, in a full menu bar (the standard's 3.7): the Mac's own at the top of
        the screen; on Windows and Linux, across the top of the window."""
        bar = self.menuBar()

        def act(m: QMenu, text: str, slot, keys=None) -> QAction:
            a = menu_item(m, None, text, slot)  # (kept: made here, never by Qt; see widgets.menu_item)
            if keys is not None:
                a.setShortcut(QKeySequence(keys))
                self.addAction(a)
            return a

        def command(m: QMenu, cid: str, keys=None) -> QAction:
            return act(m, COMMANDS[cid][0], lambda _c=False, c=cid: self.run_command(c), keys)

        f = bar.addMenu("File")
        act(f, "New", self.new_here, QKeySequence.StandardKey.New)
        for cid in ("new_gear", "new_kit", "new_rental"):
            command(f, cid)
        command(f, "new_group", "Ctrl+Shift+N")
        f.addSeparator()
        command(f, "import_sheet", "Ctrl+Shift+I")
        command(f, "import_google")
        act(f, "Export Gear as CSV…", self.export_csv, "Ctrl+Shift+E")
        act(f, "Export Kits as CSV…", self.export_kits_csv)
        act(f, "Export Rentals as CSV…", self.export_rentals_csv)
        act(f, "Get Photos from Links…", self.get_photos_from_links)
        f.addSeparator()
        act(f, "Add Rentals to Calendar", lambda: self.add_to_calendar())
        act(f, "Save Calendar File…", self.save_calendar)
        act(f, "Back Up…", self.back_up)
        act(f, "Restore from Backup…", self.restore)
        f.addSeparator()
        self.print_acts = [  # (off until there's gear to print)
            act(
                f,
                "Print Inventory List…",
                lambda: self.show_pages(("gear", self._grp()), "inventory"),
                QKeySequence.StandardKey.Print,
            ),
            act(f, "Print Rate Card…", lambda: self.show_pages(("gear", ""), "ratecard")),
            act(f, "Print Labels…", lambda: self.show_pages(("gear", self._grp()), "labels")),
        ]
        f.aboutToShow.connect(lambda: [a.setEnabled(bool(self.lib.items)) for a in self.print_acts])
        f.addSeparator()
        prefs = act(f, "Settings…", self.open_settings, QKeySequence.StandardKey.Preferences)
        prefs.setMenuRole(QAction.MenuRole.PreferencesRole)  # the Mac puts it under Bodega, ⌘,
        if sys.platform != "darwin":
            prefs.setShortcut(QKeySequence("Ctrl+,"))  # (Windows and Linux have no standard key for it)
        quit_ = act(f, "Quit Bodega", self.close, QKeySequence.StandardKey.Quit)
        quit_.setMenuRole(QAction.MenuRole.QuitRole)

        e = bar.addMenu("Edit")
        self.act_undo = act(e, "Undo", self.undo, QKeySequence.StandardKey.Undo)
        self.act_redo = act(e, "Redo", self.redo, "Ctrl+Shift+Z")
        if sys.platform != "darwin":  # Ctrl+Y too, as Windows apps do
            self.act_redo.setShortcuts([QKeySequence("Ctrl+Shift+Z"), QKeySequence("Ctrl+Y")])
        e.aboutToShow.connect(self._edit_menu_state)
        e.addSeparator()
        act(e, "Cut", lambda: self._text_do("cut"), QKeySequence.StandardKey.Cut)
        act(e, "Copy", self.copy, QKeySequence.StandardKey.Copy)
        act(e, "Paste", self.paste, QKeySequence.StandardKey.Paste)
        act(e, "Select All", self.select_all, QKeySequence.StandardKey.SelectAll)
        e.addSeparator()
        act(e, "Duplicate", self._duplicate_current, "Ctrl+D")
        act(e, "Delete", self.delete_selected, "Ctrl+Backspace")
        e.addSeparator()
        act(e, "Move Up", lambda: self.step_gear(-1))  # (no keys: the standard keeps ⌥ off arrows and the like)
        act(e, "Move Down", lambda: self.step_gear(1))
        e.addSeparator()
        find = act(e, "Find", self._focus_search, QKeySequence.StandardKey.Find)
        find.setShortcuts([*find.shortcuts(), QKeySequence("Ctrl+Alt+F")])  # ⌥⌘F, the Mac's other Find
        self.act_search = act(e, "Search Everything…", self.search_everything, "Ctrl+K")  # places, records, commands
        v = bar.addMenu("View")
        for p in PLACES:  # the same places as the sidebar (window/common.py)
            if p.menu:
                act(v, p.menu, lambda _c=False, k=p.key: self.go(k))
        act(v, "Close Panel", self.deselect)
        self.sidebar_act = act(
            v, "Hide Sidebar", self.toggle_sidebar, "Meta+Ctrl+S" if sys.platform == "darwin" else None
        )
        v.addSeparator()
        self.look_actions = {}
        looks = v.addMenu("Appearance")
        for key, label in (("system", "Match System"), ("light", "Light"), ("dark", "Dark")):
            a = menu_item(looks, None, label, lambda _c=False, k=key: self.set_look(k))
            a.setCheckable(True)
            self.look_actions[key] = a
        # the open piece's and the open rental's commands, in the menu bar too (not only in their panels)
        gm = bar.addMenu("Gear")
        self.gear_acts = [
            act(gm, "Rent This", self.rent_this),
            act(gm, "Update with AI…", lambda: self._with_open_piece(self.ai_this_piece)),
            act(gm, "Make It Its Own Piece", lambda: self._with_open_piece(self.detach)),
        ]
        gm.addSeparator()  # the group you're in (not only from its right-click menu)
        self.group_acts = [
            act(gm, "Rename Group…", lambda: self._with_group(self.rename_group)),
            act(gm, "Move Group Up", lambda: self._with_group(lambda g: self._step_group(g, -1))),
            act(gm, "Move Group Down", lambda: self._with_group(lambda g: self._step_group(g, 1))),
            act(gm, "Remove Group", lambda: self._with_group(self._remove_group)),
        ]
        gm.aboutToShow.connect(self._record_menu_state)
        rm = bar.addMenu("Rental")
        self.rental_acts = {
            "agreement": act(
                rm, "Agreement…", lambda: self._with_open_rental(lambda i: self.show_pages(("rental", i)))
            ),
            "out": act(rm, "Check Out…", lambda: self._with_open_rental(lambda i: self.check_rental(i, False))),
            "in": act(rm, "Check In…", lambda: self._with_open_rental(lambda i: self.check_rental(i, True))),
            "saldo": act(rm, "Send to Saldo…", lambda: self._with_open_rental(self.send_to_saldo)),
            "calendar": act(rm, "Add to Calendar", lambda: self._with_open_rental(self.add_to_calendar)),
        }
        rm.addSeparator()
        self.rental_acts["cancel"] = act(
            rm,
            "Mark as Cancelled…",
            lambda: self.rentals.r is not None and self.cancel_rental(self.rentals.r),
        )
        rm.aboutToShow.connect(self._record_menu_state)
        b = bar.addMenu("Profile")
        act(b, "Edit Profile…", lambda: self.edit_business(False))
        act(b, "Add Profile…", lambda: self.edit_business(True))
        act(b, "New Renter…", lambda: self.new("renters"))
        act(b, "Tidy Up Renters…", self.tidy_renters)
        ai = bar.addMenu("AI")
        self.act_assistant = act(ai, "Show Assistant", self.toggle_assistant, "Ctrl+J")
        ai.aboutToShow.connect(
            lambda: self.act_assistant.setText("Hide Assistant" if self.assistant_showing() else "Show Assistant")
        )
        ai.addSeparator()
        act(ai, "Update from Links…", lambda: self.open_ai_assistant("links"))
        act(ai, "Find Missing Links…", lambda: self.open_ai_assistant("find"))
        act(ai, "Tidy Up Names…", lambda: self.open_ai_assistant("names"))
        act(ai, "Organize Groups…", lambda: self.open_ai_assistant("groups"))
        act(ai, "Quick Tidy Up Groups…", self.tidy_groups)  # plain names by rule, no AI needed
        ai.addSeparator()
        act(ai, "AI Settings…", self.open_ai_setup)
        w = bar.addMenu("Window")
        act(w, "Minimize", self.showMinimized, "Ctrl+M")
        act(w, "Zoom", self.toggle_zoom)
        h = bar.addMenu("Help")
        act(h, "Keyboard Shortcuts", self.show_shortcuts, "Ctrl+/")
        act(h, "Send Feedback…", self.open_feedback)
        upd = act(h, "Check for Updates…", self.check_updates)
        upd.setMenuRole(QAction.MenuRole.ApplicationSpecificRole)  # on the Mac: in the Bodega menu, like Mac apps
        act(h, "Open Data Folder", self.open_data_folder)
        act(h, "Open Log File", lambda: reveal(log_dir() / "bodega.log"))
        act(h, "About Bodega", lambda: about(self, version_label(), str(data_dir())))
        bar.setVisible(True)  # (on a Mac it lives in the screen's own bar)
        self._single_keys()

        # the share button opens the page window at once: Inventory List, Rate Card and Labels are its tabs
        # (importing is in File and the + menus; Export as CSV and Get Photos in File)
        self.btn_export.clicked.connect(lambda: self.show_pages(("gear", self._grp()), "inventory"))

        self.sidebar.btn_new_dep.setMenu(self._command_menu(self.sidebar.btn_new_dep, INVENTORY_PLUS))
        self.sidebar.btn_new_dep.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        # the toolbar's + on gear pages: a piece or a group (elsewhere it makes a kit or a rental at once)
        self.new_menu = self._command_menu(self.btn_new, GEAR_PLUS)

    def _single_keys(self) -> None:
        self.single_acts = []
        for key, text, method in SINGLE_KEYS:
            a = QAction(text, self)
            keys = [QKeySequence(key), QKeySequence(f"Shift+{key}")]  # (Shift doesn't change a letter's meaning,
            a.setShortcuts(keys)  # and a ? is typed with it)
            a.triggered.connect(getattr(self, method))
            self.addAction(a)
            self.single_acts.append(a)
        self.use_single_keys(settings.value(self.lib.settings, "single_keys"))

    def use_single_keys(self, on: bool) -> None:
        """Settings › Keyboard Shortcuts: single keys on or off (⌘ and Ctrl shortcuts stay either way)."""
        for a in self.single_acts:
            a.setEnabled(on)

    def _tips_from_menus(self) -> None:
        """A button that has a menu command names its key as the command has it (never typed twice): ⌘J, ⌘K."""
        for button, words, action in (
            (self.btn_ai, "Assistant", self.act_assistant),
            (self.sidebar.search, "Search Everything", self.act_search),
        ):
            keys = action.shortcut().toString(QKeySequence.SequenceFormat.NativeText)
            button.setToolTip(f"{words} ({keys})" if keys else words)

    def _app_menu(self) -> None:
        """The profile card's menu: your profiles (pick one to work as), feedback, updates, and Settings."""
        card = self.sidebar.profile_card
        m = QMenu(card)
        current = self.business()
        if len(self.lib.businesses) > 1:
            for b in self.lib.businesses.values():
                a = m.addAction(b.name or "Unnamed Profile")
                a.setCheckable(True)
                a.setChecked(current is not None and b.id == current.id)
                a.triggered.connect(lambda _c=False, bid=b.id: self.use_business(bid))
            m.addSeparator()
        # the standard's order: Settings…, Keyboard Shortcuts, Send Feedback…, Check for Updates… (profiles are
        # added and edited in Settings › Profiles)
        s = m.addAction(theme.menu_icon("cog"), "Settings…", self.open_settings)
        s.setShortcut(QKeySequence.StandardKey.Preferences)  # shown for reference; the menu bar's runs it
        s.setShortcutVisibleInContextMenu(True)
        k = m.addAction(theme.menu_icon("keyboard"), "Keyboard Shortcuts", self.show_shortcuts)
        k.setShortcut(QKeySequence("Ctrl+/"))
        k.setShortcutVisibleInContextMenu(True)
        m.addSeparator()
        m.addAction(theme.menu_icon("message"), "Send Feedback…", self.open_feedback)
        m.addAction(theme.menu_icon("arrow-down"), "Check for Updates…", self.check_updates)
        at = card.mapToGlobal(QPoint(0, 0))
        m.exec(QPoint(at.x(), at.y() - m.sizeHint().height() - tokens.MENU_GAP))
        self.sidebar.show_who()

    # Edit
    def _text_widget(self):
        """The text box you're typing in, if any (it keeps its own undo, cut, copy and paste)."""
        w = QApplication.focusWidget()
        return w if isinstance(w, (QLineEdit, QPlainTextEdit, QTextEdit)) else None

    def _text_do(self, what: str) -> None:
        w = self._text_widget()
        if w is not None and not (what in ("cut", "paste") and w.isReadOnly()):
            getattr(w, what)()

    def _text_can_undo(self, redo: bool = False) -> bool:
        w = self._text_widget()
        if isinstance(w, QLineEdit):
            return w.isRedoAvailable() if redo else w.isUndoAvailable()
        if w is not None:
            doc = w.document()
            return doc.isRedoAvailable() if redo else doc.isUndoAvailable()
        return False

    def undo(self) -> None:
        """⌘Z: in a text box, its typing; otherwise the last change to your gear, kits, rentals, renters or groups."""
        if self._text_can_undo():
            self._text_do("undo")
            return
        self.flush()
        self._fresh = None
        what = self.history.undo() if self.history is not None else None
        if what is None:
            self.toast("Nothing to undo.")
            return
        self._after_history()
        self.toast(f"Undid {what[0].lower() + what[1:]}.", "done")

    def redo(self) -> None:
        if self._text_can_undo(redo=True):
            self._text_do("redo")
            return
        self.flush()
        what = self.history.redo() if self.history is not None else None
        if what is None:
            self.toast("Nothing to redo.")
            return
        self._after_history()
        self.toast(f"Redid {what[0].lower() + what[1:]}.", "done")

    def _with_open_piece(self, do) -> None:
        if kind_of(self.view_key) == "gear" and self.items.it is not None and self.dock.opened:
            do(self.items.it.id)

    def _with_open_rental(self, do) -> None:
        if kind_of(self.view_key) == "rentals" and self.rentals.r is not None and self.dock.opened:
            do(self.rentals.r.id)

    def _with_group(self, do) -> None:
        """A group command on the group you're in."""
        if self.view_key.startswith("grp:"):
            do(self.view_key[4:])

    def _record_menu_state(self) -> None:
        """The Gear and Rental menus work on what's open: off while nothing is."""
        it = self.items.it if kind_of(self.view_key) == "gear" and self.dock.opened else None
        for a in self.gear_acts:
            a.setEnabled(it is not None)
        if it is not None:
            self.gear_acts[2].setEnabled(bool(it.parent))
        for a in self.group_acts:
            a.setEnabled(self.view_key.startswith("grp:"))
        r = self.rentals.r if kind_of(self.view_key) == "rentals" and self.dock.opened else None
        for a in self.rental_acts.values():
            a.setEnabled(r is not None)
        if r is not None:
            self.rental_acts["out"].setEnabled(r.holds_gear() and not r.is_out())
            self.rental_acts["in"].setEnabled(r.is_out())
            self.rental_acts["cancel"].setEnabled(not r.deletable() and not r.is_cancelled())

    def _edit_menu_state(self) -> None:
        """Undo and Redo say what they'd change back ("Undo Change to Gear"), or "Undo Typing" in a text box."""
        h = self.history
        typing, typed_again = self._text_can_undo(), self._text_can_undo(redo=True)
        undo = "" if typing or h is None else h.undo_names()
        redo = "" if typed_again or h is None else h.redo_names()
        self.act_undo.setEnabled(typing or bool(undo))
        self.act_redo.setEnabled(typed_again or bool(redo))
        self.act_undo.setText("Undo Typing" if typing else f"Undo {undo}" if undo else "Undo")
        self.act_redo.setText("Redo Typing" if typed_again else f"Redo {redo}" if redo else "Redo")

    def _after_history(self) -> None:
        """Undo/redo put new copies of everything in the library: open them again in the panel."""
        for panel, attr, where in (
            (self.items, "it", self.lib.items),
            (self.packages, "pkg", self.lib.packages),
            (self.rentals, "r", self.lib.rentals),
            (self.renters, "c", self.lib.clients),
        ):
            cur = getattr(panel, attr)
            if cur is None:
                continue
            setattr(panel, attr, None)
            again = where.get(cur.id)
            if self.inspector.currentWidget() is panel and self.dock.opened:
                if again is not None:
                    panel.load(again)
                else:
                    self.dock.set_open(False)
        self.sidebar.show_who()
        self.refresh()
        shown = self.history.shown if self.history is not None else None
        if shown is not None:  # what the undo brought back or changed, in view
            kind, obj_id = shown
            QTimer.singleShot(0, self, lambda: self.open(kind, obj_id))

    def copy(self) -> None:
        """⌘C: text you've selected, or the gear you've picked as a plain list (name, company, how many)."""
        if self._text_widget() is not None:
            self._text_do("copy")
            return
        if self._table() is self.gear_table:
            rows = []
            for i in self.gear_table.chosen_ids():
                it = self.lib.items.get(i)
                if it is not None:
                    rows.append("\t".join([it.name, it.brand, str(it.qty)]))
            if rows:
                QApplication.clipboard().setText("\n".join(rows))
                self.toast(f"Copied {len(rows)} piece{'s' if len(rows) != 1 else ''}.", "done")

    def paste(self) -> None:
        """⌘V: into the text box you're typing in; otherwise a picture you copied becomes the open gear's photo."""
        if self._text_widget() is not None:
            self._text_do("paste")
        elif self.inspector.currentWidget() is self.items and self.dock.opened:
            self.items.paste_photo()

    def select_all(self) -> None:
        w = QApplication.focusWidget()
        if self._text_widget() is not None:
            self._text_do("selectAll")
        elif self._table() is self.gear_table:
            self.gear_table.setFocus()
            self.gear_table.select_showing()
        elif w is not None and hasattr(w, "selectAll"):
            w.selectAll()

    def delete_selected(self) -> None:
        """⌘⌫ or D: delete what's picked, at once, with Undo (gear on a rental is retired instead, after asking)."""
        kind = kind_of(self.view_key)
        if kind == "gear":
            ids = self.gear_table.chosen_ids() or ([self.items.it.id] if self.items.it is not None else [])
            if ids:
                self.delete_gear(ids)
            return
        table = {"packages": self.kit_table, "renters": self.renter_table}.get(kind, self.rental_table)
        ticked = table.ticked_ids()
        if ticked and self.view_key != "calendar":
            self.delete_many(kind, ticked)
            return
        cur = {"packages": self.packages.pkg, "renters": self.renters.c}.get(kind, self.rentals.r)
        if cur is not None and self.dock.opened:
            self.delete(kind, cur.id)

    def toggle_zoom(self) -> None:
        """Window › Zoom: fill the screen, or back to the smallest size (like double-clicking the title bar)."""
        from bodega.ui.components import titlebar

        titlebar.toggle_size(self)

    def show_shortcuts(self) -> None:
        self.open_settings("shortcuts")

    def _focus_search(self) -> None:
        """⌘F, ⌥⌘F or /: the cursor in this page's search (the calendar has none)."""
        if self.search.isVisible():
            self.search.setFocus()
            self.search.selectAll()
