.PHONY: run install

VENV ?= .venv/bin
BIN = $(if $(VENV),$(VENV)/,)

run:
	$(BIN)alembic upgrade head
	$(BIN)uvicorn backend.main:app --reload

install:
	python3 -m venv .venv
	$(VENV)/pip install fastapi "uvicorn[standard]" sqlalchemy "pydantic>=2.7" python-multipart alembic httpx
