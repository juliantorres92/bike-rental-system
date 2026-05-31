"""Bicycle and Station entities.

``Bicycle`` carries the minimal location for this increment as ``station_id``
(the full BICYCLE_LOCATION projection and MOVEMENT log are out of scope of the
backlog). Identity is by ``id``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..rental.errors import StationFullError
from ..shared.ids import BicycleId, StationId
from .enums import BicycleStatus


class IllegalBicycleTransition(Exception):
    """A bicycle state transition not allowed by the state machine (RN-12)."""


@dataclass
class Bicycle:
    """A rentable unit. Identity is ``id`` (modelo §5.3)."""

    id: BicycleId
    code: str
    status: BicycleStatus = BicycleStatus.DISPONIBLE
    station_id: Optional[StationId] = None
    version: int = 0

    def is_available(self) -> bool:
        """RN-02/RN-18: available means ``disponible`` AND physically at a station."""
        return self.status is BicycleStatus.DISPONIBLE and self.station_id is not None

    def is_at_station(self, station_id: StationId) -> bool:
        return self.station_id == station_id

    def is_returnable(self) -> bool:
        """RN-12 (UC-02): a bicycle can be returned only from ``rentada``.

        Pre-validation guard mirroring :meth:`is_available` for UC-01: lets a use
        case check the ``rentada -> disponible`` precondition BEFORE mutating, so
        the atomic commit never reaches :meth:`return_to` on an illegal source
        state. Same condition the transition guard enforces.
        """
        return self.status is BicycleStatus.RENTADA

    def rent(self) -> None:
        """Transition disponible -> rentada (RN-11/RN-12).

        Clears ``station_id`` because a rented bike is in the customer's hands
        and counts in no station's inventory (RN-01). Only legal from
        ``disponible``; any other source state is a domain error.
        """
        if self.status is not BicycleStatus.DISPONIBLE:
            raise IllegalBicycleTransition(
                f"Cannot rent bicycle {self.code}: status is {self.status.value}, "
                "only 'disponible' -> 'rentada' is allowed"
            )
        self.status = BicycleStatus.RENTADA
        self.station_id = None
        self.version += 1

    def return_to(self, station_id: StationId) -> None:
        """Transition rentada -> disponible at ``station_id`` (UC-02, RN-12).

        Symmetric inverse of :meth:`rent`. The destination may differ from the
        origin station — relocation is allowed in E-04 with no extra charge.
        Only legal from ``rentada``; any other source state is a domain error.
        """
        if self.status is not BicycleStatus.RENTADA:
            raise IllegalBicycleTransition(
                f"Cannot return bicycle {self.code}: status is {self.status.value}, "
                "only 'rentada' -> 'disponible' is allowed"
            )
        self.status = BicycleStatus.DISPONIBLE
        self.station_id = station_id
        self.version += 1


@dataclass
class Station:
    """A physical point with capacity and materialized inventory (modelo §5.2)."""

    id: StationId
    code: str
    name: str
    capacity: int
    available_inventory: int

    def __post_init__(self) -> None:
        if self.capacity <= 0:
            raise ValueError("Station capacity must be > 0")
        if not (0 <= self.available_inventory <= self.capacity):
            raise ValueError(
                "available_inventory must satisfy 0 <= inventory <= capacity"
            )

    def decrement_inventory(self, count: int) -> None:
        """UC-01 step 7: decrement N units when a rental is confirmed (RN-01)."""
        if count < 0:
            raise ValueError("Cannot decrement inventory by a negative amount")
        if self.available_inventory - count < 0:
            raise ValueError(
                f"Station {self.code} has insufficient inventory: "
                f"{self.available_inventory} available, {count} requested"
            )
        self.available_inventory -= count

    def increment_inventory(self, count: int) -> None:
        """UC-02 (RN-16/RN-01): increment N units when bicycles are returned
        here. Symmetric inverse of :meth:`decrement_inventory`, preserving the
        ``0 <= inventory <= capacity`` invariant validated in ``__post_init__``.

        Raises :class:`StationFullError` (a ``RentalError``) — not ``ValueError`` —
        when the increment would exceed capacity (RN-15/RN-03), so the use case's
        atomic pre-validation can catch it as a domain error before mutating."""
        if count < 0:
            raise ValueError("Cannot increment inventory by a negative amount")
        if self.available_inventory + count > self.capacity:
            raise StationFullError(
                f"Station {self.code} is full: {self.available_inventory} of "
                f"{self.capacity} occupied, {count} more cannot be returned"
            )
        self.available_inventory += count
