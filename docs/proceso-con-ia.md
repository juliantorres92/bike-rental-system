# Proceso de Construcción con IA

> **Estado:** vivo (se actualiza con cada pieza) · **Tipo:** registro de método
> **Propósito:** documentar *cómo* se construyó este entregable usando IA como herramienta profesional — no como atajo. Es el complemento del "qué" (los documentos de diseño) con el "cómo se llegó a ellos".

---

## 1. Por qué este documento

El objetivo del ejercicio no es solo el resultado, sino **demostrar criterio usando IA**: levantar requerimientos, diseñar soluciones y tomar decisiones técnicas justificadas, con la IA como multiplicador. Este log hace visible ese proceso: el método seguido, cómo se usó la IA en cada etapa, qué se verificó y dónde el criterio humano dirigió o corrigió a la IA.

**Principio rector del proceso:** *cada decisión debe ser defendible*. La IA acelera la generación y la exploración de alternativas; el humano fija la intención, elige entre trade-offs y valida los hechos. La IA no decide por nadie ni se acepta sin verificar.

---

## 2. Método

Se siguió una secuencia deliberada, de lo abstracto a lo concreto, donde **cada pieza es la raíz de la siguiente** y se entrega como un PR independiente (GitHub Flow):

```
Entrevista de intención   →  ¿qué se quiere de verdad y con qué restricciones?
        ↓
1. Especificación funcional  (PR #2)  — el "qué" del sistema
        ↓
2. Modelo de datos           (PR #3)  — cómo se estructuran los datos; resuelve tensiones de la spec
        ↓
3. ADRs                      (PR #4)  — decisiones con trade-offs (backlog que dejó el modelo)
        ↓
4. Arquitectura + C4         (PR #5)  — la forma; cómo los ADRs se reflejan en módulos
        ↓
5. Stack tecnológico         (PR #6)  — la tecnología; cierra dependencias de los ADRs
        ↓
6. Este log de proceso       — el "cómo" transversal
```

Cada flecha es una relación de trazabilidad real: el modelo cita las reglas de la spec, los ADRs citan las tensiones del modelo, la arquitectura mapea los ADRs a módulos, el stack cierra las dependencias que los ADRs dejaron abiertas.

---

## 3. La entrevista de intención (antes de escribir nada)

Antes de la primera línea de diseño, se hizo una **entrevista one-question-at-a-time** para separar lo que se *pide* de lo que se *quiere*. Cada pregunta llevaba una hipótesis con un nivel de confianza, y se iteró hasta poder predecir las respuestas.

Lo que la entrevista cambió respecto a la lectura inicial ingenua:

| Suposición inicial | Lo que reveló la entrevista |
|---|---|
| "Construir un sistema de renta de bicicletas" | El producto real es **demostrar criterio de ingeniería**; las bicicletas son el lienzo. |
| "Entregar una app funcionando" | El centro es **diseño y documentación**; el código es opcional (la cereza, no el pastel). |
| "Stack primero" | Para un rol de arquitectura en seguros, pesa más el **modelado de negocio** que el stack. |
| Plazo abierto | **Un día** de trabajo → priorizar lo de mayor señal, no la exhaustividad. |

Sin esta etapa, el esfuerzo habría ido a un CRUD completo (la señal *menos* valiosa) en vez de a las decisiones de diseño (la señal que se evalúa). **Este es el mayor retorno de usar IA con método: evitar construir lo correcto del problema equivocado.**

---

## 4. Cómo se usó la IA en cada etapa

| Etapa | Uso de la IA | Criterio/decisión humana |
|---|---|---|
| Intención | Entrevista con hipótesis + confianza; restate verificable | Confirmar/corregir cada hipótesis; fijar alcance y plazo |
| Spec funcional | Generar borrador de actores, casos de uso, reglas, casos borde; proponer el caso central | Validar completitud; aprobar el recorte MUST/SHOULD/COULD |
| Modelo de datos | Diseñar tablas, resolver 4 tensiones con trade-offs, proponer UUIDv7 | Aprobar las recomendaciones; señalar el error de render del diagrama |
| ADRs | Redactar 8 decisiones en formato MADR con alternativas y consecuencias | Revisar que cada decisión sea defendible |
| Arquitectura | Proponer estilo (monolito modular hexagonal), diagramas C4, mapa ADR→módulo | Validar el estilo frente a los drivers |
| Stack | Justificar elecciones; **verificar hechos de versión** contra documentación oficial | Elegir lenguaje (Python) y delegar el motor con criterio |

Se usaron **subagentes de planificación** para estresar la completitud del dominio (¿faltan casos de uso? ¿qué tensiones esconde el modelo?) antes de redactar — divergir para no dejar huecos, luego converger.

---

## 5. Verificación: la IA no se cree, se comprueba

Cada afirmación con riesgo de estar mal se verificó antes de quedar escrita:

- **Diagramas Mermaid:** se renderizaron localmente con `mermaid-cli` antes de confiar en ellos. En el modelo de datos, el primer diagrama ER usaba un marcador de llave inválido (`PK_FK`); **el usuario detectó que no renderizaba**, se corrigió a la sintaxis válida (`PK, FK`) y se validó el render (SVG generado, 9 entidades presentes) antes de commitear.
- **Hechos de versión del stack:** la afirmación "UUIDv7 nativo en PostgreSQL" se verificó contra la documentación oficial — es nativo (`uuidv7()`) **desde PostgreSQL 18**; en versiones anteriores se genera en la capa de aplicación. Igual con los índices únicos parciales (soportados ≥9.6). Esto evitó escribir una afirmación desactualizada en el entregable.
- **Trazabilidad:** se comprobó mecánicamente que cada regla de negocio, caso borde y entidad aparece donde debe, y que no hay enlaces internos rotos entre documentos.

---

## 6. La IA como herramienta profesional, no como atajo

Qué distingue este uso de "pedirle a la IA que lo haga":

1. **Intención antes que generación.** La entrevista evitó optimizar el artefacto equivocado.
2. **Trade-offs explícitos.** Cada decisión documenta alternativas y por qué se descartaron — la IA no "elige por defecto", argumenta.
3. **Verificación de hechos.** Render de diagramas y versiones de software comprobados, no asumidos.
4. **Trazabilidad de punta a punta.** Spec → modelo → ADR → arquitectura → stack, enlazado y verificable.
5. **Disciplina de proceso.** GitHub Flow, Conventional Commits, PRs atómicos con sección "Fuera de alcance" — el *cómo* se trabaja es parte del entregable.
6. **El humano dirige.** Fijó intención y plazo, eligió el lenguaje, controló los merges y **corrigió a la IA** cuando hizo falta (el diagrama roto).

---

## 7. Honestidad sobre límites

- El alcance se acotó conscientemente a un día: se priorizó diseño defendible sobre exhaustividad. Las políticas de negocio no estructurales (C-02, C-05, C-07, C-09) quedaron con recomendación tentativa, no resueltas.
- No hay app completa funcionando; la implementación (ver §9) es el núcleo de dominio de un solo caso de uso para probar que el diseño es implementable, no un producto.
- Este documento se actualiza si se añaden piezas posteriores.

---

## 8. Trazabilidad del proceso (PRs)

| Pieza | Rama | PR | Documento |
|---|---|---|---|
| Spec funcional | `docs/functional-spec` | #2 | [especificacion-funcional.md](especificacion-funcional.md) |
| Modelo de datos | `docs/data-model` | #3 | [modelo-de-datos.md](modelo-de-datos.md) |
| ADRs | `docs/adr` | #4 | [adr/](adr/) |
| Arquitectura | `docs/architecture` | #5 | [arquitectura.md](arquitectura.md) |
| Stack | `docs/stack` | #6 | [stack.md](stack.md) |
| Log de proceso | `docs/ai-process-log` | #7 | este documento |
| Guiño a seguros | `docs/insurance-domain` | #8 | [relacion-con-seguros.md](relacion-con-seguros.md) |
| Implementación `CreateRental` | `feature/create-rental` | #9 | [src/](../src/README.md) |

---

## 9. Implementación con equipo multi-agente (criterio #1 en acción)

La implementación del caso de uso (UC-01) se construyó simulando un **equipo agile orquestado con IA**, lo que es en sí mismo una demostración de cómo se usa la IA con criterio:

1. **PO (humano + IA):** se derivó el [backlog](backlog.md) (HU-01..04 con criterios Gherkin) de la spec; el humano lo aprobó antes de codear.
2. **Arquitecto (agente):** definió un contrato (estructura, puertos, caso de uso, casos de test) sin escribir código.
3. **Dev (agente, TDD):** implementó el dominio hexagonal + adaptadores en memoria + tests; dejó la suite en verde y **marcó honestamente** un hueco del contrato (faltaba `StationRepository`).
4. **3 revisores en paralelo (agentes):** revisaron correctitud/atomicidad, pureza hexagonal y cobertura. Cazaron el hueco como hallazgo **mayor** y otros menores.
5. **Dev de correcciones (agente):** resolvió los hallazgos bloqueantes/mayores y re-verificó.
6. **Pulido (humano + IA):** se cerraron los *minor* restantes (tests RN-20 e inactiva, código muerto, tipado, guarda de máquina de estados) y se verificó la suite localmente.

**Lección del proceso:** el contrato inicial del arquitecto tenía un defecto real (decremento de inventario sin puerto) que **el propio ciclo de revisión adversarial corrigió** — exactamente lo que aporta un equipo, no un único generador. La verificación (tests en verde corridos a mano, dominio sin imports de framework) cierra el lazo: la IA propone, el proceso comprueba.
