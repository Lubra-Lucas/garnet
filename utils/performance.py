# utils/performance.py
"""
Performance optimization utilities for GARNET system
"""
import streamlit as st
import time
from functools import wraps
from typing import Any, Callable, Optional


def timing_decorator(func: Callable) -> Callable:
    """
    Decorator to measure function execution time
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        # Only show timing in debug mode
        if st.session_state.get("debug_mode", False):
            st.sidebar.caption(f"⏱️ {func.__name__}: {end_time - start_time:.3f}s")
        
        return result
    return wrapper


@st.cache_resource
def get_database_connection():
    """
    Cached database connection
    """
    from db import engine
    return engine


@st.cache_data(ttl=60)  # Cache for 1 minute
def get_user_permissions(user_role: str) -> dict:
    """
    Cache user permissions to avoid repeated checks
    """
    permissions = {
        "manager": {
            "can_view_all": True,
            "can_edit_all": True,
            "can_delete": True,
            "can_access_financial": True,
            "can_access_reports": True,
            "can_manage_users": True
        },
        "operator": {
            "can_view_all": True,
            "can_edit_all": True,
            "can_delete": True,
            "can_access_financial": False,
            "can_access_reports": False,
            "can_manage_users": False
        },
        "viewer": {
            "can_view_all": True,
            "can_edit_all": False,
            "can_delete": False,
            "can_access_financial": False,
            "can_access_reports": False,
            "can_manage_users": False
        }
    }
    return permissions.get(user_role, permissions["viewer"])


def optimize_dataframe_display(df, max_rows: int = 1000):
    """
    Optimize DataFrame display for performance
    """
    if len(df) > max_rows:
        st.warning(f"Mostrando apenas os primeiros {max_rows} registros de {len(df)} total.")
        return df.head(max_rows)
    return df


class PerformanceMonitor:
    """
    Context manager for monitoring performance
    """
    def __init__(self, operation_name: str, show_spinner: bool = True):
        self.operation_name = operation_name
        self.show_spinner = show_spinner
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        if self.show_spinner:
            self.spinner = st.spinner(f"Executando {self.operation_name}...")
            self.spinner.__enter__()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.show_spinner and hasattr(self, 'spinner'):
            self.spinner.__exit__(exc_type, exc_val, exc_tb)
            
        elapsed = time.time() - self.start_time
        
        # Show performance info in debug mode
        if st.session_state.get("debug_mode", False):
            if elapsed > 1.0:
                st.sidebar.warning(f"⚠️ {self.operation_name}: {elapsed:.2f}s (lento)")
            else:
                st.sidebar.success(f"✅ {self.operation_name}: {elapsed:.3f}s")


def lazy_load_data(load_function: Callable, cache_key: str, ttl: int = 300):
    """
    Lazy load data with caching
    """
    @st.cache_data(ttl=ttl)
    def cached_loader():
        return load_function()
    
    return cached_loader()


def batch_database_operations(operations: list, batch_size: int = 100):
    """
    Execute database operations in batches for better performance
    """
    results = []
    for i in range(0, len(operations), batch_size):
        batch = operations[i:i + batch_size]
        # Execute batch
        batch_results = []
        for operation in batch:
            try:
                result = operation()
                batch_results.append(result)
            except Exception as e:
                st.error(f"Erro na operação: {str(e)}")
                batch_results.append(None)
        results.extend(batch_results)
    return results