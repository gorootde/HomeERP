from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Vault, Tag
from ..schemas import VaultCreate, VaultRead, VaultUpdate, TagCreate, TagRead

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
    vault = db.get(Vault, vault_id)
    if not vault:
        raise HTTPException(status_code=404, detail="Vault not found")
    return vault


@router.put("/{vault_id}", response_model=VaultRead)
def update_vault(vault_id: int, data: VaultUpdate, db: Session = Depends(get_db)):
    vault = db.get(Vault, vault_id)
    if not vault:
        raise HTTPException(status_code=404, detail="Vault not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(vault, field, value)
    db.commit()
    db.refresh(vault)
    return vault


@router.delete("/{vault_id}", status_code=204)
def delete_vault(vault_id: int, db: Session = Depends(get_db)):
    vault = db.get(Vault, vault_id)
    if not vault:
        raise HTTPException(status_code=404, detail="Vault not found")
    db.delete(vault)
    db.commit()


@router.post("/{vault_id}/tags", response_model=TagRead, status_code=201)
def add_tag_to_vault(vault_id: int, data: TagCreate, db: Session = Depends(get_db)):
    vault = db.get(Vault, vault_id)
    if not vault:
        raise HTTPException(status_code=404, detail="Vault not found")
    tag = db.query(Tag).filter(Tag.name == data.name).first()
    if not tag:
        tag = Tag(name=data.name)
        db.add(tag)
        db.flush()
    if tag not in vault.tags:
        vault.tags.append(tag)
    db.commit()
    db.refresh(tag)
    return tag


@router.delete("/{vault_id}/tags/{tag_name}", status_code=204)
def remove_tag_from_vault(vault_id: int, tag_name: str, db: Session = Depends(get_db)):
    vault = db.get(Vault, vault_id)
    if not vault:
        raise HTTPException(status_code=404, detail="Vault not found")
    tag = db.query(Tag).filter(Tag.name == tag_name).first()
    if tag and tag in vault.tags:
        vault.tags.remove(tag)
        db.commit()
