# Guía de contribución

Esta guía define la estrategia de versionado del proyecto **bike-rental-system**.
El objetivo es mantener una historia de Git limpia, revisable y reversible.

> **Contexto bilingüe:** el dominio se documenta en español; el código, las ramas y
> los mensajes de commit se escriben en inglés.

---

## Modelo de ramas — GitHub Flow

Usamos **GitHub Flow**: un único tronco (`main`) siempre desplegable y ramas de trabajo
cortas que vuelven a `main` mediante Pull Request.

```
main ──●──●──●──●──●──●──●──●──   (siempre desplegable)
         ╲   ╱ ╲     ╱
          ●─╱   ●───╱            ← ramas de feature/fix (cortas, 1–3 días)
```

Reglas:

- `main` **siempre** está en estado desplegable. Nada se rompe en `main`.
- Toda mejora, fix o cambio nace de una rama corta creada **desde `main`**.
- Las ramas viven poco (objetivo: 1–3 días). Las ramas largas divergen y generan conflictos.
- El cambio vuelve a `main` **solo vía Pull Request** revisado.
- Tras el merge, **se borra la rama**.
- El despliegue sale de `main` (continuo o por tag, según el entorno).
- Para trabajo incompleto que no puede esperar, preferir **feature flags** antes que ramas largas.

### Convención de nombres de ramas

`<tipo>/<descripción-corta>` en kebab-case y en inglés:

| Prefijo      | Uso                                         | Ejemplo                      |
|--------------|---------------------------------------------|------------------------------|
| `feature/`   | Nueva funcionalidad                         | `feature/bike-reservation`   |
| `fix/`       | Corrección de bug                           | `fix/double-booking`         |
| `refactor/`  | Cambio interno sin alterar comportamiento   | `refactor/pricing-service`   |
| `test/`      | Añadir o ajustar pruebas                    | `test/rental-flow`           |
| `docs/`      | Solo documentación                          | `docs/git-workflow`          |
| `chore/`     | Tooling, dependencias, configuración        | `chore/setup-eslint`         |

---

## Mensajes de commit — Conventional Commits

Formato:

```
<type>(<scope>): <descripción en imperativo, minúscula, sin punto final>

<cuerpo opcional: explica el PORQUÉ, no el qué>

<footer opcional: BREAKING CHANGE, Co-Authored-By, refs>
```

**Tipos permitidos:**

| Tipo       | Cuándo                                            |
|------------|---------------------------------------------------|
| `feat`     | Nueva funcionalidad                               |
| `fix`      | Corrección de bug                                 |
| `refactor` | Cambio que no añade feature ni corrige bug        |
| `test`     | Añadir o actualizar pruebas                       |
| `docs`     | Solo documentación                                |
| `chore`    | Tooling, dependencias, configuración              |
| `perf`     | Mejora de rendimiento                             |
| `ci`       | Cambios en pipelines de integración/despliegue    |

El `scope` es opcional e indica el área afectada (`feat(rental):`, `fix(pricing):`).

### Ejemplos

```text
# Bien: explica la intención
feat(rental): add hourly pricing for bike reservations

Calcula la tarifa en base a la duración de la renta y el tipo de bici.
El cálculo vive en el servicio de pricing para reutilizarlo desde
el endpoint y los jobs de facturación.

# Bien: fix conciso con contexto
fix(booking): prevent double-booking of the same bike

Añade un lock optimista al crear la reserva para evitar dos rentas
simultáneas del mismo recurso.

# Mal: no aporta información
update code
fix stuff
wip
```

### Cambios incompatibles

Marcar con `!` y/o footer `BREAKING CHANGE:`:

```text
feat(api)!: change rental response shape to include station data

BREAKING CHANGE: el campo `station` ahora es un objeto en lugar de un id.
```

### Plantilla de commit

El repo incluye [`.gitmessage`](.gitmessage). Actívala una vez por clon:

```bash
git config commit.template .gitmessage
```

A partir de ahí, `git commit` (sin `-m`) abre el editor con la guía precargada.

---

## Commits atómicos y tamaño del cambio

- **Un commit = una cosa lógica.** Si necesitas "y" para describirlo, probablemente son dos commits.
- **No mezcles concerns:** un refactor y una feature van en commits (e idealmente PRs) separados.
  No combines cambios de formato con cambios de comportamiento.
- **Tamaño objetivo:** ~100 líneas por PR. Hasta ~300 es aceptable para un cambio lógico.
  Más de ~1000 → divídelo.

```text
# Bien: cada commit se sostiene solo
feat(rental): add reservation endpoint with validation
test(rental): add reservation unit and integration tests

# Mal: todo mezclado
feat: add reservation, fix sidebar, bump deps, reformat utils
```

---

## Proceso de Pull Request

```
1. git checkout main && git pull          # parte de main actualizado
2. git checkout -b feature/<desc>          # rama corta
3. ...commits atómicos...                  # implementa en incrementos
4. git push -u origin feature/<desc>       # publica la rama
5. Abre el PR                              # se autocarga PULL_REQUEST_TEMPLATE.md
6. Revisión + checks verdes
7. Squash & merge a main
8. git branch -d feature/<desc>            # borra la rama local
```

### Checklist pre-commit

> ⏳ **Pendiente de stack.** El proyecto aún no tiene runtime elegido. Cuando exista,
> estos pasos se automatizan (ver "Siguiente paso"). Por ahora son verificaciones manuales:

- [ ] El commit hace una sola cosa lógica.
- [ ] El mensaje sigue Conventional Commits y explica el porqué.
- [ ] Sin secretos en el diff (`git diff --staged | grep -iE "password|secret|api_key|token"`).
- [ ] Sin cambios de formato mezclados con cambios de comportamiento.
- [ ] Tests y lint en verde *(cuando existan)*.

---

## Higiene del repositorio

- **No se commitea:** `.env` / `.env.*`, `node_modules/`, salidas de build (`dist/`, `.next/`),
  config de IDE no compartida, claves (`*.pem`).
- El [`.gitignore`](.gitignore) cubre las exclusiones estándar; amplíalo al elegir el stack.
- Nunca `--force` sobre ramas compartidas (incluida `main`).

---

## Siguiente paso (cuando exista `package.json`)

Automatizar la calidad con git hooks para que la disciplina no dependa de la memoria:

- **husky** — gestiona los hooks de Git.
- **commitlint** — valida que los mensajes cumplan Conventional Commits.
- **lint-staged** — corre linter/formatter solo sobre los archivos en stage.

Esto se añadirá en una rama `chore/setup-git-hooks` una vez definido el runtime.
