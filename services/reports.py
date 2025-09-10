# services/reports.py
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlmodel import Session, select, func
from models import *
from datetime import date, datetime, timedelta
import streamlit as st

def get_dashboard_kpis(session_data: dict) -> dict:
    """Calculate main dashboard KPIs"""
    # This would normally take a session parameter, but for caching we pass serializable data
    # In a real implementation, you'd reconstruct the session or use a different caching strategy
    
    return {
        "total_suppliers": session_data.get("total_suppliers", 0),
        "total_raw_materials": session_data.get("total_raw_materials", 0),
        "total_products": session_data.get("total_products", 0),
        "active_production_orders": session_data.get("active_production_orders", 0),
        "pending_purchases": session_data.get("pending_purchases", 0),
        "stock_value": session_data.get("stock_value", 0.0),
        "otif_percentage": 95.2,  # Placeholder
        "inventory_turnover": 6.5,  # Placeholder
    }

def generate_session_data(session: Session) -> dict:
    """Generate data for caching"""
    total_suppliers = session.exec(select(func.count()).select_from(Supplier)).one()
    total_raw_materials = session.exec(select(func.count()).select_from(RawMaterial)).one()
    total_products = session.exec(select(func.count()).select_from(Product)).one()
    active_production_orders = session.exec(
        select(func.count()).select_from(ProductionOrder)
        .where(ProductionOrder.status.in_(["Planejada", "Em Produção"]))
    ).one()
    pending_purchases = session.exec(
        select(func.count()).select_from(PurchaseOrder)
        .where(PurchaseOrder.status.in_(["Aberto", "Enviado"]))
    ).one()
    
    # Calculate stock value
    stock_lots = session.exec(select(StockLot).where(StockLot.status == "Aprovado")).all()
    stock_value = sum(lot.qty * (lot.avg_cost or 0) for lot in stock_lots)
    
    return {
        "total_suppliers": total_suppliers,
        "total_raw_materials": total_raw_materials,
        "total_products": total_products,
        "active_production_orders": active_production_orders,
        "pending_purchases": pending_purchases,
        "stock_value": stock_value,
    }

def create_stock_value_chart(session: Session):
    """Create stock value distribution chart"""
    stock_data = []
    
    # Raw Materials stock
    rm_lots = session.exec(
        select(StockLot, RawMaterial.name_usual)
        .join(RawMaterial, StockLot.item_id == RawMaterial.id)
        .where(StockLot.item_type == "MP")
        .where(StockLot.status == "Aprovado")
    ).all()
    
    for lot, rm_name in rm_lots:
        stock_data.append({
            "type": "Matéria-Prima",
            "name": rm_name,
            "value": lot.qty * (lot.avg_cost or 0),
            "qty": lot.qty
        })
    
    # Finished Products stock
    pa_lots = session.exec(
        select(StockLot, Product.name)
        .join(Product, StockLot.item_id == Product.id)
        .where(StockLot.item_type == "PA")
        .where(StockLot.status == "Aprovado")
    ).all()
    
    for lot, product_name in pa_lots:
        stock_data.append({
            "type": "Produto Acabado",
            "name": product_name,
            "value": lot.qty * (lot.avg_cost or 0),
            "qty": lot.qty
        })
    
    if stock_data:
        df = pd.DataFrame(stock_data)
        
        # Pie chart by type
        type_summary = df.groupby("type")["value"].sum().reset_index()
        fig_pie = px.pie(type_summary, values="value", names="type", 
                        title="Distribuição do Valor do Estoque")
        
        # Bar chart top items by value
        top_items = df.nlargest(10, "value")
        fig_bar = px.bar(top_items, x="value", y="name", orientation="h",
                        title="Top 10 Itens por Valor em Estoque",
                        color="type")
        
        return fig_pie, fig_bar
    
    return None, None

def create_production_timeline_chart(session: Session):
    """Create production orders timeline chart"""
    pos = session.exec(
        select(ProductionOrder, Product.name)
        .join(Product, ProductionOrder.product_id == Product.id)
        .where(ProductionOrder.status.in_(["Planejada", "Em Produção", "Concluída"]))
    ).all()
    
    if not pos:
        return None
    
    timeline_data = []
    for po, product_name in pos:
        start_date = po.start_date or date.today()
        end_date = po.end_date or (start_date + timedelta(days=7))
        
        timeline_data.append({
            "Task": f"{po.code} - {product_name}",
            "Start": start_date,
            "Finish": end_date,
            "Status": po.status
        })
    
    df = pd.DataFrame(timeline_data)
    
    fig = px.timeline(df, x_start="Start", x_end="Finish", y="Task", color="Status",
                     title="Timeline de Ordens de Produção")
    fig.update_yaxes(autorange="reversed")
    
    return fig

def generate_session_data(session: Session) -> dict:
    """Generate session data for dashboard KPIs"""
    from services.business import calculate_stock_value
    
    # Count suppliers
    total_suppliers = session.exec(select(func.count(Supplier.id)).where(Supplier.status == "ativo")).first() or 0
    
    # Count raw materials
    total_raw_materials = session.exec(select(func.count(RawMaterial.id)).where(RawMaterial.status == "ativo")).first() or 0
    
    # Count products
    total_products = session.exec(select(func.count(Product.id)).where(Product.status == "ativo")).first() or 0
    
    # Count active production orders
    active_production_orders = session.exec(
        select(func.count(ProductionOrder.id)).where(
            ProductionOrder.status.in_(["Planejada", "Em Produção"])
        )
    ).first() or 0
    
    # Count pending purchases
    pending_purchases = session.exec(
        select(func.count(PurchaseOrder.id)).where(
            PurchaseOrder.status.in_(["Rascunho", "Enviado"])
        )
    ).first() or 0
    
    # Calculate stock value
    stock_value = calculate_stock_value(session)["total_value"]
    
    return {
        "total_suppliers": total_suppliers,
        "total_raw_materials": total_raw_materials,
        "total_products": total_products,
        "active_production_orders": active_production_orders,
        "pending_purchases": pending_purchases,
        "stock_value": stock_value,
    }

def generate_stock_report(session: Session) -> pd.DataFrame:
    """Generate comprehensive stock report"""
    stock_data = []
    
    # Raw Materials
    rm_stock = session.exec(
        select(StockLot, RawMaterial.code, RawMaterial.name_usual, Supplier.name)
        .join(RawMaterial, StockLot.item_id == RawMaterial.id)
        .outerjoin(Supplier, RawMaterial.supplier_id == Supplier.id)
        .where(StockLot.item_type == "MP")
    ).all()
    
    for lot, rm_code, rm_name, supplier_name in rm_stock:
        stock_data.append({
            "Tipo": "Matéria-Prima",
            "Código": rm_code,
            "Nome": rm_name,
            "Lote": lot.lot_code,
            "Quantidade": lot.qty,
            "UOM": lot.uom,
            "Status": lot.status,
            "Validade": lot.expiry,
            "Localização": lot.location,
            "Custo Médio": lot.avg_cost,
            "Valor Total": lot.qty * (lot.avg_cost or 0),
            "Fornecedor": supplier_name
        })
    
    # Finished Products
    pa_stock = session.exec(
        select(StockLot, Product.code, Product.name)
        .join(Product, StockLot.item_id == Product.id)
        .where(StockLot.item_type == "PA")
    ).all()
    
    for lot, product_code, product_name in pa_stock:
        stock_data.append({
            "Tipo": "Produto Acabado",
            "Código": product_code,
            "Nome": product_name,
            "Lote": lot.lot_code,
            "Quantidade": lot.qty,
            "UOM": lot.uom,
            "Status": lot.status,
            "Validade": lot.expiry,
            "Localização": lot.location,
            "Custo Médio": lot.avg_cost,
            "Valor Total": lot.qty * (lot.avg_cost or 0),
            "Fornecedor": None
        })
    
    return pd.DataFrame(stock_data)

def generate_supplier_performance_report(session: Session) -> pd.DataFrame:
    """Generate supplier performance report"""
    suppliers = session.exec(select(Supplier)).all()
    performance_data = []
    
    for supplier in suppliers:
        # Count purchase orders
        total_pos = session.exec(
            select(func.count(PurchaseOrder.id))
            .where(PurchaseOrder.supplier_id == supplier.id)
        ).one()
        
        # Count on-time deliveries (placeholder logic)
        on_time_deliveries = int(total_pos * 0.85)  # Assuming 85% on-time rate
        
        # Calculate total purchase value
        total_value = session.exec(
            select(func.coalesce(func.sum(PurchaseOrder.total_value), 0))
            .where(PurchaseOrder.supplier_id == supplier.id)
        ).one()
        
        performance_data.append({
            "Fornecedor": supplier.name,
            "CNPJ": supplier.cnpj,
            "Total Pedidos": total_pos,
            "Entregas Pontuais": on_time_deliveries,
            "% Pontualidade": (on_time_deliveries / total_pos * 100) if total_pos > 0 else 0,
            "Valor Total": total_value,
            "Lead Time Médio": supplier.avg_leadtime_days,
            "Contato": supplier.contact,
            "Status": supplier.status
        })
    
    return pd.DataFrame(performance_data)
