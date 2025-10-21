# pages/2_Fornecedores.py
import streamlit as st
from auth import require_login, has_permission
from sqlmodel import Session, select
from db import engine
from models import Supplier
from schema import SupplierCreate, SupplierUpdate
from services.io_import import import_suppliers_from_excel, generate_import_template
from services.io_export import export_suppliers_to_excel
from utils.ui_components import render_page_header, create_data_table, render_success_message, render_error_message
from utils.form_helpers import render_form_section, validate_form_data, create_filter_section
from utils.data_helpers import apply_dataframe_filters, format_dataframe_for_display
import pandas as pd
import os
from datetime import datetime

# Require login for this page
user = require_login()

st.set_page_config(page_title="GARNET - Fornecedores", layout="wide")

# Professional page header using utility
render_page_header("Gestão de Fornecedores", "Cadastro e controle de fornecedores e parceiros")

# Clean tabs without icons
tab1, tab2, tab3 = st.tabs(["Lista de Fornecedores", "Novo Cadastro", "Importar / Exportar"])

with tab1:
    # Clean section header
    st.markdown("""
    <div style="margin-bottom: 1.5rem;">
        <h3 style="margin: 0; color: #2E4A6B; font-weight: 400;">Fornecedores Cadastrados</h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Clean filters layout
    filter_col1, filter_col2, filter_col3 = st.columns([2, 1, 1])
    
    with filter_col1:
        search_term = st.text_input("Buscar por nome ou CNPJ", placeholder="Digite para filtrar...")
    
    with filter_col2:
        status_filter = st.selectbox("Status", ["Todos", "ativo", "inativo"])
    
    with filter_col3:
        st.write("")  # Spacing
        if st.button("Atualizar", use_container_width=True, type="secondary"):
            st.rerun()
    
    # Get suppliers with filters
    with Session(engine) as session:
        query = select(Supplier)
        
        if search_term:
            query = query.where(
                (Supplier.name.ilike(f"%{search_term}%")) |
                (Supplier.cnpj.ilike(f"%{search_term}%"))
            )
        
        if status_filter != "Todos":
            query = query.where(Supplier.status == status_filter)
        
        suppliers = session.exec(query.order_by(Supplier.name)).all()
    
    if suppliers:
        # Convert to DataFrame for display
        supplier_data = []
        for supplier in suppliers:
            supplier_data.append({
                "ID": supplier.id,
                "Nome": supplier.name,
                "CNPJ": supplier.cnpj,
                "Telefone": supplier.phone,
                "Email": supplier.email,
                "Contato": supplier.contact,
                
                "Status": supplier.status
            })
        
        df = pd.DataFrame(supplier_data)
        
        # Display as interactive table
        edited_df = st.data_editor(
            df,
            hide_index=True,
            use_container_width=True,
            disabled=["ID"] if not has_permission("manager") else [],
            column_config={
                "Status": st.column_config.SelectboxColumn(
                    "Status",
                    options=["ativo", "inativo"],
                    required=True
                )
            }
        )
        
        # Update button for managers
        if has_permission("manager"):
            if st.button("💾 Salvar Alterações"):
                with Session(engine) as session:
                    for idx, row in edited_df.iterrows():
                        supplier = session.get(Supplier, row["ID"])
                        if supplier:
                            # Update fields that might have changed
                            supplier.name = row["Nome"]
                            supplier.cnpj = row["CNPJ"]
                            supplier.phone = row["Telefone"]
                            supplier.email = row["Email"]
                            supplier.contato = row["Contato"]
                            supplier.status = row["Status"]
                    
                    session.commit()
                    st.success("Alterações salvas com sucesso!")
                    st.rerun()
        
        # Edit and Delete section
        if has_permission("operator"):
            st.markdown("---")
            st.subheader("✏️ Editar/Excluir Fornecedor")
            
            if suppliers:
                action_col1, action_col2 = st.columns(2)
                
                with action_col1:
                    st.markdown("**Editar Fornecedor**")
                    edit_supplier_name = st.selectbox(
                        "Selecione fornecedor para editar:",
                        options=["Selecione..."] + [s.name for s in suppliers],
                        key="edit_supplier"
                    )
                    
                    if edit_supplier_name != "Selecione...":
                        edit_supplier = next(s for s in suppliers if s.name == edit_supplier_name)
                        
                        with st.form("edit_supplier_form"):
                            st.markdown("**Dados do Fornecedor**")
                            edit_col1, edit_col2 = st.columns(2)
                            
                            with edit_col1:
                                edit_name = st.text_input("Nome *", value=edit_supplier.name)
                                edit_cnpj = st.text_input("CNPJ", value=edit_supplier.cnpj or "")
                                edit_phone = st.text_input("Telefone", value=edit_supplier.phone or "")
                                edit_email = st.text_input("Email", value=edit_supplier.email or "")
                                edit_contact = st.text_input("Pessoa de Contato", value=edit_supplier.contact or "")
                            
                            with edit_col2:
                                edit_address = st.text_area("Endereço", value=edit_supplier.address or "")
                                edit_certifications = st.text_area("Certificações", value=edit_supplier.certifications or "")
                                edit_status = st.selectbox("Status", ["ativo", "inativo"], 
                                                         index=0 if edit_supplier.status == "ativo" else 1)
                            
                            # Show current certification files
                            import json
                            current_files = []
                            if edit_supplier.certification_files:
                                try:
                                    current_files = json.loads(edit_supplier.certification_files)
                                    st.info(f"📄 {len(current_files)} certificação(ões) atual(is)")
                                    for cert in current_files:
                                        st.caption(f"  • {cert.get('original_name', 'Arquivo')}")
                                except:
                                    pass
                            elif edit_supplier.certification_file_path and os.path.exists(edit_supplier.certification_file_path):
                                st.info(f"📄 1 certificação atual (formato antigo)")
                            
                            # Upload new certifications
                            edit_uploaded_certifications = st.file_uploader(
                                "Adicionar/Substituir certificações (PDF)",
                                type=['pdf'],
                                accept_multiple_files=True,
                                help="Deixe vazio para manter as certificações atuais. Novos arquivos substituirão os antigos.",
                                key=f"edit_cert_{edit_supplier.id}"
                            )
                            
                            edit_notes = st.text_area("Observações", value=edit_supplier.notes or "")
                            
                            if st.form_submit_button("💾 Salvar Alterações", use_container_width=True):
                                if not edit_name:
                                    st.error("Nome do fornecedor é obrigatório.")
                                else:
                                    try:
                                        import json
                                        certification_files_json = edit_supplier.certification_files
                                        
                                        # Handle new certification files upload
                                        if edit_uploaded_certifications:
                                            if len(edit_uploaded_certifications) > 15:
                                                st.error("Máximo de 15 arquivos permitidos.")
                                                st.stop()
                                            
                                            # Delete old files
                                            if edit_supplier.certification_files:
                                                try:
                                                    old_files = json.loads(edit_supplier.certification_files)
                                                    for old_file in old_files:
                                                        if os.path.exists(old_file["path"]):
                                                            try:
                                                                os.remove(old_file["path"])
                                                            except:
                                                                pass
                                                except:
                                                    pass
                                            
                                            # Create uploads directory if it doesn't exist
                                            upload_dir = "uploads/certifications"
                                            os.makedirs(upload_dir, exist_ok=True)
                                            
                                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                            safe_name = "".join(c for c in edit_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                                            safe_name = safe_name.replace(' ', '_')
                                            
                                            new_files_list = []
                                            for idx, uploaded_file in enumerate(edit_uploaded_certifications, 1):
                                                # Check file size
                                                if uploaded_file.size > 10 * 1024 * 1024:
                                                    st.warning(f"Arquivo '{uploaded_file.name}' excede 10MB e será ignorado.")
                                                    continue
                                                
                                                original_name = uploaded_file.name.replace('.pdf', '')
                                                safe_original = "".join(c for c in original_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                                                safe_original = safe_original.replace(' ', '_')
                                                filename = f"{safe_name}_{timestamp}_cert{idx}_{safe_original}.pdf"
                                                file_path = os.path.join(upload_dir, filename)
                                                
                                                try:
                                                    with open(file_path, "wb") as f:
                                                        f.write(uploaded_file.getbuffer())
                                                    new_files_list.append({
                                                        "path": file_path,
                                                        "original_name": uploaded_file.name,
                                                        "upload_date": datetime.now().isoformat()
                                                    })
                                                except Exception as e:
                                                    st.warning(f"Erro ao salvar '{uploaded_file.name}': {str(e)}")
                                                    continue
                                            
                                            certification_files_json = json.dumps(new_files_list) if new_files_list else None
                                        
                                        with Session(engine) as session:
                                            # Check if name already exists for another supplier
                                            existing = session.exec(
                                                select(Supplier).where(
                                                    (Supplier.name == edit_name) & 
                                                    (Supplier.id != edit_supplier.id)
                                                )
                                            ).first()
                                            
                                            if existing:
                                                st.error("Já existe outro fornecedor com este nome.")
                                            else:
                                                # Update supplier
                                                supplier_to_update = session.get(Supplier, edit_supplier.id)
                                                supplier_to_update.name = edit_name
                                                supplier_to_update.cnpj = edit_cnpj if edit_cnpj else None
                                                supplier_to_update.phone = edit_phone if edit_phone else None
                                                supplier_to_update.email = edit_email if edit_email else None
                                                supplier_to_update.contact = edit_contact if edit_contact else None
                                                supplier_to_update.address = edit_address if edit_address else None
                                                supplier_to_update.certifications = edit_certifications if edit_certifications else None
                                                supplier_to_update.certification_files = certification_files_json
                                                supplier_to_update.notes = edit_notes if edit_notes else None
                                                supplier_to_update.status = edit_status
                                                
                                                session.commit()
                                                success_msg = f"Fornecedor '{edit_name}' atualizado com sucesso!"
                                                if edit_uploaded_certifications:
                                                    success_msg += f" {len(edit_uploaded_certifications)} certificação(ões) anexada(s)."
                                                st.success(success_msg)
                                                st.rerun()
                                    
                                    except Exception as e:
                                        st.error(f"Erro ao atualizar fornecedor: {str(e)}")
                
                with action_col2:
                    st.markdown("**Excluir Fornecedor**")
                    delete_supplier_name = st.selectbox(
                        "Selecione fornecedor para excluir:",
                        options=["Selecione..."] + [s.name for s in suppliers],
                        key="delete_supplier"
                    )
                    
                    if delete_supplier_name != "Selecione...":
                        delete_supplier = next(s for s in suppliers if s.name == delete_supplier_name)
                        
                        st.warning(f"⚠️ Esta ação irá excluir permanentemente o fornecedor **{delete_supplier.name}**")
                        st.info("Digite 'CONFIRMAR' para prosseguir:")
                        
                        confirmation = st.text_input("Confirmação:", key="delete_confirmation")
                        
                        if st.button("🗑️ Excluir Fornecedor", type="secondary"):
                            if confirmation == "CONFIRMAR":
                                try:
                                    with Session(engine) as session:
                                        # Delete all related records to avoid foreign key constraints
                                        
                                        # Delete purchase orders and their items
                                        from models import PurchaseOrder, PurchaseItem
                                        purchase_orders = session.exec(
                                            select(PurchaseOrder).where(
                                                PurchaseOrder.supplier_id == delete_supplier.id
                                            )
                                        ).all()
                                        
                                        for po in purchase_orders:
                                            # Delete purchase items first
                                            purchase_items = session.exec(
                                                select(PurchaseItem).where(
                                                    PurchaseItem.po_id == po.id
                                                )
                                            ).all()
                                            
                                            for item in purchase_items:
                                                session.delete(item)
                                            
                                            # Delete purchase order
                                            session.delete(po)
                                        
                                        # Delete payables
                                        from models import Payable
                                        payables = session.exec(
                                            select(Payable).where(
                                                Payable.supplier_id == delete_supplier.id
                                            )
                                        ).all()
                                        
                                        for payable in payables:
                                            session.delete(payable)
                                        
                                        # Delete quote requests and their items
                                        from models import QuoteRequest, QuoteItem
                                        quote_requests = session.exec(
                                            select(QuoteRequest).where(
                                                QuoteRequest.supplier_id == delete_supplier.id
                                            )
                                        ).all()
                                        
                                        for qr in quote_requests:
                                            # Delete quote items first
                                            quote_items = session.exec(
                                                select(QuoteItem).where(
                                                    QuoteItem.quote_request_id == qr.id
                                                )
                                            ).all()
                                            
                                            for item in quote_items:
                                                session.delete(item)
                                            
                                            # Delete quote request
                                            session.delete(qr)
                                        
                                        # Update raw materials that reference this supplier
                                        from models import RawMaterial
                                        raw_materials = session.exec(
                                            select(RawMaterial).where(
                                                RawMaterial.supplier_id == delete_supplier.id
                                            )
                                        ).all()
                                        
                                        for rm in raw_materials:
                                            rm.supplier_id = None  # Remove supplier reference
                                        
                                        # Delete certification files if exist
                                        supplier_to_delete = session.get(Supplier, delete_supplier.id)
                                        if supplier_to_delete:
                                            import json
                                            # Delete multiple files (new format)
                                            if supplier_to_delete.certification_files:
                                                try:
                                                    cert_files = json.loads(supplier_to_delete.certification_files)
                                                    for cert_file in cert_files:
                                                        if os.path.exists(cert_file["path"]):
                                                            try:
                                                                os.remove(cert_file["path"])
                                                            except:
                                                                pass
                                                except:
                                                    pass
                                            # Delete single file (legacy format)
                                            if supplier_to_delete.certification_file_path and os.path.exists(supplier_to_delete.certification_file_path):
                                                try:
                                                    os.remove(supplier_to_delete.certification_file_path)
                                                except:
                                                    pass
                                            
                                            session.delete(supplier_to_delete)
                                            session.commit()
                                            
                                            # Build success message
                                            success_msg = f"Fornecedor '{delete_supplier.name}' excluído com sucesso!"
                                            details = []
                                            
                                            if len(purchase_orders) > 0:
                                                details.append(f"{len(purchase_orders)} pedidos de compra")
                                            if len(payables) > 0:
                                                details.append(f"{len(payables)} contas a pagar")
                                            if len(quote_requests) > 0:
                                                details.append(f"{len(quote_requests)} solicitações de orçamento")
                                            if len(raw_materials) > 0:
                                                details.append(f"{len(raw_materials)} matérias-primas atualizadas")
                                            
                                            if details:
                                                success_msg += f" (Também foram removidos: {', '.join(details)})"
                                            
                                            st.success(success_msg)
                                            st.rerun()
                                
                                except Exception as e:
                                    st.error(f"Erro ao excluir fornecedor: {str(e)}")
                            else:
                                st.error("Digite 'CONFIRMAR' para excluir o fornecedor.")
        
        # Detailed view section
        st.markdown("---")
        st.subheader("Detalhes do Fornecedor")
        
        if suppliers:
            selected_supplier_name = st.selectbox(
                "Selecione um fornecedor para ver detalhes:",
                options=[s.name for s in suppliers]
            )
            
            selected_supplier = next(s for s in suppliers if s.name == selected_supplier_name)
            
            detail_col1, detail_col2 = st.columns(2)
            
            with detail_col1:
                st.markdown("**Informações Básicas**")
                st.text(f"Nome: {selected_supplier.name}")
                st.text(f"CNPJ: {selected_supplier.cnpj or 'N/A'}")
                st.text(f"Telefone: {selected_supplier.phone or 'N/A'}")
                st.text(f"Email: {selected_supplier.email or 'N/A'}")
                st.text(f"Contato: {selected_supplier.contact or 'N/A'}")
                st.text(f"Status: {selected_supplier.status}")
            
            with detail_col2:
                if selected_supplier.address:
                    st.markdown("**Endereço**")
                    st.text(selected_supplier.address)
                
                if selected_supplier.certifications:
                    st.markdown("**Certificações**")
                    st.text(selected_supplier.certifications)
                
                # Display certification files (new format - multiple files)
                if selected_supplier.certification_files:
                    st.markdown("**Arquivos de Certificação**")
                    try:
                        import json
                        cert_files = json.loads(selected_supplier.certification_files)
                        for idx, cert_file in enumerate(cert_files, 1):
                            if os.path.exists(cert_file["path"]):
                                with open(cert_file["path"], "rb") as file:
                                    st.download_button(
                                        label=f"📄 {cert_file.get('original_name', f'Certificação {idx}')}",
                                        data=file.read(),
                                        file_name=cert_file.get('original_name', f"certificacao_{idx}.pdf"),
                                        mime="application/pdf",
                                        key=f"download_cert_{selected_supplier.id}_{idx}"
                                    )
                            else:
                                st.text(f"❌ {cert_file.get('original_name', f'Arquivo {idx}')} - Não encontrado")
                    except:
                        st.text("Erro ao carregar arquivos")
                # Display legacy single file if exists
                elif selected_supplier.certification_file_path:
                    st.markdown("**Arquivo de Certificação**")
                    if os.path.exists(selected_supplier.certification_file_path):
                        with open(selected_supplier.certification_file_path, "rb") as file:
                            st.download_button(
                                label="📄 Baixar Certificação PDF",
                                data=file.read(),
                                file_name=f"certificacao_{selected_supplier.name}.pdf",
                                mime="application/pdf"
                            )
                    else:
                        st.text("Arquivo não encontrado")
                
                if selected_supplier.notes:
                    st.markdown("**Observações**")
                    st.text(selected_supplier.notes)
    
    else:
        st.info("Nenhum fornecedor encontrado com os filtros aplicados.")

with tab2:
    st.subheader("Cadastrar Novo Fornecedor")
    
    if not has_permission("operator"):
        st.error("Você não tem permissão para cadastrar fornecedores.")
    else:
        with st.form("new_supplier_form", clear_on_submit=False):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Nome *", placeholder="Nome do fornecedor")
                cnpj = st.text_input("CNPJ", placeholder="00.000.000/0000-00")
                phone = st.text_input("Telefone", placeholder="(00) 0000-0000")
                email = st.text_input("Email", placeholder="contato@fornecedor.com")
                contact = st.text_input("Pessoa de Contato", placeholder="Nome do contato")
            
            with col2:
                address = st.text_area("Endereço", placeholder="Endereço completo")
                certifications = st.text_area("Certificações", placeholder="Descrição das certificações")
            
            # File upload for certifications - Multiple files support
            st.markdown("**📄 Anexar Certificações (PDF)**")
            st.caption("Você pode anexar até 15 documentos PDF (máx 10MB cada)")
            uploaded_certifications = st.file_uploader(
                "Escolha os arquivos PDF das certificações",
                type=['pdf'],
                accept_multiple_files=True,
                help="Apenas arquivos PDF são aceitos. Máximo de 15 arquivos."
            )
            
            notes = st.text_area("Observações", placeholder="Observações adicionais")
            
            submitted = st.form_submit_button("💾 Cadastrar Fornecedor", use_container_width=True)
            
            if submitted:
                if not name:
                    st.error("Nome do fornecedor é obrigatório.")
                else:
                    try:
                        import json
                        certification_files_list = []
                        
                        # Handle multiple file uploads if provided
                        if uploaded_certifications:
                            if len(uploaded_certifications) > 15:
                                st.error("Máximo de 15 arquivos permitidos.")
                                st.stop()
                            
                            # Create uploads directory if it doesn't exist
                            upload_dir = "uploads/certifications"
                            os.makedirs(upload_dir, exist_ok=True)
                            
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                            safe_name = safe_name.replace(' ', '_')
                            
                            # Save each file
                            for idx, uploaded_file in enumerate(uploaded_certifications, 1):
                                # Check file size (10MB limit per file)
                                if uploaded_file.size > 10 * 1024 * 1024:
                                    st.warning(f"Arquivo '{uploaded_file.name}' excede 10MB e será ignorado.")
                                    continue
                                
                                # Generate unique filename
                                original_name = uploaded_file.name.replace('.pdf', '')
                                safe_original = "".join(c for c in original_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                                safe_original = safe_original.replace(' ', '_')
                                filename = f"{safe_name}_{timestamp}_cert{idx}_{safe_original}.pdf"
                                file_path = os.path.join(upload_dir, filename)
                                
                                # Save the file
                                try:
                                    with open(file_path, "wb") as f:
                                        f.write(uploaded_file.getbuffer())
                                    certification_files_list.append({
                                        "path": file_path,
                                        "original_name": uploaded_file.name,
                                        "upload_date": datetime.now().isoformat()
                                    })
                                except Exception as e:
                                    st.warning(f"Erro ao salvar '{uploaded_file.name}': {str(e)}")
                                    continue
                        
                        with Session(engine) as session:
                            # Check if supplier already exists
                            existing = session.exec(
                                select(Supplier).where(Supplier.name == name)
                            ).first()
                            
                            if existing:
                                st.error("Já existe um fornecedor com este nome.")
                            else:
                                supplier_data = {
                                    "name": name,
                                    "cnpj": cnpj if cnpj else None,
                                    "phone": phone if phone else None,
                                    "email": email if email else None,
                                    "contact": contact if contact else None,
                                    "address": address if address else None,
                                    "certifications": certifications if certifications else None,
                                    "certification_files": json.dumps(certification_files_list) if certification_files_list else None,
                                    "notes": notes if notes else None
                                }
                                
                                new_supplier = Supplier(**supplier_data)
                                session.add(new_supplier)
                                session.commit()
                                
                                success_msg = f"Fornecedor '{name}' cadastrado com sucesso!"
                                if certification_files_list:
                                    success_msg += f" {len(certification_files_list)} certificação(ões) anexada(s)."
                                st.success(success_msg)
                                st.rerun()
                    
                    except Exception as e:
                        st.error(f"Erro ao cadastrar fornecedor: {str(e)}")

with tab3:
    st.subheader("Importar e Exportar Dados")
    
    import_col, export_col = st.columns(2)
    
    with import_col:
        st.markdown("#### 📥 Importar Fornecedores")
        
        if not has_permission("operator"):
            st.error("Você não tem permissão para importar dados.")
        else:
            # Download template
            if st.button("📄 Baixar Modelo Excel", use_container_width=True):
                template = generate_import_template("suppliers")
                st.download_button(
                    label="📥 Download Modelo",
                    data=template.getvalue(),
                    file_name="modelo_fornecedores.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
            # File upload
            uploaded_file = st.file_uploader(
                "Escolha arquivo Excel (.xlsx)",
                type=['xlsx'],
                help="Use o modelo fornecido para garantir a importação correta"
            )
            
            if uploaded_file:
                if st.button("🚀 Importar Dados", use_container_width=True):
                    with st.spinner("Importando dados..."):
                        with Session(engine) as session:
                            result = import_suppliers_from_excel(uploaded_file, session)
                        
                        if result["success"]:
                            st.success(f"✅ {result['imported_count']} fornecedores importados de {result['total_rows']} linhas!")
                            
                            if result["errors"]:
                                st.warning("⚠️ Alguns registros apresentaram problemas:")
                                for error in result["errors"]:
                                    st.text(f"• {error}")
                        else:
                            st.error(f"❌ Erro na importação: {result['error']}")
    
    with export_col:
        st.markdown("#### 📤 Exportar Fornecedores")
        
        if st.button("📊 Exportar para Excel", use_container_width=True):
            with st.spinner("Gerando arquivo..."):
                with Session(engine) as session:
                    excel_data = export_suppliers_to_excel(session)
                
                st.download_button(
                    label="📥 Download Excel",
                    data=excel_data.getvalue(),
                    file_name=f"fornecedores_export_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        
        # CSV export option
        if st.button("📄 Exportar para CSV", use_container_width=True):
            with Session(engine) as session:
                suppliers = session.exec(select(Supplier)).all()
                
                if suppliers:
                    data = []
                    for supplier in suppliers:
                        data.append({
                            "Nome": supplier.name,
                            "CNPJ": supplier.cnpj,
                            "Telefone": supplier.phone,
                            "Email": supplier.email,
                            "Contato": supplier.contact,
                            "Status": supplier.status
                        })
                    
                    df = pd.DataFrame(data)
                    csv_data = df.to_csv(index=False)
                    
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv_data,
                        file_name=f"fornecedores_export_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("Nenhum fornecedor para exportar.")

# Summary statistics
if st.checkbox("📊 Mostrar Estatísticas"):
    with Session(engine) as session:
        total_suppliers = session.exec(select(Supplier)).all()
        
        if total_suppliers:
            stats_col1, stats_col2, stats_col3 = st.columns(3)
            
            with stats_col1:
                st.metric("Total de Fornecedores", len(total_suppliers))
            
            with stats_col2:
                active_count = sum(1 for s in total_suppliers if s.status == "ativo")
                st.metric("Fornecedores Ativos", active_count)
            
            with stats_col3:
                with_leadtime = sum(1 for s in total_suppliers if s.avg_leadtime_days)
                avg_leadtime = sum(s.avg_leadtime_days for s in total_suppliers if s.avg_leadtime_days) / max(with_leadtime, 1)
                st.metric("Lead Time Médio", f"{avg_leadtime:.1f} dias")
