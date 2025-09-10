# utils/form_helpers.py
"""
Form utilities and helpers for GARNET system
Standardizes form patterns and validation
"""
import streamlit as st
from typing import List, Dict, Any, Optional, Tuple
from datetime import date, datetime
import pandas as pd


def create_auto_generated_code(prefix: str, model_class, session, field_name: str = "code") -> str:
    """
    Generates auto-incremented codes for entities
    
    Args:
        prefix: Code prefix (e.g., "OP-", "PC-")
        model_class: SQLModel class
        session: Database session
        field_name: Field name to check for last code
    
    Returns:
        Generated code string
    """
    from sqlmodel import select
    
    next_number = 1
    last_record = session.exec(
        select(model_class).order_by(model_class.id.desc())
    ).first()
    
    if last_record:
        last_code = getattr(last_record, field_name, "")
        if last_code and last_code.startswith(prefix):
            try:
                last_number = int(last_code.split("-")[-1])
                next_number = last_number + 1
            except:
                pass
    
    return f"{prefix}{date.today().year}-{next_number:03d}"


def render_form_section(title: str, columns: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Renders a form section with multiple columns and fields
    
    Args:
        title: Section title
        columns: List of column definitions with fields
    
    Returns:
        Dictionary with form values
    """
    st.subheader(title)
    
    if len(columns) > 1:
        cols = st.columns(len(columns))
    else:
        cols = [st.container()]
    
    form_data = {}
    
    for i, column_def in enumerate(columns):
        with cols[i]:
            for field in column_def.get("fields", []):
                field_type = field.get("type", "text")
                key = field.get("key")
                label = field.get("label", key)
                required = field.get("required", False)
                
                label_display = f"{label} *" if required else label
                
                if field_type == "text":
                    form_data[key] = st.text_input(
                        label_display,
                        value=field.get("default", ""),
                        placeholder=field.get("placeholder", ""),
                        help=field.get("help")
                    )
                elif field_type == "number":
                    form_data[key] = st.number_input(
                        label_display,
                        min_value=field.get("min_value", 0.0),
                        max_value=field.get("max_value"),
                        value=field.get("default", 0.0),
                        step=field.get("step", 0.01),
                        help=field.get("help")
                    )
                elif field_type == "date":
                    form_data[key] = st.date_input(
                        label_display,
                        value=field.get("default", date.today()),
                        help=field.get("help")
                    )
                elif field_type == "select":
                    form_data[key] = st.selectbox(
                        label_display,
                        options=field.get("options", []),
                        index=field.get("default_index", 0),
                        help=field.get("help")
                    )
                elif field_type == "textarea":
                    form_data[key] = st.text_area(
                        label_display,
                        value=field.get("default", ""),
                        placeholder=field.get("placeholder", ""),
                        help=field.get("help")
                    )
                elif field_type == "file":
                    form_data[key] = st.file_uploader(
                        label_display,
                        type=field.get("file_types", ["pdf", "xlsx", "xml"]),
                        help=field.get("help")
                    )
    
    return form_data


def validate_form_data(form_data: Dict[str, Any], rules: Dict[str, Dict[str, Any]]) -> Tuple[bool, List[str]]:
    """
    Validates form data against rules
    
    Args:
        form_data: Form data to validate
        rules: Validation rules per field
    
    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []
    
    for field_key, field_rules in rules.items():
        value = form_data.get(field_key)
        
        # Required field validation
        if field_rules.get("required", False):
            if not value or (isinstance(value, str) and not value.strip()):
                errors.append(f"{field_rules.get('label', field_key)} é obrigatório")
        
        # Min/max length validation for strings
        if value and isinstance(value, str):
            min_length = field_rules.get("min_length")
            max_length = field_rules.get("max_length")
            
            if min_length and len(value) < min_length:
                errors.append(f"{field_rules.get('label', field_key)} deve ter pelo menos {min_length} caracteres")
            
            if max_length and len(value) > max_length:
                errors.append(f"{field_rules.get('label', field_key)} deve ter no máximo {max_length} caracteres")
        
        # Numeric validation
        if value and field_rules.get("type") == "number":
            min_value = field_rules.get("min_value")
            max_value = field_rules.get("max_value")
            
            if min_value is not None and value < min_value:
                errors.append(f"{field_rules.get('label', field_key)} deve ser maior que {min_value}")
            
            if max_value is not None and value > max_value:
                errors.append(f"{field_rules.get('label', field_key)} deve ser menor que {max_value}")
    
    return len(errors) == 0, errors


def create_dynamic_item_form(
    item_type: str,
    session_key: str,
    fields_config: List[Dict[str, Any]],
    min_items: int = 1
) -> List[Dict[str, Any]]:
    """
    Creates a dynamic form for adding/removing items
    
    Args:
        item_type: Type of items being managed
        session_key: Session state key for items
        fields_config: Configuration for item fields
        min_items: Minimum number of items required
    
    Returns:
        List of item data
    """
    if session_key not in st.session_state:
        st.session_state[session_key] = [{}] * min_items
    
    items = st.session_state[session_key]
    
    st.markdown(f"**{item_type}**")
    
    # Add/remove controls
    control_col1, control_col2 = st.columns([1, 1])
    
    with control_col1:
        if st.button(f"➕ Adicionar {item_type}", key=f"add_{session_key}"):
            st.session_state[session_key].append({})
            st.rerun()
    
    with control_col2:
        if len(items) > min_items:
            if st.button(f"➖ Remover último", key=f"remove_{session_key}"):
                st.session_state[session_key].pop()
                st.rerun()
    
    # Render items
    for i, item in enumerate(items):
        st.markdown(f"**{item_type} {i+1}**")
        
        # Create columns based on fields config
        cols = st.columns(len(fields_config))
        
        for j, field_config in enumerate(fields_config):
            with cols[j]:
                field_key = field_config["key"]
                field_type = field_config.get("type", "text")
                label = field_config.get("label", field_key)
                
                if field_type == "select":
                    value = st.selectbox(
                        label,
                        options=field_config.get("options", []),
                        key=f"{session_key}_{i}_{field_key}",
                        index=field_config.get("default_index", 0)
                    )
                elif field_type == "number":
                    value = st.number_input(
                        label,
                        min_value=field_config.get("min_value", 0.0),
                        value=field_config.get("default", 0.0),
                        step=field_config.get("step", 0.01),
                        key=f"{session_key}_{i}_{field_key}"
                    )
                elif field_type == "date":
                    value = st.date_input(
                        label,
                        value=field_config.get("default", date.today()),
                        key=f"{session_key}_{i}_{field_key}"
                    )
                else:  # text
                    value = st.text_input(
                        label,
                        placeholder=field_config.get("placeholder", ""),
                        key=f"{session_key}_{i}_{field_key}"
                    )
                
                item[field_key] = value
    
    return items


def create_filter_section(filters_config: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Creates a standardized filter section
    
    Args:
        filters_config: Configuration for filters
    
    Returns:
        Dictionary with filter values
    """
    st.markdown("### Filtros")
    
    cols = st.columns(len(filters_config))
    filters = {}
    
    for i, filter_config in enumerate(filters_config):
        with cols[i]:
            filter_type = filter_config.get("type", "select")
            key = filter_config["key"]
            label = filter_config.get("label", key)
            
            if filter_type == "select":
                filters[key] = st.selectbox(
                    label,
                    options=filter_config.get("options", []),
                    index=filter_config.get("default_index", 0)
                )
            elif filter_type == "text":
                filters[key] = st.text_input(
                    label,
                    placeholder=filter_config.get("placeholder", "")
                )
            elif filter_type == "date_range":
                start_date = st.date_input(
                    f"{label} - Início",
                    value=filter_config.get("default_start", date.today())
                )
                end_date = st.date_input(
                    f"{label} - Fim",
                    value=filter_config.get("default_end", date.today())
                )
                filters[key] = {"start": start_date, "end": end_date}
    
    return filters


@st.cache_data
def format_options_list(items: List[Any], code_field: str, name_field: str) -> List[str]:
    """
    Formats a list of items into display options
    
    Args:
        items: List of items (database records)
        code_field: Field name for code
        name_field: Field name for name
    
    Returns:
        List of formatted option strings
    """
    return [f"{getattr(item, code_field)} - {getattr(item, name_field)}" for item in items]


def extract_id_from_option(option: str, items: List[Any], code_field: str) -> Optional[int]:
    """
    Extracts ID from a formatted option string
    
    Args:
        option: Selected option string
        items: Original items list
        code_field: Field name for code
    
    Returns:
        Item ID or None
    """
    if " - " in option:
        code = option.split(" - ")[0]
        for item in items:
            if getattr(item, code_field) == code:
                return item.id
    return None