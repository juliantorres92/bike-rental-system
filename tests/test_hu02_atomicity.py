"""HU-02 — Atomicity: all or nothing (RN-05, UC-01 3a/6a)."""

from __future__ import annotations

import pytest

from tests.conftest import REJECT, build_wiring, make_bicycle, make_fare, make_station
from bike_rental.inventory.enums import BicycleStatus
from bike_rental.rental.enums import RentalStatus
from bike_rental.rental.errors import (
    BicycleNotAvailableError,
    PaymentDeclinedError,
)
from bike_rental.rental.use_cases.create_rental import CreateRentalCommand


def test_hu02_1_unavailable_bicycle_aborts_with_no_side_effects(user_id):
    """T-HU02-1: 1 of 3 bikes not 'disponible' => BicycleNotAvailableError;
    no bike changes state, no active rental, gateway NOT invoked (RN-05)."""
    station = make_station(inventory=5)
    available = [make_bicycle(station_id=station.id, code=f"BIKE-{i}") for i in (1, 2)]
    # Third bike is in maintenance (not available).
    unavailable = make_bicycle(
        station_id=station.id, code="BIKE-3", status=BicycleStatus.MANTENIMIENTO
    )
    bikes = available + [unavailable]
    wiring = build_wiring(bicycles=bikes, stations=[station])
    command = CreateRentalCommand(
        user_id=user_id,
        station_id=station.id,
        bicycle_ids=[b.id for b in bikes],
        fare=make_fare(),
    )

    with pytest.raises(BicycleNotAvailableError):
        wiring.use_case.execute(command)

    # No bike changed state: the two available ones are still 'disponible'.
    for bike in available:
        stored = wiring.bicycle_repo.get(bike.id)
        assert stored.status is BicycleStatus.DISPONIBLE
        assert stored.station_id == station.id
    # The maintenance one is unchanged too.
    assert wiring.bicycle_repo.get(unavailable.id).status is BicycleStatus.MANTENIMIENTO

    # No active rental persisted, and the gateway was NEVER called (no charge).
    assert wiring.rental_repo.list_active_bicycle_ids() == set()
    assert wiring.gateway.calls == []

    # The station inventory is unchanged (no decrement on abort, RN-01/RN-05).
    assert wiring.station_repo.get(station.id).available_inventory == 5


def test_hu02_2_payment_declined_leaves_no_side_effects(user_id):
    """T-HU02-2: gateway rejects => PaymentDeclinedError; no bike 'rentada',
    no authorized payment, rental not 'activa' (RN-05, UC-01 6a)."""
    station = make_station(inventory=5)
    bikes = [make_bicycle(station_id=station.id, code=f"BIKE-{i}") for i in (1, 2, 3)]
    wiring = build_wiring(bicycles=bikes, stations=[station], outcome=REJECT)
    command = CreateRentalCommand(
        user_id=user_id,
        station_id=station.id,
        bicycle_ids=[b.id for b in bikes],
        fare=make_fare(),
    )

    with pytest.raises(PaymentDeclinedError) as exc_info:
        wiring.use_case.execute(command)

    # No bike left 'rentada' (all still 'disponible' at the station).
    for bike in bikes:
        stored = wiring.bicycle_repo.get(bike.id)
        assert stored.status is BicycleStatus.DISPONIBLE
        assert stored.station_id == station.id

    # The gateway was asked exactly once but no authorized payment was stored.
    assert len(wiring.gateway.calls) == 1
    assert wiring.payment_repo.get_by_rental(exc_info.value.rental_id) is None

    # The station inventory is unchanged (no decrement on a declined payment).
    assert wiring.station_repo.get(station.id).available_inventory == 5

    # No active rental: a second create on the same bikes still sees them free.
    assert wiring.rental_repo.list_active_bicycle_ids() == set()

    # HU-02 criterion 2: the rental is recorded as 'fallida' (observable).
    failed = wiring.rental_repo.get(exc_info.value.rental_id)
    assert failed is not None
    assert failed.status is RentalStatus.FALLIDA
    assert failed.payment_id is None
