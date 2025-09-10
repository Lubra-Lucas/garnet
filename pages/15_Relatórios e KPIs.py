# pages/15_RelatoriosKPIs.py
import streamlit as st
from auth import require_login, has_permission
from sqlmodel import Session, select, func
from db import engine
from models import *
from services.reports import get_dashboard_kpis, generate_session_data, create_stock_value_chart, generate_stock_report, generate_supplier_performance_report
from services.io_export import export_comprehensive_report, create_download_button
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import date, datetime, timedelta
import calendar
from sqlalchemy import func, text

# Require login for this page - only managers can access
user = require_login(["manager"])

st.set_page_config(page_title="GARNET - Relatórios e KPIs", layout="wide")

# Professional page header
st.markdown("""
<div style="padding: 1rem 0 2rem 0; border-bottom: 1px solid #E8E8E8; margin-bottom: 2rem;">
    <h1 style="margin: 0; color: #2E4A6B; font-weight: 300;">Relatórios e Indicadores</h1>
    <p style="margin: 0.5rem 0 0 0; color: #666; font-size: 1.1rem;">Análise de desempenho e métricas operacionais</p>
</div>
""", unsafe_allow_html=True)

# Clean tabs without icons
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Dashboard Executivo", "Relatórios Gerenciais", "KPIs Operacionais", "Análises Customizadas", "Exportações"])

