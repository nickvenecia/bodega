"""The page window: agreements, kit sheets, inventory and rate cards; PDF, PNG, print, email.

A part of MainWindow (see main_window.py); it uses the window's widgets and the library."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWidgets import QFileDialog

from bodega.core import dates, document
from bodega.core.fileutil import reveal
from bodega.core.log import get_logger
from bodega.core.looks import palette
from bodega.core.model import Business, Rental
from bodega.core.paths import documents_dir, logos_dir
from bodega.doc import export, render
from bodega.ui.dialogs.preview import PageDialog
from bodega.ui.window.common import PAGE_DOCS

log = get_logger(__name__)


class PagesMixin:
    def show_pages(self, ctx: tuple[str, str], doc: str = "") -> None:
        """Open the agreement, a kit sheet, the inventory list or the rate card in its own window."""
        self.flush()
        if ctx[0] == "gear" and not self.lib.items:
            self.toast("No gear yet.")
            return
        self.page_ctx = ctx
        d = PageDialog(self)
        self.page = d
        panel = d.panel
        docs = PAGE_DOCS[ctx[0]]
        keys = [k for k, _l in docs]
        title = ""
        if ctx[0] == "rental" and ctx[1] in self.lib.rentals:
            title = document.rental_title(self.lib.rentals[ctx[1]])
        panel.set_docs(docs, doc if doc in keys else keys[0], title)
        panel.set_rental_tools(ctx[0] == "rental")
        panel.set_dark(bool(self.lib.settings.get("dark_preview", False)))
        panel.save_pdf.connect(self.save_pdf)
        panel.print_wanted.connect(self.print_pages)
        panel.save_png.connect(self.save_png)
        panel.copy_text.connect(self.copy_text)
        panel.open_folder.connect(self.open_folder)
        panel.show_file.connect(lambda: self.last_export and reveal(self.last_export))
        panel.mark_booked.connect(self._mark_booked)
        panel.email_wanted.connect(self.email_renter)
        panel.dark_changed.connect(self._dark_changed)
        panel.doc_changed.connect(lambda _k: self.redraw())
        self.redraw()
        d.exec()
        self.page = None
        self.refresh()

    def view(self, doc: str = "") -> tuple[document.DocView, Business | None, str] | None:
        """The page for the page window (or `doc` of it), whose it is, and a file name for it."""
        kind, ref = self.page_ctx
        if not doc and self.page is not None:
            doc = self.page.panel.current_doc()
        doc = doc or PAGE_DOCS[kind][0][0]
        lib = self.lib
        if kind == "rental":
            r = lib.rentals.get(ref)
            if r is None:
                return None
            b = lib.businesses.get(r.business_id) or self.business()
            return document.build_rental(lib, r, b), b, document.rental_stem(r)
        b = self.lib.pricing()
        today = dates.iso(dates.today())
        if doc == "ratecard":
            return (
                document.build_ratecard(lib, lib.ordered_items(), list(lib.packages.values()), b),
                b,
                f"Rate Card {today}",
            )
        if doc == "labels":
            items = [i for i in lib.ordered_items() if not ref or i.group == ref]
            return document.build_labels(items, b), b, document.file_name(f"{ref or 'Gear'} Labels {today}")
        if kind == "kit":
            p = lib.packages.get(ref)
            if p is None:
                return None
            return document.build_package(lib, p, b), b, document.file_name(p.name or "Kit")
        items = [i for i in lib.ordered_items() if not ref or i.group == ref]
        title = f"{ref} Inventory" if ref else "Equipment Inventory"
        return document.build_inventory(lib, items, b, title), b, document.file_name(f"{title} {today}")

    def page_list(self, dark: bool = False, doc: str = "") -> list[render.Page]:
        """The page, laid out. `dark` only ever for the window's Dark Page: exports stay white."""
        got = self.view(doc)
        if got is None:
            return []
        v, b, _stem = got
        logo = logos_dir() / b.logo if b and b.logo else None
        return render.layout(v, palette(b.color if b else "blue", dark), logo)

    def redraw(self) -> None:
        if self.page is None:
            return
        panel = self.page.panel
        pages = self.page_list(dark=panel.dark)
        if pages:
            panel.set_pages(pages)
        else:
            panel.clear("Nothing to show.")

    def _export_folder(self) -> Path:
        saved = self.lib.settings.get("export_dir")
        if isinstance(saved, str) and Path(saved).is_dir():
            return Path(saved)
        return documents_dir()

    def _ask_path(self, title: str, suffix: str, kinds: str) -> Path | None:
        got = self.view()
        if got is None:
            return None
        folder = self._export_folder()
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError:
            folder = Path.home()
        path, _ = QFileDialog.getSaveFileName(
            self.page or self, title, str(folder / f"{got[2]}{suffix}"), kinds
        )
        if not path:
            return None
        p = Path(path)
        if p.suffix.lower() != suffix:
            p = p.with_name(p.name + suffix)
        self.lib.settings["export_dir"] = str(p.parent)
        return p

    def _exported(self, path: Path) -> None:
        self.last_export = path
        if self.page is not None:
            kind, ref = self.page_ctx
            r = self.lib.rentals.get(ref) if kind == "rental" else None
            self.page.panel.saved_hint(path.name, r is not None and r.status == "quote", r is not None)

    def save_pdf(self) -> None:
        pages = self.page_list()
        if not pages:
            return
        path = self._ask_path("Save PDF", ".pdf", "PDF (*.pdf)")
        if path is None:
            return
        try:
            v = self.view()
            export.to_pdf(pages, path, title=f"{v[0].title} {v[0].number}".strip() if v else "")
        except OSError as e:
            log.warning("PDF not saved", exc_info=True)
            self.toast(str(e) or "Couldn't save the PDF.", "problem")
            return
        self._exported(path)

    def save_png(self) -> None:
        pages = self.page_list()
        if not pages:
            return
        path = self._ask_path("Save as PNG", ".png", "PNG picture (*.png)")
        if path is None:
            return
        try:
            files = export.to_png(pages, path)
        except OSError as e:
            log.warning("PNG not saved", exc_info=True)
            self.toast(str(e) or "Couldn't save the picture.", "problem")
            return
        self._exported(files[0])

    def print_pages(self) -> None:
        pages = self.page_list()
        if not pages:
            return
        try:
            from PySide6.QtPrintSupport import QPrintDialog, QPrinter
        except ImportError:
            self.toast("Printing isn't available here. Save a PDF and print that.", "problem")
            return
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        v = self.view()
        printer.setDocName(v[2] if v else "Bodega")
        dlg = QPrintDialog(printer, self.page or self)
        if dlg.exec() != QPrintDialog.DialogCode.Accepted:
            return
        try:
            export.print_pages(printer, pages)
        except OSError as e:
            log.warning("print failed", exc_info=True)
            self.toast(str(e), "problem")

    def _page_rental(self) -> Rental | None:
        kind, ref = self.page_ctx
        return self.lib.rentals.get(ref) if kind == "rental" else None

    def copy_text(self) -> None:
        r = self._page_rental()
        if r is None:
            return
        QGuiApplication.clipboard().setText(
            document.summary_text(self.lib, r, self.lib.businesses.get(r.business_id))
        )

    def email_renter(self) -> None:
        """A new email to the renter with the summary in it; the saved PDF is shown, ready to drag in."""
        r = self._page_rental()
        if r is None:
            return
        b = self.lib.businesses.get(r.business_id)
        subject = f"{document.rental_title(r)} {r.number}" + (f": {r.project}" if r.project.strip() else "")
        body = document.summary_text(self.lib, r, b)
        body += (
            "\n\nThe quote is attached."
            if r.status == "quote"
            else "\n\nThe agreement is attached. Please sign and send it back before pickup."
        )
        if b and b.name:
            body += f"\n\n{b.name}"
        QDesktopServices.openUrl(
            QUrl(f"mailto:{quote(r.client.email.strip())}?subject={quote(subject)}&body={quote(body)}")
        )
        if self.last_export is not None and self.last_export.exists():
            reveal(self.last_export)

    def open_folder(self) -> None:
        folder = self._export_folder()
        folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def _dark_changed(self, on: bool) -> None:
        self.lib.settings["dark_preview"] = on
        self.redraw()

    def _mark_booked(self) -> None:
        r = self._page_rental()
        if r is not None and r.status == "quote":
            if not self.may_hold(r, "booked"):
                return
            self.lib.set_status(r, "booked")
            self.flush()  # (marks it for undo)
            if self.rentals.r is r:
                self.rentals.load(r)
            if self.page is not None:
                self.page.panel.saved_hint(self.last_export.name if self.last_export else None, False, True)
                self.page.panel.set_title(document.rental_title(r))
            self.redraw()
