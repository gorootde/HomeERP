.PHONY: run install build-frontend dev-frontend

VENV ?= .venv/bin
BIN = $(if $(VENV),$(VENV)/,)
HOST ?= 127.0.0.1

run:
	$(BIN)alembic upgrade head
	$(BIN)uvicorn backend.main:app --reload --host $(HOST)

install:
	python3 -m venv .venv
	$(VENV)/pip install fastapi "uvicorn[standard]" sqlalchemy "pydantic>=2.7" python-multipart alembic httpx

build-frontend:
	cd frontendv2 && npm run build

dev-frontend:
	cd frontendv2 && npm run dev