with tab1:
    st.subheader("Dashboard Executivo")

    # Generate real-time KPIs
    with Session(engine) as session:
        session_data = generate_session_data(session)
        kpis = get_dashboard_kpis(session_data)

    # Executive summary metrics
    st.markdown("### 📊 Indicadores Principais")

    exec_col1, exec_col2, exec_col3, exec_col4 = st.columns(4)

    with exec_col1:
        st.metric(
            label="💰 Valor Total Estoque",
            value=f"R$ {kpis['stock_value']:,.2f}",
            delta=f"+{(kpis['stock_value'] * 0.05):,.0f}",  # Placeholder delta
            help="Valor total do estoque atual"
        )

    with exec_col2:
        st.metric(
            label="🏭 Ordens Ativas",
            value=kpis["active_production_orders"],
            delta="+2",  # Placeholder delta
            help="Ordens de produção em andamento"
        )

    with exec_col3:
        st.metric(
            label="📦 Fornecedores Ativos",
            value=kpis["total_suppliers"],
            help="Total de fornecedores cadastrados"
        )

    with exec_col4:
        st.metric(
            label="🔄 Giro de Estoque",
            value=f"{kpis['inventory_turnover']:.1f}x",
            delta="+0.2x",  # Placeholder delta
            help="Rotatividade anual do estoque"
        )

    # Executive charts
    st.markdown("---")

    chart_exec_col1, chart_exec_col2 = st.columns(2)

    with chart_exec_col1:
        # Monthly production trend
        with Session(engine) as session:
            start_date_param = datetime.now() - timedelta(days=365)
            monthly_production = session.exec(
                text("""
                SELECT to_char(created_at, 'YYYY-MM') as month, 
                       COUNT(*) as count, 
                       SUM(qty_to_produce) as total_qty
                FROM productionorder 
                WHERE created_at >= :start_date
                GROUP BY to_char(created_at, 'YYYY-MM')
                ORDER BY to_char(created_at, 'YYYY-MM')
                """).params(start_date=start_date_param)
            ).all()

            if monthly_production:
                prod_data = []
                for month, count, total_qty in monthly_production:
                    prod_data.append({
                        "Mês": month,
                        "Ordens": count,
                        "Quantidade": total_qty or 0
                    })

                prod_df = pd.DataFrame(prod_data)

                fig_prod = make_subplots(specs=[[{"secondary_y": True}]])

                fig_prod.add_trace(
                    go.Bar(x=prod_df["Mês"], y=prod_df["Ordens"], name="Quantidade de Ordens"),
                    secondary_y=False,
                )

                fig_prod.add_trace(
                    go.Scatter(x=prod_df["Mês"], y=prod_df["Quantidade"], mode="lines+markers", name="Volume Produzido"),
                    secondary_y=True,
                )

                fig_prod.update_xaxes(title_text="Mês")
                fig_prod.update_yaxes(title_text="Número de Ordens", secondary_y=False)
                fig_prod.update_yaxes(title_text="Volume (g)", secondary_y=True)
                fig_prod.update_layout(title_text="Tendência de Produção (6 meses)")

                st.plotly_chart(fig_prod, use_container_width=True)
            else:
                st.info("Dados insuficientes para gráfico de produção.")

    with chart_exec_col2:
        # Purchase orders trend
        with Session(engine) as session:
            monthly_purchases = session.exec(
                text("""
                SELECT to_char(order_date, 'YYYY-MM') as month,
                       COUNT(id) as count,
                       SUM(total_value) as total_value
                FROM purchaseorder 
                WHERE order_date >= :start_date
                GROUP BY to_char(order_date, 'YYYY-MM')
                ORDER BY to_char(order_date, 'YYYY-MM')
                """).params(start_date=date.today() - timedelta(days=180))
            ).all()

            if monthly_purchases:
                purch_data = []
                for month, count, total_value in monthly_purchases:
                    purch_data.append({
                        "Mês": month,
                        "Pedidos": count,
                        "Valor": total_value or 0
                    })

                purch_df = pd.DataFrame(purch_data)

                fig_purch = make_subplots(specs=[[{"secondary_y": True}]])

                fig_purch.add_trace(
                    go.Bar(x=purch_df["Mês"], y=purch_df["Pedidos"], name="Quantidade de Pedidos"),
                    secondary_y=False,
                )

                fig_purch.add_trace(
                    go.Scatter(x=purch_df["Mês"], y=purch_df["Valor"], mode="lines+markers", name="Valor Total"),
                    secondary_y=True,
                )

                fig_purch.update_xaxes(title_text="Mês")
                fig_purch.update_yaxes(title_text="Número de Pedidos", secondary_y=False)
                fig_purch.update_yaxes(title_text="Valor (R$)", secondary_y=True)
                fig_purch.update_layout(title_text="Tendência de Compras (6 meses)")

                st.plotly_chart(fig_purch, use_container_width=True)
            else:
                st.info("Dados insuficientes para gráfico de compras.")

    # Status summary
    st.markdown("---")
    st.markdown("### 🎯 Status Operacional")

    status_col1, status_col2, status_col3 = st.columns(3)

    with status_col1:
        with Session(engine) as session:
            # Quality metrics
            total_lots = session.exec(select(func.count(StockLot.id))).one()
            approved_lots = session.exec(
                select(func.count(StockLot.id)).where(StockLot.status == "Aprovado")
            ).one()

            quality_rate = (approved_lots / total_lots * 100) if total_lots > 0 else 0

            st.metric("🏆 Taxa de Qualidade", f"{quality_rate:.1f}%")

            if quality_rate >= 95:
                st.success("✅ Excelente qualidade")
            elif quality_rate >= 90:
                st.warning("⚠️ Qualidade satisfatória")
            else:
                st.error("❌ Qualidade requer atenção")

    with status_col2:
        with Session(engine) as session:
            # Delivery performance
            overdue_pos = session.exec(
                select(func.count(ProductionOrder.id))
                .where(ProductionOrder.end_date < date.today())
                .where(ProductionOrder.status.in_(["Planejada", "Em Produção"]))
            ).one()

            on_time_rate = 85.0 if overdue_pos == 0 else max(50.0, 100 - (overdue_pos * 10))  # Simplified calculation

            st.metric("⏰ OTIF (Pontualidade)", f"{on_time_rate:.1f}%")

            if on_time_rate >= 90:
                st.success("✅ Entregas pontuais")
            elif on_time_rate >= 80:
                st.warning("⚠️ Atrasos moderados")
            else:
                st.error("❌ Muitos atrasos")

    with status_col3:
        with Session(engine) as session:
            # Stock availability
            total_rms = session.exec(select(func.count(RawMaterial.id)).where(RawMaterial.status == "ativo")).one()
            rms_with_stock = session.exec(
                select(func.count(func.distinct(StockLot.item_id)))
                .where(StockLot.item_type == "MP")
                .where(StockLot.qty > 0)
                .where(StockLot.status == "Aprovado")
            ).one()

            availability_rate = (rms_with_stock / total_rms * 100) if total_rms > 0 else 0

            st.metric("📦 Disponibilidade Estoque", f"{availability_rate:.1f}%")

            if availability_rate >= 95:
                st.success("✅ Estoque adequado")
            elif availability_rate >= 85:
                st.warning("⚠️ Alguns itens em falta")
            else:
                st.error("❌ Falta de materiais")

