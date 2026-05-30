"""Rental and RentalItem status enums.

``RentalStatus`` (modelo §5.x ``estado_renta``, spec §7.2) and
``RentalItemStatus`` (modelo §5.x ``estado_item_renta``, C-04).
"""

from __future__ import annotations

from enum import Enum


class RentalStatus(str, Enum):
    PENDIENTE_PAGO = "pendiente_pago"
    ACTIVA = "activa"
    PARCIALMENTE_DEVUELTA = "parcialmente_devuelta"
    COMPLETADA = "completada"
    CANCELADA = "cancelada"
    FALLIDA = "fallida"


class RentalItemStatus(str, Enum):
    ACTIVO = "activo"
    DEVUELTO = "devuelto"
