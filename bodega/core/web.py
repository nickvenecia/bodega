"""Reading web pages safely: Check Price, the AI helpers, anything that downloads a page someone linked.

A link can come from a shared spreadsheet or from an AI's answer, so it's treated as untrusted:
- only https (http is upgraded); never file://, smb://, ftp:// or anything else
- only public internet addresses: never this computer, your home network or the router (checked again on
  every redirect, so a page can't bounce us somewhere private)
- a size cap on what's downloaded and on what it unpacks to, and a timeout
- pages are read with Python's HTML parser (it takes time in proportion to the page, so a hostile page
  can't freeze the app)
Every failure is an OSError with a plain message. Some stores (B&H among them) let only web browsers read their
pages: that's Refused, and the app offers another way in (copy the photo in your browser, paste it in Bodega).
"""

from __future__ import annotations

import http.client
import ipaddress
import json
import socket
import time
import urllib.request
import zlib
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from bodega.core.log import get_logger
from bodega.core.net import ssl_context

log = get_logger(__name__)

TIMEOUT_S = 15
DEADLINE_S = 30  # a whole page, however slowly it trickles in (so Stop is never stuck behind one)
MAX_BYTES = 6_000_000  # downloaded, and again after unpacking
MAX_REDIRECTS = 5
MAX_TEXT = 20_000  # characters of a page's text handed on (to an AI, say)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
}


class Blocked(OSError):
    """A link Bodega won't open or download."""


class Refused(OSError):
    """A site that turned Bodega away (many stores let only web browsers read their pages)."""


class NotPicture(OSError):
    """A link that leads to something other than a picture."""


SITES = {
    "bhphotovideo.com": "B&H",
    "adorama.com": "Adorama",
    "amazon.com": "Amazon",
    "harborfreight.com": "Harbor Freight",
    "homedepot.com": "Home Depot",
    "guitarcenter.com": "Guitar Center",
    "sweetwater.com": "Sweetwater",
}


def site_name(url: str) -> str:
    """What to call a site in a message: "B&H" for bhphotovideo.com, else its address without www."""
    host = (urlparse(url if "://" in url else "https://" + url).hostname or "").lower().removeprefix("www.")
    for domain, name in SITES.items():
        if host == domain or host.endswith("." + domain):
            return name
    return host


# Links
def web_link(text: str) -> str:
    """A link as typed or imported -> "https://…", or "" if it isn't a plain web link.
    "bhphotovideo.com/c/x" gets https://; "file://…", "javascript:…", "smb://…", a link with a
    name@ in front of its address, or a malformed one give ""."""
    s = (text or "").strip()
    if not s or any(c.isspace() for c in s) or len(s) > 2048:
        return ""
    if "://" not in s:
        if ":" in s.split("/", 1)[0] and not s.split("/", 1)[0].rsplit(":", 1)[-1].isdigit():
            return ""  # mailto:, javascript:, …
        s = "https://" + s
    try:
        u = urlparse(s)
        host, _port = u.hostname, u.port  # .port raises for ":abc" or ":99999"
    except ValueError:
        return ""
    if u.scheme.lower() not in ("http", "https") or not host or "." not in host:
        return ""
    if "@" in u.netloc or "%" in u.netloc:  # "https://bhphotovideo.com@evil.com" really goes to evil.com
        return ""
    return s


def is_web_link(text: str) -> bool:
    return bool(web_link(text))


_NAT64 = ipaddress.ip_network("64:ff9b::/96")
_V4_COMPAT = ipaddress.ip_network("::/96")


def _private(ip) -> bool:
    """True for anything that isn't a plain public address, including IPv6 forms that carry a private
    IPv4 address inside them."""
    if not ip.is_global or ip.is_multicast:
        return True
    if ip.version == 6:
        inner = ip.ipv4_mapped or ip.sixtofour or (ip.teredo[1] if ip.teredo else None)
        if ip in _NAT64 or ip in _V4_COMPAT:
            inner = ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF)
        if inner is not None and _private(inner):
            return True
    return False


def check_public(host: str) -> str:
    """The public address to connect to for `host`. Raises Blocked if any address it resolves to isn't
    on the public internet (so a name can't point at this computer or your network)."""
    try:
        infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
    except (socket.gaierror, UnicodeError) as e:
        raise OSError(f"Couldn't find {host}.") from e
    addresses = [ipaddress.ip_address(str(info[4][0]).split("%", 1)[0]) for info in infos]
    if not addresses or any(_private(ip) for ip in addresses):
        raise Blocked(f"{host} isn't on the public internet, so Bodega won't open it.")
    return str(addresses[0])


def _https(url: str) -> str:
    link = web_link(url)
    if not link:
        raise Blocked("That isn't a web link.")
    if urlparse(link).scheme.lower() == "http":
        link = "https://" + link.split("://", 1)[1]
    return link


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # redirects are never followed with an API key on board


