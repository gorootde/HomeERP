"""Coverage for the stock-movement audit log: listing, filters, consumption
forecast and every branch of ``undo_movement``.

This subsystem previously had no backend tests at all despite containing the
most complex logic in the project (see CLAUDE.md / the refactoring plan) —
added as a safety net before splitting ``routers/stock.py``.
"""


def _movement_for(client, *, stock_entry_id=None, reason=None):
    resp = client.get("/api/stock/movements")
    assert resp.status_code == 200
    rows = resp.json()
    for row in rows:
        if stock_entry_id is not None and row["stock_entry_id"] != stock_entry_id:
            continue
        if reason is not None and row["reason"] != reason:
            continue
        return row
    raise AssertionError(f"no movement found for entry={stock_entry_id} reason={reason}")


# ── listing / filters ───────────────────────────────────────────────────────

def test_create_stock_entry_records_a_create_movement(client, make_stock_entry):
    entry = make_stock_entry(quantity=5)
    mv = _movement_for(client, stock_entry_id=entry["id"], reason="create")
    assert mv["quantity_before"] == 0
    assert mv["quantity_after"] == 5
    assert mv["delta"] == 5
    assert mv["can_undo"] is True
    assert mv["undone"] is False


def test_list_entry_movements_filters_to_one_entry(client, make_stock_entry):
    e1 = make_stock_entry(quantity=1)
    make_stock_entry(quantity=2)
    resp = client.get(f"/api/stock/entries/{e1['id']}/movements")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["stock_entry_id"] == e1["id"]


def test_list_movements_filters_by_product_vault_and_reason(client, make_stock_entry, make_product, make_vault):
    other_product = make_product(name="Other")["id"]
    other_vault = make_vault(description="Other vault")["id"]
    entry = make_stock_entry(quantity=1)
    make_stock_entry(product_id=other_product, vault_id=other_vault, quantity=1)

    by_product = client.get(f"/api/stock/movements?product_id={entry['product']['id']}").json()
    assert all(m["product_id"] == entry["product"]["id"] for m in by_product)
    assert len(by_product) == 1

    by_vault = client.get(f"/api/stock/movements?vault_id={entry['vault']['id']}").json()
    assert len(by_vault) == 1

    by_reason = client.get("/api/stock/movements?reason=create").json()
    assert len(by_reason) == 2
    by_reason_none = client.get("/api/stock/movements?reason=consume").json()
    assert by_reason_none == []


def test_list_movements_include_undone_false_hides_undone_rows(client, make_stock_entry):
    entry = make_stock_entry(quantity=5)
    mv = _movement_for(client, stock_entry_id=entry["id"], reason="create")
    resp = client.post(f"/api/stock/movements/{mv['id']}/undo")
    assert resp.status_code == 200

    with_undone = client.get("/api/stock/movements?include_undone=true").json()
    assert any(m["id"] == mv["id"] and m["undone"] for m in with_undone)

    without_undone = client.get("/api/stock/movements?include_undone=false").json()
    assert all(m["id"] != mv["id"] for m in without_undone)


# ── consumption forecast ────────────────────────────────────────────────────

def test_consumption_forecast_computes_rate_and_days_remaining(client, make_stock_entry):
    entry = make_stock_entry(quantity=10)
    resp = client.put(f"/api/stock/entries/{entry['id']}", json={"quantity": 4})
    assert resp.status_code == 200

    forecast = client.get("/api/stock/movements/forecast?days=90").json()
    row = next(f for f in forecast if f["product_id"] == entry["product"]["id"])
    assert row["current_stock"] == 4
    assert row["consumed_in_window"] == 6
    assert row["avg_daily_consumption"] == 6 / 90
    assert row["days_remaining"] == 4 / (6 / 90)


def test_consumption_forecast_excludes_products_with_no_consumption(client, make_stock_entry):
    make_stock_entry(quantity=10)  # only a "create" movement, no negative delta
    forecast = client.get("/api/stock/movements/forecast?days=90").json()
    assert forecast == []


# ── undo: restore a still-existing entry (partial) ──────────────────────────

