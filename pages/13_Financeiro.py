# pages/13_Financeiro.py
import streamlit as st
from auth import require_login, has_permission
from sqlmodel import Session, select
from db import engine
from models import Payable, Supplier, PurchaseOrder, Receivable
import pandas as pd
from datetime import date, timedelta, datetime
import calendar
import plotly.graph_objects as go

# Require login for this page
user = require_login()

st.set_page_config(page_title="GARNET - Financeiro", layout="wide")

# Professional page header
st.markdown("""
<div style="padding: 1rem 0 2rem 0; border-bottom: 1px solid #E8E8E8; margin-bottom: 2rem;">
    <h1 style="margin: 0; color: #2E4A6B; font-weight: 300;">Gestão Financeira</h1>
    <p style="margin: 0.5rem 0 0 0; color: #666; font-size: 1.1rem;">Controle de fluxo de caixa e análises financeiras</p>
</div>
""", unsafe_allow_html=True)

# Create tabs based on user permission
if has_permission("manager"):
    # Managers have access to all tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Contas a Pagar", "Receitas a Receber", "Fluxo de Caixa", "Análises", "Orçamento"])
else:
    # Other users only have access to basic tabs
    tab1, tab2 = st.tabs(["Contas a Pagar", "Receitas a Receber"])
    # Set restricted tabs to None for conditional logic
    tab3 = tab4 = tab5 = None

