from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Setting
from ..schemas import SettingRead, SettingWrite

router = APIRouter()

# Well-known setting keys
STOCK_ID_MODE        = "stock_id_mode"        # "manual" | "generated" | "extern"
STOCK_ID_PREFIX      = "stock_id_prefix"      # e.g. "INV"
STOCK_ID_COUNTER     = "stock_id_counter"     # last used counter value, e.g. "33"
STOCK_ID_PAD_LENGTH  = "stock_id_pad_length"  # 0 = no padding, else pad to this length
STOCK_ID_WEBHOOK_URL = "stock_id_webhook_url" # URL template called in "extern" mode

LABEL_PRINTER_IP = "label_printer_ip"        # IP / hostname of the label printer
LABEL_PRINTER_PROTOCOL = "label_printer_protocol"  # "ipp" | "brother_ql"
LABEL_PRINTER_MODEL = "label_printer_model"  # brother_ql model, e.g. "QL-710W"
LABEL_AUTO_PRINT = "label_auto_print"    # "1" | "0" – auto-print a label per new stock entry
LABEL_WIDTH_MM   = "label_width_mm"      # tape width in mm (from a fixed choice list)
LABEL_LENGTH_MM  = "label_length_mm"     # cut length along the endless tape, in mm (fixed mode)
LABEL_LENGTH_MODE = "label_length_mode"  # "auto" (fit to content) | "fixed"
LABEL_ORIENTATION = "label_orientation"  # "landscape" | "portrait"

DEFAULTS: dict[str, str] = {
    STOCK_ID_MODE:        "manual",
    STOCK_ID_PREFIX:      "",
    STOCK_ID_COUNTER:     "0",
    STOCK_ID_PAD_LENGTH:  "0",
    STOCK_ID_WEBHOOK_URL: "",
    LABEL_PRINTER_IP:     "",
    LABEL_PRINTER_PROTOCOL: "ipp",
    LABEL_PRINTER_MODEL:  "QL-710W",
    LABEL_AUTO_PRINT:     "0",
    LABEL_WIDTH_MM:       "62",
    LABEL_LENGTH_MM:      "90",
    LABEL_LENGTH_MODE:    "auto",
    LABEL_ORIENTATION:    "landscape",
}


@router.get("", response_model=list[SettingRead])
def list_settings(db: Session = Depends(get_db)):
    stored = {s.key: s.value for s in db.query(Setting).all()}
    # Return defaults merged with stored values
    result = []
    for key, default in DEFAULTS.items():
        result.append(SettingRead(key=key, value=stored.get(key, default)))
    # Also include any extra keys stored but not in DEFAULTS
    for key, value in stored.items():
        if key not in DEFAULTS:
            result.append(SettingRead(key=key, value=value))
    return result


@router.get("/{key}", response_model=SettingRead)
def get_setting(key: str, db: Session = Depends(get_db)):
    setting = db.get(Setting, key)
    value = setting.value if setting else DEFAULTS.get(key, "")
    return SettingRead(key=key, value=value)


@router.put("/{key}", response_model=SettingRead)
def upsert_setting(key: str, data: SettingWrite, db: Session = Depends(get_db)):
    setting = db.get(Setting, key)
    if setting:
        setting.value = data.value
    else:
        setting = Setting(key=key, value=data.value)
        db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting
