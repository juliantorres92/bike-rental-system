"""HU-16 — Return-side HTTP adapter tests (UC-02, E-04) via TestClient.

POST /rentals/{rental_id}/returns:
- 200 total return -> RentalView status 'completada'; GET reflects it.
- 200 partial return -> 'parcialmente_devuelta'; GET reflects it.
- 404 unknown rental / unknown destination station.
- 409 bicycle-not-in-rental / already-returned / rental-not-active / station-full.
- 422 malformed body (empty list / non-UUID / extra field); domain never invoked.

Skipped wholesale when fastapi/httpx are absent (the domain suite stands alone).
The world's FixedClock is advanced before each return so usage/final_amount > 0.
"""

from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from bike_rental.adapters.api import InMemoryWorld, create_app  # noqa: E402


def _client(world: InMemoryWorld) -> TestClient:
    return TestClient(create_app(world))


def _create_rental(world: InMemoryWorld, client: TestClient) -> str:
    body = {
        "user_id": str(world.user_id),
        "station_id": str(world.station_id),
        "bicycle_ids": [str(b) for b in world.bicycle_ids],
    }
    resp = client.post("/rentals", json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()["rental_id"]


# --- TC-16-api-200-total -------------------------------------------------------
def test_tc16_api_total_return_200_completada():
    world = InMemoryWorld(bicycle_count=2)
    client = _client(world)
    rental_id = _create_rental(world, client)
    world.clock.advance(timedelta(minutes=30))

    resp = client.post(
        f"/rentals/{rental_id}/returns",
        json={
            "bicycle_ids": [str(b) for b in world.bicycle_ids],
            "return_station_id": str(world.station_id),
        },
    )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "completada"
    assert all(i["status"] == "devuelto" for i in data["items"])
    assert data["payment_id"]  # authorized payment kept

    # GET reflects the new state (E-03).
    got = client.get(f"/rentals/{rental_id}")
    assert got.status_code == 200
    assert got.json()["status"] == "completada"


# --- TC-16-api-200-partial -----------------------------------------------------
def test_tc16_api_partial_return_200_parcial():
    world = InMemoryWorld(bicycle_count=3)
    client = _client(world)
    rental_id = _create_rental(world, client)
    world.clock.advance(timedelta(minutes=15))

    resp = client.post(
        f"/rentals/{rental_id}/returns",
        json={
            "bicycle_ids": [str(world.bicycle_ids[0])],
            "return_station_id": str(world.station_id),
        },
    )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "parcialmente_devuelta"
    statuses = {i["bicycle_id"]: i["status"] for i in data["items"]}
    assert statuses[str(world.bicycle_ids[0])] == "devuelto"
    assert statuses[str(world.bicycle_ids[1])] == "activo"

    got = client.get(f"/rentals/{rental_id}")
    assert got.json()["status"] == "parcialmente_devuelta"


# --- TC-16-api-404 -------------------------------------------------------------
def test_tc16_api_unknown_rental_404():
    world = InMemoryWorld(bicycle_count=2)
    client = _client(world)

    resp = client.post(
        f"/rentals/{uuid4()}/returns",
        json={
            "bicycle_ids": [str(world.bicycle_ids[0])],
            "return_station_id": str(world.station_id),
        },
    )
    assert resp.status_code == 404, resp.text
    body = resp.json()
    assert body["error"] == "RentalNotFoundError"
    assert "Traceback" not in body["detail"]


def test_tc16_api_unknown_station_404():
    world = InMemoryWorld(bicycle_count=2)
    client = _client(world)
    rental_id = _create_rental(world, client)
    world.clock.advance(timedelta(minutes=5))

    resp = client.post(
        f"/rentals/{rental_id}/returns",
        json={
            "bicycle_ids": [str(world.bicycle_ids[0])],
            "return_station_id": str(world.unknown_station_id),
        },
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["error"] == "StationNotFoundError"


# --- TC-16-api-409 -------------------------------------------------------------
def test_tc16_api_bicycle_not_in_rental_409():
    world = InMemoryWorld(bicycle_count=2)
    client = _client(world)
    rental_id = _create_rental(world, client)
    world.clock.advance(timedelta(minutes=5))

    resp = client.post(
        f"/rentals/{rental_id}/returns",
        json={
            "bicycle_ids": [str(uuid4())],  # not part of this rental
            "return_station_id": str(world.station_id),
        },
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["error"] == "BicycleNotInRentalError"


def test_tc16_api_already_returned_409():
    world = InMemoryWorld(bicycle_count=2)
    client = _client(world)
    rental_id = _create_rental(world, client)
    world.clock.advance(timedelta(minutes=5))
    first = client.post(
        f"/rentals/{rental_id}/returns",
        json={
            "bicycle_ids": [str(world.bicycle_ids[0])],
            "return_station_id": str(world.station_id),
        },
    )
    assert first.status_code == 200, first.text

    resp = client.post(
        f"/rentals/{rental_id}/returns",
        json={
            "bicycle_ids": [str(world.bicycle_ids[0])],
            "return_station_id": str(world.station_id),
        },
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["error"] == "RentalItemAlreadyReturnedError"


def test_tc16_api_rental_not_active_409():
    world = InMemoryWorld(bicycle_count=1)
    client = _client(world)
    rental_id = _create_rental(world, client)
    world.clock.advance(timedelta(minutes=5))
    done = client.post(
        f"/rentals/{rental_id}/returns",
        json={
            "bicycle_ids": [str(world.bicycle_ids[0])],
            "return_station_id": str(world.station_id),
        },
    )
    assert done.status_code == 200
    # The rental is now completada -> another return is rejected.
    resp = client.post(
        f"/rentals/{rental_id}/returns",
        json={
            "bicycle_ids": [str(world.bicycle_ids[0])],
            "return_station_id": str(world.station_id),
        },
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["error"] == "RentalNotActiveError"


def test_tc16_api_station_full_409():
    # Seed a separate full destination station directly into the repo.
    world = InMemoryWorld(bicycle_count=2)
    client = _client(world)
    rental_id = _create_rental(world, client)
    world.clock.advance(timedelta(minutes=5))

    from bike_rental.inventory.entities import Station  # noqa: E402
    from bike_rental.shared.ids import StationId  # noqa: E402

    full_id = StationId(uuid4())
    world.station_repo.save(
        Station(id=full_id, code="ST-FULL", name="Llena", capacity=2,
                available_inventory=2)
    )

    resp = client.post(
        f"/rentals/{rental_id}/returns",
        json={
            "bicycle_ids": [str(b) for b in world.bicycle_ids],
            "return_station_id": str(full_id),
        },
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["error"] == "StationFullError"


# --- TC-16-api-422 -------------------------------------------------------------
@pytest.mark.parametrize(
    "body",
    [
        {"bicycle_ids": [], "return_station_id": str(uuid4())},  # empty list
        {"bicycle_ids": ["not-a-uuid"], "return_station_id": str(uuid4())},
        {"bicycle_ids": [str(uuid4())]},  # missing return_station_id
        {
            "bicycle_ids": [str(uuid4())],
            "return_station_id": str(uuid4()),
            "extra": "x",  # forbidden extra field
        },
    ],
)
def test_tc16_api_malformed_body_422(body):
    world = InMemoryWorld(bicycle_count=2)
    client = _client(world)
    rental_id = _create_rental(world, client)

    resp = client.post(f"/rentals/{rental_id}/returns", json=body)
    assert resp.status_code == 422, resp.text
    assert resp.json()["error"] == "RequestValidationError"
