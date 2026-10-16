"""Addresses (the standard's 4.6): the street lines, city, region, postal code and country of a renter or a profile.

A blank country is the home country (HOME), so an address saved before Bodega asked for a country reads as it did.
Where a country keeps a list of regions (states, provinces), the region is one of them, stored by its code
("Texas" -> "TX"): region_code() refuses anything else, never guesses; region_from_postal() reads it from the
postal code when it's left blank. lines() is the address as it's printed. No Qt here.

An address from before Bodega had these fields is all in its street lines ("1200 Sample Ave\\nAlbuquerque, NM
87102"), with city, region and postal code blank: it prints exactly as it was typed.
"""

from __future__ import annotations

import re

from bodega.core.countries import COUNTRIES

HOME = "US"  # Bodega's home country (docs/PROJECT_ADDENDUM.md: US formats)

REGIONS: dict[str, dict[str, str]] = {  # country -> region code -> its name, for the countries that keep a list
    "US": {
        "AL": "Alabama",
        "AK": "Alaska",
        "AZ": "Arizona",
        "AR": "Arkansas",
        "CA": "California",
        "CO": "Colorado",
        "CT": "Connecticut",
        "DE": "Delaware",
        "DC": "District of Columbia",
        "FL": "Florida",
        "GA": "Georgia",
        "HI": "Hawaii",
        "ID": "Idaho",
        "IL": "Illinois",
        "IN": "Indiana",
        "IA": "Iowa",
        "KS": "Kansas",
        "KY": "Kentucky",
        "LA": "Louisiana",
        "ME": "Maine",
        "MD": "Maryland",
        "MA": "Massachusetts",
        "MI": "Michigan",
        "MN": "Minnesota",
        "MS": "Mississippi",
        "MO": "Missouri",
        "MT": "Montana",
        "NE": "Nebraska",
        "NV": "Nevada",
        "NH": "New Hampshire",
        "NJ": "New Jersey",
        "NM": "New Mexico",
        "NY": "New York",
        "NC": "North Carolina",
        "ND": "North Dakota",
        "OH": "Ohio",
        "OK": "Oklahoma",
        "OR": "Oregon",
        "PA": "Pennsylvania",
        "RI": "Rhode Island",
        "SC": "South Carolina",
        "SD": "South Dakota",
        "TN": "Tennessee",
        "TX": "Texas",
        "UT": "Utah",
        "VT": "Vermont",
        "VA": "Virginia",
        "WA": "Washington",
        "WV": "West Virginia",
        "WI": "Wisconsin",
        "WY": "Wyoming",
        "AS": "American Samoa",
        "GU": "Guam",
        "MP": "Northern Mariana Islands",
        "PR": "Puerto Rico",
        "VI": "U.S. Virgin Islands",
        "AA": "Armed Forces Americas",
        "AE": "Armed Forces Europe",
        "AP": "Armed Forces Pacific",
    },
    "CA": {
        "AB": "Alberta",
        "BC": "British Columbia",
        "MB": "Manitoba",
        "NB": "New Brunswick",
        "NL": "Newfoundland and Labrador",
        "NS": "Nova Scotia",
        "NT": "Northwest Territories",
        "NU": "Nunavut",
        "ON": "Ontario",
        "PE": "Prince Edward Island",
        "QC": "Quebec",
        "SK": "Saskatchewan",
        "YT": "Yukon",
    },
    "AU": {
        "ACT": "Australian Capital Territory",
        "NSW": "New South Wales",
        "NT": "Northern Territory",
        "QLD": "Queensland",
        "SA": "South Australia",
        "TAS": "Tasmania",
        "VIC": "Victoria",
        "WA": "Western Australia",
    },
}
REGION_WORD = {"US": "State", "CA": "Province", "AU": "State"}  # what the field is called there (else "Region")
POSTAL_WORD = {"US": "ZIP Code"}  # (else "Postal Code")

