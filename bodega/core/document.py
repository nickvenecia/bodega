"""Every string on a page, worked out before anything is drawn.

build_*() turn a rental, the whole inventory, the rate card or a package into a DocView: plain text in
the order it reads. doc/render.py lays that out on paper; nothing there decides what a page says.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from bodega.core import dates, money, pricing, words
from bodega.core.model import Business, Item, Package, Rental
from bodega.core.terms import terms_for


@dataclass
class Col:
    title: str
    width: float  # a share of the table's width
    align: str = "left"  # left / right / center
    mono: bool = False


@dataclass
class Row:
    cells: list[str]
    kind: str = "item"  # item / sub (attached or in a package) / package / fee / heading / subheading
    depth: int = 0
    note: str = ""  # a second, smaller line under the name (serial numbers, what's included)
    photo: str = ""  # the piece's photo (a file name in the photos folder), shown when the table has photos


@dataclass
class Table:
    cols: list[Col]
    rows: list[Row] = field(default_factory=list)
    name_col: int = 1
    checks: bool = False  # Out / In boxes in front of every gear row
    photos: bool = False  # a small photo before every gear row's name (when any piece in it has one)


@dataclass
class Label:
    """One sticker: what it is, a second line (its serial number, or which one of several), and its code."""

    title: str
    sub: str
    code: str  # what the QR code says: label_code(item id)


LABEL_PREFIX = "bodega:"


def label_code(item_id: str) -> str:
    return f"{LABEL_PREFIX}{item_id}"


def item_from_code(text: str) -> str | None:
    """A scanned label -> the piece's id (a scanner types the code, then Return), or None if it isn't one."""
    t = (text or "").strip()
    if not t.lower().startswith(LABEL_PREFIX):
        return None
    item_id = t[len(LABEL_PREFIX) :].strip()
    return item_id if re.fullmatch(r"[A-Za-z0-9_-]{1,64}", item_id) else None


@dataclass
class DocView:
    kind: str  # agreement / quote / inventory / ratecard / package
    title: str
    business: str = ""
    tagline: str = ""
    contact: list[str] = field(default_factory=list)
    number: str = ""
    big_label: str = ""
    big_value: str = ""
    big_sub: str = ""
    strip: list[tuple[str, str]] = field(default_factory=list)
    blocks: list[tuple[str, str]] = field(default_factory=list)
    table: Table | None = None
    totals: list[tuple[str, str, bool]] = field(default_factory=list)
    paragraphs_title: str = ""
    paragraphs: list[str] = field(default_factory=list)
    signatures: bool = False
    note: str = ""
    footer: str = ""
    labels: list[Label] = field(default_factory=list)  # a sheet of stickers instead of a page (kind "labels")


def _contact(b: Business | None) -> list[str]:
    if b is None:
        return []
    line = "  ·  ".join(x.strip() for x in (b.email, b.phone, b.website) if x.strip())
    out = [line] if line else []
    addr = b.address.strip().replace("\n", ", ")
    if addr:
        out.append(addr)
    return out


def _cur(b: Business | None) -> str:
    return (b.currency if b else "$") or "$"


def _qty(n: int) -> str:
    return f"{n:,}"


def _serials(it: Item, units: int | None = None) -> str:
    s = it.serial_list()
    if units is not None and units < it.qty:
        s = s[:units] if len(s) >= units else s
    return ("S/N " + ", ".join(s)) if s else ""


def file_name(text: str) -> str:
    """Safe on every computer: no slashes, colons or the like."""
    clean = re.sub(r'[\\/:*?"<>|\n\r\t]+', " ", text)
    return re.sub(r"\s+", " ", clean).strip() or "Bodega"


# The rental agreement
def rental_title(r: Rental) -> str:
    return "Rental Quote" if r.status == "quote" else "Rental Agreement"


def build_rental(lib, r: Rental, b: Business | None) -> DocView:
    cur = _cur(b)
    t = pricing.totals(lib, r, b)
    pick, ret = pricing.span_of(r)
    days = t.days
    v = DocView(kind="quote" if r.status == "quote" else "agreement", title=rental_title(r))
    v.business = b.name if b else ""
    v.tagline = b.tagline if b else ""
    v.contact = _contact(b)
    v.number = r.number
    v.big_label = "Total"
    v.big_value = money.fmt(t.total, cur)
    v.big_sub = f"{days.billed} day{'s' if days.billed != 1 else ''} billed  ·  {dates.span(pick, ret)}"
    billed = f"{days.billed} day{'s' if days.billed != 1 else ''}"
    if days.out != days.billed:
        billed += f" ({days.out} out)"
    if t.mixed:
        n = len(pricing.periods(r))
        billed = f"{n} periods"
        v.big_sub = f"{n} date ranges  ·  {dates.span(pick, ret)}"
    v.strip = [
        ("Quote" if r.status == "quote" else "Rental", r.number),
        ("Pickup", dates.fmt_day(pick)),
        ("Return", dates.fmt_day(ret)),
        ("Billed", billed),
    ]
    c = r.client
    renter = [x for x in (c.name.strip(), c.company.strip()) if x]
    if c.address.strip():
        renter.append(c.address.strip())
    renter.extend(x for x in (c.email.strip(), c.phone.strip()) if x)
    v.blocks = [("Renter", "\n".join(renter) or "—")]
    if b is not None:
        owner = [b.name.strip()] + [x for x in (b.email.strip(), b.phone.strip()) if x]
        v.blocks.append(("Owner", "\n".join(x for x in owner if x)))
    if r.project.strip():
        v.blocks.append(("Production", r.project.strip()))

    checks = r.show_checks and r.status != "quote"
    table = Table(
        [
            Col("Qty", 0.07, "center"),
            Col("Equipment", 0.53),
            Col("Value", 0.14, "right"),
            Col("Per Day", 0.12, "right"),
            Col("Amount", 0.14, "right"),
        ],
        checks=checks,
    )

    def add_line(line, amount) -> None:
        name = pricing.line_name(lib, line)
        if line.kind == "fee":
            qty = _qty(line.qty) if line.qty > 1 else ""
            table.rows.append(Row([qty, name or "Fee", "", "", money.fmt(amount, cur)], "fee"))
            return
        gear = pricing.line_gear(lib, line)
        value = sum((pricing.replacement(it, b) * u for it, u, _d in gear), money.ZERO)
        unit = pricing.line_unit(lib, line, b)
        if line.kind == "package":
            table.rows.append(
                Row([_qty(line.qty), name, money.fmt(value, cur), money.fmt(unit, cur), money.fmt(amount, cur)], "package")
            )  # fmt: skip
            for it, units, depth in gear:
                note = _serials(it, units) if r.show_serials else ""
                each = money.fmt(pricing.replacement(it, b) * units, cur)
                table.rows.append(Row([_qty(units), it.name, each, "", ""], "sub", depth + 1, note))
            return
        it = gear[0][0] if gear else None
        note = _serials(it, line.qty) if (it and r.show_serials) else ""
        own_value = pricing.replacement(it, b) * line.qty if it else money.ZERO
        table.rows.append(
            Row([_qty(line.qty), name, money.fmt(own_value, cur), money.fmt(unit, cur), money.fmt(amount, cur)], "item", 0, note)
        )  # fmt: skip
        for kid, units, depth in gear[1:]:
            note = _serials(kid, units) if r.show_serials else ""
            each = money.fmt(pricing.replacement(kid, b) * units, cur)
            table.rows.append(Row([_qty(units), kid.name, each, "", "Included"], "sub", depth, note))

    pairs = list(zip(r.lines, t.line_amounts, t.line_days, strict=False))
    if t.mixed:
        # one block per date range, so what goes out together is checked out together
        for a, z in pricing.periods(r):
            these = [(ln, amt, d) for ln, amt, d in pairs if ln.kind != "fee" and pricing.line_dates(r, ln) == (a, z)]
            if not these:
                continue
            d = these[0][2]
            label = f"{dates.fmt_day(a)} – {dates.fmt_day(z)}  ·  {d.billed} day{'s' if d.billed != 1 else ''} billed"
            table.rows.append(Row(["", label, "", "", ""], "subheading"))
            for ln, amt, _d in these:
                add_line(ln, amt)
        fees = [(ln, amt) for ln, amt, _d in pairs if ln.kind == "fee"]
        if fees:
            table.rows.append(Row(["", "Fees", "", "", ""], "subheading"))
            for ln, amt in fees:
                add_line(ln, amt)
    else:
        for ln, amt, _d in pairs:
            add_line(ln, amt)
    v.table = table

    if t.mixed:
        tot: list[tuple[str, str, bool]] = [
            (f"Rental, {len(pricing.periods(r))} Periods", money.fmt(t.gear, cur), False)
        ]
    else:
        tot = [("Gear per Day", money.fmt(t.per_day, cur), False)]
        tot.append((f"Rental, {billed.split(' (')[0]}", money.fmt(t.gear, cur), False))
    if t.fees:
        tot.append(("Fees", money.fmt(t.fees, cur), False))
    if t.discount:
        tot.append((f"Discount ({money.fmt_rate(r.discount)})", money.fmt(-t.discount, cur), False))
    if t.tax:
        tot.append((f"Sales Tax ({money.fmt_rate(r.tax_rate)})", money.fmt(t.tax, cur), False))
    tot.append(("Total", money.fmt(t.total, cur), True))
    if t.deposit:
        tot.append(("Security Deposit (Refundable)", money.fmt(t.deposit, cur), False))
    tot.append(("Replacement Value", money.fmt(t.value, cur), False))
    v.totals = tot

    v.paragraphs_title = "Terms"
    text = r.terms if r.terms.strip() else (terms_for(b) if b else "")
    v.paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if r.status == "quote":
        v.paragraphs.insert(0, "Quote. Prices hold for 14 days. The gear is held for you once the rental is booked.")
    v.signatures = r.status != "quote"
    v.note = r.note.strip()
    v.footer = b.name if b else ""
    return v


def rental_stem(r: Rental) -> str:
    who = r.client.company.strip() or r.client.name.strip() or r.project.strip()
    return file_name(f"{r.number} {who}" if who else r.number)


# The inventory list
def _tree(lib, items: list[Item]) -> list[tuple[Item, int]]:
    """Top-level items in order, each followed by what's attached to it (depth 1, 2…)."""
    keep = {i.id for i in items}
    out: list[tuple[Item, int]] = []
    for it in items:
        if it.parent and it.parent in keep:
            continue
        for kid, _units, depth in pricing.with_attached(lib, it, it.qty):
            if kid.id in keep:
                out.append((kid, depth))
    return out


