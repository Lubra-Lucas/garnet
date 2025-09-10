# services/io_export.py
import pandas as pd
import streamlit as st
from sqlmodel import Session, select
from models import *
from io import BytesIO
from datetime import datetime
from services.reports import generate_stock_report, generate_supplier_performance_report

def export_suppliers_to_excel(session: Session) -> BytesIO:
    """Export all suppliers to Excel"""
    suppliers = session.exec(select(Supplier)).all()
    
    data = []
    for supplier in suppliers:
        data.append({
            "ID": supplier.id,
            "Nome": supplier.name,
            "CNPJ": supplier.cnpj,
            "Telefone": supplier.phone,
            "Email": supplier.email,
            "Contato": supplier.contact,
            "Endereço": supplier.address,
            "Condições Pagamento": supplier.payment_terms,
            "Lead Time (dias)": supplier.avg_leadtime_days,
            "Certificações": supplier.certifications,
            "Observações": supplier.notes,
            "Status": supplier.status,
            "Data Criação": supplier.created_at
        })
    
    df = pd.DataFrame(data)
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Fornecedores', index=False)
    
    output.seek(0)
    return output

def export_raw_materials_to_excel(session: Session) -> BytesIO:
    """Export all raw materials to Excel"""
    # Join with supplier data
    query = select(RawMaterial, Supplier.name).outerjoin(
        Supplier, RawMaterial.supplier_id == Supplier.id
    )
    results = session.exec(query).all()
    
    data = []
    for rm, supplier_name in results:
        data.append({
            "ID": rm.id,
            "Código": rm.code,
            "Nome Usual": rm.name_usual,
            "Nome Químico": rm.name_chemical,
            "Fornecedor": supplier_name,
            "Unidade Base": rm.base_unit,
            "Preço Base": rm.base_price,
            "Densidade": rm.density,
            "Fator Conversão": rm.conv_factor,
            "Validade (dias)": rm.shelf_life_days,
            "Localização": rm.location,
            "Status": rm.status,
            "Data Criação": rm.created_at
        })
    
    df = pd.DataFrame(data)
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Matérias-Primas', index=False)
    
    output.seek(0)
    return output

def export_products_to_excel(session: Session) -> BytesIO:
    """Export all products to Excel"""
    products = session.exec(select(Product)).all()
    
    data = []
    for product in products:
        data.append({
            "ID": product.id,
            "Código": product.code,
            "Nome": product.name,
            "Cliente": product.client,
            "Categoria": product.category,
            "Peso Unitário": product.unit_weight,
            "UOM": product.unit_uom,
            "Peso Lote Padrão": product.std_batch_weight,
            "Status": product.status,
            "Data Criação": product.created_at
        })
    
    df = pd.DataFrame(data)
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Produtos', index=False)
    
    output.seek(0)
    return output

def export_stock_to_excel(session: Session) -> BytesIO:
    """Export stock report to Excel"""
    df = generate_stock_report(session)
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Estoque', index=False)
    
    output.seek(0)
    return output

def export_production_orders_to_excel(session: Session) -> BytesIO:
    """Export production orders to Excel"""
    query = select(ProductionOrder, Product.name).join(
        Product, ProductionOrder.product_id == Product.id
    )
    results = session.exec(query).all()
    
    data = []
    for po, product_name in results:
        data.append({
            "ID": po.id,
            "Código": po.code,
            "Produto": product_name,
            "Quantidade": po.qty_to_produce,
            "Lote Planejado": po.planned_lot,
            "Data Início": po.start_date,
            "Data Fim": po.end_date,
            "Centro Trabalho": po.workcenter,
            "Status": po.status,
            "Criado Por": po.created_by,
            "Data Criação": po.created_at
        })
    
    df = pd.DataFrame(data)
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Ordens_Produção', index=False)
    
    output.seek(0)
    return output

