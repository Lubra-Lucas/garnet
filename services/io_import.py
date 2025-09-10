# services/io_import.py
import pandas as pd
import streamlit as st
from sqlmodel import Session
from models import Supplier, RawMaterial, Product, StockLot
from io import BytesIO
from typing import List, Dict, Any

def import_suppliers_from_excel(file_data: BytesIO, session: Session) -> Dict[str, Any]:
    """Import suppliers from Excel file"""
    try:
        df = pd.read_excel(file_data, sheet_name=0)
        
        # Expected columns mapping
        column_mapping = {
            "Nome": "name",
            "CNPJ": "cnpj", 
            "Telefone": "phone",
            "Email": "email",
            "Contato": "contact",
            "Endereço": "address",
            "Condições Pagamento": "payment_terms",
            "Lead Time (dias)": "avg_leadtime_days",
            "Certificações": "certifications",
            "Observações": "notes"
        }
        
        imported_count = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                supplier_data = {}
                for excel_col, model_field in column_mapping.items():
                    if excel_col in df.columns:
                        value = row[excel_col]
                        if pd.notna(value):
                            supplier_data[model_field] = str(value) if model_field != "avg_leadtime_days" else int(value)
                
                if "name" in supplier_data:
                    # Check if supplier already exists
                    existing = session.exec(
                        select(Supplier).where(Supplier.name == supplier_data["name"])
                    ).first()
                    
                    if not existing:
                        supplier = Supplier(**supplier_data)
                        session.add(supplier)
                        imported_count += 1
                    else:
                        errors.append(f"Linha {index + 2}: Fornecedor '{supplier_data['name']}' já existe")
                else:
                    errors.append(f"Linha {index + 2}: Nome do fornecedor é obrigatório")
                    
            except Exception as e:
                errors.append(f"Linha {index + 2}: Erro ao processar - {str(e)}")
        
        session.commit()
        
        return {
            "success": True,
            "imported_count": imported_count,
            "errors": errors,
            "total_rows": len(df)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Erro ao processar arquivo: {str(e)}"
        }

def import_raw_materials_from_excel(file_data: BytesIO, session: Session) -> Dict[str, Any]:
    """Import raw materials from Excel file"""
    try:
        df = pd.read_excel(file_data, sheet_name=0)
        
        column_mapping = {
            "Código": "code",
            "Nome Usual": "name_usual",
            "Nome Químico": "name_chemical",
            "Fornecedor": "supplier_name",
            "Unidade Base": "base_unit",
            "Preço Base": "base_price",
            "Densidade": "density",
            "Fator Conversão": "conv_factor",
            "Validade (dias)": "shelf_life_days",
            "Localização": "location"
        }
        
        imported_count = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                rm_data = {}
                supplier_name = None
                
                for excel_col, model_field in column_mapping.items():
                    if excel_col in df.columns:
                        value = row[excel_col]
                        if pd.notna(value):
                            if model_field == "supplier_name":
                                supplier_name = str(value)
                            elif model_field in ["base_price", "density", "conv_factor"]:
                                rm_data[model_field] = float(value)
                            elif model_field == "shelf_life_days":
                                rm_data[model_field] = int(value)
                            else:
                                rm_data[model_field] = str(value)
                
                # Find supplier ID if supplier name provided
                if supplier_name:
                    supplier = session.exec(
                        select(Supplier).where(Supplier.name == supplier_name)
                    ).first()
                    if supplier:
                        rm_data["supplier_id"] = supplier.id
                
                if "code" in rm_data and "name_usual" in rm_data:
                    # Check if raw material already exists
                    existing = session.exec(
                        select(RawMaterial).where(RawMaterial.code == rm_data["code"])
                    ).first()
                    
                    if not existing:
                        rm = RawMaterial(**rm_data)
                        session.add(rm)
                        imported_count += 1
                    else:
                        errors.append(f"Linha {index + 2}: Matéria-prima '{rm_data['code']}' já existe")
                else:
                    errors.append(f"Linha {index + 2}: Código e Nome Usual são obrigatórios")
                    
            except Exception as e:
                errors.append(f"Linha {index + 2}: Erro ao processar - {str(e)}")
        
        session.commit()
        
        return {
            "success": True,
            "imported_count": imported_count,
            "errors": errors,
            "total_rows": len(df)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Erro ao processar arquivo: {str(e)}"
        }

