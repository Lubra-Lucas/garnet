# pages/4_Produtos.py
import streamlit as st
from auth import require_login, has_permission
from sqlmodel import Session, select
from db import engine, get_session
from models import Product, StockLot
from schema import ProductCreate, ProductUpdate
from services.io_import import import_products_from_excel, generate_import_template
from services.io_export import export_products_to_excel
import pandas as pd

# Require login for this page
user = require_login()

st.set_page_config(page_title="GARNET - Produtos", layout="wide")

# Professional page header
st.markdown("""
<div style="padding: 1rem 0 2rem 0; border-bottom: 1px solid #E8E8E8; margin-bottom: 2rem;">
    <h1 style="margin: 0; color: #2E4A6B; font-weight: 300;">Gestão de Produtos</h1>
    <p style="margin: 0.5rem 0 0 0; color: #666; font-size: 1.1rem;">Cadastro e controle de produtos acabados</p>
</div>
""", unsafe_allow_html=True)

# Clean tabs without icons
tab1, tab2, tab3 = st.tabs(["Catálogo", "Cadastro", "Importar / Exportar"])

with tab1:
    # Clean section header
    st.markdown("""
    <div style="margin-bottom: 1.5rem;">
        <h3 style="margin: 0; color: #2E4A6B; font-weight: 400;">Catálogo de Produtos</h3>
    </div>
    """, unsafe_allow_html=True)

    # Clean filters layout
    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns([2, 1, 1, 1])

    with filter_col1:
        search_term = st.text_input("Buscar por código ou nome", placeholder="Digite para filtrar...")

    with filter_col2:
        # Get unique clients for filter
        with get_session() as session:
            products_for_clients = session.exec(select(Product.client).distinct()).all()
            client_options = ["Todos"] + [c for c in products_for_clients if c]

        client_filter = st.selectbox("Cliente:", client_options)

    with filter_col3:
        # Get unique categories for filter
        with get_session() as session:
            products_for_categories = session.exec(select(Product.category).distinct()).all()
            category_options = ["Todas"] + [c for c in products_for_categories if c]

        category_filter = st.selectbox("Categoria:", category_options)

    with filter_col4:
        status_filter = st.selectbox("Status:", ["Todos", "ativo", "inativo"])

    # Get products with filters
    with get_session() as session:
        query = select(Product)

        if search_term:
            query = query.where(
                (Product.code.ilike(f"%{search_term}%")) |
                (Product.name.ilike(f"%{search_term}%"))
            )

        if client_filter != "Todos":
            query = query.where(Product.client == client_filter)

        if category_filter != "Todas":
            query = query.where(Product.category == category_filter)

        if status_filter != "Todos":
            query = query.where(Product.status == status_filter)

        products = session.exec(query.order_by(Product.code)).all()

    if products:
        # Convert to DataFrame for display
        product_data = []
        for product in products:
            product_data.append({
                "ID": product.id,
                "Código": product.code,
                "Nome": product.name,
                "Cliente": product.client or "N/A",
                "Categoria": product.category or "N/A",
                "Peso Unitário": f"{product.unit_weight} {product.unit_uom}",
                "Lote Padrão": f"{product.std_batch_weight} g",
                "Status": product.status
            })

        df = pd.DataFrame(product_data)

        # Display as interactive table
        if has_permission("manager"):
            edited_df = st.data_editor(
                df,
                hide_index=True,
                use_container_width=True,
                disabled=["ID", "Código"],
                column_config={
                    "Status": st.column_config.SelectboxColumn(
                        "Status",
                        options=["ativo", "inativo"],
                        required=True
                    )
                }
            )

            # Update button
            if st.button("💾 Salvar Alterações"):
                with get_session() as session:
                    for idx, row in edited_df.iterrows():
                        product = session.get(Product, row["ID"])
                        if product:
                            product.name = row["Nome"]
                            product.client = row["Cliente"] if row["Cliente"] != "N/A" else None
                            product.category = row["Categoria"] if row["Categoria"] != "N/A" else None
                            product.status = row["Status"]

                    session.commit()
                    st.success("Alterações salvas com sucesso!")
                    st.rerun()
        else:
            st.dataframe(df, hide_index=True, use_container_width=True)

        # Detailed view section
        st.markdown("---")
        st.subheader("Detalhes do Produto")

        selected_product_code = st.selectbox(
            "Selecione um produto para ver detalhes:",
            options=[p.code for p in products]
        )

        selected_product = next(p for p in products if p.code == selected_product_code)

        detail_col1, detail_col2, detail_col3 = st.columns(3)

        with detail_col1:
            st.markdown("**Identificação**")
            st.text(f"Código: {selected_product.code}")
            st.text(f"Nome: {selected_product.name}")
            st.text(f"Cliente: {selected_product.client or 'N/A'}")
            st.text(f"Categoria: {selected_product.category or 'N/A'}")

        with detail_col2:
            st.markdown("**Especificações**")
            st.text(f"Peso Unitário: {selected_product.unit_weight} {selected_product.unit_uom}")
            st.text(f"Lote Padrão: {selected_product.std_batch_weight} g")
            st.text(f"Status: {selected_product.status}")

        with detail_col3:
            st.markdown("**Cálculos**")
            if selected_product.unit_weight > 0 and selected_product.std_batch_weight > 0:
                units_per_batch = selected_product.std_batch_weight / selected_product.unit_weight
                st.text(f"Unidades por Lote: {units_per_batch:.0f}")

                # Calculate yield percentage
                yield_percent = (selected_product.unit_weight * units_per_batch) / selected_product.std_batch_weight * 100
                st.text(f"Rendimento: {yield_percent:.1f}%")
            else:
                if selected_product.unit_weight > 0:
                    st.text("Unidades por Lote: N/A (lote padrão não definido)")
                else:
                    st.text("Unidades por Lote: N/A")
                st.text("Rendimento: N/A")

        # Product management actions
        if has_permission("operator"):
            st.markdown("---")
            st.subheader("🔧 Gerenciar Produto")

            manage_col1, manage_col2 = st.columns(2)

            with manage_col1:
                if st.button("✏️ Editar Produto", use_container_width=True):
                    st.session_state.edit_product_id = selected_product.id
                    st.session_state.show_edit_form = True

            with manage_col2:
                if st.button("🗑️ Excluir Produto", use_container_width=True, type="secondary"):
                    st.session_state.delete_product_id = selected_product.id
                    st.session_state.show_delete_confirm = True

            # Edit product form
            if st.session_state.get('show_edit_form') and st.session_state.get('edit_product_id') == selected_product.id:
                st.markdown("### ✏️ Editar Produto")

                with st.form(f"edit_product_{selected_product.id}"):
                    edit_col1, edit_col2 = st.columns(2)

                    with edit_col1:
                        edit_code = st.text_input("Código *", value=selected_product.code)
                        edit_name = st.text_input("Nome do Produto *", value=selected_product.name)
                        edit_client = st.text_input("Cliente", value=selected_product.client or "")
                        edit_category = st.text_input("Categoria", value=selected_product.category or "")

                    with edit_col2:
                        edit_unit_weight = st.number_input("Peso Unitário *", min_value=0.0, value=float(selected_product.unit_weight), step=0.1)
                        edit_unit_uom = st.selectbox("Unidade de Medida *", ["G", "ML", "UN"], index=["G", "ML", "UN"].index(selected_product.unit_uom))
                        st.info(f"Lote Padrão: {selected_product.std_batch_weight} g (calculado automaticamente pela formulação)")
                        status = st.selectbox("Status", ["ativo", "inativo"], index=0 if selected_product.status == "ativo" else 1)

                    edit_col3, edit_col4 = st.columns(2)

                    with edit_col3:
                        if st.form_submit_button("💾 Salvar Alterações", use_container_width=True):
                            if not edit_code or not edit_name or edit_unit_weight <= 0:
                                st.error("Código, Nome e Peso Unitário são obrigatórios.")
                            else:
                                try:
                                    with get_session() as session:
                                        # Check if new code already exists (if changed)
                                        if edit_code != selected_product.code:
                                            existing = session.exec(
                                                select(Product).where(Product.code == edit_code)
                                            ).first()

                                            if existing:
                                                st.error("Já existe um produto com este código.")
                                                st.stop()

                                        # Update product
                                        product_to_update = session.get(Product, selected_product.id)
                                        if product_to_update:
                                            product_to_update.code = edit_code
                                            product_to_update.name = edit_name
                                            product_to_update.client = edit_client if edit_client else None
                                            product_to_update.category = edit_category if edit_category else None
                                            product_to_update.unit_weight = edit_unit_weight
                                            product_to_update.unit_uom = edit_unit_uom
                                            product_to_update.std_batch_weight = selected_product.std_batch_weight # Keep calculated value
                                            product_to_update.status = status

                                            session.commit()
                                            st.success("Produto atualizado com sucesso!")
                                            st.session_state.show_edit_form = False
                                            st.rerun()

                                except Exception as e:
                                    st.error(f"Erro ao atualizar produto: {str(e)}")

                    with edit_col4:
                        if st.form_submit_button("❌ Cancelar", use_container_width=True):
                            st.session_state.show_edit_form = False
                            st.rerun()

            # Delete confirmation
            if st.session_state.get('show_delete_confirm') and st.session_state.get('delete_product_id') == selected_product.id:
                st.markdown("### ⚠️ Confirmar Exclusão")
                st.warning(f"Tem certeza que deseja excluir o produto **{selected_product.code} - {selected_product.name}**?")
                st.error("**ATENÇÃO:** Esta ação não pode ser desfeita!")

                delete_col1, delete_col2 = st.columns(2)

                with delete_col1:
                    if st.button("🗑️ Sim, Excluir", use_container_width=True, type="primary"):
                        try:
                            with get_session() as session:
                                # Delete all related records to avoid foreign key constraints
                                
                                # Delete stock lots
                                stock_lots_deleted = session.exec(
                                    select(StockLot).where(
                                        (StockLot.item_type == "PA") &
                                        (StockLot.item_id == selected_product.id)
                                    )
                                ).all()
                                
                                for lot in stock_lots_deleted:
                                    session.delete(lot)
                                
                                # Delete production orders
                                from models import ProductionOrder
                                production_orders_deleted = session.exec(
                                    select(ProductionOrder).where(
                                        ProductionOrder.product_id == selected_product.id
                                    )
                                ).all()
                                
                                for po in production_orders_deleted:
                                    session.delete(po)
                                
                                # Delete formulations and their items
                                from models import Formulation, FormulaItem
                                formulations_deleted = session.exec(
                                    select(Formulation).where(
                                        Formulation.product_id == selected_product.id
                                    )
                                ).all()
                                
                                for formulation in formulations_deleted:
                                    # Delete formulation items first
                                    formula_items = session.exec(
                                        select(FormulaItem).where(
                                            FormulaItem.formulation_id == formulation.id
                                        )
                                    ).all()
                                    
                                    for item in formula_items:
                                        session.delete(item)
                                    
                                    # Delete formulation
                                    session.delete(formulation)
                                
                                # Finally delete the product
                                product_to_delete = session.get(Product, selected_product.id)
                                if product_to_delete:
                                    session.delete(product_to_delete)
                                    session.commit()
                                    
                                    # Build success message
                                    success_msg = f"Produto '{selected_product.code}' excluído com sucesso!"
                                    details = []
                                    
                                    if len(stock_lots_deleted) > 0:
                                        details.append(f"{len(stock_lots_deleted)} lotes de estoque")
                                    if len(production_orders_deleted) > 0:
                                        details.append(f"{len(production_orders_deleted)} ordens de produção")
                                    if len(formulations_deleted) > 0:
                                        details.append(f"{len(formulations_deleted)} formulações")
                                    
                                    if details:
                                        success_msg += f" (Também foram removidos: {', '.join(details)})"
                                    
                                    st.success(success_msg)
                                    st.session_state.show_delete_confirm = False
                                    st.rerun()

                        except Exception as e:
                            st.error(f"Erro ao excluir produto: {str(e)}")

                with delete_col2:
                    if st.button("❌ Cancelar", use_container_width=True):
                        st.session_state.show_delete_confirm = False
                        st.rerun()

    else:
        st.info("Nenhum produto encontrado com os filtros aplicados.")

