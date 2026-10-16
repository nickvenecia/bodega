"""What Bodega keeps: your gear, packages of gear, rentals, renters and your profile.

Plain dataclasses with to_dict()/from_dict(). from_dict() reads every field by what it holds, through one
shared reader (_read): text stays text, a number a number, a yes/no a yes/no, a list a list, and anything else
gets the field's default; missing keys get their default too (defaults always mean "off" or empty). Fields this
Bodega doesn't know (written by a newer one) are kept in `newer` and written back as they were, and a status it
doesn't know is read as the cautious one (a rental holds its gear, a piece isn't available).
Amounts are kept as the text that was typed ("249.99") and turned into exact decimals in pricing.py.
"""

from __future__ import annotations

import copy
import re
import uuid
from dataclasses import dataclass, field, fields, is_dataclass
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


def _text(v: Any) -> str:
    """Text from a file: a number is written as text; nothing, a list or a dict is blank."""
    if v is None or isinstance(v, (list, dict)):
        return ""
    return str(v)


def _yes(v: Any, default: bool) -> bool:
    if isinstance(v, bool):
        return v
    if v in (0, 1):
        return bool(v)
    if isinstance(v, str) and v.strip().lower() in ("true", "yes", "1", "false", "no", "0", ""):
        return v.strip().lower() in ("true", "yes", "1")
    return default


def _as(v: Any, default: Any) -> Any:
    """`v` as the kind of thing `default` is. A plain value of another kind is turned into this one (a number
    for a name is its text; text that isn't a number is the default number); nothing (null) is the default.
    A list or a dict where it can't be one is broken: ValueError, so the record is skipped and its file kept."""
    if v is None:
        return default
    if isinstance(default, (list, dict)) or is_dataclass(default):
        want = list if isinstance(default, list) else dict
        if not isinstance(v, want):
            raise ValueError(f"expected a {want.__name__}, got {type(v).__name__}")
        return type(default).from_dict(v) if is_dataclass(default) else v
    if isinstance(v, (list, dict)):
        raise ValueError(f"expected a plain value, got {type(v).__name__}")
    if isinstance(default, bool):
        return _yes(v, default)
    if isinstance(default, int):
        try:
            return int(v) if not isinstance(v, str) else int(v.strip())
        except (TypeError, ValueError, OverflowError):
            return default
    if isinstance(default, str):
        return str(v)
    return v


def _read(cls, d: dict):
    """A record from a file, every field read by what it holds (see the top of this file). A choice this
    Bodega doesn't know (a status from a newer one) is read as the cautious one, and kept to be written back."""
    obj = cls()
    names = {f.name for f in fields(cls)}
    for f in fields(cls):
        if f.name != "newer" and f.name in d:
            setattr(obj, f.name, _as(d[f.name], getattr(obj, f.name)))
    obj.newer = {k: copy.deepcopy(v) for k, v in d.items() if k not in names}
    for name, (allowed, cautious) in cls.CHOICES.items():
        if getattr(obj, name) not in allowed:
            if name in d:
                obj.newer[name] = copy.deepcopy(d[name])
            setattr(obj, name, cautious)
    return obj


def _plain(v: Any) -> Any:
    if is_dataclass(v):
        return v.to_dict()
    if isinstance(v, list):
        return [_plain(x) for x in v]
    if isinstance(v, dict):
        return {k: _plain(x) for k, x in v.items()}
    return v


class Record:
    """What every kept thing shares: to_dict() writes its fields, and the ones a newer Bodega wrote too
    (`newer`: what this one doesn't know, kept as it was). CHOICES: a field that holds one of a few words ->
    (those words, the cautious one for any other)."""

    newer: dict
    CHOICES: dict[str, tuple[tuple, Any]] = {}

    def to_dict(self) -> dict:
        out = copy.deepcopy(self.newer)
        for f in fields(self):
            if f.name != "newer":
                out[f.name] = _plain(getattr(self, f.name))
        for name, (_allowed, cautious) in self.CHOICES.items():
            if name in self.newer and getattr(self, name) == cautious:  # not changed since: as it was
                out[name] = copy.deepcopy(self.newer[name])
        return out


