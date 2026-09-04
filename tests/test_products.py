"""Coverage for backend/routers/products.py."""
import io

from PIL import Image


def _png_bytes(color=(255, 0, 0)):
    buf = io.BytesIO()
    Image.new("RGB", (4, 4), color).save(buf, format="PNG")
    return buf.getvalue()


# ── list / create / get / update / delete ──────────────────────────────────

def test_list_products_empty(client):
    resp = client.get("/api/products")
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_product_minimal(client):
    resp = client.post(
        "/api/products", json={"vendor": "ACME", "name": "Widget"}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Widget"
    assert body["vendor"] == "ACME"
    assert body["ean_codes"] == []
    assert body["id"] > 0


def test_create_product_with_full_payload(client, make_unit, make_category):
    unit = make_unit()
    cat = make_category()
    resp = client.post(
        "/api/products",
        json={
            "vendor": "ACME",
            "name": "Widget",
            "unit_id": unit["id"],
            "category_id": cat["id"],
            "entry_unit_key": "base",
            "ean_codes": ["4001234567890", "4009876543210"],
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert "size" not in body
    assert body["unit"]["id"] == unit["id"]
    assert body["category"]["id"] == cat["id"]
    assert {e["code"] for e in body["ean_codes"]} == {"4001234567890", "4009876543210"}


def test_create_product_rejects_blank_name(client):
    resp = client.post("/api/products", json={"vendor": "ACME", "name": ""})
    assert resp.status_code == 422


def test_create_product_duplicate_ean_conflicts(client, make_product):
    make_product(ean_codes=["111"])
    resp = client.post(
        "/api/products",
        json={"vendor": "V", "name": "Other", "ean_codes": ["111"]},
    )
    assert resp.status_code == 409


def test_get_product_404(client):
    assert client.get("/api/products/999").status_code == 404


def test_update_product_partial(client, make_product):
    pid = make_product(name="Old")["id"]
    resp = client.put(f"/api/products/{pid}", json={"name": "New"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "New"
    assert resp.json()["vendor"] == "Coca-Cola"  # untouched


def test_update_product_404(client):
    assert client.put("/api/products/999", json={"name": "x"}).status_code == 404


def test_delete_product(client, make_product):
    pid = make_product()["id"]
    assert client.delete(f"/api/products/{pid}").status_code == 204
    assert client.get(f"/api/products/{pid}").status_code == 404


def test_delete_product_404(client):
    assert client.delete("/api/products/999").status_code == 404


# ── search / pagination ────────────────────────────────────────────────────

def test_list_products_search_matches_name_and_vendor(client, make_product):
    make_product(name="Apple Juice", vendor="Granini")
    make_product(name="Cola", vendor="Coca-Cola")
    assert len(client.get("/api/products", params={"search": "juice"}).json()) == 1
    assert len(client.get("/api/products", params={"search": "coca"}).json()) == 1
    assert client.get("/api/products", params={"search": "zzz"}).json() == []


def test_list_products_pagination(client, make_product):
    for i in range(5):
        make_product(name=f"P{i}")
    page = client.get("/api/products", params={"skip": 2, "limit": 2}).json()
    assert len(page) == 2


# ── EAN sub-resource ───────────────────────────────────────────────────────

def test_get_product_by_ean(client, make_product):
    make_product(name="Beans", ean_codes=["4000000000001"])
    resp = client.get("/api/products/by-ean/4000000000001")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Beans"


def test_get_product_by_ean_404(client):
    assert client.get("/api/products/by-ean/nope").status_code == 404


def test_add_and_remove_ean(client, make_product):
    pid = make_product()["id"]
    resp = client.post(f"/api/products/{pid}/ean", json={"code": "555"})
    assert resp.status_code == 201
    ean_id = resp.json()["id"]

    detail = client.get(f"/api/products/{pid}").json()
    assert any(e["code"] == "555" for e in detail["ean_codes"])

    assert client.delete(f"/api/products/{pid}/ean/{ean_id}").status_code == 204
    detail = client.get(f"/api/products/{pid}").json()
    assert detail["ean_codes"] == []


def test_add_ean_to_missing_product(client):
    assert client.post("/api/products/999/ean", json={"code": "1"}).status_code == 404


def test_add_duplicate_ean_conflicts(client, make_product):
    make_product(name="A", ean_codes=["dup"])
    p2 = make_product(name="B")
    resp = client.post(f"/api/products/{p2['id']}/ean", json={"code": "dup"})
    assert resp.status_code == 409


def test_remove_ean_404(client, make_product):
    pid = make_product()["id"]
    assert client.delete(f"/api/products/{pid}/ean/12345").status_code == 404


# ── image upload / delete ──────────────────────────────────────────────────

def test_upload_image_and_delete(client, make_product):
    pid = make_product()["id"]
    resp = client.post(
        f"/api/products/{pid}/image",
        files={"file": ("p.png", _png_bytes(), "image/png")},
    )
    assert resp.status_code == 200
    assert resp.json()["image_path"].startswith("/uploads/")

    assert client.delete(f"/api/products/{pid}/image").status_code == 204
    assert client.get(f"/api/products/{pid}").json()["image_path"] is None


def test_upload_image_rejects_unsupported_type(client, make_product):
    pid = make_product()["id"]
    resp = client.post(
        f"/api/products/{pid}/image",
        files={"file": ("p.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 415


def test_upload_image_missing_product(client):
    resp = client.post(
        "/api/products/999/image",
        files={"file": ("p.png", _png_bytes(), "image/png")},
    )
    assert resp.status_code == 404


def test_image_from_url(client, make_product, monkeypatch):
    pid = make_product()["id"]

    class _Resp:
        headers = {"Content-Type": "image/png"}

        def read(self, _n=None):
            return _png_bytes()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(
        "backend.routers.products.urllib.request.urlopen", lambda *a, **k: _Resp()
    )
    resp = client.post(
        f"/api/products/{pid}/image-from-url",
        json={"url": "http://example.com/x.png"},
    )
    assert resp.status_code == 200
    assert resp.json()["image_path"].startswith("/uploads/")


def test_image_from_url_download_failure(client, make_product, monkeypatch):
    pid = make_product()["id"]

    def _boom(*_a, **_k):
        raise OSError("dns")

    monkeypatch.setattr(
        "backend.routers.products.urllib.request.urlopen", _boom
    )
    resp = client.post(
        f"/api/products/{pid}/image-from-url", json={"url": "http://x/y.png"}
    )
    assert resp.status_code == 400


# ── product tags ───────────────────────────────────────────────────────────

def test_product_tag_add_remove_and_dedup(client, make_product):
    pid = make_product()["id"]
    assert client.post(f"/api/products/{pid}/tags", json={"name": "bio"}).status_code == 201
    # adding the same tag again is idempotent, not an error
    client.post(f"/api/products/{pid}/tags", json={"name": "bio"})
    tags = client.get(f"/api/products/{pid}").json()["tags"]
    assert [t["name"] for t in tags] == ["bio"]

    assert client.delete(f"/api/products/{pid}/tags/bio").status_code == 204
    assert client.get(f"/api/products/{pid}").json()["tags"] == []


def test_product_tag_missing_product(client):
    assert client.post("/api/products/999/tags", json={"name": "x"}).status_code == 404


# ── product unit conversions ───────────────────────────────────────────────

def test_product_unit_conversion_crud(client, make_product, make_unit):
    pid = make_product()["id"]
    unit = make_unit(name="Millilitre", abbreviation="ml")

    resp = client.post(
        f"/api/products/{pid}/unit-conversions",
        json={"unit_name": "Bottle", "base_unit_id": unit["id"], "factor": 500},
    )
    assert resp.status_code == 201
    conv_id = resp.json()["id"]
    assert resp.json()["unit_name"] == "Bottle"

    listed = client.get(f"/api/products/{pid}/unit-conversions").json()
    assert len(listed) == 1

    # duplicate unit_name for the same product → 409
    dup = client.post(
        f"/api/products/{pid}/unit-conversions",
        json={"unit_name": "Bottle", "base_unit_id": unit["id"], "factor": 1},
    )
    assert dup.status_code == 409

    assert client.delete(
        f"/api/products/{pid}/unit-conversions/{conv_id}"
    ).status_code == 204
    assert client.get(f"/api/products/{pid}/unit-conversions").json() == []


def test_product_unit_conversion_missing_product(client):
    assert (
        client.get("/api/products/999/unit-conversions").status_code == 404
    )
    assert (
        client.delete("/api/products/999/unit-conversions/1").status_code == 404
    )


def test_product_unit_conversion_delete_404(client, make_product):
    pid = make_product()["id"]
    assert (
        client.delete(f"/api/products/{pid}/unit-conversions/123").status_code
        == 404
    )
