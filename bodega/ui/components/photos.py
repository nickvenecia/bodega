"""Photos of gear: kept in the data folder's photos/ (Back Up takes them along), named by what's in them.

They come from a file, a product page's link, or a picture pasted or dragged in (Copy Image in a browser: the
way in for stores that let only web browsers read their pages).

Every picture, from a file or a web page, is read and saved again by Bodega before it's kept: whatever else
the file carried (camera details, location, anything odd) is left behind, and a file that isn't really a
picture is refused. Pictures are scaled down to PHOTO_MAX_PX on their long side.

Photo files are never deleted when a piece is (undo can bring the piece back, and a copy may share the file).
"""

from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QMimeData, QRectF, Qt
from PySide6.QtGui import QImage, QPainter, QPainterPath, QPixmap

from bodega.core import errors, web
from bodega.core.model import PHOTO_NAME
from bodega.core.paths import photos_dir
from bodega.ui.style import tokens

PHOTO_MAX_PX = 1600
MAX_FILE_BYTES = 40_000_000  # a photo file you pick, before it's scaled down
JPEG_QUALITY = 88
PICTURE_FILES = (".jpg", ".jpeg", ".png", ".webp", ".heic", ".gif")


def keep(data: bytes) -> str:
    """Read `data` as a picture, scale it down, save it in the photos folder. Its file name.
    Raises ValueError if it isn't a picture Bodega can read, OSError if it can't be saved."""
    img = QImage.fromData(QByteArray(data))
    if img.isNull() or img.width() < 2 or img.height() < 2:
        raise ValueError("That isn't a picture Bodega can read. Use a JPG, PNG or WebP.")
    if max(img.width(), img.height()) > PHOTO_MAX_PX:
        img = img.scaled(
            PHOTO_MAX_PX,
            PHOTO_MAX_PX,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    clear = img.hasAlphaChannel() and not _solid(img)  # a cut-out product shot keeps its see-through background
    name = f"{hashlib.sha256(data).hexdigest()[:16]}.{'png' if clear else 'jpg'}"
    folder = photos_dir()
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / name
    if not dest.exists():
        if not clear:
            img = img.convertToFormat(QImage.Format.Format_RGB32)
        write_picture(img, dest, "PNG" if clear else "JPEG", -1 if clear else JPEG_QUALITY, "save the photo")
    return name


def encoded(img: QImage, fmt: str = "PNG", quality: int = -1) -> bytes:
    """A picture as a file's bytes."""
    data = QByteArray()
    buf = QBuffer(data)
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    if not img.save(buf, fmt, quality):
        raise ValueError("Bodega couldn't make a picture of that. Try another one.")
    buf.close()
    return bytes(data)


def write_picture(img: QImage, dest: Path, fmt: str, quality: int, doing: str) -> None:
    """Write a picture whole (a part-written one never takes its place). The computer's reason if it can't,
    in plain words, as an OSError."""
    tmp = dest.with_name(f".{dest.name}.part")
    try:
        tmp.write_bytes(encoded(img, fmt, quality))
        tmp.replace(dest)
    except OSError as e:
        tmp.unlink(missing_ok=True)
        raise OSError(errors.plain(e, doing)) from e


def _solid(img: QImage) -> bool:
    """Whether every pixel is solid: a photo copied from a browser comes with see-through it doesn't use, and
    is kept as a JPG like any photo."""
    a = img.convertToFormat(QImage.Format.Format_Alpha8)
    raw, w, line = bytes(a.constBits()), a.width(), a.bytesPerLine()
    return all(raw[y * line : y * line + w].count(255) == w for y in range(a.height()))


def keep_image(img: QImage) -> str:
    """A picture pasted or dragged in as a picture (Copy Image in a browser, a screenshot), kept like any other."""
    return keep(encoded(img))


def keep_file(path: Path) -> str:
    """A photo file you picked or dropped."""
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            raise ValueError("That picture is too big.")
        data = path.read_bytes()
    except OSError as e:
        raise OSError(f"Couldn't open {path.name}.") from e
    return keep(data)


def from_link(link: str) -> str:
    """The main picture on a product page (what the page names for sharing), kept. Run it in the background:
    it goes to the web (through core.web, like every link). Raises OSError with a plain message."""
    page = web.fetch(link)
    url = web.image_of(web.read(page.html), page.url)
    if not url:
        raise OSError("That page doesn't name a photo.")
    try:
        return keep(web.fetch_image(url))
    except ValueError as e:
        raise OSError(str(e)) from e


def from_any_link(link: str) -> str:
    """A photo dragged out of a browser: its link, or the link of the page it's on. The picture either way.
    Raises OSError with a plain message."""
    try:
        return keep(web.fetch_image(link))
    except web.NotPicture:
        return from_link(link)
    except ValueError as e:
        raise OSError(str(e)) from e


# Pasted or dropped
def picture_file(mime: QMimeData) -> Path | None:
    """A picture file among what was copied or dropped (from Finder, Explorer, the desktop)."""
    for url in mime.urls() if mime.hasUrls() else []:
        if url.isLocalFile():
            p = Path(url.toLocalFile())
            if p.suffix.lower() in PICTURE_FILES:
                return p
    return None


def picture_image(mime: QMimeData) -> QImage | None:
    """The picture itself, when it came as one (Copy Image in a browser, a screenshot)."""
    if not mime.hasImage():
        return None
    img = mime.imageData()
    if isinstance(img, QPixmap):
        img = img.toImage()
    return img if isinstance(img, QImage) and not img.isNull() else None


def picture_link(mime: QMimeData) -> str:
    """A web link among what was dragged in (a photo dragged out of a browser), or ""."""
    for url in mime.urls() if mime.hasUrls() else []:
        link = web.web_link(url.toString())
        if link:
            return link
    return ""


def has_picture(mime: QMimeData | None, links: bool = True) -> bool:
    """Whether there's a picture in what was copied or dragged. `links`: a web link counts (a drag does; a
    paste doesn't, since a link you copied is more likely meant for the Link field)."""
    if mime is None:
        return False
    if picture_file(mime) is not None or mime.hasImage():
        return True
    return links and bool(picture_link(mime))


def path_of(name: str) -> Path | None:
    """The photo's file, if the name is a photo's name and the file is there."""
    if not name or not PHOTO_NAME.fullmatch(name):
        return None
    p = photos_dir() / name
    return p if p.is_file() else None


@lru_cache(maxsize=1024)
def _square(path: str, mtime: float, size: int, dpr: float, radius: float) -> QPixmap:
    img = QImage(path)
    pix = QPixmap(round(size * dpr), round(size * dpr))
    pix.setDevicePixelRatio(dpr)
    pix.fill(Qt.GlobalColor.transparent)
    if img.isNull():
        return pix
    # fill the square (cropping the long side), with rounded corners
    scaled = img.scaled(
        round(size * dpr),
        round(size * dpr),
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
    x = (scaled.width() - round(size * dpr)) // 2
    y = (scaled.height() - round(size * dpr)) // 2
    scaled = scaled.copy(x, y, round(size * dpr), round(size * dpr))
    scaled.setDevicePixelRatio(dpr)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    clip = QPainterPath()
    clip.addRoundedRect(QRectF(0, 0, size, size), radius, radius)
    p.setClipPath(clip)
    p.drawImage(QRectF(0, 0, size, size), scaled)
    p.end()
    return pix


def thumbnail(name: str, size: int, dpr: float = 2.0, radius: float = tokens.RADIUS_SM) -> QPixmap | None:
    """A square, rounded thumbnail (cached), or None if there's no photo."""
    p = path_of(name)
    if p is None:
        return None
    try:
        mtime = p.stat().st_mtime
    except OSError:
        return None
    return _square(str(p), mtime, size, dpr, radius)


@lru_cache(maxsize=64)
def _fit(path: str, mtime: float, w: int, h: int, dpr: float) -> QPixmap:
    img = QImage(path)
    if img.isNull():
        return QPixmap()
    pix = QPixmap.fromImage(
        img.scaled(
            round(w * dpr),
            round(h * dpr),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    )
    pix.setDevicePixelRatio(dpr)
    return pix


def fitted(name: str, w: int, h: int, dpr: float = 2.0) -> QPixmap | None:
    """The whole photo, scaled to fit w × h (the gear panel)."""
    p = path_of(name)
    if p is None:
        return None
    try:
        return _fit(str(p), p.stat().st_mtime, w, h, dpr)
    except OSError:
        return None
