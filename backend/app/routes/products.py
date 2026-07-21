from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, get_current_user, require_roles
from app.db.models import Product, ProductEnvironment, ProductResource, ProviderAccount
from app.db.session import get_db
from app.schemas.common import ProductDetail, ProductOut, ProductResourceOut, ProductSummary, ProviderAccountOut
from app.schemas.inputs import ProductCreate, ProductPatch, ResourceCreate, ResourcePatch
from app.services.audit import audit
from app.services.status import latest_health_results, product_summary, provider_account_dict

router = APIRouter(tags=["products"])


@router.get("/products", response_model=list[ProductSummary])
def list_products(_: Annotated[CurrentUser, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    products = db.scalars(select(Product).order_by(Product.name)).all()
    return [product_summary(db, product) for product in products]


@router.get("/products/{slug}", response_model=ProductDetail)
def get_product(slug: str, _: Annotated[CurrentUser, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    product = db.scalar(select(Product).where(Product.slug == slug))
    if product is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    resources = db.scalars(select(ProductResource).where(ProductResource.product_id == product.id).order_by(ProductResource.resource_type, ProductResource.name)).all()
    accounts = db.scalars(select(ProviderAccount).where(ProviderAccount.product_id == product.id).order_by(ProviderAccount.provider)).all()
    return ProductDetail(
        summary=product_summary(db, product),
        resources=[ProductResourceOut.model_validate(resource) for resource in resources],
        provider_accounts=[ProviderAccountOut.model_validate(provider_account_dict(account)) for account in accounts],
        health_checks=latest_health_results(db, str(product.id)),
    )


@router.post("/products", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, user: Annotated[CurrentUser, Depends(require_roles("admin"))], db: Annotated[Session, Depends(get_db)]):
    if db.scalar(select(Product).where(Product.slug == payload.slug)):
        raise HTTPException(status_code=409, detail="Slug já cadastrado.")
    product = Product(**payload.model_dump(), status="unknown")
    db.add(product)
    db.flush()
    db.add(ProductEnvironment(product_id=product.id, name="production", required=True))
    db.commit()
    db.refresh(product)
    audit(db, action="product.create", user=user, product_id=str(product.id), after_data=payload.model_dump(), success=True)
    return ProductOut.model_validate(product)


@router.patch("/products/{product_id}", response_model=ProductOut)
def patch_product(product_id: str, payload: ProductPatch, user: Annotated[CurrentUser, Depends(require_roles("admin"))], db: Annotated[Session, Depends(get_db)]):
    product = db.get(Product, uuid.UUID(product_id))
    if product is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    before = {"name": product.name, "description": product.description, "status": product.status, "owner": product.owner}
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, key, value)
    db.commit()
    db.refresh(product)
    audit(db, action="product.update", user=user, product_id=product_id, before_data=before, after_data=payload.model_dump(exclude_unset=True), success=True)
    return ProductOut.model_validate(product)


@router.get("/products/{product_id}/resources", response_model=list[ProductResourceOut])
def list_resources(product_id: str, _: Annotated[CurrentUser, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    resources = db.scalars(select(ProductResource).where(ProductResource.product_id == uuid.UUID(product_id))).all()
    return [ProductResourceOut.model_validate(resource) for resource in resources]


@router.post("/products/{product_id}/resources", response_model=ProductResourceOut, status_code=201)
def create_resource(product_id: str, payload: ResourceCreate, user: Annotated[CurrentUser, Depends(require_roles("admin"))], db: Annotated[Session, Depends(get_db)]):
    product = db.get(Product, uuid.UUID(product_id))
    if product is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    account_id = uuid.UUID(payload.provider_account_id) if payload.provider_account_id else None
    if account_id:
        account = db.get(ProviderAccount, account_id)
        if account is None or account.product_id != product.id:
            raise HTTPException(status_code=409, detail="Conta de provedor não pertence ao produto.")
    data = payload.model_dump(exclude={"metadata"})
    data["provider_account_id"] = account_id
    resource = ProductResource(product_id=product.id, metadata_json=payload.metadata, **data)
    db.add(resource)
    db.commit()
    db.refresh(resource)
    audit(db, action="resource.create", user=user, product_id=product_id, provider_account_id=payload.provider_account_id, resource_id=str(resource.id), after_data=payload.model_dump(), success=True)
    return ProductResourceOut.model_validate(resource)


@router.patch("/resources/{resource_id}", response_model=ProductResourceOut)
def patch_resource(resource_id: str, payload: ResourcePatch, user: Annotated[CurrentUser, Depends(require_roles("admin"))], db: Annotated[Session, Depends(get_db)]):
    resource = db.get(ProductResource, uuid.UUID(resource_id))
    if resource is None:
        raise HTTPException(status_code=404, detail="Recurso não encontrado.")
    changes = payload.model_dump(exclude_unset=True)
    metadata = changes.pop("metadata", None)
    for key, value in changes.items():
        setattr(resource, key, value)
    if metadata is not None:
        resource.metadata_json = metadata
    db.commit()
    db.refresh(resource)
    audit(db, action="resource.update", user=user, product_id=str(resource.product_id), provider_account_id=str(resource.provider_account_id) if resource.provider_account_id else None, resource_id=resource_id, after_data=payload.model_dump(exclude_unset=True), success=True)
    return ProductResourceOut.model_validate(resource)