# ---------------------------------------------------------------------------- gear
PHOTO_NAME = re.compile(r"[0-9a-f]{16}\.(?:jpg|png)")  # what a photo's file is called (never a path)


LOG_KINDS = ("service", "repair", "note")


@dataclass
class LogEntry(Record):
    """One line in a piece's maintenance log."""

    date: str = ""  # ISO
    kind: str = "service"  # service / repair / note (a service resets the reminder)
    text: str = ""
    cost: str = ""
    newer: dict = field(default_factory=dict, compare=False, repr=False)  # see Record
    CHOICES = {"kind": (LOG_KINDS, "note")}

    @classmethod
    def from_dict(cls, d: dict) -> LogEntry:
        return _read(cls, d)


@dataclass
class Item(Record):
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
    newer: dict = field(default_factory=dict, compare=False, repr=False)  # see Record
    CHOICES = {"status": (ITEM_STATUSES, "repair")}  # a status it doesn't know: not available

    @classmethod
    def from_dict(cls, d: dict) -> Item:
        it = _read(cls, d)
        it.qty = clamp_qty(it.qty)
        it.serials = [_text(s) for s in it.serials]
        it.extras = [x for x in it.extras if isinstance(x, str)]
        it.photo = it.photo if PHOTO_NAME.fullmatch(it.photo) else ""
        it.log = [LogEntry.from_dict(e) for e in it.log if isinstance(e, dict)]
        it.service_days = max(0, min(3650, it.service_days))
        return it

    def serial_list(self) -> list[str]:
        """The serials that were filled in, in unit order."""
        return [s.strip() for s in self.serials[: self.qty] if s.strip()]


@dataclass
class PackageLine(Record):
    item_id: str = ""
    qty: int = 1
    newer: dict = field(default_factory=dict, compare=False, repr=False)  # see Record

    @classmethod
    def from_dict(cls, d: dict) -> PackageLine:
        line = _read(cls, d)
        line.qty = clamp_qty(line.qty)
        return line


@dataclass
class Package(Record):
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
    newer: dict = field(default_factory=dict, compare=False, repr=False)  # see Record
    CHOICES = {"pricing": (PRICINGS, "sum")}  # pricing it doesn't know: the gear's full rates

    @classmethod
    def from_dict(cls, d: dict) -> Package:
        p = _read(cls, d)
        p.lines = [PackageLine.from_dict(x) for x in p.lines if isinstance(x, dict)]
        return p


# ---------------------------------------------------------------------------- people
@dataclass
class Client(Record):
    """Someone you rent to. Saved once (New Renter…) and picked on every rental."""

    id: str = field(default_factory=new_id)
    name: str = ""
    company: str = ""
    email: str = ""
    phone: str = ""
    address: str = ""
    notes: str = ""  # ID checked, insurance on file…
    newer: dict = field(default_factory=dict, compare=False, repr=False)  # see Record

    @classmethod
    def from_dict(cls, d: dict) -> Client:
        return _read(cls, d)

    def is_blank(self) -> bool:
        return not any((self.name.strip(), self.company.strip(), self.email.strip()))


@dataclass
class Business(Record):
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
    color: str = "blue"  # the accent on the paper (core/looks.py)
    rate_pct: str = "4"  # a day's rent, as a percent of replacement value (with tax)
    value_tax: str = "8.25"  # sales tax added to what you paid, for replacement value
    week_days: int = 3  # a 7-day week is billed as this many days
    weekend_deal: bool = True  # pick up Friday, return Monday: billed as one day
    rental_tax: str = ""  # sales tax on the rental itself
    deposit_pct: str = ""  # security deposit, as a percent of the replacement value
    terms: str = ""  # the agreement's standard terms, one clause per paragraph
    note: str = ""  # a short closing line on every agreement
    saldo_profile: str = ""  # Send to Saldo: the Saldo profile (its id) this one sends invoices as
    newer: dict = field(default_factory=dict, compare=False, repr=False)  # see Record

    @classmethod
    def from_dict(cls, d: dict) -> Business:
        b = _read(cls, d)
        b.week_days = b.week_days if b.week_days in WEEK_DAYS else 3
        b.currency = b.currency or "$"
        return b


