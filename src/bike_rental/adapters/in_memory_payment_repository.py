"""In-memory PaymentRepository: store by id + index rental_id -> PaymentId."""

from __future__ import annotations

from typing import Dict, Optional

from ..payment.entities import Payment
from ..rental.ports import PaymentRepository
from ..shared.ids import PaymentId, RentalId


class InMemoryPaymentRepository(PaymentRepository):
    def __init__(self) -> None:
        self._store: Dict[PaymentId, Payment] = {}
        self._by_rental: Dict[RentalId, PaymentId] = {}

    def add(self, payment: Payment) -> None:
        self._store[payment.id] = payment
        self._by_rental[payment.rental_id] = payment.id

    def get(self, payment_id: PaymentId) -> Optional[Payment]:
        return self._store.get(payment_id)

    def get_by_rental(self, rental_id: RentalId) -> Optional[Payment]:
        payment_id = self._by_rental.get(rental_id)
        if payment_id is None:
            return None
        return self._store.get(payment_id)
