# pages/14_CustosPrecificacao.py
import streamlit as st
from auth import require_login, has_permission
from sqlmodel import Session, select
from db import engine
from models import Product, RawMaterial, Formulation, FormulaItem, StockLot
from services.business import formulation_cost, material_cost_unit
import pandas as pd
from datetime import date

# Require login for this page with manager permission
user = require_login(["manager"])

st.set_page_config(page_title="GARNET - Custos e Precificação", layout="wide")

# Professional page header
st.markdown("""
<div style="padding: 1rem 0 2rem 0; border-bottom: 1px solid #E8E8E8; margin-bottom: 2rem;">
    <h1 style="margin: 0; color: #2E4A6B; font-weight: 300;">Custos e Precificação</h1>
    <p style="margin: 0.5rem 0 0 0; color: #666; font-size: 1.1rem;">Análise de custos e estratégias de preços</p>
</div>
""", unsafe_allow_html=True)



# Clean tabs without icons
tab1, tab2, tab3, tab4 = st.tabs(["Análise de Custos", "Precificação", "Comparativo", "Tendências"])

with tab1:
    st.subheader("Análise de Custos de Produtos")
    
    # Product selection for cost analysis
    with Session(engine) as session:
        products_with_formulation = session.exec(
            select(Product, Formulation.id)
            .join(Formulation, Product.id == Formulation.product_id)
            .where(Formulation.state == "aprovada")
            .where(Product.status == "ativo")
        ).all()
    
    if not products_with_formulation:
        st.error("Nenhum produto com formulação aprovada encontrado.")
    else:
        product_options = [f"{p.code} - {p.name}" for p, _ in products_with_formulation]
        selected_product_option = st.selectbox("Selecione um produto:", product_options)
        
        selected_product = products_with_formulation[product_options.index(selected_product_option)][0]
        
        # Batch size input
        cost_col1, cost_col2 = st.columns(2)
        
        with cost_col1:
            batch_size = st.number_input("Tamanho do Lote (g):", min_value=1.0, 
                                       value=float(selected_product.std_batch_weight), step=100.0)
        
        with cost_col2:
            margin_target = st.number_input("Margem Desejada (%):", min_value=0.0, value=30.0, step=1.0)
        
        if st.button("🧮 Calcular Custos Detalhados"):
            with Session(engine) as session:
                # Get formulation
                formulation = session.exec(
                    select(Formulation)
                    .where(Formulation.product_id == selected_product.id)
                    .where(Formulation.state == "aprovada")
                ).first()
                
                if formulation:
                    # Calculate costs
                    total_cost, unit_cost = formulation_cost(session, formulation.id, batch_size)
                    
                    # Get detailed breakdown
                    items_query = select(FormulaItem, RawMaterial.code, RawMaterial.name_usual, RawMaterial.base_price, RawMaterial.base_unit).join(
                        RawMaterial, FormulaItem.raw_material_id == RawMaterial.id
                    ).where(FormulaItem.formulation_id == formulation.id)
                    
                    items_results = session.exec(items_query).all()
                    
                    st.markdown("### 📊 Análise Detalhada de Custos")
                    
                    # Summary metrics
                    summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)
                    
                    with summary_col1:
                        st.metric("Custo Total do Lote", f"R$ {total_cost:.2f}")
                    
                    with summary_col2:
                        cost_per_gram = total_cost / batch_size
                        st.metric("Custo por Grama", f"R$ {cost_per_gram:.4f}")
                    
                    with summary_col3:
                        if selected_product.unit_weight > 0:
                            units_per_batch = batch_size / selected_product.unit_weight
                            unit_cost = total_cost / units_per_batch
                            st.metric("Custo por Unidade", f"R$ {unit_cost:.4f}")
                        else:
                            st.metric("Custo por Unidade", "N/A")
                    
                    with summary_col4:
                        # Calculate suggested price with margin
                        if selected_product.unit_weight > 0:
                            suggested_price = unit_cost * (1 + margin_target/100)
                            st.metric("Preço Sugerido", f"R$ {suggested_price:.2f}")
                        else:
                            st.metric("Preço Sugerido", "N/A")
                    
                    # Detailed breakdown table
                    st.markdown("### 📋 Breakdown por Matéria-Prima")
                    
                    breakdown_data = []
                    total_percentage = 0
                    
                    for item, rm_code, rm_name, rm_price, rm_unit in items_results:
                        rm = session.get(RawMaterial, item.raw_material_id)
                        item_cost = material_cost_unit(rm, item.qty, item.uom)
                        cost_percentage = (item_cost / total_cost * 100) if total_cost > 0 else 0
                        total_percentage += cost_percentage
                        
                        # Calculate cost per unit of product
                        cost_per_product_unit = 0
                        if selected_product.unit_weight > 0:
                            units_per_batch = batch_size / selected_product.unit_weight
                            cost_per_product_unit = item_cost / units_per_batch
                        
                        breakdown_data.append({
                            "Código MP": rm_code,
                            "Matéria-Prima": rm_name,
                            "Quantidade": f"{item.qty} {item.uom}",
                            "Preço Unit. MP": f"R$ {rm_price:.2f}/{rm_unit}",
                            "Custo Total": f"R$ {item_cost:.2f}",
                            "% do Custo": f"{cost_percentage:.1f}%",
                            "Custo/Unidade Produto": f"R$ {cost_per_product_unit:.4f}" if cost_per_product_unit > 0 else "N/A"
                        })
                    
                    breakdown_df = pd.DataFrame(breakdown_data)
                    st.dataframe(breakdown_df, hide_index=True, use_container_width=True)
                    
                    # Cost distribution chart
                    st.markdown("### 📊 Distribuição de Custos")
                    
                    if breakdown_data:
                        import plotly.express as px
                        
                        chart_data = []
                        for row in breakdown_data:
                            cost_value = float(row["Custo Total"].replace("R$ ", ""))
                            chart_data.append({
                                "Material": row["Matéria-Prima"],
                                "Custo": cost_value
                            })
                        
                        chart_df = pd.DataFrame(chart_data)
                        fig = px.pie(chart_df, values="Custo", names="Material", 
                                   title="Distribuição de Custos por Matéria-Prima")
                        st.plotly_chart(fig, use_container_width=True)
                    
                    # Cost sensitivity analysis
                    st.markdown("---")
                    st.markdown("### 📈 Análise de Sensibilidade")
                    
                    sensitivity_col1, sensitivity_col2 = st.columns(2)
                    
                    with sensitivity_col1:
                        st.markdown("**Impacto da Variação de Preços**")
                        
                        price_variations = [-20, -10, -5, 0, 5, 10, 20]
                        sensitivity_data = []
                        
                        for variation in price_variations:
                            adjusted_cost = total_cost * (1 + variation/100)
                            if selected_product.unit_weight > 0:
                                units_per_batch = batch_size / selected_product.unit_weight
                                adjusted_unit_cost = adjusted_cost / units_per_batch
                                adjusted_price = adjusted_unit_cost * (1 + margin_target/100)
                            else:
                                adjusted_unit_cost = 0
                                adjusted_price = 0
                            
                            sensitivity_data.append({
                                "Variação (%)": f"{variation:+d}%",
                                "Custo Lote": f"R$ {adjusted_cost:.2f}",
                                "Custo Unitário": f"R$ {adjusted_unit_cost:.4f}",
                                "Preço Sugerido": f"R$ {adjusted_price:.2f}"
                            })
                        
                        sensitivity_df = pd.DataFrame(sensitivity_data)
                        st.dataframe(sensitivity_df, hide_index=True, use_container_width=True)
                    
                    with sensitivity_col2:
                        st.markdown("**Simulação de Margens**")
                        
                        margin_scenarios = [10, 15, 20, 25, 30, 35, 40, 50]
                        margin_data = []
                        
                        for margin in margin_scenarios:
                            if selected_product.unit_weight > 0:
                                price_with_margin = unit_cost * (1 + margin/100)
                                profit_per_unit = price_with_margin - unit_cost
                                
                                margin_data.append({
                                    "Margem (%)": f"{margin}%",
                                    "Preço Venda": f"R$ {price_with_margin:.2f}",
                                    "Lucro/Unidade": f"R$ {profit_per_unit:.2f}"
                                })
                        
                        if margin_data:
                            margin_df = pd.DataFrame(margin_data)
                            st.dataframe(margin_df, hide_index=True, use_container_width=True)
                else:
                    st.error("Formulação não encontrada para este produto.")

