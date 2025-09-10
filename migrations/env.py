from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel
import os, sys

# garante que o Python enxerga seus módulos do projeto
sys.path.append(os.getcwd())

# importe os modelos para popular o metadata:
from models import *  # se for "app/models.py", use: from app.models import *

config = context.config

# ler DATABASE_URL do ambiente (em dev e prod)
db_url = os.getenv("DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

target_metadata = SQLModel.metadata

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
