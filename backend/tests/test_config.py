from app.core.config import Settings


def test_postgresql_url_uses_psycopg_driver() -> None:
    settings = Settings(database_url="postgresql://user:pass@db.example/idp")
    assert settings.database_url == "postgresql+psycopg://user:pass@db.example/idp"


def test_render_legacy_postgres_url_uses_psycopg_driver() -> None:
    settings = Settings(database_url="postgres://user:pass@db.example/idp")
    assert settings.database_url == "postgresql+psycopg://user:pass@db.example/idp"