with tab2:
    st.subheader("💲 Definição de Preços")
    
    # Pricing strategy selection
    strategy_col1, strategy_col2 = st.columns(2)
    
    with strategy_col1:
        pricing_strategy = st.selectbox("Estratégia de Precificação:", [
            "Custo + Margem",
            "Preço de Mercado",
            "Valor Percebido",
            "Precificação Competitiva"
        ])
    
    with strategy_col2:
        pricing_period = st.selectbox("Período de Validade:", [
            "30 dias",
            "60 dias",
            "90 dias",
            "6 meses",
            "1 ano"
        ])
    
    if pricing_strategy == "Custo + Margem":
        st.markdown("### 🧮 Precificação por Custo + Margem")
        
        # Bulk pricing for all products
        if products_with_formulation:
            st.markdown("#### 📊 Precificação em Lote")
            
            bulk_col1, bulk_col2, bulk_col3 = st.columns(3)
            
            with bulk_col1:
                default_margin = st.number_input("Margem Padrão (%):", min_value=0.0, value=30.0, step=1.0)
            
            with bulk_col2:
                volume_discount = st.number_input("Desconto por Volume (%):", min_value=0.0, value=0.0, step=1.0)
            
            with bulk_col3:
                currency_factor = st.number_input("Fator Cambial:", min_value=0.1, value=1.0, step=0.1)
            
            if st.button("📋 Calcular Preços para Todos os Produtos"):
                pricing_results = []
                
                with Session(engine) as session:
                    for product, _ in products_with_formulation:
                        formulation = session.exec(
                            select(Formulation)
                            .where(Formulation.product_id == product.id)
                            .where(Formulation.state == "aprovada")
                        ).first()
                        
                        if formulation:
                            total_cost, unit_cost = formulation_cost(session, formulation.id, product.std_batch_weight)
                            
                            # Apply factors
                            adjusted_cost = unit_cost * currency_factor
                            price_with_margin = adjusted_cost * (1 + default_margin/100)
                            price_with_discount = price_with_margin * (1 - volume_discount/100)
                            
                            profit_margin = price_with_discount - adjusted_cost
                            profit_percentage = (profit_margin / adjusted_cost * 100) if adjusted_cost > 0 else 0
                            
                            pricing_results.append({
                                "Código": product.code,
                                "Produto": product.name,
                                "Custo Unitário": f"R$ {adjusted_cost:.4f}",
                                "Preço Sugerido": f"R$ {price_with_discount:.2f}",
                                "Margem Líquida": f"R$ {profit_margin:.2f}",
                                "% Margem": f"{profit_percentage:.1f}%"
                            })
                
                if pricing_results:
                    pricing_df = pd.DataFrame(pricing_results)
                    st.dataframe(pricing_df, hide_index=True, use_container_width=True)
                    
                    # Export pricing table
                    if st.button("📥 Exportar Tabela de Preços"):
                        csv = pricing_df.to_csv(index=False)
                        st.download_button(
                            label="Download CSV",
                            data=csv,
                            file_name=f"tabela_precos_{date.today().strftime('%Y%m%d')}.csv",
                            mime="text/csv"
                        )
    
    elif pricing_strategy == "Preço de Mercado":
        st.markdown("### 🏪 Precificação por Mercado")
        st.info("Funcionalidade de pesquisa de preços de mercado será implementada com integração a APIs de marketplace.")
        
        # Manual market price input
        if products_with_formulation:
            selected_product_market = st.selectbox("Produto para Análise de Mercado:", 
                                                  [f"{p.code} - {p.name}" for p, _ in products_with_formulation])
            
            market_col1, market_col2 = st.columns(2)
            
            with market_col1:
                competitor_price = st.number_input("Preço Concorrente (R$):", min_value=0.0, step=0.01)
                market_position = st.selectbox("Posicionamento:", ["Premium (+10%)", "Padrão (0%)", "Competitivo (-5%)"])
            
            with market_col2:
                if competitor_price > 0:
                    if market_position == "Premium (+10%)":
                        suggested_market_price = competitor_price * 1.10
                    elif market_position == "Competitivo (-5%)":
                        suggested_market_price = competitor_price * 0.95
                    else:
                        suggested_market_price = competitor_price
                    
                    st.metric("Preço Sugerido", f"R$ {suggested_market_price:.2f}")

