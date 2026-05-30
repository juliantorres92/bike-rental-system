# bike-rental-system
Sistema de renta de bicicletas — Especificaciones, arquitectura y stack tecnológico generados con asistencia de IA

## Documentación

- [Especificación funcional](docs/especificacion-funcional.md) — actores, casos de uso, reglas de negocio, máquinas de estado y decisiones de diseño abiertas.
- [Modelo de datos](docs/modelo-de-datos.md) — modelo lógico: entidades, diagrama ER, diccionario de datos, constraints e invariantes, y resolución de las tensiones de diseño.
- [Arquitectura técnica](docs/arquitectura.md) — estilo, diagramas C4 (contexto, contenedores, componentes) y cómo las decisiones se reflejan en la estructura.
- [Stack tecnológico](docs/stack.md) — lenguaje, framework, ORM y motor de BD con su justificación y trade-offs.
- [Decisiones de arquitectura (ADRs)](docs/adr/) — registro de las decisiones técnicas con su contexto, alternativas y consecuencias.
- [Proceso de construcción con IA](docs/proceso-con-ia.md) — cómo se usó la IA como herramienta profesional: método, verificación y criterio.
- [Relación con el dominio de seguros](docs/relacion-con-seguros.md) — por qué las decisiones de diseño de este caso transfieren al software de seguros.
- [Implementación de referencia (`CreateRental`)](src/README.md) — núcleo de dominio hexagonal en Python con tests y demo ejecutable, que prueba que el diseño es implementable.
