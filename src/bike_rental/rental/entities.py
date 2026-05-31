"""Rental aggregate: RentalItem and Rental.

- ``RentalItem`` stores a frozen SNAPSHOT of the fare's four pricing values
  (RN-08/ADR-0005), plus ``fare_id`` as a trace. The snapshot is the source of
  the charge calculation and is immutable: even if the Fare changes later, the
  item keeps the original values.
- ``Rental`` aggregates 1..N items (RN-04, minimum 1 enforced in construction).
  Its status is DERIVED from the items (ADR-0004) via ``derive_status``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple

from ..fare.entities import Fare
from ..fare.enums import TimeUnit
from ..shared.ids import (
    BicycleId,
    FareId,
    PaymentId,
    RentalId,
    RentalItemId,
    StationId,
    UserId,
)
from ..shared.money import Money
from .enums import RentalItemStatus, RentalStatus
from .errors import (
    IllegalRentalTransition,
    RentalItemAlreadyReturnedError,
    RentalNotActiveError,
)


@dataclass
class RentalItem:
    """A rental line referencing exactly one bicycle (RN-04).

    Holds the frozen fare snapshot (RN-08). ``status`` starts ``activo`` (RN-06:
    a bike is not in two active items). ``final_amount``/``usage_minutes``/
    ``returned_at`` belong to devolution and are out of scope.
    """

    id: RentalItemId
    bicycle_id: BicycleId
    fare_id: FareId
    fare_fixed_component: Money
    fare_time_component: Money
    fare_time_unit: TimeUnit
    fare_relocation_charge: Optional[Money]
    status: RentalItemStatus
    estimated_amount: Money
    started_at: datetime
    # --- Devolution snapshot (UC-02/E-04): all Optional/None at creation so
    #     ``from_fare`` is unchanged. Set only by ``mark_returned``. ---
    returned_at: Optional[datetime] = None
    return_station_id: Optional[StationId] = None
    final_amount: Optional[Money] = None
    usage_minutes: Optional[int] = None

    def is_active(self) -> bool:
        return self.status is RentalItemStatus.ACTIVO

    def is_returned(self) -> bool:
        return self.status is RentalItemStatus.DEVUELTO

    def mark_returned(
        self,
        *,
        return_station_id: StationId,
        returned_at: datetime,
        usage_minutes: int,
        final_amount: Money,
    ) -> None:
        """UC-02: mark this item 'devuelto' and record its devolution snapshot.

        Pure state-setter: the use case computes ``usage_minutes``/``final_amount``
        from the FROZEN fare snapshot (RN-08/RN-10) and passes them in; this method
        does NOT recompute fare math and does NOT apply ``fare_relocation_charge``
        (relocation charge is out of scope for E-04). Only legal from 'activo'
        (RN-12); a second return raises ``RentalItemAlreadyReturnedError``.
        """
        if self.status is not RentalItemStatus.ACTIVO:
            raise RentalItemAlreadyReturnedError(
                f"Rental item {self.id} is already returned"
            )
        self.status = RentalItemStatus.DEVUELTO
        self.return_station_id = return_station_id
        self.returned_at = returned_at
        self.usage_minutes = usage_minutes
        self.final_amount = final_amount

    @classmethod
    def from_fare(
        cls,
        *,
        item_id: RentalItemId,
        bicycle_id: BicycleId,
        fare: Fare,
        started_at: datetime,
    ) -> "RentalItem":
        """Factory copying the fare's snapshot at creation time (RN-08/ADR-0005)."""
        return cls(
            id=item_id,
            bicycle_id=bicycle_id,
            fare_id=fare.id,
            fare_fixed_component=fare.fixed_component,
            fare_time_component=fare.time_component,
            fare_time_unit=fare.time_unit,
            fare_relocation_charge=fare.relocation_charge,
            status=RentalItemStatus.ACTIVO,
            estimated_amount=fare.estimated_amount(),
            started_at=started_at,
        )


@dataclass
class Rental:
    """Rental header aggregating 1..N items (RN-04)."""

    id: RentalId
    user_id: UserId
    origin_station_id: StationId
    status: RentalStatus
    items: List[RentalItem]
    estimated_total: Money
    created_at: datetime
    payment_id: Optional[PaymentId] = None
    confirmed_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if not self.items:
            raise ValueError("A rental must have at least one item (RN-04)")

    @classmethod
    def create_pending(
        cls,
        *,
        rental_id: RentalId,
        user_id: UserId,
        origin_station_id: StationId,
        items: List[RentalItem],
        created_at: datetime,
    ) -> "Rental":
        """Build a freshly created rental in 'pendiente_pago' (spec §7.2)."""
        if not items:
            raise ValueError("A rental must have at least one item (RN-04)")
        total = Money.zero()
        for item in items:
            total = total + item.estimated_amount
        return cls(
            id=rental_id,
            user_id=user_id,
            origin_station_id=origin_station_id,
            status=RentalStatus.PENDIENTE_PAGO,
            items=list(items),
            estimated_total=total,
            created_at=created_at,
        )

    def bicycle_ids(self) -> List[BicycleId]:
        return [item.bicycle_id for item in self.items]

    def find_active_item_by_bicycle(
        self, bicycle_id: BicycleId
    ) -> Optional["RentalItem"]:
        """UC-02: return the ACTIVE item for ``bicycle_id``, or None.

        Returns None when no item references the bicycle OR when its item is
        already 'devuelto'. The use case distinguishes the two cases (absent ->
        ``BicycleNotInRentalError``; already returned ->
        ``RentalItemAlreadyReturnedError``) by also inspecting ``items``.
        """
        for item in self.items:
            if item.bicycle_id == bicycle_id and item.is_active():
                return item
        return None

    def has_item_for_bicycle(self, bicycle_id: BicycleId) -> bool:
        """Whether any item (active or returned) references ``bicycle_id``."""
        return any(item.bicycle_id == bicycle_id for item in self.items)

    def derive_status(self) -> RentalStatus:
        """ADR-0004: derive status from item statuses.

        In this increment items are created ``activo``; once paid, all-active
        derives to ``activa``. (parcialmente_devuelta/completada belong to
        devolution and are out of scope here.)
        """
        if not self.items:
            return RentalStatus.FALLIDA
        statuses = {item.status for item in self.items}
        if statuses == {RentalItemStatus.DEVUELTO}:
            return RentalStatus.COMPLETADA
        if RentalItemStatus.DEVUELTO in statuses:
            return RentalStatus.PARCIALMENTE_DEVUELTA
        return RentalStatus.ACTIVA

    def confirm(self, *, payment_id: PaymentId, confirmed_at: datetime) -> None:
        """Step 7: attach the authorized payment and move to the derived status.

        Only legal from 'pendiente_pago' (RN-12); confirming twice or confirming
        a failed/cancelled rental is a domain error.
        """
        if self.status is not RentalStatus.PENDIENTE_PAGO:
            raise IllegalRentalTransition(
                f"Cannot confirm rental in status '{self.status.value}': "
                "only 'pendiente_pago' -> 'activa' is allowed"
            )
        self.payment_id = payment_id
        self.confirmed_at = confirmed_at
        self.status = self.derive_status()

    def mark_failed(self) -> None:
        """UC-01 6a: payment rejected -> rental 'fallida' (spec §7.2).

        Only legal from 'pendiente_pago' (RN-12): a confirmed rental cannot be
        retroactively marked as failed.
        """
        if self.status is not RentalStatus.PENDIENTE_PAGO:
            raise IllegalRentalTransition(
                f"Cannot mark rental as failed in status '{self.status.value}': "
                "only 'pendiente_pago' -> 'fallida' is allowed"
            )
        self.status = RentalStatus.FALLIDA

    def apply_return(
        self,
        returned: List[Tuple["RentalItem", StationId, int, Money]],
        *,
        returned_at: datetime,
    ) -> None:
        """UC-02: apply the (already validated) return of one or more items.

        ``returned`` is a list of tuples ``(item, return_station_id,
        usage_minutes, final_amount)`` resolved by the use case. Only legal from
        'activa' or 'parcialmente_devuelta' (RN-12); otherwise
        ``RentalNotActiveError``. Marks each targeted item 'devuelto', then
        RE-DERIVES the rental status via :meth:`derive_status` (ADR-0004: a
        subset 'devuelto' -> parcialmente_devuelta, all 'devuelto' ->
        completada). If the derived status is 'completada' and the rental is not
        yet closed, records ``closed_at = returned_at``. No payment/relocation
        mutation (out of scope E-04).
        """
        if self.status not in (
            RentalStatus.ACTIVA,
            RentalStatus.PARCIALMENTE_DEVUELTA,
        ):
            raise RentalNotActiveError(
                f"Cannot return against rental in status '{self.status.value}': "
                "only 'activa'/'parcialmente_devuelta' allow returns (RN-12)"
            )
        for item, return_station_id, usage_minutes, final_amount in returned:
            item.mark_returned(
                return_station_id=return_station_id,
                returned_at=returned_at,
                usage_minutes=usage_minutes,
                final_amount=final_amount,
            )
        self.status = self.derive_status()
        if self.status is RentalStatus.COMPLETADA and self.closed_at is None:
            self.closed_at = returned_at
