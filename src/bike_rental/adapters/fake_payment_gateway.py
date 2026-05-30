"""Fake PaymentGateway for tests.

Configurable with an outcome ('authorize' | 'reject') and an optional per-key
override dict. ``authorize`` returns a ``PaymentAuthorization`` and records every
call in ``calls`` so a test can assert it was NOT called / called once (RN-05:
no charge on failure). Idempotent per ``idempotency_key``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from ..rental.ports import PaymentAuthorization, PaymentGateway
from ..shared.money import Money

AUTHORIZE = "authorize"
REJECT = "reject"


@dataclass
class GatewayCall:
    idempotency_key: str
    amount: Money


class FakePaymentGateway(PaymentGateway):
    def __init__(
        self,
        *,
        outcome: str = AUTHORIZE,
        per_key: Optional[Dict[str, str]] = None,
    ) -> None:
        if outcome not in (AUTHORIZE, REJECT):
            raise ValueError("outcome must be 'authorize' or 'reject'")
        self._default_outcome = outcome
        self._per_key = dict(per_key or {})
        self.calls: List[GatewayCall] = []
        # idempotency: remember the result already returned for a key.
        self._results: Dict[str, PaymentAuthorization] = {}
        self._counter = 0

    def authorize(self, idempotency_key: str, amount: Money) -> PaymentAuthorization:
        self.calls.append(GatewayCall(idempotency_key=idempotency_key, amount=amount))
        if idempotency_key in self._results:
            # Idempotent replay: do not produce a new effect.
            return self._results[idempotency_key]

        outcome = self._per_key.get(idempotency_key, self._default_outcome)
        if outcome == AUTHORIZE:
            self._counter += 1
            result = PaymentAuthorization(
                approved=True, reference=f"AUTH-{self._counter:06d}"
            )
        else:
            result = PaymentAuthorization(approved=False, reference=None)
        self._results[idempotency_key] = result
        return result
