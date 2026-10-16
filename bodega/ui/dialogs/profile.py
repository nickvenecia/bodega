"""Your profile: who rents the gear out, how it's priced, and the agreement's standard terms.

Filled in once. Pricing lives here because it's the same for all your gear: a day's rent as a percent of
replacement value, the sales tax that goes on what you paid, how a week is billed, the weekend deal and the
deposit. Change it and every automatic rate follows. (In the code a profile is a `Business`.)
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QIntValidator, QPainter, QPixmap
from PySide6.QtWidgets import QDialog, QFileDialog, QLabel, QLineEdit, QPushButton, QWidget

from bodega.core import dates
from bodega.core.log import get_logger
from bodega.core.looks import COLORS
from bodega.core.model import WEEK_DAYS, Business
from bodega.core.paths import logos_dir
from bodega.core.store import DEFAULT_NOTE, DEFAULT_TERMS, clean_prefix, initials
from bodega.ui.components.photos import write_picture
from bodega.ui.components.widgets import (
    Disclosure,
    Embeddable,
    FitScroll,
    Guarded,
    Section,
    TextBox,
    ToggleRow,
    combo,
    hbox,
    hint,
    percent_field,
    vbox,
)
from bodega.ui.style.tokens import (
    DIALOG_W_WIDE,
    LOGO_THUMB,
    LOGO_THUMB_MAX_W,
    PROFILE_DIALOG_H,
    SCROLL_GUTTER,
    SPACE_2,
    SPACE_3,
    SPACE_4,
    SPACE_5,
    TEXT_BOX_TERMS,
)

log = get_logger(__name__)

LOGO_MAX_PX = 1600  # bigger pictures are scaled down when added (keeps PDFs small)
LOGO_MAX_BYTES = 40_000_000  # a picture bigger than this isn't a logo


def import_logo(src: Path) -> str:
    """Copy a logo into Bodega's own folder (so moving or deleting the original never breaks a rental agreement).
    Returns the stored file name. Raises ValueError if it isn't a picture Bodega can read."""
    from bodega.core import svg
    from bodega.doc.render import logo_size

    if src.stat().st_size > LOGO_MAX_BYTES:
        raise ValueError(f"{src.name} is too big to be a logo. Use a smaller picture.")
    data = src.read_bytes()
    folder = logos_dir()
    folder.mkdir(parents=True, exist_ok=True)
    if src.suffix.lower() == ".svg":  # only its drawing is kept: nothing it points at outside itself
        data = svg.clean(data)
        name = f"{hashlib.sha256(data).hexdigest()[:16]}.svg"
        (folder / name).write_bytes(data)
        if logo_size(folder / name) is None:
            raise ValueError(f"Bodega can't read {src.name}. Use a PNG, JPG or SVG file.")
        return name
    digest = hashlib.sha256(data).hexdigest()[:16]
    img = QImage(str(src))
    if img.isNull():
        raise ValueError(f"Bodega can't read {src.name}. Use a PNG, JPG or SVG file.")
    if max(img.width(), img.height()) > LOGO_MAX_PX:
        img = img.scaled(
            LOGO_MAX_PX,
            LOGO_MAX_PX,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    name = f"{digest}.png"
    try:
        write_picture(img, folder / name, "PNG", -1, "save the logo")
    except OSError as e:
        raise ValueError(str(e)) from e  # already in plain words
    return name


def logo_thumbnail(path: Path, height: int) -> QPixmap:
    """A sharp little picture of a logo file, `height` px tall (empty if it can't be read)."""
    dpr = 2
    if path.suffix.lower() == ".svg":
        from bodega.doc.render import svg_logo

        r = svg_logo(path)
        if r is None:
            return QPixmap()
        size = r.defaultSize()
        h = height * dpr
        w = max(1, round(h * size.width() / max(1, size.height())))
        pm = QPixmap(w, h)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        r.render(p)
        p.end()
    else:
        pm = QPixmap(str(path))
        if pm.isNull():
            return pm
        pm = pm.scaledToHeight(height * dpr, Qt.TransformationMode.SmoothTransformation)
    pm.setDevicePixelRatio(dpr)
    return pm


WEEK_LABELS = {
    2: ("2 Days", "A 7-day week costs 2 days"),
    3: ("3 Days (Most Rental Houses)", "A 7-day week costs 3 days"),
    4: ("4 Days", "A 7-day week costs 4 days"),
    5: ("5 Days", "A 7-day week costs 5 days"),
    7: ("Every Day", "No week rate: every day is billed"),
}


class ProfileDialog(Guarded, Embeddable, QDialog):
    """Add or edit a profile. After Save, `.business` holds the result; `.deleted` if Delete was chosen;
    `.next_number` the number this year's rentals carry on from, when it was changed (else 0)."""

    def __init__(
        self,
        business: Business | None,
        can_delete: bool,
        parent: QWidget | None = None,
        new: bool = False,
        next_for: Callable[[str], int] | None = None,
    ):
        """`new` with a business: a new profile that starts from those values. `next_for(prefix)` is the
        next number free in that series this year (without it, there's no Next Number field)."""
        super().__init__(parent)
        self.next_for = next_for
        self.next_number = 0
        self.editing = business is not None and not new
        self.business = replace(business) if business else Business()
        self.deleted = False
        title_text = "Edit Profile" if self.editing else "Add Your Profile"
        self.setWindowTitle(title_text)
        self.setMinimumWidth(DIALOG_W_WIDE)
        self.resize(DIALOG_W_WIDE, PROFILE_DIALOG_H)
        outer = vbox(self, (0, SPACE_5, 0, SPACE_5), SPACE_3)
        head = self._head = vbox(spacing=SPACE_2)
        head.setContentsMargins(SPACE_5, 0, SPACE_5, 0)
        self.title_label = QLabel(title_text)
        self.title_label.setObjectName("DialogTitle")
        head.addWidget(self.title_label)
        outer.addLayout(head)

        body = QWidget()
        lay = self._body_lay = vbox(body, (SPACE_5, 0, SPACE_5 - SCROLL_GUTTER, 0), SPACE_3)
        b = self.business
        self.name = self._line(lay, "Name", b.name, "Your rental house or company")
        self.tagline = self._line(lay, "Tagline", b.tagline, "Camera · Lighting · Grip")
        lay.addWidget(self._build_logo())

        self.contact = Disclosure("Contact", is_open=not self.editing)
        c = self.contact.lay
        self.email = self._line(c, "Email", b.email, "rentals@example.com")
        self.phone = self._line(c, "Phone", b.phone, "")
        self.website = self._line(c, "Website", b.website, "")
        self.address = self._box(c, "Address", b.address, "Street\nCity, State ZIP")
        lay.addWidget(self.contact)

        self.pricing = Disclosure("Pricing", is_open=True)
        p = self.pricing.lay
        row = hbox(spacing=SPACE_2)
        sec = Section("Day Rate, % of Value")
        self.rate_pct = percent_field(b.rate_pct, "4")
        self.rate_pct.setToolTip("A day's rent for any piece, as a percent of its replacement value")
        sec.add(self.rate_pct)
        row.addWidget(sec, 1)
        sec = Section("Sales Tax on Gear %")
        self.value_tax = percent_field(b.value_tax, "None")
        self.value_tax.setToolTip(
            "Added to what you paid, so replacement value is what it really costs to replace"
        )
        sec.add(self.value_tax)
        row.addWidget(sec, 1)
        p.addLayout(row)
        sec = Section("A Week Bills As")
        self.week_days = combo([(str(d), *WEEK_LABELS[d]) for d in WEEK_DAYS], str(b.week_days))
        sec.add(self.week_days)
        p.addWidget(sec)
        self.weekend = ToggleRow("Weekend Counts as 1 Day", b.weekend_deal)
        self.weekend.setToolTip("Pick up Friday, return Monday: billed as one day")
        p.addWidget(self.weekend)
        row = hbox(spacing=SPACE_2)
        sec = Section("Rental Sales Tax %")
        self.rental_tax = percent_field(b.rental_tax, "None")
        self.rental_tax.setToolTip("Sales tax on the rent itself")
        sec.add(self.rental_tax)
        row.addWidget(sec, 1)
        sec = Section("Deposit, % of Value")
        self.deposit_pct = QLineEdit(b.deposit_pct)
        self.deposit_pct.setPlaceholderText("10")
        self.deposit_pct.setToolTip("What Suggest puts in a rental's security deposit")
        sec.add(self.deposit_pct)
        row.addWidget(sec, 1)
        p.addLayout(row)
        lay.addWidget(self.pricing)

        self.numbers = Disclosure("Numbers && Paper")
        row = hbox(spacing=SPACE_2)
        sec = Section("Rental Numbers Start With")
        self.prefix = QLineEdit(b.prefix)
        self.prefix.setToolTip("Like JLF-2026-001, counting up each year")
        sec.add(self.prefix)
        row.addWidget(sec, 1)
        sec = Section("Next Number")
        self.next_field = QLineEdit()
        self.next_field.setValidator(QIntValidator(1, 999999, self.next_field))
        self.next_field.setToolTip("This year's next rental number, never one already given")
        sec.add(self.next_field)
        sec.setVisible(next_for is not None)
        row.addWidget(sec, 1)
        self.numbers.add(row)
        self.next_note = QLabel()
        self.next_note.setObjectName("Warn")
        self.next_note.setWordWrap(True)
        self.next_note.hide()
        self.numbers.add(self.next_note)
        row = hbox(spacing=SPACE_2)
        sec = Section("Currency")
        self.currency = QLineEdit(b.currency or "$")
        self.currency.setMaxLength(4)
        sec.add(self.currency)
        row.addWidget(sec, 1)
        sec = Section("Paper Color")
        self.color = combo([(k, v[0], "") for k, v in COLORS.items()], b.color)
        self.color.setToolTip("The accent on agreements, the inventory and the rate card")
        sec.add(self.color)
        row.addWidget(sec, 1)
        self.numbers.add(row)
        lay.addWidget(self.numbers)

        self.agreement = Disclosure("Agreement Terms")
        self.terms = self._box(self.agreement.lay, "Terms", b.terms or DEFAULT_TERMS, "", TEXT_BOX_TERMS)
        self.terms.setToolTip("One clause per paragraph: {owner} becomes your name")
        self.note = self._line(self.agreement.lay, "Closing Note", b.note or DEFAULT_NOTE, "")
        lay.addWidget(self.agreement)
        lay.addStretch(1)

        scroll = FitScroll()
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)
        buttons = self._buttons = hbox(spacing=SPACE_2)
        buttons.setContentsMargins(SPACE_5, SPACE_4, SPACE_5, 0)
        if self.editing and can_delete:
            delete = QPushButton("Delete Profile…")
            delete.setObjectName("Danger")
            delete.clicked.connect(self._delete)
            buttons.addWidget(delete)
        buttons.addStretch(1)
        self.cancel_btn = cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        self.save = QPushButton("Save")
        self.save.setObjectName("Primary")
        self.save.setDefault(True)
        self.save.clicked.connect(self._save)
        buttons.addWidget(cancel)
        buttons.addWidget(self.save)
        outer.addLayout(buttons)

        self.name.textChanged.connect(self._name_changed)
        for f in (self.rate_pct, self.value_tax, self.prefix, self.currency):
            f.textChanged.connect(lambda _t: self._summaries())
        self._next_typed = False
        self.next_field.textEdited.connect(self._next_edited)
        self.week_days.currentIndexChanged.connect(lambda _i: self._summaries())
        for group in (self.contact, self.pricing, self.numbers, self.agreement):
            group.toggled.connect(lambda _on: self._summaries())
        for f in (
            self.tagline,
            self.email,
            self.phone,
            self.website,
            self.rental_tax,
            self.deposit_pct,
            self.note,
        ):
            f.textChanged.connect(lambda _t: self._summaries())
        for box in (self.address, self.terms):
            box.edited.connect(self._summaries)
        self.weekend.toggled.connect(lambda _on: self._summaries())
        self.color.currentIndexChanged.connect(lambda _i: self._summaries())
        self._name_changed(self.name.text())
        self._show_logo()
        self.settled()
        self._summaries()

    def form_values(self) -> object:
        return self._draft(), self.next_field.text().strip() if self._next_typed else ""

    def side_margin(self, px: int) -> None:
        """The room on the left and right (none inside Settings, which has its own)."""
        self._head.setContentsMargins(px, 0, px, 0)
        self._body_lay.setContentsMargins(px, 0, SPACE_3, 0)
        self._buttons.setContentsMargins(px, SPACE_4, SPACE_3 + SCROLL_GUTTER, 0)  # lines up with the fields

    def _line(self, lay, label: str, value: str, placeholder: str) -> QLineEdit:
        sec = Section(label)
        f = QLineEdit(value)
        f.setPlaceholderText(placeholder)
        sec.add(f)
        lay.addWidget(sec)
        return f

    def _box(self, lay, label: str, value: str, placeholder: str, height: int | None = None) -> TextBox:
        sec = Section(label)
        f = TextBox(placeholder, height) if height else TextBox(placeholder)
        f.set_text(value)
        sec.add(f)
        lay.addWidget(sec)
        return f

    def _draft(self) -> Business:
        b = replace(self.business)
        b.name = self.name.text().strip()
        b.tagline = self.tagline.text().strip()
        b.email = self.email.text().strip()
        b.phone = self.phone.text().strip()
        b.website = self.website.text().strip()
        b.address = self.address.text().strip()
        b.rate_pct = self.rate_pct.text().strip()
        b.value_tax = self.value_tax.text().strip()
        b.week_days = int(self.week_days.currentData())
        b.weekend_deal = self.weekend.isChecked()
        b.rental_tax = self.rental_tax.text().strip()
        b.deposit_pct = self.deposit_pct.text().strip()
        b.prefix = clean_prefix(self.prefix.text()) or initials(b.name)
        b.currency = self.currency.text().strip() or "$"
        b.color = self.color.currentData()
        b.terms = self.terms.text().strip()
        b.note = self.note.text().strip()
        return b

    def _name_changed(self, text: str) -> None:
        self.prefix.setPlaceholderText(initials(text))
        self._summaries()

    def _free(self) -> int:
        """The lowest Next Number allowed for the series as typed (1 without a store to ask)."""
        b = self._draft()
        return self.next_for(b.prefix) if self.next_for is not None else 1

    def _next_edited(self, _t: str) -> None:
        self._next_typed = True
        self._summaries()

    def _check_next(self) -> bool:
        """The typed Next Number, said in the field if it's one already given. True if it can be saved."""
        free = self._free()
        if not self._next_typed:
            self.next_field.setText(f"{free:03d}")
        text = self.next_field.text().strip()
        n = int(text) if text.isdigit() else 0
        b = self._draft()
        year = dates.today().year
        if self.next_for is not None and n < free:
            given = f"{b.prefix}-{year}-{free - 1:03d}" if free > 1 else ""
            self.next_note.setText(
                f"Numbers up to {given} are already given, so the next can be {free:03d} or higher."
                if given
                else "The next number is 001 or higher."
            )
            self.next_note.show()
            return False
        self.next_note.hide()
        return True

    def _summaries(self) -> None:
        from bodega.core import money, pricing
        from bodega.core.model import Item

        b = self._draft()
        self.contact.set_summary(b.email or b.phone or "")
        example = Item(value="1000")
        rate = pricing.auto_day_rate(example, b)
        self.pricing.setToolTip(
            f"Paid {b.currency}1,000: rents for {money.fmt_short(rate, b.currency)} a day, "
            f"{money.fmt_short(rate * b.week_days, b.currency)} a week"
        )
        self.pricing.set_summary(f"{money.fmt_rate(b.rate_pct)} a day · {b.week_days}-day week")
        ok = self._check_next()
        self.save.setEnabled(bool(b.name) and ok and (not self.editing or self.unsaved()))
        text = self.next_field.text().strip()
        n = int(text) if ok and text.isdigit() else self._free()
        self.numbers.set_summary(
            f"Next {b.prefix}-{dates.today().year}-{n:03d} · {COLORS.get(b.color, COLORS['blue'])[0]}"
        )

    # ------------------------------------------------------------------ logo
    def _build_logo(self) -> Section:
        sec = Section("Logo")
        row = hbox(spacing=SPACE_2)
        self.logo_thumb = QLabel()
        self.logo_thumb.setObjectName("LogoThumb")
        self.logo_thumb.setFixedHeight(LOGO_THUMB)
        self.logo_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_btn = QPushButton("Choose Logo…")
        self.logo_btn.setToolTip("PNG, JPG or SVG")
        self.logo_btn.clicked.connect(self._choose_logo)
        self.logo_remove = QPushButton("Remove")
        self.logo_remove.setObjectName("Ghost")
        self.logo_remove.setToolTip("Leave the logo off")
        self.logo_remove.clicked.connect(lambda: self._set_logo(""))
        row.addWidget(self.logo_thumb)
        row.addWidget(self.logo_btn)
        row.addWidget(self.logo_remove)
        row.addStretch(1)
        sec.add(row)
        self.logo_error = hint("")
        self.logo_error.hide()
        sec.add(self.logo_error)
        return sec

    def _show_logo(self) -> None:
        name = self.business.logo
        path = logos_dir() / name if name else None
        pm = logo_thumbnail(path, LOGO_THUMB - SPACE_2) if path and path.is_file() else QPixmap()
        has_logo = not pm.isNull()
        if has_logo:
            self.logo_thumb.setPixmap(pm)
            width = round(pm.width() / pm.devicePixelRatio()) + SPACE_2
            self.logo_thumb.setFixedWidth(min(width, LOGO_THUMB_MAX_W))
        self.logo_thumb.setVisible(has_logo)
        self.logo_remove.setVisible(has_logo)
        self.logo_btn.setText("Change…" if has_logo else "Choose Logo…")

    def _set_logo(self, name: str) -> None:
        self.business.logo = name
        self._show_logo()
        self._summaries()

    def _choose_logo(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose a Logo", str(Path.home()), "Logos (*.png *.jpg *.jpeg *.svg)"
        )
        if not path:
            return
        try:
            name = import_logo(Path(path))
        except (OSError, ValueError) as e:
            log.warning("logo not added: %s", e)
            self.logo_error.setText(str(e) if isinstance(e, ValueError) else "Couldn't read that file.")
            self.logo_error.show()
            return
        log.info("logo added")
        self.logo_error.hide()
        self._set_logo(name)

    # ------------------------------------------------------------------ buttons
    def _save(self) -> None:
        if not self._check_next():
            return
        self.business = self._draft()
        text = self.next_field.text().strip()
        self.next_number = (
            int(text) if self._next_typed and text.isdigit() and int(text) > self._free() else 0
        )
        self.accept()

    def _delete(self) -> None:
        from bodega.ui.dialogs.common import confirm

        if confirm(
            self,
            f"Delete {self.business.name or 'This Profile'}?",
            "It goes from your profiles. Edit › Undo brings it back.",
            "Delete Profile",
        ):
            self.deleted = True
            self.accept()
