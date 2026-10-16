"""Groups: moving gear between them, reordering, the sidebar's group rows and menus.

A part of MainWindow (see main_window.py); it uses the window's widgets and the library."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMenu

from bodega.core import words
from bodega.ui.dialogs.common import confirm
from bodega.ui.style import theme
from bodega.ui.window.common import kind_of
from bodega.ui.window.tables import ID


class GroupsMixin:
    def move_to(self, ids: list[str]) -> None:
        """Move To…: pick a group from a list you can search (or No Group, or a new one)."""
        from bodega.ui.dialogs.common import pick_from

        n = len(ids)
        choices = [(f"grp:{g}", g) for g in self.lib.groups()]
        choices += [("none", "None"), ("new", "New Group…")]
        picked = pick_from(self, "Move To" if n == 1 else f"Move {n} To", choices, "Move")
        if picked == "new":
            self._move_to_new_group(ids)
        elif picked == "none":
            self.move_gear(ids, "")
        elif picked:
            self.move_gear(ids, picked[4:])

    def _move_to_new_group(self, ids: list[str]) -> None:
        from bodega.ui.dialogs.common import ask_name

        name = ask_name(self, "New Group", "Move", placeholder="Pelican Cases", known=self.lib.groups())
        if name:
            self.move_gear(ids, name)

    def move_gear(self, ids: list[str], group: str) -> None:
        """Put gear in a group (what goes with it comes along)."""
        self.flush()
        n = self.lib.put_in_group(ids, group or "")
        self.lib.save_settings()
        self.refresh()
        if self.items.it is not None:
            self.items.load(self.items.it)
        if ids:
            self.gear_table.select_id(ids[0])
        where = group or "No Group"
        self.toast(f"Moved {n} to {where}." if n != 1 else f"Moved it to {where}.", "done")

    def _reordered(self, ids: list[str], anchor: str, after: bool) -> None:
        """Rows dragged by their grip: your order changes (and the list shows your order)."""
        self.flush()
        self.lib.reorder_items(ids, anchor, after, brand=self.gear_table.divide == "brand")
        self.lib.save_settings()
        t = self.gear_table
        if not t.your_order():
            t.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self.refresh()
        t.clearSelection()
        for r in t.item_rows():
            if r.data(0, ID) in ids:
                r.setSelected(True)

    def step_gear(self, step: int, ids: list[str] | None = None) -> None:
        """Move Up / Move Down (⌥⌘↑ ↓): the picked gear swaps places with the row above or below it, inside its
        group (the keyboard's way to do what dragging by the grip does)."""
        t = self.gear_table
        if kind_of(self.view_key) != "gear":
            return
        ids = ids or t.chosen_ids()
        rows = [r for r in t.showing_rows() if r.data(0, ID)]
        mine = [r for r in rows if r.data(0, ID) in ids]
        if not mine:
            return
        edge = mine[0] if step < 0 else mine[-1]
        at = rows.index(edge) + step
        if not 0 <= at < len(rows) or rows[at].parent() is not edge.parent():
            self.toast(f"It's already {'first' if step < 0 else 'last'} in its group.")
            return
        self._reordered([r.data(0, ID) for r in mine], rows[at].data(0, ID), after=step > 0)

    def _branded(self, ids: list[str], brand: str) -> None:
        self.flush()
        for i in ids:
            if i in self.lib.items:
                self.lib.items[i].brand = brand
        self.lib.save_items()
        self.refresh()
        if self.items.it is not None:
            self.items.load(self.items.it)

    def _sidebar_dropped(self, key: str) -> None:
        ids = self.gear_table.selected_ids()
        if ids and key.startswith("grp:"):
            self.gear_table.after_drag(lambda: self.move_gear(ids, key[4:]))

    def _divider_menu(self, group: str, pos) -> None:
        m = QMenu(self)
        self._group_actions(m, group)
        m.exec(pos)

    def _group_actions(self, m: QMenu, group: str) -> None:
        m.addAction(theme.menu_icon("edit"), "Rename Group…", lambda: self.rename_group(group))
        m.addAction(theme.menu_icon("arrow-up"), "Move Up", lambda: self._step_group(group, -1))
        m.addAction(theme.menu_icon("arrow-down"), "Move Down", lambda: self._step_group(group, 1))
        m.addSeparator()
        m.addAction(theme.menu_icon("trash"), "Remove Group…", lambda: self._remove_group(group))

    def _place_picked(self, key: str) -> None:
        """A row in the sidebar: a place, or one kit (opens it)."""
        if key.startswith("kit:"):
            if key[4:] in self.lib.packages:
                self.open("packages", key[4:])
            return
        self.go(key)

    def _sidebar_menu(self, key: str, pos) -> None:
        if not key.startswith("grp:"):
            return
        m = QMenu(self)
        self._group_actions(m, key[4:])
        m.exec(pos)

    def _groups_edited(self, toast: str = "") -> None:
        self.lib.save_settings()
        if self.view_key.startswith("grp:") and self._grp() not in self.lib.groups():
            self.go("gear")
        else:
            self.refresh()
        if self.items.it is not None:
            self.items.load(self.items.it)
        if toast:
            self.toast(toast, "done")

    def new_group(self) -> None:
        from bodega.ui.dialogs.common import ask_name

        name = ask_name(self, "New Group", "Add", placeholder="Cases, Lights, Media…", known=self.lib.groups())
        if name:
            self.lib.add_group(name)
            self._groups_edited()
            self.go(f"grp:{name}")

    def rename_group(self, group: str) -> None:
        from bodega.ui.dialogs.common import ask_name

        name = ask_name(self, f"Rename {group}", "Rename", text=group, known=self.lib.groups())
        if name and name != group:
            self.flush()
            was_here = self.view_key == f"grp:{group}"
            self.lib.rename_group(group, name)
            self._groups_edited()
            if was_here:
                self.go(f"grp:{name}")

    def _step_group(self, group: str, step: int) -> None:
        self.lib.step_group(group, step)
        self._groups_edited()

    def _remove_group(self, group: str) -> None:
        n = sum(1 for i in self.lib.items.values() if i.group == group)
        if n and not confirm(
            self,
            f"Remove {group}?",
            ("Its piece stays" if n == 1 else f"Its {n:,} pieces stay") + ", under No Group.",
            "Remove",
            danger=False,
        ):
            return
        self.flush()
        self.lib.remove_group(group)
        self._groups_edited(f"Removed {group}.")

    def tidy_groups(self) -> None:
        """Tidy Up Groups: plain names for everything (SD Cards → Media, 1000c → Lights…), after a look."""
        from bodega.core import tidy
        from bodega.ui.dialogs.common import tidy_preview

        self.flush()
        moves = tidy.changes(self.lib.items)
        if not moves:
            self.toast("Your groups are already tidy.")
            return
        if not tidy_preview(self, moves):
            return
        self.lib.snapshot("before-tidy")
        n = self.lib.apply_groups(tidy.suggest(self.lib.items))
        self._groups_edited(f"Tidied {words.count(n, 'piece')} into {words.count(len(self.lib.groups()), 'group')}.")
