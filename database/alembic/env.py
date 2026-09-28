import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from database.models import metadata

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = metadata

def get_url():
    url = os.environ["DATABASE_URL"]
    # SQLAlchemy doesn't accept the legacy "postgres://" scheme.
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url

def run_migrations_online():
    engine = create_engine(get_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
