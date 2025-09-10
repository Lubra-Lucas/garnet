# app.py
import streamlit as st
import os
from db import init_db
from auth import login_form, has_permission
from models import User
from sqlmodel import Session, select
from db import engine
from auth import hash_password
from utils.ui_components import render_feature_card, render_info_box, render_section_header
from utils.performance import get_user_permissions

st.set_page_config(
    page_title="GARNET - Sistema de Gestão Industrial",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database and create default users if they don't exist
init_db()

# Create default users if they don't exist
def create_default_users():
    with Session(engine) as session:
        # Check if any users exist
        existing_users = session.exec(select(User)).first()
        if not existing_users:
            # Create default users
            default_users = [
                User(username="admin", name="Administrador", role="manager", password_hash=hash_password("admin123")),
                User(username="operator", name="Operador", role="operator", password_hash=hash_password("op123")),
                User(username="viewer", name="Visualizador", role="viewer", password_hash=hash_password("view123"))
            ]
            for user in default_users:
                session.add(user)
            session.commit()

create_default_users()

# Authentication check
if "user" not in st.session_state:
    login_form()
else:
    # Professional sidebar with user info
    with st.sidebar:
        st.markdown("---")
        st.markdown(f"**{st.session_state['user']['name']}**")
        st.caption(f"Perfil: {st.session_state['user']['role'].title()}")
        st.markdown("---")

        

        # --- Applying permission restrictions to sidebar ---
        # Hiding 'Análise de Custos' sub-tab in 'Formulação' if not manager
        # This is handled within the 'Formulação' page itself.

        # Hiding restricted pages for non-managers
        if not has_permission("manager"):
            # Rerun the page if the user is not a manager and tries to access restricted pages directly
            if st.session_state.get("current_page_path") in [
                "pages/14_Custos e Precificação.py",
                "pages/15_Relatórios e KPIs.py",
                "pages/16_Usuários e Permissões.py",
                "pages/17_Configurações Gerais.py"
            ]:
                st.warning("Você não tem permissão para acessar esta página.")
                # You might want to redirect them to a default page, e.g., the homepage
                st.switch_page("pages/1_Home.py")


        if st.button("Sair do Sistema", use_container_width=True, type="secondary"):
            del st.session_state["user"]
            st.rerun()

    # Professional header
    st.markdown("""
    <div style="padding: 1.5rem 0 1.5rem 0; border-bottom: 2px solid #E8E8E8; margin-bottom: 1.5rem;">
        <h1 style="margin: 0; color: #2E4A6B; font-weight: 300; font-size: 2.5rem;">GARNET</h1>
        <h3 style="margin: 0.5rem 0 0 0; color: #666; font-weight: 300; font-size: 1.2rem;">Sistema de Gestão Industrial</h3>
    </div>
    """, unsafe_allow_html=True)

    # Info box using utility
    render_info_box(
        "Plataforma integrada para gestão completa de operações industriais, "
        "desenvolvida especificamente para empresas do setor cosmético."
    )

    # Feature cards with clean design
    col1, col2, col3 = st.columns(3, gap="medium")

    with col1:
        render_feature_card(
            "Gestão de Materiais",
            [
                "Cadastro de Fornecedores",
                "Controle de Matérias-Primas",
                "Gestão de Estoque",
                "Rastreabilidade de Lotes"
            ]
        )

    with col2:
        render_feature_card(
            "Planejamento & Produção",
            [
                "Formulações de Produtos",
                "Ordens de Produção",
                "MRP e Planejamento",
                "Controle de Qualidade"
            ]
        )

    with col3:
        render_feature_card(
            "Financeiro & Análises",
            [
                "Gestão de Compras",
                "Controle Financeiro",
                "Análise de Custos",
                "Relatórios e KPIs"
            ]
        )

    # Professional search section with proper spacing
    # Quick search section using utility
    render_section_header("Busca Rápida", with_divider=False)
    st.markdown("""
    <div style="background: white; padding: 1.25rem; border-radius: 8px; border: 1px solid #E0E0E0; margin: 0 0 1rem 0;">
    </div>
    """, unsafe_allow_html=True)

    search_term = st.text_input("Busca", placeholder="Pesquisar por código, nome ou lote...", label_visibility="collapsed")

    if search_term:
        st.info(f"Resultados da busca por: '{search_term}'")
        st.markdown("*Funcionalidade de busca será implementada nas próximas páginas*")

    # Clean access section with proper spacing
    # Quick access section using utility
    render_section_header("Acesso Rápido")

    quick_access_col1, quick_access_col2, quick_access_col3, quick_access_col4 = st.columns(4, gap="small")

    with quick_access_col1:
        if st.button("📦 Estoque", use_container_width=True, type="secondary"):
            st.switch_page("pages/6_Estoque.py")

    with quick_access_col2:
        if st.button("🏭 Produção", use_container_width=True, type="secondary"):
            st.switch_page("pages/7_Ordens de Produção.py")

    with quick_access_col3:
        if st.button("🛒 Compras", use_container_width=True, type="secondary"):
            st.switch_page("pages/9_Compras e Pedidos.py")

    with quick_access_col4:
        if st.button("📈 Relatórios", use_container_width=True, type="secondary"):
            if has_permission("manager"):
                st.switch_page("pages/15_Relatórios e KPIs.py")
            else:
                st.switch_page("pages/13_Financeiro.py")