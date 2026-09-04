"""Stock-ID assignment strategies and per-entry label auto-print.

Exercises the ``_apply_generated_stock_id`` / ``_apply_webhook_stock_id`` /
``_maybe_print_label`` helpers through the public create-entry endpoint.
"""


def _set(client, key, value):
    assert client.put(f"/api/settings/{key}", json={"value": value}).status_code == 200


# ── manual (explicit stock_id on the request) ──────────────────────────────

def test_manual_stock_id_from_request_body(client, make_product, make_vault):
    pid, vid = make_product()["id"], make_vault()["id"]
    resp = client.post(
        "/api/stock/entries",
        json={"product_id": pid, "vault_id": vid, "quantity": 1, "stock_id": "HAND-1"},
    )
    assert resp.status_code == 201
    assert [s["code"] for s in resp.json()["stock_ids"]] == ["HAND-1"]


def test_manual_mode_without_stock_id_leaves_entry_bare(client, make_product, make_vault):
    _set(client, "stock_id_mode", "manual")
    pid, vid = make_product()["id"], make_vault()["id"]
    resp = client.post(
        "/api/stock/entries",
        json={"product_id": pid, "vault_id": vid, "quantity": 1},
    )
    assert resp.json()["stock_ids"] == []


# ── generated (incrementing counter with prefix + padding) ─────────────────

def test_generated_stock_id_increments_with_prefix_and_padding(client, make_product, make_vault):
    _set(client, "stock_id_mode", "generated")
    _set(client, "stock_id_prefix", "INV")
    _set(client, "stock_id_counter", "0")
    _set(client, "stock_id_pad_length", "4")

    pid, vid = make_product()["id"], make_vault()["id"]

    first = client.post(
        "/api/stock/entries", json={"product_id": pid, "vault_id": vid, "quantity": 1}
    ).json()
    second = client.post(
        "/api/stock/entries", json={"product_id": pid, "vault_id": vid, "quantity": 1}
    ).json()

    assert [s["code"] for s in first["stock_ids"]] == ["INV0001"]
    assert [s["code"] for s in second["stock_ids"]] == ["INV0002"]
    assert client.get("/api/settings/stock_id_counter").json()["value"] == "2"


def test_generated_stock_id_without_padding(client, make_product, make_vault):
    _set(client, "stock_id_mode", "generated")
    _set(client, "stock_id_counter", "40")
    _set(client, "stock_id_pad_length", "0")
    pid, vid = make_product()["id"], make_vault()["id"]
    entry = client.post(
        "/api/stock/entries", json={"product_id": pid, "vault_id": vid, "quantity": 1}
    ).json()
    assert [s["code"] for s in entry["stock_ids"]] == ["41"]


def test_explicit_stock_id_wins_over_generated_mode(client, make_product, make_vault):
    _set(client, "stock_id_mode", "generated")
    _set(client, "stock_id_counter", "0")
    pid, vid = make_product()["id"], make_vault()["id"]
    entry = client.post(
        "/api/stock/entries",
        json={"product_id": pid, "vault_id": vid, "quantity": 1, "stock_id": "MANUAL"},
    ).json()
    assert [s["code"] for s in entry["stock_ids"]] == ["MANUAL"]
    # counter must not have advanced
    assert client.get("/api/settings/stock_id_counter").json()["value"] == "0"


# ── extern (webhook supplies the code) ─────────────────────────────────────

def test_webhook_stock_id_uses_response_body(client, make_product, make_vault, monkeypatch):
    _set(client, "stock_id_mode", "extern")
    _set(client, "stock_id_webhook_url", "http://printer.local/next?p={product_id}&q={quantity}")

    calls = {}

    class _Resp:
        text = "  WEB-777  \n"

        def raise_for_status(self):
            return None

    def _fake_get(url, timeout=None):
        calls["url"] = url
        return _Resp()

    monkeypatch.setattr("backend.routers.stock.httpx.get", _fake_get)

    pid, vid = make_product()["id"], make_vault()["id"]
    entry = client.post(
        "/api/stock/entries", json={"product_id": pid, "vault_id": vid, "quantity": 5}
    ).json()

    assert [s["code"] for s in entry["stock_ids"]] == ["WEB-777"]
    assert f"p={pid}" in calls["url"] and "q=5" in calls["url"]


def test_webhook_failure_does_not_break_entry_creation(client, make_product, make_vault, monkeypatch):
    _set(client, "stock_id_mode", "extern")
    _set(client, "stock_id_webhook_url", "http://printer.local/next")

    def _boom(*_a, **_k):
        raise RuntimeError("connection refused")

    monkeypatch.setattr("backend.routers.stock.httpx.get", _boom)

    pid, vid = make_product()["id"], make_vault()["id"]
    resp = client.post(
        "/api/stock/entries", json={"product_id": pid, "vault_id": vid, "quantity": 1}
    )
    assert resp.status_code == 201
    assert resp.json()["stock_ids"] == []


