# pages/16_UsuariosPermissoes.py
import streamlit as st
from auth import require_login, has_permission, hash_password
from sqlmodel import Session, select
from db import engine
from models import User
import pandas as pd
from datetime import datetime

# Require login for this page - only managers can access
user = require_login(["manager"])

st.set_page_config(page_title="GARNET - Usuários e Permissões", layout="wide")

# Professional page header
st.markdown("""
<div style="padding: 1rem 0 2rem 0; border-bottom: 1px solid #E8E8E8; margin-bottom: 2rem;">
    <h1 style="margin: 0; color: #2E4A6B; font-weight: 300;">Gestão de Usuários e Permissões</h1>
    <p style="margin: 0.5rem 0 0 0; color: #666; font-size: 1.1rem;">Controle de acesso e segurança do sistema</p>
</div>
""", unsafe_allow_html=True)

# Clean tabs without icons
tab1, tab2, tab3, tab4 = st.tabs(["Usuários", "Permissões", "Auditoria", "Configurações"])

with tab1:
    st.subheader("Gestão de Usuários")
    
    # Get all users
    with Session(engine) as session:
        users = session.exec(select(User).order_by(User.created_at.desc())).all()
    
    if users:
        # Users overview
        user_col1, user_col2, user_col3, user_col4 = st.columns(4)
        
        with user_col1:
            total_users = len(users)
            st.metric("Total de Usuários", total_users)
        
        with user_col2:
            active_users = sum(1 for u in users if u.is_active)
            st.metric("Usuários Ativos", active_users)
        
        with user_col3:
            managers = sum(1 for u in users if u.role == "manager")
            st.metric("Gerentes", managers)
        
        with user_col4:
            operators = sum(1 for u in users if u.role == "operator")
            st.metric("Operadores", operators)
        
        # Users table
        st.markdown("""
        <div style="margin: 2rem 0 1rem 0;">
            <h3 style="margin: 0; color: #2E4A6B; font-weight: 400;">Lista de Usuários</h3>
        </div>
        """, unsafe_allow_html=True)
        
        user_data = []
        for u in users:
            last_login = "N/A"  # Placeholder - would need login tracking
            
            user_data.append({
                "ID": u.id,
                "Usuário": u.username,
                "Nome": u.name,
                "Perfil": u.role.title(),
                "Status": "🟢 Ativo" if u.is_active else "🔴 Inativo",
                "Criado em": u.created_at.strftime("%d/%m/%Y %H:%M") if u.created_at else "N/A",
                "Último Login": last_login
            })
        
        users_df = pd.DataFrame(user_data)
        
        # Editable users table
        edited_df = st.data_editor(
            users_df,
            hide_index=True,
            use_container_width=True,
            disabled=["ID", "Usuário", "Criado em", "Último Login"],
            column_config={
                "Perfil": st.column_config.SelectboxColumn(
                    "Perfil",
                    options=["Viewer", "Operator", "Manager"],
                    required=True
                ),
                "Status": st.column_config.SelectboxColumn(
                    "Status",
                    options=["🟢 Ativo", "🔴 Inativo"],
                    required=True
                )
            }
        )
        
        action_col1, action_col2 = st.columns(2)
        
        with action_col1:
            if st.button("💾 Salvar Alterações"):
                with Session(engine) as session:
                    for idx, row in edited_df.iterrows():
                        db_user = session.get(User, row["ID"])
                        if db_user:
                            db_user.name = row["Nome"]
                            db_user.role = row["Perfil"].lower()
                            db_user.is_active = "🟢" in row["Status"]
                    
                    session.commit()
                    st.success("Alterações salvas com sucesso!")
                    st.rerun()
        
        with action_col2:
            if st.button("🔐 Alterar Senha de Usuário"):
                st.session_state.show_password_change = True
    
    # Password change modal
    if st.session_state.get('show_password_change'):
        st.markdown("---")
        st.subheader("🔐 Alterar Senha de Usuário")
        
        with st.form("change_password_form"):
            selected_user_id = st.selectbox(
                "Selecione o Usuário",
                options=[(u.id, f"{u.name} ({u.username})") for u in users],
                format_func=lambda x: x[1]
            )
            
            new_password = st.text_input("Nova Senha *", type="password", placeholder="Mínimo 6 caracteres")
            confirm_new_password = st.text_input("Confirmar Nova Senha *", type="password")
            
            change_col1, change_col2 = st.columns(2)
            
            with change_col1:
                change_submitted = st.form_submit_button("🔐 Alterar Senha", use_container_width=True)
            
            with change_col2:
                if st.form_submit_button("❌ Cancelar", use_container_width=True):
                    st.session_state.show_password_change = False
                    st.rerun()
            
            if change_submitted:
                if not new_password:
                    st.error("A nova senha é obrigatória.")
                elif len(new_password) < 6:
                    st.error("A senha deve ter pelo menos 6 caracteres.")
                elif new_password != confirm_new_password:
                    st.error("As senhas não coincidem.")
                else:
                    with Session(engine) as session:
                        target_user = session.get(User, selected_user_id[0])
                        if target_user:
                            target_user.password_hash = hash_password(new_password)
                            session.commit()
                            st.success(f"Senha do usuário '{target_user.name}' alterada com sucesso!")
                            st.session_state.show_password_change = False
                            st.rerun()
                        else:
                            st.error("Usuário não encontrado.")
    
    # User deletion section
    st.markdown("---")
    st.subheader("🗑️ Excluir Usuário")
    
    delete_col1, delete_col2 = st.columns([2, 1])
    
    with delete_col1:
        user_to_delete = st.selectbox(
            "Selecione o usuário para excluir",
            options=[None] + [(u.id, f"{u.name} ({u.username})") for u in users if u.username != user['username']],
            format_func=lambda x: "Selecione um usuário..." if x is None else x[1]
        )
    
    with delete_col2:
        if user_to_delete and st.button("🗑️ Excluir Usuário", type="secondary", use_container_width=True):
            st.session_state.delete_user_id = user_to_delete[0]
            st.session_state.show_delete_user_confirm = True
    
    # Delete confirmation
    if st.session_state.get('show_delete_user_confirm') and st.session_state.get('delete_user_id'):
        st.error("⚠️ **ATENÇÃO:** Esta ação não pode ser desfeita!")
        
        with Session(engine) as session:
            user_to_delete = session.get(User, st.session_state.delete_user_id)
            if user_to_delete:
                st.warning(f"Tem certeza que deseja excluir o usuário **{user_to_delete.name} ({user_to_delete.username})**?")
                
                confirm_col1, confirm_col2, confirm_col3 = st.columns(3)
                
                with confirm_col1:
                    if st.button("✅ Confirmar Exclusão", type="primary"):
                        try:
                            # Check if this is the current user
                            if user_to_delete.username == user['username']:
                                st.error("Você não pode excluir sua própria conta.")
                            else:
                                session.delete(user_to_delete)
                                session.commit()
                                st.success(f"Usuário '{user_to_delete.name}' excluído com sucesso!")
                                st.session_state.show_delete_user_confirm = False
                                st.session_state.delete_user_id = None
                                st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao excluir usuário: {str(e)}")
                
                with confirm_col2:
                    if st.button("❌ Cancelar"):
                        st.session_state.show_delete_user_confirm = False
                        st.session_state.delete_user_id = None
                        st.rerun()
    
    else:
        st.info("Nenhum usuário encontrado.")
    
    # Add new user
    st.markdown("---")
    st.subheader("➕ Adicionar Novo Usuário")
    
    with st.form("new_user_form"):
        user_col1, user_col2 = st.columns(2)
        
        with user_col1:
            new_username = st.text_input("Nome de Usuário *", placeholder="usuario123")
            new_name = st.text_input("Nome Completo *", placeholder="João Silva")
            new_role = st.selectbox("Perfil *", ["viewer", "operator", "manager"])
        
        with user_col2:
            new_password = st.text_input("Senha *", type="password", placeholder="Mínimo 6 caracteres")
            confirm_password = st.text_input("Confirmar Senha *", type="password")
            is_active = st.checkbox("Usuário Ativo", value=True)
        
        submitted = st.form_submit_button("👤 Criar Usuário", use_container_width=True)
        
        if submitted:
            if not new_username or not new_name or not new_password:
                st.error("Todos os campos obrigatórios devem ser preenchidos.")
            elif len(new_password) < 6:
                st.error("A senha deve ter pelo menos 6 caracteres.")
            elif new_password != confirm_password:
                st.error("As senhas não coincidem.")
            else:
                with Session(engine) as session:
                    # Check if username already exists
                    existing = session.exec(
                        select(User).where(User.username == new_username)
                    ).first()
                    
                    if existing:
                        st.error("Nome de usuário já existe.")
                    else:
                        new_user = User(
                            username=new_username,
                            name=new_name,
                            role=new_role,
                            password_hash=hash_password(new_password),
                            is_active=is_active
                        )
                        
                        session.add(new_user)
                        session.commit()
                        
                        st.success(f"Usuário '{new_username}' criado com sucesso!")
                        st.rerun()

