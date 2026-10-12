"""What Bodega keeps: your gear, packages of gear, rentals, renters and your profile.

Plain dataclasses with to_dict()/from_dict(). from_dict() tolerates files from older and newer
versions: unknown keys are ignored, missing keys get their default (defaults always mean "off" or empty).
Amounts are kept as the text that was typed ("249.99") and turned into exact decimals in pricing.py.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from typing import Any

ITEM_STATUSES = ("ready", "repair", "retired")
RENTAL_STATUSES = ("quote", "booked", "out", "returned", "cancelled")
PRICINGS = ("sum", "discount", "fixed")  # a package costs what its gear adds up to, less a %, or a set rate
WEEK_DAYS = (2, 3, 4, 5, 7)  # how many days a 7-day week is billed as
LINE_KINDS = ("item", "package", "fee")


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


MAX_QTY = 9999  # pieces of one thing: more is a typo (and would build that many serial-number fields)


def clamp_qty(v) -> int:
    """A quantity from a file or a sheet -> 1..MAX_QTY (anything unreadable is 1)."""
    try:
        return min(MAX_QTY, max(1, int(v)))
    except (TypeError, ValueError, OverflowError):
        return 1


def _known(cls, d: dict) -> dict:
    names = {f.name for f in fields(cls)}
    return {k: v for k, v in d.items() if k in names}


def _text(v: Any) -> str:
    return "" if v is None else str(v)


# ---------------------------------------------------------------------------- gear
PHOTO_NAME = re.compile(r"[0-9a-f]{16}\.(?:jpg|png)")  # what a photo's file is called (never a path)


LOG_KINDS = ("service", "repair", "note")


@dataclass
class LogEntry:
    """One line in a piece's maintenance log."""

    date: str = ""  # ISO
    kind: str = "service"  # service / repair / note (a service resets the reminder)
    text: str = ""
    cost: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> LogEntry:
        e = cls(**_known(cls, d))
        for k in ("date", "text", "cost"):
            setattr(e, k, _text(getattr(e, k)))
        if e.kind not in LOG_KINDS:
            e.kind = "note"
        return e


@dataclass
class Item:
    """One piece of gear (or several of the same: qty with a serial number per unit).

    `parent` is the id of the item this one lives with (a cage that only fits the FX6 belongs to the FX6).
    Attached gear goes wherever its parent goes: into packages, onto rentals and their agreements."""

    id: str = field(default_factory=new_id)
    name: str = ""
    brand: str = ""  # the company: Aputure, Sony, Matthews…
    series: str = ""  # its line: STORM, FX, Bolt 6…
    department: str = ""  # Camera, G&E, Audio, Post…
    group: str = ""  # Lenses, Batteries, Steel… (inside a department)
    qty: int = 1
    serials: list[str] = field(default_factory=list)  # one per unit, any may be blank
    value: str = ""  # replacement cost of ONE unit, before tax
    day_rate: str = ""  # blank = worked out from the value (see pricing.auto_day_rate)
    rentable: bool = True
    parent: str = ""
    link: str = ""
    notes: str = ""
    photo: str = ""  # a file name in the photos folder ("3f9c…a1.jpg"); see PHOTO_NAME
    log: list[LogEntry] = field(default_factory=list)  # maintenance: services, repairs, notes (newest last)
    service_days: int = 0  # remind every this many days after the last service (0: never)
    status: str = "ready"  # ready / repair / retired
    extras: list[str] = field(default_factory=list)  # sections added by hand: link, serials, works, notes
    created: str = field(default_factory=now_iso)
    updated: str = field(default_factory=now_iso)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> Item:
        it = cls(**_known(cls, d))
        it.qty = clamp_qty(it.qty)
        it.serials = [_text(s) for s in it.serials] if isinstance(it.serials, list) else []
        if it.status not in ITEM_STATUSES:
            it.status = "ready"
        for k in (
            "name",
            "brand",
            "series",
            "department",
            "group",
            "value",
            "day_rate",
            "parent",
            "link",
            "notes",
        ):
            setattr(it, k, _text(getattr(it, k)))
        it.extras = [x for x in it.extras if isinstance(x, str)] if isinstance(it.extras, list) else []
        it.rentable = bool(it.rentable)
        it.photo = it.photo if isinstance(it.photo, str) and PHOTO_NAME.fullmatch(it.photo) else ""
        raw = it.log if isinstance(it.log, list) else []
        it.log = [LogEntry.from_dict(e) for e in raw if isinstance(e, dict)]
        try:
            it.service_days = max(0, min(3650, int(it.service_days)))
        except (TypeError, ValueError):
            it.service_days = 0
        return it

    def serial_list(self) -> list[str]:
        """The serials that were filled in, in unit order."""
        return [s.strip() for s in self.serials[: self.qty] if s.strip()]


