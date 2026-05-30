# ADR-0001 — Registrar decisiones de arquitectura con ADRs

- **Estado:** aceptado
- **Fecha:** 2026-05-30
- **Decisores:** equipo de diseño (rol arquitectura)

## Contexto y problema

El proyecto toma decisiones técnicas con consecuencias de largo plazo (estrategia de llaves, consistencia, concurrencia, modelo de pago). En un dominio sensible como el asegurador, *por qué* se decidió algo importa tanto como *qué* se decidió: las decisiones deben ser auditables, defendibles y reversibles de forma trazable. Sin un registro explícito, el razonamiento se pierde y las decisiones se cuestionan o reinventan sin contexto.

## Drivers de decisión

- Trazabilidad y auditabilidad del razonamiento de diseño.
- Onboarding: que una persona nueva entienda por qué el sistema es como es.
- Reversibilidad ordenada: poder cambiar una decisión sabiendo qué reemplaza.
- Bajo costo de mantenimiento (no debe competir con escribir el sistema).

## Opciones consideradas

1. **ADRs en el repositorio (MADR ligero).**
2. **Documentación en una wiki/Confluence externa.**
3. **Sin registro formal** (decisiones implícitas en el código y en commits).

## Decisión

Se adoptan **ADRs versionados en el repositorio**, en `docs/adr/`, con formato MADR ligero. Cada ADR es inmutable; un cambio de decisión se registra con un ADR nuevo que supersede al anterior. Cada ADR enlaza a las reglas/casos de la spec y a las secciones del modelo de datos que lo originan.

## Consecuencias

**Positivas**
- El razonamiento vive junto al código, versionado con él y revisado en PRs.
- Historial de decisiones navegable y enlazado a su origen funcional.
- Coherente con el principio de trazabilidad del dominio.

**Negativas / costos**
- Disciplina de mantenerlos al día; un ADR olvidado engaña más que la ausencia.
- Riesgo de sobre-documentar decisiones triviales → solo se registran decisiones con trade-offs reales.

## Enlaces

- [Índice de ADRs](README.md) · [Especificación funcional](../especificacion-funcional.md) · [Modelo de datos](../modelo-de-datos.md)
