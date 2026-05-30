"""Fare: a versioned, immutable value object (ADR-0005, modelo §5.8/§8).

A fare is treated as an immutable VO: editing it means creating a NEW version,
never an in-place UPDATE. It is the input to the CreateRental use case; each
RentalItem copies a frozen snapshot of its four pricing values (RN-08).
``is_active`` indicates whether this is the currently-effective version of the
``code``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..shared.ids import FareId
from ..shared.money import Money
from .enums import TimeUnit


@dataclass(frozen=True)
class Fare:
    id: FareId
    code: str
    fixed_component: Money
    time_component: Money
    time_unit: TimeUnit
    relocation_charge: Optional[Money]
    version: int
    is_active: bool

    def estimated_amount(self) -> Money:
        """Estimated charge computed when the rental is created (RN-07).

        ``time_unit`` is the unit the ``time_component`` is expressed in
        (minute/hour/day); it is multiplied by the elapsed time only at
        devolution, when the real time-based charge is settled (RN-10) — out of
        scope here. The creation-time estimate is therefore intentionally a
        deterministic base that does not depend on elapsed time (unknown at
        creation): the fixed component plus one unit of the time component.
        """
        return self.fixed_component + self.time_component
