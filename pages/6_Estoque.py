# pages/6_Estoque.py
import streamlit as st
from auth import require_login, has_permission
from sqlmodel import Session, select, text
from db import engine
from models import StockLot, RawMaterial, Product, Supplier, ProductionOrder, StockMovement
from services.business import fefo_pick, calculate_stock_value, check_expiring_lots, mrp_requirements
import pandas as pd
from datetime import date, timedelta, datetime
import json

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
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Visão Geral", "Matérias-Primas", "Produtos Acabados", "Alertas", "Histórico de Consumo", "Histórico de Movimentação"])

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



with tab2:
    st.subheader("Estoque de Matérias-Primas")

    # Add manual stock withdrawal section
    if has_permission("operator"):
        st.markdown("---")
        st.markdown("### ➖ **Dar Baixa Manual no Estoque**")
        st.info("💡 Use esta funcionalidade para registrar consumos, perdas, ajustes ou saídas de estoque que não sejam por ordem de produção.")

        with st.form("baixa_estoque_form", clear_on_submit=True):
            baixa_col1, baixa_col2, baixa_col3 = st.columns(3)

            with baixa_col1:
                # Get all stock lots with available quantity
                with Session(engine) as session:
                    available_lots = session.exec(
                        select(StockLot, RawMaterial.code, RawMaterial.name_usual)
                        .join(RawMaterial, StockLot.item_id == RawMaterial.id)
                        .where(StockLot.item_type == "MP")
                        .where(StockLot.qty > 0)
                        .where(StockLot.status == "Aprovado")
                        .where(RawMaterial.status == "ativo")
                        .order_by(RawMaterial.code)
                    ).all()

                if not available_lots:
                    st.warning("⚠️ Nenhum lote disponível para baixa.")
                else:
                    lot_options = [f"{rm_code} - {rm_name} | Lote: {lot.lot_code} | Disponível: {lot.qty:.2f} {lot.uom}" 
                                   for lot, rm_code, rm_name in available_lots]
                    selected_lot_option = st.selectbox("Selecionar Lote *", lot_options, key="baixa_lot")
                    selected_lot_index = lot_options.index(selected_lot_option)
                    selected_lot_data = available_lots[selected_lot_index]

            with baixa_col2:
                if available_lots:
                    max_qty = selected_lot_data[0].qty
                    baixa_qty = st.number_input(
                        f"Quantidade a Dar Baixa (máx: {max_qty:.2f}) *", 
                        min_value=0.01, 
                        max_value=float(max_qty),
                        value=min(1.0, float(max_qty)), 
                        step=0.01, 
                        key="baixa_qty"
                    )
                    st.caption(f"Unidade: {selected_lot_data[0].uom}")

            with baixa_col3:
                if available_lots:
                    baixa_motivo = st.selectbox(
                        "Motivo da Baixa *",
                        ["Consumo Interno", "Perda/Quebra", "Ajuste de Inventário", "Transferência", "Vencimento", "Outros"],
                        key="baixa_motivo"
                    )

            if available_lots:
                baixa_observacoes = st.text_area(
                    "Observações",
                    placeholder="Descreva o motivo da baixa em detalhes...",
                    key="baixa_obs"
                )

                submitted_baixa = st.form_submit_button("🗑️ **Confirmar Baixa**", use_container_width=True, type="primary")

                if submitted_baixa:
                    if baixa_qty <= 0:
                        st.error("A quantidade deve ser maior que zero.")
                    else:
                        with Session(engine) as session:
                            lot_to_update = session.get(StockLot, selected_lot_data[0].id)

                            if lot_to_update and lot_to_update.qty >= baixa_qty:
                                old_qty = lot_to_update.qty
                                lot_to_update.qty -= baixa_qty

                                session.commit()

                                # Register movement
                                movement = StockMovement(
                                    movement_type="Saída",
                                    item_type="MP",
                                    item_id=selected_lot_data[2].id if hasattr(selected_lot_data[2], 'id') else lot_to_update.item_id,
                                    item_code=selected_lot_data[1],
                                    item_name=selected_lot_data[2],
                                    lot_code=lot_to_update.lot_code,
                                    qty=baixa_qty,
                                    uom=lot_to_update.uom,
                                    reason=baixa_motivo,
                                    notes=baixa_observacoes if baixa_observacoes else None,
                                    user=st.session_state.get("user", {}).get("name", "Sistema")
                                )
                                session.add(movement)
                                session.commit()

                                # Success message with details
                                st.success(f"✅ Baixa registrada com sucesso!")
                                st.info(f"""
                                **Detalhes da Baixa:**
                                - **Material:** {selected_lot_data[1]} - {selected_lot_data[2]}
                                - **Lote:** {lot_to_update.lot_code}
                                - **Quantidade Baixada:** {baixa_qty:.2f} {lot_to_update.uom}
                                - **Quantidade Anterior:** {old_qty:.2f} {lot_to_update.uom}
                                - **Quantidade Atual:** {lot_to_update.qty:.2f} {lot_to_update.uom}
                                - **Motivo:** {baixa_motivo}
                                {f"- **Observações:** {baixa_observacoes}" if baixa_observacoes else ""}
                                """)
                                st.rerun()
                            else:
                                st.error("Erro: Quantidade indisponível ou lote não encontrado.")

        st.markdown("---")

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
                
                # Add file uploader for certifications
                st.markdown("### 📄 Certificações (PDF)")
                st.caption("Anexe os arquivos PDF das certificações. Limite de 10 arquivos.")
                certificacoes_files = st.file_uploader(
                    "Selecione os arquivos PDF", 
                    type="pdf", 
                    accept_multiple_files=True, 
                    key="certificacoes_uploader",
                    help="Anexe até 10 arquivos PDF. Arquivos grandes podem demorar para carregar."
                )
                
                if certificacoes_files and len(certificacoes_files) > 10:
                    st.error("Limite de 10 arquivos excedido. Por favor, selecione no máximo 10 arquivos.")
                    certificacoes_files = certificacoes_files[:10]

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

                                # Handle certifications
                                if certificacoes_files:
                                    import os
                                    from datetime import datetime
                                    
                                    # Create upload directory
                                    upload_dir = "uploads/certifications_stock_lots"
                                    os.makedirs(upload_dir, exist_ok=True)
                                    
                                    # Load existing certifications
                                    if existing_lot.certification_file_path:
                                        try:
                                            current_certs = json.loads(existing_lot.certification_file_path)
                                            if not isinstance(current_certs, list):
                                                current_certs = [current_certs]
                                        except:
                                            current_certs = []
                                    else:
                                        current_certs = []
                                    
                                    # Save new certification files
                                    new_cert_paths = []
                                    for idx, uploaded_file in enumerate(certificacoes_files):
                                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                        safe_lote = entrada_lote.replace("/", "_").replace("\\", "_")
                                        file_name = f"{safe_lote}_cert_{timestamp}_{idx+1}.pdf"
                                        file_path = os.path.join(upload_dir, file_name)
                                        
                                        with open(file_path, "wb") as f:
                                            f.write(uploaded_file.getbuffer())
                                        
                                        new_cert_paths.append(file_path)
                                    
                                    # Combine and limit to 10
                                    combined_certs = current_certs + new_cert_paths
                                    if len(combined_certs) > 10:
                                        st.warning("Limite de 10 certificações atingido. As certificações mais antigas foram removidas.")
                                        # Remove old files
                                        for old_path in combined_certs[:-10]:
                                            if os.path.exists(old_path):
                                                try:
                                                    os.remove(old_path)
                                                except:
                                                    pass
                                        combined_certs = combined_certs[-10:]
                                        
                                    existing_lot.certification_file_path = json.dumps(combined_certs)

                                session.commit()

                                # Register movement
                                movement = StockMovement(
                                    movement_type="Entrada",
                                    item_type="MP",
                                    item_id=selected_rm.id,
                                    item_code=selected_rm.code,
                                    item_name=selected_rm.name_usual,
                                    lot_code=entrada_lote,
                                    qty=entrada_qty,
                                    uom=entrada_uom,
                                    reason="Entrada Manual",
                                    notes=f"Adicionado ao lote existente. Quantidade anterior: {old_qty}",
                                    user=st.session_state.get("user", {}).get("name", "Sistema")
                                )
                                session.add(movement)
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
                                
                                # Handle certifications for new lot
                                if certificacoes_files:
                                    import os
                                    from datetime import datetime
                                    
                                    # Create upload directory
                                    upload_dir = "uploads/certifications_stock_lots"
                                    os.makedirs(upload_dir, exist_ok=True)
                                    
                                    # Save certification files
                                    cert_paths = []
                                    for idx, uploaded_file in enumerate(certificacoes_files[:10]):
                                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                        safe_lote = entrada_lote.replace("/", "_").replace("\\", "_")
                                        file_name = f"{safe_lote}_cert_{timestamp}_{idx+1}.pdf"
                                        file_path = os.path.join(upload_dir, file_name)
                                        
                                        with open(file_path, "wb") as f:
                                            f.write(uploaded_file.getbuffer())
                                        
                                        cert_paths.append(file_path)
                                    
                                    new_lot.certification_file_path = json.dumps(cert_paths)

                                session.add(new_lot)
                                session.commit()

                                # Register movement
                                movement = StockMovement(
                                    movement_type="Entrada",
                                    item_type="MP",
                                    item_id=selected_rm.id,
                                    item_code=selected_rm.code,
                                    item_name=selected_rm.name_usual,
                                    lot_code=entrada_lote,
                                    qty=entrada_qty,
                                    uom=entrada_uom,
                                    reason="Entrada Manual",
                                    notes=f"Localização: {entrada_localizacao}" if entrada_localizacao else None,
                                    user=st.session_state.get("user", {}).get("name", "Sistema")
                                )
                                session.add(movement)
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

                # Check for certifications
                cert_count = 0
                if lot.certification_file_path:
                    try:
                        import json
                        cert_paths = json.loads(lot.certification_file_path)
                        if isinstance(cert_paths, list):
                            cert_count = len(cert_paths)
                        else:
                            cert_count = 1
                    except:
                        cert_count = 1

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
                    "Fornecedor": supplier_name or "N/A",
                    "Certificações": f"📄 {cert_count}" if cert_count > 0 else "-"
                })

            df = pd.DataFrame(stock_data)

            # Editable table for managers
            if has_permission("operator"):
                edited_df = st.data_editor(
                    df,
                    hide_index=True,
                    use_container_width=True,
                    disabled=["ID", "Código MP", "Nome", "Lote", "Fornecedor", "Certificações"],
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
            
            # View certifications section
            st.markdown("---")
            st.markdown("### 📄 Visualizar Certificações do Lote")
            
            # Select lot to view certifications
            lot_options = [f"{row['Código MP']} - {row['Nome']} | Lote: {row['Lote']}" for idx, row in df.iterrows()]
            
            if lot_options:
                selected_lot_option = st.selectbox(
                    "Selecione um lote para ver as certificações:",
                    lot_options,
                    key="view_cert_lot"
                )
                
                if selected_lot_option:
                    selected_idx = lot_options.index(selected_lot_option)
                    selected_lot_id = int(df.iloc[selected_idx]["ID"])  # Convert numpy.int64 to Python int
                    
                    with Session(engine) as session:
                        lot = session.get(StockLot, selected_lot_id)
                        
                        if lot and lot.certification_file_path:
                            try:
                                import os
                                cert_paths = json.loads(lot.certification_file_path)
                                
                                if isinstance(cert_paths, list):
                                    st.success(f"✅ {len(cert_paths)} certificação(ões) encontrada(s)")
                                    
                                    # Display download buttons in columns
                                    cert_cols = st.columns(min(len(cert_paths), 5))
                                    for idx, cert_path in enumerate(cert_paths):
                                        col_idx = idx % 5
                                        with cert_cols[col_idx]:
                                            if os.path.exists(cert_path):
                                                with open(cert_path, "rb") as file:
                                                    st.download_button(
                                                        label=f"📄 Cert {idx+1}",
                                                        data=file.read(),
                                                        file_name=f"certificacao_{lot.lot_code}_{idx+1}.pdf",
                                                        mime="application/pdf",
                                                        key=f"download_stock_cert_{lot.id}_{idx}",
                                                        use_container_width=True
                                                    )
                                            else:
                                                st.error(f"Arquivo {idx+1} não encontrado")
                                else:
                                    # Old format - single file
                                    if os.path.exists(cert_paths):
                                        with open(cert_paths, "rb") as file:
                                            st.download_button(
                                                label="📄 Baixar Certificação",
                                                data=file.read(),
                                                file_name=f"certificacao_{lot.lot_code}.pdf",
                                                mime="application/pdf",
                                                use_container_width=True
                                            )
                                    else:
                                        st.error("Arquivo não encontrado")
                            except json.JSONDecodeError:
                                # Old format - single file path string
                                if os.path.exists(lot.certification_file_path):
                                    with open(lot.certification_file_path, "rb") as file:
                                        st.download_button(
                                            label="📄 Baixar Certificação",
                                            data=file.read(),
                                            file_name=f"certificacao_{lot.lot_code}.pdf",
                                            mime="application/pdf",
                                            use_container_width=True
                                        )
                                else:
                                    st.error("Arquivo não encontrado")
                        else:
                            st.info("Este lote não possui certificações anexadas.")

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

with tab6:
    st.subheader("📜 Histórico de Movimentação")
    st.info("💡 Este histórico registra todas as entradas e saídas de estoque, incluindo movimentações manuais e automáticas.")

    # Filters
    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)

    with filter_col1:
        movement_date_from = st.date_input("Data Inicial:", value=date.today() - timedelta(days=30), key="mov_date_from")

    with filter_col2:
        movement_date_to = st.date_input("Data Final:", value=date.today(), key="mov_date_to")

    with filter_col3:
        movement_type_filter = st.selectbox("Tipo de Movimentação:", ["Todos", "Entrada", "Saída"], key="mov_type")

    with filter_col4:
        item_type_filter = st.selectbox("Tipo de Item:", ["Todos", "MP", "PA"], key="item_type")

    # Search filter
    search_filter = st.text_input("🔍 Buscar por código, nome ou lote:", placeholder="Digite para filtrar...", key="mov_search")

    # Get movements from database
    with Session(engine) as session:
        query = select(StockMovement).where(
            StockMovement.movement_date >= datetime.combine(movement_date_from, datetime.min.time())
        ).where(
            StockMovement.movement_date <= datetime.combine(movement_date_to, datetime.max.time())
        )

        if movement_type_filter != "Todos":
            query = query.where(StockMovement.movement_type == movement_type_filter)

        if item_type_filter != "Todos":
            query = query.where(StockMovement.item_type == item_type_filter)

        if search_filter:
            query = query.where(
                (StockMovement.item_code.ilike(f"%{search_filter}%")) |
                (StockMovement.item_name.ilike(f"%{search_filter}%")) |
                (StockMovement.lot_code.ilike(f"%{search_filter}%"))
            )

        movements = session.exec(query.order_by(StockMovement.movement_date.desc())).all()

        if movements:
            st.markdown(f"### 📊 Movimentações Encontradas ({len(movements)} registros)")

            movement_history = []
            for mov in movements:
                movement_history.append({
                    "ID": mov.id,
                    "Data": mov.movement_date.strftime("%d/%m/%Y"),
                    "Hora": mov.movement_date.strftime("%H:%M:%S"),
                    "Tipo": mov.movement_type,
                    "Item Tipo": mov.item_type,
                    "Código": mov.item_code,
                    "Nome": mov.item_name,
                    "Lote": mov.lot_code,
                    "Quantidade": f"{mov.qty:.2f} {mov.uom}",
                    "Motivo": mov.reason,
                    "Observações": mov.notes or "-",
                    "Usuário": mov.user or "Sistema"
                })

            history_df = pd.DataFrame(movement_history)

            # Color code by movement type
            def highlight_movement_type(row):
                if row["Tipo"] == "Entrada":
                    return ['background-color: #e8f5e9'] * len(row)  # Light green
                elif row["Tipo"] == "Saída":
                    return ['background-color: #ffebee'] * len(row)  # Light red
                else:
                    return [''] * len(row)

            # Display dataframe without ID column for regular users
            display_columns = [col for col in history_df.columns if col != "ID"]
            styled_df = history_df[display_columns].style.apply(highlight_movement_type, axis=1)
            st.dataframe(styled_df, hide_index=True, use_container_width=True)

            # Delete functionality for managers only
            if has_permission("manager"):
                st.markdown("---")
                st.markdown("### 🗑️ Excluir Movimentação (Apenas Gerentes)")
                st.warning("⚠️ **ATENÇÃO**: Excluir uma movimentação irá reverter o estoque automaticamente!")

                with st.form("delete_movement_form"):
                    col_del1, col_del2 = st.columns([3, 1])

                    with col_del1:
                        # Create selection options with movement details
                        movement_options = []
                        for mov in movements:
                            option_text = f"{mov.movement_date.strftime('%d/%m/%Y %H:%M')} | {mov.movement_type} | {mov.item_code} - {mov.item_name} | Lote: {mov.lot_code} | {mov.qty:.2f} {mov.uom}"
                            movement_options.append(option_text)

                        selected_movement_option = st.selectbox(
                            "Selecione a movimentação para excluir:",
                            movement_options,
                            key="delete_movement_select"
                        )

                        if selected_movement_option:
                            selected_index = movement_options.index(selected_movement_option)
                            selected_movement = movements[selected_index]

                            # Show impact of deletion
                            if selected_movement.movement_type == "Entrada":
                                st.info(f"💡 **Impacto**: O estoque do lote '{selected_movement.lot_code}' será **REDUZIDO** em {selected_movement.qty:.2f} {selected_movement.uom}")
                            else:  # Saída
                                st.info(f"💡 **Impacto**: O estoque do lote '{selected_movement.lot_code}' será **AUMENTADO** em {selected_movement.qty:.2f} {selected_movement.uom}")

                    with col_del2:
                        st.write("")  # Spacer
                        st.write("")  # Spacer

                    delete_reason = st.text_area(
                        "Motivo da Exclusão (obrigatório):",
                        placeholder="Explique por que esta movimentação está sendo excluída...",
                        key="delete_movement_reason"
                    )

                    confirm_delete = st.checkbox("Confirmo que desejo excluir esta movimentação", key="confirm_delete_movement")

                    submitted_delete = st.form_submit_button("🗑️ Confirmar Exclusão", use_container_width=True, type="secondary")

                    if submitted_delete:
                        if not confirm_delete:
                            st.error("Você precisa confirmar a exclusão marcando a caixa acima.")
                        elif not delete_reason or len(delete_reason.strip()) < 10:
                            st.error("Por favor, forneça um motivo detalhado para a exclusão (mínimo 10 caracteres).")
                        else:
                            try:
                                with Session(engine) as session:
                                    # Get the movement to delete
                                    movement_to_delete = session.get(StockMovement, selected_movement.id)

                                    if not movement_to_delete:
                                        st.error("Movimentação não encontrada.")
                                    else:
                                        # Find the corresponding lot
                                        lot = session.exec(
                                            select(StockLot).where(
                                                (StockLot.lot_code == movement_to_delete.lot_code) &
                                                (StockLot.item_type == movement_to_delete.item_type) &
                                                (StockLot.item_id == movement_to_delete.item_id)
                                            )
                                        ).first()

                                        if lot:
                                            # Reverse the stock movement
                                            if movement_to_delete.movement_type == "Entrada":
                                                # Entrada being deleted = subtract from stock
                                                lot.qty -= movement_to_delete.qty
                                                action_description = f"reduzido em {movement_to_delete.qty:.2f} {movement_to_delete.uom}"
                                            else:  # Saída
                                                # Saída being deleted = add back to stock
                                                lot.qty += movement_to_delete.qty
                                                action_description = f"aumentado em {movement_to_delete.qty:.2f} {movement_to_delete.uom}"

                                            # Prevent negative stock
                                            if lot.qty < 0:
                                                st.error(f"Erro: A exclusão desta movimentação resultaria em estoque negativo ({lot.qty:.2f} {lot.uom}). Operação cancelada.")
                                            else:
                                                # Create a compensating movement record for audit trail
                                                compensating_movement = StockMovement(
                                                    movement_type="Saída" if movement_to_delete.movement_type == "Entrada" else "Entrada",
                                                    item_type=movement_to_delete.item_type,
                                                    item_id=movement_to_delete.item_id,
                                                    item_code=movement_to_delete.item_code,
                                                    item_name=movement_to_delete.item_name,
                                                    lot_code=movement_to_delete.lot_code,
                                                    qty=movement_to_delete.qty,
                                                    uom=movement_to_delete.uom,
                                                    reason="Reversão por Exclusão de Movimentação",
                                                    notes=f"Reversão da movimentação ID {movement_to_delete.id} ({movement_to_delete.movement_type}). Motivo: {delete_reason}",
                                                    user=st.session_state.get("user", {}).get("name", "Sistema")
                                                )
                                                session.add(compensating_movement)

                                                # Delete the original movement
                                                session.delete(movement_to_delete)

                                                session.commit()

                                                st.success(f"""
                                                ✅ **Movimentação excluída com sucesso!**

                                                **Detalhes da Reversão:**
                                                - **Lote:** {lot.lot_code}
                                                - **Estoque {action_description}**
                                                - **Quantidade atual do lote:** {lot.qty:.2f} {lot.uom}
                                                - **Registro de auditoria criado para rastreabilidade**
                                                """)
                                                st.rerun()
                                        else:
                                            # Lot not found - still delete the orphaned movement
                                            st.warning(f"⚠️ Lote '{movement_to_delete.lot_code}' não encontrado. A movimentação será excluída sem ajuste de estoque.")

                                            session.delete(movement_to_delete)
                                            session.commit()

                                            st.success("✅ Movimentação órfã excluída com sucesso!")
                                            st.rerun()

                            except Exception as e:
                                st.error(f"Erro ao excluir movimentação: {str(e)}")
                                session.rollback()

            # Summary metrics
            st.markdown("---")
            st.markdown("### 📈 Resumo do Período")

            summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)

            total_entries = sum(1 for mov in movements if mov.movement_type == "Entrada")
            total_withdrawals = sum(1 for mov in movements if mov.movement_type == "Saída")

            with summary_col1:
                st.metric("Total de Movimentações", len(movements))

            with summary_col2:
                st.metric("Entradas", total_entries)

            with summary_col3:
                st.metric("Saídas", total_withdrawals)

            with summary_col4:
                balance = total_entries - total_withdrawals
                st.metric("Saldo de Movimentações", balance, delta=balance)

            # Export functionality
            st.markdown("---")
            if st.button("📊 Exportar Histórico de Movimentação", use_container_width=True):
                from io import BytesIO
                output = BytesIO()

                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    history_df.to_excel(writer, sheet_name='Historico_Movimentacao', index=False)

                st.download_button(
                    label="📥 Download Excel",
                    data=output.getvalue(),
                    file_name=f"historico_movimentacao_{movement_date_from.strftime('%Y%m%d')}_{movement_date_to.strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        else:
            st.info(f"Nenhuma movimentação encontrada entre {movement_date_from.strftime('%d/%m/%Y')} e {movement_date_to.strftime('%d/%m/%Y')} com os filtros selecionados.")