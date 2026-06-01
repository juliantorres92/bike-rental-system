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
├── inventory/       # Inventario & Ubicación: Bicycle, Station + estados (ADR-0008)
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

## API HTTP (adaptador FastAPI, E-02)

Adaptador de entrada que expone `CreateRental` por HTTP (`src/bike_rental/adapters/api/`),
con los adaptadores de salida en memoria. El dominio no cambia ni importa FastAPI.

```bash
.venv/bin/pip install fastapi httpx uvicorn    # deps del adaptador [api]
.venv/bin/uvicorn bike_rental.adapters.api.app:create_app --factory --app-dir src
```

> No hace falta instalar el paquete: `--app-dir src` pone el código en el path.
> (La instalación editable `pip install -e ".[api]"` requiere pip ≥ 21.3.)

- **Swagger UI:** http://127.0.0.1:8000/docs · **OpenAPI:** `/openapi.json`
- **Contrato versionado:** [docs/api/openapi.yaml](../docs/api/openapi.yaml)
- **Colección Postman:** [docs/postman/](../docs/postman/) (colección + environment `local`).
  Los ids del camino feliz son deterministas, así que funcionan contra el server recién levantado.

Endpoints:
- `POST /rentals` (201) — crear renta multi-bici (E-02).
- `GET /stations` (200) — listar estaciones / descubrir ids (E-03).
- `GET /stations/{id}/bicycles` (200 · 404) — bicicletas de una estación; `?available=true` filtra disponibles (E-03).
- `GET /rentals/{id}` (200 · 404) — consultar una renta creada (E-03).
- `POST /rentals/{id}/returns` (200 · 404 · 409) — devolver bicicletas, total o parcial (E-04).
- `GET /health` (200).

Errores de dominio → 404 / 409 / 422 / 402 con cuerpo `{error, detail}`.

> **Reloj:** el servidor en vivo usa un `SystemClock` (tiempo real), así que
> `started_at`/`returned_at` y los minutos facturados (RN-10) reflejan el reloj
> de pared. Los tests inyectan un `FixedClock` determinista que avanzan a mano.

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
| API HTTP HU-05..08 (FastAPI) | `tests/test_api_create_rental.py` |
| API consultas HU-10..12 (GET) | `tests/test_api_read_endpoints.py` |
| Devolución dominio HU-13..15 (UC-02) | `tests/test_hu13_16_return_bicycles.py` |
| API devolución HU-16 (POST returns) | `tests/test_api_return_bicycles.py` |

## Fuera de alcance (trabajo posterior)

Persistencia real (SQLAlchemy + PostgreSQL), concurrencia física
(locks/reservas, ADR-0006), autenticación/autorización, liquidación del pago
en la devolución (captura/reembolso, C-04b), cargo por reubicación (C-05), y
las épicas de movimientos entre estaciones.
