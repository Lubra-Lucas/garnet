# pages/5_Formulacao.py
import streamlit as st
from auth import require_login, has_permission
from sqlmodel import Session, select
from db import engine
from models import Product, RawMaterial, Formulation, FormulaItem, Supplier
from services.business import formulation_cost
from utils.ui_components import render_page_header, create_data_table, render_success_message, render_error_message
from utils.form_helpers import create_dynamic_item_form
from utils.data_helpers import get_cached_raw_materials, get_cached_products
import pandas as pd

# Require login for this page
user = require_login()

st.set_page_config(page_title="GARNET - Formulação", layout="wide")

# Professional page header using utility
render_page_header("Formulação de Produtos", "Criação e gestão de receitas e fórmulas")

# Clean tabs without icons - Análise de Custos apenas para managers
if has_permission("manager"):
    tab1, tab2, tab3 = st.tabs(["Formulações", "Nova Formulação", "Análise de Custos"])
else:
    tab1, tab2 = st.tabs(["Formulações", "Nova Formulação"])
    tab3 = None

with tab1:
    # Clean section header
    st.markdown("""
    <div style="margin-bottom: 1.5rem;">
        <h3 style="margin: 0; color: #2E4A6B; font-weight: 400;">Formulações Cadastradas</h3>
    </div>
    """, unsafe_allow_html=True)

    # Get formulations with product info
    with Session(engine) as session:
        query = select(Formulation, Product.name, Product.code).join(
            Product, Formulation.product_id == Product.id
        )
        results = session.exec(query.order_by(Product.code)).all()

    if results:
        # Display formulations table
        formulation_data = []
        for formulation, product_name, product_code in results:
            # Count formula items
            item_count = session.exec(
                select(FormulaItem).where(FormulaItem.formulation_id == formulation.id)
            ).all()

            formulation_data.append({
                "ID": formulation.id,
                "Produto": f"{product_code} - {product_name}",
                "Versão": formulation.version,
                "Estado": formulation.state,
                "Itens": len(item_count),
                "Aprovado Por": formulation.approved_by or "N/A",
                "Data Aprovação": formulation.approved_at.strftime("%d/%m/%Y") if formulation.approved_at else "N/A"
            })

        df = pd.DataFrame(formulation_data)
        st.dataframe(df, hide_index=True, use_container_width=True)

        # Detailed view
        st.markdown("---")
        st.subheader("Detalhes da Formulação")

        if results and has_permission("operator"):
            selected_id = st.selectbox(
                "Selecione uma formulação:",
                options=[f["ID"] for f in formulation_data],
                format_func=lambda x: next(f["Produto"] + f" (v{f['Versão']})" for f in formulation_data if f["ID"] == x)
            )

            # Get selected formulation details
            with Session(engine) as session:
                formulation = session.get(Formulation, selected_id)
                product = session.get(Product, formulation.product_id)

                # Get formula items with raw material and supplier info
                items_query = select(
                    FormulaItem, 
                    RawMaterial.code, 
                    RawMaterial.name_usual, 
                    RawMaterial.base_price,
                    RawMaterial.supplier_id,
                    Supplier.name.label('supplier_name')
                ).join(
                    RawMaterial, FormulaItem.raw_material_id == RawMaterial.id
                ).outerjoin(
                    Supplier, RawMaterial.supplier_id == Supplier.id
                ).where(FormulaItem.formulation_id == selected_id)

                items_results = session.exec(items_query).all()

                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("**Informações da Formulação**")
                    st.text(f"Produto: {product.code} - {product.name}")
                    st.text(f"Versão: {formulation.version}")
                    st.text(f"Estado: {formulation.state}")
                    st.text(f"Lote Padrão: {product.std_batch_weight} g")

                with col2:
                    st.markdown("**Status de Aprovação**")
                    st.text(f"Aprovado Por: {formulation.approved_by or 'Não aprovado'}")
                    st.text(f"Data Aprovação: {formulation.approved_at or 'N/A'}")

                    # Approval actions for managers
                    if has_permission("manager") and formulation.state == "Em desenvolvimento":
                        if st.button("✅ Aprovar Formulação"):
                            formulation.state = "Aprovado/Em Uso"
                            formulation.approved_by = user["name"]
                            from datetime import datetime
                            formulation.approved_at = datetime.now()
                            session.commit()
                            st.success("Formulação aprovada!")
                            st.rerun()
                
                # Botão para gerar PDF da formulação
                if st.button("📄 Gerar PDF da Formulação", type="primary", use_container_width=True):
                    try:
                        from services.pdf_generator import generate_formulation_pdf
                        import os
                        
                        # Gerar PDF passando o role do usuário
                        pdf_path = generate_formulation_pdf(formulation, product, items_results, user["role"])
                        
                        # Fornecer download
                        with open(pdf_path, "rb") as pdf_file:
                            pdf_bytes = pdf_file.read()
                            
                        st.download_button(
                            label="⬇️ Baixar PDF da Formulação",
                            data=pdf_bytes,
                            file_name=f"Formulacao_{product.code}_{formulation.version}.pdf",
                            mime="application/pdf"
                        )
                        
                        st.success("PDF gerado com sucesso!")
                        
                        # Limpar arquivo temporário
                        if os.path.exists(pdf_path):
                            os.remove(pdf_path)
                            
                    except Exception as e:
                        st.error(f"Erro ao gerar PDF: {str(e)}")

                if items_results:
                    st.markdown("**Composição**")
                    items_data = []
                    total_cost = 0

                    for item, rm_code, rm_name, rm_price, supplier_id, supplier_name in items_results:
                        # Use the proper cost calculation function
                        from services.business import material_cost_unit
                        rm = session.get(RawMaterial, item.raw_material_id)
                        item_cost = material_cost_unit(rm, item.qty, item.uom)
                        total_cost += item_cost

                        # Calculate percentage based on standard batch weight
                        # Convert item quantity to grams for percentage calculation
                        item_qty_in_grams = item.qty
                        if item.uom == "KG":
                            item_qty_in_grams = item.qty * 1000
                        elif item.uom == "L":
                            item_qty_in_grams = item.qty * 1000  # Assuming density ~1 g/ml
                        elif item.uom == "ML":
                            item_qty_in_grams = item.qty * 1  # Assuming density ~1 g/ml
                        # For "UN" keep original value (this might need adjustment based on actual unit)

                        # Calculate percentage based on standard batch weight
                        percentage_calc = (item_qty_in_grams / product.std_batch_weight * 100) if product.std_batch_weight > 0 else 0

                        # Only show cost information to admin users
                        if has_permission("manager"):
                            items_data.append({
                                "Código MP": rm_code,
                                "Matéria-Prima": rm_name,
                                "Fornecedor": supplier_name or "Não informado",
                                "Quantidade": f"{item.qty} {item.uom}",
                                "Preço Base": f"R$ {rm_price:.2f}/{rm.base_unit}",
                                "% Formulação": f"{percentage_calc:.1f}%",
                                "Custo": f"R$ {item_cost:.2f}"
                            })
                        else:
                            items_data.append({
                                "Código MP": rm_code,
                                "Matéria-Prima": rm_name,
                                "Fornecedor": supplier_name or "Não informado",
                                "Quantidade": f"{item.qty} {item.uom}",
                                "% Formulação": f"{percentage_calc:.1f}%"
                            })

                    items_df = pd.DataFrame(items_data)
                    st.dataframe(items_df, hide_index=True, use_container_width=True)

                    # Cost summary - only for admin users
                    if has_permission("manager"):
                        st.markdown("**Resumo de Custos**")
                        cost_col1, cost_col2, cost_col3 = st.columns(3)

                        with cost_col1:
                            st.metric("Custo Total do Lote", f"R$ {total_cost:.2f}")

                        with cost_col2:
                            if product.unit_weight > 0:
                                units_per_batch = product.std_batch_weight / product.unit_weight
                                unit_cost = total_cost / units_per_batch
                                st.metric("Custo por Unidade", f"R$ {unit_cost:.4f}")
                            else:
                                st.metric("Custo por Unidade", "N/A")

                        with cost_col3:
                            cost_per_gram = total_cost / product.std_batch_weight
                            st.metric("Custo por Grama", f"R$ {cost_per_gram:.4f}")

                # Formulation management actions
                if has_permission("operator"):
                    st.markdown("---")
                    st.subheader("🔧 Gerenciar Formulação")

                    manage_col1, manage_col2 = st.columns(2)

                    with manage_col1:
                        if st.button("✏️ Editar Formulação", use_container_width=True):
                            st.session_state.edit_formulation_id = selected_id
                            st.session_state.show_edit_formulation = True

                    with manage_col2:
                        if st.button("🗑️ Excluir Formulação", use_container_width=True, type="secondary"):
                            st.session_state.delete_formulation_id = selected_id
                            st.session_state.show_delete_formulation = True

                    # Edit formulation form
                    if st.session_state.get('show_edit_formulation') and st.session_state.get('edit_formulation_id') == selected_id:
                        st.markdown("### ✏️ Editar Formulação")

                        # Initialize edit items in session state if not exists
                        if f"edit_formula_items_{selected_id}" not in st.session_state:
                            # Load current items into session state
                            edit_items = []
                            for item, rm_code, rm_name, rm_price, supplier_id, supplier_name in items_results:
                                edit_items.append({
                                    "item_id": item.id,
                                    "rm_id": item.raw_material_id,
                                    "qty": item.qty,
                                    "uom": item.uom,
                                    "percent": item.percent or 0.0,
                                    "rm_code": rm_code,
                                    "rm_name": rm_name
                                })
                            st.session_state[f"edit_formula_items_{selected_id}"] = edit_items

                        # Get all raw materials for selection
                        with Session(engine) as session:
                            all_raw_materials = session.exec(select(RawMaterial).where(RawMaterial.status == "ativo")).all()

                        # Basic formulation info
                        edit_basic_col1, edit_basic_col2 = st.columns(2)

                        with edit_basic_col1:
                            edit_version = st.text_input("Versão *", value=formulation.version, key=f"edit_version_{selected_id}")
                            edit_state = st.selectbox("Estado *", ["Em desenvolvimento", "Aprovado/Em Uso"], 
                                                    index=0 if formulation.state == "Em desenvolvimento" else 1,
                                                    key=f"edit_state_{selected_id}")

                        with edit_basic_col2:
                            st.info(f"Produto: {product.code} - {product.name}")

                        # Show current formula items for editing
                        st.markdown("**Composição da Formulação**")

                        # Calculate current batch weight
                        current_batch_weight = 0.0
                        for item in st.session_state[f"edit_formula_items_{selected_id}"]:
                            if item["qty"] > 0:
                                qty_in_grams = item["qty"]
                                if item["uom"] == "KG":
                                    qty_in_grams *= 1000
                                elif item["uom"] == "L":
                                    qty_in_grams *= 1000
                                elif item["uom"] == "ML":
                                    qty_in_grams *= 1
                                current_batch_weight += qty_in_grams

                        st.info(f"📊 Lote padrão calculado: {current_batch_weight:.1f} g")

                        # Display editable formula items
                        for i, item in enumerate(st.session_state[f"edit_formula_items_{selected_id}"]):
                            item_col1, item_col2, item_col3, item_col4, item_col5 = st.columns([3, 1, 1, 1, 0.5])

                            with item_col1:
                                rm_options = [f"{rm.code} - {rm.name_usual}" for rm in all_raw_materials]
                                current_rm_option = f"{item['rm_code']} - {item['rm_name']}"

                                # Find current selection index
                                try:
                                    current_index = rm_options.index(current_rm_option) + 1  # +1 because of "Selecione..."
                                except ValueError:
                                    current_index = 0

                                rm_selection = st.selectbox(
                                    f"Matéria-Prima {i+1}", 
                                    ["Selecione..."] + rm_options, 
                                    index=current_index,
                                    key=f"edit_rm_{selected_id}_{i}"
                                )

                                if rm_selection != "Selecione...":
                                    selected_rm = all_raw_materials[rm_options.index(rm_selection)]
                                    item["rm_id"] = selected_rm.id
                                    item["rm_code"] = selected_rm.code
                                    item["rm_name"] = selected_rm.name_usual

                            with item_col2:
                                item["qty"] = st.number_input(
                                    f"Qtd {i+1}", 
                                    min_value=0.0, 
                                    value=float(item["qty"]), 
                                    step=0.1, 
                                    key=f"edit_qty_{selected_id}_{i}"
                                )

                            with item_col3:
                                current_uom_index = ["G", "KG", "ML", "L", "UN"].index(item["uom"])
                                item["uom"] = st.selectbox(
                                    f"UOM {i+1}", 
                                    ["G", "KG", "ML", "L", "UN"], 
                                    index=current_uom_index,
                                    key=f"edit_uom_{selected_id}_{i}"
                                )

                            with item_col4:
                                item["percent"] = st.number_input(
                                    f"% {i+1}", 
                                    min_value=0.0, 
                                    max_value=100.0, 
                                    value=float(item["percent"]), 
                                    step=0.1, 
                                    key=f"edit_percent_{selected_id}_{i}"
                                )

                            with item_col5:
                                if st.button("🗑️", key=f"delete_item_{selected_id}_{i}", help="Remover item"):
                                    st.session_state[f"edit_formula_items_{selected_id}"].pop(i)
                                    st.rerun()

                        # Item management buttons
                        item_mgmt_col1, item_mgmt_col2, item_mgmt_col3 = st.columns(3)

                        with item_mgmt_col1:
                            if st.button("➕ Adicionar Item", key=f"add_item_{selected_id}"):
                                st.session_state[f"edit_formula_items_{selected_id}"].append({
                                    "item_id": None,  # New item
                                    "rm_id": None,
                                    "qty": 0.0,
                                    "uom": "G",
                                    "percent": 0.0,
                                    "rm_code": "",
                                    "rm_name": ""
                                })
                                st.rerun()

                        with item_mgmt_col2:
                            if st.button("💾 Salvar Alterações", key=f"save_edit_{selected_id}", type="primary"):
                                if not edit_version:
                                    st.error("Versão é obrigatória.")
                                elif not any(item["rm_id"] for item in st.session_state[f"edit_formula_items_{selected_id}"]):
                                    st.error("A formulação deve ter pelo menos um item.")
                                else:
                                    try:
                                        with Session(engine) as session:
                                            # Check if new version already exists (if changed)
                                            if edit_version != formulation.version:
                                                existing = session.exec(
                                                    select(Formulation)
                                                    .where(Formulation.product_id == formulation.product_id)
                                                    .where(Formulation.version == edit_version)
                                                ).first()

                                                if existing:
                                                    st.error("Já existe uma formulação com esta versão para este produto.")
                                                    st.stop()

                                            # Update formulation basic info
                                            formulation_to_update = session.get(Formulation, selected_id)
                                            if formulation_to_update:
                                                formulation_to_update.version = edit_version

                                                # Se mudando para "Aprovado/Em Uso", automaticamente aprovar
                                                if edit_state == "Aprovado/Em Uso" and formulation_to_update.state != "Aprovado/Em Uso":
                                                    formulation_to_update.approved_by = user["name"]
                                                    from datetime import datetime
                                                    formulation_to_update.approved_at = datetime.now()

                                                formulation_to_update.state = edit_state

                                                # Delete all existing formula items
                                                existing_items = session.exec(
                                                    select(FormulaItem).where(FormulaItem.formulation_id == selected_id)
                                                ).all()
                                                for existing_item in existing_items:
                                                    session.delete(existing_item)

                                                # Add updated formula items and calculate total batch weight
                                                total_batch_weight = 0.0
                                                for item in st.session_state[f"edit_formula_items_{selected_id}"]:
                                                    if item["rm_id"] and item["qty"] > 0:
                                                        formula_item = FormulaItem(
                                                            formulation_id=selected_id,
                                                            raw_material_id=item["rm_id"],
                                                            qty=item["qty"],
                                                            uom=item["uom"],
                                                            percent=item["percent"] if item["percent"] > 0 else None
                                                        )
                                                        session.add(formula_item)

                                                        # Convert quantity to grams for batch weight calculation
                                                        qty_in_grams = item["qty"]
                                                        if item["uom"] == "KG":
                                                            qty_in_grams *= 1000
                                                        elif item["uom"] == "L":
                                                            qty_in_grams *= 1000
                                                        elif item["uom"] == "ML":
                                                            qty_in_grams *= 1

                                                        total_batch_weight += qty_in_grams

                                                # Update product's standard batch weight
                                                product_to_update = session.get(Product, formulation_to_update.product_id)
                                                if product_to_update and total_batch_weight > 0:
                                                    product_to_update.std_batch_weight = total_batch_weight

                                                session.commit()

                                                if edit_state == "Aprovado/Em Uso":
                                                    st.success("Formulação atualizada e automaticamente aprovada!")
                                                else:
                                                    st.success("Formulação atualizada com sucesso!")

                                                # Clear session state
                                                del st.session_state[f"edit_formula_items_{selected_id}"]
                                                st.session_state.show_edit_formulation = False
                                                st.rerun()

                                    except Exception as e:
                                        st.error(f"Erro ao atualizar formulação: {str(e)}")

                        with item_mgmt_col3:
                            if st.button("❌ Cancelar", key=f"cancel_edit_{selected_id}"):
                                # Clear session state
                                if f"edit_formula_items_{selected_id}" in st.session_state:
                                    del st.session_state[f"edit_formula_items_{selected_id}"]
                                st.session_state.show_edit_formulation = False
                                st.rerun()

                    # Delete confirmation
                    if st.session_state.get('show_delete_formulation') and st.session_state.get('delete_formulation_id') == selected_id:
                        st.markdown("### ⚠️ Confirmar Exclusão")
                        st.warning(f"Tem certeza que deseja excluir a formulação **{formulation.version}** do produto **{product.code} - {product.name}**?")
                        st.error("**ATENÇÃO:** Esta ação não pode ser desfeita e removerá todos os itens da formulação!")

                        delete_col1, delete_col2 = st.columns(2)

                        with delete_col1:
                            if st.button("🗑️ Sim, Excluir", use_container_width=True, type="primary"):
                                try:
                                    with Session(engine) as session:
                                        # Delete formula items first
                                        formula_items = session.exec(
                                            select(FormulaItem).where(FormulaItem.formulation_id == selected_id)
                                        ).all()

                                        for item in formula_items:
                                            session.delete(item)

                                        # Delete formulation
                                        formulation_to_delete = session.get(Formulation, selected_id)
                                        if formulation_to_delete:
                                            session.delete(formulation_to_delete)
                                            session.commit()
                                            st.success(f"Formulação '{formulation.version}' excluída com sucesso!")
                                            st.session_state.show_delete_formulation = False
                                            st.rerun()

                                except Exception as e:
                                    st.error(f"Erro ao excluir formulação: {str(e)}")

                        with delete_col2:
                            if st.button("❌ Cancelar", use_container_width=True):
                                st.session_state.show_delete_formulation = False
                                st.rerun()

                else:
                    st.info("Esta formulação não possui itens cadastrados.")
        else:
            st.info("Você não tem permissão para visualizar os detalhes das formulações.")
    else:
        st.info("Nenhuma formulação cadastrada.")

