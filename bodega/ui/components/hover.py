"""Hover's lift (the standard's §6.2, I-18): a small filled control (the accent button, the accent + circle) rises
under the pointer: a touch larger, with a soft shadow beneath, easing back as the pointer leaves (dur-hover). Controls
drawn without a fill take a highlight, tiles and rows a tint (the stylesheet's :hover, as Appendix G gives them);
nothing gets a shadow without the scale. Under Reduce Motion it lifts and settles at once.

The app's event filter (app.py) calls hovered() as the pointer comes and goes. The effect is put on only while a
control is lifted or settling, so the rest of the time nothing is drawn through it."""

from __future__ import annotations

import shiboken6
from PySide6.QtCore import QEasingCurve, QPoint, QRectF, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import QGraphicsEffect, QWidget

from bodega.ui.components import access
from bodega.ui.style import theme, tokens

LIFTED = {"Primary", "CirclePrimary"}  # what lifts, by kind (its object name): the accent-filled controls


def lifts(w: QWidget) -> bool:
    """`w` is one that lifts: its kind, and enabled (a disabled control has no hover)."""
    return w.objectName() in LIFTED and w.isEnabled()


class LiftEffect(QGraphicsEffect):
    """Draws its control a touch larger around its middle (LIFT_SCALE), over a soft shadow in its capsule's shape, by
    `amount` (0 at rest, 1 lifted)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.grow = tokens.LIFT_SCALE
        self.amount = 0.0
        self.anim = QVariantAnimation(self)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.valueChanged.connect(self._step)

    def _step(self, v) -> None:
        self.amount = float(v)
        self.update()

    def boundingRectFor(self, rect: QRectF) -> QRectF:
        room = tokens.LIFT_SHADOW_BLUR + max(rect.width(), rect.height()) * self.grow
        return rect.adjusted(-room, -room, room, room + tokens.LIFT_SHADOW_DROP)

    def draw(self, painter: QPainter) -> None:
        if self.amount <= 0:
            self.drawSource(painter)
            return
        shape = self.sourceBoundingRect(Qt.CoordinateSystem.LogicalCoordinates)  # (the control itself)
        at = QPoint()  # (where the picture goes: filled in by Qt)
        pix = self.sourcePixmap(Qt.CoordinateSystem.LogicalCoordinates, at, QGraphicsEffect.PixmapPadMode.NoPad)
        scale = 1 + self.grow * self.amount
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.translate(shape.center())
        painter.scale(scale, scale)
        painter.translate(-shape.center())
        self._shadow(painter, shape)
        painter.drawPixmap(at, pix)
        painter.restore()

    def _shadow(self, painter: QPainter, shape: QRectF) -> None:
        """A soft shadow under the capsule, in faint layers that reach further out, dropped a little below it."""
        base = theme.qcolor(tokens.LIFT_SHADOW)
        steps = tokens.LIFT_SHADOW_STEPS
        drop = tokens.LIFT_SHADOW_DROP * self.amount
        painter.setPen(Qt.PenStyle.NoPen)
        for n in range(1, steps + 1):
            reach = tokens.LIFT_SHADOW_BLUR * n / steps / 2
            c = QColor(base)
            c.setAlphaF(base.alphaF() * self.amount / steps)
            r = shape.adjusted(-reach, -reach, reach, reach).translated(0, drop)
            path = QPainterPath()
            path.addRoundedRect(r, r.height() / 2, r.height() / 2)
            painter.fillPath(path, c)


def hovered(w: QWidget, inside: bool) -> None:
    """The pointer came onto `w` (or left it): it lifts (or settles, and the effect comes off once it has)."""
    if not shiboken6.isValid(w) or not lifts(w):
        return
    effect = w.graphicsEffect()
    if effect is not None and not isinstance(effect, LiftEffect):
        return  # (fading in or out: its own effect wins)
    if effect is None:
        if not inside:
            return
        effect = LiftEffect(w)
        effect.anim.finished.connect(lambda w=w, e=effect: _settled(w, e))
        w.setGraphicsEffect(effect)
    effect.anim.stop()
    effect.anim.setDuration(access.duration(tokens.LIFT_MS))
    effect.anim.setStartValue(effect.amount)
    effect.anim.setEndValue(1.0 if inside else 0.0)
    effect.anim.start()


def _settled(w: QWidget, e: LiftEffect) -> None:
    if shiboken6.isValid(w) and w.graphicsEffect() is e and e.amount <= 0:
        w.setGraphicsEffect(None)  # (at rest: drawn as itself again)
