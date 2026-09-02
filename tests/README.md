# Backend tests (pytest)

```bash
.venv/bin/pip install pytest respx     # or: poetry install --with dev
.venv/bin/python -m pytest
```

Every request handler in `backend/routers/` has a matching `test_<resource>.py`
covering the happy path plus validation / 404 / 409 / conflict cases.

| File | Covers |
| --- | --- |
| `test_products.py` | products, EAN codes, image upload / from-URL, tags, unit conversions |
| `test_stock.py` | stock entries CRUD, filters, `/summary`, `/category-summary`, tags, stock IDs |
| `test_stock_id_modes.py` | manual / generated / webhook Stock-ID assignment, label auto-print gating |
| `test_vaults.py` · `test_units.py` · `test_categories.py` | CRUD + sub-resources (tags, conversions) |
| `test_tags.py` | the read-only tag index |
| `test_settings.py` | key/value settings, defaults, validation |
| `test_ean_lookup.py` | OpenFoodFacts lookup (HTTP stubbed with `respx`) |
| `test_label_printing.py` | `/api/settings/printing/*` — options, preview PNG, test-print, clear-queue |
| `test_label_rendering.py` | `label_printing.render_label_png` layout/geometry helpers (pure) |
| `test_data_transfer.py` | ZIP export + import preview/apply round-trip |
| `test_app.py` | OpenAPI schema, SPA fallback, end-to-end CRUD smoke |
| `test_migrations.py` | `alembic upgrade head` reproduces `Base.metadata` |

## How it works

`conftest.py`:

- builds a fresh SQLite file per test from `Base.metadata.create_all` and
  overrides the `get_db` dependency to point at it;
- **autouse `no_external_side_effects`** neutralises every outbound path —
  OpenFoodFacts, the Stock-ID webhook (`httpx.get` raises if hit unstubbed),
  and the label printer;
- exposes builder fixtures: `make_unit`, `make_category`, `make_vault`,
  `make_product`, `make_stock_entry`.

Tests stay hermetic: no network, no printer, no shared state between tests.
