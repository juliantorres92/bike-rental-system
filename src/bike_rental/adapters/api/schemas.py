"""Pydantic v2 schemas for the HTTP adapter (E-02).

These models live at the edge of the hexagon: they validate the incoming HTTP
payload (HU-07) and shape the outgoing JSON. They depend only on stdlib + Pydantic
and never import the domain — the route handler translates between these DTOs and
the domain ``CreateRentalCommand`` / ``CreateRentalResult``.

Python 3.9 compatible: ``from __future__ import annotations`` + ``typing.List``;
no ``X | Y`` runtime unions.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateRentalRequest(BaseModel):
    """Cuerpo de ``POST /rentals`` (HU-05/HU-07).

    Pydantic valida la sintaxis de los UUID (malformado → 422) y exige una lista
    de bicicletas no vacía en el borde (``min_length=1``); el dominio además lanza
    ``EmptyRentalError`` como red de seguridad. ``extra='forbid'`` rechaza campos
    desconocidos en la frontera.
    """

    model_config = ConfigDict(extra="forbid")

    user_id: UUID = Field(description="Identificador del cliente que renta")
    station_id: UUID = Field(description="Estación de origen de la renta")
    bicycle_ids: List[UUID] = Field(
        min_length=1, description="Bicicletas a rentar (al menos una)"
    )


class ReturnBicyclesRequest(BaseModel):
    """Cuerpo de ``POST /rentals/{rental_id}/returns`` (HU-16/UC-02).

    Pydantic valida la sintaxis de los UUID (malformado → 422) y exige una lista
    de bicicletas no vacía (``min_length=1``); el dominio además lanza
    ``EmptyRentalError``/``DuplicateBicycleError`` como red de seguridad.
    ``extra='forbid'`` rechaza campos desconocidos en la frontera. El
    ``rental_id`` viaja como parámetro de ruta, no en el cuerpo.
    """

    model_config = ConfigDict(extra="forbid")

    bicycle_ids: List[UUID] = Field(
        min_length=1, description="Bicicletas a devolver (al menos una)"
    )
    return_station_id: UUID = Field(description="Estación destino de la devolución")


class RentalResponse(BaseModel):
    """Respuesta de éxito de ``POST /rentals`` (201): la renta creada."""

    rental_id: UUID = Field(description="Identificador de la renta creada")
    payment_id: UUID = Field(description="Identificador del pago autorizado")
    status: str = Field(description="Estado de la renta (p. ej. 'activa')")


class ErrorResponse(BaseModel):
    """Cuerpo uniforme de error. ``error`` es el nombre estable del error de
    dominio; ``detail`` es un mensaje legible — nunca una traza de error."""

    error: str = Field(description="Nombre del error de dominio")
    detail: str = Field(description="Mensaje legible del error")


class HealthResponse(BaseModel):
    """Cuerpo de ``GET /health`` (HU-08): estado del servicio."""

    status: str = Field(description="Estado del servicio, p. ej. 'ok'")


# --- Read-side views (E-03, HU-10..12) ---------------------------------------
# Vistas de SOLO LECTURA: el handler mapea entidades de dominio a estos modelos;
# nunca se serializa una entidad de dominio cruda.


class MoneyView(BaseModel):
    """Vista de un valor ``Money`` del dominio.

    ``amount`` es ``Decimal`` (DECIMAL(12,2)); Pydantic lo serializa como número
    JSON, NUNCA como ``float``, preservando la precisión monetaria."""

    amount: Decimal = Field(description="Monto con 2 decimales (DECIMAL(12,2))")
    currency: str = Field(description="Moneda, p. ej. 'COP'")


class StationView(BaseModel):
    """Vista de una estación (HU-10)."""

    id: UUID = Field(description="Identificador de la estación")
    code: str = Field(description="Código de la estación, p. ej. 'ST-01'")
    name: str = Field(description="Nombre de la estación")
    capacity: int = Field(description="Capacidad total de la estación")
    available_inventory: int = Field(description="Bicicletas disponibles en la estación")


class BicycleView(BaseModel):
    """Vista de una bicicleta (HU-11)."""

    id: UUID = Field(description="Identificador de la bicicleta")
    code: str = Field(description="Código de la bicicleta, p. ej. 'BIKE-1'")
    status: str = Field(description="Estado de la bicicleta, p. ej. 'disponible'")


class RentalItemView(BaseModel):
    """Vista de un ítem de renta (HU-12).

    Los campos de devolución (E-04) son nulos mientras el ítem está ``activo`` y
    se rellenan al devolverlo (``devuelto``).
    """

    bicycle_id: UUID = Field(description="Bicicleta asociada al ítem")
    status: str = Field(description="Estado del ítem, p. ej. 'activo' o 'devuelto'")
    estimated_amount: MoneyView = Field(description="Monto estimado del ítem")
    final_amount: Optional[MoneyView] = Field(
        default=None, description="Monto final al devolver (None si aún activo)"
    )
    usage_minutes: Optional[int] = Field(
        default=None, description="Minutos de uso al devolver (None si aún activo)"
    )
    returned_at: Optional[datetime] = Field(
        default=None, description="Instante de devolución (None si aún activo)"
    )


class RentalView(BaseModel):
    """Vista de una renta y sus ítems (HU-12)."""

    id: UUID = Field(description="Identificador de la renta")
    status: str = Field(description="Estado de la renta, p. ej. 'activa'")
    estimated_total: MoneyView = Field(description="Total estimado de la renta")
    payment_id: Optional[UUID] = Field(
        default=None, description="Pago asociado (None si aún no confirmada / fallida)"
    )
    items: List[RentalItemView] = Field(description="Ítems de la renta")
