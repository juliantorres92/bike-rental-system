# ADR-0002 — UUIDv7 como estrategia de llaves primarias

- **Estado:** aceptado
- **Fecha:** 2026-05-30
- **Origen:** [Modelo de datos §4](../modelo-de-datos.md); RN-20, C-06

## Contexto y problema

Toda entidad de negocio necesita una llave primaria estable. La elección permea el esquema completo, los índices, las llamadas a sistemas externos y la trazabilidad. En un dominio asegurador los identificadores aparecen en logs, reportes, claves de idempotencia hacia la pasarela y, eventualmente, en exportaciones a un data warehouse. ¿Entero autoincremental o UUID? Y si UUID, ¿qué variante?

## Drivers de decisión

- **Trazabilidad y auditabilidad** (principio rector del dominio).
- **Idempotencia** frente a la pasarela de pagos (RN-20, C-06): poder fijar el identificador *antes* de la transacción.
- **No filtración de información de negocio** (volumen, secuencia).
- **Rendimiento de índices** y costo de almacenamiento.
- Facilidad de integración/exportación futura.

## Opciones consideradas

1. **Entero autoincremental (bigint).** Compacto (8 B), índices eficientes y secuenciales. Pero revela volumen (`rental #4521`), es enumerable por terceros, requiere round-trip a la BD para conocer el id antes de insertar, y colisiona al unificar fuentes.
2. **UUIDv4 (aleatorio).** Global, no filtra volumen, generable en cliente. Pero su aleatoriedad **fragmenta el índice de la PK** (inserciones en posiciones dispersas del B-tree), penalizando escritura y localidad.
3. **UUIDv7 (ordenable por tiempo).** Las ventajas de v4 (global, no enumerable, generable antes de la transacción) **más** orden temporal, que mantiene las inserciones casi secuenciales y mitiga la fragmentación.

## Decisión

**UUIDv7 como PK de toda entidad de negocio.** Los identificadores de negocio legibles (`station.code`, `bicycle.code`/placa) se modelan como columnas `UNIQUE` separadas, para no acoplar la integridad referencial a un dato mutable o de presentación. Excepción: `BICYCLE_LOCATION` usa `bicycle_id` como PK (relación 1:1, ver [ADR-0003](0003-ubicacion-e-inventario-como-proyecciones-materializadas.md)).

## Consecuencias

**Positivas**
- El `id` de renta/pago se genera antes de abrir la transacción → sirve de base para la `idempotency_key` sin round-trip (habilita [ADR-0007](0007-modelo-de-pago-e-idempotencia.md)).
- No filtra volumen de negocio; estable y global.
- Orden temporal → fragmentación de índice acotada, cercana a la de un secuencial.

**Negativas / costos**
- 16 bytes vs 4–8: índices y joins ligeramente mayores. Irrelevante para el volumen de este dominio (decenas de estaciones, miles de bicicletas); se acepta conscientemente.
- **Dependencia de soporte:** si el motor elegido no genera UUIDv7 nativo, habrá que generarlo en la aplicación o vía función. Se confirma en el **ADR de stack**.

## Enlaces

- Aterriza en: [Modelo de datos §4](../modelo-de-datos.md). Habilita [ADR-0007](0007-modelo-de-pago-e-idempotencia.md).
