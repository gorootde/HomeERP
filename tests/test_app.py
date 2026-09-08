"""App-level wiring: OpenAPI, SPA fallback, uploads mount, CRUD smoke path."""


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


def test_root_static_assets_are_served(client, tmp_path, monkeypatch):
    """Files emitted at the root of the SvelteKit build (favicon, manifest,
    PWA icons, …) must be served as real files, not shadowed by the SPA
    index fallback."""
    import backend.main as main

    (tmp_path / "index.html").write_text("<!doctype html><title>SPA</title>")
    (tmp_path / "favicon.ico").write_bytes(b"\x00\x00\x01\x00")
    (tmp_path / "homeerp-icon.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>")
    monkeypatch.setattr(main, "FRONTEND_DIR", tmp_path)

    ico = client.get("/favicon.ico")
    assert ico.status_code == 200
    assert ico.content == b"\x00\x00\x01\x00"
    assert "text/html" not in ico.headers["content-type"]

    svg = client.get("/homeerp-icon.svg")
    assert svg.status_code == 200
    assert "svg" in svg.headers["content-type"]

    # Unknown non-API paths still fall through to the SPA index.
    spa = client.get("/some/client/route")
    assert spa.status_code == 200
    assert "text/html" in spa.headers["content-type"]


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
