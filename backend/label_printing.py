"""Label rendering (PNG) and IPP printing for stock-entry labels.

The exact same PNG produced by :func:`render_label_png` is used both for the
settings preview and for the actual print job sent to the IPP printer.

Geometry note: ``width_mm`` is the physical tape width (fixed by the roll you
buy – Brother QL, DYMO, …), picked from :data:`WIDTH_CHOICES_MM`. The feed
length is either computed from the content (``length_mode="auto"``, keeps
endless tape usage minimal) or taken from ``length_mm`` (``"fixed"``, for
die-cut labels). ``orientation`` picks the text/QR arrangement.
"""
from __future__ import annotations

import asyncio
import io
from datetime import date
from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageFont
from pyipp import IPP
from pyipp.enums import IppOperation
from pyipp.exceptions import IPPError

try:  # optional – only used to make error messages readable
    from pyipp.enums import IppStatus
except Exception:  # pragma: no cover
    IppStatus = None  # type: ignore[assignment]

_IPP_DOCUMENT_FORMAT_NOT_SUPPORTED = 0x040A  # 1034
# Transient printer states worth retrying: temporary-error, not-accepting-jobs, busy.
_IPP_TRANSIENT_STATUS = {0x0505, 0x0506, 0x0507}

DPI = 300

# Common continuous-tape widths (mm) for Brother QL / DYMO and similar printers.
WIDTH_CHOICES_MM = [12, 19, 29, 38, 50, 54, 62, 102]

ORIENTATION_LANDSCAPE = "landscape"          # compact: text left, QR right
ORIENTATION_COMPACT_QTY = "compact_qty"      # like landscape + quantity on the MHD line
ORIENTATION_PORTRAIT = "portrait"            # text on top, large QR below
ORIENTATION_CHOICES = [ORIENTATION_LANDSCAPE, ORIENTATION_COMPACT_QTY, ORIENTATION_PORTRAIT]

LENGTH_MODE_AUTO = "auto"
LENGTH_MODE_FIXED = "fixed"
LENGTH_MODE_CHOICES = [LENGTH_MODE_AUTO, LENGTH_MODE_FIXED]

PROTOCOL_IPP = "ipp"
PROTOCOL_BROTHER_QL = "brother_ql"       # raw Brother raster over TCP :9100
PROTOCOL_CHOICES = [PROTOCOL_IPP, PROTOCOL_BROTHER_QL]

DEFAULT_WIDTH_MM = 62
DEFAULT_LENGTH_MM = 90
DEFAULT_ORIENTATION = ORIENTATION_LANDSCAPE
DEFAULT_LENGTH_MODE = LENGTH_MODE_AUTO
DEFAULT_PROTOCOL = PROTOCOL_IPP
DEFAULT_BROTHER_MODEL = "QL-710W"

# Printable dot width per Brother endless-tape label id (across the tape).
_BROTHER_ENDLESS = {12: ("12", 106), 29: ("29", 306), 38: ("38", 413),
                    50: ("50", 554), 54: ("54", 590), 62: ("62", 696),
                    102: ("102", 1164)}

# Font candidates in preference order. DejaVu (Linux, installed via
# ``fonts-dejavu-core`` in the Docker image) and Arial (macOS dev machines)
# both cover the Latin-1 umlauts the built-in Pillow font lacks.
_REGULAR_FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
]
_BOLD_FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
]


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    for candidate in _BOLD_FONTS if bold else _REGULAR_FONTS:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    # Fallback: Pillow's scalable built-in font (ASCII-only glyph coverage).
    return ImageFont.load_default(size=size)


def _mm_to_px(mm: float) -> int:
    return max(1, round(mm / 25.4 * DPI))


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int):
    """Word-wrap ``text`` to ``max_width`` (unbounded line count).

    Returns ``(wrapped_text, had_hard_break)``. A single word that is wider than
    ``max_width`` is hyphen-broken as a last resort (``had_hard_break`` = True)
    so long product / vendor names never overflow the column.
    """
    max_width = max(1, max_width)
    out: list[str] = []
    cur = ""
    broke = False
    for word in (text or "").split():
        while draw.textlength(word, font=font) > max_width and len(word) > 1:
            broke = True
            lo, hi, best = 1, len(word) - 1, 1
            while lo <= hi:
                mid = (lo + hi) // 2
                if draw.textlength(word[:mid] + "-", font=font) <= max_width:
                    best, lo = mid, mid + 1
                else:
                    hi = mid - 1
            if cur:
                out.append(cur)
                cur = ""
            out.append(word[:best] + "-")
            word = word[best:]
        cand = f"{cur} {word}".strip()
        if not cur or draw.textlength(cand, font=font) <= max_width:
            cur = cand
        else:
            out.append(cur)
            cur = word
    if cur:
        out.append(cur)
    return "\n".join(out), broke