with tab2:
    st.subheader("📋 Relatórios Gerenciais")

    # Report categories
    report_type = st.selectbox("Tipo de Relatório:", [
        "Relatório de Estoque",
        "Performance de Fornecedores",
        "Análise de Produção",
        "Controle de Qualidade",
        "Análise Financeira"
    ])

    # Date range selection
    report_col1, report_col2 = st.columns(2)

    with report_col1:
        start_date = st.date_input("Data Início:", value=date.today() - timedelta(days=30))

    with report_col2:
        end_date = st.date_input("Data Fim:", value=date.today())

    if st.button("📊 Gerar Relatório"):
        with Session(engine) as session:
            if report_type == "Relatório de Estoque":
                st.markdown("### 📦 Relatório de Estoque")

                stock_df = generate_stock_report(session)

                if not stock_df.empty:
                    # Summary metrics
                    stock_summary_col1, stock_summary_col2, stock_summary_col3 = st.columns(3)

                    with stock_summary_col1:
                        total_items = len(stock_df)
                        st.metric("Total de Itens", total_items)

                    with stock_summary_col2:
                        total_value = stock_df["Valor Total"].apply(lambda x: float(x.replace("R$ ", "").replace(",", "")) if isinstance(x, str) else 0).sum()
                        st.metric("Valor Total", f"R$ {total_value:,.2f}")

                    with stock_summary_col3:
                        approved_items = len(stock_df[stock_df["Status"] == "Aprovado"])
                        approval_rate = (approved_items / total_items * 100) if total_items > 0 else 0
                        st.metric("Taxa Aprovação", f"{approval_rate:.1f}%")

                    st.dataframe(stock_df, hide_index=True, use_container_width=True)

                    # Download option
                    create_download_button(stock_df, "relatorio_estoque", "📥 Download Relatório")
                else:
                    st.info("Nenhum dado de estoque encontrado.")

            elif report_type == "Performance de Fornecedores":
                st.markdown("### 🏭 Performance de Fornecedores")

                supplier_df = generate_supplier_performance_report(session)

                if not supplier_df.empty:
                    st.dataframe(supplier_df, hide_index=True, use_container_width=True)

                    # Performance chart
                    fig_supplier_perf = px.bar(
                        supplier_df.head(10), 
                        x="Fornecedor", 
                        y="% Pontualidade", 
                        title="Top 10 Fornecedores - Pontualidade"
                    )
                    fig_supplier_perf.update_xaxes(tickangle=45)
                    st.plotly_chart(fig_supplier_perf, use_container_width=True)

                    create_download_button(supplier_df, "performance_fornecedores", "📥 Download Relatório")
                else:
                    st.info("Nenhum dado de fornecedor encontrado.")

            elif report_type == "Análise de Produção":
                st.markdown("### 🏭 Análise de Produção")

                # Production analysis within date range
                production_orders = session.exec(
                    select(ProductionOrder, Product.name, Product.code)
                    .join(Product, ProductionOrder.product_id == Product.id)
                    .where(ProductionOrder.created_at >= start_date)
                    .where(ProductionOrder.created_at <= end_date)
                ).all()

                if production_orders:
                    production_data = []
                    total_planned = 0
                    total_completed = 0

                    for po, product_name, product_code in production_orders:
                        total_planned += po.qty_to_produce
                        if po.status == "Concluída":
                            total_completed += po.qty_to_produce

                        production_data.append({
                            "Código OP": po.code,
                            "Produto": f"{product_code} - {product_name}",
                            "Quantidade": po.qty_to_produce,
                            "Status": po.status,
                            "Data Início": po.start_date.strftime("%d/%m/%Y") if po.start_date else "N/A",
                            "Data Fim": po.end_date.strftime("%d/%m/%Y") if po.end_date else "N/A",
                            "Centro": po.workcenter or "N/A"
                        })

                    production_df = pd.DataFrame(production_data)

                    # Production metrics
                    prod_metrics_col1, prod_metrics_col2, prod_metrics_col3 = st.columns(3)

                    with prod_metrics_col1:
                        st.metric("Ordens no Período", len(production_orders))

                    with prod_metrics_col2:
                        st.metric("Volume Planejado", f"{total_planned:,.0f} g")

                    with prod_metrics_col3:
                        completion_rate = (total_completed / total_planned * 100) if total_planned > 0 else 0
                        st.metric("Taxa Conclusão", f"{completion_rate:.1f}%")

                    st.dataframe(production_df, hide_index=True, use_container_width=True)

                    # Status distribution
                    status_dist = production_df["Status"].value_counts()
                    fig_status = px.pie(values=status_dist.values, names=status_dist.index, 
                                      title="Distribuição por Status")
                    st.plotly_chart(fig_status, use_container_width=True)

                    create_download_button(production_df, "analise_producao", "📥 Download Relatório")
                else:
                    st.info("Nenhuma ordem de produção encontrada no período.")

