"""Sheets (the standard's 4.9 and G.18): every dialog Bodega makes shows over its window, never as a window of its own.

The window behind is blurred and dimmed (a still picture of it, taken as the sheet opens, so what's underneath stays
exactly as it was), the dialog sits on a rounded, raised panel in the middle, a ✕ circle at the panel's top trailing
corner closes it as Esc does, and a click on the dimmed area closes it too, unless closing would lose work. Nothing
under the dimmed area ever gets that click. The scrim fades in and the panel rises into place (under Reduce Motion
it's simply there). Focus goes to the dialog and comes back to what opened it when it closes (Qt's own modal rule).

It's done to each dialog as it is: as it's made it calls prepare() and becomes frameless; when it shows, it takes its
window's place and size, and its own layout's margins are widened to the panel's edges, so the dialog keeps its
own padding inside the panel and nothing in it is rebuilt. A dialog says how it wants to be shown with class
attributes:

    SHEET = False            a window of its own (the page window), or one that draws its own (Search Everything)
    SHEET_KIND = "window"    the window over the app (Settings): wider padding, a stronger blur, glass corners
    SHEET_OUTSIDE = False    a click outside doesn't close it (it would lose work: an import being set up)
    SHEET_CLOSE = False      no ✕ (an alert: Cancel is its way out)
    SHEET_PANEL = False      it draws its own card (an alert)
    SHEET_AT = "third"       a little above the middle, like a Mac's alert (else the middle)

On Wayland a window can't be placed over another, so dialogs stay windows of their own there.
"""

from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QMargins,
    QObject,
    QPoint,
    QPropertyAnimation,
    QRect,
    QRectF,
    QSize,
    Qt,
    QVariantAnimation,
)
from PySide6.QtGui import QGuiApplication, QImage, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QGraphicsBlurEffect,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QLabel,
    QWidget,
)

from bodega.ui.components import access
from bodega.ui.components.glass import paint_shadow
from bodega.ui.components.widgets import circle_button
from bodega.ui.style import theme, tokens

TITLES = ("DialogTitle", "PageTitle")  # the ✕ sits level with the first of these that shows


