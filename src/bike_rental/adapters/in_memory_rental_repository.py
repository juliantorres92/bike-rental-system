"""In-memory RentalRepository.

``list_active_bicycle_ids`` walks rentals whose status is 'activa' or
'parcialmente_devuelta' and returns the bicycle ids of their 'activo' items
(supports RN-06).
"""

from __future__ import annotations

from typing import Dict, Optional, Set

from ..rental.entities import Rental
from ..rental.enums import RentalItemStatus, RentalStatus
from ..rental.ports import RentalRepository
from ..shared.ids import BicycleId, RentalId

_ACTIVE_RENTAL_STATUSES = {
    RentalStatus.ACTIVA,
    RentalStatus.PARCIALMENTE_DEVUELTA,
}


class InMemoryRentalRepository(RentalRepository):
    def __init__(self) -> None:
        self._store: Dict[RentalId, Rental] = {}

    def add(self, rental: Rental) -> None:
        self._store[rental.id] = rental

    def get(self, rental_id: RentalId) -> Optional[Rental]:
        return self._store.get(rental_id)

    def list_active_bicycle_ids(self) -> Set[BicycleId]:
        active: Set[BicycleId] = set()
        for rental in self._store.values():
            if rental.status not in _ACTIVE_RENTAL_STATUSES:
                continue
            for item in rental.items:
                if item.status is RentalItemStatus.ACTIVO:
                    active.add(item.bicycle_id)
        return active
