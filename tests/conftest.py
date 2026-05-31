"""Shared pytest fixtures and builders for the CreateRental tests.

Ensures ``src`` is importable without installing the package, then exposes
factory helpers and a wired-up use case fixture.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from decimal import Decimal
from typing import List

import pytest

# Make ``src`` importable when running pytest from the repo root without install.
_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from bike_rental.adapters.fake_payment_gateway import (  # noqa: E402
    AUTHORIZE,
    REJECT,
    FakePaymentGateway,
)
from bike_rental.adapters.fixed_clock import (  # noqa: E402
    DeterministicIdGenerator,
    FixedClock,
    utc,
)
from bike_rental.adapters.in_memory_bicycle_repository import (  # noqa: E402
    InMemoryBicycleRepository,
)
from bike_rental.adapters.in_memory_payment_repository import (  # noqa: E402
    InMemoryPaymentRepository,
)
from bike_rental.adapters.in_memory_rental_repository import (  # noqa: E402
    InMemoryRentalRepository,
)
from bike_rental.adapters.in_memory_station_repository import (  # noqa: E402
    InMemoryStationRepository,
)
from bike_rental.bicycle.entities import Bicycle, Station  # noqa: E402
from bike_rental.bicycle.enums import BicycleStatus  # noqa: E402
from bike_rental.fare.entities import Fare  # noqa: E402
from bike_rental.fare.enums import TimeUnit  # noqa: E402
from bike_rental.rental.use_cases.create_rental import CreateRental  # noqa: E402
from bike_rental.rental.use_cases.return_bicycles import ReturnBicycles  # noqa: E402
from bike_rental.shared.ids import (  # noqa: E402
    new_bicycle_id,
    new_fare_id,
    new_station_id,
    new_user_id,
)
from bike_rental.shared.money import Money  # noqa: E402


def make_money(value: str) -> Money:
    return Money(Decimal(value))


def make_station(*, capacity: int = 10, inventory: int = 5) -> Station:
    return Station(
        id=new_station_id(),
        code="ST-001",
        name="Estacion Centro",
        capacity=capacity,
        available_inventory=inventory,
    )


def make_bicycle(
    *,
    station_id,
    code: str,
    status: BicycleStatus = BicycleStatus.DISPONIBLE,
) -> Bicycle:
    return Bicycle(
        id=new_bicycle_id(),
        code=code,
        status=status,
        station_id=station_id if status is BicycleStatus.DISPONIBLE else None,
    )


def make_fare(
    *,
    fixed: str = "2000.00",
    time: str = "150.00",
    time_unit: TimeUnit = TimeUnit.MINUTO,
    relocation: str = "1000.00",
    version: int = 1,
    is_active: bool = True,
    code: str = "STANDARD",
) -> Fare:
    return Fare(
        id=new_fare_id(),
        code=code,
        fixed_component=make_money(fixed),
        time_component=make_money(time),
        time_unit=time_unit,
        relocation_charge=make_money(relocation),
        version=version,
        is_active=is_active,
    )


@dataclass
class Wiring:
    """Bundle of adapters + the use case for convenient access in tests."""

    bicycle_repo: InMemoryBicycleRepository
    station_repo: InMemoryStationRepository
    rental_repo: InMemoryRentalRepository
    payment_repo: InMemoryPaymentRepository
    gateway: FakePaymentGateway
    clock: FixedClock
    ids: DeterministicIdGenerator
    use_case: CreateRental
    return_use_case: ReturnBicycles


def build_wiring(
    *,
    bicycles: List[Bicycle],
    stations: List[Station] = (),
    outcome: str = AUTHORIZE,
) -> Wiring:
    bicycle_repo = InMemoryBicycleRepository(bicycles)
    station_repo = InMemoryStationRepository(stations)
    rental_repo = InMemoryRentalRepository()
    payment_repo = InMemoryPaymentRepository()
    gateway = FakePaymentGateway(outcome=outcome)
    clock = FixedClock(utc(2026, 5, 30, 12, 0))
    ids = DeterministicIdGenerator()
    use_case = CreateRental(
        bicycle_repo=bicycle_repo,
        station_repo=station_repo,
        rental_repo=rental_repo,
        payment_repo=payment_repo,
        payment_gateway=gateway,
        clock=clock,
        id_generator=ids,
    )
    return_use_case = ReturnBicycles(
        rental_repo=rental_repo,
        bicycle_repo=bicycle_repo,
        station_repo=station_repo,
        clock=clock,
    )
    return Wiring(
        bicycle_repo=bicycle_repo,
        station_repo=station_repo,
        rental_repo=rental_repo,
        payment_repo=payment_repo,
        gateway=gateway,
        clock=clock,
        ids=ids,
        use_case=use_case,
        return_use_case=return_use_case,
    )


@pytest.fixture
def user_id():
    return new_user_id()


# Re-export commonly used symbols for tests.
__all__ = [
    "AUTHORIZE",
    "REJECT",
    "Bicycle",
    "BicycleStatus",
    "Fare",
    "Station",
    "TimeUnit",
    "Wiring",
    "build_wiring",
    "make_bicycle",
    "make_fare",
    "make_money",
    "make_station",
]
