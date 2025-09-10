# utils/data_helpers.py
"""
Data processing and caching utilities for GARNET system
Improves performance through intelligent caching and data processing
"""
import streamlit as st
import pandas as pd
from typing import List, Dict, Any, Optional, Union
from sqlmodel import Session, select, func
from datetime import date, datetime, timedelta


@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_cached_suppliers(engine) -> List[Dict[str, Any]]:
    """
    Get suppliers with caching for performance
    """
    from models import Supplier
    
    with Session(engine) as session:
        suppliers = session.exec(select(Supplier).where(Supplier.status == "ativo")).all()
        return [
            {
                "id": s.id,
                "name": s.name,
                "code": s.code or f"F{s.id:03d}",
                "status": s.status
            }
            for s in suppliers
        ]


@st.cache_data(ttl=300)
def get_cached_raw_materials(engine) -> List[Dict[str, Any]]:
    """
    Get raw materials with caching for performance
    """
    from models import RawMaterial
    
    with Session(engine) as session:
        materials = session.exec(select(RawMaterial).where(RawMaterial.status == "ativo")).all()
        return [
            {
                "id": rm.id,
                "code": rm.code,
                "name_usual": rm.name_usual,
                "uom": rm.uom,
                "status": rm.status
            }
            for rm in materials
        ]


@st.cache_data(ttl=300)
def get_cached_products(engine) -> List[Dict[str, Any]]:
    """
    Get products with caching for performance
    """
    from models import Product
    
    with Session(engine) as session:
        products = session.exec(select(Product).where(Product.status == "ativo")).all()
        return [
            {
                "id": p.id,
                "code": p.code,
                "name": p.name,
                "category": p.category,
                "status": p.status
            }
            for p in products
        ]


@st.cache_data(ttl=600)  # Cache for 10 minutes
def get_dashboard_summary(engine) -> Dict[str, Any]:
    """
    Get dashboard summary data with caching
    """
    from models import Supplier, RawMaterial, Product, StockLot, ProductionOrder
    
    with Session(engine) as session:
        # Count active entities
        suppliers_count = session.exec(
            select(func.count(Supplier.id)).where(Supplier.status == "ativo")
        ).one()
        
        materials_count = session.exec(
            select(func.count(RawMaterial.id)).where(RawMaterial.status == "ativo")
        ).one()
        
        products_count = session.exec(
            select(func.count(Product.id)).where(Product.status == "ativo")
        ).one()
        
        # Stock value calculation
        stock_lots = session.exec(select(StockLot)).all()
        total_stock_value = sum(
            lot.qty_available * (lot.unit_cost or 0) for lot in stock_lots
        )
        
        # Production orders this month
        month_start = date.today().replace(day=1)
        production_orders_month = session.exec(
            select(func.count(ProductionOrder.id))
            .where(ProductionOrder.created_at >= month_start)
        ).one()
        
        return {
            "suppliers_count": suppliers_count,
            "materials_count": materials_count,
            "products_count": products_count,
            "total_stock_value": total_stock_value,
            "production_orders_month": production_orders_month
        }


