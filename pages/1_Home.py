# pages/1_Home.py
import streamlit as st
from auth import require_login
from sqlmodel import Session, select
from db import engine
from services.reports import get_dashboard_kpis, generate_session_data, create_stock_value_chart
from models import Product, RawMaterial, Supplier
from utils.ui_components import render_page_header, create_metric_card
from utils.performance import PerformanceMonitor
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import date, datetime, timedelta
import pandas as pd

# Require login for this page
user = require_login()

st.set_page_config(page_title="GARNET - Dashboard", layout="wide")

# Professional page header using utility
render_page_header("Dashboard Principal", "Visão geral do sistema e indicadores operacionais")

# Welcome message
st.markdown(f"""
<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1.5rem; border-radius: 10px; margin: 1rem 0 2rem 0; text-align: center;">
    <h2 style="margin: 0; color: white; font-weight: 300;">👋 Bem-vindo, {user['name']}!</h2>
    <p style="margin: 0.5rem 0 0 0; color: white; opacity: 0.9;">Como está? Esperamos que tenha um excelente dia de trabalho!</p>
</div>
""", unsafe_allow_html=True)

# Generate real-time data for KPIs with performance monitoring
with PerformanceMonitor("Carregando dados do dashboard"):
    with Session(engine) as session:
        session_data = generate_session_data(session)
        # Get fresh KPIs without cache
        from services.business import calculate_stock_value

        # Calculate stock value directly without cache
        stock_value = calculate_stock_value(session)["total_value"]

        kpis = {
            "total_suppliers": session_data.get("total_suppliers", 0),
            "total_raw_materials": session_data.get("total_raw_materials", 0),
            "total_products": session_data.get("total_products", 0),
            "active_production_orders": session_data.get("active_production_orders", 0),
            "pending_purchases": session_data.get("pending_purchases", 0),
            "stock_value": stock_value,  # Always fresh value
            "otif_percentage": 95.2,  # Placeholder
            "inventory_turnover": 6.5,  # Placeholder
        }

# Professional KPI cards
col1, col2, col3, col4 = st.columns(4, gap="large")

with col1:
    st.markdown("""
    <div style="background: white; padding: 1.5rem; border-radius: 8px; border: 1px solid #E0E0E0; text-align: center;">
        <h3 style="margin: 0; color: #2E4A6B; font-size: 1.8rem; font-weight: 300;">{}</h3>
        <p style="margin: 0.5rem 0 0 0; color: #666; font-size: 0.9rem;">Fornecedores</p>
    </div>
    """.format(kpis["total_suppliers"]), unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div style="background: white; padding: 1.5rem; border-radius: 8px; border: 1px solid #E0E0E0; text-align: center;">
        <h3 style="margin: 0; color: #2E4A6B; font-size: 1.8rem; font-weight: 300;">{}</h3>
        <p style="margin: 0.5rem 0 0 0; color: #666; font-size: 0.9rem;">Matérias-Primas</p>
    </div>
    """.format(kpis["total_raw_materials"]), unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div style="background: white; padding: 1.5rem; border-radius: 8px; border: 1px solid #E0E0E0; text-align: center;">
        <h3 style="margin: 0; color: #2E4A6B; font-size: 1.8rem; font-weight: 300;">{}</h3>
        <p style="margin: 0.5rem 0 0 0; color: #666; font-size: 0.9rem;">Produtos</p>
    </div>
    """.format(kpis["total_products"]), unsafe_allow_html=True)

with col4:
    st.markdown("""
    <div style="background: white; padding: 1.5rem; border-radius: 8px; border: 1px solid #E0E0E0; text-align: center;">
        <h3 style="margin: 0; color: #2E4A6B; font-size: 1.8rem; font-weight: 300;">R$ {:,.0f}</h3>
        <p style="margin: 0.5rem 0 0 0; color: #666; font-size: 0.9rem;">Valor Estoque</p>
    </div>
    """.format(kpis["stock_value"]), unsafe_allow_html=True)

st.markdown("---")

# Secondary KPIs
col5, col6 = st.columns(2)

with col5:
    st.metric(
        label="🔄 Ordens Produção Ativas",
        value=kpis["active_production_orders"],
        help="Ordens de produção em andamento"
    )

with col6:
    st.metric(
        label="🛒 Pedidos Compra Pendentes",
        value=kpis["pending_purchases"],
        help="Pedidos de compra não finalizados"
    )

st.markdown("---")

# Charts section
st.subheader("📊 Análises Visuais")

chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    # Stock value distribution chart
    with Session(engine) as session:
        fig_pie, fig_bar = create_stock_value_chart(session)

        if fig_pie:
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Sem dados de estoque para exibir gráfico.")

with chart_col2:
    # Material delivery countdown
    st.markdown("### ⏳ Entregas Programadas")

    with Session(engine) as session:
        from models import PurchaseOrder, ProductionOrder

        # Get production orders that need materials
        upcoming_deliveries = session.exec(
            select(ProductionOrder, Product.name, Product.code)
            .join(Product, ProductionOrder.product_id == Product.id)
            .where(ProductionOrder.status.in_(["Planejada", "Em Produção"]))
            .where(ProductionOrder.start_date.isnot(None))
            .where(ProductionOrder.start_date >= date.today())
            .where(ProductionOrder.start_date <= date.today() + timedelta(days=30))
        ).all()

        if upcoming_deliveries:
            delivery_data = []
            for po, product_name, product_code in upcoming_deliveries:
                days_until = (po.start_date - date.today()).days
                delivery_data.append({
                    "Ordem": po.code,
                    "Produto": f"{product_code} - {product_name}",
                    "Data Início": po.start_date.strftime("%d/%m/%Y"),
                    "Dias Restantes": days_until,
                    "Status": "🔴 Crítico" if days_until <= 3 else "🟡 Atenção" if days_until <= 7 else "🟢 Normal"
                })

            delivery_df = pd.DataFrame(delivery_data)
            delivery_df = delivery_df.sort_values("Dias Restantes")

            st.dataframe(delivery_df, hide_index=True, use_container_width=True)
        else:
            st.info("Nenhuma entrega programada nos próximos 30 dias.")

# Notifications section
st.markdown("---")
st.subheader("🔔 Notificações e Pendências")

def get_notifications(session):
    """Get all pending notifications"""
    from models import Payable, Receivable, PurchaseOrder, ProductionOrder, StockLot
    from datetime import timedelta

    notifications = []
    today = date.today()

    # Overdue payables
    overdue_payables = session.exec(
        select(Payable).where(Payable.due_date < today).where(Payable.status == "Pendente")
    ).all()

    for payable in overdue_payables:
        days_overdue = (today - payable.due_date).days
        notifications.append({
            "type": "error",
            "icon": "💸",
            "message": f"Pagamento vencido há {days_overdue} dias: {payable.doc_ref} - R$ {payable.value:,.2f}",
            "priority": 100 + days_overdue
        })

    # Payables due in next 7 days
    upcoming_payables = session.exec(
        select(Payable).where(Payable.due_date >= today).where(Payable.due_date <= today + timedelta(days=7)).where(Payable.status == "Pendente")
    ).all()

    for payable in upcoming_payables:
        days_until = (payable.due_date - today).days
        if days_until <= 3:
            notifications.append({
                "type": "warning",
                "icon": "⚠️",
                "message": f"Pagamento vence em {days_until} dias: {payable.doc_ref} - R$ {payable.value:,.2f}",
                "priority": 80 + (3 - days_until)
            })

    # Overdue receivables
    overdue_receivables = session.exec(
        select(Receivable).where(Receivable.due_date < today).where(Receivable.status == "Pendente")
    ).all()

    for receivable in overdue_receivables:
        days_overdue = (today - receivable.due_date).days
        notifications.append({
            "type": "warning",
            "icon": "💰",
            "message": f"Recebimento em atraso há {days_overdue} dias: {receivable.doc_ref} - R$ {receivable.value:,.2f}",
            "priority": 70 + days_overdue
        })

    # Production orders ending soon
    ending_productions = session.exec(
        select(ProductionOrder, Product.name, Product.code)
        .join(Product, ProductionOrder.product_id == Product.id)
        .where(ProductionOrder.status.in_(["Planejada", "Em Produção"]))
        .where(ProductionOrder.end_date >= today)
        .where(ProductionOrder.end_date <= today + timedelta(days=3))
    ).all()

    for po, product_name, product_code in ending_productions:
        days_until = (po.end_date - today).days
        if po.status == "Em Produção":
            notifications.append({
                "type": "info",
                "icon": "🏭",
                "message": f"Produção {po.code} ({product_code}) termina em {days_until} dias - {po.qty_to_produce:,.0f} unidades",
                "priority": 60 + (3 - days_until)
            })
        elif days_until <= 1:
            notifications.append({
                "type": "warning",
                "icon": "🚨",
                "message": f"Produção {po.code} ({product_code}) deve iniciar em {days_until} dias",
                "priority": 75 + (1 - days_until)
            })

    # Purchase orders delayed
    delayed_purchases = session.exec(
        select(PurchaseOrder, Supplier.name)
        .join(Supplier, PurchaseOrder.supplier_id == Supplier.id)
        .where(PurchaseOrder.status == "Enviado")
        .where(PurchaseOrder.order_date < today - timedelta(days=15))
    ).all()

    for po, supplier_name in delayed_purchases:
        days_since = (today - po.order_date).days
        notifications.append({
            "type": "warning",
            "icon": "📦",
            "message": f"Pedido {po.code} ({supplier_name}) enviado há {days_since} dias sem confirmação",
            "priority": 50 + min(days_since - 15, 30)
        })

    # Expiring stock lots
    expiring_lots = session.exec(
        select(StockLot, RawMaterial.name_usual, RawMaterial.code)
        .join(RawMaterial, StockLot.item_id == RawMaterial.id)
        .where(StockLot.item_type == "MP")
        .where(StockLot.expiry.isnot(None))
        .where(StockLot.expiry <= today + timedelta(days=30))
        .where(StockLot.status == "Aprovado")
        .where(StockLot.qty > 0)
    ).all()

    for lot, rm_name, rm_code in expiring_lots:
        days_until_expiry = (lot.expiry - today).days
        if days_until_expiry < 0:
            notifications.append({
                "type": "error",
                "icon": "🚫",
                "message": f"Lote {lot.lot_code} ({rm_code}) vencido há {abs(days_until_expiry)} dias - {lot.qty:,.1f} {lot.uom}",
                "priority": 120 + abs(days_until_expiry)
            })
        elif days_until_expiry <= 7:
            notifications.append({
                "type": "warning",
                "icon": "⏰",
                "message": f"Lote {lot.lot_code} ({rm_code}) vence em {days_until_expiry} dias - {lot.qty:,.1f} {lot.uom}",
                "priority": 90 + (7 - days_until_expiry)
            })
        elif days_until_expiry <= 30:
            notifications.append({
                "type": "info",
                "icon": "📅",
                "message": f"Lote {lot.lot_code} ({rm_code}) vence em {days_until_expiry} dias - {lot.qty:,.1f} {lot.uom}",
                "priority": 40 + (30 - days_until_expiry)
            })

    # Low stock alerts (simplified)
    low_stock_lots = session.exec(
        select(StockLot, RawMaterial.name_usual, RawMaterial.code)
        .join(RawMaterial, StockLot.item_id == RawMaterial.id)
        .where(StockLot.item_type == "MP")
        .where(StockLot.status == "Aprovado")
        .where(StockLot.qty < 10)  # Simple threshold
        .where(StockLot.qty > 0)
    ).all()

    for lot, rm_name, rm_code in low_stock_lots:
        notifications.append({
            "type": "info",
            "icon": "📉",
            "message": f"Estoque baixo: {rm_code} - {lot.qty:,.1f} {lot.uom} restantes",
            "priority": 30
        })

    # Sort by priority (higher priority first)
    notifications.sort(key=lambda x: x["priority"], reverse=True)

    return notifications[:15]  # Limit to top 15 notifications

# Get notifications
with Session(engine) as session:
    notifications = get_notifications(session)

if notifications:
    # Group notifications by type
    critical_notifications = [n for n in notifications if n["type"] == "error"]
    warning_notifications = [n for n in notifications if n["type"] == "warning"]
    info_notifications = [n for n in notifications if n["type"] == "info"]

    # Display notifications in columns
    notif_col1, notif_col2 = st.columns(2)

    with notif_col1:
        st.markdown("**🚨 Críticas e Urgentes**")

        # Critical notifications
        if critical_notifications:
            for notif in critical_notifications[:5]:
                st.error(f"{notif['icon']} {notif['message']}")

        # Warning notifications
        if warning_notifications:
            for notif in warning_notifications[:5]:
                st.warning(f"{notif['icon']} {notif['message']}")

    with notif_col2:
        st.markdown("**ℹ️ Informativas**")

        # Info notifications
        if info_notifications:
            for notif in info_notifications[:8]:
                st.info(f"{notif['icon']} {notif['message']}")

        if not info_notifications:
            st.success("✅ Nenhuma pendência informativa no momento")

    # Summary metrics
    st.markdown("---")
    summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)

    with summary_col1:
        st.metric("🚨 Críticas", len(critical_notifications))

    with summary_col2:
        st.metric("⚠️ Avisos", len(warning_notifications))

    with summary_col3:
        st.metric("ℹ️ Informativas", len(info_notifications))

    with summary_col4:
        st.metric("📋 Total", len(notifications))

else:
    st.success("🎉 Parabéns! Não há pendências críticas no momento.")
    st.info("💡 Continue monitorando regularmente para manter a operação em dia.")

# Quick actions section
st.markdown("---")
st.subheader("⚡ Ações Rápidas")

action_col1, action_col2, action_col3, action_col4 = st.columns(4)

with action_col1:
    if st.button("➕ Nova Ordem Produção", use_container_width=True):
        st.switch_page("pages/7_OrdensProducao.py")

with action_col2:
    if st.button("🛒 Novo Pedido Compra", use_container_width=True):
        st.switch_page("pages/9_ComprasPedidos.py")

with action_col3:
    if st.button("📋 Verificar Estoque", use_container_width=True):
        st.switch_page("pages/6_Estoque.py")

with action_col4:
    if st.button("📊 Gerar Relatório", use_container_width=True):
        st.switch_page("pages/15_RelatoriosKPIs.py")

# System status footer
st.markdown("---")
with st.expander("ℹ️ Status do Sistema"):
    status_col1, status_col2, status_col3 = st.columns(3)

    with status_col1:
        st.markdown("**🗄️ Banco de Dados**")
        from db import get_db_info
        db_info = get_db_info()
        st.text(f"Tipo: {db_info['type']}")
        st.text(f"Status: ✅ Conectado")

    with status_col2:
        st.markdown("**👤 Usuário Atual**")
        st.text(f"Nome: {user['name']}")
        st.text(f"Perfil: {user['role'].title()}")

    with status_col3:
        st.markdown("**🕐 Última Atualização**")
        st.text(f"Dashboard: {datetime.now().strftime('%H:%M:%S')}")
        st.text("Status: ✅ Online")
