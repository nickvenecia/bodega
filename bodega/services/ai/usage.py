"""What Bodega has asked your AI, and how much it may (the standard's 14.6): every question is counted, by day and by
month, with the tokens the provider says it used; a daily limit (settings "ai_daily_limit", 0 for none) warns at
80% and stops at 100%, saying so in plain words; and no more than RATE_PER_MIN questions go in any minute (a job
waits its turn rather than fail). Checking a key or listing models isn't a question and isn't counted.

Jobs ask from their own threads, so METER is guarded by a lock; the window loads it from settings and saves it
back (load() / dump()). No Qt here."""

from __future__ import annotations

import threading
import time
from collections import deque
from collections.abc import Callable
from datetime import date

DEFAULT_DAILY = 300  # questions a day: far more than a day's jobs (a big Tidy Up Names is about 40)
WARN_AT = 0.8  # the share of the daily limit at which Bodega says it's getting close
RATE_PER_MIN = 20  # the standard's default rate limit, per person
LIMIT_REACHED = (
    "Stopped: Bodega has asked your AI {limit:,} times today, your daily limit. It starts again tomorrow, or raise "
    "the limit in Settings › AI."
)


class DailyLimit(OSError):
    """Today's limit is used up (providers.ask says it as providers.LimitReached)."""


class Meter:
    def __init__(
        self,
        clock: Callable[[], float] = time.monotonic,
        today: Callable[[], date] = date.today,
        rate: int = RATE_PER_MIN,
    ):
        self._lock = threading.Lock()
        self._clock, self._today = clock, today
        self.rate = rate  # questions a minute, at most
        self.limit = DEFAULT_DAILY
        self.day, self.asked_today, self.tokens_today = "", 0, 0
        self.month, self.asked_this_month = "", 0
        self._recent: deque[float] = deque()  # when the last questions went, for the rate limit
        self._warned = ""  # the day the 80% warning was last said

    # kept in settings
    def load(self, settings: dict) -> None:
        from bodega.core import settings as kept

        u = kept.value(settings, "ai_usage")
        with self._lock:
            self.limit = max(0, kept.value(settings, "ai_daily_limit"))
            self.day = str(u.get("day", "")) if isinstance(u, dict) else ""
            self.asked_today = _count(u, "asked_today")
            self.tokens_today = _count(u, "tokens_today")
            self.month = str(u.get("month", "")) if isinstance(u, dict) else ""
            self.asked_this_month = _count(u, "asked_this_month")
            self._roll()

    def dump(self, settings: dict) -> None:
        with self._lock:
            self._roll()
            settings["ai_usage"] = {
                "day": self.day,
                "asked_today": self.asked_today,
                "tokens_today": self.tokens_today,
                "month": self.month,
                "asked_this_month": self.asked_this_month,
            }

    def set_limit(self, limit: int) -> None:
        """A new daily limit, from the next question on (what's been asked so far stays counted)."""
        with self._lock:
            self.limit = max(0, limit)

    def _roll(self) -> None:
        """A new day (or month) starts its count again."""
        today = self._today()
        if self.day != today.isoformat():
            self.day, self.asked_today, self.tokens_today = today.isoformat(), 0, 0
        if self.month != today.isoformat()[:7]:
            self.month, self.asked_this_month = today.isoformat()[:7], 0

    # around every question
    def take(self, sleep: Callable[[float], None] = time.sleep) -> None:
        """Before a question: stop at the daily limit; wait for a turn under the rate limit; count it."""
        while True:
            with self._lock:
                self._roll()
                if self.limit and self.asked_today >= self.limit:
                    raise DailyLimit(LIMIT_REACHED.format(limit=self.limit))
                now = self._clock()
                while self._recent and now - self._recent[0] >= 60:
                    self._recent.popleft()
                if len(self._recent) < self.rate:
                    self._recent.append(now)
                    self.asked_today += 1
                    self.asked_this_month += 1
                    return
                wait = 60 - (now - self._recent[0])
            sleep(max(0.05, wait))

    def used(self, answer: dict) -> None:
        """The tokens a provider's answer says it used (Anthropic: input + output; the others: total)."""
        u = answer.get("usage") if isinstance(answer, dict) else None
        if not isinstance(u, dict):
            return
        n = _count(u, "total_tokens") or _count(u, "input_tokens") + _count(u, "output_tokens")
        with self._lock:
            self.tokens_today += n

    # said
    def close_to_limit(self) -> str:
        """Once a day, when 80% of the limit is used: words to say so ("" otherwise)."""
        with self._lock:
            self._roll()
            if not self.limit or self.asked_today < WARN_AT * self.limit or self._warned == self.day:
                return ""
            self._warned = self.day
            return f"Bodega has asked your AI {self.asked_today:,} times today, of your daily limit of {self.limit:,}."

    def summary(self) -> str:
        """For Settings › AI: "Today: 34 of 300 questions (about 52,000 tokens) · This month: 412"."""
        with self._lock:
            self._roll()
            today = f"{self.asked_today:,} of {self.limit:,}" if self.limit else f"{self.asked_today:,}"
            tokens = f" (about {self.tokens_today:,} tokens)" if self.tokens_today else ""
            return f"Today: {today} questions{tokens} · This month: {self.asked_this_month:,}"


def _count(d, key: str) -> int:
    v = d.get(key) if isinstance(d, dict) else None
    return v if isinstance(v, int) and not isinstance(v, bool) and v > 0 else 0


METER = Meter()
