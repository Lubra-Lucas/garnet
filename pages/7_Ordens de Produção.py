# pages/7_OrdensProducao.py
import streamlit as st
from auth import require_login, has_permission
from sqlmodel import Session, select
from db import engine, get_session
from models import ProductionOrder, Product, Formulation, FormulaItem, StockLot, RawMaterial
from services.business import mrp_requirements
import pandas as pd
from datetime import date, timedelta

# Require login for this page
user = require_login()

st.set_page_config(page_title="GARNET - Ordens de Produção", layout="wide")

# Professional page header
st.markdown("""
<div style="padding: 1rem 0 2rem 0; border-bottom: 1px solid #E8E8E8; margin-bottom: 2rem;">
    <h1 style="margin: 0; color: #2E4A6B; font-weight: 300;">Ordens de Produção</h1>
    <p style="margin: 0.5rem 0 0 0; color: #666; font-size: 1.1rem;">Planejamento e controle de produção industrial</p>
</div>
""", unsafe_allow_html=True)

# Clean tabs without icons
tab1, tab2, tab3 = st.tabs(["Lista de Ordens", "Nova Ordem", "Planejamento"])

with tab1:
    st.subheader("Ordens de Produção")

    # Info about automatic stock consumption
    with st.expander("ℹ️ Informações sobre Baixa Automática do Estoque"):
        st.markdown("""
        **Como funciona a baixa automática:**
        
        1. Quando uma ordem de produção é marcada como **"Concluída"**, o sistema automaticamente:
           - Calcula as matérias-primas necessárias baseado na formulação aprovada
           - Consome as quantidades do estoque usando lógica FEFO (First Expired, First Out)
           - Atualiza as quantidades dos lotes de estoque
        
        2. **Lógica FEFO**: Prioriza o consumo de lotes com data de vencimento mais próxima
        
        3. **Conversão de Unidades**: O sistema converte automaticamente entre diferentes unidades (kg↔g, L↔mL)
        
        4. **Estoque Insuficiente**: Se não houver estoque suficiente, o sistema consome o que está disponível e registra o que falta
        
        ⚠️ **Importante**: A baixa só ocorre quando o status muda para "Concluída". Certifique-se de que a formulação do produto esteja aprovada.
        """)

    # Filters
    filter_col1, filter_col2, filter_col3 = st.columns(3)

    with filter_col1:
        search_term = st.text_input("🔍 Buscar por código:", placeholder="OP-2024-001")

    with filter_col2:
        status_filter = st.selectbox("Status:", ["Todos", "Planejada", "Em Produção", "Concluída", "Cancelada"])

    with filter_col3:
        # Date range filter
        date_filter = st.selectbox("Período:", ["Todas", "Esta Semana", "Este Mês", "Últimos 30 dias"])

    # Get production orders
    with get_session() as session:
        query = select(ProductionOrder, Product.name, Product.code).join(
            Product, ProductionOrder.product_id == Product.id
        )

        if search_term:
            query = query.where(ProductionOrder.code.ilike(f"%{search_term}%"))

        if status_filter != "Todos":
            query = query.where(ProductionOrder.status == status_filter)

        # Apply date filter
        if date_filter == "Esta Semana":
            start_date = date.today() - timedelta(days=date.today().weekday())
            query = query.where(ProductionOrder.start_date >= start_date)
        elif date_filter == "Este Mês":
            start_date = date.today().replace(day=1)
            query = query.where(ProductionOrder.start_date >= start_date)
        elif date_filter == "Últimos 30 dias":
            start_date = date.today() - timedelta(days=30)
            query = query.where(ProductionOrder.created_at >= start_date)

        results = session.exec(query.order_by(ProductionOrder.created_at.desc())).all()

    if results:
        po_data = []
        for po, product_name, product_code in results:
            # Calculate progress (placeholder logic)
            progress = 0
            if po.status == "Em Produção":
                progress = 50
            elif po.status == "Concluída":
                progress = 100

            # Add visual indicator for automatic consumption
            status_display = po.status
            if po.status == "Concluída":
                status_display = "✅ Concluída (Baixa Automática)"
            elif po.status == "Em Produção":
                status_display = "🔄 Em Produção"
            elif po.status == "Planejada":
                status_display = "📋 Planejada"
            elif po.status == "Cancelada":
                status_display = "❌ Cancelada"

            po_data.append({
                "ID": po.id,
                "Código": po.code,
                "Produto": f"{product_code} - {product_name}",
                "Quantidade (un)": po.qty_to_produce,
                "Lote Planejado": po.planned_lot or "N/A",
                "Data Início": po.start_date.strftime("%d/%m/%Y") if po.start_date else "N/A",
                "Data Fim": po.end_date.strftime("%d/%m/%Y") if po.end_date else "N/A",
                "Centro Trabalho": po.workcenter or "N/A",
                "Status": status_display,
                "Progresso %": progress,
                "Criado Por": po.created_by or "N/A"
            })

        df = pd.DataFrame(po_data)

        # Display with editing capabilities for operators
        if has_permission("operator"):
            edited_df = st.data_editor(
                df,
                hide_index=True,
                use_container_width=True,
                disabled=["ID", "Código", "Produto", "Criado Por"],
                column_config={
                    "Status": st.column_config.SelectboxColumn(
                        "Status",
                        options=["Planejada", "Em Produção", "Concluída", "Cancelada"],
                        required=True
                    ),
                    "Progresso %": st.column_config.ProgressColumn(
                        "Progresso %",
                        min_value=0,
                        max_value=100
                    )
                }
            )

            if st.button("💾 Salvar Alterações"):
                with get_session() as session:
                    changes_made = []
                    consumption_results = []
                    
                    for idx, row in edited_df.iterrows():
                        po = session.get(ProductionOrder, row["ID"])
                        if po:
                            # Check if status is changing to "Concluída"
                            old_status = po.status
                            new_status = row["Status"]
                            
                            # Update all fields
                            po.qty_to_produce = row["Quantidade (un)"]
                            po.planned_lot = row["Lote Planejado"] if row["Lote Planejado"] != "N/A" else None
                            po.workcenter = row["Centro Trabalho"] if row["Centro Trabalho"] != "N/A" else None
                            po.status = new_status

                            # Parse dates
                            try:
                                if row["Data Início"] != "N/A":
                                    po.start_date = pd.to_datetime(row["Data Início"], format="%d/%m/%Y").date()
                                if row["Data Fim"] != "N/A":
                                    po.end_date = pd.to_datetime(row["Data Fim"], format="%d/%m/%Y").date()
                            except:
                                pass  # Keep existing dates if parsing fails

                            # If status changed to "Concluída", consume raw materials from stock
                            if old_status != "Concluída" and new_status == "Concluída":
                                from services.business import consume_raw_materials_from_stock
                                consumption_result = consume_raw_materials_from_stock(session, po.product_id, po.qty_to_produce)
                                consumption_results.append({
                                    "po_code": po.code,
                                    "result": consumption_result
                                })
                                changes_made.append(f"Ordem {po.code} concluída - baixa automática executada")
                            else:
                                changes_made.append(f"Ordem {po.code} atualizada")

                    session.commit()
                    
                    # Show success message and consumption details
                    st.success("Alterações salvas com sucesso!")
                    
                    # Show consumption results if any
                    for consumption in consumption_results:
                        po_code = consumption["po_code"]
                        result = consumption["result"]
                        
                        if result["success"]:
                            st.success(f"✅ **Ordem {po_code}**: Baixa automática realizada com sucesso!")
                            
                            # Show consumption details
                            with st.expander(f"Ver detalhes da baixa - Ordem {po_code}"):
                                st.info(f"Produção: {result['produced_units']:.0f} unidades (proporção: {result['proportion_used']:.3f}x)")
                                
                                for consumption in result["consumptions"]:
                                    st.markdown(f"**{consumption['raw_material_code']} - {consumption['raw_material_name']}**")
                                    st.text(f"Necessário: {consumption['required_qty']:.3f} {consumption['required_uom']}")
                                    
                                    for lot_consumption in consumption["lot_consumptions"]:
                                        st.text(f"  • Lote {lot_consumption['lot_code']}: -{lot_consumption['consumed_qty']:.3f} {lot_consumption['consumed_uom']} (restante: {lot_consumption['remaining_qty']:.3f})")
                        else:
                            st.error(f"❌ **Ordem {po_code}**: Erro na baixa automática!")
                            st.error(f"Erro: {result['error']}")
                            
                            if result.get("issues"):
                                for issue in result["issues"]:
                                    st.warning(f"⚠️ {issue}")
                    
                    st.rerun()
        else:
            st.dataframe(df, hide_index=True, use_container_width=True)

        # Detailed view
        st.markdown("---")
        st.subheader("Detalhes da Ordem de Produção")

        if results:
            selected_po_code = st.selectbox(
                "Selecione uma ordem para ver detalhes:",
                options=[po.code for po, _, _ in results]
            )

            selected_po = next(po for po, _, _ in results if po.code == selected_po_code)
            selected_product = next((product_name, product_code) for po, product_name, product_code in results if po.code == selected_po_code)

            detail_col1, detail_col2, detail_col3 = st.columns(3)

            with detail_col1:
                st.markdown("**Informações Básicas**")
                st.text(f"Código: {selected_po.code}")
                st.text(f"Produto: {selected_product[1]} - {selected_product[0]}")
                st.text(f"Quantidade: {selected_po.qty_to_produce} unidades")
                st.text(f"Status: {selected_po.status}")

            with detail_col2:
                st.markdown("**Cronograma**")
                st.text(f"Data Início: {selected_po.start_date or 'Não definida'}")
                st.text(f"Data Fim: {selected_po.end_date or 'Não definida'}")
                st.text(f"Centro Trabalho: {selected_po.workcenter or 'Não definido'}")

                if selected_po.start_date and selected_po.end_date:
                    duration = (selected_po.end_date - selected_po.start_date).days
                    st.text(f"Duração: {duration} dias")

            with detail_col3:
                st.markdown("**Controle**")
                st.text(f"Lote Planejado: {selected_po.planned_lot or 'Não definido'}")
                st.text(f"Criado Por: {selected_po.created_by or 'N/A'}")
                st.text(f"Data Criação: {selected_po.created_at.strftime('%d/%m/%Y %H:%M') if selected_po.created_at else 'N/A'}")

            # MRP Requirements for this order
            st.markdown("**Necessidades de Matéria-Prima**")

            # Unit toggle for display
            unit_display = st.radio(
                "Unidade de Exibição:",
                ["Gramas", "Quilogramas"],
                horizontal=True,
                key=f"unit_display_{selected_po.id}"
            )

            with get_session() as session:
                requirements = mrp_requirements(session, selected_po.product_id, selected_po.qty_to_produce)

                if requirements:
                    req_data = []
                    for req in requirements:
                        # Convert quantities based on unit selection
                        if unit_display == "Quilogramas":
                            # Convert to kg for display
                            display_unit = "KG"

                            # Convert quantities from original unit to kg
                            def convert_to_kg(qty, original_unit):
                                if original_unit in ["G", "GRAMAS", "GRAMA"]:
                                    return qty / 1000
                                elif original_unit in ["KG"]:
                                    return qty
                                elif original_unit in ["L", "LITRO", "LITROS"]:
                                    # Assuming density ~1 for liquids (water-like)
                                    return qty  # 1L ≈ 1kg
                                elif original_unit in ["ML", "MILILITRO", "MILILITROS"]:
                                    return qty / 1000  # Assuming density ~1
                                else:
                                    return qty  # Keep original for other units

                            required_display = convert_to_kg(req['required_qty'], req['uom'])
                            available_display = convert_to_kg(req['available_qty'], req['uom'])
                            net_requirement_display = convert_to_kg(req['net_requirement'], req['uom'])

                        else:  # Gramas
                            display_unit = "G"

                            # Convert quantities to grams for display
                            def convert_to_g(qty, original_unit):
                                if original_unit in ["G", "GRAMAS", "GRAMA"]:
                                    return qty
                                elif original_unit in ["KG"]:
                                    return qty * 1000
                                elif original_unit in ["L", "LITRO", "LITROS"]:
                                    return qty * 1000  # Assuming density ~1
                                elif original_unit in ["ML", "MILILITRO", "MILILITROS"]:
                                    return qty  # Assuming density ~1
                                else:
                                    return qty  # Keep original for other units

                            required_display = convert_to_g(req['required_qty'], req['uom'])
                            available_display = convert_to_g(req['available_qty'], req['uom'])
                            net_requirement_display = convert_to_g(req['net_requirement'], req['uom'])

                        # Status message
                        status = "✅ OK" if req["net_requirement"] == 0 else f"⚠️ Falta {net_requirement_display:.3f} {display_unit}"

                        req_data.append({
                            "Código MP": req["raw_material_code"],
                            "Matéria-Prima": req["raw_material_name"],
                            "Necessário": f"{required_display:.3f} {display_unit}",
                            "Disponível": f"{available_display:.3f} {display_unit}",
                            "Necessidade Líquida": f"{net_requirement_display:.3f} {display_unit}" if net_requirement_display > 0 else "0",
                            "Status": status
                        })

                    req_df = pd.DataFrame(req_data)
                    st.dataframe(req_df, hide_index=True, use_container_width=True)
                else:
                    st.info("Produto sem formulação aprovada ou sem necessidades calculadas.")

            # Delete production order section (only for operators)
            if has_permission("operator"):
                st.markdown("---")
                st.markdown("### Excluir Ordem de Produção")
                
                # Confirmation protection
                if not st.session_state.get('show_delete_po_confirm'):
                    if st.button("🗑️ Excluir esta Ordem", type="primary", help="Clique para confirmar a exclusão"):
                        st.session_state.show_delete_po_confirm = True
                        st.session_state.po_to_delete_id = selected_po.id
                        st.rerun()
                else:
                    st.warning(f"⚠️ **ATENÇÃO**: Você está prestes a excluir a ordem de produção **{selected_po.code}**")
                    st.error("Esta ação não pode ser desfeita!")
                    
                    delete_col1, delete_col2 = st.columns(2)
                    
                    with delete_col1:
                        if st.button("✅ Confirmar Exclusão", type="primary"):
                            with get_session() as session:
                                po_to_delete = session.get(ProductionOrder, st.session_state.po_to_delete_id)
                                if po_to_delete:
                                    po_code = po_to_delete.code
                                    session.delete(po_to_delete)
                                    session.commit()
                                    st.success(f"Ordem de produção {po_code} excluída com sucesso!")
                                    st.session_state.show_delete_po_confirm = False
                                    st.session_state.po_to_delete_id = None
                                    st.rerun()
                                else:
                                    st.error("Ordem de produção não encontrada.")
                    
                    with delete_col2:
                        if st.button("❌ Cancelar"):
                            st.session_state.show_delete_po_confirm = False
                            st.session_state.po_to_delete_id = None
                            st.rerun()
    else:
        st.info("Nenhuma ordem de produção encontrada.")

