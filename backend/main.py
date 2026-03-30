import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .routers import products, vaults, stock, tags, units, categories, app_settings, ean_lookup, data_transfer

app = FastAPI(title="HomeERP", version="1.0.0")

app.include_router(products.router, prefix="/api/products", tags=["products"])
app.include_router(vaults.router, prefix="/api/vaults", tags=["vaults"])
app.include_router(stock.router, prefix="/api/stock", tags=["stock"])
app.include_router(tags.router, prefix="/api/tags", tags=["tags"])
app.include_router(units.router, prefix="/api/units", tags=["units"])
app.include_router(categories.router, prefix="/api/categories", tags=["categories"])
app.include_router(app_settings.router, prefix="/api/settings", tags=["settings"])
app.include_router(ean_lookup.router, prefix="/api/ean-info", tags=["ean-info"])
app.include_router(data_transfer.export_router, prefix="/api/export", tags=["export"])
app.include_router(data_transfer.import_router, prefix="/api/import", tags=["import"])

FRONTEND_DIR = Path(os.getenv("FRONTEND_DIR", str(Path(__file__).parent.parent / "frontend_dist")))
UPLOADS_DIR = Path(os.getenv("UPLOADS_DIR", str(Path(__file__).parent.parent / "uploads")))
UPLOADS_DIR.mkdir(exist_ok=True)

app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

# Serve SvelteKit static assets under /_app
_app_dir = FRONTEND_DIR / "_app"
if _app_dir.exists():
    app.mount("/_app", StaticFiles(directory=str(_app_dir)), name="spa_assets")


@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    raise HTTPException(status_code=404, detail="Frontend not found")
