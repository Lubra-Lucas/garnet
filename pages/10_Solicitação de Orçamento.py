
# pages/10_SolicitacaoOrcamento.py
import streamlit as st
from auth import require_login, has_permission
from sqlmodel import select
from db import get_session
from models import QuoteRequest, QuoteItem, Supplier, PurchaseOrder, PurchaseItem
import pandas as pd
from datetime import date, timedelta

# Require login for this page
user = require_login()

st.set_page_config(page_title="GARNET - Solicitação de Orçamento", layout="wide")

# Professional page header
st.markdown("""
<div style="padding: 1rem 0 2rem 0; border-bottom: 1px solid #E8E8E8; margin-bottom: 2rem;">
    <h1 style="margin: 0; color: #2E4A6B; font-weight: 300;">Solicitação de Orçamento</h1>
    <p style="margin: 0.5rem 0 0 0; color: #666; font-size: 1.1rem;">Gestão de cotações e comparação de propostas</p>
</div>
""", unsafe_allow_html=True)

# Clean tabs without icons
tab1, tab2 = st.tabs(["Orçamentos Solicitados", "Nova Solicitação"])

with tab1:
    st.subheader("Orçamentos Solicitados")
    
    # Filters
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    
    with filter_col1:
        search_term = st.text_input("🔍 Buscar por código:", placeholder="OR-2024-001")
    
    with filter_col2:
        status_filter = st.selectbox("Status:", ["Todos", "Pendente", "Aprovado", "Arquivado"])
    
    with filter_col3:
        # Get suppliers for filter
        with get_session() as session:
            suppliers = session.exec(select(Supplier)).all()
            supplier_options = ["Todos"] + [s.name for s in suppliers]
        
        supplier_filter = st.selectbox("Fornecedor:", supplier_options)
    
    # Get quote requests
    with get_session() as session:
        query = select(QuoteRequest, Supplier.name).join(
            Supplier, QuoteRequest.supplier_id == Supplier.id
        )
        
        if search_term:
            query = query.where(QuoteRequest.code.ilike(f"%{search_term}%"))
        
        if status_filter != "Todos":
            query = query.where(QuoteRequest.status == status_filter)
        
        if supplier_filter != "Todos":
            query = query.where(Supplier.name == supplier_filter)
        
        results = session.exec(query.order_by(QuoteRequest.created_at.desc())).all()
    
    if results:
        quote_data = []
        for quote, supplier_name in results:
            # Count items in this quote
            item_count = len(session.exec(
                select(QuoteItem).where(QuoteItem.quote_request_id == quote.id)
            ).all())
            
            # Calculate total value
            items = session.exec(
                select(QuoteItem).where(QuoteItem.quote_request_id == quote.id)
            ).all()
            total_value = sum(item.total_price_with_tax for item in items)
            
            quote_data.append({
                "ID": quote.id,
                "Código": quote.code,
                "Fornecedor": supplier_name,
                "Data Solicitação": quote.request_date.strftime("%d/%m/%Y"),
                "Status": quote.status,
                "Itens": item_count,
                "Valor Total": f"R$ {total_value:.2f}",
                "Observações": quote.notes or "N/A"
            })
        
        df = pd.DataFrame(quote_data)
        st.dataframe(df, hide_index=True, use_container_width=True)
        
        # Action buttons for all quotes
        if results and has_permission("operator"):
            st.markdown("---")
            st.subheader("🔧 Ações para Orçamentos")
            
            # Edit quote section
            st.markdown("**Editar Orçamento**")
            edit_options = [f"{q.code} - {next(s for qr, s in results if qr.id == q.id)}" for q, _ in results]
            
            if edit_options:
                selected_edit = st.selectbox("Selecione orçamento para editar:", ["Selecione..."] + edit_options, key="edit_quote_select")
                
                if selected_edit != "Selecione...":
                    selected_quote_id = next(q.id for q, _ in results if f"{q.code} - {next(s for qr, s in results if qr.id == q.id)}" == selected_edit)
                    
                    edit_col1, edit_col2 = st.columns(2)
                    
                    with edit_col1:
                        if st.button("✏️ Editar Dados do Orçamento", use_container_width=True):
                            st.session_state.edit_quote_id = selected_quote_id
                            st.session_state.show_edit_quote_form = True
                    
                    with edit_col2:
                        if st.button("📝 Editar Itens do Orçamento", use_container_width=True):
                            st.session_state.edit_quote_items_id = selected_quote_id
                            st.session_state.show_edit_quote_items = True
        
        # Edit quote form
        if st.session_state.get('show_edit_quote_form') and st.session_state.get('edit_quote_id'):
            with get_session() as session:
                quote_to_edit = session.get(QuoteRequest, st.session_state.edit_quote_id)
                suppliers = session.exec(select(Supplier).where(Supplier.status == "ativo")).all()
                
                if quote_to_edit and suppliers:
                    st.markdown("### ✏️ Editar Dados do Orçamento")
                    
                    with st.form(f"edit_quote_{quote_to_edit.id}"):
                        edit_quote_col1, edit_quote_col2 = st.columns(2)
                        
                        with edit_quote_col1:
                            edit_code = st.text_input("Código da Solicitação *", value=quote_to_edit.code)
                            
                            # Current supplier
                            current_supplier = session.get(Supplier, quote_to_edit.supplier_id)
                            supplier_options = [f"{s.name} (ID: {s.id})" for s in suppliers]
                            current_supplier_option = f"{current_supplier.name} (ID: {current_supplier.id})"
                            current_index = supplier_options.index(current_supplier_option) if current_supplier_option in supplier_options else 0
                            
                            selected_supplier_option = st.selectbox("Fornecedor *", supplier_options, index=current_index)
                            selected_supplier_id = int(selected_supplier_option.split("ID: ")[1].split(")")[0])
                        
                        with edit_quote_col2:
                            edit_request_date = st.date_input("Data da Solicitação", value=quote_to_edit.request_date)
                            edit_status = st.selectbox("Status", ["Pendente", "Aprovado", "Arquivado"], 
                                                     index=["Pendente", "Aprovado", "Arquivado"].index(quote_to_edit.status))
                        
                        edit_notes = st.text_area("Observações", value=quote_to_edit.notes or "")
                        
                        form_col1, form_col2 = st.columns(2)
                        
                        with form_col1:
                            if st.form_submit_button("💾 Salvar Alterações", use_container_width=True):
                                if not edit_code:
                                    st.error("Código da solicitação é obrigatório.")
                                else:
                                    try:
                                        # Check if new code already exists (if changed)
                                        if edit_code != quote_to_edit.code:
                                            existing = session.exec(
                                                select(QuoteRequest).where(QuoteRequest.code == edit_code)
                                            ).first()
                                            
                                            if existing:
                                                st.error("Já existe uma solicitação com este código.")
                                                st.stop()
                                        
                                        # Update quote
                                        quote_to_edit.code = edit_code
                                        quote_to_edit.supplier_id = selected_supplier_id
                                        quote_to_edit.request_date = edit_request_date
                                        quote_to_edit.status = edit_status
                                        quote_to_edit.notes = edit_notes if edit_notes else None
                                        
                                        session.commit()
                                        st.success("Orçamento atualizado com sucesso!")
                                        st.session_state.show_edit_quote_form = False
                                        st.rerun()
                                    
                                    except Exception as e:
                                        st.error(f"Erro ao atualizar orçamento: {str(e)}")
                        
                        with form_col2:
                            if st.form_submit_button("❌ Cancelar", use_container_width=True):
                                st.session_state.show_edit_quote_form = False
                                st.rerun()
        
        # Edit quote items
        if st.session_state.get('show_edit_quote_items') and st.session_state.get('edit_quote_items_id'):
            with get_session() as session:
                quote_to_edit = session.get(QuoteRequest, st.session_state.edit_quote_items_id)
                quote_items = session.exec(
                    select(QuoteItem).where(QuoteItem.quote_request_id == quote_to_edit.id)
                ).all()
                
                if quote_to_edit:
                    st.markdown("### 📝 Editar Itens do Orçamento")
                    st.info(f"Editando itens do orçamento: {quote_to_edit.code}")
                    
                    # Initialize quote items in session state if not exists
                    if f"edit_quote_items_{quote_to_edit.id}" not in st.session_state:
                        st.session_state[f"edit_quote_items_{quote_to_edit.id}"] = []
                        for item in quote_items:
                            st.session_state[f"edit_quote_items_{quote_to_edit.id}"].append({
                                "id": item.id,
                                "type": item.item_type,
                                "name": item.item_name,
                                "chemical_name": item.chemical_name or "",
                                "commercial_name": item.commercial_name or "",
                                "min_qty": item.min_quantity,
                                "uom": item.uom,
                                "unit_price": item.unit_price,
                                "total_price": item.total_price_with_tax,
                                "validity": item.validity_days or 0,
                                "lead_time": item.lead_time_days or 0
                            })
                    
                    edit_items = st.session_state[f"edit_quote_items_{quote_to_edit.id}"]
                    
                    # Display items for editing
                    for i, item in enumerate(edit_items):
                        st.markdown(f"**Item {i+1}**")
                        item_col1, item_col2, item_col3, item_col4 = st.columns(4)
                        
                        with item_col1:
                            item["type"] = st.selectbox(f"Tipo {i+1}", ["Matéria-Prima", "Insumo"], 
                                                      index=0 if item["type"] == "Matéria-Prima" else 1, key=f"edit_quote_type_{quote_to_edit.id}_{i}")
                            item["name"] = st.text_input(f"Nome do {'Produto' if item['type'] == 'Insumo' else 'Item'} {i+1}", 
                                                       value=item["name"], key=f"edit_quote_name_{quote_to_edit.id}_{i}")
                            
                            if item["type"] == "Matéria-Prima":
                                item["chemical_name"] = st.text_input(f"Nome Químico {i+1}", 
                                                                    value=item["chemical_name"], key=f"edit_quote_chem_{quote_to_edit.id}_{i}")
                                item["commercial_name"] = st.text_input(f"Nome Comercial {i+1}", 
                                                                      value=item["commercial_name"], key=f"edit_quote_comm_{quote_to_edit.id}_{i}")
                        
                        with item_col2:
                            item["min_qty"] = st.number_input(f"Qtd Mínima {i+1}", min_value=0.0, value=item["min_qty"], 
                                                            step=0.1, key=f"edit_quote_qty_{quote_to_edit.id}_{i}")
                            item["uom"] = st.selectbox(f"UOM {i+1}", ["KG", "G", "L", "ML", "UN"], 
                                                     index=["KG", "G", "L", "ML", "UN"].index(item["uom"]), key=f"edit_quote_uom_{quote_to_edit.id}_{i}")
                            item["unit_price"] = st.number_input(f"Preço Unit. {i+1}", min_value=0.0, value=item["unit_price"], 
                                                               step=0.01, key=f"edit_quote_uprice_{quote_to_edit.id}_{i}")
                        
                        with item_col3:
                            item["total_price"] = st.number_input(f"Total c/ Imposto {i+1}", min_value=0.0, value=item["total_price"], 
                                                                step=0.01, key=f"edit_quote_tprice_{quote_to_edit.id}_{i}")
                            item["validity"] = st.number_input(f"Validade (dias) {i+1}", min_value=0, value=item["validity"], 
                                                             step=1, key=f"edit_quote_validity_{quote_to_edit.id}_{i}")
                            item["lead_time"] = st.number_input(f"Lead Time (dias) {i+1}", min_value=0, value=item["lead_time"], 
                                                              step=1, key=f"edit_quote_lead_{quote_to_edit.id}_{i}")
                        
                        with item_col4:
                            st.write("")  # Spacing
                            st.write("")  # Spacing
                            if st.button("🗑️ Remover", key=f"edit_quote_del_{quote_to_edit.id}_{i}"):
                                edit_items.pop(i)
                                st.rerun()
                    
                    # Add new item button
                    if st.button("➕ Adicionar Item", key=f"add_item_{quote_to_edit.id}"):
                        edit_items.append({
                            "id": None,  # New item
                            "type": "Matéria-Prima",
                            "name": "",
                            "chemical_name": "",
                            "commercial_name": "",
                            "min_qty": 0.0,
                            "uom": "KG",
                            "unit_price": 0.0,
                            "total_price": 0.0,
                            "validity": 0,
                            "lead_time": 0
                        })
                        st.rerun()
                    
                    # Calculate total
                    total_quote_value = sum(item["total_price"] for item in edit_items if item["name"] and item["total_price"] > 0)
                    st.info(f"💰 Valor Total do Orçamento: R$ {total_quote_value:.2f}")
                    
                    # Save/Cancel buttons
                    save_col1, save_col2 = st.columns(2)
                    
                    with save_col1:
                        if st.button("💾 Salvar Itens", use_container_width=True, key=f"save_items_{quote_to_edit.id}"):
                            try:
                                # Delete existing items
                                for item in quote_items:
                                    session.delete(item)
                                
                                # Add updated items
                                for item in edit_items:
                                    if item["name"]:
                                        quote_item = QuoteItem(
                                            quote_request_id=quote_to_edit.id,
                                            item_type=item["type"],
                                            item_name=item["name"],
                                            chemical_name=item["chemical_name"] if item["chemical_name"] else None,
                                            commercial_name=item["commercial_name"] if item["commercial_name"] else None,
                                            min_quantity=item["min_qty"],
                                            unit_price=item["unit_price"],
                                            total_price_with_tax=item["total_price"],
                                            validity_days=item["validity"] if item["validity"] > 0 else None,
                                            lead_time_days=item["lead_time"] if item["lead_time"] > 0 else None,
                                            uom=item["uom"]
                                        )
                                        session.add(quote_item)
                                
                                session.commit()
                                st.success("Itens do orçamento atualizados com sucesso!")
                                st.session_state.show_edit_quote_items = False
                                del st.session_state[f"edit_quote_items_{quote_to_edit.id}"]
                                st.rerun()
                            
                            except Exception as e:
                                st.error(f"Erro ao atualizar itens: {str(e)}")
                    
                    with save_col2:
                        if st.button("❌ Cancelar", use_container_width=True, key=f"cancel_items_{quote_to_edit.id}"):
                            st.session_state.show_edit_quote_items = False
                            del st.session_state[f"edit_quote_items_{quote_to_edit.id}"]
                            st.rerun()
        
        # Action buttons for pending quotes only
        pending_quotes = [quote for quote, _ in results if quote.status == "Pendente"]
        
        if pending_quotes and has_permission("operator"):
            st.markdown("---")
            st.subheader("🔧 Ações para Orçamentos Pendentes")
            
            action_col1, action_col2 = st.columns(2)
            
            with action_col1:
                st.markdown("**Aprovar Orçamento**")
                approve_options = [f"{q.code} - {next(s for qr, s in results if qr.id == q.id)}" for q in pending_quotes]
                
                if approve_options:
                    selected_approve = st.selectbox("Selecione orçamento para aprovar:", ["Selecione..."] + approve_options)
                    
                    if selected_approve != "Selecione...":
                        selected_quote_id = next(q.id for q in pending_quotes if f"{q.code} - {next(s for qr, s in results if qr.id == q.id)}" == selected_approve)
                        
                        if st.button("✅ Aprovar e Criar Pedido de Compra", use_container_width=True):
                            try:
                                with get_session() as session:
                                    # Update quote status
                                    quote_to_approve = session.get(QuoteRequest, selected_quote_id)
                                    quote_to_approve.status = "Aprovado"
                                    
                                    # Get quote items
                                    quote_items = session.exec(
                                        select(QuoteItem).where(QuoteItem.quote_request_id == selected_quote_id)
                                    ).all()
                                    
                                    # Generate PO code
                                    next_number = 1
                                    last_po = session.exec(
                                        select(PurchaseOrder).order_by(PurchaseOrder.id.desc())
                                    ).first()
                                    if last_po and last_po.code.startswith("PC-"):
                                        try:
                                            last_number = int(last_po.code.split("-")[-1])
                                            next_number = last_number + 1
                                        except:
                                            pass
                                    
                                    po_code = f"PC-{date.today().year}-{next_number:03d}"
                                    
                                    # Create purchase order
                                    total_po_value = sum(item.total_price_with_tax for item in quote_items)
                                    
                                    new_po = PurchaseOrder(
                                        code=po_code,
                                        supplier_id=quote_to_approve.supplier_id,
                                        order_date=date.today(),
                                        total_value=total_po_value,
                                        payment_terms="Conforme orçamento aprovado"
                                    )
                                    session.add(new_po)
                                    session.flush()
                                    
                                    # Create purchase items
                                    for item in quote_items:
                                        # Try to find matching raw material
                                        raw_material_id = None
                                        if item.item_type =="Matéria-Prima":
                                            from models import RawMaterial
                                            rm = session.exec(
                                                select(RawMaterial).where(
                                                    (RawMaterial.name_usual.ilike(f"%{item.item_name}%")) |
                                                    (RawMaterial.name_chemical.ilike(f"%{item.chemical_name}%") if item.chemical_name else False)
                                                )
                                            ).first()
                                            if rm:
                                                raw_material_id = rm.id
                                        
                                        if raw_material_id:
                                            purchase_item = PurchaseItem(
                                                po_id=new_po.id,
                                                raw_material_id=raw_material_id,
                                                qty=item.min_quantity,
                                                uom=item.uom,
                                                price=item.unit_price,
                                                due_date=date.today() + timedelta(days=item.lead_time_days or 30)
                                            )
                                            session.add(purchase_item)
                                    
                                    session.commit()
                                    st.success(f"Orçamento aprovado e Pedido de Compra '{po_code}' criado com sucesso!")
                                    st.rerun()
                            
                            except Exception as e:
                                st.error(f"Erro ao aprovar orçamento: {str(e)}")
            
            with action_col2:
                st.markdown("**Arquivar Orçamento**")
                archive_options = [f"{q.code} - {next(s for qr, s in results if qr.id == q.id)}" for q in pending_quotes]
                
                if archive_options:
                    selected_archive = st.selectbox("Selecione orçamento para arquivar:", ["Selecione..."] + archive_options)
                    
                    if selected_archive != "Selecione...":
                        selected_quote_id = next(q.id for q in pending_quotes if f"{q.code} - {next(s for qr, s in results if qr.id == q.id)}" == selected_archive)
                        
                        if st.button("📁 Arquivar Orçamento", use_container_width=True, type="secondary"):
                            try:
                                with get_session() as session:
                                    quote_to_archive = session.get(QuoteRequest, selected_quote_id)
                                    quote_to_archive.status = "Arquivado"
                                    session.commit()
                                    st.success("Orçamento arquivado com sucesso!")
                                    st.rerun()
                            
                            except Exception as e:
                                st.error(f"Erro ao arquivar orçamento: {str(e)}")
        
        # Detailed view
        st.markdown("---")
        st.subheader("Detalhes do Orçamento")
        
        if results:
            selected_quote_code = st.selectbox(
                "Selecione um orçamento para ver detalhes:",
                options=[quote.code for quote, _ in results]
            )
            
            selected_quote = next(quote for quote, _ in results if quote.code == selected_quote_code)
            selected_supplier = next(supplier_name for quote, supplier_name in results if quote.code == selected_quote_code)
            
            detail_col1, detail_col2 = st.columns(2)
            
            with detail_col1:
                st.markdown("**Informações do Orçamento**")
                st.text(f"Código: {selected_quote.code}")
                st.text(f"Fornecedor: {selected_supplier}")
                st.text(f"Data: {selected_quote.request_date.strftime('%d/%m/%Y')}")
                st.text(f"Status: {selected_quote.status}")
                st.text(f"Criado por: {selected_quote.created_by or 'Sistema'}")
            
            with detail_col2:
                st.markdown("**Observações**")
                st.text(selected_quote.notes or "Nenhuma observação")
            
            # Items in this quote request
            st.markdown("**Itens do Orçamento**")
            
            items = session.exec(
                select(QuoteItem).where(QuoteItem.quote_request_id == selected_quote.id)
            ).all()
            
            if items:
                items_data = []
                total_value = 0
                
                for item in items:
                    total_value += item.total_price_with_tax
                    
                    items_data.append({
                        "Tipo": "Matéria-Prima" if item.item_type == "Matéria-Prima" else "Produto",
                        "Nome do Item": item.item_name,
                        "Nome Químico": item.chemical_name or "N/A",
                        "Nome Comercial": item.commercial_name or "N/A",
                        "Qtd Mínima": f"{item.min_quantity} {item.uom}",
                        "Preço Unit.": f"R$ {item.unit_price:.2f}",
                        "Total c/ Imposto": f"R$ {item.total_price_with_tax:.2f}",
                        "Validade": f"{item.validity_days} dias" if item.validity_days else "N/A",
                        "Lead Time": f"{item.lead_time_days} dias" if item.lead_time_days else "N/A"
                    })
                
                items_df = pd.DataFrame(items_data)
                st.dataframe(items_df, hide_index=True, use_container_width=True)
                
                st.info(f"💰 Valor Total do Orçamento: R$ {total_value:.2f}")
            else:
                st.info("Este orçamento não possui itens cadastrados.")
    
    else:
        st.info("Nenhuma solicitação de orçamento encontrada.")

