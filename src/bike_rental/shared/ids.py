"""Typed identifiers.

Modelo §4: every business entity has a ``UUID`` PK. We model identifiers as
``NewType`` aliases over ``UUID`` so the type checker distinguishes a
``BicycleId`` from a ``RentalId`` while staying a plain UUID at runtime.

Generation uses ``uuid4`` in this increment; UUIDv7 is deferred to the stack
(modelo §4.5, ADR-0002).
"""

from __future__ import annotations

from typing import NewType
from uuid import UUID, uuid4

BicycleId = NewType("BicycleId", UUID)
StationId = NewType("StationId", UUID)
UserId = NewType("UserId", UUID)
FareId = NewType("FareId", UUID)
RentalId = NewType("RentalId", UUID)
RentalItemId = NewType("RentalItemId", UUID)
PaymentId = NewType("PaymentId", UUID)


def new_bicycle_id() -> BicycleId:
    return BicycleId(uuid4())


def new_station_id() -> StationId:
    return StationId(uuid4())


def new_user_id() -> UserId:
    return UserId(uuid4())


def new_fare_id() -> FareId:
    return FareId(uuid4())


def new_rental_id() -> RentalId:
    return RentalId(uuid4())


def new_rental_item_id() -> RentalItemId:
    return RentalItemId(uuid4())


def new_payment_id() -> PaymentId:
    return PaymentId(uuid4())
