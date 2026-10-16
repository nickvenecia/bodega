"""Send a rental to Saldo (the invoicing app, once called Cobro) as a draft invoice.

Saldo lets another app hand it a draft by writing an invoice file into its `invoices/` folder, in its format
(saldo/core/model.py Invoice), named <id>.json. Bodega writes: the Saldo profile this Bodega profile sends to
(asked once, then remembered), the renter, one line per rental line with its dates, the discount and the rental's
sales tax, so Saldo's total is the rental's total. The number follows Saldo's own counting
(saldo/core/numbering.py: the highest in the series, plus one).

The rental remembers the draft it became. Sending it again updates that draft while it's still a draft (what was
changed in Saldo otherwise stays, fields Bodega doesn't know included), and makes a new one once Saldo has sent it.

Saldo reads its folder only when it opens and numbers invoices from the ones it has open, so the window asks for
Saldo to be quit first. Bodega never writes into Saldo's folder before Saldo has been opened once (that would stop
Saldo bringing over what Cobro had), and never into Cobro's old folder. No Qt here.
"""

from __future__ import annotations

import json
import os
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path

from bodega.core import addresses, dates, money, pricing
from bodega.core.model import Business, Rental
from bodega.core.store import safe_id, write_json

STATUS_WORDS = {"draft": "drafted", "sent": "sent", "paid": "was paid for"}
TERMS_DAYS = 15  # days to pay, when the Saldo profile sets none (Saldo's own default)
# what Bodega fills in on a draft it updates; everything else on it stays as Saldo has it
FROM_THE_RENTAL = ("client", "project", "work_dates", "items", "discount", "tax_rate")


def _standard(name: str) -> Path:
    home = Path.home()
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / name
    if sys.platform.startswith("win"):
        return Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local")) / name
    return Path(os.environ.get("XDG_DATA_HOME", home / ".local" / "share")) / name.lower()


def data_dir() -> Path:
    """Saldo's data folder (the same place Saldo keeps it; SALDO_DATA_DIR moves it, as it does Saldo's)."""
    env = os.environ.get("SALDO_DATA_DIR")
    return Path(env) if env else _standard("Saldo")


def cobro_dir() -> Path:
    """Where Cobro kept its files, before it became Saldo (only ever looked at, never written)."""
    env = os.environ.get("COBRO_DATA_DIR")
    return Path(env) if env else _standard("Cobro")


def _read(path: Path, default):
    """Read one of Saldo's files without ever touching it (Bodega's own reader sets broken files aside)."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def installed() -> bool:
    """Saldo has been opened on this computer and has a profile."""
    return (data_dir() / "businesses.json").is_file()


def waiting_for_cobro() -> bool:
    """Cobro's files are here but Saldo hasn't been opened yet to bring them over."""
    return not installed() and (cobro_dir() / "businesses.json").is_file()


def profiles() -> list[dict]:
    """Saldo's profiles (each a dict with at least an id and a name)."""
    got = _read(data_dir() / "businesses.json", [])
    return [d for d in got if isinstance(d, dict) and str(d.get("id", ""))] if isinstance(got, list) else []


def profile_for(found: list[dict], b: Business | None) -> dict | None:
    """The Saldo profile this Bodega profile sends to: the one it was given, or the only one. None: ask."""
    if b is not None and b.saldo_profile:
        for d in found:
            if str(d.get("id")) == b.saldo_profile:
                return d
    return found[0] if len(found) == 1 else None


# Saldo's numbers (saldo/core/numbering.py)
def _clean_prefix(prefix: str) -> str:
    p = re.sub(r"[^A-Za-z0-9-]", "", prefix or "").strip("-").upper()
    return p or "INV"


def _client_code(name: str) -> str:
    letters = re.sub(r"[^A-Za-z0-9]", "", name or "").upper()
    if not letters:
        return ""
    return (letters[0] + "".join(ch for ch in letters[1:] if ch not in "AEIOU"))[:4]


def _head(prefix: str, code: str, style: str) -> str:
    prefix, code = _clean_prefix(prefix), re.sub(r"[^A-Za-z0-9]", "", code or "").upper()[:8]
    if code and style == "client":
        return f"{prefix}-{code}"
    if code and style == "client_only":
        return code
    return prefix


def next_number(prefix: str, existing: list[str], year: int) -> str:
    head = f"{_clean_prefix(prefix)}-{year}-"
    highest, width = 0, 3
    for n in existing:
        if n.upper().startswith(head.upper()):
            tail = n[len(head) :]
            if tail.isdigit():
                highest = max(highest, int(tail))
                width = max(width, len(tail))
    return f"{head}{highest + 1:0{width}d}"