def _grouped(lib, items: list[Item]):
    """(group, "", [(item, depth)]) in the library's order; attached gear stays with its parent."""
    rows = _tree(lib, items)
    sections: list[tuple[str, str, list[tuple[Item, int]]]] = []
    for it, depth in rows:
        if depth == 0:
            key = (it.group or "Other", "")
            if not sections or sections[-1][:2] != key:
                sections.append((key[0], key[1], []))
        if sections:
            sections[-1][2].append((it, depth))
    return sections


def build_inventory(lib, items: list[Item], b: Business | None, title: str = "Equipment Inventory") -> DocView:
    cur = _cur(b)
    items = [i for i in items if i.status != "retired"]
    v = DocView(kind="inventory", title=title)
    v.business = b.name if b else ""
    v.tagline = b.tagline if b else ""
    v.contact = _contact(b)
    total = sum((pricing.replacement(i, b) * i.qty for i in items), money.ZERO)
    pieces = sum(i.qty for i in items)
    v.number = dates.fmt(dates.today())
    v.big_label = "Replacement Value"
    v.big_value = money.fmt(total, cur)
    v.big_sub = f"{words.count(len(items), 'kind')} of gear  ·  {words.count(pieces, 'piece')}"
    groups = []
    for i in items:
        if (i.group or "Other") not in groups:
            groups.append(i.group or "Other")
    v.strip = [("As Of", dates.fmt(dates.today())), ("Gear", f"{len(items):,}"), ("Pieces", f"{pieces:,}")]
    v.strip.append(("Groups", f"{len(groups):,}"))
    table = Table(
        [
            Col("Qty", 0.07, "center"),
            Col("Gear", 0.47),
            Col("Serial Numbers", 0.18, mono=True),
            Col("Unit Value", 0.13, "right"),
            Col("Total", 0.15, "right"),
        ]
    )
    last_dep = None
    for dep, group, rows in _grouped(lib, items):
        if dep != last_dep:
            dep_total = sum(
                (pricing.replacement(i, b) * i.qty for i in items if (i.group or "Other") == dep),
                money.ZERO,
            )
            table.rows.append(Row(["", dep, "", "", money.fmt(dep_total, cur)], "heading"))
            last_dep = dep
        if group:
            table.rows.append(Row(["", group, "", "", ""], "subheading"))
        for it, depth in rows:
            each = pricing.replacement(it, b)
            name = it.name + ("  (In Repair)" if it.status == "repair" else "")
            serial = ", ".join(it.serial_list())
            table.rows.append(
                Row(
                    [_qty(it.qty), name, serial, money.fmt(each, cur), money.fmt(each * it.qty, cur)],
                    "sub" if depth else "item",
                    depth,
                    photo=it.photo,
                )
            )
    table.photos = any(r.photo for r in table.rows)
    v.table = table
    v.totals = [("Gear", f"{len(items):,}", False), ("Pieces", f"{pieces:,}", False)]
    v.totals.append(("Replacement Value", money.fmt(total, cur), True))
    if b is not None and money.parse(b.value_tax):
        v.note = f"Replacement value is what each piece cost plus {money.fmt_rate(b.value_tax)} sales tax."
    v.footer = b.name if b else ""
    return v