@dataclass
class PackageLine:
    item_id: str = ""
    qty: int = 1

    @classmethod
    def from_dict(cls, d: dict) -> PackageLine:
        line = cls(**_known(cls, d))
        line.qty = clamp_qty(line.qty)
        return line


@dataclass
class Package:
    """A set of gear you rent out together ("FX6 Run && Gun", "Interview Light Kit")."""

    id: str = field(default_factory=new_id)
    name: str = ""
    notes: str = ""
    lines: list[PackageLine] = field(default_factory=list)
    pricing: str = "discount"  # sum / discount / fixed
    discount: str = "15"  # percent off the gear's day rates (pricing "discount")
    day_rate: str = ""  # the package's own day rate (pricing "fixed")
    created: str = field(default_factory=now_iso)
    updated: str = field(default_factory=now_iso)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> Package:
        p = cls(**_known(cls, d))
        p.lines = [PackageLine.from_dict(x) for x in (d.get("lines") or []) if isinstance(x, dict)]
        if p.pricing not in PRICINGS:
            p.pricing = "discount"
        p.discount, p.day_rate = _text(p.discount), _text(p.day_rate)
        return p


# ---------------------------------------------------------------------------- people
@dataclass
class Client:
    """Someone you rent to. Saved once (New Renter…) and picked on every rental."""

    id: str = field(default_factory=new_id)
    name: str = ""
    company: str = ""
    email: str = ""
    phone: str = ""
    address: str = ""
    notes: str = ""  # ID checked, insurance on file…

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> Client:
        c = cls(**_known(cls, d))
        for f in fields(cls):
            setattr(c, f.name, _text(getattr(c, f.name)))
        return c

    def is_blank(self) -> bool:
        return not any((self.name.strip(), self.company.strip(), self.email.strip()))


@dataclass
class Business:
    """Your profile: who rents the gear out, how it's priced, and the agreement's standard terms."""

    id: str = field(default_factory=new_id)
    name: str = ""
    tagline: str = ""
    email: str = ""
    phone: str = ""
    website: str = ""
    address: str = ""
    logo: str = ""  # file name inside data_dir()/logos
    currency: str = "$"
    prefix: str = ""  # rental numbers: PREFIX-2026-001
    color: str = "violet"  # the accent on the paper (core/looks.py)
    rate_pct: str = "4"  # a day's rent, as a percent of replacement value (with tax)
    value_tax: str = "8.25"  # sales tax added to what you paid, for replacement value
    week_days: int = 3  # a 7-day week is billed as this many days
    weekend_deal: bool = True  # pick up Friday, return Monday: billed as one day
    rental_tax: str = ""  # sales tax on the rental itself
    deposit_pct: str = ""  # security deposit, as a percent of the replacement value
    terms: str = ""  # the agreement's standard terms, one clause per paragraph
    note: str = ""  # a short closing line on every agreement

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> Business:
        b = cls(**_known(cls, d))
        try:
            b.week_days = int(b.week_days)
        except (TypeError, ValueError):
            b.week_days = 3
        if b.week_days not in WEEK_DAYS:
            b.week_days = 3
        b.weekend_deal = bool(b.weekend_deal)
        for k in ("name", "tagline", "email", "phone", "website", "address", "logo", "currency", "prefix"):
            setattr(b, k, _text(getattr(b, k)))
        for k in ("rate_pct", "value_tax", "rental_tax", "deposit_pct", "terms", "note", "color"):
            setattr(b, k, _text(getattr(b, k)))
        b.currency = b.currency or "$"
        return b


