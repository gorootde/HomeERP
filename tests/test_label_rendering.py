"""Unit tests for backend/label_printing.py rendering helpers (no I/O)."""
import io

import pytest
from PIL import Image

from backend import label_printing as lp


def _dims(png: bytes):
    img = Image.open(io.BytesIO(png))
    assert img.format == "PNG"
    return img.size


@pytest.mark.parametrize("orientation", lp.ORIENTATION_CHOICES)
def test_render_label_png_all_orientations(orientation):
    png = lp.render_label_png(
        product_name="Beispielprodukt",
        vendor="Beispielhersteller GmbH",
        best_before="2030-01-15",
        stock_id_code="DEMO-0001",
        orientation=orientation,
        quantity=2,
        unit="Stk.",
    )
    w, h = _dims(png)
    assert w > 0 and h > 0


def test_render_without_qr_is_narrower_or_shorter():
    with_qr = lp.render_label_png("Name", "Vendor", "2030-01-01", "CODE-1")
    without_qr = lp.render_label_png("Name", "Vendor", "2030-01-01", None)
    assert with_qr != without_qr


def test_fixed_length_mode_uses_length_mm():
    png = lp.render_label_png(
        "Name", "Vendor", None, None,
        width_mm=62, length_mm=90, length_mode="fixed",
    )
    _w, h = _dims(png)
    # 90 mm @ 300 dpi ≈ 1063 px
    assert abs(h - lp._mm_to_px(90)) <= 2


def test_auto_length_mode_shrinks_below_fixed():
    fixed = _dims(lp.render_label_png("N", "V", None, None, length_mm=90, length_mode="fixed"))
    auto = _dims(lp.render_label_png("N", "V", None, None, length_mm=90, length_mode="auto"))
    assert auto[1] < fixed[1]


def test_width_mm_is_clamped():
    tiny = lp.render_label_png("N", "V", None, None, width_mm=1)
    w, _h = _dims(tiny)
    assert w == lp._mm_to_px(10)  # clamped to the 10 mm floor


def test_format_mhd():
    assert lp._format_mhd("2030-01-15") == "15.01.2030"
    assert lp._format_mhd(None) is None
    assert lp._format_mhd("not-a-date") == "not-a-date"


def test_format_qty():
    assert lp._format_qty(2.5, "l") == "2,5 l"
    assert lp._format_qty(3, "Stk.") == "3 Stk."
    assert lp._format_qty(None, "l") == ""


def test_brother_label_id_picks_nearest_tape():
    assert lp._brother_label_id(62)[0] == "62"
    assert lp._brother_label_id(60)[0] == "62"
    assert lp._brother_label_id(12)[0] == "12"


def test_long_name_still_renders(monkeypatch):
    png = lp.render_label_png(
        "Averyveryverylongsingleproductwordthatcannotwrap " * 3,
        "Averyverylongvendornamehere GmbH & Co KG",
        "2031-12-31",
        "STOCK-999999",
        orientation="portrait",
    )
    assert _dims(png)[0] > 0
