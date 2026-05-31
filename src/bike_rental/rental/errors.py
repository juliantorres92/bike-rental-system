"""Domain errors raised by the CreateRental use case.

On any failure the use case raises one of these and leaves NO side effects
(RN-05): no bicycle becomes ``rentada``, no active rental, no effective charge.
All inherit from ``RentalError`` so a caller can catch the family.
"""

from __future__ import annotations


class RentalError(Exception):
    """Base class for rental domain errors."""


class EmptyRentalError(RentalError):
    """RN-04: a rental must include at least one bicycle."""


class DuplicateBicycleError(RentalError):
    """The same bicycle id was requested more than once in a single command."""


class BicycleNotFoundError(RentalError):
    """A requested bicycle id does not exist in the repository."""


class StationNotFoundError(RentalError):
    """The origin station id does not exist in the repository."""


class RentalNotFoundError(RentalError):
    """A requested rental id does not exist in the repository (HU-12).

    Raised at the adapter (read) boundary by the ``GET /rentals/{rental_id}``
    handler when ``RentalRepository.get`` returns ``None``; it is NOT raised by
    any domain use case. Modeled as a ``RentalError`` so the existing family
    handler serializes it uniformly to ``{error, detail}`` with HTTP 404.
    """


class BicycleNotAvailableError(RentalError):
    """RN-02/RN-18: a bicycle is not 'disponible' or not at the origin station."""


class BicycleAlreadyRentedError(RentalError):
    """RN-06: a bicycle is already part of an active rental item."""


class InactiveFareError(RentalError):
    """The supplied fare is not the active/effective version."""


class IllegalRentalTransition(RentalError):
    """RN-12: a rental state transition not allowed by the state machine."""


class RentalNotActiveError(RentalError):
    """RN-12 (UC-02): a return was attempted on a rental that is not in a
    returnable status ('activa' or 'parcialmente_devuelta'). Mapped to 409."""


class RentalItemAlreadyReturnedError(RentalError):
    """UC-02: an item targeted for return is already 'devuelto'. Mapped to 409."""


class BicycleNotInRentalError(RentalError):
    """UC-02: a bicycle is not an active item of the rental being returned.
    Mapped to 409."""


class BicycleNotReturnableError(RentalError):
    """RN-12 (UC-02): a bicycle resolved to an active item of this rental is not
    in 'rentada' status, so the 'rentada' -> 'disponible' transition is illegal.

    Defensive guard for the cross-aggregate invariant 'active item <=> RENTADA
    bicycle'. Pre-validated by the use case (mirroring CreateRental's
    availability pre-check) so the atomic commit never invokes
    ``Bicycle.return_to`` on an illegal source state. Mapped to 409."""


class StationFullError(RentalError):
    """RN-15/RN-03: the destination station has no capacity for the returned
    bicycles. Raised by ``Station.increment_inventory`` (and pre-checked by the
    use case) so the atomic pre-validation catches it before any mutation.
    Mapped to 409."""


class PaymentDeclinedError(RentalError):
    """RN-19/RN-05: the payment gateway did not authorize the charge.

    Carries the id of the rental left in status 'fallida' (HU-02 criterion 2),
    so a caller can locate and inspect it via the rental repository.
    """

    def __init__(self, message: str, *, rental_id: object = None) -> None:
        super().__init__(message)
        self.rental_id = rental_id