def _whole(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return default


# The invoice
def invoice_for(lib, r: Rental, b: Business | None, profile: dict, taken: list[str]) -> dict:
    t = pricing.totals(lib, r, b)
    items = []
    for line, amount, days in zip(r.lines, t.line_amounts, t.line_days, strict=False):
        name = pricing.line_name(lib, line)
        bits = []
        if line.qty > 1:
            bits.append(f"{line.qty} ×")
        if line.kind != "fee":
            a, z = pricing.line_dates(r, line)
            if a:
                bits.append(dates.span(a, z or a))
            bits.append(f"{days.billed} day{'s' if days.billed != 1 else ''}")
        items.append({"description": name, "details": " · ".join(bits), "qty": "1", "rate": str(amount)})
    who = r.client
    client_name = (who.company or who.name).strip()
    client = {
        "id": uuid.uuid4().hex[:12],
        "name": client_name,
        "contact": who.name.strip() if who.company.strip() else "",
        "address": "\n".join(addresses.of(who)),
        "email": who.email,
        "code": "",
    }
    style = str(profile.get("number_style") or "year")
    code = _client_code(client_name) if style != "year" else ""
    today = dates.today()
    number = next_number(_head(str(profile.get("prefix", "")), code, style), taken, today.year)
    now = datetime.now().isoformat(timespec="seconds")
    pick, ret = pricing.span_of(r)
    return {
        "id": uuid.uuid4().hex[:12],
        "business_id": str(profile.get("id", "")),
        "number": number,
        "auto_number": True,
        "client": client,
        "issued": dates.iso(today),
        "terms_days": _whole(profile.get("terms_days"), TERMS_DAYS),
        "project": r.project or r.number,
        "work_dates": dates.span(pick, ret or pick) if pick else "",
        "delivered": "",
        "items": items or [{"description": "", "details": "", "qty": "1", "rate": ""}],
        "discount": str(t.discount) if t.discount else "",
        "deposit": "",
        "tax_rate": str(money.parse(r.tax_rate)) if money.parse(r.tax_rate) else "",
        "payment": str(profile.get("payment") or ""),
        "terms": str(profile.get("terms") or ""),
        "note": f"Rental {r.number}" + (f" · {profile.get('note')}" if profile.get("note") else ""),
        "status": "draft",
        "sent_on": "",
        "paid_on": "",
        "created": now,
        "updated": now,
    }


def _invoices() -> Path:
    return data_dir() / "invoices"


def draft_of(r: Rental) -> dict | None:
    """The invoice this rental became in Saldo, as Saldo has it now (None if there isn't one any more)."""
    if not safe_id(r.saldo_invoice):
        return None
    got = _read(_invoices() / f"{r.saldo_invoice}.json", None)
    return got if isinstance(got, dict) and str(got.get("id", "")) == r.saldo_invoice else None


def where(r: Rental) -> str:
    """Where the rental's invoice stands in Saldo, for its panel ('' if it was never sent)."""
    if not r.saldo_invoice:
        return ""
    inv = draft_of(r)
    if inv is None:
        return f"Invoice {r.saldo_number} isn't in Saldo any more." if r.saldo_number else ""
    n = str(inv.get("number", "") or r.saldo_number)
    return {
        "draft": f"Draft invoice {n} in Saldo, not sent yet.",
        "sent": f"Invoice {n} sent from Saldo.",
        "paid": f"Invoice {n} paid, in Saldo.",
    }.get(str(inv.get("status")), f"Invoice {n} in Saldo.")


def said(inv: dict) -> str:
    """ "sent INV-2026-014": what Saldo has done with an invoice, in a few words."""
    return f"{STATUS_WORDS.get(str(inv.get('status')), 'has')} {inv.get('number', '')}".strip()


def send(lib, r: Rental, b: Business | None, profile: dict) -> tuple[str, bool]:
    """Write the rental into Saldo as a draft: the one it became, while it's still a draft, else a new one.
    Remembers it on the rental (save the rental after). Returns (its number, whether a draft was updated).
    OSError with a plain message if it can't."""
    if not installed():
        raise OSError("Saldo isn't set up on this computer yet. Open it once and add your profile.")
    folder = _invoices()
    taken = []
    for f in folder.glob("*.json") if folder.is_dir() else []:
        d = _read(f, None)
        if isinstance(d, dict) and isinstance(d.get("number"), str):
            taken.append(d["number"])
    fresh = invoice_for(lib, r, b, profile, taken)
    old = draft_of(r)
    if old is not None and old.get("status") == "draft":
        inv = {**old, **{k: fresh[k] for k in FROM_THE_RENTAL}, "updated": fresh["updated"]}
        updated = True
    else:
        inv, updated = fresh, False
    write_json(folder / f"{inv['id']}.json", inv)
    r.saldo_invoice, r.saldo_number = inv["id"], str(inv.get("number", ""))
    r.happened(f"Draft invoice {r.saldo_number} updated in Saldo" if updated else f"Sent to Saldo as {r.saldo_number}")
    return r.saldo_number, updated
