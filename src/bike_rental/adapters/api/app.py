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
from uuid import UUID

from fastapi import Depends, FastAPI, Request

from ...bicycle.entities import Bicycle, Station
from ...fare.entities import Fare
from ...rental.entities import Rental, RentalItem
from ...rental.errors import RentalNotFoundError, StationNotFoundError
from ...rental.ports import BicycleRepository, RentalRepository, StationRepository
from ...rental.use_cases.create_rental import (
    CreateRental,
    CreateRentalCommand,
)
from ...rental.use_cases.return_bicycles import (
    ReturnBicycles,
    ReturnBicyclesCommand,
)
from ...shared.ids import BicycleId, RentalId, StationId, UserId
from ...shared.money import Money
from .composition import InMemoryWorld
from .errors import install_error_handlers
from .schemas import (
    BicycleView,
    CreateRentalRequest,
    ErrorResponse,
    HealthResponse,
    MoneyView,
    RentalItemView,
    RentalResponse,
    RentalView,
    ReturnBicyclesRequest,
    StationView,
)


def get_create_rental(request: Request) -> CreateRental:
    """Resolve the wired use case from the composition root on app.state."""
    return request.app.state.world.use_case


def get_return_bicycles(request: Request) -> ReturnBicycles:
    """Resolve the wired return use case from the composition root (UC-02)."""
    return request.app.state.world.return_use_case


def get_active_fare(request: Request) -> Fare:
    """Resolve the seeded active fare from the composition root on app.state.

    No FareRepository exists in this increment (out of scope of E-02); the API
    applies this single seeded fare.
    """
    return request.app.state.world.active_fare


def get_station_repo(request: Request) -> StationRepository:
    """Resolve the wired StationRepository from app.state (HU-10/HU-11)."""
    return request.app.state.world.station_repo


def get_bicycle_repo(request: Request) -> BicycleRepository:
    """Resolve the wired BicycleRepository from app.state (HU-11)."""
    return request.app.state.world.bicycle_repo


def get_rental_repo(request: Request) -> RentalRepository:
    """Resolve the wired RentalRepository from app.state (HU-12)."""
    return request.app.state.world.rental_repo


# --- Read-side view mappers: domain entity -> Pydantic view (E-03) -----------
# The handler is the boundary translator; raw domain entities are never returned.


def _money_view(money: Money) -> MoneyView:
    return MoneyView(amount=money.amount, currency=money.currency)


def _station_view(station: Station) -> StationView:
    return StationView(
        id=station.id,
        code=station.code,
        name=station.name,
        capacity=station.capacity,
        available_inventory=station.available_inventory,
    )


def _bicycle_view(bicycle: Bicycle) -> BicycleView:
    return BicycleView(
        id=bicycle.id,
        code=bicycle.code,
        status=bicycle.status.value,
    )


def _rental_item_view(item: RentalItem) -> RentalItemView:
    return RentalItemView(
        bicycle_id=item.bicycle_id,
        status=item.status.value,
        estimated_amount=_money_view(item.estimated_amount),
        final_amount=_money_view(item.final_amount) if item.final_amount is not None else None,
        usage_minutes=item.usage_minutes,
        returned_at=item.returned_at,
    )


def _rental_view(rental: Rental) -> RentalView:
    return RentalView(
        id=rental.id,
        status=rental.status.value,
        estimated_total=_money_view(rental.estimated_total),
        payment_id=rental.payment_id,
        items=[_rental_item_view(i) for i in rental.items],
    )


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

    @app.post(
        "/rentals/{rental_id}/returns",
        status_code=200,
        response_model=RentalView,
        summary="Devolver una o varias bicicletas de una renta",
        description=(
            "Devuelve una o varias bicicletas de una renta en una estación "
            "destino (UC-02). Devolución total → renta 'completada'; parcial → "
            "'parcialmente_devuelta' (estado derivado). Operación atómica: si "
            "algo falla, no se devuelve ninguna (RN-05). No liquida el pago ni "
            "cobra reubicación (fuera de alcance E-04)."
        ),
        responses={
            200: {"description": "Renta actualizada tras la devolución"},
            404: {
                "model": ErrorResponse,
                "description": "Renta o estación destino inexistente",
            },
            409: {
                "model": ErrorResponse,
                "description": (
                    "Conflicto: renta no activa, ítem ya devuelto, bicicleta "
                    "ajena a la renta o estación destino llena"
                ),
            },
            422: {
                "model": ErrorResponse,
                "description": "Entrada inválida (lista vacía / UUID malformado)",
            },
        },
    )
    def return_bicycles_endpoint(
        rental_id: UUID,
        body: ReturnBicyclesRequest,
        use_case: ReturnBicycles = Depends(get_return_bicycles),
    ) -> RentalView:
        # HU-16: translate edge DTO + path param -> domain command.
        command = ReturnBicyclesCommand(
            rental_id=RentalId(rental_id),
            bicycle_ids=[BicycleId(b) for b in body.bicycle_ids],
            return_station_id=StationId(body.return_station_id),
        )
        rental = use_case.execute(command)
        return _rental_view(rental)

    @app.get(
        "/stations",
        response_model=List[StationView],
        summary="Listar estaciones",
        description=(
            "HU-10: lista todas las estaciones sembradas para descubrir ids e "
            "inventario. Solo lectura; lista vacía (200, []) si no hay estaciones."
        ),
    )
    def list_stations_endpoint(
        station_repo: StationRepository = Depends(get_station_repo),
    ) -> List[StationView]:
        return [_station_view(s) for s in station_repo.list_stations()]

    @app.get(
        "/stations/{station_id}/bicycles",
        response_model=List[BicycleView],
        summary="Bicicletas de una estación",
        description=(
            "HU-11: lista las bicicletas ubicadas en una estación. Con "
            "``?available=true`` filtra solo las disponibles en estación."
        ),
        responses={
            404: {"model": ErrorResponse, "description": "Estación inexistente"},
            422: {"model": ErrorResponse, "description": "station_id no es un UUID válido"},
        },
    )
    def list_station_bicycles_endpoint(
        station_id: UUID,
        available: bool = False,
        station_repo: StationRepository = Depends(get_station_repo),
        bicycle_repo: BicycleRepository = Depends(get_bicycle_repo),
    ) -> List[BicycleView]:
        # HU-11: validate existence first (404), then read bicycles at the station.
        sid = StationId(station_id)
        if station_repo.get(sid) is None:
            raise StationNotFoundError(f"Station {station_id} not found")
        bicycles = bicycle_repo.list_by_station(sid)
        if available:
            bicycles = [b for b in bicycles if b.is_available()]
        return [_bicycle_view(b) for b in bicycles]

    @app.get(
        "/rentals/{rental_id}",
        response_model=RentalView,
        summary="Consultar una renta por id",
        description=(
            "HU-12: obtiene una renta por id para verificar su estado e ítems "
            "tras crearla. Solo lectura."
        ),
        responses={
            404: {"model": ErrorResponse, "description": "Renta inexistente"},
            422: {"model": ErrorResponse, "description": "rental_id no es un UUID válido"},
        },
    )
    def get_rental_endpoint(
        rental_id: UUID,
        rental_repo: RentalRepository = Depends(get_rental_repo),
    ) -> RentalView:
        # HU-12: adapter-level read miss expressed as a domain error -> 404.
        rental = rental_repo.get(RentalId(rental_id))
        if rental is None:
            raise RentalNotFoundError(f"Rental {rental_id} not found")
        return _rental_view(rental)

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
