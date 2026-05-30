"""Bicycle and Station entities.

``Bicycle`` carries the minimal location for this increment as ``station_id``
(the full BICYCLE_LOCATION projection and MOVEMENT log are out of scope of the
backlog). Identity is by ``id``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

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
