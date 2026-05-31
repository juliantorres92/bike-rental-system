"""ReturnBicycles use case (UC-02): return one or more bicycles of a rental.

Atomicity at the domain level (RN-05, mirroring UC-01): validate EVERYTHING and
buffer all computed values BEFORE mutating anything. The only mutations and
persistence happen in the final commit step, and only after every pre-condition
has been checked, so the in-memory writes cannot raise. On any failure the use
case raises a domain error and leaves NO side effects: no item becomes
'devuelto', no bicycle becomes 'disponible', no station inventory changes.

OUT OF SCOPE (E-04, intentional): payment settlement (capture/refund) and the
relocation charge. The authorized payment is kept untouched; returning at a
station other than the origin is allowed with NO extra charge. No id minting and
no PaymentGateway/PaymentRepository are involved.

TRANSACTIONAL BOUNDARY: the final commit performs several writes (items ->
devuelto, rental status re-derived + closed_at, bicycles -> disponible at
destination, station inventory incremented, rental persisted) that must succeed
as a unit. The real transactional guarantee belongs to the infrastructure
adapter (ADR-0008); here the up-front validation ensures the commit cannot leave
a half-done state.

Python 3.9 compatible: ``from __future__ import annotations`` + ``typing``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple

from ...bicycle.entities import Bicycle
from ...fare.enums import TimeUnit
from ...shared.ids import BicycleId, RentalId, StationId
from ...shared.money import Money
from ..entities import Rental, RentalItem
from ..enums import RentalStatus
from ..errors import (
    BicycleNotFoundError,
    BicycleNotInRentalError,
    BicycleNotReturnableError,
    DuplicateBicycleError,
    EmptyRentalError,
    RentalItemAlreadyReturnedError,
    RentalNotActiveError,
    RentalNotFoundError,
    StationFullError,
    StationNotFoundError,
)
from ..ports import (
    BicycleRepository,
    Clock,
    RentalRepository,
    StationRepository,
)

# Minutes per fare time unit (RN-09), used to convert elapsed minutes into
# billable units (RN-10) over the frozen snapshot.
_MINUTES_PER_UNIT: Dict[TimeUnit, int] = {
    TimeUnit.MINUTO: 1,
    TimeUnit.HORA: 60,
    TimeUnit.DIA: 1440,
}

_RETURNABLE_STATUSES = (
    RentalStatus.ACTIVA,
    RentalStatus.PARCIALMENTE_DEVUELTA,
)


@dataclass(frozen=True)
class ReturnBicyclesCommand:
    """Immutable input. ``bicycle_ids`` must be non-empty and duplicate-free."""

    rental_id: RentalId
    bicycle_ids: List[BicycleId]
    return_station_id: StationId


class ReturnBicycles:
    def __init__(
        self,
        *,
        rental_repo: RentalRepository,
        bicycle_repo: BicycleRepository,
        station_repo: StationRepository,
        clock: Clock,
    ) -> None:
        self._rentals = rental_repo
        self._bicycles = bicycle_repo
        self._stations = station_repo
        self._clock = clock

    def execute(self, command: ReturnBicyclesCommand) -> Rental:
        # --- Step 1: validate the command shape (no reads/mutations yet) ---
        if not command.bicycle_ids:
            raise EmptyRentalError(
                "A return must include at least one bicycle (RN-04)"
            )
        if len(set(command.bicycle_ids)) != len(command.bicycle_ids):
            raise DuplicateBicycleError(
                "The same bicycle cannot appear twice in one return"
            )

        # --- Step 2: load the rental; guard its status (RN-12) ---
        rental = self._rentals.get(command.rental_id)
        if rental is None:
            raise RentalNotFoundError(f"Rental not found: {command.rental_id}")
        # apply_return guards the status, but we check up front so no station/
        # bicycle reads or computations happen for a non-returnable rental.
        if rental.status not in _RETURNABLE_STATUSES:
            raise RentalNotActiveError(
                f"Cannot return against rental in status '{rental.status.value}': "
                "only 'activa'/'parcialmente_devuelta' allow returns (RN-12)"
            )

        # --- Step 3: resolve each bicycle to an ACTIVE item of THIS rental ---
        matched: List[Tuple[BicycleId, RentalItem]] = []
        for bid in command.bicycle_ids:
            item = rental.find_active_item_by_bicycle(bid)
            if item is None:
                if rental.has_item_for_bicycle(bid):
                    raise RentalItemAlreadyReturnedError(
                        f"Bicycle {bid} is already returned in rental "
                        f"{command.rental_id}"
                    )
                raise BicycleNotInRentalError(
                    f"Bicycle {bid} is not an active item of rental "
                    f"{command.rental_id}"
                )
            matched.append((bid, item))

        # --- Step 4: load destination station; capacity pre-check (RN-15/RN-03) ---
        station = self._stations.get(command.return_station_id)
        if station is None:
            raise StationNotFoundError(
                f"Return station not found: {command.return_station_id}"
            )
        n = len(matched)
        if station.available_inventory + n > station.capacity:
            raise StationFullError(
                f"Station {station.code} is full: {station.available_inventory} "
                f"of {station.capacity} occupied, {n} returns do not fit "
                "(RN-15/RN-03)"
            )

        # --- Step 5: load the bicycles; any missing -> error (defensive) ---
        found = self._bicycles.get_many(command.bicycle_ids)
        by_id: Dict[BicycleId, Bicycle] = {b.id: b for b in found}
        missing = [bid for bid in command.bicycle_ids if bid not in by_id]
        if missing:
            raise BicycleNotFoundError(f"Bicycles not found: {missing}")

        # --- Step 5b: pre-validate the 'rentada' -> 'disponible' guard (RN-12) ---
        # Mirrors CreateRental's availability pre-check (step 4): the bicycle
        # transition is the one commit mutation that could raise on an
        # unvalidated condition, so we assert each matched bike is RENTADA HERE,
        # before any apply_return/return_to. Defends the cross-aggregate
        # invariant 'active item <=> RENTADA bicycle' and keeps the commit
        # raise-free, preserving atomicity (validate before mutate, RN-05).
        not_returnable = [
            by_id[bid].code for bid in command.bicycle_ids if not by_id[bid].is_returnable()
        ]
        if not_returnable:
            raise BicycleNotReturnableError(
                "Bicycles are not in 'rentada' status and cannot be returned "
                f"(RN-12): {not_returnable}"
            )

        # --- Step 6: compute time + money per item from the FROZEN snapshot ---
        # Buffered only; nothing is mutated yet (RN-08/RN-10). No relocation charge.
        now = self._clock.now()
        returned: List[Tuple[RentalItem, StationId, int, Money]] = []
        for bid, item in matched:
            usage_minutes = _elapsed_minutes(item.started_at, now)
            units = _billable_units(usage_minutes, item.fare_time_unit)
            final_amount = item.fare_fixed_component + (
                item.fare_time_component * units
            )
            returned.append(
                (item, command.return_station_id, usage_minutes, final_amount)
            )

        # --- Step 7: ATOMIC COMMIT (pre-validated, cannot raise) ---
        # 7a. Mark items 'devuelto', re-derive rental status, set closed_at.
        rental.apply_return(returned, returned_at=now)
        # 7b. Bicycles rentada -> disponible at the destination (relocation OK).
        #     Source state pre-validated in step 5b, so return_to cannot raise.
        bikes = [by_id[bid] for bid in command.bicycle_ids]
        for bike in bikes:
            bike.return_to(command.return_station_id)
        # 7c. Destination station inventory += N (RN-16/RN-01).
        station.increment_inventory(n)
        # 7d. Persist together. Payment untouched (out of scope E-04).
        self._bicycles.save_all(bikes)
        self._stations.save(station)
        self._rentals.add(rental)  # add() overwrites by id (in-memory upsert)

        # --- Step 8: return the updated rental aggregate ---
        return rental


def _elapsed_minutes(started_at, now) -> int:
    """Whole elapsed minutes from ``started_at`` to ``now`` (RN-10), floored at 0."""
    delta = now - started_at
    minutes = int(delta.total_seconds() // 60)
    return max(minutes, 0)


def _billable_units(usage_minutes: int, time_unit: TimeUnit) -> int:
    """Billable units over ``time_unit`` (ceil), with a minimum of 1 (RN-10)."""
    per_unit = _MINUTES_PER_UNIT[time_unit]
    units = math.ceil(usage_minutes / per_unit)
    return max(units, 1)
