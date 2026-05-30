# ADR-0006 — Concurrencia: control optimista + reserva con expiración

- **Estado:** aceptado
- **Fecha:** 2026-05-30
- **Origen:** C-03, NFR-02, RN-02, RN-06, UC-01; [Modelo de datos §5.3/§5.7/§10](../modelo-de-datos.md)

## Contexto y problema

Dos clientes pueden intentar rentar la **última bicicleta** disponible al mismo tiempo (C-03). El sistema debe evitar la doble asignación (RN-06, NFR-02) sin degradar la experiencia interactiva: entre que el cliente selecciona bicicletas (UC-01, paso 1) y confirma el pago (paso 6) puede pasar un tiempo no trivial, y mantener la base bloqueada durante esa ventana es inaceptable.

## Drivers de decisión

- Correctitud: nunca dos rentas activas sobre la misma bicicleta (RN-06).
- No bloquear recursos durante la decisión humana (selección → pago).
- Experiencia: el cliente debe enterarse pronto si "su" bici ya no está.
- Simplicidad operativa.

## Opciones consideradas

1. **Bloqueo pesimista** (`SELECT ... FOR UPDATE` sobre la bici/inventario durante toda la transacción de renta). Garantiza exclusión, pero si abarca la ventana selección→pago, mantiene locks largos → contención y riesgo de deadlock. Si solo abarca la confirmación, no protege la fase de selección.
2. **Control optimista puro** (columna `version`; se detecta el conflicto al confirmar y se reintenta). Sin locks largos, pero el cliente solo descubre el conflicto al final, tras decidir y pagar → mala experiencia en el caso de la "última bici".
3. **Reserva con expiración + control optimista al confirmar.** Al seleccionar, se crea una **reserva** temporal (con timeout) que retira la bici del pool disponible; si la renta no se confirma a tiempo, el scheduler libera la reserva (Actor Sistema). La confirmación final usa la columna `version` para cerrar cualquier ventana de carrera residual.

## Decisión

**Opción 3.** Reserva con expiración para la fase interactiva (evita que dos clientes avancen con la misma bici y da feedback temprano), respaldada por **control optimista** (`version` en `BICYCLE` y `RENTAL_ITEM`) en la confirmación. La expiración de reservas la dispara el Actor Sistema/scheduler (coherente con la spec §3).

## Consecuencias

**Positivas**
- Sin locks largos durante la decisión del cliente; buena concurrencia de lectura/escritura.
- Feedback temprano en el caso de la última bicicleta.
- La detección optimista al confirmar cubre la carrera residual (RN-06, NFR-02).

**Negativas / costos**
- Introduce el concepto de **reserva** y su expiración (estado y job de limpieza) → más complejidad que el optimista puro.
- Requiere elegir un timeout de reserva (parámetro de negocio); muy corto frustra al cliente, muy largo reduce disponibilidad. Se calibra con datos.
- Soporte de **índice único parcial** para RN-06 (`UNIQUE (bicycle_id) WHERE status='activo'`) depende del motor → se confirma en el ADR de stack; si no, la exclusión recae en la lógica transaccional.

## Enlaces

- Aterriza en: [Modelo de datos §5.3, §5.7, §10](../modelo-de-datos.md). Relacionado: [ADR-0003](0003-ubicacion-e-inventario-como-proyecciones-materializadas.md) (las proyecciones de inventario se ajustan bajo estas operaciones).
