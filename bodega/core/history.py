"""Undo and redo for what you keep in Bodega: gear, kits, rentals, renters, profiles and your groups.

The window calls mark() whenever things settle (after a save or a refresh). If anything changed since the last
mark, the state before it becomes one undo step. Undo puts that state back and saves it. A change that's taken
straight back (a new piece dropped before you filled it in) leaves no step behind.

Window things (what's open, folded, the look) aren't undone; neither are app settings. No Qt here.
"""

from __future__ import annotations

from typing import Any

from bodega.core.model import Business, Client, Item, Package, Rental

LIMIT = 100  # steps kept

State = dict[str, Any]


def state_of(lib) -> State:
    rentals = {}
    for rid, r in lib.rentals.items():
        d = r.to_dict()
        d.pop("updated", None)  # saving stamps the time; that alone isn't a change
        rentals[rid] = d
    groups = lib.settings.get("group_list")
    return {
        "items": [i.to_dict() for i in lib.items.values()],
        "packages": [p.to_dict() for p in lib.packages.values()],
        "clients": [c.to_dict() for c in lib.clients.values()],
        "businesses": [b.to_dict() for b in lib.businesses.values()],
        "rentals": rentals,
        "groups": list(groups) if isinstance(groups, list) else None,
    }


def shared(new: State, old: State) -> State:
    """`new`, with every record that's the same as it was in `old` swapped for old's own copy: undo steps share
    what didn't change, so a hundred of them cost little more than one (at 3,000 pieces: about 3 MB a step
    otherwise)."""
    out = dict(new)
    for key in ("items", "packages", "clients", "businesses"):
        before = {d.get("id"): d for d in old.get(key) or []}
        out[key] = [before[d.get("id")] if before.get(d.get("id")) == d else d for d in new[key]]
    before = old.get("rentals") or {}
    out["rentals"] = {rid: before[rid] if before.get(rid) == d else d for rid, d in new["rentals"].items()}
    return out


KINDS = [  # (key, kind as the window opens it, one, many, its name in a record) in the order an action is named by
    ("items", "gear", "piece", "pieces", lambda d: d.get("name") or "Untitled Piece"),
    ("rentals", "rentals", "rental", "rentals", lambda d: d.get("number") or "Rental"),
    ("packages", "packages", "kit", "kits", lambda d: d.get("name") or "Untitled Kit"),
    ("clients", "", "renter", "renters", lambda d: d.get("company") or d.get("name") or "Renter"),
    ("businesses", "", "profile", "profiles", lambda d: d.get("name") or "Profile"),
]
NAME_MAX = 32  # a record's name in Undo's menu item is cut to this


def _by_id(s: State, key: str) -> dict:
    got = s.get(key) or {}
    return dict(got) if isinstance(got, dict) else {d.get("id"): d for d in got}


def action(before: State, after: State) -> tuple[str, tuple[str, str] | None]:
    """What was done to go from `before` to `after`, as Undo names it ("Delete Sony FX6", "Change to JLF-2026-001",
    "Add 3 Pieces", "Change to Groups"), and the one record it was about (kind, id) when there was one."""
    found = []
    for key, kind, one, many, name_of in KINDS:
        a, b = _by_id(before, key), _by_id(after, key)
        added = [i for i in b if i not in a]
        gone = [i for i in a if i not in b]
        changed = [i for i in b if i in a and a[i] != b[i]]
        for verb, ids, where in (("Delete", gone, a), ("Add", added, b), ("Change to", changed, b)):
            if ids:
                found.append((verb, ids, where, kind, one, many, name_of))
    if not found:
        return ("Change to Groups" if before.get("groups") != after.get("groups") else "Change"), None
    # what you did first, the rest following from it: a deletion or an addition before a change it made elsewhere
    verb, ids, where, kind, one, many, name_of = next((f for f in found if f[0] != "Change to"), found[0])
    if len(ids) == 1:
        name = " ".join(name_of(where[ids[0]]).split())
        name = name if len(name) <= NAME_MAX else name[: NAME_MAX - 1].rstrip() + "…"
        return f"{verb} {name}", ((kind, ids[0]) if kind and verb != "Delete" else None)
    return (
        f"{verb} {len(ids):,} {many.title()}" if verb != "Change to" else f"Changes to {len(ids):,} {many.title()}",
        None,
    )


