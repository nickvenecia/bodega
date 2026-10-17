"""Scroll bars (the standard's §6.2, I-09): where the system shows them only while scrolling, they lie over the content
(no room kept) and are drawn only while it scrolls, then gone a moment after; where the system says Always, the same
thumb stays with its room kept. (overlay() asks access.always_show_scroll_bars, which BODEGA_SCROLL_BARS stands in
for.)"""

from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel

from bodega.ui.components import scrollbars
from bodega.ui.components.widgets import FitScroll
from bodega.ui.style import tokens
from tests.ui import wait_for


def _area():
    area = FitScroll()
    body = QLabel("\n".join(f"Row {n}" for n in range(200)))
    area.setWidget(body)
    area.resize(300, 200)
    area.show()
    QTest.qWait(30)
    return area


def _thumb_drawn(area) -> bool:
    """Any pixel in the scroll bar's strip that isn't the content's own background."""
    img = area.grab().toImage()
    bar = area.verticalScrollBar()
    x0 = bar.mapTo(area, bar.rect().topLeft()).x()
    under = QColor(img.pixel(x0 - tokens.SPACE_4, img.height() // 2))
    return any(
        QColor(img.pixel(x, y)) != under
        for x in range(x0, min(img.width(), x0 + tokens.SCROLL_W))
        for y in range(0, img.height(), 4)
    )


def test_overlay_bars_lie_over_the_content_and_show_only_while_it_scrolls(qapp, monkeypatch):
    monkeypatch.setenv("BODEGA_SCROLL_BARS", "overlay")
    area = _area()
    assert area.viewport().width() == area.width()  # no room kept: it lies over the content
    bar = area.verticalScrollBar()
    wait_for(lambda: not _thumb_drawn(area), tokens.SCROLL_HIDE_MS + 1500)  # (past the moment it showed at first)
    assert not _thumb_drawn(area)  # out of sight at rest
    bar.setValue(bar.value() + 40)  # scrolling
    QApplication.processEvents()
    assert _thumb_drawn(area)
    wait_for(lambda: not _thumb_drawn(area), tokens.SCROLL_HIDE_MS + 1500)
    assert not _thumb_drawn(area)  # gone a moment after
    area.close()


def test_always_keeps_the_thumb_and_its_room(qapp, monkeypatch):
    monkeypatch.setenv("BODEGA_SCROLL_BARS", "always")
    area = _area()
    area.setVerticalScrollBarPolicy(area.verticalScrollBarPolicy())  # (the layout asks the style again)
    area.resize(301, 200)
    QTest.qWait(30)
    assert area.viewport().width() == area.width() - tokens.SCROLL_W  # its room kept beside the content
    assert _thumb_drawn(area)  # there at rest
    area.close()


def test_the_bars_have_no_arrows_and_a_thumb_of_at_least_its_length(qapp):
    from PySide6.QtWidgets import QScrollBar, QStyle

    bar = QScrollBar()
    bar.setRange(0, 100_000)
    bar.setPageStep(10)
    bar.resize(tokens.SCROLL_W, 300)
    opt = scrollbars.QStyleOptionSlider()
    bar.initStyleOption(opt)
    style = bar.style()
    arrows = style.subControlRect(QStyle.ComplexControl.CC_ScrollBar, opt, QStyle.SubControl.SC_ScrollBarAddLine, bar)
    thumb = style.subControlRect(QStyle.ComplexControl.CC_ScrollBar, opt, QStyle.SubControl.SC_ScrollBarSlider, bar)
    assert arrows.isEmpty() and thumb.height() >= tokens.SCROLL_MIN