with tab2:
    st.subheader("Nova Solicitação de Orçamento")
    
    if not has_permission("operator"):
        st.error("Acesso negado.")
    else:
        with get_session() as session:
            suppliers = session.exec(select(Supplier).where(Supplier.status == "ativo")).all()
        
        if not suppliers:
            st.error("Nenhum fornecedor ativo encontrado.")
        else:
            # Initialize quote items in session state
            if "quote_items" not in st.session_state:
                st.session_state.quote_items = [{"type": "Matéria-Prima", "name": "", "chemical_name": "", "commercial_name": "", 
                                               "min_qty": 0.0, "uom": "KG", "unit_price": 0.0, "total_price": 0.0, 
                                               "validity": None, "lead_time": None}]
            
            # Form for quote request data
            with st.form("new_quote_request"):
                quote_col1, quote_col2 = st.columns(2)
                
                with quote_col1:
                    # Auto-generate quote code
                    next_number = 1
                    with get_session() as session:
                        last_quote = session.exec(
                            select(QuoteRequest).order_by(QuoteRequest.id.desc())
                        ).first()
                        if last_quote and last_quote.code.startswith("OR-"):
                            try:
                                last_number = int(last_quote.code.split("-")[-1])
                                next_number = last_number + 1
                            except:
                                pass
                    
                    suggested_code = f"OR-{date.today().year}-{next_number:03d}"
                    code = st.text_input("Código da Solicitação *", value=suggested_code)
                    
                    # Supplier selection
                    supplier_options = [f"{s.name} (ID: {s.id})" for s in suppliers]
                    selected_supplier_option = st.selectbox("Fornecedor *", supplier_options)
                    selected_supplier_id = int(selected_supplier_option.split("ID: ")[1].split(")")[0])
                
                with quote_col2:
                    request_date = st.date_input("Data da Solicitação", value=date.today())
                    notes = st.text_area("Observações", placeholder="Observações sobre a solicitação")
                
                submitted = st.form_submit_button("📋 Solicitar Orçamento", use_container_width=True)
            
            # Items management outside the form
            st.markdown("**Itens da Solicitação**")
            
            # Display quote items
            for i, item in enumerate(st.session_state.quote_items):
                st.markdown(f"**Item {i+1}**")
                item_col1, item_col2, item_col3, item_col4 = st.columns(4)
                
                with item_col1:
                    item["type"] = st.selectbox(f"Tipo {i+1}", ["Matéria-Prima", "Insumo"], 
                                              index=0 if item["type"] == "Matéria-Prima" else 1, key=f"quote_type_{i}")
                    item["name"] = st.text_input(f"Nome do {'Produto' if item['type'] == 'Insumo' else 'Item'} {i+1}", 
                                               value=item["name"], key=f"quote_name_{i}")
                    
                    if item["type"] == "Matéria-Prima":
                        item["chemical_name"] = st.text_input(f"Nome Químico {i+1}", 
                                                            value=item["chemical_name"], key=f"quote_chem_{i}")
                        item["commercial_name"] = st.text_input(f"Nome Comercial {i+1}", 
                                                              value=item["commercial_name"], key=f"quote_comm_{i}")
                
                with item_col2:
                    item["min_qty"] = st.number_input(f"Qtd Mínima {i+1}", min_value=0.0, value=item["min_qty"], 
                                                    step=0.1, key=f"quote_qty_{i}")
                    item["uom"] = st.selectbox(f"UOM {i+1}", ["KG", "G", "L", "ML", "UN"], 
                                             index=["KG", "G", "L", "ML", "UN"].index(item["uom"]), key=f"quote_uom_{i}")
                    item["unit_price"] = st.number_input(f"Preço Unit. {i+1}", min_value=0.0, value=item["unit_price"], 
                                                       step=0.01, key=f"quote_uprice_{i}")
                
                with item_col3:
                    item["total_price"] = st.number_input(f"Total c/ Imposto {i+1}", min_value=0.0, value=item["total_price"], 
                                                        step=0.01, key=f"quote_tprice_{i}")
                    item["validity"] = st.number_input(f"Validade (dias) {i+1}", min_value=0, value=item["validity"] or 0, 
                                                     step=1, key=f"quote_validity_{i}")
                    item["lead_time"] = st.number_input(f"Lead Time (dias) {i+1}", min_value=0, value=item["lead_time"] or 0, 
                                                      step=1, key=f"quote_lead_{i}")
                
                with item_col4:
                    st.write("")  # Spacing
                    st.write("")  # Spacing
                    if st.button("🗑️ Remover", key=f"quote_del_{i}"):
                        st.session_state.quote_items.pop(i)
                        st.rerun()
            
            # Add new item button
            if st.button("➕ Adicionar Item"):
                st.session_state.quote_items.append({"type": "Matéria-Prima", "name": "", "chemical_name": "", "commercial_name": "", 
                                                   "min_qty": 0.0, "uom": "KG", "unit_price": 0.0, "total_price": 0.0, 
                                                   "validity": None, "lead_time": None})
                st.rerun()
            
            # Calculate total
            total_quote_value = sum(item["total_price"] for item in st.session_state.quote_items if item["name"] and item["total_price"] > 0)
            st.info(f"💰 Valor Total da Solicitação: R$ {total_quote_value:.2f}")
            
            if submitted:
                    if not code:
                        st.error("Código da solicitação é obrigatório.")
                    elif not any(item["name"] for item in st.session_state.quote_items):
                        st.error("Adicione pelo menos um item à solicitação.")
                    else:
                        try:
                            with get_session() as session:
                                # Check if code already exists
                                existing = session.exec(
                                    select(QuoteRequest).where(QuoteRequest.code == code)
                                ).first()
                                
                                if existing:
                                    st.error("Já existe uma solicitação com este código.")
                                else:
                                    # Create quote request
                                    new_quote = QuoteRequest(
                                        code=code,
                                        supplier_id=selected_supplier_id,
                                        request_date=request_date,
                                        notes=notes if notes else None,
                                        created_by=user.get("username", "Sistema")
                                    )
                                    session.add(new_quote)
                                    session.flush()  # Get the ID
                                    
                                    # Add quote items
                                    for item in st.session_state.quote_items:
                                        if item["name"]:
                                            quote_item = QuoteItem(
                                                quote_request_id=new_quote.id,
                                                item_type=item["type"],
                                                item_name=item["name"],
                                                chemical_name=item["chemical_name"] if item["chemical_name"] else None,
                                                commercial_name=item["commercial_name"] if item["commercial_name"] else None,
                                                min_quantity=item["min_qty"],
                                                unit_price=item["unit_price"],
                                                total_price_with_tax=item["total_price"],
                                                validity_days=item["validity"] if item["validity"] and item["validity"] > 0 else None,
                                                lead_time_days=item["lead_time"] if item["lead_time"] and item["lead_time"] > 0 else None,
                                                uom=item["uom"]
                                            )
                                            session.add(quote_item)
                                    
                                    session.commit()
                                    st.success(f"Solicitação de orçamento '{code}' criada com sucesso!")
                                    
                                    # Clear session state
                                    del st.session_state.quote_items
                                    st.rerun()
                        
                        except Exception as e:
                            st.error(f"Erro ao criar solicitação: {str(e)}")


