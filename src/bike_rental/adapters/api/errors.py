"""Domain-error -> HTTP-status mapping and exception handlers (HU-06).

The handler translates a raised ``RentalError`` into an ``ErrorResponse`` body
``{error, detail}`` with the contractual status code, never leaking a stack
trace. A ``RequestValidationError`` from the Pydantic edge (HU-07) is normalized
into the same shape with status 422.

Mapping (per E-02 contract):
  BicycleNotFoundError / StationNotFoundError ........... 404
  BicycleNotAvailableError / BicycleAlreadyRentedError /
  InactiveFareError / IllegalRentalTransition ........... 409
  EmptyRentalError / DuplicateBicycleError .............. 422
  PaymentDeclinedError .................................. 402
  RentalError (unexpected base fallback) ................ 500

Python 3.9 compatible.
"""

from __future__ import annotations

from typing import Dict, Type

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from ...rental.errors import (
    BicycleAlreadyRentedError,
    BicycleNotAvailableError,
    BicycleNotFoundError,
    DuplicateBicycleError,
    EmptyRentalError,
    IllegalRentalTransition,
    InactiveFareError,
    PaymentDeclinedError,
    RentalError,
    StationNotFoundError,
)

# Concrete domain errors -> HTTP status. The base ``RentalError`` is the
# unexpected fallback (500) and is handled separately.
ERROR_STATUS: Dict[Type[RentalError], int] = {
    BicycleNotFoundError: 404,
    StationNotFoundError: 404,
    BicycleNotAvailableError: 409,
    BicycleAlreadyRentedError: 409,
    InactiveFareError: 409,
    IllegalRentalTransition: 409,
    EmptyRentalError: 422,
    DuplicateBicycleError: 422,
    PaymentDeclinedError: 402,
}


def status_for(error: RentalError) -> int:
    """Resolve the HTTP status for a domain error; unmapped subclasses fall back
    to 500 (an unexpected base ``RentalError`` should not happen in HU-05..08)."""
    return ERROR_STATUS.get(type(error), 500)


def _error_body(error: RentalError) -> Dict[str, str]:
    return {"error": type(error).__name__, "detail": str(error)}


def install_error_handlers(app: FastAPI) -> None:
    """Register the domain-error and validation-error handlers on ``app``."""

    async def handle_rental_error(request: Request, exc: RentalError) -> JSONResponse:
        return JSONResponse(status_code=status_for(exc), content=_error_body(exc))

    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # HU-07: malformed UUID / empty list / extra field rejected at the edge.
        return JSONResponse(
            status_code=422,
            content={"error": "RequestValidationError", "detail": str(exc.errors())},
        )

    # A single handler for the whole RentalError family (subclasses included).
    app.add_exception_handler(RentalError, handle_rental_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