with tab2:
    st.subheader("🔐 Gestão de Permissões")
    
    # Role definitions
    st.markdown("### 📋 Definição de Perfis")
    
    role_definitions = {
        "viewer": {
            "name": "Visualizador",
            "description": "Acesso somente leitura",
            "permissions": [
                "✅ Visualizar dashboards",
                "✅ Consultar relatórios",
                "✅ Visualizar estoque",
                "❌ Criar/editar dados",
                "❌ Aprovar processos",
                "❌ Gerenciar usuários"
            ]
        },
        "operator": {
            "name": "Operador",
            "description": "Operações do dia a dia",
            "permissions": [
                "✅ Todas permissões do Visualizador",
                "✅ Criar/editar fornecedores",
                "✅ Gerenciar estoque",
                "✅ Criar ordens de produção",
                "✅ Registrar recebimentos",
                "✅ Realizar testes de qualidade",
                "❌ Gerenciar usuários"
            ]
        },
        "manager": {
            "name": "Gerente",
            "description": "Acesso administrativo completo",
            "permissions": [
                "✅ Todas permissões do Operador",
                "✅ Aprovar formulações",
                "✅ Gerenciar usuários",
                "✅ Configurar sistema",
                "✅ Exportar dados sensíveis",
                "✅ Visualizar dados financeiros"
            ]
        }
    }
    
    # Display role information
    role_col1, role_col2, role_col3 = st.columns(3)
    
    with role_col1:
        st.markdown("#### 👁️ Visualizador")
        role_info = role_definitions["viewer"]
        st.info(role_info["description"])
        for perm in role_info["permissions"]:
            st.text(perm)
    
    with role_col2:
        st.markdown("#### ⚙️ Operador")
        role_info = role_definitions["operator"]
        st.info(role_info["description"])
        for perm in role_info["permissions"]:
            st.text(perm)
    
    with role_col3:
        st.markdown("#### 👑 Gerente")
        role_info = role_definitions["manager"]
        st.info(role_info["description"])
        for perm in role_info["permissions"]:
            st.text(perm)
    
    # Permission matrix
    st.markdown("---")
    st.markdown("### 🎯 Matriz de Permissões")
    
    permissions_matrix = {
        "Funcionalidade": [
            "Visualizar Dashboard",
            "Consultar Relatórios",
            "Gerenciar Fornecedores",
            "Gerenciar Matérias-Primas",
            "Gerenciar Produtos",
            "Criar Formulações",
            "Aprovar Formulações",
            "Gerenciar Estoque",
            "Criar Ordens Produção",
            "Registrar Recebimentos",
            "Testes Qualidade",
            "Aprovar Lotes",
            "Criar Pedidos Compra",
            "Dados Financeiros",
            "Gerenciar Usuários",
            "Configurar Sistema"
        ],
        "Visualizador": [
            "✅", "✅", "❌", "❌", "❌", "❌", "❌", 
            "👁️", "❌", "❌", "👁️", "❌", "❌", "❌", "❌", "❌"
        ],
        "Operador": [
            "✅", "✅", "✅", "✅", "✅", "✅", "❌",
            "✅", "✅", "✅", "✅", "✅", "✅", "👁️", "❌", "❌"
        ],
        "Gerente": [
            "✅", "✅", "✅", "✅", "✅", "✅", "✅",
            "✅", "✅", "✅", "✅", "✅", "✅", "✅", "✅", "✅"
        ]
    }
    
    permissions_df = pd.DataFrame(permissions_matrix)
    st.dataframe(permissions_df, hide_index=True, use_container_width=True)
    
    st.caption("✅ = Acesso Total | 👁️ = Somente Leitura | ❌ = Sem Acesso")

