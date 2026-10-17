"""Making, copying, deleting and editing gear, kits, rentals, renters and profiles.

A part of MainWindow (see main_window.py); it uses the window's widgets and the library."""

from __future__ import annotations

from dataclasses import replace

from bodega.core import money, pricing, settings, words
from bodega.core.log import get_logger
from bodega.core.model import (
    HOLD_VERBS,
    Business,
    Client,
    Item,
    Package,
    PackageLine,
    Rental,
    RentalLine,
    new_id,
    now_iso,
)
from bodega.ui.components.panels import Act
from bodega.ui.components.widgets import one_stop
from bodega.ui.dialogs.client import ClientDialog
from bodega.ui.dialogs.common import confirm
from bodega.ui.dialogs.gear_picker import GearPicker
from bodega.ui.dialogs.profile import ProfileDialog
from bodega.ui.window.common import kind_of
from bodega.ui.window.tables import ID

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
        elif kind == "renters":
            c = self.edit_client(True, assign=False)  # (a new renter is a sheet: kept only once you save it)
            if c is not None and kind_of(self.view_key) == "renters":
                self.open("renters", c.id)
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

    def new_here(self) -> None:
        """N (and ⌘N): this page's new thing (a piece on gear pages, a kit on Kits, a rental on rentals, a renter
        on Renters)."""
        self.new(kind_of(self.view_key))

    def edit_open(self) -> None:
        """E: the record on screen, ready to type in (what's marked in the list opens first); the cursor goes to
        its first field, as it does in a new one."""
        kind = kind_of(self.view_key)
        panel, field = {
            "gear": (self.items, "it"),
            "packages": (self.packages, "pkg"),
            "rentals": (self.rentals, "r"),
            "renters": (self.renters, "c"),
        }[kind]
        if getattr(panel, field) is None or not self.dock.opened or self.assistant_showing():
            t = self._table()
            row = t.currentItem() if t is not None else None
            if row is None or row not in list(t.showing_rows()):
                return
            self.open(kind, row.data(0, ID))
        if kind == "renters":
            first = self.renters.editor.name if self.renters.editor is not None else None
        else:
            first = {"gear": self.items.name, "packages": self.packages.name, "rentals": self.rentals.client}[kind]
        if first is not None and first.isEnabled():
            first.setFocus()

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
        cur = {"gear": self.items.it, "packages": self.packages.pkg, "rentals": self.rentals.r}.get(kind)
        if cur is not None:  # (a renter isn't copied: two of the same person would only confuse)
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
        if kind == "renters":
            self.delete_renters([obj_id])
            return
        # deleted at once, with Undo (the standard's 4.19: never ask about what can be taken back)
        if kind == "packages":
            p = self.lib.packages.get(obj_id)
            if p is None:
                return
            self.lib.delete_package(obj_id)
            self.packages.pkg = None
            said = f"Deleted {p.name or 'the kit'}. The gear in it stays."
        else:
            r = self.lib.rentals.get(obj_id)
            if r is None:
                return
            if not r.deletable():
                self.cancel_rental(r)
                return
            self._dirty_rentals.discard(obj_id)
            self.lib.delete_rental(obj_id)
            self.rentals.r = None
            said = f"Deleted {r.number}."
        self.go(self.view_key)
        self.toast_undo(said)

    def delete_many(self, kind: str, ids: list[str]) -> None:
        """Delete what's ticked: kits, or the quotes among ticked rentals (a booked rental is cancelled, never
        deleted, so those stay as they are), at once, with one Undo."""
        if kind == "gear":
            self.delete_gear(ids)
            return
        if kind == "renters":
            self.delete_renters(ids)
            return
        self.flush()
        if kind == "packages":
            gone = [i for i in ids if i in self.lib.packages]
            what = (self.lib.packages[gone[0]].name or "the kit") if len(gone) == 1 else words.count(len(gone), "kit")
            for i in gone:
                self.lib.delete_package(i)
            if self.packages.pkg is not None and self.packages.pkg.id in gone:
                self.packages.pkg = None
            said = f"Deleted {what}. The gear in {'it' if len(gone) == 1 else 'them'} stays."
        else:
            gone = [i for i in ids if i in self.lib.rentals and self.lib.rentals[i].deletable()]
            for i in gone:
                self._dirty_rentals.discard(i)
                self.lib.delete_rental(i)
            if self.rentals.r is not None and self.rentals.r.id in gone:
                self.rentals.r = None
            said = f"Deleted {words.count(len(gone), 'quote')}."
        if not gone:
            return
        self.go(self.view_key)
        self.toast_undo(said)

    def may_hold(self, r, status: str) -> bool:
        """Booking or marking out gear that's already promised (or in repair) asks first: a sub-rental can
        make it deliberate. True to go ahead."""
        shorts = pricing.shortages(self.lib, r)
        if not shorts:
            return True
        lines = [
            f"{s.item.name}: needs {s.needed}, {s.free} free ({s.why})" if s.free or s.needed > 1
            else f"{s.item.name} ({s.why})"
            for s in shorts[:3]
        ]  # fmt: skip
        more = f" And {len(shorts) - 3} more." if len(shorts) > 3 else ""
        verb = HOLD_VERBS.get(status, "Mark Out")
        return confirm(
            self,
            f"{verb} {r.number} Anyway?",
            "Some of its gear isn't free on its dates. "
            + "; ".join(lines)
            + "."
            + more
            + " Go ahead if you're renting more in to cover it.",
            f"{verb} Anyway",
            danger=False,
        )

    def cancel_rental(self, r) -> None:
        """A rental that's been booked is cancelled, never deleted: its number, prices and history stay."""
        if r.is_cancelled():
            self.toast(f"{r.number} is cancelled and kept, with its number and history.")
            return
        if not confirm(
            self,
            f"Mark {r.number} as Cancelled?",
            "Only a quote can be deleted. A rental that's been booked stays on record: cancelled, its gear is "
            "free again, and its number, prices and history are kept.",
            "Mark as Cancelled",
            danger=False,
        ):
            return
        self.flush()
        self.lib.set_status(r, "cancelled")
        self.flush()  # (marks it for undo)
        if self.rentals.r is r:
            self.rentals.load(r)
        self.refresh()
        self.toast(f"Cancelled {r.number}.", "done")

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
        on_rentals: list[str] = []  # retired instead: a piece rentals point to, with what's attached to it
        for i in everything:
            if self.lib.rentals_with(i):
                for x, _u, _d in pricing.with_attached(self.lib, self.lib.items[i], 1):
                    if x.id not in on_rentals:
                        on_rentals.append(x.id)
        if on_rentals and not self._retire_instead(on_rentals, everything):  # retiring isn't deleting: it asks
            return
        everything = [i for i in everything if i not in on_rentals]
        picked = [i for i in picked if i in everything]
        if not picked:
            return
        # deleted at once, with Undo (the standard's 4.19); what's attached goes with it, and rentals keep the names
        extra = len(everything) - len(picked)
        names = [self.lib.items[i].name or "Untitled Piece" for i in picked]
        said = f"Deleted {names[0]}" if len(picked) == 1 else f"Deleted {len(picked):,} pieces"
        if extra:
            said += f" and the {extra:,} attached" if extra != 1 or len(picked) != 1 else " and what's attached"
        keyboard = self.gear_table.hasFocus()
        shown = [r.data(0, ID) for r in self.gear_table.showing_rows()]
        gone = set(everything)
        after = [
            i for i in shown[max((n for n, i in enumerate(shown) if i in gone), default=-1) + 1 :] if i not in gone
        ]
        before = [i for i in shown if i not in gone]
        neighbour = (after or before[-1:] or [None])[0]  # the row after what went, else the one before
        n = self.lib.delete_items(everything)
        log.info("deleted %d items", n)
        self.items.it = None
        self.go(self.view_key)
        if keyboard and neighbour:  # deleted from the keyboard: the next row is where the keyboard is now
            self.gear_table.select_id(neighbour)
            self.gear_table.setFocus()
        self.toast_undo(one_stop(said + "."))

    def _retire_instead(self, ids: list[str], everything: list[str]) -> bool:
        """Gear that rentals point to is retired, not deleted (asked first). True to go on with the rest."""
        main = [i for i in ids if self.lib.items[i].parent not in ids] or ids  # attached ones go with these
        names = [self.lib.items[i].name or "Untitled Piece" for i in main]
        listed = ", ".join(names[:3]) + (f" and {len(names) - 3} more" if len(names) > 3 else "")
        rest = len([i for i in everything if i not in ids])
        n = len({r.id for i in ids for r in self.lib.rentals_with(i)})
        title = f"Retire {names[0]} Instead?" if len(main) == 1 else f"Retire {len(main)} Pieces Instead?"
        if rest:
            title = f"Retire {len(ids)} and Delete {rest}?"
        attached = len(ids) - len(main)
        text = (
            f"{listed} {'is' if len(main) == 1 else 'are'} on {n} rental{'s' if n != 1 else ''}, so "
            f"{'it stays' if len(main) == 1 else 'they stay'} on record"
            + (f", with the {attached} attached" if attached else "")
            + ": retired gear can't be booked and is left off your inventory, rate card and labels. You can "
            "bring it back by changing its status."
            + (f" The other {rest} {'is' if rest == 1 else 'are'} deleted." if rest else "")
        )
        if not confirm(self, title, text, "Retire" if not rest else "Retire and Delete", danger=bool(rest)):
            return False
        self.lib.retire(ids)
        if not rest:
            if self.items.it is not None and self.items.it.id in ids:
                self.items.load(self.items.it)
            self.refresh()
            self.toast(f"Retired {listed}.", "done")
        return True

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
            self.lib, self.lib.pricing(), f"Attach to {it.name or 'This Piece'}", "Attach",
            exclude=up | already, main_only=False, parent=self,
        )  # fmt: skip
        if d.exec() != GearPicker.DialogCode.Accepted:
            return
        n = self.lib.attach([ref for _kind, ref in d.picked], item_id)
        self.refresh()
        self.items.refresh_attached()
        self.toast(f"Attached {n} to {it.name}.", "done")

    def detach(self, item_id: str) -> None:
        if item_id not in self.lib.items:
            return
        self.lib.detach(item_id)
        self.refresh()
        if self.items.it is not None:
            self.items.load(self.items.it)

    def add_to_package(self, pkg_id: str) -> None:
        p = self.lib.packages.get(pkg_id)
        if p is None:
            return
        have = {ln.item_id for ln in p.lines}
        d = GearPicker(self.lib, self.lib.pricing(), f"Add to {p.name or 'the Kit'}", exclude=have, parent=self)
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
        d = GearPicker(self.lib, self.lib.businesses.get(r.business_id), "Add to Rental", packages=True, parent=self)
        if d.exec() != GearPicker.DialogCode.Accepted:
            return
        for kind, ref in d.picked:
            existing = next((ln for ln in r.lines if ln.kind == kind and ln.ref == ref and not r.own_dates(ln)), None)
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
        self._save_soon()
        self._table_timer.start()

    def _structure_changed(self) -> None:
        self._dirty_items = True
        self._save_soon()
        self._table_timer.start()

    def _package_edited(self, p: Package) -> None:
        p.updated = now_iso()
        self._dirty_packages = True
        self._save_soon()
        self._table_timer.start()

    def _rental_edited(self, r: Rental) -> None:
        self._dirty_rentals.add(r.id)
        self._save_soon()
        self._table_timer.start()

    def _save_soon(self) -> None:
        """Save a moment after the last change, and never later than SAVE_MAX_MS after the first one (typing
        without a pause still gets saved)."""
        self._save_timer.start()
        if not self._save_cap.isActive():
            self._save_cap.start()

    def flush(self) -> None:
        """Write anything edited, now, and anything that couldn't be written before. A write that fails is
        kept in memory (lib.unsaved) and said in a banner until it works."""
        self._save_cap.stop()
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
                    if r is self.rentals.r:
                        self.rentals.show_history()  # saving is what writes its history
                self._dirty_rentals.discard(rid)
        except OSError:
            pass  # the store kept what failed (lib.unsaved), and the banner says so
        self.show_save_state(had_problem)
        self.mark_soon()

    def show_save_state(self, had_problem: bool = False) -> None:
        """Not saved: a banner across the top (back each time a save fails again), "Not Saved" in the profile
        card, and another try every little while. Saved again: all of that goes, with a word that it worked."""
        unsaved = bool(self.lib.unsaved)
        if unsaved:
            why = (self.lib.why_unsaved or ("Bodega can't write to its folder", ""))[0]
            self.banner.say(f"Your latest changes aren't saved: {why}. Bodega keeps trying.")
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

    def tidy_renters(self) -> None:
        """Tidy Up Renters: names, companies and addresses in proper case, after a look (core/tidy_renters.py)."""
        from bodega.core import tidy_renters
        from bodega.ui.dialogs.common import tidy_renters_preview

        self.flush()
        found = tidy_renters.changes(self.lib.clients)
        if not found:
            self.toast("Your renters are already tidy.")
            return
        names = {c.id: c.name or c.company or "Renter" for c in self.lib.clients.values()}
        if not tidy_renters_preview(self, found, names):
            return
        n = self.lib.tidy_clients(found)
        self.refresh()
        self.toast(f"Tidied {words.count(n, 'renter')}.", "done")

    def edit_client(self, new: bool, assign: bool = True) -> Client | None:
        """A renter: a new one fills in a sheet; one you've saved opens on the Renters page, edited in place.
        Returns the renter saved from the sheet (None if it was closed)."""
        r = self.rentals.r if kind_of(self.view_key) == "rentals" else None
        current = None
        if not new and r is not None and not r.client.is_blank():
            if r.client.id in self.lib.clients:
                self.open("renters", r.client.id)
                return None
            current = replace(r.client)  # (one this rental only has: kept as a renter once you save it)
        d = ClientDialog(current, False, parent=self)
        if d.exec() != ClientDialog.DialogCode.Accepted:
            return None
        self.flush()
        c = self.lib.save_client(d.client)
        if r is not None and assign:
            self.rentals.use_client(c)
        else:
            self.toast(f"Saved {c.name or c.company}.", "done")
            self.rentals.refresh_clients()
        self.refresh()
        return c

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
            start = self.lib.with_sheet_pricing(Business())  # a sheet's pricing, if one came before a profile
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
            log.info("added a profile")
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
        groups = settings.value(self.lib.settings, "groups")
        groups[key] = state
        self.lib.settings["groups"] = groups

    # What a record can do
    def record_acts(self, kind: str, obj_id: str) -> list[Act]:
        """Everything a piece, kit or rental can do, in one list: its row's menu shows them all, its panel shows
        the next step and Print beside its ⋯, and the rest in it (the standard's 4.5, C-65). Only what applies."""
        if kind == "gear":
            it = self.lib.items.get(obj_id)
            if it is None:
                return []
            return [
                *(
                    [Act("plus", "Rent This", lambda: (self.open("gear", obj_id), self.rent_this()), "step")]
                    if it.can_rent()
                    else []
                ),
                Act("copy", "Duplicate", lambda: self.duplicate("gear", obj_id)),
                *([Act("unlink", "Make It Its Own Piece", lambda: self.detach(obj_id))] if it.parent else []),
                Act("assistant", "Update with AI…", lambda: self.ai_this_piece(obj_id)),
                Act("", "-"),
                Act("trash", "Delete", lambda: self.delete("gear", obj_id)),
            ]
        if kind == "renters":
            if obj_id not in self.lib.clients:
                return []
            return [Act("trash", "Delete", lambda: self.delete_renters([obj_id]))]
        if kind == "packages":
            if obj_id not in self.lib.packages:
                return []
            return [
                Act("printer", "Kit Sheet…", lambda: self.show_pages(("kit", obj_id)), "print"),
                Act("copy", "Duplicate", lambda: self.duplicate("packages", obj_id)),
                Act("", "-"),
                Act("trash", "Delete", lambda: self.delete("packages", obj_id)),
            ]
        r = self.lib.rentals.get(obj_id)
        if r is None:
            return []
        acts = [Act("printer", "Agreement…", lambda: self.show_pages(("rental", obj_id)), "print")]
        if r.is_booked():  # its next step (the Rental menu's rule: booked goes out, out comes back)
            acts.append(Act("check", "Check Out…", lambda: self.check_rental(obj_id, False), "step"))
        elif r.is_out():
            acts.append(Act("check", "Check In…", lambda: self.check_rental(obj_id, True), "step"))
        acts += [
            Act("copy", "Duplicate", lambda: self.duplicate("rentals", obj_id)),
            Act("calendar", "Add to Calendar", lambda: self.add_to_calendar(obj_id)),
            Act("receipt", "Send to Saldo…", lambda: self.send_to_saldo(obj_id)),
            Act("", "-"),
        ]
        if r.deletable():
            acts.append(Act("trash", "Delete", lambda: self.delete("rentals", obj_id)))
        elif not r.is_cancelled():  # a booked rental is cancelled, never deleted
            acts.append(Act("x", "Mark as Cancelled…", lambda: self.cancel_rental(r)))
        return acts

    # Check out / check in
    def can_check(self, ids: list[str], back: bool) -> list[Rental]:
        """Of these rentals, the ones that can take the next step: booked ones go out, ones that are out come back."""
        rs = [self.lib.rentals[i] for i in ids if i in self.lib.rentals]
        return [r for r in rs if (r.is_out() if back else r.is_booked())]

    def check_many(self, ids: list[str], back: bool) -> None:
        """Check Out or Check In for the ticked rentals at once (the standard's 4.17): the ones that can take it,
        asked once with how many, what they come to and how many stay as they are. Gear that isn't free is asked
        about for the batch as a whole. Each rental's own Check Out… still has its checklist."""
        can = self.can_check(ids, back)
        if not can:
            return
        self.flush()
        n = words.count(len(can), "Rental")
        verb = "Check In" if back else "Check Out"
        sums = [(pricing.totals(self.lib, r, self.lib.businesses.get(r.business_id)), self._currency(r)) for r in can]
        text = f"{'They come back' if back else 'They go out'} now"
        if len({cur for _t, cur in sums}) == 1:  # (one currency: what they come to)
            text += f", {money.fmt(sum((t.total for t, _c in sums), money.ZERO), sums[0][1])} in all"
        text += "."
        left = len([i for i in ids if i in self.lib.rentals]) - len(can)
        if left:
            text += f" {'The other one stays' if left == 1 else f'The other {left:,} stay'} as {'it is' if left == 1 else 'they are'}."
        short = [] if back else [r for r in can if pricing.shortages(self.lib, r)]
        if short:
            text += (
                f" {len(short):,} of them {'has' if len(short) == 1 else 'have'} gear that "
                "isn't free on its dates. Go ahead if you're renting more in to cover it."
            )
        if not confirm(self, f"{verb} {n}?", text, f"{verb} {n}", danger=False):
            return
        for r in can:
            self.lib.set_status(r, "returned" if back else "out")
        self.flush()  # (marks it for undo)
        if self.rentals.r in can:
            self.rentals.load(self.rentals.r)
        self.refresh()
        self.toast_undo(f"{n} {'back' if back else 'out'}.")

    def _currency(self, r: Rental) -> str:
        b = self.lib.businesses.get(r.business_id) or self.lib.pricing()
        return (b.currency if b else "$") or "$"

    def check_rental(self, rental_id: str, back: bool) -> None:
        """Check Out… / Check In…: tick the gear, note its condition; then mark the rental Out or Returned."""
        from bodega.ui.dialogs.checklist import CheckDialog

        r = self.lib.rentals.get(rental_id)
        if r is None:
            return
        self.flush()
        if not r.lines:
            self.toast("Add gear to the rental first.", "problem")
            return
        d = CheckDialog(self.lib, r, back, self)

        def keep(rows: list) -> None:  # each tick, note and photo, kept on the rental as it's made
            r.checks = [replace(c, photos=list(c.photos)) for c in rows]
            self._rental_edited(r)

        d.edited.connect(keep)
        d.exec()
        r.checks = d.rows
        if d.mark and (back or r.is_out() or self.may_hold(r, "out")):
            self.lib.set_status(r, "returned" if back else "out")
        self._dirty_rentals.add(r.id)
        self.flush()
        if self.rentals.r is r:
            self.rentals.load(r)
        self.refresh()
        if d.mark:
            self.toast(f"{r.number} is {'back' if back else 'out'}.", "done")
