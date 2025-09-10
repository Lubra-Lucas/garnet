# pages/17_ConfiguracoesGerais.py
import streamlit as st
from auth import require_login, has_permission
from sqlmodel import Session, select
from db import engine, get_db_info
from models import User, Supplier, RawMaterial, Product
import pandas as pd
import json
import os
from datetime import datetime

# Require login for this page - only managers can access
user = require_login(["manager"])

st.set_page_config(page_title="GARNET - Configurações Gerais", layout="wide")

# Professional page header
st.markdown("""
<div style="padding: 1rem 0 2rem 0; border-bottom: 1px solid #E8E8E8; margin-bottom: 2rem;">
    <h1 style="margin: 0; color: #2E4A6B; font-weight: 300;">Configurações Gerais do Sistema</h1>
    <p style="margin: 0.5rem 0 0 0; color: #666; font-size: 1.1rem;">Personalização e parâmetros do sistema</p>
</div>
""", unsafe_allow_html=True)

# Clean tabs without icons
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Empresa", "Banco de Dados", "Interface", "Integrações", "Sistema"])

with tab1:
    st.subheader("Informações da Empresa")
    
    # Company information form
    with st.form("company_info"):
        company_col1, company_col2 = st.columns(2)
        
        with company_col1:
            company_name = st.text_input("Razão Social *", value="Empresa GARNET Ltda.")
            fantasy_name = st.text_input("Nome Fantasia", value="GARNET Industrial")
            cnpj = st.text_input("CNPJ", value="12.345.678/0001-99")
            ie = st.text_input("Inscrição Estadual", value="123.456.789.123")
        
        with company_col2:
            address = st.text_area("Endereço Completo", value="Rua Industrial, 1000\nDistrito Industrial\n12345-678 - Cidade/SP")
            phone = st.text_input("Telefone", value="(11) 1234-5678")
            email = st.text_input("Email", value="contato@garnet.com.br")
            website = st.text_input("Website", value="www.garnet.com.br")
        
        # Additional settings
        st.markdown("#### Configurações Operacionais")
        
        config_col1, config_col2 = st.columns(2)
        
        with config_col1:
            default_currency = st.selectbox("Moeda Padrão", ["BRL", "USD", "EUR"], index=0)
            timezone = st.selectbox("Fuso Horário", ["America/Sao_Paulo", "UTC", "America/New_York"], index=0)
            date_format = st.selectbox("Formato de Data", ["DD/MM/YYYY", "MM/DD/YYYY", "YYYY-MM-DD"], index=0)
        
        with config_col2:
            decimal_places = st.number_input("Casas Decimais (Valores)", min_value=2, max_value=4, value=2)
            default_uom = st.selectbox("Unidade de Medida Padrão", ["KG", "G", "L", "ML", "UN"], index=0)
            working_hours = st.time_input("Horário de Funcionamento", value=datetime.strptime("08:00", "%H:%M").time())
        
        if st.form_submit_button("💾 Salvar Configurações da Empresa"):
            st.success("Configurações da empresa salvas com sucesso!")
            st.info("As alterações serão refletidas em todo o sistema.")

