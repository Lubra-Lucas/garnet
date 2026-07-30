# db.py
import os
import logging
import streamlit as st
from sqlmodel import SQLModel, create_engine
from sqlalchemy import text


logger = logging.getLogger(__name__)
SQLITE_DATABASE_URL = "sqlite:///data/app.db"
DATABASE_FALLBACK_USED = False


def get_database_url():
    """
    Define o banco correto conforme o ambiente.

    EC2 Windows:
        usa C:/garnet/data/app.db

    Replit / Linux:
        usa data/app.db

    Se existir DATABASE_URL no ambiente/secrets, tenta usar PostgreSQL.
    No desenvolvimento, se essa conexão estiver indisponível, usa o SQLite
    local para que o sistema continue acessível. Em produção, a falha é
    propagada para não mascarar uma configuração inválida.
    """

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        try:
            database_url = st.secrets.get("DATABASE_URL")
        except Exception:
            database_url = None

    if database_url:
        return database_url

    if os.name == "nt":
        os.makedirs(r"C:\garnet\data", exist_ok=True)
        return "sqlite:///C:/garnet/data/app.db"

    os.makedirs("data", exist_ok=True)
    return SQLITE_DATABASE_URL


DATABASE_URL = get_database_url()


connect_args = {}

if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

elif DATABASE_URL.startswith("postgresql"):
    connect_args = {
        "sslmode": "require",
        "connect_timeout": 10,
    }


@st.cache_resource
def get_engine():
    global DATABASE_FALLBACK_USED

    engine_kwargs = {
        "echo": False,
        "connect_args": connect_args,
        "pool_pre_ping": True,
    }

    candidate = create_engine(DATABASE_URL, **engine_kwargs)

    if not DATABASE_URL.startswith("postgresql"):
        return candidate

    try:
        with candidate.connect() as connection:
            connection.execute(text("SELECT 1"))
        return candidate
    except Exception:
        # A local preview must remain usable when an old/invalid PostgreSQL
        # secret is present. Deployments still fail explicitly instead.
        if os.getenv("REPLIT_DEPLOYMENT") or os.getenv("APP_ENV") == "production":
            raise

        DATABASE_FALLBACK_USED = True
        logger.warning(
            "PostgreSQL indisponível no desenvolvimento; usando SQLite local."
        )
        return create_engine(
            SQLITE_DATABASE_URL,
            echo=False,
            connect_args={"check_same_thread": False},
            pool_pre_ping=True,
        )


engine = get_engine()


def init_db():
    SQLModel.metadata.create_all(engine)


def get_session():
    from sqlmodel import Session
    from sqlalchemy import text

    global engine

    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        try:
            session = Session(engine)
            session.exec(text("SELECT 1")).first()
            return session

        except Exception as e:
            retry_count += 1

            if retry_count >= max_retries:
                get_engine.clear()
                engine = get_engine()

                try:
                    session = Session(engine)
                    session.exec(text("SELECT 1")).first()
                    return session
                except Exception:
                    raise e

            else:
                import time
                time.sleep(1)


def get_db_info():
    active_url = SQLITE_DATABASE_URL if DATABASE_FALLBACK_USED else DATABASE_URL
    db_type = "PostgreSQL" if active_url.startswith("postgresql") else "SQLite"
    db_location = active_url.split("://")[1] if "://" in active_url else active_url

    return {
        "type": db_type,
        "location": db_location,
        "url": active_url,
    }