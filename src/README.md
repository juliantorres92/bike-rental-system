# Implementación de referencia — `CreateRental`

Implementación del caso de uso **"crear renta multi-bicicleta"** (UC-01) como
**núcleo de dominio hexagonal** (ADR-0008). Es una prueba de que el diseño
documentado es implementable y correcto — **no** un producto completo.

- **Alcance:** dominio + tests, con adaptadores **en memoria**. Sin API real ni
  base de datos (eso es trabajo posterior). El dominio **no importa frameworks**.
- **Backlog:** [docs/backlog.md](../docs/backlog.md) — historias HU-01..HU-04.
- **Diseño:** [especificación](../docs/especificacion-funcional.md) ·
  [modelo de datos](../docs/modelo-de-datos.md) · [ADRs](../docs/adr/) ·
  [arquitectura](../docs/arquitectura.md) · [stack](../docs/stack.md).

## Estructura (hexagonal)

```
src/bike_rental/
├── shared/          # value objects transversales (Money, ids)
├── bicycle/         # entidad Bicycle, Station + estados
├── fare/            # Fare (versionada, snapshot RN-08)
├── payment/         # Payment + idempotencia (RN-20)
├── rental/
│   ├── entities.py      # Rental, RentalItem (estado derivado, ADR-0004)
│   ├── ports.py         # puertos (interfaces) del hexágono
│   ├── errors.py        # errores de dominio
│   └── use_cases/create_rental.py   # CreateRental (8 pasos atómicos)
└── adapters/        # implementaciones EN MEMORIA de los puertos
```

## Cómo ejecutar

Tests (requiere pytest en un venv):

```bash
python3 -m venv .venv
.venv/bin/pip install pytest
.venv/bin/python -m pytest -q        # o -v para ver cada test
```

Demo ejecutable (no requiere pytest — dominio Python puro):

```bash
python3 examples/demo_create_rental.py
```

El demo muestra los tres comportamientos clave funcionando: camino feliz,
atomicidad ante pago rechazado y rechazo de doble asignación.

## Mapa criterio → test

| Historia / regla | Test |
|---|---|
| HU-01 camino feliz (RN-04, RN-19) | `tests/test_hu01_create_rental_happy_path.py` |
| HU-02 atomicidad (RN-05) | `tests/test_hu02_atomicity.py` |
| HU-03 no doble asignación (RN-06) | `tests/test_hu03_no_double_assignment.py` |
| HU-04 tarifa congelada (RN-08) | `tests/test_hu04_frozen_fare.py` |
| Idempotencia del cobro (RN-20) | `tests/test_rn20_payment_idempotency.py` |
| Tarifa inactiva rechazada | `tests/test_create_rental_validation.py` |
| Máquina de estados de la renta (RN-12) | `tests/test_rental_state_machine.py` |

## Fuera de alcance (trabajo posterior)

Adaptador HTTP (FastAPI), persistencia real (SQLAlchemy + PostgreSQL),
concurrencia física (locks/reservas, ADR-0006), y las épicas de devolución,
movimientos y pagos parciales.
