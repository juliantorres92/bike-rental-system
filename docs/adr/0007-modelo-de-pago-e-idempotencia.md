# ADR-0007 — Modelo de pago: un Pago por Renta, idempotencia y saga de compensación

- **Estado:** aceptado
- **Fecha:** 2026-05-30
- **Origen:** C-06, RN-19, RN-20, RN-05, UC-01, UC-03; [Modelo de datos §5.9](../modelo-de-datos.md)

## Contexto y problema

La creación de una renta es atómica e involucra a un **tercero**: la pasarela de pagos (RN-05, UC-01). Entre el momento en que la pasarela autoriza el cobro y el momento en que el sistema confirma la renta puede fallar la red, el proceso o la pasarela (UC-01, flujo 7a; C-06). Hay que garantizar que un cobro nunca se duplica (RN-20), que toda renta activa tiene un pago autorizado (RN-19), y que un fallo a mitad de camino deja el sistema consistente (sin cobrar sin renta, ni renta sin cobro).

## Drivers de decisión

- **Idempotencia**: reintentos no duplican el cargo (RN-20).
- **Atomicidad de cara al cliente** (RN-05): o renta + cobro, o nada.
- **Consistencia ante fallo parcial** entre un recurso transaccional (la BD) y uno no transaccional (la pasarela).
- Trazabilidad del cobro y soporte de reembolso parcial (ligado a la devolución parcial, [ADR-0004](0004-estado-de-renta-derivado-de-itemrenta.md)).

## Opciones consideradas

1. **Múltiples filas `Payment` por intento.** Refleja cada intento, pero complica saber el estado consolidado del cobro y la unicidad ("¿cuál es el pago de esta renta?").
2. **Un `Payment` por `Renta` con máquina de estados + `idempotency_key`.** Estado consolidado claro; los intentos/reembolsos son **transiciones**; el detalle fino de la pasarela vive en su propio log.
3. **Transacción distribuida (2PC) entre BD y pasarela.** Garantía fuerte, pero las pasarelas no ofrecen 2PC; inviable en la práctica.

## Decisión

**Opción 2, con un patrón saga para el cruce con la pasarela.**

- **Un `PAYMENT` por `RENTAL`** (`rental_id UNIQUE`, RN-19), con `status` (`iniciado`/`autorizado`/`capturado`/`reembolsado`/`rechazado`) y montos (`authorized`/`captured`/`refunded`).
- **`idempotency_key UNIQUE`** generada a partir del `id` (UUIDv7, [ADR-0002](0002-uuid-v7-como-estrategia-de-llaves.md)) **antes** de llamar a la pasarela → un reintento con la misma clave no duplica el cargo (RN-20).
- **Saga de compensación** para C-06: si el sistema falla tras autorizar pero antes de confirmar la renta, una operación de compensación **revierte/anula el cobro**; si falla antes de autorizar, no hay nada que revertir y la renta queda `fallida`. El estado consolidado siempre permite decidir la compensación.
- **Reembolso parcial** ligado a la devolución por ítem: `captured_amount`/`refunded_amount` se ajustan progresivamente (coherente con [ADR-0004](0004-estado-de-renta-derivado-de-itemrenta.md) y RN-10).
- **Nunca** se almacena PAN ni datos de tarjeta (S-03, NFR-07); solo la `gateway_reference`.

## Consecuencias

**Positivas**
- Idempotencia garantizada a nivel de esquema (`UNIQUE`) + clave determinista.
- Estado de cobro consolidado y trazable; reembolso parcial natural.
- Consistencia ante fallo parcial sin depender de 2PC.

**Negativas / costos**
- La saga (compensación) es **lógica de aplicación**, no la protege la BD; requiere diseñar e implementar los pasos de compensación y su reintento.
- La atomicidad renta+cobro es **eventual** en el borde con la pasarela (ventana entre autorizar y confirmar), no estrictamente transaccional. Se acepta porque el tercero no es transaccional; la saga acota la ventana.

## Enlaces

- Aterriza en: [Modelo de datos §5.9](../modelo-de-datos.md). Depende de [ADR-0002](0002-uuid-v7-como-estrategia-de-llaves.md). Relacionado: [ADR-0004](0004-estado-de-renta-derivado-de-itemrenta.md).
