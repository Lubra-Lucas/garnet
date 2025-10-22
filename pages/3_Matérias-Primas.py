# pages/3_MateriasPrimas.py
import streamlit as st
from auth import require_login, has_permission
from sqlmodel import Session, select
from db import engine
from models import RawMaterial, Supplier
from schema import RawMaterialCreate, RawMaterialUpdate
from services.io_import import import_raw_materials_from_excel, generate_import_template
from services.io_export import export_raw_materials_to_excel
import pandas as pd

# Require login for this page
user = require_login()

st.set_page_config(page_title="GARNET - Matérias-Primas", layout="wide")

# Professional page header
st.markdown("""
<div style="padding: 1rem 0 2rem 0; border-bottom: 1px solid #E8E8E8; margin-bottom: 2rem;">
    <h1 style="margin: 0; color: #2E4A6B; font-weight: 300;">Gestão de Matérias-Primas e Insumos</h1>
    <p style="margin: 0.5rem 0 0 0; color: #666; font-size: 1.1rem;">Cadastro e controle de materiais e insumos</p>
</div>
""", unsafe_allow_html=True)

# Clean tabs without icons
tab1, tab2, tab3 = st.tabs(["Catálogo", "Cadastro", "Importar / Exportar"])

with tab1:
    # Clean section header
    st.markdown("""
    <div style="margin-bottom: 1.5rem;">
        <h3 style="margin: 0; color: #2E4A6B; font-weight: 400;">Catálogo de Matérias-Primas</h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Clean filters layout
    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns([2, 1, 1, 1])
    
    with filter_col1:
        search_term = st.text_input("Buscar por código ou nome", placeholder="Digite para filtrar...")
    
    with filter_col2:
        # Get suppliers for filter
        with Session(engine) as session:
            suppliers = session.exec(select(Supplier).where(Supplier.status == "ativo")).all()
            supplier_options = ["Todos"] + [s.name for s in suppliers]
        
        supplier_filter = st.selectbox("Fornecedor:", supplier_options)
    
    with filter_col3:
        status_filter = st.selectbox("Status:", ["Todos", "ativo", "inativo"])
    
    with filter_col4:
        unit_filter = st.selectbox("Unidade:", ["Todas", "KG", "G", "L", "ML", "UN"])
    
    # Get raw materials with filters
    with Session(engine) as session:
        query = select(RawMaterial, Supplier.name).outerjoin(
            Supplier, RawMaterial.supplier_id == Supplier.id
        )
        
        if search_term:
            query = query.where(
                (RawMaterial.code.ilike(f"%{search_term}%")) |
                (RawMaterial.name_usual.ilike(f"%{search_term}%")) |
                (RawMaterial.name_chemical.ilike(f"%{search_term}%"))
            )
        
        if supplier_filter != "Todos":
            query = query.where(Supplier.name == supplier_filter)
        
        if status_filter != "Todos":
            query = query.where(RawMaterial.status == status_filter)
        
        if unit_filter != "Todas":
            query = query.where(RawMaterial.base_unit == unit_filter)
        
        results = session.exec(query.order_by(RawMaterial.code)).all()
    
    if results:
        # Convert to DataFrame for display
        rm_data = []
        for rm, supplier_name in results:
            rm_data.append({
                "ID": rm.id,
                "Código": rm.code,
                "Nome Usual": rm.name_usual,
                "Nome Químico": rm.name_chemical or "N/A",
                "Fornecedor": supplier_name or "N/A",
                "Unidade": rm.base_unit,
                "Preço Base": f"R$ {rm.base_price:.2f}",
                "Validade (dias)": rm.shelf_life_days or "N/A",
                "Localização": rm.location or "N/A",
                "Status": rm.status
            })
        
        df = pd.DataFrame(rm_data)
        
        # Remove Validade column
        df_display = df.drop(columns=["Validade (dias)"])
        
        # Display as interactive table
        if has_permission("manager"):
            edited_df = st.data_editor(
                df_display,
                hide_index=True,
                use_container_width=True,
                disabled=["ID", "Código"],
                column_config={
                    "Status": st.column_config.SelectboxColumn(
                        "Status",
                        options=["ativo", "inativo"],
                        required=True
                    ),
                    "Preço Base": st.column_config.NumberColumn(
                        "Preço Base (R$)",
                        min_value=0.0,
                        format="R$ %.2f"
                    )
                }
            )
            
            # Update button
            if st.button("💾 Salvar Alterações"):
                with Session(engine) as session:
                    for idx, row in edited_df.iterrows():
                        rm = session.get(RawMaterial, row["ID"])
                        if rm:
                            rm.name_usual = row["Nome Usual"]
                            rm.name_chemical = row["Nome Químico"] if row["Nome Químico"] != "N/A" else None
                            rm.location = row["Localização"] if row["Localização"] != "N/A" else None
                            rm.status = row["Status"]
                            # Parse price
                            price_str = row["Preço Base"].replace("R$ ", "").replace(",", ".")
                            rm.base_price = float(price_str)
                    
                    session.commit()
                    st.success("Alterações salvas com sucesso!")
                    st.rerun()
        else:
            st.dataframe(df_display, hide_index=True, use_container_width=True)
        
        # Detailed view section
        st.markdown("---")
        st.subheader("Detalhes da Matéria-Prima")
        
        selected_rm_code = st.selectbox(
            "Selecione uma matéria-prima para ver detalhes:",
            options=[rm.code for rm, _ in results]
        )
        
        selected_rm = next(rm for rm, _ in results if rm.code == selected_rm_code)
        selected_supplier = next((supplier_name for rm, supplier_name in results if rm.code == selected_rm_code), None)
        
        detail_col1, detail_col2, detail_col3 = st.columns(3)
        
        with detail_col1:
            st.markdown("**Identificação**")
            st.text(f"Código: {selected_rm.code}")
            st.text(f"Nome Usual: {selected_rm.name_usual}")
            st.text(f"Nome Químico: {selected_rm.name_chemical or 'N/A'}")
            st.text(f"Status: {selected_rm.status}")
        
        with detail_col2:
            st.markdown("**Especificações Técnicas**")
            st.text(f"Unidade Base: {selected_rm.base_unit}")
            st.text(f"Densidade: {selected_rm.density or 'N/A'}")
            st.text(f"Fator Conversão: {selected_rm.conv_factor or 'N/A'}")
            st.text(f"Validade: {selected_rm.shelf_life_days or 'N/A'} dias")
        
        with detail_col3:
            st.markdown("**Informações Comerciais**")
            st.text(f"Fornecedor: {selected_supplier or 'N/A'}")
            st.text(f"Preço Base: R$ {selected_rm.base_price:.2f}")
            st.text(f"Localização: {selected_rm.location or 'N/A'}")
        
        # Display certification files if they exist
        if selected_rm.certification_file_path:
            st.markdown("---")
            st.markdown("**Arquivos de Certificação**")
            import json
            import os
            try:
                # Try to parse as JSON list
                cert_paths = json.loads(selected_rm.certification_file_path)
                if isinstance(cert_paths, list):
                    cert_cols = st.columns(min(len(cert_paths), 5))
                    for idx, cert_path in enumerate(cert_paths):
                        col_idx = idx % 5
                        with cert_cols[col_idx]:
                            if os.path.exists(cert_path):
                                with open(cert_path, "rb") as file:
                                    st.download_button(
                                        label=f"📄 Cert {idx+1}",
                                        data=file.read(),
                                        file_name=f"certificacao_{selected_rm.code}_{idx+1}.pdf",
                                        mime="application/pdf",
                                        key=f"download_cert_{selected_rm.id}_{idx}",
                                        use_container_width=True
                                    )
                            else:
                                st.text(f"Arquivo {idx+1} não encontrado")
                else:
                    # Old format - single file
                    if os.path.exists(selected_rm.certification_file_path):
                        with open(selected_rm.certification_file_path, "rb") as file:
                            st.download_button(
                                label="📄 Baixar Certificação PDF",
                                data=file.read(),
                                file_name=f"certificacao_{selected_rm.code}.pdf",
                                mime="application/pdf",
                                use_container_width=True
                            )
                    else:
                        st.text("Arquivo não encontrado")
            except json.JSONDecodeError:
                # Old format - single file path string
                if os.path.exists(selected_rm.certification_file_path):
                    with open(selected_rm.certification_file_path, "rb") as file:
                        st.download_button(
                            label="📄 Baixar Certificação PDF",
                            data=file.read(),
                            file_name=f"certificacao_{selected_rm.code}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                else:
                    st.text("Arquivo não encontrado")
        
        # Cost calculator
        st.markdown("---")
        st.subheader("🧮 Calculadora de Custos")
        
        calc_col1, calc_col2, calc_col3 = st.columns(3)
        
        with calc_col1:
            calc_qty = st.number_input("Quantidade:", min_value=0.0, value=1.0, step=0.1)
        
        with calc_col2:
            calc_unit = st.selectbox("Unidade:", [selected_rm.base_unit, "G", "KG", "ML", "L", "UN"])
        
        with calc_col3:
            st.write("")  # Spacing
            if st.button("💰 Calcular Custo"):
                from services.business import material_cost_unit
                cost = material_cost_unit(selected_rm, calc_qty, calc_unit)
                st.success(f"Custo: R$ {cost:.2f}")
    
    else:
        st.info("Nenhuma matéria-prima encontrada com os filtros aplicados.")

with tab2:
    st.subheader("Cadastrar Nova Matéria-Prima")
    
    if not has_permission("operator"):
        st.error("Você não tem permissão para cadastrar matérias-primas.")
    else:
        # Create subtabs for Add/Edit/Delete
        subtab1, subtab2, subtab3 = st.tabs(["➕ Cadastrar", "✏️ Editar", "🗑️ Excluir"])
        
        with subtab1:
            with st.form("new_raw_material_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    code = st.text_input("Código *", placeholder="MP001")
                    name_usual = st.text_input("Nome Usual *", placeholder="Nome comercial")
                    name_chemical = st.text_input("Nome Químico", placeholder="Nome químico/científico")
                
                with col2:
                    # Supplier selection
                    with Session(engine) as session:
                        suppliers = session.exec(select(Supplier).where(Supplier.status == "ativo")).all()
                        supplier_options = ["Nenhum"] + [f"{s.name} (ID: {s.id})" for s in suppliers]
                    
                    supplier_selection = st.selectbox("Fornecedor:", supplier_options)
                    supplier_id = None
                    if supplier_selection != "Nenhum":
                        supplier_id = int(supplier_selection.split("ID: ")[1].split(")")[0])
                    
                    base_unit = st.selectbox("Unidade Base *", ["KG", "G", "L", "ML", "UN"])
                    base_price = st.number_input("Preço Base (R$) *", min_value=0.0, value=0.0, step=0.01)
                
                # Upload certifications
                st.markdown("**Certificações (PDF)**")
                uploaded_certifications = st.file_uploader(
                    "Anexar certificações (PDF) - máximo 10",
                    type=['pdf'],
                    accept_multiple_files=True,
                    help="Selecione até 10 arquivos PDF com certificações da matéria-prima",
                    key="new_rm_certifications"
                )
                
                if uploaded_certifications and len(uploaded_certifications) > 10:
                    st.error("Limite de 10 arquivos excedido. Por favor, selecione no máximo 10 arquivos.")
                    uploaded_certifications = uploaded_certifications[:10]
                
                submitted = st.form_submit_button("💾 Cadastrar Matéria-Prima", use_container_width=True)
                
                if submitted:
                    if not code or not name_usual:
                        st.error("Código e Nome Usual são obrigatórios.")
                    else:
                        try:
                            with Session(engine) as session:
                                # Check if code already exists
                                existing = session.exec(
                                    select(RawMaterial).where(RawMaterial.code == code)
                                ).first()
                                
                                if existing:
                                    st.error("Já existe uma matéria-prima com este código.")
                                else:
                                    # Handle file uploads
                                    import json
                                    import os
                                    from datetime import datetime
                                    
                                    certification_file_path = None
                                    if uploaded_certifications:
                                        # Create uploads directory if it doesn't exist
                                        upload_dir = "uploads/certifications_raw_materials"
                                        os.makedirs(upload_dir, exist_ok=True)
                                        
                                        # Save files
                                        certification_file_paths = []
                                        for idx, uploaded_file in enumerate(uploaded_certifications[:10]):
                                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                            safe_code = code.replace("/", "_").replace("\\", "_")
                                            file_name = f"{safe_code}_cert_{idx+1}_{timestamp}.pdf"
                                            file_path = os.path.join(upload_dir, file_name)
                                            
                                            with open(file_path, "wb") as f:
                                                f.write(uploaded_file.getbuffer())
                                            
                                            certification_file_paths.append(file_path)
                                        
                                        certification_file_path = json.dumps(certification_file_paths)
                                    
                                    rm_data = {
                                        "code": code,
                                        "name_usual": name_usual,
                                        "name_chemical": name_chemical if name_chemical else None,
                                        "supplier_id": supplier_id,
                                        "base_unit": base_unit,
                                        "base_price": base_price,
                                        "certification_file_path": certification_file_path
                                    }
                                    
                                    new_rm = RawMaterial(**rm_data)
                                    session.add(new_rm)
                                    session.commit()
                                    
                                    success_msg = f"Matéria-prima '{code}' cadastrada com sucesso!"
                                    if uploaded_certifications:
                                        success_msg += f" {len(uploaded_certifications)} certificação(ões) anexada(s)."
                                    st.success(success_msg)
                                    st.rerun()
                        
                        except Exception as e:
                            st.error(f"Erro ao cadastrar matéria-prima: {str(e)}")
        
        with subtab2:
            st.markdown("#### Editar Matéria-Prima Existente")
            
            # Select material to edit
            with Session(engine) as session:
                materials = session.exec(select(RawMaterial)).all()
                if not materials:
                    st.info("Nenhuma matéria-prima cadastrada.")
                else:
                    material_options = [f"{rm.code} - {rm.name_usual}" for rm in materials]
                    selected_material_option = st.selectbox("Selecione a matéria-prima para editar:", material_options)
                    
                    if selected_material_option:
                        selected_material = next(rm for rm in materials if f"{rm.code} - {rm.name_usual}" == selected_material_option)
                        
                        with st.form("edit_raw_material_form"):
                            st.info(f"Editando: {selected_material.code}")
                            
                            edit_col1, edit_col2 = st.columns(2)
                            
                            with edit_col1:
                                edit_name_usual = st.text_input("Nome Usual *", value=selected_material.name_usual)
                                edit_name_chemical = st.text_input("Nome Químico", value=selected_material.name_chemical or "")
                                edit_base_unit = st.selectbox("Unidade Base *", ["KG", "G", "L", "ML", "UN"], 
                                                            index=["KG", "G", "L", "ML", "UN"].index(selected_material.base_unit))
                            
                            with edit_col2:
                                # Supplier selection
                                suppliers = session.exec(select(Supplier).where(Supplier.status == "ativo")).all()
                                supplier_options = ["Nenhum"] + [f"{s.name} (ID: {s.id})" for s in suppliers]
                                
                                current_supplier_index = 0
                                if selected_material.supplier_id:
                                    current_supplier = session.get(Supplier, selected_material.supplier_id)
                                    if current_supplier:
                                        current_supplier_option = f"{current_supplier.name} (ID: {current_supplier.id})"
                                        if current_supplier_option in supplier_options:
                                            current_supplier_index = supplier_options.index(current_supplier_option)
                                
                                edit_supplier_selection = st.selectbox("Fornecedor:", supplier_options, index=current_supplier_index)
                                edit_supplier_id = None
                                if edit_supplier_selection != "Nenhum":
                                    edit_supplier_id = int(edit_supplier_selection.split("ID: ")[1].split(")")[0])
                                
                                edit_base_price = st.number_input("Preço Base (R$) *", min_value=0.0, 
                                                                value=float(selected_material.base_price), step=0.01)
                                edit_status = st.selectbox("Status", ["ativo", "inativo"], 
                                                         index=0 if selected_material.status == "ativo" else 1)
                            
                            # Show current certification files if exist
                            if selected_material.certification_file_path:
                                import json
                                try:
                                    cert_paths = json.loads(selected_material.certification_file_path)
                                    if isinstance(cert_paths, list):
                                        st.info(f"📄 {len(cert_paths)} certificação(ões) atual(is)")
                                    else:
                                        st.info(f"📄 Certificação atual: {os.path.basename(selected_material.certification_file_path)}")
                                except json.JSONDecodeError:
                                    st.info(f"📄 Certificação atual: {os.path.basename(selected_material.certification_file_path)}")
                            
                            # Upload new certifications
                            edit_uploaded_certifications = st.file_uploader(
                                "Substituir certificações (PDF) - máximo 10",
                                type=['pdf'],
                                accept_multiple_files=True,
                                help="Deixe vazio para manter as certificações atuais",
                                key=f"edit_cert_{selected_material.id}"
                            )
                            
                            if edit_uploaded_certifications and len(edit_uploaded_certifications) > 10:
                                st.error("Limite de 10 arquivos excedido. Por favor, selecione no máximo 10 arquivos.")
                                edit_uploaded_certifications = edit_uploaded_certifications[:10]
                            
                            if st.form_submit_button("💾 Salvar Alterações", use_container_width=True):
                                if not edit_name_usual:
                                    st.error("Nome Usual é obrigatório.")
                                else:
                                    try:
                                        import json
                                        import os
                                        from datetime import datetime
                                        
                                        # Handle certification files
                                        certification_file_path = selected_material.certification_file_path
                                        if edit_uploaded_certifications:
                                            # Delete old files if exist
                                            if certification_file_path:
                                                try:
                                                    old_paths = json.loads(certification_file_path)
                                                    if isinstance(old_paths, list):
                                                        for old_path in old_paths:
                                                            if os.path.exists(old_path):
                                                                try:
                                                                    os.remove(old_path)
                                                                except:
                                                                    pass
                                                    else:
                                                        if os.path.exists(certification_file_path):
                                                            try:
                                                                os.remove(certification_file_path)
                                                            except:
                                                                pass
                                                except json.JSONDecodeError:
                                                    if os.path.exists(certification_file_path):
                                                        try:
                                                            os.remove(certification_file_path)
                                                        except:
                                                            pass
                                            
                                            # Create uploads directory if it doesn't exist
                                            upload_dir = "uploads/certifications_raw_materials"
                                            os.makedirs(upload_dir, exist_ok=True)
                                            
                                            # Save new files
                                            certification_file_paths = []
                                            for idx, uploaded_file in enumerate(edit_uploaded_certifications[:10]):
                                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                                safe_code = selected_material.code.replace("/", "_").replace("\\", "_")
                                                file_name = f"{safe_code}_cert_{idx+1}_{timestamp}.pdf"
                                                file_path = os.path.join(upload_dir, file_name)
                                                
                                                with open(file_path, "wb") as f:
                                                    f.write(uploaded_file.getbuffer())
                                                
                                                certification_file_paths.append(file_path)
                                            
                                            certification_file_path = json.dumps(certification_file_paths)
                                        
                                        selected_material.name_usual = edit_name_usual
                                        selected_material.name_chemical = edit_name_chemical if edit_name_chemical else None
                                        selected_material.supplier_id = edit_supplier_id
                                        selected_material.base_unit = edit_base_unit
                                        selected_material.base_price = edit_base_price
                                        selected_material.status = edit_status
                                        selected_material.certification_file_path = certification_file_path
                                        
                                        session.commit()
                                        success_msg = "Matéria-prima atualizada com sucesso!"
                                        if edit_uploaded_certifications:
                                            success_msg += f" {len(edit_uploaded_certifications)} nova(s) certificação(ões) anexada(s)."
                                        st.success(success_msg)
                                        st.rerun()
                                    
                                    except Exception as e:
                                        st.error(f"Erro ao atualizar matéria-prima: {str(e)}")
        
        with subtab3:
            st.markdown("#### Excluir Matéria-Prima")
            
            # Select material to delete
            with Session(engine) as session:
                materials = session.exec(select(RawMaterial)).all()
                if not materials:
                    st.info("Nenhuma matéria-prima cadastrada.")
                else:
                    material_options = [f"{rm.code} - {rm.name_usual}" for rm in materials]
                    selected_delete_option = st.selectbox("Selecione a matéria-prima para excluir:", 
                                                        [""] + material_options)
                    
                    if selected_delete_option:
                        selected_delete_material = next(rm for rm in materials if f"{rm.code} - {rm.name_usual}" == selected_delete_option)
                        
                        st.warning(f"⚠️ Você está prestes a excluir: **{selected_delete_material.code} - {selected_delete_material.name_usual}**")
                        st.error("Esta ação não pode ser desfeita!")
                        
                        # Show material details
                        detail_col1, detail_col2 = st.columns(2)
                        with detail_col1:
                            st.text(f"Código: {selected_delete_material.code}")
                            st.text(f"Nome Usual: {selected_delete_material.name_usual}")
                            st.text(f"Unidade: {selected_delete_material.base_unit}")
                        
                        with detail_col2:
                            st.text(f"Preço: R$ {selected_delete_material.base_price:.2f}")
                            st.text(f"Status: {selected_delete_material.status}")
                        
                        # Confirmation
                        confirm_delete = st.checkbox("Confirmo que desejo excluir esta matéria-prima")
                        
                        if confirm_delete:
                            if st.button("🗑️ CONFIRMAR EXCLUSÃO", type="secondary", use_container_width=True):
                                try:
                                    import json
                                    import os
                                    
                                    # Delete certification files if they exist
                                    if selected_delete_material.certification_file_path:
                                        try:
                                            cert_paths = json.loads(selected_delete_material.certification_file_path)
                                            if isinstance(cert_paths, list):
                                                for cert_path in cert_paths:
                                                    if os.path.exists(cert_path):
                                                        try:
                                                            os.remove(cert_path)
                                                        except:
                                                            pass
                                            else:
                                                if os.path.exists(selected_delete_material.certification_file_path):
                                                    try:
                                                        os.remove(selected_delete_material.certification_file_path)
                                                    except:
                                                        pass
                                        except json.JSONDecodeError:
                                            if os.path.exists(selected_delete_material.certification_file_path):
                                                try:
                                                    os.remove(selected_delete_material.certification_file_path)
                                                except:
                                                    pass
                                    
                                    # First, get all stock lots related to this raw material
                                    from models import StockLot
                                    related_lots = session.exec(
                                        select(StockLot).where(
                                            (StockLot.item_type == "MP") &
                                            (StockLot.item_id == selected_delete_material.id)
                                        )
                                    ).all()
                                    
                                    # Delete related stock lots first
                                    for lot in related_lots:
                                        session.delete(lot)
                                    
                                    # Then delete the raw material
                                    session.delete(selected_delete_material)
                                    session.commit()
                                    
                                    lot_count = len(related_lots)
                                    success_msg = f"Matéria-prima '{selected_delete_material.code}' excluída com sucesso!"
                                    if lot_count > 0:
                                        success_msg += f" (Também foram removidos {lot_count} lotes de estoque relacionados)"
                                    
                                    st.success(success_msg)
                                    st.rerun()
                                
                                except Exception as e:
                                    st.error(f"Erro ao excluir matéria-prima: {str(e)}")
                                    st.info("Pode existir dependências desta matéria-prima em formulações ou outros registros.")

with tab3:
    st.subheader("Importar e Exportar Dados")
    
    import_col, export_col = st.columns(2)
    
    with import_col:
        st.markdown("#### 📥 Importar Matérias-Primas")
        
        if not has_permission("operator"):
            st.error("Você não tem permissão para importar dados.")
        else:
            # Download template
            if st.button("📄 Baixar Modelo Excel", use_container_width=True):
                template = generate_import_template("raw_materials")
                st.download_button(
                    label="📥 Download Modelo",
                    data=template.getvalue(),
                    file_name="modelo_materias_primas.xlsx",
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
                            result = import_raw_materials_from_excel(uploaded_file, session)
                        
                        if result["success"]:
                            st.success(f"✅ {result['imported_count']} matérias-primas importadas de {result['total_rows']} linhas!")
                            
                            if result["errors"]:
                                st.warning("⚠️ Alguns registros apresentaram problemas:")
                                for error in result["errors"]:
                                    st.text(f"• {error}")
                        else:
                            st.error(f"❌ Erro na importação: {result['error']}")
    
    with export_col:
        st.markdown("#### 📤 Exportar Matérias-Primas")
        
        if st.button("📊 Exportar para Excel", use_container_width=True):
            with st.spinner("Gerando arquivo..."):
                with Session(engine) as session:
                    excel_data = export_raw_materials_to_excel(session)
                
                st.download_button(
                    label="📥 Download Excel",
                    data=excel_data.getvalue(),
                    file_name=f"materias_primas_export_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )


