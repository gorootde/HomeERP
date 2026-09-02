"""Coverage for backend/routers/tags.py (the read-only tag index)."""


def test_list_tags_empty(client):
    assert client.get("/api/tags").json() == []


def test_list_tags_aggregates_from_all_owners_sorted(client, make_product, make_vault):
    pid = make_product()["id"]
    vid = make_vault()["id"]
    client.post(f"/api/products/{pid}/tags", json={"name": "zeta"})
    client.post(f"/api/vaults/{vid}/tags", json={"name": "alpha"})
    client.post(f"/api/products/{pid}/tags", json={"name": "mike"})

    names = [t["name"] for t in client.get("/api/tags").json()]
    assert names == ["alpha", "mike", "zeta"]


def test_tag_is_shared_not_duplicated(client, make_product, make_vault):
    pid = make_product()["id"]
    vid = make_vault()["id"]
    client.post(f"/api/products/{pid}/tags", json={"name": "shared"})
    client.post(f"/api/vaults/{vid}/tags", json={"name": "shared"})
    assert [t["name"] for t in client.get("/api/tags").json()] == ["shared"]
