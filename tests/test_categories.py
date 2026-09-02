"""Coverage for backend/routers/categories.py."""


def test_list_categories_empty(client):
    assert client.get("/api/categories").json() == []


def test_category_crud(client, make_unit):
    unit = make_unit()
    created = client.post(
        "/api/categories",
        json={
            "name": "Beverages",
            "min_stock_quantity": 5,
            "min_stock_unit_id": unit["id"],
        },
    )
    assert created.status_code == 201
    cid = created.json()["id"]
    assert created.json()["min_stock_quantity"] == 5
    assert created.json()["min_stock_unit"]["id"] == unit["id"]

    assert client.get(f"/api/categories/{cid}").json()["name"] == "Beverages"

    updated = client.put(f"/api/categories/{cid}", json={"name": "Drinks"})
    assert updated.status_code == 200
    assert updated.json()["name"] == "Drinks"

    assert client.delete(f"/api/categories/{cid}").status_code == 204
    assert client.get(f"/api/categories/{cid}").status_code == 404


def test_categories_sorted_by_name(client, make_category):
    make_category(name="Zoo")
    make_category(name="Ants")
    names = [c["name"] for c in client.get("/api/categories").json()]
    assert names == sorted(names)


def test_create_category_duplicate_name_conflicts(client, make_category):
    make_category(name="Beverages")
    resp = client.post("/api/categories", json={"name": "Beverages"})
    assert resp.status_code == 409


def test_create_category_rejects_blank_name(client):
    assert client.post("/api/categories", json={"name": ""}).status_code == 422


def test_create_category_rejects_non_positive_min_stock(client):
    resp = client.post(
        "/api/categories", json={"name": "X", "min_stock_quantity": 0}
    )
    assert resp.status_code == 422


def test_category_missing_404(client):
    assert client.get("/api/categories/999").status_code == 404
    assert client.put("/api/categories/999", json={"name": "x"}).status_code == 404
    assert client.delete("/api/categories/999").status_code == 404