def test_undo_edit_restores_previous_quantity(client, make_stock_entry):
    entry = make_stock_entry(quantity=5)
    resp = client.put(f"/api/stock/entries/{entry['id']}", json={"quantity": 3})
    assert resp.status_code == 200
    edit_mv = _movement_for(client, stock_entry_id=entry["id"], reason="edit")

    resp = client.post(f"/api/stock/movements/{edit_mv['id']}/undo")
    assert resp.status_code == 200
    reversal = resp.json()
    assert reversal["reason"] == "undo"
    assert reversal["quantity_before"] == 3
    assert reversal["quantity_after"] == 5

    refreshed = client.get(f"/api/stock/entries/{entry['id']}").json()
    assert refreshed["quantity"] == 5


def test_undo_negative_result_is_rejected(client, make_stock_entry):
    entry = make_stock_entry(quantity=5)
    create_mv = _movement_for(client, stock_entry_id=entry["id"], reason="create")
    resp = client.put(f"/api/stock/entries/{entry['id']}", json={"quantity": 2})
    assert resp.status_code == 200

    resp = client.post(f"/api/stock/movements/{create_mv['id']}/undo")
    assert resp.status_code == 409


# ── undo: restore-to-zero deletes the entry ─────────────────────────────────

def test_undo_create_movement_deletes_entry_when_quantity_unchanged(client, make_stock_entry):
    entry = make_stock_entry(quantity=5)
    create_mv = _movement_for(client, stock_entry_id=entry["id"], reason="create")

    resp = client.post(f"/api/stock/movements/{create_mv['id']}/undo")
    assert resp.status_code == 200
    reversal = resp.json()
    assert reversal["stock_entry_id"] is None
    assert reversal["quantity_after"] == 0

    assert client.get(f"/api/stock/entries/{entry['id']}").status_code == 404


# ── undo: recreate a deleted entry from its snapshot ────────────────────────

def test_undo_delete_recreates_entry_from_snapshot(client, make_stock_entry):
    entry = make_stock_entry(quantity=5, comment="test note", stock_id="SID-1")
    resp = client.delete(f"/api/stock/entries/{entry['id']}")
    assert resp.status_code == 204
    delete_mv = _movement_for(client, stock_entry_id=None, reason="delete")

    resp = client.post(f"/api/stock/movements/{delete_mv['id']}/undo")
    assert resp.status_code == 200
    reversal = resp.json()
    assert reversal["reason"] == "undo"
    assert reversal["quantity_after"] == 5
    new_entry_id = reversal["stock_entry_id"]
    assert new_entry_id is not None

    recreated = client.get(f"/api/stock/entries/{new_entry_id}").json()
    assert recreated["quantity"] == 5
    assert recreated["comment"] == "test note"
    assert [s["code"] for s in recreated["stock_ids"]] == ["SID-1"]


def test_undo_delete_conflict_when_product_no_longer_exists(client, make_stock_entry, make_product):
    entry = make_stock_entry(quantity=5)
    product_id = entry["product"]["id"]
    resp = client.delete(f"/api/stock/entries/{entry['id']}")
    assert resp.status_code == 204
    delete_mv = _movement_for(client, stock_entry_id=None, reason="delete")

    assert client.delete(f"/api/products/{product_id}").status_code == 204

    resp = client.post(f"/api/stock/movements/{delete_mv['id']}/undo")
    assert resp.status_code == 409


# ── undo: guard rails ────────────────────────────────────────────────────────

def test_undo_already_undone_movement_returns_409(client, make_stock_entry):
    entry = make_stock_entry(quantity=5)
    create_mv = _movement_for(client, stock_entry_id=entry["id"], reason="create")
    assert client.post(f"/api/stock/movements/{create_mv['id']}/undo").status_code == 200
    resp = client.post(f"/api/stock/movements/{create_mv['id']}/undo")
    assert resp.status_code == 409


def test_undo_an_undo_movement_returns_409(client, make_stock_entry):
    entry = make_stock_entry(quantity=5)
    create_mv = _movement_for(client, stock_entry_id=entry["id"], reason="create")
    undo_resp = client.post(f"/api/stock/movements/{create_mv['id']}/undo")
    assert undo_resp.status_code == 200
    undo_mv_id = undo_resp.json()["id"]

    resp = client.post(f"/api/stock/movements/{undo_mv_id}/undo")
    assert resp.status_code == 409


def test_undo_missing_movement_returns_404(client):
    resp = client.post("/api/stock/movements/999999/undo")
    assert resp.status_code == 404
