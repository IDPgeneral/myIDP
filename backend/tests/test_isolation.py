from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.core.security import CredentialResolver, assert_resource_binding
from app.db.models import Product, ProductResource, ProviderAccount


def seed(db):
    milu = Product(name="MILU Software", slug="milu-software", owner="owner", status="unknown")
    color = Product(name="ColorGlass", slug="colorglass", owner="owner", status="unknown")
    db.add_all([milu, color])
    db.flush()
    milu_account = ProviderAccount(provider="render", name="render-milu", product_id=milu.id, credential_ref="RENDER_API_KEY_MILU")
    color_account = ProviderAccount(provider="render", name="render-colorglass", product_id=color.id, credential_ref="RENDER_API_KEY_COLORGLASS")
    db.add_all([milu_account, color_account])
    db.flush()
    resource = ProductResource(product_id=milu.id, provider_account_id=milu_account.id, resource_type="render_service", external_id="srv-placeholder", name="backend", environment="production", metadata_json={})
    db.add(resource)
    db.commit()
    return milu, color, milu_account, color_account, resource


def test_selects_correct_credential_per_product(db, monkeypatch):
    _, _, milu_account, color_account, _ = seed(db)
    monkeypatch.setenv("RENDER_API_KEY_MILU", "milu-key")
    monkeypatch.setenv("RENDER_API_KEY_COLORGLASS", "color-key")
    resolver = CredentialResolver()
    assert resolver.resolve(milu_account) == "milu-key"
    assert resolver.resolve(color_account) == "color-key"


def test_rejects_cross_product_binding(db):
    milu, color, milu_account, color_account, resource = seed(db)
    with pytest.raises(HTTPException):
        assert_resource_binding(db, product_id=str(color.id), provider_account_id=str(color_account.id), resource_id=str(resource.id), environment="production")


def test_resource_bound_to_exact_account(db):
    milu, _, milu_account, _, resource = seed(db)
    account, bound = assert_resource_binding(db, product_id=str(milu.id), provider_account_id=str(milu_account.id), resource_id=str(resource.id), environment="production")
    assert account.id == milu_account.id
    assert bound.id == resource.id
