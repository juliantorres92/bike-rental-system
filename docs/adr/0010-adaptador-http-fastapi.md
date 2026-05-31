# ADR-0010 — Adaptador HTTP (FastAPI): mapeo de errores, composición en memoria y validación de borde

- **Estado:** aceptado
- **Fecha:** 2026-05-31
- **Origen:** Épica E-02 (HU-05..09); [ADR-0008](0008-estilo-de-arquitectura.md) (hexagonal); [stack.md](../stack.md). Implementación en [src/bike_rental/adapters/api/](../../src/bike_rental/adapters/api/).

## Contexto y problema

El caso de uso `CreateRental` ya existía como núcleo de dominio. Para exponerlo por HTTP (lado *driving* del hexágono) hay que decidir varias cosas del adaptador sin contaminar el dominio: cómo se traducen los errores de dominio a códigos HTTP, dónde vive la validación de entrada, cómo se inyecta el caso de uso y de dónde salen los datos (no hay base de datos en este incremento). Estas decisiones son del adaptador, no del dominio.

## Drivers de decisión

- El dominio **no debe importar el framework** (ADR-0008); las decisiones de transporte viven en el adaptador.
- Respuestas HTTP semánticamente correctas y consumibles, sin filtrar trazas.
- Testeabilidad sin servidor real (sustituir la composición en tests).
- Coste proporcional al alcance (sin persistencia todavía).

## Decisiones

1. **Mapeo error de dominio → HTTP** (un único handler para la familia `RentalError`):
   - `BicycleNotFoundError`, `StationNotFoundError` → **404**
   - `BicycleNotAvailableError`, `BicycleAlreadyRentedError`, `InactiveFareError`, `IllegalRentalTransition` → **409**
   - `EmptyRentalError`, `DuplicateBicycleError` → **422**
   - `PaymentDeclinedError` → **402**
   - `RentalError` base (inesperado) → **500** (fallback)
   - Cuerpo uniforme `{error, detail}`; `error` = nombre estable del error, `detail` = mensaje legible. **Nunca** una traza.

2. **Validación en el borde (Pydantic v2):** los modelos del adaptador validan formato (UUID, lista no vacía, `extra='forbid'`); un payload malformado responde **422** (`RequestValidationError`, normalizado al mismo cuerpo `{error, detail}`) **antes** de tocar el dominio. El dominio conserva sus validaciones como red de seguridad.

3. **Inyección de dependencias:** el caso de uso y la tarifa activa se resuelven con `Depends` leyendo la **raíz de composición** desde `app.state.world`. `create_app(world)` permite que cada test construya su propio mundo → aislamiento sin estado global.

4. **Composición en memoria con datos sembrados deterministas:** no hay base de datos ni endpoints de catálogo en E-02, así que `InMemoryWorld` siembra una estación, bicicletas y una tarifa con **ids fijos**, estables para la documentación/Postman. Una renta exitosa muta ese estado en memoria.

5. **Sin `FareRepository`:** la API aplica la tarifa activa sembrada en la composición (no se resuelve por id). Es una simplificación consciente del alcance.

## Consecuencias

**Positivas**
- Contrato HTTP claro y consistente; errores legibles y sin fugas de implementación.
- Dominio intacto y framework-free; adaptador 100% testeable con `TestClient`.
- DI sustituible → tests aislados, sin singletons.

**Negativas / costos**
- Los datos sembrados son la única fuente: `station_id`/`bicycle_ids` válidos son los sembrados (otros → 404). Resolverlo requiere **descubrimiento** (épica E-03) o **persistencia real** (futuro).
- La tarifa por id y el catálogo quedan pendientes (sin `FareRepository`/`StationRepository` de lectura).
- El mapeo error→HTTP vive en el adaptador; añadir un error de dominio nuevo obliga a mapearlo (o cae al 500 de fallback).

## Enlaces

- Implementación: [src/bike_rental/adapters/api/](../../src/bike_rental/adapters/api/) · Contrato: [docs/api/openapi.yaml](../api/openapi.yaml) · Backlog: [E-02](../backlog.md).
- Relacionado: [ADR-0008](0008-estilo-de-arquitectura.md) (hexagonal), [ADR-0007](0007-modelo-de-pago-e-idempotencia.md) (saga/idempotencia que el 402 refleja).