with tab3:
    st.subheader("📊 Análise Comparativa")
    
    # Compare multiple products
    if len(products_with_formulation) >= 2:
        st.markdown("### 🔍 Comparativo de Produtos")
        
        # Multi-select for products
        comparison_products = st.multiselect(
            "Selecione produtos para comparar:",
            options=[f"{p.code} - {p.name}" for p, _ in products_with_formulation],
            default=[f"{p.code} - {p.name}" for p, _ in products_with_formulation[:3]]
        )
        
        if len(comparison_products) >= 2:
            comparison_data = []
            
            with Session(engine) as session:
                for product_option in comparison_products:
                    product = next(p for p, _ in products_with_formulation if f"{p.code} - {p.name}" == product_option)
                    
                    formulation = session.exec(
                        select(Formulation)
                        .where(Formulation.product_id == product.id)
                        .where(Formulation.state == "aprovada")
                    ).first()
                    
                    if formulation:
                        total_cost, unit_cost = formulation_cost(session, formulation.id, product.std_batch_weight)
                        
                        # Count ingredients
                        ingredient_count = session.exec(
                            select(FormulaItem).where(FormulaItem.formulation_id == formulation.id)
                        ).all()
                        
                        comparison_data.append({
                            "Produto": f"{product.code} - {product.name}",
                            "Peso Unitário": f"{product.unit_weight} {product.unit_uom}",
                            "Lote Padrão": f"{product.std_batch_weight} g",
                            "Ingredientes": len(ingredient_count),
                            "Custo/Lote": f"R$ {total_cost:.2f}",
                            "Custo/Unidade": f"R$ {unit_cost:.4f}",
                            "Custo/Grama": f"R$ {total_cost/product.std_batch_weight:.4f}"
                        })
            
            if comparison_data:
                comparison_df = pd.DataFrame(comparison_data)
                st.dataframe(comparison_df, hide_index=True, use_container_width=True)
                
                # Comparison charts
                chart_col1, chart_col2 = st.columns(2)
                
                with chart_col1:
                    # Cost per unit comparison
                    import plotly.express as px
                    
                    cost_data = []
                    for row in comparison_data:
                        cost_value = float(row["Custo/Unidade"].replace("R$ ", ""))
                        cost_data.append({
                            "Produto": row["Produto"].split(" - ")[0],  # Just the code
                            "Custo": cost_value
                        })
                    
                    cost_df = pd.DataFrame(cost_data)
                    fig_cost = px.bar(cost_df, x="Produto", y="Custo", 
                                    title="Custo por Unidade - Comparativo")
                    st.plotly_chart(fig_cost, use_container_width=True)
                
                with chart_col2:
                    # Complexity comparison (by ingredient count)
                    complexity_data = []
                    for row in comparison_data:
                        complexity_data.append({
                            "Produto": row["Produto"].split(" - ")[0],
                            "Ingredientes": row["Ingredientes"]
                        })
                    
                    complexity_df = pd.DataFrame(complexity_data)
                    fig_complexity = px.bar(complexity_df, x="Produto", y="Ingredientes", 
                                          title="Complexidade da Formulação")
                    st.plotly_chart(fig_complexity, use_container_width=True)
    else:
        st.info("Necessário pelo menos 2 produtos com formulação para comparação.")

