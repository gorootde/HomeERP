---
name: run-project
description: How to run HomeERP locally for testing/debugging, and how to run its test suites (backend pytest, frontend/e2e Playwright). Use whenever asked to start, run, or test this project.
---

# Running HomeERP locally

Always use the **Makefile** — don't call `uvicorn`/`alembic`/`npm` directly.

## First-time setup

```bash
make install          # creates .venv, installs backend deps
cd frontend && npm install && cd ..
```

## Start for local dev/debugging

```bash
make run              # runs alembic migrations, starts backend (uvicorn --reload) on :8000
make dev-frontend      # in a second terminal: SvelteKit dev server with hot reload, proxies /api and /uploads to :8000
```

Open `http://localhost:5173` (dev-frontend) for hot-reloading UI work, or `http://localhost:8000` to hit the backend directly / use the built frontend (`make build-frontend` first).

## Tests

There are two suites, no more:

- **Backend (pytest)** — hermetic, no Makefile target, run directly:
  ```bash
  .venv/bin/pytest
  ```
- **Frontend / E2E (Playwright)** — this is the only frontend test suite (there is no separate unit-test runner); it builds the frontend and boots a real backend against a scratch DB:
  ```bash
  make test-e2e          # == cd frontend && npm run test:e2e
  ```

## Linting

```bash
poetry run ruff check .    # backend + tests
cd frontend && npm run lint  # ESLint
```

Run lint and both test suites before pushing — CI (`.github/workflows/docker-publish.yml`)
now runs all four as required checks on every push/PR, and only builds/publishes the Docker
image after they pass.
