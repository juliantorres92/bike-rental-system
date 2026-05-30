"""RN-20 — Payment idempotency.

A retry with the SAME idempotency key must not produce a second charge: the
gateway replays the original authorization instead of creating a new effect.
The key is derived deterministically from the rental id (UUIDv7, ADR-0002),
so a retry of the same rental reuses the same key.
"""

from __future__ import annotations

from tests.conftest import AUTHORIZE, make_money
from bike_rental.adapters.fake_payment_gateway import FakePaymentGateway
from bike_rental.payment.entities import idempotency_key_for
from bike_rental.shared.ids import new_rental_id


def test_rn20_same_key_replays_authorization_without_duplicating_charge():
    gateway = FakePaymentGateway(outcome=AUTHORIZE)
    key = idempotency_key_for(new_rental_id())
    amount = make_money("3500.00")

    first = gateway.authorize(idempotency_key=key, amount=amount)
    second = gateway.authorize(idempotency_key=key, amount=amount)

    # Both approved and the SAME authorization is returned on replay.
    assert first.approved and second.approved
    assert first.reference == second.reference  # no new charge effect

    # Two requests were received, but they collapse to a single authorization.
    assert len(gateway.calls) == 2


def test_rn20_different_keys_produce_distinct_authorizations():
    gateway = FakePaymentGateway(outcome=AUTHORIZE)
    amount = make_money("3500.00")

    a = gateway.authorize(idempotency_key=idempotency_key_for(new_rental_id()), amount=amount)
    b = gateway.authorize(idempotency_key=idempotency_key_for(new_rental_id()), amount=amount)

    # Distinct rentals (distinct keys) get distinct authorizations.
    assert a.reference != b.reference
