# Backlog — Incremento «Crear renta multi-bicicleta»

> **Estado:** propuesto (pendiente de aprobación del PO/cliente)
> **Alcance de este incremento:** **núcleo de dominio + tests** (hexagonal, sin API ni BD real). Los puertos (repositorios, pasarela, reloj) se implementan con **adaptadores en memoria**.
> **Origen:** [UC-01](especificacion-funcional.md) y las reglas RN-04, RN-05, RN-06, RN-08, RN-19; decisiones en [ADR-0004](adr/0004-estado-de-renta-derivado-de-itemrenta.md), [ADR-0005](adr/0005-tarifa-versionada-inmutable-con-snapshot.md), [ADR-0008](adr/0008-estilo-de-arquitectura.md).

---

## Épica

**E-01 — Crear renta de múltiples bicicletas.** Como cliente, quiero tomar varias bicicletas de una estación en una sola operación atómica, pagando una vez, para llevarme todo lo que necesito sin transacciones sueltas.

El objetivo del incremento es **probar que el diseño es implementable y correcto**, demostrando el caso central (atomicidad) con el dominio hexagonal aislado y testeable.

---

## Definición de Listo (DoR)

Una HU está lista para desarrollarse si: tiene criterios de aceptación verificables, cita la regla de negocio que la respalda, y sus dependencias (puertos, entidades) están identificadas.

## Definición de Hecho (DoD)

- Código de dominio en `src/` (Python, identificadores en inglés).
- Tests `pytest` que cubren cada criterio de aceptación, en verde.
- Sin dependencias de framework/infraestructura en el dominio (solo puertos).
- Invariantes verificadas por test, no solo por inspección.

---

## Historias de usuario

### HU-01 — Crear renta multi-bici (camino feliz)
**Como** cliente, **quiero** rentar N bicicletas disponibles de una estación en una sola renta, **para** usarlas a la vez.

**Prioridad:** Must · **Estimación:** 5 pts · **Respaldo:** RN-04, RN-19, UC-01

**Criterios de aceptación (Gherkin):**
- **Dado** una estación con 3 bicicletas `disponible` y una tarifa vigente, **cuando** el cliente crea una renta con esas 3 bicicletas y el pago se autoriza, **entonces** se crea una `Rental` con 3 `RentalItem`, cada bici pasa a `rentada`, y la renta queda `activa`.
- **Dado** lo anterior, **entonces** la renta referencia un `Payment` autorizado (RN-19).

---

### HU-02 — Atomicidad: todo o nada
**Como** cliente, **quiero** que si una de las bicicletas solicitadas no está disponible, **no se rente ninguna ni se me cobre**, para no quedar con una renta parcial inesperada.

**Prioridad:** Must · **Estimación:** 3 pts · **Respaldo:** RN-05, UC-01 flujo 3a/6a · **(caso central de la evaluación)**

**Criterios de aceptación:**
- **Dado** un intento de renta con 3 bicicletas donde 1 no está `disponible`, **cuando** se crea la renta, **entonces** se rechaza, **ninguna** bici cambia de estado y **no** se genera cobro.
- **Dado** una renta de 3 bicicletas donde el pago es **rechazado** por la pasarela, **entonces** ninguna bici queda `rentada` y la renta queda `fallida` (sin efectos colaterales).

---

### HU-03 — No doble asignación
**Como** operador del sistema, **quiero** que una bicicleta que ya está en una renta activa **no pueda** incluirse en otra, para no asignar la misma unidad dos veces.

**Prioridad:** Must · **Estimación:** 2 pts · **Respaldo:** RN-06

**Criterios de aceptación:**
- **Dado** una bicicleta ya presente en una renta `activa`, **cuando** se intenta crear otra renta que la incluya, **entonces** se rechaza la nueva renta.

---

### HU-04 — Tarifa congelada en el ítem
**Como** cliente, **quiero** que el precio que se me aplica quede fijado al momento de rentar, **para** que un cambio posterior de tarifa no altere mi cobro.

**Prioridad:** Should · **Estimación:** 2 pts · **Respaldo:** RN-08, ADR-0005

**Criterios de aceptación:**
- **Dado** una tarifa vigente al crear la renta, **cuando** se crea cada `RentalItem`, **entonces** guarda un **snapshot** de los valores de la tarifa (componente fijo, por tiempo, unidad).
- **Dado** que después cambia la tarifa, **entonces** el `RentalItem` ya creado conserva el snapshot original (el cobro no varía).

---

## Fuera de alcance de este incremento (intencional)

- **API REST (FastAPI) y persistencia real (PostgreSQL/SQLAlchemy):** los puertos se implementan en memoria. La entrada hexagonal y la BD se podrían añadir en un incremento posterior.
- **Concurrencia real** (locks/`version`, reservas con expiración, [ADR-0006](adr/0006-estrategia-de-concurrencia.md)): la invariante de no-doble-asignación (HU-03) se prueba a nivel de dominio; la concurrencia física pertenece a la capa de infraestructura.
- **Devolución, movimientos, pagos parciales:** otras épicas; aquí solo la creación de renta.

---

## Plan de trabajo (equipo simulado, multi-agente)

1. **Planning (PO):** este backlog. ← *requiere aprobación antes de codear*
2. **Implementación (devs, TDD):** modelo de dominio (entidades + value objects + puertos), caso de uso `CreateRental`, adaptadores en memoria, y tests por cada criterio de aceptación.
3. **Review (reviewer):** validación contra criterios de aceptación e invariantes (RN-05, RN-06).

---

# Épica E-02 — Exponer `CreateRental` por HTTP (adaptador FastAPI)

> **Estado:** propuesto (pendiente de aprobación del PO/cliente)
> **Alcance:** **adaptador de entrada HTTP** (FastAPI) sobre el dominio ya existente, con los adaptadores de salida **en memoria** (sin BD real). Demuestra el lado *driving* del hexágono ([ADR-0008](adr/0008-estilo-de-arquitectura.md)) de punta a punta.
> **Origen:** UC-01; reutiliza el caso de uso y los errores de dominio ya implementados ([src/](../src/README.md)).

**Como** cliente de la plataforma (app/integración), **quiero** crear una renta de varias bicicletas mediante una llamada HTTP, **para** consumir el caso de uso sin acoplarme a su implementación.

## Historias de usuario

### HU-05 — Crear renta vía `POST /rentals` (camino feliz)
**Como** consumidor de la API, **quiero** enviar un usuario, una estación y una lista de bicicletas y recibir la renta creada.

**Prioridad:** Must · **Respaldo:** UC-01, RN-04

**Criterios de aceptación:**
- **Dado** un cuerpo válido (`user_id`, `station_id`, `bicycle_ids` con ≥1 elemento) y bicicletas disponibles, **cuando** se hace `POST /rentals`, **entonces** responde **201** con `{rental_id, payment_id, status: "activa"}`.

### HU-06 — Errores de dominio → códigos HTTP correctos
**Como** consumidor, **quiero** códigos de estado HTTP que reflejen el error, **para** reaccionar adecuadamente.

**Prioridad:** Must · **Respaldo:** mapeo de los errores de dominio existentes

**Criterios de aceptación (mapeo):**
- Bicicleta/estación inexistente → **404** (`BicycleNotFoundError`, `StationNotFoundError`).
- Bici no disponible / ya rentada / tarifa inactiva → **409** (`BicycleNotAvailableError`, `BicycleAlreadyRentedError`, `InactiveFareError`).
- Lista vacía / bicis duplicadas → **422** (`EmptyRentalError`, `DuplicateBicycleError`).
- Pago rechazado → **402** (`PaymentDeclinedError`).
- En todos los casos el cuerpo incluye `{error, detail}` y **no** se filtra un stack trace.

### HU-07 — Validación de entrada en el borde
**Como** consumidor, **quiero** que una petición malformada se rechace con **422** antes de tocar el dominio.

**Prioridad:** Should · **Respaldo:** validación Pydantic en el adaptador

**Criterios de aceptación:**
- **Dado** un `bicycle_ids` vacío o un UUID malformado, **entonces** responde **422** (validación del adaptador) y el dominio nunca se invoca.

### HU-08 — `GET /health`
**Como** operador, **quiero** un endpoint de salud, **para** verificar que el servicio responde.

**Prioridad:** Could · **Criterio:** `GET /health` → **200** `{"status": "ok"}`.

### HU-09 — Documentación consumible de la API (OpenAPI + Postman)
**Como** consumidor de la API, **quiero** una forma lista de explorar y probar los endpoints, **para** integrarme rápido.

**Prioridad:** Should · **Respaldo:** OpenAPI nativo de FastAPI + colección Postman

**Criterios de aceptación:**
- La app expone **OpenAPI** en `/openapi.json` y **Swagger UI** en `/docs` (nativo de FastAPI; sin archivos extra).
- Se **exporta el contrato a `docs/api/openapi.yaml`** (volcado del spec generado por la app) como artefacto versionado, importable en el Swagger Editor.
- Existe una **colección Postman** en `docs/postman/` con requests para: `POST /rentals` (camino feliz), al menos un caso de error (p. ej. bici ya rentada → 409), y `GET /health`; más una *environment* con `base_url`.
- El `src/README.md` explica cómo levantar la API y dónde están `/docs`, el `openapi.yaml` y la colección.

## Definición de Hecho (E-02)

- Adaptador en `src/bike_rental/adapters/api/` (FastAPI). El **dominio no cambia** y no importa FastAPI.
- Inyección de dependencias: el caso de uso se resuelve por `Depends` desde una raíz de composición sustituible en tests.
- Tests con `TestClient` cubriendo HU-05..08; idealmente con `pytest.importorskip("fastapi")` para no romper la suite de dominio si FastAPI no está instalado.
- `fastapi`/`httpx` declarados como dependencia opcional `[api]` en `pyproject.toml`.

## Fuera de alcance de E-02 (intencional)

- **Persistencia real, autenticación/autorización, paginación, versionado de API.**
- **Resolución de tarifa por id** (no hay `FareRepository` aún): la API aplica una tarifa activa sembrada en la raíz de composición. Follow-up natural.

## Plan de trabajo (equipo multi-agente)

1. **Planning (PO):** esta épica E-02. ← *requiere aprobación antes de codear*
2. **Implementación (devs, TDD):** paquete `adapters/api` (modelos Pydantic, raíz de composición en memoria, app FastAPI con DI y handlers de error) + tests con `TestClient`.
3. **Review (reviewers):** mapeo de errores correcto, pureza (dominio sin FastAPI), cobertura de HU-05..08.
4. **Cierre (PO/humano):** colección Postman en `docs/postman/` + nota en `src/README.md` sobre `/docs` (Swagger) y la colección (HU-09).

---

# Épica E-03 — Endpoints de consulta (lado lectura)

> **Estado:** propuesto (pendiente de aprobación del PO/cliente)
> **Alcance:** endpoints HTTP **de solo lectura** sobre los adaptadores en memoria existentes, para **descubrir ids** y **consultar rentas**. No cambian reglas de negocio; añaden métodos de lectura a los repos y rutas `GET` al adaptador.
> **Origen:** resuelve la fricción detectada en E-02 (un consumidor no conoce los ids sembrados) y completa el lado *query* del hexágono. UC-05/UC-08 de la spec.

**Como** consumidor de la API, **quiero** consultar estaciones, sus bicicletas y una renta por id, **para** descubrir qué datos existen y verificar el resultado de una renta sin acceso a la base de datos.

## Historias de usuario

### HU-10 — Listar estaciones (`GET /stations`)
**Como** consumidor, **quiero** la lista de estaciones, **para** elegir una y conocer su inventario.

**Prioridad:** Must · **Respaldo:** UC-05

**Criterios de aceptación:**
- **Dado** el catálogo sembrado, **cuando** hago `GET /stations`, **entonces** responde **200** con una lista de `{id, code, name, capacity, available_inventory}`.

### HU-11 — Bicicletas de una estación (`GET /stations/{station_id}/bicycles`)
**Como** consumidor, **quiero** ver las bicicletas de una estación, **para** saber cuáles puedo rentar.

**Prioridad:** Must · **Respaldo:** UC-05/UC-08

**Criterios de aceptación:**
- **Dado** un `station_id` existente, **entonces** responde **200** con `[{id, code, status}]` de las bicicletas de esa estación.
- **Dado** un `station_id` inexistente, **entonces** responde **404** (`StationNotFoundError`).
- (Opcional) soporta `?available=true` para filtrar solo `disponible`.

### HU-12 — Consultar una renta (`GET /rentals/{rental_id}`)
**Como** consumidor, **quiero** consultar una renta por id, **para** verificar su estado e ítems tras crearla.

**Prioridad:** Must · **Respaldo:** UC-01 (postcondición observable)

**Criterios de aceptación:**
- **Dado** una renta existente, **entonces** responde **200** con `{id, status, estimated_total, payment_id, items: [{bicycle_id, status, estimated_amount}]}`.
- **Dado** un `rental_id` inexistente, **entonces** responde **404** (`RentalNotFoundError`).

## Definición de Hecho (E-03)

- Métodos de **lectura** en los repos/puertos en memoria (p. ej. `list_stations()`, `list_bicycles_by_station()`, `RentalRepository.get` ya existe). El dominio **no cambia su comportamiento**; solo se añade capacidad de consulta.
- Nuevos modelos de respuesta Pydantic (vistas de lectura) en el adaptador; **sin** filtrar entidades de dominio crudas.
- Si hace falta un error `RentalNotFoundError` para el 404 de HU-12, se añade a los errores de dominio y se mapea en el adaptador (404).
- Tests `TestClient` para HU-10..12 (incluidos los 404).
- Se añaden los endpoints al `openapi.yaml`, a la colección Postman y al `src/README.md`.

## Fuera de alcance de E-03 (intencional)

- **Persistencia real, paginación, filtros avanzados, auth.**
- **Mutaciones** (esas son E-04 devolución y siguientes).

## Plan de trabajo (equipo multi-agente)

1. **Planning (PO):** esta épica E-03. ← *requiere aprobación antes de codear*
2. **Implementación (devs, TDD):** métodos de lectura en repos + vistas Pydantic + rutas `GET` + tests `TestClient`.
3. **Review (reviewers):** read-only (sin mutaciones ni reglas nuevas), 404 correctos, dominio sin framework, cobertura HU-10..12.
4. **Cierre (PO/humano):** regenerar `openapi.yaml`, actualizar Postman y README.


---

# Épica E-04 — Devolución de bicicletas (UC-02)

> **Estado:** propuesto (pendiente de aprobación del PO/cliente)
> **Alcance:** caso de uso de dominio **`ReturnBicycles`** (devolución total y parcial) + endpoint HTTP que lo expone. Reutiliza el estado derivado de la renta ([ADR-0004](adr/0004-estado-de-renta-derivado-de-itemrenta.md)) y el snapshot de tarifa ([ADR-0005](adr/0005-tarifa-versionada-inmutable-con-snapshot.md)).
> **Origen:** [UC-02](especificacion-funcional.md); RN-10, RN-13, RN-14, RN-15, RN-16, RN-03.

**Como** cliente, **quiero** devolver una o varias bicicletas de una renta en una estación, **para** terminar (total o parcialmente) mi renta y dejar las bicis disponibles de nuevo.

## Historias de usuario

### HU-13 — Devolución total → renta `completada`
**Como** cliente, **quiero** devolver todas las bicicletas de mi renta, **para** cerrarla.

**Prioridad:** Must · **Respaldo:** RN-14, ADR-0004

**Criterios de aceptación:**
- **Dado** una renta `activa` con N bicicletas, **cuando** se devuelven las N en una estación con capacidad, **entonces** cada `RentalItem` queda `devuelto`, la renta queda `completada` (estado derivado), cada bicicleta vuelve a `disponible` en la estación destino y el inventario de esa estación se incrementa en N (RN-01/RN-16).