def test_webhook_empty_response_yields_no_stock_id(client, make_product, make_vault, monkeypatch):
    _set(client, "stock_id_mode", "extern")
    _set(client, "stock_id_webhook_url", "http://printer.local/next")

    class _Resp:
        text = "   "

        def raise_for_status(self):
            return None

    monkeypatch.setattr("backend.routers.stock.httpx.get", lambda *a, **k: _Resp())

    pid, vid = make_product()["id"], make_vault()["id"]
    entry = client.post(
        "/api/stock/entries", json={"product_id": pid, "vault_id": vid, "quantity": 1}
    ).json()
    assert entry["stock_ids"] == []


# ── label auto-print gating ────────────────────────────────────────────────

def test_auto_print_queued_when_enabled_and_printer_set(client, make_product, make_vault, monkeypatch):
    _set(client, "label_auto_print", "1")
    _set(client, "label_printer_ip", "192.168.1.50")

    printed = []
    monkeypatch.setattr(
        "backend.routers.stock._render_and_print",
        lambda *a, **k: printed.append((a, k)),
    )

    pid, vid = make_product()["id"], make_vault()["id"]
    resp = client.post(
        "/api/stock/entries", json={"product_id": pid, "vault_id": vid, "quantity": 1}
    )
    assert resp.status_code == 201
    assert len(printed) == 1


def test_auto_print_skipped_without_printer_ip(client, make_product, make_vault, monkeypatch):
    _set(client, "label_auto_print", "1")

    printed = []
    monkeypatch.setattr(
        "backend.routers.stock._render_and_print", lambda *a, **k: printed.append(1)
    )
    pid, vid = make_product()["id"], make_vault()["id"]
    client.post("/api/stock/entries", json={"product_id": pid, "vault_id": vid, "quantity": 1})
    assert printed == []


def test_auto_print_per_entry_opt_out(client, make_product, make_vault, monkeypatch):
    _set(client, "label_auto_print", "1")
    _set(client, "label_printer_ip", "192.168.1.50")

    printed = []
    monkeypatch.setattr(
        "backend.routers.stock._render_and_print", lambda *a, **k: printed.append(1)
    )
    pid, vid = make_product()["id"], make_vault()["id"]
    resp = client.post(
        "/api/stock/entries",
        json={"product_id": pid, "vault_id": vid, "quantity": 1, "print_label": False},
    )
    assert resp.status_code == 201
    assert printed == []


def test_no_auto_print_when_setting_disabled(client, make_product, make_vault, monkeypatch):
    _set(client, "label_auto_print", "0")
    _set(client, "label_printer_ip", "192.168.1.50")
    printed = []
    monkeypatch.setattr(
        "backend.routers.stock._render_and_print", lambda *a, **k: printed.append(1)
    )
    pid, vid = make_product()["id"], make_vault()["id"]
    client.post("/api/stock/entries", json={"product_id": pid, "vault_id": vid, "quantity": 1})
    assert printed == []


# ── manual label reprint ────────────────────────────────────────────────────

def test_reprint_label_sends_entry_data_to_printer(client, make_stock_entry, monkeypatch):
    _set(client, "label_printer_ip", "192.168.1.50")

    printed = []
    monkeypatch.setattr(
        "backend.routers.stock._render_and_print",
        lambda *a, **k: printed.append(k),
    )

    entry = make_stock_entry(quantity=3)
    resp = client.post(f"/api/stock/entries/{entry['id']}/print-label")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    assert len(printed) == 1
    assert printed[0]["printer_ip"] == "192.168.1.50"
    assert printed[0]["product_name"] == "Cola 0.33"
    assert printed[0]["quantity"] == 3
    assert printed[0]["raise_on_error"] is True


def test_reprint_label_without_printer_ip_returns_400(client, make_stock_entry, monkeypatch):
    printed = []
    monkeypatch.setattr(
        "backend.routers.stock._render_and_print", lambda *a, **k: printed.append(1)
    )
    entry = make_stock_entry()
    resp = client.post(f"/api/stock/entries/{entry['id']}/print-label")
    assert resp.status_code == 400
    assert printed == []


def test_reprint_label_missing_entry_returns_404(client):
    resp = client.post("/api/stock/entries/999999/print-label")
    assert resp.status_code == 404


def test_reprint_label_printer_failure_returns_502(client, make_stock_entry, monkeypatch):
    _set(client, "label_printer_ip", "192.168.1.50")

    def _boom(*_a, **_k):
        raise RuntimeError("printer offline")

    monkeypatch.setattr("backend.routers.stock._render_and_print", _boom)
    entry = make_stock_entry()
    resp = client.post(f"/api/stock/entries/{entry['id']}/print-label")
    assert resp.status_code == 502
