# pages/9_ComprasPedidos.py
import streamlit as st
from auth import require_login, has_permission
from sqlmodel import Session, select
from db import engine
from models import PurchaseOrder, PurchaseItem, Supplier, RawMaterial
import pandas as pd
from datetime import date, timedelta
from services.pdf_generator import generate_purchase_order_pdf
import os

# Require login for this page
user = require_login()

st.set_page_config(page_title="GARNET - Compras e Pedidos", layout="wide")

# Professional page header
st.markdown("""
<div style="padding: 1rem 0 2rem 0; border-bottom: 1px solid #E8E8E8; margin-bottom: 2rem;">
    <h1 style="margin: 0; color: #2E4A6B; font-weight: 300;">Gestão de Compras e Pedidos</h1>
    <p style="margin: 0.5rem 0 0 0; color: #666; font-size: 1.1rem;">Controle de aquisições e relacionamento com fornecedores</p>
</div>
""", unsafe_allow_html=True)

# Clean tabs without icons
tab1, tab2, tab3 = st.tabs(["Pedidos de Compra", "Novo Pedido", "Análise de Compras"])

with tab1:
    st.subheader("Pedidos de Compra")

    # Filters
    filter_col1, filter_col2, filter_col3 = st.columns(3)

    with filter_col1:
        search_term = st.text_input("🔍 Buscar por código:", placeholder="PC-2024-001")

    with filter_col2:
        status_filter = st.selectbox("Status:", ["Todos", "Aberto", "Enviado", "Recebido", "Cancelado"])

    with filter_col3:
        # Get suppliers for filter
        with Session(engine) as session:
            suppliers = session.exec(select(Supplier)).all()
            supplier_options = ["Todos"] + [s.name for s in suppliers]

        supplier_filter = st.selectbox("Fornecedor:", supplier_options)

    # Get purchase orders
    with Session(engine) as session:
        query = select(PurchaseOrder, Supplier.name).join(
            Supplier, PurchaseOrder.supplier_id == Supplier.id
        )

        if search_term:
            query = query.where(PurchaseOrder.code.ilike(f"%{search_term}%"))

        if status_filter != "Todos":
            query = query.where(PurchaseOrder.status == status_filter)

        if supplier_filter != "Todos":
            query = query.where(Supplier.name == supplier_filter)

        results = session.exec(query.order_by(PurchaseOrder.created_at.desc())).all()

    if results:
        po_data = []
        for po, supplier_name in results:
            # Count items in this PO
            item_count = session.exec(
                select(PurchaseItem).where(PurchaseItem.po_id == po.id)
            ).all()

            po_data.append({
                "ID": po.id,
                "Código": po.code,
                "Fornecedor": supplier_name,
                "Data Pedido": po.order_date.strftime("%d/%m/%Y"),
                "Status": po.status,
                "Condições Pagamento": po.payment_terms or "N/A",
                "Valor Total": f"R$ {po.total_value:.2f}",
                "Itens": len(item_count)
            })

        df = pd.DataFrame(po_data)

        # Display with editing for operators
        if has_permission("operator"):
            edited_df = st.data_editor(
                df,
                hide_index=True,
                use_container_width=True,
                disabled=["ID", "Código", "Fornecedor", "Data Pedido", "Itens"],
                column_config={
                    "Status": st.column_config.SelectboxColumn(
                        "Status",
                        options=["Aberto", "Enviado", "Recebido", "Cancelado"],
                        required=True
                    )
                }
            )

            if st.button("💾 Salvar Alterações"):
                with Session(engine) as session:
                    for idx, row in edited_df.iterrows():
                        po = session.get(PurchaseOrder, row["ID"])
                        if po:
                            po.status = row["Status"]
                            po.payment_terms = row["Condições Pagamento"] if row["Condições Pagamento"] != "N/A" else None

                    session.commit()
                    st.success("Alterações salvas com sucesso!")
                    st.rerun()
        else:
            st.dataframe(df, hide_index=True, use_container_width=True)

        # Action buttons for editing purchase orders
        if results and has_permission("operator"):
            st.markdown("---")
            st.subheader("🔧 Editar Pedido de Compra")

            edit_po_options = [f"{po.code} - {next(s for p, s in results if p.id == po.id)}" for po, _ in results]
            selected_edit_po = st.selectbox("Selecione pedido para editar:", ["Selecione..."] + edit_po_options, key="edit_po_select")

            if selected_edit_po != "Selecione...":
                selected_edit_po_id = next(po.id for po, _ in results if f"{po.code} - {next(s for p, s in results if p.id == po.id)}" == selected_edit_po)

                edit_col1, edit_col2, edit_col3 = st.columns(3)

                with edit_col1:
                    if st.button("✏️ Editar Dados do Pedido", use_container_width=True):
                        st.session_state.edit_po_id = selected_edit_po_id
                        st.session_state.show_edit_po_form = True

                with edit_col2:
                    if st.button("📝 Editar Itens do Pedido", use_container_width=True):
                        st.session_state.edit_po_items_id = selected_edit_po_id
                        st.session_state.show_edit_po_items = True

                with edit_col3:
                    if st.button("📄 Gerar PDF do Pedido", use_container_width=True):
                        selected_po_for_pdf = next(po for po, _ in results if po.id == selected_edit_po_id)

                        # Fetch all details for PDF generation
                        with Session(engine) as session_pdf:
                            po_details = session_pdf.get(PurchaseOrder, selected_edit_po_id)
                            supplier_details = session_pdf.get(Supplier, po_details.supplier_id)
                            po_items_details = session_pdf.exec(
                                select(PurchaseItem, RawMaterial.code, RawMaterial.name_usual).join(
                                    RawMaterial, PurchaseItem.raw_material_id == RawMaterial.id
                                ).where(PurchaseItem.po_id == selected_edit_po_id)
                            ).all()

                            # Determinar tipo de pedido
                            order_type = po_details.notes if po_details.notes in ["Pedido de Compra", "Pedido de Amostra"] else "Pedido de Compra"

                            # Generate PDF
                            pdf_filepath = generate_purchase_order_pdf(po_details, supplier_details, po_items_details, order_type)

                            # Provide download link
                            with open(pdf_filepath, "rb") as fp:
                                btn = st.download_button(
                                    label="📥 Baixar PDF",
                                    data=fp,
                                    file_name=f"Pedido_Compra_{po_details.code}.pdf",
                                    mime="application/pdf"
                                )

                            # Clean up the generated file
                            if os.path.exists(pdf_filepath):
                                os.remove(pdf_filepath)

                # Delete purchase order section
                st.markdown("---")
                st.subheader("🗑️ Excluir Pedido de Compra")

                delete_po_options = [f"{po.code} - {next(s for p, s in results if p.id == po.id)}" for po, _ in results]
                selected_delete_po = st.selectbox("Selecione pedido para excluir:", ["Selecione..."] + delete_po_options, key="delete_po_select")

                if selected_delete_po != "Selecione...":
                    selected_delete_po_id = next(po.id for po, _ in results if f"{po.code} - {next(s for p, s in results if p.id == po.id)}" == selected_delete_po)

                    # Confirmation protection
                    if not st.session_state.get('show_delete_po_confirm'):
                        if st.button("🗑️ Excluir Pedido", type="primary", help="Clique para confirmar a exclusão"):
                            st.session_state.show_delete_po_confirm = True
                            st.session_state.po_to_delete_id = selected_delete_po_id
                            st.rerun()
                    else:
                        with Session(engine) as session:
                            po_to_delete = session.get(PurchaseOrder, st.session_state.po_to_delete_id)
                            if po_to_delete:
                                st.warning(f"⚠️ **ATENÇÃO**: Você está prestes a excluir o pedido **{po_to_delete.code}**")
                                st.error("Esta ação não pode ser desfeita! Todos os itens do pedido também serão excluídos.")

                                delete_col1, delete_col2 = st.columns(2)

                                with delete_col1:
                                    if st.button("✅ Confirmar Exclusão", type="primary"):
                                        try:
                                            # Delete all purchase items first
                                            po_items = session.exec(
                                                select(PurchaseItem).where(PurchaseItem.po_id == po_to_delete.id)
                                            ).all()

                                            for item in po_items:
                                                session.delete(item)

                                            # Delete purchase order
                                            po_code = po_to_delete.code
                                            session.delete(po_to_delete)
                                            session.commit()

                                            st.success(f"Pedido {po_code} excluído com sucesso!")
                                            st.session_state.show_delete_po_confirm = False
                                            st.session_state.po_to_delete_id = None
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Erro ao excluir pedido: {str(e)}")

                                with delete_col2:
                                    if st.button("❌ Cancelar"):
                                        st.session_state.show_delete_po_confirm = False
                                        st.session_state.po_to_delete_id = None
                                        st.rerun()

        # Edit PO form
        if st.session_state.get('show_edit_po_form') and st.session_state.get('edit_po_id'):
            with Session(engine) as session:
                po_to_edit = session.get(PurchaseOrder, st.session_state.edit_po_id)
                suppliers = session.exec(select(Supplier).where(Supplier.status == "ativo")).all()

                if po_to_edit and suppliers:
                    st.markdown("### ✏️ Editar Dados do Pedido de Compra")

                    with st.form(f"edit_po_{po_to_edit.id}"):
                        edit_po_col1, edit_po_col2 = st.columns(2)

                        with edit_po_col1:
                            edit_code = st.text_input("Código do Pedido *", value=po_to_edit.code)

                            # Current supplier
                            current_supplier = session.get(Supplier, po_to_edit.supplier_id)
                            supplier_options = [f"{s.name} (ID: {s.id})" for s in suppliers]
                            current_supplier_option = f"{current_supplier.name} (ID: {current_supplier.id})"
                            current_index = supplier_options.index(current_supplier_option) if current_supplier_option in supplier_options else 0

                            selected_supplier_option = st.selectbox("Fornecedor *", supplier_options, index=current_index)
                            selected_supplier_id = int(selected_supplier_option.split("ID: ")[1].split(")")[0])

                        with edit_po_col2:
                            edit_order_date = st.date_input("Data do Pedido", value=po_to_edit.order_date)
                            edit_status = st.selectbox("Status", ["Aberto", "Enviado", "Recebido", "Cancelado"], 
                                                     index=["Aberto", "Enviado", "Recebido", "Cancelado"].index(po_to_edit.status))

                        edit_payment_terms = st.text_input("Condições de Pagamento", value=po_to_edit.payment_terms or "")

                        form_col1, form_col2 = st.columns(2)

                        with form_col1:
                            if st.form_submit_button("💾 Salvar Alterações", use_container_width=True):
                                if not edit_code:
                                    st.error("Código do pedido é obrigatório.")
                                else:
                                    try:
                                        # Check if new code already exists (if changed)
                                        if edit_code != po_to_edit.code:
                                            existing = session.exec(
                                                select(PurchaseOrder).where(PurchaseOrder.code == edit_code)
                                            ).first()

                                            if existing:
                                                st.error("Já existe um pedido com este código.")
                                                st.stop()

                                        # Update PO
                                        po_to_edit.code = edit_code
                                        po_to_edit.supplier_id = selected_supplier_id
                                        po_to_edit.order_date = edit_order_date
                                        po_to_edit.status = edit_status
                                        po_to_edit.payment_terms = edit_payment_terms if edit_payment_terms else None

                                        session.commit()
                                        st.success("Pedido de compra atualizado com sucesso!")
                                        st.session_state.show_edit_po_form = False
                                        st.rerun()

                                    except Exception as e:
                                        st.error(f"Erro ao atualizar pedido: {str(e)}")

                        with form_col2:
                            if st.form_submit_button("❌ Cancelar", use_container_width=True):
                                st.session_state.show_edit_po_form = False
                                st.rerun()

        # Edit PO items
        if st.session_state.get('show_edit_po_items') and st.session_state.get('edit_po_items_id'):
            with Session(engine) as session:
                po_to_edit = session.get(PurchaseOrder, st.session_state.edit_po_items_id)
                po_items = session.exec(
                    select(PurchaseItem).where(PurchaseItem.po_id == po_to_edit.id)
                ).all()
                raw_materials = session.exec(select(RawMaterial).where(RawMaterial.status == "ativo")).all()

                if po_to_edit and raw_materials:
                    st.markdown("### 📝 Editar Itens do Pedido de Compra")
                    st.info(f"Editando itens do pedido: {po_to_edit.code}")

                    # Initialize PO items in session state if not exists
                    if f"edit_po_items_{po_to_edit.id}" not in st.session_state:
                        st.session_state[f"edit_po_items_{po_to_edit.id}"] = []
                        for item in po_items:
                            st.session_state[f"edit_po_items_{po_to_edit.id}"].append({
                                "id": item.id,
                                "rm_id": item.raw_material_id,
                                "qty": item.qty,
                                "uom": item.uom,
                                "price": item.price,
                                "due_date": item.due_date,
                                "received_qty": item.received_qty
                            })

                    edit_items = st.session_state[f"edit_po_items_{po_to_edit.id}"]

                    # Display items for editing
                    for i, item in enumerate(edit_items):
                        st.markdown(f"**Item {i+1}**")
                        item_col1, item_col2, item_col3, item_col4, item_col5, item_col6 = st.columns([3, 1, 1, 1, 2, 1])

                        with item_col1:
                            rm_options = [f"{rm.code} - {rm.name_usual}" for rm in raw_materials]
                            current_rm = next((rm for rm in raw_materials if rm.id == item["rm_id"]), None)
                            current_option = f"{current_rm.code} - {current_rm.name_usual}" if current_rm else None
                            current_index = rm_options.index(current_option) if current_option in rm_options else 0

                            rm_selection = st.selectbox(f"Matéria-Prima {i+1}", rm_options, index=current_index, key=f"edit_po_rm_{po_to_edit.id}_{i}")
                            item["rm_id"] = raw_materials[rm_options.index(rm_selection)].id

                        with item_col2:
                            item["qty"] = st.number_input(f"Qtd {i+1}", min_value=0.0, value=item["qty"], step=0.1, key=f"edit_po_qty_{po_to_edit.id}_{i}")

                        with item_col3:
                            item["uom"] = st.selectbox(f"UOM {i+1}", ["KG", "G", "L", "ML", "UN"], 
                                                     index=["KG", "G", "L", "ML", "UN"].index(item["uom"]), key=f"edit_po_uom_{po_to_edit.id}_{i}")

                        with item_col4:
                            item["price"] = st.number_input(f"Valor Total {i+1}", min_value=0.0, value=item["price"], step=0.01, key=f"edit_po_price_{po_to_edit.id}_{i}")

                        with item_col5:
                            item["due_date"] = st.date_input(f"Entrega {i+1}", value=item["due_date"], key=f"edit_po_due_{po_to_edit.id}_{i}")

                        with item_col6:
                            st.write("")  # Spacing
                            st.write("")  # Spacing
                            if st.button("🗑️ Remover", key=f"edit_po_del_{po_to_edit.id}_{i}"):
                                edit_items.pop(i)
                                st.rerun()

                    # Add new item button
                    if st.button("➕ Adicionar Item", key=f"add_po_item_{po_to_edit.id}"):
                        edit_items.append({
                            "id": None,  # New item
                            "rm_id": raw_materials[0].id if raw_materials else None,
                            "qty": 0.0,
                            "uom": "KG",
                            "price": 0.0,
                            "due_date": date.today(),
                            "received_qty": 0.0
                        })
                        st.rerun()

                    # Calculate total (price is already the total for each item)
                    total_po_value = sum(item["price"] for item in edit_items if item["rm_id"] and item["price"] > 0)
                    st.info(f"💰 Valor Total do Pedido: R$ {total_po_value:.2f}")

                    # Save/Cancel buttons
                    save_col1, save_col2 = st.columns(2)

                    with save_col1:
                        if st.button("💾 Salvar Itens", use_container_width=True, key=f"save_po_items_{po_to_edit.id}"):
                            try:
                                # Delete existing items
                                for item in po_items:
                                    session.delete(item)

                                # Add updated items
                                for item in edit_items:
                                    if item["rm_id"]:
                                        po_item = PurchaseItem(
                                            po_id=po_to_edit.id,
                                            raw_material_id=item["rm_id"],
                                            qty=item["qty"],
                                            uom=item["uom"],
                                            price=item["price"],
                                            due_date=item["due_date"],
                                            received_qty=item.get("received_qty", 0.0)
                                        )
                                        session.add(po_item)

                                # Update total value
                                po_to_edit.total_value = total_po_value

                                session.commit()
                                st.success("Itens do pedido atualizados com sucesso!")
                                st.session_state.show_edit_po_items = False
                                del st.session_state[f"edit_po_items_{po_to_edit.id}"]
                                st.rerun()

                            except Exception as e:
                                st.error(f"Erro ao atualizar itens: {str(e)}")

                    with save_col2:
                        if st.button("❌ Cancelar", use_container_width=True, key=f"cancel_po_items_{po_to_edit.id}"):
                            st.session_state.show_edit_po_items = False
                            del st.session_state[f"edit_po_items_{po_to_edit.id}"]
                            st.rerun()

        # Detailed view
        st.markdown("---")
        st.subheader("Detalhes do Pedido")

        if results:
            selected_po_code = st.selectbox(
                "Selecione um pedido para ver detalhes:",
                options=[po.code for po, _ in results]
            )

            selected_po = next(po for po, _ in results if po.code == selected_po_code)
            selected_supplier = next(supplier_name for po, supplier_name in results if po.code == selected_po_code)

            detail_col1, detail_col2 = st.columns(2)

            with detail_col1:
                st.markdown("**Informações do Pedido**")
                st.text(f"Código: {selected_po.code}")
                st.text(f"Fornecedor: {selected_supplier}")
                st.text(f"Data: {selected_po.order_date.strftime('%d/%m/%Y')}")
                st.text(f"Status: {selected_po.status}")

            with detail_col2:
                st.markdown("**Informações Comerciais**")
                st.text(f"Condições Pagamento: {selected_po.payment_terms or 'Não definido'}")
                st.text(f"Valor Total: R$ {selected_po.total_value:.2f}")
                st.text(f"Criado em: {selected_po.created_at.strftime('%d/%m/%Y %H:%M') if selected_po.created_at else 'N/A'}")

            # Items in this purchase order
            st.markdown("**Itens do Pedido**")

            items_query = select(PurchaseItem, RawMaterial.code, RawMaterial.name_usual).join(
                RawMaterial, PurchaseItem.raw_material_id == RawMaterial.id
            ).where(PurchaseItem.po_id == selected_po.id)

            items_results = session.exec(items_query).all()

            if items_results:
                items_data = []
                total_value = 0

                for item, rm_code, rm_name in items_results:
                    line_total = item.price  # Price is already the total value
                    total_value += line_total

                    # Calculate received percentage
                    received_pct = (item.received_qty / item.qty * 100) if item.qty > 0 else 0

                    items_data.append({
                        "Código MP": rm_code,
                        "Matéria-Prima": rm_name,
                        "Quantidade": f"{item.qty} {item.uom}",
                        "Valor Total": f"R$ {item.price:.2f}",
                        "Data Entrega": item.due_date.strftime("%d/%m/%Y") if item.due_date else "N/A",
                        "Recebido": f"{item.received_qty} {item.uom}",
                        "% Recebido": f"{received_pct:.1f}%"
                    })

                items_df = pd.DataFrame(items_data)
                st.dataframe(items_df, hide_index=True, use_container_width=True)

                # Update total value if different
                if abs(selected_po.total_value - total_value) > 0.01:
                    selected_po.total_value = total_value
                    session.commit()
            else:
                st.info("Este pedido não possui itens cadastrados.")
    else:
        st.info("Nenhum pedido de compra encontrado.")

