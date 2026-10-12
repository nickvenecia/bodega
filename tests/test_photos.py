"""Photos of gear: kept safely (read and saved again), from a file or a product page's link."""

from __future__ import annotations

import pytest
from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QColor, QImage

from bodega.core import sample, web
from bodega.core.model import Item
from bodega.core.store import Library


def picture(w=40, h=30, fmt="PNG", color="#7c5cff") -> bytes:
    img = QImage(w, h, QImage.Format.Format_RGB32)
    img.fill(QColor(color))
    data = QByteArray()
    buf = QBuffer(data)
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf, fmt)
    return bytes(data)


def test_keep_reads_and_saves_again(qapp, data_folder):
    from bodega.ui.components import photos

    name = photos.keep(picture())
    assert name.endswith(".jpg") and photos.path_of(name) is not None
    assert photos.keep(picture()) == name  # the same picture is kept once
    with pytest.raises(ValueError):
        photos.keep(b"<html>not a picture</html>")
    big = photos.keep(picture(4000, 1000, color="#123456"))
    img = QImage(str(photos.path_of(big)))
    assert max(img.width(), img.height()) == photos.PHOTO_MAX_PX
    assert photos.thumbnail(name, 24) is not None and photos.thumbnail("", 24) is None


def test_photo_names_are_only_names():
    assert Item.from_dict({"photo": "../../etc/passwd"}).photo == ""
    assert Item.from_dict({"photo": "0123456789abcdef.jpg"}).photo == "0123456789abcdef.jpg"


def test_a_pages_main_picture():
    html = """<html><head>
    <meta property="og:image" content="/img/fx6.jpg">
    <script type="application/ld+json">{"@type": "Product", "image": ["https://cdn.example.com/a.png"]}</script>
    </head><body>FX6</body></html>"""
    info = web.read(html)
    assert web.image_of(info, "https://shop.example.com/p/fx6") == "https://shop.example.com/img/fx6.jpg"
    only_ld = web.read(html.replace('<meta property="og:image" content="/img/fx6.jpg">', ""))
    assert web.image_of(only_ld, "https://shop.example.com/p") == "https://cdn.example.com/a.png"
    assert web.image_of(web.read("<p>nothing</p>"), "https://x.example.com") == ""
    bad = web.read('<meta property="og:image" content="javascript:alert(1)">')
    assert web.image_of(bad, "https://x.example.com") == ""


def test_from_link(qapp, data_folder, monkeypatch):
    from bodega.ui.components import photos

    page = web.Page(
        "https://shop.example.com/fx6", '<meta property="og:image" content="https://cdn.example.com/fx6.jpg">'
    )
    asked = []
    monkeypatch.setattr(web, "fetch", lambda url, **_k: page)
    monkeypatch.setattr(web, "fetch_image", lambda url, **_k: asked.append(url) or picture())
    name = photos.from_link("https://shop.example.com/fx6")
    assert asked == ["https://cdn.example.com/fx6.jpg"] and photos.path_of(name)
    monkeypatch.setattr(web, "fetch", lambda url, **_k: web.Page(url, "<p>no picture</p>"))
    with pytest.raises(OSError):
        photos.from_link("https://shop.example.com/x")


def test_photo_in_the_panel_and_the_list(qapp, data_folder, monkeypatch):
    from bodega.ui.components import photos
    from bodega.ui.window.main_window import MainWindow

    win = MainWindow(sample.fill(Library(data_folder).load()))
    win.show()
    it = next(iter(win.lib.items.values()))
    win.open("gear", it.id)
    assert win.items.add_photo.isVisibleTo(win.items) and not win.items.photo.isVisibleTo(win.items)
    win.items._use_photo(photos.keep(picture()))
    win.flush()
    assert Library(data_folder).load().items[it.id].photo == it.photo
    assert win.items.photo.isVisibleTo(win.items) and not win.items.add_photo.isVisibleTo(win.items)
    win.refresh()
    assert win.gear_table.thumbs
    win.gear_table.grab()  # paints the thumbnails
    win.undo()  # one undo takes the photo off
    assert not win.lib.items[it.id].photo
    win.close()


def test_get_photos_from_links(qapp, data_folder, monkeypatch):
    from bodega.ui.components import photos
    from bodega.ui.window import transfer
    from bodega.ui.window.main_window import MainWindow

    win = MainWindow(sample.fill(Library(data_folder).load()))
    win.show()
    with_links = list(win.lib.items.values())[:2]
    for n, it in enumerate(with_links):
        it.link = f"https://shop.example.com/p/{n}"
    win.lib.save_items()
    monkeypatch.setattr("bodega.ui.dialogs.common.confirm", lambda *a, **k: True)
    monkeypatch.setattr(photos, "from_link", lambda link: photos.keep(picture(color="#22aa66")))
    win.get_photos_from_links()
    win._photo_worker.wait(5000)
    from PySide6.QtWidgets import QApplication

    QApplication.processEvents()
    assert all(win.lib.items[i.id].photo for i in with_links)
    assert transfer  # (the command lives with import and export)
    win.close()


def test_photos_on_the_inventory_list(qapp, data_folder):
    from bodega.core import document
    from bodega.core.looks import palette
    from bodega.doc import render
    from bodega.ui.components import photos

    lib = sample.fill(Library(data_folder).load())
    items = lib.ordered_items()
    v = document.build_inventory(lib, items, lib.pricing())
    assert not v.table.photos  # no photos yet: the list looks as it always did
    items[0].photo = photos.keep(picture())
    v = document.build_inventory(lib, items, lib.pricing())
    assert v.table.photos
    pages = render.layout(v, palette("blue"))
    assert any(isinstance(s, render.Photo) for pg in pages for s in pg.steps)
    r = document.build_ratecard(lib, items, list(lib.packages.values()), lib.pricing())
    assert r.table.photos


def test_labels_sheet_and_scanning(qapp, data_folder):
    from bodega.core import document
    from bodega.core.looks import palette
    from bodega.doc import render

    lib = sample.fill(Library(data_folder).load())
    items = lib.ordered_items()
    v = document.build_labels(items, lib.pricing())
    units = sum(i.qty for i in items if i.status != "retired")
    assert len(v.labels) == units
    pages = render.layout(v, palette("blue"))
    assert len(pages) == -(-units // 30)  # 30 to a sheet
    qrs = [s for pg in pages for s in pg.steps if isinstance(s, render.QR)]
    assert len(qrs) == units and qrs[0].modules and len(qrs[0].modules) == len(qrs[0].modules[0])
    it = items[0]
    assert document.item_from_code(document.label_code(it.id)) == it.id
    assert document.item_from_code("bodega:../../x") is None and document.item_from_code("hello") is None
    from bodega.ui.window.main_window import MainWindow

    win = MainWindow(lib)
    win.show()
    win.search.setText(document.label_code(it.id))
    win._scanned()  # (a scanner presses Return)
    assert win.items.it is it and win.search.text() == ""
    win.close()
