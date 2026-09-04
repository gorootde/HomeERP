"""Shared fixtures for the FastAPI test suite.

Every test runs against a throw-away SQLite file created from
``Base.metadata`` (no Alembic needed for the schema itself – the migrations get
their own dedicated test in ``test_migrations.py``). Outbound network calls
(OpenFoodFacts, the Stock-ID webhook) and the label printer are stubbed out by
the autouse ``no_external_side_effects`` fixture so the suite is hermetic.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import backend.models as models  # noqa: F401 – registers every ORM model on Base
from backend.database import Base, get_db
from backend.main import app


@pytest.fixture()
def db_path(tmp_path):
    return tmp_path / "homeerp_test.db"


@pytest.fixture()
def engine(db_path):
    eng = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(eng)
    try:
        yield eng
    finally:
        Base.metadata.drop_all(eng)
        eng.dispose()


@pytest.fixture()
def SessionLocal(engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture()
def db(SessionLocal):
    """A raw session for arranging state / asserting directly on the DB."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(SessionLocal):
    def _override_get_db():
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ── Hermetic-ness guards ────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def no_external_side_effects(monkeypatch):
    """Neutralise every code path that would touch the network or a printer."""

    async def _off_nothing(_barcode):  # OpenFoodFacts lookup → "not found"
        return None

    monkeypatch.setattr(
        "backend.routers.ean_lookup._query_openfoodfacts", _off_nothing
    )

    # Stock-entry auto-print: keep it a no-op unless a test opts in.
    monkeypatch.setattr(
        "backend.routers.stock._render_and_print", lambda *a, **k: None
    )

    # Stock-ID "extern" webhook: fail loudly if a test forgets to stub it.
    def _no_webhook(*_a, **_k):
        raise AssertionError(
            "outbound httpx.get called – stub the webhook in the test"
        )

    monkeypatch.setattr("backend.services.stock_id.httpx.get", _no_webhook)

    # Label-printing settings endpoints.
    monkeypatch.setattr(
        "backend.routers.label_printing.print_label", lambda *a, **k: None
    )
    monkeypatch.setattr(
        "backend.routers.label_printing.clear_print_queue",
        lambda *a, **k: "Purge-Jobs",
    )


# ── Convenience builders ───────────────────────────────────────────────────

@pytest.fixture()
def make_unit(client):
    def _make(name="Litre", abbreviation="l"):
        resp = client.post(
            "/api/units", json={"name": name, "abbreviation": abbreviation}
        )
        assert resp.status_code == 201, resp.text
        return resp.json()

    return _make


@pytest.fixture()
def make_category(client):
    def _make(name="Beverages", min_stock_quantity=None, min_stock_unit_id=None):
        body = {"name": name}
        if min_stock_quantity is not None:
            body["min_stock_quantity"] = min_stock_quantity
        if min_stock_unit_id is not None:
            body["min_stock_unit_id"] = min_stock_unit_id
        resp = client.post("/api/categories", json=body)
        assert resp.status_code == 201, resp.text
        return resp.json()

    return _make


@pytest.fixture()
def make_vault(client):
    def _make(description="Cellar"):
        resp = client.post("/api/vaults", json={"description": description})
        assert resp.status_code == 201, resp.text
        return resp.json()

    return _make


@pytest.fixture()
def make_product(client):
    def _make(name="Cola 0.33", vendor="Coca-Cola", ean_codes=None, **extra):
        body = {"name": name, "vendor": vendor, "ean_codes": ean_codes or []}
        body.update(extra)
        resp = client.post("/api/products", json=body)
        assert resp.status_code == 201, resp.text
        return resp.json()

    return _make


@pytest.fixture()
def make_stock_entry(client, make_product, make_vault):
    def _make(product_id=None, vault_id=None, quantity=1.0, **extra):
        if product_id is None:
            product_id = make_product()["id"]
        if vault_id is None:
            vault_id = make_vault()["id"]
        body = {"product_id": product_id, "vault_id": vault_id, "quantity": quantity}
        body.update(extra)
        resp = client.post("/api/stock/entries", json=body)
        assert resp.status_code == 201, resp.text
        return resp.json()

    return _make