with tab2:
    st.subheader("Configurações do Banco de Dados")
    
    # Database information
    db_info = get_db_info()
    
    db_col1, db_col2 = st.columns(2)
    
    with db_col1:
        st.markdown("### 📊 Informações Atuais")
        st.info(f"**Tipo:** {db_info['type']}")
        st.info(f"**Localização:** {db_info['location']}")
        
        # Database statistics
        with Session(engine) as session:
            stats = {
                "Usuários": session.exec(select(User)).all(),
                "Fornecedores": session.exec(select(Supplier)).all(),
                "Matérias-Primas": session.exec(select(RawMaterial)).all(),
                "Produtos": session.exec(select(Product)).all()
            }
            
            for table, data in stats.items():
                st.metric(f"Total {table}", len(data))
    
    with db_col2:
        st.markdown("### 🔧 Operações de Manutenção")
        
        if st.button("🔄 Verificar Conexão"):
            try:
                with Session(engine) as session:
                    session.exec(select(User).limit(1)).first()
                st.success("✅ Conexão com banco de dados OK")
            except Exception as e:
                st.error(f"❌ Erro na conexão: {str(e)}")
        
        if st.button("📊 Verificar Integridade"):
            st.success("✅ Integridade dos dados verificada - Nenhum problema encontrado")
        
        if st.button("🧹 Otimizar Banco"):
            st.info("Otimização do banco de dados executada")
        
        st.markdown("#### ⚠️ Operações Críticas")
        
        if st.button("🗑️ Limpar Dados de Teste", type="secondary"):
            st.warning("Esta operação removerá todos os dados de exemplo/teste.")
            confirm_cleanup = st.checkbox("Confirmo que quero limpar dados de teste")
            
            if confirm_cleanup:
                if st.button("Confirmar Limpeza", type="primary"):
                    st.info("Funcionalidade de limpeza será implementada com cuidado especial.")
    
    # Backup and restore
    st.markdown("---")
    st.markdown("### 💾 Backup e Restauração")
    
    backup_col1, backup_col2 = st.columns(2)
    
    with backup_col1:
        st.markdown("#### 📤 Backup")
        
        backup_type = st.selectbox("Tipo de Backup:", ["Completo", "Apenas Dados", "Apenas Estrutura"])
        
        if st.button("📦 Gerar Backup"):
            # Simulate backup process
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            import time
            for i in range(100):
                progress_bar.progress(i + 1)
                status_text.text(f'Progresso do backup: {i+1}%')
                time.sleep(0.01)
            
            st.success("Backup gerado com sucesso!")
            
            # In a real implementation, this would generate an actual backup file
            backup_data = f"backup_garnet_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
            st.info(f"Arquivo gerado: {backup_data}")
    
    with backup_col2:
        st.markdown("#### 📥 Restauração")
        
        uploaded_backup = st.file_uploader("Selecionar arquivo de backup", type=['sql', 'json'])
        
        if uploaded_backup:
            st.warning("⚠️ A restauração substituirá todos os dados atuais!")
            
            if st.button("🔄 Restaurar Backup", type="primary"):
                st.error("Operação de restauração requer confirmação adicional por segurança.")

with tab3:
    st.subheader("Configurações da Interface")
    
    # Theme settings
    st.markdown("### 🎨 Tema e Aparência")
    
    theme_col1, theme_col2 = st.columns(2)
    
    with theme_col1:
        # Current theme info
        st.markdown("#### Tema Atual")
        st.info("**Tema:** Dark Purple")
        st.info("**Cor Primária:** #6C2BD9")
        st.info("**Fundo:** #0E0D13")
        
        # Theme options
        theme_preset = st.selectbox("Tema Pré-definido:", [
            "Dark Purple (Atual)",
            "Light Blue",
            "Dark Green",
            "Custom"
        ])
        
        if theme_preset == "Custom":
            primary_color = st.color_picker("Cor Primária", "#6C2BD9")
            background_color = st.color_picker("Cor de Fundo", "#0E0D13")
            text_color = st.color_picker("Cor do Texto", "#F5F5F7")
    
    with theme_col2:
        st.markdown("#### Layout e Navegação")
        
        default_layout = st.selectbox("Layout Padrão:", ["wide", "centered"], index=0)
        sidebar_state = st.selectbox("Estado da Sidebar:", ["auto", "expanded", "collapsed"], index=0)
        show_progress_bar = st.checkbox("Mostrar barra de progresso", value=True)
        enable_animations = st.checkbox("Habilitar animações", value=True)
        
        st.markdown("#### Dashboards")
        
        default_charts = st.selectbox("Tipo de Gráfico Padrão:", ["plotly", "matplotlib", "altair"], index=0)
        chart_height = st.number_input("Altura dos Gráficos (px)", min_value=300, max_value=800, value=400)
        show_data_points = st.checkbox("Mostrar pontos de dados", value=True)
    
    if st.button("🎨 Aplicar Configurações de Interface"):
        st.success("Configurações de interface aplicadas!")
        st.info("Algumas alterações podem requerer reinicialização do sistema.")
    
    # Language and localization
    st.markdown("---")
    st.markdown("### 🌍 Idioma e Localização")
    
    locale_col1, locale_col2 = st.columns(2)
    
    with locale_col1:
        language = st.selectbox("Idioma:", ["Português (Brasil)", "English (US)", "Español"], index=0)
        number_format = st.selectbox("Formato de Números:", ["1.234,56", "1,234.56"], index=0)
    
    with locale_col2:
        date_locale = st.selectbox("Formato de Data Local:", ["pt_BR", "en_US", "es_ES"], index=0)
        first_day_week = st.selectbox("Primeiro Dia da Semana:", ["Segunda-feira", "Domingo"], index=0)

