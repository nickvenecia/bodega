"""Every setting Bodega keeps in settings.json, with what it holds and what it is until you change it: one list,
so each place that reads a setting gets the same default, and a value of the wrong kind (a hand-edited file, an
older Bodega) is read as the default, never as a crash. No Qt here.

    value(lib.settings, "appearance")  ->  "system", "light" or "dark"
"""

from __future__ import annotations

import copy

from bodega.core.log import get_logger

log = get_logger(__name__)

DEFAULTS: dict[str, tuple[type, object]] = {  # key -> (what it holds, its default)
    "appearance": (str, "system"),  # system / light / dark
    "accent": (str, ""),  # "" = Bodega's own blue
    "auto_update": (bool, True),  # check for updates each time Bodega opens
    "dark_preview": (bool, False),  # the page window's Dark Page
    "view": (str, "gear"),  # the place you were on
    "calendar_mode": (str, "month"),  # month / timeline
    "business": (str, ""),  # the profile you work as
    "google_sheet": (str, ""),  # the last Google Sheet link imported
    "export_dir": (str, ""),  # where the last PDF went
    "geometry": (str, ""),  # the window's size and place
    "folded": (list, []),  # gear dividers you folded
    "column_order": (list, []),  # the gear list's columns, in the order you put them
    "ai_models": (dict, {}),  # the provider's list of models, kept for the day it was asked
    "companies_guessed": (bool, False),  # gear from before Company existed got its company once
}


def value(settings: dict, key: str):
    """The setting, or its default when it's missing or of the wrong kind."""
    kind, default = DEFAULTS[key]
    if key not in settings:
        return copy.copy(default)  # a copy: one reader's list is never another's
    got = settings[key]
    if isinstance(got, kind) and not (kind is not bool and isinstance(got, bool)):
        return got
    log.info("setting %s held an odd value; using its default", key)
    return copy.copy(default)