with tab2:
    st.subheader("Criar Novo Pedido de Compra")

    if not has_permission("operator"):
        st.error("Você não tem permissão para criar pedidos de compra.")
    else:
        with Session(engine) as session:
            suppliers = session.exec(select(Supplier).where(Supplier.status == "ativo")).all()
            raw_materials = session.exec(select(RawMaterial).where(RawMaterial.status == "ativo")).all()

        if not suppliers:
            st.error("Nenhum fornecedor ativo encontrado.")
        elif not raw_materials:
            st.error("Nenhuma matéria-prima ativa encontrada.")
        else:
            with st.form("new_purchase_order"):
                # Seletor de tipo de pedido
                order_type = st.selectbox("Tipo de Pedido *", ["Pedido de Compra", "Pedido de Amostra"])

                po_col1, po_col2 = st.columns(2)

                with po_col1:
                    # Auto-generate PO code
                    next_number = 1
                    with Session(engine) as session:
                        last_po = session.exec(
                            select(PurchaseOrder).order_by(PurchaseOrder.id.desc())
                        ).first()
                        if last_po and last_po.code.startswith("PC-"):
                            try:
                                last_number = int(last_po.code.split("-")[-1])
                                next_number = last_number + 1
                            except:
                                pass

                    # Ajustar prefixo do código baseado no tipo de pedido
                    prefix = "PC" if order_type == "Pedido de Compra" else "PA"
                    suggested_code = f"{prefix}-{date.today().year}-{next_number:03d}"
                    code = st.text_input("Código do Pedido *", value=suggested_code)

                    # Supplier selection
                    supplier_options = [f"{s.name} (ID: {s.id})" for s in suppliers]
                    selected_supplier_option = st.selectbox("Fornecedor *", supplier_options)
                    selected_supplier_id = int(selected_supplier_option.split("ID: ")[1].split(")")[0])

                with po_col2:
                    order_date = st.date_input("Data do Pedido", value=date.today())
                    payment_terms = st.text_input("Condições de Pagamento", placeholder="Ex: 30 dias")

                st.markdown("**Itens do Pedido**")

                # Dynamic purchase items
                if "purchase_items" not in st.session_state:
                    if order_type == "Pedido de Amostra":
                        st.session_state.purchase_items = [{"product_name": "", "qty": 0.01, "uom": "KG", "price": 0.0, "due_date": None}]
                    else:
                        st.session_state.purchase_items = [{"rm_id": None, "qty": 0.01, "uom": "KG", "price": 0.0, "due_date": None}]

                # Display purchase items based on order type
                for i, item in enumerate(st.session_state.purchase_items):
                    item_col1, item_col2, item_col3, item_col4, item_col5 = st.columns([3, 1, 1, 1, 2])

                    with item_col1:
                        if order_type == "Pedido de Amostra":
                            # Free text field for sample requests
                            item["product_name"] = st.text_input(
                                f"Nome do Produto {i+1}", 
                                value=item.get("product_name", ""),
                                placeholder="Digite o nome do produto/amostra",
                                key=f"po_product_{i}"
                            )
                            # Set rm_id to None for sample orders
                            item["rm_id"] = None
                        else:
                            # Original dropdown for purchase orders
                            rm_options = [f"{rm.code} - {rm.name_usual}" for rm in raw_materials]
                            rm_selection = st.selectbox(f"Matéria-Prima {i+1}", ["Selecione..."] + rm_options, key=f"po_rm_{i}")
                            if rm_selection != "Selecione...":
                                item["rm_id"] = raw_materials[rm_options.index(rm_selection)].id
                            else:
                                item["rm_id"] = None
                            # Clear product_name for purchase orders
                            item["product_name"] = ""

                    with item_col2:
                        item["qty"] = st.number_input(f"Qtd {i+1}", min_value=0.01, value=max(0.01, item["qty"]), step=0.01, key=f"po_qty_{i}")

                    with item_col3:
                        item["uom"] = st.selectbox(f"UOM {i+1}", ["KG", "G", "L", "ML", "UN"], 
                                                 index=["KG", "G", "L", "ML", "UN"].index(item["uom"]), key=f"po_uom_{i}")

                    with item_col4:
                        item["price"] = st.number_input(f"Valor Total {i+1}", min_value=0.0, value=item["price"], step=0.01, key=f"po_price_{i}")

                    with item_col5:
                        item["due_date"] = st.date_input(f"Entrega {i+1}", value=item["due_date"], key=f"po_due_{i}")

                # Calculate total (price is already the total for each item)
                total_po_value = sum(item["price"] for item in st.session_state.purchase_items if (item["rm_id"] or item.get("product_name")) and item["price"] > 0)
                st.info(f"💰 Valor Total do Pedido: R$ {total_po_value:.2f}")

                # Form action buttons
                form_col1, form_col2, form_col3 = st.columns(3)
                
                with form_col1:
                    submitted = st.form_submit_button("💾 Criar Pedido de Compra", use_container_width=True)
                
                with form_col2:
                    add_item = st.form_submit_button("➕ Adicionar Item", use_container_width=True)
                
                with form_col3:
                    remove_last = st.form_submit_button("🗑️ Remover Último Item", use_container_width=True)

            # Handle add/remove items
            if add_item:
                if order_type == "Pedido de Amostra":
                    st.session_state.purchase_items.append({"product_name": "", "qty": 0.01, "uom": "KG", "price": 0.0, "due_date": None})
                else:
                    st.session_state.purchase_items.append({"rm_id": None, "qty": 0.01, "uom": "KG", "price": 0.0, "due_date": None})
                st.rerun()
            
            if remove_last and len(st.session_state.purchase_items) > 1:
                st.session_state.purchase_items.pop()
                st.rerun()

            if submitted:
                    if not code:
                        st.error("Código do pedido é obrigatório.")
                    elif not any(item.get("rm_id") or item.get("product_name") for item in st.session_state.purchase_items):
                        st.error("Adicione pelo menos um item ao pedido.")
                    else:
                        try:
                            with Session(engine) as session:
                                # Check if code already exists
                                existing = session.exec(
                                    select(PurchaseOrder).where(PurchaseOrder.code == code)
                                ).first()

                                if existing:
                                    st.error("Já existe um pedido com este código.")
                                else:
                                    # Create purchase order
                                    new_po = PurchaseOrder(
                                        code=code,
                                        supplier_id=selected_supplier_id,
                                        order_date=order_date,
                                        payment_terms=payment_terms if payment_terms else None,
                                        total_value=total_po_value,
                                        notes=order_type  # Armazenar o tipo do pedido no campo notes
                                    )
                                    session.add(new_po)
                                    session.flush()  # Get the ID

                                    # Add purchase items
                                    for item in st.session_state.purchase_items:
                                        if item.get("rm_id"):  # For Pedido de Compra
                                            purchase_item = PurchaseItem(
                                                po_id=new_po.id,
                                                raw_material_id=item["rm_id"],
                                                qty=item["qty"],
                                                uom=item["uom"],
                                                price=item["price"],
                                                due_date=item["due_date"]
                                            )
                                            session.add(purchase_item)
                                        elif item.get("product_name"):  # For Pedido de Amostra
                                            purchase_item = PurchaseItem(
                                                po_id=new_po.id,
                                                raw_material_id=None,
                                                qty=item["qty"],
                                                uom=item["uom"],
                                                price=item["price"],
                                                due_date=item["due_date"],
                                                notes=f"Amostra: {item['product_name']}"
                                            )
                                            session.add(purchase_item)


                                    session.commit()
                                    st.success(f"Pedido de compra '{code}' criado com sucesso!")

                                    # Clear session state
                                    if "purchase_items" in st.session_state:
                                        del st.session_state.purchase_items
                                    st.rerun()

                        except Exception as e:
                            st.error(f"Erro ao criar pedido: {str(e)}")

