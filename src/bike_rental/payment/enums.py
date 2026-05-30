"""Payment status enum (modelo §5.x ``estado_pago``, spec §7.3)."""

from __future__ import annotations

from enum import Enum


class PaymentStatus(str, Enum):
    INICIADO = "iniciado"
    AUTORIZADO = "autorizado"
    CAPTURADO = "capturado"
    REEMBOLSADO = "reembolsado"
    RECHAZADO = "rechazado"
