# Stack Tecnológico — Sistema de Renta de Bicicletas

> **Estado:** versión inicial (v0.1) · **Tipo:** documento de stack
> **Convención de idioma:** narrativa en español; identificadores/código en inglés (ver [CLAUDE.md](../CLAUDE.md)).
> **Documentos raíz:** [Arquitectura](arquitectura.md), [Modelo de datos](modelo-de-datos.md), [ADRs](adr/).
> **Decisión formal:** [ADR-0009](adr/0009-stack-tecnologico.md).

---

## 1. Propósito

La [arquitectura](arquitectura.md) decidió la *forma* (monolito modular hexagonal) de forma agnóstica al stack y dejó "huecos" tecnológicos: el servicio de aplicación, el motor relacional, el worker. Este documento los **rellena con tecnología concreta y justificada**, y **cierra las dependencias** que los ADRs dejaron abiertas (UUIDv7 nativo, índices únicos parciales, enums). No es un tutorial de configuración; es la justificación de cada elección con su trade-off.

---

## 2. Resumen del stack

| Capa | Elección | Rol en la arquitectura |
|---|---|---|
| Lenguaje | **Python 3.12+** | Lenguaje del servicio de aplicación y del dominio. |
| Framework web | **FastAPI** (async, Pydantic v2, OpenAPI) | Adaptador de entrada (API REST). |
| Persistencia | **SQLAlchemy 2.0** + **Alembic** | Adaptador de salida (repositorios) + migraciones de esquema. |
| Base de datos | **PostgreSQL** (18 recomendado) | Entidades, log de movimientos y proyecciones materializadas. |
| Worker / scheduler | **APScheduler** (o **Taskiq** si crece) | Actor Sistema: expira reservas, cierra rentas abandonadas. |
| Pruebas | **pytest** (+ pytest-asyncio) | Dominio testeado con adaptadores falsos. |
| Validación | **Pydantic v2** | Validación en los adaptadores de entrada (no en el dominio). |

---

## 3. Justificación por elección

### 3.1 Python 3.12+

- **Encaja con el entregable:** la rebanada de implementación opcional se previó en Python; mantener un solo lenguaje da coherencia.
- **Dominio expresivo:** tipado gradual + dataclasses/`typing` permiten un núcleo de dominio limpio y legible, que es lo que se evalúa.
- **Trade-off:** Python no es el más rápido en CPU ni el más fuerte en concurrencia por hilos (GIL). Para este sistema —dominado por E/S a base de datos y a la pasarela, no por cómputo— es irrelevante; el modelo `async` cubre la concurrencia de E/S. Si el cuello de botella fuera CPU, la elección se reconsideraría.

### 3.2 FastAPI como adaptador de entrada

- **Ajuste hexagonal:** el sistema de **inyección de dependencias** de FastAPI mapea de forma natural a los puertos del hexágono (ADR-0008): los controladores reciben los casos de uso como dependencias, sin acoplar el dominio al framework.
- **Contrato explícito:** genera OpenAPI automáticamente → el contrato de la API es documentación viva (apoya la disciplina de [diseño de interfaces](especificacion-funcional.md)).
- **Async nativo:** maneja bien la espera de E/S (BD, pasarela) sin bloquear.
- **Pydantic v2** valida la entrada **en el borde** (adaptadores), manteniendo el dominio libre de dependencias del framework.

### 3.3 SQLAlchemy 2.0 + Alembic

- **Repositorios como adaptador de salida:** SQLAlchemy implementa el puerto de persistencia; el dominio habla con interfaces de repositorio, no con SQLAlchemy directamente.
- **Control transaccional explícito:** el estilo 2.0 (sesión/`Unit of Work`) permite expresar con precisión el **límite transaccional** del caso central (arquitectura §8, NFR-01) — clave para la atomicidad de la renta multi-bici.
- **Alembic** versiona el esquema derivado del [modelo de datos](modelo-de-datos.md), de forma auditable y coherente con GitHub Flow.
- **Trade-off:** un ORM añade abstracción sobre SQL; para las consultas calientes (UC-05) se puede bajar a SQL explícito cuando convenga. SQLAlchemy lo permite sin abandonar el ecosistema.

### 3.4 PostgreSQL como motor relacional — y cierre de dependencias de los ADRs

PostgreSQL es la elección de **menor fricción** con el diseño: soporta de forma nativa todo lo que los ADRs y el modelo de datos dieron por necesario.

