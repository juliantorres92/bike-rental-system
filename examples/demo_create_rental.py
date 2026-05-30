"""Demo ejecutable del caso de uso CreateRental (UC-01).

Cablea los adaptadores EN MEMORIA del dominio hexagonal y ejecuta tres
escenarios para "ver funcionar" el diseño sin API ni base de datos:

  1. Camino feliz: rentar 3 bicicletas en una transacción.
  2. Atomicidad (RN-05): el pago es rechazado -> nada cambia.
  3. No doble asignación (RN-06): una bici ya rentada no entra en otra renta.

No requiere pytest ni dependencias externas (el dominio es Python puro).
Ejecutar desde la raíz del repo:

    python3 examples/demo_create_rental.py
"""

from __future__ import annotations

import os
import sys
from decimal import Decimal

# Hacer importable el paquete bajo src/ sin instalar nada.
_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from bike_rental.adapters.fake_payment_gateway import AUTHORIZE, REJECT, FakePaymentGateway
from bike_rental.adapters.fixed_clock import DeterministicIdGenerator, FixedClock, utc
from bike_rental.adapters.in_memory_bicycle_repository import InMemoryBicycleRepository
from bike_rental.adapters.in_memory_payment_repository import InMemoryPaymentRepository
from bike_rental.adapters.in_memory_rental_repository import InMemoryRentalRepository
from bike_rental.adapters.in_memory_station_repository import InMemoryStationRepository
from bike_rental.bicycle.entities import Bicycle, Station
from bike_rental.bicycle.enums import BicycleStatus
from bike_rental.fare.entities import Fare
from bike_rental.fare.enums import TimeUnit
from bike_rental.rental.errors import BicycleAlreadyRentedError, PaymentDeclinedError
from bike_rental.rental.use_cases.create_rental import CreateRental, CreateRentalCommand
from bike_rental.shared.ids import new_bicycle_id, new_fare_id, new_station_id, new_user_id
from bike_rental.shared.money import Money


def build(*, bicycles, station, outcome=AUTHORIZE):
    """Cablea adaptadores en memoria + el caso de uso (composición del hexágono)."""
    bicycle_repo = InMemoryBicycleRepository(bicycles)
    station_repo = InMemoryStationRepository([station])
    rental_repo = InMemoryRentalRepository()
    payment_repo = InMemoryPaymentRepository()
    gateway = FakePaymentGateway(outcome=outcome)
    use_case = CreateRental(
        bicycle_repo=bicycle_repo,
        station_repo=station_repo,
        rental_repo=rental_repo,
        payment_repo=payment_repo,
        payment_gateway=gateway,
        clock=FixedClock(utc(2026, 5, 30, 12, 0)),
        id_generator=DeterministicIdGenerator(),
    )
    return use_case, bicycle_repo, station_repo, rental_repo, payment_repo, gateway


def seed(*, inventory=5, n=3):
    station = Station(
        id=new_station_id(), code="ST-001", name="Estacion Centro",
        capacity=10, available_inventory=inventory,
    )
    bikes = [
        Bicycle(id=new_bicycle_id(), code=f"BIKE-{i}", status=BicycleStatus.DISPONIBLE,
                station_id=station.id)
        for i in range(1, n + 1)
    ]
    fare = Fare(
        id=new_fare_id(), code="STANDARD",
        fixed_component=Money(Decimal("2000.00")),
        time_component=Money(Decimal("150.00")),
        time_unit=TimeUnit.MINUTO,
        relocation_charge=Money(Decimal("1000.00")),
        version=1, is_active=True,
    )
    return station, bikes, fare


def hr(title):
    print("\n" + "=" * 64)
    print(title)
    print("=" * 64)


def main():
    # ----- Escenario 1: camino feliz -----------------------------------
    hr("1) CAMINO FELIZ — rentar 3 bicicletas en una sola transaccion")
    station, bikes, fare = seed(inventory=5, n=3)
    uc, bike_repo, station_repo, rental_repo, payment_repo, gw = build(
        bicycles=bikes, station=station
    )
    print(f"Inventario de la estacion ANTES: {station_repo.get(station.id).available_inventory}")

    result = uc.execute(CreateRentalCommand(
        user_id=new_user_id(), station_id=station.id,
        bicycle_ids=[b.id for b in bikes], fare=fare,
    ))

    rental = rental_repo.get(result.rental_id)
    payment = payment_repo.get(result.payment_id)
    print(f"\nRenta creada -> status: {rental.status.value}")
    print(f"  total estimado: {rental.estimated_total}")
    print(f"  items ({len(rental.items)}):")
    for it in rental.items:
        print(f"    - bici {str(it.bicycle_id)[:8]}… | tarifa congelada: "
              f"fijo={it.fare_fixed_component} + tiempo={it.fare_time_component}"
              f"/{it.fare_time_unit.value} | estimado={it.estimated_amount}")
    print(f"  pago -> {payment.status.value} | {payment.authorized_amount} | ref {payment.gateway_reference}")
    print("\nEstado de las bicicletas tras la renta:")
    for b in bikes:
        st = bike_repo.get(b.id)
        print(f"    - {b.code}: {st.status.value} (station_id={st.station_id})")
    print(f"Inventario de la estacion DESPUES: {station_repo.get(station.id).available_inventory}  "
          f"(decrementado en {len(bikes)} — RN-01)")

    # ----- Escenario 2: atomicidad (pago rechazado) --------------------
    hr("2) ATOMICIDAD (RN-05) — el pago es rechazado, NADA cambia")
    station2, bikes2, fare2 = seed(inventory=5, n=3)
    uc2, bike_repo2, station_repo2, rental_repo2, payment_repo2, gw2 = build(
        bicycles=bikes2, station=station2, outcome=REJECT
    )
    failed_rental_id = None
    try:
        uc2.execute(CreateRentalCommand(
            user_id=new_user_id(), station_id=station2.id,
            bicycle_ids=[b.id for b in bikes2], fare=fare2,
        ))
    except PaymentDeclinedError as exc:
        failed_rental_id = exc.rental_id
        print(f"Excepcion de dominio: {type(exc).__name__} -> {exc}")
        print(f"  la renta queda observable como: {rental_repo2.get(failed_rental_id).status.value}")
    print("Verificacion de 'nada cambio':")
    print(f"  bicicletas: {[bike_repo2.get(b.id).status.value for b in bikes2]}  (todas siguen disponible)")
    sin_pago = payment_repo2.get_by_rental(failed_rental_id) is None
    print(f"  cobro efectivo: {'sin pago autorizado' if sin_pago else 'HAY PAGO (mal)'}")
    print(f"  inventario estacion: {station_repo2.get(station2.id).available_inventory}  (intacto)")
    print(f"  llamadas a la pasarela: {len(gw2.calls)}  (se intento 1, pero sin efecto)")

    # ----- Escenario 3: no doble asignacion ----------------------------
    hr("3) NO DOBLE ASIGNACION (RN-06) — una bici ya rentada no entra en otra renta")
    # Reusamos el wiring del escenario 1: BIKE-1 ya esta en una renta activa.
    try:
        uc.execute(CreateRentalCommand(
            user_id=new_user_id(), station_id=station.id,
            bicycle_ids=[bikes[0].id], fare=fare,
        ))
    except BicycleAlreadyRentedError as exc:
        print(f"Excepcion de dominio: {type(exc).__name__} -> {exc}")
        print("  La segunda renta se rechaza: la bicicleta ya esta en una renta activa.")

    print("\n" + "-" * 64)
    print("Demo completado. El dominio garantiza atomicidad, no doble asignacion")
    print("y tarifa congelada — sin API ni base de datos (adaptadores en memoria).")


if __name__ == "__main__":
    main()
