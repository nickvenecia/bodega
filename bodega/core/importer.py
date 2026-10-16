"""Bring gear in from a spreadsheet (.xlsx or .csv), and send it back out as .csv.

Spreadsheets laid out by hand are read the way a person reads them:
- the header row is found by its words (Qty, Equipment / Item / Name, Cost / Value, Rent?, Serial, Link…);
- a row with only a word in the first column ("Camera", "Lenses") is a heading. Known departments
  (Camera, G&E, Audio, Post…) start a department; any other heading starts a group inside it;
- a row with a word only in the name column ("1000c", "Steel") is a group heading too;
- every other row with a name is an item.

The percent and tax in formulas like `=(C6*1.0825)*A6` and a 0.04 in the header row are picked up, so the
day-rate settings can match the sheet.

After reading, gear made for another piece ("Tilta Cage for Sony FX6", "CF4 Fresnel for STORM 80c") is
attached to that piece (see attach_guesses). It's a suggestion: everything can be changed after.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from bodega.core import money, web
from bodega.core.log import get_logger
from bodega.core.model import Item, clamp_qty

log = get_logger(__name__)

DEPARTMENTS = {
    "camera": "Camera",
    "g&e": "G&E",
    "g & e": "G&E",
    "grip": "Grip",
    "electric": "Electric",
    "grip & electric": "G&E",
    "grip and electric": "G&E",
    "lighting": "Lighting",
    "audio": "Audio",
    "sound": "Sound",
    "post": "Post",
    "post production": "Post",
    "art": "Art",
    "production": "Production",
}

# header words -> our column names
HEADERS = {
    "qty": "qty",
    "quantity": "qty",
    "count": "qty",
    "#": "qty",
    "equipment": "name",
    "item": "name",
    "name": "name",
    "gear": "name",
    "description": "name",
    "replacement cost (per/unit)": "value",
    "replacement cost": "value",
    "unit value": "value",
    "value": "value",
    "cost": "value",
    "price": "value",
    "rent?": "rentable",
    "rent": "rentable",
    "rentable": "rentable",
    "serial": "serials",
    "serials": "serials",
    "serial number": "serials",
    "serial numbers": "serials",
    "serial no.": "serials",
    "s/n": "serials",
    "link": "link",
    "url": "link",
    "notes": "notes",
    "note": "notes",
    "department": "department",
    "category": "department",
    "company": "brand",
    "brand": "brand",
    "make": "brand",
    "manufacturer": "brand",
    "series": "series",
    "model": "series",
    "group": "group",
    "day rate": "day_rate",
    "belongs to": "parent",
    "status": "status",
}


# film-gear companies (more get recognised when several pieces start with the same word)
BRANDS = [
    "Kondor Blue", "Dana Dolly", "Iron Glass", "Modern Studio", "Gator Cases", "Canvas Grip", "Blackmagic Design",
    "Peak Design", "Think Tank", "Western Digital", "Light & Motion", "Wooden Camera", "Bright Tangerine",
    "Anton Bauer", "Core SWX", "Sound Devices", "Ready Rig", "Mole Richardson", "Matthews Studio Equipment",
    "Sony", "Canon", "Nikon", "Panasonic", "Blackmagic", "ARRI", "RED", "Fujifilm", "Sigma", "Zeiss", "Leica",
    "Tilta", "SmallRig", "Aputure", "amaran", "Godox", "Nanlite", "Litepanels", "Astera", "Quasar", "DJI",
    "Teradek", "SmallHD", "Atomos", "Sennheiser", "RODE", "Shure", "Deity", "Zoom", "Tascam", "Matthews",
    "Avenger", "Manfrotto", "Sachtler", "Pelican", "SKB", "Apache", "DZOFilm", "Laowa", "Sirui", "Tokina",
    "Rokinon", "Samyang", "Cooke", "Tiffen", "NiSi", "PolarPro", "IDX", "Bebob", "SanDisk", "Samsung", "Apple",
    "Angelbird", "ProGrade", "Lexar", "LaCie", "Impact", "Westcott", "Profoto", "Chimera", "Inovativ", "Bessey",
    "Kupo", "Neewer", "Ulanzi", "Hollyland", "Accsoon", "Zhiyun", "Moza", "Easyrig", "Auray", "Kino Flo",
    "Niceyrig", "Tiltaing", "Dunlop", "Livewire", "CAMVATE", "8Sinn", "Sensei",
]  # fmt: skip
# words a name often starts with that aren't a company
NOT_BRANDS = {
    "the", "a", "an", "pair", "set", "custom", "universal", "portable", "heavy", "large", "small", "mini", "new",
    "used", "black", "white", "pro", "kit", "cine", "prime", "lens", "lenses", "stand", "c-stand", "combo",
    "sandbag", "shotgun", "boompole", "boom", "cable", "battery", "batteries", "monitor", "light", "led", "case",
    "hard", "soft", "on-camera", "camera", "wireless", "power", "dual", "single", "triple", "extension", "apple box",
    "apple", "hdmi", "sdi", "usb", "xlr", "d-tap", "pl", "ef", "v-mount", "gold", "mount", "rod", "rods", "clamp",
    "grip", "arm", "head", "tripod", "slider", "dolly", "track", "cart", "bag", "flag", "frame", "net", "silk",
    "bounce", "dimmer", "stinger", "cord", "adapter", "filter", "matte", "box", "card", "drive", "ssd", "hdd",
}  # fmt: skip


def _first_word(name: str) -> str:
    return (name or "").strip().split(" ", 1)[0].strip(",;:-")


def guess_brand(name: str, common: set[str] | None = None) -> str:
    """The company, read off the front of a gear name ("Aputure STORM 80c" -> "Aputure"). "" if unsure.
    `common`: first words several of your pieces share (likely companies too)."""
    name = (name or "").strip()
    low = name.lower()
    for b in sorted(BRANDS, key=len, reverse=True):
        if low == b.lower() or low.startswith(b.lower() + " "):
            return name[: len(b)] if b != "Matthews Studio Equipment" else "Matthews"
    first = _first_word(name)
    if not first or first.lower() in NOT_BRANDS or "/" in first or '"' in first:
        return ""
    if not re.search(r"[A-Za-z]{2}", first) or re.match(r"^\d+(pcs|pc|x|mm|gb|tb|in|ft)\b", first.lower()):
        return ""
    if re.match(r"^\d+-", first):  # "7-inch"
        return ""
    if common and first.lower() in common:
        return first
    if re.fullmatch(r"[A-Z]{3,}", first) or re.search(r"[a-z][A-Z]", first) or re.match(r"^\d+[A-Za-z]{3,}$", first):
        return first  # SHAPE, CAMVATE, SmallRig, LightBridge, 8Sinn
    return ""


def common_first_words(names: list[str]) -> set[str]:
    """First words that start two or more names: in a gear list, those are nearly always companies."""
    seen: dict[str, int] = {}
    for n in names:
        w = _first_word(n).lower()
        if w:
            seen[w] = seen.get(w, 0) + 1
    return {w for w, c in seen.items() if c >= 2 and w not in NOT_BRANDS}


@dataclass
class Imported:
    items: list[Item] = field(default_factory=list)
    attached: int = 0
    rate_pct: str = ""  # found in the sheet ("4")
    value_tax: str = ""  # found in the sheet ("8.25")
    skipped: int = 0
    # what the sheet didn't say, filled in (the Import window shows it): no quantity counts as 1, nothing
    # under Rent? means for rent, and a company guessed from the name
    assumed_qty: int = 0
    assumed_rent: int = 0
    skipped_qty: int = 0  # pieces with no quantity, left out (when asked)
    guessed_brand: int = 0
    sheet_total: Decimal | None = None  # the sheet's own Total row, to check what was read against


def total_check(got: Imported, currency: str = "$") -> str:
    """What the sheet's own total says about what was read: it matches (by each piece's price, or by price × how
    many), or the difference. '' when the sheet has no total to check."""
    if got.sheet_total is None:
        return ""
    each = sum((money.parse(i.value) for i in got.items), money.ZERO)
    every = sum((money.parse(i.value) * i.qty for i in got.items), money.ZERO)
    said = money.fmt(got.sheet_total, currency)
    if money.cents(got.sheet_total) in (money.cents(each), money.cents(every)):
        return f"The sheet's own total, {said}, matches what was read."
    read = every if abs(every - got.sheet_total) <= abs(each - got.sheet_total) else each
    return (
        f"The sheet's own total is {said}; what was read adds up to {money.fmt(read, currency)} "
        f"({money.fmt(abs(got.sheet_total - read), currency)} {'less' if read < got.sheet_total else 'more'}). "
        "Check the rows that were left out."
    )


def _clean(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return re.sub(r"\s+", " ", str(v)).strip()


def _clean_lines(v) -> str:
    """Like _clean, but keeps line breaks (notes)."""
    if v is None:
        return ""
    lines = [re.sub(r"[^\S\n]+", " ", ln).strip() for ln in str(v).replace("\r\n", "\n").split("\n")]
    return "\n".join(lines).strip()


def _is_formula(v) -> bool:
    return isinstance(v, str) and v.startswith("=")


def _number(v) -> Decimal | None:
    if v is None or isinstance(v, bool) or _is_formula(v):
        return None
    if isinstance(v, (int, float)):
        d = Decimal(str(v))
    else:
        s = re.sub(r"[^\d.\-]", "", str(v))
        if not s or s in ("-", "."):
            return None
        try:
            d = Decimal(s)
        except ArithmeticError:
            return None
    return d if d.is_finite() and abs(d) < money.LIMIT else None


def _truthy(v) -> bool | None:
    if isinstance(v, bool):
        return v
    s = _clean(v).lower()
    if s in ("true", "yes", "y", "x", "1", "✓"):
        return True
    if s in ("false", "no", "n", "0"):
        return False
    return None


def _value_text(d: Decimal | None) -> str:
    if d is None:
        return ""
    d = money.cents(d)
    return f"{d:f}".rstrip("0").rstrip(".") if "." in f"{d:f}" else f"{d:f}"


# Reading rows
_HYPERLINK = re.compile(r'^=\s*HYPERLINK\(\s*"([^"]+)"\s*(?:[,;]\s*"([^"]*)"\s*)?\)\s*$', re.I)


def _hyperlink_formula(value) -> tuple[str, str] | None:
    """(url, text) from =HYPERLINK("url", "text"), else None."""
    if not isinstance(value, str) or "HYPERLINK" not in value.upper():
        return None
    m = _HYPERLINK.match(value.strip())
    if not m:
        return None
    return m.group(1), m.group(2) if m.group(2) is not None else m.group(1)


# Google Sheets
GOOGLE_SHEET = re.compile(r"docs\.google\.com/spreadsheets/d/([A-Za-z0-9_-]{20,})")


def google_export_url(link: str) -> str | None:
    """A Google Sheets link -> the address that downloads it as .xlsx (links included). None if it isn't one."""
    m = GOOGLE_SHEET.search(link or "")
    if not m:
        return None
    return f"https://docs.google.com/spreadsheets/d/{m.group(1)}/export?format=xlsx"


