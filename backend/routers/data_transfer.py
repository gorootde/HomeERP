import io
import json
import os
import tempfile
import uuid
import zipfile
from datetime import date
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import Date as SADate
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import Session

from ..database import Base, get_db

export_router = APIRouter()
import_router = APIRouter()

# In-memory map of pending import sessions: {import_id: temp_file_path}
_pending_imports: dict[str, str] = {}


# ── Shared helpers ────────────────────────────────────────────────────────────

def _get_model_map() -> dict:
    """Return {tablename: model_class} for all mapped ORM models.
    New models added to models.py are picked up automatically."""
    return {
        mapper.class_.__tablename__: mapper.class_
        for mapper in Base.registry.mappers
    }


def _sorted_table_names() -> list[str]:
    """Table names in topological order (parents before children)."""
    return [t.name for t in Base.metadata.sorted_tables]


def _row_to_dict(instance) -> dict:
    result = {}
    for attr in sa_inspect(instance).mapper.column_attrs:
        val = getattr(instance, attr.key)
        if hasattr(val, 'isoformat'):
            val = val.isoformat()
        result[attr.key] = val
    return result


def _coerce_row(cls, row_data: dict) -> dict:
    """Coerce values from the JSON payload to the correct Python types."""
    mapper = sa_inspect(cls)
    col_types = {ca.key: ca.columns[0].type for ca in mapper.column_attrs}
    result = {}
    for key, val in row_data.items():
        if val is None:
            result[key] = None
        elif key in col_types and isinstance(col_types[key], SADate):
            result[key] = date.fromisoformat(val) if isinstance(val, str) else val
        else:
            result[key] = val
    return result


def _parse_zip(zip_path: str) -> dict[str, list[dict]]:
    """Read a ZIP and return {table_name: [row_dicts]} for every .json entry."""
    result = {}
    with zipfile.ZipFile(zip_path, 'r') as zf:
        for name in zf.namelist():
            if not name.endswith('.json'):
                continue
            table_name = name[:-5]  # strip .json
            raw = zf.read(name).decode('utf-8')
            rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
            result[table_name] = rows
    return result


# ── Export ────────────────────────────────────────────────────────────────────

@export_router.get("/models")
def list_exportable_models(db: Session = Depends(get_db)):
    model_map = _get_model_map()
    result = []
    for table_name, cls in sorted(model_map.items()):
        count = db.query(cls).count()
        result.append({
            "table_name": table_name,
            "display_name": table_name.replace('_', ' ').title(),
            "row_count": count,
        })
    return result


class ExportRequest(BaseModel):
    tables: List[str]


@export_router.post("")
def export_data(req: ExportRequest, db: Session = Depends(get_db)):
    model_map = _get_model_map()

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for table_name in req.tables:
            cls = model_map.get(table_name)
            if cls is None:
                continue
            rows = db.query(cls).all()
            lines = '\n'.join(json.dumps(_row_to_dict(r), ensure_ascii=False) for r in rows)
            zf.writestr(f"{table_name}.json", lines)

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=homeerp_export.zip"},
    )


# ── Import ────────────────────────────────────────────────────────────────────

@import_router.post("/preview")
async def import_preview(file: UploadFile = File(...)):
    """Upload a ZIP, parse its contents and return a row-count preview.
    The file is kept in a temp location until /apply is called."""
    if not (file.filename or '').lower().endswith('.zip'):
        raise HTTPException(status_code=400, detail="Only ZIP files are accepted.")

    fd, tmp_path = tempfile.mkstemp(suffix='.zip', prefix='homeerp_import_')
    try:
        os.close(fd)
        content = await file.read()
        with open(tmp_path, 'wb') as f:
            f.write(content)
        table_data = _parse_zip(tmp_path)
    except HTTPException:
        raise
    except Exception as e:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise HTTPException(status_code=400, detail=f"Could not read ZIP: {e}")

    model_map = _get_model_map()
    import_id = str(uuid.uuid4())
    _pending_imports[import_id] = tmp_path

    preview = [
        {
            "table_name": table_name,
            "display_name": table_name.replace('_', ' ').title(),
            "row_count": len(rows),
            "known": table_name in model_map,
        }
        for table_name, rows in sorted(table_data.items())
    ]

    return {"import_id": import_id, "preview": preview}


@import_router.post("/apply/{import_id}")
def import_apply(import_id: str, db: Session = Depends(get_db)):
    """Apply a previously previewed import. The temp file is deleted afterwards."""
    tmp_path = _pending_imports.pop(import_id, None)
    if not tmp_path or not os.path.exists(tmp_path):
        raise HTTPException(status_code=404, detail="Import session not found or expired.")

    try:
        table_data = _parse_zip(tmp_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read import file: {e}")
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    model_map = _get_model_map()
    ordered_names = _sorted_table_names()

    # Process known tables in topological order; unknown tables are reported as skipped
    known_ordered = [t for t in ordered_names if t in table_data and t in model_map]
    unknown = [t for t in sorted(table_data) if t not in model_map]

    results = []

    for table_name in known_ordered:
        rows = table_data[table_name]
        cls = model_map[table_name]
        imported = 0
        error_msg = None
        try:
            with db.begin_nested():
                for row_data in rows:
                    coerced = _coerce_row(cls, row_data)
                    db.merge(cls(**coerced))
                    imported += 1
        except Exception as e:
            error_msg = str(e)
            imported = 0

        results.append({
            "table_name": table_name,
            "display_name": table_name.replace('_', ' ').title(),
            "imported": imported,
            "total": len(rows),
            "error": error_msg,
        })

    for table_name in unknown:
        results.append({
            "table_name": table_name,
            "display_name": table_name.replace('_', ' ').title(),
            "imported": 0,
            "total": len(table_data[table_name]),
            "error": "unknown_table",
        })

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Commit failed: {e}")

    return {"results": results}