# The first three digits of a US ZIP code -> its state (USPS's prefixes), as ranges (first, last, state)
_US_ZIP3 = (
    (5, 5, "NY"),
    (6, 7, "PR"),
    (8, 8, "VI"),
    (9, 9, "PR"),
    (10, 27, "MA"),
    (28, 29, "RI"),
    (30, 38, "NH"),
    (39, 49, "ME"),
    (50, 54, "VT"),
    (55, 55, "MA"),
    (56, 59, "VT"),
    (60, 69, "CT"),
    (70, 89, "NJ"),
    (90, 99, "AE"),
    (100, 149, "NY"),
    (150, 196, "PA"),
    (197, 199, "DE"),
    (200, 200, "DC"),
    (201, 201, "VA"),
    (202, 205, "DC"),
    (206, 219, "MD"),
    (220, 246, "VA"),
    (247, 268, "WV"),
    (270, 289, "NC"),
    (290, 299, "SC"),
    (300, 319, "GA"),
    (320, 339, "FL"),
    (340, 340, "AA"),
    (341, 349, "FL"),
    (350, 369, "AL"),
    (370, 385, "TN"),
    (386, 397, "MS"),
    (398, 399, "GA"),
    (400, 427, "KY"),
    (430, 459, "OH"),
    (460, 479, "IN"),
    (480, 499, "MI"),
    (500, 528, "IA"),
    (530, 549, "WI"),
    (550, 567, "MN"),
    (569, 569, "DC"),
    (570, 577, "SD"),
    (580, 588, "ND"),
    (590, 599, "MT"),
    (600, 629, "IL"),
    (630, 658, "MO"),
    (660, 679, "KS"),
    (680, 693, "NE"),
    (700, 714, "LA"),
    (716, 729, "AR"),
    (730, 731, "OK"),
    (733, 733, "TX"),
    (734, 749, "OK"),
    (750, 799, "TX"),
    (800, 816, "CO"),
    (820, 831, "WY"),
    (832, 838, "ID"),
    (840, 847, "UT"),
    (850, 865, "AZ"),
    (870, 884, "NM"),
    (885, 885, "TX"),
    (889, 898, "NV"),
    (900, 961, "CA"),
    (962, 966, "AP"),
    (967, 968, "HI"),
    (969, 969, "GU"),
    (970, 979, "OR"),
    (980, 994, "WA"),
    (995, 999, "AK"),
)
_US_ZIP5 = ((96799, 96799, "AS"), (96950, 96952, "MP"))  # inside the prefixes above
_CA_FIRST = {  # a Canadian postal code's first letter -> its province (X: the north, X0A-X0C Nunavut)
    "A": "NL",
    "B": "NS",
    "C": "PE",
    "E": "NB",
    "G": "QC",
    "H": "QC",
    "J": "QC",
    "K": "ON",
    "L": "ON",
    "M": "ON",
    "N": "ON",
    "P": "ON",
    "R": "MB",
    "S": "SK",
    "T": "AB",
    "V": "BC",
    "X": "NT",
    "Y": "YT",
}
_AU_POSTCODE = (  # (first, last, state); the capital's ranges sit inside New South Wales'
    (200, 299, "ACT"),
    (800, 999, "NT"),
    (2600, 2618, "ACT"),
    (2900, 2920, "ACT"),
    (1000, 2999, "NSW"),
    (3000, 3999, "VIC"),
    (4000, 4999, "QLD"),
    (5000, 5999, "SA"),
    (6000, 6999, "WA"),
    (7000, 7999, "TAS"),
    (8000, 8999, "VIC"),
    (9000, 9999, "QLD"),
)


def country_of(code: str) -> str:
    """The country an address is in: its own, or the home country when none was given."""
    code = code.strip().upper()
    return code if code in COUNTRIES else HOME


def country_name(code: str) -> str:
    return COUNTRIES.get(country_of(code), "")


def regions(country: str) -> dict[str, str]:
    """The country's own list of regions (code -> name), or {} where none is kept."""
    return REGIONS.get(country_of(country), {})


def region_code(country: str, text: str) -> str | None:
    """A region typed or picked, as its code ("Texas", "tx" -> "TX"); "" for none. Where the country keeps a list,
    anything not on it is refused (None); elsewhere it's kept as typed."""
    text = " ".join(text.split())
    if not text:
        return ""
    listed = regions(country)
    if not listed:
        return text
    if text.upper() in listed:
        return text.upper()
    by_name = {name.casefold(): code for code, name in listed.items()}
    return by_name.get(text.casefold())


def region_from_postal(country: str, postal: str) -> str:
    """The region a postal code is in, where it can be told ("" where it can't)."""
    country, postal = country_of(country), postal.strip().upper()
    if country == "US" and (m := re.fullmatch(r"(\d{5})(?:-?\d{4})?", postal)):
        five = int(m.group(1))
        for first, last, state in (*_US_ZIP5, *((a * 100, b * 100 + 99, s) for a, b, s in _US_ZIP3)):
            if first <= five <= last:
                return state
    elif country == "CA" and re.fullmatch(r"[A-Z]\d[A-Z] ?\d[A-Z]\d", postal):
        if postal[0] == "X" and postal[:3] in ("X0A", "X0B", "X0C"):
            return "NU"
        return _CA_FIRST.get(postal[0], "")
    elif country == "AU" and re.fullmatch(r"\d{4}", postal):
        n = int(postal)
        for first, last, state in _AU_POSTCODE:
            if first <= n <= last:
                return state
    return ""


def lines(street: str, city: str = "", region: str = "", postal: str = "", country: str = "") -> list[str]:
    """The address as it's printed: the street lines, then "City, ST 12345", then the country when it isn't the
    home country. One saved before these fields is its street lines alone, as typed."""
    out = [line.strip() for line in street.splitlines() if line.strip()]
    place = city.strip()
    if region.strip():
        place = f"{place}, {region.strip()}" if place else region.strip()
    if postal.strip():
        place = f"{place} {postal.strip()}" if place else postal.strip()
    if place:
        out.append(place)
    if country.strip() and country_of(country) != HOME:
        out.append(country_name(country))
    return out


def of(record) -> list[str]:
    """A renter's or a profile's address, as it's printed."""
    return lines(record.address, record.city, record.region, record.postal, record.country)