NOT_SHARED = (
    "Google didn't share that sheet with Bodega. In the sheet, click Share and set General access to "
    "Anyone with the link, then try again."
)


def download_google_sheet(link: str, folder: Path) -> Path:
    """Download a Google Sheet as .xlsx into `folder`. Raises OSError with a plain message."""
    import urllib.request

    from bodega.core.net import ssl_context

    url = google_export_url(link)
    if url is None:
        raise OSError("That isn't a Google Sheets link. It starts with docs.google.com/spreadsheets.")
    req = urllib.request.Request(url, headers={"User-Agent": "Bodega"})
    try:
        with urllib.request.urlopen(req, timeout=30, context=ssl_context()) as resp:
            kind = (resp.headers.get("Content-Type") or "").lower()
            data = resp.read(MAX_FILE_BYTES + 1)
    except Exception as e:  # urllib raises many kinds
        code = getattr(e, "code", None)
        if code in (401, 403, 404):
            raise OSError(NOT_SHARED) from e
        raise OSError("Couldn't reach Google. Check your internet and try again.") from e
    if len(data) > MAX_FILE_BYTES:
        raise OSError("That sheet is too big to be a gear list.")
    if "html" in kind or not data.startswith(b"PK"):  # a sign-in page instead of the file
        raise OSError(NOT_SHARED)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "Google Sheet.xlsx"
    path.write_bytes(data)
    return path


