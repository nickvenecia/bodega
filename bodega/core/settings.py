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
    "text_size": (int, 0),  # how large Bodega draws, in percent (100–200); 0: as the computer's text size is
    "auto_update": (bool, True),  # check for updates each time Bodega opens
    "dark_preview": (bool, False),  # the page window's Dark Page
    "view": (str, "gear"),  # the place you were on
    "calendar_mode": (str, "month"),  # month / timeline
    "business": (str, ""),  # the profile you work as
    "google_sheet": (str, ""),  # the last Google Sheet link imported
    "import_columns": (dict, {}),  # a sheet's header (importer.layout_key) -> which column is which, as you set it
    "ai_usage": (dict, {}),  # what Bodega has asked your AI today and this month (services/ai/usage.py)
    "ai_daily_limit": (int, 300),  # questions to your AI a day (0: no limit), usage.DEFAULT_DAILY
    "single_keys": (bool, True),  # N, E, D, /, ? and A work alone, outside text fields (Settings › Keyboard Shortcuts)
    "export_dir": (str, ""),  # where the last PDF went
    "geometry": (str, ""),  # the window's size and place
    "folded": (list, []),  # gear dividers you folded
    "gear_open": (list, []),  # the pieces you opened in the gear list, to show the gear that goes with them
    "column_order": (list, []),  # the gear list's columns, in the order you put them
    "ai_models": (dict, {}),  # the provider's list of models, kept for the day it was asked
    "companies_guessed": (bool, False),  # gear from before Company existed got its company once
    "groups": (dict, {}),  # which cards are open in each panel ("gear", "kit", "rental")
    "hidden_columns": (list, None),  # the gear list's columns you hid (None: never chosen, the list's own)
    "columns_known": (list, []),  # the columns there were when you last chose (newer ones start hidden)
    "divide": (dict, {}),  # how the gear list is divided: in All Gear ("all") and in a group ("grp")
    "sidebar_folded": (list, None),  # the sidebar rows you folded (None: the ones folded at first)
    "sidebar_rows_seen": (list, None),  # the rows there were when you last folded
    "sheet_pricing": (dict, {}),  # the day rate % and tax a sheet had, before there was a profile
    "group_list": (list, None),  # your groups, in your order (None: in the order your gear has them)
    "departments": (list, None),  # (the same, from before groups had their own list)
    "ai": (dict, {}),  # the AI provider, model and address (the key is in the keychain, never here)
    "numbers": (dict, {}),  # the last rental number given in each series (never given again)
    "last_update_check": (float, 0.0),  # when Bodega last asked for an update (seconds)
    "format": (int, 0),  # the data folder's format (core/store.py FORMAT): what wrote it
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