with tab1:
    st.subheader("Contas a Pagar")

    # Search field
    search_term_payable = st.text_input("🔍 Buscar por documento, fornecedor ou observações:", key="search_payable")

    # Filters
    filter_col1, filter_col2, filter_col3, filter_col4, filter_col5 = st.columns(5)

    with filter_col1:
        status_filter = st.selectbox("Status:", ["Todos", "Pendente", "Pago", "Vencido"])

    with filter_col2:
        # Get suppliers for filter
        with Session(engine) as session:
            suppliers = session.exec(select(Supplier)).all()
            supplier_options = ["Todos"] + [s.name for s in suppliers]

        supplier_filter = st.selectbox("Fornecedor:", supplier_options)

    with filter_col3:
        date_range = st.selectbox("Período:", ["Todos", "Vence Hoje", "Próximos 7 dias", "Próximos 30 dias", "Vencidos"])

    with filter_col4:
        # Get unique expense types for filter
        with Session(engine) as session:
            expense_types = session.exec(select(Payable.expense_type).distinct().where(Payable.expense_type.isnot(None))).all()
            expense_type_options = ["Todos"] + [et for et in expense_types if et]

        expense_type_filter = st.selectbox("Tipo de Gasto:", expense_type_options)

    with filter_col5:
        value_min = st.number_input("Valor mínimo:", min_value=0.0, value=0.0, step=100.0, key="payable_min")
        value_max = st.number_input("Valor máximo:", min_value=0.0, value=0.0, step=100.0, key="payable_max")

    # Get payables based on filters
    with Session(engine) as session:
        query = select(Payable, Supplier.name).outerjoin(
            Supplier, Payable.supplier_id == Supplier.id
        ).where(Payable.status != "Controle")  # Exclude control records

        # Apply search filter
        if search_term_payable:
            search_pattern = f"%{search_term_payable}%"
            query = query.where(
                (Payable.doc_ref.ilike(search_pattern)) |
                (Supplier.name.ilike(search_pattern)) |
                (Payable.notes.ilike(search_pattern))
            )

        # Apply filters
        if status_filter != "Todos":
            if status_filter == "Vencido":
                query = query.where(Payable.due_date < date.today()).where(Payable.status == "Pendente")
            else:
                query = query.where(Payable.status == status_filter)

        if supplier_filter != "Todos":
            query = query.where(Supplier.name == supplier_filter)

        if expense_type_filter != "Todos":
            query = query.where(Payable.expense_type == expense_type_filter)

        # Apply value filters
        if value_min > 0:
            query = query.where(Payable.value >= value_min)
        if value_max > 0:
            query = query.where(Payable.value <= value_max)

        # Apply date filters
        if date_range == "Vence Hoje":
            query = query.where(Payable.due_date == date.today())
        elif date_range == "Próximos 7 dias":
            query = query.where(Payable.due_date <= date.today() + timedelta(days=7))
            query = query.where(Payable.due_date >= date.today())
        elif date_range == "Próximos 30 dias":
            query = query.where(Payable.due_date <= date.today() + timedelta(days=30))
            query = query.where(Payable.due_date >= date.today())
        elif date_range == "Vencidos":
            query = query.where(Payable.due_date < date.today())

        results = session.exec(query.order_by(Payable.due_date)).all()

    if results:
        payable_data = []
        total_pending = 0
        total_overdue = 0

        for payable, supplier_name in results:
            days_to_due = (payable.due_date - date.today()).days

            # Status indicator
            if payable.status == "Pago":
                status_icon = "✅"
            elif days_to_due < 0:
                status_icon = "🔴"
                total_overdue += payable.value
            elif days_to_due <= 7:
                status_icon = "🟡"
            else:
                status_icon = "🟢"

            if payable.status == "Pendente":
                total_pending += payable.value

            installment_info = ""
            if payable.is_installment and payable.installment_number and payable.total_installments:
                installment_info = f" ({payable.installment_number}/{payable.total_installments})"

            payable_data.append({
                "ID": payable.id,
                "Status": status_icon,
                "Fornecedor": supplier_name or "N/A",
                "Empresa": payable.empresa or "N/A",
                "Documento": payable.doc_ref + installment_info,
                "Tipo de Gasto": payable.expense_type or "N/A",
                "Valor": f"R$ {payable.value:,.2f}",
                "Vencimento": payable.due_date.strftime("%d/%m/%Y"),
                "Dias": days_to_due,
                "Status Pag.": payable.status,
                "PDF": "✅" if payable.xml_file_path else "❌",
                "Observações": payable.notes or "N/A"
            })

        # Summary metrics
        if has_permission("manager"):
            metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)

            with metrics_col1:
                st.metric("Total a Pagar", f"R$ {total_pending:,.2f}")

            with metrics_col2:
                st.metric("Total Vencido", f"R$ {total_overdue:,.2f}")

            with metrics_col3:
                today_due = sum(payable.value for payable, _ in results if payable.due_date == date.today())
                st.metric("Vence Hoje", f"R$ {today_due:,.2f}")

            with metrics_col4:
                st.metric("Total de Títulos", len(payable_data))
        else:
            # Operadores veem apenas o total de títulos
            st.metric("Total de Títulos", len(payable_data))

        # Display table
        st.markdown("### 📋 Lista de Contas a Pagar")

        df = pd.DataFrame(payable_data)

        # Editable table for operators
        if has_permission("operator"):
            edited_df = st.data_editor(
                df,
                hide_index=True,
                use_container_width=True,
                disabled=["ID", "Status", "Fornecedor", "Empresa", "Documento", "Dias", "PDF"],
                column_config={
                    "Status Pag.": st.column_config.SelectboxColumn(
                        "Status Pagamento",
                        options=["Pendente", "Pago"],
                        required=True
                    )
                }
            )

            # Action buttons
            action_col1, action_col2, action_col3 = st.columns(3)
            
            with action_col1:
                if st.button("💾 Salvar Alterações"):
                    with Session(engine) as session:
                        for idx, row in edited_df.iterrows():
                            payable = session.get(Payable, int(row["ID"]))
                            if payable:
                                payable.status = row["Status Pag."]
                                payable.expense_type = row["Tipo de Gasto"] if row["Tipo de Gasto"] != "N/A" else None
                                payable.notes = row["Observações"] if row["Observações"] != "N/A" else None

                        session.commit()
                        st.success("Alterações salvas com sucesso!")
                        st.rerun()

            with action_col2:
                # Edit payable
                payable_options = [f"{row['Documento']} - R$ {row['Valor']}" for _, row in df.iterrows()]
                if payable_options:
                    selected_payable_option = st.selectbox("Selecionar conta para editar:", [""] + payable_options, key="edit_payable_select")
                    
                    if selected_payable_option and st.button("✏️ Editar Conta"):
                        selected_payable_id = df[df.apply(lambda x: f"{x['Documento']} - R$ {x['Valor']}" == selected_payable_option, axis=1)]['ID'].iloc[0]
                        st.session_state.edit_payable_id = int(selected_payable_id)
                        st.session_state.show_edit_payable_form = True

            with action_col3:
                # Delete payable
                if payable_options:
                    selected_delete_payable_option = st.selectbox("Selecionar conta para excluir:", [""] + payable_options, key="delete_payable_select")
                    
                    if selected_delete_payable_option and st.button("🗑️ Excluir Conta"):
                        selected_delete_payable_id = df[df.apply(lambda x: f"{x['Documento']} - R$ {x['Valor']}" == selected_delete_payable_option, axis=1)]['ID'].iloc[0]
                        st.session_state.delete_payable_id = int(selected_delete_payable_id)
                        st.session_state.show_delete_payable_confirm = True

            # Edit payable form
            if st.session_state.get('show_edit_payable_form') and st.session_state.get('edit_payable_id'):
                with Session(engine) as session:
                    payable_to_edit = session.get(Payable, st.session_state.edit_payable_id)
                    if payable_to_edit:
                        st.markdown("---")
                        st.markdown("### ✏️ Editar Conta a Pagar")
                        
                        with st.form("edit_payable_form"):
                            edit_col1, edit_col2 = st.columns(2)
                            
                            with edit_col1:
                                # Get supplier info for display
                                supplier_name = "Nenhum"
                                if payable_to_edit.supplier_id:
                                    supplier = session.get(Supplier, payable_to_edit.supplier_id)
                                    if supplier:
                                        supplier_name = f"{supplier.name} (ID: {supplier.id})"
                                
                                supplier_options = ["Nenhum"] + [f"{s.name} (ID: {s.id})" for s in suppliers]
                                current_supplier_index = 0
                                if supplier_name in supplier_options:
                                    current_supplier_index = supplier_options.index(supplier_name)
                                
                                edit_supplier_option = st.selectbox("Fornecedor:", supplier_options, index=current_supplier_index)
                                edit_supplier_id = None
                                if edit_supplier_option != "Nenhum":
                                    edit_supplier_id = int(edit_supplier_option.split("ID: ")[1].split(")")[0])
                                
                                edit_doc_ref = st.text_input("Documento *", value=payable_to_edit.doc_ref)
                                edit_empresa = st.text_input("Empresa Pagante", value=payable_to_edit.empresa or "")
                                edit_expense_type = st.text_input("Tipo de Gasto", value=payable_to_edit.expense_type or "")
                                edit_value = st.number_input("Valor *", min_value=0.0, step=0.01, value=float(payable_to_edit.value))
                            
                            with edit_col2:
                                edit_due_date = st.date_input("Data de Vencimento *", value=payable_to_edit.due_date)
                                edit_status = st.selectbox("Status", ["Pendente", "Pago"], 
                                                         index=0 if payable_to_edit.status == "Pendente" else 1)
                                edit_notes = st.text_area("Observações", value=payable_to_edit.notes or "")
                            
                            # PDF file upload
                            st.markdown("**Anexar/Atualizar Nota Fiscal (PDF)**")
                            if payable_to_edit.xml_file_path:
                                st.info(f"PDF atual: {payable_to_edit.xml_file_path.split('/')[-1]}")
                            edit_xml_file = st.file_uploader(
                                "Selecione o arquivo PDF da nota fiscal (deixe em branco para manter o atual)", 
                                type=['pdf'], 
                                help="Faça upload do arquivo PDF da nota fiscal",
                                key="edit_payable_pdf"
                            )
                            
                            form_col1, form_col2 = st.columns(2)
                            
                            with form_col1:
                                if st.form_submit_button("💾 Salvar Alterações", use_container_width=True):
                                    if not edit_doc_ref or edit_value <= 0:
                                        st.error("Documento e valor são obrigatórios.")
                                    else:
                                        import os
                                        
                                        # Handle PDF file upload
                                        if edit_xml_file:
                                            upload_dir = "uploads/pdf_files"
                                            os.makedirs(upload_dir, exist_ok=True)
                                            edit_xml_file_path = os.path.join(upload_dir, f"{edit_doc_ref}_{edit_xml_file.name}")
                                            with open(edit_xml_file_path, "wb") as f:
                                                f.write(edit_xml_file.getbuffer())
                                            payable_to_edit.xml_file_path = edit_xml_file_path
                                        
                                        payable_to_edit.supplier_id = edit_supplier_id
                                        payable_to_edit.doc_ref = edit_doc_ref
                                        payable_to_edit.empresa = edit_empresa if edit_empresa else None
                                        payable_to_edit.expense_type = edit_expense_type if edit_expense_type else None
                                        payable_to_edit.value = edit_value
                                        payable_to_edit.due_date = edit_due_date
                                        payable_to_edit.status = edit_status
                                        payable_to_edit.notes = edit_notes if edit_notes else None
                                        
                                        session.commit()
                                        st.success("Conta a pagar atualizada com sucesso!")
                                        st.session_state.show_edit_payable_form = False
                                        st.rerun()
                            
                            with form_col2:
                                if st.form_submit_button("❌ Cancelar", use_container_width=True):
                                    st.session_state.show_edit_payable_form = False
                                    st.rerun()

            # Delete payable confirmation
            if st.session_state.get('show_delete_payable_confirm') and st.session_state.get('delete_payable_id'):
                with Session(engine) as session:
                    payable_to_delete = session.get(Payable, st.session_state.delete_payable_id)
                    if payable_to_delete:
                        st.markdown("---")
                        st.markdown("### ⚠️ Confirmar Exclusão de Conta a Pagar")
                        st.warning(f"Tem certeza que deseja excluir a conta **{payable_to_delete.doc_ref}** no valor de **R$ {payable_to_delete.value:,.2f}**?")
                        
                        # Check if this is a parent record (has children)
                        children = session.exec(select(Payable).where(Payable.parent_payable_id == payable_to_delete.id)).all()
                        if children:
                            st.warning(f"⚠️ Esta conta possui {len(children)} parcelas que também serão excluídas!")
                        
                        st.error("**ATENÇÃO:** Esta ação não pode ser desfeita!")
                        
                        delete_col1, delete_col2 = st.columns(2)
                        
                        with delete_col1:
                            if st.button("🗑️ Sim, Excluir", use_container_width=True, type="primary"):
                                try:
                                    # Refresh the payable object to ensure we have the latest data
                                    session.refresh(payable_to_delete)
                                    
                                    # Check if this payable is a child (installment) of another payable
                                    if payable_to_delete.parent_payable_id:
                                        # This is a child installment, just delete it
                                        session.delete(payable_to_delete)
                                        session.commit()
                                        st.success(f"Parcela '{payable_to_delete.doc_ref}' excluída com sucesso!")
                                    else:
                                        # This might be a parent, check for children first
                                        children = session.exec(select(Payable).where(Payable.parent_payable_id == payable_to_delete.id)).all()
                                        
                                        # Delete all children (installments) first to avoid foreign key constraint
                                        for child in children:
                                            session.delete(child)
                                        
                                        # Commit the children deletions first
                                        session.commit()
                                        
                                        # Now delete the parent
                                        session.delete(payable_to_delete)
                                        session.commit()
                                        
                                        if children:
                                            st.success(f"Conta '{payable_to_delete.doc_ref}' e suas {len(children)} parcelas foram excluídas com sucesso!")
                                        else:
                                            st.success(f"Conta '{payable_to_delete.doc_ref}' excluída com sucesso!")
                                    
                                    st.session_state.show_delete_payable_confirm = False
                                    st.rerun()
                                    
                                except Exception as e:
                                    st.error(f"Erro ao excluir conta: {str(e)}")
                                    session.rollback()
                        
                        with delete_col2:
                            if st.button("❌ Cancelar", use_container_width=True):
                                st.session_state.show_delete_payable_confirm = False
                                st.rerun()
        else:
            st.dataframe(df, hide_index=True, use_container_width=True)

    else:
        st.info("Nenhuma conta a pagar encontrada com os filtros aplicados.")

    # Add new payable
    if has_permission("operator"):
        st.markdown("---")
        st.subheader("➕ Adicionar Conta a Pagar")

        with st.form("new_payable"):
            payable_col1, payable_col2 = st.columns(2)

            with payable_col1:
                # Supplier selection
                supplier_options = ["Nenhum"] + [f"{s.name} (ID: {s.id})" for s in suppliers]
                selected_supplier_option = st.selectbox("Fornecedor:", supplier_options)
                supplier_id = None
                if selected_supplier_option != "Nenhum":
                    supplier_id = int(selected_supplier_option.split("ID: ")[1].split(")")[0])

                doc_ref = st.text_input("Documento *", placeholder="NF, Fatura, etc.")
                expense_type = st.text_input("Tipo de Gasto", placeholder="Categoria do gasto")
                empresa = st.text_input("Empresa", placeholder="Nome da empresa pagante")
                value = st.number_input("Valor *", min_value=0.0, step=0.01)

            with payable_col2:
                due_date = st.date_input("Data de Vencimento *", value=date.today() + timedelta(days=30))
                status = st.selectbox("Status", ["Pendente", "Pago"])
                notes = st.text_area("Observações", placeholder="Observações adicionais")

            # PDF file upload
            st.markdown("**Anexar Nota Fiscal (PDF)**")
            xml_file = st.file_uploader(
                "Selecione o arquivo PDF da nota fiscal", 
                type=['pdf'], 
                help="Faça upload do arquivo PDF da nota fiscal"
            )

            # Installment options
            st.markdown("**Parcelamento**")
            
            # Check previous state to detect changes
            prev_installment_state = st.session_state.get("prev_payable_installment", False)
            is_installment = st.checkbox("Esta conta será parcelada?", key="payable_installment_checkbox")

            # If state changed, update session state and rerun
            if is_installment != prev_installment_state:
                st.session_state.prev_payable_installment = is_installment
                st.rerun()

            installments = 1
            installment_values = []
            installment_dates = []

            if is_installment:
                installment_col1, installment_col2 = st.columns(2)
                with installment_col1:
                    installments = st.number_input("Número de Parcelas", min_value=2, max_value=24, value=2, key="payable_installments_count")

                st.markdown("**Configurar Parcelas**")

                # Initialize session state for installment values if not exists
                if f"payable_installment_values" not in st.session_state:
                    st.session_state.payable_installment_values = {}
                if f"payable_installment_dates" not in st.session_state:
                    st.session_state.payable_installment_dates = {}

                for i in range(installments):
                    parcela_col1, parcela_col2 = st.columns(2)
                    with parcela_col1:
                        # Use session state to maintain values
                        default_value = value/installments if value > 0 else 0.0
                        if f"parcela_valor_{i}" not in st.session_state.payable_installment_values:
                            st.session_state.payable_installment_values[f"parcela_valor_{i}"] = default_value
                        
                        parcela_value = st.number_input(
                            f"Valor da Parcela {i+1}", 
                            min_value=0.0, 
                            step=0.01, 
                            value=st.session_state.payable_installment_values[f"parcela_valor_{i}"],
                            key=f"parcela_valor_{i}"
                        )
                        st.session_state.payable_installment_values[f"parcela_valor_{i}"] = parcela_value
                        installment_values.append(parcela_value)

                    with parcela_col2:
                        # Use session state to maintain dates
                        default_date = due_date + timedelta(days=30*i)
                        if f"parcela_data_{i}" not in st.session_state.payable_installment_dates:
                            st.session_state.payable_installment_dates[f"parcela_data_{i}"] = default_date
                        
                        parcela_date = st.date_input(
                            f"Vencimento Parcela {i+1}", 
                            value=st.session_state.payable_installment_dates[f"parcela_data_{i}"],
                            key=f"parcela_data_{i}"
                        )
                        st.session_state.payable_installment_dates[f"parcela_data_{i}"] = parcela_date
                        installment_dates.append(parcela_date)
            else:
                # Clear session state when installment is unchecked
                if f"payable_installment_values" in st.session_state:
                    st.session_state.payable_installment_values = {}
                if f"payable_installment_dates" in st.session_state:
                    st.session_state.payable_installment_dates = {}

            if st.form_submit_button("💾 Adicionar Conta"):
                if not doc_ref or value <= 0:
                    st.error("Documento e valor são obrigatórios.")
                elif is_installment and sum(installment_values) != value:
                    st.error(f"A soma das parcelas (R$ {sum(installment_values):,.2f}) deve ser igual ao valor total (R$ {value:,.2f}).")
                else:
                    import os
                    xml_file_path = None

                    # Handle PDF file upload
                    if xml_file:
                        upload_dir = "uploads/pdf_files"
                        os.makedirs(upload_dir, exist_ok=True)
                        xml_file_path = os.path.join(upload_dir, f"{doc_ref}_{xml_file.name}")
                        with open(xml_file_path, "wb") as f:
                            f.write(xml_file.getbuffer())

                    with Session(engine) as session:
                        if not is_installment:
                            # Single payment
                            new_payable = Payable(
                                supplier_id=supplier_id,
                                doc_ref=doc_ref,
                                expense_type=expense_type if expense_type else None,
                                empresa=empresa if empresa else None,
                                value=value,
                                due_date=due_date,
                                status=status,
                                notes=notes if notes else None,
                                xml_file_path=xml_file_path,
                                is_installment=False
                            )
                            session.add(new_payable)
                            session.commit()
                            st.success(f"Conta '{doc_ref}' adicionada com sucesso!")
                        else:
                            # Create parent record first
                            parent_payable = Payable(
                                supplier_id=supplier_id,
                                doc_ref=f"{doc_ref} - Controle",
                                expense_type=expense_type if expense_type else None,
                                empresa=empresa if empresa else None,
                                value=value,
                                due_date=due_date,
                                status="Controle",  # Special status for parent record
                                notes=f"Conta parcelada em {installments}x. " + (notes if notes else ""),
                                xml_file_path=xml_file_path,
                                is_installment=False
                            )
                            session.add(parent_payable)
                            session.commit()
                            session.refresh(parent_payable)

                            # Create installment records
                            for i in range(installments):
                                installment_payable = Payable(
                                    supplier_id=supplier_id,
                                    doc_ref=f"{doc_ref} - Parcela {i+1}/{installments}",
                                    expense_type=expense_type if expense_type else None,
                                    empresa=empresa if empresa else None,
                                    value=installment_values[i],
                                    due_date=installment_dates[i],
                                    status=status,
                                    notes=notes if notes else None,
                                    xml_file_path=xml_file_path,
                                    is_installment=True,
                                    installment_number=i+1,
                                    total_installments=installments,
                                    parent_payable_id=parent_payable.id
                                )
                                session.add(installment_payable)

                            session.commit()
                            st.success(f"Conta '{doc_ref}' parcelada em {installments}x adicionada com sucesso!")

                        st.rerun()