MAX_FILE_BYTES = 50_000_000  # a gear list is kilobytes; anything this big isn't one
MAX_UNPACKED_BYTES = 200_000_000  # an .xlsx is a zip: what it unpacks to, at most
MAX_ROWS = 50_000  # rows in all of a sheet's tabs: a gear list has hundreds
MAX_COLUMNS = 500
TOO_BIG = "{name} is too big to be a gear list ({why}). Split it, or import only the part with your gear."


def _check_size(path: Path) -> None:
    """Refuse files too big to be a gear list, and .xlsx files that unpack to something huge (a "zip bomb")."""
    import zipfile

    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            raise OSError(f"{path.name} is too big to be a gear list.")
        if path.suffix.lower() in (".xlsx", ".xlsm"):
            with zipfile.ZipFile(path) as z:
                if sum(i.file_size for i in z.infolist()) > MAX_UNPACKED_BYTES:
                    raise OSError(f"{path.name} is too big to be a gear list.")
    except zipfile.BadZipFile as e:
        raise OSError(f"Bodega can't read {path.name}. Check that it's an Excel file (.xlsx).") from e


def safe_cell(value) -> object:
    """A cell for a CSV that a spreadsheet will open: text starting with = + - @ would run as a formula
    (and can fetch web pages or run commands), so it gets a leading ' (shown as text). Numbers stay."""
    if not isinstance(value, str) or not value or value[0] not in "=+-@\t\r":
        return value
    try:
        Decimal(value)
        return value  # -50 is a number, not a formula
    except ArithmeticError:
        return "'" + value


