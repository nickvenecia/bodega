"""Hover (the standard's §6.2, I-18): the accent-filled controls lift under the pointer, a touch larger over a soft
shadow, and settle back when it leaves; at rest nothing is drawn through an effect. Rows tint and unfilled controls
highlight (the stylesheet's :hover); a disabled control doesn't lift."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QPointF
from PySide6.QtGui import QEnterEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QHBoxLayout, QPushButton, QWidget

from bodega.ui.components import hover
from bodega.ui.components.widgets import primary_button
from bodega.ui.style import tokens


def _enter(w):
    QApplication.sendEvent(w, QEnterEvent(QPointF(2, 2), QPointF(2, 2), QPointF(2, 2)))


def _leave(w):
    QApplication.sendEvent(w, QEvent(QEvent.Type.Leave))


def test_the_accent_button_lifts_and_settles(qapp, monkeypatch):
    monkeypatch.setenv("BODEGA_REDUCE_MOTION", "0")
    holder = QWidget()
    QHBoxLayout(holder).addWidget(b := primary_button("Save"))
    holder.show()
    _enter(b)
    effect = b.graphicsEffect()
    assert isinstance(effect, hover.LiftEffect)
    QTest.qWait(tokens.LIFT_MS + 80)
    assert effect.amount == 1.0
    assert b.grab().size() == b.size()  # (it still draws: through the effect)
    _leave(b)
    QTest.qWait(tokens.LIFT_MS + 80)
    assert b.graphicsEffect() is None  # at rest: drawn as itself
    holder.close()


def test_under_reduce_motion_it_lifts_at_once_and_plain_controls_dont(qapp, monkeypatch):
    monkeypatch.setenv("BODEGA_REDUCE_MOTION", "1")
    b = primary_button("Import Spreadsheet…")
    b.show()
    _enter(b)
    QApplication.processEvents()
    assert isinstance(b.graphicsEffect(), hover.LiftEffect) and b.graphicsEffect().amount == 1.0
    _leave(b)
    QApplication.processEvents()
    assert b.graphicsEffect() is None
    plain = QPushButton("Cancel")  # a button drawn without the accent: a highlight, no lift
    plain.show()
    _enter(plain)
    assert plain.graphicsEffect() is None
    off = primary_button("Save")
    off.setEnabled(False)
    off.show()
    _enter(off)
    assert off.graphicsEffect() is None  # disabled: no hover
    for w in (b, plain, off):
        w.close()