# ---------------------------------------------------------------------------- rentals
@dataclass
class RentalLine(Record):
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
    locked_day: str = ""  # what the whole line cost a day when its rental was booked (blank: priced live)
    locked_qty: int = 0  # …for this many
    newer: dict = field(default_factory=dict, compare=False, repr=False)  # see Record
    CHOICES = {"kind": (LINE_KINDS, "item")}

    @classmethod
    def from_dict(cls, d: dict) -> RentalLine:
        line = _read(cls, d)
        line.qty = clamp_qty(line.qty)
        line.locked_qty = clamp_qty(line.locked_qty) if line.locked_day else 0
        return line


@dataclass
class CheckRow(Record):
    """One piece on a rental's check-out / check-in list."""

    item_id: str = ""
    out: bool = False  # ticked when it left
    back: bool = False  # ticked when it came back
    note: str = ""  # its condition, damage
    photos: list[str] = field(default_factory=list)  # condition photos (file names in the photos folder)
    newer: dict = field(default_factory=dict, compare=False, repr=False)  # see Record

    @classmethod
    def from_dict(cls, d: dict) -> CheckRow:
        c = _read(cls, d)
        c.photos = [x for x in c.photos if isinstance(x, str) and PHOTO_NAME.fullmatch(x)]
        return c


@dataclass
class RentalEvent(Record):
    """One line of a rental's history: when, and what happened ("Booked", "Number changed to …")."""

    at: str = ""  # ISO time
    what: str = ""
    newer: dict = field(default_factory=dict, compare=False, repr=False)  # see Record

    @classmethod
    def from_dict(cls, d: dict) -> RentalEvent:
        return _read(cls, d)


STATUS_EVENTS = {  # a rental's status, as its history says it
    "quote": "Made a quote again",
    "booked": "Booked",
    "out": "Marked out",
    "returned": "Marked returned",
    "cancelled": "Cancelled",
}


@dataclass
class Rental(Record):
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
    week_days: int = (
        0  # a week billed as this many days, kept from the profile when booked (0: the profile's)
    )
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
    saldo_invoice: str = ""  # Send to Saldo: the invoice (its id in Saldo) this rental became
    saldo_number: str = ""  # …and its number
    history: list[RentalEvent] = field(
        default_factory=list
    )  # what happened to it, oldest first; only added to
    created: str = field(default_factory=now_iso)
    updated: str = field(default_factory=now_iso)
    newer: dict = field(default_factory=dict, compare=False, repr=False)  # see Record
    CHOICES = {"status": (RENTAL_STATUSES, "booked")}  # a status it doesn't know: it holds its gear

    @classmethod
    def from_dict(cls, d: dict) -> Rental:
        r = _read(cls, d)
        r.lines = [RentalLine.from_dict(x) for x in r.lines if isinstance(x, dict)]
        r.week_days = r.week_days if r.week_days in WEEK_DAYS else 0
        r.checks = [CheckRow.from_dict(x) for x in r.checks if isinstance(x, dict)]
        r.history = [RentalEvent.from_dict(x) for x in r.history if isinstance(x, dict)]
        return r

    def happened(self, what: str) -> None:
        """Add a line to its history (it's only ever added to)."""
        self.history.append(RentalEvent(now_iso(), what))

    def deletable(self) -> bool:
        """Only a quote can be deleted; a rental that's been booked is cancelled instead, and kept."""
        return self.status == "quote"

    def own_dates(self, line: RentalLine) -> bool:
        return (
            line.kind != "fee"
            and bool(line.pickup)
            and (line.pickup != self.pickup or (line.return_date or line.pickup) != self.return_date)
        )

    def holds_gear(self) -> bool:
        """Booked and out rentals keep their gear from being promised twice."""
        return self.status in ("booked", "out")