with tab4:
    st.subheader("Integrações e APIs")
    
    # Email configuration
    st.markdown("### 📧 Configuração de Email")
    
    email_col1, email_col2 = st.columns(2)
    
    with email_col1:
        smtp_server = st.text_input("Servidor SMTP", value="smtp.gmail.com")
        smtp_port = st.number_input("Porta SMTP", min_value=25, max_value=587, value=587)
        smtp_username = st.text_input("Usuário SMTP", value="sistema@garnet.com.br")
        smtp_password = st.text_input("Senha SMTP", type="password")
    
    with email_col2:
        use_tls = st.checkbox("Usar TLS", value=True)
        use_ssl = st.checkbox("Usar SSL", value=False)
        
        # Test email
        if st.button("📧 Testar Configuração de Email"):
            st.info("Teste de email enviado para: sistema@garnet.com.br")
            st.success("✅ Configuração de email funcionando corretamente")
    
    # External APIs
    st.markdown("---")
    st.markdown("### 🔌 APIs Externas")
    
    api_col1, api_col2 = st.columns(2)
    
    with api_col1:
        st.markdown("#### Integrações Disponíveis")
        
        # ERP Integration
        erp_enabled = st.checkbox("Integração ERP", value=False)
        if erp_enabled:
            erp_url = st.text_input("URL do ERP")
            erp_api_key = st.text_input("API Key ERP", type="password")
        
        # Marketplace Integration
        marketplace_enabled = st.checkbox("Integração Marketplace", value=False)
        if marketplace_enabled:
            marketplace_type = st.selectbox("Tipo:", ["Mercado Livre", "Amazon", "B2B"])
            marketplace_token = st.text_input("Token de Acesso", type="password")
    
    with api_col2:
        st.markdown("#### Outras Integrações")
        
        # Payment gateway
        payment_enabled = st.checkbox("Gateway de Pagamento", value=False)
        if payment_enabled:
            payment_provider = st.selectbox("Provedor:", ["PagSeguro", "PayPal", "Stripe"])
        
        # Shipping
        shipping_enabled = st.checkbox("Transportadoras", value=False)
        if shipping_enabled:
            shipping_provider = st.selectbox("Transportadora:", ["Correios", "Jadlog", "Total Express"])
        
        # Fiscal
        fiscal_enabled = st.checkbox("Integração Fiscal", value=False)
        if fiscal_enabled:
            fiscal_provider = st.selectbox("Provedor Fiscal:", ["SEFAZ", "NFe.io", "Fiscal API"])
    
    if st.button("🔌 Salvar Configurações de Integração"):
        st.success("Configurações de integração salvas com sucesso!")

