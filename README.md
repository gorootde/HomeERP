# HomeERP

A self-hosted home inventory and stock management system built with FastAPI and vanilla JavaScript.

I was deeply disappointed by the attitude of maintainers in some existing open-source inventory management solutions who were unwilling to accept contributions or changes, so I created this project as a more flexible and community-driven alternative.

---

## Features

- 📦 **Products** — Name, vendor, size, unit, category, photo, and multiple EAN codes per product
- 🏪 **Stock** — Multi-location tracking, quantity management, best-before dates, comments, and stock IDs
- 📷 **Barcode scanning** — Camera-based scanner for product lookup, stock operations, and quick product creation
- 🌐 **OpenFoodFacts** — Automatic product data and image retrieval via EAN lookup
- 📋 **Inventory** — Guided counting workflow with scan support and a diff view to spot discrepancies
- 📊 **Dashboard** — Stock overview, category breakdown, and low-stock / critical-stock alerts
- ⚖️ **Units** — Configurable units of measure with conversion factors
- 🏷️ **Stock IDs** — Manual, auto-incremented, or webhook-assigned stock IDs
- 🔖 **Tags** — Free-form tagging on products and storage locations
- 🌍 **i18n** — English and German UI, switchable at runtime
- 🔌 **REST API** — Full API coverage; interactive docs at `/docs`

---

## Getting Started

### Option A — Makefile (local dev)

**Prerequisites:** Python 3.11+, Node.js 20+

```bash
# One-time setup: creates .venv and installs Python dependencies
make install

# Build frontend vendor files (Lucide icons, html5-qrcode)
cd frontend && npm install && npm run vendor && cd ..

# Run migrations and start the dev server (with --reload)
make run
```

Open <http://localhost:8000>.

### Option B — Docker

```bash
docker build -t homeerp .

docker run -p 8000:8000 \
  -v homeerp-data:/data \
  -v homeerp-uploads:/app/uploads \
  homeerp
```

Open <http://localhost:8000>.

**Volumes:**

| Mount          | Contents                       |
| -------------- | ------------------------------ |
| `/data`        | SQLite database (`homeerp.db`) |
| `/app/uploads` | User-uploaded product images   |

**Environment variables:**

| Variable       | Default                      | Description              |
| -------------- | ---------------------------- | ------------------------ |
| `DATABASE_URL` | `sqlite:////data/homeerp.db` | SQLAlchemy database URL  |
| `UPLOADS_DIR`  | `/app/uploads`               | Path for uploaded images |

---

## Concepts

HomeERP manages household inventory - cellar, kitchen, pantry, or any other storage location in your home.

### Products and EAN codes

A **product** is a generic item description, e.g. _Coca-Cola 0.33 l can_. Products are created by scanning or entering their EAN barcode. If the code is known to the OpenFoodFacts database, HomeERP automatically populates the name, manufacturer, image, and other details.

### Stock entries and Stock IDs

A **stock entry** is a concrete instance of a product — e.g. _the 0.33 l Cola can with best-before date 2027-03-01_. Because an EAN code carries no expiry information, each entry (or multi-pack) gets an additional **Stock ID**. Only through this ID can you unambiguously identify "the water with best-before date XYZ".

Stock IDs can be assigned in several ways:

- **Manual** — write the ID directly on the item, e.g. with a marker pen
- **Auto-increment** — a sequential number, optionally with a freely chosen prefix (e.g. `INV<ID>`)
- **Webhook** — HomeERP calls an external endpoint that supplies the ID and can, for example, trigger a label printer directly, so a new label is printed immediately after a stock entry is created

### Categories and minimum stock levels

Products are assigned to **categories**. Each category can have a **minimum stock level**. If the actual stock falls below that threshold, HomeERP shows an alert on the dashboard.

### Units of measure and conversions

Units and conversion factors can be defined **globally** (e.g. litres → millilitres) or **per product** (e.g. 1 pack = 6 bottles), so stock quantities are correctly aggregated and compared regardless of packaging unit.

---

## Architecture

```
HomeERP/
├── backend/          # FastAPI application
│   ├── main.py       # Entry point, static file mounts
│   ├── database.py   # SQLAlchemy engine + session
│   ├── models.py     # ORM models
│   ├── schemas.py    # Pydantic schemas
│   └── routers/      # API route handlers
├── frontend/         # Vanilla JS SPA (no build step)
│   ├── index.html
│   ├── css/
│   ├── js/           # ES modules, hash-based routing
│   └── vendor/       # Bundled third-party libs
├── migrations/       # Alembic migration scripts
├── Dockerfile
├── Makefile
└── pyproject.toml
```

**Stack:** FastAPI · SQLAlchemy 2 · Alembic · SQLite · Vanilla JS · Lucide Icons

The backend serves the frontend as static files and acts as the API. No separate frontend server or build pipeline is required.

---

## API

Interactive docs are available at `/docs` (Swagger UI) and `/redoc` once the server is running.

Key endpoint groups:

```
/api/products      Products and EAN codes
/api/stock         Stock entries and summaries
/api/vaults        Storage locations
/api/units         Units of measure and conversions
/api/categories    Product categories
/api/tags          Tags
/api/settings      Application settings
/api/ean-info      OpenFoodFacts EAN lookup
```

---

## Contributing

1. Open an issue to discuss your idea before starting work
2. Fork the repository and create a feature branch
3. Submit a pull request — small, focused PRs are easier to review

By contributing you agree to the [Contributor License Agreement](CLA.md). It grants the maintainer the right to change the license in the future — for example to move to a more permissive license — while keeping the project open source.

---

## License

[AGPL-3.0](LICENSE) — see the license file for details.

## Author

[gorootde](https://github.com/gorootde)