with tab2:
    st.subheader("Cadastrar Formulação")

    if not has_permission("operator"):
        st.error("Você não tem permissão para criar formulações.")
    else:
        # Product selection
        with Session(engine) as session:
            products = session.exec(select(Product).where(Product.status == "ativo")).all()

        if not products:
            st.error("Nenhum produto ativo encontrado. Cadastre produtos primeiro.")
        else:
            with st.form("new_formulation_form"):
                col1, col2 = st.columns(2)

                with col1:
                    product_options = [f"{p.code} - {p.name}" for p in products]
                    selected_product_option = st.selectbox("Produto *", product_options)
                    selected_product_id = products[product_options.index(selected_product_option)].id

                    version = st.text_input("Versão *", value="v1", placeholder="v1, v2, etc.")

                with col2:
                    client_name = st.text_input("Cliente", placeholder="Nome do cliente")
                    state = st.selectbox("Estado *", ["Em desenvolvimento", "Aprovado/Em Uso"], index=0)

                st.markdown("**Composição da Formulação**")

                # Get raw materials for selection
                with Session(engine) as session:
                    raw_materials = session.exec(select(RawMaterial).where(RawMaterial.status == "ativo")).all()

                if not raw_materials:
                    st.error("Nenhuma matéria-prima ativa encontrada. Cadastre matérias-primas primeiro.")
                else:
                    # Dynamic formula items
                    if "formula_items" not in st.session_state:
                        st.session_state.formula_items = [{"rm_id": None, "qty": 0.0, "uom": "G", "percent": 0.0}]

                    # Calculate and display current batch weight
                    current_batch_weight = 0.0
                    for item in st.session_state.formula_items:
                        if item["qty"] > 0:
                            qty_in_grams = item["qty"]
                            if item["uom"] == "KG":
                                qty_in_grams *= 1000
                            elif item["uom"] == "L":
                                qty_in_grams *= 1000
                            elif item["uom"] == "ML":
                                qty_in_grams *= 1
                            current_batch_weight += qty_in_grams

                    st.info(f"📊 Lote padrão calculado: {current_batch_weight:.1f} g")

                    # Display formula items
                    for i, item in enumerate(st.session_state.formula_items):
                        item_col1, item_col2, item_col3, item_col4 = st.columns([3, 1, 1, 1])

                        with item_col1:
                            rm_options = [f"{rm.code} - {rm.name_usual}" for rm in raw_materials]
                            rm_selection = st.selectbox(f"Matéria-Prima {i+1}", ["Selecione..."] + rm_options, key=f"rm_{i}")
                            if rm_selection != "Selecione...":
                                item["rm_id"] = raw_materials[rm_options.index(rm_selection)].id

                        with item_col2:
                            item["qty"] = st.number_input(f"Qtd {i+1}", min_value=0.0, value=item["qty"], step=0.1, key=f"qty_{i}")

                        with item_col3:
                            item["uom"] = st.selectbox(f"UOM {i+1}", ["G", "KG", "ML", "L", "UN"], 
                                                     index=["G", "KG", "ML", "L", "UN"].index(item["uom"]), key=f"uom_{i}")

                        with item_col4:
                            item["percent"] = st.number_input(f"% {i+1}", min_value=0.0, max_value=100.0, 
                                                            value=item["percent"], step=0.1, key=f"percent_{i}")

                    submitted = st.form_submit_button("💾 Criar Formulação", use_container_width=True)

            # Item management buttons (outside form)
            item_mgmt_col1, item_mgmt_col2 = st.columns(2)

            with item_mgmt_col1:
                if st.button("➕ Adicionar Item"):
                    st.session_state.formula_items.append({"rm_id": None, "qty": 0.0, "uom": "G", "percent": 0.0})
                    st.rerun()

            with item_mgmt_col2:
                if len(st.session_state.formula_items) > 1:
                    if st.button("🗑️ Remover Último Item"):
                        st.session_state.formula_items.pop()
                        st.rerun()

            if submitted:
                if not version:
                    st.error("Versão é obrigatória.")
                elif not any(item["rm_id"] for item in st.session_state.formula_items):
                    st.error("Adicione pelo menos um item à formulação.")
                else:
                    try:
                        with Session(engine) as session:
                            # Check if formulation already exists
                            existing = session.exec(
                                select(Formulation)
                                .where(Formulation.product_id == selected_product_id)
                                .where(Formulation.version == version)
                            ).first()

                            if existing:
                                st.error(f"Já existe uma formulação versão '{version}' para este produto.")
                            else:
                                # Create formulation
                                new_formulation = Formulation(
                                    product_id=selected_product_id,
                                    version=version,
                                    state=state
                                )

                                # Se criando com estado "Aprovado/Em Uso", automaticamente aprovar
                                if state == "Aprovado/Em Uso":
                                    new_formulation.approved_by = user["name"]
                                    from datetime import datetime
                                    new_formulation.approved_at = datetime.now()

                                session.add(new_formulation)
                                session.flush()  # Get the ID

                                # Add formula items and calculate total batch weight
                                total_batch_weight = 0.0
                                for item in st.session_state.formula_items:
                                    if item["rm_id"] and item["qty"] > 0:
                                        formula_item = FormulaItem(
                                            formulation_id=new_formulation.id,
                                            raw_material_id=item["rm_id"],
                                            qty=item["qty"],
                                            uom=item["uom"],
                                            percent=item["percent"] if item["percent"] > 0 else None
                                        )
                                        session.add(formula_item)

                                        # Convert quantity to grams for batch weight calculation
                                        qty_in_grams = item["qty"]
                                        if item["uom"] == "KG":
                                            qty_in_grams *= 1000
                                        elif item["uom"] == "L":
                                            qty_in_grams *= 1000  # Assuming density ~1 g/ml
                                        elif item["uom"] == "ML":
                                            qty_in_grams *= 1  # Assuming density ~1 g/ml
                                        # For "UN" we'll keep the original value

                                        total_batch_weight += qty_in_grams

                                # Update product's standard batch weight
                                product = session.get(Product, selected_product_id)
                                if product and total_batch_weight > 0:
                                    product.std_batch_weight = total_batch_weight

                                session.commit()
                                st.success(f"Formulação '{version}' criada com sucesso!")

                                # Clear session state
                                del st.session_state.formula_items
                                st.rerun()

                    except Exception as e:
                        st.error(f"Erro ao criar formulação: {str(e)}")

