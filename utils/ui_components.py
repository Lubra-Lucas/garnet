# utils/ui_components.py
"""
UI Components and styling utilities for GARNET system
Centralizes repeated UI patterns and improves consistency
"""
import streamlit as st
from typing import List, Optional, Dict, Any


def render_page_header(title: str, subtitle: str) -> None:
    """
    Renders a professional page header with consistent styling
    
    Args:
        title: Main page title
        subtitle: Descriptive subtitle
    """
    st.markdown(f"""
    <div style="padding: 1rem 0 2rem 0; border-bottom: 1px solid #E8E8E8; margin-bottom: 2rem;">
        <h1 style="margin: 0; color: #2E4A6B; font-weight: 300;">{title}</h1>
        <p style="margin: 0.5rem 0 0 0; color: #666; font-size: 1.1rem;">{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)


def render_feature_card(title: str, features: List[str]) -> None:
    """
    Renders a feature card with consistent styling
    
    Args:
        title: Card title
        features: List of feature descriptions
    """
    features_html = "".join([
        f'<li style="margin-bottom: 0.25rem;">{feature}</li>' 
        for feature in features
    ])
    
    st.markdown(f"""
    <div style="background: white; padding: 1.25rem; border-radius: 8px; border: 1px solid #E0E0E0; min-height: 180px; margin-bottom: 1rem;">
        <h4 style="margin: 0 0 0.75rem 0; color: #2E4A6B; font-size: 1.1rem;">{title}</h4>
        <ul style="margin: 0; padding-left: 1.25rem; color: #666; line-height: 1.5; font-size: 0.95rem;">
            {features_html}
        </ul>
    </div>
    """, unsafe_allow_html=True)


def render_info_box(content: str, background_color: str = "#F8F9FA") -> None:
    """
    Renders an info box with consistent styling
    
    Args:
        content: Box content
        background_color: Background color (default: light gray)
    """
    st.markdown(f"""
    <div style="background: {background_color}; padding: 1.25rem; border-radius: 8px; margin-bottom: 1.5rem; border: 1px solid #E0E0E0;">
        <p style="margin: 0; font-size: 1rem; color: #444; line-height: 1.5;">
        {content}
        </p>
    </div>
    """, unsafe_allow_html=True)


def render_section_header(title: str, with_divider: bool = True) -> None:
    """
    Renders a section header with optional top divider
    
    Args:
        title: Section title
        with_divider: Whether to include top border divider
    """
    border_style = "border-top: 1px solid #E8E8E8;" if with_divider else ""
    
    st.markdown(f"""
    <div style="margin: 1.5rem 0 0.75rem 0; padding-top: 1rem; {border_style}">
        <h4 style="margin: 0; color: #2E4A6B; font-size: 1.1rem;">{title}</h4>
    </div>
    """, unsafe_allow_html=True)


@st.cache_data
def get_status_display(status: str, status_type: str = "generic") -> str:
    """
    Returns formatted status display with appropriate icons
    
    Args:
        status: Raw status string
        status_type: Type of status (production, purchase, etc.)
    """
    status_icons = {
        "production": {
            "Planejada": "📋 Planejada",
            "Em Produção": "🔄 Em Produção", 
            "Concluída": "✅ Concluída",
            "Cancelada": "❌ Cancelada"
        },
        "purchase": {
            "Aberto": "📝 Aberto",
            "Enviado": "📤 Enviado",
            "Recebido": "✅ Recebido",
            "Cancelado": "❌ Cancelado"
        },
        "financial": {
            "Pendente": "⏳ Pendente",
            "Pago": "✅ Pago",
            "Recebido": "✅ Recebido",
            "Vencido": "🔴 Vencido"
        },
        "generic": {
            "ativo": "✅ Ativo",
            "inativo": "❌ Inativo",
            "aprovada": "✅ Aprovada",
            "pendente": "⏳ Pendente"
        }
    }
    
    return status_icons.get(status_type, {}).get(status, status)


def create_metric_card(label: str, value: str, delta: Optional[str] = None) -> None:
    """
    Creates a professional metric card
    
    Args:
        label: Metric label
        value: Metric value
        delta: Optional delta change
    """
    st.metric(label=label, value=value, delta=delta)


def show_loading_spinner(message: str = "Carregando...") -> None:
    """
    Shows a loading spinner with message
    
    Args:
        message: Loading message
    """
    with st.spinner(message):
        pass


def render_success_message(message: str, details: Optional[str] = None) -> None:
    """
    Renders a success message with optional details
    
    Args:
        message: Success message
        details: Optional additional details
    """
    st.success(message)
    if details:
        with st.expander("Ver detalhes"):
            st.info(details)


def render_error_message(message: str, error_details: Optional[str] = None) -> None:
    """
    Renders an error message with optional technical details
    
    Args:
        message: User-friendly error message
        error_details: Optional technical error details
    """
    st.error(message)
    if error_details:
        with st.expander("Detalhes técnicos"):
            st.code(error_details)


def create_confirmation_dialog(
    title: str, 
    message: str, 
    confirm_text: str = "Confirmar",
    cancel_text: str = "Cancelar",
    danger: bool = False
) -> Dict[str, bool]:
    """
    Creates a confirmation dialog with consistent styling
    
    Args:
        title: Dialog title
        message: Confirmation message
        confirm_text: Confirm button text
        cancel_text: Cancel button text
        danger: Whether this is a dangerous action
    
    Returns:
        Dict with 'confirmed' and 'cancelled' keys
    """
    st.warning(f"⚠️ **{title}**")
    if danger:
        st.error(message)
    else:
        st.info(message)
    
    col1, col2 = st.columns(2)
    
    with col1:
        confirmed = st.button(
            f"✅ {confirm_text}", 
            type="primary" if not danger else "primary",
            use_container_width=True
        )
    
    with col2:
        cancelled = st.button(
            f"❌ {cancel_text}",
            use_container_width=True
        )
    
    return {"confirmed": confirmed, "cancelled": cancelled}


def format_currency(value: float, currency: str = "R$") -> str:
    """
    Formats currency values consistently
    
    Args:
        value: Numeric value
        currency: Currency symbol
    
    Returns:
        Formatted currency string
    """
    return f"{currency} {value:,.2f}"


def format_date(date_obj, format_str: str = "%d/%m/%Y") -> str:
    """
    Formats dates consistently
    
    Args:
        date_obj: Date object
        format_str: Date format string
    
    Returns:
        Formatted date string
    """
    if date_obj:
        return date_obj.strftime(format_str)
    return "N/A"


def create_data_table(
    data: List[Dict[str, Any]], 
    editable: bool = False,
    key: Optional[str] = None
) -> Any:
    """
    Creates a consistent data table with optional editing
    
    Args:
        data: Table data
        editable: Whether table should be editable
        key: Unique key for the table
    
    Returns:
        DataFrame (edited if editable=True)
    """
    import pandas as pd
    
    if not data:
        st.info("Nenhum dado encontrado.")
        return None
    
    df = pd.DataFrame(data)
    
    if editable:
        return st.data_editor(
            df,
            hide_index=True,
            use_container_width=True,
            key=key
        )
    else:
        st.dataframe(df, hide_index=True, use_container_width=True)
        return df