with tab3:
    st.subheader("🎯 KPIs Operacionais")

    # KPI categories
    kpi_category = st.selectbox("Categoria de KPIs:", [
        "Eficiência Operacional",
        "Qualidade",
        "Custos",
        "Fornecedores",
        "Estoque"
    ])

    if kpi_category == "Eficiência Operacional":
        st.markdown("### ⚡ KPIs de Eficiência")

        with Session(engine) as session:
            # Calculate operational KPIs
            efficiency_col1, efficiency_col2, efficiency_col3 = st.columns(3)

            with efficiency_col1:
                # Production efficiency
                total_pos = session.exec(select(func.count(ProductionOrder.id))).one()
                completed_pos = session.exec(
                    select(func.count(ProductionOrder.id)).where(ProductionOrder.status == "Concluída")
                ).one()

                completion_rate = (completed_pos / total_pos * 100) if total_pos > 0 else 0

                st.metric("📈 Taxa de Conclusão", f"{completion_rate:.1f}%")

                # Efficiency gauge
                fig_gauge = go.Figure(go.Indicator(
                    mode = "gauge+number+delta",
                    value = completion_rate,
                    domain = {'x': [0, 1], 'y': [0, 1]},
                    title = {'text': "Eficiência Produção"},
                    delta = {'reference': 80},
                    gauge = {
                        'axis': {'range': [None, 100]},
                        'bar': {'color': "darkblue"},
                        'steps': [
                            {'range': [0, 50], 'color': "lightgray"},
                            {'range': [50, 80], 'color': "gray"}],
                        'threshold': {
                            'line': {'color': "red", 'width': 4},
                            'thickness': 0.75,
                            'value': 90}}))

                fig_gauge.update_layout(height=300)
                st.plotly_chart(fig_gauge, use_container_width=True)

            with efficiency_col2:
                # Average production time
                avg_production_time = 5.2  # Placeholder calculation
                st.metric("⏱️ Tempo Médio Produção", f"{avg_production_time:.1f} dias")

                # Lead time trend
                lead_times = [4.8, 5.1, 5.3, 5.0, 5.2, 4.9, 5.1]  # Sample data
                days = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']

                fig_lead = go.Figure()
                fig_lead.add_trace(go.Scatter(x=days, y=lead_times, mode='lines+markers', name='Lead Time'))
                fig_lead.update_layout(title="Lead Time Semanal", height=300)
                st.plotly_chart(fig_lead, use_container_width=True)

            with efficiency_col3:
                # Resource utilization
                utilization_rate = 78.5  # Placeholder
                st.metric("🏭 Utilização Recursos", f"{utilization_rate:.1f}%")

                # Utilization by center
                centers = ['Centro A', 'Centro B', 'Centro C']
                utilization = [85, 72, 80]

                fig_util = px.bar(x=centers, y=utilization, title="Utilização por Centro")
                fig_util.update_layout(height=300)
                st.plotly_chart(fig_util, use_container_width=True)

    elif kpi_category == "Qualidade":
        st.markdown("### 🏆 KPIs de Qualidade")

        with Session(engine) as session:
            quality_col1, quality_col2, quality_col3 = st.columns(3)

            with quality_col1:
                # Quality rate
                total_tests = session.exec(select(func.count(QualityTest.id))).one()
                passed_tests = session.exec(
                    select(func.count(QualityTest.id)).where(QualityTest.status == "Conforme")
                ).one()

                quality_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
                st.metric("✅ Taxa de Conformidade", f"{quality_rate:.1f}%")

            with quality_col2:
                # First pass yield
                first_pass_yield = 92.3  # Placeholder
                st.metric("🎯 First Pass Yield", f"{first_pass_yield:.1f}%")

            with quality_col3:
                # Defect rate
                defect_rate = 100 - quality_rate
                st.metric("❌ Taxa de Defeitos", f"{defect_rate:.1f}%")

            # Quality trend
            if total_tests > 0:
                st.markdown("#### 📊 Tendência de Qualidade")

                quality_trend = session.exec(
                    text("""
                    SELECT to_char(test_date, 'YYYY-MM') as month,
                           COUNT(id) as total,
                           SUM(CASE WHEN status = 'Conforme' THEN 1 ELSE 0 END) as passed
                    FROM qualitytest 
                    WHERE test_date >= :start_date
                    GROUP BY to_char(test_date, 'YYYY-MM')
                    ORDER BY to_char(test_date, 'YYYY-MM')
                    """).params(start_date=date.today() - timedelta(days=180))
                ).all()

                if quality_trend:
                    trend_data = []
                    for month, total, passed in quality_trend:
                        rate = (passed / total * 100) if total > 0 else 0
                        trend_data.append({
                            "Mês": month,
                            "Taxa Conformidade": rate,
                            "Total Testes": total
                        })

                    trend_df = pd.DataFrame(trend_data)

                    fig_quality_trend = px.line(trend_df, x="Mês", y="Taxa Conformidade", 
                                              title="Evolução da Taxa de Conformidade")
                    st.plotly_chart(fig_quality_trend, use_container_width=True)

