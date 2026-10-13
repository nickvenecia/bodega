"""Bringing gear in (spreadsheets, Google Sheets) and out (CSV, backups).

A part of MainWindow (see main_window.py); it uses the window's widgets and the library."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog

from bodega.core import dates, importer
from bodega.core.log import get_logger
from bodega.core.model import Item
from bodega.core.paths import data_dir, documents_dir
from bodega.ui.dialogs.common import notice

log = get_logger(__name__)


class TransferMixin:
    def import_sheet(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Import a Gear Spreadsheet", str(Path.home()), "Spreadsheets (*.xlsx *.xlsm *.csv)"
        )
        if path:
            self.import_file(Path(path))

    def import_google(self) -> None:
        """Import straight from a Google Sheet (shared as Anyone with the link). Links on it come along."""
        import tempfile

        from PySide6.QtWidgets import QApplication

        from bodega.ui.dialogs.common import ask_name

        last = self.lib.settings.get("google_sheet", "")
        link = ask_name(
            self,
            "Import from Google Sheets",
            "Import",
            text=last if isinstance(last, str) else "",
            placeholder="https://docs.google.com/spreadsheets/d/…",
        )
        if not link:
            return
        if importer.google_export_url(link) is None:
            self.toast("That isn't a Google Sheets link.", "problem")
            return
        with tempfile.TemporaryDirectory(prefix="bodega-sheet-") as folder:  # gone once it's read
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                path = importer.download_google_sheet(link, Path(folder))
            except OSError as e:
                QApplication.restoreOverrideCursor()
                notice(self, "Couldn't Open the Sheet", str(e))
                return
            QApplication.restoreOverrideCursor()
            self.lib.settings["google_sheet"] = link
            self.import_file(path)

    def import_file(self, path: Path, ask: bool = True) -> int:
        """Read a spreadsheet. With `ask`, the Import window shows what's in it and lets you choose what
        comes in; without (tests, scripts), everything new comes in as Bodega reads it."""
        try:
            rows = importer.load_rows(path)
        except OSError as e:
            log.warning("import failed", exc_info=True)
            self.toast(str(e) or "Couldn't read that file.", "problem")
            return 0
        have = {(i.name.casefold(), i.department.casefold()): i.id for i in self.lib.items.values()}
        if ask:
            from bodega.ui.dialogs.import_sheet import ImportDialog

            d = ImportDialog(path, rows, set(have), self)
            if d.exec() != ImportDialog.DialogCode.Accepted:
                return 0
            chosen, everything, pricing_found = d.items, d.got.items, d.pricing
        else:
            got = importer.parse_rows(rows)
            importer.attach_guesses(got.items)
            everything = got.items
            chosen = [i for i in everything if (i.name.casefold(), i.department.casefold()) not in have]
            pricing_found = (got.rate_pct, got.value_tax) if (got.rate_pct or got.value_tax) else None
        linked = self._fill_links(everything, have)
        if not chosen:
            if linked:
                self.lib.save_items()
                self.refresh()
                self.toast(f"Added links to {linked} items.", "done")
            else:
                self.toast(f"Nothing new in {path.name}." if everything else f"No gear found in {path.name}.")
            return 0
        ids = {i.id for i in chosen}
        same = {
            i.id: have[(i.name.casefold(), i.department.casefold())]
            for i in everything
            if i.id not in ids and (i.name.casefold(), i.department.casefold()) in have
        }
        for i in chosen:
            if i.parent and i.parent not in ids:
                i.parent = same.get(i.parent, "")
        self.flush()
        for i in chosen:
            self.lib.add_item(i)
        if pricing_found:
            rate, tax = pricing_found
            b = self.business()
            if b is not None:
                b.rate_pct = rate or b.rate_pct
                b.value_tax = tax or b.value_tax
                self.lib.save_businesses()
            else:
                self.lib.settings["sheet_pricing"] = {"rate_pct": rate, "value_tax": tax}
        self.lib.untangle()  # a sheet can say A goes with B and B goes with A
        self.lib.save_items()
        log.info("imported %d items from %s", len(chosen), path.name)
        self.go("gear")
        self.toast(f"Added {len(chosen)} items." + (f" Links for {linked} more." if linked else ""), "done")
        return len(chosen)

    def _fill_links(self, sheet: list[Item], have: dict) -> int:
        """Gear you already have that has no link gets the sheet's. Returns how many."""
        n = 0
        for i in sheet:
            mine = self.lib.items.get(have.get((i.name.casefold(), i.department.casefold()), ""))
            if mine is not None and not mine.link.strip() and i.link.strip():
                mine.link = i.link
                n += 1
        return n

    def export_csv(self) -> None:
        if not self.lib.items:
            self.toast("No gear to export yet.")
            return
        default = self._export_folder() / f"Bodega Gear {dates.iso(dates.today())}.csv"
        path, _ = QFileDialog.getSaveFileName(self, "Export Gear as CSV", str(default), "CSV (*.csv)")
        if not path:
            return
        p = Path(path)
        if p.suffix.lower() != ".csv":
            p = p.with_name(p.name + ".csv")
        try:
            importer.write_csv(self.lib.ordered_items(), self.lib.items, p)
        except OSError:
            log.warning("CSV not saved", exc_info=True)
            self.toast("Couldn't save the CSV.", "problem")
            return
        self.last_export = p
        self.toast(f"Saved {p.name}.", "done")

    def open_data_folder(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(data_dir())))

    def back_up(self) -> None:
        """Save everything (gear, kits, rentals, renters, profiles, logos, photos) as one zip file."""
        from bodega.core.fileutil import zip_folder

        self.flush()
        name = f"Bodega Backup {dates.iso(dates.today())}.zip"
        path, _ = QFileDialog.getSaveFileName(
            self, "Back Up", str(documents_dir() / name), "Zip Files (*.zip)"
        )
        if not path:
            return
        try:
            zip_folder(data_dir(), Path(path), skip=("ui",))
        except OSError as e:
            notice(self, "Couldn't back up", str(e))
            return
        self.toast("Backed up", "done")

    # ------------------------------------------------------------------ photos from links
    def get_photos_from_links(self) -> None:
        """File › Get Photos from Links: each piece with a link and no photo gets its product page's main
        picture, in the background. One undo (⌘Z) takes them all back."""
        from bodega.core import web
        from bodega.ui.components import photos
        from bodega.ui.components.worker import Worker
        from bodega.ui.dialogs.common import confirm

        if getattr(self, "_photo_worker", None) is not None and self._photo_worker.isRunning():
            self.toast("Already getting photos.")
            return
        self.flush()
        todo = [(it.id, it.link) for it in self.lib.ordered_items() if not it.photo and web.web_link(it.link)]
        if not todo:
            self.toast("Every piece with a link already has a photo.")
            return
        n = len(todo)
        if not confirm(
            self,
            f"Get photos for {n} piece{'s' if n != 1 else ''}?",
            "Bodega takes the main picture from each piece's link. You can change or remove any of them.",
            "Get Photos",
            danger=False,
        ):
            return

        def job(progress, cancel):
            found: dict[str, str] = {}
            for i, (item_id, link) in enumerate(todo):
                if cancel.is_set():
                    break
                progress(i, n)
                try:
                    found[item_id] = photos.from_link(link)
                except OSError:
                    continue  # a store that won't share its page: that piece just stays without
            return found

        w = Worker(job, self)
        w.progress.connect(lambda i, total: self.toast(f"Getting photos… {i + 1} of {total}"))
        w.done.connect(self._photos_came)
        w.failed.connect(lambda e: self.toast(e, "problem"))
        self._photo_worker = w
        w.start()

    def _photos_came(self, found: dict) -> None:
        self.flush()
        for item_id, name in found.items():
            it = self.lib.items.get(item_id)
            if it is not None and not it.photo:
                it.photo = name
        if found:
            self.lib.save_items()
            if self.items.it is not None:
                self.items.load(self.items.it)
            self.refresh()
        n = len(found)
        if n:
            self.toast(f"Added {n} photo{'s' if n != 1 else ''}.", "done")
        else:
            self.toast("None of those pages shared a photo.", "problem")

    # ------------------------------------------------------------------ calendars
    def add_to_calendar(self, rental_id: str = "") -> None:
        """Add Rentals to Calendar (or one rental's, from its ⋯): a calendar file, opened in your calendar app
        (Apple Calendar on a Mac). Adding it again updates the same events."""
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        from bodega.core import ics
        from bodega.core.store import write_text

        self.flush()
        rentals = None
        name = "Bodega Rentals.ics"
        if rental_id:
            r = self.lib.rentals.get(rental_id)
            if r is None:
                return
            if not (r.pickup or r.return_date):
                self.toast("Give the rental its dates first.", "problem")
                return
            rentals, name = [r], f"{r.number or 'Rental'}.ics"
        text = ics.calendar(self.lib, rentals)
        if text.count("BEGIN:VEVENT") == 0:
            self.toast("No booked or out rentals with dates yet.")
            return
        path = data_dir() / "calendar" / name
        try:
            write_text(path, text)
        except OSError:
            self.toast(
                "Couldn't write the calendar file. Check that there's free space on this computer.", "problem"
            )
            return
        if QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
            self.toast("Opened in your calendar app. For Google Calendar: File › Save Calendar File…", "done")
        else:
            self.save_calendar()

    def save_calendar(self) -> None:
        """Save Calendar File…: the same file, wherever you like (Google Calendar: Settings › Import)."""
        from bodega.core import ics
        from bodega.core.store import write_text

        self.flush()
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Calendar File", str(Path.home() / "Bodega Rentals.ics"), "Calendar (*.ics)"
        )
        if not path:
            return
        try:
            write_text(Path(path), ics.calendar(self.lib))
        except OSError as e:
            notice(self, "Couldn't save", str(e))
            return
        self.toast("Saved. In Google Calendar: Settings › Import & Export › Import.", "done")

    # ------------------------------------------------------------------ Cobro
    def send_to_cobro(self, rental_id: str) -> None:
        """Send to Cobro…: the rental as a draft invoice in Cobro (your profile, the renter, every line)."""
        from bodega.services import cobro
        from bodega.ui.dialogs.common import confirm

        r = self.lib.rentals.get(rental_id)
        if r is None:
            return
        self.flush()
        if not r.lines:
            self.toast("Add gear to the rental first.", "problem")
            return
        if not cobro.installed():
            notice(
                self,
                "Cobro isn't set up here",
                "Send to Cobro makes the invoice in Cobro, the invoice app. Open Cobro once "
                "on this computer and add your profile, then try again.",
            )
            return
        who = r.client.company or r.client.name or "the renter"
        if not confirm(
            self, f"Send {r.number} to Cobro?", f"Cobro gets a draft invoice for {who}.", "Send", danger=False
        ):
            return
        b = self.lib.businesses.get(r.business_id) or self.business()
        try:
            number = cobro.send(self.lib, r, b)
        except OSError as e:
            notice(self, "Couldn't send it to Cobro", str(e))
            return
        self.toast(f"Cobro has draft invoice {number}. Open Cobro to send it.", "done")