def _block_bottom(draw: ImageDraw.ImageDraw, top: int, wrapped: str, font, spacing: int) -> int:
    """Y of the bottom edge of a multiline block drawn with its top at ``top``."""
    if not wrapped:
        return top
    return draw.multiline_textbbox((0, top), wrapped, font=font, spacing=spacing)[3]


def _draw_text_block(draw, x, top, name_w, vendor_w, qty_w, mhd_w, tf, bf, mf, spacing, vendor_gap) -> int:
    """Draw name / vendor / quantity / MHD stacked from ``top``; return the y below them.

    ``vendor_gap`` is the vertical gap between the name and the vendor, and
    between the vendor and the quantity (kept tight in the compact layout);
    the quantity shares the vendor's font (``bf``) so it reads as part of the
    same line group. ``mf`` is the MHD font (may be larger/bold).
    """
    y = top
    draw.multiline_text((x, y), name_w, font=tf, fill="black", spacing=spacing)
    y = _block_bottom(draw, y, name_w, tf, spacing)
    if vendor_w:
        y += vendor_gap
        draw.multiline_text((x, y), vendor_w, font=bf, fill="black", spacing=spacing)
        y = _block_bottom(draw, y, vendor_w, bf, spacing)
    if qty_w:
        y += vendor_gap
        draw.multiline_text((x, y), qty_w, font=bf, fill="black", spacing=spacing)
        y = _block_bottom(draw, y, qty_w, bf, spacing)
    if mhd_w:
        y += spacing
        draw.multiline_text((x, y), mhd_w, font=mf, fill="black", spacing=spacing)
        y = _block_bottom(draw, y, mhd_w, mf, spacing)
    return y


def _measure(draw, name_w, vendor_w, qty_w, mhd_w, tf, bf, mf, spacing, vendor_gap) -> int:
    """Total height of the name / vendor / quantity / MHD text block."""
    y = _block_bottom(draw, 0, name_w, tf, spacing)
    if vendor_w:
        y = _block_bottom(draw, y + vendor_gap, vendor_w, bf, spacing)
    if qty_w:
        y = _block_bottom(draw, y + vendor_gap, qty_w, bf, spacing)
    if mhd_w:
        y = _block_bottom(draw, y + spacing, mhd_w, mf, spacing)
    return y


def _fit_text(draw, name, vendor, qty_text, mhd_text, col_w, avail_h,
              title_size, body_size, spacing, min_title, min_body,
              *, mhd_scale=1.0, mhd_bold=False, vendor_gap=None):
    """Wrap name/vendor/quantity/MHD to ``col_w``; shrink the fonts
    (proportionally, down to the minimums) until nothing is hyphen-broken and
    the block fits ``avail_h`` (``None`` = no height limit).

    The quantity is set in the vendor's own font/size (``bf``) so it visually
    matches the manufacturer line it sits under. ``mhd_scale`` / ``mhd_bold``
    size the MHD relative to the body font; ``vendor_gap`` overrides the
    name→vendor and vendor→quantity gap (defaults to ``spacing``).

    Returns ``(title_font, body_font, mhd_font, name_w, vendor_w, qty_w,
    mhd_w, block_height, ok)`` – ``ok`` is False only if even the minimum
    fonts could not avoid a hyphen-break or an overflow.
    """
    col_w = max(1, col_w)
    vg = spacing if vendor_gap is None else vendor_gap
    t, b = title_size, body_size
    while True:
        tf = _font(t, bold=True)
        bf = _font(b, bold=False)
        mf = _font(max(min_body, round(b * mhd_scale)), bold=mhd_bold)
        name_w, nb = _wrap(draw, name or "", tf, col_w)
        vendor_w, vb = _wrap(draw, vendor or "", bf, col_w)
        qty_w, qb = _wrap(draw, qty_text or "", bf, col_w)
        mhd_w, mb = _wrap(draw, mhd_text or "", mf, col_w)
        h = _measure(draw, name_w, vendor_w, qty_w, mhd_w, tf, bf, mf, spacing, vg)
        fits = (not nb and not vb and not qb and not mb) and (avail_h is None or h <= avail_h)
        if fits:
            return tf, bf, mf, name_w, vendor_w, qty_w, mhd_w, h, True
        if t <= min_title and b <= min_body:
            return tf, bf, mf, name_w, vendor_w, qty_w, mhd_w, h, False
        t = max(min_title, int(t * 0.9))
        b = max(min_body, int(b * 0.9))


