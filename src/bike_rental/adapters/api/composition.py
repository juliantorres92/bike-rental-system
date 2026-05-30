"""In-memory composition root for the HTTP adapter (ADR-0008, E-02).

``InMemoryWorld`` is the driving-side composition root: it builds and wires every
existing in-memory driven adapter, seeds deterministic data, and exposes the
ready-to-use ``CreateRental`` use case plus the seeded active ``Fare``.

There is no ``FareRepository`` in this increment (out of scope of E-02): the API
applies a single active fare seeded here and injected into the
``CreateRentalCommand`` by the route handler.

The class is parameterizable for tests (number of bicycles, payment outcome,
active/inactive fare, an unavailable bicycle, a bicycle pre-seeded into an active
rental) and offers ``with_defaults()`` for the normal app boot.

Python 3.9 compatible: ``from __future__ import annotations`` + ``typing.List``.
"""

from __future__ import annotations

from decimal import Decimal
from typing import List, Optional
from uuid import UUID, uuid4

from ...bicycle.entities import Bicycle, Station
from ...bicycle.enums import BicycleStatus
from ...fare.entities import Fare
from ...fare.enums import TimeUnit
from ...payment.entities import Payment
from ...rental.entities import Rental, RentalItem
from ...rental.use_cases.create_rental import CreateRental
from ...shared.ids import (
    BicycleId,
    FareId,
    PaymentId,
    StationId,
    UserId,
    new_rental_id,
    new_rental_item_id,
)
from ...shared.money import Money
from ..fake_payment_gateway import AUTHORIZE, FakePaymentGateway
from ..fixed_clock import FixedClock, UuidGenerator, utc
from ..in_memory_bicycle_repository import InMemoryBicycleRepository
from ..in_memory_payment_repository import InMemoryPaymentRepository
from ..in_memory_rental_repository import InMemoryRentalRepository
from ..in_memory_station_repository import InMemoryStationRepository

# Fixed ids for the happy-path seed, so a running server has STABLE ids the
# Postman collection / docs can reference (the optional 404/409 fixtures keep
# using random ids — their value is irrelevant). Aligns with "deterministic
# data" and makes `POST /rentals` runnable out of the box.
_STATION_ID = StationId(UUID("11111111-1111-1111-1111-111111111111"))
_USER_ID = UserId(UUID("22222222-2222-2222-2222-222222222222"))


def _seed_bicycle_id(i: int) -> BicycleId:
    return BicycleId(UUID(f"a0000000-0000-0000-0000-{i:012d}"))


