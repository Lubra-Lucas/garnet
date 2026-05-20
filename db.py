# db.py
import os
from sqlmodel import SQLModel, create_engine
import streamlit as st

DATABASE_URL = "sqlite:///data/app.db"

# Handle connection arguments
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    # Ensure data directory exists for SQLite
    os.makedirs("data", exist_ok=True)
elif DATABASE_URL.startswith("postgresql"):
    # PostgreSQL connection pooling and SSL settings
    connect_args = {
        "sslmode": "prefer",
        "connect_timeout": 10,
    }

# Create engine with caching for Streamlit
@st.cache_resource
def get_engine():
    """Create and cache database engine with improved connection handling"""
    engine_kwargs = {
        "echo": False,
        "connect_args": connect_args,
    }
    
    return create_engine(DATABASE_URL, **engine_kwargs)

engine = get_engine()

def init_db():
    """Initialize database by creating all tables"""
    SQLModel.metadata.create_all(engine)

def get_session():
    """Get database session with connection retry"""
    from sqlmodel import Session
    from sqlalchemy import text
    global engine
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            session = Session(engine)
            # Test connection
            session.exec(text("SELECT 1")).first()
            return session
        except Exception as e:
            retry_count += 1
            if retry_count >= max_retries:
                # Clear the cached engine and try once more
                get_engine.clear()
                engine = get_engine()
                try:
                    session = Session(engine)
                    session.exec(text("SELECT 1")).first()
                    return session
                except:
                    raise e
            else:
                import time
                time.sleep(1)  # Wait 1 second before retry

def get_db_info():
    """Get database connection information"""
    db_type = "SQLite"
    db_location = DATABASE_URL.split("://")[1] if "://" in DATABASE_URL else DATABASE_URL
    return {
        "type": db_type,
        "location": db_location,
        "url": DATABASE_URL
    }
