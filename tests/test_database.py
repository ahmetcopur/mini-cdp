from app.database import sqlalchemy_url


def test_hosted_postgres_urls_use_psycopg_3():
    url = "postgresql://user:secret@ep-example.neon.tech/neondb?sslmode=require"
    assert sqlalchemy_url(url) == "postgresql+psycopg://user:secret@ep-example.neon.tech/neondb?sslmode=require"


def test_other_urls_are_unchanged():
    for url in ("postgresql+psycopg://cdp:cdp@db:5432/cdp", "sqlite:///./cdp.db"):
        assert sqlalchemy_url(url) == url
