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
    """Body of ``POST /rentals`` (HU-05/HU-07).

    Pydantic validates UUID syntax (malformed -> 422) and enforces a non-empty
    bicycle list at the edge (``min_length=1``); the domain still raises
    ``EmptyRentalError`` as a safety net. ``extra='forbid'`` rejects unknown
    fields at the boundary.
    """

    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    station_id: UUID
    bicycle_ids: List[UUID] = Field(min_length=1)


class RentalResponse(BaseModel):
    """Success body of ``POST /rentals`` (201)."""

    rental_id: UUID
    payment_id: UUID
    status: str


class ErrorResponse(BaseModel):
    """Uniform error body. ``error`` is the stable domain error name; ``detail``
    is a human-readable message — never a stack trace."""

    error: str
    detail: str


class HealthResponse(BaseModel):
    """Body of ``GET /health`` (HU-08)."""

    status: str
