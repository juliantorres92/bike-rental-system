"""Money value object.

Domain rule (modelo §2): all monetary amounts are ``DECIMAL(12,2)``. We use
``Decimal`` and NEVER ``float`` to avoid binary rounding errors on money.
``Money`` is an immutable value object quantized to 2 decimals (ROUND_HALF_UP)
and rejects negative amounts at construction time.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Union

DEFAULT_CURRENCY = "COP"
_TWO_PLACES = Decimal("0.01")

Numeric = Union["Money", int, str, Decimal]


def _quantize(amount: Decimal) -> Decimal:
    return amount.quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Money:
    """Immutable monetary amount with a currency (default COP)."""

    amount: Decimal
    currency: str = DEFAULT_CURRENCY

    def __post_init__(self) -> None:
        # Coerce common inputs (int/str) to Decimal; reject float to avoid
        # silent precision loss (a float literal like 0.1 is not exact).
        raw = self.amount
        if isinstance(raw, float):
            raise TypeError("Money does not accept float; use Decimal/str/int")
        if not isinstance(raw, Decimal):
            raw = Decimal(str(raw))
        quantized = _quantize(raw)
        if quantized < Decimal("0"):
            raise ValueError("Money amount cannot be negative")
        # frozen dataclass: assign via object.__setattr__
        object.__setattr__(self, "amount", quantized)

    @classmethod
    def zero(cls, currency: str = DEFAULT_CURRENCY) -> "Money":
        return cls(Decimal("0"), currency)

    def _check_same_currency(self, other: "Money") -> None:
        if self.currency != other.currency:
            raise ValueError(
                f"Currency mismatch: {self.currency} vs {other.currency}"
            )

    def __add__(self, other: "Money") -> "Money":
        if not isinstance(other, Money):
            return NotImplemented
        self._check_same_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __mul__(self, factor: Union[int, Decimal]) -> "Money":
        if isinstance(factor, float):
            raise TypeError("Money cannot be multiplied by float; use int/Decimal")
        if not isinstance(factor, (int, Decimal)):
            return NotImplemented
        return Money(self.amount * Decimal(factor), self.currency)

    __rmul__ = __mul__

    def __str__(self) -> str:
        return f"{self.amount} {self.currency}"
