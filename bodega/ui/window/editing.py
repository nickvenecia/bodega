"""Making, copying, deleting and editing gear, kits, rentals, renters and profiles.

A part of MainWindow (see main_window.py); it uses the window's widgets and the library."""

from __future__ import annotations

from dataclasses import replace

from bodega.core import pricing
from bodega.core.log import get_logger
from bodega.core.model import Business, Item, Package, PackageLine, Rental, RentalLine, new_id, now_iso
from bodega.ui.dialogs.client import ClientDialog
from bodega.ui.dialogs.common import confirm
from bodega.ui.dialogs.gear_picker import GearPicker
from bodega.ui.dialogs.profile import ProfileDialog
from bodega.ui.window.common import kind_of

log = get_logger(__name__)


def _blank(obj) -> dict:
    """What a new record holds, to tell whether you've changed it (when it was saved aside)."""
    d = obj.to_dict()
    d.pop("updated", None)
    return d


class EditingMixin:
    def new(self, kind: str) -> None:
        self.flush()
        if kind == "gear":
            if kind_of(self.view_key) != "gear":
                self.go("gear")
            self.search.clear()
            self.view_menu.clear()  # a filter could hide the new piece
            it = Item(group=self._grp())
            self.lib.add_item(it)
            self._dirty_items = True
            self.flush()
            self.refresh()
            self.open("gear", it.id)
            self.items.name.setFocus()
            self._fresh = ("gear", it.id, _blank(it))
        elif kind == "packages":
            p = self.lib.new_package()
            self.go("kits")
            self.open("packages", p.id)
            self.packages.name.setFocus()
            self._fresh = ("packages", p.id, _blank(p))
        else:
            b = self.business()
            if b is None:
                self.go("rentals")
                self.edit_business(True)
                return
            r = self.lib.new_rental(b)
            if kind_of(self.view_key) != "rentals" or self.view_key == "out":
                self.go("upcoming")
            self.refresh()
            self.open("rentals", r.id)
            self.rentals.client.setFocus()
            self._fresh = ("rentals", r.id, _blank(r))

    def _drop_fresh(self, keep: str = "") -> None:
        """A new piece, kit or rental you left without filling anything in (Esc, or opening something else)
        isn't kept."""
        fresh, self._fresh = self._fresh, None
        if fresh is None:
            return
        kind, obj_id, before = fresh
        if obj_id == keep:
            self._fresh = fresh
            return
        where = {"gear": self.lib.items, "packages": self.lib.packages, "rentals": self.lib.rentals}[kind]
        obj = where.get(obj_id)
        if obj is None or _blank(obj) != before:
            return
        if kind == "gear":
            self._dirty_items = False
            self.lib.delete_items([obj_id])
            self.items.it = None
        elif kind == "packages":
            self._dirty_packages = False
            self.lib.delete_package(obj_id)
            self.packages.pkg = None
        else:
            self._dirty_rentals.discard(obj_id)
            self.lib.delete_rental(obj_id)
            self.rentals.r = None
        self.dock.set_open(False)
        self.refresh()

    def _duplicate_current(self) -> None:
        kind = kind_of(self.view_key)
        cur = {"gear": self.items.it, "packages": self.packages.pkg, "rentals": self.rentals.r}[kind]
        if cur is not None:
            self.duplicate(kind, cur.id)

    def duplicate(self, kind: str, obj_id: str) -> None:
        self.flush()
        if kind == "gear":
            src = self.lib.items.get(obj_id)
            if src is None:
                return
            it = Item.from_dict(src.to_dict())
            it.id, it.created, it.updated = new_id(), now_iso(), now_iso()
            it.serials = []
            self.lib.add_item(it)
            self.lib.save_items()
            self.refresh()
            self.open("gear", it.id)
            self.toast("Copied. Serial numbers start empty.", "done")
        elif kind == "packages":
            src = self.lib.packages.get(obj_id)
            if src is None:
                return
            p = Package.from_dict(src.to_dict())
            p.id, p.created = new_id(), now_iso()
            p.name = f"{src.name} (Copy)" if src.name else ""
            self.lib.packages[p.id] = p
            self.lib.save_packages()
            self.refresh()
            self.open("packages", p.id)
        else:
            src = self.lib.rentals.get(obj_id)
            if src is None:
                return
            r = self.lib.duplicate_rental(src)
            self.refresh()
            self.open("rentals", r.id)
            self.toast(f"Made {r.number}, as a quote.", "done")

    def delete(self, kind: str, obj_id: str) -> None:
        self.flush()
        if kind == "gear":
            self.delete_gear([obj_id])
            return
        if kind == "packages":
            p = self.lib.packages.get(obj_id)
            if p is None or not confirm(
                self, f"Delete {p.name or 'this kit'}?", "The gear in it stays.", "Delete"
            ):
                return
            self.lib.delete_package(obj_id)
            self.packages.pkg = None
        else:
            r = self.lib.rentals.get(obj_id)
            if r is None or not confirm(
                self, f"Delete {r.number}?", "PDFs you saved stay where they are.", "Delete"
            ):
                return
            self._dirty_rentals.discard(obj_id)
            self.lib.delete_rental(obj_id)
            self.rentals.r = None
        self.go(self.view_key)

    def delete_gear(self, ids: list[str]) -> None:
        """Delete one piece or many (Cmd+A, Shift or Cmd-click, then Delete), after a warning.
        Gear attached to them goes too: it's part of the piece."""
        picked = [i for i in ids if i in self.lib.items]
        if not picked:
            return
        self.flush()
        everything: list[str] = []
        for i in picked:
            for x, _u, _d in pricing.with_attached(self.lib, self.lib.items[i], 1):
                if x.id not in everything:
                    everything.append(x.id)
        extra = len(everything) - len(picked)
        names = [self.lib.items[i].name or "New item" for i in picked]
        if len(picked) == 1:
            title = f"Delete {names[0]}?"
        elif len(everything) == len(self.lib.items):
            title = f"Delete all {len(picked)} pieces of gear?"
        else:
            title = f"Delete {len(picked)} pieces of gear?"
        listed = ", ".join(names[:3]) + (f" and {len(names) - 3} more" if len(names) > 3 else "")
        text = (listed + ". ") if len(picked) > 1 else ""
        if extra:
            text += (
                f"The {extra} piece{'s' if extra != 1 else ''} attached go{'' if extra != 1 else 'es'} too. "
            )
        text += "Rentals that had them keep their names."
        if not confirm(self, title, text, "Delete" if len(everything) == 1 else f"Delete {len(everything)}"):
            return
        n = self.lib.delete_items(everything)
        log.info("deleted %d items", n)
        self.items.it = None
        self.go(self.view_key)
        self.toast(f"Deleted {n} pieces." if n != 1 else "Deleted it.", "done")

    def _selection_count(self) -> None:
        t = self._table()
        if t is not self.gear_table:
            return
        picked = len(self.gear_table.chosen_ids()) if len(self.gear_table.selectedItems()) > 1 else 0
        shown = sum(1 for r in self.gear_table.item_rows() if not r.isHidden())
        self.count.set_full_text(f"{picked} selected" if picked > 1 else (f"{shown:,}" if shown else ""))

    def attach_to(self, item_id: str) -> None:
        """Pick gear that lives with this piece."""
        it = self.lib.items.get(item_id)
        if it is None:
            return
        self.flush()
        up = {item_id}
        cur = it
        while cur.parent and cur.parent in self.lib.items and cur.parent not in up:
            up.add(cur.parent)
            cur = self.lib.items[cur.parent]
        already = {k.id for k in pricing.children(self.lib, item_id)}
        d = GearPicker(
            self.lib, self.lib.pricing(), f"Attach to {it.name or 'This Item'}", "Attach",
            exclude=up | already, main_only=False, parent=self,
        )  # fmt: skip
        if d.exec() != GearPicker.DialogCode.Accepted:
            return
        for _kind, ref in d.picked:
            kid = self.lib.items.get(ref)
            if kid is None:
                continue
            kid.parent = item_id
            kid.group = it.group
            for grand, _u, depth in pricing.with_attached(self.lib, kid, 1):
                if depth:
                    grand.group = it.group
        self.lib.save_items()
        self.refresh()
        self.items.refresh_attached()
        n = len(d.picked)
        self.toast(f"Attached {n} to {it.name}.", "done")

    def detach(self, item_id: str) -> None:
        it = self.lib.items.get(item_id)
        if it is None:
            return
        it.parent = ""
        self.lib.save_items()
        self.refresh()
        if self.items.it is not None:
            self.items.load(self.items.it)

    def add_to_package(self, pkg_id: str) -> None:
        p = self.lib.packages.get(pkg_id)
        if p is None:
            return
        have = {ln.item_id for ln in p.lines}
        d = GearPicker(
            self.lib, self.lib.pricing(), f"Add to {p.name or 'the Kit'}", exclude=have, parent=self
        )
        if d.exec() != GearPicker.DialogCode.Accepted:
            return
        for _kind, ref in d.picked:
            p.lines.append(PackageLine(ref, 1))
        self.lib.save_packages()
        self.packages.build_lines()
        self.refresh()

    def add_to_rental(self, rental_id: str) -> None:
        r = self.lib.rentals.get(rental_id)
        if r is None:
            return
        d = GearPicker(
            self.lib, self.lib.businesses.get(r.business_id), "Add to the Rental", packages=True, parent=self
        )
        if d.exec() != GearPicker.DialogCode.Accepted:
            return
        for kind, ref in d.picked:
            existing = next(
                (ln for ln in r.lines if ln.kind == kind and ln.ref == ref and not r.own_dates(ln)), None
            )
            if existing is not None:
                existing.qty += 1
            else:
                r.lines.append(RentalLine(kind, ref, 1))
        self._dirty_rentals.add(r.id)
        self.flush()
        self.rentals.build_lines()
        self.refresh()

    def rent_this(self) -> None:
        """A new quote with the open piece on it (what's attached comes along)."""
        it = self.items.it
        if it is None:
            return
        b = self.business()
        if b is None:
            self.go("rentals")
            self.edit_business(True)
            return
        self.flush()
        r = self.lib.new_rental(b)
        root = pricing.root_of(self.lib, it)
        r.lines.append(RentalLine("item", root.id, 1))
        self.lib.save_rental(r)
        self.go("upcoming")
        self.open("rentals", r.id)
        self.toast(f"Started {r.number}. Pick the renter and dates.", "done")

    def _item_edited(self, it: Item) -> None:
        it.updated = now_iso()
        self._dirty_items = True
        self._save_timer.start()
        self._table_timer.start()

    def _structure_changed(self) -> None:
        self._dirty_items = True
        self._save_timer.start()
        self._table_timer.start()

    def _package_edited(self, p: Package) -> None:
        p.updated = now_iso()
        self._dirty_packages = True
        self._save_timer.start()
        self._table_timer.start()

    def _rental_edited(self, r: Rental) -> None:
        self._dirty_rentals.add(r.id)
        self._save_timer.start()
        self._table_timer.start()

    def flush(self) -> None:
        """Write anything edited, now, and anything that couldn't be written before. A write that fails is
        kept in memory (lib.unsaved) and said in a banner until it works."""
        had_problem = bool(self.lib.unsaved)
        try:
            if self.lib.unsaved:
                self.lib.save_again()
            if self._dirty_items:
                self.lib.save_items()
                self._dirty_items = False
            if self._dirty_packages:
                self.lib.save_packages()
                self._dirty_packages = False
            for rid in list(self._dirty_rentals):
                r = self.lib.rentals.get(rid)
                if r is not None:
                    self.lib.save_rental(r)
                self._dirty_rentals.discard(rid)
        except OSError:
            pass  # the store kept what failed (lib.unsaved), and the banner says so
        self.show_save_state(had_problem)
        if self.history is not None:
            self.history.mark()

    def show_save_state(self, had_problem: bool = False) -> None:
        """Not saved: a banner across the top (back each time a save fails again), "Not Saved" in the profile
        card, and another try every little while. Saved again: all of that goes, with a word that it worked."""
        unsaved = bool(self.lib.unsaved)
        if unsaved:
            self.banner.say(
                "Your latest changes aren't saved: Bodega can't write to its folder. Check that there's free space "
                "on this computer; Bodega keeps trying."
            )
            if not self._retry_timer.isActive():
                self._retry_timer.start()
        else:
            self.banner.hide()
            self._retry_timer.stop()
            if had_problem:
                self.toast("Saved.", "done")
        if unsaved != self._was_unsaved:
            self._was_unsaved = unsaved
            self.sidebar.show_who()

    def try_saving_again(self) -> None:
        self.flush()
        if self.lib.unsaved:
            self.toast("Still not saved.", "problem")

    def edit_client(self, new: bool, assign: bool = True) -> None:
        r = self.rentals.r if kind_of(self.view_key) == "rentals" else None
        current = None
        if not new and r is not None and not r.client.is_blank():
            saved = self.lib.clients.get(r.client.id)
            current = replace(saved) if saved else replace(r.client)
        d = ClientDialog(current, current is not None and current.id in self.lib.clients, parent=self)
        if d.exec() != ClientDialog.DialogCode.Accepted:
            return
        self.flush()
        if d.deleted:
            self.lib.delete_client(d.client.id)
            self.rentals.refresh_clients()
            return
        c = self.lib.save_client(d.client)
        if r is not None and assign:
            self.rentals.use_client(c)
        else:
            self.toast(f"Saved {c.name or c.company}.", "done")
            self.rentals.refresh_clients()
        self.refresh()

    def _on_rental(self) -> bool:
        return self.rentals.r is not None and kind_of(self.view_key) == "rentals" and self.dock.opened

    def edit_business(self, add: bool) -> None:
        """Your profile, in Settings › Profiles (a new one when `add`, or the one the open rental uses)."""
        first = not self.lib.businesses
        start = None
        if not add:
            b = self.rentals.current_business() if self._on_rental() else self.business()
            start = b.id if b is not None else None
        self.open_settings("profiles", profile=start, add_profile=add, for_rental=add and self._on_rental())
        if first and self.lib.businesses and kind_of(self.view_key) == "rentals":
            self.new("rentals")
        elif self.rentals.r is not None:
            self.rentals.refresh_businesses()

    def profile_start(self, b_id: str | None) -> tuple[Business | None, Business, bool]:
        """For the profile editor: (the saved profile or None for a new one, what the form starts with,
        whether it can be deleted). A new profile starts from the sheet's pricing, if a sheet had some."""
        current = self.lib.businesses.get(b_id) if b_id else None
        can_delete = (
            current is not None
            and len(self.lib.businesses) > 1
            and not any(r.business_id == current.id for r in self.lib.rentals.values())
        )
        start = current
        if current is None:
            start = Business()
            sheet = self.lib.settings.get("sheet_pricing")
            if isinstance(sheet, dict):
                start.rate_pct = str(sheet.get("rate_pct") or start.rate_pct)
                start.value_tax = str(sheet.get("value_tax") or start.value_tax)
        return current, start, can_delete

    def profile_saved(self, d: ProfileDialog, current: Business | None, for_rental: bool = False) -> str:
        """The profile editor saved (or deleted): keep it, and show it everywhere. Returns the profile's id."""
        self.flush()
        if d.deleted and current is not None:
            self.lib.delete_business(current.id)
            self.refresh()
            self.sidebar.show_who()
            return ""
        b = d.business
        if current is None:
            self.lib.add_business(b)
            log.info("added profile %s", b.name)
        else:
            self.lib.businesses[b.id] = b
            self.lib.save_businesses()
        if d.next_number:
            self.lib.set_next_number(b, d.next_number)
        self.lib.settings["business"] = b.id
        if self._on_rental():
            r = self.rentals.r
            if for_rental and current is None:
                r.business_id = b.id
            if r.business_id == b.id:
                self.lib.renumber(r)
                self._dirty_rentals.add(r.id)
                self.flush()
                self.rentals.load(r)
        if self.items.it is not None:
            self.items.load(self.items.it)
        if self.packages.pkg is not None:
            self.packages.load(self.packages.pkg)
        self.refresh()
        self.sidebar.show_who()
        return b.id

    def _defaults_saved(self, b: Business) -> None:
        self.lib.save_businesses()
        self.toast("New rentals will start with these terms.", "done")

    def _groups_changed(self, key: str, state: dict) -> None:
        groups = self.lib.settings.get("groups", {})
        groups = groups if isinstance(groups, dict) else {}
        groups[key] = state
        self.lib.settings["groups"] = groups

    # ------------------------------------------------------------------ check out / check in
    def check_rental(self, rental_id: str, back: bool) -> None:
        """Check Out… / Check In…: tick the gear, note its condition; then mark the rental Out or Returned."""
        from bodega.core.model import now_iso
        from bodega.ui.dialogs.checklist import CheckDialog

        r = self.lib.rentals.get(rental_id)
        if r is None:
            return
        self.flush()
        if not r.lines:
            self.toast("Add gear to the rental first.", "problem")
            return
        d = CheckDialog(self.lib, r, back, self)
        if d.exec() != CheckDialog.DialogCode.Accepted:
            return
        r.checks = d.rows
        if d.mark:
            if back:
                r.status, r.checked_in = "returned", now_iso()
            else:
                r.status, r.checked_out = "out", now_iso()
        self._dirty_rentals.add(r.id)
        self.flush()
        if self.rentals.r is r:
            self.rentals.load(r)
        self.refresh()
        if d.mark:
            self.toast(f"{r.number} is {'back' if back else 'out'}.", "done")
