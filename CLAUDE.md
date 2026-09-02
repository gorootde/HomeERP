# HomeERP — working conventions

Project overview, feature list, stack, setup and API endpoint groups are in
[README.md](README.md); domain concepts (stock entries vs. stock IDs, categories, units,
movement history) are in its *Concepts* section. This file only covers conventions and
gotchas that aren't obvious from the code.

## Golden rules

- **Test-driven development** is the default workflow: write or extend the pytest coverage
  in `tests/` for the new behaviour first, watch it fail, then implement. Every router has a
  matching `tests/test_<resource>.py`.
- **Every feature is a public, documented REST endpoint.** Add functionality to a `routers/`
  module with a typed `response_model`, a tag, and a docstring so it lands in the OpenAPI
  schema / Swagger UI at `/docs`. The frontend consumes only that public API (through
  `src/lib/api.js`) — no private/undocumented routes.
- Use **Alembic** for every schema change. `tests/test_migrations.py` asserts the migration
  chain reproduces `Base.metadata`, so a model change without a migration fails.
- Keep tests **hermetic** — no real network or printer calls. `tests/conftest.py`
  monkeypatches every outbound code path; add new ones there when you introduce them.
- Datetimes are stored **naive in UTC** (SQLite drops tzinfo). Use `models._utcnow` and
  re-attach `timezone.utc` when serializing (see `schemas.StockMovementRead`).
- SQLite runs with **foreign-key enforcement off**. Don't rely on DB-level `ON DELETE`;
  make cascade/null behaviour explicit in the ORM relationships.

## Backend patterns

- **Routers:** one module per resource in `backend/routers/`, each defining
  `router = APIRouter()`; `main.py` mounts it at `/api/<name>` with a matching tag. DB
  access is always `db: Session = Depends(get_db)`.
- **Endpoints:** set `response_model=`; use explicit status codes (`201` create, `204`
  delete); raise `HTTPException` for errors; look rows up with `db.get(Model, id)`; do
  partial updates via `data.model_dump(exclude_unset=True)` + `setattr`; `db.commit()` then
  `db.refresh()` before returning.
- **Schemas** (`backend/schemas.py`): `XxxBase` / `XxxCreate` / `XxxUpdate` / `XxxRead`
  split. Read models carry `model_config = ConfigDict(from_attributes=True)`. Validate with
  `Field(...)`.
- **Settings** are key/value rows in the `settings` table. Well-known keys and their
  `DEFAULTS` live in `routers/app_settings.py`; read them with the `_get_setting` /
  `_float_setting` helpers in `routers/stock.py`.
- **Audit log** (`stock_movements`): append-only. Always go through `_record_movement`;
  `product_id` / `vault_id` are denormalised so stats survive entry deletion; a JSON
  `entry_snapshot` column enables undo; undo appends a compensating movement, never mutates
  existing rows.
- **External calls** use `httpx` and must fail soft — return an empty result, never 404
  (see `routers/ean_lookup.py`). Deferred work goes through FastAPI `BackgroundTasks`.
- **Generic table import/export** (`routers/data_transfer.py`) is driven by
  `Base.registry.mappers` / `Base.metadata.sorted_tables`, so new models are picked up
  automatically — no per-model wiring.
- **Alembic:** `migrations/env.py` reads `DATABASE_URL` and targets `backend.models.Base`.
  `render_as_batch=True` is set and required for SQLite `ALTER TABLE` — keep it.

## Frontend patterns

- SvelteKit 2 + **Svelte 5 runes only** (`$state`, `$derived`, `$props`); component
  callbacks are props (`onclose`, `onconfirm`, `onadd`), not `createEventDispatcher`.
- Routing is file-based in `src/routes/` (`+page.svelte`, `+layout.svelte`).
- **All API access goes through `src/lib/api.js`** — a thin `fetch` wrapper that sets JSON
  headers, throws `Error(text)` on non-2xx, returns `null` on 204. Add one named export per
  endpoint; components never call `fetch` directly.
- Cross-cutting state via Svelte stores: `src/lib/toast.js` (`showToast(msg, type)`) and
  `src/lib/i18n.js` (`t(key)`, `locale`). i18n dictionaries are inline DE + EN; **German is
  the base language** and every user-facing string goes through `t(...)`.
- Styling is Tailwind v4 utility classes inline (`@theme` tokens in `src/app.css`); icons
  from `lucide-svelte`; formatting helpers (`fmtQty`, `fmtDate`, …) in `src/lib/utils.js`.
- **Page pattern:** `onMount` loads data, a `loading` flag guards render, mutations call a
  local `reload()` and `showToast` on success/error.
- Build output goes to `frontend_dist/`, which the backend serves as static files; `npm run
  dev` proxies `/api` and `/uploads` to `:8000`.

## Tests

- **Backend:** `pytest` (`testpaths = ["tests"]`). `conftest.py` builds a throw-away SQLite
  file per test from `Base.metadata.create_all` (not Alembic), overrides `get_db`, and
  exposes builder fixtures (`make_unit`, `make_product`, `make_vault`, `make_stock_entry`,
  `make_category`). Stub `httpx` with `respx`. `test_migrations.py` is the one place that
  runs the real Alembic chain.
- **E2E:** Playwright in `frontend/tests/e2e/` (`frontend/playwright.config.js`) boots a
  real backend against a scratch DB plus the Vite dev server, chromium with a fake camera.
  Run `npm run test:e2e` from `frontend/`.

## CI

`.github/workflows/docker-publish.yml` builds and pushes the image to GHCR on every push to
`main`. There is no automated test workflow — run `pytest` (and the E2E suite) locally
before pushing.