def apply_dataframe_filters(df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
    """
    Apply filters to a pandas DataFrame
    
    Args:
        df: DataFrame to filter
        filters: Dictionary of filter criteria
    
    Returns:
        Filtered DataFrame
    """
    filtered_df = df.copy()
    
    for column, filter_value in filters.items():
        if filter_value and column in filtered_df.columns:
            if isinstance(filter_value, str) and filter_value != "Todos":
                # Text filter
                if filter_value.startswith("search:"):
                    # Search filter
                    search_term = filter_value[7:].lower()
                    filtered_df = filtered_df[
                        filtered_df[column].astype(str).str.lower().str.contains(search_term, na=False)
                    ]
                else:
                    # Exact match filter
                    filtered_df = filtered_df[filtered_df[column] == filter_value]
            elif isinstance(filter_value, dict) and "start" in filter_value:
                # Date range filter
                start_date = filter_value["start"]
                end_date = filter_value["end"]
                filtered_df[column] = pd.to_datetime(filtered_df[column])
                filtered_df = filtered_df[
                    (filtered_df[column].dt.date >= start_date) &
                    (filtered_df[column].dt.date <= end_date)
                ]
    
    return filtered_df


def format_dataframe_for_display(df: pd.DataFrame, format_config: Dict[str, Dict[str, Any]]) -> pd.DataFrame:
    """
    Format DataFrame columns for better display
    
    Args:
        df: DataFrame to format
        format_config: Formatting configuration per column
    
    Returns:
        Formatted DataFrame
    """
    formatted_df = df.copy()
    
    for column, config in format_config.items():
        if column in formatted_df.columns:
            format_type = config.get("type", "text")
            
            if format_type == "currency":
                currency = config.get("currency", "R$")
                formatted_df[column] = formatted_df[column].apply(
                    lambda x: f"{currency} {x:,.2f}" if pd.notna(x) else "N/A"
                )
            elif format_type == "date":
                date_format = config.get("format", "%d/%m/%Y")
                formatted_df[column] = pd.to_datetime(formatted_df[column]).dt.strftime(date_format)
            elif format_type == "percentage":
                formatted_df[column] = formatted_df[column].apply(
                    lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A"
                )
            elif format_type == "status":
                status_map = config.get("status_map", {})
                formatted_df[column] = formatted_df[column].map(status_map).fillna(formatted_df[column])
    
    return formatted_df


@st.cache_data(ttl=300)
def calculate_stock_metrics(engine) -> Dict[str, float]:
    """
    Calculate stock-related metrics with caching
    """
    from models import StockLot, RawMaterial
    
    with Session(engine) as session:
        # Get all stock lots with raw material info
        query = select(StockLot, RawMaterial.name_usual).join(
            RawMaterial, StockLot.raw_material_id == RawMaterial.id
        )
        results = session.exec(query).all()
        
        total_value = 0
        low_stock_count = 0
        expired_count = 0
        
        for lot, material_name in results:
            # Calculate value
            value = lot.qty_available * (lot.unit_cost or 0)
            total_value += value
            
            # Check low stock (example threshold)
            if lot.qty_available < 10:  # Configurable threshold
                low_stock_count += 1
            
            # Check expired
            if lot.expiry_date and lot.expiry_date < date.today():
                expired_count += 1
        
        return {
            "total_value": total_value,
            "low_stock_count": low_stock_count,
            "expired_count": expired_count,
            "total_lots": len(results)
        }


def optimize_query_performance(query, limit: int = 1000):
    """
    Apply performance optimizations to queries
    
    Args:
        query: SQLModel query
        limit: Maximum number of records to return
    
    Returns:
        Optimized query
    """
    # Add limit to prevent large result sets
    return query.limit(limit)


def paginate_results(items: List[Any], page_size: int = 50, page_number: int = 1) -> Dict[str, Any]:
    """
    Paginate results for better performance
    
    Args:
        items: List of items to paginate
        page_size: Number of items per page
        page_number: Current page number (1-indexed)
    
    Returns:
        Dictionary with paginated data and metadata
    """
    total_items = len(items)
    total_pages = max(1, (total_items + page_size - 1) // page_size)
    
    start_idx = (page_number - 1) * page_size
    end_idx = min(start_idx + page_size, total_items)
    
    return {
        "items": items[start_idx:end_idx],
        "current_page": page_number,
        "total_pages": total_pages,
        "total_items": total_items,
        "has_next": page_number < total_pages,
        "has_prev": page_number > 1
    }


def create_pagination_controls(pagination_data: Dict[str, Any], key_prefix: str = "") -> int:
    """
    Create pagination controls
    
    Args:
        pagination_data: Pagination metadata
        key_prefix: Unique key prefix for controls
    
    Returns:
        Selected page number
    """
    col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
    
    current_page = pagination_data["current_page"]
    total_pages = pagination_data["total_pages"]
    
    with col1:
        if pagination_data["has_prev"]:
            if st.button("« Anterior", key=f"{key_prefix}_prev"):
                return current_page - 1
    
    with col2:
        if st.button("Primeira", key=f"{key_prefix}_first", disabled=current_page == 1):
            return 1
    
    with col3:
        st.markdown(f"**Página {current_page} de {total_pages}**")
        st.caption(f"Total: {pagination_data['total_items']} itens")
    
    with col4:
        if st.button("Última", key=f"{key_prefix}_last", disabled=current_page == total_pages):
            return total_pages
    
    with col5:
        if pagination_data["has_next"]:
            if st.button("Próxima »", key=f"{key_prefix}_next"):
                return current_page + 1
    
    return current_page


def export_to_excel(data: List[Dict[str, Any]], filename: str) -> bytes:
    """
    Export data to Excel format
    
    Args:
        data: Data to export
        filename: Output filename
    
    Returns:
        Excel file bytes
    """
    df = pd.DataFrame(data)
    
    # Create Excel file in memory
    from io import BytesIO
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Dados', index=False)
        
        # Auto-adjust column widths
        worksheet = writer.sheets['Dados']
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    return output.getvalue()