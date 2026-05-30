# ADR-0003 — Ubicación e inventario como proyecciones materializadas sobre un log de movimientos

- **Estado:** aceptado
- **Fecha:** 2026-05-30
- **Origen:** C-01, RN-01, RN-16, RN-17, RN-18, NFR-03, UC-05, UC-08; [Modelo de datos §6 y §9](../modelo-de-datos.md)

## Contexto y problema

El sistema debe responder en todo momento, con exactitud y rápido, a dos preguntas: *¿dónde está cada bicicleta?* (UC-08) y *¿qué hay disponible en cada estación?* (UC-05, la lectura más frecuente, NFR-06). A la vez, todo cambio de ubicación debe ser auditable y reconstruible (RN-16/17/18, NFR-03). Hay tensión entre **lectura rápida** (favorece dato materializado) y **una sola fuente de verdad sin desincronía** (favorece dato derivado).

## Drivers de decisión

- Lectura interactiva de disponibilidad y ubicación (UC-05, UC-08, NFR-06).
- Auditabilidad: todo movimiento registrado y reconstruible (RN-17, NFR-03).
- Evitar el **doble conteo**: una bici en tránsito no cuenta en ninguna estación (RN-01).
- Consistencia entre ubicación, estado e inventario sin estados ambiguos.

## Opciones consideradas

1. **Derivar todo en lectura** (sin tablas materializadas): ubicación e inventario se calculan por agregación sobre el log de movimientos cada vez. Una sola fuente, cero desincronía. Pero cada consulta de disponibilidad agrega sobre el historial → penaliza la lectura caliente (UC-05).
2. **Materializar sin log** (solo el estado actual, sin historial de movimientos): lectura O(1), pero se pierde la auditabilidad y la capacidad de reconstruir; un dato corrupto no se puede recuperar.
3. **Log append-only + proyecciones materializadas** (CQRS-lite): `MOVEMENT` es el registro inmutable y auditable; `BICYCLE_LOCATION` (1:1 con la bici) y `STATION.available_inventory` son **proyecciones** actualizadas en la misma transacción que confirma el movimiento, y reconstruibles a partir del log.

## Decisión

**Opción 3.** 

- `MOVEMENT` es **append-only** y registra **todo** cambio de estación (RN-17): alta, rebalanceo, **renta y devolución** (estas también generan filas de movimiento, no solo cambian la ubicación — así el log es la fuente única de todo cambio).
- `BICYCLE_LOCATION` es 1:1 con `BICYCLE` (`bicycle_id` como PK y FK), con un `location_type` explícito (`en_estacion` / `en_poder_cliente` / `en_transito`) que elimina la ambigüedad del `station_id` NULL.
- `STATION.available_inventory` se mantiene transaccionalmente; su definición exacta es el conteo de bicis `disponible` y `en_estacion` (RN-01).
- Ambas proyecciones se actualizan **en la misma transacción** que el cambio de estado y se pueden **reconstruir** reproduciendo el log.

## Consecuencias

**Positivas**
- Lectura O(1) para UC-05 y UC-08; auditabilidad total (NFR-03); reconstruibilidad ante corrupción.
- `location_type` y la regla "en tránsito no cuenta" eliminan el doble conteo (RN-01) y los estados ambiguos (RN-18).

**Negativas / costos**
- La igualdad *proyección == fold del log* **no la garantiza el esquema**: depende de disciplina transaccional. Mitigación: actualizar siempre dentro de la misma transacción + job/test de reconciliación.
- Renta/devolución generan filas de movimiento → más volumen en `MOVEMENT`. Aceptable por la trazabilidad que exige el dominio.

## Enlaces

- Aterriza en: [Modelo de datos §6 y §9](../modelo-de-datos.md). Relacionado: [ADR-0006](0006-estrategia-de-concurrencia.md) (las proyecciones se tocan bajo concurrencia).
