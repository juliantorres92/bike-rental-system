# PRD-0001 — Renombrar el módulo `bicycle/` → `inventory/`

- **Tipo:** deuda técnica (refactor de nomenclatura, sin cambio de comportamiento)
- **Estado:** propuesto
- **Fecha:** 2026-05-31
- **Origen:** alineación con [ADR-0008](../adr/0008-estilo-de-arquitectura.md) (módulos de dominio: *Rentas, Inventario & Ubicación, Tarifas, Pagos*)
- **Rama:** `refactor/rename-bicycle-to-inventory`

## 1. Problema

El [ADR-0008](../adr/0008-estilo-de-arquitectura.md) define cuatro módulos de
dominio, uno de ellos llamado **«Inventario & Ubicación»**. En el código ese
módulo vive en la carpeta `src/bike_rental/bicycle/`, que contiene tanto la
entidad `Bicycle` (unidad rentable) como `Station` (punto físico con inventario y
capacidad). El nombre `bicycle` **no refleja** la responsabilidad real del módulo
—gestionar el inventario y la ubicación— y rompe la trazabilidad nombre-a-nombre
entre el ADR y el código.

No es un desvío arquitectónico (la estructura modular hexagonal se cumple), pero
sí una **inconsistencia de nomenclatura** que obliga a un lector a inferir que
`bicycle/` = «Inventario & Ubicación».

## 2. Decisión

Renombrar el paquete `bike_rental.bicycle` → `bike_rental.inventory`.

**Por qué `inventory`** (y no `location`, `fleet` o `inventory_location`): es el
término más cercano y conciso a la etiqueta del ADR-0008, encaja con el lenguaje
ya usado (`available_inventory`, `decrement_inventory`) y mantiene el nombre de
paquete idiomático en Python.

**Qué NO cambia:** la entidad `Bicycle`, los identificadores `BicycleId`,
`BicycleStatus`, `bicycle_id`, `bicycle_repo`, etc. Solo cambia la **ruta del
paquete** (la carpeta y los `import`). El comportamiento del dominio es idéntico.

## 3. Alcance

- **15 archivos `.py`** importan el paquete (`src/` y `tests/`): actualizar la ruta
  de import `bicycle` → `inventory`.
- **`src/README.md`** (árbol de carpetas, línea ~19): actualizar `bicycle/` →
  `inventory/`.
- **`ADR-0008`**: añadir una nota de cierre que enlace el módulo «Inventario &
  Ubicación» con la carpeta `inventory/` (cierra la trazabilidad).
- `pyproject.toml` usa autodescubrimiento de paquetes → **no requiere cambios**.

### Fuera de alcance (intencional)
- Renombrar la entidad `Bicycle` o cualquier identificador de dominio.
- Mover `Station` a un módulo propio (decisión futura si el dominio crece:
  rebalanceo entre estaciones, mantenimiento).
- Cualquier cambio de comportamiento, regla de negocio o test de criterio.

## 4. Historia de usuario técnica

### HU-T01 — Alinear el nombre del módulo de inventario con el ADR-0008
**Como** mantenedor del sistema, **quiero** que el módulo «Inventario & Ubicación»
viva en una carpeta llamada `inventory/`, **para** que la nomenclatura del código
sea trazable con la arquitectura documentada y autoexplicativa.

**Prioridad:** Should · **Estimación:** 1 pt · **Respaldo:** ADR-0008

**Criterios de aceptación (Gherkin):**
- **Dado** el paquete `bike_rental.bicycle`, **cuando** se completa el refactor,
  **entonces** existe `bike_rental.inventory` con `entities.py`, `enums.py` y
  `__init__.py`, y `bike_rental.bicycle` ya no existe como paquete.
- **Dado** que 15 archivos importaban `bicycle`, **entonces** todos importan
  `inventory` y no queda ninguna referencia colgante a `..bicycle.` /
  `bike_rental.bicycle`.
- **Dado** el baseline de 57 tests en verde, **cuando** se completa el refactor,
  **entonces** los 57 tests siguen en verde **sin modificar ningún assert** (la
  red de seguridad demuestra ausencia de cambio de comportamiento).
- **Dado** el `src/README.md` y el `ADR-0008`, **entonces** reflejan el nuevo
  nombre del módulo.

## 5. Plan de trabajo (equipo multi-agente simulado, secuencial)

1. **Planning (PO):** este PRD + HU-T01. ← *artefacto actual*
2. **Implementación (dev, refactor seguro):** `git mv` del paquete, actualizar los
   imports de los 15 archivos, correr la suite como red de seguridad (verde→verde).
3. **Review (reviewer):** verificar que no queda ninguna referencia a `bicycle` como
   paquete, que el dominio sigue sin framework, y que ningún assert cambió.
4. **Cierre (PO/humano):** actualizar `src/README.md` y `ADR-0008`; abrir PR.

> **Nota de orquestación:** un rename es un cambio **atómico y secuencial** (todos
> los imports dependen entre sí), por lo que NO se paraleliza el trabajo. El valor
> «multi-agente» aquí es aplicar el **flujo de roles** (PO → dev → reviewer), no el
> fan-out. Se documenta así para no confundir disciplina de proceso con paralelismo.

## 6. Riesgos y mitigación

| Riesgo | Mitigación |
|---|---|
| Un import queda sin actualizar | La suite de 57 tests falla al instante (red de seguridad) |
| Renombrar de más (la palabra «bicycle» fuera del paquete) | Solo se tocan rutas de import `..bicycle.` / `bike_rental.bicycle`, nunca `Bicycle`/`bicycle_id` |
| Pérdida del historial de git | Usar `git mv` (preserva el historial del archivo) |