### HU-14 — Devolución parcial → renta `parcialmente_devuelta`
**Como** cliente, **quiero** devolver solo algunas bicicletas, **para** seguir usando el resto.

**Prioridad:** Must · **Respaldo:** RN-14, ADR-0004 *(caso central de la épica)*

**Criterios de aceptación:**
- **Dado** una renta `activa` con 3 bicicletas, **cuando** se devuelven 2, **entonces** esos 2 ítems quedan `devuelto`, el tercero sigue `activo`, la renta queda `parcialmente_devuelta` y la bici no devuelta sigue `rentada`.
- **Dado** una renta `parcialmente_devuelta`, **cuando** se devuelve el último ítem, **entonces** la renta pasa a `completada`.

### HU-15 — Reglas y consistencia de la devolución
**Como** sistema, **quiero** aplicar las reglas de devolución, **para** mantener las invariantes.

**Prioridad:** Must · **Respaldo:** RN-15/RN-03, RN-16, RN-12

**Criterios de aceptación:**
- No se puede devolver un ítem **ya devuelto** ni operar sobre una renta no activa/parcial → error de dominio (RN-12).
- No se puede devolver una bicicleta que **no pertenece** a esa renta → error de dominio.
- La estación destino debe tener **capacidad**; si está llena, se rechaza (RN-15/RN-03).
- Se calcula un **`final_amount`** por ítem en función del tiempo de uso (RN-10) usando el reloj y el **snapshot de tarifa** congelado (RN-08); la operación es atómica (todo o nada).

### HU-16 — Exponer la devolución por HTTP
**Como** consumidor, **quiero** un endpoint para devolver, **para** consumir el caso de uso.

**Prioridad:** Should · **Respaldo:** ADR-0010

**Criterios de aceptación:**
- `POST /rentals/{rental_id}/returns` con `{bicycle_ids, return_station_id}` → **200** con la `RentalView` actualizada (estado e ítems).
- Errores → HTTP: renta/estación inexistente **404**; ítem ya devuelto / renta no activa / estación llena / bici no pertenece **409**; cuerpo inválido **422**.
- `GET /rentals/{id}` (E-03) refleja el nuevo estado tras la devolución.

## Definición de Hecho (E-04)

- Caso de uso `ReturnBicycles` en `rental/use_cases/`, con sus errores de dominio.
- `RentalItem` gana los campos de devolución (`returned_at`, `return_station_id`, `final_amount`, `usage_minutes`) y método para marcarse devuelto; `Rental` aplica la devolución y deriva su estado (reusa `derive_status`); `Bicycle` gana la transición `rentada → disponible`; `Station` gana `increment_inventory` con chequeo de capacidad.
- Tests `pytest` (dominio) y `TestClient` (API) para HU-13..16, incluidos los caminos de error.
- Cierre: regenerar `openapi.yaml`, ampliar Postman (crear → devolver parcial → `GET` muestra `parcialmente_devuelta`) y actualizar README.

## Fuera de alcance de E-04 (intencional)

- **Liquidación del pago** (captura/reembolso por ítem, C-04b): el pago autorizado se mantiene; el ajuste monetario real es follow-up.
- **Cargo por reubicación** (C-05) al devolver en otra estación: se permite devolver en otra estación, sin cargo extra por ahora.
- Concurrencia física, persistencia real.

## Plan de trabajo (equipo multi-agente)

1. **Planning (PO):** esta épica E-04. ← *requiere aprobación antes de codear*
2. **Implementación (devs, TDD):** dominio (`ReturnBicycles` + cambios en entidades) y API (`POST /rentals/{id}/returns`) + tests.
3. **Review (reviewers):** atomicidad y estado derivado, invariantes (capacidad/pertenencia/estado), pureza, cobertura HU-13..16.
4. **Cierre (PO/humano):** OpenAPI + Postman + README.
