"""App entry point: fonts, stylesheet, rounded popups, one window at a time, and --smoke-test."""

from __future__ import annotations

import logging
import os
import secrets
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QPoint, Qt, QTimer
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QAbstractButton,
    QAbstractScrollArea,
    QAbstractSlider,
    QAbstractSpinBox,
    QApplication,
    QComboBox,
    QLabel,
    QLineEdit,
    QMenu,
    QPlainTextEdit,
    QScrollBar,
    QTextEdit,
    QWidget,
)

from bodega import APP_NAME, __version__
from bodega.core import errors
from bodega.core.log import get_logger, setup_logging
from bodega.core.paths import ASSETS, data_dir, log_dir, use_data_dir
from bodega.ui.components.widgets import ComboItemDelegate
from bodega.ui.style import theme, tokens

log = get_logger(__name__)


def _server_name() -> str:
    """Where the open Bodega listens. On Linux a plain name would be a socket in /tmp, which another account
    on the computer could take first (Bodega would then quit at launch), so it's a path in a folder only this
    account can use: the session's runtime folder, else Bodega's own data folder."""
    import getpass

    try:
        user = getpass.getuser()
    except Exception:
        user = "user"
    if sys.platform.startswith("linux"):
        runtime = os.environ.get("XDG_RUNTIME_DIR", "")
        folder = Path(runtime) if runtime and Path(runtime).is_dir() else data_dir()
        path = folder / "bodega.sock"
        if len(str(path)) < 100:  # a socket's path has a length limit
            try:
                folder.mkdir(parents=True, exist_ok=True)
                return str(path)
            except OSError:
                log.warning("no folder of its own for the open-window socket")
    return f"bodega-{user}"


def _wake_running() -> bool:
    """If Bodega is already open, bring its window forward and return True (one window, one set of files)."""
    from PySide6.QtNetwork import QLocalSocket

    sock = QLocalSocket()
    sock.connectToServer(_server_name())
    if not sock.waitForConnected(1500):
        return False
    sock.write(b"show\n")
    sock.flush()
    sock.waitForBytesWritten(1500)
    sock.disconnectFromServer()
    return True


def _listen(window) -> object:
    from PySide6.QtNetwork import QLocalServer

    name = _server_name()
    QLocalServer.removeServer(name)  # clear a stale socket from a crash
    server = QLocalServer(window)
    server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)  # only this user's account
    if not server.listen(name):
        return None

    def on_conn() -> None:
        sock = server.nextPendingConnection()

        def read() -> None:
            sock.readAll()  # the message is always "show"; anything else is ignored
            if window.isMinimized():
                window.showNormal()
            window.raise_()
            window.activateWindow()
            sock.disconnectFromServer()

        sock.readyRead.connect(read)
        sock.disconnected.connect(sock.deleteLater)

    server.newConnection.connect(on_conn)
    return server


def place_menu(menu: QWidget, button: QWidget) -> None:
    """A button's menu opens just below it, with a little air between: lined up with its left edge, or, for a
    button on the right of the window, with its right edge (so it never runs off past the window)."""
    size = menu.size()
    top_left = button.mapToGlobal(QPoint(0, 0))
    win = button.window()
    on_right = button.mapTo(win, button.rect().center()).x() > win.width() / 2
    x = top_left.x() + button.width() - size.width() if on_right else top_left.x()
    y = top_left.y() + button.height() + tokens.MENU_GAP
    screen = button.screen().availableGeometry() if button.screen() else None
    if screen is not None:
        if y + size.height() > screen.bottom():  # no room below: above it instead
            y = top_left.y() - size.height() - tokens.MENU_GAP
        x = max(screen.left(), min(x, screen.right() - size.width()))
    menu.move(x, y)


def _name_from_tip(b: QAbstractButton) -> None:
    """A button that's only an icon is named by its tooltip, for screen readers (VoiceOver, Narrator, Orca),
    which would otherwise say only "button"."""
    if b.text().strip() or b.property("named_by_hand"):
        return
    tip = " ".join(b.toolTip().split())
    tip = tip.split(" (")[0] if tip.endswith(")") else tip  # "Assistant (⌘J)": the name, not the key
    if tip and b.accessibleName() != tip:
        b.setAccessibleName(tip)


class _RoundPopups(QObject):
    """Qt gives menus and dropdown lists square windows; make them see-through so the
    stylesheet's rounded corners are what you actually see. A button's menu opens just below it, with a
    little air (place_menu); so does a dropdown's list. Also: scrolling never changes a value
    (dropdowns, dates and sliders pass the wheel on to the panel, which scrolls instead), and never moves the
    cursor (Qt gives dropdowns and dates the focus as the wheel goes over them: they take it from a click or Tab
    only, so the field you're typing in keeps it while you scroll past). And a field you're typing in keeps its
    own editing keys: ⌘⌫ / Ctrl+Backspace deletes a word or a line there, never the piece (Delete…). Buttons that
    are only an icon take their tooltip as their name, for screen readers."""

    @staticmethod
    def _see_through(win: QWidget) -> None:
        if not win.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground):
            win.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
            win.setWindowFlag(Qt.WindowType.NoDropShadowWindowHint, True)
            win.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def _menu_type_ahead(self, menu: QMenu, typed: str) -> bool:
        from time import monotonic

        from bodega.core import search

        now = monotonic()
        quick = now - getattr(self, "_menu_typed_at", 0.0) < QApplication.keyboardInputInterval() / 1000
        self._menu_typed = (getattr(self, "_menu_typed", "") if quick else "") + typed
        self._menu_typed_at = now
        wanted = search.folded(self._menu_typed)
        choices = [a for a in menu.actions() if a.isVisible() and a.isEnabled() and not a.isSeparator()]
        for a in choices:
            if search.folded(a.text().replace("&", "")).startswith(wanted):
                menu.setActiveAction(a)
                return True
        return False  # nothing starts so: the menu does what it would

    def eventFilter(self, obj, ev):
        if (
            ev.type() == QEvent.Type.KeyPress
            and isinstance(obj, QMenu)
            and ev.key() in (Qt.Key.Key_Home, Qt.Key.Key_End, Qt.Key.Key_PageUp, Qt.Key.Key_PageDown)
        ):  # Home / End (and Page Up / Down) go to a menu's first or last choice, as the Mac's menus do
            choices = [a for a in obj.actions() if a.isVisible() and a.isEnabled() and not a.isSeparator()]
            if choices:
                first = ev.key() in (Qt.Key.Key_Home, Qt.Key.Key_PageUp)
                obj.setActiveAction(choices[0] if first else choices[-1])
            return True
        if (
            ev.type() == QEvent.Type.KeyPress
            and isinstance(obj, QMenu)
            and not ev.modifiers() & ~Qt.KeyboardModifier.ShiftModifier
            and ev.text().strip()
            and ev.text().isprintable()
        ):  # typing a choice's first letters jumps to it, as the Mac's menus do
            return self._menu_type_ahead(obj, ev.text())
        if (
            ev.type() == QEvent.Type.ShortcutOverride
            and isinstance(obj, (QLineEdit, QPlainTextEdit, QTextEdit, QAbstractSpinBox))
            and ev.key() in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete)
            and not getattr(obj, "isReadOnly", lambda: False)()
        ):
            ev.accept()  # the field gets the key; the window's shortcut doesn't fire
            return False
        wheel_on_control = isinstance(obj, (QComboBox, QAbstractSlider, QAbstractSpinBox)) and not isinstance(
            obj, QScrollBar
        )
        if ev.type() == QEvent.Type.Wheel and wheel_on_control:
            area = obj.parent()
            while area is not None and not isinstance(area, QAbstractScrollArea):
                area = area.parent()
            if area is not None:
                QApplication.sendEvent(area.verticalScrollBar(), ev)
            return True
        if ev.type() == QEvent.Type.Show and isinstance(obj, QMenu) and obj.defaultAction() is None:
            danger = next((a for a in obj.actions() if theme.is_danger(a.icon())), None)
            if danger is not None:  # its words red, like its icon (theme.py: QMenu::item:default)
                obj.setDefaultAction(danger)
        if ev.type() == QEvent.Type.Show and isinstance(obj, QWidget) and obj.isWindow():
            owner = obj.parentWidget()
            if (
                isinstance(obj, QMenu)
                and isinstance(owner, QAbstractButton)
                and getattr(owner, "menu", lambda: None)() is obj
            ):
                place_menu(obj, owner)
            elif obj.inherits("QComboBoxPrivateContainer") and isinstance(owner, QComboBox):
                below = owner.mapToGlobal(QPoint(0, owner.height()))
                if obj.y() >= below.y() - 1:  # opened below the box: leave the same air
                    obj.move(obj.x(), below.y() + tokens.MENU_GAP)
        if ev.type() in (QEvent.Type.Polish, QEvent.Type.ToolTipChange) and isinstance(obj, QAbstractButton):
            _name_from_tip(obj)
        if ev.type() == QEvent.Type.Polish and isinstance(obj, QWidget):
            if obj.focusPolicy() == Qt.FocusPolicy.WheelFocus:
                obj.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            if isinstance(obj, QComboBox):
                obj.setMaxVisibleItems(tokens.MENU_ROWS)  # a list of data shows 8 rows, then scrolls
            if isinstance(obj, QAbstractButton) and obj.focusPolicy() == Qt.FocusPolicy.StrongFocus:
                obj.setFocusPolicy(Qt.FocusPolicy.TabFocus)  # Tab gives it the focus (and its ring); a click doesn't
            if (
                isinstance(obj, QLabel) and obj.textFormat() == Qt.TextFormat.AutoText and not obj.inherits("QTipLabel")
            ):  # names are shown as typed: a gear name like "<img …>" mustn't turn into a picture
                obj.setTextFormat(Qt.TextFormat.PlainText)
            if (isinstance(obj, QMenu) and obj.isWindow()) or obj.inherits("QTipLabel"):
                self._see_through(obj)
            elif isinstance(obj, QComboBox):
                if not isinstance(obj.itemDelegate(), ComboItemDelegate):
                    obj.setItemDelegate(ComboItemDelegate(obj))
                container = obj.view().window()
                if container is not obj.window():
                    self._see_through(container)  # its look is in theme.py (QComboBoxPrivateContainer)
        return False


_crash_file = None


def _log_uncaught() -> None:
    import threading

    previous = sys.excepthook

    def hook(kind, value, tb):
        ref = secrets.token_hex(2).upper()
        log.error("unexpected error, ref %s", ref, exc_info=(kind, value, tb))
        if previous is not None:
            previous(kind, value, tb)
        if isinstance(value, Exception):  # say so in the window too, in plain words with the log's reference
            _say_problem(errors.plain(value, "finish that", ref))

    sys.excepthook = hook
    threading.excepthook = lambda a: log.error(
        "unexpected error in %s", a.thread.name if a.thread else "a thread",
        exc_info=(a.exc_type, a.exc_value, a.exc_traceback),
    )  # fmt: skip


def _say_problem(text: str) -> None:
    """An error toast in the main window (it stays until closed), once whatever failed is over."""
    from PySide6.QtCore import QTimer

    app = QApplication.instance()
    for w in app.topLevelWidgets() if app is not None else []:
        if hasattr(w, "toast") and w.isVisible():
            QTimer.singleShot(0, w, lambda w=w: w.toast(text, "error"))
            return


def _crash_log() -> None:
    global _crash_file
    import faulthandler

    try:
        log_dir().mkdir(parents=True, exist_ok=True)
        _crash_file = open(log_dir() / "crash.log", "a", encoding="utf-8")  # noqa: SIM115 — open for the app's life
        faulthandler.enable(_crash_file, all_threads=True)
    except OSError:
        log.debug("no crash log", exc_info=True)


def setup_app(app: QApplication) -> None:
    """Fonts, stylesheet and look (also used by the tests and screenshots)."""
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setOrganizationName("Bodega")
    app.setApplicationVersion(__version__)
    app.setStyle("Fusion")
    icon_path = ASSETS / "icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    family = theme.load_fonts()
    f = QFont(family or app.font().family())
    f.setPixelSize(tokens.TEXT_MD)  # every size is in pixels (the stylesheet's too), so they match
    f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    app.setFont(f)
    set_appearance(app, *saved_look())
    hints = app.styleHints()
    if hasattr(hints, "colorSchemeChanged"):
        hints.colorSchemeChanged.connect(lambda _s: _system_changed(app))
    if hasattr(hints, "accessibility"):  # Increase Contrast turned on or off: redraw in it
        hints.accessibility().contrastPreferenceChanged.connect(
            lambda _p: set_appearance(app, getattr(app, "_appearance", "system"))
        )
    app._round = _RoundPopups(app)
    app.installEventFilter(app._round)


def saved_look() -> tuple[str, str]:
    """The look and accent you picked, as Bodega last saved them (Match System and its own blue at first)."""
    from bodega.core import settings
    from bodega.core.store import read_json

    saved = read_json(data_dir() / "settings.json", {})
    saved = saved if isinstance(saved, dict) else {}
    return settings.value(saved, "appearance"), settings.value(saved, "accent")


def set_appearance(app: QApplication, appearance: str, accent: str | None = None) -> str:
    """Light, dark, or "system" (follow the computer), and the accent ("" = Bodega's own; None keeps it).
    Redraws open windows."""
    app._appearance = appearance
    app._applying = True  # asking the system can itself report a change
    try:
        look = theme.apply(app, appearance, data_dir() / "ui", accent)
    finally:
        app._applying = False
    for w in app.topLevelWidgets():
        if hasattr(w, "look_changed"):
            w.look_changed()
    return look


def _system_changed(app: QApplication) -> None:
    if getattr(app, "_appearance", "system") == "system" and not getattr(app, "_applying", False):
        set_appearance(app, "system")


def _smoke(app: QApplication) -> int:
    """Used by the build pipeline: open the window on a throwaway data folder with sample gear, a package
    and a rental, save the rental agreement as a PDF, check the file, quit."""
    from bodega.core import sample
    from bodega.core.store import Library
    from bodega.doc import export
    from bodega.ui.window.main_window import MainWindow

    tmp = Path(tempfile.mkdtemp(prefix="bodega-smoke-"))
    use_data_dir(tmp)
    lib = sample.fill(Library(tmp).load())
    w = MainWindow(lib)
    w.show()
    w.go("rentals")
    w.page_ctx = ("rental", next(iter(lib.rentals)))
    out = tmp / "smoke.pdf"
    export.to_pdf(w.page_list(), out)
    ok = out.exists() and out.stat().st_size > 1000 and out.read_bytes().startswith(b"%PDF")
    try:
        import openpyxl  # noqa: F401 — spreadsheets must import in the packaged app
    except ImportError:
        ok = False
    print(
        f"smoke: Bodega {__version__}, PDF {'ok' if ok else 'MISSING'} ({out.stat().st_size if out.exists() else 0} bytes)",
        flush=True,
    )
    QTimer.singleShot(1200, app.quit)
    code = app.exec()
    return code if ok else 3


def _ask_to_sign_in(window) -> None:
    """Once accounts exist and are required (services/account.py REQUIRED), ask at launch."""
    from bodega.services import account

    if account.REQUIRED and account.service().connected and account.current() is None:
        from bodega.ui.dialogs.account import SignInDialog

        QTimer.singleShot(0, lambda: SignInDialog(window).exec())


def main() -> int:
    if sys.platform == "win32":
        try:  # own taskbar icon instead of python's
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Bodega.Bodega")
        except Exception:
            log.debug("couldn't set the Windows app id", exc_info=True)
    smoke = "--smoke-test" in sys.argv
    if smoke:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    setup_logging()
    log.info("Bodega %s starting (%s)", __version__, sys.platform)
    _crash_log()
    _log_uncaught()
    app = QApplication(sys.argv)
    if not smoke and _wake_running():
        return 0  # Bodega is already open: it came to the front
    setup_app(app)
    if smoke:
        return _smoke(app)

    from bodega.ui.window.main_window import MainWindow

    w = MainWindow()
    app.aboutToQuit.connect(w.shutdown)
    app._server = _listen(w)
    w.show()
    w.raise_()
    _ask_to_sign_in(w)
    code = app.exec()
    if app.property("exit_now"):  # a download was still running: leave without waiting for it
        logging.shutdown()
        os._exit(code)
    return code


if __name__ == "__main__":
    sys.exit(main())
