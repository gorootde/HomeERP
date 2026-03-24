.PHONY: run install

VENV ?= .venv/bin

run:
	$(VENV)/alembic upgrade head
	$(VENV)/uvicorn backend.main:app --reload

install:
	python3 -m venv .venv
	$(VENV)/pip install fastapi "uvicorn[standard]" sqlalchemy "pydantic>=2.7" python-multipart alembic httpx