with tab3:
    st.subheader("📊 Análise de Compras")

    # Purchase analytics
    with Session(engine) as session:
        # Overall metrics
        total_pos = session.exec(select(PurchaseOrder)).all()
        total_value = sum(po.total_value for po in total_pos)

        open_pos = [po for po in total_pos if po.status in ["Aberto", "Enviado"]]
        pending_value = sum(po.total_value for po in open_pos)

        metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)

        with metrics_col1:
            st.metric("Total de Pedidos", len(total_pos))

        with metrics_col2:
            st.metric("Valor Total", f"R$ {total_value:,.2f}")

        with metrics_col3:
            st.metric("Pedidos Pendentes", len(open_pos))

        with metrics_col4:
            st.metric("Valor Pendente", f"R$ {pending_value:,.2f}")

    # Charts
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.markdown("### 📊 Pedidos por Status")

        if total_pos:
            status_counts = {}
            for po in total_pos:
                status_counts[po.status] = status_counts.get(po.status, 0) + 1

            status_df = pd.DataFrame(list(status_counts.items()), columns=["Status", "Quantidade"])

            import plotly.express as px
            fig_status = px.pie(status_df, values="Quantidade", names="Status", 
                              title="Distribuição por Status")
            st.plotly_chart(fig_status, use_container_width=True)
        else:
            st.info("Nenhum pedido para exibir.")

    with chart_col2:
        st.markdown("### 💰 Valor por Fornecedor")

        # Supplier purchase analysis
        supplier_values = {}
        for po in total_pos:
            supplier = session.get(Supplier, po.supplier_id)
            supplier_name = supplier.name if supplier else "Desconhecido"
            supplier_values[supplier_name] = supplier_values.get(supplier_name, 0) + po.total_value

        if supplier_values:
            supplier_df = pd.DataFrame(list(supplier_values.items()), columns=["Fornecedor", "Valor Total"])
            supplier_df = supplier_df.sort_values("Valor Total", ascending=True)

            fig_supplier = px.bar(supplier_df, x="Valor Total", y="Fornecedor", orientation="h",
                                title="Compras por Fornecedor")
            st.plotly_chart(fig_supplier, use_container_width=True)
        else:
            st.info("Nenhum dado de fornecedor para exibir.")

    # Timeline analysis
    st.markdown("---")
    st.markdown("### 📅 Timeline de Compras")

    if total_pos:
        # Monthly purchase analysis
        monthly_purchases = {}
        for po in total_pos:
            month_key = po.order_date.strftime("%Y-%m")
            if month_key not in monthly_purchases:
                monthly_purchases[month_key] = {"count": 0, "value": 0}
            monthly_purchases[month_key]["count"] += 1
            monthly_purchases[month_key]["value"] += po.total_value

        if monthly_purchases:
            monthly_data = []
            for month, data in monthly_purchases.items():
                monthly_data.append({
                    "Mês": month,
                    "Quantidade de Pedidos": data["count"],
                    "Valor Total": data["value"]
                })

            monthly_df = pd.DataFrame(monthly_data)
            monthly_df = monthly_df.sort_values("Mês")

            # Dual axis chart
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots

            fig_timeline = make_subplots(specs=[[{"secondary_y": True}]])

            fig_timeline.add_trace(
                go.Bar(x=monthly_df["Mês"], y=monthly_df["Quantidade de Pedidos"], name="Quantidade"),
                secondary_y=False,
            )

            fig_timeline.add_trace(
                go.Scatter(x=monthly_df["Mês"], y=monthly_df["Valor Total"], mode="lines+markers", name="Valor"),
                secondary_y=True,
            )

            fig_timeline.update_xaxes(title_text="Mês")
            fig_timeline.update_yaxes(title_text="Quantidade de Pedidos", secondary_y=False)
            fig_timeline.update_yaxes(title_text="Valor Total (R$)", secondary_y=True)
            fig_timeline.update_layout(title_text="Evolução de Compras Mensais")

            st.plotly_chart(fig_timeline, use_container_width=True)

    # Top materials
    st.markdown("---")
    st.markdown("### 🧪 Top Matérias-Primas Compradas")

    # Get all purchase items
    all_items = session.exec(select(PurchaseItem, RawMaterial.code, RawMaterial.name_usual).join(
        RawMaterial, PurchaseItem.raw_material_id == RawMaterial.id
    )).all()

    if all_items:
        material_stats = {}
        for item, rm_code, rm_name in all_items:
            if rm_name not in material_stats:
                material_stats[rm_name] = {"qty": 0, "value": 0}
            material_stats[rm_name]["qty"] += item.qty
            material_stats[rm_name]["value"] += item.qty * item.price

        # Sort by value
        top_materials = sorted(material_stats.items(), key=lambda x: x[1]["value"], reverse=True)[:10]

        if top_materials:
            top_data = []
            for material, stats in top_materials:
                top_data.append({
                    "Matéria-Prima": material,
                    "Quantidade Total": f"{stats['qty']:,.2f}",
                    "Valor Total": f"R$ {stats['value']:,.2f}"
                })

            top_df = pd.DataFrame(top_data)
            st.dataframe(top_df, hide_index=True, use_container_width=True)
        else:
            st.info("Nenhum item de compra encontrado.")
    else:
        st.info("Nenhum item de compra encontrado.")