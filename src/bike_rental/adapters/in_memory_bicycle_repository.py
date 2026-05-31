"""In-memory BicycleRepository.

Seeded in the constructor. ``save``/``save_all`` overwrite; ``get_many`` returns
only the bicycles found. Nothing is persisted until the use case calls
``save_all`` explicitly — this is key for testing RN-05: if nothing is saved,
no bicycle is left 'rentada'.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence

from ..bicycle.entities import Bicycle
from ..shared.ids import BicycleId, StationId
from ..rental.ports import BicycleRepository


class InMemoryBicycleRepository(BicycleRepository):
    def __init__(self, bicycles: Iterable[Bicycle] = ()) -> None:
        self._store: Dict[BicycleId, Bicycle] = {b.id: b for b in bicycles}

    def get(self, bicycle_id: BicycleId) -> Optional[Bicycle]:
        return self._store.get(bicycle_id)

    def get_many(self, bicycle_ids: Sequence[BicycleId]) -> List[Bicycle]:
        return [self._store[bid] for bid in bicycle_ids if bid in self._store]

    def list_by_station(self, station_id: StationId) -> List[Bicycle]:
        # Read-only (HU-11): a rented bike has station_id=None -> excluded.
        return [b for b in self._store.values() if b.station_id == station_id]

    def save(self, bicycle: Bicycle) -> None:
        self._store[bicycle.id] = bicycle

    def save_all(self, bicycles: Sequence[Bicycle]) -> None:
        for bicycle in bicycles:
            self._store[bicycle.id] = bicycle
