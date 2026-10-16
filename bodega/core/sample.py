"""A made-up rental house with a little gear, a package and a rental (tests, the smoke test, screenshots).
Never put real people's details here: the repo is public."""

from __future__ import annotations

from bodega.core import dates
from bodega.core.model import Business, Client, Item, Package, PackageLine, RentalLine
from bodega.core.store import Library


def business() -> Business:
    return Business(
        name="Juniper Lane Films",
        tagline="Camera · Lighting · Grip",
        email="rentals@juniperlane.example",
        phone="(505) 555-0142",
        address="1200 Sample Ave",
        city="Albuquerque",
        region="NM",
        postal="87102",
        prefix="JLF",
    )


GEAR = [
    # (department, group, name, qty, value, parent name, serials)
    ("Camera", "Body", "Sony FX6 Cinema Camera (Body Only)", 1, "5998", "", ["5021734"]),
    ("Camera", "Body", "Tilta Camera Cage for Sony FX6", 1, "279", "Sony FX6 Cinema Camera (Body Only)", []),
    ("Camera", "Body", "Tilta Top Handle for Sony FX6", 1, "69", "Sony FX6 Cinema Camera (Body Only)", []),
    (
        "Camera",
        "Body",
        "D-Tap Power Cable for Sony FX6",
        1,
        "113.52",
        "Sony FX6 Cinema Camera (Body Only)",
        [],
    ),
    ("Camera", "Media", "Sony 960GB CFexpress Type A Card", 2, "748", "", ["A1", "A2"]),
    ("Camera", "Batteries", "Mini V-Mount Battery", 6, "249.99", "", []),
    ("Camera", "Lenses", "Cine Prime 21mm T1.4 (PL)", 1, "2649", "", ["DZ2104"]),
    ("Camera", "Lenses", "Cine Prime 40mm T1.4 (PL)", 1, "2149", "", ["DZ4011"]),
    ("Camera", "Lenses", "PL to Sony E Lens Adapter", 1, "269", "", []),
    ("Camera", "Monitoring", "7-inch On-Camera Monitor", 1, "1299", "", []),
    ("G&E", "Lights", "Aputure STORM 80c LED Monolight", 3, "599", "", ["80C-118", "80C-119", "80C-120"]),
    ("G&E", "Lights", "CF4 Fresnel for STORM 80c", 2, "109", "Aputure STORM 80c LED Monolight", []),
    ("G&E", "Lights", "Light Dome 40 for STORM 80c", 1, "99", "Aputure STORM 80c LED Monolight", []),
    ("G&E", "Steel", "C-Stand with Grip Arm Kit (10.5')", 4, "263", "", []),
    ("G&E", "Steel", "Combo Triple Riser Stand", 2, "390", "", []),
    ("G&E", "Grip", "Sandbag (25 lb)", 8, "76", "", []),
    ("Audio", "Microphones", "Shotgun Microphone", 1, "699", "", ["NTG-55120"]),
    ("Audio", "Microphones", "Boompole (10.6')", 1, "149", "", []),
]


def fill(lib: Library) -> Library:
    """Add the sample profile, gear, a package and a rental to an (empty) library."""
    b = lib.add_business(business())
    by_name: dict[str, Item] = {}
    for dep, group, name, qty, value, parent, serials in GEAR:
        it = Item(name=name, department=dep, group=group, qty=qty, value=value, serials=list(serials))
        it.brand = next((b for b in ("Sony", "Tilta", "Aputure") if name.startswith(b)), "")
        it.series = {"Sony FX6": "FX", "Aputure STORM": "STORM"}.get(" ".join(name.split()[:2]), "")
        if parent:
            it.parent = by_name[parent].id
        lib.add_item(it)
        by_name[name] = it
    lib.save_items()
    pkg = Package(
        name="FX6 Run & Gun",
        notes="Everything for a small documentary crew: camera, two primes, power and media.",
        lines=[
            PackageLine(by_name["Sony FX6 Cinema Camera (Body Only)"].id),
            PackageLine(by_name["Cine Prime 21mm T1.4 (PL)"].id),
            PackageLine(by_name["Cine Prime 40mm T1.4 (PL)"].id),
            PackageLine(by_name["PL to Sony E Lens Adapter"].id),
            PackageLine(by_name["Sony 960GB CFexpress Type A Card"].id, 2),
            PackageLine(by_name["Mini V-Mount Battery"].id, 4),
        ],
    )
    lib.packages[pkg.id] = pkg
    lib.save_packages()
    client = lib.save_client(
        Client(
            name="Alex Rivera",
            company="Northwind Media",
            email="alex@northwind.example",
            phone="(602) 555-0199",
            address="88 Example St",
            city="Phoenix",
            region="AZ",
            postal="85004",
        )
    )
    r = lib.new_rental(b)
    r.client = client
    r.project = "Fall Brand Film"
    today = dates.today()
    start = dates.plus(today, (6 - today.weekday()) % 7 or 7)  # next Sunday
    r.pickup, r.return_date = dates.iso(start), dates.iso(dates.plus(start, 7))
    r.status = "booked"
    mon, wed = dates.iso(dates.plus(start, 1)), dates.iso(dates.plus(start, 3))
    r.lines = [
        RentalLine("package", pkg.id),  # Sunday to Sunday
        RentalLine("item", by_name["Aputure STORM 80c LED Monolight"].id, 2, pickup=mon, return_date=wed),
        RentalLine("item", by_name["C-Stand with Grip Arm Kit (10.5')"].id, 2, pickup=mon, return_date=wed),
        RentalLine("fee", "", 1, "75", "Delivery and pickup"),
    ]
    r.deposit = "1000"
    lib.save_rental(r)
    return lib