def _unquote(cell: str) -> str:
    """Undo safe_cell when reading our own CSV back."""
    return cell[1:] if len(cell) > 1 and cell[0] == "'" and cell[1] in "=+-@\t\r" else cell


class Rows(list):
    """A sheet's rows, plus the web links on its cells (row number -> the first link in that row).
    Gear lists often link each name to where it was bought."""

    def __init__(self, rows=(), links: dict[int, str] | None = None):
        super().__init__(rows)
        self.links: dict[int, str] = links or {}


def _rows_xlsx(path: Path) -> Rows:
    try:
        import openpyxl
    except ImportError as e:  # pragma: no cover - bundled with the app
        raise OSError("Bodega can't read .xlsx files here. Save the sheet as .csv and import that.") from e
    _check_size(path)
    try:
        wb = openpyxl.load_workbook(str(path), data_only=False)  # not read-only: that drops the links
    except Exception as e:
        raise OSError(f"Bodega can't read {path.name}. Check that it's an Excel file (.xlsx).") from e
    rows = Rows()
    try:
        if sum(ws.max_row or 0 for ws in wb.worksheets) > MAX_ROWS:
            raise OSError(TOO_BIG.format(name=path.name, why=f"more than {MAX_ROWS:,} rows"))
        if any((ws.max_column or 0) > MAX_COLUMNS for ws in wb.worksheets):
            raise OSError(TOO_BIG.format(name=path.name, why=f"more than {MAX_COLUMNS:,} columns"))
        for ws in wb.worksheets:
            for row in ws.iter_rows():
                link = next((c.hyperlink.target for c in row if c.hyperlink and c.hyperlink.target), "")
                values = []
                for c in row:
                    got = _hyperlink_formula(c.value)
                    if got:  # =HYPERLINK("url", "name"), as Google Sheets writes links
                        link = link or got[0]
                        values.append(got[1])
                    else:
                        values.append(c.value)
                if link and link.startswith(("http://", "https://", "www.")):
                    rows.links[len(rows)] = link
                rows.append(values)
            rows.append([])  # a sheet break
    finally:
        wb.close()
    return rows


