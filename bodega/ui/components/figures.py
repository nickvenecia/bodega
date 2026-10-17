"""The figure row above a list (the standard's 4.3, G.10.5): a tile per figure (core/figures.py), its number large,
its name under it. A tile that's a slice of the list is a button: pressed, it shows only that slice and stays marked
on; pressed again, it lets go."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QLabel, QLayout, QSizePolicy, QWidget

from bodega.core.figures import Figure
from bodega.ui.components.widgets import by_keyboard, hbox, repolish, vbox
from bodega.ui.style import theme, tokens


class FigureTile(QFrame):
    pressed = Signal(str)  # its slice

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("FigureTile")
        lay = vbox(self, tokens.FIGURE_PAD, tokens.SPACE_0_5)
        self.value = QLabel()
        self.value.setObjectName("FigureValue")
        theme.use_tabular(self.value)  # (its size and weight: the style's #FigureValue)
        self.label = QLabel()
        self.label.setObjectName("FigureLabel")
        lay.addWidget(self.value)
        lay.addWidget(self.label)
        self.slice = ""
        self.shadow = QGraphicsDropShadowEffect(self)  # (shadow-card)
        self.shadow.setBlurRadius(tokens.CARD_SHADOW_BLUR)
        self.shadow.setOffset(0, tokens.CARD_SHADOW_DROP)
        self.setGraphicsEffect(self.shadow)

    def show_figure(self, f: Figure, on: bool) -> None:
        self.slice = f.slice
        self.shadow.setColor(theme.qcolor(tokens.CARD_SHADOW))  # (light or dark, as it is now)
        self.value.setText(f.value)
        self.label.setText(f.label)
        for w, key, v in ((self.value, "tone", f.tone), (self, "slice", bool(f.slice)), (self, "on", on)):
            if w.property(key) != v:
                w.setProperty(key, v)
                repolish(w)
        self.setCursor(Qt.CursorShape.PointingHandCursor if f.slice else Qt.CursorShape.ArrowCursor)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus if f.slice else Qt.FocusPolicy.NoFocus)
        self.setAccessibleName(f"{f.label}: {f.value}")
        self.setToolTip(theme.plain_tip(("Show all again" if on else f"Show only {f.label}") if f.slice else ""))

    def mousePressEvent(self, e) -> None:
        if self.slice and e.button() == Qt.MouseButton.LeftButton:
            QTimer.singleShot(0, self, lambda: self.pressed.emit(self.slice))  # once the click is over
            e.accept()
            return
        super().mousePressEvent(e)

    def keyPressEvent(self, e) -> None:
        if not (self.slice and by_keyboard(self, lambda: self.pressed.emit(self.slice), e)):
            super().keyPressEvent(e)


class FigureRow(QWidget):
    """Tiles side by side (FIGURE_GAP apart); `pressed` says which slice a tile turns on, or off. Where they don't all
    fit (a narrow window, a large text size), the last ones step aside rather than cut their words short."""

    pressed = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("FigureRow")
        self.lay = hbox(self, (tokens.PAGE_INSET, 0, tokens.PAGE_INSET, tokens.FIGURE_BELOW), tokens.FIGURE_GAP)
        self.lay.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)  # its width is the page's: what doesn't
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)  # fit steps aside (_fit)
        self.tiles: list[FigureTile] = []

    def show_for(self, figures: list[Figure], on: str = "") -> None:
        """These figures (the one whose slice is `on` marked on); none: the row goes."""
        while len(self.tiles) < len(figures):
            t = FigureTile()
            t.pressed.connect(self.pressed)
            self.lay.addWidget(t, 1)
            self.tiles.append(t)
        self._count = len(figures)
        for n, t in enumerate(self.tiles):
            if n < len(figures):
                t.show_figure(figures[n], bool(on) and figures[n].slice == on)
        self._fit()
        self.setVisible(bool(figures))

    def _fit(self) -> None:
        """As many tiles as fit at their own width, most important first."""
        count = getattr(self, "_count", 0)
        m = self.lay.contentsMargins()
        room = self.width() - m.left() - m.right()
        shown, used = 0, 0
        for t in self.tiles[:count]:
            need = t.minimumSizeHint().width() + (tokens.FIGURE_GAP if shown else 0)
            if shown and used + need > room:
                break
            used += need
            shown += 1
        for n, t in enumerate(self.tiles):
            t.setVisible(n < shown)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._fit()


class FigureStrip(QWidget):
    """A record's figures under its head (the standard's 4.5, G.17): side by side, divided by hairlines, never as
    tiles; the value in Title 2 Semibold, its name under it. Shows only the figures that apply, most important
    first: in a narrow panel the space around the hairlines narrows (to STRIP_PAD_MIN), then the last ones go."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("FigureStrip")
        self.lay = hbox(self, 0, 0)
        self.lay.addStretch(1)
        self.lay.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)  # its width is its panel's, never wider:
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)  # what doesn't fit is left out
        self.cells: list[tuple[QFrame, QWidget, QLabel, QLabel]] = []  # (the hairline before it, cell, value, label)
        self._count = 0  # figures to show (as many as fit of them show)

    def _cell(self) -> tuple[QFrame, QWidget, QLabel, QLabel]:
        line = QFrame()
        line.setObjectName("StripLine")
        line.setFixedWidth(1)
        cell = QWidget()
        cl = vbox(cell, 0, tokens.SPACE_0_5)
        value = QLabel()
        value.setObjectName("StripValue")
        theme.use_tabular(value)  # (its size and weight: the style's #StripValue)
        label = QLabel()
        label.setObjectName("FigureLabel")
        cl.addWidget(value)
        cl.addWidget(label)
        n = self.lay.count() - 1  # (before the stretch)
        self.lay.insertWidget(n, line)
        self.lay.insertWidget(n + 1, cell)
        return line, cell, value, label

    def show_for(self, figures: list[Figure]) -> None:
        while len(self.cells) < len(figures):
            self.cells.append(self._cell())
        for (_line, cell, value, label), f in zip(self.cells, figures, strict=False):
            value.setText(f.value)
            label.setText(f.label)
            if value.property("tone") != f.tone:
                value.setProperty("tone", f.tone)
                repolish(value)
            cell.setAccessibleName(f"{f.label}: {f.value}")
            cell.setToolTip(theme.plain_tip(f.tip) if f.tip else "")
        self._count = len(figures)
        self.setVisible(bool(figures))
        self._fit()

    def resizeEvent(self, e) -> None:
        super().resizeEvent(e)
        self._fit()

    def _fit(self) -> None:
        """As many figures as fit the width, each STRIP_PAD from its hairlines, or less, down to STRIP_PAD_MIN."""
        m = self.contentsMargins()
        room = self.width() - m.left() - m.right()
        widths = []
        for _line, _cell, value, label in self.cells[: self._count]:
            widths.append(max(value.sizeHint().width(), label.sizeHint().width()))
        n = len(widths)
        while n > 1:
            gaps = n - 1  # each: a hairline, with a pad either side
            pad = (room - sum(widths[:n]) - gaps) // (2 * gaps)
            pad -= pad % tokens.SPACE_1  # (on the 4-point grid, G.28's 19)
            if pad >= tokens.STRIP_PAD_MIN:
                break
            n -= 1
        pad = tokens.STRIP_PAD if n <= 1 else min(tokens.STRIP_PAD, pad)
        for k, (line, cell, _value, _label) in enumerate(self.cells):
            on = k < n
            line.setVisible(on and k > 0)  # between figures only
            cell.setVisible(on)
            if on:
                cell.layout().setContentsMargins(0 if k == 0 else pad, 0, pad if k < n - 1 else 0, 0)  # the ends: 0
