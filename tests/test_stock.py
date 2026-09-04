"""Coverage for backend/routers/stock.py – entries, summaries, sub-resources."""


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
