"""Time unit enum (modelo §5.x ``unidad_tiempo``, RN-09)."""

from __future__ import annotations

from enum import Enum


class TimeUnit(str, Enum):
    MINUTO = "minuto"
    HORA = "hora"
    DIA = "dia"
