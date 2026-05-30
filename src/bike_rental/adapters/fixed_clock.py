"""Deterministic clock and id generator adapters for tests.

``FixedClock.now`` returns an injected fixed datetime; ``advance`` moves it (for
HU-04 fare-change-over-time scenarios). ``DeterministicIdGenerator`` produces
predictable sequential UUIDs for stable asserts; the default ``UuidGenerator``
uses uuid4.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from ..rental.ports import Clock, IdGenerator
from ..shared.ids import (
    PaymentId,
    RentalId,
    RentalItemId,
    new_payment_id,
    new_rental_id,
    new_rental_item_id,
)


class FixedClock(Clock):
    def __init__(self, fixed: datetime) -> None:
        self._now = fixed

    def now(self) -> datetime:
        return self._now

    def advance(self, delta: timedelta) -> None:
        self._now = self._now + delta


class UuidGenerator(IdGenerator):
    """Default generator using uuid4 (modelo §4.5: v7 deferred to stack)."""

    def new_rental_id(self) -> RentalId:
        return new_rental_id()

    def new_rental_item_id(self) -> RentalItemId:
        return new_rental_item_id()

    def new_payment_id(self) -> PaymentId:
        return new_payment_id()


class DeterministicIdGenerator(IdGenerator):
    """Sequential, predictable UUIDs for stable test assertions."""

    def __init__(self) -> None:
        self._rental = 0
        self._item = 0
        self._payment = 0

    @staticmethod
    def _seq_uuid(prefix: int, n: int) -> UUID:
        # Build a deterministic UUID from a prefix and a counter.
        return UUID(int=(prefix << 64) | n)

    def new_rental_id(self) -> RentalId:
        self._rental += 1
        return RentalId(self._seq_uuid(0x1, self._rental))

    def new_rental_item_id(self) -> RentalItemId:
        self._item += 1
        return RentalItemId(self._seq_uuid(0x2, self._item))

    def new_payment_id(self) -> PaymentId:
        self._payment += 1
        return PaymentId(self._seq_uuid(0x3, self._payment))


def utc(year: int, month: int, day: int, hour: int = 12, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)