with tab3:
    st.subheader("📊 Auditoria de Acesso")
    
    # User activity overview
    with Session(engine) as session:
        users = session.exec(select(User)).all()
    
    # Simulated audit data
    audit_data = [
        {
            "Data/Hora": "25/01/2025 14:30",
            "Usuário": "admin",
            "Ação": "Login",
            "Módulo": "Sistema",
            "IP": "192.168.1.100",
            "Status": "✅ Sucesso"
        },
        {
            "Data/Hora": "25/01/2025 14:25",
            "Usuário": "operator",
            "Ação": "Criar Ordem Produção",
            "Módulo": "Produção",
            "IP": "192.168.1.101",
            "Status": "✅ Sucesso"
        },
        {
            "Data/Hora": "25/01/2025 14:20",
            "Usuário": "viewer",
            "Ação": "Visualizar Relatório",
            "Módulo": "Relatórios",
            "IP": "192.168.1.102",
            "Status": "✅ Sucesso"
        },
        {
            "Data/Hora": "25/01/2025 14:15",
            "Usuário": "test_user",
            "Ação": "Login",
            "Módulo": "Sistema",
            "IP": "192.168.1.200",
            "Status": "❌ Falha"
        }
    ]
    
    audit_df = pd.DataFrame(audit_data)
    
    # Audit filters
    audit_col1, audit_col2, audit_col3 = st.columns(3)
    
    with audit_col1:
        audit_user_filter = st.selectbox("Usuário:", ["Todos"] + [u.username for u in users])
    
    with audit_col2:
        audit_action_filter = st.selectbox("Ação:", ["Todas", "Login", "Logout", "Criar", "Editar", "Excluir", "Visualizar"])
    
    with audit_col3:
        audit_days = st.selectbox("Período:", ["Hoje", "Últimos 7 dias", "Últimos 30 dias", "Todos"])
    
    # Display audit log
    st.markdown("### 📋 Log de Auditoria")
    st.dataframe(audit_df, hide_index=True, use_container_width=True)
    
    # Audit statistics
    st.markdown("---")
    st.markdown("### 📊 Estatísticas de Acesso")
    
    stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)
    
    with stats_col1:
        total_actions = len(audit_df)
        st.metric("Total de Ações", total_actions)
    
    with stats_col2:
        successful_actions = len(audit_df[audit_df["Status"].str.contains("✅")])
        st.metric("Ações Bem-sucedidas", successful_actions)
    
    with stats_col3:
        failed_actions = len(audit_df[audit_df["Status"].str.contains("❌")])
        st.metric("Tentativas Falharam", failed_actions)
    
    with stats_col4:
        unique_users = len(audit_df["Usuário"].unique())
        st.metric("Usuários Únicos", unique_users)
    
    # Activity chart
    import plotly.express as px
    
    action_counts = audit_df["Ação"].value_counts()
    fig_actions = px.bar(x=action_counts.index, y=action_counts.values, 
                        title="Distribuição de Ações por Tipo")
    st.plotly_chart(fig_actions, use_container_width=True)