def _decoded(raw: bytes) -> str:
    """A CSV's words: UTF-8 (what most apps write), else Windows' own (Excel's "CSV" on Windows: "Café", "–"),
    else Latin-1, which reads any bytes at all."""
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1")


def _rows_csv(path: Path) -> list[list]:
    _check_size(path)
    try:
        raw = path.read_bytes()
    except OSError as e:
        raise OSError(f"Bodega can't open {path.name}.") from e
    text = _decoded(raw)
    out = []
    try:
        for r in csv.reader(io.StringIO(text, newline="")):  # keeps line breaks inside cells
            if len(out) >= MAX_ROWS:
                raise OSError(TOO_BIG.format(name=path.name, why=f"more than {MAX_ROWS:,} rows"))
            if len(r) > MAX_COLUMNS:
                raise OSError(TOO_BIG.format(name=path.name, why=f"more than {MAX_COLUMNS:,} columns"))
            out.append([_unquote(c) for c in r])
    except csv.Error as e:  # a cell far longer than any gear list's, or a broken quote
        raise OSError(f"Bodega can't read {path.name}: part of it isn't laid out as a sheet.") from e
    return out


def load_rows(path: Path) -> list[list]:
    """Every row of the sheet (all worksheets of an .xlsx, one after another), as cell values."""
    path = Path(path)
    return _rows_xlsx(path) if path.suffix.lower() in (".xlsx", ".xlsm") else _rows_csv(path)


def fill_brands(items: list[Item], also: list[str] | None = None) -> int:
    """Guess the company where it's blank. Returns how many got one."""
    common = common_first_words([i.name for i in items] + (also or []))
    n = 0
    for it in items:
        if not it.brand:
            it.brand = guess_brand(it.name, common)
            n += bool(it.brand)
    return n


def read(path: Path) -> Imported:
    """Read a sheet the way Bodega guesses it's laid out, gear attached where it says what it's for."""
    path = Path(path)
    out = parse_rows(load_rows(path))
    out.attached = attach_guesses(out.items)
    log.info("imported %d items (%d attached) from %s", len(out.items), out.attached, path.name)
    return out


# what each of our fields is called in the Import window, in the order shown there
FIELDS = [
    ("name", "Name"),
    ("brand", "Company"),
    ("series", "Series"),
    ("qty", "How Many"),
    ("value", "Paid Each"),
    ("rentable", "For Rent"),
    ("day_rate", "Day Rate"),
    ("serials", "Serial Numbers"),
    ("department", "Department"),
    ("group", "Group"),
    ("parent", "Belongs To"),
    ("link", "Link"),
    ("notes", "Notes"),
    ("status", "Status"),
]


@dataclass
class Layout:
    """Where things are in a sheet: the header row (-1: none) and which column holds which field."""

    head: int
    cols: dict[str, int]
    labels: list[str]  # "A · Qty", "B · Equipment"… one per column