class History:
    def __init__(self, lib):
        self.lib = lib
        self.undos: list[State] = []
        self.redos: list[State] = []
        self.last = state_of(lib)
        self.shown: tuple[str, str] | None = None  # the record the last undo or redo brought back, to show it

    def mark(self) -> bool:
        """Note where things stand. True if that made a new undo step."""
        now = state_of(self.lib)
        if now == self.last:
            return False
        if self.undos and self.undos[-1] == now:  # taken straight back: no step either way
            self.undos.pop()
            self.last = now
            return False
        self.undos.append(self.last)
        del self.undos[:-LIMIT]
        self.redos.clear()
        self.last = shared(now, self.last)
        return True

    def can_undo(self) -> bool:
        return bool(self.undos) or state_of(self.lib) != self.last

    def can_redo(self) -> bool:
        return bool(self.redos)

    def undo_names(self) -> str:
        """What Undo would take back ("Delete Sony FX6", "Change to 3 Pieces"), or '' if nothing."""
        now = state_of(self.lib)
        if now != self.last:
            return action(self.last, now)[0]
        return action(self.undos[-1], self.last)[0] if self.undos else ""

    def redo_names(self) -> str:
        """What Redo would do again, or ''."""
        return action(self.last, self.redos[-1])[0] if self.redos else ""

    def undo(self) -> str | None:
        """Go back one step; what changed back (for a toast), or None if there's nothing to undo."""
        self.mark()
        if not self.undos:
            return None
        before = self.undos.pop()
        self.redos.append(self.last)
        what, about = action(before, self.last)
        if what.startswith("Delete "):  # a deletion taken back: what came back is the thing to show
            about = action(self.last, before)[1]
        elif what.startswith("Add "):  # an addition taken back: it's gone, nothing to show
            about = None
        self.shown = about
        self._put(before)
        return what

    def redo(self) -> str | None:
        if not self.redos:
            return None
        self.mark()  # (nothing new can have happened since an undo without clearing redos)
        if not self.redos:
            return None
        after = self.redos.pop()
        self.undos.append(self.last)
        what, self.shown = action(self.last, after)
        self._put(after)
        return what

    def _put(self, s: State) -> None:
        """Make the library this state, and save it: only the parts that differ from how things stand (`last`:
        undo and redo mark first), so taking back one rental's change rewrites that rental, not the whole gear list
        (at a rental house's size that was most of an undo's time)."""
        lib, now = self.lib, self.last
        if s["items"] != now["items"]:
            lib.items = {d["id"]: Item.from_dict(d) for d in s["items"]}
            lib.save_items()
        if s["packages"] != now["packages"]:
            lib.packages = {d["id"]: Package.from_dict(d) for d in s["packages"]}
            lib.save_packages()
        if s["clients"] != now["clients"]:
            lib.clients = {d["id"]: Client.from_dict(d) for d in s["clients"]}
            lib.save_clients()
        if s["businesses"] != now["businesses"]:
            lib.businesses = {d["id"]: Business.from_dict(d) for d in s["businesses"]}
            lib.save_businesses()
        old = now["rentals"]
        for rid in list(lib.rentals):
            if rid not in s["rentals"]:
                lib.delete_rental(rid)
        for rid, d in s["rentals"].items():
            if old.get(rid) != d:
                lib.save_rental(Rental.from_dict(d))
        if s["groups"] != now["groups"]:
            if s["groups"] is None:
                lib.settings.pop("group_list", None)
            else:
                lib.settings["group_list"] = list(s["groups"])
            lib.save_settings()
        self.last = shared(state_of(lib), s)
