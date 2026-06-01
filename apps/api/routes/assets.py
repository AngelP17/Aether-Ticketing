from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.api.services.asset_service import AssetService

router = APIRouter()


@router.get("/")
def list_assets(db: Session = Depends(get_db)) -> Any:
    service = AssetService(db)
    return service.list_assets()


@router.get("/{asset_id}")
def get_asset(asset_id: int, db: Session = Depends(get_db)) -> Any:
    service = AssetService(db)
    asset = service.get_asset(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset
