"""Saving and loading: everything lives as small JSON files in Bodega's data folder.

    gear.json          every item (one file: a few hundred items is still small)
    packages.json      your packages
    rentals/<id>.json  one file per rental
    clients.json       your saved renters
    businesses.json    your profile(s)
    settings.json      window and app preferences

Every write goes to a temp file next to the real one, then replaces it in one step, so a crash
or a full disk never leaves a half-written file. A file that can't be read is set aside as
<name>.unreadable-<time> (never deleted) and logged.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import time
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

from bodega.core import dates
from bodega.core.log import get_logger
from bodega.core.model import Business, Client, Item, Package, Rental, RentalLine, new_id, now_iso
from bodega.core.paths import data_dir

log = get_logger(__name__)

DEFAULT_TERMS = """Rental period. The rental starts when the gear is picked up and ends when all of it is back with {owner}. Gear returned late is billed at its day rate for every extra day.

Care and use. The renter will use the gear with care, by people who know how to use it, for the production named above. No lending, sub-renting, or taking the gear outside the United States without written permission.

Loss and damage. From pickup until return, the renter is responsible for the gear, including loss, theft and damage, and pays for repairs or the replacement value listed above.

Insurance. Before pickup, the renter sends a certificate of insurance covering the full replacement value, naming {owner} as loss payee and additional insured.

Checking the gear. The renter checks the gear at pickup. Anything missing or not working must be reported within 24 hours, or the gear is taken as complete and working.

Cancellation. Cancelling less than 48 hours before pickup is billed one day's rent.

Payment and deposit. Rent is due at pickup. The security deposit is returned within 7 days of the gear coming back complete and undamaged, less any charges under this agreement.

Agreement. Signing below means the renter has read and accepts these terms."""
DEFAULT_NOTE = "Thanks for renting with us."


def write_json(path: Path, data: Any) -> None:
    """Write atomically: a temp file in the same folder, then os.replace."""
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2))


def write_text(path: Path, text: str) -> None:
    """Write a text file atomically: a temp file in the same folder, then os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            log.warning("couldn't remove %s", tmp, exc_info=True)
        raise


# The data folder's format, kept in settings.json ("format"). Raise it when a file's shape changes, with a step
# in UPGRADES that brings a folder from the version before up to it (each step one version, each with a test).
# Files from before formats were written are format 1.
FORMAT = 1
UPGRADES: dict[int, Callable[[Library], None]] = {}  # from this version to the next

ID_OK = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def safe_id(text: str) -> bool:
    """Ids name files (rentals/<id>.json): letters, digits, - and _ only."""
    return bool(ID_OK.match(str(text or "")))


def set_aside(path: Path, why: str, copy: bool = False) -> None:
    """Keep a file we couldn't use as <name>.<why>-<time>, so nothing is ever lost. `copy` leaves the
    original in place (when the good parts of it are still being used)."""
    aside = path.with_name(f"{path.name}.{why}-{int(time.time())}")
    log.warning("couldn't use all of %s; kept a copy as %s", path, aside.name)
    try:
        if copy:
            aside.write_bytes(path.read_bytes())
        else:
            path.replace(aside)
    except OSError:
        log.warning("couldn't set %s aside", path, exc_info=True)


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        log.warning("couldn't read %s", path, exc_info=True)
        set_aside(path, "unreadable")
        return default


def initials(name: str) -> str:
    """ "Juniper Lane Films" -> "JLF"; a single word -> its first three letters."""
    words = [w for w in re.split(r"[^A-Za-z0-9]+", name) if w]
    if not words:
        return "RENT"
    if len(words) == 1:
        return words[0][:3].upper()
    return "".join(w[0] for w in words[:4]).upper()


def clean_prefix(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", text).upper()[:8]


NUMBER = re.compile(r"^([A-Za-z0-9]{1,8})-(\d{4})-(\d{1,6})$")  # a rental number: PREFIX-YEAR-001


def terms_for(b: Business) -> str:
    who = b.name.strip() or "the owner"
    return (b.terms or DEFAULT_TERMS).replace("{owner}", who)


class Library:
    """Everything Bodega knows, loaded from the data folder and saved back file by file."""

    def __init__(self, root: Path | None = None):
        self.root = root or data_dir()
        self.items: dict[str, Item] = {}
        self.packages: dict[str, Package] = {}
        self.rentals: dict[str, Rental] = {}
        self.clients: dict[str, Client] = {}
        self.businesses: dict[str, Business] = {}
        self.settings: dict[str, Any] = {}
        # what couldn't be written last time ("gear", "kits", "renters", "profiles", "settings" or a rental's
        # id): still in memory, tried again by save_again(). on_unsaved is told the moment a write fails.
        self.unsaved: set[str] = set()
        self.on_unsaved: Callable[[], None] | None = None
        self.newer_format = False

    # ------------------------------------------------------------------ files
    @property
    def _rental_dir(self) -> Path:
        return self.root / "rentals"

    def load(self) -> Library:
        def build(cls, d: dict):
            """A record -> its object, or None if it's broken. A bad id (ids name files) gets a new one."""
            try:
                obj = cls.from_dict(d)
            except (TypeError, ValueError, AttributeError, KeyError, OverflowError, ArithmeticError):
                log.warning("skipped a broken %s record", cls.__name__, exc_info=True)
                return None
            if not safe_id(obj.id):
                obj.id = new_id()
            return obj

        def many(name: str, cls) -> dict:
            path = self.root / name
            raw = read_json(path, [])
            if not isinstance(raw, list):  # the wrong shape: keep it aside rather than save over it
                set_aside(path, "unreadable")
                return {}
            out = {}
            for d in raw:
                obj = build(cls, d) if isinstance(d, dict) else None
                if obj is None:
                    continue
                out[obj.id] = obj
            if len(out) < len(raw):  # some records couldn't be read: keep the whole file as it was
                set_aside(path, "partly-unreadable", copy=True)
            return out

        self.items = many("gear.json", Item)
        self.packages = many("packages.json", Package)
        self.clients = many("clients.json", Client)
        self.businesses = many("businesses.json", Business)
        self.rentals = {}
        if self._rental_dir.is_dir():
            for f in sorted(self._rental_dir.glob("*.json")):
                data = read_json(f, None)
                r = build(Rental, data) if isinstance(data, dict) else None
                if r is None:
                    if f.exists():
                        set_aside(f, "unreadable")
                    continue
                if f.stem != r.id:  # saved under its id from now on
                    r.id = f.stem if safe_id(f.stem) else r.id
                self.rentals[r.id] = r
        s = read_json(self.root / "settings.json", {})
        self.settings = s if isinstance(s, dict) else {}
        fmt = self.settings.get("format")
        fmt = fmt if isinstance(fmt, int) and not isinstance(fmt, bool) and fmt >= 1 else 1
        self.newer_format = fmt > FORMAT  # saved by a newer Bodega: what it added is kept as it was
        self._upgrade(fmt)
        for b in self.businesses.values():  # a logo is a file name in the logos folder, nothing more
            b.logo = Path(b.logo).name if b.logo else ""
        self.untangle()
        self._settle_rentals()
        log.info(
            "loaded %d items, %d packages, %d rentals, %d renters from %s",
            len(self.items), len(self.packages), len(self.rentals), len(self.clients), self.root,
        )  # fmt: skip
        return self

    def _upgrade(self, fmt: int) -> None:
        """A folder from an older format, brought up one version at a time and saved (a safety copy first)."""
        if fmt >= FORMAT:
            return
        from bodega.core import backups

        backups.safety_copy(self.root, f"before-format-{FORMAT}")
        for v in range(fmt, FORMAT):
            UPGRADES[v](self)
            log.info("data folder upgraded from format %d to %d", v, v + 1)
        try:
            self.save_items()
            self.save_packages()
            self.save_clients()
            self.save_businesses()
            for r in self.rentals.values():
                self.save_rental(r)
            self.save_settings()
        except OSError:
            pass  # kept as unsaved, and tried again with the next save

    def _settle_rentals(self) -> None:
        """Rentals booked before prices locked at booking: lock them now, at today's prices."""
        from bodega.core import pricing

        for r in self.rentals.values():
            if r.status in pricing.LOCKED and pricing.settle(
                self, r, self.businesses.get(r.business_id) or self.pricing()
            ):
                try:
                    self._write(r.id, self._rental_dir / f"{r.id}.json", r.to_dict())
                except OSError:
                    pass  # kept as unsaved, and tried again with the next save

    def untangle(self) -> None:
        """An item can't belong to something that's gone, to itself, or (through others) to itself."""
        for it in self.items.values():
            seen = {it.id}
            p = it.parent
            while p:
                if p not in self.items or p in seen:
                    it.parent = ""
                    break
                seen.add(p)
                p = self.items[p].parent

    def snapshot(self, why: str) -> Path | None:
        """A safety copy of every record before a big change (an import, an AI's edits): see core/backups.py.
        None if there's nothing yet or it couldn't be written."""
        from bodega.core import backups

        return backups.safety_copy(self.root, why)

    def restore(self, backup) -> Path | None:
        """Put a backup (core/backups.read_backup) back in place of everything, after a safety copy of how
        things are now (returned, so it can be put back in turn). Numbers given since stay spent."""
        from bodega.core import backups

        for r in self.rentals.values():
            self._spend_number(r.number)
        spent = self._spent()
        kept = backups.safety_copy(self.root, "before-restore")
        backups.put_back(self.root, backup)
        self.unsaved.clear()
        self.load()
        for series, n in spent.items():
            self._spend(series, n)
        return kept

    def _write(self, what: str, path: Path, data: Any) -> None:
        """Write one file; if it fails, remember it as unsaved (and say so) before the error goes on up."""
        try:
            write_json(path, data)
        except OSError:
            log.warning("couldn't save %s", what, exc_info=True)
            self.unsaved.add(what)
            if self.on_unsaved is not None:
                self.on_unsaved()
            raise
        self.unsaved.discard(what)

    def save_again(self) -> bool:
        """Write again everything that couldn't be written. True once nothing is left unsaved."""
        for what in sorted(self.unsaved):
            save = {
                "gear": self.save_items,
                "kits": self.save_packages,
                "renters": self.save_clients,
                "profiles": self.save_businesses,
                "settings": self.save_settings,
            }.get(what)
            try:
                if save is not None:
                    save()
                elif (r := self.rentals.get(what)) is not None:
                    self.save_rental(r)
                else:  # a rental that's gone since (deleted, or undone)
                    self.unsaved.discard(what)
            except OSError:
                return False
        return not self.unsaved

    def save_items(self) -> None:
        self._write("gear", self.root / "gear.json", [i.to_dict() for i in self.items.values()])

    def save_packages(self) -> None:
        self._write("kits", self.root / "packages.json", [p.to_dict() for p in self.packages.values()])

    def save_clients(self) -> None:
        clients = sorted(self.clients.values(), key=lambda c: c.name.casefold())
        self._write("renters", self.root / "clients.json", [c.to_dict() for c in clients])

    def save_businesses(self) -> None:
        self._write(
            "profiles", self.root / "businesses.json", [b.to_dict() for b in self.businesses.values()]
        )

    def save_rental(self, r: Rental) -> None:
        from bodega.core import pricing

        pricing.settle(self, r, self.businesses.get(r.business_id) or self.pricing())  # booked: prices hold
        r.updated = now_iso()
        self.rentals[r.id] = r
        self._write(r.id, self._rental_dir / f"{r.id}.json", r.to_dict())

    def save_settings(self) -> None:
        fmt = self.settings.get("format")
        newer = fmt if isinstance(fmt, int) and not isinstance(fmt, bool) else 0
        self.settings["format"] = max(FORMAT, newer)  # never says older than what wrote the folder
        self._write("settings", self.root / "settings.json", self.settings)

    # ------------------------------------------------------------------ gear
    # ------------------------------------------------------------------ groups
    # Groups (Cameras, Lenses, Grip…) are how gear is organised: one per piece. Their order is saved in
    # settings ("group_list"), so you can make empty ones, rename and reorder them. A sheet's departments
    # (Camera, G&E…) are kept on each piece but only used while importing.
    def groups(self) -> list[str]:
        """Every group, in your order (new ones after, in the order they were first used)."""
        order = self.settings.get("group_list")
        seen = [g for g in order if isinstance(g, str) and g] if isinstance(order, list) else []
        for it in self.items.values():
            if it.group and it.group not in seen:
                seen.append(it.group)
        return seen

    def _save_groups(self, groups: list[str]) -> None:
        self.settings["group_list"] = list(dict.fromkeys(g for g in groups if g))

    def add_group(self, name: str) -> str:
        name = name.strip()
        self._save_groups([*self.groups(), name])
        return name

    def rename_group(self, old: str, new: str) -> None:
        """Rename a group (or merge it into another, if that name is taken)."""
        new = new.strip()
        if not new or new == old:
            return
        groups = self.groups()
        groups = (
            [g for g in groups if g != old] if new in groups else [new if g == old else g for g in groups]
        )
        for it in self.items.values():
            if it.group == old:
                it.group = new
        self._save_groups(groups)
        self.save_items()

    def remove_group(self, name: str) -> None:
        """The group goes; its gear stays, without a group."""
        for it in self.items.values():
            if it.group == name:
                it.group = ""
        self._save_groups([g for g in self.groups() if g != name])
        self.save_items()

    def step_group(self, name: str, step: int) -> None:
        """Up (-1) or down (+1) in the list."""
        groups = self.groups()
        if name not in groups:
            return
        i = groups.index(name)
        groups.insert(max(0, min(len(groups) - 1, i + step)), groups.pop(i))
        self._save_groups(groups)

    def put_in_group(self, ids: list[str], group: str) -> int:
        """Put gear in a group. What goes with it comes along. A group the move empties goes away
        (one you made empty on purpose stays). Returns how many moved."""
        from bodega.core.pricing import with_attached

        if group:
            self.add_group(group)
        left: set[str] = set()
        n = 0
        for item_id in ids:
            it = self.items.get(item_id)
            if it is None:
                continue
            for x, _u, _d in with_attached(self, it, 1):
                left.add(x.group)
                x.group = group
            n += 1
        for g in left:
            if g and g != group and not any(i.group == g for i in self.items.values()):
                self._save_groups([x for x in self.groups() if x != g])
        self.save_items()
        return n

    def reorder_items(self, ids: list[str], anchor_id: str, after: bool = False, brand: bool = False) -> None:
        """Put gear just before (or after) another piece, in its group (and, with `brand`, its company).
        Your order is the order gear.json keeps."""
        anchor = self.items.get(anchor_id)
        moving = [i for i in ids if i in self.items and i != anchor_id]
        if anchor is None or not moving:
            return
        if any(self.items[i].group != anchor.group for i in moving):
            self.put_in_group(moving, anchor.group)
        if brand:
            for i in moving:
                self.items[i].brand = anchor.brand
        order = [i for i in self.items if i not in moving]
        at = order.index(anchor_id) + (1 if after else 0)
        order[at:at] = moving
        kept = {i: self.items[i] for i in order}
        self.items.clear()  # in place: other parts of the app hold this dict
        self.items.update(kept)
        self.save_items()

    def apply_groups(self, new: dict[str, str]) -> int:
        """Set many pieces' groups at once (Tidy Up Groups). Returns how many changed."""
        n = 0
        for item_id, group in new.items():
            it = self.items.get(item_id)
            if it is not None and it.group != group:
                it.group = group
                n += 1
        from bodega.core.tidy import GROUPS

        used = {i.group for i in self.items.values()}
        self._save_groups([g for g in GROUPS if g in used] + [g for g in self.groups() if g in used])
        self.save_items()
        return n

    def departments(self) -> list[str]:
        """A sheet's departments (Camera, G&E…) as imported: used by the Import window only."""
        order = self.settings.get("departments")
        seen = [d for d in order if isinstance(d, str) and d] if isinstance(order, list) else []
        for it in self.items.values():
            if it.department and it.department not in seen:
                seen.append(it.department)
        return seen

    def pricing(self) -> Business:
        """The profile prices come from: the one in use, or (before you've made one) the rate and tax read
        from your spreadsheet, else the usual 4% and 8.25%. Never None, so prices never show as $0."""
        cur = self.settings.get("business", "")
        b = self.businesses.get(cur) or next(iter(self.businesses.values()), None)
        if b is not None:
            return b
        fallback = Business()
        sheet = self.settings.get("sheet_pricing")
        if isinstance(sheet, dict):
            fallback.rate_pct = str(sheet.get("rate_pct") or fallback.rate_pct)
            fallback.value_tax = str(sheet.get("value_tax") or fallback.value_tax)
        return fallback

    def brands(self) -> list[str]:
        """Every company your gear is from, A to Z."""
        return sorted({i.brand for i in self.items.values() if i.brand}, key=str.casefold)

    def series_of(self, brand: str) -> list[str]:
        """The series you have from a company (all of them for "")."""
        return sorted(
            {i.series for i in self.items.values() if i.series and (not brand or i.brand == brand)},
            key=str.casefold,
        )

    def guess_brands(self) -> int:
        """Fill in the company from the name, where it's blank. Returns how many."""
        from bodega.core.importer import fill_brands

        return fill_brands(list(self.items.values()))

    def add_item(self, it: Item) -> Item:
        self.items[it.id] = it
        if it.group:
            self._save_groups(self.groups())
        return it

    def delete_item(self, item_id: str) -> None:
        self.delete_items([item_id])

    def delete_items(self, ids: list[str]) -> int:
        """Gear attached to what's deleted becomes its own item; kits drop it; rentals keep its name.
        Saved once at the end. Returns how many went."""
        gone = {i: self.items[i] for i in ids if i in self.items}
        if not gone:
            return 0
        held = self._hold_rental_prices()
        for item_id in gone:
            self.items.pop(item_id)

        def landing(parent: str) -> str:  # the nearest piece above that isn't being deleted
            seen = set()
            while parent in gone and parent not in seen:
                seen.add(parent)
                parent = gone[parent].parent
            return parent if parent in self.items else ""

        for it in self.items.values():
            if it.parent in gone:
                it.parent = landing(it.parent)
        for p in self.packages.values():
            p.lines = [ln for ln in p.lines if ln.item_id not in gone]
        changed = self._keep_rental_prices(held)
        for r in self.rentals.values():
            for ln in r.lines:
                if ln.kind == "item" and ln.ref in gone and not ln.name:
                    ln.name = gone[ln.ref].name
                    changed.add(r.id)
        for rid in changed:
            self.save_rental(self.rentals[rid])
        self.save_items()
        self.save_packages()
        return len(gone)

    def ordered_items(self) -> list[Item]:
        """By group (in your order; no group last), then your order inside it (an imported sheet keeps its own)."""
        order = {g: n for n, g in enumerate(self.groups())}
        added = {item_id: n for n, item_id in enumerate(self.items)}
        return sorted(self.items.values(), key=lambda i: (order.get(i.group, len(order)), added[i.id]))

    # ------------------------------------------------------------------ packages
    def new_package(self) -> Package:
        p = Package(name="")
        self.packages[p.id] = p
        self.save_packages()
        return p

    def delete_package(self, pkg_id: str) -> None:
        if pkg_id not in self.packages:
            return
        held = self._hold_rental_prices()
        gone = self.packages.pop(pkg_id)
        changed = self._keep_rental_prices(held)
        for r in self.rentals.values():
            for ln in r.lines:
                if ln.kind == "package" and ln.ref == pkg_id and not ln.name:
                    ln.name = gone.name
                    changed.add(r.id)
        for rid in changed:
            self.save_rental(self.rentals[rid])
        self.save_packages()

    # a rental's prices must not change because gear or a kit it used was deleted
    def _hold_rental_prices(self) -> list:
        """Every rental line priced by its gear: (rental, line, today's rate for one)."""
        from bodega.core import pricing

        held = []
        for r in self.rentals.values():
            b = self.businesses.get(r.business_id) or self.pricing()
            for ln in r.lines:
                if ln.kind in ("item", "package") and not ln.rate.strip():
                    held.append((r, ln, pricing.line_unit(self, ln, b)))
        return held

    def _keep_rental_prices(self, held: list) -> set[str]:
        """After a delete: write the old rate onto any line whose price moved. Returns the rentals changed."""
        from bodega.core import pricing

        changed = set()
        for r, ln, was in held:
            b = self.businesses.get(r.business_id) or self.pricing()
            if pricing.line_unit(self, ln, b) != was:
                ln.rate = str(was)
                changed.add(r.id)
        return changed

    # ------------------------------------------------------------------ profiles
    def add_business(self, b: Business) -> Business:
        b.prefix = clean_prefix(b.prefix) or initials(b.name)
        if not b.terms.strip():
            b.terms = DEFAULT_TERMS
        if not b.note.strip():
            b.note = DEFAULT_NOTE
        self.businesses[b.id] = b
        self.save_businesses()
        return b

    def delete_business(self, b_id: str) -> None:
        self.businesses.pop(b_id, None)
        self.save_businesses()

    # ------------------------------------------------------------------ renters
    def save_client(self, c: Client) -> Client:
        """Save a renter; rentals that aren't out the door yet follow the change."""
        c = replace(c)
        self.clients[c.id] = c
        self.save_clients()
        for r in self.rentals.values():
            if r.client.id == c.id and r.status in ("quote", "booked"):
                r.client = replace(c)
                self.save_rental(r)
        return c

    def delete_client(self, c_id: str) -> None:
        self.clients.pop(c_id, None)
        self.save_clients()

    def match_client(self, c: Client) -> Client | None:
        return self.clients.get(c.id)

    # ------------------------------------------------------------------ rentals
    # A rental number is never given twice: settings "numbers" keeps the last one Bodega gave in each series
    # ("JLF-2026": 7), and a deleted rental's number stays spent. A rental keeps its number once it has one.
    def _spent(self) -> dict[str, int]:
        s = self.settings.get("numbers")
        if not isinstance(s, dict):
            return {}
        return {k: v for k, v in s.items() if isinstance(k, str) and isinstance(v, int) and v > 0}

    def _spend(self, series: str, n: int) -> None:
        spent = self._spent()
        if n > spent.get(series, 0):
            spent[series] = n
            self.settings["numbers"] = spent
            self.save_settings()

    def _spend_number(self, number: str) -> None:
        """A number that was given (or typed) stays spent, whatever happens to its rental."""
        if m := NUMBER.match(number.strip()):
            self._spend(f"{m.group(1).upper()}-{m.group(2)}", int(m.group(3)))

    def number_after(self, prefix: str, year: int, skip: str = "") -> int:
        """The next number free in a series: past every number in use and every one given before."""
        prefix = clean_prefix(prefix)
        pat = re.compile(rf"^{re.escape(prefix)}-{year}-(\d+)$", re.IGNORECASE)
        used = [
            int(m.group(1))
            for r in self.rentals.values()
            if r.id != skip and (m := pat.match(r.number.strip()))
        ]
        return max([*used, self._spent().get(f"{prefix}-{year}", 0)]) + 1

    def next_number(self, b: Business, year: int, skip: str = "") -> str:
        """What the next rental of this profile would be called (nothing is spent by asking)."""
        prefix = clean_prefix(b.prefix) or initials(b.name)
        return f"{prefix}-{year}-{self.number_after(prefix, year, skip):03d}"

    def _issue(self, b: Business, year: int) -> str:
        """Give out the next number: it's spent from now on, kept or not."""
        prefix = clean_prefix(b.prefix) or initials(b.name)
        n = self.number_after(prefix, year)
        self._spend(f"{prefix}-{year}", n)
        return f"{prefix}-{year}-{n:03d}"

    def set_next_number(self, b: Business, n: int, year: int | None = None) -> bool:
        """Profile › Next Number: this year's series carries on from n (a series from another system).
        Never lower than a number already given. Returns False if n was too low."""
        year = year or dates.today().year
        prefix = clean_prefix(b.prefix) or initials(b.name)
        if n < self.number_after(prefix, year):
            return False
        self._spend(f"{prefix}-{year}", n - 1)
        return True

    def number_taken(self, number: str, skip: str = "") -> Rental | None:
        """Another rental that already has this number (letters' case and spaces aside), or None."""
        key = number.strip().casefold()
        if not key:
            return None
        return next(
            (r for r in self.rentals.values() if r.id != skip and r.number.strip().casefold() == key), None
        )

    def renumber(self, r: Rental) -> bool:
        """A quote whose number Bodega picked takes its profile's series when its profile changes (the old
        number stays spent). A new date never changes it. Returns True if it changed."""
        b = self.businesses.get(r.business_id)
        if not r.auto_number or r.status != "quote" or b is None:
            return False
        prefix = clean_prefix(b.prefix) or initials(b.name)
        if r.number.upper().startswith(f"{prefix}-"):
            return False
        m = NUMBER.match(r.number.strip())
        self._spend_number(r.number)
        r.number = self._issue(b, int(m.group(2)) if m else dates.today().year)
        return True

    def new_rental(self, b: Business) -> Rental:
        start = dates.plus(dates.today(), 1)
        r = Rental(
            business_id=b.id,
            number=self._issue(b, start.year),
            pickup=dates.iso(start),
            return_date=dates.iso(dates.plus(start, 1)),
            weekend_deal=b.weekend_deal,
            tax_rate=b.rental_tax,
            terms=terms_for(b),
            note=b.note,
        )
        self.save_rental(r)
        return r

    def duplicate_rental(self, src: Rental) -> Rental:
        b = self.businesses.get(src.business_id) or next(iter(self.businesses.values()))
        r = Rental.from_dict(src.to_dict())
        r.id = new_id()
        r.status = "quote"
        r.auto_number = True
        r.number = self._issue(b, dates.today().year)
        r.lines = [RentalLine.from_dict(ln.to_dict()) for ln in src.lines]
        r.created = now_iso()
        self.save_rental(r)
        return r

    def delete_rental(self, r_id: str) -> None:
        if (r := self.rentals.pop(r_id, None)) is not None:
            self._spend_number(r.number)
        self.unsaved.discard(r_id)
        f = self._rental_dir / f"{r_id}.json"
        try:
            f.unlink(missing_ok=True)
        except OSError:
            log.warning("couldn't remove %s", f, exc_info=True)

    def ordered_rentals(self) -> list[Rental]:
        """Soonest pickup first among what's coming up; the rest newest first."""
        return sorted(self.rentals.values(), key=lambda r: (r.pickup or "", r.created), reverse=True)
