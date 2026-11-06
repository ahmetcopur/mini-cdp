import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker



def sqlalchemy_url(url):
    # Hosts like Neon hand out "postgresql://" URLs, which SQLAlchemy would open with
    # psycopg2. This project uses psycopg 3.
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url


def connect_args_for(url):
    if url.startswith("sqlite"):
        return {"check_same_thread": False}
    if "-pooler." in url:
        # Neon's pooled hostnames go through PgBouncer in transaction mode, where each
        # transaction can run on a different server connection. psycopg would prepare
        # repeated queries on one of them and then not find them on the next, so it
        # doesn't prepare them here.
        return {"prepare_threshold": None}
    return {}


DATABASE_URL = sqlalchemy_url(os.getenv("DATABASE_URL", "sqlite:///./cdp.db"))

# Neon suspends a database that has been idle for a few minutes, which closes its
# connections. pool_pre_ping checks a connection from the pool before using it and
# opens a new one if it has been closed.
engine = create_engine(DATABASE_URL, connect_args=connect_args_for(DATABASE_URL), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
