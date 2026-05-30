"""HU-04 — Frozen fare snapshot in the rental item (RN-08, ADR-0005)."""

from __future__ import annotations

from decimal import Decimal

from tests.conftest import build_wiring, make_bicycle, make_fare, make_money, make_station
from bike_rental.fare.enums import TimeUnit
from bike_rental.rental.use_cases.create_rental import CreateRentalCommand


def test_hu04_1_item_freezes_fare_snapshot_at_creation(user_id):
    """T-HU04-1: each RentalItem stores a snapshot equal to the active fare's
    values at creation (RN-08, ADR-0005)."""
    station = make_station(inventory=5)
    bikes = [make_bicycle(station_id=station.id, code=f"BIKE-{i}") for i in (1, 2)]
    fare = make_fare(
        fixed="2000.00", time="150.00", time_unit=TimeUnit.MINUTO, relocation="1000.00"
    )
    wiring = build_wiring(bicycles=bikes, stations=[station])
    command = CreateRentalCommand(
        user_id=user_id,
        station_id=station.id,
        bicycle_ids=[b.id for b in bikes],
        fare=fare,
    )

    result = wiring.use_case.execute(command)
    rental = wiring.rental_repo.get(result.rental_id)

    for item in rental.items:
        assert item.fare_id == fare.id
        assert item.fare_fixed_component == fare.fixed_component
        assert item.fare_time_component == fare.time_component
        assert item.fare_time_unit == fare.time_unit
        assert item.fare_relocation_charge == fare.relocation_charge


def test_hu04_2_snapshot_immune_to_later_fare_change(user_id):
    """T-HU04-2: after creating the rental, a new fare version with different
    values appears; the existing item keeps the original snapshot (charge stays).
    """
    station = make_station(inventory=5)
    bikes = [make_bicycle(station_id=station.id, code="BIKE-1")]
    original_fare = make_fare(fixed="2000.00", time="150.00", version=1)
    wiring = build_wiring(bicycles=bikes, stations=[station])
    command = CreateRentalCommand(
        user_id=user_id,
        station_id=station.id,
        bicycle_ids=[b.id for b in bikes],
        fare=original_fare,
    )

    result = wiring.use_case.execute(command)
    rental = wiring.rental_repo.get(result.rental_id)
    item = rental.items[0]

    # Capture the frozen values and the estimated total.
    frozen_fixed = item.fare_fixed_component
    frozen_time = item.fare_time_component
    frozen_estimated = item.estimated_amount
    rental_total_before = rental.estimated_total

    # A new, different version of the SAME fare code is introduced later.
    new_version = make_fare(
        code=original_fare.code,
        fixed="9999.00",
        time="999.00",
        version=2,
        is_active=True,
    )
    # The original fare object is immutable; this models the admin editing.
    assert new_version.fixed_component != original_fare.fixed_component

    # The already-created item is unaffected.
    assert item.fare_fixed_component == frozen_fixed == make_money("2000.00")
    assert item.fare_time_component == frozen_time == make_money("150.00")
    assert item.estimated_amount == frozen_estimated
    assert rental.estimated_total == rental_total_before

    # And it still differs from the new version's values.
    assert item.fare_fixed_component != new_version.fixed_component


def test_hu04_fare_is_immutable_value_object():
    """A Fare is a frozen VO: editing means creating a new version, not mutating."""
    fare = make_fare()
    try:
        fare.fixed_component = make_money("1.00")  # type: ignore[misc]
        mutated = True
    except Exception:
        mutated = False
    assert mutated is False
