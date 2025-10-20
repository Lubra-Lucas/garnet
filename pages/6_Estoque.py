# pages/6_Estoque.py
import streamlit as st
from auth import require_login, has_permission
from sqlmodel import Session, select, text
from db import engine
from models import StockLot, RawMaterial, Product, Supplier, ProductionOrder
from services.business import fefo_pick, calculate_stock_value, check_expiring_lots, mrp_requirements
import pandas as pd
from datetime import date, timedelta, datetime

# Require login for this page
user = require_login()

st.set_page_config(page_title="GARNET - Estoque", layout="wide")

# Professional page header
st.markdown("""
<div style="padding: 1rem 0 2rem 0; border-bottom: 1px solid #E8E8E8; margin-bottom: 2rem;">
    <h1 style="margin: 0; color: #2E4A6B; font-weight: 300;">Gestão de Estoque</h1>
    <p style="margin: 0.5rem 0 0 0; color: #666; font-size: 1.1rem;">Controle de inventário e movimentação de materiais</p>
</div>
""", unsafe_allow_html=True)

# Clean tabs without icons
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Visão Geral", "Matérias-Primas", "Produtos Acabados", "Alertas", "Histórico de Consumo"])

with tab1:
    st.subheader("Visão Geral do Estoque")

    # Summary metrics
    with Session(engine) as session:
        # Raw materials stock
        rm_stock = calculate_stock_value(session, "MP")
        pa_stock = calculate_stock_value(session, "PA")
        total_stock = rm_stock["total_value"] + pa_stock["total_value"]

        # Count lots - only those that have valid references
        valid_mp_lots = session.exec(
            select(StockLot)
            .join(RawMaterial, StockLot.item_id == RawMaterial.id)
            .where(StockLot.item_type == "MP")
            .where(StockLot.qty > 0)
            .where(RawMaterial.status == "ativo")
        ).all()
        
        valid_pa_lots = session.exec(
            select(StockLot)
            .join(Product, StockLot.item_id == Product.id)
            .where(StockLot.item_type == "PA")
            .where(StockLot.qty > 0)
            .where(Product.status == "ativo")
        ).all()
        
        total_lots = valid_mp_lots + valid_pa_lots
        approved_lots = [lot for lot in total_lots if lot.status == "Aprovado"]

        metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)

        with metrics_col1:
            st.metric("Valor Total do Estoque", f"R$ {total_stock:,.2f}")

        with metrics_col2:
            st.metric("Total de Lotes", len(total_lots))

        with metrics_col3:
            st.metric("Lotes Aprovados", len(approved_lots))

        with metrics_col4:
            pending_lots = len(total_lots) - len(approved_lots)
            st.metric("Pendentes/Quarentena", pending_lots)

    # Stock distribution
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📊 Distribuição por Tipo")
        if total_stock > 0:
            import plotly.express as px

            stock_distribution = pd.DataFrame([
                {"Tipo": "Matérias-Primas", "Valor": rm_stock["total_value"]},
                {"Tipo": "Produtos Acabados", "Valor": pa_stock["total_value"]}
            ])

            fig_pie = px.pie(stock_distribution, values="Valor", names="Tipo", 
                           title="Valor do Estoque por Tipo")
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Sem dados de estoque para exibir.")

    with col2:
        st.markdown("### 📈 Status dos Lotes")
        if total_lots:
            status_count = {}
            for lot in total_lots:
                status_count[lot.status] = status_count.get(lot.status, 0) + 1

            status_df = pd.DataFrame(list(status_count.items()), columns=["Status", "Quantidade"])

            import plotly.express as px
            fig_bar = px.bar(status_df, x="Status", y="Quantidade", 
                           title="Lotes por Status")
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("Nenhum lote encontrado.")

    # Raw materials inventory summary
    st.markdown("---")
    st.subheader("🧪 Lista de Matérias-Primas e Quantidades em Estoque")

    with Session(engine) as session:
        # Get all raw materials with their current stock quantities using proper SQLModel query
        from sqlmodel import text

        rm_stock_query = text("""
        SELECT 
            rm.id,
            rm.code,
            rm.name_usual,
            rm.base_unit,
            rm.base_price,
            COALESCE(SUM(sl.qty), 0) as total_qty,
            s.name as supplier_name
        FROM rawmaterial rm
        LEFT JOIN stocklot sl ON rm.id = sl.item_id AND sl.item_type = 'MP'
        LEFT JOIN supplier s ON rm.supplier_id = s.id
        WHERE rm.status = 'ativo'
        GROUP BY rm.id, rm.code, rm.name_usual, rm.base_unit, rm.base_price, s.name
        ORDER BY rm.code
        """)

        result = session.exec(rm_stock_query).all()

        if result:
            rm_inventory_data = []
            total_stock_value = 0

            for row in result:
                total_qty = row[5]  # total_qty
                base_price = row[4]  # base_price
                supplier_name = row[6]  # supplier_name
                stock_value = total_qty * base_price
                total_stock_value += stock_value

                rm_inventory_data.append({
                    "Código": row[1],  # code
                    "Matéria-Prima": row[2],  # name_usual
                    "Fornecedor": supplier_name or "Não informado",
                    "Unidade": row[3],  # base_unit
                    "Quantidade": f"{total_qty:.1f}",
                    "Preço Unit.": f"R$ {base_price:.2f}",
                    "Valor Total": f"R$ {stock_value:.2f}"
                })

            rm_inventory_df = pd.DataFrame(rm_inventory_data)

            # Summary info
            summary_col1, summary_col2, summary_col3 = st.columns(3)
            with summary_col1:
                st.metric("Total de Matérias-Primas", len(rm_inventory_data))
            with summary_col2:
                active_stock = len([row for row in rm_inventory_data if float(row["Quantidade"]) > 0])
                st.metric("Com Estoque Disponível", active_stock)
            with summary_col3:
                st.metric("Valor Total em Estoque", f"R$ {total_stock_value:,.2f}")

            # Style the dataframe to highlight stock levels
            def highlight_stock(row):
                qty = float(row["Quantidade"])
                if qty == 0:
                    return ['background-color: #ffebee'] * len(row)  # Light red for zero stock
                elif qty < 10:  # Low stock threshold
                    return ['background-color: #fff3e0'] * len(row)  # Light orange for low stock
                elif qty > 100:  # High stock
                    return ['background-color: #e8f5e8'] * len(row)  # Light green for high stock
                else:
                    return [''] * len(row)

            styled_rm_df = rm_inventory_df.style.apply(highlight_stock, axis=1)
            st.dataframe(styled_rm_df, hide_index=True, use_container_width=True)

            # Legend
            st.markdown("**Legenda de Cores:**")
            legend_col1, legend_col2, legend_col3 = st.columns(3)
            with legend_col1:
                st.markdown("🔴 **Vermelho**: Sem estoque")
            with legend_col2:
                st.markdown("🟡 **Laranja**: Estoque baixo (< 10 unidades)")
            with legend_col3:
                st.markdown("🟢 **Verde**: Estoque alto (> 100 unidades)")

        else:
            st.info("Nenhuma matéria-prima cadastrada encontrada.")

    # Recent movements - only valid lots
    st.markdown("---")
    st.subheader("🔄 Movimentações Recentes")

    with Session(engine) as session:
        # Get recent MP lots with valid raw materials
        recent_mp_lots = session.exec(
            select(StockLot, RawMaterial.code, RawMaterial.name_usual)
            .join(RawMaterial, StockLot.item_id == RawMaterial.id)
            .where(StockLot.item_type == "MP")
            .where(RawMaterial.status == "ativo")
            .order_by(StockLot.created_at.desc())
            .limit(5)
        ).all()
        
        # Get recent PA lots with valid products
        recent_pa_lots = session.exec(
            select(StockLot, Product.code, Product.name)
            .join(Product, StockLot.item_id == Product.id)
            .where(StockLot.item_type == "PA")
            .where(Product.status == "ativo")
            .order_by(StockLot.created_at.desc())
            .limit(5)
        ).all()

        if recent_mp_lots or recent_pa_lots:
            movements_data = []
            
            # Process MP lots
            for lot, rm_code, rm_name in recent_mp_lots:
                movements_data.append({
                    "Data": lot.created_at.strftime("%d/%m/%Y %H:%M") if lot.created_at else "N/A",
                    "Tipo": "MP",
                    "Item": f"{rm_code} - {rm_name}",
                    "Lote": lot.lot_code,
                    "Quantidade": f"{lot.qty} {lot.uom}",
                    "Status": lot.status,
                    "Created": lot.created_at or datetime.min
                })
            
            # Process PA lots
            for lot, product_code, product_name in recent_pa_lots:
                movements_data.append({
                    "Data": lot.created_at.strftime("%d/%m/%Y %H:%M") if lot.created_at else "N/A",
                    "Tipo": "PA",
                    "Item": f"{product_code} - {product_name}",
                    "Lote": lot.lot_code,
                    "Quantidade": f"{lot.qty} {lot.uom}",
                    "Status": lot.status,
                    "Created": lot.created_at or datetime.min
                })
            
            # Sort by creation date and limit to 10 most recent
            movements_data.sort(key=lambda x: x["Created"], reverse=True)
            movements_data = movements_data[:10]
            
            # Remove the Created field before displaying
            for movement in movements_data:
                del movement["Created"]

            movements_df = pd.DataFrame(movements_data)
            st.dataframe(movements_df, hide_index=True, use_container_width=True)
        else:
            st.info("Nenhuma movimentação recente encontrada.")

