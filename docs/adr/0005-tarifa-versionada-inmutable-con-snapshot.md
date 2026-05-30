# ADR-0005 — Tarifa versionada inmutable + snapshot en ItemRenta

- **Estado:** aceptado
- **Fecha:** 2026-05-30
- **Origen:** RN-07, RN-08, C-08, RN-10; [Modelo de datos §8](../modelo-de-datos.md)

## Contexto y problema

El precio de una renta se calcula con la tarifa vigente al momento de crearla (RN-07) y debe quedar **congelado**: aunque la tarifa cambie después, el monto aplicado a esa renta no puede variar (RN-08, C-08). El monto final se confirma en la devolución según el tiempo de uso real (RN-10). ¿Cómo se garantiza esa inmutabilidad sin perder trazabilidad a la definición tarifaria?

## Drivers de decisión

- Inmutabilidad del precio aplicado (RN-08): predecible y justo para el cliente.
- Trazabilidad: poder responder "¿de qué definición tarifaria salió este monto?".
- Monto **auto-contenido y reconstruible** (exigencia del dominio asegurador).
- Capacidad de reportar/auditar por esquema de tarifa.

## Opciones consideradas

1. **Solo FK a `FARE` con UPDATE in-place.** Simple, pero editar la tarifa cambia retroactivamente el precio de rentas pasadas → viola RN-08.
2. **Solo snapshot de valores en `RENTAL_ITEM`.** El precio queda congelado e independiente, pero se pierde la traza a qué definición tarifaria lo originó y la capacidad de reportar por tarifa.
3. **FK a una `FARE` versionada inmutable + snapshot embebido en `RENTAL_ITEM`.** Editar una tarifa crea una **nueva versión** (`version`+1, nuevo `valid_from`) y cierra la anterior (`valid_to`); nunca hay UPDATE destructivo. El ítem guarda además una copia de los valores aplicados.

## Decisión

**Opción 3 (ambos mecanismos).**

- **Snapshot embebido** (`fare_fixed_component`, `fare_time_component`, `fare_time_unit`, `fare_relocation_charge`): es la **fuente del cálculo** del cargo (RN-10) y la garantía de inmutabilidad — auto-contenido aunque la versión de tarifa se archivara.
- **FK a `FARE` versionada** (`fare_id`): es la **traza de origen**, y habilita reportar por esquema de tarifa. `FARE` es inmutable en sus valores de precio; las ediciones generan versiones nuevas (`UNIQUE (code, version)`).

## Consecuencias

**Positivas**
- Precio congelado garantizado por diseño (RN-08, C-08) y monto reconstruible.
- Trazabilidad completa a la definición tarifaria; auditable y reportable.

**Negativas / costos**
- **Duplicación de datos** (valores en `FARE` y copiados en `RENTAL_ITEM`). Es duplicación **inmutable por diseño**: un snapshot histórico no se actualiza nunca, así que no puede desincronizarse — no es la desnormalización peligrosa habitual.
- Versionar tarifas añade complejidad de gestión (vigencias, versión activa por `code`).

## Enlaces

- Aterriza en: [Modelo de datos §8](../modelo-de-datos.md).