with tab4:
    st.subheader("📈 Tendências de Custos")
    
    # Historical cost analysis
    st.markdown("### 📊 Análise Histórica de Custos")
    
    # Placeholder for historical analysis
    with Session(engine) as session:
        # Get raw material price trends
        raw_materials = session.exec(select(RawMaterial).where(RawMaterial.status == "ativo")).all()
        
        if raw_materials:
            st.markdown("#### 💹 Tendência de Preços de Matérias-Primas")
            
            # Current pricing table
            rm_pricing_data = []
            for rm in raw_materials:
                rm_pricing_data.append({
                    "Código": rm.code,
                    "Matéria-Prima": rm.name_usual,
                    "Preço Atual": f"R$ {rm.base_price:.2f}/{rm.base_unit}",
                    "Última Atualização": rm.created_at.strftime("%d/%m/%Y") if rm.created_at else "N/A",
                    "Status": rm.status
                })
            
            rm_pricing_df = pd.DataFrame(rm_pricing_data)
            st.dataframe(rm_pricing_df, hide_index=True, use_container_width=True)
            
            # Price volatility analysis
            st.markdown("#### 📊 Análise de Volatilidade")
            
            volatility_col1, volatility_col2 = st.columns(2)
            
            with volatility_col1:
                # Top expensive materials
                expensive_materials = sorted(raw_materials, key=lambda x: x.base_price, reverse=True)[:5]
                
                expensive_data = []
                for rm in expensive_materials:
                    expensive_data.append({
                        "Material": rm.name_usual,
                        "Preço": rm.base_price
                    })
                
                if expensive_data:
                    import plotly.express as px
                    expensive_df = pd.DataFrame(expensive_data)
                    fig_expensive = px.bar(expensive_df, x="Material", y="Preço", 
                                         title="Top 5 Matérias-Primas Mais Caras")
                    fig_expensive.update_xaxes(tickangle=45)
                    st.plotly_chart(fig_expensive, use_container_width=True)
            
            with volatility_col2:
                # Price distribution
                price_ranges = {"0-10": 0, "10-50": 0, "50-100": 0, "100+": 0}
                
                for rm in raw_materials:
                    if rm.base_price <= 10:
                        price_ranges["0-10"] += 1
                    elif rm.base_price <= 50:
                        price_ranges["10-50"] += 1
                    elif rm.base_price <= 100:
                        price_ranges["50-100"] += 1
                    else:
                        price_ranges["100+"] += 1
                
                range_df = pd.DataFrame(list(price_ranges.items()), columns=["Faixa", "Quantidade"])
                fig_range = px.pie(range_df, values="Quantidade", names="Faixa", 
                                 title="Distribuição por Faixa de Preço")
                st.plotly_chart(fig_range, use_container_width=True)
        
        # Cost forecasting
        st.markdown("---")
        st.markdown("### 🔮 Projeções de Custo")
        
        forecast_col1, forecast_col2 = st.columns(2)
        
        with forecast_col1:
            inflation_rate = st.number_input("Taxa de Inflação Anual (%):", min_value=0.0, value=5.0, step=0.1)
            exchange_variation = st.number_input("Variação Cambial (%):", min_value=-50.0, max_value=50.0, value=0.0, step=1.0)
        
        with forecast_col2:
            forecast_months = st.selectbox("Período de Projeção:", [3, 6, 12, 24])
            cost_adjustment = st.number_input("Ajuste Adicional (%):", min_value=-20.0, max_value=20.0, value=0.0, step=1.0)
        
        if st.button("📈 Gerar Projeção"):
            # Calculate projected costs
            monthly_inflation = inflation_rate / 12 / 100
            exchange_factor = 1 + exchange_variation / 100
            adjustment_factor = 1 + cost_adjustment / 100
            
            projection_data = []
            
            if products_with_formulation:
                for product, _ in products_with_formulation[:5]:  # Limit to first 5 for demo
                    formulation = session.exec(
                        select(Formulation)
                        .where(Formulation.product_id == product.id)
                        .where(Formulation.state == "aprovada")
                    ).first()
                    
                    if formulation:
                        current_cost, current_unit_cost = formulation_cost(session, formulation.id, product.std_batch_weight)
                        
                        # Calculate projected cost
                        projected_cost = current_cost
                        for month in range(forecast_months):
                            projected_cost *= (1 + monthly_inflation)
                        
                        projected_cost *= exchange_factor * adjustment_factor
                        
                        units_per_batch = product.std_batch_weight / product.unit_weight if product.unit_weight > 0 else 1
                        projected_unit_cost = projected_cost / units_per_batch
                        
                        cost_increase = ((projected_unit_cost - current_unit_cost) / current_unit_cost * 100) if current_unit_cost > 0 else 0
                        
                        projection_data.append({
                            "Produto": f"{product.code} - {product.name}",
                            "Custo Atual": f"R$ {current_unit_cost:.4f}",
                            "Custo Projetado": f"R$ {projected_unit_cost:.4f}",
                            "Aumento": f"{cost_increase:.1f}%",
                            "Impacto/Mês": f"R$ {(projected_unit_cost - current_unit_cost):.4f}"
                        })
                
                if projection_data:
                    st.markdown(f"### 📊 Projeção de Custos - {forecast_months} meses")
                    projection_df = pd.DataFrame(projection_data)
                    st.dataframe(projection_df, hide_index=True, use_container_width=True)
                    
                    # Alert for high increases
                    high_increase_products = [p for p in projection_data if float(p["Aumento"].replace("%", "")) > 15]
                    if high_increase_products:
                        st.warning(f"⚠️ {len(high_increase_products)} produtos com aumento superior a 15%")
