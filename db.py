# db.py
import os
import streamlit as st
from sqlmodel import SQLModel, create_engine


def get_database_url():
    """
    Define o banco correto conforme o ambiente.

    EC2 Windows:
        usa C:/garnet/data/app.db

    Replit / Linux:
        usa data/app.db

    Se existir DATABASE_URL no ambiente/secrets:
        usa ela primeiro.
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
    return "sqlite:///data/app.db"


DATABASE_URL = get_database_url()


connect_args = {}

if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

elif DATABASE_URL.startswith("postgresql"):
    connect_args = {
        "sslmode": "prefer",
        "connect_timeout": 10,
    }


@st.cache_resource
def get_engine():
    engine_kwargs = {
        "echo": False,
        "connect_args": connect_args,
    }

    return create_engine(DATABASE_URL, **engine_kwargs)


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
    db_type = "PostgreSQL" if DATABASE_URL.startswith("postgresql") else "SQLite"
    db_location = DATABASE_URL.split("://")[1] if "://" in DATABASE_URL else DATABASE_URL

    return {
        "type": db_type,
        "location": db_location,
        "url": DATABASE_URL,
    }