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

DEFAULTS: dict[str, str] = {
    STOCK_ID_MODE:        "manual",
    STOCK_ID_PREFIX:      "",
    STOCK_ID_COUNTER:     "0",
    STOCK_ID_PAD_LENGTH:  "0",
    STOCK_ID_WEBHOOK_URL: "",
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
