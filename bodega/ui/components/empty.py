"""What shows where a table would be when there's nothing in it yet (the standard's 4.11 and G.10.9): a title of a
few words, one short line and the one button that starts it ("No Gear Yet" · Import Spreadsheet…). A spreadsheet
dropped anywhere on the gear page comes in too; the page lights up while one is dragged over it."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QEvent, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QLabel, QPushButton, QWidget

from bodega.ui.components.widgets import hint, primary_button, vbox
from bodega.ui.style import theme, tokens

SHEETS = (".xlsx", ".xlsm", ".csv")  # what the Import page reads


def sheet_in(mime) -> Path | None:
    """The spreadsheet being dragged in, if it is one (the first file only)."""
    urls = mime.urls() if mime.hasUrls() else []
    if not urls or not urls[0].isLocalFile():
        return None
    path = Path(urls[0].toLocalFile())
    return path if path.suffix.lower() in SHEETS else None


class EmptyPage(QWidget):
    """The empty page. `show_for()` sets its words and its button; `dropped` is a spreadsheet let go on it (only
    while the page takes them).

    What the button starts runs just after its click is over: New Rental with no profile yet opens Settings, and the
    page may change before that window closes."""

    dropped = Signal(Path)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._action: Callable | None = None
        self._sheets = False  # a spreadsheet dropped here is imported
        self._hot = False  # one is being dragged over it
        pad_top, pad_x, pad_bottom = tokens.EMPTY_PAD
        lay = vbox(self, (pad_x, pad_top, pad_x, pad_bottom), 0)
        lay.addStretch(2)
        self.title = QLabel()
        self.title.setObjectName("EmptyTitle")
        self.line = hint("")
        for w in (self.title, self.line):
            w.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(w)
            if w is self.title:
                lay.addSpacing(tokens.SPACE_1)
        lay.addSpacing(tokens.SPACE_4)
        self.button = primary_button()
        self.button.clicked.connect(lambda: QTimer.singleShot(0, self, self._go))  # once the click is over
        lay.addWidget(self.button, 0, Qt.AlignmentFlag.AlignHCenter)
        lay.addStretch(3)

    def show_for(self, title: str, line: str, button: str, action: Callable, sheets: bool = False) -> None:
        """Its title, its line, its one button and what that does; `sheets`: a spreadsheet dropped here comes in."""
        self.title.setText(title)
        self.line.setText(line)
        self.button.setText(button)
        self._action = action
        self._sheets = sheets

    def _go(self) -> None:
        if self._action is not None:
            self._action()

    # A spreadsheet dragged in from the Finder or Explorer lights the page and is imported
    def _light(self, on: bool) -> None:
        if self._hot != on:
            self._hot = on
            self.update()

    def paintEvent(self, _e):
        if not self._hot:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(tokens.SPACE_3, tokens.SPACE_3, -tokens.SPACE_3, -tokens.SPACE_3)
        path = QPainterPath()
        path.addRoundedRect(r, tokens.RADIUS_LG, tokens.RADIUS_LG)
        p.fillPath(path, theme.qcolor(tokens.ACCENT_TINT))
        p.setPen(QPen(theme.qcolor(tokens.ACCENT_EDGE), 1.5))
        p.drawPath(path)
        p.end()

    def dragEnterEvent(self, e):
        if self._sheets and sheet_in(e.mimeData()) is not None:
            e.acceptProposedAction()
            self._light(True)
        else:
            e.ignore()

    def dragLeaveEvent(self, e):
        self._light(False)

    def dropEvent(self, e):
        self._light(False)
        path = sheet_in(e.mimeData()) if self._sheets else None
        if path is None:
            e.ignore()
            return
        e.acceptProposedAction()
        QTimer.singleShot(0, self, lambda: self.dropped.emit(path))  # after the drag ends: the Import page waits


class NoResults(QWidget):
    """Over a table whose every row a search or a filter hides: "No Results", what hid them, and the way back
    (Clear Search or Clear Filters). It sits on the table it covers and is hidden, never thrown away, when the
    rows come back (its button may still be finishing its click)."""

    clear_wanted = Signal(str)  # "search" or "filters"

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("NoResults")
        self._what = "search"
        lay = vbox(self, tokens.SPACE_5, tokens.SPACE_2)
        lay.addStretch(2)
        self.title = QLabel("No Results")
        self.title.setObjectName("EmptyTitle")
        self.detail = hint("")
        self.clear = QPushButton("Clear Search")
        self.clear.clicked.connect(lambda: QTimer.singleShot(0, self, lambda: self.clear_wanted.emit(self._what)))
        for w in (self.title, self.detail):
            w.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(w)
        lay.addSpacing(tokens.SPACE_2)
        lay.addWidget(self.clear, 0, Qt.AlignmentFlag.AlignHCenter)
        lay.addStretch(3)
        self.hide()

    def show_over(self, table, text: str) -> None:
        """Cover `table` (a QAbstractItemView): nothing matches `text`, or (no text) the filters."""
        area = table.viewport()
        if self.parent() is not area:
            if self.parent() is not None:
                self.parent().removeEventFilter(self)
            self.setParent(area)
            area.installEventFilter(self)
        searched = text.strip()
        self._what = "search" if searched else "filters"
        self.detail.setText(
            f"Nothing matches \u201c{searched}\u201d." if searched else "Nothing matches these filters."
        )
        self.clear.setText("Clear Search" if searched else "Clear Filters")
        self.setGeometry(area.rect())
        self.show()
        self.raise_()

    def eventFilter(self, obj, e):
        if e.type() == QEvent.Type.Resize and obj is self.parent():
            self.setGeometry(obj.rect())
        return False
