"""Coverage for backend/routers/label_printing.py (the /api/settings/printing/* API).

``print_label`` / ``clear_print_queue`` are stubbed by the conftest autouse
fixture; individual tests re-stub them to assert behaviour or simulate failure.
"""
import io

from PIL import Image

from backend.label_printing import (
    DEFAULT_ORIENTATION,
    DEFAULT_WIDTH_MM,
    ORIENTATION_CHOICES,
    PROTOCOL_CHOICES,
    WIDTH_CHOICES_MM,
)


def _set(client, key, value):
    client.put(f"/api/settings/{key}", json={"value": value})


# ── /options ───────────────────────────────────────────────────────────────

def test_label_options(client):
    body = client.get("/api/settings/printing/options").json()
    assert body["width_choices_mm"] == WIDTH_CHOICES_MM
    assert body["orientation_choices"] == ORIENTATION_CHOICES
    assert body["protocol_choices"] == PROTOCOL_CHOICES
    assert body["default_width_mm"] == DEFAULT_WIDTH_MM
    assert body["default_orientation"] == DEFAULT_ORIENTATION


# ── /preview ───────────────────────────────────────────────────────────────

def test_label_preview_returns_png(client):
    resp = client.get("/api/settings/printing/preview")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    img = Image.open(io.BytesIO(resp.content))
    assert img.format == "PNG"
    assert img.width > 0 and img.height > 0


def test_label_preview_respects_query_overrides(client):
    landscape = client.get(
        "/api/settings/printing/preview",
        params={"orientation": "landscape", "length_mode": "auto", "width_mm": 62},
    )
    portrait = client.get(
        "/api/settings/printing/preview",
        params={"orientation": "portrait", "length_mode": "auto", "width_mm": 62},
    )
    assert landscape.status_code == portrait.status_code == 200
    # Different layouts render to different byte streams.
    assert landscape.content != portrait.content


def test_label_preview_uses_stored_settings(client):
    _set(client, "label_orientation", "portrait")
    _set(client, "label_width_mm", "29")
    resp = client.get("/api/settings/printing/preview")
    assert resp.status_code == 200


# ── /test-print ────────────────────────────────────────────────────────────

def test_test_print_requires_printer_ip(client):
    resp = client.post("/api/settings/printing/test-print")
    assert resp.status_code == 400
    assert "printer" in resp.json()["detail"].lower()


def test_test_print_ok(client, monkeypatch):
    _set(client, "label_printer_ip", "192.168.1.50")
    sent = {}
    monkeypatch.setattr(
        "backend.routers.label_printing.print_label",
        lambda png, ip, **kw: sent.update(ip=ip, kw=kw, size=len(png)),
    )
    resp = client.post("/api/settings/printing/test-print")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    assert sent["ip"] == "192.168.1.50"
    assert sent["size"] > 0


def test_test_print_surfaces_printer_error_as_502(client, monkeypatch):
    _set(client, "label_printer_ip", "192.168.1.50")

    def _boom(*_a, **_k):
        raise RuntimeError("spool is full")

    monkeypatch.setattr("backend.routers.label_printing.print_label", _boom)
    resp = client.post("/api/settings/printing/test-print")
    assert resp.status_code == 502
    assert "spool is full" in resp.json()["detail"]


# ── /clear-queue ───────────────────────────────────────────────────────────

def test_clear_queue_requires_printer_ip(client):
    assert client.post("/api/settings/printing/clear-queue").status_code == 400


def test_clear_queue_ok(client, monkeypatch):
    _set(client, "label_printer_ip", "192.168.1.50")
    monkeypatch.setattr(
        "backend.routers.label_printing.clear_print_queue", lambda ip: "Purge-Jobs"
    )
    resp = client.post("/api/settings/printing/clear-queue")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "operation": "Purge-Jobs"}


def test_clear_queue_surfaces_error_as_502(client, monkeypatch):
    _set(client, "label_printer_ip", "192.168.1.50")

    def _boom(_ip):
        raise RuntimeError("unreachable")

    monkeypatch.setattr("backend.routers.label_printing.clear_print_queue", _boom)
    resp = client.post("/api/settings/printing/clear-queue")
    assert resp.status_code == 502
