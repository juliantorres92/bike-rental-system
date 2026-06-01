"""Ports (driven side of the hexagon, ADR-0008).

Abstract interfaces the domain depends on; in-memory adapters implement them.
The domain NEVER imports a framework or performs real I/O.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Sequence, Set

from ..inventory.entities import Bicycle, Station
from ..payment.entities import Payment
from ..shared.ids import (
    BicycleId,
    PaymentId,
    RentalId,
    RentalItemId,
    StationId,
)
from ..shared.money import Money
from .entities import Rental


@dataclass(frozen=True)
class PaymentAuthorization:
    """Result of a gateway authorization attempt."""

    approved: bool
    reference: Optional[str] = None


class BicycleRepository(ABC):
    @abstractmethod
    def get(self, bicycle_id: BicycleId) -> Optional[Bicycle]: ...

    @abstractmethod
    def get_many(self, bicycle_ids: Sequence[BicycleId]) -> List[Bicycle]:
        """Return only the bicycles found (missing ids are simply absent)."""

    @abstractmethod
    def list_by_station(self, station_id: StationId) -> List[Bicycle]:
        """Read-only (HU-11): bicycles currently located at ``station_id``.

        A rented bike has ``station_id=None`` and is therefore excluded.
        """

    @abstractmethod
    def save(self, bicycle: Bicycle) -> None: ...

    @abstractmethod
    def save_all(self, bicycles: Sequence[Bicycle]) -> None: ...


class RentalRepository(ABC):
    @abstractmethod
    def add(self, rental: Rental) -> None: ...

    @abstractmethod
    def get(self, rental_id: RentalId) -> Optional[Rental]: ...

    @abstractmethod
    def list_active_bicycle_ids(self) -> Set[BicycleId]:
        """RN-06: bicycle ids of active items across active rentals."""


class StationRepository(ABC):
    @abstractmethod
    def get(self, station_id: StationId) -> Optional[Station]:
        """Load the origin station (UC-01 step 7 / RN-01 inventory)."""

    @abstractmethod
    def list_stations(self) -> List[Station]:
        """Read-only (HU-10): all seeded stations, in insertion order."""

    @abstractmethod
    def save(self, station: Station) -> None:
        """Persist the station after decrementing its inventory (RN-01)."""


class PaymentRepository(ABC):
    @abstractmethod
    def add(self, payment: Payment) -> None: ...

    @abstractmethod
    def get(self, payment_id: PaymentId) -> Optional[Payment]: ...

    @abstractmethod
    def get_by_rental(self, rental_id: RentalId) -> Optional[Payment]: ...


class PaymentGateway(ABC):
    @abstractmethod
    def authorize(
        self, idempotency_key: str, amount: Money
    ) -> PaymentAuthorization: ...


class Clock(ABC):
    @abstractmethod
    def now(self) -> datetime: ...


class IdGenerator(ABC):
    @abstractmethod
    def new_rental_id(self) -> RentalId: ...

    @abstractmethod
    def new_rental_item_id(self) -> RentalItemId: ...

    @abstractmethod
    def new_payment_id(self) -> PaymentId: ...
