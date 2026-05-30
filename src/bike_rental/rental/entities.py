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
from typing import List, Optional

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
from .errors import IllegalRentalTransition


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
