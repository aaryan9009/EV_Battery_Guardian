import os
from alembic import context
from sqlalchemy import create_engine
from app.database.session import Base
import app.models  # noqa: F401

config = context.config
target_metadata = Base.metadata
url = os.environ.get("DATABASE_URL") or __import__("app.core.config", fromlist=["x"]).get_settings().database_url

def run_migrations_offline():
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, compare_type=True)
    with context.begin_transaction(): context.run_migrations()

def run_migrations_online():
    engine = create_engine(url)
    with engine.connect() as conn:
        context.configure(connection=conn, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction(): context.run_migrations()

run_migrations_offline() if context.is_offline_mode() else run_migrations_online()