with tab2:
    st.subheader("🧾 Contas a Receber")

    # Search field
    search_term_receivable = st.text_input("🔍 Buscar por documento, cliente ou observações:", key="search_receivable")

    # Filters for accounts receivable
    filter_ar_col1, filter_ar_col2, filter_ar_col3, filter_ar_col4, filter_ar_col5 = st.columns(5)

    with filter_ar_col1:
        status_ar_filter = st.selectbox("Status:", ["Todos", "Pendente", "Recebido", "Vencido"], key="ar_status")

    with filter_ar_col2:
        # Get unique customers for filter
        with Session(engine) as session:
            receivables_for_customers = session.exec(select(Receivable.customer_name).distinct()).all()
            customer_options = ["Todos"] + [c for c in receivables_for_customers if c]

        customer_filter = st.selectbox("Cliente:", customer_options, key="ar_customer")

    with filter_ar_col3:
        date_range_ar = st.selectbox("Período:", ["Todos", "Recebe Hoje", "Próximos 7 dias", "Próximos 30 dias", "Atrasados"], key="ar_date_range")

    with filter_ar_col4:
        # Get unique revenue types for filter
        with Session(engine) as session:
            revenue_types = session.exec(select(Receivable.revenue_type).distinct().where(Receivable.revenue_type.isnot(None))).all()
            revenue_type_options = ["Todos"] + [rt for rt in revenue_types if rt]

        revenue_type_filter = st.selectbox("Tipo de Receita:", revenue_type_options)

    with filter_ar_col5:
        value_ar_min = st.number_input("Valor mínimo:", min_value=0.0, value=0.0, step=100.0, key="receivable_min")
        value_ar_max = st.number_input("Valor máximo:", min_value=0.0, value=0.0, step=100.0, key="receivable_max")

    # Get receivables based on filters
    with Session(engine) as session:
        query = select(Receivable).where(Receivable.status != "Controle")  # Exclude control records

        # Apply search filter
        if search_term_receivable:
            search_pattern = f"%{search_term_receivable}%"
            query = query.where(
                (Receivable.doc_ref.ilike(search_pattern)) |
                (Receivable.customer_name.ilike(search_pattern)) |
                (Receivable.notes.ilike(search_pattern))
            )

        # Apply filters
        if status_ar_filter != "Todos":
            if status_ar_filter == "Vencido":
                query = query.where(Receivable.due_date < date.today()).where(Receivable.status == "Pendente")
            else:
                query = query.where(Receivable.status == status_ar_filter)

        if customer_filter != "Todos":
            query = query.where(Receivable.customer_name == customer_filter)

        if revenue_type_filter != "Todos":
            query = query.where(Receivable.revenue_type == revenue_type_filter)

        # Apply value filters
        if value_ar_min > 0:
            query = query.where(Receivable.value >= value_ar_min)
        if value_ar_max > 0:
            query = query.where(Receivable.value <= value_ar_max)

        # Apply date filters
        if date_range_ar == "Recebe Hoje":
            query = query.where(Receivable.due_date == date.today())
        elif date_range_ar == "Próximos 7 dias":
            query = query.where(Receivable.due_date <= date.today() + timedelta(days=7))
            query = query.where(Receivable.due_date >= date.today())
        elif date_range_ar == "Próximos 30 dias":
            query = query.where(Receivable.due_date <= date.today() + timedelta(days=30))
            query = query.where(Receivable.due_date >= date.today())
        elif date_range_ar == "Atrasados":
            query = query.where(Receivable.due_date < date.today())

        receivables = session.exec(query.order_by(Receivable.due_date)).all()

    if receivables:
        receivable_data = []
        total_pending_ar = 0
        total_overdue_ar = 0

        for receivable in receivables:
            days_to_due = (receivable.due_date - date.today()).days

            # Status indicator
            if receivable.status == "Recebido":
                status_icon = "✅"
            elif days_to_due < 0:
                status_icon = "🔴"
                total_overdue_ar += receivable.value
            elif days_to_due <= 7:
                status_icon = "🟡"
            else:
                status_icon = "🟢"

            if receivable.status == "Pendente":
                total_pending_ar += receivable.value

            installment_info = ""
            if receivable.is_installment and receivable.installment_number and receivable.total_installments:
                installment_info = f" ({receivable.installment_number}/{receivable.total_installments})"

            receivable_data.append({
                "ID": receivable.id,
                "Status": status_icon,
                "Cliente": receivable.customer_name or "N/A",
                "Documento": receivable.doc_ref + installment_info,
                "Tipo de Receita": receivable.revenue_type or "N/A",
                "Valor": f"R$ {receivable.value:,.2f}",
                "Vencimento": receivable.due_date.strftime("%d/%m/%Y"),
                "Dias": days_to_due,
                "Status Rec.": receivable.status,
                "PDF": "✅" if receivable.xml_file_path else "❌",
                "Observações": receivable.notes or "N/A"
            })

        # Summary metrics
        if has_permission("manager"):
            metrics_ar_col1, metrics_ar_col2, metrics_ar_col3, metrics_ar_col4 = st.columns(4)

            with metrics_ar_col1:
                st.metric("Total a Receber", f"R$ {total_pending_ar:,.2f}")

            with metrics_ar_col2:
                st.metric("Total Vencido", f"R$ {total_overdue_ar:,.2f}")

            with metrics_ar_col3:
                today_due_ar = sum(r.value for r in receivables if r.due_date == date.today())
                st.metric("Recebe Hoje", f"R$ {today_due_ar:,.2f}")

            with metrics_ar_col4:
                st.metric("Total de Títulos", len(receivable_data))
        else:
            # Operadores veem apenas o total de títulos
            st.metric("Total de Títulos", len(receivable_data))

        # Display table
        st.markdown("### 📋 Lista de Contas a Receber")

        df_ar = pd.DataFrame(receivable_data)

        # Editable table for operators
        if has_permission("operator"):
            edited_df_ar = st.data_editor(
                df_ar,
                hide_index=True,
                use_container_width=True,
                disabled=["ID", "Status", "Cliente", "Documento", "Dias", "PDF"],
                column_config={
                    "Status Rec.": st.column_config.SelectboxColumn(
                        "Status Recebimento",
                        options=["Pendente", "Recebido"],
                        required=True
                    )
                },
                key="receivables_editor"
            )

            # Action buttons for receivables
            action_ar_col1, action_ar_col2, action_ar_col3 = st.columns(3)
            
            with action_ar_col1:
                if st.button("💾 Salvar Alterações", key="save_receivables"):
                    with Session(engine) as session:
                        for idx, row in edited_df_ar.iterrows():
                            receivable = session.get(Receivable, int(row["ID"]))
                            if receivable:
                                receivable.status = row["Status Rec."]
                                receivable.revenue_type = row["Tipo de Receita"] if row["Tipo de Receita"] != "N/A" else None
                                receivable.notes = row["Observações"] if row["Observações"] != "N/A" else None

                        session.commit()
                        st.success("Alterações salvas com sucesso!")
                        st.rerun()

            with action_ar_col2:
                # Edit receivable
                receivable_options = [f"{row['Documento']} - R$ {row['Valor']}" for _, row in df_ar.iterrows()]
                if receivable_options:
                    selected_receivable_option = st.selectbox("Selecionar receita para editar:", [""] + receivable_options, key="edit_receivable_select")
                    
                    if selected_receivable_option and st.button("✏️ Editar Receita"):
                        selected_receivable_id = df_ar[df_ar.apply(lambda x: f"{x['Documento']} - R$ {x['Valor']}" == selected_receivable_option, axis=1)]['ID'].iloc[0]
                        st.session_state.edit_receivable_id = int(selected_receivable_id)
                        st.session_state.show_edit_receivable_form = True

            with action_ar_col3:
                # Delete receivable
                if receivable_options:
                    selected_delete_receivable_option = st.selectbox("Selecionar receita para excluir:", [""] + receivable_options, key="delete_receivable_select")
                    
                    if selected_delete_receivable_option and st.button("🗑️ Excluir Receita"):
                        selected_delete_receivable_id = df_ar[df_ar.apply(lambda x: f"{x['Documento']} - R$ {x['Valor']}" == selected_delete_receivable_option, axis=1)]['ID'].iloc[0]
                        st.session_state.delete_receivable_id = int(selected_delete_receivable_id)
                        st.session_state.show_delete_receivable_confirm = True

            # Edit receivable form
            if st.session_state.get('show_edit_receivable_form') and st.session_state.get('edit_receivable_id'):
                with Session(engine) as session:
                    receivable_to_edit = session.get(Receivable, st.session_state.edit_receivable_id)
                    if receivable_to_edit:
                        st.markdown("---")
                        st.markdown("### ✏️ Editar Conta a Receber")
                        
                        with st.form("edit_receivable_form"):
                            edit_ar_col1, edit_ar_col2 = st.columns(2)
                            
                            with edit_ar_col1:
                                edit_customer_name = st.text_input("Cliente", value=receivable_to_edit.customer_name or "")
                                edit_doc_ref_ar = st.text_input("Documento *", value=receivable_to_edit.doc_ref)
                                edit_revenue_type = st.text_input("Tipo de Receita", value=receivable_to_edit.revenue_type or "")
                                edit_value_ar = st.number_input("Valor *", min_value=0.0, step=0.01, value=float(receivable_to_edit.value))
                            
                            with edit_ar_col2:
                                edit_due_date_ar = st.date_input("Data de Vencimento *", value=receivable_to_edit.due_date)
                                edit_status_ar = st.selectbox("Status", ["Pendente", "Recebido"], 
                                                            index=0 if receivable_to_edit.status == "Pendente" else 1)
                                edit_notes_ar = st.text_area("Observações", value=receivable_to_edit.notes or "")
                            
                            # PDF file upload
                            st.markdown("**Anexar/Atualizar Nota Fiscal (PDF)**")
                            if receivable_to_edit.xml_file_path:
                                st.info(f"PDF atual: {receivable_to_edit.xml_file_path.split('/')[-1]}")
                            edit_xml_file_ar = st.file_uploader(
                                "Selecione o arquivo PDF da nota fiscal (deixe em branco para manter o atual)", 
                                type=['pdf'], 
                                help="Faça upload do arquivo PDF da nota fiscal",
                                key="edit_receivable_pdf"
                            )
                            
                            form_ar_col1, form_ar_col2 = st.columns(2)
                            
                            with form_ar_col1:
                                if st.form_submit_button("💾 Salvar Alterações", use_container_width=True):
                                    if not edit_doc_ref_ar or edit_value_ar <= 0:
                                        st.error("Documento e valor são obrigatórios.")
                                    else:
                                        import os
                                        
                                        # Handle PDF file upload
                                        if edit_xml_file_ar:
                                            upload_dir = "uploads/pdf_files"
                                            os.makedirs(upload_dir, exist_ok=True)
                                            edit_xml_file_path_ar = os.path.join(upload_dir, f"{edit_doc_ref_ar}_{edit_xml_file_ar.name}")
                                            with open(edit_xml_file_path_ar, "wb") as f:
                                                f.write(edit_xml_file_ar.getbuffer())
                                            receivable_to_edit.xml_file_path = edit_xml_file_path_ar
                                        
                                        receivable_to_edit.customer_name = edit_customer_name if edit_customer_name else None
                                        receivable_to_edit.doc_ref = edit_doc_ref_ar
                                        receivable_to_edit.revenue_type = edit_revenue_type if edit_revenue_type else None
                                        receivable_to_edit.value = edit_value_ar
                                        receivable_to_edit.due_date = edit_due_date_ar
                                        receivable_to_edit.status = edit_status_ar
                                        receivable_to_edit.notes = edit_notes_ar if edit_notes_ar else None
                                        
                                        session.commit()
                                        st.success("Conta a receber atualizada com sucesso!")
                                        st.session_state.show_edit_receivable_form = False
                                        st.rerun()
                            
                            with form_ar_col2:
                                if st.form_submit_button("❌ Cancelar", use_container_width=True):
                                    st.session_state.show_edit_receivable_form = False
                                    st.rerun()

            # Delete receivable confirmation
            if st.session_state.get('show_delete_receivable_confirm') and st.session_state.get('delete_receivable_id'):
                with Session(engine) as session:
                    receivable_to_delete = session.get(Receivable, st.session_state.delete_receivable_id)
                    if receivable_to_delete:
                        st.markdown("---")
                        st.markdown("### ⚠️ Confirmar Exclusão de Conta a Receber")
                        st.warning(f"Tem certeza que deseja excluir a receita **{receivable_to_delete.doc_ref}** no valor de **R$ {receivable_to_delete.value:,.2f}**?")
                        
                        # Check if this is a parent record (has children)
                        children_ar = session.exec(select(Receivable).where(Receivable.parent_receivable_id == receivable_to_delete.id)).all()
                        if children_ar:
                            st.warning(f"⚠️ Esta receita possui {len(children_ar)} parcelas que também serão excluídas!")
                        
                        st.error("**ATENÇÃO:** Esta ação não pode ser desfeita!")
                        
                        delete_ar_col1, delete_ar_col2 = st.columns(2)
                        
                        with delete_ar_col1:
                            if st.button("🗑️ Sim, Excluir", use_container_width=True, type="primary", key="confirm_delete_receivable"):
                                try:
                                    # Refresh the receivable object to ensure we have the latest data
                                    session.refresh(receivable_to_delete)
                                    
                                    # Check if this receivable is a child (installment) of another receivable
                                    if receivable_to_delete.parent_receivable_id:
                                        # This is a child installment, just delete it
                                        session.delete(receivable_to_delete)
                                        session.commit()
                                        st.success(f"Parcela '{receivable_to_delete.doc_ref}' excluída com sucesso!")
                                    else:
                                        # This might be a parent, check for children first
                                        children_ar = session.exec(select(Receivable).where(Receivable.parent_receivable_id == receivable_to_delete.id)).all()
                                        
                                        # Delete all children (installments) first to avoid foreign key constraint
                                        for child in children_ar:
                                            session.delete(child)
                                        
                                        # Commit the children deletions first
                                        session.commit()
                                        
                                        # Now delete the parent
                                        session.delete(receivable_to_delete)
                                        session.commit()
                                        
                                        if children_ar:
                                            st.success(f"Receita '{receivable_to_delete.doc_ref}' e suas {len(children_ar)} parcelas foram excluídas com sucesso!")
                                        else:
                                            st.success(f"Receita '{receivable_to_delete.doc_ref}' excluída com sucesso!")
                                    
                                    st.session_state.show_delete_receivable_confirm = False
                                    st.rerun()
                                    
                                except Exception as e:
                                    st.error(f"Erro ao excluir receita: {str(e)}")
                                    session.rollback()
                        
                        with delete_ar_col2:
                            if st.button("❌ Cancelar", use_container_width=True, key="cancel_delete_receivable"):
                                st.session_state.show_delete_receivable_confirm = False
                                st.rerun()
        else:
            st.dataframe(df_ar, hide_index=True, use_container_width=True)

    else:
        st.info("Nenhuma conta a receber encontrada com os filtros aplicados.")

    # Add new receivable
    if has_permission("operator"):
        st.markdown("---")
        st.subheader("➕ Adicionar Conta a Receber")

        with st.form("new_receivable"):
            receivable_col1, receivable_col2 = st.columns(2)

            with receivable_col1:
                customer_name = st.text_input("Cliente", placeholder="Nome do cliente")
                doc_ref_ar = st.text_input("Documento *", placeholder="NF, Fatura, etc.")
                revenue_type = st.text_input("Tipo de Receita", placeholder="Categoria da receita")
                empresa_ar = st.text_input("Empresa", placeholder="Nome da empresa recebedora")
                value_ar = st.number_input("Valor *", min_value=0.0, step=0.01)

            with receivable_col2:
                due_date_ar = st.date_input("Data de Vencimento *", value=date.today() + timedelta(days=30))
                status_ar = st.selectbox("Status", ["Pendente", "Recebido"], key="new_receivable_status")
                notes_ar = st.text_area("Observações", placeholder="Observações adicionais")

            # PDF file upload
            st.markdown("**Anexar Nota Fiscal (PDF)**")
            xml_file_ar = st.file_uploader(
                "Selecione o arquivo PDF da nota fiscal", 
                type=['pdf'], 
                help="Faça upload do arquivo PDF da nota fiscal",
                key="receivable_pdf"
            )

            # Installment options
            st.markdown("**Parcelamento**")
            
            # Check previous state to detect changes
            prev_installment_ar_state = st.session_state.get("prev_receivable_installment", False)
            is_installment_ar = st.checkbox("Esta receita será parcelada?", key="receivable_installment_checkbox")

            # If state changed, update session state and rerun
            if is_installment_ar != prev_installment_ar_state:
                st.session_state.prev_receivable_installment = is_installment_ar
                st.rerun()

            installments_ar = 1
            installment_values_ar = []
            installment_dates_ar = []

            if is_installment_ar:
                installments_ar = st.number_input("Número de Parcelas", min_value=2, max_value=24, value=2, key="receivable_installment_count")

                st.markdown("**Configurar Parcelas**")

                # Initialize session state for receivable installment values if not exists
                if f"receivable_installment_values" not in st.session_state:
                    st.session_state.receivable_installment_values = {}
                if f"receivable_installment_dates" not in st.session_state:
                    st.session_state.receivable_installment_dates = {}

                for i in range(installments_ar):
                    parcela_col1, parcela_col2 = st.columns(2)
                    with parcela_col1:
                        # Use session state to maintain values
                        default_value_ar = value_ar/installments_ar if value_ar > 0 else 0.0
                        if f"parcela_valor_ar_{i}" not in st.session_state.receivable_installment_values:
                            st.session_state.receivable_installment_values[f"parcela_valor_ar_{i}"] = default_value_ar
                        
                        parcela_value = st.number_input(
                            f"Valor da Parcela {i+1}",
                            min_value=0.0,
                            step=0.01,
                            value=st.session_state.receivable_installment_values[f"parcela_valor_ar_{i}"],
                            key=f"parcela_valor_ar_{i}"
                        )
                        st.session_state.receivable_installment_values[f"parcela_valor_ar_{i}"] = parcela_value
                        installment_values_ar.append(parcela_value)
                    
                    with parcela_col2:
                        # Use session state to maintain dates
                        default_date_ar = due_date_ar + timedelta(days=30*i)
                        if f"parcela_data_ar_{i}" not in st.session_state.receivable_installment_dates:
                            st.session_state.receivable_installment_dates[f"parcela_data_ar_{i}"] = default_date_ar
                        
                        parcela_date = st.date_input(
                            f"Vencimento Parcela {i+1}",
                            value=st.session_state.receivable_installment_dates[f"parcela_data_ar_{i}"],
                            key=f"parcela_data_ar_{i}"
                        )
                        st.session_state.receivable_installment_dates[f"parcela_data_ar_{i}"] = parcela_date
                        installment_dates_ar.append(parcela_date)
            else:
                # Clear session state when installment is unchecked
                if f"receivable_installment_values" in st.session_state:
                    st.session_state.receivable_installment_values = {}
                if f"receivable_installment_dates" in st.session_state:
                    st.session_state.receivable_installment_dates = {}

            if st.form_submit_button("💾 Adicionar Receita"):
                if not doc_ref_ar or value_ar <= 0:
                    st.error("Documento e valor são obrigatórios para contas a receber.")
                elif is_installment_ar and abs(sum(installment_values_ar) - value_ar) > 0.01:
                    st.error(f"A soma das parcelas (R$ {sum(installment_values_ar):,.2f}) deve ser igual ao valor total (R$ {value_ar:,.2f}).")
                else:
                    import os
                    xml_file_path_ar = None

                    # Handle PDF file upload
                    if xml_file_ar:
                        upload_dir = "uploads/pdf_files"
                        os.makedirs(upload_dir, exist_ok=True)
                        xml_file_path_ar = os.path.join(upload_dir, f"{doc_ref_ar}_{xml_file_ar.name}")
                        with open(xml_file_path_ar, "wb") as f:
                            f.write(xml_file_ar.getbuffer())

                    with Session(engine) as session:
                        if not is_installment_ar:
                            # Single payment
                            new_receivable = Receivable(
                                customer_name=customer_name if customer_name else None,
                                doc_ref=doc_ref_ar,
                                revenue_type=revenue_type if revenue_type else None,
                                empresa=empresa_ar if empresa_ar else None,
                                value=value_ar,
                                due_date=due_date_ar,
                                status=status_ar,
                                notes=notes_ar if notes_ar else None,
                                xml_file_path=xml_file_path_ar,
                                is_installment=False
                            )
                            session.add(new_receivable)
                            session.commit()
                            st.success(f"Receita '{doc_ref_ar}' adicionada com sucesso!")
                        else:
                            # Create parent record first
                            parent_receivable = Receivable(
                                customer_name=customer_name if customer_name else None,
                                doc_ref=f"{doc_ref_ar} - Controle",
                                revenue_type=revenue_type if revenue_type else None,
                                empresa=empresa_ar if empresa_ar else None,
                                value=value_ar,
                                due_date=due_date_ar,
                                status="Controle",  # Special status for parent record
                                notes=f"Receita parcelada em {installments_ar}x. " + (notes_ar if notes_ar else ""),
                                xml_file_path=xml_file_path_ar,
                                is_installment=False
                            )
                            session.add(parent_receivable)
                            session.commit()
                            session.refresh(parent_receivable)

                            # Create installment records
                            for i in range(installments_ar):
                                installment_receivable = Receivable(
                                    customer_name=customer_name if customer_name else None,
                                    doc_ref=f"{doc_ref_ar} - Parcela {i+1}/{installments_ar}",
                                    revenue_type=revenue_type if revenue_type else None,
                                    empresa=empresa_ar if empresa_ar else None,
                                    value=installment_values_ar[i],
                                    due_date=installment_dates_ar[i],
                                    status=status_ar,
                                    notes=notes_ar if notes_ar else None,
                                    xml_file_path=xml_file_path_ar,
                                    is_installment=True,
                                    installment_number=i+1,
                                    total_installments=installments_ar,
                                    parent_receivable_id=parent_receivable.id
                                )
                                session.add(installment_receivable)

                            session.commit()
                            st.success(f"Receita '{doc_ref_ar}' parcelada em {installments_ar}x adicionada com sucesso!")

                        st.rerun()

