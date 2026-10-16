"""Reordering gear by dragging its grip, drawn live: the piece lifts and follows the pointer, and the other
rows slide apart to open a gap where it will land (like the Finder or Reminders).

While a piece is lifted the table shows a drawing of itself (every row drawn once into a picture, then just
moved), so the slide stays smooth on a long list. Letting go turns the gap into a move:
before the row under the gap, after the row above it, or into a group whose divider is right above.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, QPointF, QRect, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import QStyle, QStyleOptionViewItem, QTreeWidget, QTreeWidgetItem

from bodega.ui.components import access
from bodega.ui.style import theme, tokens

# what a row is, for working out where a drop lands: ("item", id) or ("divider", group, "group"/"brand")
Describe = Callable[[QTreeWidgetItem], tuple]


class Lift(QObject):
    def __init__(
        self,
        table: QTreeWidget,
        rows: list[QTreeWidgetItem],
        moving_ids: list[str],
        grab: QTreeWidgetItem,
        press_y: float,
        describe: Describe,
    ):
        super().__init__(table)
        self.t = table
        self.describe = describe
        off = table.verticalOffset()
        moving = set(moving_ids)
        self.ids = [d[1] for r in rows if (d := describe(r))[0] == "item" and d[1] in moving]
        self.moving = [r for r in rows if describe(r)[0] == "item" and describe(r)[1] in moving]
        self.rest = [r for r in rows if r not in self.moving]
        rects = {id(r): table.visualItemRect(r) for r in rows}
        self.h = {id(r): rects[id(r)].height() or tokens.TABLE_ROW_H for r in rows}
        self.top = min((rects[id(r)].top() + off for r in rows), default=0)
        self.gap = sum(self.h[id(r)] for r in self.moving)
        self.base = []  # where each other row sits with the moving rows taken out
        y = self.top
        for r in self.rest:
            self.base.append(y)
            y += self.h[id(r)]
        self.end_y = y
        self.cur = {id(r): float(rects[id(r)].top() + off) for r in self.rest}  # where each is drawn now
        self.grab_dy = press_y + off - (rects[id(grab)].top() + off)
        self.mouse_y = press_y
        self.start_k = sum(1 for r in self.rest if rects[id(r)].top() < rects[id(grab)].top())
        self.k = self.start_k
        self.slot_y = float(self._slot(self.k))
        self._pix: dict[int, QPixmap] = {}
        self.timer = QTimer(self, interval=tokens.LIFT_STEP_MS, timeout=self._step)
        self.timer.start()

    # Where it lands
    def _slot(self, k: int) -> float:
        return self.base[k] if k < len(self.rest) else self.end_y

    def _target_k(self) -> int:
        card_top = self.mouse_y + self.t.verticalOffset() - self.grab_dy
        center = card_top + min(self.gap, tokens.TABLE_ROW_H) / 2
        k = sum(1 for i, r in enumerate(self.rest) if self.base[i] + self.h[id(r)] / 2 < center)
        if k == 0 and self.rest and self.describe(self.rest[0])[0] == "divider":
            k = 1  # never above the first divider
        return k

    def move_to(self, y: float) -> None:
        self.mouse_y = y

    def result(self) -> tuple | None:
        """("before", id) / ("after", id) / ("into", group, kind), or None (it didn't move)."""
        k = self.k
        if k == self.start_k:
            return None
        prev = self.describe(self.rest[k - 1]) if k > 0 else None
        nxt = self.describe(self.rest[k]) if k < len(self.rest) else None
        if nxt is not None and nxt[0] == "item":
            return ("before", nxt[1])
        if prev is not None and prev[0] == "item":
            return ("after", prev[1])
        if prev is not None and prev[0] == "divider":
            return ("into", prev[1], prev[2])
        return None

    # Each step
    def _step(self) -> None:
        vp = self.t.viewport()
        edge = tokens.TABLE_ROW_H
        bar = self.t.verticalScrollBar()
        if self.mouse_y < edge:  # near the top or bottom: scroll
            bar.setValue(bar.value() - int((edge - self.mouse_y) / 2) - 1)
        elif self.mouse_y > vp.height() - edge:
            bar.setValue(bar.value() + int((self.mouse_y - vp.height() + edge) / 2) + 1)
        self.k = self._target_k()
        ease = 1.0 if access.reduce_motion() else tokens.LIFT_EASE  # Reduce Motion: rows jump to their place
        for i, r in enumerate(self.rest):  # each row eases towards where it should be
            target = self.base[i] + (self.gap if i >= self.k else 0)
            y = self.cur[id(r)]
            self.cur[id(r)] = y + (target - y) * ease if abs(target - y) > 0.5 else float(target)
        slot = self._slot(self.k)
        if abs(slot - self.slot_y) > 0.5:
            self.slot_y += (slot - self.slot_y) * ease
        else:
            self.slot_y = float(slot)
        vp.update()  # the card follows the pointer every step

    def stop(self) -> None:
        self.timer.stop()

    # Drawing
    def _picture(self, r: QTreeWidgetItem) -> QPixmap:
        """One row, drawn by the table's own painter (once, then reused while it slides)."""
        got = self._pix.get(id(r))
        if got is not None:
            return got
        t = self.t
        vp = t.viewport()
        h = self.h[id(r)]
        dpr = vp.devicePixelRatioF()
        pix = QPixmap(max(1, round(vp.width() * dpr)), max(1, round(h * dpr)))
        pix.setDevicePixelRatio(dpr)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        head = t.header()
        for col in range(t.columnCount()):
            if t.isColumnHidden(col):
                continue
            opt = QStyleOptionViewItem()
            t.initViewItemOption(opt)
            opt.state &= ~(QStyle.StateFlag.State_Selected | QStyle.StateFlag.State_MouseOver)
            opt.rect = QRect(head.sectionViewportPosition(col), 0, head.sectionSize(col), h)
            t.itemDelegate().paint(p, opt, t.indexFromItem(r, col))
        p.end()
        self._pix[id(r)] = pix
        return pix

    def paint(self) -> None:
        t = self.t
        vp = t.viewport()
        off = t.verticalOffset()
        p = QPainter(vp)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, vh = vp.width(), vp.height()
        # the gap: a soft slot where it will land
        inset = tokens.ROW_INSET
        slot = QRectF(inset, self.slot_y - off + inset, w - 2 * inset, self.gap - 2 * inset)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(theme.qcolor(tokens.CHIP))
        p.drawRoundedRect(slot, tokens.ROW_R, tokens.ROW_R)
        for r in self.rest:
            y = self.cur[id(r)] - off
            if y + self.h[id(r)] < 0 or y > vh:
                continue
            p.drawPixmap(QPointF(0, y), self._picture(r))
        self._paint_card(p, self.mouse_y - self.grab_dy, w)
        p.end()

    def _paint_card(self, p: QPainter, y: float, w: float) -> None:
        """The lifted piece(s): a raised card with a soft shadow, following the pointer."""
        shown = self.moving[: tokens.LIFT_ROWS_SHOWN]
        h = sum(self.h[id(r)] for r in shown)
        card = QRectF(tokens.ROW_INSET, y, w - 2 * tokens.ROW_INSET, h)
        shadow = theme.qcolor(tokens.GLASS_SHADOW)
        for i in range(tokens.LIFT_SHADOW_STEPS, 0, -1):  # a soft shadow: rings fading outwards
            c = QColor(shadow)
            c.setAlphaF(shadow.alphaF() * 0.5 / i)
            grow = i * 1.5
            ring = QPainterPath()
            ring.addRoundedRect(
                card.adjusted(-grow, -grow + 2, grow, grow + 3), tokens.ROW_R + grow, tokens.ROW_R + grow
            )
            p.fillPath(ring, c)
        path = QPainterPath()
        path.addRoundedRect(card, tokens.ROW_R, tokens.ROW_R)
        p.fillPath(path, theme.qcolor(tokens.RAISED))
        p.setPen(theme.qcolor(tokens.ACCENT_EDGE))
        p.drawPath(path)
        p.save()
        p.setClipPath(path)
        top = y
        for r in shown:
            p.drawPixmap(QPointF(0, top), self._picture(r))
            top += self.h[id(r)]
        p.restore()
        if len(self.moving) > 1:  # how many are moving, in an accent badge at the top right
            label = str(len(self.moving))
            fm = p.fontMetrics()
            bw = max(tokens.SMALL_H, fm.horizontalAdvance(label) + 2 * tokens.SPACE_2)
            badge = QRectF(card.right() - bw / 2 - tokens.SPACE_2, card.top() - tokens.SMALL_H / 2, bw, tokens.SMALL_H)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(theme.qcolor(tokens.ACCENT))
            p.drawRoundedRect(badge, tokens.SMALL_H / 2, tokens.SMALL_H / 2)
            p.setPen(theme.qcolor(tokens.ON_ACCENT))
            p.drawText(badge, int(Qt.AlignmentFlag.AlignCenter), label)
