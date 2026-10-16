"""Settings › Keyboard Shortcuts (Help › Keyboard Shortcuts, ⌘/ or ?): every command that has a key, read from the
menus themselves, so the list is never out of date. Shows ⌘ ⇧ ⌥ on the Mac and Ctrl/Shift/Alt elsewhere."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QLabel, QMenuBar, QWidget

from bodega.ui.components.widgets import Section, hbox, vbox
from bodega.ui.style import tokens

# keys that work without a menu item
EXTRA = [
    ("Delete What's Picked", QKeySequence(Qt.Key.Key_Backspace)),
    ("Close Panel", QKeySequence(Qt.Key.Key_Escape)),
]


def keys_by_menu(bar: QMenuBar) -> list[tuple[str, list[tuple[str, str]]]]:
    out = []
    for top in bar.actions():
        menu = top.menu()
        if menu is None:
            continue
        rows = []
        for a in menu.actions():
            keys = a.shortcuts()
            if a.isSeparator() or not keys or keys[0].isEmpty():
                continue
            name = a.text().replace("&", "")
            name = name.split(" Change to ")[0].removesuffix(" Typing")  # Undo and Redo, by their own names
            rows.append((name, keys[0].toString(QKeySequence.SequenceFormat.NativeText)))
        if rows:
            out.append((top.text().replace("&", ""), rows))
    return out


def single_keys(acts: list[QAction]) -> list[tuple[str, str]]:
    """The single keys (window/menus.py SINGLE_KEYS), each by its own key: N, E, D, /, ?, A."""
    return [(a.text(), a.shortcuts()[0].toString(QKeySequence.SequenceFormat.NativeText)) for a in acts]


class ShortcutsList(QWidget):
    """Every key, grouped by menu (Settings › Keyboard Shortcuts); first `top` (the single keys' switch), and the
    single keys (`singles`) after the menus."""

    def __init__(
        self,
        bar: QMenuBar,
        singles: list[QAction] | None = None,
        top: Section | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        bl = vbox(self, (0, 0, tokens.SPACE_3, tokens.SPACE_4), tokens.SPACE_3)
        if top is not None:
            bl.addWidget(top)
        groups = keys_by_menu(bar)
        if singles:
            groups.append(("Single Keys", single_keys(singles)))
        groups.append(("Anywhere", [(t, k.toString(QKeySequence.SequenceFormat.NativeText)) for t, k in EXTRA]))
        for title, rows in groups:
            sec = Section(title)
            for text, key in rows:
                row = hbox(spacing=tokens.SPACE_2)
                row.addWidget(QLabel(text), 1)
                cap = QLabel(key)
                cap.setObjectName("KeyCap")
                row.addWidget(cap)
                sec.add(row)
            bl.addWidget(sec)
        bl.addStretch(1)