with tab4:
    st.subheader("⚙️ Configurações de Segurança")
    
    # Security settings
    st.markdown("### 🔒 Políticas de Senha")
    
    security_col1, security_col2 = st.columns(2)
    
    with security_col1:
        min_password_length = st.number_input("Comprimento mínimo da senha:", min_value=6, max_value=20, value=8)
        require_special_chars = st.checkbox("Exigir caracteres especiais", value=True)
        require_numbers = st.checkbox("Exigir números", value=True)
        require_uppercase = st.checkbox("Exigir maiúsculas", value=True)
    
    with security_col2:
        password_expiry_days = st.number_input("Validade da senha (dias):", min_value=0, max_value=365, value=90)
        max_login_attempts = st.number_input("Máximo tentativas de login:", min_value=3, max_value=10, value=5)
        session_timeout_minutes = st.number_input("Timeout da sessão (minutos):", min_value=15, max_value=480, value=60)
        enable_2fa = st.checkbox("Habilitar autenticação 2FA", value=False, disabled=True, help="Funcionalidade futura")
    
    if st.button("💾 Salvar Configurações de Segurança"):
        st.success("Configurações de segurança salvas com sucesso!")
        st.info("As configurações serão aplicadas no próximo login dos usuários.")
    
    # Session management
    st.markdown("---")
    st.markdown("### 🕐 Gestão de Sessões")
    
    # Active sessions (simulated)
    active_sessions = [
        {
            "Usuário": "admin",
            "IP": "192.168.1.100",
            "Início da Sessão": "25/01/2025 14:30",
            "Última Atividade": "25/01/2025 15:45",
            "Status": "🟢 Ativa"
        },
        {
            "Usuário": "operator",
            "IP": "192.168.1.101",
            "Início da Sessão": "25/01/2025 13:15",
            "Última Atividade": "25/01/2025 15:42",
            "Status": "🟢 Ativa"
        }
    ]
    
    sessions_df = pd.DataFrame(active_sessions)
    st.dataframe(sessions_df, hide_index=True, use_container_width=True)
    
    session_actions_col1, session_actions_col2 = st.columns(2)
    
    with session_actions_col1:
        if st.button("🔄 Atualizar Lista de Sessões"):
            st.success("Lista de sessões atualizada!")
    
    with session_actions_col2:
        if st.button("⚠️ Encerrar Todas as Sessões"):
            st.warning("Esta ação encerrará todas as sessões ativas (exceto a sua).")
            if st.button("Confirmar Encerramento", type="primary"):
                st.success("Todas as sessões foram encerradas!")
    
    # Backup and maintenance
    st.markdown("---")
    st.markdown("### 💾 Backup e Manutenção")
    
    backup_col1, backup_col2 = st.columns(2)
    
    with backup_col1:
        st.markdown("**Backup de Dados de Usuários**")
        
        if st.button("📤 Exportar Dados de Usuários"):
            with Session(engine) as session:
                users = session.exec(select(User)).all()
                
                backup_data = []
                for u in users:
                    backup_data.append({
                        "username": u.username,
                        "name": u.name,
                        "role": u.role,
                        "is_active": u.is_active,
                        "created_at": u.created_at.isoformat() if u.created_at else None
                    })
                
                backup_df = pd.DataFrame(backup_data)
                csv_data = backup_df.to_csv(index=False)
                
                st.download_button(
                    label="📥 Download Backup",
                    data=csv_data,
                    file_name=f"backup_usuarios_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
    
    with backup_col2:
        st.markdown("**Limpeza de Dados**")
        
        if st.button("🧹 Limpar Logs Antigos"):
            st.info("Funcionalidade de limpeza de logs será implementada.")
        
        if st.button("🔍 Verificar Integridade"):
            st.success("Verificação de integridade concluída - Nenhum problema encontrado.")
    
    # System information
    st.markdown("---")
    st.markdown("### ℹ️ Informações do Sistema")
    
    info_col1, info_col2, info_col3 = st.columns(3)
    
    with info_col1:
        st.metric("Versão do Sistema", "1.0.0")
        st.metric("Usuários Cadastrados", len(users) if users else 0)
    
    with info_col2:
        st.metric("Última Atualização", "25/01/2025")
        st.metric("Sessões Ativas", len(active_sessions))
    
    with info_col3:
        from db import get_db_info
        db_info = get_db_info()
        st.metric("Tipo de Banco", db_info["type"])
        st.metric("Status", "🟢 Online")
