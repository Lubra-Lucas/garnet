
import streamlit as st
from sqlmodel import Session, select
from db import engine
from models import QuoteRequest, QuoteItem, Supplier
from auth import has_permission
import pandas as pd
from datetime import datetime
from services.pdf_generator import generate_quote_request_pdf
import os

st.set_page_config(page_title="Solicitação de Orçamento - GARNET", page_icon="💰", layout="wide")

if "user" not in st.session_state:
    st.switch_page("app.py")

# Page header
st.markdown("""
<div style="padding: 1rem 0 2rem 0; border-bottom: 1px solid #E8E8E8; margin-bottom: 2rem;">
    <h1 style="margin: 0; color: #2E4A6B; font-weight: 300;">💰 Solicitação de Orçamento</h1>
    <p style="margin: 0.5rem 0 0 0; color: #666; font-size: 1.1rem;">Gerenciamento de solicitações de orçamento para fornecedores</p>
</div>
""", unsafe_allow_html=True)

# Tabs
tab1, tab2 = st.tabs(["📋 Solicitações", "➕ Nova Solicitação"])

with tab1:
    st.subheader("📋 Solicitações de Orçamento Cadastradas")
    
    with Session(engine) as session:
        quote_requests = session.exec(select(QuoteRequest)).all()
        
        if not quote_requests:
            st.info("Nenhuma solicitação de orçamento cadastrada.")
        else:
            # Create DataFrame for display
            quotes_data = []
            for qr in quote_requests:
                supplier = session.get(Supplier, qr.supplier_id)
                quotes_data.append({
                    "ID": qr.id,
                    "Número": qr.request_number,
                    "Fornecedor": supplier.name if supplier else "N/A",
                    "Data": qr.request_date.strftime("%d/%m/%Y") if qr.request_date else "",
                    "Status": qr.status,
                    "Itens": len(qr.items) if qr.items else 0
                })
            
            df = pd.DataFrame(quotes_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Quote details
            st.markdown("---")
            st.subheader("Detalhes da Solicitação")
            
            selected_quote_id = st.selectbox(
                "Selecione uma solicitação:",
                options=[q["ID"] for q in quotes_data],
                format_func=lambda x: next((q["Número"] for q in quotes_data if q["ID"] == x), "")
            )
            
            if selected_quote_id:
                quote = session.get(QuoteRequest, selected_quote_id)
                supplier = session.get(Supplier, quote.supplier_id)
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Número", quote.request_number)
                    st.metric("Fornecedor", supplier.name if supplier else "N/A")
                
                with col2:
                    st.metric("Data", quote.request_date.strftime("%d/%m/%Y") if quote.request_date else "")
                    st.metric("Status", quote.status)
                
                with col3:
                    st.metric("Total de Itens", len(quote.items) if quote.items else 0)
                
                if quote.notes:
                    st.text_area("Observações", value=quote.notes, disabled=True, height=100)
                
                # Items table
                st.markdown("#### Itens da Solicitação")
                
                if quote.items:
                    items_data = []
                    for item in quote.items:
                        items_data.append({
                            "Tipo": item.item_type,
                            "Nome do Item": item.item_name,
                            "Químico": item.chemical_name or "-",
                            "Comercial": item.commercial_name or "-",
                            "Quantidade": item.quantity
                        })
                    
                    items_df = pd.DataFrame(items_data)
                    st.dataframe(items_df, use_container_width=True, hide_index=True)
                    
                    # Generate PDF button
                    if st.button("📄 Gerar PDF da Solicitação", type="primary"):
                        try:
                            pdf_path = generate_quote_request_pdf(quote, supplier, quote.items)
                            
                            with open(pdf_path, "rb") as pdf_file:
                                pdf_bytes = pdf_file.read()
                                
                            st.download_button(
                                label="⬇️ Baixar PDF",
                                data=pdf_bytes,
                                file_name=f"Solicitacao_Orcamento_{quote.request_number}.pdf",
                                mime="application/pdf"
                            )
                            
                            st.success("PDF gerado com sucesso!")
                            
                            # Clean up temporary file
                            if os.path.exists(pdf_path):
                                os.remove(pdf_path)
                                
                        except Exception as e:
                            st.error(f"Erro ao gerar PDF: {str(e)}")
                else:
                    st.info("Nenhum item cadastrado para esta solicitação.")

with tab2:
    st.subheader("➕ Nova Solicitação de Orçamento")
    
    with Session(engine) as session:
        suppliers = session.exec(select(Supplier)).all()
        
        if not suppliers:
            st.warning("⚠️ Nenhum fornecedor cadastrado. Por favor, cadastre fornecedores primeiro.")
        else:
            with st.form("new_quote_request_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    request_number = st.text_input("Número da Solicitação *", placeholder="Ex: SOL-001")
                    
                    supplier_options = {s.id: f"{s.code} - {s.name}" for s in suppliers}
                    selected_supplier_id = st.selectbox(
                        "Fornecedor *",
                        options=list(supplier_options.keys()),
                        format_func=lambda x: supplier_options[x]
                    )
                
                with col2:
                    request_date = st.date_input("Data da Solicitação *", value=datetime.now())
                    status = st.selectbox("Status", ["Pendente", "Enviada", "Em Análise", "Respondida", "Cancelada"])
                
                notes = st.text_area("Observações", placeholder="Observações gerais sobre a solicitação...")
                
                st.markdown("---")
                st.markdown("#### Itens da Solicitação")
                
                # Initialize items in session state
                if "quote_items" not in st.session_state:
                    st.session_state.quote_items = []
                
                # Add item section
                st.markdown("**Adicionar Item**")
                
                item_col1, item_col2, item_col3, item_col4 = st.columns([2, 2, 2, 2])
                
                with item_col1:
                    item_type = st.selectbox("Tipo *", ["Matéria-Prima", "Embalagem", "Outro"], key="new_item_type")
                
                with item_col2:
                    item_name = st.text_input("Nome do Item *", placeholder="Ex: Óleo Essencial", key="new_item_name")
                
                with item_col3:
                    chemical_name = st.text_input("Nome Químico", placeholder="Ex: Citrus aurantium", key="new_chemical_name")
                
                with item_col4:
                    commercial_name = st.text_input("Nome Comercial", placeholder="Ex: OE Laranja Doce", key="new_commercial_name")
                
                quantity_col, add_col = st.columns([3, 1])
                
                with quantity_col:
                    quantity = st.number_input("Quantidade *", min_value=0.0, step=1.0, key="new_quantity")
                
                with add_col:
                    st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                    if st.form_submit_button("➕ Adicionar Item", use_container_width=True):
                        if item_name and quantity > 0:
                            st.session_state.quote_items.append({
                                "item_type": item_type,
                                "item_name": item_name,
                                "chemical_name": chemical_name,
                                "commercial_name": commercial_name,
                                "quantity": quantity
                            })
                            st.rerun()
                        else:
                            st.error("Preencha o nome do item e a quantidade.")
                
                # Display added items
                if st.session_state.quote_items:
                    st.markdown("**Itens Adicionados:**")
                    
                    items_display = []
                    for idx, item in enumerate(st.session_state.quote_items):
                        items_display.append({
                            "#": idx + 1,
                            "Tipo": item["item_type"],
                            "Nome": item["item_name"],
                            "Químico": item["chemical_name"] or "-",
                            "Comercial": item["commercial_name"] or "-",
                            "Quantidade": item["quantity"]
                        })
                    
                    st.dataframe(pd.DataFrame(items_display), use_container_width=True, hide_index=True)
                    
                    if st.form_submit_button("🗑️ Limpar Todos os Itens"):
                        st.session_state.quote_items = []
                        st.rerun()
                
                st.markdown("---")
                
                # Submit button
                submitted = st.form_submit_button("💾 Salvar Solicitação", type="primary", use_container_width=True)
                
                if submitted:
                    if not request_number:
                        st.error("⚠️ Número da solicitação é obrigatório.")
                    elif not st.session_state.quote_items:
                        st.error("⚠️ Adicione pelo menos um item à solicitação.")
                    else:
                        try:
                            # Create quote request
                            new_quote = QuoteRequest(
                                code=request_number,  # Usando request_number como code
                                request_number=request_number,
                                supplier_id=selected_supplier_id,
                                request_date=request_date,
                                status=status,
                                notes=notes
                            )
                            
                            session.add(new_quote)
                            session.commit()
                            session.refresh(new_quote)
                            
                            # Add items
                            for item_data in st.session_state.quote_items:
                                new_item = QuoteItem(
                                    quote_request_id=new_quote.id,
                                    item_type=item_data["item_type"],
                                    item_name=item_data["item_name"],
                                    chemical_name=item_data["chemical_name"],
                                    commercial_name=item_data["commercial_name"],
                                    min_quantity=item_data["quantity"],
                                    unit_price=0.0,
                                    total_price_with_tax=0.0
                                )
                                session.add(new_item)
                            
                            session.commit()
                            
                            # Clear items from session state
                            st.session_state.quote_items = []
                            
                            st.success(f"✅ Solicitação de orçamento '{request_number}' criada com sucesso!")
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"❌ Erro ao salvar solicitação: {str(e)}")
