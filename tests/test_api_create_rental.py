"""HTTP adapter tests (E-02, HU-05..HU-08) driven through TestClient.

The domain suite must keep passing even without FastAPI installed, so we skip
this whole module when fastapi/httpx are missing.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from bike_rental.adapters.api import InMemoryWorld, create_app  # noqa: E402
from bike_rental.adapters.fake_payment_gateway import REJECT  # noqa: E402
from bike_rental.rental.enums import RentalStatus  # noqa: E402


def _client(world: InMemoryWorld) -> TestClient:
    return TestClient(create_app(world))


def _is_uuid(value: str) -> bool:
    try:
        UUID(str(value))
        return True
    except (ValueError, TypeError):
        return False


# --- TC-01 / HU-05: happy path -------------------------------------------------
def test_tc01_create_rental_happy_path_returns_201():
    world = InMemoryWorld(bicycle_count=3)
    client = _client(world)

    body = {
        "user_id": str(world.user_id),
        "station_id": str(world.station_id),
        "bicycle_ids": [str(b) for b in world.bicycle_ids],
    }
    resp = client.post("/rentals", json=body)

    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert set(data) == {"rental_id", "payment_id", "status"}
    assert data["status"] == RentalStatus.ACTIVA.value == "activa"
    assert _is_uuid(data["rental_id"])
    assert _is_uuid(data["payment_id"])
    # The use case actually ran and authorized exactly once.
    assert len(world.gateway.calls) == 1


# --- TC-02 / HU-06: unknown bicycle -> 404 ------------------------------------
def test_tc02_unknown_bicycle_returns_404():
    world = InMemoryWorld(bicycle_count=3)
    client = _client(world)

    body = {
        "user_id": str(world.user_id),
        "station_id": str(world.station_id),
        "bicycle_ids": [str(world.unknown_bicycle_id)],
    }
    resp = client.post("/rentals", json=body)

    assert resp.status_code == 404, resp.text
    data = resp.json()
    assert data["error"] == "BicycleNotFoundError"
    assert "detail" in data and data["detail"]
    assert "Traceback" not in data["detail"]


# --- TC-03 / HU-06: unknown station -> 404 ------------------------------------
def test_tc03_unknown_station_returns_404():
    world = InMemoryWorld(bicycle_count=3)
    client = _client(world)

    body = {
        "user_id": str(world.user_id),
        "station_id": str(world.unknown_station_id),
        "bicycle_ids": [str(world.bicycle_ids[0])],
    }
    resp = client.post("/rentals", json=body)

    assert resp.status_code == 404, resp.text
    assert resp.json()["error"] == "StationNotFoundError"


# --- TC-04 / HU-06: unavailable bicycle -> 409 --------------------------------
def test_tc04_unavailable_bicycle_returns_409():
    world = InMemoryWorld(bicycle_count=3, with_unavailable_bicycle=True)
    client = _client(world)

    body = {
        "user_id": str(world.user_id),
        "station_id": str(world.station_id),
        "bicycle_ids": [str(world.unavailable_bicycle_id)],
    }
    resp = client.post("/rentals", json=body)

    assert resp.status_code == 409, resp.text
    assert resp.json()["error"] == "BicycleNotAvailableError"


# --- TC-05 / HU-06: bicycle already in an active rental -> 409 ----------------
def test_tc05_already_rented_bicycle_returns_409():
    world = InMemoryWorld(bicycle_count=3, with_active_rental=True)
    client = _client(world)

    body = {
        "user_id": str(world.user_id),
        "station_id": str(world.station_id),
        "bicycle_ids": [str(world.already_rented_bicycle_id)],
    }
    resp = client.post("/rentals", json=body)

    assert resp.status_code == 409, resp.text
    assert resp.json()["error"] == "BicycleAlreadyRentedError"


# --- TC-06 / HU-06: inactive fare -> 409 --------------------------------------
def test_tc06_inactive_fare_returns_409():
    world = InMemoryWorld(bicycle_count=3, fare_active=False)
    client = _client(world)

    body = {
        "user_id": str(world.user_id),
        "station_id": str(world.station_id),
        "bicycle_ids": [str(world.bicycle_ids[0])],
    }
    resp = client.post("/rentals", json=body)

    assert resp.status_code == 409, resp.text
    assert resp.json()["error"] == "InactiveFareError"


# --- TC-07 / HU-06: payment declined -> 402 + no side effects (RN-05) ---------
def test_tc07_payment_declined_returns_402_and_no_side_effects():
    world = InMemoryWorld(bicycle_count=3, payment_outcome=REJECT)
    client = _client(world)

    body = {
        "user_id": str(world.user_id),
        "station_id": str(world.station_id),
        "bicycle_ids": [str(b) for b in world.bicycle_ids],
    }
    resp = client.post("/rentals", json=body)

    assert resp.status_code == 402, resp.text
    assert resp.json()["error"] == "PaymentDeclinedError"

    # RN-05: the rental is recorded 'fallida' and no bicycle was left rented.
    assert world.rental_repo.list_active_bicycle_ids() == set()
    rentals = list(world.rental_repo._store.values())
    assert len(rentals) == 1
    assert rentals[0].status is RentalStatus.FALLIDA
    for bid in world.bicycle_ids:
        bike = world.bicycle_repo.get(bid)
        assert bike is not None
        assert bike.status.value == "disponible"


# --- TC-07b / HU-06: duplicated bicycle id -> 422 (DuplicateBicycleError) ------
def test_tc07b_duplicate_bicycle_id_returns_422():
    world = InMemoryWorld(bicycle_count=3)
    client = _client(world)

    # Pydantic's List[UUID] does NOT deduplicate, so the repeated id reaches the
    # domain and the use case raises DuplicateBicycleError (mapped to 422).
    bid = str(world.bicycle_ids[0])
    body = {
        "user_id": str(world.user_id),
        "station_id": str(world.station_id),
        "bicycle_ids": [bid, bid],
    }
    resp = client.post("/rentals", json=body)

    assert resp.status_code == 422, resp.text
    assert resp.json()["error"] == "DuplicateBicycleError"
    # The duplicate is rejected before authorizing any payment.
    assert world.gateway.calls == []


# --- TC-08 / HU-07: empty bicycle_ids -> 422, use case never invoked ----------
def test_tc08_empty_bicycle_ids_returns_422_without_invoking_use_case():
    world = InMemoryWorld(bicycle_count=3)
    client = _client(world)

    body = {
        "user_id": str(world.user_id),
        "station_id": str(world.station_id),
        "bicycle_ids": [],
    }
    resp = client.post("/rentals", json=body)

    assert resp.status_code == 422, resp.text
    assert resp.json()["error"] == "RequestValidationError"
    # The domain was never reached: the gateway recorded no call.
    assert world.gateway.calls == []


# --- TC-09 / HU-07: malformed UUID -> 422 -------------------------------------
def test_tc09_malformed_uuid_returns_422():
    world = InMemoryWorld(bicycle_count=3)
    client = _client(world)

    body = {
        "user_id": str(world.user_id),
        "station_id": "not-a-uuid",
        "bicycle_ids": ["also-not-a-uuid"],
    }
    resp = client.post("/rentals", json=body)

    assert resp.status_code == 422, resp.text
    assert resp.json()["error"] == "RequestValidationError"
    assert world.gateway.calls == []


def test_tc09b_extra_field_rejected_returns_422():
    world = InMemoryWorld(bicycle_count=3)
    client = _client(world)

    body = {
        "user_id": str(world.user_id),
        "station_id": str(world.station_id),
        "bicycle_ids": [str(world.bicycle_ids[0])],
        "unexpected": "field",
    }
    resp = client.post("/rentals", json=body)

    assert resp.status_code == 422, resp.text
    assert resp.json()["error"] == "RequestValidationError"


# --- TC-10 / HU-08: health ----------------------------------------------------
def test_tc10_health_returns_200_ok():
    client = _client(InMemoryWorld.with_defaults())
    resp = client.get("/health")
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"status": "ok"}
