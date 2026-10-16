"""The app icon, from one vector source (the standard's V-41).

    python scripts/make_icon.py            draws bodega/assets/icon.png from bodega/assets/icon.svg
    python scripts/make_icon.py --source   writes icon.svg again (after a change to the letters, tile or colors)

icon.svg is the icon: Apple's 824-point rounded tile on a 1024 grid with its shade and hairline, and "b." as the
outlines of the bundled Inter Display Bold, the full stop in the accent. The mark is framed by its measured ink:
centred on the tile, as tall as MARK_PX of type. The build turns icon.png into the Mac .icns and the Windows .ico
(bodega.spec), so every size comes from the one drawing. Colors come from the design tokens.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRectF  # noqa: E402
from PySide6.QtGui import (  # noqa: E402
    QFont,
    QFontDatabase,
    QFontMetricsF,
    QGuiApplication,
    QImage,
    QPainter,
    QPainterPath,
)
from PySide6.QtSvg import QSvgRenderer  # noqa: E402

from bodega.ui.style.tokens import ACCENT, TEXT  # noqa: E402

SIZE = 1024
TILE = 824  # Apple's icon grid: an 824 px rounded square centred on 1024 (room for the shadow)
RADIUS = 185
TILE_TOP = "#1E1E22"  # a soft top-to-bottom shade of the app background (BG #111113)
TILE_BOTTOM = "#121214"
EDGE = 3  # a hairline edge so it holds up on dark docks…
EDGE_ALPHA = 0.086  # …white, barely
MARK_PX = 560  # the letters' size
FONT = ROOT / "bodega" / "assets" / "fonts" / "InterDisplay-Bold.otf"
SVG = ROOT / "bodega" / "assets" / "icon.svg"
PNG = ROOT / "bodega" / "assets" / "icon.png"


def _d(path: QPainterPath, dx: float, dy: float) -> str:
    """A QPainterPath as SVG path data, moved by (dx, dy)."""
    out, n = [], 0
    while n < path.elementCount():
        e = path.elementAt(n)
        if e.isMoveTo():
            out.append(f"M{e.x + dx:.2f} {e.y + dy:.2f}")
        elif e.isLineTo():
            out.append(f"L{e.x + dx:.2f} {e.y + dy:.2f}")
        else:  # a curve: this point and the next two
            c1, c2 = path.elementAt(n + 1), path.elementAt(n + 2)
            out.append(
                f"C{e.x + dx:.2f} {e.y + dy:.2f} {c1.x + dx:.2f} {c1.y + dy:.2f} {c2.x + dx:.2f} {c2.y + dy:.2f}"
            )
            n += 2
        n += 1
    return " ".join(out) + " Z"


def source() -> str:
    """The SVG: the tile, and "b." as outlines centred on their ink."""
    family = QFontDatabase.applicationFontFamilies(QFontDatabase.addApplicationFont(str(FONT)))[0]
    f = QFont(family)
    f.setPixelSize(MARK_PX)
    f.setWeight(QFont.Weight.Bold)  # (the file is the bold face; asked for, it isn't thinned to a regular)
    letter, dot = QPainterPath(), QPainterPath()
    letter.addText(0, 0, f, "b")
    dot.addText(QFontMetricsF(f).horizontalAdvance("b"), 0, f, ".")
    ink = letter.boundingRect().united(dot.boundingRect())
    dx, dy = (SIZE - ink.width()) / 2 - ink.left(), (SIZE - ink.height()) / 2 - ink.top()
    off, inner = (SIZE - TILE) / 2, EDGE / 2
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{SIZE}" height="{SIZE}" viewBox="0 0 {SIZE} {SIZE}">
  <!-- Bodega's icon, written by scripts/make_icon.py (its source option); icon.png is drawn from it -->
  <defs>
    <linearGradient id="shade" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{TILE_TOP}"/>
      <stop offset="1" stop-color="{TILE_BOTTOM}"/>
    </linearGradient>
  </defs>
  <rect x="{off}" y="{off}" width="{TILE}" height="{TILE}" rx="{RADIUS}" fill="url(#shade)"/>
  <rect x="{off + inner}" y="{off + inner}" width="{TILE - EDGE}" height="{TILE - EDGE}" rx="{RADIUS - inner}"
        fill="none" stroke="#FFFFFF" stroke-opacity="{EDGE_ALPHA}" stroke-width="{EDGE}"/>
  <path fill="{TEXT}" d="{_d(letter, dx, dy)}"/>
  <path fill="{ACCENT}" d="{_d(dot, dx, dy)}"/>
</svg>
"""


def draw(size: int = SIZE) -> QImage:
    """icon.svg at this size, on a clear background."""
    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(0)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    QSvgRenderer(str(SVG)).render(p, QRectF(0, 0, size, size))
    p.end()
    return img


if __name__ == "__main__":
    app = QGuiApplication(sys.argv[:1])
    if "--source" in sys.argv:
        SVG.write_text(source(), encoding="utf-8")
        print(f"wrote {SVG}")
    draw().save(str(PNG))
    print(f"wrote {PNG}")
