"""Troubleshooting log: a small rotating file in Bodega's data folder, one JSON object a line
({"time", "level", "where", "what", and "error" with the traceback when there is one}).

Use ``log = get_logger(__name__)`` in any module. Nothing is ever sent anywhere. Lines say what happened and how
many, never a renter's name, a profile's name or a full path (file names only). Started from a terminal
(`python -m bodega`), the same lines also print there, as plain text.
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import sys

from bodega.core.paths import log_dir

_configured = False


class _Lines(logging.Formatter):
    """One JSON object a line, so the log can be read by a program as well as a person."""

    def format(self, record: logging.LogRecord) -> str:
        line = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname.lower(),
            "where": record.name,
            "what": record.getMessage(),
        }
        if record.exc_info:
            line["error"] = self.formatException(record.exc_info)
        return json.dumps(line, ensure_ascii=False)


def setup_logging(level: int = logging.INFO, filename: str = "bodega.log") -> None:
    """Write to <data dir>/logs/<filename> (1 MB x 3 files). Safe to call more than once."""
    global _configured
    if _configured:
        return
    _configured = True
    root = logging.getLogger("bodega")
    root.setLevel(level)
    try:
        log_dir().mkdir(parents=True, exist_ok=True)
        handler: logging.Handler = logging.handlers.RotatingFileHandler(
            log_dir() / filename, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
    except OSError:
        handler = logging.NullHandler()  # read-only home folder etc. — logging is optional
    handler.setFormatter(_Lines())
    root.addHandler(handler)
    stream = sys.stderr
    if stream is not None and hasattr(stream, "isatty") and stream.isatty():
        console = logging.StreamHandler(stream)
        console.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s", "%H:%M:%S"))
        root.addHandler(console)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name if name.startswith("bodega") else f"bodega.{name}")
