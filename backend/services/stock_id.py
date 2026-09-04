"""Stock-ID assignment strategies for freshly created stock entries.

Split out of ``routers/stock.py`` (see the refactoring plan, section 2) since
ID generation/webhook dispatch is a distinct responsibility from the plain
CRUD endpoints. Both functions are no-ops unless ``stock_id_mode`` selects
them, so calling both unconditionally after entry creation is safe.
"""
import logging
from urllib.parse import quote

import httpx
from sqlalchemy.orm import Session

from ..models import Setting, StockEntry, StockEntryId
from ..routers.app_settings import (
    STOCK_ID_COUNTER,
    STOCK_ID_MODE,
    STOCK_ID_PAD_LENGTH,
    STOCK_ID_PREFIX,
    STOCK_ID_WEBHOOK_URL,
)
from ..settings_helpers import get_setting

logger = logging.getLogger(__name__)


def apply_generated_stock_id(entry: StockEntry, db: Session) -> None:
    """If mode is 'generated', build an incremental ID and attach it to the entry."""
    if get_setting(db, STOCK_ID_MODE) != "generated":
        return
    prefix     = get_setting(db, STOCK_ID_PREFIX, "")
    counter    = int(get_setting(db, STOCK_ID_COUNTER, "0") or "0")
    pad_length = int(get_setting(db, STOCK_ID_PAD_LENGTH, "0") or "0")

    next_counter = counter + 1
    num_str = str(next_counter).zfill(pad_length) if pad_length > 0 else str(next_counter)
    code = f"{prefix}{num_str}"

    # Persist incremented counter
    setting = db.get(Setting, STOCK_ID_COUNTER)
    if setting:
        setting.value = str(next_counter)
    else:
        db.add(Setting(key=STOCK_ID_COUNTER, value=str(next_counter)))

    db.add(StockEntryId(code=code, stock_entry_id=entry.id))
    db.commit()
    db.refresh(entry)


def apply_webhook_stock_id(entry: StockEntry, db: Session) -> None:
    """If mode is 'extern', call the configured webhook and attach the returned ID."""
    if get_setting(db, STOCK_ID_MODE) != "extern":
        return
    url_template = get_setting(db, STOCK_ID_WEBHOOK_URL)
    if not url_template:
        return

    bbd = entry.best_before_date.isoformat() if entry.best_before_date else ""
    url = (
        url_template
        .replace("{quantity}",         quote(str(entry.quantity)))
        .replace("{product_id}",       quote(str(entry.product_id)))
        .replace("{vault_id}",         quote(str(entry.vault_id)))
        .replace("{best_before_date}", quote(bbd))
        .replace("{comment}",          quote(entry.comment or ""))
    )
    try:
        resp = httpx.get(url, timeout=10.0)
        resp.raise_for_status()
        code = resp.text.strip()
        if code:
            db.add(StockEntryId(code=code, stock_entry_id=entry.id))
            db.commit()
            db.refresh(entry)
    except Exception:
        # Webhook failure must not prevent entry creation (external calls must
        # fail soft, see CLAUDE.md) — but still log it so a broken webhook
        # doesn't fail silently forever.
        logger.warning("Stock-ID webhook call failed for entry %s", entry.id, exc_info=True)
