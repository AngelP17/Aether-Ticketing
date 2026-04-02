from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.api.schemas.management import (
    CategoryCreateRequest,
    CategoryUpdateRequest,
    LabelCreateRequest,
)
from apps.api.security import get_current_user, require_admin
from apps.api.services.catalog_service import CatalogService

router = APIRouter()


@router.get("/categories")
def list_categories(db: Session = Depends(get_db), _: dict = Depends(get_current_user)):
    return CatalogService(db).list_categories(active_only=True)


@router.post("/categories", status_code=201)
def create_category(
    body: CategoryCreateRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    try:
        return CatalogService(db).create_category(body.name, body.color, body.icon)
    except Exception as error:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.put("/categories/{category_id}")
def update_category(
    category_id: int,
    body: CategoryUpdateRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    category = CatalogService(db).update_category(category_id, body.model_dump(exclude_unset=True))
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.delete("/categories/{category_id}")
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    CatalogService(db).delete_category(category_id)
    return {"status": "success"}


@router.get("/labels")
def list_labels(db: Session = Depends(get_db), _: dict = Depends(get_current_user)):
    return CatalogService(db).list_labels()


@router.post("/labels", status_code=201)
def create_label(
    body: LabelCreateRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    try:
        return CatalogService(db).create_label(body.name, body.color)
    except Exception as error:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.delete("/labels/{label_id}")
def delete_label(
    label_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    CatalogService(db).delete_label(label_id)
    return {"status": "success"}


@router.get("/options")
def get_options(db: Session = Depends(get_db), _: dict = Depends(get_current_user)):
    return CatalogService(db).get_options()
