# ADR-0004 — Estado de Renta derivado del estado de sus ItemRenta

- **Estado:** aceptado
- **Fecha:** 2026-05-30
- **Origen:** C-04, RN-14, RN-10; [Modelo de datos §7](../modelo-de-datos.md)

## Contexto y problema

Una renta agrupa N bicicletas (RN-04) y admite **devolución parcial**: el cliente puede devolver 2 de 3 bicicletas (RN-14). Hace falta decidir dónde vive la verdad de "qué se devolvió" y cómo se refleja en el estado de la renta (`activa` / `parcialmente_devuelta` / `completada`).

## Drivers de decisión

- Modelar correctamente la devolución parcial (RN-14): la renta no cierra hasta el último ítem.
- Liquidación por ítem (tiempo de uso y monto real por bicicleta, RN-10).
- Capacidad de filtrar/reportar por estado de renta (dominio asegurador).
- Evitar desincronía entre el estado de la cabecera y el de las líneas.

## Opciones consideradas

1. **Estado solo en la cabecera (`RENTAL`).** Simple, pero no puede representar que unas bicis volvieron y otras no sin duplicar lógica; rompe con la devolución parcial.
2. **Verdad en los ítems + estado de renta puramente derivado (vista/cálculo en lectura).** Una sola fuente (los ítems), cero desincronía. Costo: cada lectura agrega sobre `RENTAL_ITEM`; el estado no tiene columna física, lo que dificulta filtrar ("dame las rentas parcialmente devueltas") e indexar para reportes.
3. **Verdad en los ítems + estado de renta persistido pero derivado.** `RENTAL_ITEM` lleva su propio `status` (`activo`/`devuelto`), `returned_at`, `return_station_id`, `final_amount`, `usage_minutes`. El `status` de `RENTAL` se **recalcula y persiste** en la transacción de devolución.

## Decisión

**Opción 3.** La verdad atómica vive en `RENTAL_ITEM`; el `status` de `RENTAL` es un valor **derivado y persistido**, recalculado en cada devolución según:

| Condición sobre los ItemRenta | RENTAL.status |
|---|---|
| Todos `activo` (y renta pagada) | `activa` |
| Al menos uno `devuelto` y al menos uno `activo` | `parcialmente_devuelta` |
| Todos `devuelto` | `completada` |

El cierre del último ítem fija `final_total` de la renta (RN-10) y dispara los ajustes de captura/reembolso del pago ([ADR-0007](0007-modelo-de-pago-e-idempotencia.md)).

## Consecuencias

**Positivas**
- Lectura y filtrado directos por columna de estado → reportes y consultas eficientes.
- Devolución parcial modelada con precisión; liquidación por ítem.

**Negativas / costos**
- Invariante "estado de cabecera == derivación de los ítems" sostenida por **lógica transaccional**, no por esquema. Mitigación: recálculo siempre dentro de la transacción de devolución + job/test de reconciliación.
- Denormalización deliberada → se documenta como tal para que no se asuma protegida por la BD.

## Enlaces

- Aterriza en: [Modelo de datos §7](../modelo-de-datos.md). Relacionado: [ADR-0007](0007-modelo-de-pago-e-idempotencia.md) (ajustes de pago por ítem).
