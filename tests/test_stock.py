"""Coverage for backend/routers/stock.py – entries, summaries, sub-resources."""

import pytest

# ── create / read / update / delete ────────────────────────────────────────

def test_create_stock_entry(client, make_product, make_vault):
    pid = make_product()["id"]
    vid = make_vault()["id"]
    resp = client.post(
        "/api/stock/entries",
        json={"product_id": pid, "vault_id": vid, "quantity": 3, "comment": "hi"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["quantity"] == 3
    assert body["comment"] == "hi"
    assert body["product"]["id"] == pid
    assert body["vault"]["id"] == vid
    assert body["stock_ids"] == []


def test_create_stock_entry_with_bbd(client, make_product, make_vault):
    pid, vid = make_product()["id"], make_vault()["id"]
    resp = client.post(
        "/api/stock/entries",
        json={
            "product_id": pid,
            "vault_id": vid,
            "quantity": 1,
            "best_before_date": "2030-01-15",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["best_before_date"] == "2030-01-15"


def test_create_stock_entry_unknown_product(client, make_vault):
    resp = client.post(
        "/api/stock/entries",
        json={"product_id": 999, "vault_id": make_vault()["id"], "quantity": 1},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Product not found"


def test_create_stock_entry_unknown_vault(client, make_product):
    resp = client.post(
        "/api/stock/entries",
        json={"product_id": make_product()["id"], "vault_id": 999, "quantity": 1},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Vault not found"


def test_create_stock_entry_rejects_non_positive_quantity(client, make_product, make_vault):
    resp = client.post(
        "/api/stock/entries",
        json={"product_id": make_product()["id"], "vault_id": make_vault()["id"], "quantity": 0},
    )
    assert resp.status_code == 422


def test_create_stock_entry_persists_entry_unit(client, make_product, make_vault):
    pid, vid = make_product()["id"], make_vault()["id"]
    resp = client.post(
        "/api/stock/entries",
        json={
            "product_id": pid, "vault_id": vid,
            "quantity": 12, "entry_unit_key": "puc_7", "entry_quantity": 1,
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["quantity"] == 12
    assert body["entry_unit_key"] == "puc_7"
    assert body["entry_quantity"] == 1
    # round-trips on a follow-up GET too
    got = client.get(f"/api/stock/entries/{body['id']}").json()
    assert got["entry_unit_key"] == "puc_7"
    assert got["entry_quantity"] == 1


def test_create_stock_entry_without_entry_unit_is_null(client, make_product, make_vault):
    pid, vid = make_product()["id"], make_vault()["id"]
    body = client.post(
        "/api/stock/entries",
        json={"product_id": pid, "vault_id": vid, "quantity": 5},
    ).json()
    assert body["entry_unit_key"] is None
    assert body["entry_quantity"] is None


def test_create_stock_entry_rejects_non_positive_entry_quantity(client, make_product, make_vault):
    pid, vid = make_product()["id"], make_vault()["id"]
    resp = client.post(
        "/api/stock/entries",
        json={"product_id": pid, "vault_id": vid, "quantity": 5, "entry_quantity": 0},
    )
    assert resp.status_code == 422


def test_update_stock_entry_rewrites_entry_unit(client, make_stock_entry):
    entry = make_stock_entry(quantity=12, entry_unit_key="puc_7", entry_quantity=1)
    resp = client.put(
        f"/api/stock/entries/{entry['id']}",
        json={"quantity": 6, "entry_unit_key": "base", "entry_quantity": 6},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["quantity"] == 6
    assert body["entry_unit_key"] == "base"
    assert body["entry_quantity"] == 6


def test_entry_unit_does_not_affect_stock_summary(client, make_product, make_vault):
    pid, vid = make_product()["id"], make_vault()["id"]
    client.post(
        "/api/stock/entries",
        json={
            "product_id": pid, "vault_id": vid,
            "quantity": 12, "entry_unit_key": "puc_7", "entry_quantity": 1,
        },
    )
    row = next(r for r in client.get("/api/stock/summary").json() if r["product_id"] == pid)
    assert row["total_quantity"] == 12


def test_get_stock_entry_404(client):
    assert client.get("/api/stock/entries/999").status_code == 404


def test_update_stock_entry(client, make_stock_entry):
    entry = make_stock_entry(quantity=2)
    resp = client.put(
        f"/api/stock/entries/{entry['id']}",
        json={"quantity": 7, "comment": "changed"},
    )
    assert resp.status_code == 200
    assert resp.json()["quantity"] == 7
    assert resp.json()["comment"] == "changed"


def test_update_stock_entry_404(client):
    assert client.put("/api/stock/entries/999", json={"quantity": 1}).status_code == 404


def test_update_stock_entry_rejects_non_positive_quantity(client, make_stock_entry):
    entry = make_stock_entry()
    resp = client.put(f"/api/stock/entries/{entry['id']}", json={"quantity": -1})
    assert resp.status_code == 422


def test_delete_stock_entry(client, make_stock_entry):
    entry = make_stock_entry()
    assert client.delete(f"/api/stock/entries/{entry['id']}").status_code == 204
    assert client.get(f"/api/stock/entries/{entry['id']}").status_code == 404


def test_delete_stock_entry_404(client):
    assert client.delete("/api/stock/entries/999").status_code == 404


# ── listing + filters ──────────────────────────────────────────────────────

def test_list_entries_filter_by_vault_and_product(client, make_product, make_vault, make_stock_entry):
    p1, p2 = make_product(name="P1")["id"], make_product(name="P2")["id"]
    v1, v2 = make_vault(description="V1")["id"], make_vault(description="V2")["id"]
    make_stock_entry(product_id=p1, vault_id=v1)
    make_stock_entry(product_id=p2, vault_id=v1)
    make_stock_entry(product_id=p1, vault_id=v2)

    assert len(client.get("/api/stock/entries").json()) == 3
    assert len(client.get("/api/stock/entries", params={"vault_id": v1}).json()) == 2
    assert len(client.get("/api/stock/entries", params={"product_id": p1}).json()) == 2
    assert len(
        client.get("/api/stock/entries", params={"vault_id": v2, "product_id": p1}).json()
    ) == 1


def test_list_entries_pagination(client, make_stock_entry):
    for _ in range(4):
        make_stock_entry()
    page = client.get("/api/stock/entries", params={"skip": 1, "limit": 2}).json()
    assert len(page) == 2


# ── stock summary ──────────────────────────────────────────────────────────

def test_stock_summary_empty(client):
    assert client.get("/api/stock/summary").json() == []


def test_stock_summary_aggregates_by_product_and_vault(client, make_product, make_vault, make_stock_entry):
    pid = make_product(name="Cola")["id"]
    v1 = make_vault(description="Cellar")["id"]
    v2 = make_vault(description="Kitchen")["id"]
    make_stock_entry(product_id=pid, vault_id=v1, quantity=2)
    make_stock_entry(product_id=pid, vault_id=v1, quantity=3)
    make_stock_entry(product_id=pid, vault_id=v2, quantity=4)

    summary = client.get("/api/stock/summary").json()
    assert len(summary) == 1
    row = summary[0]
    assert row["product_id"] == pid
    assert row["total_quantity"] == 9
    by_vault = {v["vault_description"]: v["total_quantity"] for v in row["by_vault"]}
    assert by_vault == {"Cellar": 5, "Kitchen": 4}


# ── category summary ───────────────────────────────────────────────────────

def test_category_summary_groups_and_flags_uncategorised(client, make_category, make_product, make_stock_entry):
    cat = make_category(name="Beverages", min_stock_quantity=10)
    with_cat = make_product(name="Cola", category_id=cat["id"])["id"]
    without_cat = make_product(name="Salt")["id"]
    make_stock_entry(product_id=with_cat, quantity=4)
    make_stock_entry(product_id=without_cat, quantity=1)

    rows = {r["category_name"]: r for r in client.get("/api/stock/category-summary").json()}
    assert rows["Beverages"]["total_quantity"] == 4
    assert rows["Beverages"]["min_stock_quantity"] == 10
    assert rows["Beverages"]["product_count"] == 1
    assert "Ohne Kategorie" in rows
    assert rows["Ohne Kategorie"]["category_id"] is None


def test_category_summary_includes_empty_categories(client, make_category):
    make_category(name="Empty")
    rows = {r["category_name"]: r for r in client.get("/api/stock/category-summary").json()}
    assert rows["Empty"]["total_quantity"] == 0
    assert rows["Empty"]["product_count"] == 0


# ── category summary: unit conversion of the aggregated balance ─────────────
#
# StockEntry.quantity is stored in each product's own base unit. The category
# card on the dashboard prints that sum with the category's ``min_stock_unit``
# label and the traffic light compares it against ``min_stock_quantity`` — so
# the backend has to express ``total_quantity`` in ``min_stock_unit``, applying
# the global UnitConversion table per product before summing.


@pytest.fixture()
def make_conversion(client):
    """1 <from> == factor <to>; the reverse factor is auto-created by the API."""
    def _make(from_unit_id, to_unit_id, factor):
        resp = client.post(
            f"/api/units/{from_unit_id}/conversions",
            json={"to_unit_id": to_unit_id, "factor": factor},
        )
        assert resp.status_code == 201, resp.text
        return resp.json()

    return _make


def test_category_summary_converts_grams_to_kilograms(
    client, make_unit, make_conversion, make_category, make_product, make_stock_entry
):
    # Repro of the prod report: 1441 g in stock must not surface as "1441 kg".
    g = make_unit(name="Gramm", abbreviation="g")
    kg = make_unit(name="Kilogramm", abbreviation="kg")
    make_conversion(kg["id"], g["id"], 1000)  # 1 kg == 1000 g

    cat = make_category(
        name="Fisch & Fleisch", min_stock_quantity=1, min_stock_unit_id=kg["id"]
    )
    pid = make_product(name="Lachs", unit_id=g["id"], category_id=cat["id"])["id"]
    make_stock_entry(product_id=pid, quantity=1441)  # 1441 g

    row = next(
        r for r in client.get("/api/stock/category-summary").json()
        if r["category_name"] == "Fisch & Fleisch"
    )
    assert row["total_quantity"] == pytest.approx(1.441)
    assert row["min_stock_unit"]["abbreviation"] == "kg"
    assert row["unconverted_product_count"] == 0


def test_category_summary_sums_mixed_base_units_after_conversion(
    client, make_unit, make_conversion, make_category, make_product, make_stock_entry
):
    g = make_unit(name="Gramm", abbreviation="g")
    kg = make_unit(name="Kilogramm", abbreviation="kg")
    make_conversion(kg["id"], g["id"], 1000)

    cat = make_category(name="Fleisch", min_stock_unit_id=kg["id"])
    in_g = make_product(name="Hack", unit_id=g["id"], category_id=cat["id"])["id"]
    in_kg = make_product(name="Braten", unit_id=kg["id"], category_id=cat["id"])["id"]
    make_stock_entry(product_id=in_g, quantity=500)   # 0.5 kg
    make_stock_entry(product_id=in_kg, quantity=2)    # 2   kg

    row = next(
        r for r in client.get("/api/stock/category-summary").json()
        if r["category_name"] == "Fleisch"
    )
    assert row["total_quantity"] == pytest.approx(2.5)
    assert row["product_count"] == 2
    assert row["unconverted_product_count"] == 0


def test_category_summary_no_conversion_needed_when_unit_matches(
    client, make_unit, make_category, make_product, make_stock_entry
):
    kg = make_unit(name="Kilogramm", abbreviation="kg")
    cat = make_category(name="Fleisch", min_stock_unit_id=kg["id"])
    pid = make_product(name="Braten", unit_id=kg["id"], category_id=cat["id"])["id"]
    make_stock_entry(product_id=pid, quantity=3)

    row = next(
        r for r in client.get("/api/stock/category-summary").json()
        if r["category_name"] == "Fleisch"
    )
    assert row["total_quantity"] == pytest.approx(3)
    assert row["unconverted_product_count"] == 0


def test_category_summary_flags_products_without_conversion_path(
    client, make_unit, make_conversion, make_category, make_product, make_stock_entry
):
    g = make_unit(name="Gramm", abbreviation="g")
    kg = make_unit(name="Kilogramm", abbreviation="kg")
    stk = make_unit(name="Stück", abbreviation="Stk")
    make_conversion(kg["id"], g["id"], 1000)  # no path between Stück and kg

    cat = make_category(name="Fleisch", min_stock_unit_id=kg["id"])
    convertible = make_product(name="Hack", unit_id=g["id"], category_id=cat["id"])["id"]
    orphan = make_product(name="Würstchen", unit_id=stk["id"], category_id=cat["id"])["id"]
    make_stock_entry(product_id=convertible, quantity=1000)  # 1 kg
    make_stock_entry(product_id=orphan, quantity=5)          # cannot convert

    row = next(
        r for r in client.get("/api/stock/category-summary").json()
        if r["category_name"] == "Fleisch"
    )
    assert row["total_quantity"] == pytest.approx(1.0)  # orphan excluded
    assert row["product_count"] == 2
    assert row["unconverted_product_count"] == 1


def test_category_summary_flags_product_without_unit(
    client, make_unit, make_category, make_product, make_stock_entry
):
    kg = make_unit(name="Kilogramm", abbreviation="kg")
    cat = make_category(name="Fleisch", min_stock_unit_id=kg["id"])
    pid = make_product(name="Mystery", category_id=cat["id"])["id"]  # unit_id is None
    make_stock_entry(product_id=pid, quantity=4)

    row = next(
        r for r in client.get("/api/stock/category-summary").json()
        if r["category_name"] == "Fleisch"
    )
    assert row["total_quantity"] == pytest.approx(0.0)
    assert row["unconverted_product_count"] == 1


def test_category_summary_without_min_stock_unit_sums_raw(
    client, make_unit, make_category, make_product, make_stock_entry
):
    # No target unit on the category → nothing to convert to; keep the plain sum
    # and report nothing as unconverted.
    g = make_unit(name="Gramm", abbreviation="g")
    kg = make_unit(name="Kilogramm", abbreviation="kg")
    cat = make_category(name="Diverses")  # min_stock_unit_id omitted
    a = make_product(name="A", unit_id=g["id"], category_id=cat["id"])["id"]
    b = make_product(name="B", unit_id=kg["id"], category_id=cat["id"])["id"]
    make_stock_entry(product_id=a, quantity=2)
    make_stock_entry(product_id=b, quantity=3)

    row = next(
        r for r in client.get("/api/stock/category-summary").json()
        if r["category_name"] == "Diverses"
    )
    assert row["total_quantity"] == pytest.approx(5)
    assert row["unconverted_product_count"] == 0


def test_category_summary_uncategorised_sums_raw(
    client, make_unit, make_product, make_stock_entry
):
    g = make_unit(name="Gramm", abbreviation="g")
    pid = make_product(name="Salz", unit_id=g["id"])["id"]  # no category
    make_stock_entry(product_id=pid, quantity=750)

    row = next(
        r for r in client.get("/api/stock/category-summary").json()
        if r["category_id"] is None
    )
    assert row["total_quantity"] == pytest.approx(750)
    assert row["unconverted_product_count"] == 0


def test_category_summary_uses_reverse_conversion_factor(
    client, make_unit, make_conversion, make_category, make_product, make_stock_entry
):
    # Conversion registered as kg→g; product is in kg, category wants g.
    g = make_unit(name="Gramm", abbreviation="g")
    kg = make_unit(name="Kilogramm", abbreviation="kg")
    make_conversion(kg["id"], g["id"], 1000)

    cat = make_category(name="Fleisch", min_stock_unit_id=g["id"])
    pid = make_product(name="Braten", unit_id=kg["id"], category_id=cat["id"])["id"]
    make_stock_entry(product_id=pid, quantity=2)  # 2 kg → 2000 g

    row = next(
        r for r in client.get("/api/stock/category-summary").json()
        if r["category_name"] == "Fleisch"
    )
    assert row["total_quantity"] == pytest.approx(2000)
    assert row["unconverted_product_count"] == 0


def test_category_summary_empty_category_reports_zero_unconverted(client, make_category):
    make_category(name="Empty")
    row = next(
        r for r in client.get("/api/stock/category-summary").json()
        if r["category_name"] == "Empty"
    )
    assert row["unconverted_product_count"] == 0


# ── stock-entry tags ───────────────────────────────────────────────────────

def test_stock_entry_tag_add_remove(client, make_stock_entry):
    eid = make_stock_entry()["id"]
    assert client.post(f"/api/stock/entries/{eid}/tags", json={"name": "opened"}).status_code == 201
    client.post(f"/api/stock/entries/{eid}/tags", json={"name": "opened"})  # idempotent
    tags = client.get(f"/api/stock/entries/{eid}").json()["tags"]
    assert [t["name"] for t in tags] == ["opened"]

    assert client.delete(f"/api/stock/entries/{eid}/tags/opened").status_code == 204
    assert client.get(f"/api/stock/entries/{eid}").json()["tags"] == []


def test_stock_entry_tag_missing_entry(client):
    assert client.post("/api/stock/entries/999/tags", json={"name": "x"}).status_code == 404
    assert client.delete("/api/stock/entries/999/tags/x").status_code == 404


# ── stock IDs ──────────────────────────────────────────────────────────────

def test_add_lookup_and_remove_stock_id(client, make_stock_entry):
    eid = make_stock_entry()["id"]
    resp = client.post(f"/api/stock/entries/{eid}/stockids", json={"code": "INV-1"})
    assert resp.status_code == 201
    sid = resp.json()["id"]

    found = client.get("/api/stock/entries/by-stockid/INV-1")
    assert found.status_code == 200
    assert found.json()["id"] == eid

    assert client.delete(f"/api/stock/entries/{eid}/stockids/{sid}").status_code == 204
    assert client.get("/api/stock/entries/by-stockid/INV-1").status_code == 404


def test_add_stock_id_missing_entry(client):
    assert client.post("/api/stock/entries/999/stockids", json={"code": "x"}).status_code == 404


def test_remove_stock_id_404(client, make_stock_entry):
    eid = make_stock_entry()["id"]
    assert client.delete(f"/api/stock/entries/{eid}/stockids/123").status_code == 404


def test_lookup_by_unknown_stock_id(client):
    assert client.get("/api/stock/entries/by-stockid/nope").status_code == 404