with tab2:
    st.subheader("Estoque de Matérias-Primas")

    # Add stock entry section at the top
    if has_permission("operator"):
        st.markdown("---")
        st.markdown("### ➕ **Dar Entrada no Estoque**")

        # Get active raw materials first
        with Session(engine) as session:
            raw_materials = session.exec(select(RawMaterial).where(RawMaterial.status == "ativo")).all()

        if not raw_materials:
            st.error("⚠️ Nenhuma matéria-prima ativa encontrada. Cadastre matérias-primas primeiro na aba 'Matérias-Primas'.")
        else:
            with st.form("entrada_estoque_form", clear_on_submit=True):
                entrada_col1, entrada_col2, entrada_col3, entrada_col4 = st.columns(4)

                with entrada_col1:
                    rm_options = [f"{rm.code} - {rm.name_usual}" for rm in raw_materials]
                    selected_rm_option = st.selectbox("Matéria-Prima *", rm_options, key="entrada_rm")
                    selected_rm = raw_materials[rm_options.index(selected_rm_option)]

                with entrada_col2:
                    entrada_qty = st.number_input("Quantidade *", min_value=0.01, value=1.0, step=0.01, key="entrada_qty")
                    entrada_uom = st.selectbox("Unidade *", ["KG", "G", "L", "ML", "UN"], 
                                             index=["KG", "G", "L", "ML", "UN"].index(selected_rm.base_unit), key="entrada_uom")

                with entrada_col3:
                    entrada_lote = st.text_input("Código do Lote *", placeholder="LOTE-2024-001", key="entrada_lote")
                    entrada_validade = st.date_input("Data de Validade", value=None, key="entrada_validade")

                with entrada_col4:
                    st.info(f"💰 Custo automático: R$ {selected_rm.base_price:.2f}/{selected_rm.base_unit}")
                    st.caption("Status: Aprovado (automático)")

                entrada_localizacao = st.text_input("Localização", placeholder="Ex: Almoxarifado A - Prateleira 1", key="entrada_local")

                # Submit button - this was missing!
                submitted = st.form_submit_button("💾 **Confirmar Entrada**", use_container_width=True)

                if submitted:
                    if not entrada_lote or entrada_qty <= 0:
                        st.error("Código do lote e quantidade são obrigatórios.")
                    else:
                        with Session(engine) as session:
                            # Check if lot already exists
                            existing_lot = session.exec(
                                select(StockLot).where(
                                    (StockLot.lot_code == entrada_lote) & 
                                    (StockLot.item_id == selected_rm.id) &
                                    (StockLot.item_type == "MP")
                                )
                            ).first()

                            if existing_lot:
                                # Add quantity to existing lot
                                old_qty = existing_lot.qty
                                existing_lot.qty += entrada_qty
                                # Always set status to Aprovado
                                existing_lot.status = "Aprovado"
                                # Update other fields if provided
                                if entrada_validade:
                                    existing_lot.expiry = entrada_validade
                                if entrada_localizacao:
                                    existing_lot.location = entrada_localizacao
                                # Always update cost to current raw material price
                                existing_lot.avg_cost = selected_rm.base_price

                                session.commit()
                                st.success(f"✅ Quantidade adicionada ao lote '{entrada_lote}'! Quantidade anterior: {old_qty} {existing_lot.uom} → Nova quantidade: {existing_lot.qty} {existing_lot.uom}")
                                st.rerun()
                            else:
                                # Create new stock lot
                                new_lot = StockLot(
                                    item_type="MP",
                                    item_id=selected_rm.id,
                                    lot_code=entrada_lote,
                                    qty=entrada_qty,
                                    uom=entrada_uom,
                                    expiry=entrada_validade,
                                    status="Aprovado",  # Always approved
                                    avg_cost=selected_rm.base_price,  # Always use current price from raw material
                                    location=entrada_localizacao if entrada_localizacao else None
                                )

                                session.add(new_lot)
                                session.commit()

                                st.success(f"✅ Entrada registrada com sucesso! Novo lote '{entrada_lote}' - {entrada_qty} {entrada_uom} de {selected_rm.name_usual}")
                                st.rerun()

        st.markdown("---")

    # Filters
    filter_col1, filter_col2, filter_col3 = st.columns(3)

    with filter_col1:
        search_term = st.text_input("🔍 Buscar MP:", placeholder="Código ou nome...")

    with filter_col2:
        status_filter = st.selectbox("Status:", ["Todos", "Aprovado", "Quarentena", "Rejeitado"])

    with filter_col3:
        location_filter = st.text_input("Localização:", placeholder="Filtrar por local...")

    # Get raw materials stock
    with Session(engine) as session:
        query = select(StockLot, RawMaterial.code, RawMaterial.name_usual, Supplier.name).join(
            RawMaterial, StockLot.item_id == RawMaterial.id
        ).outerjoin(
            Supplier, RawMaterial.supplier_id == Supplier.id
        ).where(StockLot.item_type == "MP")

        if search_term:
            query = query.where(
                (RawMaterial.code.ilike(f"%{search_term}%")) |
                (RawMaterial.name_usual.ilike(f"%{search_term}%"))
            )

        if status_filter != "Todos":
            query = query.where(StockLot.status == status_filter)

        if location_filter:
            query = query.where(StockLot.location.ilike(f"%{location_filter}%"))

        results = session.exec(query.order_by(RawMaterial.code)).all()

    if results:
        stock_data = []
        for lot, rm_code, rm_name, supplier_name in results:
            value = lot.qty * (lot.avg_cost or 0)

            stock_data.append({
                "ID": lot.id,
                "Código MP": rm_code,
                "Nome": rm_name,
                "Lote": lot.lot_code,
                "Quantidade": lot.qty,
                "UOM": lot.uom,
                "Validade": lot.expiry.strftime("%d/%m/%Y") if lot.expiry else "N/A",
                "Status": lot.status,
                "Localização": lot.location or "N/A",
                "Custo Médio": f"R$ {lot.avg_cost:.2f}" if lot.avg_cost else "N/A",
                "Valor Total": f"R$ {value:.2f}",
                "Fornecedor": supplier_name or "N/A"
            })

        df = pd.DataFrame(stock_data)

        # Editable table for managers
        if has_permission("operator"):
            edited_df = st.data_editor(
                df,
                hide_index=True,
                use_container_width=True,
                disabled=["ID", "Código MP", "Nome", "Lote", "Fornecedor"],
                column_config={
                    "Status": st.column_config.SelectboxColumn(
                        "Status",
                        options=["Aprovado", "Quarentena", "Rejeitado"],
                        required=True
                    ),
                    "Quantidade": st.column_config.NumberColumn(
                        "Quantidade",
                        min_value=0.0,
                        step=0.1
                    )
                }
            )

            if st.button("💾 Salvar Alterações"):
                with Session(engine) as session:
                    for idx, row in edited_df.iterrows():
                        lot = session.get(StockLot, row["ID"])
                        if lot:
                            lot.qty = row["Quantidade"]
                            lot.status = row["Status"]
                            lot.location = row["Localização"] if row["Localização"] != "N/A" else None

                    session.commit()
                    st.success("Alterações salvas com sucesso!")
                    st.rerun()
        else:
            st.dataframe(df, hide_index=True, use_container_width=True)


    else:
        st.info("Nenhum estoque de matéria-prima encontrado.")