def export_purchase_orders_to_excel(session: Session) -> BytesIO:
    """Export purchase orders to Excel"""
    # Get purchase orders with supplier info
    po_query = select(PurchaseOrder, Supplier.name).join(
        Supplier, PurchaseOrder.supplier_id == Supplier.id
    )
    po_results = session.exec(po_query).all()
    
    po_data = []
    for po, supplier_name in po_results:
        po_data.append({
            "ID": po.id,
            "Código": po.code,
            "Fornecedor": supplier_name,
            "Data Pedido": po.order_date,
            "Status": po.status,
            "Condições Pagamento": po.payment_terms,
            "Valor Total": po.total_value,
            "Data Criação": po.created_at
        })
    
    # Get purchase order items
    item_query = select(
        PurchaseItem, PurchaseOrder.code, RawMaterial.code, RawMaterial.name_usual
    ).join(
        PurchaseOrder, PurchaseItem.po_id == PurchaseOrder.id
    ).join(
        RawMaterial, PurchaseItem.raw_material_id == RawMaterial.id
    )
    item_results = session.exec(item_query).all()
    
    item_data = []
    for item, po_code, rm_code, rm_name in item_results:
        item_data.append({
            "ID Item": item.id,
            "Código Pedido": po_code,
            "Código MP": rm_code,
            "Matéria-Prima": rm_name,
            "Quantidade": item.qty,
            "UOM": item.uom,
            "Preço": item.price,
            "Data Entrega": item.due_date,
            "Qtd Recebida": item.received_qty
        })
    
    po_df = pd.DataFrame(po_data)
    item_df = pd.DataFrame(item_data)
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        po_df.to_excel(writer, sheet_name='Pedidos_Compra', index=False)
        item_df.to_excel(writer, sheet_name='Itens_Pedidos', index=False)
    
    output.seek(0)
    return output

def export_comprehensive_report(session: Session) -> BytesIO:
    """Export comprehensive report with multiple sheets"""
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Stock report
        stock_df = generate_stock_report(session)
        stock_df.to_excel(writer, sheet_name='Estoque', index=False)
        
        # Supplier performance
        supplier_df = generate_supplier_performance_report(session)
        supplier_df.to_excel(writer, sheet_name='Performance_Fornecedores', index=False)
        
        # Production orders summary
        po_query = select(ProductionOrder, Product.name).join(
            Product, ProductionOrder.product_id == Product.id
        )
        po_results = session.exec(po_query).all()
        
        po_data = []
        for po, product_name in po_results:
            po_data.append({
                "Código": po.code,
                "Produto": product_name,
                "Quantidade": po.qty_to_produce,
                "Status": po.status,
                "Data Início": po.start_date,
                "Data Fim": po.end_date
            })
        
        if po_data:
            po_df = pd.DataFrame(po_data)
            po_df.to_excel(writer, sheet_name='Ordens_Produção', index=False)
        
        # Purchase orders summary
        purchase_query = select(PurchaseOrder, Supplier.name).join(
            Supplier, PurchaseOrder.supplier_id == Supplier.id
        )
        purchase_results = session.exec(purchase_query).all()
        
        purchase_data = []
        for po, supplier_name in purchase_results:
            purchase_data.append({
                "Código": po.code,
                "Fornecedor": supplier_name,
                "Data": po.order_date,
                "Status": po.status,
                "Valor Total": po.total_value
            })
        
        if purchase_data:
            purchase_df = pd.DataFrame(purchase_data)
            purchase_df.to_excel(writer, sheet_name='Pedidos_Compra', index=False)
    
    output.seek(0)
    return output

def export_to_csv(df: pd.DataFrame) -> str:
    """Export DataFrame to CSV string"""
    return df.to_csv(index=False)

def create_download_button(df: pd.DataFrame, filename: str, button_text: str, file_format: str = "excel"):
    """Create download button for DataFrame"""
    if file_format == "excel":
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Dados', index=False)
        output.seek(0)
        
        st.download_button(
            label=button_text,
            data=output.getvalue(),
            file_name=f"{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    elif file_format == "csv":
        csv_data = df.to_csv(index=False)
        
        st.download_button(
            label=button_text,
            data=csv_data,
            file_name=f"{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
