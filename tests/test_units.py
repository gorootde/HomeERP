"""Coverage for backend/routers/units.py."""


def test_list_units_empty(client):
    assert client.get("/api/units").json() == []


def test_unit_crud(client):
    created = client.post("/api/units", json={"name": "Kilogram", "abbreviation": "kg"})
    assert created.status_code == 201
    uid = created.json()["id"]

    assert client.get(f"/api/units/{uid}").json()["name"] == "Kilogram"

    updated = client.put(f"/api/units/{uid}", json={"abbreviation": "kgs"})
    assert updated.status_code == 200
    assert updated.json()["abbreviation"] == "kgs"
    assert updated.json()["name"] == "Kilogram"

    assert client.delete(f"/api/units/{uid}").status_code == 204
    assert client.get(f"/api/units/{uid}").status_code == 404


def test_units_sorted_by_name(client, make_unit):
    make_unit(name="Zeta", abbreviation="z")
    make_unit(name="Alpha", abbreviation="a")
    names = [u["name"] for u in client.get("/api/units").json()]
    assert names == sorted(names)


def test_create_unit_duplicate_name(client, make_unit):
    make_unit(name="Litre", abbreviation="l")
    resp = client.post("/api/units", json={"name": "Litre", "abbreviation": "L2"})
    assert resp.status_code == 400


def test_create_unit_duplicate_abbreviation(client, make_unit):
    make_unit(name="Litre", abbreviation="l")
    resp = client.post("/api/units", json={"name": "Liter2", "abbreviation": "l"})
    assert resp.status_code == 400


def test_unit_missing_404(client):
    assert client.get("/api/units/999").status_code == 404
    assert client.put("/api/units/999", json={"name": "x"}).status_code == 404
    assert client.delete("/api/units/999").status_code == 404


# ── conversions ────────────────────────────────────────────────────────────

def test_add_conversion_creates_reverse(client, make_unit):
    litre = make_unit(name="Litre", abbreviation="l")
    ml = make_unit(name="Millilitre", abbreviation="ml")

    resp = client.post(
        f"/api/units/{litre['id']}/conversions",
        json={"to_unit_id": ml["id"], "factor": 1000},
    )
    assert resp.status_code == 201
    assert resp.json()["factor"] == 1000
    assert resp.json()["to_unit"]["id"] == ml["id"]

    # reverse conversion is auto-created on the other unit
    ml_detail = client.get(f"/api/units/{ml['id']}").json()
    rev = [c for c in ml_detail["conversions"] if c["to_unit"]["id"] == litre["id"]]
    assert rev and rev[0]["factor"] == 0.001


def test_add_conversion_upserts_existing(client, make_unit):
    a = make_unit(name="A", abbreviation="a")
    b = make_unit(name="B", abbreviation="b")
    client.post(f"/api/units/{a['id']}/conversions", json={"to_unit_id": b["id"], "factor": 2})
    client.post(f"/api/units/{a['id']}/conversions", json={"to_unit_id": b["id"], "factor": 5})

    conv = client.get(f"/api/units/{a['id']}").json()["conversions"]
    assert len(conv) == 1
    assert conv[0]["factor"] == 5


def test_conversion_to_self_rejected(client, make_unit):
    u = make_unit()
    resp = client.post(
        f"/api/units/{u['id']}/conversions",
        json={"to_unit_id": u["id"], "factor": 2},
    )
    assert resp.status_code == 400


def test_conversion_unknown_units(client, make_unit):
    u = make_unit()
    assert client.post(
        "/api/units/999/conversions", json={"to_unit_id": u["id"], "factor": 2}
    ).status_code == 404
    assert client.post(
        f"/api/units/{u['id']}/conversions", json={"to_unit_id": 999, "factor": 2}
    ).status_code == 404


def test_conversion_factor_must_be_positive(client, make_unit):
    a = make_unit(name="A", abbreviation="a")
    b = make_unit(name="B", abbreviation="b")
    resp = client.post(
        f"/api/units/{a['id']}/conversions",
        json={"to_unit_id": b["id"], "factor": 0},
    )
    assert resp.status_code == 422


def test_delete_conversion_removes_reverse(client, make_unit):
    a = make_unit(name="A", abbreviation="a")
    b = make_unit(name="B", abbreviation="b")
    conv = client.post(
        f"/api/units/{a['id']}/conversions",
        json={"to_unit_id": b["id"], "factor": 4},
    ).json()

    assert client.delete(
        f"/api/units/{a['id']}/conversions/{conv['id']}"
    ).status_code == 204
    assert client.get(f"/api/units/{a['id']}").json()["conversions"] == []
    assert client.get(f"/api/units/{b['id']}").json()["conversions"] == []


def test_delete_conversion_404(client, make_unit):
    u = make_unit()
    assert client.delete(
        f"/api/units/{u['id']}/conversions/123"
    ).status_code == 404