# ---------------------------------------------------------------------------- rentals
@dataclass
class RentalLine:
    """One line on a rental: a piece of gear (with what's attached to it), a package, or a flat fee.

    A line can have its own dates: on one production the FX6 package goes out Sunday to Sunday while the
    FX3 package goes Monday to Wednesday. Blank dates mean the rental's own."""

    kind: str = "item"  # item / package / fee
    ref: str = ""  # the item's or package's id
    qty: int = 1
    rate: str = ""  # blank = the gear's or package's own day rate; for a fee, its flat amount
    name: str = ""  # a fee's description; for gear, the name it had (shown if the gear is deleted)
    pickup: str = ""  # this line's own dates (ISO); blank = the rental's dates
    return_date: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> RentalLine:
        line = cls(**_known(cls, d))
        line.pickup, line.return_date = _text(line.pickup), _text(line.return_date)
        if line.kind not in LINE_KINDS:
            line.kind = "item"
        line.qty = clamp_qty(line.qty)
        line.rate, line.name, line.ref = _text(line.rate), _text(line.name), _text(line.ref)
        return line


@dataclass
class CheckRow:
    """One piece on a rental's check-out / check-in list."""

    item_id: str = ""
    out: bool = False  # ticked when it left
    back: bool = False  # ticked when it came back
    note: str = ""  # its condition, damage
    photos: list[str] = field(default_factory=list)  # condition photos (file names in the photos folder)

    @classmethod
    def from_dict(cls, d: dict) -> CheckRow:
        c = cls(**_known(cls, d))
        c.item_id, c.note = _text(c.item_id), _text(c.note)
        c.out, c.back = bool(c.out), bool(c.back)
        c.photos = (
            [x for x in c.photos if isinstance(x, str) and PHOTO_NAME.fullmatch(x)]
            if isinstance(c.photos, list)
            else []
        )
        return c


@dataclass
class Rental:
    id: str = field(default_factory=new_id)
    number: str = ""
    auto_number: bool = True  # Bodega picked the number (it follows the profile and year until typed over)
    business_id: str = ""
    client: Client = field(default_factory=Client)
    status: str = "quote"  # quote / booked / out / returned / cancelled
    project: str = ""
    pickup: str = ""  # ISO dates
    return_date: str = ""
    billed_days: str = ""  # blank = worked out from the dates
    weekend_deal: bool = True
    lines: list[RentalLine] = field(default_factory=list)
    discount: str = ""  # percent off the whole rental
    tax_rate: str = ""
    deposit: str = ""  # security deposit (refundable), an amount
    terms: str = ""
    note: str = ""
    show_serials: bool = True
    show_checks: bool = True  # Out / In boxes beside every line, for checking gear out and back in
    checks: list[CheckRow] = field(
        default_factory=list
    )  # Check Out / Check In: each piece ticked, notes, photos
    checked_out: str = ""  # when it was checked out (ISO time)
    checked_in: str = ""  # when it was checked back in
    created: str = field(default_factory=now_iso)
    updated: str = field(default_factory=now_iso)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["client"] = self.client.to_dict()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> Rental:
        r = cls(**_known(cls, d))
        r.client = Client.from_dict(d.get("client") or {}) if isinstance(d.get("client"), dict) else Client()
        r.lines = [RentalLine.from_dict(x) for x in (d.get("lines") or []) if isinstance(x, dict)]
        if r.status not in RENTAL_STATUSES:
            r.status = "quote"
        for k in ("number", "project", "pickup", "return_date", "billed_days", "discount", "tax_rate"):
            setattr(r, k, _text(getattr(r, k)))
        for k in ("deposit", "terms", "note", "business_id"):
            setattr(r, k, _text(getattr(r, k)))
        for k in ("auto_number", "weekend_deal", "show_serials", "show_checks"):
            setattr(r, k, bool(getattr(r, k)))
        raw = r.checks if isinstance(r.checks, list) else []
        r.checks = [CheckRow.from_dict(x) for x in raw if isinstance(x, dict)]
        r.checked_out, r.checked_in = _text(r.checked_out), _text(r.checked_in)
        return r

    def own_dates(self, line: RentalLine) -> bool:
        return (
            line.kind != "fee"
            and bool(line.pickup)
            and (line.pickup != self.pickup or (line.return_date or line.pickup) != self.return_date)
        )

    def holds_gear(self) -> bool:
        """Booked and out rentals keep their gear from being promised twice."""
        return self.status in ("booked", "out")
