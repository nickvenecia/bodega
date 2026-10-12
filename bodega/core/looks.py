"""The paper's colors: the accent you pick in your profile, and the ink for white paper and the Dark Page."""

from __future__ import annotations

from dataclasses import dataclass

# key -> (label, accent on white paper, accent on the Dark Page)
COLORS = {
    "blue": ("Sky Blue", "#2A62C9", "#7FB0FF"),
    "chile": ("Chile Red", "#C8352A", "#F47566"),
    "violet": ("Dusk Violet", "#5B48D9", "#A99BFF"),
    "turquoise": ("Turquoise", "#11806F", "#4FD1BD"),
    "marigold": ("Marigold", "#A86A12", "#F2B347"),
    "sage": ("Sage", "#4A7356", "#8FC29C"),
    "ink": ("Ink", "#1B1B1F", "#F2F0EB"),
}

FONT = "Inter"
MONO = "IBM Plex Mono"
WHITE_PAPER = "#FFFFFF"


@dataclass(frozen=True)
class Palette:
    paper: str
    ink: str
    soft: str
    faint: str
    rule: str
    fill: str  # boxes, table headings
    accent: str
    on_accent: str


def palette(color: str, dark: bool = False) -> Palette:
    _label, light_accent, dark_accent = COLORS.get(color, COLORS["blue"])
    if dark:
        return Palette(
            "#1A1A1E", "#F2F0EB", "#B4AFA8", "#7C7872", "#3A3A42", "#24242A", dark_accent, "#121214"
        )
    return Palette(
        WHITE_PAPER, "#1B1B1F", "#5E5E66", "#8E8E96", "#D9D9DE", "#F3F3F5", light_accent, "#FFFFFF"
    )
