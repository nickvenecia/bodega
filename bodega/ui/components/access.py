"""The person's accessibility settings, from the computer: Reduce Motion, Increase Contrast and Reduce
Transparency (the standard's §2.13 and G.1).

Qt reports the first two (QStyleHints.accessibility()); transparency is read from the system's own setting (the
Mac's universal access defaults, the Windows "Transparency effects" switch). BODEGA_REDUCE_MOTION,
BODEGA_MORE_CONTRAST and BODEGA_LESS_TRANSPARENCY ("1" or "0") stand in for the system, for tests and for anyone
who wants them without changing the whole computer.

- Reduce Motion: nothing slides or rises; the inspector, toasts and a dragged row arrive at once (`duration()`).
- Increase Contrast: secondary words take the main text's color and every edge is drawn strong (tokens.use).
- Reduce Transparency: the glass panels are solid (tokens.use).
- Show Scroll Bars: Always (and Windows' and GNOME's own): scroll bars stay, with room kept for them; otherwise
  they lie over the content and show only while scrolling (components/scrollbars.py).
"""

from __future__ import annotations

import os
import subprocess
import sys

from bodega.core.fileutil import popen_kwargs
from bodega.core.log import get_logger

log = get_logger(__name__)


def _env(name: str) -> bool | None:
    v = os.environ.get(name, "").strip()
    return {"1": True, "0": False}.get(v)


def _hints():
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication.instance()
    if app is None or not hasattr(app.styleHints(), "accessibility"):
        return None
    return app.styleHints().accessibility()


def _asks(read) -> bool:
    """One of Qt's accessibility hints, False if there's none to read (Qt can replace the object under us)."""
    try:
        a = _hints()
        return a is not None and read(a)
    except RuntimeError:
        return False


def reduce_motion() -> bool:
    forced = _env("BODEGA_REDUCE_MOTION")
    if forced is not None:
        return forced
    from PySide6.QtCore import Qt

    return _asks(lambda a: a.motionPreference() == Qt.MotionPreference.ReducedMotion)


def more_contrast() -> bool:
    forced = _env("BODEGA_MORE_CONTRAST")
    if forced is not None:
        return forced
    from PySide6.QtCore import Qt

    return _asks(lambda a: a.contrastPreference() == Qt.ContrastPreference.HighContrast)


_transparency: bool | None = None


def less_transparency() -> bool:
    """Read once (it asks the system); a change applies the next time Bodega opens."""
    global _transparency
    forced = _env("BODEGA_LESS_TRANSPARENCY")
    if forced is not None:
        return forced
    if _transparency is None:
        _transparency = _system_less_transparency()
    return _transparency


_always_bars: bool | None = None


def always_show_scroll_bars() -> bool:
    """The system says to show scroll bars all the time: the Mac's Show Scroll Bars: Always, Windows' Always Show
    Scrollbars, GNOME's overlay scrolling off. Otherwise they're out of sight until scrolling (the standard's §6.2,
    I-09). Read once; BODEGA_SCROLL_BARS ("always" or "overlay") stands in for the system."""
    global _always_bars
    forced = os.environ.get("BODEGA_SCROLL_BARS", "").strip().lower()
    if forced in ("always", "overlay"):
        return forced == "always"
    if _always_bars is None:
        _always_bars = _system_always_bars()
    return _always_bars


def _system_always_bars() -> bool:
    try:
        if sys.platform == "darwin":
            out = subprocess.run(
                ["/usr/bin/defaults", "read", "-g", "AppleShowScrollBars"],
                capture_output=True, text=True, timeout=2, **popen_kwargs(),
            )  # fmt: skip
            return out.stdout.strip() == "Always"
        if sys.platform == "win32":
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Accessibility") as k:
                value, _kind = winreg.QueryValueEx(k, "DynamicScrollbars")
            return value == 0
        if os.environ.get("GTK_OVERLAY_SCROLLING", "").strip() == "0":
            return True
        out = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.interface", "overlay-scrolling"],
            capture_output=True, text=True, timeout=2, **popen_kwargs(),
        )  # fmt: skip
        return out.stdout.strip() == "false"
    except (OSError, subprocess.SubprocessError, ValueError):
        log.debug("couldn't read the scroll bar setting", exc_info=True)
    return False


def _system_less_transparency() -> bool:
    try:
        if sys.platform == "darwin":
            out = subprocess.run(
                ["/usr/bin/defaults", "read", "com.apple.universalaccess", "reduceTransparency"],
                capture_output=True, text=True, timeout=2, **popen_kwargs(),
            )  # fmt: skip
            return out.stdout.strip() == "1"
        if sys.platform == "win32":
            import winreg

            key = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as k:
                value, _kind = winreg.QueryValueEx(k, "EnableTransparency")
            return value == 0
    except (OSError, subprocess.SubprocessError, ValueError):
        log.debug("couldn't read the transparency setting", exc_info=True)
    return False


def duration(ms: int) -> int:
    """An animation's length, or none at all when the person asked for less motion."""
    return 0 if reduce_motion() else ms