def column_letter(i: int) -> str:
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def detect(rows: list[list]) -> Layout:
    head, cols = _find_header(rows)
    if head < 0:
        cols = {"qty": 0, "name": 1, "value": 2, "rentable": 4}
    width = max((len(r) for r in rows[: max(head, 0) + 60]), default=0)
    header = rows[head] if head >= 0 else []
    labels = []
    for c in range(width):
        word = _clean(header[c]) if c < len(header) else ""
        if not word or _number(header[c]) is not None:
            # no header word: show the first thing written in that column
            word = next(
                (
                    _clean(r[c])
                    for r in rows[head + 1 : head + 40]
                    if c < len(r) and _clean(r[c]) and not _is_formula(r[c])
                ),
                "",
            )
            word = (word[:24] + "…") if len(word) > 25 else word
        labels.append(f"{column_letter(c)} · {word}" if word else column_letter(c))
    return Layout(head, {k: v for k, v in cols.items() if v < max(width, 1)}, labels)


def _find_header(rows: list[list]) -> tuple[int, dict[str, int]]:
    for r, row in enumerate(rows[:40]):
        cols: dict[str, int] = {}
        for c, v in enumerate(row):
            key = HEADERS.get(_clean(v).lower())
            if key and key not in cols:
                cols[key] = c
        if "name" in cols and len(cols) >= 2:
            return r, cols
    return -1, {}


def parse_rows(
    rows: list[list],
    layout: Layout | None = None,
    guess_brands: bool = True,
    blank_rent: bool = True,
    no_qty: str = "one",
) -> Imported:
    """Turn rows into items. `layout` says which column is which (detect() guesses it). What the sheet
    leaves blank is filled in and counted (Imported.assumed_*); `guess_brands`: a blank company is guessed;
    `blank_rent`: what a blank Rent? means (for rent, or not); `no_qty`: a piece with no quantity counts as
    "one", or is left out ("skip", counted in Imported.skipped_qty)."""
    out = Imported()
    layout = layout or detect(rows)
    head, cols = layout.head, dict(layout.cols)
    if "name" not in cols:
        return out
    if head >= 0:
        # a lone percent in the header row ("0.04" over the rent column) is the day-rate percent
        for v in rows[head]:
            n = _number(v)
            if n is not None and 0 < n < 1:
                out.rate_pct = _value_text(n * 100)
    name_col = cols["name"]
    department = group = ""
    links = getattr(rows, "links", {})
    for n, row in enumerate(rows[head + 1 :], head + 1):
        cells = list(row) + [None] * (max(cols.values()) + 1 - len(row))

        def get(key: str, cells=cells):
            c = cols.get(key)
            return cells[c] if c is not None and c < len(cells) else None

        for v in cells:  # pick up the tax in formulas like =(C6*1.0825)*A6
            if not out.value_tax and _is_formula(v):
                m = re.search(r"\*\s*1\.(\d{2,4})\b", v)
                if m:
                    out.value_tax = _value_text(Decimal("0." + m.group(1)) * 100)
        name = _clean(get("name"))
        qty = _number(get("qty"))
        value = _number(get("value"))
        first = cells[0] if cells else None
        first_text = "" if _is_formula(first) or name_col == 0 else _clean(first)

        # a heading in the first column ("Camera", "Lenses")
        if first_text and not name and qty is None and value is None and _number(first) is None:
            known = DEPARTMENTS.get(first_text.lower())
            if known or not department:
                department, group = known or first_text, ""
            else:
                group = first_text
            continue
        if not name:
            continue
        low = name.lower()
        if low in ("equipment total", "total", "rental cost", "subtotal"):
            if low in ("equipment total", "total") and value is not None:
                out.sheet_total = Decimal(str(value))  # kept, to check what was read against it
            continue
        # a heading in the name column ("1000c", "Steel", or "Post" under a repeated header row)
        others_empty = qty is None and value is None and not _clean(get("serials")) and not _clean(get("link"))
        if others_empty:
            known = DEPARTMENTS.get(low)
            if known:
                department, group = known, ""
            else:
                group = name
            continue
        it = Item(name=name, department=_clean(get("department")) or department, imported_as=name)
        it.group = _clean(get("group")) or group or it.department  # no sub-heading: the heading is its group
        it.brand = _clean(get("brand"))
        it.series = _clean(get("series"))
        if qty is None and no_qty == "skip":
            out.skipped_qty += 1
            continue
        it.qty = clamp_qty(qty) if qty is not None else 1
        out.assumed_qty += qty is None
        it.value = _value_text(value)
        rent = _truthy(get("rentable"))
        it.rentable = blank_rent if rent is None else rent
        out.assumed_rent += rent is None
        serial_text = _clean(get("serials"))
        if serial_text:
            it.serials = [s.strip() for s in re.split(r"[;,\n]| / ", serial_text) if s.strip()]
            it.qty = max(it.qty, len(it.serials))
        it.link = web.web_link(_clean(get("link"))) or web.web_link(links.get(n, ""))  # web pages only
        it.notes = _clean_lines(get("notes"))
        rate = _number(get("day_rate"))
        it.day_rate = _value_text(rate) if rate is not None else ""
        status = _clean(get("status")).lower()
        if status in ("repair", "in repair"):
            it.status = "repair"
        elif status == "retired":
            it.status = "retired"
        parent = _clean(get("parent"))
        if parent:
            it.parent = "name:" + parent  # resolved below, once every item is read
        out.items.append(it)

    by_name = {i.name.casefold(): i for i in out.items}
    for it in out.items:
        if it.parent.startswith("name:"):
            p = by_name.get(it.parent[5:].casefold())
            it.parent = p.id if p is not None and p is not it else ""
    out.guessed_brand = fill_brands(out.items) if guess_brands else 0
    return out


