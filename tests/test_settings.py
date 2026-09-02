"""Coverage for backend/routers/app_settings.py."""
from backend.routers.app_settings import DEFAULTS


def test_list_settings_returns_all_defaults(client):
    body = {s["key"]: s["value"] for s in client.get("/api/settings").json()}
    for key, default in DEFAULTS.items():
        assert body[key] == default


def test_get_unknown_setting_returns_empty_string(client):
    resp = client.get("/api/settings/does_not_exist")
    assert resp.status_code == 200
    assert resp.json() == {"key": "does_not_exist", "value": ""}


def test_get_known_setting_returns_default(client):
    resp = client.get("/api/settings/stock_id_mode")
    assert resp.json()["value"] == "manual"


def test_upsert_setting_insert_then_update(client):
    r1 = client.put("/api/settings/stock_id_prefix", json={"value": "INV-"})
    assert r1.status_code == 200
    assert r1.json()["value"] == "INV-"
    assert client.get("/api/settings/stock_id_prefix").json()["value"] == "INV-"

    r2 = client.put("/api/settings/stock_id_prefix", json={"value": "S-"})
    assert r2.json()["value"] == "S-"
    assert client.get("/api/settings/stock_id_prefix").json()["value"] == "S-"


def test_list_settings_includes_custom_keys(client):
    client.put("/api/settings/my_custom", json={"value": "42"})
    body = {s["key"]: s["value"] for s in client.get("/api/settings").json()}
    assert body["my_custom"] == "42"


def test_upsert_setting_allows_empty_value(client):
    resp = client.put("/api/settings/stock_id_prefix", json={"value": ""})
    assert resp.status_code == 200
    assert resp.json()["value"] == ""


def test_upsert_setting_rejects_overlong_value(client):
    resp = client.put("/api/settings/x", json={"value": "a" * 1025})
    assert resp.status_code == 422
