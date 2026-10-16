"""Bodega without a window: make a sample page, or read a spreadsheet and print the inventory.

python -m bodega cli sample OUT.pdf [--doc agreement|quote|inventory|ratecard|package] [--dark]
python -m bodega cli import SHEET.xlsx OUT.pdf [--doc inventory|ratecard]
python -m bodega cli update-check     (no internet: this copy reads a made-up newer release and finds its file)
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

DOCS = ("agreement", "quote", "inventory", "ratecard", "package")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="bodega cli")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sample", help="a sample page as PDF or PNG")
    s.add_argument("out")
    s.add_argument("--doc", choices=DOCS, default="agreement")
    s.add_argument("--dark", action="store_true", help="the preview's Dark Page colors")
    i = sub.add_parser("import", help="read a spreadsheet and save its inventory as PDF or PNG")
    i.add_argument("sheet")
    i.add_argument("out")
    i.add_argument("--doc", choices=("inventory", "ratecard"), default="inventory")
    i.add_argument("--name", default="", help="the name at the top of the page")
    sub.add_parser("update-check", help="check this copy can read a release and pick its own file (offline)")
    args = ap.parse_args(argv)
    if args.cmd == "update-check":
        return update_check()

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])  # noqa: F841 — fonts need an app

    from bodega.core import document, importer, sample
    from bodega.core.looks import palette
    from bodega.core.paths import use_data_dir
    from bodega.core.store import Library
    from bodega.doc import export, fonts, render

    fonts.load_bundled()
    tmp = Path(tempfile.mkdtemp(prefix="bodega-cli-"))
    use_data_dir(tmp)
    lib = Library(tmp).load()
    if args.cmd == "sample":
        sample.fill(lib)
        doc = args.doc
    else:
        from bodega.core.model import Business

        lib.add_business(Business(name=args.name) if args.name else sample.business())
        got = importer.read(Path(args.sheet))
        for it in got.items:
            lib.add_item(it)
        b = next(iter(lib.businesses.values()))
        b.rate_pct = got.rate_pct or b.rate_pct
        b.value_tax = got.value_tax or b.value_tax
        print(f"read {len(got.items)} items, attached {got.attached}", flush=True)
        doc = args.doc
    b = next(iter(lib.businesses.values()))
    if doc in ("agreement", "quote"):
        r = next(iter(lib.rentals.values()))
        if doc == "quote":
            r.status = "quote"
        view = document.build_rental(lib, r, b)
    elif doc == "inventory":
        view = document.build_inventory(lib, lib.ordered_items(), b)
    elif doc == "ratecard":
        view = document.build_ratecard(lib, lib.ordered_items(), list(lib.packages.values()), b)
    else:
        view = document.build_package(lib, next(iter(lib.packages.values())), b)
    pages = render.layout(view, palette(b.color, args.__dict__.get("dark", False)))
    out = Path(args.out)
    if out.suffix.lower() == ".png":
        export.to_png(pages, out)
    else:
        export.to_pdf(pages, out, title=view.title)
    print(f"wrote {out} ({len(pages)} page{'s' if len(pages) != 1 else ''})", flush=True)
    return 0


ASSETS = (  # the release files CI publishes (the names are a contract: README links, update.asset_name)
    "Bodega-mac-apple-silicon.dmg",
    "Bodega-mac-intel.dmg",
    "Bodega-windows-setup.exe",
    "Bodega-windows-portable.zip",
    "Bodega-linux-x64.AppImage",
    "Bodega-linux-x64.tar.gz",
)


def update_check() -> int:
    """What a real update does first, without the internet: read a release one version newer than this copy, see
    that it's newer, and find the file that updates this kind of install. 0 if all of that works."""
    from bodega import __version__
    from bodega.core import update

    major, minor, patch = update.version_tuple(__version__)
    newer = f"v{major}.{minor}.{patch + 1}"
    release = update.parse_release(
        {
            "tag_name": newer,
            "html_url": f"https://github.com/{update.REPO}/releases/tag/{newer}",
            "body": "## What's new\n- A check",
            "assets": [
                {
                    "name": n,
                    "browser_download_url": f"https://example.invalid/{n}",
                    "size": 1,
                    "digest": "sha256:00",
                }
                for n in ASSETS
            ],
        }
    )
    kind = update.install_kind()
    name = update.asset_name(kind)
    problems = []
    if not release.newer:
        problems.append(f"{newer} isn't seen as newer than {__version__}")
    if kind != "source" and (name is None or name not in release.assets):
        problems.append(f"no release file for this install ({kind})")
    if problems:
        print("update check failed: " + "; ".join(problems), flush=True)
        return 1
    print(
        f"update check ok: {kind} would update to {release.version} with {name or 'nothing (source)'}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
