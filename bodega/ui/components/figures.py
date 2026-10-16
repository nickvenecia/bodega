"""The figure row above a list (the standard's 4.3, G.10.5): a tile per figure (core/figures.py), its number large,
its name under it. A tile that's a slice of the list is a button: pressed, it shows only that slice and stays marked
on; pressed again, it lets go."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QFrame, QLabel, QWidget

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

    def show_figure(self, f: Figure, on: bool) -> None:
        self.slice = f.slice
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
    """Tiles side by side (FIGURE_GAP apart); `pressed` says which slice a tile turns on, or off."""

    pressed = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("FigureRow")
        self.lay = hbox(self, (tokens.PAGE_INSET, 0, tokens.PAGE_INSET, tokens.FIGURE_BELOW), tokens.FIGURE_GAP)
        self.tiles: list[FigureTile] = []

    def show_for(self, figures: list[Figure], on: str = "") -> None:
        """These figures (the one whose slice is `on` marked on); none: the row goes."""
        while len(self.tiles) < len(figures):
            t = FigureTile()
            t.pressed.connect(self.pressed)
            self.lay.addWidget(t, 1)
            self.tiles.append(t)
        for n, t in enumerate(self.tiles):
            if n < len(figures):
                t.show_figure(figures[n], bool(on) and figures[n].slice == on)
                t.show()
            else:
                t.hide()
        self.setVisible(bool(figures))