_opener = urllib.request.build_opener(_NoRedirect(), urllib.request.HTTPSHandler(context=ssl_context()))
_direct = urllib.request.build_opener(  # for this computer: never through a proxy
    _NoRedirect(), urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=ssl_context())
)


def open_no_redirect(req: urllib.request.Request, timeout: float, direct: bool = False):
    """Open `req` without following redirects (an API key in its headers must never be sent on to
    wherever a redirect points). A redirect comes back as an HTTPError. `direct`: skip any proxy (a model
    on this computer: its key must not travel through a proxy in plain http)."""
    return (_direct if direct else _opener).open(req, timeout=timeout)


@dataclass
class Page:
    url: str  # where it ended up
    html: str
    content_type: str = ""


def _unpack(raw: bytes, encoding: str, limit: int) -> bytes:
    if encoding not in ("gzip", "deflate", "x-gzip"):
        return raw
    for wbits in (47, -15):  # gzip or zlib (auto), then raw deflate
        try:
            d = zlib.decompressobj(wbits=wbits)
            out = d.decompress(raw, limit)  # never more than `limit`, however well it packs
            return out
        except zlib.error:
            continue
    raise OSError("The page came back garbled.")


class _PinnedHTTPS(http.client.HTTPSConnection):
    """HTTPS to the exact address that was checked (asking DNS again could give a different, private
    one), with the certificate still checked against the name."""

    def __init__(self, host: str, ip: str, port: int, timeout: float):
        super().__init__(host, port, timeout=timeout, context=ssl_context())
        self._ip = ip

    def connect(self):
        sock = socket.create_connection((self._ip, self.port), self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


@dataclass
class _Reply:
    status: int
    headers: http.client.HTTPMessage
    body: bytes


def _get(url: str, ip: str, timeout: float, max_bytes: int) -> _Reply:
    """One GET to the checked address (no redirects followed)."""
    u = urlparse(url)
    path = (u.path or "/") + (f"?{u.query}" if u.query else "")
    conn = _PinnedHTTPS(u.hostname or "", ip, u.port or 443, timeout)
    deadline = time.monotonic() + DEADLINE_S
    try:
        conn.request("GET", path, headers=HEADERS)
        resp = conn.getresponse()
        chunks, got = [], 0
        while got < max_bytes:
            if time.monotonic() > deadline:
                raise TimeoutError("the page took too long")
            chunk = resp.read(min(64 * 1024, max_bytes - got))
            if not chunk:
                break
            chunks.append(chunk)
            got += len(chunk)
        return _Reply(resp.status, resp.headers, b"".join(chunks))
    finally:
        conn.close()


def _fetch(url: str, max_bytes: int, timeout: float) -> tuple[str, _Reply, bytes]:
    """GET a public https link, following redirects (each one checked). (where it ended up, reply, body)."""
    url = _https(url)
    for _hop in range(MAX_REDIRECTS + 1):
        host = urlparse(url).hostname or ""
        site = site_name(url)
        ip = check_public(host)
        try:
            r = _get(url, ip, timeout, max_bytes)
        except OSError as e:
            log.info("fetch failed for %s: %s", host, type(e).__name__)
            raise OSError(f"Couldn't reach {site}.") from e
        except Exception as e:  # http.client raises a few kinds of its own
            log.info("fetch failed for %s: %s", host, type(e).__name__)
            raise OSError(f"Couldn't reach {site}.") from e
        if r.status in (301, 302, 303, 307, 308) and r.headers.get("Location"):
            try:
                url = _https(urljoin(url, r.headers["Location"]))
            except ValueError as e:
                raise Blocked("That page redirects to a broken link.") from e
            continue
        if r.status >= 400:
            log.info("fetch failed for %s: HTTP %s", host, r.status)
            if r.status in (401, 403):
                raise Refused(f"{site} only lets web browsers read its pages.")
            if r.status in (429, 503):
                raise Refused(f"{site} didn't let Bodega read the page.")
            if r.status in (404, 410):
                raise OSError(f"That page isn't on {site} any more.")
            if r.status >= 500:
                raise OSError(f"{site} had a problem sending the page. Try again later.")
            raise OSError(f"{site} didn't send the page.")
        body = _unpack(r.body, (r.headers.get("Content-Encoding") or "").lower(), max_bytes)
        return url, r, body
    raise OSError("That link redirects too many times.")


def fetch(url: str, max_bytes: int = MAX_BYTES, timeout: float = TIMEOUT_S) -> Page:
    """Download a public web page over https. Raises OSError (Blocked for links it won't follow)."""
    url, r, body = _fetch(url, max_bytes, timeout)
    charset = r.headers.get_content_charset() or "utf-8"
    try:
        text = body.decode(charset, errors="replace")
    except (LookupError, ValueError):  # a charset Python doesn't know, or can't use here
        text = body.decode("utf-8", errors="replace")
    return Page(url, text, r.headers.get_content_type() or "")


IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_IMAGE_BYTES = 12_000_000


def fetch_image(url: str, timeout: float = TIMEOUT_S) -> bytes:
    """Download a picture from a public https link: a picture type only, and whole (a picture that's too big
    is refused, not cut short). The bytes still have to be read as a picture by whoever uses them."""
    _url, r, body = _fetch(url, MAX_IMAGE_BYTES + 1, timeout)
    if (r.headers.get_content_type() or "").lower() not in IMAGE_TYPES:
        raise NotPicture("That link isn't a picture.")
    if len(body) > MAX_IMAGE_BYTES:
        raise OSError("That picture is too big.")
    return body


# Reading a page
@dataclass
class PageInfo:
    title: str = ""
    meta: dict[str, str] = field(default_factory=dict)  # property / name / itemprop -> content (first wins)
    ld_json: list = field(default_factory=list)  # parsed JSON-LD blocks
    item_price: str = ""  # itemprop="price" content
    offscreen_price: str = ""  # Amazon's a-offscreen price
    text: str = ""  # the visible words, cut to MAX_TEXT


class _Reader(HTMLParser):
    SKIP = {"script", "style", "noscript", "template", "svg"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.info = PageInfo()
        self._ld: list[str] | None = None
        self._skip = 0
        self._title = False
        self._title_parts: list[str] = []
        self._title_size = 0
        self._offscreen = False
        self._words: list[str] = []
        self._size = 0

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "script" and "ld+json" in a.get("type", "").lower():
            self._ld = []
        if tag in self.SKIP:
            self._skip += 1
        elif tag == "title":
            self._title = True
        elif tag == "meta":
            key = (a.get("property") or a.get("name") or a.get("itemprop") or "").lower()
            if key and a.get("content"):
                self.info.meta.setdefault(key, a["content"])
        if a.get("itemprop", "").lower() == "price" and a.get("content") and not self.info.item_price:
            self.info.item_price = a["content"]
        if tag == "span" and "a-offscreen" in a.get("class", "").split():
            self._offscreen = True

    def handle_endtag(self, tag):
        if tag == "script" and self._ld is not None:
            block = "".join(self._ld).strip()
            self._ld = None
            try:
                self.info.ld_json.append(json.loads(block))
            except (ValueError, RecursionError):
                pass
        if tag in self.SKIP and self._skip:
            self._skip -= 1
        elif tag == "title":
            self._title = False
        elif tag == "span":
            self._offscreen = False

    def handle_data(self, data):
        if self._ld is not None:
            self._ld.append(data)
            return
        if self._skip:
            return
        if self._title and self._title_size < 300:
            self._title_parts.append(data)
            self._title_size += len(data)
        if self._offscreen and not self.info.offscreen_price:
            self.info.offscreen_price = data.strip()
        words = " ".join(data.split())
        if words and self._size < MAX_TEXT:
            self._words.append(words)
            self._size += len(words) + 1


def image_of(info: PageInfo, page_url: str) -> str:
    """A product page's main picture: the one it names for sharing (og:image, twitter:image), else the
    product's image in its JSON-LD. An https link, or "" if it names none."""

    def ld_images(block, depth=0):
        if depth > 6:
            return
        if isinstance(block, list):
            for b in block:
                yield from ld_images(b, depth + 1)
        elif isinstance(block, dict):
            if "@graph" in block:
                yield from ld_images(block["@graph"], depth + 1)
            kind = block.get("@type")
            kinds = kind if isinstance(kind, list) else [kind]
            if "Product" in kinds:
                img = block.get("image")
                for one in img if isinstance(img, list) else [img]:
                    if isinstance(one, dict):
                        one = one.get("url") or one.get("contentUrl")
                    if isinstance(one, str):
                        yield one

    found = [info.meta.get(k, "") for k in ("og:image:secure_url", "og:image", "twitter:image", "image")]
    found += list(ld_images(info.ld_json))
    for raw in found:
        raw = (raw or "").strip()
        if not raw:
            continue
        try:
            link = web_link(urljoin(page_url, raw))
        except ValueError:
            continue
        if link:
            return "https://" + link.split("://", 1)[1]  # fetched over https, like every link
    return ""


def read(html: str) -> PageInfo:
    """What's in a page: title, meta tags, JSON-LD, prices and its visible text."""
    r = _Reader()
    try:
        r.feed(html)
        r.close()
    except Exception:  # a broken page: keep what was read
        log.debug("page didn't parse cleanly", exc_info=True)
    r.info.title = " ".join("".join(r._title_parts).split())[:300]
    r.info.text = " ".join(r._words)[:MAX_TEXT]
    return r.info
