"""The menu bar (Mac) and the ⋯ menu: every command with its shortcut.

A part of MainWindow (see main_window.py); it uses the window's widgets and the library."""

from __future__ import annotations

import sys

from PySide6.QtCore import QPoint
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QApplication, QLineEdit, QMenu, QPlainTextEdit, QTextEdit, QToolButton

from bodega import __version__
from bodega.core.fileutil import reveal
from bodega.core.paths import data_dir, log_dir
from bodega.ui.dialogs.common import about
from bodega.ui.style import theme, tokens
from bodega.ui.window.common import kind_of


class MenusMixin:
    def _menus(self) -> None:
        """Commands with shortcuts. The menu bar shows on the Mac; on Windows/Linux it's hidden and the
        shortcuts still work, with the same commands under ⋯ in the sidebar."""
        bar = self.menuBar()

        def act(m: QMenu, text: str, slot, keys=None) -> QAction:
            a = m.addAction(text)
            a.triggered.connect(slot)
            if keys is not None:
                a.setShortcut(QKeySequence(keys))
                self.addAction(a)
            return a

        f = bar.addMenu("File")
        act(f, "New", lambda: self.new(kind_of(self.view_key)), QKeySequence.StandardKey.New)
        act(f, "New Gear", lambda: self.new("gear"))
        act(f, "New Kit", lambda: self.new("packages"))
        act(f, "New Rental", lambda: self.new("rentals"))
        act(f, "New Group…", self.new_group, "Ctrl+Shift+N")
        f.addSeparator()
        act(f, "Import Spreadsheet…", self.import_sheet, "Ctrl+Shift+I")
        act(f, "Import from Google Sheets…", self.import_google)
        act(f, "Export Gear as CSV…", self.export_csv, "Ctrl+Shift+E")
        act(f, "Get Photos from Links…", self.get_photos_from_links)
        f.addSeparator()
        act(f, "Add Rentals to Calendar", lambda: self.add_to_calendar())
        act(f, "Save Calendar File…", self.save_calendar)
        act(f, "Back Up…", self.back_up)
        f.addSeparator()
        act(
            f,
            "Print Inventory List…",
            lambda: self.show_pages(("gear", self._grp()), "inventory"),
            QKeySequence.StandardKey.Print,
        )
        act(f, "Rate Card…", lambda: self.show_pages(("gear", ""), "ratecard"))
        act(f, "Print Labels…", lambda: self.show_pages(("gear", self._grp()), "labels"))
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
        act(e, "Delete…", self.delete_selected, "Ctrl+Backspace")
        e.addSeparator()
        act(e, "Find", self._focus_search, QKeySequence.StandardKey.Find)
        v = bar.addMenu("View")
        act(v, "All Gear", lambda: self.go("gear"), "Ctrl+1")
        act(v, "Kits", lambda: self.go("kits"), "Ctrl+2")
        act(v, "Rentals", lambda: self.go("rentals"), "Ctrl+3")
        act(v, "Calendar", lambda: self.go("calendar"), "Ctrl+4")
        act(v, "Close Panel", self.deselect)
        v.addSeparator()
        self.look_actions = {}
        looks = v.addMenu("Appearance")
        for key, label in (("system", "Match the System"), ("light", "Light"), ("dark", "Dark")):
            a = looks.addAction(label)
            a.setCheckable(True)
            a.triggered.connect(lambda _c=False, k=key: self.set_look(k))
            self.look_actions[key] = a
        b = bar.addMenu("Profile")
        act(b, "Edit Profile…", lambda: self.edit_business(False))
        act(b, "Add a Profile…", lambda: self.edit_business(True))
        act(b, "New Renter…", lambda: self.edit_client(True, assign=False))
        ai = bar.addMenu("AI")
        act(ai, "Assistant", self.toggle_assistant, "Ctrl+J")
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
        upd.setMenuRole(
            QAction.MenuRole.ApplicationSpecificRole
        )  # on the Mac: in the Bodega menu, like Mac apps
        act(h, "Open Data Folder", self.open_data_folder)
        act(h, "Open Log File", lambda: reveal(log_dir() / "bodega.log"))
        act(h, "About Bodega", lambda: about(self, __version__, str(data_dir())))
        bar.setVisible(sys.platform == "darwin")

        e = QMenu(self.btn_export)  # Import & Export
        e.addAction(theme.menu_icon("table"), "Import Spreadsheet…", self.import_sheet)
        e.addAction(theme.menu_icon("link"), "Import from Google Sheets…", self.import_google)
        e.addSeparator()
        e.addAction(
            theme.menu_icon("file"),
            "Inventory List…",
            lambda: self.show_pages(("gear", self._grp()), "inventory"),
        )
        e.addAction(
            theme.menu_icon("receipt"), "Rate Card…", lambda: self.show_pages(("gear", ""), "ratecard")
        )
        e.addAction(
            theme.menu_icon("tag"), "Labels…", lambda: self.show_pages(("gear", self._grp()), "labels")
        )
        e.addSeparator()
        e.addAction(theme.menu_icon("table"), "Export Gear as CSV…", self.export_csv)
        e.addSeparator()
        e.addAction(theme.menu_icon("image"), "Get Photos from Links…", self.get_photos_from_links)
        self.btn_export.setMenu(e)

        g = QMenu(self.sidebar.btn_new_dep)  # the + beside Inventory
        g.addAction(theme.menu_icon("box"), "New Gear", lambda: self.new("gear"))
        g.addAction(theme.menu_icon("folder"), "New Group…", self.new_group)
        g.addAction(theme.menu_icon("case"), "New Kit", lambda: self.new("packages"))
        self.sidebar.btn_new_dep.setMenu(g)
        self.sidebar.btn_new_dep.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        # the toolbar's + on gear pages: a piece or a group (elsewhere it makes a kit or a rental at once)
        self.new_menu = QMenu(self.btn_new)
        self.new_menu.addAction(theme.menu_icon("box"), "New Gear", lambda: self.new("gear"))
        self.new_menu.addAction(theme.menu_icon("folder"), "New Group…", self.new_group)

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
        m.addAction(
            theme.menu_icon("edit"), "Edit Profile…", lambda: self.edit_business(not self.lib.businesses)
        )
        m.addAction(theme.menu_icon("plus"), "Add a Profile…", lambda: self.edit_business(True))
        m.addSeparator()
        m.addAction(theme.menu_icon("message"), "Send Feedback…", self.open_feedback)
        m.addAction(theme.menu_icon("arrow-down"), "Check for Updates…", self.check_updates)
        s = m.addAction(theme.menu_icon("cog"), "Settings…", self.open_settings)
        s.setShortcut(QKeySequence.StandardKey.Preferences)  # shown for reference; the menu bar's runs it
        s.setShortcutVisibleInContextMenu(True)
        at = card.mapToGlobal(QPoint(0, 0))
        m.exec(QPoint(at.x(), at.y() - m.sizeHint().height() - tokens.MENU_GAP))
        self.sidebar.show_who()

    # ------------------------------------------------------------------ Edit
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
        """⌘Z: in a text box, its typing; otherwise the last change to your gear, kits, rentals or groups."""
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
        self.toast(f"Undid the last change to {what}.")

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
        self.toast(f"Redid the change to {what}.")

    def _edit_menu_state(self) -> None:
        h = self.history
        self.act_undo.setEnabled(self._text_can_undo() or (h is not None and h.can_undo()))
        self.act_redo.setEnabled(self._text_can_undo(redo=True) or (h is not None and h.can_redo()))

    def _after_history(self) -> None:
        """Undo/redo put new copies of everything in the library: open them again in the panel."""
        for panel, attr, where in (
            (self.items, "it", self.lib.items),
            (self.packages, "pkg", self.lib.packages),
            (self.rentals, "r", self.lib.rentals),
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
                self.toast(f"Copied {len(rows)} piece{'s' if len(rows) != 1 else ''}.")

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
        """⌘⌫: delete what's picked (after asking)."""
        kind = kind_of(self.view_key)
        if kind == "gear":
            ids = self.gear_table.chosen_ids() or ([self.items.it.id] if self.items.it is not None else [])
            if ids:
                self.delete_gear(ids)
            return
        cur = self.packages.pkg if kind == "packages" else self.rentals.r
        if cur is not None and self.dock.opened:
            self.delete(kind, cur.id)

    def toggle_zoom(self) -> None:
        """Window › Zoom: fill the screen, or back to the smallest size (like double-clicking the title bar)."""
        from bodega.ui.components import titlebar

        titlebar.toggle_size(self)

    def show_shortcuts(self) -> None:
        self.open_settings("shortcuts")

    def _focus_search(self) -> None:
        self.search.setFocus()
        self.search.selectAll()
