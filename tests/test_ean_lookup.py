"""Coverage for backend/routers/ean_lookup.py.

The router calls OpenFoodFacts over HTTP; ``respx`` stubs the transport so the
real ``_query_openfoodfacts`` parsing logic is exercised end to end.
"""
import httpx
import pytest
import respx

from backend.routers import ean_lookup

# Captured at import time – before conftest's autouse stub replaces it.
_REAL_QUERY = ean_lookup._query_openfoodfacts

OFF_URL = "https://world.openfoodfacts.org/api/v2/product/"


@pytest.fixture()
def real_off(monkeypatch):
    """Restore the genuine OpenFoodFacts lookup for this test."""
    monkeypatch.setattr(
        "backend.routers.ean_lookup._query_openfoodfacts", _REAL_QUERY
    )


@respx.mock
def test_ean_info_found(client, real_off):
    respx.get(url__startswith=OFF_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "status": 1,
                "product": {
                    "product_name_de": "Bio Cola",
                    "brands": "Fritz, Other",
                    "quantity": "0.33 l",
                    "image_front_url": "http://img/cola.jpg",
                },
            },
        )
    )
    body = client.get("/api/ean-info/4001234567890").json()
    assert body == {
        "name": "Bio Cola",
        "vendor": "Fritz",
        "size": "0.33 l",
        "image_url": "http://img/cola.jpg",
        "source": "openfoodfacts",
    }


@respx.mock
def test_ean_info_falls_back_to_english_name(client, real_off):
    respx.get(url__startswith=OFF_URL).mock(
        return_value=httpx.Response(
            200,
            json={"status": 1, "product": {"product_name_en": "Cola", "brands": ""}},
        )
    )
    body = client.get("/api/ean-info/1").json()
    assert body["name"] == "Cola"
    assert body["vendor"] is None


@respx.mock
def test_ean_info_not_found_returns_empty_result(client, real_off):
    respx.get(url__startswith=OFF_URL).mock(
        return_value=httpx.Response(200, json={"status": 0})
    )
    assert client.get("/api/ean-info/0000").json() == {
        "name": None,
        "vendor": None,
        "size": None,
        "image_url": None,
        "source": None,
    }


@respx.mock
def test_ean_info_upstream_http_error_is_swallowed(client, real_off):
    respx.get(url__startswith=OFF_URL).mock(return_value=httpx.Response(500))
    assert client.get("/api/ean-info/1").json()["source"] is None


@respx.mock
def test_ean_info_upstream_connection_error_is_swallowed(client, real_off):
    respx.get(url__startswith=OFF_URL).mock(side_effect=httpx.ConnectError("boom"))
    assert client.get("/api/ean-info/1").json()["source"] is None


def test_ean_info_default_stub_returns_empty(client):
    """With the conftest stub in place the endpoint still answers 200 / empty."""
    assert client.get("/api/ean-info/12345").json()["source"] is None


@respx.mock
def test_ean_info_uses_generic_product_name_when_no_language_variant(client, real_off):
    respx.get(url__startswith=OFF_URL).mock(
        return_value=httpx.Response(
            200, json={"status": 1, "product": {"product_name": "Cola", "brands": ""}}
        )
    )
    assert client.get("/api/ean-info/1").json()["name"] == "Cola"


@respx.mock
def test_ean_info_falls_back_to_image_url_when_no_front_image(client, real_off):
    respx.get(url__startswith=OFF_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "status": 1,
                "product": {"product_name": "Cola", "image_url": "http://img/cola.jpg"},
            },
        )
    )
    assert client.get("/api/ean-info/1").json()["image_url"] == "http://img/cola.jpg"


@respx.mock
def test_ean_info_malformed_upstream_body_is_swallowed(client, real_off):
    respx.get(url__startswith=OFF_URL).mock(
        return_value=httpx.Response(200, content=b"not json")
    )
    assert client.get("/api/ean-info/1").json()["source"] is None
