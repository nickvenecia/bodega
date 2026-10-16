"""What went wrong, in plain words: one translator for the errors the computer gives (a full disk, a folder
Bodega isn't allowed to write to, a file another app has open), so no "[Errno 13]" ever reaches a person.

    plain(e, "save the backup")  ->  "Couldn't save the backup: Bodega isn't allowed to write to that folder.
                                      Choose another folder, or check its permissions."

Anything it doesn't know gets a short reference ("ref 7F3A"), written to the log with the full error, so a
person who sends feedback can point at the right line. No Qt here.
"""

from __future__ import annotations

import errno
import secrets
import socket
import ssl
import urllib.error

from bodega.core.log import get_logger

log = get_logger(__name__)

REASONS = {  # errno -> (why, what to do)
    errno.ENOSPC: ("there's no free space left on this computer", "Free some space, then try again."),
    errno.EDQUOT: ("there's no free space left on this computer", "Free some space, then try again."),
    errno.EACCES: (
        "Bodega isn't allowed to write to that folder",
        "Choose another folder, or check its permissions.",
    ),
    errno.EPERM: (
        "Bodega isn't allowed to write to that folder",
        "Choose another folder, or check its permissions.",
    ),
    errno.EROFS: ("that place can only be read, not written", "Choose another folder."),
    errno.ENOENT: ("the folder isn't there any more", "Choose another folder, or plug the drive back in."),
    errno.ENOTDIR: ("the folder isn't there any more", "Choose another folder."),
    errno.EBUSY: ("another app has the file open", "Close it there, then try again."),
    errno.ENAMETOOLONG: ("the file's name is too long", "Choose a shorter name or a folder nearer the top."),
    errno.EIO: ("the drive couldn't be read or written", "Check the drive, then try again."),
}
WINDOWS = {32: errno.EBUSY, 33: errno.EBUSY, 5: errno.EACCES, 112: errno.ENOSPC}  # winerror -> errno


def reason(e: OSError) -> tuple[str, str] | None:
    """(why, what to do) for an error the computer gave, or None if it's not one Bodega knows."""
    code = WINDOWS.get(getattr(e, "winerror", None) or 0) or e.errno
    return REASONS.get(code) if code is not None else None


def reference(e: BaseException, doing: str) -> str:
    """A short reference for an error nobody expected, logged with everything about it."""
    ref = secrets.token_hex(2).upper()
    log.warning("ref %s: couldn't %s", ref, doing, exc_info=e)
    return ref


NETWORK = (
    "Bodega couldn't reach the internet",
    "Check your connection, then try again.",
)
ANSWER = ("the website didn't answer properly", "Try again later.")


def _network(e: BaseException) -> tuple[str, str] | None:
    """The internet's errors (no connection, a timeout, a website's error page), never their raw text."""
    if isinstance(e, urllib.error.HTTPError):
        return ANSWER
    if isinstance(e, urllib.error.URLError | TimeoutError | ConnectionError | socket.gaierror | ssl.SSLError):
        return NETWORK
    return None


def plain(e: BaseException, doing: str) -> str:
    """'Couldn't {doing}: {why}. {What to do}' — or, for something unknown, the same with a reference."""
    found = _network(e)
    if found is None and isinstance(e, OSError) and e.errno is None and str(e) and str(e)[0] not in "[<":
        return str(e)  # Bodega's own plain-words errors (web, AI, keychain) pass through as they are
    if found is None and isinstance(e, OSError):
        found = reason(e)
    if found is not None:
        why, todo = found
        return f"Couldn't {doing}: {why}. {todo}"
    return (
        f"Couldn't {doing}. Try again; if it keeps happening, send feedback with ref {reference(e, doing)}."
    )