with tab3:
    st.subheader("Estoque de Produtos Acabados")

    # Similar structure for finished products
    with Session(engine) as session:
        pa_query = select(StockLot, Product.code, Product.name).join(
            Product, StockLot.item_id == Product.id
        ).where(StockLot.item_type == "PA")

        pa_results = session.exec(pa_query.order_by(Product.code)).all()

    if pa_results:
        pa_data = []
        for lot, product_code, product_name in pa_results:
            value = lot.qty * (lot.avg_cost or 0)

            pa_data.append({
                "ID": lot.id,
                "Código Produto": product_code,
                "Nome": product_name,
                "Lote": lot.lot_code,
                "Quantidade": lot.qty,
                "UOM": lot.uom,
                "Validade": lot.expiry.strftime("%d/%m/%Y") if lot.expiry else "N/A",
                "Status": lot.status,
                "Localização": lot.location or "N/A",
                "Valor Total": f"R$ {value:.2f}"
            })

        pa_df = pd.DataFrame(pa_data)
        st.dataframe(pa_df, hide_index=True, use_container_width=True)
    else:
        st.info("Nenhum estoque de produto acabado encontrado.")

with tab4:
    st.subheader("⚠️ Alertas de Estoque")

    # Data integrity section
    st.markdown("---")
    st.markdown("### 🔧 Limpeza de Dados")

    if has_permission("manager"):
        # Check for orphaned stock lots (lots that reference deleted materials/products)
        with Session(engine) as session:
            # Check for orphaned MP lots
            orphaned_mp_query = text("""
            SELECT sl.id, sl.lot_code, sl.item_id, sl.qty, sl.uom
            FROM stocklot sl
            WHERE sl.item_type = 'MP' 
            AND NOT EXISTS (
                SELECT 1 FROM rawmaterial rm WHERE rm.id = sl.item_id
            )
            """)

            orphaned_mp_lots = session.exec(orphaned_mp_query).all()

            # Check for orphaned PA lots
            orphaned_pa_query = text("""
            SELECT sl.id, sl.lot_code, sl.item_id, sl.qty, sl.uom
            FROM stocklot sl
            WHERE sl.item_type = 'PA' 
            AND NOT EXISTS (
                SELECT 1 FROM product p WHERE p.id = sl.item_id
            )
            """)

            orphaned_pa_lots = session.exec(orphaned_pa_query).all()

            total_orphaned = len(orphaned_mp_lots) + len(orphaned_pa_lots)

            if total_orphaned > 0:
                st.warning(f"⚠️ Encontrados {total_orphaned} lotes órfãos (referenciando itens excluídos)")

                # Show details
                if orphaned_mp_lots:
                    st.markdown("**Lotes de Matérias-Primas Órfãos:**")
                    mp_orphan_data = []
                    for lot in orphaned_mp_lots:
                        mp_orphan_data.append({
                            "ID Lote": lot[0],
                            "Código Lote": lot[1],
                            "ID Item (Excluído)": lot[2],
                            "Quantidade": f"{lot[3]} {lot[4]}"
                        })
                    st.dataframe(pd.DataFrame(mp_orphan_data), hide_index=True)

                if orphaned_pa_lots:
                    st.markdown("**Lotes de Produtos Órfãos:**")
                    pa_orphan_data = []
                    for lot in orphaned_pa_lots:
                        pa_orphan_data.append({
                            "ID Lote": lot[0],
                            "Código Lote": lot[1],
                            "ID Item (Excluído)": lot[2],
                            "Quantidade": f"{lot[3]} {lot[4]}"
                        })
                    st.dataframe(pd.DataFrame(pa_orphan_data), hide_index=True)

                # Cleanup button
                cleanup_confirm = st.checkbox("Confirmo que desejo remover todos os lotes órfãos")
                
                if cleanup_confirm:
                    if st.button("🗑️ Confirmar Limpeza", type="secondary", help="Remove todos os lotes que referenciam itens excluídos"):
                        try:
                            # Delete orphaned lots
                            for lot in orphaned_mp_lots + orphaned_pa_lots:
                                lot_to_delete = session.get(StockLot, lot[0])
                                if lot_to_delete:
                                    session.delete(lot_to_delete)

                            session.commit()
                            st.success(f"✅ {total_orphaned} lotes órfãos removidos com sucesso!")
                            st.rerun()

                        except Exception as e:
                            st.error(f"Erro ao limpar dados: {str(e)}")
                            session.rollback()
            else:
                st.success("✅ Nenhum lote órfão encontrado. Dados íntegros!")
    else:
        st.info("Função disponível apenas para gerentes.")

    # Expiring lots
    st.markdown("### 📅 Lotes Próximos ao Vencimento")

    days_ahead = st.selectbox("Mostrar lotes que vencem em:", [7, 15, 30, 60], index=1)

    with Session(engine) as session:
        # Get expiring lots but filter to only include lots with active items
        from datetime import timedelta
        cutoff_date = date.today() + timedelta(days=days_ahead)
        
        # Get expiring MP lots with active raw materials only
        expiring_mp_lots = session.exec(
            select(StockLot, RawMaterial.code, RawMaterial.name_usual)
            .join(RawMaterial, StockLot.item_id == RawMaterial.id)
            .where(StockLot.item_type == "MP")
            .where(StockLot.expiry.isnot(None))
            .where(StockLot.expiry <= cutoff_date)
            .where(StockLot.status == "Aprovado")
            .where(StockLot.qty > 0)
            .where(RawMaterial.status == "ativo")  # Only active raw materials
        ).all()
        
        # Get expiring PA lots with active products only
        expiring_pa_lots = session.exec(
            select(StockLot, Product.code, Product.name)
            .join(Product, StockLot.item_id == Product.id)
            .where(StockLot.item_type == "PA")
            .where(StockLot.expiry.isnot(None))
            .where(StockLot.expiry <= cutoff_date)
            .where(StockLot.status == "Aprovado")
            .where(StockLot.qty > 0)
            .where(Product.status == "ativo")  # Only active products
        ).all()

        all_expiring_lots = []
        
        # Process MP lots
        for lot, rm_code, rm_name in expiring_mp_lots:
            days_to_expire = (lot.expiry - date.today()).days if lot.expiry else 0
            all_expiring_lots.append({
                "Tipo": "MP",
                "Item": f"{rm_code} - {rm_name}",
                "Lote": lot.lot_code,
                "Quantidade": f"{lot.qty} {lot.uom}",
                "Validade": lot.expiry.strftime("%d/%m/%Y") if lot.expiry else "N/A",
                "Dias p/ Vencer": days_to_expire,
                "Status": lot.status,
                "Localização": lot.location or "N/A"
            })
        
        # Process PA lots
        for lot, product_code, product_name in expiring_pa_lots:
            days_to_expire = (lot.expiry - date.today()).days if lot.expiry else 0
            all_expiring_lots.append({
                "Tipo": "PA",
                "Item": f"{product_code} - {product_name}",
                "Lote": lot.lot_code,
                "Quantidade": f"{lot.qty} {lot.uom}",
                "Validade": lot.expiry.strftime("%d/%m/%Y") if lot.expiry else "N/A",
                "Dias p/ Vencer": days_to_expire,
                "Status": lot.status,
                "Localização": lot.location or "N/A"
            })

        if all_expiring_lots:

            # Sort by days to expire
            all_expiring_lots.sort(key=lambda x: x["Dias p/ Vencer"])
            expiring_df = pd.DataFrame(all_expiring_lots)

            # Color code by urgency
            def highlight_urgency(row):
                if row["Dias p/ Vencer"] <= 7:
                    return ['background-color: #ffebee'] * len(row)  # Light red
                elif row["Dias p/ Vencer"] <= 15:
                    return ['background-color: #fff3e0'] * len(row)  # Light orange
                else:
                    return [''] * len(row)

            styled_df = expiring_df.style.apply(highlight_urgency, axis=1)
            st.dataframe(styled_df, hide_index=True, use_container_width=True)
        else:
            st.success(f"✅ Nenhum lote vence nos próximos {days_ahead} dias.")

    # Low stock alerts (placeholder)
    st.markdown("---")
    st.markdown("### 📉 Alertas de Estoque Baixo")
    st.info("Funcionalidade de estoque mínimo será implementada com dados históricos de consumo.")

    # Quality alerts
    st.markdown("---")
    st.markdown("### 🔬 Alertas de Qualidade")

    with Session(engine) as session:
        # Get quarantine MP lots with active raw materials only
        quarantine_mp_lots = session.exec(
            select(StockLot, RawMaterial.code, RawMaterial.name_usual)
            .join(RawMaterial, StockLot.item_id == RawMaterial.id)
            .where(StockLot.item_type == "MP")
            .where(StockLot.status == "Quarentena")
            .where(RawMaterial.status == "ativo")
        ).all()
        
        # Get quarantine PA lots with active products only
        quarantine_pa_lots = session.exec(
            select(StockLot, Product.code, Product.name)
            .join(Product, StockLot.item_id == Product.id)
            .where(StockLot.item_type == "PA")
            .where(StockLot.status == "Quarentena")
            .where(Product.status == "ativo")
        ).all()
        
        total_quarantine = len(quarantine_mp_lots) + len(quarantine_pa_lots)

        if total_quarantine > 0:
            st.warning(f"⚠️ {total_quarantine} lotes em quarentena aguardando análise:")

            quarantine_data = []
            
            # Process MP lots
            for lot, rm_code, rm_name in quarantine_mp_lots:
                quarantine_data.append({
                    "Tipo": "MP",
                    "Item": f"{rm_code} - {rm_name}",
                    "Lote": lot.lot_code,
                    "Quantidade": f"{lot.qty} {lot.uom}",
                    "Data Recebimento": lot.received_date.strftime("%d/%m/%Y") if lot.received_date else "N/A"
                })
            
            # Process PA lots
            for lot, product_code, product_name in quarantine_pa_lots:
                quarantine_data.append({
                    "Tipo": "PA",
                    "Item": f"{product_code} - {product_name}",
                    "Lote": lot.lot_code,
                    "Quantidade": f"{lot.qty} {lot.uom}",
                    "Data Recebimento": lot.received_date.strftime("%d/%m/%Y") if lot.received_date else "N/A"
                })

            quarantine_df = pd.DataFrame(quarantine_data)
            st.dataframe(quarantine_df, hide_index=True, use_container_width=True)
        else:
            st.success("✅ Nenhum lote em quarentena.")

