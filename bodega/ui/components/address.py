"""The one address control (the standard's 4.6), on every form with an address (a renter, a profile): the street
lines, then city, region and postal code, then the country. Where the country keeps a list of regions (core/
addresses.py REGIONS), the region is picked from that list, and read from the postal code while it's left blank;
elsewhere it's typed."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QLineEdit, QWidget

from bodega.core import addresses
from bodega.core.countries import COUNTRIES
from bodega.ui.components.widgets import Section, TextBox, combo, hbox, set_combo, sized, vbox
from bodega.ui.style import tokens

NO_REGION = "—"  # the region list's first choice: none picked yet


class AddressFields(QWidget):
    """`edited` fires on typing or picking (never when it's filled in); values() is what it holds, for saving as
    (address, city, region, postal, country) on a renter or a profile."""

    edited = Signal()

    def __init__(self, record, parent: QWidget | None = None):
        super().__init__(parent)
        lay = vbox(self, 0, tokens.SPACE_2)
        self._country = addresses.country_of(record.country)
        self._blank_country = not record.country.strip()  # kept blank (the home country) unless one is picked

        street = Section("Street")
        self.street = TextBox("Street and number, apartment or suite")
        self.street.set_text(record.address)
        street.add(self.street)
        lay.addWidget(street)

        row = hbox(spacing=tokens.SPACE_2)
        city = Section("City")
        self.city = QLineEdit(record.city)
        city.add(self.city)
        row.addWidget(city, 1)
        self.region_sec = Section(addresses.REGION_WORD.get(self._country, "Region"))
        self.region_pick = QComboBox()
        self.region_text = QLineEdit()
        self.region_sec.add(self.region_pick)
        self.region_sec.add(self.region_text)
        row.addWidget(self.region_sec, 1)
        self.postal_sec = Section(addresses.POSTAL_WORD.get(self._country, "Postal Code"))
        self.postal = sized(QLineEdit(record.postal), "short")
        self.postal_sec.add(self.postal)
        row.addWidget(self.postal_sec)
        lay.addLayout(row)

        country = Section("Country")
        self.country = combo([(code, name, "") for code, name in COUNTRIES.items()], self._country)
        self.country.setMaxVisibleItems(tokens.MENU_ROWS)
        country.add(self.country)
        lay.addWidget(country)

        self._fill_regions(record.region)
        self.street.edited.connect(self.edited)
        self.city.textEdited.connect(lambda _t: self.edited.emit())
        self.region_text.textEdited.connect(lambda _t: self.edited.emit())
        self.region_pick.activated.connect(lambda _i: self.edited.emit())
        self.postal.textEdited.connect(self._postal_typed)
        self.country.activated.connect(self._country_picked)

    def _fill_regions(self, keep: str) -> None:
        """The region as the country has it: picked from its list, or typed."""
        listed = addresses.regions(self._country)
        self.region_sec.label.setText(addresses.REGION_WORD.get(self._country, "Region"))
        self.postal_sec.label.setText(addresses.POSTAL_WORD.get(self._country, "Postal Code"))
        for w in (self.region_pick, self.region_text):  # a screen reader says what the field is called here
            w.setAccessibleName(self.region_sec.label.text())
        self.postal.setAccessibleName(self.postal_sec.label.text())
        self.region_pick.setVisible(bool(listed))
        self.region_text.setVisible(not listed)
        if listed:
            self.region_pick.blockSignals(True)
            self.region_pick.clear()
            self.region_pick.addItem(NO_REGION, "")
            for code, name in listed.items():
                self.region_pick.addItem(name, code)
            self.region_pick.blockSignals(False)
            set_combo(self.region_pick, addresses.region_code(self._country, keep) or "")
            self.region_text.clear()
        else:
            self.region_text.setText(keep)

    def _postal_typed(self, _text: str) -> None:
        """A postal code fills in the region while the region's blank (a region you picked stays)."""
        if addresses.regions(self._country) and not self.region_pick.currentData():
            found = addresses.region_from_postal(self._country, self.postal.text())
            if found:
                set_combo(self.region_pick, found)
        self.edited.emit()

    def _country_picked(self, _i: int) -> None:
        was = self.region()
        self._country = self.country.currentData()
        self._blank_country = False
        self._fill_regions(was)  # a region the new country doesn't have goes (never guessed)
        if addresses.regions(self._country) and not self.region_pick.currentData():
            self._postal_typed(self.postal.text())
        self.edited.emit()

    def region(self) -> str:
        if addresses.regions(self._country):
            return self.region_pick.currentData() or ""
        return " ".join(self.region_text.text().split())

    def values(self) -> tuple[str, str, str, str, str]:
        """(street lines, city, region, postal code, country): blank country while it's the home one you never
        picked, so an address from before reads as it did."""
        country = "" if self._blank_country and self._country == addresses.HOME else self._country
        return (
            self.street.text().strip(),
            " ".join(self.city.text().split()),
            self.region(),
            self.postal.text().strip().upper(),
            country,
        )

    def put_in(self, record) -> None:
        record.address, record.city, record.region, record.postal, record.country = self.values()
