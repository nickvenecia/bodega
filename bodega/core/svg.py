"""SVG logos, read as untrusted: only the drawing is kept.

An SVG can point at other files: a picture by its path on this computer (<image href="/Users/…/x.png">), a
style sheet, another SVG. Qt's SVG reader follows those, so a logo from a stranger could print a file from this
computer onto every agreement. clean() keeps the drawing and drops everything that reaches outside it: pictures
other than ones written into the file (data:image/png or jpeg), links to anything but a part of the same file
(#id), scripts, embedded web content, url() to anything but #id, and any DOCTYPE or ENTITY. No Qt here.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from defusedxml import DefusedXmlException
from defusedxml.ElementTree import fromstring

MAX_BYTES = 2_000_000  # a logo is a few kilobytes; a big one is a picture pasted in
SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
DROPPED = {"script", "foreignObject", "iframe", "audio", "video", "handler", "listener", "animation"}
REFERS = {"image", "use", "feImage", "tref", "font-face-uri", "a"}  # elements that mean only their link
INLINE = re.compile(r"^data:image/(png|jpeg|jpg);base64,", re.IGNORECASE)
OUTSIDE_URL = re.compile(r"url\(\s*['\"]?\s*(?!#)", re.IGNORECASE)

ET.register_namespace("", SVG_NS)
ET.register_namespace("xlink", XLINK_NS)


class NotALogo(ValueError):
    """An SVG Bodega won't use as a logo, in plain words."""


def _local(name: str) -> str:
    return name.rsplit("}", 1)[-1]


def _href_ok(element: str, value: str) -> bool:
    value = value.strip()
    if value.startswith("#"):
        return element != "image"
    return element in ("image", "feImage") and bool(INLINE.match(value))


def clean(data: bytes) -> bytes:
    """The SVG with only its drawing left. Raises NotALogo if it isn't an SVG Bodega can use."""
    if len(data) > MAX_BYTES:
        raise NotALogo("That SVG is too big to be a logo. Use a smaller file, or a PNG.")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise NotALogo("That file isn't an SVG Bodega can read. Use a PNG, JPG or SVG file.") from e
    if re.search(r"<!\s*(DOCTYPE|ENTITY)", text, re.IGNORECASE):
        raise NotALogo(
            "That SVG asks to read other files, so Bodega won't use it. Save it as a PNG and use that."
        )
    try:
        root = fromstring(text, forbid_dtd=True)
    except (ET.ParseError, DefusedXmlException) as e:
        raise NotALogo("That file isn't an SVG Bodega can read. Use a PNG, JPG or SVG file.") from e
    if _local(root.tag) != "svg":
        raise NotALogo("That file isn't an SVG Bodega can read. Use a PNG, JPG or SVG file.")
    _tidy(root)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _tidy(parent: ET.Element) -> None:
    for el in list(parent):
        name = _local(el.tag)
        if name in DROPPED:
            parent.remove(el)
            continue
        if name == "style" and ("@import" in (el.text or "") or OUTSIDE_URL.search(el.text or "")):
            parent.remove(el)
            continue
        refused = False
        for attr, value in list(el.attrib.items()):
            local = _local(attr)
            if local == "href":
                if not _href_ok(name, value):
                    del el.attrib[attr]
                    refused = True
            elif local.lower().startswith("on") or OUTSIDE_URL.search(value):
                del el.attrib[attr]
        if refused and name in REFERS and name != "a":
            parent.remove(el)
            continue
        _tidy(el)
    for attr, value in list(parent.attrib.items()):
        local = _local(attr)
        if (
            local.lower().startswith("on")
            or OUTSIDE_URL.search(value)
            or (local == "href" and not _href_ok(_local(parent.tag), value))
        ):
            del parent.attrib[attr]
