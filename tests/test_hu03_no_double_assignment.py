"""HU-03 — No double assignment (RN-06)."""

from __future__ import annotations

import pytest

from tests.conftest import build_wiring, make_bicycle, make_fare, make_station
from bike_rental.bicycle.enums import BicycleStatus
from bike_rental.rental.enums import RentalStatus
from bike_rental.rental.errors import BicycleAlreadyRentedError
from bike_rental.rental.use_cases.create_rental import CreateRentalCommand


def test_hu03_1_bicycle_in_active_rental_cannot_be_rented_again(user_id):
    """T-HU03-1: a bike already in an active rental item; a second create that
    includes it => BicycleAlreadyRentedError; second rental rejected, no effects.
    """
    station = make_station(inventory=5)
    shared_bike = make_bicycle(station_id=station.id, code="BIKE-SHARED")
    other_bike = make_bicycle(station_id=station.id, code="BIKE-OTHER")
    bikes = [shared_bike, other_bike]
    wiring = build_wiring(bicycles=bikes, stations=[station])

    # First rental: takes the shared bike, becomes 'activa'.
    first = CreateRentalCommand(
        user_id=user_id,
        station_id=station.id,
        bicycle_ids=[shared_bike.id],
        fare=make_fare(),
    )
    first_result = wiring.use_case.execute(first)
    assert first_result.status is RentalStatus.ACTIVA
    assert shared_bike.id in wiring.rental_repo.list_active_bicycle_ids()

    # Second rental tries to include the already-rented bike.
    second = CreateRentalCommand(
        user_id=user_id,
        station_id=station.id,
        bicycle_ids=[shared_bike.id, other_bike.id],
        fare=make_fare(),
    )
    calls_before = len(wiring.gateway.calls)
    with pytest.raises(BicycleAlreadyRentedError):
        wiring.use_case.execute(second)

    # The other bike was NOT touched (still available at the station).
    stored_other = wiring.bicycle_repo.get(other_bike.id)
    assert stored_other.status is BicycleStatus.DISPONIBLE
    assert stored_other.station_id == station.id

    # No charge attempted for the rejected second rental (rejected before step 6).
    assert len(wiring.gateway.calls) == calls_before

    # Only the first rental's bike remains the single active assignment.
    assert wiring.rental_repo.list_active_bicycle_ids() == {shared_bike.id}