def _format_mhd(best_before: str | None) -> str | None:
    if not best_before:
        return None
    try:
        return date.fromisoformat(best_before).strftime("%d.%m.%Y")
    except ValueError:
        return best_before


def _format_qty(quantity: float | None, unit: str) -> str:
    if quantity is None:
        return ""
    n = f"{quantity:g}".replace(".", ",")
    return f"{n} {unit}".strip()


def _make_qr(data: str, size: int) -> Image.Image:
    qr = qrcode.QRCode(border=1, box_size=10)
    qr.add_data(data)
    qr.make(fit=True)
    im = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    return im.resize((size, size), Image.NEAREST)


_TINY_CAPTION_MM = 1.3  # deliberately smaller than any other label text


def _qr_block(data: str, qr_size: int) -> Image.Image:
    """The QR code with the inventory number it encodes printed tiny underneath."""
    qr_img = _make_qr(data, qr_size)
    font = _font(_mm_to_px(_TINY_CAPTION_MM))
    probe = ImageDraw.Draw(Image.new("RGB", (4, 4), "white"))
    wrapped, _ = _wrap(probe, data, font, qr_size)
    gap = max(1, round(qr_size * 0.02))
    bbox = probe.multiline_textbbox((0, 0), wrapped, font=font, align="center")
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    block = Image.new("RGB", (qr_size, qr_size + gap + text_h), "white")
    block.paste(qr_img, (0, 0))
    bd = ImageDraw.Draw(block)
    bd.multiline_text(((qr_size - text_w) // 2, qr_size + gap - bbox[1]), wrapped,
                       font=font, fill="black", align="center")
    return block


def render_label_png(
    product_name: str,
    vendor: str,
    best_before: str | None,
    stock_id_code: str | None,
    width_mm: float = DEFAULT_WIDTH_MM,
    length_mm: float = DEFAULT_LENGTH_MM,
    orientation: str = DEFAULT_ORIENTATION,
    length_mode: str = DEFAULT_LENGTH_MODE,
    quantity: float | None = None,
    unit: str = "",
) -> bytes:
    """Render a stock-entry label and return it as PNG bytes.

    ``width_mm`` is the physical tape width (fixed). ``length_mode`` is
    ``"auto"`` – the feed length is computed from the content so the endless
    tape is used as sparingly as possible – or ``"fixed"``, in which case
    ``length_mm`` is used verbatim (for die-cut labels).

    The tape width is always the image width. ``length_mode="auto"`` shrinks the
    feed length (image height) to the content, ``"fixed"`` uses ``length_mm``.

    ``orientation="landscape"`` places the product text (name bold, vendor, MHD)
    left-aligned and the QR right-aligned on the same level – this packs a full
    label into very little feed length. ``"compact_qty"`` is identical but also
    prints ``quantity``/``unit`` on its own line right under the vendor, in the
    vendor's font size and weight. ``"portrait"`` stacks the text on top with a
    larger QR centered below. Long names/vendors wrap at word boundaries; the
    font is only shrunk when a single word still would not fit. Without a
    ``stock_id_code`` the QR is dropped.
    """
    width_mm = _clamp(width_mm, 10, 210)
    length_mm = _clamp(length_mm, 15, 500)
    orient = str(orientation).lower()
    portrait = orient == ORIENTATION_PORTRAIT
    with_qty = orient == ORIENTATION_COMPACT_QTY
    auto = str(length_mode).lower() != LENGTH_MODE_FIXED
    has_qr = bool(stock_id_code)

    tape_px = _mm_to_px(width_mm)
    img_w = tape_px
    mx = max(8, round(tape_px * 0.035))       # margin along the tape width
    my = max(4, round(tape_px * 0.018))       # margin along the feed length
    inner = img_w - 2 * mx
    fixed_h = _mm_to_px(length_mm)

    mhd = _format_mhd(best_before)
    mhd_text = f"MHD: {mhd}" if mhd else ""
    qty_text = _format_qty(quantity, unit) if with_qty else ""

    probe = ImageDraw.Draw(Image.new("RGB", (4, 4), "white"))

    if portrait:
        # Text spans the full width, a large QR is centered below it.
        gap = max(4, round(inner * 0.04))
        title_base = int(_clamp(round(inner * 0.13), 18, 42))
        body_base = int(_clamp(round(inner * 0.095), 15, 30))
        qr_size = 0
        qr_img = None
        if has_qr:
            qr_size = min(inner, _mm_to_px(40) if auto else round(fixed_h * 0.55))
            qr_img = _qr_block(stock_id_code, qr_size)
        qr_h = qr_img.size[1] if qr_img else 0
        avail = None if auto else max(1, fixed_h - 2 * my - (gap + qr_h if qr_h else 0))
        tf, bf, mf, name_w, vendor_w, qty_w, mhd_w, block_h, _ = _fit_text(
            probe, product_name, vendor, qty_text, mhd_text, inner, avail,
            title_base, body_base, gap, _mm_to_px(2.3), _mm_to_px(1.9),
        )
        img_h = max(my * 2 + block_h + (gap + qr_h if qr_h else 0), _mm_to_px(10)) if auto else fixed_h

        img = Image.new("RGB", (img_w, img_h), "white")
        draw = ImageDraw.Draw(img)
        y = _draw_text_block(draw, mx, my, name_w, vendor_w, qty_w, mhd_w, tf, bf, mf, gap, gap)
        if qr_img is not None:
            top = y + gap
            qw, qh = qr_img.size
            img.paste(qr_img, ((img_w - qw) // 2, top + max(0, (img_h - my - top - qh) // 2)))
    else:
        # Landscape: text left, QR right, both on the same level. The feed
        # length only needs to cover max(text-block height, QR size).
        gap = max(6, round(tape_px * 0.03))
        title_base = int(_clamp(round(inner * 0.05), 20, 40))
        body_base = int(_clamp(round(inner * 0.039), 16, 30))
        min_t, min_b = _mm_to_px(1.9), _mm_to_px(1.6)
        # The vendor sits tight under the name; the MHD is printed larger and
        # bold so it stays readable from a distance.
        vendor_gap = max(2, round(body_base * 0.12))

        def fit_left(col_w, avail_h):
            return _fit_text(probe, product_name, vendor, qty_text, mhd_text, max(1, col_w), avail_h,
                             title_base, body_base, gap, min_t, min_b,
                             mhd_scale=1.45, mhd_bold=True, vendor_gap=vendor_gap)

        if auto:
            qr_size = int(_clamp(round(inner * 0.20), _mm_to_px(10), round(inner * 0.42))) if has_qr else 0
            tf, bf, mf, name_w, vendor_w, qty_w, mhd_w, block_h, _ = fit_left(
                inner - (qr_size + gap if qr_size else 0), None)
            if has_qr:
                qr_size = int(_clamp(block_h, _mm_to_px(10), round(inner * 0.45)))
                tf, bf, mf, name_w, vendor_w, qty_w, mhd_w, block_h, _ = fit_left(inner - qr_size - gap, None)
            qr_img = _qr_block(stock_id_code, qr_size) if has_qr else None
            qr_h = qr_img.size[1] if qr_img else 0
            content_h = max(block_h, qr_h)
            img_h = max(my * 2 + content_h, _mm_to_px(8))
        else:
            img_h = fixed_h
            qr_size = min(img_h - 2 * my, round(inner * 0.4)) if has_qr else 0
            qr_size = max(qr_size, 0)
            qr_img = _qr_block(stock_id_code, qr_size) if has_qr and qr_size > 0 else None
            qr_h = qr_img.size[1] if qr_img else 0
            tf, bf, mf, name_w, vendor_w, qty_w, mhd_w, block_h, _ = fit_left(
                inner - (qr_size + gap if qr_size else 0), img_h - 2 * my)
            content_h = max(block_h, qr_h, img_h - 2 * my)

        img = Image.new("RGB", (img_w, img_h), "white")
        draw = ImageDraw.Draw(img)
        band_top = my + max(0, (img_h - 2 * my - content_h) // 2)
        _draw_text_block(draw, mx, band_top + max(0, (content_h - block_h) // 2),
                         name_w, vendor_w, qty_w, mhd_w, tf, bf, mf, gap, vendor_gap)
        if qr_img is not None:
            qw, qh = qr_img.size
            img.paste(qr_img, (img_w - mx - qw, band_top + max(0, (content_h - qh) // 2)))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _png_to_pdf(png_bytes: bytes) -> bytes:
    """Wrap the label PNG in a single-page PDF sized to the label (via DPI)."""
    im = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    buf = io.BytesIO()
    im.save(buf, format="PDF", resolution=DPI)
    return buf.getvalue()


def _png_to_jpeg(png_bytes: bytes) -> bytes:
    im = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=92, dpi=(DPI, DPI))
    return buf.getvalue()


def _status_name(code) -> str:
    if IppStatus is not None:
        try:
            return f"{IppStatus(code).name.lower().replace('_', '-')} ({code})"
        except Exception:
            pass
    return str(code)


def _status_code(exc: Exception):
    if isinstance(exc, IPPError) and len(exc.args) > 1 and isinstance(exc.args[1], dict):
        return exc.args[1].get("status-code")
    return None


async def _printer_attrs(ipp: IPP) -> tuple[set[str], list[str], str]:
    """Best-effort ``(document-format-supported, printer-state-reasons, make_model)``."""
    try:
        resp = await ipp.execute(
            IppOperation.GET_PRINTER_ATTRIBUTES,
            {"operation-attributes-tag": {"requested-attributes": [
                "document-format-supported", "printer-state-reasons", "printer-make-and-model",
            ]}},
        )
    except Exception:
        return set(), [], ""

    formats: set[str] = set()
    reasons: list[str] = []
    make_model: list[str] = []

    def _walk(obj):
        if isinstance(obj, dict):
            for key, val in obj.items():
                items = val if isinstance(val, (list, tuple, set)) else [val]
                if key == "document-format-supported":
                    formats.update(str(v) for v in items)
                elif key == "printer-state-reasons":
                    reasons.extend(str(v) for v in items)
                elif key == "printer-make-and-model":
                    make_model.extend(str(v) for v in items)
                else:
                    _walk(val)
        elif isinstance(obj, (list, tuple)):
            for item in obj:
                _walk(item)

    _walk(resp)
    reasons = [r for r in reasons if r and r != "none"]
    return formats, reasons, (make_model[0] if make_model else "")


async def _print_async(png_bytes: bytes, printer_ip: str) -> None:
    async with IPP(f"ipp://{printer_ip}:631/ipp/print", request_timeout=8) as ipp:
        fmts, reasons, make_model = await _printer_attrs(ipp)

        def _ctx() -> str:
            parts = []
            if make_model:
                parts.append(f"printer: {make_model}")
            parts.append(f"formats: {', '.join(sorted(fmts)) if fmts else 'unknown'}")
            if reasons:
                parts.append(f"state: {', '.join(reasons)}")
            return "; ".join(parts)

        # If the printer's spool is full, sending more jobs only makes it worse.
        if any("spool-area-full" in r for r in reasons):
            raise RuntimeError(
                "Printer spool is full – cancel its pending jobs or power-cycle it, then retry. "
                + _ctx())

        # Pick exactly one document format (don't spray jobs into the spool).
        if not fmts or "application/pdf" in fmts:
            doc_format, data = "application/pdf", _png_to_pdf(png_bytes)
        elif "image/png" in fmts:
            doc_format, data = "image/png", png_bytes
        elif "image/jpeg" in fmts:
            doc_format, data = "image/jpeg", _png_to_jpeg(png_bytes)
        elif "application/octet-stream" in fmts:
            doc_format, data = "application/octet-stream", _png_to_pdf(png_bytes)
        else:
            raise RuntimeError(
                "Printer accepts none of PDF/PNG/JPEG. " + _ctx()
                + ". Raster-only printers (image/urf, image/pwg-raster) are not supported yet.")

        last_err: Exception | None = None
        for attempt in range(2):
            try:
                await ipp.execute(
                    IppOperation.PRINT_JOB,
                    {
                        "operation-attributes-tag": {
                            "requesting-user-name": "HomeERP",
                            "job-name": "Stock label",
                            "document-format": doc_format,
                        },
                        "data": data,
                    },
                )
                return
            except IPPError as exc:
                code = _status_code(exc)
                last_err = exc
                if code is None:
                    raise  # connection / parse error – propagate as-is
                if code in _IPP_TRANSIENT_STATUS and attempt == 0:
                    await asyncio.sleep(3)
                    continue
                raise RuntimeError(f"{_status_name(code)} via {doc_format}; {_ctx()}") from exc

        raise RuntimeError(
            f"{_status_name(_status_code(last_err))} via {doc_format}; {_ctx()}") from last_err


def _brother_label_id(width_mm: float) -> tuple[str, int]:
    key = min(_BROTHER_ENDLESS, key=lambda k: abs(k - width_mm))
    return _BROTHER_ENDLESS[key]


def _print_brother_ql(png_bytes: bytes, printer_ip: str, width_mm: float, model: str) -> None:
    """Send the label to a Brother QL printer as raw raster over TCP :9100.

    Brother QL printers (e.g. QL-710W) do not accept PDF/PNG over IPP – they
    speak their own raster protocol. ``brother_ql`` builds it; we push it over
    the JetDirect port, bypassing the IPP spool entirely.
    """
    from brother_ql.backends.helpers import send
    from brother_ql.conversion import convert
    from brother_ql.raster import BrotherQLRaster

    label_id, dots = _brother_label_id(width_mm)
    im = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    if im.size[0] != dots:  # resize here so brother_ql never hits Image.ANTIALIAS
        im = im.resize((dots, max(1, round(dots / im.size[0] * im.size[1]))), Image.LANCZOS)

    qlr = BrotherQLRaster(model or DEFAULT_BROTHER_MODEL)
    qlr.exception_on_warning = False
    instructions = convert(
        qlr=qlr, images=[im], label=label_id, rotate="0",
        threshold=70.0, dither=False, compress=False, red=False,
        dpi_600=False, hq=True, cut=True,
    )
    target = printer_ip if "://" in printer_ip else f"tcp://{printer_ip}"
    send(instructions=instructions, printer_identifier=target,
         backend_identifier="network", blocking=True)


def print_label(png_bytes: bytes, printer_ip: str, *, protocol: str = DEFAULT_PROTOCOL,
                width_mm: float = DEFAULT_WIDTH_MM, model: str = DEFAULT_BROTHER_MODEL) -> None:
    """Send ``png_bytes`` to ``printer_ip``.

    ``protocol="brother_ql"`` uses raw Brother raster over TCP :9100, otherwise
    IPP. Raises on any failure – the caller decides whether to surface or swallow.
    """
    if str(protocol).lower() == PROTOCOL_BROTHER_QL:
        _print_brother_ql(png_bytes, printer_ip, width_mm, model)
    else:
        asyncio.run(_print_async(png_bytes, printer_ip))


async def _purge_ipp_jobs(printer_ip: str) -> str:
    async with IPP(f"ipp://{printer_ip}:631/ipp/print", request_timeout=8) as ipp:
        for op in (IppOperation.PURGE_JOBS, IppOperation.CANCEL_JOBS):
            try:
                await ipp.execute(op, {"operation-attributes-tag": {
                    "requesting-user-name": "HomeERP", "my-jobs": False, "purge-jobs": True,
                }})
                return op.name
            except Exception:  # noqa: BLE001 – try the next operation
                continue
    raise RuntimeError("Printer accepted neither Purge-Jobs nor Cancel-Jobs")


def clear_print_queue(printer_ip: str) -> str:
    """Best-effort: tell the printer to drop all pending jobs. Returns the op used."""
    return asyncio.run(_purge_ipp_jobs(printer_ip))