# The rate card
def build_ratecard(lib, items: list[Item], packages: list[Package], b: Business | None) -> DocView:
    cur = _cur(b)
    wd = b.week_days if b else 7
    v = DocView(kind="ratecard", title="Rate Card")
    v.business = b.name if b else ""
    v.tagline = b.tagline if b else ""
    v.contact = _contact(b)
    v.number = dates.fmt(dates.today())
    v.big_label = "A Week Bills As"
    v.big_value = f"{wd} Days"
    v.big_sub = "Friday to Monday bills as 1 day" if (b and b.weekend_deal) else ""
    table = Table([Col("Gear", 0.68), Col("Day", 0.16, "right"), Col("Week", 0.16, "right")], name_col=0)
    pk = [p for p in packages if p.lines]
    if pk:
        table.rows.append(Row(["Kits", "", ""], "heading"))
        for p in sorted(pk, key=lambda p: p.name.casefold()):
            rate = pricing.package_rate(lib, p, b)
            gear = pricing.package_gear(lib, p)
            names = "Includes " + ", ".join(it.name for it, _u, d in gear if d == 0)
            table.rows.append(
                Row([p.name or "Kit", money.fmt_short(rate, cur), money.fmt_short(rate * wd, cur)], "package", 0, names)
            )  # fmt: skip
    shown = [i for i in items if i.rentable and i.status != "retired" and not (i.parent and i.parent in lib.items)]
    last_dep = None
    for dep, group, rows in _grouped(lib, shown):
        if dep != last_dep:
            table.rows.append(Row([dep, "", ""], "heading"))
            last_dep = dep
        if group:
            table.rows.append(Row([group, "", ""], "subheading"))
        for it, depth in rows:
            if depth:
                continue
            rate = pricing.item_rate(lib, it, b)
            kids = pricing.children(lib, it.id)
            note = ""
            if kids:
                first = [k.name for k in kids[:3]]
                more = len(kids) - len(first)
                note = "With " + ", ".join(first) + (f" and {more} more" if more else "")
            name = it.name + (f"  (×{it.qty})" if it.qty > 1 else "")
            day = money.fmt_short(rate, cur) if rate else "Free"
            week = money.fmt_short(rate * wd, cur) if rate else ""
            table.rows.append(Row([name, day, week], "item", 0, note, photo=it.photo))
    table.photos = any(r.photo for r in table.rows)
    v.table = table
    v.note = "Rates are per day, for one of each, and include the gear listed with it."
    v.footer = b.name if b else ""
    return v