if tab3:  # Only available for managers
    with tab3:
        st.subheader("Análise de Custos")
        # Get formulations for analysis
        with Session(engine) as session:
            approved_formulations = session.exec(
                select(Formulation, Product.name, Product.code)
                .join(Product, Formulation.product_id == Product.id)
                .where(Formulation.state == "Aprovado/Em Uso")
            ).all()

        if approved_formulations:
            # Formulation selection for cost analysis
            formulation_options = [f"{code} - {name} (v{form.version})" for form, name, code in approved_formulations]
            selected_formulation_option = st.selectbox("Selecione uma formulação para análise:", formulation_options)

            if selected_formulation_option:
                selected_index = formulation_options.index(selected_formulation_option)
                selected_formulation = approved_formulations[selected_index][0]
                selected_product_name = approved_formulations[selected_index][1]
                selected_product_code = approved_formulations[selected_index][2]

                # Get the actual product object
                with Session(engine) as session:
                    product = session.get(Product, selected_formulation.product_id)

                col1, col2 = st.columns(2)

                with col1:
                    batch_size = st.number_input("Tamanho do Lote (g):", min_value=1.0, 
                                               value=float(product.std_batch_weight), step=100.0)

                with col2:
                    target_units = st.number_input("Unidades Desejadas:", min_value=1, value=100, step=10)

                if st.button("🧮 Calcular Custos"):
                    with Session(engine) as session:
                        # Get cost calculation
                        total_cost, unit_cost = formulation_cost(session, selected_formulation.id, batch_size)

                        # Display results
                        st.markdown("---")
                        st.markdown("### Resultado da Análise")

                        metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)

                        with metrics_col1:
                            st.metric("Custo Total do Lote", f"R$ {total_cost:.2f}")

                        with metrics_col2:
                            st.metric("Custo por Grama", f"R$ {total_cost/batch_size:.4f}")

                        with metrics_col3:
                            st.metric("Custo por Unidade", f"R$ {unit_cost:.4f}")

                        with metrics_col4:
                            total_cost_target = (total_cost / batch_size) * (target_units * product.unit_weight)
                            st.metric(f"Custo para {target_units} unidades", f"R$ {total_cost_target:.2f}")

                        # Detailed breakdown
                        st.markdown("### Breakdown por Matéria-Prima")

                        items_query = select(FormulaItem, RawMaterial.code, RawMaterial.name_usual, RawMaterial.base_price).join(
                            RawMaterial, FormulaItem.raw_material_id == RawMaterial.id
                        ).where(FormulaItem.formulation_id == selected_formulation.id)

                        items_results = session.exec(items_query).all()

                        breakdown_data = []
                        for item, rm_code, rm_name, rm_price in items_results:
                            from services.business import material_cost_unit
                            rm = session.get(RawMaterial, item.raw_material_id)
                            item_cost = material_cost_unit(rm, item.qty, item.uom)
                            percentage = (item_cost / total_cost * 100) if total_cost > 0 else 0

                            breakdown_data.append({
                                "Código MP": rm_code,
                                "Matéria-Prima": rm_name,
                                "Quantidade": f"{item.qty} {item.uom}",
                                "Preço Unitário": f"R$ {rm_price:.2f}",
                                "Custo Total": f"R$ {item_cost:.2f}",
                                "% do Custo": f"{percentage:.1f}%"
                            })

                        breakdown_df = pd.DataFrame(breakdown_data)
                        st.dataframe(breakdown_df, hide_index=True, use_container_width=True)

                        # Cost chart
                        if breakdown_data:
                            import plotly.express as px
                            chart_df = pd.DataFrame([
                                {"Material": row["Matéria-Prima"], "Custo": float(row["Custo Total"].replace("R$ ", ""))}
                                for row in breakdown_data
                            ])

                            fig = px.pie(chart_df, values="Custo", names="Material", 
                                       title="Distribuição de Custos por Matéria-Prima")
                            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhuma formulação aprovada encontrada.")