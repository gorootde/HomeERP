# ── Stage 1: Build SvelteKit frontend ─────────────────────────────────────────
FROM node:22-slim AS frontend-builder

WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build
# Output written to /build/frontend_dist/ (adapter-static: "../frontend_dist")

# ── Stage 2: Python application ───────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends make \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir poetry

COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --only main --no-root

COPY Makefile    ./
COPY backend/    backend/
COPY migrations/ migrations/
COPY alembic.ini ./

# Copy built frontend assets from Stage 1
COPY --from=frontend-builder /build/frontend_dist/ frontend_dist/

# Create mount-point directories
RUN mkdir -p /data /app/uploads

# ── Volumes ───────────────────────────────────────────────────────────────────
# /data        → SQLite database file (homeerp.db)
# /app/uploads → user-uploaded product images
VOLUME ["/data", "/app/uploads"]

# ── Configuration ─────────────────────────────────────────────────────────────
ENV DATABASE_URL=sqlite:////data/homeerp.db
ENV UPLOADS_DIR=/app/uploads

EXPOSE 8000

# Run migrations, then start the server
CMD ["make", "run", "VENV=", "HOST=0.0.0.0"]
