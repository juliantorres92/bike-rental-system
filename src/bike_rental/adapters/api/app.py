"""FastAPI app factory for the rental HTTP adapter (E-02, ADR-0008).

``create_app(world)`` builds a self-contained FastAPI application whose driven
side is the in-memory composition root stored on ``app.state.world``. Because the
use case and the active fare are resolved from ``app.state`` via ``Depends``, each
test can build its own ``InMemoryWorld`` and its own app — no shared global state.

The route handler is the boundary translator: it maps the validated
``CreateRentalRequest`` (typed UUIDs) into a domain ``CreateRentalCommand`` (typed
ids + the seeded active fare) and returns a ``RentalResponse`` from the
``CreateRentalResult``. Domain errors raised by the use case are turned into HTTP
responses by the handlers installed in ``errors.py`` (HU-06).

Python 3.9 compatible: ``from __future__ import annotations`` + ``typing.List/Optional``.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import Depends, FastAPI, Request

from ...fare.entities import Fare
from ...rental.use_cases.create_rental import (
    CreateRental,
    CreateRentalCommand,
)
from ...shared.ids import BicycleId, StationId, UserId
from .composition import InMemoryWorld
from .errors import install_error_handlers
from .schemas import (
    CreateRentalRequest,
    ErrorResponse,
    HealthResponse,
    RentalResponse,
)


def get_create_rental(request: Request) -> CreateRental:
    """Resolve the wired use case from the composition root on app.state."""
    return request.app.state.world.use_case


def get_active_fare(request: Request) -> Fare:
    """Resolve the seeded active fare from the composition root on app.state.

    No FareRepository exists in this increment (out of scope of E-02); the API
    applies this single seeded fare.
    """
    return request.app.state.world.active_fare


def create_app(world: Optional[InMemoryWorld] = None) -> FastAPI:
    """Build a FastAPI app wired to ``world`` (or a default one).

    Storing the composition root on ``app.state.world`` keeps the app
    reconstructible and isolated per test.
    """
    if world is None:
        world = InMemoryWorld.with_defaults()

    app = FastAPI(
        title="API de Renta de Bicicletas",
        version="0.1.0",
        description=(
            "Adaptador HTTP de referencia (hexagonal) del caso de uso "
            "**crear renta multi-bicicleta** (UC-01). Los adaptadores de salida "
            "son en memoria; el dominio no depende de este framework."
        ),
    )
    app.state.world = world
    install_error_handlers(app)

    @app.post(
        "/rentals",
        status_code=201,
        response_model=RentalResponse,
        summary="Crear renta de varias bicicletas",
        description=(
            "Crea una renta atómica de una o varias bicicletas de una estación "
            "(UC-01). Si una bicicleta no está disponible o el pago es rechazado, "
            "no se renta ninguna ni se cobra (RN-05)."
        ),
        responses={
            201: {"description": "Renta creada y activa"},
            402: {"model": ErrorResponse, "description": "Pago rechazado por la pasarela"},
            404: {"model": ErrorResponse, "description": "Bicicleta o estación inexistente"},
            409: {
                "model": ErrorResponse,
                "description": "Conflicto: bicicleta no disponible, ya rentada o tarifa inactiva",
            },
            422: {
                "model": ErrorResponse,
                "description": "Entrada inválida o regla de negocio (lista vacía / bicicletas duplicadas)",
            },
        },
    )
    def create_rental_endpoint(
        body: CreateRentalRequest,
        use_case: CreateRental = Depends(get_create_rental),
        fare: Fare = Depends(get_active_fare),
    ) -> RentalResponse:
        # HU-05: translate edge DTO -> domain command using the seeded fare.
        bicycle_ids: List[BicycleId] = [BicycleId(b) for b in body.bicycle_ids]
        command = CreateRentalCommand(
            user_id=UserId(body.user_id),
            station_id=StationId(body.station_id),
            bicycle_ids=bicycle_ids,
            fare=fare,
        )
        result = use_case.execute(command)
        return RentalResponse(
            rental_id=result.rental_id,
            payment_id=result.payment_id,
            status=result.status.value,
        )

    @app.get(
        "/health",
        response_model=HealthResponse,
        summary="Estado del servicio",
        description="Verifica que el servicio responde (sin tocar el dominio).",
    )
    def health_endpoint() -> HealthResponse:
        # HU-08: no domain dependency; just proves the service responds.
        return HealthResponse(status="ok")

    return app
