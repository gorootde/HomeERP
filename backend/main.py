import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .routers import products, vaults, stock, tags, units, categories, app_settings, ean_lookup

app = FastAPI(title="HomeERP", version="1.0.0")

app.include_router(products.router, prefix="/api/products", tags=["products"])
app.include_router(vaults.router, prefix="/api/vaults", tags=["vaults"])
app.include_router(stock.router, prefix="/api/stock", tags=["stock"])
app.include_router(tags.router, prefix="/api/tags", tags=["tags"])
app.include_router(units.router, prefix="/api/units", tags=["units"])
app.include_router(categories.router, prefix="/api/categories", tags=["categories"])
app.include_router(app_settings.router, prefix="/api/settings", tags=["settings"])
app.include_router(ean_lookup.router, prefix="/api/ean-info", tags=["ean-info"])

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
UPLOADS_DIR = Path(os.getenv("UPLOADS_DIR", str(Path(__file__).parent.parent / "uploads")))
UPLOADS_DIR.mkdir(exist_ok=True)

app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(FRONTEND_DIR / "index.html")
