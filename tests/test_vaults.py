"""Coverage for backend/routers/vaults.py."""


def test_list_vaults_empty(client):
    assert client.get("/api/vaults").json() == []


def test_vault_crud(client):
    created = client.post("/api/vaults", json={"description": "Cellar"})
    assert created.status_code == 201
    vid = created.json()["id"]

    assert client.get(f"/api/vaults/{vid}").json()["description"] == "Cellar"

    updated = client.put(f"/api/vaults/{vid}", json={"description": "Pantry"})
    assert updated.status_code == 200
    assert updated.json()["description"] == "Pantry"

    assert client.delete(f"/api/vaults/{vid}").status_code == 204
    assert client.get(f"/api/vaults/{vid}").status_code == 404


def test_create_vault_rejects_blank(client):
    assert client.post("/api/vaults", json={"description": ""}).status_code == 422


def test_get_update_delete_missing_vault(client):
    assert client.get("/api/vaults/999").status_code == 404
    assert client.put("/api/vaults/999", json={"description": "x"}).status_code == 404
    assert client.delete("/api/vaults/999").status_code == 404


def test_vault_tags(client, make_vault):
    vid = make_vault()["id"]
    assert client.post(f"/api/vaults/{vid}/tags", json={"name": "cold"}).status_code == 201
    client.post(f"/api/vaults/{vid}/tags", json={"name": "cold"})  # idempotent
    assert [t["name"] for t in client.get(f"/api/vaults/{vid}").json()["tags"]] == ["cold"]

    assert client.delete(f"/api/vaults/{vid}/tags/cold").status_code == 204
    assert client.get(f"/api/vaults/{vid}").json()["tags"] == []


def test_vault_tag_missing_vault(client):
    assert client.post("/api/vaults/999/tags", json={"name": "x"}).status_code == 404
    assert client.delete("/api/vaults/999/tags/x").status_code == 404


def test_deleting_vault_cascades_stock_entries(client, make_stock_entry, make_vault):
    vid = make_vault(description="Temp")["id"]
    entry = make_stock_entry(vault_id=vid)
    assert client.delete(f"/api/vaults/{vid}").status_code == 204
    assert client.get(f"/api/stock/entries/{entry['id']}").status_code == 404