with tab2:
    st.subheader("Criar Nova Ordem de Produção")

    if not has_permission("operator"):
        st.error("Você não tem permissão para criar ordens de produção.")
    else:
        with get_session() as session:
            products = session.exec(select(Product).where(Product.status == "ativo")).all()

        if not products:
            st.error("Nenhum produto ativo encontrado. Cadastre produtos primeiro.")
        else:
            with st.form("new_production_order"):
                col1, col2 = st.columns(2)

                with col1:
                    # Auto-generate PO code
                    next_number = 1
                    with get_session() as session:
                        last_po = session.exec(
                            select(ProductionOrder).order_by(ProductionOrder.id.desc())
                        ).first()
                        if last_po and last_po.code.startswith("OP-"):
                            try:
                                last_number = int(last_po.code.split("-")[-1])
                                next_number = last_number + 1
                            except:
                                pass

                    suggested_code = f"OP-{date.today().year}-{next_number:03d}"
                    code = st.text_input("Código da Ordem *", value=suggested_code)

                    # Product selection
                    product_options = [f"{p.code} - {p.name}" for p in products]
                    selected_product_option = st.selectbox("Produto *", product_options)
                    selected_product_id = products[product_options.index(selected_product_option)].id
                    selected_product = products[product_options.index(selected_product_option)]

                    # Production quantity mode selection
                    production_mode = st.radio(
                        "Tipo de Quantidade:",
                        ["Unidades", "Peso (Kg)"],
                        horizontal=True
                    )

                    if production_mode == "Unidades":
                        # Calculate default units per batch
                        if selected_product.unit_weight > 0:
                            default_units = selected_product.std_batch_weight / selected_product.unit_weight
                        else:
                            default_units = 1.0

                        qty_input = st.number_input("Quantidade a Produzir (unidades) *", min_value=0.0,
                                                   value=float(default_units), step=1.0)
                        qty_to_produce = qty_input  # Units
                    else:  # Weight mode
                        # Calculate default weight (standard batch weight in kg)
                        default_weight_kg = selected_product.std_batch_weight / 1000  # Convert grams to kg

                        weight_kg_input = st.number_input("Peso a Produzir (Kg) *", min_value=0.0,
                                                         value=float(default_weight_kg), step=0.1)

                        # Convert weight to units for internal calculations
                        if selected_product.unit_weight > 0:
                            weight_in_grams = weight_kg_input * 1000
                            qty_to_produce = weight_in_grams / selected_product.unit_weight
                        else:
                            qty_to_produce = 1.0

                        # Show calculated units for reference
                        st.info(f"💡 Isso equivale a aproximadamente {qty_to_produce:.0f} unidades do produto")

                with col2:
                    planned_lot = st.text_input("Lote Planejado", placeholder="LOTE-PA-2024-001")
                    start_date = st.date_input("Data de Início", value=date.today())
                    end_date = st.date_input("Data de Fim", value=date.today() + timedelta(days=7))

                # Show MRP analysis
                st.markdown("**Análise de Necessidades (MRP)**")

                # Add submit button for MRP analysis
                mrp_analysis = st.form_submit_button("🔍 Analisar Necessidades", use_container_width=True)

                if qty_to_produce > 0 and mrp_analysis:
                    with get_session() as session:
                        # Get approved formulation for the product
                        formulation = session.exec(
                            select(Formulation)
                            .where(Formulation.product_id == selected_product_id)
                            .where(Formulation.state == "Aprovado/Em Uso")
                        ).first()

                        if formulation:
                            # Get formulation items
                            formula_items = session.exec(
                                select(FormulaItem, RawMaterial.code, RawMaterial.name_usual, RawMaterial.base_unit)
                                .join(RawMaterial, FormulaItem.raw_material_id == RawMaterial.id)
                                .where(FormulaItem.formulation_id == formulation.id)
                            ).all()

                            # Use the improved MRP calculation function
                            requirements = mrp_requirements(session, selected_product_id, qty_to_produce)

                            mrp_data = []
                            all_available = True

                            for req in requirements:
                                available = req["net_requirement"] == 0
                                if not available:
                                    all_available = False

                                mrp_data.append({
                                    "Código": req["raw_material_code"],
                                    "Matéria-Prima": req["raw_material_name"],
                                    "Necessário": f"{req['required_qty']:.3f} {req['uom']}",
                                    "Disponível Estoque": f"{req['available_qty']:.3f} {req['uom']}",
                                    "Necessidade Líquida": f"{req['net_requirement']:.3f} {req['uom']}" if req['net_requirement'] > 0 else "0",
                                    "Status": "✅ OK" if available else f"❌ Falta {req['net_requirement']:.3f} {req['uom']}"
                                })

                            mrp_df = pd.DataFrame(mrp_data)
                            st.dataframe(mrp_df, hide_index=True, use_container_width=True)

                            if not all_available:
                                st.warning("⚠️ Algumas matérias-primas não estão disponíveis em quantidade suficiente.")

                                # Show total missing items
                                missing_items = [row for row in mrp_data if "❌" in row["Status"]]
                                st.error(f"📋 {len(missing_items)} matérias-primas em falta para esta produção.")
                            else:
                                st.success("✅ Todas as matérias-primas estão disponíveis para esta produção.")
                                st.info("🔄 **Baixa Automática**: Quando esta ordem for marcada como 'Concluída', as matérias-primas serão automaticamente consumidas do estoque usando a lógica FEFO (First Expired, First Out).")

                            # Show calculation info
                            if requirements:
                                units_per_batch = requirements[0]["units_per_batch"]
                                proportion = requirements[0]["proportion_factor"]
                                st.info(f"💡 Cálculo baseado em: {qty_to_produce:.0f} unidades ÷ {units_per_batch:.0f} unidades/lote = {proportion:.3f}x a formulação")
                        else:
                            st.info("Produto sem formulação aprovada.")

                submitted = st.form_submit_button("🏭 Criar Ordem de Produção", use_container_width=True)

                if submitted:
                    if not code or qty_to_produce <= 0:
                        st.error("Código e quantidade são obrigatórios.")
                    elif start_date > end_date:
                        st.error("Data de início deve ser anterior à data de fim.")
                    else:
                        try:
                            with get_session() as session:
                                # Check if code already exists
                                existing = session.exec(
                                    select(ProductionOrder).where(ProductionOrder.code == code)
                                ).first()

                                if existing:
                                    st.error("Já existe uma ordem com este código.")
                                else:
                                    new_po = ProductionOrder(
                                        code=code,
                                        product_id=selected_product_id,
                                        qty_to_produce=qty_to_produce,
                                        planned_lot=planned_lot if planned_lot else None,
                                        start_date=start_date,
                                        end_date=end_date,
                                        workcenter=None,
                                        created_by=user["name"]
                                    )

                                    session.add(new_po)
                                    session.commit()

                                    st.success(f"Ordem de produção '{code}' criada com sucesso!")
                                    st.rerun()

                        except Exception as e:
                            st.error(f"Erro ao criar ordem de produção: {str(e)}")

with tab3:
    st.subheader("📊 Planejamento de Produção")

    # Timeline view
    st.markdown("### 📅 Timeline de Produção")

    with get_session() as session:
        active_pos = session.exec(
            select(ProductionOrder, Product.name, Product.code)
            .join(Product, ProductionOrder.product_id == Product.id)
            .where(ProductionOrder.status.in_(["Planejada", "Em Produção"]))
            .where(ProductionOrder.start_date.isnot(None))
        ).all()

        if active_pos:
            timeline_data = []
            for po, product_name, product_code in active_pos:
                timeline_data.append({
                    "Ordem": po.code,
                    "Produto": f"{product_code} - {product_name}",
                    "Início": po.start_date,
                    "Fim": po.end_date or (po.start_date + timedelta(days=7)),
                    "Status": po.status,
                    "Centro": po.workcenter or "Não definido"
                })

            timeline_df = pd.DataFrame(timeline_data)

            # Create Gantt chart
            import plotly.express as px

            fig = px.timeline(
                timeline_df,
                x_start="Início",
                x_end="Fim",
                y="Ordem",
                color="Status",
                title="Timeline de Ordens de Produção",
                hover_data=["Produto", "Centro"]
            )
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhuma ordem ativa com datas definidas.")

    # Capacity analysis
    st.markdown("---")
    st.markdown("### 📈 Análise de Capacidade")

    capacity_col1, capacity_col2 = st.columns(2)

    with capacity_col1:
        st.markdown("**Ordens por Status**")
        with get_session() as session:
            status_counts = {}
            all_pos = session.exec(select(ProductionOrder)).all()

            for po in all_pos:
                status_counts[po.status] = status_counts.get(po.status, 0) + 1

            if status_counts:
                status_df = pd.DataFrame(list(status_counts.items()), columns=["Status", "Quantidade"])

                import plotly.express as px
                fig_status = px.pie(status_df, values="Quantidade", names="Status",
                                  title="Distribuição por Status")
                st.plotly_chart(fig_status, use_container_width=True)
            else:
                st.info("Nenhuma ordem encontrada.")

    with capacity_col2:
        st.markdown("**Produção por Período**")

        # Weekly production view
        if active_pos:
            weekly_data = {}

            for po, product_name, product_code in active_pos:
                if po.start_date:
                    week_key = po.start_date.strftime("%Y-W%W")
                    if week_key not in weekly_data:
                        weekly_data[week_key] = 0
                    weekly_data[week_key] += 1

            if weekly_data:
                weekly_df = pd.DataFrame(list(weekly_data.items()), columns=["Semana", "Ordens"])

                import plotly.express as px
                fig_weekly = px.bar(weekly_df, x="Semana", y="Ordens",
                                  title="Ordens por Semana")
                st.plotly_chart(fig_weekly, use_container_width=True)
            else:
                st.info("Sem dados para análise semanal.")
        else:
            st.info("Nenhuma ordem ativa para análise.")

    # Resource conflicts
    st.markdown("---")
    st.markdown("### ⚠️ Conflitos de Recursos")

    if active_pos:
        # Check for overlapping orders in the same workcenter
        conflicts = []
        for i, (po1, _, _) in enumerate(active_pos):
            for j, (po2, _, _) in enumerate(active_pos[i+1:], i+1):
                if (po1.workcenter and po2.workcenter and
                    po1.workcenter == po2.workcenter and
                    po1.start_date and po1.end_date and
                    po2.start_date and po2.end_date):

                    # Check for overlap
                    if (po1.start_date <= po2.end_date and po2.start_date <= po1.end_date):
                        conflicts.append({
                            "Centro de Trabalho": po1.workcenter,
                            "Ordem 1": po1.code,
                            "Período 1": f"{po1.start_date} - {po1.end_date}",
                            "Ordem 2": po2.code,
                            "Período 2": f"{po2.start_date} - {po2.end_date}"
                        })

        if conflicts:
            st.warning(f"⚠️ {len(conflicts)} conflitos de recursos detectados:")
            conflicts_df = pd.DataFrame(conflicts)
            st.dataframe(conflicts_df, hide_index=True, use_container_width=True)
        else:
            st.success("✅ Nenhum conflito de recursos detectado.")
    else:
        st.info("Nenhuma ordem ativa para verificar conflitos.")