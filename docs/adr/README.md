# Architecture Decision Records (ADRs)

Este directorio registra las **decisiones de arquitectura** del sistema de renta de bicicletas: por qué se eligió cada opción, qué alternativas se descartaron y con qué consecuencias. Cada ADR es inmutable una vez aceptado; si una decisión cambia, se crea un ADR nuevo que **supersede** al anterior (no se edita el viejo).

## Formato

Se usa una variante ligera de [MADR](https://adr.github.io/madr/) (Markdown Any Decision Records). Cada ADR tiene: contexto y problema, drivers de decisión, opciones consideradas (con pros/contras), decisión y consecuencias. Los ADRs citan la regla de negocio (`RN-xx`), caso de uso (`UC-xx`) o caso borde (`C-xx`) de la [especificación funcional](../especificacion-funcional.md) que los origina, y la sección del [modelo de datos](../modelo-de-datos.md) donde aterrizan.

## Estados

`propuesto` → `aceptado` → (`superseded por ADR-XXXX` | `obsoleto`). En este entregable los ADRs nacen `aceptado` porque documentan decisiones ya tomadas y justificadas durante el diseño.

## Índice

| ADR | Título | Estado | Origen (spec / modelo) |
|---|---|---|---|
| [0001](0001-registrar-decisiones-de-arquitectura.md) | Registrar decisiones de arquitectura con ADRs | aceptado | proceso |
| [0002](0002-uuid-v7-como-estrategia-de-llaves.md) | UUIDv7 como estrategia de llaves primarias | aceptado | modelo §4 |
| [0003](0003-ubicacion-e-inventario-como-proyecciones-materializadas.md) | Ubicación e inventario como proyecciones materializadas sobre un log de movimientos | aceptado | C-01, RN-01, modelo §6/§9 |
| [0004](0004-estado-de-renta-derivado-de-itemrenta.md) | Estado de Renta derivado del estado de sus ItemRenta | aceptado | C-04, RN-14, modelo §7 |
| [0005](0005-tarifa-versionada-inmutable-con-snapshot.md) | Tarifa versionada inmutable + snapshot en ItemRenta | aceptado | RN-08, C-08, modelo §8 |
| [0006](0006-estrategia-de-concurrencia.md) | Concurrencia: control optimista + reserva con expiración | aceptado | C-03, NFR-02 |
| [0007](0007-modelo-de-pago-e-idempotencia.md) | Modelo de pago: un Pago por Renta, idempotencia y saga de compensación | aceptado | C-06, RN-19, RN-20 |
| [0008](0008-estilo-de-arquitectura.md) | Estilo de arquitectura: monolito modular hexagonal | aceptado | NFR-01, NFR-02, [arquitectura](../arquitectura.md) |

## Decisiones diferidas

- **Materialización física de enums** (tipo nativo vs `CHECK` sobre `TEXT` vs tabla de catálogo): depende del motor de base de datos; se decidirá en el futuro **ADR de stack tecnológico**.
- **Estilo de arquitectura, capas y despliegue**: se tratará en el documento de arquitectura técnica (pieza posterior) y sus ADRs asociados.
- **Políticas de negocio abiertas** de la spec §8 que no son estructurales (C-02 degradación de renta, C-05 cargo por reubicación, C-07 estación llena, C-09 timeout de renta): se resolverán como ADRs de política cuando se prioricen; hoy quedan con la recomendación tentativa de la spec.