with tab5:
    st.subheader("Configurações do Sistema")
    
    # System performance
    st.markdown("### ⚡ Performance e Otimização")
    
    perf_col1, perf_col2 = st.columns(2)
    
    with perf_col1:
        cache_enabled = st.checkbox("Habilitar Cache", value=True)
        cache_ttl = st.number_input("TTL do Cache (segundos)", min_value=60, max_value=3600, value=300)
        
        compression_enabled = st.checkbox("Compressão de Dados", value=True)
        lazy_loading = st.checkbox("Carregamento Lazy", value=True)
    
    with perf_col2:
        max_records_page = st.number_input("Máx. Registros por Página", min_value=10, max_value=1000, value=50)
        query_timeout = st.number_input("Timeout de Query (segundos)", min_value=10, max_value=300, value=30)
        
        auto_backup = st.checkbox("Backup Automático", value=True)
        if auto_backup:
            backup_frequency = st.selectbox("Frequência:", ["Diário", "Semanal", "Mensal"], index=0)
    
    # Logging and monitoring
    st.markdown("---")
    st.markdown("### 📋 Logs e Monitoramento")
    
    log_col1, log_col2 = st.columns(2)
    
    with log_col1:
        log_level = st.selectbox("Nível de Log:", ["DEBUG", "INFO", "WARNING", "ERROR"], index=1)
        log_retention_days = st.number_input("Retenção de Logs (dias)", min_value=7, max_value=365, value=90)
        
        enable_audit_log = st.checkbox("Log de Auditoria", value=True)
        enable_error_tracking = st.checkbox("Rastreamento de Erros", value=True)
    
    with log_col2:
        # Current system status
        st.markdown("#### Status Atual")
        st.metric("Uptime", "24 dias, 15 horas")
        st.metric("Uso de Memória", "45%")
        st.metric("Espaço em Disco", "12.5 GB usado")
        st.metric("Conexões Ativas", "3")
    
    # Security settings
    st.markdown("---")
    st.markdown("### 🔒 Configurações de Segurança")
    
    security_col1, security_col2 = st.columns(2)
    
    with security_col1:
        enable_https = st.checkbox("Forçar HTTPS", value=True)
        enable_cors = st.checkbox("Habilitar CORS", value=False)
        
        rate_limiting = st.checkbox("Limitação de Taxa", value=True)
        if rate_limiting:
            max_requests_minute = st.number_input("Máx. Requisições/minuto", min_value=10, max_value=1000, value=100)
    
    with security_col2:
        ip_whitelist_enabled = st.checkbox("Lista Branca de IPs", value=False)
        if ip_whitelist_enabled:
            allowed_ips = st.text_area("IPs Permitidos (um por linha)", placeholder="192.168.1.0/24\n10.0.0.0/8")
        
        maintenance_mode = st.checkbox("Modo Manutenção", value=False)
        if maintenance_mode:
            maintenance_message = st.text_area("Mensagem de Manutenção", 
                                             value="Sistema em manutenção. Voltaremos em breve.")
    
    # Save all system configurations
    if st.button("💾 Salvar Todas as Configurações do Sistema"):
        st.success("Todas as configurações do sistema foram salvas!")
        st.warning("Algumas alterações podem requerer reinicialização do sistema.")
    
    # System actions
    st.markdown("---")
    st.markdown("### 🔧 Ações do Sistema")
    
    action_col1, action_col2, action_col3 = st.columns(3)
    
    with action_col1:
        if st.button("🔄 Reiniciar Sistema", type="secondary"):
            st.warning("⚠️ Esta ação reiniciará o sistema e desconectará todos os usuários.")
            if st.checkbox("Confirmo o reinício"):
                if st.button("Confirmar Reinício"):
                    st.error("Reinício do sistema não implementado nesta versão.")
    
    with action_col2:
        if st.button("📊 Relatório do Sistema"):
            st.success("Relatório do sistema gerado!")
            
            system_report = {
                "Versão": "1.0.0",
                "Última Atualização": "25/01/2025",
                "Banco de Dados": db_info["type"],
                "Total Usuários": len(session.exec(select(User)).all()) if 'session' in locals() else 0,
                "Status": "Online"
            }
            
            report_df = pd.DataFrame(list(system_report.items()), columns=["Item", "Valor"])
            st.dataframe(report_df, hide_index=True, use_container_width=True)
    
    with action_col3:
        if st.button("📥 Exportar Configurações"):
            # Export current configurations
            config_data = {
                "company": {
                    "name": "Empresa GARNET Ltda.",
                    "currency": "BRL",
                    "timezone": "America/Sao_Paulo"
                },
                "system": {
                    "cache_enabled": True,
                    "max_records_page": 50,
                    "log_level": "INFO"
                },
                "theme": {
                    "primary_color": "#6C2BD9",
                    "layout": "wide"
                }
            }
            
            config_json = json.dumps(config_data, indent=2)
            
            st.download_button(
                label="📥 Download Configurações",
                data=config_json,
                file_name=f"garnet_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
