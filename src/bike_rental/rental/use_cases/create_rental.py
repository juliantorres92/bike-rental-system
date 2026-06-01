"""CreateRental use case (UC-01): create a multi-bicycle rental atomically.

Atomicity at the domain level (RN-05): validate EVERYTHING before mutating
anything. The only mutations/persistence happen in step 7, and only after the
gateway authorizes. On any failure the use case raises a domain error and
leaves no side effects (no bicycle 'rentada', no active rental, no effective
charge).

TRANSACTIONAL BOUNDARY (RN-05/RN-19, ADR-0008): step 7 performs several writes
(bicycles -> rentada, station inventory decremented, payment persisted, rental
persisted) that must succeed or fail as a unit. The domain expresses the
"all or nothing" intent by (a) validating everything up front so the in-memory
mutations in step 7 cannot raise, and (b) ordering writes so the rental and its
authorized payment are persisted together (RN-19: an active rental always has
an authorized payment). The REAL transactional guarantee — a single commit/
rollback wrapping step 7, plus compensation/reversal of the gateway charge on a
late failure (spec 7a / C-06) — belongs to the infrastructure adapter (ADR-0008
leaves the transactional boundary to the stack). In-memory adapters do not
roll back, so this use case must not leave step 7 half-done; it does not.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from ...inventory.entities import Bicycle
from ...fare.entities import Fare
from ...payment.entities import Payment, idempotency_key_for
from ...shared.ids import BicycleId, PaymentId, RentalId, StationId, UserId
from ..entities import Rental, RentalItem
from ..enums import RentalStatus
from ..errors import (
    BicycleAlreadyRentedError,
    BicycleNotAvailableError,
    BicycleNotFoundError,
    DuplicateBicycleError,
    EmptyRentalError,
    InactiveFareError,
    PaymentDeclinedError,
    StationNotFoundError,
)
from ..ports import (
    BicycleRepository,
    Clock,
    IdGenerator,
    PaymentGateway,
    PaymentRepository,
    RentalRepository,
    StationRepository,
)


@dataclass(frozen=True)
class CreateRentalCommand:
    """Immutable input. ``bicycle_ids`` must have >= 1 element (RN-04)."""

    user_id: UserId
    station_id: StationId
    bicycle_ids: List[BicycleId]
    fare: Fare


@dataclass(frozen=True)
class CreateRentalResult:
    rental_id: RentalId
    payment_id: PaymentId
    status: RentalStatus


class CreateRental:
    def __init__(
        self,
        *,
        bicycle_repo: BicycleRepository,
        station_repo: StationRepository,
        rental_repo: RentalRepository,
        payment_repo: PaymentRepository,
        payment_gateway: PaymentGateway,
        clock: Clock,
        id_generator: IdGenerator,
    ) -> None:
        self._bicycles = bicycle_repo
        self._stations = station_repo
        self._rentals = rental_repo
        self._payments = payment_repo
        self._gateway = payment_gateway
        self._clock = clock
        self._ids = id_generator

    def execute(self, command: CreateRentalCommand) -> CreateRentalResult:
        # --- Step 1: validate the command (no reads/mutations yet) ---
        if not command.bicycle_ids:
            raise EmptyRentalError("A rental must include at least one bicycle (RN-04)")
        if len(set(command.bicycle_ids)) != len(command.bicycle_ids):
            raise DuplicateBicycleError(
                "The same bicycle cannot appear twice in one rental"
            )

        # --- Step 2: load origin station + bicycles; any missing -> error ---
        # Loading happens before any mutation; failures here leave no side effects.
        station = self._stations.get(command.station_id)
        if station is None:
            raise StationNotFoundError(
                f"Origin station not found: {command.station_id}"
            )

        found = self._bicycles.get_many(command.bicycle_ids)
        by_id: Dict[BicycleId, Bicycle] = {b.id: b for b in found}
        missing = [bid for bid in command.bicycle_ids if bid not in by_id]
        if missing:
            raise BicycleNotFoundError(f"Bicycles not found: {missing}")

        # --- Step 3: RN-06 no double assignment (no mutations yet) ---
        active_ids = self._rentals.list_active_bicycle_ids()
        already = [bid for bid in command.bicycle_ids if bid in active_ids]
        if already:
            raise BicycleAlreadyRentedError(
                f"Bicycles already in an active rental: {already}"
            )

        # --- Step 4: RN-02/RN-18 availability + station; fare must be active ---
        for bid in command.bicycle_ids:
            bike = by_id[bid]
            if not (bike.is_available() and bike.is_at_station(command.station_id)):
                raise BicycleNotAvailableError(
                    f"Bicycle {bike.code} is not available at station "
                    f"{command.station_id}"
                )
        if not command.fare.is_active:
            raise InactiveFareError(f"Fare {command.fare.code} is not active")

        # --- Step 5: build everything in memory (no persistence yet) ---
        now = self._clock.now()
        rental_id = self._ids.new_rental_id()
        items: List[RentalItem] = [
            RentalItem.from_fare(
                item_id=self._ids.new_rental_item_id(),
                bicycle_id=bid,
                fare=command.fare,
                started_at=now,
            )
            for bid in command.bicycle_ids
        ]
        rental = Rental.create_pending(
            rental_id=rental_id,
            user_id=command.user_id,
            origin_station_id=command.station_id,
            items=items,
            created_at=now,
        )

        # --- Step 6: RN-19 request authorization ---
        authorization = self._gateway.authorize(
            idempotency_key=idempotency_key_for(rental_id),
            amount=rental.estimated_total,
        )
        if not authorization.approved:
            # UC-01 6a / RN-05: no bicycle mutated, no inventory change, no
            # authorized payment. The rental is recorded as 'fallida' so the
            # outcome is observable (HU-02 criterion 2: "la renta queda
            # fallida"); a failed rental holds no active items, so it never
            # counts in list_active_bicycle_ids (RN-06 unaffected).
            rental.mark_failed()
            self._rentals.add(rental)
            raise PaymentDeclinedError(
                f"Payment declined for rental {rental_id}",
                rental_id=rental_id,
            )

        # --- Step 7: atomic commit (in-memory side) only after authorization ---
        # See module docstring: in a real adapter this whole block is one
        # transaction. Here every operation is pre-validated and cannot raise,
        # so the in-memory writes always complete together.
        confirmed_at = self._clock.now()

        # 7a. Bicycles -> rentada (RN-01: a rented bike counts in no inventory).
        for bid in command.bicycle_ids:
            by_id[bid].rent()
        self._bicycles.save_all([by_id[bid] for bid in command.bicycle_ids])

        # 7b. Decrement the origin station inventory by N (UC-01 §5.2 / RN-01).
        station.decrement_inventory(len(command.bicycle_ids))
        self._stations.save(station)

        # 7c. Persist the authorized payment and the confirmed rental together,
        #     so an active rental always carries an authorized payment (RN-19).
        payment = Payment.authorized(
            id=self._ids.new_payment_id(),
            rental_id=rental_id,
            amount=rental.estimated_total,
            gateway_reference=authorization.reference,
            authorized_at=confirmed_at,
        )
        rental.confirm(payment_id=payment.id, confirmed_at=confirmed_at)
        self._payments.add(payment)
        self._rentals.add(rental)

        # --- Step 8: return result (postconditions of UC-01 hold) ---
        return CreateRentalResult(
            rental_id=rental_id,
            payment_id=payment.id,
            status=rental.status,
        )