# Attaching
_GENERIC = {
    "for", "with", "and", "the", "a", "an", "of", "to", "kit", "set", "case", "cable", "cables", "mount",
    "black", "silver", "white", "gray", "grey", "space", "pro", "plus", "mini", "series", "system",
    "adapter", "light", "lights", "camera", "cameras", "monitor", "lens", "lenses", "led", "us", "v",
    "rig", "universal", "hard", "soft", "power", "battery", "plate", "bag", "pack", "type",
}  # fmt: skip


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", text.lower()) if len(t) >= 2}


def _weight(tok: str) -> int:
    if tok in _GENERIC:
        return 0
    has_digit = any(ch.isdigit() for ch in tok)
    has_alpha = any(ch.isalpha() for ch in tok)
    if has_digit and has_alpha:
        return 3  # a model name: FX6, 80c, CF12, UTX-B40
    if has_digit:
        return 2  # a plain number ("Cine 13")
    return 1


def _score(want: set[str], cand: set[str]) -> int:
    total = 0
    for t in want:
        w = _weight(t)
        if not w:
            continue
        if t in cand:
            total += w
        elif w == 3 and any(c.startswith(t) and len(t) >= 3 for c in cand):
            total += 2  # "UWP-D" names the "UWP-D26"
    return total


def _identity(name: str) -> str:
    """What a thing IS, without what it's for: "Tilta Top Handle for Sony FX6" -> "Tilta Top Handle"."""
    return re.split(r"\bfor\b", name, maxsplit=1, flags=re.IGNORECASE)[0]