if tab3:  # Only available for managers
    with tab3:
        st.subheader("📊 Fluxo de Caixa")

    # Date range for cash flow
    flow_col1, flow_col2 = st.columns(2)

    with flow_col1:
        flow_start = st.date_input("Data Início:", value=date.today())

    with flow_col2:
        flow_end = st.date_input("Data Fim:", value=date.today() + timedelta(days=90))

    # Generate cash flow projection
    with Session(engine) as session:
        # Exclude control records (parent records with status "Controle")
        payables_in_period = session.exec(
            select(Payable)
            .where(Payable.due_date >= flow_start)
            .where(Payable.due_date <= flow_end)
            .where(Payable.status != "Controle")
        ).all()

        # Get receivables in period (exclude control records)
        receivables_in_period = session.exec(
            select(Receivable)
            .where(Receivable.due_date >= flow_start)
            .where(Receivable.due_date <= flow_end)
            .where(Receivable.status != "Controle")
        ).all()

        if payables_in_period or receivables_in_period:
            # Group by date
            cash_flow = {}
            current_date = flow_start

            while current_date <= flow_end:
                cash_flow[current_date] = {"outflow": 0, "inflow": 0, "count_out": 0, "count_in": 0}
                current_date += timedelta(days=1)

            # Add payables to cash flow
            for payable in payables_in_period:
                if payable.due_date in cash_flow:
                    cash_flow[payable.due_date]["outflow"] += payable.value
                    cash_flow[payable.due_date]["count_out"] += 1

            # Add receivables to cash flow (placeholder)
            for receivable in receivables_in_period:
                if receivable.due_date in cash_flow:
                    cash_flow[receivable.due_date]["inflow"] += receivable.value
                    cash_flow[receivable.due_date]["count_in"] += 1

            # Convert to DataFrame
            flow_data = []
            cumulative_outflow = 0
            cumulative_inflow = 0
            net_flow = 0

            for date_key, data in cash_flow.items():
                cumulative_outflow += data["outflow"]
                cumulative_inflow += data["inflow"]
                net_flow = cumulative_inflow - cumulative_outflow

                flow_data.append({
                    "Data": date_key,
                    "Saídas": data["outflow"],
                    "Entradas": data["inflow"],
                    "Títulos Pagos": data["count_out"],
                    "Títulos Recebidos": data["count_in"],
                    "Saldo Acumulado": net_flow
                })

            flow_df = pd.DataFrame(flow_data)

            # Filter only days with movement or weekly summary
            view_type = st.radio("Visualização:", ["Apenas com movimento", "Resumo semanal", "Todos os dias"])

            if view_type == "Apenas com movimento":
                flow_df = flow_df[
                    (flow_df["Saídas"] > 0) | 
                    (flow_df["Entradas"] > 0)
                ]
            elif view_type == "Resumo semanal":
                # Group by week - convert Data column to datetime first
                flow_df["Data"] = pd.to_datetime(flow_df["Data"])
                flow_df["Semana"] = flow_df["Data"].dt.strftime("%Y-W%U")
                weekly_flow = flow_df.groupby("Semana").agg({
                    "Saídas": "sum",
                    "Entradas": "sum",
                    "Títulos Pagos": "sum",
                    "Títulos Recebidos": "sum",
                    "Saldo Acumulado": "last" # Taking the last accumulated balance of the week
                }).reset_index()
                flow_df = weekly_flow

            # Display cash flow
            if not flow_df.empty:
                st.markdown("### 💸 Projeção de Fluxo de Caixa")

                # Summary metrics
                flow_metrics_col1, flow_metrics_col2, flow_metrics_col3 = st.columns(3)

                with flow_metrics_col1:
                    total_outflow = flow_df["Saídas"].sum()
                    st.metric("Total Saídas", f"R$ {total_outflow:,.2f}")

                with flow_metrics_col2:
                    total_inflow = flow_df["Entradas"].sum()
                    st.metric("Total Entradas", f"R$ {total_inflow:,.2f}")

                with flow_metrics_col3:
                    net_total = total_inflow - total_outflow
                    st.metric("Saldo Líquido", f"R$ {net_total:,.2f}")


                # Cash flow chart
                import plotly.express as px

                # Melt DataFrame for easier plotting with Plotly
                if view_type != "Resumo semanal":
                    melted_flow_df = flow_df.melt(id_vars=["Data"], value_vars=["Saídas", "Entradas"],
                                                var_name="Tipo", value_name="Valor")
                    fig_flow = px.bar(melted_flow_df, x="Data", y="Valor", color="Tipo",
                                      title="Fluxo de Caixa Projetado",
                                      color_discrete_map={'Saídas': 'red', 'Entradas': 'green'})
                else:
                    melted_flow_df = flow_df.melt(id_vars=["Semana"], value_vars=["Saídas", "Entradas"],
                                                var_name="Tipo", value_name="Valor")
                    fig_flow = px.bar(melted_flow_df, x="Semana", y="Valor", color="Tipo",
                                      title="Fluxo de Caixa Semanal",
                                      color_discrete_map={'Saídas': 'red', 'Entradas': 'green'})

                st.plotly_chart(fig_flow, use_container_width=True)

                # Data table
                if view_type != "Resumo semanal":
                    display_df = flow_df.copy()
                    if "Data" in display_df.columns:
                        display_df["Data"] = pd.to_datetime(display_df["Data"]).dt.strftime("%d/%m/%Y")
                    display_df["Saídas"] = display_df["Saídas"].apply(lambda x: f"R$ {x:,.2f}")
                    display_df["Entradas"] = display_df["Entradas"].apply(lambda x: f"R$ {x:,.2f}")
                    display_df["Saldo Acumulado"] = display_df["Saldo Acumulado"].apply(lambda x: f"R$ {x:,.2f}")

                    st.dataframe(display_df, hide_index=True, use_container_width=True)
                else:
                    display_df = flow_df.copy()
                    display_df["Saídas"] = display_df["Saídas"].apply(lambda x: f"R$ {x:,.2f}")
                    display_df["Entradas"] = display_df["Entradas"].apply(lambda x: f"R$ {x:,.2f}")
                    display_df["Saldo Acumulado"] = display_df["Saldo Acumulado"].apply(lambda x: f"R$ {x:,.2f}")

                    st.dataframe(display_df, hide_index=True, use_container_width=True)
            else:
                st.info("Nenhuma movimentação no período selecionado.")
        else:
            st.info("Nenhuma conta a pagar ou a receber no período selecionado.")

