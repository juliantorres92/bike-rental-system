# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Bike rental system (sistema de renta de bicicletas). The project is in its initial stage — no application code, build system, or tests exist yet. The README is in Spanish; assume bilingual context (Spanish domain, English code).

## Status

Greenfield project. Tech stack and architecture have not been chosen yet. Update this file as foundational decisions are made.

## Git Workflow

The versioning strategy is defined and is the source of truth in [CONTRIBUTING.md](CONTRIBUTING.md): **GitHub Flow** (deployable `main`, short-lived branches, PR-based merge) with **Conventional Commits**. Follow it for every change — branch from `main`, keep commits atomic, open a PR using the template in `.github/`. Commit/branch tooling (husky, commitlint, lint-staged) is deferred until a `package.json` exists.