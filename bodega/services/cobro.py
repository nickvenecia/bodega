"""Send a rental to Cobro (the invoice app) as a draft invoice.

Bodega writes the invoice straight into Cobro's data folder, in Cobro's own format (cobro/core/model.py
Invoice): your profile there (matched by name), the renter, one line per rental line with its dates, the
discount and the rental's sales tax, so Cobro's total is the rental's total. The number follows Cobro's
own counting (ported from cobro/core/numbering.py). Cobro shows it the next time it opens.

No Qt here.
"""

from __future__ import annotations

import json
import os
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path

from bodega.core import dates, money, pricing
from bodega.core.model import Business, Rental
from bodega.core.store import write_json


def data_dir() -> Path:
    """Cobro's data folder (the same place Cobro keeps it)."""
    env = os.environ.get("COBRO_DATA_DIR")
    if env:
        return Path(env)
    home = Path.home()
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / "Cobro"
    if sys.platform.startswith("win"):
        return Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local")) / "Cobro"
    return Path(os.environ.get("XDG_DATA_HOME", home / ".local" / "share")) / "cobro"


def _read(path: Path, default):
    """Read one of Cobro's files without ever touching it (Bodega's own reader sets broken files aside)."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def installed() -> bool:
    """Cobro has been opened on this computer (it has a profile file)."""
    return (data_dir() / "businesses.json").is_file()


# ---------------------------------------------------------------- Cobro's numbers (cobro/core/numbering.py)
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


# ---------------------------------------------------------------- the invoice
def _pick_business(businesses: list[dict], b: Business | None) -> dict:
    if not businesses:
        raise OSError("Open Cobro once and add your profile there first.")
    name = (b.name if b else "").strip().casefold()
    for d in businesses:
        if isinstance(d, dict) and str(d.get("name", "")).strip().casefold() == name and name:
            return d
    return businesses[0]


def invoice_for(lib, r: Rental, b: Business | None, cobro_business: dict, taken: list[str]) -> dict:
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
        "address": who.address,
        "email": who.email,
        "code": "",
    }
    style = str(cobro_business.get("number_style") or "year")
    code = _client_code(client_name) if style != "year" else ""
    today = dates.today()
    number = next_number(_head(str(cobro_business.get("prefix", "")), code, style), taken, today.year)
    now = datetime.now().isoformat(timespec="seconds")
    pick, ret = pricing.span_of(r)
    return {
        "id": uuid.uuid4().hex[:12],
        "business_id": str(cobro_business.get("id", "")),
        "number": number,
        "auto_number": True,
        "client": client,
        "issued": dates.iso(today),
        "terms_days": int(cobro_business.get("terms_days") or 15),
        "project": r.project or r.number,
        "work_dates": dates.span(pick, ret or pick) if pick else "",
        "delivered": "",
        "items": items or [{"description": "", "details": "", "qty": "1", "rate": ""}],
        "discount": str(t.discount) if t.discount else "",
        "deposit": "",
        "tax_rate": str(money.parse(r.tax_rate)) if money.parse(r.tax_rate) else "",
        "payment": str(cobro_business.get("payment") or ""),
        "terms": str(cobro_business.get("terms") or ""),
        "note": f"Rental {r.number}"
        + (f" · {cobro_business.get('note')}" if cobro_business.get("note") else ""),
        "status": "draft",
        "sent_on": "",
        "paid_on": "",
        "created": now,
        "updated": now,
    }


def send(lib, r: Rental, b: Business | None) -> str:
    """Write the draft invoice into Cobro. Returns its number. OSError with a plain message if it can't."""
    root = data_dir()
    if not installed():
        raise OSError("Cobro isn't set up on this computer yet. Open it once and add your profile.")
    businesses = _read(root / "businesses.json", [])
    chosen = _pick_business(businesses if isinstance(businesses, list) else [], b)
    folder = root / "invoices"
    taken = []
    for f in folder.glob("*.json") if folder.is_dir() else []:
        d = _read(f, None)
        if isinstance(d, dict) and isinstance(d.get("number"), str):
            taken.append(d["number"])
    inv = invoice_for(lib, r, b, chosen, taken)
    write_json(folder / f"{inv['id']}.json", inv)
    return inv["number"]
