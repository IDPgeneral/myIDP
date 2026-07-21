from app.core.config import Settings
from app.db.models import Product, ProviderAccount
from app.services.sync import SyncCoordinator


def test_product_sync_continues_after_one_account_failure(db, monkeypatch):
    product = Product(name="MILU", slug="milu", owner="owner", status="unknown")
    db.add(product)
    db.flush()
    first = ProviderAccount(provider="render", name="render-a", product_id=product.id, credential_ref="RENDER_A")
    second = ProviderAccount(provider="render", name="render-b", product_id=product.id, credential_ref="RENDER_B")
    db.add_all([first, second])
    db.commit()

    calls = []
    def fake(self, account):
        calls.append(account.name)
        class Run:
            status = "error" if account.name == "render-a" else "success"
        return Run()

    monkeypatch.setattr(SyncCoordinator, "sync_account", fake)
    run = SyncCoordinator(db, Settings(app_env="test", database_url="sqlite://")).sync_product(product)
    assert calls == ["render-a", "render-b"]
    assert run.status == "partial"
