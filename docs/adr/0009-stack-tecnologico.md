# ADR-0009 — Stack tecnológico: Python + FastAPI + SQLAlchemy + PostgreSQL

- **Estado:** aceptado
- **Fecha:** 2026-05-30
- **Origen:** [Arquitectura](../arquitectura.md), [ADR-0008](0008-estilo-de-arquitectura.md), dependencias de [ADR-0002](0002-uuid-v7-como-estrategia-de-llaves.md)/[0006](0006-estrategia-de-concurrencia.md); detalle en [stack.md](../stack.md)

## Contexto y problema

La arquitectura (ADR-0008) definió un monolito modular hexagonal de forma agnóstica al stack y dejó huecos tecnológicos. Varios ADRs dejaron además dependencias explícitas a confirmar contra el motor: UUIDv7 nativo ([ADR-0002](0002-uuid-v7-como-estrategia-de-llaves.md)), índices únicos parciales para RN-06 ([ADR-0006](0006-estrategia-de-concurrencia.md)) y materialización de enums (índice de ADRs). Hay que fijar lenguaje, framework, ORM y motor de base de datos.

## Drivers de decisión

- Encaje con la arquitectura hexagonal (puertos/adaptadores, dominio aislado).
- Control transaccional preciso (NFR-01, el driver dominante).
- Soporte nativo de las primitivas que el diseño dio por sentadas (UUIDv7, índices parciales, enums, `DECIMAL`).
- Coherencia con el entregable (preferencia explícita por Python).
- Costo proporcional al alcance (un operador).

## Opciones consideradas

- **Lenguaje:** Python (preferencia explícita). Alternativas como JVM o Node quedaron fuera por decisión previa.
- **Framework web:** **FastAPI** vs Django vs Flask. Django impone estructura propia que riñe con el hexagonal; Flask exige ensamblar validación/OpenAPI a mano; FastAPI ofrece async + validación (Pydantic v2) + contrato OpenAPI con bajo acoplamiento.
- **Persistencia:** **SQLAlchemy 2.0 + Alembic** (control transaccional explícito, migraciones versionadas) vs ORMs más opinados.
- **Motor:** **PostgreSQL** vs MySQL/MariaDB. En MySQL los índices únicos parciales y los enums se modelan distinto, forzando a mover invariantes (RN-06) del esquema a la lógica.

## Decisión

**Python 3.12+ · FastAPI (Pydantic v2) · SQLAlchemy 2.0 + Alembic · PostgreSQL (18 recomendado) · APScheduler para el worker · pytest.**

PostgreSQL se elige por **mínima fricción** con el diseño: cubre nativamente UUIDv7 (`uuidv7()` en v18), índices únicos parciales (≥9.6), enums, `CHECK` y `DECIMAL`. En PostgreSQL ≤17, el UUIDv7 se genera en la capa Python sin cambiar el contrato del identificador.

## Consecuencias

**Positivas**
- Cierra todas las dependencias abiertas de los ADRs anteriores a nivel de esquema (no de lógica), salvo UUIDv7 en Postgres <18.
- DI de FastAPI ≈ puertos del hexágono; SQLAlchemy/pasarela como adaptadores → arquitectura testeable.
- Control transaccional explícito para el caso central (NFR-01).

**Negativas / costos**
- Python es E/S-bound-friendly pero limitado en CPU/concurrencia por hilos (GIL); aceptable para este sistema dominado por E/S.
- El ORM abstrae SQL; en consultas calientes (UC-05) puede requerir SQL explícito puntual.
- Dependencia de versión para `uuidv7()` nativo (Postgres 18).

## Enlaces

- Detalle y trazabilidad: [stack.md](../stack.md). Concreta: [ADR-0008](0008-estilo-de-arquitectura.md), [ADR-0002](0002-uuid-v7-como-estrategia-de-llaves.md), [ADR-0006](0006-estrategia-de-concurrencia.md).
