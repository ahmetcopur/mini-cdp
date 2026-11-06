from app.database import connect_args_for, sqlalchemy_url


def test_hosted_postgres_urls_use_psycopg_3():
    url = "postgresql://user:secret@ep-example.neon.tech/neondb?sslmode=require"
    assert sqlalchemy_url(url) == "postgresql+psycopg://user:secret@ep-example.neon.tech/neondb?sslmode=require"


def test_other_urls_are_unchanged():
    for url in ("postgresql+psycopg://cdp:cdp@db:5432/cdp", "sqlite:///./cdp.db"):
        assert sqlalchemy_url(url) == url


def test_pooled_neon_urls_turn_off_prepared_statements():
    pooled = "postgresql+psycopg://user:secret@ep-example-pooler.eu-central-1.aws.neon.tech/neondb"
    direct = "postgresql+psycopg://user:secret@ep-example.eu-central-1.aws.neon.tech/neondb"
    assert connect_args_for(pooled) == {"prepare_threshold": None}
    assert connect_args_for(direct) == {}
    assert connect_args_for("sqlite:///./cdp.db") == {"check_same_thread": False}
