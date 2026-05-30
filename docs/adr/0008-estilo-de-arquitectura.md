# ADR-0008 — Estilo de arquitectura: monolito modular hexagonal

- **Estado:** aceptado
- **Fecha:** 2026-05-30
- **Origen:** NFR-01, NFR-02, UC-01, spec §2.2; [Arquitectura §3](../arquitectura.md)

## Contexto y problema

Hay que elegir el estilo arquitectónico del sistema. La decisión condiciona los límites transaccionales, el costo operativo y la testeabilidad. El driver dominante es la **correctitud transaccional** (NFR-01): el caso central (UC-01, renta multi-bici) cruza varias entidades —bicicletas, ítems, inventario, ubicación, pago— bajo una garantía "todo o nada" (RN-05). El alcance es un **único operador** (spec §2.2).

## Drivers de decisión

- Mantener las invariantes transaccionales en un único límite (NFR-01).
- Evitar transacciones distribuidas / sagas donde una transacción local basta.
- Aislar el dominio (lo valioso) de la infraestructura (lo diferido al stack).
- Testeabilidad del núcleo sin BD ni pasarela reales.
- Costo operativo proporcional al alcance (un operador).

## Opciones consideradas

1. **Microservicios** (servicios separados para rentas, inventario, pagos…). Escalan y se despliegan independientemente, pero **parten el caso central por fronteras de red**: la renta multi-bici exigiría saga/2PC entre inventario y rentas, introduciendo consistencia eventual donde el negocio pide atomicidad. Costo operativo (despliegue, observabilidad, datos distribuidos) desproporcionado para un operador.
2. **Monolito en capas tradicional** (controlador → servicio → DAO). Simple, pero acopla el dominio a la infraestructura (servicios que dependen de detalles de persistencia/HTTP), dificultando aislar y testear las reglas de negocio.
3. **Monolito modular hexagonal** (puertos y adaptadores, módulos de dominio con límites claros). Una sola unidad desplegable → transacción local cubre el caso central; el dominio no depende de infraestructura; los módulos internos preparan una eventual extracción si el alcance creciera.

## Decisión

**Opción 3: monolito modular con arquitectura hexagonal.** Módulos de dominio: Rentas, Inventario & Ubicación, Tarifas, Pagos. Infraestructura (BD, pasarela, reloj) entra por puertos con adaptadores intercambiables.

## Consecuencias

**Positivas**
- El caso central se resuelve en **una transacción local** (NFR-01) sin saga interna; la única saga es el cruce con la pasarela externa ([ADR-0007](0007-modelo-de-pago-e-idempotencia.md)).
- Dominio testeable de forma aislada (adaptadores falsos por puerto).
- Límites de módulo claros → camino de extracción a servicios si algún día el alcance lo exige.

**Negativas / costos**
- Un monolito mal disciplinado degenera en acoplamiento; los límites de módulo deben **vigilarse** (revisión en PRs), no solo declararse.
- Escalado por unidad completa (no por módulo). Aceptable para el alcance; el servicio es sin estado salvo la BD, así que escala horizontalmente.
- La arquitectura hexagonal añade indirección (puertos/adaptadores) que para un CRUD trivial sería excesiva; aquí se justifica por la riqueza del dominio.

## Enlaces

- Aterriza en: [Arquitectura §3 y §6](../arquitectura.md). Relacionado: [ADR-0007](0007-modelo-de-pago-e-idempotencia.md) (la única frontera no transaccional).