class InMemoryWorld:
    """Wires the in-memory adapters and seeds deterministic data.

    Public attributes for tests:
    - ``station_id``      : the seeded origin station id.
    - ``bicycle_ids``     : ids of the seeded available bicycles (the ones a
                            happy-path request should use).
    - ``user_id``         : a seeded user id.
    - ``unknown_bicycle_id`` / ``unknown_station_id`` : syntactically valid ids
                            that are NOT seeded (to force 404s).
    - ``unavailable_bicycle_id`` : id of a bicycle seeded as not available
                            (when ``with_unavailable_bicycle=True``) -> 409.
    - ``already_rented_bicycle_id`` : id of a bicycle that is available at the
                            station BUT already part of a seeded active rental
                            (when ``with_active_rental=True``) -> 409.
    - ``active_fare``     : the fare the app injects into the command.
    - ``use_case``        : the wired ``CreateRental``.
    - ``gateway``         : the ``FakePaymentGateway`` (inspect ``.calls``).
    - ``rental_repo`` / ``bicycle_repo`` / ``station_repo`` / ``payment_repo``.
    """

    def __init__(
        self,
        *,
        bicycle_count: int = 3,
        payment_outcome: str = AUTHORIZE,
        fare_active: bool = True,
        with_unavailable_bicycle: bool = False,
        with_active_rental: bool = False,
    ) -> None:
        # --- Seeded ids: happy-path ids are fixed (stable for docs/Postman);
        #     the not-seeded ids stay random (only used to force 404s) ---
        self.station_id: StationId = _STATION_ID
        self.user_id: UserId = _USER_ID
        self.unknown_bicycle_id: BicycleId = BicycleId(uuid4())
        self.unknown_station_id: StationId = StationId(uuid4())

        self.unavailable_bicycle_id: Optional[BicycleId] = None
        self.already_rented_bicycle_id: Optional[BicycleId] = None

        # --- Available bicycles (the happy-path set) ---
        bicycles: List[Bicycle] = []
        self.bicycle_ids: List[BicycleId] = []
        for i in range(1, bicycle_count + 1):
            bid = _seed_bicycle_id(i)
            self.bicycle_ids.append(bid)
            bicycles.append(
                Bicycle(
                    id=bid,
                    code=f"BIKE-{i}",
                    status=BicycleStatus.DISPONIBLE,
                    station_id=self.station_id,
                )
            )

        # --- Optional: an explicitly unavailable bicycle (RENTADA) -> 409 ---
        if with_unavailable_bicycle:
            self.unavailable_bicycle_id = BicycleId(uuid4())
            bicycles.append(
                Bicycle(
                    id=self.unavailable_bicycle_id,
                    code="BIKE-UNAVAILABLE",
                    status=BicycleStatus.RENTADA,
                    station_id=None,
                )
            )

        # --- Optional: a bicycle available at the station but already inside an
        #     active rental, to force BicycleAlreadyRentedError (RN-06) -> 409 ---
        active_rental: Optional[Rental] = None
        if with_active_rental:
            self.already_rented_bicycle_id = BicycleId(uuid4())
            bicycles.append(
                Bicycle(
                    id=self.already_rented_bicycle_id,
                    code="BIKE-ACTIVE",
                    status=BicycleStatus.DISPONIBLE,
                    station_id=self.station_id,
                )
            )

        # --- Station: capacity/inventory big enough for the seeded set ---
        capacity = max(bicycle_count + 2, 5)
        station = Station(
            id=self.station_id,
            code="ST-01",
            name="Centro",
            capacity=capacity,
            available_inventory=bicycle_count,
        )

        # --- Active fare (no FareRepository; injected by the app) ---
        self.active_fare: Fare = Fare(
            id=FareId(uuid4()),
            code="STD",
            fixed_component=Money(Decimal("1000")),
            time_component=Money(Decimal("200")),
            time_unit=TimeUnit.MINUTO,
            relocation_charge=None,
            version=1,
            is_active=fare_active,
        )

        # --- Wire the driven adapters ---
        self.bicycle_repo = InMemoryBicycleRepository(bicycles)
        self.station_repo = InMemoryStationRepository([station])
        self.rental_repo = InMemoryRentalRepository()
        self.payment_repo = InMemoryPaymentRepository()
        self.gateway = FakePaymentGateway(outcome=payment_outcome)
        self.clock = FixedClock(utc(2026, 5, 30))
        self.id_generator = UuidGenerator()

        # --- Seed the active rental AFTER wiring (uses an active fare snapshot) ---
        if active_rental is None and with_active_rental:
            active_rental = self._build_active_rental(
                bicycle_id=self.already_rented_bicycle_id
            )
        if active_rental is not None:
            self.rental_repo.add(active_rental)
            payment = Payment.authorized(
                id=PaymentId(uuid4()),
                rental_id=active_rental.id,
                amount=active_rental.estimated_total,
                gateway_reference="SEED-AUTH",
                authorized_at=self.clock.now(),
            )
            self.payment_repo.add(payment)

        # --- The use case (exact constructor kwargs) ---
        self.use_case: CreateRental = CreateRental(
            bicycle_repo=self.bicycle_repo,
            station_repo=self.station_repo,
            rental_repo=self.rental_repo,
            payment_repo=self.payment_repo,
            payment_gateway=self.gateway,
            clock=self.clock,
            id_generator=self.id_generator,
        )

    def _build_active_rental(self, *, bicycle_id: BicycleId) -> Rental:
        """Build an already-confirmed ('activa') rental holding ``bicycle_id`` as
        an active item, so ``list_active_bicycle_ids`` reports it (RN-06)."""
        # Use a fresh active fare for the snapshot (is_active state of the world's
        # fare is irrelevant to a pre-existing rental's frozen snapshot).
        seed_fare = Fare(
            id=FareId(uuid4()),
            code="STD",
            fixed_component=Money(Decimal("1000")),
            time_component=Money(Decimal("200")),
            time_unit=TimeUnit.MINUTO,
            relocation_charge=None,
            version=1,
            is_active=True,
        )
        now = utc(2026, 5, 30)
        item = RentalItem.from_fare(
            item_id=new_rental_item_id(),
            bicycle_id=bicycle_id,
            fare=seed_fare,
            started_at=now,
        )
        rental = Rental.create_pending(
            rental_id=new_rental_id(),
            user_id=self.user_id,
            origin_station_id=self.station_id,
            items=[item],
            created_at=now,
        )
        rental.confirm(payment_id=PaymentId(uuid4()), confirmed_at=now)
        return rental

    @classmethod
    def with_defaults(cls) -> "InMemoryWorld":
        """Convenience factory for the normal app boot (3 available bicycles,
        gateway AUTHORIZE, active fare)."""
        return cls()
