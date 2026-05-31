"""In-memory StationRepository.

Seeded in the constructor. ``get`` returns the live stored entity (so a mutation
followed by ``save`` is observable); ``save`` overwrites. Like the bicycle
repository, nothing is persisted until the use case calls ``save`` explicitly —
key for RN-05: if the use case never saves, the station inventory is unchanged.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from ..bicycle.entities import Station
from ..rental.ports import StationRepository
from ..shared.ids import StationId


class InMemoryStationRepository(StationRepository):
    def __init__(self, stations: Iterable[Station] = ()) -> None:
        self._store: Dict[StationId, Station] = {s.id: s for s in stations}

    def get(self, station_id: StationId) -> Optional[Station]:
        return self._store.get(station_id)

    def list_stations(self) -> List[Station]:
        # Read-only (HU-10): insertion order of the dict store.
        return list(self._store.values())

    def save(self, station: Station) -> None:
        self._store[station.id] = station
