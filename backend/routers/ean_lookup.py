import logging
from typing import Optional

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


class EanInfoResult(BaseModel):
    name:       Optional[str] = None
    vendor:     Optional[str] = None
    size:       Optional[str] = None
    image_url:  Optional[str] = None
    source:     Optional[str] = None  # which provider matched, None if nothing found
    # Extra signals for auto-selecting the product's unit (see routers/units.py:suggest_unit).
    categories: list[str] = []        # raw OpenFoodFacts categories_tags
    size_value: Optional[float] = None  # normalised net amount (in size_unit)
    size_unit:  Optional[str] = None    # 'g' or 'ml' as reported by OpenFoodFacts


def _to_float(value) -> Optional[float]:
    try:
        return float(str(value).replace(",", ".")) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


async def _query_openfoodfacts(barcode: str) -> Optional[EanInfoResult]:
    fields = (
        "product_name,product_name_de,product_name_en,brands,quantity,"
        "image_front_url,image_url,categories_tags,product_quantity,product_quantity_unit"
    )
    url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}?fields={fields}"
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.get(url, headers={"User-Agent": "HomeERP/1.0"})
        if resp.status_code != 200:
            return None
        data = resp.json()
        if data.get("status") != 1 or not data.get("product"):
            return None
        p = data["product"]
        name   = p.get("product_name_de") or p.get("product_name") or p.get("product_name_en") or None
        brands = p.get("brands", "")
        vendor = brands.split(",")[0].strip() if brands else None
        return EanInfoResult(
            name=name or None,
            vendor=vendor or None,
            size=p.get("quantity") or None,
            image_url=p.get("image_front_url") or p.get("image_url") or None,
            source="openfoodfacts",
            categories=p.get("categories_tags") or [],
            size_value=_to_float(p.get("product_quantity")),
            size_unit=p.get("product_quantity_unit") or None,
        )
    except Exception:
        # Must fail soft (see CLAUDE.md) — but still log it so a broken
        # provider integration doesn't fail silently forever.
        logger.warning("OpenFoodFacts lookup failed for barcode %s", barcode, exc_info=True)
        return None


@router.get("/{barcode}", response_model=EanInfoResult)
async def get_ean_info(barcode: str):
    """Look up product information for an EAN/barcode from external sources.
    Returns an empty result (all fields null) when nothing is found — never 404.
    Currently backed by OpenFoodFacts; additional sources can be added here later.
    """
    result = await _query_openfoodfacts(barcode)
    return result or EanInfoResult()
