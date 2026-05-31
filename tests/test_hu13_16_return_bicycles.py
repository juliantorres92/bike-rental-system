"""HU-13..HU-15 — ReturnBicycles domain use case (UC-02, E-04).

Each scenario first creates an ACTIVE rental through CreateRental, then advances
the FixedClock so usage_minutes/final_amount are > 0, and finally exercises
ReturnBicycles against the SAME wired repositories. Atomicity (RN-05): on any
error nothing mutates (no item 'devuelto', no bicycle 'disponible', no inventory
change, payment untouched).
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest

from tests.conftest import build_wiring, make_bicycle, make_fare, make_station
from bike_rental.bicycle.enums import BicycleStatus
from bike_rental.fare.enums import TimeUnit
from bike_rental.rental.enums import RentalItemStatus, RentalStatus
from bike_rental.rental.errors import (
    BicycleNotInRentalError,
    RentalItemAlreadyReturnedError,
    RentalNotActiveError,
    StationFullError,
)
from bike_rental.rental.use_cases.create_rental import CreateRentalCommand
from bike_rental.rental.use_cases.return_bicycles import ReturnBicyclesCommand
from bike_rental.shared.money import Money


# Fare: fixed 1000, time 200 per MINUTO -> easy to assert final_amount.
def _fare():
    return make_fare(fixed="1000.00", time="200.00", relocation="500.00")


def _create_active_rental(user_id, *, n_bikes=3, station_inventory=0, capacity=10):
    """Create an 'activa' rental with ``n_bikes`` and return (wiring, rental, bikes,
    station). The origin station starts with the given inventory/capacity."""
    station = make_station(capacity=capacity, inventory=station_inventory + n_bikes)
    bikes = [
        make_bicycle(station_id=station.id, code=f"BIKE-{i}")
        for i in range(1, n_bikes + 1)
    ]
    wiring = build_wiring(bicycles=bikes, stations=[station])
    result = wiring.use_case.execute(
        CreateRentalCommand(
            user_id=user_id,
            station_id=station.id,
            bicycle_ids=[b.id for b in bikes],
            fare=_fare(),
        )
    )
    rental = wiring.rental_repo.get(result.rental_id)
    # After create, origin inventory dropped by n_bikes back to station_inventory.
    return wiring, rental, bikes, station


# --- TC-13-total / HU-13 -------------------------------------------------------
def test_tc13_total_return_completes_rental(user_id):
    wiring, rental, bikes, station = _create_active_rental(user_id, n_bikes=3)
    inv_before = wiring.station_repo.get(station.id).available_inventory
    payment_before = rental.payment_id

    wiring.clock.advance(timedelta(minutes=30))
    updated = wiring.return_use_case.execute(
        ReturnBicyclesCommand(
            rental_id=rental.id,
            bicycle_ids=[b.id for b in bikes],
            return_station_id=station.id,
        )
    )

    assert updated.status is RentalStatus.COMPLETADA
    assert all(i.status is RentalItemStatus.DEVUELTO for i in updated.items)
    assert updated.closed_at == wiring.clock.now()
    # Payment authorized is kept untouched (out of scope settlement).
    assert updated.payment_id == payment_before

    for bike in bikes:
        stored = wiring.bicycle_repo.get(bike.id)
        assert stored.status is BicycleStatus.DISPONIBLE
        assert stored.station_id == station.id

    after = wiring.station_repo.get(station.id)
    assert after.available_inventory == inv_before + 3

    # final_amount per item: fixed 1000 + time 200 * ceil(30/1) = 1000 + 6000.
    for item in updated.items:
        assert item.final_amount == Money(Decimal("7000.00"))
        assert item.usage_minutes == 30
        assert item.final_amount.amount > 0


# --- TC-14-partial-then-last / HU-14 (central case) ----------------------------
def test_tc14_partial_then_last(user_id):
    wiring, rental, bikes, station = _create_active_rental(user_id, n_bikes=3)
    inv_before = wiring.station_repo.get(station.id).available_inventory

    # Return 2 of 3.
    wiring.clock.advance(timedelta(minutes=10))
    updated = wiring.return_use_case.execute(
        ReturnBicyclesCommand(
            rental_id=rental.id,
            bicycle_ids=[bikes[0].id, bikes[1].id],
            return_station_id=station.id,
        )
    )
    assert updated.status is RentalStatus.PARCIALMENTE_DEVUELTA
    assert updated.closed_at is None
    returned_ids = {bikes[0].id, bikes[1].id}
    for item in updated.items:
        if item.bicycle_id in returned_ids:
            assert item.status is RentalItemStatus.DEVUELTO
        else:
            assert item.status is RentalItemStatus.ACTIVO
    # The non-returned bike is still rentada.
    assert wiring.bicycle_repo.get(bikes[2].id).status is BicycleStatus.RENTADA
    assert wiring.station_repo.get(station.id).available_inventory == inv_before + 2

    # Return the last one against the PARCIALMENTE_DEVUELTA rental.
    wiring.clock.advance(timedelta(minutes=5))
    final = wiring.return_use_case.execute(
        ReturnBicyclesCommand(
            rental_id=rental.id,
            bicycle_ids=[bikes[2].id],
            return_station_id=station.id,
        )
    )
    assert final.status is RentalStatus.COMPLETADA
    assert final.closed_at == wiring.clock.now()
    assert wiring.station_repo.get(station.id).available_inventory == inv_before + 3
    last = next(i for i in final.items if i.bicycle_id == bikes[2].id)
    assert last.final_amount.amount > 0


# --- TC-15-already-returned / HU-15 -------------------------------------------
def test_tc15_already_returned_is_rejected_atomically(user_id):
    wiring, rental, bikes, station = _create_active_rental(user_id, n_bikes=2)
    wiring.clock.advance(timedelta(minutes=10))
    wiring.return_use_case.execute(
        ReturnBicyclesCommand(
            rental_id=rental.id,
            bicycle_ids=[bikes[0].id],
            return_station_id=station.id,
        )
    )
    inv_after_first = wiring.station_repo.get(station.id).available_inventory

    with pytest.raises(RentalItemAlreadyReturnedError):
        wiring.return_use_case.execute(
            ReturnBicyclesCommand(
                rental_id=rental.id,
                bicycle_ids=[bikes[0].id],
                return_station_id=station.id,
            )
        )

    # Nothing changed: item still devuelto once, inventory unchanged.
    item0 = next(i for i in wiring.rental_repo.get(rental.id).items
                 if i.bicycle_id == bikes[0].id)
    assert item0.status is RentalItemStatus.DEVUELTO
    assert wiring.station_repo.get(station.id).available_inventory == inv_after_first


# --- TC-15-not-in-rental / HU-15 ----------------------------------------------
def test_tc15_bicycle_not_in_rental(user_id):
    wiring, rental, bikes, station = _create_active_rental(user_id, n_bikes=2)
    # A bicycle that exists in the repo but is NOT part of the rental.
    foreign = make_bicycle(station_id=station.id, code="BIKE-FOREIGN")
    wiring.bicycle_repo.save(foreign)
    inv_before = wiring.station_repo.get(station.id).available_inventory

    wiring.clock.advance(timedelta(minutes=10))
    with pytest.raises(BicycleNotInRentalError):
        wiring.return_use_case.execute(
            ReturnBicyclesCommand(
                rental_id=rental.id,
                bicycle_ids=[foreign.id],
                return_station_id=station.id,
            )
        )

    assert all(i.status is RentalItemStatus.ACTIVO
               for i in wiring.rental_repo.get(rental.id).items)
    assert wiring.station_repo.get(station.id).available_inventory == inv_before


# --- TC-15-station-full / HU-15 -----------------------------------------------
def test_tc15_station_full_is_rejected_atomically(user_id):
    # Return at a SEPARATE destination station that is already at capacity.
    wiring, rental, bikes, origin = _create_active_rental(user_id, n_bikes=2)
    full = make_station(capacity=3, inventory=3)  # full
    wiring.station_repo.save(full)

    wiring.clock.advance(timedelta(minutes=10))
    with pytest.raises(StationFullError):
        wiring.return_use_case.execute(
            ReturnBicyclesCommand(
                rental_id=rental.id,
                bicycle_ids=[b.id for b in bikes],
                return_station_id=full.id,
            )
        )

    # Atomic: no item devuelto, no bike disponible, no inventory change.
    assert all(i.status is RentalItemStatus.ACTIVO
               for i in wiring.rental_repo.get(rental.id).items)
    for bike in bikes:
        assert wiring.bicycle_repo.get(bike.id).status is BicycleStatus.RENTADA
    assert wiring.station_repo.get(full.id).available_inventory == 3


# --- TC-15-not-active / HU-15 -------------------------------------------------
def test_tc15_rental_not_active(user_id):
    # Complete the rental, then attempt another return -> RentalNotActiveError.
    wiring, rental, bikes, station = _create_active_rental(user_id, n_bikes=1)
    wiring.clock.advance(timedelta(minutes=10))
    wiring.return_use_case.execute(
        ReturnBicyclesCommand(
            rental_id=rental.id,
            bicycle_ids=[bikes[0].id],
            return_station_id=station.id,
        )
    )
    assert wiring.rental_repo.get(rental.id).status is RentalStatus.COMPLETADA
    inv_before = wiring.station_repo.get(station.id).available_inventory

    with pytest.raises(RentalNotActiveError):
        wiring.return_use_case.execute(
            ReturnBicyclesCommand(
                rental_id=rental.id,
                bicycle_ids=[bikes[0].id],
                return_station_id=station.id,
            )
        )
    assert wiring.station_repo.get(station.id).available_inventory == inv_before


# --- TC-15-final-amount / HU-15 (frozen snapshot, no relocation charge) -------
def test_tc15_final_amount_uses_frozen_snapshot_no_relocation(user_id):
    wiring, rental, bikes, origin = _create_active_rental(user_id, n_bikes=1)
    # A DIFFERENT destination station (relocation) with room.
    dest = make_station(capacity=5, inventory=0)
    wiring.station_repo.save(dest)

    wiring.clock.advance(timedelta(minutes=90))
    updated = wiring.return_use_case.execute(
        ReturnBicyclesCommand(
            rental_id=rental.id,
            bicycle_ids=[bikes[0].id],
            return_station_id=dest.id,
        )
    )
    item = updated.items[0]
    # fixed 1000 + time 200 * ceil(90/1) = 1000 + 18000 = 19000. NO relocation.
    assert item.usage_minutes == 90
    assert item.final_amount == Money(Decimal("19000.00"))
    assert item.final_amount.amount > 0
    # Bike relocated to the destination, no extra charge applied.
    assert wiring.bicycle_repo.get(bikes[0].id).station_id == dest.id
    assert wiring.station_repo.get(dest.id).available_inventory == 1


# --- HU billable units: hour rounding (ceil, min 1) ----------------------------
def test_billable_units_hour_unit_ceils(user_id):
    station = make_station(capacity=10, inventory=1)
    bike = make_bicycle(station_id=station.id, code="BIKE-H")
    wiring = build_wiring(bicycles=[bike], stations=[station])
    fare = make_fare(fixed="500.00", time="3000.00", time_unit=TimeUnit.HORA)
    result = wiring.use_case.execute(
        CreateRentalCommand(
            user_id=user_id,
            station_id=station.id,
            bicycle_ids=[bike.id],
            fare=fare,
        )
    )
    rental = wiring.rental_repo.get(result.rental_id)
    wiring.clock.advance(timedelta(minutes=61))  # ceil(61/60) = 2 hours
    updated = wiring.return_use_case.execute(
        ReturnBicyclesCommand(
            rental_id=rental.id,
            bicycle_ids=[bike.id],
            return_station_id=station.id,
        )
    )
    # 500 + 3000 * 2 = 6500.
    assert updated.items[0].final_amount == Money(Decimal("6500.00"))
