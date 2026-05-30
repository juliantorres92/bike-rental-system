"""HU-01 — Create multi-bicycle rental, happy path (RN-04, RN-19, UC-01)."""

from __future__ import annotations

from tests.conftest import build_wiring, make_bicycle, make_fare, make_station
from bike_rental.bicycle.enums import BicycleStatus
from bike_rental.payment.enums import PaymentStatus
from bike_rental.rental.enums import RentalItemStatus, RentalStatus
from bike_rental.rental.use_cases.create_rental import CreateRentalCommand


def _setup_three_available(user_id):
    station = make_station(inventory=5)
    bikes = [
        make_bicycle(station_id=station.id, code=f"BIKE-{i}") for i in range(1, 4)
    ]
    fare = make_fare()
    wiring = build_wiring(bicycles=bikes, stations=[station])
    command = CreateRentalCommand(
        user_id=user_id,
        station_id=station.id,
        bicycle_ids=[b.id for b in bikes],
        fare=fare,
    )
    return wiring, station, bikes, fare, command


def test_hu01_1_happy_path_creates_rental_with_three_items(user_id):
    """T-HU01-1: 3 'disponible' bikes + active fare + gateway authorizes =>
    Rental with 3 items, each bicycle 'rentada', rental 'activa'."""
    wiring, station, bikes, fare, command = _setup_three_available(user_id)

    result = wiring.use_case.execute(command)

    assert result.status is RentalStatus.ACTIVA

    rental = wiring.rental_repo.get(result.rental_id)
    assert rental is not None
    assert rental.status is RentalStatus.ACTIVA
    assert len(rental.items) == 3
    assert all(item.status is RentalItemStatus.ACTIVO for item in rental.items)

    # Each bicycle is now 'rentada' and detached from the station (RN-01).
    for bike in bikes:
        stored = wiring.bicycle_repo.get(bike.id)
        assert stored.status is BicycleStatus.RENTADA
        assert stored.station_id is None

    # The gateway was called exactly once.
    assert len(wiring.gateway.calls) == 1


def test_hu01_2_authorized_payment_linked_one_to_one(user_id):
    """T-HU01-2: a Payment 'autorizado' linked 1:1 to the rental (RN-19)."""
    wiring, station, bikes, fare, command = _setup_three_available(user_id)

    result = wiring.use_case.execute(command)

    rental = wiring.rental_repo.get(result.rental_id)
    assert rental.payment_id is not None

    payment = wiring.payment_repo.get(result.payment_id)
    assert payment is not None
    assert payment.status is PaymentStatus.AUTORIZADO
    assert payment.rental_id == rental.id
    assert rental.payment_id == payment.id

    # 1:1 also reachable by rental id.
    by_rental = wiring.payment_repo.get_by_rental(rental.id)
    assert by_rental is payment


def test_hu01_estimated_total_is_sum_of_items(user_id):
    """Estimated total equals the sum of the items' estimated amounts."""
    wiring, station, bikes, fare, command = _setup_three_available(user_id)

    result = wiring.use_case.execute(command)
    rental = wiring.rental_repo.get(result.rental_id)

    expected = fare.estimated_amount() * 3
    assert rental.estimated_total == expected

    payment = wiring.payment_repo.get(result.payment_id)
    assert payment.authorized_amount == expected


def test_hu01_station_inventory_decremented_by_n(user_id):
    """UC-01 step 7 / RN-01: executing the use case decrements the origin
    station's inventory by N (end-to-end via the StationRepository), and the
    decrement is persisted (observable after execute)."""
    wiring, station, bikes, fare, command = _setup_three_available(user_id)
    assert station.available_inventory == 5  # precondition

    wiring.use_case.execute(command)

    stored_station = wiring.station_repo.get(station.id)
    assert stored_station.available_inventory == 5 - len(bikes) == 2