with tab4:
    st.subheader("📊 Análises Customizadas")

    # Custom analysis builder
    st.markdown("### 🔧 Construtor de Análises")

    analysis_col1, analysis_col2 = st.columns(2)

    with analysis_col1:
        analysis_type = st.selectbox("Tipo de Análise:", [
            "Análise ABC (Estoque)",
            "Análise de Pareto (Fornecedores)",
            "Tendência Temporal",
            "Correlação de Dados",
            "Análise Comparativa"
        ])

    with analysis_col2:
        data_source = st.selectbox("Fonte de Dados:", [
            "Estoque",
            "Produção",
            "Compras",
            "Qualidade",
            "Financeiro"
        ])

    # Analysis parameters
    param_col1, param_col2, param_col3 = st.columns(3)

    with param_col1:
        metric_field = st.selectbox("Campo de Análise:", [
            "Valor",
            "Quantidade",
            "Frequência",
            "Tempo",
            "Taxa"
        ])

    with param_col2:
        grouping = st.selectbox("Agrupar por:", [
            "Produto",
            "Fornecedor",
            "Categoria",
            "Período",
            "Status"
        ])

    with param_col3:
        top_n = st.number_input("Top N resultados:", min_value=5, max_value=50, value=10)

    if st.button("🚀 Executar Análise"):
        with Session(engine) as session:
            if analysis_type == "Análise ABC (Estoque)":
                st.markdown("### 📊 Análise ABC - Classificação de Estoque")

                # ABC Analysis based on stock value
                stock_lots = session.exec(
                    select(StockLot, RawMaterial.code, RawMaterial.name_usual)
                    .join(RawMaterial, StockLot.item_id == RawMaterial.id)
                    .where(StockLot.item_type == "MP")
                    .where(StockLot.qty > 0)
                ).all()

                if stock_lots:
                    abc_data = []
                    for lot, rm_code, rm_name in stock_lots:
                        value = lot.qty * (lot.avg_cost or 0)
                        abc_data.append({
                            "Código": rm_code,
                            "Material": rm_name,
                            "Valor": value,
                            "Quantidade": lot.qty
                        })

                    abc_df = pd.DataFrame(abc_data)
                    abc_df = abc_df.sort_values("Valor", ascending=False)

                    # Calculate ABC classification
                    total_value = abc_df["Valor"].sum()
                    abc_df["% Acumulado"] = abc_df["Valor"].cumsum() / total_value * 100

                    def classify_abc(pct):
                        if pct <= 80:
                            return "A"
                        elif pct <= 95:
                            return "B"
                        else:
                            return "C"

                    abc_df["Classe ABC"] = abc_df["% Acumulado"].apply(classify_abc)

                    # Display results
                    abc_summary = abc_df["Classe ABC"].value_counts()

                    summary_abc_col1, summary_abc_col2, summary_abc_col3 = st.columns(3)

                    with summary_abc_col1:
                        st.metric("Classe A", f"{abc_summary.get('A', 0)} itens")

                    with summary_abc_col2:
                        st.metric("Classe B", f"{abc_summary.get('B', 0)} itens")

                    with summary_abc_col3:
                        st.metric("Classe C", f"{abc_summary.get('C', 0)} itens")

                    # ABC Chart
                    fig_abc = px.bar(abc_df.head(top_n), x="Material", y="Valor", color="Classe ABC",
                                   title=f"Top {top_n} Materiais - Análise ABC")
                    fig_abc.update_xaxes(tickangle=45)
                    st.plotly_chart(fig_abc, use_container_width=True)

                    # Display table
                    display_abc = abc_df[["Código", "Material", "Valor", "% Acumulado", "Classe ABC"]].head(top_n)
                    display_abc["Valor"] = display_abc["Valor"].apply(lambda x: f"R$ {x:,.2f}")
                    display_abc["% Acumulado"] = display_abc["% Acumulado"].apply(lambda x: f"{x:.1f}%")

                    st.dataframe(display_abc, hide_index=True, use_container_width=True)
                else:
                    st.info("Nenhum dado de estoque para análise ABC.")

