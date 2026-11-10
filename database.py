import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not configured")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def ensure_schema():
    """Add columns introduced after the first deploy. create_all does not alter existing tables."""
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    with engine.begin() as conn:
        if inspector.has_table("reviews"):
            review_cols = {col["name"]: col for col in inspector.get_columns("reviews")}
            if "is_visible" not in review_cols:
                conn.execute(text(
                    "ALTER TABLE reviews ADD COLUMN is_visible BOOLEAN NOT NULL DEFAULT TRUE"
                ))
            if "author_name" not in review_cols:
                conn.execute(text(
                    "ALTER TABLE reviews ADD COLUMN author_name VARCHAR(100)"
                ))
            user_col = review_cols.get("user_id")
            if user_col and user_col.get("nullable") is False:
                conn.execute(text("ALTER TABLE reviews ALTER COLUMN user_id DROP NOT NULL"))
        if inspector.has_table("product_screenshots"):
            shot_cols = {col["name"] for col in inspector.get_columns("product_screenshots")}
            if "thumb_url" not in shot_cols:
                conn.execute(text(
                    "ALTER TABLE product_screenshots ADD COLUMN thumb_url VARCHAR(500)"
                ))