def import_products_from_excel(file_data: BytesIO, session: Session) -> Dict[str, Any]:
    """Import products from Excel file"""
    try:
        df = pd.read_excel(file_data, sheet_name=0)
        
        column_mapping = {
            "Código": "code",
            "Nome": "name",
            "Cliente": "client",
            "Categoria": "category",
            "Peso Unitário": "unit_weight",
            "UOM": "unit_uom",
            "Peso Lote Padrão": "std_batch_weight"
        }
        
        imported_count = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                product_data = {}
                
                for excel_col, model_field in column_mapping.items():
                    if excel_col in df.columns:
                        value = row[excel_col]
                        if pd.notna(value):
                            if model_field in ["unit_weight", "std_batch_weight"]:
                                product_data[model_field] = float(value)
                            else:
                                product_data[model_field] = str(value)
                
                if "code" in product_data and "name" in product_data:
                    # Check if product already exists
                    existing = session.exec(
                        select(Product).where(Product.code == product_data["code"])
                    ).first()
                    
                    if not existing:
                        product = Product(**product_data)
                        session.add(product)
                        imported_count += 1
                    else:
                        errors.append(f"Linha {index + 2}: Produto '{product_data['code']}' já existe")
                else:
                    errors.append(f"Linha {index + 2}: Código e Nome são obrigatórios")
                    
            except Exception as e:
                errors.append(f"Linha {index + 2}: Erro ao processar - {str(e)}")
        
        session.commit()
        
        return {
            "success": True,
            "imported_count": imported_count,
            "errors": errors,
            "total_rows": len(df)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Erro ao processar arquivo: {str(e)}"
        }

def validate_excel_structure(file_data: BytesIO, expected_columns: List[str]) -> Dict[str, Any]:
    """Validate Excel file structure before import"""
    try:
        df = pd.read_excel(file_data, sheet_name=0, nrows=0)  # Just read headers
        
        missing_columns = [col for col in expected_columns if col not in df.columns]
        extra_columns = [col for col in df.columns if col not in expected_columns]
        
        return {
            "valid": len(missing_columns) == 0,
            "missing_columns": missing_columns,
            "extra_columns": extra_columns,
            "found_columns": list(df.columns)
        }
        
    except Exception as e:
        return {
            "valid": False,
            "error": f"Erro ao ler arquivo: {str(e)}"
        }

# Expected column structures for different import types
IMPORT_TEMPLATES = {
    "suppliers": ["Nome", "CNPJ", "Telefone", "Email", "Contato", "Endereço", 
                 "Condições Pagamento", "Lead Time (dias)", "Certificações", "Observações"],
    "raw_materials": ["Código", "Nome Usual", "Nome Químico", "Fornecedor", 
                     "Unidade Base", "Preço Base", "Densidade", "Fator Conversão", 
                     "Validade (dias)", "Localização"],
    "products": ["Código", "Nome", "Cliente", "Categoria", "Peso Unitário", 
                "UOM", "Peso Lote Padrão"]
}

def generate_import_template(template_type: str) -> BytesIO:
    """Generate Excel template for import"""
    if template_type not in IMPORT_TEMPLATES:
        raise ValueError(f"Template type '{template_type}' not supported")
    
    df = pd.DataFrame(columns=IMPORT_TEMPLATES[template_type])
    
    # Add sample row with example data
    if template_type == "suppliers":
        df.loc[0] = ["Fornecedor Exemplo", "12.345.678/0001-99", "(11) 1234-5678", 
                    "contato@fornecedor.com", "João Silva", "Rua Exemplo, 123",
                    "30 dias", 15, "ISO 9001", "Observações exemplo"]
    elif template_type == "raw_materials":
        df.loc[0] = ["MP001", "Açúcar Cristal", "Sacarose", "Fornecedor A", 
                    "KG", 2.50, 1.59, 1000, 365, "Estoque A"]
    elif template_type == "products":
        df.loc[0] = ["PA001", "Produto Exemplo", "Cliente A", "Categoria 1", 
                    100.0, "G", 1500.0]
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Dados', index=False)
    
    output.seek(0)
    return output
