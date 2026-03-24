from typing import Optional
import httpx
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class EanInfoResult(BaseModel):
    name:      Optional[str] = None
    vendor:    Optional[str] = None
    size:      Optional[str] = None
    image_url: Optional[str] = None
    source:    Optional[str] = None  # which provider matched, None if nothing found


async def _query_openfoodfacts(barcode: str) -> Optional[EanInfoResult]:
    fields = "product_name,product_name_de,product_name_en,brands,quantity,image_front_url,image_url"
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
        )
    except Exception:
        return None


@router.get("/{barcode}", response_model=EanInfoResult)
async def get_ean_info(barcode: str):
    """Look up product information for an EAN/barcode from external sources.
    Returns an empty result (all fields null) when nothing is found — never 404.
    Currently backed by OpenFoodFacts; additional sources can be added here later.
    """
    result = await _query_openfoodfacts(barcode)
    return result or EanInfoResult()
