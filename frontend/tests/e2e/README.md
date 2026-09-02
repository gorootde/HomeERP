# End-to-end tests (Playwright)

Browser tests that drive the real SvelteKit SPA against a real FastAPI backend.

## Running

```bash
cd frontend
npm install
npx playwright install chromium   # one-time: download the browser
npm run test:e2e                   # builds the SPA, then runs the suite
```

`npm run test:e2e` = `npm run build && playwright test`.

`playwright.config.js` starts **one** web server: the FastAPI backend
(`uvicorn backend.main:app` on `:8000`) which also serves the built SPA from
`frontend_dist/` — the same setup as production, so there is no SSR dev server
in the loop. The web-server command is
`node frontend/tests/e2e/reset-db.js && alembic upgrade head && uvicorn …`:
`reset-db.js` wipes and recreates `frontend/e2e-data/` so every run starts from
an empty SQLite database, then Alembic migrates the fresh file.

To run against a backend you started yourself:

```bash
DATABASE_URL='sqlite:///./frontend/e2e-data/e.db' python -m alembic upgrade head
DATABASE_URL='sqlite:///./frontend/e2e-data/e.db' python -m uvicorn backend.main:app --port 8000
# then, in frontend/:
PW_NO_SERVER=1 npx playwright test
```

## Layout

| File | Covers |
| --- | --- |
| `navigation.spec.js` | routing, sidebar links, `/` → `/dashboard` redirect |
| `dashboard.spec.js` | stat tiles, category cards, product table |
| `products.spec.js` | product CRUD, search, EAN management, tags |
| `stock.spec.js` | stock-entry CRUD, vault filter, stock-ID management |
| `vaults.spec.js` | vault CRUD + tags |
| `units.spec.js` | unit CRUD + conversions |
| `categories.spec.js` | category CRUD + minimum stock level |
| `stockid-settings.spec.js` | manual / generated / webhook Stock-ID modes |
| `printing-settings.spec.js` | label preview, test print, persisting printer settings |
| `data-transfer.spec.js` | export panel, import panel, ZIP download |
| `inventory.spec.js` | guided counting workflow (select → count → result) |
| `scanner.spec.js` | scanner page mount + start/stop (camera is faked) |
| `i18n.spec.js` | DE ⇄ EN language switch + persistence |

`helpers.js` exposes `makeApi()` — a small REST client used to arrange backend
state quickly — plus `uid()` for collision-free entity names and
`useLanguage(page, 'de'|'en')`.

## Notes

- Chromium runs with `--use-fake-device-for-media-stream`, so the barcode
  scanner starts but never decodes a real code; scanner/inventory specs assert
  UI state and workflow transitions, not decode results.
- Specs create uniquely-named entities (`uid()`) and tolerate pre-existing
  rows, so a shared/re-used database does not break them.
