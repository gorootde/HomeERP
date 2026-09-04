from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..helpers import add_tag, get_or_404, remove_tag
from ..models import Vault
from ..schemas import TagCreate, TagRead, VaultCreate, VaultRead, VaultUpdate

router = APIRouter()


@router.get("", response_model=list[VaultRead])
def list_vaults(db: Session = Depends(get_db)):
    return db.query(Vault).all()


@router.post("", response_model=VaultRead, status_code=201)
def create_vault(data: VaultCreate, db: Session = Depends(get_db)):
    vault = Vault(description=data.description)
    db.add(vault)
    db.commit()
    db.refresh(vault)
    return vault


@router.get("/{vault_id}", response_model=VaultRead)
def get_vault(vault_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, Vault, vault_id, "Vault not found")


@router.put("/{vault_id}", response_model=VaultRead)
def update_vault(vault_id: int, data: VaultUpdate, db: Session = Depends(get_db)):
    vault = get_or_404(db, Vault, vault_id, "Vault not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(vault, field, value)
    db.commit()
    db.refresh(vault)
    return vault


@router.delete("/{vault_id}", status_code=204)
def delete_vault(vault_id: int, db: Session = Depends(get_db)):
    vault = get_or_404(db, Vault, vault_id, "Vault not found")
    db.delete(vault)
    db.commit()


@router.post("/{vault_id}/tags", response_model=TagRead, status_code=201)
def add_tag_to_vault(vault_id: int, data: TagCreate, db: Session = Depends(get_db)):
    vault = get_or_404(db, Vault, vault_id, "Vault not found")
    return add_tag(db, vault, data.name)


@router.delete("/{vault_id}/tags/{tag_name}", status_code=204)
def remove_tag_from_vault(vault_id: int, tag_name: str, db: Session = Depends(get_db)):
    vault = get_or_404(db, Vault, vault_id, "Vault not found")
    remove_tag(db, vault, tag_name)
