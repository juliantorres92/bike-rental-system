"""Real (wall-clock) Clock adapter for running the app.

``FixedClock`` (see ``fixed_clock.py``) is for deterministic tests; this is the
clock the live server uses, so ``started_at``/``returned_at`` and the elapsed
time used to bill a return (RN-10) reflect actual time.
"""

from __future__ import annotations

from datetime import datetime, timezone

from ..rental.ports import Clock


class SystemClock(Clock):
    """Returns the current UTC time."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)
