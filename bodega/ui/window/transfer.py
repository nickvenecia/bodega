"""Bringing gear in (spreadsheets, Google Sheets) and out (CSV, backups).

A part of MainWindow (see main_window.py); it uses the window's widgets and the library."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog

from bodega.core import dates, importer
from bodega.core.history import History
from bodega.core.log import get_logger
from bodega.core.model import Item
from bodega.core.paths import data_dir, documents_dir
from bodega.ui.dialogs.common import notice
from bodega.ui.style import tokens

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

            d = ImportDialog(path, rows, set(have), self, has_profile=bool(self.lib.businesses))
            if d.exec() != ImportDialog.DialogCode.Accepted:
                return 0
            chosen, everything, pricing_found = d.items, d.got.items, d.pricing
            fill_links = d.fill_links
        else:
            got = importer.parse_rows(rows)
            importer.attach_guesses(got.items)
            everything = got.items
            chosen = [i for i in everything if (i.name.casefold(), i.department.casefold()) not in have]
            pricing_found = (got.rate_pct, got.value_tax) if (got.rate_pct or got.value_tax) else None
            fill_links = True
        linked = self._fill_links(everything, have) if fill_links else 0
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
        self.lib.snapshot("before-import")
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

    def restore(self) -> None:
        """File › Restore from Backup…: put a Back Up zip or a safety copy back in place of everything, after a
        look at what's in it. How things are now is kept as a safety copy first."""
        from bodega.core import backups
        from bodega.ui.dialogs.common import confirm

        self.flush()
        start = backups.folder(self.lib.root) if backups.copies(self.lib.root) else documents_dir()
        path, _ = QFileDialog.getOpenFileName(
            self, "Restore from Backup", str(start), "Bodega Backups (*.zip)"
        )
        if not path:
            return
        try:
            backup = backups.read_backup(Path(path))
        except ValueError as e:
            notice(self, "Couldn't Restore That", str(e))
            return
        if not confirm(
            self,
            "Replace Everything with This Backup?",
            f"Your gear, kits, rentals, renters and profiles become what {Path(path).name} holds: "
            f"{backup.summary()}. What you have now is kept as a safety copy first, so you can go back.",
            "Restore",
        ):
            return
        try:
            kept = self.lib.restore(backup)
            problem = ""
        except OSError as e:
            log.warning("restore failed", exc_info=True)
            kept, problem = None, f"Bodega couldn't write to its folder ({e.strerror or e})."
            self.lib.load()  # whatever made it back, as it now is on disk
        self.deselect()
        self.history = History(self.lib)  # undo starts again from what was put back
        self.refresh()
        self.sidebar.show_who()
        if problem:
            notice(self, "Couldn't Restore All of It", problem)
            return
        log.info("restored %s", Path(path).name)
        self.toast("Restored." + (f" What you had before is kept as {kept.name}." if kept else ""), "done")

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

    # ------------------------------------------------------------------ Saldo
    def send_to_saldo(self, rental_id: str) -> None:
        """Send to Saldo…: the rental as a draft invoice in Saldo (the renter, every line, the totals). Sent
        again, it updates that draft while it's still one."""
        from bodega.services import saldo
        from bodega.ui.dialogs.common import ask_choice, confirm

        r = self.lib.rentals.get(rental_id)
        if r is None:
            return
        self.flush()
        if not r.lines:
            self.toast("Add gear to the rental first.", "problem")
            return
        if saldo.waiting_for_cobro():
            notice(
                self,
                "Open Saldo Once First",
                "Cobro is now called Saldo. The first time Saldo opens, it brings over everything Cobro had. "
                "Open Saldo once, quit it, then send this again.",
            )
            return
        if not saldo.installed():
            notice(
                self,
                "Saldo Isn't Set Up Here",
                "Send to Saldo makes the invoice in Saldo, the invoicing app. Open Saldo once on this computer "
                "and add your profile, then try again.",
            )
            return
        if saldo_is_open():
            notice(
                self,
                "Quit Saldo First",
                "Saldo reads new invoices when it opens, and numbers them from the ones it has open. Quit Saldo, "
                "send this again, then open Saldo.",
            )
            return
        b = self.lib.businesses.get(r.business_id) or self.business()
        found = saldo.profiles()
        if not found:
            notice(self, "Saldo Has No Profile Yet", "Open Saldo and add your profile there, then try again.")
            return
        profile = saldo.profile_for(found, b)
        if profile is None:
            names = [(str(d["id"]), str(d.get("name") or "Untitled Profile")) for d in found]
            pick = ask_choice(
                self,
                "Which Saldo Profile Sends It?",
                f"Invoices from {b.name if b else 'this profile'} go out as this profile in Saldo. "
                "Bodega remembers it.",
                names,
                "Use This Profile",
            )
            if pick is None:
                return
            profile = next(d for d in found if str(d["id"]) == pick)
        if b is not None and b.saldo_profile != str(profile["id"]):
            b.saldo_profile = str(profile["id"])
            self.lib.save_businesses()
        who = r.client.company or r.client.name or "the renter"
        old = saldo.draft_of(r)
        if old is not None and old.get("status") == "draft":
            asked = confirm(
                self,
                f"Update Draft {old.get('number', '')} in Saldo?",
                "It gets this rental's renter, lines and totals as they are now. What you changed on it in Saldo "
                "otherwise stays.",
                "Update",
                danger=False,
            )
        elif old is not None:
            asked = confirm(
                self,
                f"Make a New Draft for {r.number}?",
                f"Saldo already {saldo.said(old)} for this rental. A new draft invoice for {who} goes beside it.",
                "Make Draft",
                danger=False,
            )
        else:
            asked = confirm(
                self,
                f"Send {r.number} to Saldo?",
                f"Saldo gets a draft invoice for {who}.",
                "Send",
                danger=False,
            )
        if not asked:
            return
        try:
            number, updated = saldo.send(self.lib, r, b, profile)
        except OSError as e:
            notice(self, "Couldn't Send It to Saldo", str(e))
            return
        self._dirty_rentals.add(r.id)
        self.flush()
        self.toast(
            f"Updated draft invoice {number} in Saldo."
            if updated
            else f"Saldo has draft invoice {number}. Open Saldo to send it.",
            "done",
        )


def saldo_is_open() -> bool:
    """Saldo is open on this computer (it answers on its own local socket; nothing is said to it, so its
    window stays where it is)."""
    import getpass

    from PySide6.QtNetwork import QLocalSocket

    try:
        user = getpass.getuser()
    except Exception:
        user = "user"
    sock = QLocalSocket()
    sock.connectToServer(f"saldo-{user}")
    if not sock.waitForConnected(tokens.SALDO_CHECK_MS):
        return False
    sock.disconnectFromServer()
    return True