with tab5:
    st.subheader("📜 Histórico de Consumo Automático")
    st.info("💡 Este histórico mostra as baixas automáticas de matéria-prima quando ordens de produção são concluídas.")

    # Filter by date range
    col_filter1, col_filter2 = st.columns(2)
    
    with col_filter1:
        date_from = st.date_input("Data Inicial:", value=date.today() - timedelta(days=30))
    
    with col_filter2:
        date_to = st.date_input("Data Final:", value=date.today())

    # Since we don't have a dedicated consumption tracking table yet,
    # we'll show completed production orders as a proxy for consumption events
    with Session(engine) as session:
        completed_pos = session.exec(
            select(ProductionOrder, Product.code, Product.name)
            .join(Product, ProductionOrder.product_id == Product.id)
            .where(ProductionOrder.status == "Concluída")
            .where(ProductionOrder.end_date >= date_from)
            .where(ProductionOrder.end_date <= date_to)
            .order_by(ProductionOrder.end_date.desc())
        ).all()

        if completed_pos:
            st.markdown(f"### 📊 Ordens Concluídas no Período ({len(completed_pos)} registros)")

            consumption_history = []
            for po, product_code, product_name in completed_pos:
                # Calculate what would have been consumed using MRP
                requirements = mrp_requirements(session, po.product_id, po.qty_to_produce)
                
                total_materials = len(requirements)
                
                # Calcular custo apenas para managers
                if has_permission("manager"):
                    estimated_cost = 0.0
                    for req in requirements:
                        rm = session.get(RawMaterial, req["raw_material_id"])
                        if rm:
                            from services.business import material_cost_unit
                            estimated_cost += material_cost_unit(rm, req["required_qty"], req["uom"])
                    
                    consumption_history.append({
                        "Data": po.end_date.strftime("%d/%m/%Y") if po.end_date else "N/A",
                        "Ordem de Produção": po.code,
                        "Produto": f"{product_code} - {product_name}",
                        "Quantidade Produzida": f"{po.qty_to_produce:.0f} unidades",
                        "Matérias-Primas": f"{total_materials} itens",
                        "Custo Estimado": f"R$ {estimated_cost:.2f}",
                        "Lote": po.planned_lot or "N/A"
                    })
                else:
                    consumption_history.append({
                        "Data": po.end_date.strftime("%d/%m/%Y") if po.end_date else "N/A",
                        "Ordem de Produção": po.code,
                        "Produto": f"{product_code} - {product_name}",
                        "Quantidade Produzida": f"{po.qty_to_produce:.0f} unidades",
                        "Matérias-Primas": f"{total_materials} itens",
                        "Lote": po.planned_lot or "N/A"
                    })

            history_df = pd.DataFrame(consumption_history)
            st.dataframe(history_df, hide_index=True, use_container_width=True)

            # Summary
            total_units = sum(float(row["Quantidade Produzida"].split(" ")[0]) for row in consumption_history)

            if has_permission("manager"):
                total_cost = sum(float(row["Custo Estimado"].replace("R$ ", "").replace(",", "")) for row in consumption_history)
                summary_col1, summary_col2, summary_col3 = st.columns(3)
                
                with summary_col1:
                    st.metric("Total de Ordens", len(completed_pos))
                
                with summary_col2:
                    st.metric("Unidades Produzidas", f"{total_units:.0f}")
                
                with summary_col3:
                    st.metric("Custo Total Estimado", f"R$ {total_cost:,.2f}")
            else:
                summary_col1, summary_col2 = st.columns(2)
                
                with summary_col1:
                    st.metric("Total de Ordens", len(completed_pos))
                
                with summary_col2:
                    st.metric("Unidades Produzidas", f"{total_units:.0f}")

            # Detail view for selected order
            st.markdown("---")
            st.subheader("🔍 Detalhamento por Ordem")
            
            if consumption_history:
                selected_po_code = st.selectbox(
                    "Selecione uma ordem para ver o detalhamento:",
                    options=[row["Ordem de Produção"] for row in consumption_history]
                )

                selected_po = next(po for po, _, _ in completed_pos if po.code == selected_po_code)
                
                # Calculate and show detailed MRP for this order
                detailed_requirements = mrp_requirements(session, selected_po.product_id, selected_po.qty_to_produce)
                
                if detailed_requirements:
                    st.markdown(f"**Consumo estimado para ordem {selected_po_code}:**")
                    
                    detail_data = []
                    for req in detailed_requirements:
                        rm = session.get(RawMaterial, req["raw_material_id"])
                        
                        if has_permission("manager"):
                            cost = 0.0
                            if rm:
                                from services.business import material_cost_unit
                                cost = material_cost_unit(rm, req["required_qty"], req["uom"])

                            detail_data.append({
                                "Código MP": req["raw_material_code"],
                                "Matéria-Prima": req["raw_material_name"],
                                "Quantidade": f"{req['required_qty']:.3f} {req['uom']}",
                                "Custo Unitário": f"R$ {rm.base_price:.2f}/{rm.base_unit}" if rm else "N/A",
                                "Custo Total": f"R$ {cost:.2f}"
                            })
                        else:
                            detail_data.append({
                                "Código MP": req["raw_material_code"],
                                "Matéria-Prima": req["raw_material_name"],
                                "Quantidade": f"{req['required_qty']:.3f} {req['uom']}"
                            })

                    detail_df = pd.DataFrame(detail_data)
                    st.dataframe(detail_df, hide_index=True, use_container_width=True)
                else:
                    st.info("Sem formulação aprovada para este produto.")
        else:
            st.info(f"Nenhuma ordem concluída encontrada entre {date_from.strftime('%d/%m/%Y')} e {date_to.strftime('%d/%m/%Y')}.")

        # Export functionality
        if completed_pos:
            st.markdown("---")
            if st.button("📊 Exportar Histórico"):
                # Create export data
                export_data = []
                for po, product_code, product_name in completed_pos:
                    requirements = mrp_requirements(session, po.product_id, po.qty_to_produce)
                    
                    for req in requirements:
                        rm = session.get(RawMaterial, req["raw_material_id"])
                        
                        if has_permission("manager"):
                            cost = 0.0
                            if rm:
                                from services.business import material_cost_unit
                                cost = material_cost_unit(rm, req["required_qty"], req["uom"])

                            export_data.append({
                                "Data": po.end_date.strftime("%d/%m/%Y") if po.end_date else "",
                                "Ordem_Producao": po.code,
                                "Produto_Codigo": product_code,
                                "Produto_Nome": product_name,
                                "Quantidade_Produzida": po.qty_to_produce,
                                "MP_Codigo": req["raw_material_code"],
                                "MP_Nome": req["raw_material_name"],
                                "Quantidade_Consumida": req["required_qty"],
                                "Unidade": req["uom"],
                                "Custo_Unitario": rm.base_price if rm else 0,
                                "Custo_Total": cost,
                                "Lote_Planejado": po.planned_lot or ""
                            })
                        else:
                            export_data.append({
                                "Data": po.end_date.strftime("%d/%m/%Y") if po.end_date else "",
                                "Ordem_Producao": po.code,
                                "Produto_Codigo": product_code,
                                "Produto_Nome": product_name,
                                "Quantidade_Produzida": po.qty_to_produce,
                                "MP_Codigo": req["raw_material_code"],
                                "MP_Nome": req["raw_material_name"],
                                "Quantidade_Consumida": req["required_qty"],
                                "Unidade": req["uom"],
                                "Lote_Planejado": po.planned_lot or ""
                            })

                if export_data:
                    export_df = pd.DataFrame(export_data)
                    
                    # Create Excel file
                    from io import BytesIO
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        export_df.to_excel(writer, sheet_name='Historico_Consumo', index=False)
                    
                    st.download_button(
                        label="📥 Download Excel",
                        data=output.getvalue(),
                        file_name=f"historico_consumo_{date_from.strftime('%Y%m%d')}_{date_to.strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )