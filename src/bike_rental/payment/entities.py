"""Payment entity (RN-19, modelo §5.9).

1:1 with a Rental. This increment models only authorization
(iniciado -> autorizado / rechazado). It NEVER stores card data (S-03).
``idempotency_key`` is derived from the rental id (RN-20). Capture/refund are
out of scope.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from ..shared.ids import PaymentId, RentalId
from ..shared.money import Money
from .enums import PaymentStatus


def idempotency_key_for(rental_id: RentalId) -> str:
    """RN-20: idempotency key derived deterministically from the rental id."""
    return f"rental:{rental_id}"


@dataclass
class Payment:
    id: PaymentId
    rental_id: RentalId
    status: PaymentStatus
    authorized_amount: Money
    idempotency_key: str
    gateway_reference: Optional[str] = None
    authorized_at: Optional[datetime] = None

    @classmethod
    def authorized(
        cls,
        *,
        id: PaymentId,
        rental_id: RentalId,
        amount: Money,
        gateway_reference: Optional[str],
        authorized_at: datetime,
    ) -> "Payment":
        return cls(
            id=id,
            rental_id=rental_id,
            status=PaymentStatus.AUTORIZADO,
            authorized_amount=amount,
            idempotency_key=idempotency_key_for(rental_id),
            gateway_reference=gateway_reference,
            authorized_at=authorized_at,
        )

    def is_authorized(self) -> bool:
        return self.status is PaymentStatus.AUTORIZADO
