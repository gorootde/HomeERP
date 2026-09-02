"""App-level wiring: OpenAPI, SPA fallback, uploads mount, CRUD smoke path."""
import pytest


def test_openapi_schema_served(client):
    spec = client.get("/openapi.json").json()
    assert spec["info"]["title"] == "HomeERP"
    paths = spec["paths"]
    assert "/api/products" in paths
    assert "/api/stock/entries" in paths
    assert "/api/settings/printing/preview" in paths


def test_docs_available(client):
    assert client.get("/docs").status_code == 200


def test_unknown_api_path_is_404_not_spa(client):
    resp = client.get("/api/definitely-not-a-route")
    assert resp.status_code == 404


def test_spa_fallback_serves_index_for_client_routes(client):
    """Non-API paths fall through to the SPA index (or a clean 404 if it is
    not built)."""
    resp = client.get("/some/client/route")
    if resp.status_code == 200:
        assert "text/html" in resp.headers["content-type"]
    else:
        assert resp.status_code == 404


def test_full_crud_smoke(client):
    unit = client.post("/api/units", json={"name": "Piece", "abbreviation": "pc"}).json()
    cat = client.post("/api/categories", json={"name": "Misc"}).json()
    product = client.post(
        "/api/products",
        json={
            "vendor": "ACME",
            "name": "Gadget",
            "unit_id": unit["id"],
            "category_id": cat["id"],
            "ean_codes": ["4000000012345"],
        },
    ).json()
    vault = client.post("/api/vaults", json={"description": "Shelf A"}).json()

    entry = client.post(
        "/api/stock/entries",
        json={
            "product_id": product["id"],
            "vault_id": vault["id"],
            "quantity": 6,
            "stock_id": "SMOKE-1",
        },
    ).json()

    # scanner lookups
    assert client.get("/api/products/by-ean/4000000012345").json()["id"] == product["id"]
    assert client.get("/api/stock/entries/by-stockid/SMOKE-1").json()["id"] == entry["id"]

    # dashboard aggregates
    summary = client.get("/api/stock/summary").json()
    assert summary[0]["total_quantity"] == 6
    cats = {c["category_name"]: c for c in client.get("/api/stock/category-summary").json()}
    assert cats["Misc"]["total_quantity"] == 6

    # tear down
    assert client.delete(f"/api/stock/entries/{entry['id']}").status_code == 204
    assert client.delete(f"/api/products/{product['id']}").status_code == 204
