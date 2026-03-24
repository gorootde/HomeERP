# ── Stage 1: build frontend vendor files ─────────────────────────────────────
FROM node:20-slim AS frontend-builder
WORKDIR /frontend
COPY frontend/package.json frontend/vendor-copy.js ./
RUN npm install
COPY frontend/ ./
RUN npm run vendor

# ── Stage 2: Python application ───────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends make \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependency manager
RUN pip install --no-cache-dir poetry

# Install dependencies (no virtualenv inside the container)
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --only main

# Copy application source
COPY backend/    backend/
COPY migrations/ migrations/
COPY alembic.ini ./
COPY frontend/   frontend/

# Overwrite vendor files with freshly built ones from Stage 1
COPY --from=frontend-builder /frontend/vendor/ frontend/vendor/

# Create mount-point directories
RUN mkdir -p /data /app/uploads

# ── Volumes ───────────────────────────────────────────────────────────────────
# /data      → SQLite database file (homeerp.db)
# /app/uploads → user-uploaded product images
VOLUME ["/data", "/app/uploads"]

# ── Configuration ─────────────────────────────────────────────────────────────
ENV DATABASE_URL=sqlite:////data/homeerp.db
ENV UPLOADS_DIR=/app/uploads

EXPOSE 8000

# Run migrations, then start the server
CMD ["make", "run", "VENV="]