if tab4:  # Only available for managers
    with tab4:
        st.subheader("📈 Análises Financeiras")

    # Monthly analysis
    with Session(engine) as session:
        # Exclude control records from analysis
        all_payables = session.exec(select(Payable).where(Payable.status != "Controle")).all()
        all_receivables = session.exec(select(Receivable).where(Receivable.status != "Controle")).all()

        if all_payables or all_receivables:
            # Group by month for payables
            monthly_analysis_payables = {}
            for payable in all_payables:
                month_key = payable.due_date.strftime("%Y-%m")
                if month_key not in monthly_analysis_payables:
                    monthly_analysis_payables[month_key] = {"total": 0, "paid": 0, "pending": 0, "count": 0, "suppliers": set()}
                monthly_analysis_payables[month_key]["total"] += payable.value
                monthly_analysis_payables[month_key]["count"] += 1
                if payable.status == "Pago": monthly_analysis_payables[month_key]["paid"] += payable.value
                else: monthly_analysis_payables[month_key]["pending"] += payable.value
                if payable.supplier_id:
                    supplier = session.get(Supplier, payable.supplier_id)
                    if supplier: monthly_analysis_payables[month_key]["suppliers"].add(supplier.name)

            # Group by month for receivables
            monthly_analysis_receivables = {}
            for receivable in all_receivables:
                month_key = receivable.due_date.strftime("%Y-%m")
                if month_key not in monthly_analysis_receivables:
                    monthly_analysis_receivables[month_key] = {"total": 0, "received": 0, "pending": 0, "count": 0, "customers": set()}
                monthly_analysis_receivables[month_key]["total"] += receivable.value
                monthly_analysis_receivables[month_key]["count"] += 1
                if receivable.status == "Recebido": 
                    monthly_analysis_receivables[month_key]["received"] += receivable.value
                else: 
                    monthly_analysis_receivables[month_key]["pending"] += receivable.value
                if receivable.customer_name:
                    monthly_analysis_receivables[month_key]["customers"].add(receivable.customer_name)

            # Combine and display monthly analysis
            st.markdown("### 📊 Análise Mensal de Despesas")
            if monthly_analysis_payables:
                monthly_data = []
                for month, data in monthly_analysis_payables.items():
                    monthly_data.append({
                        "Mês": month, "Total": data["total"], "Pago": data["paid"],
                        "Pendente": data["pending"], "Títulos": data["count"],
                        "Fornecedores": len(data["suppliers"])
                    })
                monthly_df = pd.DataFrame(monthly_data).sort_values("Mês")

                fig_monthly = go.Figure()
                fig_monthly.add_trace(go.Bar(x=monthly_df["Mês"], y=monthly_df["Pago"], name="Pago"))
                fig_monthly.add_trace(go.Bar(x=monthly_df["Mês"], y=monthly_df["Pendente"], name="Pendente"))
                fig_monthly.update_layout(title="Análise Mensal de Pagamentos", barmode="stack")
                st.plotly_chart(fig_monthly, use_container_width=True)

                display_monthly = monthly_df.copy()
                display_monthly["Total"] = display_monthly["Total"].apply(lambda x: f"R$ {x:,.2f}")
                display_monthly["Pago"] = display_monthly["Pago"].apply(lambda x: f"R$ {x:,.2f}")
                display_monthly["Pendente"] = display_monthly["Pendente"].apply(lambda x: f"R$ {x:,.2f}")
                st.dataframe(display_df, hide_index=True, use_container_width=True)
            else:
                st.info("Nenhum dado de despesa mensal disponível.")

            # Monthly receivables analysis
            st.markdown("### 📊 Análise Mensal de Receitas")
            if monthly_analysis_receivables:
                monthly_data_ar = []
                for month, data in monthly_analysis_receivables.items():
                    monthly_data_ar.append({
                        "Mês": month, "Total": data["total"], "Recebido": data["received"],
                        "Pendente": data["pending"], "Títulos": data["count"],
                        "Clientes": len(data["customers"])
                    })
                monthly_df_ar = pd.DataFrame(monthly_data_ar).sort_values("Mês")

                import plotly.graph_objects as go
                fig_monthly_ar = go.Figure()
                fig_monthly_ar.add_trace(go.Bar(x=monthly_df_ar["Mês"], y=monthly_df_ar["Recebido"], name="Recebido"))
                fig_monthly_ar.add_trace(go.Bar(x=monthly_df_ar["Mês"], y=monthly_df_ar["Pendente"], name="Pendente"))
                fig_monthly_ar.update_layout(title="Análise Mensal de Recebimentos", barmode="stack")
                st.plotly_chart(fig_monthly_ar, use_container_width=True)

                display_monthly_ar = monthly_df_ar.copy()
                display_monthly_ar["Total"] = display_monthly_ar["Total"].apply(lambda x: f"R$ {x:,.2f}")
                display_monthly_ar["Recebido"] = display_monthly_ar["Recebido"].apply(lambda x: f"R$ {x:,.2f}")
                display_monthly_ar["Pendente"] = display_monthly_ar["Pendente"].apply(lambda x: f"R$ {x:,.2f}")
                st.dataframe(display_monthly_ar, hide_index=True, use_container_width=True)
            else:
                st.info("Nenhum dado de receita mensal disponível.")


    # Supplier analysis
    st.markdown("---")
    st.markdown("### 🏭 Análise por Fornecedor")
    supplier_analysis = {}
    with Session(engine) as session:
        # Use filtered payables (already excludes control records)
        for payable in all_payables:
            supplier_name = "Não Informado"
            if payable.supplier_id:
                supplier = session.get(Supplier, payable.supplier_id)
                supplier_name = supplier.name if supplier else "Não Informado"
            if supplier_name not in supplier_analysis:
                supplier_analysis[supplier_name] = {"total": 0, "paid": 0, "pending": 0, "count": 0, "overdue": 0}
            supplier_analysis[supplier_name]["total"] += payable.value
            supplier_analysis[supplier_name]["count"] += 1
            if payable.status == "Pago": supplier_analysis[supplier_name]["paid"] += payable.value
            else:
                supplier_analysis[supplier_name]["pending"] += payable.value
                if payable.due_date < date.today(): supplier_analysis[supplier_name]["overdue"] += payable.value

    if supplier_analysis:
        supplier_data = []
        for supplier, data in supplier_analysis.items():
            payment_rate = (data["paid"] / data["total"] * 100) if data["total"] > 0 else 0
            supplier_data.append({
                "Fornecedor": supplier, "Valor Total": f"R$ {data['total']:,.2f}",
                "Pago": f"R$ {data['paid']:,.2f}", "Pendente": f"R$ {data['pending']:,.2f}",
                "Vencido": f"R$ {data['overdue']:,.2f}", "Títulos": data["count"],
                "% Pago": f"{payment_rate:.1f}%"
            })
        supplier_df = pd.DataFrame(supplier_data)
        supplier_df['_total_numeric'] = [data['total'] for data in supplier_analysis.values()]
        supplier_df = supplier_df.sort_values("_total_numeric", ascending=False).drop('_total_numeric', axis=1)
        st.dataframe(supplier_df, hide_index=True, use_container_width=True)
    else:
        st.info("Nenhum dado de fornecedor disponível.")

    # Customer analysis
    st.markdown("---")
    st.markdown("### 👥 Análise por Cliente")
    customer_analysis = {}
    with Session(engine) as session:
        # Use filtered receivables (already excludes control records)
        for receivable in all_receivables:
            customer_name = receivable.customer_name or "Não Informado"
            if customer_name not in customer_analysis:
                customer_analysis[customer_name] = {"total": 0, "received": 0, "pending": 0, "count": 0, "overdue": 0}
            customer_analysis[customer_name]["total"] += receivable.value
            customer_analysis[customer_name]["count"] += 1
            if receivable.status == "Recebido": 
                customer_analysis[customer_name]["received"] += receivable.value
            else:
                customer_analysis[customer_name]["pending"] += receivable.value
                if receivable.due_date < date.today(): 
                    customer_analysis[customer_name]["overdue"] += receivable.value

    if customer_analysis:
        customer_data = []
        for customer, data in customer_analysis.items():
            payment_rate = (data["received"] / data["total"] * 100) if data["total"] > 0 else 0
            customer_data.append({
                "Cliente": customer, "Valor Total": f"R$ {data['total']:,.2f}",
                "Recebido": f"R$ {data['received']:,.2f}", "Pendente": f"R$ {data['pending']:,.2f}",
                "Vencido": f"R$ {data['overdue']:,.2f}", "Títulos": data["count"],
                "% Recebido": f"{payment_rate:.1f}%"
            })
        customer_df = pd.DataFrame(customer_data)
        customer_df['_total_numeric'] = [data['total'] for data in customer_analysis.values()]
        customer_df = customer_df.sort_values("_total_numeric", ascending=False).drop('_total_numeric', axis=1)
        st.dataframe(customer_df, hide_index=True, use_container_width=True)
    else:
        st.info("Nenhum dado de cliente disponível.")

    # Budget alerts
    st.markdown("---")
    st.markdown("### ⚠️ Alertas Financeiros")

    alert_col1, alert_col2, alert_col3 = st.columns(3)

    with alert_col1:
        # Placeholder for budget execution rate
        st.info("Alerta de execução orçamentária (a implementar)")

    with alert_col2:
        # Use filtered data (already excludes control records)
        overdue_value = sum(p.value for p in all_payables if p.due_date < date.today() and p.status == "Pendente")
        if overdue_value > 0:
            st.error(f"🔴 R$ {overdue_value:,.2f} em atraso (Contas a Pagar)")
        else:
            st.success("✅ Nenhum título a pagar em atraso")
        # Add alert for overdue receivables
        overdue_receivables_value = sum(r.value for r in all_receivables if r.due_date < date.today() and r.status == "Pendente")
        if overdue_receivables_value > 0:
            st.error(f"🔴 R$ {overdue_receivables_value:,.2f} em atraso (Contas a Receber)")
        else:
            st.success("✅ Nenhum título a receber em atraso")

    with alert_col3:
        # Use filtered data (already excludes control records)
        upcoming_week = sum(p.value for p in all_payables
                           if date.today() <= p.due_date <= date.today() + timedelta(days=7)
                           and p.status == "Pendente")
        if upcoming_week > 0:
            st.warning(f"🟡 R$ {upcoming_week:,.2f} a pagar vence em 7 dias")
        else:
            st.success("✅ Nenhum título a pagar vencendo")
        # Add alert for upcoming receivables
        upcoming_receivables = sum(r.value for r in all_receivables
                                   if date.today() <= r.due_date <= date.today() + timedelta(days=7)
                                   and r.status == "Pendente")
        if upcoming_receivables > 0:
            st.warning(f"🟡 R$ {upcoming_receivables:,.2f} a receber vence em 7 dias")
        else:
            st.success("✅ Nenhum título a receber vencendo")