with tab2:
    st.subheader("Cadastrar Novo Produto")

    if not has_permission("operator"):
        st.error("Você não tem permissão para cadastrar produtos.")
    else:
        with st.form("new_product_form"):
            col1, col2 = st.columns(2)

            with col1:
                code = st.text_input("Código *", placeholder="PA001")
                name = st.text_input("Nome do Produto *", placeholder="Nome do produto")
                client = st.text_input("Cliente", placeholder="Nome do cliente")
                category = st.text_input("Categoria", placeholder="Categoria do produto")

            with col2:
                unit_weight = st.number_input("Peso Unitário *", min_value=0.0, value=100.0, step=0.1)
                unit_uom = st.selectbox("Unidade de Medida *", ["G", "ML", "UN"])
                # Removed manual input for std_batch_weight
                st.info("Lote Padrão: será calculado automaticamente pela formulação.")

            submitted = st.form_submit_button("💾 Cadastrar Produto", use_container_width=True)

            if submitted:
                if not code or not name or unit_weight <= 0:
                    st.error("Código, Nome e Peso Unitário são obrigatórios.")
                else:
                    try:
                        with get_session() as session:
                            # Check if code already exists
                            existing = session.exec(
                                select(Product).where(Product.code == code)
                            ).first()

                            if existing:
                                st.error("Já existe um produto com este código.")
                            else:
                                product_data = {
                                    "code": code,
                                    "name": name,
                                    "client": client if client else None,
                                    "category": category if category else None,
                                    "unit_weight": unit_weight,
                                    "unit_uom": unit_uom,
                                    "std_batch_weight": 0 # Default to 0, will be updated by formulation
                                }

                                new_product = Product(**product_data)
                                session.add(new_product)
                                session.commit()

                                st.success(f"Produto '{code}' cadastrado com sucesso!")
                                st.rerun()

                    except Exception as e:
                        st.error(f"Erro ao cadastrar produto: {str(e)}")

with tab3:
    st.subheader("Importar e Exportar Dados")

    import_col, export_col = st.columns(2)

    with import_col:
        st.markdown("#### 📥 Importar Produtos")

        if not has_permission("operator"):
            st.error("Você não tem permissão para importar dados.")
        else:
            # Download template
            if st.button("📄 Baixar Modelo Excel", use_container_width=True):
                template = generate_import_template("products")
                st.download_button(
                    label="📥 Download Modelo",
                    data=template.getvalue(),
                    file_name="modelo_produtos.xlsx",
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
                        with get_session() as session:
                            result = import_products_from_excel(uploaded_file, session)

                        if result["success"]:
                            st.success(f"✅ {result['imported_count']} produtos importados de {result['total_rows']} linhas!")

                            if result["errors"]:
                                st.warning("⚠️ Alguns registros apresentaram problemas:")
                                for error in result["errors"]:
                                    st.text(f"• {error}")
                        else:
                            st.error(f"❌ Erro na importação: {result['error']}")

    with export_col:
        st.markdown("#### 📤 Exportar Produtos")

        if st.button("📊 Exportar para Excel", use_container_width=True):
            with st.spinner("Gerando arquivo..."):
                with get_session() as session:
                    excel_data = export_products_to_excel(session)

                st.download_button(
                    label="📥 Download Excel",
                    data=excel_data.getvalue(),
                    file_name=f"produtos_export_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

# Statistics section
if st.checkbox("📊 Mostrar Estatísticas"):
    with get_session() as session:
        all_products = session.exec(select(Product)).all()

        if all_products:
            stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)

            with stats_col1:
                st.metric("Total de Produtos", len(all_products))

            with stats_col2:
                active_count = sum(1 for p in all_products if p.status == "ativo")
                st.metric("Produtos Ativos", active_count)

            with stats_col3:
                unique_clients = len(set(p.client for p in all_products if p.client))
                st.metric("Clientes Únicos", unique_clients)

            with stats_col4:
                avg_weight = sum(p.unit_weight for p in all_products) / len(all_products)
                st.metric("Peso Médio", f"{avg_weight:.1f} g")

            # Category distribution
            if any(p.category for p in all_products):
                st.markdown("---")
                st.subheader("📊 Distribuição por Categoria")

                category_counts = {}
                for product in all_products:
                    category = product.category or "Sem Categoria"
                    category_counts[category] = category_counts.get(category, 0) + 1

                cat_df = pd.DataFrame(list(category_counts.items()), columns=["Categoria", "Quantidade"])

                import plotly.express as px
                fig = px.pie(cat_df, values="Quantidade", names="Categoria", title="Produtos por Categoria")
                st.plotly_chart(fig, use_container_width=True)