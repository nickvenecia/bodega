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


PARTS = [  # (key, a few words for a toast)
    ("items", "gear"),
    ("packages", "kits"),
    ("rentals", "rentals"),
    ("clients", "renters"),
    ("businesses", "profiles"),
    ("groups", "groups"),
]


def describe(a: State, b: State) -> str:
    """What differs between two states, in a few words: "gear", "gear and rentals"."""
    parts = [words for key, words in PARTS if a.get(key) != b.get(key)]
    if not parts:
        return "a change"
    if a["items"] != b["items"] and len(a["items"]) != len(b["items"]):
        n = abs(len(a["items"]) - len(b["items"]))
        parts[parts.index("gear")] = f"{n} piece{'s' if n != 1 else ''} of gear"
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]


class History:
    def __init__(self, lib):
        self.lib = lib
        self.undos: list[State] = []
        self.redos: list[State] = []
        self.last = state_of(lib)

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
        self.last = now
        return True

    def can_undo(self) -> bool:
        return bool(self.undos) or state_of(self.lib) != self.last

    def can_redo(self) -> bool:
        return bool(self.redos)

    def undo_names(self) -> str:
        """What Undo would change back ("gear", "2 pieces of gear"), or '' if nothing."""
        now = state_of(self.lib)
        if now != self.last:
            return describe(now, self.last)
        return describe(self.last, self.undos[-1]) if self.undos else ""

    def redo_names(self) -> str:
        return describe(self.last, self.redos[-1]) if self.redos else ""

    def undo(self) -> str | None:
        """Go back one step; what changed back (for a toast), or None if there's nothing to undo."""
        self.mark()
        if not self.undos:
            return None
        before = self.undos.pop()
        self.redos.append(self.last)
        what = describe(self.last, before)
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
        what = describe(self.last, after)
        self._put(after)
        return what

    def _put(self, s: State) -> None:
        """Make the library this state, and save it."""
        lib = self.lib
        lib.items = {d["id"]: Item.from_dict(d) for d in s["items"]}
        lib.packages = {d["id"]: Package.from_dict(d) for d in s["packages"]}
        lib.clients = {d["id"]: Client.from_dict(d) for d in s["clients"]}
        lib.businesses = {d["id"]: Business.from_dict(d) for d in s["businesses"]}
        old = state_of(lib)["rentals"] if lib.rentals else {}
        for rid in list(lib.rentals):
            if rid not in s["rentals"]:
                lib.delete_rental(rid)
        for rid, d in s["rentals"].items():
            if old.get(rid) != d:
                lib.save_rental(Rental.from_dict(d))
        if s["groups"] is None:
            lib.settings.pop("group_list", None)
        else:
            lib.settings["group_list"] = list(s["groups"])
        lib.save_items()
        lib.save_packages()
        lib.save_clients()
        lib.save_businesses()
        lib.save_settings()
        self.last = state_of(lib)