if tab5:  # Only available for managers
    with tab5:
        st.subheader("💹 Orçamento e Planejamento")

    # Budget planning
    current_year = date.today().year
    current_month = date.today().month

    budget_col1, budget_col2 = st.columns(2)

    with budget_col1:
        selected_year = st.selectbox("Ano:", [current_year - 1, current_year, current_year + 1], index=1)

    with budget_col2:
        selected_month = st.selectbox("Mês:", list(range(1, 13)), index=current_month - 1,
                                    format_func=lambda x: calendar.month_name[x])

    # Current month analysis
    with Session(engine) as session:
        month_start = date(selected_year, selected_month, 1)

        # Calculate last day of month
        if selected_month == 12:
            month_end = date(selected_year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(selected_year, selected_month + 1, 1) - timedelta(days=1)

        month_payables = session.exec(
            select(Payable)
            .where(Payable.due_date >= month_start)
            .where(Payable.due_date <= month_end)
            .where(Payable.status != "Controle")  # Exclude control records
        ).all()

        # Placeholder for receivables in the selected month
        # month_receivables = session.exec(
        #     select(Receivable)
        #     .where(Receivable.due_date >= month_start)
        #     .where(Receivable.due_date <= month_end)
        # ).all()

        # Calculate metrics for payables
        total_budgeted = sum(p.value for p in month_payables)
        paid_amount = sum(p.value for p in month_payables if p.status == "Pago")
        pending_amount = sum(p.value for p in month_payables if p.status == "Pendente")

        # Calculate metrics for receivables (placeholder)
        # total_budgeted_ar = sum(r.value for r in month_receivables)
        # received_amount_ar = sum(r.value for r in month_receivables if r.status == "Recebido")
        # pending_amount_ar = sum(r.value for r in month_receivables if r.status == "Pendente")


        # Budget metrics for payables
        budget_metrics_col1, budget_metrics_col2, budget_metrics_col3, budget_metrics_col4 = st.columns(4)

        with budget_metrics_col1:
            st.metric("Orçado (Despesas)", f"R$ {total_budgeted:,.2f}")

        with budget_metrics_col2:
            st.metric("Realizado (Despesas)", f"R$ {paid_amount:,.2f}")

        with budget_metrics_col3:
            st.metric("Pendente (Despesas)", f"R$ {pending_amount:,.2f}")

        with budget_metrics_col4:
            execution_rate = (paid_amount / total_budgeted * 100) if total_budgeted > 0 else 0
            st.metric("% Execução (Despesas)", f"{execution_rate:.1f}%")

        # Placeholder for budget metrics for receivables
        # budget_metrics_ar_col1, budget_metrics_ar_col2, budget_metrics_ar_col3, budget_metrics_ar_col4 = st.columns(4)
        # with budget_metrics_ar_col1: st.metric("Orçado (Receitas)", f"R$ {total_budgeted_ar:,.2f}")
        # with budget_metrics_ar_col2: st.metric("Realizado (Receitas)", f"R$ {received_amount_ar:,.2f}")
        # with budget_metrics_ar_col3: st.metric("Pendente (Receitas)", f"R$ {pending_amount_ar:,.2f}")
        # with budget_metrics_ar_col4:
        #     execution_rate_ar = (received_amount_ar / total_budgeted_ar * 100) if total_budgeted_ar > 0 else 0
        #     st.metric("% Execução (Receitas)", f"{execution_rate_ar:.1f}%")


        # Budget breakdown by cost center for payables
        if month_payables:
            st.markdown(f"### 📊 Detalhamento de Despesas - {calendar.month_name[selected_month]}/{selected_year}")

            expense_type_analysis = {}
            for payable in month_payables:
                expense_type = payable.expense_type or "Não Classificado"
                if expense_type not in expense_type_analysis:
                    expense_type_analysis[expense_type] = {"total": 0, "paid": 0, "pending": 0}
                expense_type_analysis[expense_type]["total"] += payable.value
                if payable.status == "Pago": expense_type_analysis[expense_type]["paid"] += payable.value
                else: expense_type_analysis[expense_type]["pending"] += payable.value

            expense_data = []
            for expense_type, data in expense_type_analysis.items():
                execution = (data["paid"] / data["total"] * 100) if data["total"] > 0 else 0
                expense_data.append({
                    "Tipo de Gasto": expense_type,
                    "Orçado": f"R$ {data['total']:,.2f}", "Realizado": f"R$ {data['paid']:,.2f}",
                    "Pendente": f"R$ {data['pending']:,.2f}", "% Execução": f"{execution:.1f}%"
                })
            expense_df = pd.DataFrame(expense_data)
            st.dataframe(expense_df, hide_index=True, use_container_width=True)

            # Budget chart for payables
            chart_data = []
            for expense_type, data in expense_type_analysis.items():
                chart_data.append({"Tipo": expense_type, "Valor": data["total"]})
            if chart_data:
                chart_df = pd.DataFrame(chart_data)
                fig_budget = px.pie(chart_df, values="Valor", names="Tipo",
                                  title="Distribuição Orçamentária por Tipo de Gasto")
                st.plotly_chart(fig_budget, use_container_width=True)
        else:
            st.info(f"Nenhuma despesa orçada para {calendar.month_name[selected_month]}/{selected_year}.")

        # Placeholder for budget breakdown by customer/revenue type for receivables
        # st.markdown(f"### 📊 Detalhamento de Receitas - {calendar.month_name[selected_month]}/{selected_year}")
        # if month_receivables:
        #     # Similar processing and display as expense_type_analysis
        #     st.info("Detalhamento de receitas a ser implementado.")
        # else:
        #     st.info(f"Nenhuma receita orçada para {calendar.month_name[selected_month]}/{selected_year}.")


    # Alerts (already have some alerts, could add more specific to budget execution)
    st.markdown("---")
    st.markdown("### ⚠️ Alertas Orçamentários")

    alert_budget_col1, alert_budget_col2 = st.columns(2)

    with alert_budget_col1:
        if execution_rate > 90: st.success("✅ Execução orçamentária dentro do planejado")
        elif execution_rate > 70: st.warning("⚠️ Execução orçamentária acima da média")
        else: st.info("📊 Execução orçamentária normal")

    with alert_budget_col2:
        overdue_value = sum(p.value for p in month_payables if p.due_date < date.today() and p.status == "Pendente")
        if overdue_value > 0: st.error(f"🔴 R$ {overdue_value:,.2f} em atraso")
        else: st.success("✅ Nenhum título em atraso")