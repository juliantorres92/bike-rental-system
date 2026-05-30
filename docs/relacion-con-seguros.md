# Por qué este modelado transfiere al dominio de seguros

> **Estado:** nota de contexto · **Tipo:** puente de dominio
> **Propósito:** mostrar que las decisiones de diseño de este ejercicio no son específicas de bicicletas — son los mismos problemas que enfrenta el software de seguros, resueltos con las mismas herramientas.

---

## La idea

El caso (renta de bicicletas) es el lienzo, pero las **tensiones de diseño** que se resolvieron son las que dominan un sistema de seguros: contratos con vigencia, precios que no pueden cambiar retroactivamente, eventos auditables, cobros idempotentes con terceros y consistencia transaccional sobre dinero. Lo que se diseñó aquí se reusa casi 1:1 cambiando los nombres.

## Análogos de modelado

| En la renta de bicicletas | En seguros | Decisión de diseño que se reusa |
|---|---|---|
| `Renta` (contrato de uso con inicio/fin) | **Póliza** | Cabecera con estado derivado de sus líneas; ciclo de vida explícito ([ADR-0004](adr/0004-estado-de-renta-derivado-de-itemrenta.md)) |
| `ItemRenta` (una bici dentro de la renta) | **Cobertura / riesgo asegurado** dentro de la póliza | Líneas con su propio estado y liquidación; el todo se cierra con la última línea |
| `Tarifa` vigente y **congelada** en el ítem | **Prima** calculada con la tarifa vigente y **congelada** en la póliza | Versionado inmutable + snapshot ([ADR-0005](adr/0005-tarifa-versionada-inmutable-con-snapshot.md)): el precio no cambia retroactivamente |
| Daño / robo de una bicicleta | **Siniestro / reclamación** | Evento que altera el estado del contrato y dispara liquidación |
| `Movimiento` (log append-only de cambios) | **Bitácora de eventos de la póliza** (endosos, siniestros) | Log auditable y reconstruible como fuente de verdad ([ADR-0003](adr/0003-ubicacion-e-inventario-como-proyecciones-materializadas.md)) |
| `Pago` con idempotencia y saga | **Cobro de prima / pago de indemnización** | Idempotencia + compensación frente a un tercero ([ADR-0007](adr/0007-modelo-de-pago-e-idempotencia.md)) |
| Devolución parcial de una renta multi-bici | **Cancelación parcial de coberturas** de una póliza | Estado del contrato derivado del estado de sus líneas |
| Atomicidad de la renta multi-bici | **Emisión atómica** de una póliza con varias coberturas | Una transacción "todo o nada" (NFR-01) |

## Por qué importa para el rol

Tres propiedades que se trataron como ciudadanas de primera clase aquí son exactamente las que un sistema asegurador no puede equivocar:

1. **Inmutabilidad y trazabilidad del dinero.** La prima congelada y los montos auto-contenidos ([ADR-0005](adr/0005-tarifa-versionada-inmutable-con-snapshot.md)) son la misma exigencia que "lo que se cotizó es lo que se cobra, y debe poder auditarse años después".
2. **Eventos auditables reconstruibles.** El log de movimientos ([ADR-0003](adr/0003-ubicacion-e-inventario-como-proyecciones-materializadas.md)) es el patrón de la bitácora de endosos y siniestros: el estado actual es una proyección, la verdad es el historial.
3. **Consistencia transaccional con terceros.** La idempotencia y la saga del cobro ([ADR-0007](adr/0007-modelo-de-pago-e-idempotencia.md)) son las mismas que median entre el sistema y una pasarela, un reasegurador o un sistema de cobranza.

El ejercicio se resolvió pensando en estas propiedades, no en bicicletas. Esa es la transferencia.
