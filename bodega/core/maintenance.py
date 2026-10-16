"""Looking after gear: when a piece was last serviced and when it's due again.

A piece with `service_days` set is due that many days after its last service (or after it was added, if it
has never had one). Repairs and notes are kept in the log but don't reset the clock.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from bodega.core import dates
from bodega.core.model import Item

SOON_DAYS = 14  # "due soon" this many days ahead
EVERY = [  # the choices for how often (days; 0 = never)
    (0, "Never"),
    (30, "Every Month"),
    (90, "Every 3 Months"),
    (180, "Every 6 Months"),
    (365, "Every Year"),
]


@dataclass(frozen=True)
class Due:
    when: date
    days: int  # from today: negative when overdue
    state: str  # "overdue" / "soon" / "ok"


def last_service(it: Item) -> date | None:
    done = [d for d in (dates.parse(e.date) for e in it.log if e.kind == "service") if d is not None]
    return max(done) if done else None


def due(it: Item, today: date | None = None) -> Due | None:
    """When it's next due for service, or None if it has no reminder (or is retired)."""
    if it.service_days <= 0 or it.is_retired():
        return None
    today = today or dates.today()
    start = last_service(it) or dates.parse((it.created or "")[:10]) or today
    when = start + timedelta(days=it.service_days)
    days = (when - today).days
    return Due(when, days, "overdue" if days < 0 else ("soon" if days <= SOON_DAYS else "ok"))


def needs_service(it: Item, today: date | None = None) -> bool:
    d = due(it, today)
    return d is not None and d.state != "ok"


def say(d: Due) -> str:
    """ "Due Nov 3 (in 22 days)", "Due today", "Overdue by 4 days"."""
    if d.days < 0:
        n = -d.days
        return f"Overdue by {n} day{'s' if n != 1 else ''} (was due {dates.fmt(d.when)})"
    if d.days == 0:
        return "Due today"
    return f"Due {dates.fmt(d.when)} (in {d.days} day{'s' if d.days != 1 else ''})"
