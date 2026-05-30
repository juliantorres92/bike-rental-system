"""Pydantic v2 schemas for the HTTP adapter (E-02).

These models live at the edge of the hexagon: they validate the incoming HTTP
payload (HU-07) and shape the outgoing JSON. They depend only on stdlib + Pydantic
and never import the domain — the route handler translates between these DTOs and
the domain ``CreateRentalCommand`` / ``CreateRentalResult``.

Python 3.9 compatible: ``from __future__ import annotations`` + ``typing.List``;
no ``X | Y`` runtime unions.
"""

from __future__ import annotations

from typing import List
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
