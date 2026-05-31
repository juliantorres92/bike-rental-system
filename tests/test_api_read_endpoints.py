"""Read-side HTTP adapter tests (E-03, HU-10..HU-12) via TestClient.

Covers the GET endpoints added on the query side of the hexagon:
- GET /stations                       (HU-10)
- GET /stations/{station_id}/bicycles (HU-11, incl. 404 + ?available filter)
- GET /rentals/{rental_id}            (HU-12, incl. 404)

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
from bike_rental.bicycle.enums import BicycleStatus  # noqa: E402
from bike_rental.rental.enums import RentalItemStatus, RentalStatus  # noqa: E402


def _client(world: InMemoryWorld) -> TestClient:
    return TestClient(create_app(world))


def _is_uuid(value) -> bool:
    try:
        UUID(str(value))
        return True
    except (ValueError, TypeError):
        return False


def _create_active_rental(world: InMemoryWorld, client: TestClient) -> str:
    """Create an active rental through the public API and return its id."""
    body = {
        "user_id": str(world.user_id),
        "station_id": str(world.station_id),
        "bicycle_ids": [str(b) for b in world.bicycle_ids],
    }
    resp = client.post("/rentals", json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()["rental_id"]


# --- T-HU10-200 / HU-10: list stations ----------------------------------------
def test_hu10_list_stations_returns_200_with_seeded_station():
    world = InMemoryWorld(bicycle_count=3)
    client = _client(world)

    resp = client.get("/stations")

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1
    station = data[0]
    assert set(station) == {"id", "code", "name", "capacity", "available_inventory"}
    assert _is_uuid(station["id"])
    assert station["code"] == "ST-01"
    assert station["name"] == "Centro"
    # available_inventory matches the seeded bicycle count; capacity per seed rule.
    assert station["available_inventory"] == 3
    assert station["capacity"] == max(3 + 2, 5)


# --- HU-11: list a station's bicycles ------------------------------------------
def test_hu11_list_station_bicycles_returns_200_with_available_bikes():
    world = InMemoryWorld(bicycle_count=3)
    client = _client(world)

    resp = client.get(f"/stations/{world.station_id}/bicycles")

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 3
    for bike in data:
        assert set(bike) == {"id", "code", "status"}
        assert bike["status"] == BicycleStatus.DISPONIBLE.value == "disponible"
        assert _is_uuid(bike["id"])
    returned_ids = {bike["id"] for bike in data}
    assert returned_ids == {str(b) for b in world.bicycle_ids}


def test_hu11_excludes_rented_bike_with_no_station():
    # An unavailable (RENTADA) bike has station_id=None -> naturally excluded.
    world = InMemoryWorld(bicycle_count=2, with_unavailable_bicycle=True)
    client = _client(world)

    resp = client.get(f"/stations/{world.station_id}/bicycles")

    assert resp.status_code == 200, resp.text
    ids = {bike["id"] for bike in resp.json()}
    assert str(world.unavailable_bicycle_id) not in ids
    assert ids == {str(b) for b in world.bicycle_ids}


# --- T-HU11-available-filter / HU-11 (optional) --------------------------------
def test_hu11_available_filter_returns_only_available_bikes():
    # The 'already rented' bike is DISPONIBLE and located at the station, so it
    # appears unfiltered; with_active_rental does not make it non-available, so
    # we instead assert the filter is a strict subset that excludes nothing here,
    # and use a directly-seeded non-available bike at a station via the repo.
    world = InMemoryWorld(bicycle_count=2)
    # Seed a MANTENIMIENTO bike physically at the station (not available) by
    # mutating the in-memory store directly (test setup, not via the API).
    from bike_rental.bicycle.entities import Bicycle  # noqa: E402
    from bike_rental.shared.ids import BicycleId  # noqa: E402

    maint_id = BicycleId(uuid4())
    world.bicycle_repo._store[maint_id] = Bicycle(
        id=maint_id,
        code="BIKE-MAINT",
        status=BicycleStatus.MANTENIMIENTO,
        station_id=world.station_id,
    )
    client = _client(world)

    all_resp = client.get(f"/stations/{world.station_id}/bicycles")
    avail_resp = client.get(f"/stations/{world.station_id}/bicycles?available=true")

    assert all_resp.status_code == 200, all_resp.text
    assert avail_resp.status_code == 200, avail_resp.text
    all_ids = {b["id"] for b in all_resp.json()}
    avail_ids = {b["id"] for b in avail_resp.json()}
    # The maintenance bike is present unfiltered but excluded by ?available=true.
    assert str(maint_id) in all_ids
    assert str(maint_id) not in avail_ids
    assert all(b["status"] == "disponible" for b in avail_resp.json())


# --- T-HU11-404 / HU-11: unknown station ---------------------------------------
def test_hu11_unknown_station_returns_404():
    world = InMemoryWorld(bicycle_count=3)
    client = _client(world)

    resp = client.get(f"/stations/{world.unknown_station_id}/bicycles")

    assert resp.status_code == 404, resp.text
    data = resp.json()
    assert data["error"] == "StationNotFoundError"
    assert "detail" in data and data["detail"]
    assert "Traceback" not in data["detail"]


def test_hu11_malformed_station_id_returns_422():
    world = InMemoryWorld(bicycle_count=3)
    client = _client(world)

    resp = client.get("/stations/not-a-uuid/bicycles")

    assert resp.status_code == 422, resp.text
    assert resp.json()["error"] == "RequestValidationError"


# --- T-HU12-200 / HU-12: fetch a rental ----------------------------------------
def test_hu12_get_rental_returns_200_with_items_and_money():
    world = InMemoryWorld(bicycle_count=2)
    client = _client(world)
    rental_id = _create_active_rental(world, client)

    resp = client.get(f"/rentals/{rental_id}")

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert set(data) == {"id", "status", "estimated_total", "payment_id", "items"}
    assert data["id"] == rental_id
    assert data["status"] == RentalStatus.ACTIVA.value == "activa"
    assert _is_uuid(data["payment_id"])

    total = data["estimated_total"]
    assert set(total) == {"amount", "currency"}
    assert total["currency"] == "COP"

    assert len(data["items"]) == 2
    from decimal import Decimal  # noqa: E402

    items_sum = Decimal("0")
    for item in data["items"]:
        assert set(item) == {"bicycle_id", "status", "estimated_amount"}
        assert item["status"] == RentalItemStatus.ACTIVO.value == "activo"
        assert _is_uuid(item["bicycle_id"])
        amt = item["estimated_amount"]
        assert set(amt) == {"amount", "currency"}
        items_sum += Decimal(str(amt["amount"]))
    # estimated_total equals the sum of item estimated_amounts.
    assert Decimal(str(total["amount"])) == items_sum


# --- T-HU12-404 / HU-12: unknown rental ----------------------------------------
def test_hu12_unknown_rental_returns_404():
    world = InMemoryWorld(bicycle_count=3)
    client = _client(world)

    resp = client.get(f"/rentals/{uuid4()}")

    assert resp.status_code == 404, resp.text
    data = resp.json()
    assert data["error"] == "RentalNotFoundError"
    assert "detail" in data and data["detail"]
    assert "Traceback" not in data["detail"]


def test_hu12_malformed_rental_id_returns_422():
    world = InMemoryWorld(bicycle_count=3)
    client = _client(world)

    resp = client.get("/rentals/not-a-uuid")

    assert resp.status_code == 422, resp.text
    assert resp.json()["error"] == "RequestValidationError"