# One package
def build_package(lib, p: Package, b: Business | None) -> DocView:
    cur = _cur(b)
    wd = b.week_days if b else 7
    rate = pricing.package_rate(lib, p, b)
    alone = pricing.package_sum(lib, p, b)
    value = pricing.package_value(lib, p, b)
    v = DocView(kind="package", title=p.name.strip() or "Kit")
    v.business = b.name if b else ""
    v.tagline = b.tagline if b else ""
    v.contact = _contact(b)
    v.number = "Kit"
    v.big_label = "Day Rate"
    v.big_value = money.fmt_short(rate, cur)
    v.big_sub = f"{money.fmt_short(rate * wd, cur)} a week ({wd}-day week)"
    v.strip = [
        ("Day", money.fmt_short(rate, cur)),
        ("Week", money.fmt_short(rate * wd, cur)),
        ("Gear on Its Own", money.fmt_short(alone, cur) + " a day"),
        ("You Save", money.fmt_short(max(money.ZERO, alone - rate), cur) + " a day"),
    ]
    table = Table([Col("Qty", 0.08, "center"), Col("Equipment", 0.58), Col("Serial Numbers", 0.18, mono=True), Col("Value", 0.16, "right")])  # fmt: skip
    for it, units, depth in pricing.package_gear(lib, p):
        table.rows.append(
            Row(
                [_qty(units), it.name, ", ".join(it.serial_list()[:units]), money.fmt(pricing.replacement(it, b) * units, cur)],
                "sub" if depth else "item",
                depth,
            )
        )  # fmt: skip
    v.table = table
    v.totals = [("Replacement Value", money.fmt(value, cur), True)]
    if p.notes.strip():
        v.paragraphs_title = "About This Kit"
        v.paragraphs = [x.strip() for x in re.split(r"\n\s*\n", p.notes) if x.strip()]
    v.footer = b.name if b else ""
    return v


