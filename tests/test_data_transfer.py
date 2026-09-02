"""Coverage for backend/routers/data_transfer.py – export ZIP + preview/apply import."""
import io
import json
import zipfile

import pytest


def _read_zip(content: bytes):
    zf = zipfile.ZipFile(io.BytesIO(content))
    return {name: zf.read(name) for name in zf.namelist()}


# ── export ─────────────────────────────────────────────────────────────────

def test_export_models_lists_tables_with_counts(client, make_product):
    make_product()
    make_product(name="Second")
    rows = {m["table_name"]: m for m in client.get("/api/export/models").json()}
    assert "products" in rows
    assert rows["products"]["row_count"] == 2
    assert rows["products"]["display_name"] == "Products"


def test_export_produces_zip_with_selected_tables(client, make_product, make_vault):
    make_product(name="Exported", ean_codes=["999"])
    make_vault(description="ExportedVault")

    resp = client.post("/api/export", json={"tables": ["products", "vaults", "ean_codes"]})
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"

    members = _read_zip(resp.content)
    assert set(members) == {"products.json", "vaults.json", "ean_codes.json"}

    products = [json.loads(l) for l in members["products.json"].decode().splitlines() if l.strip()]
    assert products[0]["name"] == "Exported"


def test_export_ignores_unknown_tables(client, make_product):
    make_product()
    resp = client.post("/api/export", json={"tables": ["products", "not_a_table"]})
    assert resp.status_code == 200
    assert set(_read_zip(resp.content)) == {"products.json"}


def test_export_bundles_product_images(client, make_product):
    pid = make_product()["id"]
    import io as _io
    from PIL import Image

    buf = _io.BytesIO()
    Image.new("RGB", (4, 4), (0, 128, 0)).save(buf, format="PNG")
    client.post(
        f"/api/products/{pid}/image",
        files={"file": ("p.png", buf.getvalue(), "image/png")},
    )

    resp = client.post("/api/export", json={"tables": ["products"]})
    members = _read_zip(resp.content)
    assert any(name.startswith("images/") for name in members)


# ── import round-trip ──────────────────────────────────────────────────────

def _make_import_zip(tables: dict[str, list[dict]]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, rows in tables.items():
            zf.writestr(
                f"{name}.json",
                "\n".join(json.dumps(r) for r in rows),
            )
    return buf.getvalue()


def test_import_preview_then_apply(client):
    zip_bytes = _make_import_zip(
        {
            "vaults": [{"id": 1, "description": "Imported Cellar"}],
            "units": [{"id": 1, "name": "Litre", "abbreviation": "l"}],
        }
    )

    preview = client.post(
        "/api/import/preview",
        files={"file": ("dump.zip", zip_bytes, "application/zip")},
    ).json()
    assert "import_id" in preview
    tables = {row["table_name"]: row for row in preview["preview"]}
    assert tables["vaults"]["row_count"] == 1
    assert tables["vaults"]["known"] is True

    result = client.post(f"/api/import/apply/{preview['import_id']}").json()
    applied = {r["table_name"]: r for r in result["results"]}
    assert applied["vaults"]["imported"] == 1
    assert applied["units"]["imported"] == 1

    assert client.get("/api/vaults/1").json()["description"] == "Imported Cellar"
    assert client.get("/api/units/1").json()["name"] == "Litre"


def test_import_preview_rejects_non_zip(client):
    resp = client.post(
        "/api/import/preview",
        files={"file": ("dump.txt", b"nope", "text/plain")},
    )
    assert resp.status_code == 400


def test_import_preview_flags_unknown_tables(client):
    zip_bytes = _make_import_zip({"martians": [{"id": 1}]})
    preview = client.post(
        "/api/import/preview",
        files={"file": ("d.zip", zip_bytes, "application/zip")},
    ).json()
    tables = {row["table_name"]: row for row in preview["preview"]}
    assert tables["martians"]["known"] is False

    result = client.post(f"/api/import/apply/{preview['import_id']}").json()
    applied = {r["table_name"]: r for r in result["results"]}
    assert applied["martians"]["error"] == "unknown_table"
    assert applied["martians"]["imported"] == 0


def test_import_apply_unknown_session_404(client):
    assert client.post("/api/import/apply/does-not-exist").status_code == 404


def test_import_apply_is_single_use(client):
    zip_bytes = _make_import_zip({"vaults": [{"id": 5, "description": "Once"}]})
    preview = client.post(
        "/api/import/preview",
        files={"file": ("d.zip", zip_bytes, "application/zip")},
    ).json()
    first = client.post(f"/api/import/apply/{preview['import_id']}")
    assert first.status_code == 200
    second = client.post(f"/api/import/apply/{preview['import_id']}")
    assert second.status_code == 404


def test_import_coerces_date_columns(client, make_product, make_vault):
    pid = make_product()["id"]
    vid = make_vault()["id"]
    zip_bytes = _make_import_zip(
        {
            "stock_entries": [
                {
                    "id": 1,
                    "product_id": pid,
                    "vault_id": vid,
                    "quantity": 2.0,
                    "comment": None,
                    "best_before_date": "2030-06-01",
                }
            ]
        }
    )
    preview = client.post(
        "/api/import/preview",
        files={"file": ("d.zip", zip_bytes, "application/zip")},
    ).json()
    client.post(f"/api/import/apply/{preview['import_id']}")
    entry = client.get("/api/stock/entries/1").json()
    assert entry["best_before_date"] == "2030-06-01"