def still(win: QWidget, blur: int) -> QPixmap:
    """A still picture of `win`, blurred `blur` points (at one pixel a point: it's soft anyway, and quick)."""
    shot = win.grab()
    size = win.size()
    img = shot.toImage().scaled(size, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
    if blur <= 0:
        return QPixmap.fromImage(img)
    scene = QGraphicsScene()
    item = QGraphicsPixmapItem(QPixmap.fromImage(img))
    effect = QGraphicsBlurEffect()
    effect.setBlurRadius(blur * 2)  # (Qt's radius is about twice a CSS blur)
    effect.setBlurHints(QGraphicsBlurEffect.BlurHint.QualityHint)
    item.setGraphicsEffect(effect)
    scene.addItem(item)
    out = QImage(size, QImage.Format.Format_ARGB32_Premultiplied)
    out.fill(theme.qcolor(tokens.BG))  # (the blur's edges fade into the window's own color, not into nothing)
    p = QPainter(out)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    scene.render(p, QRectF(0, 0, size.width(), size.height()), QRectF(0, 0, size.width(), size.height()))
    p.end()
    scene.removeItem(item)
    return QPixmap.fromImage(out)


def wanted(d: QDialog) -> bool:
    """`d` is one of Bodega's dialogs that shows as a sheet."""
    import shiboken6

    return (
        getattr(d, "SHEET", True)
        and d.isWindow()
        and d.parentWidget() is not None
        and shiboken6.createdByPython(d)
        and not QGuiApplication.platformName().startswith("wayland")
    )


def prepare(d: QDialog) -> None:
    """Every dialog calls this as it's made (before it's shown): frameless, with no background of its own (the
    panel's is drawn under it), and watched so it can take its window's place as it shows."""
    if d.property("sheet") or not wanted(d):
        return
    d.setProperty("sheet", True)
    d.setWindowFlags(d.windowFlags() | Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
    d.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)  # (QDialog[sheet="true"] in theme.py)
    Sheet(d)


class _Backdrop(QWidget):
    """Under the dialog's own widgets: the blurred window, the scrim, and the panel's shadow and surface."""

    def __init__(self, sheet: Sheet):
        super().__init__(sheet.d)
        self.sheet = sheet
        self._pressed = False

    def paintEvent(self, _e):
        s = self.sheet
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if s.picture is not None:
            p.drawPixmap(self.rect(), s.picture)
        if not s.alone:
            p.fillRect(self.rect(), theme.qcolor(tokens.SCRIM))
        if s.panel_drawn and not s.panel.isEmpty():
            r = QRectF(s.panel)
            rad = s.radius
            paint_shadow(p, r, rad, tokens.SHEET_SHADOW)
            path = QPainterPath()
            path.addRoundedRect(r, rad, rad)
            # (a dialog's own surface, which its buttons and fields were made to sit on)
            p.fillPath(path, theme.qcolor(tokens.BG if s.kind == "window" else tokens.PANEL))
            p.setPen(QPen(theme.qcolor(tokens.SHEET_RING), 1))
            p.drawPath(path)
        p.end()

    def mousePressEvent(self, e):
        self._pressed = not self.sheet.panel.contains(e.position().toPoint())
        e.accept()  # (nothing under the scrim ever gets the click)

    def mouseReleaseEvent(self, e):
        outside = self._pressed and not self.sheet.panel.contains(e.position().toPoint())
        self._pressed = False
        e.accept()
        if outside:
            self.sheet.outside()


class Sheet(QObject):
    """One dialog shown as a sheet (see the module's words); kept as the dialog's child."""

    def __init__(self, d: QDialog):
        super().__init__(d)
        self.d = d
        self.kind = getattr(d, "SHEET_KIND", "sheet")
        self.radius = tokens.GLASS_R if self.kind == "window" else tokens.RADIUS_XL
        self.panel_drawn = getattr(d, "SHEET_PANEL", True)
        self.picture: QPixmap | None = None
        self.panel = QRect()
        self.want = QSize()
        self.margins: QMargins | None = None  # the dialog's own padding
        self.lift = 0.0  # how far below its place it is, rising in
        self.alone = False  # its window isn't showing: just the panel, on its own
        self.win: QWidget | None = None  # the window it's over (followed if it moves)
        self.came_from: QWidget | None = None  # what had the focus before it opened (it gets it back)
        self._placing = False
        self._anims: list = []
        self.backdrop = _Backdrop(self)
        self.backdrop.hide()
        self.close_btn = None
        if getattr(d, "SHEET_CLOSE", True):
            self.close_btn = circle_button("x", "Close")
            self.close_btn.setParent(d)
            self.close_btn.setAccessibleName("Close")
            self.close_btn.clicked.connect(d.reject)
            self.close_btn.hide()
        d.installEventFilter(self)

    # Its place
    def _window(self) -> QWidget | None:
        parent = self.d.parentWidget()
        return parent.window() if parent is not None else None

    def open(self) -> None:
        d, win = self.d, self._window()
        if win is None or not d.isWindow():
            return
        had = QApplication.focusWidget()
        self.came_from = had if had is not None and not d.isAncestorOf(had) else None
        if self.margins is None:  # the first time: its own padding, and the size it chose (or Qt gave it)
            lay = d.layout()
            self.margins = lay.contentsMargins() if lay is not None else QMargins()
            self.want = d.size()
            d.setMinimumSize(0, 0)
            d.setMaximumSize(16777215, 16777215)
            if self.close_btn is not None:
                for label in d.findChildren(QLabel):
                    if label.objectName() in TITLES:  # (a long title never runs under the ✕)
                        label.setContentsMargins(0, 0, tokens.CONTROL_H + tokens.SPACE_2, 0)
        if self.win is not win:
            if self.win is not None:
                self.win.removeEventFilter(self)
            self.win = win
            win.installEventFilter(self)  # (it follows the window if it moves)
        self.alone = not win.isVisible() or win.isMinimized()
        if self.alone:  # nothing to sit over (the window isn't showing yet): the panel alone, mid-screen
            self.picture = None
            screen = (win.screen() or QGuiApplication.primaryScreen()).availableGeometry()
            d.setGeometry(
                QRect(QPoint(0, 0), self.want).translated(screen.center() - QRect(QPoint(), self.want).center())
            )
        else:
            over_sheet = bool(win.property("sheet"))
            blur = 0 if over_sheet else tokens.WINDOW_BLUR if self.kind == "window" else tokens.SHEET_BLUR
            self.picture = still(win, blur)  # (over another sheet: dimmed, never blurred twice)
            d.setGeometry(QRect(win.mapToGlobal(QPoint(0, 0)), win.size()))
        self.backdrop.show()
        self.backdrop.lower()
        if self.close_btn is not None:
            self.close_btn.show()
        self._come_in()
        self.place()

    def place(self) -> None:
        """Size the panel to the dialog's own (more if what's in it grew) and put it in the middle."""
        d, lay = self.d, self.d.layout()
        if self._placing or self.margins is None or lay is None:
            return
        self._placing = True
        try:
            W, H = d.width(), d.height()
            o, now = self.margins, lay.contentsMargins()
            if self.alone:
                self.panel = QRect(0, 0, W, H)
                if now != o:
                    lay.setContentsMargins(o)
                self.backdrop.setGeometry(d.rect())
                self._place_close()
                return
            content = lay.sizeHint() - QSize(now.left() + now.right(), now.top() + now.bottom())
            need = QSize(content.width() + o.left() + o.right(), content.height() + o.top() + o.bottom())
            pad_x, pad_y = (tokens.WINDOW_PAD,) * 2 if self.kind == "window" else tokens.SHEET_PAD
            pw = min(max(self.want.width(), 0), W - 2 * pad_x)
            ph = min(max(self.want.height(), need.height()), H - 2 * pad_y)
            x = (W - pw) // 2
            y = (H - ph) // 3 if getattr(d, "SHEET_AT", "") == "third" else (H - ph) // 2
            y = max(pad_y if ph <= H - 2 * pad_y else 0, y) + round(self.lift)
            self.panel = QRect(x, y, pw, ph)
            m = QMargins(x + o.left(), y + o.top(), W - x - pw + o.right(), H - y - ph + o.bottom())
            if m != now:
                lay.setContentsMargins(m)
                lay.activate()
            self.backdrop.setGeometry(d.rect())
            self._place_close()
            self.backdrop.update()
        finally:
            self._placing = False

    def _place_close(self) -> None:
        b = self.close_btn
        if b is None:
            return
        size = tokens.CONTROL_H
        b.setFixedSize(size, size)
        inset = tokens.SHEET_CLOSE_INSET
        title = next(
            (t for t in self.d.findChildren(QLabel) if t.objectName() in TITLES and t.isVisibleTo(self.d)), None
        )
        right = self.panel.right() + 1 - inset
        if title is not None and title.height() > 1:
            at = title.mapTo(self.d, QPoint(title.width(), title.height() // 2))
            mid = at.y()
            if self.kind == "window":  # (Settings: its trailing edge on the cards' edge, as the title's is)
                right = at.x()
        else:
            mid = self.panel.top() + tokens.SPACE_4 + size // 2
        b.move(right - size, mid - size // 2)
        b.raise_()

    # Coming in
    def _come_in(self) -> None:
        for a in self._anims:
            a.stop()
        self._anims = []
        fade, rise = access.duration(tokens.SHEET_FADE_MS), access.duration(tokens.SHEET_RISE_MS)
        if not fade:
            self.d.setWindowOpacity(1.0)
            self.lift = 0.0
            return
        a = QPropertyAnimation(self.d, b"windowOpacity", self)
        a.setStartValue(0.0)
        a.setEndValue(1.0)
        a.setDuration(fade)
        b = QVariantAnimation(self, startValue=float(tokens.SHEET_RISE), endValue=0.0, duration=rise)
        b.setEasingCurve(QEasingCurve.Type.OutCubic)
        b.valueChanged.connect(self._rise)
        self.lift = float(tokens.SHEET_RISE)
        self._anims = [a, b]
        a.start()
        b.start()

    def _rise(self, v) -> None:
        self.lift = float(v)
        self.place()

    # Going
    def _give_back(self) -> None:
        """The focus goes back to what had it before (the standard's 4.9)."""
        import shiboken6

        w, self.came_from = self.came_from, None
        if w is not None and shiboken6.isValid(w) and w.isVisible():
            w.window().activateWindow()
            w.setFocus(Qt.FocusReason.OtherFocusReason)

    def outside(self) -> None:
        """A click on the dimmed area: it closes, unless that would lose work (then nothing happens)."""
        if getattr(self.d, "SHEET_OUTSIDE", True):
            self.d.reject()

    def eventFilter(self, obj, e):
        if obj is self.win and self.d.isVisible() and not self.alone:
            if e.type() in (QEvent.Type.Move, QEvent.Type.Resize):  # the window moved: so does all of it
                self.d.setGeometry(QRect(obj.mapToGlobal(QPoint(0, 0)), obj.size()))
            return False
        if obj is self.d:
            t = e.type()
            if t == QEvent.Type.Show:
                self.open()
            elif t in (QEvent.Type.LayoutRequest, QEvent.Type.Resize) and self.d.isVisible():
                self.place()
            elif t == QEvent.Type.Hide:
                for a in self._anims:
                    a.stop()
                self._anims = []
                self.lift = 0.0
                self._give_back()
        return False
