"""Finding and using things in a window the way a person (or a screen reader) does: a button by its words, a field
by its label, a menu command by its menu and its words, a part by its own object name (the standard's T-13).

UI tests act through these, and through what each part makes public, never through a part's private names
(tests/test_code_rules.py checks)."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QEvent, QObject, QPoint, QPointF, Qt, QTimer
from PySide6.QtGui import QAction, QContextMenuEvent, QEnterEvent, QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QAbstractButton,
    QAbstractSpinBox,
    QApplication,
    QComboBox,
    QLineEdit,
    QMainWindow,
    QMenu,
    QPlainTextEdit,
    QWidget,
)

FIELDS = (QLineEdit, QComboBox, QAbstractSpinBox, QPlainTextEdit)


def plain(words: str) -> str:
    """Words as they're read: no & that marks a mnemonic ("&&" is a real &), the spaces closed up."""
    return " ".join(words.replace("&&", "\x00").replace("&", "").replace("\x00", "&").split())


def _named(found: list, words: str, names: Callable[[object], list[str]], what: str):
    """The one thing among `found` named `words` (a trailing "…" counts only when nothing matches without it)."""
    for trim in (False, True):
        cut = (lambda s: s.removesuffix("…").rstrip()) if trim else (lambda s: s)
        hits = [x for x in found if cut(words) in {cut(plain(n)) for n in names(x) if n}]
        if len(hits) == 1:
            return hits[0]
        if hits:
            raise AssertionError(f"{len(hits)} {what}s are called {words!r}: look inside the part that holds one")
    seen = sorted({plain(n) for x in found for n in names(x) if n})
    raise AssertionError(f"no {what} called {words!r}; there are: {seen}")


def _showing(w: QWidget, top: QWidget) -> bool:
    """It shows when `top` does (`top` itself may not be on screen yet: a form made for a test)."""
    return w is top or w.isVisibleTo(top)


def button(top: QWidget, words: str) -> QAbstractButton:
    """The button showing in `top` whose words, or the name a screen reader says for it, are `words` ("Save"; an
    icon's "Close", which it takes from its tooltip)."""
    top.ensurePolished()  # (an icon button is named by its tooltip as it's polished: app.py _name_from_tip)
    found = [b for b in top.findChildren(QAbstractButton) if _showing(b, top)]
    return _named(found, words, lambda b: [b.text(), b.accessibleName()], "button")


def field(top: QWidget, name: str) -> QWidget:
    """The field showing in `top` that a screen reader names `name` (a Section names its fields by its label)."""
    found = [f for f in top.findChildren(QWidget) if isinstance(f, FIELDS) and _showing(f, top)]
    return _named(found, name, lambda f: [f.accessibleName()], "field")


def by_id(top: QObject, name: str, kind: type = QObject) -> QObject:
    """A part by the object name it gives itself (the standard's component-owned test ID)."""
    found = top.findChild(kind, name)
    assert found is not None, f"nothing in {type(top).__name__} is called {name!r}"
    return found


# Menus
def open_menu(menu: QMenu) -> QMenu:
    """A menu as it opens: it fills itself and turns its commands on or off for what's open now."""
    menu.aboutToShow.emit()
    return menu


def bar_menu(window: QMainWindow, title: str) -> QMenu:
    """The menu bar's menu called `title`, opened."""
    menus = [a.menu() for a in window.menuBar().actions() if a.menu() is not None]
    return open_menu(_named(menus, title, lambda m: [m.title()], "menu"))


def action_in(menu: QMenu, words: str) -> QAction:
    """The first command in a menu (an open one) with these words, as a person reading down it finds it."""
    acts = [a for a in menu.actions() if not a.isSeparator()]
    for trim in (False, True):
        cut = (lambda s: s.removesuffix("…").rstrip()) if trim else (lambda s: s)
        hit = next((a for a in acts if cut(plain(a.text())) == cut(words)), None)
        if hit is not None:
            return hit
    raise AssertionError(f"no {words!r} in the menu; it has: {[plain(a.text()) for a in acts]}")


def menu_action(window: QMainWindow, title: str, words: str) -> QAction:
    """A command in the menu bar, by its menu's title and its own words (the menu opened first, as you'd open it)."""
    return action_in(bar_menu(window, title), words)


def pick(menu: QMenu, words: str) -> None:
    """Open a menu and pick a command from it."""
    a = action_in(open_menu(menu), words)
    assert a.isEnabled(), f"{words!r} is off"
    a.trigger()


def pick_from_next_menu(words: str) -> list[str]:
    """Once the next menu opens (from a right-click, say, which waits for it), pick `words` from it, as a person
    would; then it closes. Returns the words the menu offered, filled in once it has opened."""
    offered: list[str] = []
    tries = [500]

    def look() -> None:
        shown = [w for w in QApplication.topLevelWidgets() if isinstance(w, QMenu) and w.isVisible()]
        if not shown:
            if tries[0]:
                tries[0] -= 1
                QTimer.singleShot(10, look)
            return
        m = shown[0]
        offered.extend(plain(a.text()) for a in m.actions() if not a.isSeparator())
        hit = next((a for a in m.actions() if plain(a.text()) == words and a.isEnabled()), None)
        if hit is not None:
            hit.trigger()
        m.close()

    QTimer.singleShot(0, look)
    return offered


# Doing
def choose(box: QComboBox, words: str) -> None:
    """Pick `words` from a dropdown's list, as a click on it does (the box says it was picked)."""
    i = box.findText(words)
    assert i >= 0, f"no {words!r} in the list; it has: {[box.itemText(n) for n in range(box.count())]}"
    box.setCurrentIndex(i)
    box.activated.emit(i)
    box.textActivated.emit(box.itemText(i))


def type_into(f: QWidget, text: str) -> None:
    """Type into a field, over what's in it, then leave it (as Tab or a click elsewhere would)."""
    f.setFocus()
    f.selectAll()
    QTest.keyClicks(f, text)
    if isinstance(f, QLineEdit):
        f.editingFinished.emit()


def press(w: QWidget, key: Qt.Key, modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier) -> None:
    QTest.keyClick(w, key, modifiers)


def click(
    w: QWidget,
    at: QPoint | QPointF | None = None,
    modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
) -> None:
    """A click on `w` (at its middle, or `at`, in its own coordinates)."""
    pos = at.toPoint() if isinstance(at, QPointF) else at if at is not None else w.rect().center()
    QTest.mouseClick(w, Qt.MouseButton.LeftButton, modifiers, pos)


def right_click(w: QWidget, at: QPoint) -> None:
    """A right-click at `at` (its menu, if it has one)."""
    QApplication.sendEvent(w, QContextMenuEvent(QContextMenuEvent.Reason.Mouse, at, w.mapToGlobal(at)))


def hover(w: QWidget, at: QPoint | None = None) -> None:
    """The pointer comes onto `w` and rests at `at` (no button held)."""
    pos = QPointF(at if at is not None else w.rect().center())
    where = QPointF(w.mapToGlobal(pos.toPoint()))
    QApplication.sendEvent(w, QEnterEvent(pos, pos, where))
    QApplication.sendEvent(
        w,
        QMouseEvent(
            QEvent.Type.MouseMove,
            pos,
            where,
            Qt.MouseButton.NoButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        ),
    )


def wait_for(done: Callable[[], object], ms: int = 5000) -> None:
    """Wait for what you're waiting on (never a fixed time), the window going on meanwhile."""
    for _ in range(ms // 10):
        if done():
            return
        QTest.qWait(10)
    raise AssertionError("never happened")


def keep_size(window: QMainWindow) -> None:
    """The main window opens at the size it's given (a test's, a screenshot's) and never saves its size and place
    for next time, instead of opening where it was left. Only tests and screenshots want that, so the window keeps
    it as a private note and this is the one place a test sets it (tests/test_code_rules.py says why)."""
    window._restored = True