# As text
def summary_text(lib, r: Rental, b: Business | None) -> str:
    """For pasting into an email."""
    cur = _cur(b)
    t = pricing.totals(lib, r, b)
    pick, ret = pricing.span_of(r)
    lines = [f"{rental_title(r)} {r.number}" + (f" · {r.project}" if r.project.strip() else "")]
    lines.append(f"Pickup {dates.fmt_day(pick)}, return {dates.fmt_day(ret)} ({t.days.why})")
    lines.append("")
    for line, amt, d in zip(r.lines, t.line_amounts, t.line_days, strict=False):
        q = f"{line.qty} × " if line.qty > 1 else ""
        when = ""
        if r.own_dates(line):
            a, z = pricing.line_dates(r, line)
            when = f" ({dates.span(a, z)}, {d.billed} day{'s' if d.billed != 1 else ''})"
        lines.append(f"- {q}{pricing.line_name(lib, line)}{when}: {money.fmt(amt, cur)}")
    lines.append("")
    if t.discount:
        lines.append(f"Discount: {money.fmt(-t.discount, cur)}")
    if t.tax:
        lines.append(f"Sales tax: {money.fmt(t.tax, cur)}")
    lines.append(f"Total: {money.fmt(t.total, cur)}")
    if t.deposit:
        lines.append(f"Security deposit (refundable): {money.fmt(t.deposit, cur)}")
    lines.append(f"Replacement value: {money.fmt(t.value, cur)}")
    return "\n".join(lines)


# Labels
def build_labels(items: list[Item], b: Business | None) -> DocView:
    """A sticker for every unit (retired gear left out), with a QR code a scanner reads back as the piece."""
    v = DocView(kind="labels", title="Labels", business=b.name if b else "")
    for it in items:
        if it.status == "retired":
            continue
        for u in range(it.qty):
            serial = it.serials[u].strip() if u < len(it.serials) else ""
            if serial:
                sub = f"S/N {serial}"
            elif it.qty > 1:
                sub = f"{u + 1} of {it.qty}"
            else:
                sub = it.brand
            v.labels.append(Label(it.name or "Untitled Piece", sub, label_code(it.id)))
    return v
