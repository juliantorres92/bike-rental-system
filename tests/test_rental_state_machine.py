"""Rental state-machine guard (RN-12).

``confirm`` and ``mark_failed`` are only legal from 'pendiente_pago'. Confirming
twice, or failing an already-confirmed rental, is a domain error.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from tests.conftest import make_fare
from bike_rental.rental.entities import Rental, RentalItem
from bike_rental.rental.enums import RentalStatus
from bike_rental.rental.errors import IllegalRentalTransition
from bike_rental.shared.ids import (
    new_bicycle_id,
    new_payment_id,
    new_rental_id,
    new_rental_item_id,
    new_station_id,
    new_user_id,
)


def _pending_rental():
    now = datetime(2026, 5, 30, 12, 0, tzinfo=timezone.utc)
    item = RentalItem.from_fare(
        item_id=new_rental_item_id(),
        bicycle_id=new_bicycle_id(),
        fare=make_fare(),
        started_at=now,
    )
    rental = Rental.create_pending(
        rental_id=new_rental_id(),
        user_id=new_user_id(),
        origin_station_id=new_station_id(),
        items=[item],
        created_at=now,
    )
    return rental, now


def test_confirm_moves_pending_to_activa():
    rental, now = _pending_rental()
    rental.confirm(payment_id=new_payment_id(), confirmed_at=now)
    assert rental.status is RentalStatus.ACTIVA


def test_confirm_twice_is_illegal():
    rental, now = _pending_rental()
    rental.confirm(payment_id=new_payment_id(), confirmed_at=now)
    with pytest.raises(IllegalRentalTransition):
        rental.confirm(payment_id=new_payment_id(), confirmed_at=now)


def test_mark_failed_after_confirm_is_illegal():
    rental, now = _pending_rental()
    rental.confirm(payment_id=new_payment_id(), confirmed_at=now)
    with pytest.raises(IllegalRentalTransition):
        rental.mark_failed()
