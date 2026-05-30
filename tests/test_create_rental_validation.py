"""CreateRental validation: an inactive fare is rejected (InactiveFareError).

The use case validates that the fare is the currently-effective version before
any mutation (RN-07/RN-08, step 4). A non-active fare must abort with no side
effects.
"""

from __future__ import annotations

import pytest

from tests.conftest import build_wiring, make_bicycle, make_fare, make_station
from bike_rental.bicycle.enums import BicycleStatus
from bike_rental.rental.errors import InactiveFareError
from bike_rental.rental.use_cases.create_rental import CreateRentalCommand


def test_inactive_fare_is_rejected_with_no_side_effects(user_id):
    station = make_station(inventory=5)
    bikes = [make_bicycle(station_id=station.id, code=f"BIKE-{i}") for i in (1, 2)]
    wiring = build_wiring(bicycles=bikes, stations=[station])
    command = CreateRentalCommand(
        user_id=user_id,
        station_id=station.id,
        bicycle_ids=[b.id for b in bikes],
        fare=make_fare(is_active=False),
    )

    with pytest.raises(InactiveFareError):
        wiring.use_case.execute(command)

    # No side effects: bikes still available, gateway never called, inventory intact.
    for bike in bikes:
        assert wiring.bicycle_repo.get(bike.id).status is BicycleStatus.DISPONIBLE
    assert wiring.gateway.calls == []
    assert wiring.station_repo.get(station.id).available_inventory == 5
    assert wiring.rental_repo.list_active_bicycle_ids() == set()