def attach_guesses(items: list[Item]) -> int:
    """Attach gear that says what it's for ("… for Sony FX6") to the best match. Returns how many.

    Each "for …" is compared with what every other item IS (its name up to its own "for"), model names
    weighing most. Gear attached to attached gear hangs off the top item, and nothing goes in a circle."""
    ident = {it.id: _tokens(_identity(it.name)) for it in items}
    by_id = {it.id: it for it in items}

    def chain(it: Item) -> list[str]:
        out, cur = [it.id], it
        while cur.parent and cur.parent in by_id and cur.parent not in out:
            cur = by_id[cur.parent]
            out.append(cur.id)
        return out

    count = 0
    for it in items:
        if it.parent:
            continue
        m = re.search(r"\bfor\b(.*)$", it.name, re.IGNORECASE)
        if not m:
            continue
        want = _tokens(m.group(1))
        best, best_score = None, 0
        for other in items:
            if other is it:
                continue
            s = _score(want, ident[other.id])
            if s > best_score or (
                s == best_score and best is not None and money.parse(other.value) > money.parse(best.value)
            ):
                best, best_score = other, s
        if best is None or best_score < 3:
            continue
        up = chain(best)
        if it.id in up:
            continue  # would go in a circle
        it.parent = up[-1]
        count += 1
    for it in items:  # flatten: everything hangs off a top item
        if it.parent:
            up = chain(it)
            it.parent = up[-1] if up[-1] != it.id else ""
    return count


# CSV out
CSV_COLUMNS = [
    "Department", "Group", "Name", "Company", "Series", "Qty", "Serial Numbers", "Unit Value", "Day Rate", "Rentable",
    "Belongs To", "Status", "Link", "Notes",
]  # fmt: skip


def write_csv(items: list[Item], lookup: dict[str, Item], path: Path) -> Path:
    """Every item as one row; reads back in with read()."""
    rows = []
    for it in items:
        parent = lookup.get(it.parent)
        rows.append([
            it.department, it.group, it.name, it.brand, it.series, it.qty, "; ".join(it.serial_list()), it.value,
            it.day_rate, "Yes" if it.rentable else "No", parent.name if parent else "",
            {"ready": "", "repair": "In Repair", "retired": "Retired"}[it.status], it.link, it.notes,
        ])  # fmt: skip
    return write_rows(CSV_COLUMNS, rows, path)


def write_rows(header: list[str], rows: list[list], path: Path) -> Path:
    """A CSV, written whole or not at all, every cell made safe for a spreadsheet (no formulas)."""
    import os
    import tempfile

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.stem}.", suffix=".csv", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(header)
            for row in rows:
                w.writerow(safe_cell(c) for c in row)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return path


KIT_COLUMNS = ["Name", "Pieces", "Day Rate", "Week", "Value", "Gear", "Notes"]
RENTAL_COLUMNS = [
    "Rental", "Status", "Renter", "Company", "Email", "Production", "Pickup", "Return", "Gear", "Fees",
    "Discount", "Tax", "Total", "Deposit",
]  # fmt: skip


def write_kits_csv(lib, kits: list, b, path: Path) -> Path:
    """Each kit as a row: its pieces, prices (as its list shows them) and what's in it."""
    from bodega.core import pricing

    wd = b.week_days if b else 7
    rows = []
    for p in kits:
        gear = pricing.package_gear(lib, p)
        rate = pricing.package_rate(lib, p, b)
        rows.append([
            p.name, sum(u for _i, u, _d in gear), str(rate), str(rate * wd), str(pricing.package_value(lib, p, b)),
            "; ".join(f"{u} × {it.name}" for it, u, _d in gear), p.notes,
        ])  # fmt: skip
    return write_rows(KIT_COLUMNS, rows, path)


def write_rentals_csv(lib, rentals: list, path: Path) -> Path:
    """Each rental as a row: who, when, its status and its money (each by its own profile's pricing)."""
    from bodega.core import dates, pricing
    from bodega.core.model import RENTAL_WORDS

    rows = []
    for r in rentals:
        t = pricing.totals(lib, r, lib.businesses.get(r.business_id))
        a, z = pricing.span_of(r)
        rows.append([
            r.number, RENTAL_WORDS.get(r.status, r.status), r.client.name, r.client.company, r.client.email, r.project,
            dates.iso(a) if a else "", dates.iso(z) if z else "", str(t.gear), str(t.fees), str(t.discount),
            str(t.tax), str(t.total), str(t.deposit),
        ])  # fmt: skip
    return write_rows(RENTAL_COLUMNS, rows, path)
