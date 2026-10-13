"""What shows where a table would be when there's nothing in it yet: the place's icon in a soft circle, a
headline, and the ways to start as tiles. Gear starts three ways (manually, a spreadsheet, a Google Sheet), and a
spreadsheet dropped anywhere on the page comes in too; kits and rentals start one way."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QFrame, QLabel, QWidget

from bodega.ui.components.widgets import IconLabel, hbox, repolish, vbox
from bodega.ui.style import theme, tokens

SHEETS = (".xlsx", ".xlsm", ".csv")  # what the Import window reads


def sheet_in(mime) -> Path | None:
    """The spreadsheet being dragged in, if it is one (the first file only)."""
    urls = mime.urls() if mime.hasUrls() else []
    if not urls or not urls[0].isLocalFile():
        return None
    path = Path(urls[0].toLocalFile())
    return path if path.suffix.lower() in SHEETS else None


def _badge(name: str, size: int, icon: int) -> QFrame:
    """An icon in a circle of the accent's tint."""
    badge = QFrame()
    badge.setObjectName("StartBadge")
    badge.setFixedSize(size, size)
    badge.setProperty("big", size == tokens.EMPTY_BADGE)
    lay = vbox(badge)
    lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
    badge.icon = IconLabel(name, "ACCENT", icon)
    lay.addWidget(badge.icon)
    return badge


class StartTile(QFrame):
    """One way to start: an icon, what it is, a few words. A click, Space or Return picks it."""

    clicked = Signal()

    def __init__(self, icon: str, title: str, detail: str, tip: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("StartTile")
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedWidth(tokens.START_TILE_W)
        if tip:
            self.setToolTip(theme.plain_tip(tip))
        lay = vbox(self, (tokens.SPACE_4, tokens.SPACE_5, tokens.SPACE_4, tokens.SPACE_5), tokens.SPACE_1)
        lay.addWidget(_badge(icon, tokens.START_BADGE, tokens.ICON_LG), 0, Qt.AlignmentFlag.AlignHCenter)
        lay.addSpacing(tokens.SPACE_2)
        name = QLabel(title)
        name.setObjectName("StartTitle")
        sub = QLabel(detail)
        sub.setObjectName("StartDetail")
        for w in (name, sub):
            w.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(w)

    def set_hot(self, on: bool) -> None:
        """Lit while a spreadsheet is dragged over the page."""
        if self.property("hot") is not on:
            self.setProperty("hot", on)
            repolish(self)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            e.accept()  # the release comes back here
        else:
            super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self.rect().contains(e.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(e)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.clicked.emit()
            return
        super().keyPressEvent(e)


class EmptyPage(QWidget):
    """The empty page. `show_for()` sets what it says and offers; `dropped` is a spreadsheet let go on it
    (only while the page takes them)."""

    dropped = Signal(Path)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._key: tuple = ()
        self._slots: list[Callable] = []
        self._sheet_tile: int | None = None  # the tile that lights up while a spreadsheet is dragged in
        self.tiles: list[StartTile] = []
        lay = vbox(self, tokens.SPACE_5, 0)
        lay.addStretch(2)
        self.badge = _badge("", tokens.EMPTY_BADGE, tokens.ICON_XL)
        lay.addWidget(self.badge, 0, Qt.AlignmentFlag.AlignHCenter)
        lay.addSpacing(tokens.SPACE_4)
        self.title = QLabel()
        self.title.setObjectName("EmptyTitle")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.title)
        lay.addSpacing(tokens.SPACE_5)
        self.tile_row = hbox(spacing=tokens.SPACE_3)
        lay.addLayout(self.tile_row)
        lay.addStretch(3)

    def show_for(
        self,
        icon: str,
        title: str,
        tiles: tuple[tuple[str, str, str, str, Callable], ...],
        sheet_tile: int | None = None,
    ) -> None:
        """The place's icon and headline, then its tiles (icon, title, detail, tooltip, what it does).
        `sheet_tile`: a spreadsheet dropped here is imported, and that tile lights up while it's dragged in."""
        self._sheet_tile = sheet_tile
        self.title.setText(title)
        self.badge.icon.set_icon(icon)
        self._slots = [t[4] for t in tiles]
        key = tuple(t[:4] for t in tiles)
        if key == self._key:
            return
        self._key = key
        while self.tile_row.count():
            w = self.tile_row.takeAt(0).widget()
            if w is not None:
                w.deleteLater()
        self.tiles = []
        self.tile_row.addStretch(1)
        for n, (name, label, detail, tip, _slot) in enumerate(tiles):
            tile = StartTile(name, label, detail, tip)
            tile.clicked.connect(lambda n=n: self._slots[n]())
            self.tile_row.addWidget(tile)
            self.tiles.append(tile)
        self.tile_row.addStretch(1)

    # ---- a spreadsheet dragged in from the Finder or Explorer lights its tile and is imported
    def _light(self, on: bool) -> None:
        if self._sheet_tile is not None and self._sheet_tile < len(self.tiles):
            self.tiles[self._sheet_tile].set_hot(on)

    def dragEnterEvent(self, e):
        if self._sheet_tile is not None and sheet_in(e.mimeData()) is not None:
            e.acceptProposedAction()
            self._light(True)
        else:
            e.ignore()

    def dragLeaveEvent(self, e):
        self._light(False)

    def dropEvent(self, e):
        self._light(False)
        path = sheet_in(e.mimeData()) if self._sheet_tile is not None else None
        if path is None:
            e.ignore()
            return
        e.acceptProposedAction()
        QTimer.singleShot(0, lambda: self.dropped.emit(path))  # after the drag ends: the Import window waits
