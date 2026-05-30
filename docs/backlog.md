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
