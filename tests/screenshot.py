"""Screenshots of the window without a display, for checking UI changes.

    QT_QPA_PLATFORM=offscreen python tests/screenshot.py OUTDIR [SHEET.xlsx]
    BODEGA_LOOK=dark QT_QPA_PLATFORM=offscreen python tests/screenshot.py OUTDIR    (the dark look)
    BODEGA_ACCENT=yellow BODEGA_SIZE=1280x700 …                                     (another accent, another size)

Uses a throwaway data folder with the made-up sample rental house (or a spreadsheet you point it at),
never your real gear.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtWidgets import QApplication

from bodega.app import setup_app
from bodega.core import sample
from bodega.core.paths import use_data_dir
from bodega.core.store import Library

SIZE = tuple(int(n) for n in os.environ.get("BODEGA_SIZE", "1600x1000").split("x"))  # the window's
LOOK = os.environ.get("BODEGA_LOOK", "light")  # "light" or "dark"
ACCENT = os.environ.get("BODEGA_ACCENT", "")  # "" = Bodega's blue; or a key of tokens.ACCENTS


def wait(ms: int = 400) -> None:
    from PySide6.QtCore import QEventLoop, QTimer

    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def shot(w, path: Path) -> None:
    wait()
    w.grab().save(str(path))
    print("wrote", path)


def _give_photos(lib) -> None:
    """Made-up product shots (soft gradients with a shape) for a few pieces, so photos show in screenshots."""
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QRectF
    from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter

    from bodega.ui.components import photos

    tints = ["#2b2d42", "#5b48d9", "#11806f", "#a86a12", "#8d99ae", "#3d405b"]
    for n, it in enumerate(lib.ordered_items()[:12]):
        img = QImage(600, 600, QImage.Format.Format_RGB32)
        p = QPainter(img)
        g = QLinearGradient(0, 0, 600, 600)
        g.setColorAt(0, QColor("#f4f4f6"))
        g.setColorAt(1, QColor("#d9d9e0"))
        p.fillRect(img.rect(), g)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor(tints[n % len(tints)]))
        p.setPen(QColor(0, 0, 0, 0))
        p.drawRoundedRect(QRectF(150, 190, 300, 220), 40, 40)
        p.setBrush(QColor("#111"))
        p.drawEllipse(QRectF(250, 240, 120, 120))
        p.end()
        data = QByteArray()
        buf = QBuffer(data)
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        img.save(buf, "PNG")
        it.photo = photos.keep(bytes(data))
    lib.save_items()


def main(out: Path, sheet: Path | None = None) -> int:
    out.mkdir(parents=True, exist_ok=True)
    app = QApplication(sys.argv[:1])
    tmp = Path(tempfile.mkdtemp(prefix="bodega-shots-"))
    use_data_dir(tmp)
    setup_app(app)
    from bodega.ui.dialogs.preview import PageDialog
    from bodega.ui.window.main_window import MainWindow

    def window(lib):
        w = MainWindow(lib)
        w._restored = True  # a fixed size, not the screen's
        w.resize(*SIZE)
        w.set_look(LOOK)
        if ACCENT:
            w.set_accent(ACCENT)
        w.show()
        return w

    w = window(Library(tmp).load())
    shot(w, out / "1-first-launch.png")
    w.close()

    lib = sample.fill(Library(tmp).load())
    _give_photos(lib)
    from datetime import timedelta

    from bodega.core import dates
    from bodega.core.model import LogEntry

    for r in lib.rentals.values():  # gone out two days ago, so the gear is out and has earned something
        start = dates.parse(r.pickup)
        step = (dates.today() - timedelta(days=2) - start) if start else timedelta(0)
        for owner, key in [(r, "pickup"), (r, "return_date")] + [
            (ln, k) for ln in r.lines for k in ("pickup", "return_date")
        ]:
            d = dates.parse(getattr(owner, key))
            if d is not None:
                setattr(owner, key, dates.iso(d + step))
        r.status = "out"
        lib.save_rental(r)
    first = lib.ordered_items()[0]
    first.service_days = 90
    first.log = [LogEntry("2026-07-01", "service", "Sensor cleaned, firmware 4.0", "45")]
    lib.save_items()
    w = window(lib)
    if sheet is not None:
        w.import_file(sheet, ask=False)
    fx6 = next((i for i in lib.items.values() if "FX6" in i.name and not i.parent), None)
    if fx6 is not None:
        w.gear_table.open_pieces.add(fx6.id)  # (open, to show the gear under it)
        w.refresh()
        w.open("gear", fx6.id)
    shot(w, out / "2-gear.png")
    groups = lib.groups()
    if groups:
        w.go(f"grp:{groups[0]}")
        shot(w, out / "3-group.png")
    w.go("kits")
    if lib.packages:
        w.open("packages", next(iter(lib.packages)))  # (its panel: the name, the strip, the gear)
    shot(w, out / "4-kits.png")
    w.go("rentals")
    if lib.rentals:
        w.open("rentals", next(iter(lib.rentals)))  # (its panel: the head, the strip, a line open)
    for e in w.rentals.editors[1:2]:
        w.rentals._open_editor(e)
    shot(w, out / "5-rental.png")
    w.go("calendar")
    shot(w, out / "6-calendar.png")
    from bodega.ui.dialogs.checklist import CheckDialog

    d = CheckDialog(lib, next(iter(lib.rentals.values())), True, w)
    d.show()
    shot(d, out / "15-check-in.png")
    d.close()
    w.calendar.set_mode("timeline")
    shot(w, out / "6b-timeline.png")
    w.calendar.set_mode("month")
    w.go("gear")
    w.set_gear_filter("out")
    shot(w, out / "2b-filtered.png")
    w.set_gear_filter("all")
    for name, menu in (("2c-filter-menu", w.view_menu.m), ("2d-new-menu", w.new_menu)):
        menu.popup(w.mapToGlobal(w.rect().center()))
        shot(menu, out / f"{name}.png")
        menu.close()
    from bodega.ui.dialogs.common import Alert
    from bodega.ui.dialogs.settings import SettingsDialog

    for name, d in (
        (
            "12-alert",
            Alert(w, "Delete Sony FX6?", "Rentals that had it keep its name.", "Delete", "Cancel", True),
        ),
    ):
        d.show()
        shot(d, out / f"{name}.png")
        d.close()
    for pane in ("general", "profiles", "ai", "shortcuts", "data"):
        d = SettingsDialog(w.lib, w, pane)
        d.show()
        shot(d, out / f"13-settings-{pane}.png")
        d.close()
    w.go("gear")
    w.open_ai_assistant()
    wait()
    shot(w, out / "11-assistant.png")
    w.close_assistant()

    names = iter(["7-agreement.png", "8-inventory.png", "16-labels.png"])

    def page_shot(d):
        d.show()
        shot(d, out / next(names))
        d.close()
        return 0

    PageDialog.exec = page_shot
    w.show_pages(("rental", next(iter(lib.rentals))))
    w.show_pages(("gear", ""), "inventory")
    w.show_pages(("gear", ""), "labels")
    from bodega.ui.dialogs.gear_picker import GearPicker

    d = GearPicker(lib, w.business(), "Add to the Rental", packages=True, parent=w)
    d.show()
    shot(d, out / "9-picker.png")
    d.close()
    from bodega.ui.dialogs.profile import ProfileDialog

    d = ProfileDialog(w.business(), False, w)
    d.show()
    shot(d, out / "10-profile.png")
    d.close()
    w.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]), Path(sys.argv[2]) if len(sys.argv) > 2 else None))
