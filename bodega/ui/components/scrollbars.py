"""Scroll bars as the standard draws them (§6.2, I-09): where the system shows its scroll bars only while scrolling
(as a Mac, Windows 11 and GNOME do unless told otherwise), they lie over the content and show only while it
scrolls, while the pointer is on one, or for a moment when a list first shows (so it's plain it scrolls): a thin
rounded thumb, no track, gone SCROLL_HIDE_MS after. Where the system is set to always show them
(access.always_show_scroll_bars), the same thumb stays, with its room kept beside the content (SCROLL_GUTTER).

Bodega draws its controls with Fusion everywhere; this style is Fusion with these scroll bars (app.py sets it).
Nothing about them is in the stylesheet, so the stylesheet leaves their drawing here."""

from __future__ import annotations

import shiboken6
from PySide6.QtCore import QEvent, QObject, QRect, Qt, QTimer
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QProxyStyle, QScrollBar, QStyle, QStyleOptionSlider

from bodega.ui.components import access
from bodega.ui.style import theme, tokens

CC = QStyle.ComplexControl
SC = QStyle.SubControl
PM = QStyle.PixelMetric


def overlay() -> bool:
    """Scroll bars lie over the content and show only while scrolling (else: always, with room kept)."""
    return not access.always_show_scroll_bars()


class _Shown(QObject):
    """When one overlay scroll bar shows: while it scrolls, while the pointer's on it, and for a moment after."""

    def __init__(self, bar: QScrollBar):
        super().__init__(bar)
        self.bar = bar
        self.on = False
        self.hovered = False
        self.timer = QTimer(self, singleShot=True, interval=tokens.SCROLL_HIDE_MS, timeout=self._hide)
        bar.valueChanged.connect(lambda _v: self.flash())
        bar.sliderPressed.connect(self.flash)
        bar.installEventFilter(self)

    @staticmethod
    def of(bar: QScrollBar) -> _Shown:
        found = bar.findChild(_Shown, options=Qt.FindChildOption.FindDirectChildrenOnly)
        return found if found is not None else _Shown(bar)

    def flash(self) -> None:
        if not self.on:
            self.on = True
            self.bar.update()
        self.timer.start()

    def _hide(self) -> None:
        if self.hovered or self.bar.isSliderDown():
            self.timer.start()  # (still in use: it stays)
            return
        self.on = False
        if shiboken6.isValid(self.bar):
            self.bar.update()

    def eventFilter(self, obj, ev):
        t = ev.type()
        if t == QEvent.Type.Enter:
            self.hovered = True
            self.flash()
        elif t == QEvent.Type.Leave:
            self.hovered = False
            self.timer.start()
        elif t == QEvent.Type.Show:
            self.flash()  # (a list that scrolls says so as it shows)
        return False


class Style(QProxyStyle):
    """Fusion, with the scroll bars above."""

    def styleHint(self, hint, opt=None, w=None, ret=None):
        if hint == QStyle.StyleHint.SH_ScrollBar_Transient:
            return int(overlay())
        return super().styleHint(hint, opt, w, ret)

    def pixelMetric(self, m, opt=None, w=None):
        if m == PM.PM_ScrollBarExtent:
            return tokens.SCROLL_W
        if m == PM.PM_ScrollView_ScrollBarOverlap:
            return tokens.SCROLL_W if overlay() else 0  # (over the content: no room kept)
        if m == PM.PM_ScrollBarSliderMin:
            return tokens.SCROLL_MIN
        return super().pixelMetric(m, opt, w)

    def subControlRect(self, cc, opt, sc, w=None):
        if cc != CC.CC_ScrollBar or not isinstance(opt, QStyleOptionSlider):
            return super().subControlRect(cc, opt, sc, w)
        r = opt.rect
        across = opt.orientation == Qt.Orientation.Horizontal
        if sc in (SC.SC_ScrollBarAddLine, SC.SC_ScrollBarSubLine, SC.SC_ScrollBarFirst, SC.SC_ScrollBarLast):
            return QRect()  # (no arrows)
        if sc == SC.SC_ScrollBarGroove:
            return QRect(r)
        length = r.width() if across else r.height()
        span = opt.maximum - opt.minimum
        handle = length if span <= 0 else max(tokens.SCROLL_MIN, length * opt.pageStep // (span + opt.pageStep))
        handle = min(handle, length)
        at = QStyle.sliderPositionFromValue(
            opt.minimum, opt.maximum, opt.sliderPosition, length - handle, opt.upsideDown
        )
        if across:
            slider = QRect(r.left() + at, r.top(), handle, r.height())
            before = QRect(r.left(), r.top(), at, r.height())
            after = QRect(slider.right() + 1, r.top(), r.right() - slider.right(), r.height())
        else:
            slider = QRect(r.left(), r.top() + at, r.width(), handle)
            before = QRect(r.left(), r.top(), r.width(), at)
            after = QRect(r.left(), slider.bottom() + 1, r.width(), r.bottom() - slider.bottom())
        return {SC.SC_ScrollBarSlider: slider, SC.SC_ScrollBarSubPage: before, SC.SC_ScrollBarAddPage: after}.get(
            sc, QRect()
        )

    def drawComplexControl(self, cc, opt, p, w=None):
        if cc != CC.CC_ScrollBar or not isinstance(opt, QStyleOptionSlider):
            super().drawComplexControl(cc, opt, p, w)
            return
        if opt.maximum <= opt.minimum or not opt.state & QStyle.StateFlag.State_Enabled:
            return  # nothing to scroll: nothing drawn
        if overlay() and isinstance(w, QScrollBar) and not _Shown.of(w).on:
            return  # out of sight until it scrolls
        thumb = self.subControlRect(cc, opt, SC.SC_ScrollBarSlider, w)
        i = tokens.SCROLL_INSET
        thumb = thumb.adjusted(i, i, -i, -i)
        lit = bool(opt.state & QStyle.StateFlag.State_MouseOver) or bool(opt.state & QStyle.StateFlag.State_Sunken)
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(theme.qcolor(tokens.BORDER_HOVER if lit else tokens.BORDER_STRONG))
        radius = min(thumb.width(), thumb.height()) / 2
        p.drawRoundedRect(thumb, radius, radius)
        p.restore()