| Dependencia abierta (ADR / modelo) | Soporte en PostgreSQL |
|---|---|
| **UUIDv7** ([ADR-0002](adr/0002-uuid-v7-como-estrategia-de-llaves.md)) | Función nativa **`uuidv7()`** desde **PostgreSQL 18**. En versiones ≤17 se genera en la capa Python (p. ej. con una librería de uuid6/uuidv7) — ver §5. |
| **Índice único parcial** para RN-06 ([ADR-0006](adr/0006-estrategia-de-concurrencia.md), modelo §10) | `CREATE UNIQUE INDEX ... WHERE status='activo'` soportado desde 9.6 → RN-06 garantizado **a nivel de esquema**. |
| **Enums** (modelo §5.x) | Tipos `ENUM` nativos (o `CHECK` sobre `TEXT`); cierra la "decisión diferida" del índice de ADRs. |
| **Invariantes con `CHECK`** (RN-03, modelo §10) | `CHECK (0 <= available_inventory AND available_inventory <= capacity)`. |
| **Montos** (`DECIMAL`) | `NUMERIC/DECIMAL` exacto, sin error de coma flotante en dinero. |
| **Concurrencia optimista** ([ADR-0006](adr/0006-estrategia-de-concurrencia.md)) | MVCC + columna `version`; bloqueos a nivel de fila cuando hagan falta. |
| **Auditabilidad** (NFR-03) | Robustez transaccional para el log `MOVEMENT` append-only. |

**Recomendación de versión: PostgreSQL 18** para usar `uuidv7()` nativo. Si el entorno de despliegue fija una versión anterior, la única diferencia es **dónde** se genera el UUIDv7 (aplicación en vez de BD); el resto del diseño no cambia.

### 3.5 Worker / scheduler

- **APScheduler** para el alcance actual: simple, en proceso, suficiente para expirar reservas ([ADR-0006](adr/0006-estrategia-de-concurrencia.md)) y cerrar rentas abandonadas (C-09).
- Si la carga o la necesidad de durabilidad/reintentos creciera, se migra a **Taskiq** o Celery (cola de tareas con backend). Se documenta como camino de evolución, no como necesidad actual (coherente con el principio de "costo proporcional al alcance" del ADR-0008).

### 3.6 Pruebas

- **pytest** + **pytest-asyncio**. La arquitectura hexagonal permite testear el dominio con **adaptadores falsos** (repositorios y pasarela en memoria), sin BD ni red — pruebas rápidas y deterministas de las invariantes (atomicidad, derivación de estado, idempotencia).

---

## 4. Alternativas consideradas (resumen)

La elección de lenguaje fue una preferencia explícita (Python); dentro de ese ecosistema:

- **Framework:** FastAPI vs **Django** vs **Flask**. Django trae ORM/admin/baterías pero impone su propia estructura, que riñe con el hexagonal puro; Flask es minimalista pero exige ensamblar validación/OpenAPI a mano. FastAPI da el mejor equilibrio (async, validación, contrato) con bajo acoplamiento. → ver [ADR-0009](adr/0009-stack-tecnologico.md).
- **Motor:** PostgreSQL vs **MySQL/MariaDB**. En MySQL los índices únicos parciales y los enums se modelan distinto, lo que obligaría a mover algunas invariantes (RN-06) del esquema a la lógica. PostgreSQL minimiza esa fricción.

---

## 5. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Entorno con **PostgreSQL < 18** (sin `uuidv7()` nativo) | Generar UUIDv7 en la capa Python; el contrato del id no cambia ([ADR-0002](adr/0002-uuid-v7-como-estrategia-de-llaves.md)). |
| **GIL / CPU** si aparece cómputo pesado | El sistema es E/S-bound; si cambiara, aislar el cómputo o reconsiderar runtime. |
| Abstracción del **ORM** en consultas calientes (UC-05) | SQLAlchemy permite SQL explícito puntual sin salir del ecosistema. |
| **Acoplamiento** del dominio al framework | Pydantic/FastAPI viven solo en los adaptadores; el dominio no los importa (disciplina vigilada en PRs). |

---

## 6. Trazabilidad: ADR/arquitectura → tecnología

| Origen | Cómo lo concreta el stack |
|---|---|
| [ADR-0002](adr/0002-uuid-v7-como-estrategia-de-llaves.md) UUIDv7 | `uuidv7()` de PostgreSQL 18 (o Python en ≤17) — §3.4, §5 |
| [ADR-0003](adr/0003-ubicacion-e-inventario-como-proyecciones-materializadas.md) proyecciones + log | Transacciones SQLAlchemy 2.0; robustez de Postgres — §3.3, §3.4 |
| [ADR-0006](adr/0006-estrategia-de-concurrencia.md) optimista + reserva | Columna `version` + índice único parcial; expiración en APScheduler — §3.4, §3.5 |
| [ADR-0007](adr/0007-modelo-de-pago-e-idempotencia.md) pago/saga | `idempotency_key UNIQUE`; saga orquestada en el dominio Python — §3.4 |
| [ADR-0008](adr/0008-estilo-de-arquitectura.md) hexagonal | DI de FastAPI = puertos; SQLAlchemy/pasarela = adaptadores — §3.2, §3.3 |
| Arquitectura §9 despliegue | Servicio sin estado + worker + Postgres gestionado — (pieza de shipping) |
