"""Bicycle status enum (modelo §5.x ``estado_bicicleta``, spec §7.1, RN-11).

Values use the Spanish domain vocabulary (the closed set is part of the
business contract); the identifier name is English per CLAUDE.md.
"""

from __future__ import annotations

from enum import Enum


class BicycleStatus(str, Enum):
    DISPONIBLE = "disponible"
    RENTADA = "rentada"
    EN_MOVIMIENTO = "en_movimiento"
    MANTENIMIENTO = "mantenimiento"
