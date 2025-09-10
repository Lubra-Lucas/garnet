# auth.py
import streamlit as st
from passlib.context import CryptContext
from sqlmodel import Session, select
from models import User
from db import engine
from typing import List

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain, hashed)

def login_form():
    """Display professional login form and handle authentication"""
    # Clean, centered login layout
    st.markdown("""
    <style>
    .login-container {
        max-width: 400px;
        margin: 2rem auto;
        padding: 2rem;
        background: white;
        border-radius: 12px;
        border: 1px solid #E0E0E0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .login-header {
        text-align: center;
        margin-bottom: 2rem;
    }
    .login-title {
        color: #2E4A6B;
        font-size: 2rem;
        font-weight: 300;
        margin: 0;
    }
    .login-subtitle {
        color: #666;
        font-size: 1rem;
        margin: 0.5rem 0 0 0;
    }
    </style>
    """, unsafe_allow_html=True)

    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("""
        <div class="login-container">
            <div class="login-header">
                <h1 class="login-title">GARNET</h1>
                <p class="login-subtitle">Sistema de Gestão Industrial</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            username = st.text_input("Usuário", placeholder="Digite seu usuário")
            password = st.text_input("Senha", type="password", placeholder="Digite sua senha")
            submit = st.form_submit_button("Acessar Sistema", use_container_width=True, type="primary")

            if submit:
                if not username or not password:
                    st.error("Por favor, preencha usuário e senha.")
                    return

                with Session(engine) as session:
                    user = session.exec(select(User).where(User.username == username)).first()
                    if user and verify_password(password, user.password_hash):
                        st.session_state["user"] = {
                            "id": user.id,
                            "name": user.name,
                            "role": user.role,
                            "username": user.username
                        }
                        st.success("Acesso autorizado. Redirecionando...")
                        st.rerun()
                    else:
                        st.error("Credenciais inválidas. Verifique usuário e senha.")

def require_login(allowed_roles: List[str] = None):
    """Require user to be logged in and optionally check role permissions"""
    user = st.session_state.get("user")
    if not user:
        st.error("Acesso negado. Faça login para continuar.")
        st.stop()

    user_role = user.get("role")
    if allowed_roles and user_role not in allowed_roles:
        st.error("Acesso negado.")
        st.stop()

    return user

def get_current_user():
    """Get current logged in user"""
    return st.session_state.get("user")

def has_permission(required_role: str = None):
    """Check if current user has required permission level"""
    user = get_current_user()
    if not user:
        return False

    # Role hierarchy: viewer < operator < manager
    role_levels = {"viewer": 1, "operator": 2, "manager": 3}
    user_level = role_levels.get(user.get("role"), 0)
    required_level = role_levels.get(required_role, 0)

    return user_level >= required_level