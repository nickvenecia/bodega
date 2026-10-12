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
        for b in self.businesses.values():  # a logo is a file name in the logos folder, nothing more
            b.logo = Path(b.logo).name if b.logo else ""
        self.untangle()
        log.info(
            "loaded %d items, %d packages, %d rentals, %d renters from %s",
            len(self.items), len(self.packages), len(self.rentals), len(self.clients), self.root,
        )  # fmt: skip
        return self

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

    SNAPSHOTS_KEPT = 20

    def snapshot(self, why: str) -> Path | None:
        """A dated copy of gear.json in backups/ before a big change (an AI's edits, say); the newest
        SNAPSHOTS_KEPT are kept. None if there's no gear yet or it couldn't be written."""
        src = self.root / "gear.json"
        if not src.exists():
            return None
        folder = self.root / "backups"
        stamp = time.strftime("%Y-%m-%d-%H%M%S")
        dest = folder / f"gear-{stamp}-{re.sub(r'[^a-z0-9-]', '', why.lower())}.json"
        try:
            folder.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(src.read_bytes())
            for old in sorted(folder.glob("gear-*.json"))[: -self.SNAPSHOTS_KEPT]:
                old.unlink(missing_ok=True)
        except OSError:
            log.warning("couldn't keep a copy of the gear before %s", why, exc_info=True)
            return None
        return dest

    def save_items(self) -> None:
        write_json(self.root / "gear.json", [i.to_dict() for i in self.items.values()])

    def save_packages(self) -> None:
        write_json(self.root / "packages.json", [p.to_dict() for p in self.packages.values()])

    def save_clients(self) -> None:
        clients = sorted(self.clients.values(), key=lambda c: c.name.casefold())
        write_json(self.root / "clients.json", [c.to_dict() for c in clients])

    def save_businesses(self) -> None:
        write_json(self.root / "businesses.json", [b.to_dict() for b in self.businesses.values()])

    def save_rental(self, r: Rental) -> None:
        r.updated = now_iso()
        self.rentals[r.id] = r
        write_json(self._rental_dir / f"{r.id}.json", r.to_dict())

    def save_settings(self) -> None:
        write_json(self.root / "settings.json", self.settings)

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
    def next_number(self, b: Business, year: int, skip: str = "") -> str:
        prefix = clean_prefix(b.prefix) or initials(b.name)
        pat = re.compile(rf"^{re.escape(prefix)}-{year}-(\d+)$")
        used = [
            int(m.group(1))
            for r in self.rentals.values()
            if r.id != skip and (m := pat.match(r.number.strip()))
        ]
        return f"{prefix}-{year}-{(max(used) + 1 if used else 1):03d}"

    def renumber(self, r: Rental) -> bool:
        """A quote whose number Bodega picked follows its profile and year. Returns True if it changed."""
        b = self.businesses.get(r.business_id)
        if not r.auto_number or r.status != "quote" or b is None:
            return False
        year = (dates.parse(r.pickup) or dates.today()).year
        number = self.next_number(b, year, skip=r.id)
        if r.number.startswith(f"{clean_prefix(b.prefix) or initials(b.name)}-{year}-"):
            return False
        r.number = number
        return True

    def new_rental(self, b: Business) -> Rental:
        start = dates.plus(dates.today(), 1)
        r = Rental(
            business_id=b.id,
            number=self.next_number(b, start.year),
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
        r.number = self.next_number(b, (dates.parse(r.pickup) or dates.today()).year)
        r.lines = [RentalLine.from_dict(vars(ln).copy()) for ln in src.lines]
        r.created = now_iso()
        self.save_rental(r)
        return r

    def delete_rental(self, r_id: str) -> None:
        self.rentals.pop(r_id, None)
        f = self._rental_dir / f"{r_id}.json"
        try:
            f.unlink(missing_ok=True)
        except OSError:
            log.warning("couldn't remove %s", f, exc_info=True)

    def ordered_rentals(self) -> list[Rental]:
        """Soonest pickup first among what's coming up; the rest newest first."""
        return sorted(self.rentals.values(), key=lambda r: (r.pickup or "", r.created), reverse=True)