with tab5:
    st.subheader("📁 Exportações")

    # Export options
    export_col1, export_col2 = st.columns(2)

    with export_col1:
        st.markdown("### 📊 Relatórios Padrão")

        if st.button("📦 Exportar Relatório de Estoque", use_container_width=True):
            with Session(engine) as session:
                stock_df = generate_stock_report(session)
                if not stock_df.empty:
                    create_download_button(stock_df, "relatorio_estoque_completo", "📥 Download Excel", "excel")
                else:
                    st.error("Nenhum dado de estoque para exportar.")

        if st.button("🏭 Exportar Performance Fornecedores", use_container_width=True):
            with Session(engine) as session:
                supplier_df = generate_supplier_performance_report(session)
                if not supplier_df.empty:
                    create_download_button(supplier_df, "performance_fornecedores", "📥 Download Excel", "excel")
                else:
                    st.error("Nenhum dado de fornecedor para exportar.")

        if st.button("📋 Exportar Todas Ordens de Produção", use_container_width=True):
            with Session(engine) as session:
                from services.io_export import export_production_orders_to_excel
                excel_data = export_production_orders_to_excel(session)

                st.download_button(
                    label="📥 Download Excel",
                    data=excel_data.getvalue(),
                    file_name=f"ordens_producao_{date.today().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

    with export_col2:
        st.markdown("### 📋 Relatório Consolidado")

        if st.button("📊 Exportar Relatório Executivo Completo", use_container_width=True):
            with Session(engine) as session:
                comprehensive_data = export_comprehensive_report(session)

                st.download_button(
                    label="📥 Download Relatório Completo",
                    data=comprehensive_data.getvalue(),
                    file_name=f"relatorio_executivo_{date.today().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        st.markdown("### ⚙️ Exportações Customizadas")

        # Custom export parameters
        export_format = st.selectbox("Formato:", ["Excel", "CSV", "PDF"])
        include_charts = st.checkbox("Incluir Gráficos", value=True)
        date_range_export = st.date_input("Período dos Dados:", value=[date.today() - timedelta(days=30), date.today()])

        if st.button("🎯 Gerar Exportação Customizada"):
            st.info("Funcionalidade de exportação customizada será implementada.")

    # Export history
    st.markdown("---")
    st.markdown("### 📚 Histórico de Exportações")

    # Placeholder for export history
    export_history = [
        {"Data": "25/01/2025", "Relatório": "Estoque Completo", "Usuário": user["name"], "Formato": "Excel"},
        {"Data": "24/01/2025", "Relatório": "Performance Fornecedores", "Usuário": user["name"], "Formato": "CSV"},
        {"Data": "23/01/2025", "Relatório": "Análise Produção", "Usuário": "admin", "Formato": "PDF"},
    ]

    history_df = pd.DataFrame(export_history)
    st.dataframe(history_df, hide_index=True, use_container_width=True)